import hashlib
import json
from unittest.mock import patch

import pytest

from klippy.models import ModelUnavailable, verify_pack
from klippy.runtime import LlamaRuntime


def pack(tmp_path):
    assets = []
    names = {"wake": "wake.bin", "asr": "asr.bin", "tts": "tts.bin", "llm": "llm.bin",
             "llama_binary": "llama.exe"}
    for role, name in names.items():
        (tmp_path / name).write_bytes(b"test fixture")
        assets.append({"path": name, "role": role, "source": "https://example.invalid/immutable/test",
                       "version": "test", "license": "test-only", "sha256": hashlib.sha256(b"test fixture").hexdigest()})
    manifest = {"assets": assets, "speech_config": {"wake": {"tokens": "wake.bin"},
                "asr": {"tokens": "asr.bin"}, "tts": {"model": "tts.bin"}},
                "runtime": {"binary": "llama.exe", "model": "llm.bin"}}
    return manifest


def test_config_cannot_reference_unverified_files(tmp_path):
    manifest = pack(tmp_path)
    (tmp_path / "not-verified.bin").write_bytes(b"unknown")
    manifest["speech_config"]["wake"]["tokens"] = "not-verified.bin"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ModelUnavailable, match="unverified"):
        verify_pack(tmp_path)


def test_config_cannot_escape_model_pack(tmp_path):
    manifest = pack(tmp_path)
    manifest["runtime"]["binary"] = "../llama.exe"
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ModelUnavailable, match="escapes"):
        verify_pack(tmp_path)


async def test_unqualified_runtime_never_launches_process(tmp_path):
    (tmp_path / "manifest.json").write_text('{"assets": []}')
    runtime = LlamaRuntime()
    with patch("subprocess.Popen") as popen, pytest.raises(ModelUnavailable):
        await runtime.start(tmp_path)
    popen.assert_not_called()


def test_complete_fixture_passes_integrity_not_model_qualification(tmp_path):
    manifest = pack(tmp_path)
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    assert verify_pack(tmp_path) == manifest
