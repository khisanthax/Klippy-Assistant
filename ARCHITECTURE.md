# Architecture

Qt main thread owns widgets and tray. A dedicated asyncio worker owns network tasks;
speech processing uses a bounded capture queue and a separate worker. Failures in local
inference do not stop monitoring. All runtime services are local or enrolled LAN printers.

| Layer | Modules | Authority |
|---|---|---|
| Speech | voice, models, listening | Capture, local ONNX inference, spoken output; no printer writes |
| Interpretation | conversation, macros | Strict structured intents and clarification; no execution authority |
| Information | queries, query_catalog, query_format | Verified capabilities/freshness, 41 query types, 13 reviewed GET paths; no write authority |
| Policy | safety, domain | Enrollment, selected target, state, schema, approval, confirmation, dispatch |
| Transport | moonraker | Supported HTTP endpoints; no command retries or redirects |
| Monitoring | monitor | Status queries and deduplicated events only |
| Persistence | storage | SQLite preferences/configuration, OS vault secrets, bounded event codes |
| Presentation | app, presentation, printer_names | Management UI, tray, companion, validated factual speech and local name registry |

All write operations from the application flow through SafetyEngine. Proposed intents
are serialized before confirmation. Confirmation is single-use, uses the configured response
window (30 seconds by default, beginning after successful playback),
and binds action, parameters, selected enrollment, relevant live state and reviewed macro
policy. Cancellation/target changes during asynchronous validation invalidate in-flight
proposals using a generation counter. Requests already dispatched cannot be retracted.

Macro definitions are untrusted data. Every macro configuration snapshot is fingerprinted
conservatively; changes to any configuration section revoke approvals, including callers
whose helper macros or printer settings changed. Immediately before a macro write the
configuration and printer state are fetched again. Renames never transfer approval.
Any configuration snapshot change is also detected on reconnect and through a periodic
read-only refresh. Schema-valid model hallucinations face an additional explicit-action
evidence gate. Missing macro parameters can be supplied in a short, expiring follow-up
bound to the same printer and draft intent.

HTTP endpoints resolve to local/private IPs and connections pin the validated address.
Ambient HTTP proxies and redirects are disabled. Public endpoints and the common cloud
metadata address are rejected. HTTPS hostnames currently require a certificate valid for
the pinned IP; hostname-aware TLS/SNI is an outstanding compatibility improvement.

WebSocket subscription support exists in the transport but the UI currently polls every
five seconds. Full per-object/MMU fault subscriptions,
sleep/resume handling and full performance qualification remain open. Missing models leave
manual read-only commands and monitoring available. A failed model never grants write access.
LlamaRuntime owns a CPU-only child process with --offline, a random loopback port and
ephemeral API key. It checks local asset integrity before launch and terminates on exit.

Query presentation retains exact detailed text separately from deterministic speech.
Styles never call an LLM to rewrite facts. Missing and stale values remain unknown; important
status messages are retained. Pending safety prompts bypass conversational summaries and
keep exact values/tokens. Friendly speech replaces only known interpretation failures;
unknown safety and uncertain-outcome warnings remain intact. Printer-name editing, local
recognition testing and conversation selection share one word-boundary matcher; editing and
enrollment reject conflicting names/aliases before saving. Hardware actions still require
the policy layer; no name test or read-only query grants authority to dispatch a write.

Wake capture preserves the first candidate/token for an utterance. Bounded preroll drops
a preceding sentence after silence; final ASR prefix and own-echo verification still gate
session activation. Numeric in-memory counters separate microphone readiness/capture, drops,
KWS candidates, ASR starts/rejections and delivered input. They never retain user audio or
transcripts. Shared session holds preserve follow-ups during interpretation and playback.
