import pytest

from klippy.conversation import Conversation
from klippy.domain import Printer
from klippy.macros import discover
from klippy.safety import Rejected


async def test_nonwake_ignored_and_wake_status_recognized(rig):
    _, sim, engine, clock = rig
    conversation = Conversation(engine, clock=lambda: clock[0])
    assert await conversation.hear("status", source="voice") is None
    assert "63%" in await conversation.hear("Hey Klippy, status", source="voice")
    assert not sim.writes


async def test_similar_words_do_not_wake(rig):
    _, _, engine, clock = rig
    c = Conversation(engine, clock=lambda: clock[0])
    assert await c.hear("Klipper home", source="voice") is None
    assert await c.hear("Clippy home", source="voice") is None


async def test_own_voice_never_activates(rig):
    _, sim, engine, _ = rig
    c = Conversation(engine)
    assert await c.hear("Klippy home", source="voice", own_voice=True) is None
    assert not sim.writes


async def test_stop_talking_does_not_cancel_print(rig):
    _, sim, engine, _ = rig
    assert await Conversation(engine).hear("Klippy stop talking") == "speech_stopped"
    assert not sim.writes


@pytest.mark.parametrize("text", ["no", "don't do that", "cancel that", "never mind", "don't home", "do not pause"])
async def test_negative_instruction_cancels_pending(rig, text):
    _, sim, engine, _ = rig
    c = Conversation(engine)
    await c.hear("home")
    assert engine.pending
    await c.hear(text)
    assert engine.pending is None
    assert not sim.writes


async def test_unrelated_speech_never_confirms(rig):
    _, sim, engine, _ = rig
    c = Conversation(engine)
    await c.hear("home")
    with pytest.raises(Rejected):
        await c.hear("yes that sounds good")
    assert not engine.pending
    assert not sim.writes


async def test_printer_change_invalidates_pending(rig):
    store, sim, engine, _ = rig
    store.save_printer(Printer(id="other", name="Second Printer", url="http://127.0.0.1:7126", approved=True))
    c = Conversation(engine)
    await c.hear("home")
    token = engine.pending.token
    await c.hear("select Second Printer")
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert store.get("selected") == "other"
    assert not sim.writes


async def test_multiple_printer_mentions_clarify(rig):
    store, sim, engine, _ = rig
    store.save_printer(Printer(id="other", name="Second Printer", url="http://127.0.0.1:7126", approved=True))
    with pytest.raises(Rejected):
        await Conversation(engine).hear("pause Test Printer and Second Printer")
    assert not sim.writes


async def test_ambiguous_macro_clarifies(rig):
    store, sim, engine, _ = rig
    sim.config = {"gcode_macro LOAD_FILAMENT": {"gcode": "G1 E1"},
                  "gcode_macro FILAMENT_LOAD": {"gcode": "G1 E2"}}
    registry, _ = discover(sim.config, {})
    store.replace_macros("sim", {name: m.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                                 for name, m in registry.items()})
    with pytest.raises(Rejected, match="Which macro"):
        await Conversation(engine).hear("load filament")
    assert not sim.writes


async def test_session_expiry_forgets_pending(rig):
    _, sim, engine, clock = rig
    c = Conversation(engine, clock=lambda: clock[0])
    await c.hear("Klippy home", source="voice")
    clock[0] += 31
    assert await c.hear("confirm", source="voice") is None
    # The engine independently enforces expiry, even before the UI clears context.
    with pytest.raises(Rejected):
        await engine.confirm(engine.pending.token)
    assert not sim.writes


async def test_malformed_model_output_executes_nothing(rig):
    from unittest.mock import patch

    import httpx

    from klippy.conversation import LocalLLM
    _, sim, engine, _ = rig
    model = LocalLLM()
    response = httpx.Response(200, json={"choices": [{"message": {"content": '{"gcode":"G28"}'}}]},
                              request=httpx.Request("POST", "http://127.0.0.1"))
    async def post(*args, **kwargs):
        return response
    with patch("httpx.AsyncClient.post", post), pytest.raises(Rejected):
        await Conversation(engine, llm=model).hear("do something vaguely dangerous")
    assert not sim.writes


async def test_transcripts_not_persisted(rig):
    store, _, engine, _ = rig
    await Conversation(engine).hear("Klippy status")
    dump = "\n".join(store.db.iterdump())
    assert "Klippy status" not in dump
    assert "63%" not in dump


async def test_interruption_prevents_stale_llm_result_from_proposing(rig):
    import asyncio

    from klippy.domain import Action, Intent
    _, sim, engine, _ = rig
    entered, release = asyncio.Event(), asyncio.Event()
    class Model:
        async def interpret(self, *args):
            entered.set()
            await release.wait()
            return Intent(action=Action.HOME, printer_id="sim")
    conversation = Conversation(engine, llm=Model())
    task = asyncio.create_task(conversation.hear("please perform homing"))
    await entered.wait()
    conversation.clear()
    release.set()
    assert await task is None
    assert engine.pending is None and not sim.writes


async def test_voice_confirmation_requires_capture_time_token(rig):
    _, sim, engine, _ = rig
    conversation = Conversation(engine)
    await conversation.hear("Klippy home", source="voice")
    with pytest.raises(Rejected):
        await conversation.hear("confirm", source="voice")
    assert not sim.writes


async def test_wake_interruption_preserves_exact_pending_confirmation(rig):
    _, sim, engine, _ = rig
    conversation = Conversation(engine)
    await conversation.hear("Klippy home", source="voice")
    token = engine.pending.token
    conversation.interrupt()
    assert engine.pending.token == token
    await conversation.hear("Klippy confirm", source="voice", confirmation_token=token)
    assert len(sim.writes) == 1  # Simulated transport only.
