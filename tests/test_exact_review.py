import json

import pytest
from pydantic import ValidationError

from klippy.conversation import Conversation
from klippy.domain import Action, Intent, Parameter
from klippy.macros import discover
from klippy.safety import Rejected


def reviewed_macro(store, sim, parameters):
    definition = "M105 # " + " ".join("{params." + key + "}" for key in parameters)
    sim.config = {"gcode_macro FEED": {"gcode": definition}}
    registry, _ = discover(sim.config, {})
    store.replace_macros("sim", {"FEED": registry["FEED"].model_copy(update={
        "approved": True, "enabled": True, "reviewed": True, "parameters": parameters})})


@pytest.mark.parametrize("value,minimum,maximum", [
    (999999.9, 0.0, 999999.9), (1.0000007, 1.0000006, 1.0000008), (0.0000001, 0.00000001, 0.000001),
])
async def test_macro_review_and_transmission_preserve_validated_number(rig, value, minimum, maximum):
    store, sim, engine, _ = rig
    reviewed_macro(store, sim, {"DISTANCE": Parameter(minimum=minimum, maximum=maximum)})
    text = await engine.propose(Intent(action=Action.MACRO, printer_id="sim", macro="FEED", params={"DISTANCE": value}))
    assert "macro FEED" in text and "DISTANCE=" in text and "Test Printer" in text
    await engine.confirm(engine.pending.token)
    script = json.loads(sim.writes[0][1])["script"]
    number = script.split("DISTANCE=", 1)[1]
    assert float(number) == value and minimum <= float(number) <= maximum
    assert "e" not in number.lower() and f"DISTANCE={number}" in text
    assert len(sim.writes) == 1


async def test_heat_review_echoes_heater_temperature_and_fixed_decimal(rig):
    store, sim, engine, _ = rig
    store.set("heater_limits", {"sim": {"0": 250}})
    text = await engine.propose(Intent(action=Action.HEAT, printer_id="sim", params={"heater": 0, "temperature": .000001}))
    assert "heat nozzle to 0.000001 degrees Celsius on Test Printer" in text
    await engine.confirm(engine.pending.token)
    assert json.loads(sim.writes[0][1])["script"] == "M104 S0.000001"


async def test_home_review_explicitly_identifies_all_axes(rig):
    _, sim, engine, _ = rig
    assert "home all axes on Test Printer" in await engine.propose(Intent(action=Action.HOME, printer_id="sim"))
    assert not sim.writes


@pytest.mark.parametrize("minimum,maximum", [(float("nan"), 10.0), (0.0, float("inf")), (10.0, 1.0)])
def test_parameter_review_requires_finite_ordered_bounds(minimum, maximum):
    with pytest.raises(ValidationError):
        Parameter(minimum=minimum, maximum=maximum)


async def test_model_interpretation_cannot_opt_out_of_explicit_review(rig):
    store, sim, engine, _ = rig
    store.set("confirmations", {"home": False})
    class Model:
        async def interpret(self, *args):
            return Intent(action=Action.HOME, printer_id="sim")
    text = await Conversation(engine, Model()).hear("home only Z")
    assert "Model interpretation requires explicit review" in text and "all axes" in text
    assert engine.pending and not sim.writes


async def test_explicit_heat_can_opt_out_but_never_bypass_limits(rig):
    store, sim, engine, _ = rig
    store.set("confirmations", {"heat": False})
    store.set("heater_limits", {"sim": {"0": 210}})
    class Model:
        async def interpret(self, *args):
            pytest.fail("Explicit supported heat request reached model")
    c = Conversation(engine, Model())
    assert "accepted" in await c.hear("Please heat the nozzle to 205.5 degrees Celsius")
    assert json.loads(sim.writes[0][1])["script"] == "M104 S205.5"
    with pytest.raises(Rejected, match="limits"):
        await c.hear("heat nozzle to 211")
    assert len(sim.writes) == 1


async def test_action_too_long_to_review_cannot_create_a_confirmation(rig):
    store, sim, engine, _ = rig
    keys = ["P" + str(index) + "_" + "A" * 80 for index in range(8)]
    reviewed_macro(store, sim, {key: Parameter(minimum=0.0, maximum=2.0) for key in keys})
    with pytest.raises(Rejected, match="complete voice review limit"):
        await engine.propose(Intent(action=Action.MACRO, printer_id="sim", macro="FEED", params=dict.fromkeys(keys, 1)))
    assert engine.pending is None and not sim.writes


async def test_bare_cancel_cannot_cancel_a_print_when_prompt_is_disabled(rig):
    store, sim, engine, _ = rig
    sim.state = "printing"
    store.set("confirmations", {"cancel": False})
    await engine.propose(Intent(action=Action.PAUSE, printer_id="sim"))
    c = Conversation(engine)
    assert "canceled" in await c.hear("cancel")
    assert engine.pending is None and not sim.writes and sim.state == "printing"
    assert "cancelled" in await c.hear("cancel print")
    assert len(sim.writes) == 1 and sim.state == "cancelled"
