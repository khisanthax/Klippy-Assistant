# Architecture

Qt main thread owns widgets and tray. A dedicated asyncio worker owns network tasks;
speech processing uses a bounded capture queue and a separate worker. Failures in local
inference do not stop monitoring. All runtime services are local or enrolled LAN printers.

| Layer | Modules | Authority |
|---|---|---|
| Speech | voice, models, listening | Capture, local ONNX inference, spoken output; no printer writes |
| Interpretation | conversation, macros | Strict structured intents and clarification; no execution authority |
| Policy | safety, domain | Enrollment, selected target, state, schema, approval, confirmation, dispatch |
| Transport | moonraker | Supported HTTP endpoints; no command retries or redirects |
| Monitoring | monitor | Status queries and deduplicated events only |
| Persistence | storage | SQLite preferences/configuration, OS vault secrets, bounded event codes |
| Presentation | app | Management UI, tray, movable auto-hiding companion |

All write operations from the application flow through SafetyEngine. Proposed intents
are serialized before confirmation. Confirmation is single-use, expires after 25 seconds,
and binds action, parameters, selected enrollment, relevant live state and reviewed macro
policy. Cancellation/target changes during asynchronous validation invalidate in-flight
proposals using a generation counter. Requests already dispatched cannot be retracted.

Macro definitions are untrusted data. Every macro configuration snapshot is fingerprinted
conservatively; changes to any configuration section revoke approvals, including callers
whose helper macros or printer settings changed. Immediately before a macro write the
configuration and printer state are fetched again. Renames never transfer approval.

HTTP endpoints resolve to local/private IPs and connections pin the validated address.
Ambient HTTP proxies and redirects are disabled. Public endpoints and the common cloud
metadata address are rejected. HTTPS hostnames currently require a certificate valid for
the pinned IP; hostname-aware TLS/SNI is an outstanding compatibility improvement.

WebSocket subscription support exists in the transport but the UI currently polls every
five seconds. Full per-object/MMU fault subscriptions, reconnect-triggered macro refresh,
sleep/resume handling and performance qualification remain open. Missing models leave
manual read-only commands and monitoring available. A failed model never grants write access.
