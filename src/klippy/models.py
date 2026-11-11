import hashlib
import json
import sys
from pathlib import Path


class ModelUnavailable(Exception):
    pass


def bundled_pack():
    root = Path(sys._MEIPASS) / "models" if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2] / "local" / "bundle-models-voice"
    return root if (root / "manifest.json").is_file() else None


def verify_pack(root: Path, *, require_complete=True, require_qualified=False):
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
            if path in verified:
                raise ModelUnavailable("Duplicate asset entry")
            verified.add(path)
        if require_qualified:
            qualification = manifest.get("qualification", {})
            if qualification.get("status") != "redistribution-reviewed" or not qualification.get("components"):
                raise ModelUnavailable("Local model pack has not passed redistribution review")
            allowed = {"Apache-2.0", "MIT", "BSD-2-Clause", "BSD-3-Clause", "MIT AND Apache-2.0",
                       "Apache-2.0 WITH LLVM-exception", "LicenseRef-Public-Domain"}
            if any(a["license"] not in allowed for a in manifest["assets"]):
                raise ModelUnavailable("Unreviewed model or binary license")
            for component in qualification["components"]:
                if not component.get("evidence") or not component.get("notices"):
                    raise ModelUnavailable("Model license evidence is incomplete")
                for relative in component["notices"]:
                    if (root / relative).resolve() not in verified:
                        raise ModelUnavailable("License notice is not integrity-verified")
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
            binary_dir = (root / manifest["runtime"]["binary"]).resolve().parent
            if any(p.resolve() not in verified for p in binary_dir.iterdir()
                   if p.is_file() and p.suffix.lower() in {".exe", ".dll"}):
                raise ModelUnavailable("Runtime directory contains an unverified binary")
        return manifest
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise ModelUnavailable("Local model manifest missing or invalid") from None
