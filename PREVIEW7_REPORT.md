# 0.7 engineering preview - local troubleshooting and conversation controls

Candidate pending exact-source Windows CI, frozen and installer qualification.
Unsigned engineering preview; hardware, acoustic, clean interactive VM and actual 16 GB
acceptance remain open. No physical printer actions are permitted by qualification.

## Optional local history

The new Diagnostics / History tab is OFF by default. Independent opt-ins control user/ASR
and normalized request text, Klippy response/spoken text and millisecond timings. Event-only
records remain useful with both text settings off. Retention defaults to seven days/1000
entries, configurable to 1-30 days and 1-10000 entries. A separate local SQLite WAL database
next to settings, conversation-history.sqlite, retains bounded records. Retention is applied
on reads/writes and periodically even when recording is disabled. No audio is accepted or
recorded, no cloud upload exists, and normal configuration export excludes this history.

Turns correlate by session and reaction ID. Records include input source, verified wake,
printer resolution, normalized request/intent/query, numeric parameters, clarification,
proposal/confirmation/cancellation/expiry/dispatch result, response and available existing
timing stages. Credential fields, confirmation tokens and endpoints are excluded; opted-in
text is redacted for labeled credentials, URLs/IPs and long token-like strings. Revoking a
text/timing opt-in removes those fields from retained entries. Clear checkpoints the WAL.
Storage failures expose a diagnostic and do not grant execution authority or retry actions.

The page offers printer/outcome/time filters, text search, selected-entry JSON details,
clear and selected/filtered/all JSON export. Exports can contain opted-in private text and
should be reviewed before sharing. Text redaction cannot identify every unlabeled secret
someone deliberately speaks; keep text disabled when discussing sensitive information.
ASR text is the recognizer's output, not independent ground truth about what was spoken.
Timings combine stage durations and monotonic marks relative to speech end; wake marks can
precede zero. Missing stages are omitted rather than invented. Logs are local, unencrypted
under the user's Windows profile; OS permissions/backups are outside the app's erasure scope.

## Shared-session countdown

Settings > Voice Orb > Show follow-up countdown ring defaults on. A red inner arc uses the
existing Session remaining fraction, distinct from the outer state glow. It appears only
after successful playback and DAC/echo tail completion, with an enabled/ready microphone
and an active, unheld follow-up window. Capture, processing, TTS, verification, mute and
expiry hide it; successful exchanges reset the configured window. Reduced-motion mode still
updates the informational arc. A zero-second follow-up setting disables the window/ring.
Mute clears authorization; unmute cannot restore the previous session. No second countdown
timer or microphone stream is created. Confirmation and follow-up deadlines stay independent.

## Orb-anchored clarification

Two to six matching approved/reviewed macros open a non-activating popup above the orb.
It lists real friendly/technical identities, descriptions, printer and conservative
state-changing/mandatory-confirmation classification. Radio choices, Continue, Cancel,
keyboard navigation and active-session voice ordinal/exact-name selection resolve identity.
Missing required reviewed macro parameters use bounded-value fields and the same validation
path. More than six alternatives request narrower wording. Unique built-in operations and
single matching macros retain their deterministic path; arbitrary native G-code is not added.

Continue only proposes an intent through SafetyEngine. It never confirms or dispatches it.
Definition/dependency/schema/approval/alias changes, printer/session changes, cancellation,
expiry or unrelated requests invalidate prior context. Live config is re-read at resolution.
The default-off Remember checkbox stores per-printer normalized-request signatures and macro
identity/registry fingerprints, never confirmation tokens or authority. Reuse rechecks live
configuration and always retains mandatory macro confirmation. Remembered choices has a
separate review/delete tab. It shows request signatures instead of persisting spoken phrases.
Any registry change conservatively invalidates a remembered choice. Existing macro review
and enrollment, exact parameter review and single-use confirmation remain mandatory.

Popup geometry tracks orb movement/size and native taskbar-safe monitor work area. The
window does not activate on appearance; clicking allows normal keyboard navigation. Full
multi-monitor/DPI/auto-hide/focus acceptance remains open until checked interactively.

## Qualification

The original 610 tests and offline voice/audio safety gates remain required. New regressions
exercise consent, retention/export/corruption, late-ASR mute privacy, actual playback-tail
countdown timing, clarification identity/parameters, remembered-choice invalidation, mouse
and voice selection, stale/canceled contexts and taskbar-safe geometry. The actual Qt orb
self-test additionally runs temporary-history, popup and ring checks with a write-rejecting
Moonraker simulator, saving synthetic-only screenshots. Native frozen and installed results
must pass before publication; numerical simulation does not close human/hardware gates.

## Conversational personality and grounded explanations

Owner reports audio quality satisfactory for now. No resampler, TTS model, buffering or
playback-quality algorithm changes are prioritized in this preview. Changes in voice.py are
history instrumentation and the existing shared session's response-ready signal only.

Settings adds Friendly/Calm/Direct personality and Short/Standard/Detailed response length,
with validated backup/restore and migration from the prior response-style setting. Routine
printer information uses fast verified-fact templates with no model call. Greetings, thanks,
basic small talk and general homing/temperature/progress explanations do not require a
selected printer. Read-only context supports and the bed, actually the nozzle, why is that,
explain that and tell me more. Expired/unvalidated voice input still needs a wake word.
Acknowledgments never confirm actions; pending reviews require restatement if clarified.

For complex information questions, the local LLM selects the structure and wording from a
closed bank containing the complete verified observation and vetted explanatory clauses.
Only verified read capabilities and those clauses are supplied as printer context. The
schema cannot add prose, numbers, printer states, actions or tool calls; the complete
observation is mandatory. This is model-composed grounded explanation, not unrestricted
model prose. Supported explanatory topics are bounded; an unreported cause stays unknown.
Safety reviews never enter the composer and retain their exact existing text/policies.
Routine responses bypass it. Model failure/invalid output falls back to factual templates
within a four-second composition budget. Information aging during composition gets an
explicit earlier-observation label; generation/target checks discard superseded replies.

Actual bundled-model local probe: routine simulated nozzle answer 7.44 ms without a model
call; one accepted explanation 3530.21 ms; all multi-turn/fact/safety checks passed. This is
text-response latency on a loaded development host, excluding ASR, TTS and device playback.
Existing reaction diagnostics retain those other stages separately when opted in. Native
frozen/installed/memory qualification now additionally requires actual model composition,
verified observation retention, no routine model call, casual conversation without a printer,
zero writes/pending actions and bounded explanation latency. All original gates remain.

Local pre-package validation: 689 passed (prior 610 preserved), Ruff clean; native Qt 29
orb checks plus 19 conversation-feature checks passed. Mute revokes capture before storage
I/O; lifecycle observers are queued and drained outside capture locks. Log failures cannot
prevent session closure or cancellation. Executed in history means dispatch accepted by
Moonraker, never proof of physical completion. Windows package qualification remains pending.

Event-only records include the reviewed macro command identity after validation. Initial
f94fcfe candidate was superseded before publication to complete that no-text diagnostic
requirement; original persistence regression retained and one macro-metadata case added.

Final metadata candidate: 690 local tests passed, Ruff clean; full native Windows and
installer qualification follow. A transient Windows socket-buffer setup error was retained
in LOGBOOK.md; the unchanged full rerun passed without relaxed criteria.

## Frozen dialogue correction

Source 04ddb7e's frozen gate rejected template fallback at 3524.97 ms, despite all prior
engineering gates and desktop controls passing. No preview was published. Exact failure
reason was not captured in that candidate; it is now a controlled timeout/HTTP/schema code.
The model now returns a single index into vetted reply plans, preserving the complete fact
and excluding action authority or new prose. This reduced a local packet from 32 output
tokens/3322.56 ms to 7/1831.87 ms; routine response 6.09 ms. These are single-run text timings,
not an ASR/TTS/acoustic performance claim. Four-second fallback and mandatory actual-model
qualification remain unchanged. Tests cover malformed plan indices and failure diagnostics.

Indexed-plan candidate: 697 local tests passed, Ruff clean. Qt keyboard Escape and Space
Continue are covered alongside mouse/voice selections. All previous 690 cases remain.
