# Test plan

## Floating voice orb (0.6)

Preserve 510 previous cases; 568 total cover the passive orb and associated stale-event
fixes. `python -m klippy.app --orb-self-test --smoke-report local/orb.json` uses actual Qt
widgets, synthetic PCM and isolated settings without opening devices or printers. Inspect
state/size PNGs, nonactivation, native taskbar observations, cleanup and measured CPU/memory.
Frozen build and offline installed QA must run this in addition to every existing probe.
Upgrade/reinstall fixtures include orb preferences. Real Windows 10/11 DPI/auto-hide/
hot-plug/vertical-taskbar/full-screen/reduced-motion/sleep-resume acceptance remains open.

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

The 0.5.1 regression suite includes the exact owner heating phrase and all requested
variations, configured/colliding number-word aliases, Celsius default and explicit Fahrenheit,
converted limit boundaries, missing heaters/limits, read-only versus heating classification,
wrong-action model parameters, explicit cancellation versus negative conversational remarks,
clarification/playback/confirmation races, configured prompt policy and single-use/no-retry.
Unit/heater/command words cannot become printer mentions; explicit “90 F on F”, unsupported
K units and genuine Nozzle One names exercise ambiguous positions without physical APIs.
Frozen/installed/memory probes additionally require all 21 command cases through Conversation
and SafetyEngine with every HTTP write forbidden, zero supported-request LLM calls and no
remaining pending action. These checks do not authorize or qualify actual printer heating.

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

## 0.4 query qualification

Run `python -m pytest tests/test_queries.py -q` for every catalog ID/example, missing or
malformed objects/fields/components, aliases and two-printer follow-ups, query/action
separation, current/stale/cache-delta behavior, reset/configuration changes, bounded object
batches and delayed old-endpoint response isolation. Query transports assert GET and the
independent endpoint/field/parameter allowlist rejects control and arbitrary API paths.

Both full `--voice-self-test` and explicit engineering `--preview-self-test` retain
query_probe's seven-case simulated-printer/native-query-LLM report. Preview mode requires
Hey-Klippy acknowledgement followed by actual ASR-to-query status, six negative audio
inputs opening zero sessions/requests, own-echo rejection, verified interruption and zero
writes. Original full voice gates/results remain visible and can be false; full continuous
speech/raw KWS acoustic acceptance stays open. Both frozen and installed probes must
include it; it cannot be substituted by an unrelated hardcoded status request. Inspect
`query_catalog` in each JSON report. Every probe must report zero printer writes.

Cross-version installer qualification upgrades 0.3 to 0.4 while preserving private SQLite
fixtures. Hardware, acoustics, real fleet/authentication, clean desktop VM and actual 16 GB
host gates remain open regardless of synthetic passes. API coverage/exclusions and expected
fields: docs/MOONRAKER_QUERIES.md and docs/query_catalog.json.
