"""Run device-free bundled-model wake recheck qualification."""
import argparse
import json
from pathlib import Path

from klippy.wake_probe import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pack)
    args.report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "cases"}, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
