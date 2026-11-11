import argparse
from pathlib import Path

from klippy.models import verify_pack

parser = argparse.ArgumentParser()
parser.add_argument("pack", type=Path)
parser.add_argument("--qualified", action="store_true")
args = parser.parse_args()
value = verify_pack(args.pack.resolve(), require_qualified=args.qualified)
print(f"Verified {len(value['assets'])} assets")
