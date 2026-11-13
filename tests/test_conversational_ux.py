import httpx
import pytest
from test_queries import QuerySimulator

from klippy.conversation import Conversation
from klippy.domain import Printer
from klippy.moonraker import Moonraker
from klippy.presentation import Response, friendly_error, present
from klippy.printer_names import matching, rename
from klippy.queries import QueryRequest, QueryService, match_query
from klippy.safety import Rejected
from klippy.storage import Store


@pytest.fixture
def queries(rig):
    store, _, engine, clock = rig
    sim = QuerySimulator()
    rename(store, store.printers()[0], "M1", ["Mercury One"])
    def factory(printer):
        return Moonraker(printer, transport=httpx.MockTransport(sim.handle))
    engine.clients = factory
    return sim, QueryService(store, factory, clock=lambda: clock[0]), engine, clock


@pytest.mark.parametrize("phrase", ["Switch to M1", "Switch to Mercury Two", "Use the SV08",
    "Change printers to Mercury One", "Select my M1 printer", "Go back to Mercury Two"])
async def test_natural_switch_is_local_and_cancels_pending(rig, phrase):
    store, sim, engine, _ = rig
    one = rename(store, store.printers()[0], "M1", ["Mercury One"])
    store.save_printer(Printer(id="two", name="SV08", aliases=("Mercury Two",),
                              url="http://127.0.0.1:7126", approved=True))
    c = Conversation(engine)
    await c.hear("home")
    token = engine.pending.token
    answer = await c.hear(phrase)
    expected = "two" if "Two" in phrase or "SV08" in phrase else one.id
    assert store.get("selected") == expected and "selected" in answer
    assert engine.pending is None and not sim.writes
    with pytest.raises(Rejected):
        await engine.confirm(token)


@pytest.mark.parametrize("phrase", ["Which printer am I using?", "What printer are you connected to?"])
async def test_active_printer_is_answered_without_model_or_network(rig, phrase):
    _, sim, engine, _ = rig
    class NoModel:
        async def interpret(self, *args):
            pytest.fail("Active target query invoked model")
    assert await Conversation(engine, NoModel()).hear(phrase) == "You're using Test Printer."
    assert not sim.writes


@pytest.mark.parametrize("phrase", ["Switch to Mars", "Use the unknown printer", "heat nozzle", "heat"])
async def test_incomplete_requests_clarify_without_model_or_action(rig, phrase):
    _, sim, engine, _ = rig
    with pytest.raises(Rejected, match="[Ww]hich|[Ww]hat"):
        await Conversation(engine).hear(phrase)
    assert not sim.writes and engine.pending is None


def test_names_survive_restart_and_removed_alias_stops_matching(rig):
    store, _, _, _ = rig
    printer = rename(store, store.printers()[0], "Mercury One", ["M1", "first printer"])
    assert matching(store.printers(), "Switch to m1") == [printer]
    assert not matching(store.printers(), "M10")
    rename(store, printer, "Mercury One", ["first printer"])
    reopened = Store(store.path)
    try:
        assert reopened.printers()[0].aliases == ("first printer",)
        assert not matching(reopened.printers(), "M1")
    finally:
        reopened.close()


@pytest.mark.parametrize("name,aliases", [("Other", []), ("New", ["other alias"]),
                                         ("M1", ["m1"]), (" ", []), ("Good", [" "])])
def test_conflicting_or_empty_names_never_save(rig, name, aliases):
    store, _, _, _ = rig
    original = store.printers()[0]
    store.save_printer(Printer(id="other", name="Other", aliases=("Other Alias",), url="http://127.0.0.1:7126"))
    with pytest.raises(ValueError):
        rename(store, original, name, aliases)
    assert next(p for p in store.printers() if p.id == original.id) == original


async def test_wake_once_heater_followup_and_other_printer_preserve_subject(queries):
    sim, service, engine, clock = queries
    c = Conversation(engine, clock=lambda: clock[0], queries=service)
    assert await c.hear("Hey Klippy", source="voice") == "I'm listening."
    value = await c.hear("How hot is the nozzle?", source="voice")
    assert "206 degrees" in value.spoken and "205.5" in str(value)
    value = await c.hear("And the bed?", source="voice")
    assert "60 degrees" in value.spoken and "nozzle" not in value.spoken
    engine.store.save_printer(Printer(id="two", name="SV08", url="http://127.0.0.1:7126", approved=True))
    value = await c.hear("What about the SV08?", source="voice")
    assert "SV08" in value.spoken and "bed" in value.spoken
    assert all(method == "GET" for method, _, _ in sim.calls)
    clock[0] += 31
    assert await c.hear("And the nozzle?", source="voice") is None


async def test_stale_speech_never_claims_current_state(queries):
    sim, service, _, clock = queries
    await service.answer("sim", QueryRequest(query_id="homing"))
    clock[0] += 3
    sim.fail = True
    value = await service.answer("sim", QueryRequest(query_id="homing"))
    assert "STALE" in value and "can't verify" in value.spoken and "homed" not in value.spoken


@pytest.mark.parametrize("style", ["brief", "conversational", "detailed"])
async def test_style_does_not_change_raw_values_or_authority(queries, style):
    sim, service, engine, _ = queries
    engine.store.set("response_style", style)
    sim.status["extruder"].update(temperature=25.75, target=0)
    sim.status["heater_bed"].update(temperature=30.25, target=0)
    value = await service.answer("sim", QueryRequest(query_id="temperatures"))
    assert "25.75" in value and "30.25" in value
    assert "chamber" not in value.spoken and "active heating targets" in value.spoken
    assert "powered off" not in value.spoken
    assert ("25.75" if style == "detailed" else "26 degrees") in value.spoken
    assert not engine.pending


@pytest.mark.parametrize("axes,expected", [("xyz", "fully homed"), ("xy", "Z is not homed"),
    ("", "X, Y, Z are not homed"), ("xx", "hasn't reported"), (None, "hasn't reported")])
def test_homing_spoken_is_factual(axes, expected):
    assert expected in present("M1", "homing", {"toolhead": {"homed_axes": axes}}, "raw").spoken


def test_unknown_safety_warnings_are_never_reworded():
    for warning in ["Outcome uncertain; do not retry", "Heater limit unavailable; action blocked",
                    "Confirm heating the nozzle to 210 degrees", "Printer shutdown: temperature error"]:
        assert friendly_error(warning) == warning
    assert "say that another way" in friendly_error("Please clarify the information query; no action sent")
    assert Response("exact", "friendly") == "exact"


def test_concise_status_keeps_unexpected_ready_state_warning():
    status = {"webhooks": {"state": "ready", "state_message": "Inspect heater wiring before operating"},
              "print_stats": {"state": "standby", "message": "Check filament path"}}
    for style in ("brief", "conversational", "detailed"):
        speech = present("M1", "status", status, "raw", style=style).spoken
        assert "Inspect heater wiring before operating" in speech and "Check filament path" in speech


async def test_auxiliary_sensor_speech_requires_explicit_request(queries):
    _, service, _, _ = queries
    answer = await service.answer("sim", match_query("How hot is the chamber?"))
    assert "chamber is at 35 degrees" in answer.spoken and "nozzle" not in answer.spoken
    ordinary = await service.answer("sim", match_query("What are the temperatures?"))
    assert "chamber" not in ordinary.spoken


def test_response_style_backup_restore_and_invalid_value_are_atomic(rig, tmp_path):
    import json
    store = rig[0]
    store.set("response_style", "detailed")
    path = tmp_path / "private.json"
    store.export(path)
    store.set("response_style", "brief")
    store.restore(path)
    assert store.get("response_style") == "detailed"
    payload = json.loads(path.read_text())
    payload["preferences"]["response_style"] = ["invalid"]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        store.restore(path)
    assert store.get("response_style") == "detailed"
