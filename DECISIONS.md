# Decisions and evidence

## 2026-11-11 — Initial implementation

- Python 3.13.3 and PySide6 6.12.0 installed successfully on this Windows host. Python 3.12+
  remains the declared source target; Python 3.12 binary compatibility is not measured.
- Qt widgets provide management panels and a tray; a small drawn vector companion avoids
  unnecessary image assets. PyInstaller onedir + Inno Setup is the initial packaging path.
- SQLite stores configuration and bounded operational event codes. Windows keyring stores
  API keys. Configuration exports deliberately exclude secrets and revoke approvals on restore.
- All actions, including pause/resume/emergency, require explicit confirmation in this
  preview. Fundamental validation cannot be disabled. Unknown macros are blocked until review.
- Macro execution is conservatively idle-only. All configuration changes revoke all macro
  approvals, including callers. Precision dependency analysis can be added after validation.
- Numeric macro parameters only. No freeform strings, raw G-code, or model-generated code.
- HTTP polling is the first UI monitoring path; WebSocket subscription adapter is separate.
- Speech candidate: sherpa-onnx 2.0.1 (installed Windows wheel), KWS transducer, Whisper
  ASR and VITS TTS. No model is accepted merely because a runtime package is licensed.
- LLM candidate: Qwen3 1.7B GGUF via llama.cpp, loopback-only with strict Pydantic validation
  after constrained generation. Model output never authorizes execution.
- Preview speech capture is half duplex to reject self-triggering. Manual interruption
  works through Stop speaking. Acoustic echo cancellation and hands-free barge-in remain
  required before stable voice release; disabling self-voice detection would be unsafe.

## Primary technical references

- [Moonraker printer API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
- [Moonraker object specification](https://moonraker.readthedocs.io/en/latest/printer_objects/)
- [Sherpa keyword spotting](https://k2-fsa.github.io/sherpa/onnx/kws/index.html)
- [Sherpa model catalog](https://k2-fsa.github.io/sherpa/onnx/pretrained_models/)
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Official Qwen GGUF candidate](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF)

## Measurements

No acoustic accuracy, idle memory/CPU, LLM latency, model memory or clean-machine results
are claimed. Record hardware, tools, settings, samples, measurements and date before adding
performance claims. Synthetic safety tests are not real-printer validation.
