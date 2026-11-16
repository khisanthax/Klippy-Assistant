"""Compare synthetic compute paths with a trusted local Git revision. No devices opened."""
import argparse
import importlib.util
import json
import statistics
import subprocess
import time
from pathlib import Path

import numpy as np

from klippy.audio import FRAME, EchoFilter
from klippy.macros import discover


def baseline_module(name, revision, path):
    source = subprocess.check_output(["git", "show", f"{revision}:{path}"], text=True)
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader(name, loader=None))
    exec(compile(source, path, "exec"), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", default="f604ef7", help="Trusted local Git revision")
    parser.add_argument("--output", type=Path, default=Path("local/query-capture-compute.json"))
    args = parser.parse_args()
    audio = baseline_module("baseline_audio", args.baseline, "src/klippy/audio.py")
    macros = baseline_module("klippy.baseline_macros", args.baseline, "src/klippy/macros.py")
    signal, silence = np.full(FRAME, .03, np.float32), np.zeros(FRAME, np.float32)
    result = {"scope": "Synthetic arrays/generated macros; no microphones or physical printers",
              "baseline": args.baseline, "frames": 2000}
    for label, cls in [("before", audio.EchoFilter), ("after", EchoFilter)]:
        echo, times, equal = cls(), [], True
        for _ in range(2000):
            start = time.perf_counter()
            output = echo.process(signal, silence)
            times.append((time.perf_counter() - start) * 1000)
            equal &= np.array_equal(signal, output)
        result[label] = {"cold_aec_median_ms": statistics.median(times[150:]),
                         "cold_aec_p99_ms": sorted(times[150:])[int(.99 * 1850)], "pcm_exact": bool(equal)}
    config = {f"gcode_macro SYNTHETIC_{i}": {
        "gcode": "\n".join(f"G1 X{j+i} Y{j%7} F3000" for j in range(100))} for i in range(10)}
    for label, function, kwargs in [("before", macros.discover, {}),
                                     ("after", discover, {"analyze_conflicts": False})]:
        times = []
        for _ in range(3):
            start = time.perf_counter()
            registry, _ = function(config, {}, **kwargs)
            times.append((time.perf_counter() - start) * 1000)
        result[label].update(background_discovery_median_ms=statistics.median(times), macro_count=len(registry))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
