"""Actual bundled local model + simulated multi-turn facts. No audio or printers."""

import argparse
import asyncio
import json
from pathlib import Path

from klippy.dialogue_probe import run
from klippy.models import verify_pack
from klippy.runtime import LlamaRuntime


async def probe(pack):
    verify_pack(pack, require_qualified=True)
    runtime = LlamaRuntime()
    try:
        return await run(await runtime.start(pack))
    finally:
        runtime.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = asyncio.run(probe(args.pack))
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
