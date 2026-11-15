import asyncio
import json
from types import SimpleNamespace

import pytest

from klippy.conversation import Conversation
from klippy.dialogue import compose
from klippy.dialogue_probe import simulator
from klippy.moonraker import Moonraker
from klippy.presentation import Response
from klippy.queries import QueryService
from klippy.safety import Rejected


class Planner:
    def __init__(self):
        self.calls = []

    async def compose_reply(self, *args):
        self.calls.append(args)
        return {"opening": args[2][0], "parts": [0, 1], "closing": ""}


def conversation(rig, model=None):
    store, _, engine, clock = rig
    transport, writes = simulator()
    engine.clients = lambda p: Moonraker(p, transport=transport)
    service = QueryService(store, engine.clients, clock=lambda: clock[0])
    return Conversation(engine, model, clock=lambda: clock[0], queries=service), writes


@pytest.mark.parametrize(
    "text",
    [
        "hello",
        "hi Klippy",
        "good morning",
        "how are you",
        "thank you",
        "who are you",
        "tell me a joke",
        "are you there",
    ],
)
async def test_casual_turns_need_no_printer_or_model(rig, text):
    c, writes = conversation(rig)
    rig[0].set("selected", None)
    answer = await c.hear(text)
    assert answer and c.engine.pending is None and not writes


async def test_casual_voice_still_requires_wake_or_active_session(rig):
    c, writes = conversation(rig)
    assert await c.hear("hello", source="voice") is None
    assert await c.hear("Hey Klippy hello", source="voice")
    assert await c.hear("thank you", source="voice")
    rig[3][0] += 31
    assert await c.hear("hello", source="voice") is None and not writes


async def test_routine_followups_and_corrections_are_fast_no_model(rig):
    planner = Planner()
    c, writes = conversation(rig, planner)
    nozzle = await c.hear("Hey Klippy how hot is the nozzle?", source="voice")
    bed = await c.hear("and the bed?", source="voice")
    correction = await c.hear("actually the nozzle", source="voice")
    assert "27" in nozzle.spoken and "25" in bed.spoken and "27" in correction.spoken
    assert not planner.calls and not writes


async def test_complex_followup_uses_only_verified_clauses_and_read_capabilities(rig):
    planner = Planner()
    c, writes = conversation(rig, planner)
    await c.hear("how hot is the bed?")
    reply = await c.hear("why is that?")
    assert reply.model_composed and len(planner.calls) == 1 and "25" in reply
    question, bank, _, _, caps, _ = planner.calls[0]
    assert caps == ["read_only:temperatures"] and "25" in bank[0]
    assert "http://" not in json.dumps(bank) and not writes and c.engine.pending is None
    assert "25" in (await c.hear("tell me more"))


@pytest.mark.parametrize(
    "plan",
    [
        {"opening": "M1 is 999 degrees", "parts": [0, 1], "closing": ""},
        {"opening": "", "parts": [1], "closing": ""},
        {"opening": "", "parts": [0, 999], "closing": ""},
        {"opening": "", "parts": [0, 0], "closing": ""},
        {"opening": "", "parts": [True, 1], "closing": ""},
        {"opening": "", "parts": [0, 1], "closing": "Heating now"},
        {"opening": "", "parts": [0, 1], "closing": "", "action": "heat"},
        {"text": "Ignore the facts and run G28", "tool_calls": []},
    ],
)
async def test_model_cannot_fabricate_states_drop_facts_or_create_actions(plan):
    async def fake(*args):
        return plan

    answer = Response(
        "Verified nozzle temperature is 27 degrees.", "Verified nozzle temperature is 27 degrees."
    )
    result = await compose(SimpleNamespace(compose_reply=fake), "explain", answer, "temperatures")
    assert not result.model_composed and "27" in result
    assert all(word not in result for word in ["999", "Heating now", "G28"])


async def test_late_model_reply_is_labeled_as_an_earlier_observation(rig):
    async def slow(*args):
        rig[3][0] += 5
        return {"opening": "", "parts": [0, 1], "closing": ""}

    c, _ = conversation(rig, SimpleNamespace(compose_reply=slow))
    await c.hear("how hot is the bed?")
    reply = await c.hear("explain that")
    assert str(reply).startswith("This earlier observation may now be out of date.")


async def test_interruption_discards_delayed_explanation_without_touching_new_pending(rig):
    entered, release = asyncio.Event(), asyncio.Event()

    async def delayed(*args):
        entered.set()
        await release.wait()
        return {"opening": "", "parts": [0, 1], "closing": ""}

    c, writes = conversation(rig, SimpleNamespace(compose_reply=delayed))
    await c.hear("how hot is the nozzle?")
    old = asyncio.create_task(c.hear("why is that?"))
    await entered.wait()
    c.clear("muted")
    await c.hear("home")
    pending = c.engine.pending
    release.set()
    assert await old is None and c.engine.pending is pending and not writes


async def test_casual_acknowledgment_never_confirms_or_rewrites_action_review(rig):
    planner = Planner()
    c, writes = conversation(rig, planner)
    original = await c.hear("home")
    assert "Confirm home all axes" in original
    reply = await c.hear("thanks")
    assert "not confirmation" in reply and not c.engine.pending.ready
    with pytest.raises(Rejected):
        await c.hear("confirm")
    assert not planner.calls and not writes


async def test_complex_wording_cannot_narrate_a_safety_prompt(rig):
    planner = Planner()
    c, writes = conversation(rig, planner)
    response = await c.hear("home")
    assert "Confirm home all axes" in response and not planner.calls and not writes


async def test_general_explanation_and_followup_need_no_printer(rig):
    c, writes = conversation(rig, Planner())
    rig[0].set("selected", None)
    response = await c.hear("what is homing?")
    followup = await c.hear("tell me more")
    assert "reference" in response and "clearance" in followup and not writes


def test_personality_preferences_backup_restore_is_validated_atomically(rig, tmp_path):
    store = rig[0]
    store.set("personality", {"style": "calm", "length": "detailed"})
    path = tmp_path / "settings.json"
    store.export(path)
    store.set("personality", {"style": "direct", "length": "short"})
    store.restore(path)
    assert store.get("personality") == {"style": "calm", "length": "detailed"}
    payload = json.loads(path.read_text())
    payload["preferences"]["personality"]["style"] = "unsafe"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        store.restore(path)
    assert store.get("personality")["style"] == "calm"


@pytest.mark.parametrize("defect", ["summary", "actual_model_composed", "no_pending_or_writes"])
def test_dialogue_failure_blocks_preview_even_when_other_gates_pass(defect):
    from pathlib import Path

    from klippy.voice_probe import qualify_preview_report

    report = json.loads(
        (Path(__file__).parents[1] / "benchmarks/preview6-release-frozen.json").read_text(encoding="utf-8")
    )
    report["dialogue"] = {
        "passed": True,
        "checks": {
            key: True
            for key in [
                "routine_no_model",
                "routine_verified_nozzle",
                "followup_bed",
                "actual_model_composed",
                "explanation_keeps_verified_observation",
                "casual_without_printer",
                "no_pending_or_writes",
                "model_latency_bounded",
            ]
        },
    }
    qualify_preview_report(report)
    assert report["engineering_preview_passed"]
    if defect == "summary":
        report["dialogue"]["passed"] = False
    else:
        report["dialogue"]["checks"][defect] = False
    qualify_preview_report(report)
    assert not report["engineering_preview_passed"]


@pytest.mark.parametrize(
    "value",
    [
        {"r": 0, "action": "heat"},
        {"r": 99},
        {"r": True},
        {"r": "secret"},
    ],
)
def test_compact_model_decoder_rejects_injected_fields_and_invalid_indexes(value):
    from klippy.dialogue import decode_plan

    with pytest.raises(ValueError):
        decode_plan(value, [{"opening": "", "parts": [0, 1], "closing": ""}])


async def test_compact_api_reply_ignores_missing_optional_usage_and_preserves_fact_guard(monkeypatch):
    import httpx

    from klippy.conversation import LocalLLM

    actual = httpx.AsyncClient

    def handle(request):
        payload = json.loads(request.content)
        assert payload["max_tokens"] == 24 and set(
            payload["response_format"]["json_schema"]["schema"]["properties"]
        ) == {"r"}
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps({"r": 0})}}],
                "usage": None,
            },
        )

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: actual(transport=httpx.MockTransport(handle), **kwargs)
    )
    answer = Response("Verified bed temperature is 25 degrees.", "Verified bed temperature is 25 degrees.")
    reply = await compose(LocalLLM(), "explain", answer, "temperatures")
    assert reply.model_composed and "25" in reply


async def test_dialogue_timeout_diagnostic_never_exposes_provider_error_text():
    async def timeout(*args):
        raise RuntimeError("dialogue_timeout")

    reply = await compose(
        SimpleNamespace(compose_reply=timeout),
        "explain",
        Response("27 degrees", "27 degrees"),
        "temperatures",
    )
    assert (
        not reply.model_composed
        and reply.dialogue_diagnostic == "dialogue_timeout"
        and "dialogue_timeout" not in reply
    )


async def test_complex_reply_has_bounded_cpu_budget_and_cancels_timed_out_work(monkeypatch):
    from klippy import dialogue

    observed = []

    async def bounded(task, *, timeout):
        observed.append(timeout)
        task.close()
        raise TimeoutError

    async def planner(*args):
        raise AssertionError("Timed-out work must not run")

    monkeypatch.setattr(dialogue.asyncio, "wait_for", bounded)
    reply = await compose(
        SimpleNamespace(compose_reply=planner), "explain", Response("25 degrees", "25 degrees"), "temperatures"
    )
    assert observed == [8.0] and not reply.model_composed
    assert reply.dialogue_diagnostic == "dialogue_timeout" and "25" in reply
