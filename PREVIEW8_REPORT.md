# 0.8 capability limits engineering preview candidate

Qualification is pending. Do not treat this source candidate as a published or qualified build.

Per-printer active Klipper capability discovery, deterministic single-axis relative/absolute
movement, bounded machine/G-code coordinate translation, fresh state/limit validation and
mandatory single-use motion confirmation are implemented. Firmware heater limits are now
authoritative with existing owner caps and optional stricter overrides retained. See
[the registry specification](docs/PRINTER_LIMITS.md) for exact supported conditions and sources.

Cartesian/CoreXY direct moves only; delta/other layouts retain native discovered information
while direct motion stays blocked. Active/unknown transforms, unhomed/moving state, stale data,
ambiguous bed directions, unsupported extrusion and model-selected movements are blocked.
This does not establish path clearance. No physical printer connections or actions in tests.

Local validation: all 886 tests and Ruff pass (124 additional cases). Native model engineering
preview gates pass with zero writes; the independent broad continuous-capture result is False.
Focused limits/motion qualification passes; native desktop 29 orb checks and
26 feature checks (including limits inspection/expansion rejection/stricter local save) pass.
Windows frozen/installer/offline/upgrade/memory qualification must finish before publication.
Local evidence: benchmarks/preview8-local-native.json and preview8-local-orb.json. Models/audio/wake thresholds are unchanged.

Hardware, human microphone/room, sustained device load, clean interactive desktop VM and an
actual 16 GB host remain open. A process-tree 16 GiB budget is not actual-host acceptance.
