import asyncio
import json

import pytest
from pydantic import ValidationError

from klippy.domain import Action, Intent
from klippy.macros import discover
from klippy.safety import Rejected


def intent(action, **kwargs):
    return Intent(action=action, printer_id="sim", **kwargs)


def approve(store, sim):
    registry, _ = discover(sim.config, store.macros("sim"))
    registry = {name: m.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                for name, m in registry.items()}
    store.replace_macros("sim", registry)


async def test_status_and_temperatures_never_write(rig):
    _store, sim, engine, _ = rig
    assert "63%" in await engine.propose(intent(Action.STATUS))
    assert "23.0" in await engine.propose(intent(Action.TEMPERATURES))
    assert not sim.writes


async def test_confirmation_is_required_and_single_use(rig):
    _, sim, engine, _ = rig
    sim.state = "printing"
    assert "Confirm" in await engine.propose(intent(Action.PAUSE))
    assert not sim.writes
    token = engine.pending.token
    assert "paused" in await engine.confirm(token)
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert len(sim.writes) == 1


async def test_expired_confirmation(rig):
    _, sim, engine, clock = rig
    await engine.propose(intent(Action.HOME))
    token = engine.pending.token
    clock[0] += 26
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert not sim.writes


async def test_wrong_confirmation_cannot_execute(rig):
    _, sim, engine, _ = rig
    await engine.propose(intent(Action.HOME))
    with pytest.raises(Rejected):
        await engine.confirm("unrelated speech")
    assert not sim.writes


async def test_state_revalidated_at_confirmation(rig):
    _, sim, engine, _ = rig
    await engine.propose(intent(Action.HOME))
    token = engine.pending.token
    sim.state = "printing"
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert not sim.writes


async def test_new_unapproved_macro_cannot_execute(rig):
    store, sim, engine, _ = rig
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.MACRO, macro="LOAD_FILAMENT"))
    assert not store.macros("sim")["LOAD_FILAMENT"].approved
    assert not sim.writes


async def test_changed_macro_revokes_approval(rig):
    store, sim, engine, _ = rig
    approve(store, sim)
    await engine.propose(intent(Action.MACRO, macro="LOAD_FILAMENT"))
    token = engine.pending.token
    sim.config["gcode_macro LOAD_FILAMENT"]["gcode"] = "M104 S250"
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert not store.macros("sim")["LOAD_FILAMENT"].approved
    assert not sim.writes


async def test_changed_callee_revokes_caller_approval(rig):
    store, sim, engine, _ = rig
    sim.config["gcode_macro HELPER"] = {"gcode": "M83"}
    approve(store, sim)
    sim.config["gcode_macro HELPER"] = {"gcode": "M104 S280"}
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.MACRO, macro="LOAD_FILAMENT"))
    assert not sim.writes


async def test_removed_macro_does_not_execute(rig):
    store, sim, engine, _ = rig
    approve(store, sim)
    sim.config.clear()
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.MACRO, macro="LOAD_FILAMENT"))
    assert not store.macros("sim")
    assert not sim.writes


async def test_excluded_macro_is_unavailable(rig):
    store, sim, engine, _ = rig
    approve(store, sim)
    registry = store.macros("sim")
    registry["LOAD_FILAMENT"] = registry["LOAD_FILAMENT"].model_copy(update={"enabled": False})
    store.replace_macros("sim", registry)
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.MACRO, macro="LOAD_FILAMENT"))
    assert not sim.writes


async def test_macro_accepted_does_not_claim_completion(rig):
    store, sim, engine, _ = rig
    approve(store, sim)
    await engine.propose(intent(Action.MACRO, macro="LOAD_FILAMENT"))
    assert "completion has not been verified" in await engine.confirm(engine.pending.token)
    assert len(sim.writes) == 1


async def test_write_timeout_never_retries_or_claims_failure(rig):
    _, sim, engine, _ = rig
    sim.timeout_on_write = True
    await engine.propose(intent(Action.HOME))
    result = await engine.confirm(engine.pending.token)
    assert "unknown" in result
    assert "secret" not in result
    assert engine.pending is None
    assert len(sim.writes) == 1


async def test_disconnect_invalidates_confirmation(rig):
    from klippy.moonraker import ConnectionFailure
    _, sim, engine, _ = rig
    await engine.propose(intent(Action.HOME))
    sim.offline = True
    with pytest.raises(ConnectionFailure):
        await engine.confirm(engine.pending.token)
    assert engine.pending is None
    assert not sim.writes


async def test_emergency_uses_dedicated_endpoint(rig):
    _, sim, engine, _ = rig
    sim.ready = False
    await engine.propose(intent(Action.EMERGENCY))
    await engine.confirm(engine.pending.token)
    assert sim.writes[0][0] == "/printer/emergency_stop"


@pytest.mark.parametrize("macro", ["LOAD_FILAMENT\nG28", "G28;M112", "BAD NAME"])
async def test_gcode_injection_in_name_blocked(rig, macro):
    _, sim, engine, _ = rig
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.MACRO, macro=macro))
    assert not sim.writes


@pytest.mark.parametrize("params", [{"LANE": "3\nG28"}, {"LANE": True}, {"LANE": float("nan")}])
def test_malformed_parameters_rejected(params):
    with pytest.raises(ValidationError):
        intent(Action.MACRO, macro="LOAD_FILAMENT", params=params)


async def test_unknown_parameters_blocked(rig):
    store, sim, engine, _ = rig
    approve(store, sim)
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.MACRO, macro="LOAD_FILAMENT", params={"LANE": 3}))
    assert not sim.writes


async def test_heat_needs_active_limits_even_with_owner_cap(rig):
    store, sim, engine, _ = rig
    sim.settings.pop('extruder')
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.HEAT, params={"temperature": 200, "heater": 0}))
    store.set("heater_limits", {"sim": {"0": 220}})
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.HEAT, params={"temperature": 200, "heater": 0}))
    sim.settings['extruder'] = {'min_temp': 0, 'max_temp': 250}
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.HEAT, params={"temperature": 230, "heater": 0}))
    assert not sim.writes


async def test_unenrolled_target_blocked(rig):
    _, sim, engine, _ = rig
    with pytest.raises(Rejected):
        await engine.propose(Intent(action=Action.HOME, printer_id="other"))
    assert not sim.writes


async def test_ui_cancel_during_slow_validation_prevents_dispatch(rig):
    _, sim, engine, _ = rig
    await engine.propose(intent(Action.HOME))
    token = engine.pending.token
    original = engine.validate
    entered, release = asyncio.Event(), asyncio.Event()
    async def slow(value):
        result = await original(value)
        entered.set()
        await release.wait()
        return result
    engine.validate = slow
    task = asyncio.create_task(engine.confirm(token))
    await entered.wait()
    engine.cancel()
    release.set()
    with pytest.raises(Rejected):
        await task
    assert not sim.writes


async def test_cancel_during_proposal_does_not_resurrect_confirmation(rig):
    _, _sim, engine, _ = rig
    original = engine.validate
    async def slow(value):
        result = await original(value)
        engine.cancel()
        return result
    engine.validate = slow
    with pytest.raises(Rejected):
        await engine.propose(intent(Action.HOME))
    assert engine.pending is None


def test_extra_llm_fields_rejected():
    with pytest.raises(ValidationError):
        Intent.model_validate_json(json.dumps({"action": "home", "printer_id": "sim", "gcode": "G28"}))
