# Offline model pack

Runtime never downloads models. Large model files do not belong in Git.
The manifest is intentionally empty until assets are qualified. Load local voice pack
rejects an incomplete or tampered manifest; manual controls/monitoring remain usable.

Each asset must specify `path`, `role`, `source`, `version`, `license`, and `sha256`.
Required roles: wake, asr, tts, llm, llama_binary. All files used by each model (tokens,
encoder/decoder/joiner, voice data, binary dependencies and license texts) need entries.
Use an immutable revision URL and verify upstream hash/license before recording local hashes.

The speech_config contains sherpa constructor arguments, with relative paths:

```json
{
  "wake": {"tokens":"wake/tokens.txt", "encoder":"wake/encoder.onnx", "decoder":"wake/decoder.onnx", "joiner":"wake/joiner.onnx", "keywords_file":"wake/klippy-keywords.txt"},
  "asr": {"encoder":"asr/encoder.onnx", "decoder":"asr/decoder.onnx", "tokens":"asr/tokens.txt"},
  "tts": {"model":"tts/voice.onnx", "tokens":"tts/tokens.txt", "data_dir":"tts/espeak-ng-data"}
}
```

Keyword tokenization must match the selected model, explicitly encode Klippy, and be
validated acoustically. A manifest's presence alone does not qualify a model. Stable
packaging needs a reviewed license inventory and complete-file coverage.
