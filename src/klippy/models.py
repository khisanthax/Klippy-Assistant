import hashlib
import json
from pathlib import Path


class ModelUnavailable(Exception):
    pass


def verify_pack(root: Path, *, require_complete=True):
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        roles = set()
        for asset in manifest["assets"]:
            relative = Path(asset["path"])
            path = (root / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(root.resolve()):
                raise ModelUnavailable("Invalid model asset path")
            if not asset.get("license") or not asset.get("source") or not asset.get("version"):
                raise ModelUnavailable("Asset provenance is incomplete")
            if not path.is_file():
                raise ModelUnavailable("Required local model asset is missing")
            with path.open("rb") as stream:
                checksum = hashlib.file_digest(stream, "sha256").hexdigest()
            if checksum != asset["sha256"]:
                raise ModelUnavailable("Local model integrity check failed")
            roles.add(asset["role"])
        if require_complete and not {"wake", "asr", "tts", "llm", "llama_binary"} <= roles:
            raise ModelUnavailable("Voice pack is incomplete; manual controls and monitoring remain available")
        return manifest
    except (OSError, ValueError, KeyError):
        raise ModelUnavailable("Local model manifest missing or invalid") from None
