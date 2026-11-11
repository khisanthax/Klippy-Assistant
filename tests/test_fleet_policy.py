import httpx
import pytest

from klippy.conversation import Conversation
from klippy.domain import Action, Intent, Macro, Printer
from klippy.macros import candidates, conflicts, discover
from klippy.mmu import normalize
from klippy.monitor import Monitor
from klippy.moonraker import Moonraker
from klippy.safety import Rejected


@pytest.mark.parametrize("key", ["print_state", "print_job_state"])
async def test_mmu_faults_are_deduplicated_per_printer_and_never_write(rig, key):
    store, _, _, _ = rig
    store.save_printer(Printer(id="second", name="Second", url="http://127.0.0.1:7126", approved=True))
    states = {"sim": "pause_locked", "second": "printing"}
    requests = []
    def factory(printer):
        def handle(request):
            requests.append(request.method)
            assert request.method == "GET"
            if request.url.path.endswith("list"):
                result = {"objects": ["mmu"]}
            elif request.url.query == b"mmu":
                result = {"status": {"mmu": {key: states[printer.id], "tool": 2, "gate": 3}}}
            elif b"configfile" in request.url.query:
                result = {"status": {"configfile": {"config": {}}}}
            else:
                result = {"status": {"webhooks": {"state": "ready"}, "print_stats": {"state": "printing"}}}
            return httpx.Response(200, json={"result": result})
        return Moonraker(printer, transport=httpx.MockTransport(handle))
    monitor = Monitor(store, factory)
    assert await monitor.poll() == [("Test Printer", "mmu_fault")]
    assert await monitor.poll() == []
    states["second"] = "error"
    assert await monitor.poll() == [("Second", "mmu_fault")]
    states["sim"] = "printing"
    await monitor.poll()
    states["sim"] = "pause_locked"
    assert await monitor.poll() == [("Test Printer", "mmu_fault")]
    assert set(requests) == {"GET"}


def test_mmu_unknown_and_malformed_never_invent_fault_or_tool():
    assert not normalize({}).available
    mmu = normalize({"tool": True, "gate": "3", "print_state": []})
    assert mmu.tool is None and mmu.gate is None and not mmu.fault


async def test_disabled_confirmation_still_revalidates_and_executes_once(rig):
    store, sim, engine, _ = rig
    store.set("confirmations", {"home": False})
    assert "accepted" in await engine.propose(Intent(action=Action.HOME, printer_id="sim"))
    assert len(sim.writes) == 1 and engine.pending is None
    with pytest.raises(Rejected):
        await engine.confirm("anything")
    sim.state = "printing"
    with pytest.raises(Rejected):
        await engine.propose(Intent(action=Action.HOME, printer_id="sim"))
    assert len(sim.writes) == 1


async def test_disabled_confirmation_never_skips_fresh_validation(rig):
    store, sim, engine, _ = rig
    store.set("confirmations", {"home": False})
    original = engine.validate
    calls = []
    async def changed(intent):
        result = await original(intent)
        calls.append(True)
        sim.state = "printing"
        return result
    engine.validate = changed
    with pytest.raises(Rejected):
        await engine.propose(Intent(action=Action.HOME, printer_id="sim"))
    assert not sim.writes and len(calls) == 1


async def test_macros_and_critical_actions_ignore_disabled_confirmation_setting(rig):
    store, sim, engine, _ = rig
    store.set("confirmations", {"macro": False, "emergency_stop": False})
    await engine.propose(Intent(action=Action.EMERGENCY, printer_id="sim"))
    assert engine.pending and not sim.writes
    registry, _ = discover(sim.config, {})
    store.replace_macros("sim", {k: v.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                                for k, v in registry.items()})
    await engine.propose(Intent(action=Action.MACRO, printer_id="sim", macro="LOAD_FILAMENT"))
    assert engine.pending and not sim.writes


async def test_policy_change_invalidates_existing_exact_confirmation(rig):
    store, sim, engine, _ = rig
    await engine.propose(Intent(action=Action.HOME, printer_id="sim"))
    token = engine.pending.token
    store.set("confirmations", {"home": False})
    with pytest.raises(Rejected, match="changed"):
        await engine.confirm(token)
    assert not sim.writes


def test_function_similarity_and_rename_never_transfer_approval():
    old = {"OLD": Macro(name="OLD", definition="M83\nG1 E5", approved=True, enabled=True, reviewed=True)}
    registry, notices = discover({"gcode_macro NEW": {"gcode": "M83 # comment\n G1 E5"},
                                  "gcode_macro OTHER": {"gcode": "M83\nG1 E5"}}, old)
    assert any("Similar function" in n for n in notices)
    assert any("Possible rename" in n for n in notices)
    assert all(not m.approved and m.previous_definition == old["OLD"].definition for m in registry.values())
    assert conflicts(registry)


async def test_natural_macro_synonym_preserves_approval_and_target(rig):
    store, sim, engine, _ = rig
    registry, _ = discover(sim.config, {})
    store.replace_macros("sim", {k: v.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                                for k, v in registry.items()})
    assert candidates("could you please feed some filament", store.macros("sim")) == ["LOAD_FILAMENT"]
    assert "Confirm macro" in await Conversation(engine).hear("feed filament")
    assert engine.pending and not sim.writes
    assert not candidates("eject filament", {"LOAD_FILAMENT": registry["LOAD_FILAMENT"]})


async def test_unreviewed_natural_parameter_never_silently_uses_macro_defaults(rig):
    store, sim, engine, _ = rig
    registry, _ = discover(sim.config, {})
    store.replace_macros("sim", {k: v.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                                for k, v in registry.items()})
    with pytest.raises(Rejected, match="unknown parameters"):
        await Conversation(engine).hear("feed filament speed 9999")
    assert engine.pending is None and not sim.writes


@pytest.mark.parametrize("access", ["params . get('DISTANCE', 500)", "params.get('DISTANCE', 500)"])
async def test_method_style_dynamic_parameters_are_blocked(rig, access):
    store, sim, engine, _ = rig
    sim.config = {"gcode_macro LOAD_FILAMENT": {"gcode": "G1 E{" + access + "}"}}
    registry, _ = discover(sim.config, {})
    store.replace_macros("sim", {k: v.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                                for k, v in registry.items()})
    with pytest.raises(Rejected):
        await engine.propose(Intent(action=Action.MACRO, printer_id="sim", macro="LOAD_FILAMENT"))
    assert engine.pending is None and not sim.writes


async def test_disabled_heat_prompt_cannot_bypass_reviewed_limits(rig):
    store, sim, engine, _ = rig
    store.set("confirmations", {"heat": False})
    store.set("heater_limits", {"sim": {"0": 200}})
    with pytest.raises(Rejected, match="limits"):
        await engine.propose(Intent(action=Action.HEAT, printer_id="sim", params={"heater": 0, "temperature": 250}))
    assert not sim.writes
