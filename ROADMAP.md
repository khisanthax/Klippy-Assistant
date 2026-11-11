# Roadmap

Each phase stays open until its exit gate is verified. Implementation is not acceptance.

| Phase | Status | Verified / remaining |
|---|---|---|
| 1. Foundation | Complete | Private repo pushed, runnable Qt application, storage, docs, 78 local tests; Windows CI green on application commit aa5b30c; phase milestone/issue closed |
| 2. Local voice and AI | Partial | Actual KWS/Whisper/VITS/Qwen candidate probes, bounded capture, owned offline llama process, schema+evidence validation; short Klippy wake failure, model rights review, acoustic qualification, speaker enrollment and hands-free interruption remain |
| 3. Connectivity | Partial | Manual approval, vault keys, LAN discovery, HTTP client, status polling, subscription adapter, read-only API validated on one real instance; full fleet/auth/subscription qualification pending |
| 4. Macro intelligence | Partial | Discovery, fingerprint/reapproval, conflicts, possible renames, aliases, review UI; semantic benchmark and rich differences pending |
| 5. Safe execution | Partial | Central engine, schemas, state checks, confirmations, uncertain outcomes, dedicated emergency endpoint; supervised hardware tests pending |
| 6. Companion/monitoring | Partial | Hidden tray launch, movable animated companion, auto-hide, active banner, schedule, fault alerts, read-only reconnect macro refresh; richer MMU-specific fault handling and desktop acceptance pending |
| 7. Stabilization | In progress | Simulated regressions and startup smoke testing; audio/CPU/sleep/real fleet gates pending |
| 8. Distribution | Partial | Unsigned preview installer builds; install/reinstall/settings preservation/installed launch/uninstall passed on development host; complete licensed model payload, clean VM/cross-version qualification and stable release pending |

## Next priority

1. Keep safety regressions passing; exercise Windows build/installer and remote CI.
2. Qualify model candidates and licenses; pin provenance and checksums, implement bundled
   microphone-qualified Klippy detection. Owned llama.cpp lifecycle and actual BPE keyword tokens are implemented.
3. Validate on a microphone with labeled recordings (Klippy, Hey Klippy, Klipper, Clippy,
   silence, own TTS, interruptions). Do not claim transcript tests validate acoustics.
4. Supervised printer movement/heating/cancellation tests require the owner present.
5. Complete qualification, then publish stable v1.0 only when every release gate passes.
