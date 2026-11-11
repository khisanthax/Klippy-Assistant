# Klippy engineering preview — 2026-11-11

## Repository and version

Private repository: https://github.com/khisanthax/Klippy-Assistant

Source version: 0.1.0.dev1. Installer/release label: 0.1.0-preview.1.
This is an engineering preview. Stable v1.0 is not complete, and several software phases
remain partial in addition to hardware acceptance gates.

Installer location after publication:
https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.1.0-preview.1

Local artifact: dist/Klippy-Setup-0.1.0-preview.1.exe, with adjacent SHA-256 file.
Run the installer as your normal Windows user, then open Klippy from the Start menu.
Startup-with-Windows and desktop shortcuts are optional. Closing the panel hides it;
Quit in the tray exits. Upgrade/uninstall preserve user settings and vault credentials.
README.md describes manual data removal. Installer is unsigned.

## Implemented

- Qt control panel, hidden tray launch, movable auto-hiding companion with speaking/error
  states and active printer banner.
- Explicit LAN printer enrollment/approval, connection tests, credential vault, discovery,
  last-printer persistence and removal.
- Read-only status/temperature polling and notification-only fault/disconnect alerts.
- Per-printer macro discovery, exclusions, review, optional aliases and numeric parameter
  bounds; configuration fingerprints, conservative reapproval, conflicts and possible renames.
- Independent safety engine, live state/permission checks, single-use expiring confirmations,
  asynchronous cancellation invalidation, no command retry and uncertain-outcome reporting.
- Local structured intent interpretation, lexical fallback, short-lived follow-ups and
  missing-parameter clarification. No LLM-generated G-code or persisted conversation history.
- Listening modes/schedules, microphone controls independent of monitoring, configuration
  export/restore, credential-free exports and bounded operational event codes.
- Actual local Sherpa/Whisper/VITS/Qwen/llama.cpp candidate inference probes, an owned
  CPU-only offline llama process and strict asset integrity checks. These are experimental;
  voice is disabled by default in the installer and qualified model weights are not bundled.

## Verification

78 local automated tests passed. Ruff passed. Earlier Windows GitHub CI passed; consult
the repository Actions tab for the final evidence commit. Source and frozen Windows
startup/clean shutdown passed, including native speech/audio imports. The installer built
and initial per-user install/reinstall/preservation/installed launch/uninstall checks passed
on the development host. Final evidence is maintained in LOGBOOK.md.

Read-only real hardware: configured Mercury SSH access verified; two Moonraker instances
found, one reporting error and one ready. The application's HTTP snapshot client queried
the ready instance successfully (standby, two temperature objects). No device was enrolled
automatically. No movement, heating, pause, cancel, repair or configuration write occurred.
Other printers are unverified. No supervised actuation or microphone test was performed.

## Scoped measurements

Developer host: Windows 11 build 26200, Ryzen 7 5800X, 16 logical processors, 63.9 GiB RAM.
CPU-only synthetic probes, not the requested typical 16 GB end-user baseline:

| Probe | Measured result |
|---|---|
| Hidden source shell, no models/devices/printers | 89.3 MiB working set; 0.104% of one CPU core over 14.992 s |
| Speech engine load | 4.303 s |
| VITS generation | 0.503 s for 1.261 s generated speech |
| Whisper ASR | 0.142 s; synthetic text: pause the test printer |
| Llama startup | 3.324 s (warm filesystem cache; separate earlier run 11.13 s) |
| Qwen interpretation | 1.552–3.165 s across three synthetic prompts |
| Preview installer | approximately 53.8 MiB before final license/docs repackaging |

Detailed JSON evidence is under benchmarks/. These small samples are not accuracy rates
or latency guarantees. Full voice-pipeline latency, device changes, sleep/resume, model
memory and clean-machine offline runtime remain unmeasured.

## Remaining work and user involvement

Primary short Klippy detection failed its synthetic probe at the tested threshold; Hey
Klippy passed. No substitute wake word is silently enabled. Voice requires further tuning,
acoustic qualification, echo cancellation and hands-free interruption. Speaker enrollment
is absent. Model/lexicon/binary redistribution review and complete bundled payload remain
unfinished. Full WebSocket/MMU monitoring, richer macro review/differences, some settings
controls and broader end-to-end acceptance are still software work, tracked in GitHub.

Stable release also requires a clean Windows VM with no developer tools, network-isolated
runtime, cross-version upgrade/data handling tests, a typical 16 GB CPU baseline, actual
microphone/default-device tests and the owner's supervised printer safety tests. Only
those physical/consequential tests require user presence; ordinary software work remains
authorized. No stable-release claim is made based on simulations or this preview.
