# Klippy Assistant

Fully local Windows desktop companion for explicitly approved Klipper/Moonraker printers.

Current engineering preview **0.7.1-preview.1** fixes wake Attention diagnostics and stale
recognition after input-queue overrun. Stored wake-prefix rejections are distinguished from
microphone, ASR and playback failures. Hover over Attention for its reason, or right-click
the orb / open Diagnostics / History for **Copy latest diagnostic**. A new wake clears the
previous warning; discarded old events cannot restore it.

Short wake-only recovery requires a separate stricter phonetic check and two strict complete
ASR results. It forwards only Klippy with no command or confirmation token. Uncertain, echo,
canceled and stale input stays rejected. No TTS/audio-quality algorithm or model payload change.

Personality/length/context/casual chat, optional local History, shared follow-up countdown and
reviewed-macro clarification remain. Logging stays off for new profiles; existing choices are
preserved. Diagnostic event fields/transcripts respect current consent. No microphone audio
is recorded. Read [PREVIEW71_REPORT.md](PREVIEW71_REPORT.md) for the cause and evidence limits.

725 tests/Ruff, 29 orb/22 feature checks and exact-source frozen/installed native wake, 0.7.0
upgrade/reinstall/offline/settings/history-choice preservation and process-tree memory gates
passed. All 13 release asset sizes/digests verified. Human microphone/room accuracy, full
interactive desktop, clean VM, actual 16 GB hardware and supervised printer acceptance remain
open; unsigned engineering preview, not stable v1.0.

The 0.6 preview adds a floating waveform orb using the existing voice streams. It shows wake
verification, listening, thinking, real playback and pending confirmation above the taskbar
clock. **Settings → Voice Orb** controls diameter, labels, auto-hide, pinning and motion;
drag to customize and right-click to reset. It normally stays hidden with the microphone
off or outside a conversation. See [PREVIEW6_REPORT.md](PREVIEW6_REPORT.md) for actual Qt
captures, measurements, qualification progress and open desktop acceptance gates.

[Download the 0.7.1 engineering preview](https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.7.1-preview.1)
(unsigned, about 1.39 GiB). Run Setup as a normal Windows user, open Klippy from Start,
then enable the microphone from the tray and wait for the models to become ready.
The repository is private: sign in to GitHub with an account that has access before
opening the download link. GitHub can show 404 when you are signed out or lack access.

**0.6.0.dev1 — floating voice orb engineering preview, not stable v1.0.** The installer includes
local wake-word, ASR, TTS and language models. Enable the microphone in the tray or
Settings to load them. No post-install model download, Python, Ollama or cloud AI is needed.
Microphone/room accuracy and supervised printer safety acceptance remain open.

568 tests/Ruff and exact-source Windows frozen/installed/offline qualification passed.
The installer upgrades 0.5.1 and preserves settings, including orb preferences. All nine
release asset digests were verified. Interactive desktop, clean-VM and actual-16-GB gates
remain open; see [PREVIEW6_REPORT.md](PREVIEW6_REPORT.md).

Real CPU-only probes recognize Klippy and Hey Klippy, transcribe requests, generate
Kokoro speech and run Qwen3 1.7B through an owned offline llama.cpp process. Duplex
echo cancellation and local wake verification support interruption. Synthetic double-talk
tests pass; the Windows default audio path also passed a capture/render smoke test.
Clippy is a homophone and cannot be excluded by spelling. These are not broad acoustic
accuracy results. See [PHASE2_REPORT.md](PHASE2_REPORT.md).

See [docs/MOONRAKER_QUERIES.md](docs/MOONRAKER_QUERIES.md) for the 41-query catalog, capabilities, freshness and safety boundaries. Open **Queries & Commands** to search queries, operations and discovered macros, refresh capabilities, or edit printer voice aliases. Ask “Klippy, is my M1 printer homed?”, “What about the SV08?”, “How hot is the bed?” or “What layer am I on?”. Information queries never run homing/heating actions.

See [PREVIEW4_REPORT.md](PREVIEW4_REPORT.md) for query qualification and remaining gaps.

The 0.5 source adds **Printers → Edit Names & Aliases**, a local recognition test,
natural switching (“Switch to M1”, “Use the SV08”, “Go back to Mercury Two”) and
“Which printer am I using?”. Settings offers Brief, Conversational and Detailed speech.
Ordinary speech rounds temperatures; detailed UI values stay exact. Ask “How hot is the
nozzle?” then “And the bed?” without repeating the wake word during the active session.
See [PREVIEW5_REPORT.md](PREVIEW5_REPORT.md) for capture fixes, diagnostics and open gates.

The [0.5.1 hotfix report](PREVIEW51_REPORT.md) covers deterministic heating and explicit
cancellation. With Mercury One/M1 configured, ask “Can you set the Mercury 1 nozzle to 90
degrees?” or “Heat Mercury One's hotend to ninety”. Omitted units mean Celsius; explicit
Fahrenheit converts before reviewed-limit checks (“194 F” reviews 90 C). “What's the nozzle
temperature?” remains read-only. Units/command words cannot be mistaken for printer names.
Only explicit cancellation phrases discard a review. Ordinary uncertain “not” remarks ask
clarification; an existing review cannot execute until a complete new request is stated.
Invalid model action/parameters produce helpful explanations, with technical codes only
in Settings diagnostics. Reviewed heater limits, configured prompts and no-retry safeguards
remain. 510 tests and all 21 packaged command cases passed; physical heating acceptance stays open.

See [PREVIEW3_REPORT.md](PREVIEW3_REPORT.md) for voice latency fixes, fleet/MMU monitoring,
macro review improvements, confirmation settings, recovery and qualification limits.

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
5. Requests such as `pause`, `resume`, `cancel print` and `home` require a confirmation
   bound to the exact target/action. The default response window is 30 seconds after
   spoken playback finishes; interrupted/failed prompts cancel. Settings can change the
   window or disable selected operational prompts. Mandatory checks always apply; macros,
   critical operations and model-interpreted writes retain confirmation. Bare `cancel`
   cancels the pending request; use `cancel print` for a print job. No transmission retry.

For voice, enable listening and wait for the local model status to become ready. Say
"Hey Klippy", wait for acknowledgement, then ask "status" or "what is the temperature?".
Both preregistered single-attempt Hey wake-only and Hey-plus-temperature cases passed
synthetic frozen/installed/memory probes. Broader continuous-speech and raw wake-word accuracy
remain unqualified; the installed original bare-Klippy continuous case missed activation
and its failure is retained. Voice is experimental. Follow-up listening lasts
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
