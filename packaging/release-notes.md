Klippy Assistant 0.2.0 offline voice engineering preview

99 automated tests pass locally and in Windows test CI. The single installer includes
all required KWS, Whisper, Kokoro and Qwen/llama.cpp models with reviewed licenses,
provenance, checksums and notices. No post-install model download or cloud AI is needed.

Klippy and Hey Klippy detection now pass synthetic probes. Duplex echo cancellation and
local wake verification support interruption. Source, frozen and installed-model tests
stopped playback and transcribed the interruption with zero printer writes. Own-voice
echo probes created no requests. Windows default capture/render and TTS playback passed.
Clippy is a homophone and cannot be reliably excluded by spelling.

This is not stable v1.0. Human microphone/room accuracy, unplug/replug, clean-machine
offline qualification and supervised printer safety remain open. Optional speaker
enrollment is deferred. No live printer actions were performed. The package is unsigned.

Run Klippy-Setup-0.2.0-preview.1.exe (~1.39 GiB) as a normal Windows user, open Klippy
from Start, enable the microphone from the tray and wait for models to become ready.
No separate Python or Ollama is needed. Read PHASE2_REPORT.md before testing. Settings
and vault credentials are preserved on uninstall; README describes data removal.
Verify the adjacent SHA-256 file. Development-host install/reinstall/SQLite preservation,
installed voice integration and uninstall passed. Remaining gates are tracked in issues.
