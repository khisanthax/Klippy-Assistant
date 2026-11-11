"""Real TTS with a simulated PCM sink and printer; no devices or live actions."""
import argparse
import asyncio
import json
import tempfile
import threading
import time
from pathlib import Path

from klippy.audio import FRAME, RATE
from klippy.conversation import Conversation
from klippy.diagnostics import current, timings
from klippy.domain import Printer, Snapshot
from klippy.models import bundled_pack, verify_pack
from klippy.safety import SafetyEngine
from klippy.storage import Store
from klippy.voice import SherpaBackend, VoiceLoop


async def probe(backend, output):
    class Client:
        async def snapshot(self):
            return Snapshot(connected=True, ready=True, state="standby")

        async def execute(self, *args):
            raise AssertionError("Delivery qualification must never execute a printer action")

    with tempfile.TemporaryDirectory(prefix="klippy-delivery-") as directory:
        store = Store(Path(directory) / "probe.sqlite")
        printer = Printer(id="simulation", name="Test Printer", url="http://127.0.0.1:7125", approved=True)
        store.save_printer(printer)
        store.set("selected", printer.id)
        engine = SafetyEngine(store, lambda p: Client())
        engine.confirmation_seconds = 30
        conversation = Conversation(engine)
        done = threading.Event()
        deliveries = []
        def delivery(token, success):
            engine.delivery_finished(token, success)
            deliveries.append((success, time.monotonic()))
            done.set()
        voice = VoiceLoop(backend, lambda v: None, lambda v: None,
                          session=conversation.session, on_delivery=delivery)
        worker = threading.Thread(target=voice._speak)
        worker.start()
        rows = []
        try:
            for run in range(2):
                done.clear()
                trace = timings.new()
                context = current.set(trace)
                try:
                    with timings.span("intent_and_validation"):
                        prompt = await conversation.hear("Klippy home" if run == 0 else "home", source="voice",
                                                         defer_confirmation=True)
                finally:
                    current.reset(context)
                token = engine.pending.token
                started, first, early_arm = time.monotonic(), None, False
                voice.say(prompt, token=token, trace=trace)
                while not done.is_set():
                    pcm = voice._render(FRAME)
                    if first is None and any(pcm):
                        first = time.monotonic() - started
                    if engine.pending.ready and (voice.playback.remaining or voice.speaking.is_set()):
                        early_arm = True
                    if time.monotonic() - started > 60:
                        raise TimeoutError("Simulated render did not complete")
                    await asyncio.sleep(FRAME / RATE)
                remaining = engine.pending.expires - deliveries[-1][1]
                assert deliveries[-1][0] and engine.pending.ready and not early_arm
                assert 29.9 <= remaining <= 30.1
                assert not voice.playback.remaining and not voice.speaking.is_set()
                rows.append({"run": run + 1, "cached": run == 1,
                             "first_render_seconds": round(first, 3),
                             "delivery_seconds": round(deliveries[-1][1] - started, 3),
                             "confirmation_window_seconds": round(remaining, 3),
                             "confirmation_armed_early": early_arm})
            report = {"passed": True, "scope": __doc__, "printer_writes": 0,
                      "rows": rows, "timings": timings.snapshot()}
            output.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(json.dumps(report, indent=2))
        finally:
            voice.close()
            worker.join(5)
            store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("local/delivery-probe.json"))
    args = parser.parse_args()
    pack = bundled_pack()
    backend = SherpaBackend(pack, verify_pack(pack)["speech_config"])
    asyncio.run(probe(backend, args.output))
