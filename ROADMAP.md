# Roadmap

Each phase stays open until its exit gate is verified. Implementation is not acceptance.

| Phase | Status | Verified / remaining |
|---|---|---|
| 1. Foundation | Complete | Private repo pushed, runnable Qt application, storage, docs, 78 local tests; Windows CI green on application commit aa5b30c; phase milestone/issue closed |
| 2. Local voice and AI | Core implemented; hardware gate open | Klippy/Hey Klippy synthetic detection fixed, actual Whisper/Kokoro/Qwen pipeline, duplex AEC/interruption, Windows capture/render smoke, 57-file license-reviewed payload; human wake/room accuracy and optional speaker enrollment remain open |
| 3. Connectivity | Partial | Bounded concurrent fleet polling, per-printer status/MMU view, Happy Hare v3/v4 fault notifications, enrollment/vault/discovery/client implemented; simulated multi-printer isolation verified; actual fleet/auth/subscription qualification open |
| 4. Macro intelligence | Partial | Discovery/reapproval, deterministic synonyms and numeric parameters, body similarity, rename warnings and review diffs implemented; extended semantic and actual fleet acceptance open |
| 5. Safe execution | Partial | Central engine with mandatory fresh checks, configurable operational prompts, exact playback-bound confirmation windows, single-use tokens and uncertain outcomes; supervised hardware tests open |
| 6. Companion/monitoring | Partial | Hidden tray launch, movable animated companion, auto-hide, active banner, schedule, fault alerts, read-only reconnect macro refresh; Happy Hare fault notifications, persisted companion position/visibility/duration and scrollable settings added; desktop/sleep acceptance open |
| 7. Stabilization | In progress | Expanded simulated regressions, crash/WAL recovery, validated backup/restore and monotonic reaction diagnostics; memory-budget probe prepared; actual 16 GB VM/audio/sleep/fleet gates open |
| 8. Distribution | Partial | Unsigned preview installer builds; install/reinstall/settings preservation/installed launch/uninstall passed on development host; complete licensed model payload, cross-version and external-egress installer qualification automated; clean Windows desktop VM and stable release gates remain open |

## Next priority

1. Keep safety regressions passing; exercise Windows build/installer and remote CI.
2. Finish frozen/installed verification of the complete voice payload, then calibrate
   microphone-qualified Klippy detection and room interruption with labeled human samples.
3. Validate on a microphone with labeled recordings (Klippy, Hey Klippy, Klipper, Clippy,
   silence, own TTS, interruptions). Do not claim transcript tests validate acoustics.
4. Supervised printer movement/heating/cancellation tests require the owner present.
5. Complete qualification, then publish stable v1.0 only when every release gate passes.

## 0.3 preview software work

Shared processing/playback follow-up sessions, streamed/cached TTS, post-playback confirmation
windows and deterministic natural temperature/progress queries address the owner usability report.
See PREVIEW3_REPORT.md and benchmarks/preview3-*.json for measured scope. Hardware calibration
does not block independent software work; it remains a separate acceptance gate.
