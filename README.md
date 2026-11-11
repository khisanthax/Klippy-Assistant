# Klippy Assistant

Fully local Windows desktop companion for explicitly approved Klipper/Moonraker printers.

**0.1.0.dev1 — engineering preview, not stable v1.0.** Manual controls, simulated safety
coverage and a tray UI are implemented. Offline speech adapters exist, but a qualified
redistributable model pack, acoustic barge-in and supervised hardware validation are
release blockers. Do not treat this build as a validated voice assistant.

Real CPU-only candidate probes generated TTS, transcribed a synthetic request, and ran
Qwen3 1.7B through an owned llama.cpp process. Synthetic Hey Klippy activated KWS; short
Klippy failed at the tested threshold. These results are not microphone qualification.
See [RELEASE_REPORT.md](RELEASE_REPORT.md) for the tested preview and remaining work.

## Run from source (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-lock.txt
.\.venv\Scripts\python -m pip install -e . --no-deps
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
The preview installer is unsigned and does not include a qualified speech/LLM pack.
Stable packaging must fail if verified model assets are missing. Runtime never downloads models.
