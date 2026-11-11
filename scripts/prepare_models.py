"""Build-time-only, checksum-pinned asset assembly. The installed app never downloads models."""
import argparse
import hashlib
import json
import shutil
import tarfile
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import sentencepiece
from model_recipe import build_lexicon

from klippy.models import verify_pack

REPO = Path(__file__).resolve().parent.parent
SOURCES = json.loads((REPO / "scripts/model_sources.json").read_text(encoding="utf-8"))


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(source, cache):
    path = cache / source["filename"]
    if path.is_file() and checksum(path) == source["sha256"]:
        return path
    temporary = path.with_suffix(path.suffix + ".partial")
    with httpx.Client(timeout=120, follow_redirects=True, trust_env=False) as client:
        with client.stream("GET", source["url"]) as response:
            response.raise_for_status()
            with temporary.open("wb") as stream:
                for chunk in response.iter_bytes(1024 * 1024):
                    stream.write(chunk)
    if checksum(temporary) != source["sha256"]:
        raise ValueError("Downloaded model does not match the reviewed source checksum")
    temporary.replace(path)
    return path


def unpack(path, destination):
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                if not (destination / item.filename).resolve().is_relative_to(destination.resolve()):
                    raise ValueError("Unsafe model archive path")
            archive.extractall(destination)
    else:
        with tarfile.open(path) as archive:
            archive.extractall(destination, filter="data")


def assemble(destination, cache, *, write_manifest=False):
    cache.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        # Preserve installed/developer packs; never recursively delete a supplied directory.
        manifest = verify_pack(destination, require_qualified=True)
        expected = json.loads((REPO / "models/manifest.json").read_text(encoding="utf-8"))
        if manifest == expected:
            print("Existing model pack matches the reviewed manifest")
            return manifest
        raise ValueError("Destination already contains a different pack; select a new empty directory")
    with ThreadPoolExecutor(max_workers=4) as pool:
        downloaded = dict(zip(SOURCES, pool.map(lambda s: fetch(s, cache), SOURCES.values())))
    assets = []
    def record(path, role, source, version, license):
        assets.append({"path": path.relative_to(destination).as_posix(), "role": role,
                       "source": source, "version": version, "license": license, "sha256": checksum(path)})
    with tempfile.TemporaryDirectory(prefix="klippy-model-build-") as temp:
        extracted = Path(temp)
        for role in ("wake", "asr", "tts", "llama_binary"):
            directory = extracted / role
            directory.mkdir()
            unpack(downloaded[role], directory)
            source_root = directory / SOURCES[role].get("directory", "")
            target_root = destination / ("llama" if role == "llama_binary" else role)
            target_root.mkdir()
            if role == "wake":
                selected = ["tokens.txt", "bpe.model", "README.md", *[
                    f"{name}-epoch-12-avg-2-chunk-16-left-64.int8.onnx" for name in ("encoder", "decoder", "joiner")]]
            elif role == "asr":
                selected = ["tiny.en-encoder.int8.onnx", "tiny.en-decoder.int8.onnx", "tiny.en-tokens.txt"]
            elif role == "tts":
                selected = ["model.int8.onnx", "voices.bin", "tokens.txt", "LICENSE", "README.md"]
            else:
                selected = [p.name for p in source_root.iterdir() if p.suffix.lower() == ".dll"]
                selected += ["llama-server.exe", "LICENSE-LLVM-OpenMP"]
            for name in selected:
                target = target_root / name
                shutil.copy2(source_root / name, target)
                license = "MIT" if role == "llama_binary" else "Apache-2.0"
                if name in {"libomp.dll", "LICENSE-LLVM-OpenMP"}:
                    license = "Apache-2.0 WITH LLVM-exception"
                if role == "asr":
                    license = "MIT"
                record(target, role, SOURCES[role]["url"] + "#" + name,
                       SOURCES[role]["sha256"], license)
        llm = destination / SOURCES["llm"]["filename"]
        shutil.copy2(downloaded["llm"], llm)
        record(llm, "llm", SOURCES["llm"]["url"], "daeb8e2d528a760970442092f6bf1e55c3b659eb", "Apache-2.0")

    # No CMU-in-IPA, eSpeak dictionaries, multilingual FSTs or unreviewed lexicons are bundled.
    lexicon = destination / "tts/klippy-cmudict.txt"
    build_lexicon(lexicon, destination / "tts/tokens.txt")
    record(lexicon, "tts", "https://pypi.org/project/cmudict/1.1.3/", "cmudict-1.1.3; klippy-arpabet-recipe-1", "BSD-2-Clause")
    bpe = sentencepiece.SentencePieceProcessor(model_file=str(destination / "wake/bpe.model"))
    keywords = destination / "wake/klippy-keywords.txt"
    keywords.write_text("\n".join(" ".join(bpe.encode(text, out_type=str)) + " @KLIPPY"
                                   for text in ["KLIPPY", "CLIPPY", "HEY KLIPPY", "HEY CLIPPY"]) + "\n",
                        encoding="utf-8", newline="\n")
    record(keywords, "wake", "https://github.com/khisanthax/Klippy-Assistant/blob/main/scripts/prepare_models.py",
           "klippy-phonetic-recipe-1; sentencepiece-0.2.3", "Apache-2.0")
    notices = destination / "notices"
    notices.mkdir()
    notice_names = ["Apache-2.0.txt", "Whisper-MIT.txt", "CMUdict-BSD.txt"] + [
        p.name for p in sorted((REPO / "packaging/licenses").glob("LLAMA-*.txt"))]
    for name in notice_names:
        target = notices / name
        shutil.copy2(REPO / "packaging/licenses" / name, target)
        license = "BSD-2-Clause" if "CMU" in name else "MIT" if "MIT" in name else "Apache-2.0"
        if name.startswith("LLAMA-"):
            license = "BSD-2-Clause" if "xxhash" in name else "LicenseRef-Public-Domain" if "sha256" in name else "MIT"
        record(target, "notice", "https://github.com/khisanthax/Klippy-Assistant/tree/main/packaging/licenses", "review-2026-11-11", license)
    manifest = {
        "format": 2, "qualification": {"status": "redistribution-reviewed", "reviewed_on": "2026-11-11",
            "scope": "License and integrity qualification, not microphone/room accuracy or stable-release acceptance",
            "components": [
                {"name": "GigaSpeech KWS", "license": "Apache-2.0", "evidence": [
                    SOURCES["wake"]["url"] + "#README.md",
                    "https://github.com/k2-fsa/sherpa-onnx/issues/3802#issuecomment-6415898531"],
                 "notices": ["notices/Apache-2.0.txt", "wake/README.md"]},
                {"name": "Whisper tiny.en ONNX", "license": "MIT", "evidence": [
                    "https://github.com/openai/whisper/tree/86098128c0b4f24f0e2aa2994de830614b474227#license",
                    SOURCES["asr"]["url"]], "notices": ["notices/Whisper-MIT.txt"]},
                {"name": "Kokoro v1.0 ONNX and voices", "license": "Apache-2.0", "evidence": [
                    "https://huggingface.co/hexgrad/Kokoro-82M/tree/f3ff3571791e39611d31c381e3a41a3af07b4987",
                    SOURCES["tts"]["url"]], "notices": ["notices/Apache-2.0.txt", "tts/LICENSE"]},
                {"name": "CMUdict derived lexicon", "license": "BSD-2-Clause", "evidence": [
                    "https://github.com/cmusphinx/cmudict/blob/74790861f652b15e4ac49015a90074ad62a27690/LICENSE",
                    "https://pypi.org/project/cmudict/1.1.3/"], "notices": ["notices/CMUdict-BSD.txt"]},
                {"name": "Qwen3 1.7B Q4_K_M", "license": "Apache-2.0", "evidence": [
                    "https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/blob/90862c4b9d2787eaed51d12237eafdfe7c5f6077/LICENSE",
                    SOURCES["llm"]["url"]], "notices": ["notices/Apache-2.0.txt"]},
                {"name": "llama.cpp CPU and LLVM OpenMP", "license": "MIT AND Apache-2.0 WITH LLVM-exception",
                 "evidence": [SOURCES["llama_binary"]["url"]],
                 "notices": ["notices/" + n for n in notice_names if n.startswith("LLAMA-")] +
                            ["llama/LICENSE-LLVM-OpenMP"]}]},
        "assets": sorted(assets, key=lambda a: a["path"]),
        "speech_config": {"tts_kind": "kokoro", "voice_id": 3,
            "wake": {"tokens": "wake/tokens.txt", "encoder": "wake/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
                     "decoder": "wake/decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
                     "joiner": "wake/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx", "keywords_file": "wake/klippy-keywords.txt"},
            "asr": {"encoder": "asr/tiny.en-encoder.int8.onnx", "decoder": "asr/tiny.en-decoder.int8.onnx", "tokens": "asr/tiny.en-tokens.txt"},
            "tts": {"model": "tts/model.int8.onnx", "voices": "tts/voices.bin", "tokens": "tts/tokens.txt", "lexicon": "tts/klippy-cmudict.txt"}},
        "runtime": {"binary": "llama/llama-server.exe", "model": llm.name}}
    text = json.dumps(manifest, indent=2) + "\n"
    expected_path = REPO / "models/manifest.json"
    if not write_manifest and json.loads(expected_path.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Generated assets differ from the reviewed manifest; qualification review required")
    (destination / "manifest.json").write_text(text, encoding="utf-8", newline="\n")
    verify_pack(destination, require_qualified=True)
    if write_manifest:
        expected_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Verified {len(assets)} bundled assets; no runtime model downloads required")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=REPO / "local/bundle-models-voice")
    parser.add_argument("--cache", type=Path, default=REPO / "local/model-cache")
    parser.add_argument("--write-manifest", action="store_true", help="Record a newly reviewed asset inventory")
    args = parser.parse_args()
    assemble(args.destination.resolve(), args.cache.resolve(), write_manifest=args.write_manifest)
