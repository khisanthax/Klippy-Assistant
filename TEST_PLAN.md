# Test plan

## Automated

Run pytest and Ruff, then a Qt startup/clean-shutdown subprocess test. Tests use a simulated
Moonraker transport with real HTTP client serialization. They cover read-only status,
confirmation binding/expiry/single use, state changes, canceled asynchronous validation,
unknown/changed/removed/renamed/excluded macros, callee changes, injection, strict model
output, parameters, no command retry, uncertain physical completion, credential redaction,
printer selection persistence, backup restore, notification-only monitoring, schedules,
missing/tampered models and transcript non-persistence.

Wake/non-wake text cases validate conversation gating only. They do not validate audio models.
Offline tests validate isolated software paths with simulated LAN transport, not a full
network-isolated speech installation. CI must not substitute these for acceptance gates.

## Physical hardware — pending supervised testing

- Klippy and Hey Klippy recognition, Klipper/Clippy false positives; labeled sample counts.
- Default recording/playback devices, unplug/replug, device changes, speaker failure.
- AEC/self-TTS rejection, speech interruption latency and corrected target/request.
- CPU-only end-to-end speech latency/memory and idle CPU on a 16 GB Windows host.
- Read-only connection/status/macro discovery for each individual printer.
- Explicitly supervised pause/resume/cancel/home/heater/macro/MMU operations only.
- Disconnect during action, sleep/resume and multi-printer faults.
- Notification accessibility and auto-hide on a normal Windows desktop.

## Installer — pending clean VM qualification

Install on a Windows x64 VM with no Python/development tools; block WAN access and allow
only enrolled LAN devices. Verify all required bundled models and license notices. Exercise
launch, upgrade with sentinel settings, uninstall keeping data and uninstall deleting data.
Check shortcuts, optional Windows startup, credential removal options and no leftover app
files. Capture installer hash, build environment, signatures and actual results.

## 0.3 repeatable software qualification

- `python -m pytest -q` and `python -m ruff check src tests scripts`: preserve the original
  99 cases plus shared-session, delayed delivery, exact-token, notification isolation,
  muted/failed playback, natural queries, fleet/MMU, confirmation preferences and recovery cases.
- `python scripts/latency_probe.py --output local/latency-after.json`: real CPU TTS first
  PCM, full generation and warm-cache timing, without opening devices.
- `scripts/build.ps1`: complete qualified model payload, frozen launch and real-model
  synthetic integration. The isolated integration process denies Python external sockets;
  native llama.cpp uses offline mode. No real printer APIs are used.
- `scripts/test_installer.ps1 -PreviousInstaller dist/Klippy-Setup-0.2.0-preview.1.exe`:
  isolated actual upgrade, reinstall, SQLite preservation, installed startup/voice and uninstall.
  Refuses to touch a registered owner installation. `-BlockExternalNetwork` additionally
  blocks external egress for installed app/runtime executables and requires firewall privileges.
- `scripts/performance_probe.ps1`: real frozen pipeline with inherited process-tree 16 GiB
  commit limit and CPU/peak-memory accounting. This cannot substitute for 16 GB total-VM RAM.
- Fresh Windows CI installer job provides independent offline/upgrade evidence. An actual
  clean Windows desktop VM without Python, disabled networking, 16 GB total RAM and extended
  sleep/resume/audio soak remains a separate gate; unavailable on this development host.
