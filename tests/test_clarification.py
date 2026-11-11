import pytest

from klippy.conversation import Conversation
from klippy.domain import Parameter
from klippy.macros import discover
from klippy.safety import NeedsParameter, Rejected


def parameterized_macro(store, sim):
    sim.config = {"gcode_macro LOAD_FILAMENT": {"gcode": "G1 E{params.LANE}"}}
    registry, _ = discover(sim.config, {})
    macro = registry["LOAD_FILAMENT"].model_copy(update={"approved": True, "enabled": True, "reviewed": True,
                    "parameters": {"LANE": Parameter(minimum=1.0, maximum=4.0, integer=True)}})
    store.replace_macros("sim", {macro.name: macro})


async def test_missing_parameter_followup_is_bound_to_draft(rig):
    store, sim, engine, _ = rig
    parameterized_macro(store, sim)
    c = Conversation(engine)
    with pytest.raises(NeedsParameter):
        await c.hear("load filament")
    assert "Confirm" in await c.hear("lane 3")
    assert not sim.writes
    await c.hear("confirm")
    assert b"LANE=3" in sim.writes[0][1]


async def test_canceled_parameter_draft_cannot_execute(rig):
    store, sim, engine, _ = rig
    parameterized_macro(store, sim)
    c = Conversation(engine)
    with pytest.raises(NeedsParameter):
        await c.hear("load filament")
    await c.hear("no")
    with pytest.raises(Rejected):
        await c.hear("3")
    assert not sim.writes


async def test_expired_parameter_draft_cannot_execute(rig):
    store, sim, engine, clock = rig
    parameterized_macro(store, sim)
    c = Conversation(engine, clock=lambda: clock[0])
    with pytest.raises(NeedsParameter):
        await c.hear("load filament")
    clock[0] += 31
    with pytest.raises(Rejected):
        await c.hear("3")
    assert not sim.writes
