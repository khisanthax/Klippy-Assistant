"""Actual ASR/Kokoro synthetic wake comparison; PCM stays in memory; no devices/printers."""
import time

import numpy as np

from klippy.audio import RATE
from klippy.models import verify_pack
from klippy.resampling import SpeechResampler
from klippy.voice import WAKE_PREFIX, SherpaBackend, VoiceLoop


def run(root):
    manifest = verify_pack(root, require_qualified=True)
    backend = SherpaBackend(root, manifest["speech_config"])
    rows = []
    recovered_audio = []
    standard_audio = None
    for positive, phrase in [(True, "Hey Clippy"), (True, "Clippy"),
                             (False, "Hey puppy"), (False, "Hey creepy"),
                             (False, "Hey copy"), (False, "Klipper"), (False, "Hey Clipper"),
                             (False, "Hey Cuppy"), (False, "Hey Crippy")]:
        for voice_id in ([0, 1, 3] if positive else [0]):
            backend.voice_id = voice_id
            audio = backend.synthesize(phrase)
            pcm = SpeechResampler(audio.sample_rate).push(audio.samples, final=True)
            for speed in ([.85, 1, 1.15] if positive else [1]):
                wave = np.interp(np.arange(0, len(pcm), speed), np.arange(len(pcm)), pcm).astype(np.float32)
                if phrase == "Hey Clippy" and voice_id == 0 and speed == 1:
                    standard_audio = wave.copy()
                baseline = backend.transcribe(wave).strip()
                recheck = None
                started = time.perf_counter()
                if WAKE_PREFIX.fullmatch(baseline) is None:
                    recheck = backend.verify_short_wake(wave, lambda: False)
                if positive and recheck:
                    recovered_audio.append(wave.copy())
                rows.append({"synthetic_phrase": phrase, "positive": positive, "voice": voice_id,
                             "speed": speed, "baseline": baseline, "recheck": recheck,
                             "baseline_wake_only": WAKE_PREFIX.fullmatch(baseline) is not None,
                             "recovered_wake_only": bool(recheck),
                             "recheck_ms": round((time.perf_counter()-started)*1000, 2),
                             "seconds": round(len(wave)/RATE, 3)})
    negatives = [r for r in rows if not r["positive"]]
    recovered = [r for r in rows if r["positive"] and not r["baseline_wake_only"] and r["recovered_wake_only"]]
    delivered = []
    pipeline = []
    for wave in [standard_audio, *recovered_audio]:
        inputs, states = [], []
        voice = VoiceLoop(backend, inputs.append, states.append)
        voice.enabled.set()
        try:
            voice._transcribe(wave, voice.epoch, True, False, "synthetic_token_must_not_forward")
            voice.asr_pool.submit(lambda: None).result(timeout=20)
            pipeline.append({"inputs": [{"text": x.text, "raw": x.raw_transcript, "token_cleared": x.confirmation_token is None} for x in inputs], "states": [str(s) for s in states], "counters": voice.wake_diagnostics()})
            delivered.append(len(inputs) == 1 and inputs[0].text.strip() == "Klippy"
                             and inputs[0].confirmation_token is None)
        finally:
            voice.close()
    # Deterministic initial-ASR fault injection, followed by real stricter KWS and TWO
    # real ASR passes on the same generated speech. This does not claim natural recovery
    # on every run; legitimately uncertain generated variants must remain rejected.
    original_transcribe = backend.transcribe
    first = True
    native_decodes = 0
    def initial_fault(samples):
        nonlocal first, native_decodes
        if first:
            first = False
            return "unrecognized wake"
        native_decodes += 1
        return original_transcribe(samples)
    backend.transcribe = initial_fault
    inputs, states = [], []
    voice = VoiceLoop(backend, inputs.append, states.append)
    voice.enabled.set()
    try:
        voice._transcribe(standard_audio, voice.epoch, True, False, "must_not_forward")
        voice.asr_pool.submit(lambda: None).result(timeout=20)
    finally:
        voice.close()
        backend.transcribe = original_transcribe
    injected = {"injected_initial_rejection": True, "native_verification_passes": native_decodes,
                "delivered_wake_only": len(inputs) == 1 and inputs[0].text.strip() == "Klippy"
                and inputs[0].confirmation_token is None,
                "states": [str(state) for state in states]}
    checks = {"native_strict_recovery_after_injected_asr_fault": injected["delivered_wake_only"] and native_decodes == 2,
              "actual_pipeline_wake_only": any(delivered),
              "no_unsafe_pipeline_delivery": all(len(row["inputs"]) <= 1 and all(
                  item["text"].strip() == "Klippy" and item["token_cleared"] for item in row["inputs"]) for row in pipeline),"no_new_negative_acceptances": not any(r["recovered_wake_only"] for r in negatives),
              "recheck_bounded": max(r["recheck_ms"] for r in rows) < 4000}
    return {"passed": all(checks.values()), "checks": checks, "recovered_positive_cases": len(recovered), "pipeline": pipeline, "injected_asr_fault": injected,
            "scope": "Synthetic speech only; forced candidate comparison, no physical microphone or printer; no audio saved",
            "cases": rows}
