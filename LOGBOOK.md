# Logbook

## 2026-11-11 — Initial implementation and safety regressions

Work completed: created private khisanthax/Klippy-Assistant; installed a project-local Python
environment; implemented Qt desktop/tray/companion, approved printer management, vault
credentials, macro review, local scheduling, backup/restore, HTTP/WebSocket adapters,
notification-only monitoring, structured local LLM adapter and ONNX speech adapter.

Decisions: all writes require single-use confirmation in the preview; macros are idle-only;
any configuration change revokes macro approvals conservatively. No arbitrary G-code from
the model. No command retries. Speech remains disabled without a verified full asset pack.

Files: pyproject.toml, src/klippy, tests, architecture/safety/roadmap/release docs, model manifest.

Tests: initial pytest run 60 passed / 1 skipped; removed the skip by adding metadata-host
restriction. First UI smoke exposed double cleanup of the asyncio loop; added idempotent
shutdown and a regression subprocess test. Added cancellation-during-validation regressions.
Full rerun and packaging are next; do not treat initial results as final acceptance.

Hardware: configured Mercury SSH alias works in batch mode. Read-only inspection found two
Moonraker instances on non-default ports; one reports Klipper error and the other ready.
No live write, movement, heating, cancellation, repair or configuration changes performed.
No real addresses/configurations copied into repository files.

Known issues: qualified speech/LLM model payload absent, llama process management absent,
half-duplex speech only, speaker enrollment absent, full MMU fault semantics and automatic
reconnect macro refresh unfinished. Installer/CI/clean-machine tests and acoustic/hazardous
hardware qualification pending. No stable release or performance claims.

Next actions: rerun tests/lint/UI, build frozen preview and installer, track eight phases on
GitHub, push meaningful milestone, then qualify offline engines and package gates. Keep all
unverified acceptance items open. Read this file before resuming work.
