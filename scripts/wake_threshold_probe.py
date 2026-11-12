"""Paired threshold comparison on fresh synthetic speech; no audio is retained."""
import argparse
import json
from pathlib import Path

import numpy as np
import sherpa_onnx as so

from klippy.audio import FRAME, RATE, resample
from klippy.models import bundled_pack, verify_pack
from klippy.speech_text import normalize_for_speech
from klippy.voice import SherpaBackend


def run(repeats, output, thresholds, context):
    root = bundled_pack()
    config = verify_pack(root)["speech_config"]
    backend = SherpaBackend(root, config)
    spotters = {threshold: so.KeywordSpotter(
        **{key: str(root / value) for key, value in config["wake"].items()},
        keywords_threshold=threshold, keywords_score=2.0, num_threads=1) for threshold in thresholds}
    rows = []
    phrases = ["Klippy", "Hey Klippy", "clipper", "Klipper", "The printer is ready"]
    if context:
        phrases += ["Klippy, what is the status of the test printer?", "Hey Klippy, what is the nozzle temperature?"]
    for repeat in range(repeats):
        for phrase in phrases:
            for sid in [0, 3]:
                audio = backend.tts.generate(normalize_for_speech(phrase, backend.vocabulary), sid=sid)
                pcm = np.r_[np.zeros(RATE // 2, dtype=np.float32), resample(audio.samples, audio.sample_rate),
                            np.zeros(RATE * 2, dtype=np.float32)]
                detections = {}
                for threshold, kws in spotters.items():
                    stream, hit = kws.create_stream(), False
                    for at in range(0, len(pcm), FRAME):
                        stream.accept_waveform(RATE, pcm[at:at + FRAME])
                        while kws.is_ready(stream):
                            kws.decode_stream(stream)
                        if kws.get_result(stream):
                            hit = True
                            kws.reset_stream(stream)
                    detections[str(threshold)] = hit
                row = {"repeat": repeat, "phrase": phrase, "voice": sid, "detected": detections}
                rows.append(row)
                print(json.dumps(row), flush=True)
    output.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("local/wake-thresholds.json"))
    parser.add_argument("--thresholds", type=float, nargs="+", default=[.15, .25, .35, .5])
    parser.add_argument("--context", action="store_true", help="Include wake-plus-request utterances")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 20:
        parser.error("Use between 1 and 20 repeats")
    if any(not .01 <= threshold <= 1 for threshold in args.thresholds):
        parser.error("Thresholds must be between .01 and 1")
    run(args.repeats, args.output, args.thresholds, args.context)
