# Klippy Assistant

Fully local Windows desktop companion for explicitly approved Klipper/Moonraker printers.

**0.2.0.dev1 — offline voice engineering preview, not stable v1.0.** The installer includes
local wake-word, ASR, TTS and language models. Enable the microphone in the tray or
Settings to load them. No post-install model download, Python, Ollama or cloud AI is needed.
Microphone/room accuracy and supervised printer safety acceptance remain open.

Real CPU-only probes recognize Klippy and Hey Klippy, transcribe requests, generate
Kokoro speech and run Qwen3 1.7B through an owned offline llama.cpp process. Duplex
echo cancellation and local wake verification support interruption. Synthetic double-talk
tests pass; the Windows default audio path also passed a capture/render smoke test.
Clippy is a homophone and cannot be excluded by spelling. These are not broad acoustic
accuracy results. See [PHASE2_REPORT.md](PHASE2_REPORT.md).

## Run from source (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
.\.venv\Scripts\python -m pip install -e . --no-deps
.\.venv\Scripts\python scripts/prepare_models.py
.\.venv\Scripts\python -m klippy.app --show
```

Python 3.13 x64 was used for the first local build. The normal launch starts hidden
in the system tray. Double-click the tray icon to show controls; closing the window
hides it. Choose Quit in the tray menu to exit. `--show` opens the panel immediately.

1. Add a LAN Moonraker endpoint and a unique friendly name in Printers.
2. Test the connection read-only; explicitly approve the printer.
3. Select it in Companion. Ask `status`, `temperatures`, or `list macros`.
4. Refresh Macros, inspect actual definitions and callees, then explicitly review any
   macro you want to enable. All approvals are per printer. Parameters need reviewed
   numeric bounds; dynamic/raw parameter access is blocked in this preview.
5. Requests such as `pause`, `resume`, `cancel` and `home` require a confirmation
   bound to the exact target/action and expiring in 25 seconds. No transmission retry.

For voice, enable listening and wait for the local model status to become ready. Say
"Klippy, status" or "Hey Klippy, what's the temperature?". Follow-up listening lasts
about 30 seconds. During a response, say "Klippy, stop talking" to stop speech. You can
also use Stop speaking at any time. This never cancels a running print. Spoken approval
applies only to the exact pending action and capture-time confirmation token.

Monitoring is notification-only and independent of the microphone. No unsolicited
recovery, repair, movement or heating occurs. Firmware and physical safety mechanisms
remain essential. An explicit emergency-stop request uses Moonraker's dedicated endpoint
after approval in this conservative preview; do not wait for voice in an emergency.

## Privacy and recovery

Settings and a maximum of 1,000 operational event codes live in
`%LOCALAPPDATA%\KlippyAssistant\settings.sqlite`. API keys live in the Windows credential
vault. Speech recordings and conversation transcripts are not written to disk. On-screen
responses expire with the conversation. Exports contain private device configuration,
never credentials. Restore revokes device/macro approvals. Keep exports private.

Corrupt settings are preserved and startup fails visibly. Back up settings before
manual recovery. To reset: quit Klippy, move the application data directory to a private
backup, then launch again. Delete unneeded vault entries using Windows Credential Manager.
Optional speaker enrollment is not implemented; no enrolled voice data exists to delete.

## Validate and package

```powershell
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\ruff check src tests scripts
.\.venv\Scripts\python -m klippy.app --smoke-test
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

See [ROADMAP.md](ROADMAP.md), [TEST_PLAN.md](TEST_PLAN.md),
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) and [LOGBOOK.md](LOGBOOK.md).
The preview installer is unsigned and includes the license-reviewed model pack.
Model assets and archives stay outside Git; scripts/prepare_models.py is a build-time
checksum-pinned downloader/assembler. Runtime never downloads models. Builds reject
unreviewed, missing, altered or unlisted runtime binaries. Stable release stays gated
on physical acoustic/safety and clean-machine acceptance. Optional speaker enrollment
is deferred; wake detection and speaker identity are separate features.
