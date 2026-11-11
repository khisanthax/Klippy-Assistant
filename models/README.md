# Offline model pack

Runtime never downloads models. Large model files do not belong in Git.
manifest.json describes the 57-file license-reviewed Phase 2 pack. The reproducible
scripts/prepare_models.py assembler downloads only at build time and verifies every input
against scripts/model_sources.json. It rebuilds the CMUdict-derived English lexicon and
phonetic keyword file, then compares the complete output to the committed manifest.
The installed application includes those assets and never downloads a model.

candidates.json is historical Phase 1 evidence, not the production bundle. Its VITS and
unreviewed lexicon are excluded. Production uses Kokoro v1.0, a CMUdict-derived lexicon,
GigaSpeech KWS, Whisper tiny.en, Qwen3 1.7B and CPU-only llama.cpp. Qualification here
means redistribution/integrity review, not microphone accuracy or stable-release acceptance.

Each asset must specify `path`, `role`, `source`, `version`, `license`, and `sha256`.
Required roles: wake, asr, tts, llm, llama_binary. All files used by each model (tokens,
encoder/decoder/joiner, voice data, binary dependencies and license texts) need entries.
Use an immutable revision/checksum and verify license evidence before recording local hashes.
Notice files are integrity-verified. Unlisted DLL/EXE files beside the runtime are rejected.

The speech_config contains sherpa constructor arguments, with relative paths:
The runtime entry specifies binary/model paths; every referenced file and every file in
a referenced data directory must have an integrity entry.

```json
{
  "wake": {"tokens":"wake/tokens.txt", "encoder":"wake/encoder.onnx", "decoder":"wake/decoder.onnx", "joiner":"wake/joiner.onnx", "keywords_file":"wake/klippy-keywords.txt"},
  "asr": {"encoder":"asr/encoder.onnx", "decoder":"asr/decoder.onnx", "tokens":"asr/tokens.txt"},
  "tts_kind": "kokoro",
  "voice_id": 3,
  "tts": {"model":"tts/model.int8.onnx", "voices":"tts/voices.bin", "tokens":"tts/tokens.txt", "lexicon":"tts/klippy-cmudict.txt"}
}
```

Keyword tokenization must match the selected model, explicitly encode Klippy, and be
validated acoustically. A manifest's presence alone does not qualify a model. Stable
packaging needs a reviewed license inventory and complete-file coverage.
