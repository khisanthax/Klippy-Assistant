"""Real-model voice integration, simulated acoustics and simulated printer. No devices open."""
import argparse
import asyncio
import json
import time
from pathlib import Path

import httpx
import numpy as np

from klippy.audio import FRAME, RATE, resample
from klippy.conversation import Conversation
from klippy.domain import Printer
from klippy.models import verify_pack
from klippy.moonraker import Moonraker
from klippy.runtime import LlamaRuntime
from klippy.safety import SafetyEngine
from klippy.storage import Store
from klippy.voice import SherpaBackend, VoiceLoop


def qualify_report(report):
    """Gate the composite application; retain raw embedded-keyword recall separately.

    Interruption has two corroborating paths. A KWS-only miss is not an application
    interruption failure when the actual ASR-verified barge-in succeeds.
    """
    cases = {(case["phrase"], case["synthetic_voice"]): case["detected"] for case in report["wake_cases"]}
    embedded = [case for case in report["wake_cases"] if "klippy" in case["phrase"].lower()
                and case["phrase"] not in {"Klippy", "Hey Klippy"}]
    report["raw_embedded_keyword"] = {"detected": sum(bool(case["detected"]) for case in embedded),
                                      "total": len(embedded),
                                      "misses": [case for case in embedded if not case["detected"]]}
    report["gates"] = {
        "standalone_wake": all(cases.get((phrase, sid)) is True
                               for phrase in ("Klippy", "Hey Klippy") for sid in (0, 3)),
        "negative_words": all(cases.get((phrase, sid)) is False
                              for phrase in ("clipper", "Klipper", "The printer is ready") for sid in (0, 3)),
        "captured_status": bool(report["pipeline_transcripts"]) and "63%" in (report["simulated_status_response"] or ""),
        "own_echo": report["own_echo_requests"] == 0 and report["own_echo_wakes"] == 0,
        "verified_interruption": (report["barge_wakes"] > 0 and report["playback_flushed"]
                                  and any("stop talking" in text.lower() for text in report["barge_requests"])),
        "local_language": report["llm_intent"]["action"] == "temperatures",
        "no_printer_writes": report["printer_writes"] == 0,
    }
    report["passed"] = all(report["gates"].values())


def run(pack):
    from .offline_probe import deny_external_network
    deny_external_network()
    manifest = verify_pack(pack, require_qualified=True)
    started = time.perf_counter()
    backend = SherpaBackend(pack, manifest["speech_config"])
    report = {"scope": "CPU-only real models; synthetic audio/acoustics and simulated printer; no devices or real printer APIs",
              "speech_load_seconds": round(time.perf_counter() - started, 3),
              "python_external_network_denied": True, "wake_threshold": backend.wake_threshold,
              "keywords_score": 2.0, "wake_cases": []}
    def audio(text, voice=3, speed=1.0):
        # Probe alternate public synthetic voices without opening playback devices.
        from klippy.speech_text import normalize_for_speech
        value = backend.tts.generate(normalize_for_speech(text, backend.vocabulary), sid=voice, speed=speed)
        return resample(value.samples, value.sample_rate)
    def pad(samples):
        return np.r_[np.zeros(RATE // 2, dtype=np.float32), samples, np.zeros(RATE * 2, dtype=np.float32)]
    for phrase in ["Klippy", "Hey Klippy", "Klippy stop talking", "Hey Klippy stop talking", "clipper", "Klipper", "The printer is ready", "clippy"]:
        for voice in [0, 3]:
            backend.reset_wake()
            samples = pad(audio(phrase, voice))
            woke = False
            for i in range(0, len(samples), FRAME):
                woke |= backend.wake(samples[i:i + FRAME])
            report["wake_cases"].append({"phrase": phrase, "synthetic_voice": voice, "detected": bool(woke)})
    received, wakes, states = [], [], []
    clock = [0.0]
    asr_observations = []
    asr_errors = []
    transcribe = backend.transcribe
    def traced_transcribe(samples):
        try:
            text = transcribe(samples)
        except Exception as exc:
            asr_errors.append(type(exc).__name__)
            raise
        asr_observations.append({"at": round(clock[0], 3), "text": text, "audio_seconds": round(len(samples) / RATE, 3)})
        return text
    backend.transcribe = traced_transcribe
    voice = VoiceLoop(backend, received.append, states.append, lambda epoch: wakes.append((clock[0], epoch, voice.playback.remaining)),
                      clock=lambda: clock[0])
    voice.enabled.set()
    def feed(near, far=None, active=False):
        if far is None:
            far = np.zeros_like(near)
        remainder = (-len(near)) % FRAME
        near, far = np.pad(near, (0, remainder)), np.pad(far, (0, remainder))
        for i in range(0, len(near), FRAME):
            clock[0] += FRAME / RATE
            voice.process_frame(near[i:i + FRAME], far[i:i + FRAME], clock[0], output_active=active)
        voice.asr_pool.submit(lambda: None).result(timeout=30)
    try:
        backend.reset_wake()
        feed(pad(audio("Klippy, what is the status of the test printer?", voice=0)))
        report["pipeline_transcripts"] = [v.text for v in received]
        report["pipeline_wakes"] = list(wakes)
        report["pipeline_states"] = list(states)
        report["asr_errors"] = asr_errors
        # Exactly matching speaker echo must not become a command, including warm-up.
        voice._reset_dsp()
        received.clear()
        wakes.clear()
        spoken = audio("Klippy confirm. Klippy home the test printer.")
        far = pad(spoken)
        near = .6 * np.roll(far, 800) + .1 * np.roll(far, 1120)
        near[:1120] = 0
        voice.spoken.append((clock[0], "Klippy confirm. Klippy home the test printer."))
        feed(near, far, active=True)
        report["own_echo_wakes"] = len(wakes)
        report["own_echo_requests"] = len(received)
        # Warm AEC with actual speech, then interrupt it with another synthetic speaker.
        voice._reset_dsp()
        received.clear()
        wakes.clear()
        own = audio("The test printer is currently printing. The job is sixty three percent complete. Please ask if you need more details.")
        user = audio("Klippy stop talking", voice=0)
        start = RATE * 3
        length = max(len(own), start + len(user)) + RATE * 2
        reference = np.pad(own, (0, max(0, length - len(own))))
        voice.playback.enqueue(reference, voice.epoch)
        history = np.zeros(length, dtype=np.float32)
        begin = clock[0]
        candidates = []
        frame_metrics = []
        wake_method = backend.wake
        def traced_wake(samples):
            hit = wake_method(samples)
            if hit:
                candidates.append({"time": round(clock[0] - begin, 3),
                                   "near_end_until": round(voice.near_end_until - begin, 3),
                                   "echo_correlation": round(voice.echo.correlation, 3)})
            return hit
        backend.wake = traced_wake
        wall_start = time.perf_counter()
        for i in range(0, length - FRAME, FRAME):
            # Let background ONNX ASR run against real-time audio arrival rather
            # than outrunning the asynchronous worker with an instantaneous file.
            time.sleep(max(0, wall_start + i / RATE - time.perf_counter()))
            far_frame = voice.playback.render(FRAME)
            history[i:i + FRAME] = far_frame
            near_frame = np.zeros(FRAME, dtype=np.float32)
            for delay, gain in [(800, .6), (1120, .1)]:
                at = i - delay
                if at >= 0:
                    near_frame += gain * history[at:at + FRAME]
            left, right = max(i, start), min(i + FRAME, start + len(user))
            if right > left:
                near_frame[left - i:right - i] += .8 * user[left - start:right - start]
            clock[0] += FRAME / RATE
            voice.process_frame(near_frame, far_frame, clock[0], output_active=bool(voice.playback.remaining))
            if i % 1600 == 0 and start <= i < start + len(user):
                frame_metrics.append({"at": round(i / RATE, 3), "energy": round(voice.last_energy, 4),
                    "near_end": voice.near_end_until > clock[0], "probe_busy": voice.probe_pending.is_set(),
                    "correlation": round(voice.echo.correlation, 3)})
        voice.asr_pool.submit(lambda: None).result(timeout=30)
        report["barge_wakes"] = len(wakes)
        report["barge_candidates"] = candidates
        report["barge_linear_fit_error"] = voice.echo.linear_fit_error
        report["barge_states"] = states[-8:]
        report["asr_observations"] = asr_observations
        report["barge_frame_metrics"] = frame_metrics
        report["barge_requests"] = [v.text for v in received]
        report["barge_detection_seconds_from_user_start"] = round(wakes[0][0] - begin - 3, 3) if wakes else None
        report["playback_flushed"] = bool(wakes) and all(w[2] == 0 for w in wakes)
    finally:
        voice.close()
    async def language_probe():
        runtime = LlamaRuntime()
        try:
            model = await runtime.start(pack)
            value = await model.interpret("What is the nozzle temperature?", "synthetic-printer", {})
            report["llm_intent"] = value.model_dump(mode="json")
        finally:
            runtime.close()
    asyncio.run(language_probe())
    # All inference integration above has no command transport. Verify read-only conversation
    # separately against an injected simulator whose every write raises immediately.
    import tempfile
    with tempfile.TemporaryDirectory() as temp:
        store = Store(Path(temp) / "test.sqlite")
        printer = Printer(id="sim", name="test printer", url="http://127.0.0.1:1", approved=True)
        store.save_printer(printer)
        store.set("selected", "sim")
        writes = []
        def transport(request):
            if request.method != "GET":
                writes.append(request.url.path)
                raise AssertionError("No simulated or real actuation permitted in voice probes")
            return httpx.Response(200, json={"result": {"status": {"webhooks": {"state": "ready"},
                "print_stats": {"state": "printing"}, "virtual_sdcard": {"progress": .63},
                "extruder": {"temperature": 23.0}}}})
        engine = SafetyEngine(store, lambda p: Moonraker(p, transport=httpx.MockTransport(transport)))
        conversation = Conversation(engine)
        report["simulated_status_response"] = (asyncio.run(conversation.hear(report["pipeline_transcripts"][0], source="voice"))
                                               if report["pipeline_transcripts"] else None)
        report["printer_writes"] = len(writes)
        store.close()
    qualify_report(report)
    report["homophone_note"] = "Clippy is acoustically equivalent to Klippy; it cannot be reliably excluded by spelling."
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    parser.add_argument("--output", type=Path, default=Path("local/phase2-probe.json"))
    args = parser.parse_args()
    result = run(args.pack.resolve())
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
