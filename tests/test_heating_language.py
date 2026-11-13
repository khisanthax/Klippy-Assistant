import json
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from klippy.conversation import Conversation, LocalLLM
from klippy.diagnostics import Timings
from klippy.domain import Action, Intent, Printer, Snapshot
from klippy.language import heat_intent, normalize
from klippy.printer_names import matching, validate_names
from klippy.safety import Rejected


class NoModel:
    async def interpret(self, *args):
        pytest.fail("Deterministic request used the model")
    async def interpret_query(self, *args):
        pytest.fail("Heating request used the query model")


@pytest.fixture
def heating(rig):
    store, sim, engine, clock = rig
    store.save_printer(Printer(id="sim", name="Mercury One", aliases=("M1",), url="http://127.0.0.1:17125", approved=True))
    store.set("heater_limits", {"sim": {"0": 200, "1": 100}})
    return store, sim, engine, clock


@pytest.mark.parametrize("phrase", [
    "Hey Klippy, can you set the Mercury 1 nozzle to 90 degrees Celsius?",
    "Set M1's nozzle to 90 degrees.", "Can you set the Mercury 1 nozzle to 90 Celsius?",
    "Heat Mercury One's hotend to 90.", "Set the nozzle temperature to 90 on M1.",
    "Bring the nozzle up to 90 degrees.", "Please warm the extruder to ninety C.",
    "Could you please set Mercury One’s hot end to ninety degrees Celsius?",
    "Heat the nozzle to ninety", "Set M1’s nozzle temperature to 90°C!",
    "Set the nozzle to 194 degrees Fahrenheit on Mercury One", "Heat nozzle 194F",
])
async def test_owner_phrases_create_exact_heat_review_without_model_or_write(heating, phrase):
    _, sim, engine, _ = heating
    answer = await Conversation(engine, NoModel()).hear(phrase, source="voice" if phrase.startswith("Hey") else "manual")
    pending = Intent.model_validate_json(engine.pending.intent_json)
    assert pending.action == Action.HEAT and pending.printer_id == "sim"
    assert pending.params == {"heater": 0, "temperature": 90}
    assert "heat nozzle to 90 degrees Celsius on Mercury One" in answer
    assert not sim.writes


@pytest.mark.parametrize("unit,target", [("",90), (" C",90), (" Celsius",90), (" degrees",90),
    (" degrees Celsius",90), (" F", pytest.approx(32.22222222222222)),
    (" Fahrenheit",pytest.approx(32.22222222222222)), (" degrees Fahrenheit",pytest.approx(32.22222222222222))])
def test_default_and_explicit_units(unit, target):
    assert heat_intent("heat nozzle to 90" + unit, "sim").params["temperature"] == target


@pytest.mark.parametrize("text,value", [("ninety",90), ("one hundred and ninety four",194),
    ("two hundred twelve",212), ("ninety point five",90.5), ("ninety-five",95),
    ("minus five",-5), ("0.000001",.000001), (".5",.5)])
def test_numbers_and_decimal_precision(text, value):
    assert heat_intent("heat nozzle " + text, "sim").params["temperature"] == value


@pytest.mark.parametrize("phrase", ["set pressure advance", "set bed mesh"])
def test_non_heating_set_phrases_remain_available_to_macro_recognition(phrase):
    assert heat_intent(phrase, "sim") is None


@pytest.mark.parametrize("phrase", ["What's the nozzle temperature?", "How hot is Mercury 1's nozzle?",
                                    "What's M1's target temperature?"])
async def test_temperature_questions_never_become_heating(heating, phrase):
    _, sim, engine, _ = heating
    assert heat_intent(phrase, "sim") is None
    # The target query uses the capability-aware service; all mocks admit GET only.
    if "target" not in phrase:
        answer = await Conversation(engine, NoModel()).hear(phrase)
        assert "23" in answer
    assert engine.pending is None and not sim.writes


@pytest.mark.parametrize("phrase", ["Set the nozzle temperature", "heat nozzle to 90 K", "heat nozzle to 90 C F",
    "heat nozzle to 90 or 100", "heat nozzle to 90 and pause", "heat nozzle to NaN", "heat nozzle to infinity",
    "set unknown printer nozzle to 90", "heat chamber to 90", "heat nozzle to one ninety",
    "heat nozzle to 90 and bed to 60"])
async def test_ambiguous_or_incomplete_heat_never_uses_model(heating, phrase):
    _, sim, engine, _ = heating
    with pytest.raises(Rejected):
        await Conversation(engine, NoModel()).hear(phrase)
    assert engine.pending is None and not sim.writes


def test_name_normalization_uses_configured_labels_only_and_detects_collisions(heating):
    store, _, _, _ = heating
    mercury = store.printers()[0]
    assert matching([mercury], "Heat Mercury 1's nozzle") == [mercury]
    assert matching([mercury], "M1") == [mercury]
    assert not matching([mercury], "M2")
    other = Printer(id="other",name="Mercury 1",url="http://127.0.0.1:17126",approved=True)
    with pytest.raises(ValueError):
        validate_names(store, other, other.name, [])
    assert len(matching([mercury, other], "Heat Mercury One nozzle")) == 2


async def test_canonical_alias_ambiguity_never_selects_or_heats(heating):
    store, sim, engine, _ = heating
    # A pre-existing backup can contain collisions; matching must reject them too.
    store.save_printer(Printer(id="other",name="Mercury 1",url="http://127.0.0.1:17126",approved=True))
    with pytest.raises(Rejected, match="single printer"):
        await Conversation(engine, NoModel()).hear("Heat Mercury One nozzle to 90")
    assert store.get("selected") == "sim" and not sim.writes


async def test_printer_specific_limits_and_bed_selection(heating):
    store, sim, engine, _ = heating
    other = Printer(id="other",name="SV08",url="http://127.0.0.1:17126",approved=True)
    store.save_printer(other)
    with pytest.raises(Rejected, match="limits"):
        await Conversation(engine).hear("Heat SV08 nozzle 90")
    assert store.get("selected") == "other" and not sim.writes
    text = await Conversation(engine).hear("Heat M1 bed 90")
    assert "heat bed to 90 degrees Celsius on Mercury One" in text
    assert Intent.model_validate_json(engine.pending.intent_json).params["heater"] == 1


@pytest.mark.parametrize("phrase", ["heat nozzle to 194.000000000000001 F", "heat nozzle to 90.000000000000001 C",
                                    "heat nozzle to 212 F", "heat nozzle to -1", "heat nozzle to 31 F"])
async def test_converted_values_cannot_round_into_reviewed_limits(heating, phrase):
    store, sim, engine, _ = heating
    store.set("heater_limits", {"sim": {"0": 90}})
    with pytest.raises(Rejected, match="limits"):
        await Conversation(engine, NoModel()).hear(phrase)
    assert not sim.writes and engine.pending is None


@pytest.mark.parametrize("maximum", [None, "200", True, float("inf"), float("nan"), -1])
async def test_invalid_limit_records_never_allow_heat(heating, maximum):
    store, sim, engine, _ = heating
    store.set("heater_limits", {"sim": {"0": maximum}})
    with pytest.raises(Rejected, match="limits"):
        await Conversation(engine).hear("heat nozzle 90")
    assert not sim.writes


async def test_missing_heater_is_checked_at_proposal_and_confirmation(heating):
    _, sim, engine, _ = heating
    await Conversation(engine).hear("heat nozzle 90")
    token = engine.pending.token
    class Missing:
        async def snapshot(self):
            return Snapshot(connected=True,ready=True,state="standby",temperatures={"heater_bed":21.0})
        async def execute(self, *args):
            pytest.fail("Missing heater reached write transport")
    engine.clients = lambda p: Missing()
    with pytest.raises(Rejected, match="valid temperature"):
        await engine.confirm(token)
    with pytest.raises(Rejected):
        await Conversation(engine).hear("heat nozzle 90")
    assert not sim.writes


@pytest.mark.parametrize("phrase", ["No, don't do that.", "Cancel that request.", "Never mind.", "Don't heat the nozzle."])
async def test_only_explicit_cancellation_discards_pending(heating, phrase):
    _, sim, engine, _ = heating
    c = Conversation(engine)
    await c.hear("heat nozzle 90")
    assert "canceled" in await c.hear(phrase)
    assert engine.pending is None and not sim.writes


@pytest.mark.parametrize("phrase", ["I'm not sure why it didn't understand.", "That's not what I meant.",
                                    "I don't know what happened.", "I never said to heat it."])
async def test_comments_clarify_without_canceling_or_allowing_stale_confirmation(heating, phrase):
    _, sim, engine, _ = heating
    c = Conversation(engine)
    await c.hear("heat nozzle 90", defer_confirmation=True)
    token = engine.pending.token
    text = await c.hear(phrase)
    assert "canceled" not in text and "restate" in text
    assert engine.pending and engine.pending.token == token and engine.pending.clarification_required
    engine.delivery_finished(token, True)
    assert not engine.pending.ready
    with pytest.raises(Rejected, match="clarifying"):
        await engine.confirm(token)
    await c.hear("heat nozzle 80")
    assert engine.pending.token != token and not engine.pending.clarification_required
    assert not sim.writes


async def test_confirmed_fahrenheit_executes_converted_celsius_once_and_never_retries(heating):
    _, sim, engine, _ = heating
    c = Conversation(engine)
    text = await c.hear("heat nozzle 194 F")
    assert "90 degrees Celsius" in text
    token = engine.pending.token
    sim.timeout_on_write = True
    assert "unknown" in await engine.confirm(token)
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert len(sim.writes) == 1 and json.loads(sim.writes[0][1])["script"] == "M104 S90"


async def test_disabled_confirmation_preserves_conversion_and_limits(heating):
    store, sim, engine, _ = heating
    store.set("confirmations", {"heat":False})
    c = Conversation(engine, NoModel())
    await c.hear("heat nozzle 194 F")
    assert len(sim.writes) == 1 and json.loads(sim.writes[0][1])["script"] == "M104 S90"
    with pytest.raises(Rejected):
        await c.hear("heat nozzle 500 F")
    assert len(sim.writes) == 1


@pytest.mark.parametrize("action", ["temperatures", "status", "pause"])
async def test_model_parameters_attached_to_wrong_action_reject_with_safe_diagnostic(heating, action):
    _, sim, engine, _ = heating
    content = json.dumps({"intent":{"action":action,"printer_id":"sim","params":{"heater":0,"temperature":90}},"question":None})
    response = httpx.Response(200,json={"choices":[{"message":{"content":content}}]}, request=httpx.Request("POST","http://127.0.0.1"))
    async def post(*args, **kwargs):
        return response
    with patch("httpx.AsyncClient.post",post):
        with pytest.raises(Rejected) as failure:
            await LocalLLM().interpret("adjust the nozzle to 90", "sim", {})
    assert failure.value.code == "intent_parameters_for_" + action
    assert "Unexpected parameters" not in str(failure.value) and failure.value.code not in str(failure.value)
    assert not sim.writes and engine.pending is None


async def test_injected_model_mismatch_cannot_reach_engine_dispatch(heating):
    _, sim, engine, _ = heating
    class WrongModel:
        async def interpret(self, *args):
            return Intent(action=Action.TEMPERATURES,printer_id="sim",params={"heater":0,"temperature":90})
    with pytest.raises(Rejected) as failure:
        await Conversation(engine, WrongModel()).hear("adjust the nozzle to 90")
    assert failure.value.code == "intent_parameters_for_temperatures" and not sim.writes


def test_diagnostics_show_code_without_speaking_or_retaining_utterance():
    metrics = Timings()
    trace = metrics.new()
    metrics.error("intent_parameters_for_temperatures",trace)
    assert metrics.snapshot()[-1]["error_code"] == "intent_parameters_for_temperatures"
    assert "Latest diagnostic: intent_parameters_for_temperatures" in metrics.compact()
    assert normalize("Mercury One’s nozzle, ninety degrees Celsius!") == "mercury 1 nozzle 90 degrees celsius"


@pytest.mark.parametrize("text,params,valid", [
    ("heat nozzle to 194 F", {"heater":0,"temperature":90}, True),
    ("heat nozzle to 32 F", {"heater":0,"temperature":0}, True),
    ("heat nozzle to 90 F", {"heater":0,"temperature":90}, False),
    ("heat bed to 90", {"heater":0,"temperature":90}, False),
    ("What's the nozzle temperature?", {"heater":0,"temperature":90}, False),
    ("heat nozzle to 90", {"target":90}, False),
])
async def test_model_heat_must_agree_with_independent_celsius_parse(text, params, valid):
    content = json.dumps({"intent":{"action":"heat","printer_id":"sim","params":params},"question":None})
    response = httpx.Response(200,json={"choices":[{"message":{"content":content}}]},request=httpx.Request("POST","http://127.0.0.1"))
    async def post(*args, **kwargs):
        return response
    with patch("httpx.AsyncClient.post",post):
        if valid:
            result = await LocalLLM().interpret(text,"sim",{})
            assert result.params == params
        else:
            with pytest.raises(Rejected) as failure:
                await LocalLLM().interpret(text,"sim",{})
            assert failure.value.code == "model_heat_target_mismatch"


async def test_unapproved_printer_cannot_be_heated_by_alias(heating):
    store, sim, engine, _ = heating
    printer = store.printers()[0]
    store.save_printer(printer.model_copy(update={"approved":False}))
    with pytest.raises(Rejected,match="not approved"):
        await Conversation(engine).hear("heat Mercury 1 nozzle 90")
    assert not sim.writes


async def test_changed_reviewed_limit_blocks_converted_pending_target(heating):
    store, sim, engine, _ = heating
    await Conversation(engine).hear("heat nozzle 194 Fahrenheit")
    token = engine.pending.token
    store.set("heater_limits", {"sim":{"0":80}})
    with pytest.raises(Rejected,match="limits"):
        await engine.confirm(token)
    assert not sim.writes


async def test_clarification_during_validation_cannot_resurrect_pending(heating):
    import asyncio
    _, sim, engine, _ = heating
    entered, release = asyncio.Event(), asyncio.Event()
    original = engine.validate
    async def slow(intent):
        value = await original(intent)
        entered.set()
        await release.wait()
        return value
    engine.validate = slow
    c = Conversation(engine)
    task = asyncio.create_task(c.hear("heat nozzle 90"))
    await entered.wait()
    assert "canceled" not in await c.hear("That's not what I meant")
    release.set()
    with pytest.raises(Rejected):
        await task
    assert engine.pending is None and not sim.writes


async def test_packaged_command_probe_requires_all_twenty_cases_without_writes():
    from klippy.command_probe import run
    report = await run()
    assert report["passed"] and len(report["cases"]) == 20
    assert report["printer_writes"] == report["supported_request_llm_calls"] == 0
    assert not report["pending_write"]


@pytest.mark.parametrize("field,value", [("passed",False), ("printer_writes",1),
                                       ("supported_request_llm_calls",1), ("pending_write",True)])
def test_preview_rejects_failed_command_qualification(field, value):
    from klippy.voice_probe import qualify_preview_report
    report = json.loads((Path(__file__).parents[1] / "benchmarks/preview5-release-frozen.json").read_text())
    report["heat_fix_probe"] = {"passed":True,"printer_writes":0,"supported_request_llm_calls":0,"pending_write":False}
    report["heat_fix_probe"][field] = value
    qualify_preview_report(report)
    assert not report["preview_gates"]["heating_parser_and_cancel_safety"]
    assert not report["engineering_preview_passed"]
