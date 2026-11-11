"""Synthetic CPU-only model probes; never connects to a printer or opens audio devices."""
import argparse
import asyncio
import json
import platform
import time
from pathlib import Path

import numpy as np

from klippy.models import verify_pack
from klippy.runtime import LlamaRuntime
from klippy.safety import Rejected
from klippy.voice import SherpaBackend


async def run(root):
    manifest = verify_pack(root)
    report = {"date": "2026-11-11", "platform": platform.platform(),
              "note": "Synthetic fixtures, CPU-only; no microphones/printers, not real-world accuracy",
              "wake_probes": [], "llm_probes": []}
    started = time.perf_counter()
    backend = SherpaBackend(root, manifest["speech_config"])
    report["speech_load_seconds"] = round(time.perf_counter() - started, 3)
    for text in ["Klippy", "Hey Klippy", "The printer is ready", "clipper", "clippy"]:
        audio = backend.synthesize(text)
        # Linear resampling suffices for a synthetic probe; not an accuracy benchmark.
        size = int(len(audio.samples) * 16000 / audio.sample_rate)
        samples = np.interp(np.linspace(0, len(audio.samples) - 1, size),
                            np.arange(len(audio.samples)), audio.samples).astype(np.float32)
        samples = np.concatenate((samples, np.zeros(16000, dtype=np.float32)))
        backend.stream = backend.kws.create_stream()
        activated = False
        for i in range(0, len(samples), 1600):
            activated |= backend.wake(samples[i:i + 1600])
        report["wake_probes"].append({"synthetic_text": text, "activated": bool(activated)})
    started = time.perf_counter()
    audio = backend.synthesize("Pause the test printer.")
    report["tts_generate_seconds"] = round(time.perf_counter() - started, 3)
    report["tts_audio_seconds"] = round(len(audio.samples) / audio.sample_rate, 3)
    samples = np.interp(np.linspace(0, len(audio.samples) - 1, int(len(audio.samples) * 16000 / audio.sample_rate)),
                        np.arange(len(audio.samples)), audio.samples).astype(np.float32)
    started = time.perf_counter()
    report["asr_synthetic_text"] = backend.transcribe(samples)
    report["asr_seconds"] = round(time.perf_counter() - started, 3)
    runtime = LlamaRuntime()
    try:
        started = time.perf_counter()
        model = await runtime.start(root)
        report["llm_start_seconds"] = round(time.perf_counter() - started, 3)
        for text in ["What is the nozzle temperature?", "Would you pause it please?", "Do the thing"]:
            started = time.perf_counter()
            try:
                intent = await model.interpret(text, "synthetic-printer", {})
                value = intent.model_dump(mode="json")
            except Rejected as exc:
                value = {"clarification_or_failure": str(exc)}
            report["llm_probes"].append({"synthetic_text": text, "result": value,
                                          "elapsed_seconds": round(time.perf_counter() - started, 3)})
    finally:
        runtime.close()
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    parser.add_argument("--output", type=Path, default=Path("local/model-benchmark.json"))
    args = parser.parse_args()
    report = asyncio.run(run(args.pack.resolve()))
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
