import hashlib
import json
from pathlib import Path


class ModelUnavailable(Exception):
    pass


def verify_pack(root: Path, *, require_complete=True):
    try:
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        roles = set()
        verified = set()
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
            verified.add(path)
        if require_complete and not {"wake", "asr", "tts", "llm", "llama_binary"} <= roles:
            raise ModelUnavailable("Voice pack is incomplete; manual controls and monitoring remain available")
        if require_complete:
            refs = []
            for group in ("wake", "asr", "tts"):
                values = manifest["speech_config"][group]
                refs.extend(values.values())
            refs.extend([manifest["runtime"]["binary"], manifest["runtime"]["model"]])
            for ref in refs:
                if not isinstance(ref, str):
                    raise ModelUnavailable("Model configuration paths must be strings")
                path = (root / ref).resolve()
                if not path.is_relative_to(root.resolve()):
                    raise ModelUnavailable("Model configuration escapes the pack")
                files = [p.resolve() for p in path.rglob("*") if p.is_file()] if path.is_dir() else [path]
                if not files or any(p not in verified for p in files):
                    raise ModelUnavailable("Model configuration references unverified assets")
        return manifest
    except (OSError, ValueError, KeyError):
        raise ModelUnavailable("Local model manifest missing or invalid") from None
