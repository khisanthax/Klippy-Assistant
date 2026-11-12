# Roadmap

Each phase stays open until its exit gate is verified. Implementation is not acceptance.

| Phase | Status | Verified / remaining |
|---|---|---|
| 1. Foundation | Complete | Private repo pushed, runnable Qt application, storage, docs, 78 local tests; Windows CI green on application commit aa5b30c; phase milestone/issue closed |
| 2. Local voice and AI | Core implemented; hardware gate open | Klippy/Hey Klippy synthetic detection fixed, actual Whisper/Kokoro/Qwen pipeline, duplex AEC/interruption, Windows capture/render smoke, 57-file license-reviewed payload; human wake/room accuracy and optional speaker enrollment remain open |
| 3. Connectivity | Partial | Bounded concurrent fleet polling, per-printer status/MMU view, Happy Hare v3/v4 fault notifications, enrollment/vault/discovery/client implemented; simulated multi-printer isolation verified; actual fleet/auth/subscription qualification open |
| 4. Macro intelligence | Partial | Discovery/reapproval, deterministic synonyms and numeric parameters, body similarity, rename warnings and review diffs implemented; extended semantic and actual fleet acceptance open |
| 5. Safe execution | Partial | Central engine with mandatory fresh checks, configurable operational prompts, exact playback-bound confirmation windows, exact action/value review, mandatory model-write review, single-use tokens and uncertain outcomes; supervised hardware tests open |
| 6. Companion/monitoring | Partial | Hidden tray launch, movable animated companion, auto-hide, active banner, schedule, fault alerts, read-only reconnect macro refresh; Happy Hare fault notifications, persisted companion position/visibility/duration and scrollable settings added; desktop/sleep acceptance open |
| 7. Stabilization | In progress | Expanded simulated regressions, crash/WAL recovery, validated backup/restore and monotonic reaction diagnostics; fresh-runner offline upgrade and 16 GiB process-budget probes passed; actual 16 GB VM/audio/sleep/fleet gates open |
| 8. Distribution | Partial | Unsigned preview installer builds; install/reinstall/settings preservation/installed launch/uninstall passed on development host; complete licensed model payload, fresh Windows CI cross-version upgrade/reinstall/SQLite preservation/offline-model/uninstall qualification passed; clean Windows desktop VM and stable release gates remain open |

## Moonraker query expansion (0.4 preview)

Published [v0.4.0-preview.1](https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.4.0-preview.1) at source `643b949` after exact
run 43260616461 passed all required engineering-preview jobs. Full continuous/raw-KWS
acceptance is separate and remains open; the budgeted diagnostic missed continuous wake.


Implemented 41 built-in read-only query types, per-printer object/field/component discovery,
strict endpoint/parameter allowlist, deterministic common questions and isolated query-only
local LLM fallback. Added printer aliases, query/subject follow-ups, two-second field-aware
cache reuse with explicit stale labels, reconnect/configuration invalidation and searchable
Queries & Commands inventory. Original 179 tests preserved; 370 tests and Ruff pass.
Actual local-model query probe passed after correcting a semantic category confusion;
failed and corrected evidence is retained. Exact-source run 43260616461 attempt 1 passed frozen/installed/offline
0.3-to-0.4 upgrade/reinstall/recovery and memory-budget qualification. A prior same-source
frozen wake-capture failure is retained; it remains an acoustic reliability limitation. All physical and clean-machine gates remain open.

## Next priority

1. Preserve the 370 passing regressions (original 179/99 cases unchanged); extend unfamiliar
   query semantic coverage and supported field/accessory cases without granting write authority.
2. Extend the macro semantic benchmark and fleet authentication/subscription qualification;
   use simulated services for software work independently of hardware availability.
3. Obtain a clean Windows desktop VM without development dependencies and a 16 GB total-RAM
   environment for offline installation, performance, sleep/resume and desktop acceptance.
4. Separately validate microphone samples (Klippy, Hey Klippy, Klipper, Clippy, silence,
   own TTS, interruptions). Supervised consequential printer tests require the owner present.
5. Publish accurately scoped previews; stable v1.0 requires every release gate to pass.

## 0.3 preview software work

Published [v0.3.0-preview.1](https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.3.0-preview.1) after exact Windows qualification run 43136945820
passed all jobs. The source tag is `69e5bf7`; final artifact and scope are in PREVIEW3_REPORT.md.

Shared processing/playback follow-up sessions, streamed/cached TTS, post-playback confirmation
windows and deterministic natural temperature/progress queries address the owner usability report.
See PREVIEW3_REPORT.md and benchmarks/preview3-*.json for measured scope. Hardware calibration
does not block independent software work; it remains a separate acceptance gate.
