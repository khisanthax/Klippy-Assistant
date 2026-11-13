# 0.5 preview — conversational UX

Qualified engineering-preview scope at application source `60fac7845aab494680b889eb34819f1d9b72d8db`.
Human microphone accuracy, physical printer
acceptance, a clean Windows desktop VM and actual 16 GB hardware remain open. This is
not a stable release or a claim of universal first-attempt wake recognition.

The Printers page now exposes **Edit Names & Aliases**. Edit the primary name, add or
remove aliases one per line and test a phrase locally. Matching is case insensitive
with word boundaries. Duplicate names/aliases across printers are rejected before saving.
Edits persist and invalidate pending work. Recognition testing dispatches no printer action.

Deterministic selection supports switch to, change printers to, select my printer,
use the printer and go back to, plus active-printer questions. Unknown or ambiguous
targets ask for clarification. Selection updates the existing active target immediately;
the completed turn refreshes the combo/banner. Selection remains stored after restart.
Switching invalidates pending confirmations. Heater follow-ups such as “and the bed?”
reuse the information query and subject within the session, including across printers.

A deterministic presentation layer retains detailed UI values and supplies separate
speech. Homing, temperatures, targets, progress, status, position and layers get concise
phrasing. Brief is the default; Conversational and Detailed are available in Settings
and private backups. Temperatures round for ordinary speech; Detailed retains decimals.
Auxiliary sensors are spoken only when requested. Zero targets mean no active heating
target, never powered off. Missing or invalid data remains unknown and stale speech
explicitly refuses to claim current state. Safety prompts preserve exact wording,
values and capture-bound confirmation tokens. Known interpretation failures have friendly
spoken explanations; unknown safety and uncertain-outcome warnings remain intact.

Wake investigation found two software capture problems: repeated KWS candidates could
replace the beginning of an ongoing utterance, and the three-second preroll could include
an earlier sentence before the wake prefix. Capture now keeps the first candidate/token
and discards a prior sentence separated by at least 300 ms silence while retaining 100 ms
of lead-in. Newly loaded listening workers are enabled before starting, eliminating the
wait for the next UI tick. No threshold or phonetic-prefix protection was relaxed.
Candidates visibly show “Checking wake word”; verified input shows “Listening”; a wake-only
turn replies “I'm listening.” Follow-up capture shares the conversation session.

In-memory diagnostics count microphone frames, device readiness, dropped frames,
discontinuities, voiced frames, candidates, duplicate suppression, ASR starts, rejected
prefixes/echo, verified wakes and delivered inputs. Existing reaction timings remain.
No microphone audio, user transcript, private endpoint or credentials are recorded.
The native probe records preregistered single-attempt Hey Klippy wake-only and continuous
wake-plus-temperature cases with no retries. Failures remain visible alongside the older
continuous-speech and negative-word metrics. Engineering-preview gates remain separate
from full acoustic acceptance. Synthetic voices are not human microphone evidence.

The existing 41-query/13-GET catalog, verified capabilities, freshness, query-only model
fallback, reviewed macros and SafetyEngine write path remain. No physical printer was
connected or acted on for this work. The same licensed 57-file model pack remains outside
Git and is verified during packaging.

## Verified qualification

[Windows run 43408559522, attempt 1](https://github.com/khisanthax/Klippy-Assistant/actions/runs/43408559522)
passed every job at the exact source above. All prior 370 tests are retained: **408 passed,
zero failed/skipped**, plus Ruff. Local full suite also passed 408 tests. Qt visual QA used
isolated synthetic printer settings; no owner installation or physical printer was changed.

Frozen startup and the native engineering-preview probe passed. Fresh Windows CI verified
actual 0.4-to-0.5 upgrade, same-version reinstall, legacy SQLite preservation, names/aliases,
selected-printer and response-style persistence, installed startup, offline native models,
uninstall removing the executable and preserving settings. All firewall profiles were enabled;
application and owned language-runtime external egress were blocked during offline probes.

Each of the frozen, installed and memory-limited processes passed additional publication
checks: exactly one preregistered Hey wake-only attempt accepted one wake, opened a session
and yielded “I'm listening”; exactly one continuous Hey-plus-temperature attempt delivered
the complete temperature question; the subsequent unprefixed status question returned 63%.
No attempt was retried or substituted. All three passed seven native read-only query cases,
six negative audio inputs with no accepted requests/sessions, own-echo/interruption gates,
zero printer writes and no pending query action. Stage counts in the reports are cumulative
for each probe process, not per-case deltas.

**The original broader full-voice result was True / False / True** for frozen / installed /
memory-limited processes. The installed run missed the older continuous bare “Klippy, what
is the status …” case before ASR (no pipeline wake/transcript). That failure remains in
`benchmarks/preview5-release-installed.json`; no threshold, negative-input or full-voice gate
was weakened. Both new Hey cases passed there. Broad continuous/raw KWS and human accuracy
remain separate open acceptance gates. Earlier 0.4 failures also remain in the repository.
The initial e840b2a workflow was deliberately cancelled for the warning-preservation fix;
the final 60fac78 qualification passed on attempt 1.

On the 8 GiB Windows runner (AMD EPYC 7763), the app/process tree peaked at 1,953,746,944 bytes
commit (about 1.82 GiB), three processes and 144.065 seconds wall time under a 16 GiB job
commit budget. This is not qualification on an actual 16 GB computer or a clean desktop VM.
Frozen simulated common reads measured 0.282–9.519 ms; the unfamiliar local-model query
took 12.140 seconds. These exclude actual LAN and human microphone response time.

Installer: `Klippy-Setup-0.5.0-preview.1.exe`, **1,489,751,508 bytes** (about 1.39 GiB), unsigned.

SHA-256: `d9831b4da7cda4a6ee40ba1c57d190148716ed319c01387b16c56906997e98f7`.

Downloaded CI artifact, sidecar, installer-QA digest and local `dist` copy agree. Complete
self-contained evidence is `benchmarks/preview5-release-qualification.json`, with individual
frozen/installed/memory reports alongside it. The same per-user application identity upgrades
the existing installation while retaining settings and OS-vault credentials. GitHub repository
access/sign-in is needed to download from the private prerelease page.
