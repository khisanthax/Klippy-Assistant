# 0.8 capability limits engineering preview candidate

**Unpublished; not qualified for release.** Application source `5862ec29cbaa37dc2e7b8501dac3033b135e47d1`.

Implemented per-printer active Klipper capability discovery, deterministic single-axis
relative/absolute movement, machine/G-code offset translation, fresh state/limit validation
and mandatory single-use motion confirmation. Firmware heater limits are authoritative;
existing owner caps and new optional stricter limits can only restrict execution. Settings
provides read-only inspection and a validated stricter-limit editor. See
[the registry specification](docs/PRINTER_LIMITS.md) for supported conditions and primary sources.

Cartesian/CoreXY single-axis XYZ only. Delta/other kinematics retain native discovered data
while movement stays blocked. Unhomed/moving state, active/unknown transforms, stale or
malformed data, unsupported extrusion, ambiguous physical bed directions and model-selected
movement block safely. Firmware limits do not establish path clearance. Configuration,
restart, disconnect, selected printer and relevant state/policy changes revoke reviews.
No physical printer connections/actions or owner installed-profile changes in qualification.

## Verified on the Windows development host

- All **886 tests**, zero failures/skips, and Ruff passed; 124 additional regressions.
- All 57 unchanged model/runtime assets verified against their existing qualified manifest.
- Frozen startup/shutdown, 29 orb and 26 actual Qt feature checks passed. The latter include
  capability inspection, rejection of expanded limits and saving stricter local limits.
- All retained native engineering-preview gates passed: 25 wake cases plus injected recovery,
  eleven read-only query cases, 21 heating/cancellation cases, grounded dialogue, audio delivery,
  echo/interruption, three unprefixed follow-ups and **eight read-only limits/motion cases**.
- Frozen native integration passed under a **16 GiB process-tree commit limit**: peak
  2.356 GiB across 3 processes,
  103.232 seconds wall time and 181.547 CPU seconds. The build compressor
  was also running; this is a budget pass, not a controlled latency comparison or 16 GB host test.
- Original broad continuous-capture outcomes remain independent: frozen `False`,
  memory-budgeted `False`. Required paced preview gates passed in both. No acoustic
  assertion was weakened, and no human wake accuracy is claimed.
- Inno Setup compilation and SHA-256/sidecar comparison passed. Installer was **not installed**
  over the owner's registered application; installed upgrade/offline/reinstall qualification
  awaits a fresh runner. Existing owner installation/settings remain untouched.

Native proposed-move timings use synthetic Moonraker, excluding ASR/TTS/playback and real LAN
latency: X relative 2.352 ms; X absolute
1.429 ms; Z relative
1.382 ms. Diagnostics expose the `limits_refresh` span.

## CI blocker and release status

[Windows workflow dispatch](https://github.com/khisanthax/Klippy-Assistant/actions/runs/44202364931) and push run 44202365689 failed **before any job
steps**. GitHub's annotation: “The job was not started because an Actions budget is preventing
further use.” This is an infrastructure block, not a test failure or passing CI qualification.
No public preview release has been published. The latest published release stays 0.7.2.

Once Actions budget is available, rerun the exact-source workflow and require all test/build/
installed-qualification jobs, including actual 0.7.2 upgrade/reinstall/offline/settings/history/
owner-limit preservation, installed memory gates, artifact verification and source tagging.
No gate will be waived to publish this candidate. Issue #19 remains open.

Candidate installer: `Klippy-Setup-0.8.0-preview.1.exe`; 1489543358 bytes.
SHA-256: `c4f78386009211369424f013e8165de925275a26734c5f9214751a39b6110256`.
Local location: `dist/Klippy-Setup-0.8.0-preview.1.exe` with adjacent SHA-256 sidecar.

Evidence: benchmarks/preview8-local-package-qualification.json, local-frozen/local-frozen-orb/
local-frozen-wake/local-memory/local-memory-voice JSON, and earlier local native/Qt reports.
No owner conversations, printer configurations, microphone recordings or credentials committed.

Supervised hardware/path/offset acceptance, unsupported motion scope, human acoustic accuracy,
sustained device load, clean interactive Windows VM and an actual 16 GB host remain open.
The installer is unsigned; this is an engineering candidate, not stable v1.0.
