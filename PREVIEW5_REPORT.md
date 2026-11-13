# 0.5 preview — conversational UX

Engineering preview under qualification. Human microphone accuracy, physical printer
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
Git and is verified during packaging. Installer/CI results and artifact identity will be
recorded here after qualification; no installer is claimed qualified before those checks.
