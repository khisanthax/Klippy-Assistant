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

## Measured candidate probes

See benchmarks/ for actual CPU-only synthetic probe results. VITS generated speech and
Whisper tiny.en transcribed the generated pause request. Qwen3 1.7B Q4_K_M returned
temperatures/pause and clarification after prompt/schema changes. Initially it invented
a macro on a vague request: this motivated the independent evidence gate and regressions.

The KWS archive includes an Apache-2.0 model card. See the
[maintainer's clarification](https://github.com/k2-fsa/sherpa-onnx/issues/3802#issuecomment-6415898531).
Actual KWS accepted BPE tokens for Klippy/Hey Klippy and rejected two seconds of silence.
Synthetic Hey Klippy activated; synthetic short Klippy did not at threshold 0.25. This
is a failing primary wake requirement, not a reason to substitute a different wake word.

VITS-LJS includes an Apache-2.0 model card but its CMU-in-IPA lexicon provenance needs
complete redistribution review. The first lessac candidate referred to a separate dataset
license and was not selected. Model and binary asset checksums are in models/candidates.json;
these are experimental inputs, not the qualified distribution manifest.

Source-shell idle and synthetic inference timings are scoped to the recorded developer
host (Ryzen 7 5800X, 63.9 GiB, Windows 11 build 26200), not the requested typical 16 GB
baseline. Microphone accuracy, full-pipeline latency, model memory and clean-machine
results are unmeasured. Synthetic tests are not real-printer or acoustic validation.

## Packaging defect found and fixed

PyInstaller initially bundled Poppler's incompatible ICU from the developer PATH, causing
QtCore import failure. Controlled PATH collection fixed it. Console diagnosis and frozen
startup/shutdown checks verified the fix. Installer testing is isolated from actual settings.
