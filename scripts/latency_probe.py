"""Repeatable CPU TTS benchmark. No microphone, speaker, network or physical printer."""
import argparse
import json
import platform
import time
from pathlib import Path

from klippy.models import bundled_pack, verify_pack
from klippy.voice import SherpaBackend


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    pack = bundled_pack()
    backend = SherpaBackend(pack, verify_pack(pack)["speech_config"])
    rows = []
    for name, text in [
        ("temperature", "extruder: 23.0 degrees; heater_bed: 21.0 degrees"),
        ("confirmation", "Confirm home on Test Printer? Check the bed and toolhead path are clear. "
         "Say exactly confirm or choose Confirm within 25 seconds."),
    ]:
        for run in range(2):
            started = time.monotonic()
            chunks = []
            audio = backend.synthesize(text, on_chunk=lambda pcm, rate: chunks.append(time.monotonic() - started))
            rows.append({"case": name, "run": run + 1, "cache": run == 1,
                         "first_pcm_seconds": round(chunks[0], 3),
                         "generation_seconds": round(time.monotonic() - started, 3),
                         "audio_seconds": round(len(audio.samples) / audio.sample_rate, 3)})
    result = {"scope": "CPU TTS; first PCM available, not measured physical audibility",
              "host": platform.processor(), "rows": rows}
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run()
