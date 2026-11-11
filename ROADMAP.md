# Roadmap

Each phase stays open until its exit gate is verified. Implementation is not acceptance.

| Phase | Status | Verified / remaining |
|---|---|---|
| 1. Foundation | In progress | Private repo created; runnable Qt application, storage, docs and tests implemented; CI/push pending |
| 2. Local voice and AI | Partial | Sherpa ONNX adapters, bounded capture, local llama.cpp structured HTTP adapter; missing qualified models, managed llama process, acoustic validation, speaker enrollment and hands-free interruption |
| 3. Connectivity | Partial | Manual approval, vault keys, LAN discovery, HTTP client, status polling, subscription adapter; real read-only qualification and reconnect workflow pending |
| 4. Macro intelligence | Partial | Discovery, fingerprint/reapproval, conflicts, possible renames, aliases, review UI; semantic benchmark and rich differences pending |
| 5. Safe execution | Partial | Central engine, schemas, state checks, confirmations, uncertain outcomes, dedicated emergency endpoint; supervised hardware tests pending |
| 6. Companion/monitoring | Partial | Hidden tray launch, movable companion, auto-hide, active banner, schedule, fault alerts; animation and MMU-specific fault handling pending |
| 7. Stabilization | In progress | Simulated regressions and startup smoke testing; audio/CPU/sleep/real fleet gates pending |
| 8. Distribution | In progress | Preview packaging being built; complete licensed model payload, clean VM install/upgrade/uninstall and stable release pending |

## Next priority

1. Keep safety regressions passing; exercise Windows build/installer and remote CI.
2. Qualify model candidates and licenses; pin provenance and checksums, implement bundled
   llama.cpp process lifecycle and actual keyword tokenization for Klippy.
3. Validate on a microphone with labeled recordings (Klippy, Hey Klippy, Klipper, Clippy,
   silence, own TTS, interruptions). Do not claim transcript tests validate acoustics.
4. Supervised printer movement/heating/cancellation tests require the owner present.
5. Complete qualification, then publish stable v1.0 only when every release gate passes.
