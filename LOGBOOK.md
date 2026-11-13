# Logbook

## 2026-11-13 — Qualified 0.5.1 heating/cancellation hotfix

Exact source 2eabdfaee0bf0f189f18e5719714b0cbaec2ae63 passed every job in Windows run
43461231046 attempt 1: 510 tests (all prior 408 retained), zero failed/skipped, Ruff,
frozen startup/native probes, actual 0.5.0 upgrade/reinstall, legacy SQLite/name/alias/
selected-target/style preservation, installed startup, offline models, process-tree budget
and uninstall preserving data. All firewall profiles enabled; external app/runtime egress blocked.

Every frozen/installed/budgeted process passed all 21 heating/cancellation cases with zero
HTTP writes, supported-request LLM calls or pending action. Seven query cases, six negative
audio inputs, own echo/interruption, both single-attempt Hey cases and acknowledgement/
unprefixed follow-up also passed. Original broader voice flags remain True/False/True:
installed ASR returned Clibby for the older bare-Klippy continuous status case; strict prefix
verification rejected it. Failure retained in preview51-release-installed.json and aggregate.
No acoustic gate, threshold or phonetic-prefix rule was weakened. Earlier code builds were
cancelled for unit/name correctness, not retried for passing audio. Initial failures retained.

Installer: Klippy-Setup-0.5.1-preview.1.exe, 1,489,751,540 bytes, SHA-256
c3b87742262793490f24511103db577d019fa8353043e3b1a756f636b460424f.
CI/sidecar/installed-QA/local copy agree. Peak process-tree commit 1,958,084,608 bytes, three
processes, wall 164.913 seconds on an 8 GiB Intel Xeon 8370C runner under a 16 GiB commit
budget; not actual 16 GB hardware or clean desktop VM qualification. Complete evidence in
benchmarks/preview51-release-qualification.json. No physical connections/heating, owner
recordings or owner installation changes; models unchanged/outside Git.

Next: tag exact qualified source, verify every uploaded asset size/digest and publish the
accurately labeled unsigned prerelease. Retain human microphone/room, actual fleet/accessory,
clean VM/actual 16 GB, sleep/resume and supervised consequential acceptance gates as open.

## 2026-11-13 — Contextual name proof finalized, 510 tests passed

Refined the operand fix into syntax-proven name spans. Complete heating requests retain
the current selection; command words/operands cannot be inferred as names. A genuine name
must occur before the heater or after on/for, and removing that exact span must leave a
complete heating request or a header missing its target. Nozzle One remains usable in
switching/queries/named heating; unknown unit K cannot become a configured K printer and
silently default to Celsius. No placeholder temperature is used for execution.

Final local full suite: 510 passed, all prior 408 retained; Ruff passed. Native command probe
still requires all 21 cases with zero writes/LLM calls/pending actions. Cancelled intermediate
20bc35c run 43458654066 for this final name-context correction, before publication. Exact
corrected source will be qualified afresh; no acoustic result was retried or hidden.

## 2026-11-13 — Final unit/name collision safety review

Before publication, reproduced a configured F alias matching the unit in “heat nozzle to
90 F”; name removal then left “heat nozzle to 90”, silently changing units and target
selection. Evidence: benchmarks/preview51-unit-alias-reproduction.json. No network/writes.
Heater/value/unit operands are now masked for name matching, with original spans retained
so only genuine name mentions are removed. Added regressions for F, C, Celsius, numeric and
nozzle aliases and explicit “90 F on F” preserving both the selected printer and conversion.
The packaged command probe now has 21 cases, including the unit/name collision.

Cancelled the 0588ed8 qualification run 43454620523 for this correction after its 497 tests
and frozen 20-case probe passed. No attempt was selected for passing acoustic results.
Final corrected full suite: 503 passed, all prior 408 retained; Ruff passed. The corrected
application will be committed and qualified again before publication, including all 21
packaged command cases. Earlier unqualified installer copies are discarded after checksum
verification so they cannot be confused with the final distribution.

## 2026-11-13 — Reproduced owner heating/cancellation failures; 0.5.1 implementation

Started from clean latest main 8e2b211. Reproduced the exact owner phrase with Mercury One/M1
configured: Mercury 1 was not resolved, deterministic intent returned None, and an injected
model TEMPERATURES intent with heater/temperature parameters reproduced “Unexpected parameters”.
This is the actual failing guard/path under simulation; the owner's actual model JSON is
unknown, not recovered. The ordinary “I'm not sure why it didn't understand” remark also
reproduced “Pending action canceled” and removed the pending review. Zero simulated writes.
Initial evidence is benchmarks/preview51-initial-reproduction.json.

Implemented deterministic normalized heating with configured name/alias matching, number
words, possessives/punctuation, hotend synonyms, polite wording, Celsius default and explicit
Fahrenheit conversion. Ambiguous/incomplete actions cannot fall through to query/model paths.
Converted targets pass fresh selected-printer/heater/state/reviewed-limit checks and existing
confirmation policy; Celsius values are reviewed, and no transmission is automatically retried.
Wrong model action/parameter combinations reject with helpful speech and separate safe codes
in bounded diagnostics. The owner phrase now becomes HEAT(heater=0, temperature=90) without LLM.

Replaced generic-not cancellation with explicit cancellation matching. Uncertain remarks ask
clarification and retain an existing review suspended, preventing old prompt completion or
confirmation from executing it until a complete fresh request is given. Added safety races,
unit boundaries, invalid model/limits/heater regressions and a write-forbidden 20-case packaged
command probe. First full run: 489 passed. Expanded run found a new UI diagnostic test looking
at the speech reaction instead of the rejected request; diagnostics now identify the latest
error's reaction even after feedback speech, and the regression verifies that association.
Final full suite: 497 passed, all prior 408 retained, Ruff passed. The final 97-test targeted
heating/UI run also passed before the two additional non-heating-set regressions. The
20-case command probe passed with zero writes, supported-request LLM calls or pending action.
Exact frozen/installer qualification is next. See PREVIEW51_REPORT.md.

No physical printer connection/action, owner recording or owner installation change. Models
unchanged/outside Git. Human wake/room, clean VM/actual 16 GB, actual fleet/accessory and
supervised consequential acceptance stay open. Do not infer hardware acceptance from mocks.

## 2026-11-13 — Published v0.5.0-preview.1

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.5.0-preview.1
at annotated exact-source tag 60fac7845aab494680b889eb34819f1d9b72d8db after all jobs in
43408559522 attempt 1 passed. Seven uploaded assets were checked individually against
local size/SHA-256 before publication. GitHub installer digest agrees with CI/sidecar/QA:
d9831b4da7cda4a6ee40ba1c57d190148716ed319c01387b16c56906997e98f7.
Release is published, prerelease=true, unsigned and not latest/stable. README/roadmap and
relevant GitHub issues point to the qualified preview; full reports retain the installed
bare-Klippy continuous activation miss and True/False/True original full-voice results.
Both new single-attempt Hey cases and the engineering envelope passed all three processes.

Next: preserve 408 regressions and use in-memory stage counters to diagnose owner microphone
first-attempt reports. Keep broader semantic/fleet/accessory, human room/interruption,
sleep/resume, clean desktop VM/actual 16 GB and supervised consequential acceptance open.
Do not claim these were satisfied by CI or synthetic audio. No physical printer connection
or action, owner microphone recording or owner installation change was performed.

## 2026-11-13 — Qualified 0.5 conversational UX preview

Exact application source 60fac7845aab494680b889eb34819f1d9b72d8db passed every job in
Windows run 43408559522 attempt 1. 408 tests passed (all prior 370 retained), zero skipped
or failed, plus Ruff. Local full run: 408 passed. Frozen startup/native probe, actual
0.4 upgrade/reinstall, legacy SQLite and name/alias/selected-target/style preservation,
installed startup, offline native inference, process-tree budget and uninstall preserving
settings passed. All firewall profiles enabled; external app/runtime egress blocked.

Both new single-attempt Hey wake-only and Hey-plus-temperature cases passed in all three
frozen/installed/budgeted processes. Wake acknowledgement and unprefixed follow-up passed;
7 native queries, 6 negative composite inputs, zero writes/pending query action, own echo
and interruption passed. Original full-voice flags remain True/False/True: the installed
probe missed the older bare-Klippy continuous status case before ASR. Failure retained in
preview5-release-installed.json and the aggregate; broad/human wake acceptance remains open.
The earlier e840b2a workflow was cancelled for the status-warning fix, not retried for a
passing voice sample. Stage counts are cumulative; synthetic audio is not microphone proof.

Installer: Klippy-Setup-0.5.0-preview.1.exe, 1,489,751,508 bytes; SHA-256
d9831b4da7cda4a6ee40ba1c57d190148716ed319c01387b16c56906997e98f7.
CI artifact/sidecar/installed-QA digest/local dist copy agree. Peak process-tree commit
1,953,746,944 bytes on an 8 GiB runner under a 16 GiB commit limit; wall 144.065 seconds.
Actual 16 GB hardware and clean desktop VM gates remain open. No real printer connections,
owner microphone recording or owner installation changes. Models unchanged and outside Git.

Next: publish the accurately scoped unsigned prerelease at the qualified source tag after
checking uploaded asset sizes/digests. Then retain the open human microphone/room, sleep,
actual fleet/accessory, clean VM/16 GB and supervised consequential acceptance gates.

## 2026-11-13 — Conversational UX implementation, qualification in progress

Read the latest owner attachment and continuity docs; started from clean current main
2f74fca. Implemented visible name/alias editing with local recognition tests and conflict
validation, deterministic natural printer switching/active-target questions, heater-subject
follow-ups, deterministic speech presentation/styles, friendly known query failures and
specific incomplete-heater clarifications. Exact detailed values, safety prompts and
uncertain-outcome warnings remain intact. No application write authority was added.

Fixed duplicate wake candidates resetting the first capture, preceding-sentence preroll,
and the post-model-load wait for the next listening tick. Threshold/prefix/echo protection
unchanged. Added bounded numeric stage diagnostics and single-attempt native Hey probes.
Regression tests cover names/conflicts/persistence, selections, pending invalidation,
multi-turn subject/printer context, stale speech, styles, safety prompts and capture defects.
Final full suite passed 407 tests (all original 370 retained), with Ruff passing; the
41-test targeted UX/UI run also passed. Frozen/installer qualification is next.
Native source probe delay was traced to hashlib.file_digest during model verification,
before inference. Do not infer voice qualification from process launch.

Post-review: concise ready-state speech must retain unexpected Klipper state messages,
even if the state is ready. Added the warning-preservation regression before release;
exact-source CI is restarted for this final presentation correction.

No real printer connections/actions, owner microphone recording or owner installer changes.
Models remain unchanged/outside Git. First-attempt human wake, clean desktop VM, actual
16 GB hardware, real fleet and supervised consequential acceptance gates stay open.

## 2026-11-12 — Published v0.4.0-preview.1 query engineering preview

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.4.0-preview.1 at exact qualified application source 643b949.
Annotated source tag verified; all seven assets uploaded before publication and each GitHub
digest/size checked against the local files. Installer digest matches CI, sidecar and local
distribution: 5e3d9d8d4221620772df89ee38eb8495b770a35e9cb70efa5b003ed6d3caafac.
Release is published, prerelease=true, unsigned and not latest/stable. Includes installer,
checksum, report, official API inventory, catalog JSON, model manifest and complete evidence.
Issue #9 and phase issues updated; all hardware/room/VM/16 GB/soak gates remain open.
The budgeted process's original continuous-wake full-voice result remains false in evidence;
publication qualifies only the explicit supported query engineering-preview envelope.
No physical printer connection/action, microphone recording or owner installation change.

Next: actual approved-fleet read-only/authentication/accessory validation; broader unfamiliar
query semantic benchmarks; remaining catalog extensions and raw/continuous wake calibration.
Obtain a clean desktop VM/actual 16 GB host separately. Consequential physical-printer
acceptance requires supervised authorization. Preserve 370 regressions and original 179 cases.

## 2026-11-12 — Exact 0.4 preview qualification

Source 643b9493f3bd3c67009657b2b01376f67fdc0233, CI run 43260616461 attempt 1 passed every required job.
370 tests/Ruff, frozen and both installed native voice/query probes, actual 0.3 upgrade,
reinstall/legacy SQLite preservation, offline runtime, memory accounting and uninstall
preserving data passed. All firewall profiles enabled; app/runtime external egress blocked.
Every engineering-preview probe passed seven query cases, actual Hey-wake/follow-up ASR-to-catalog status, zero accepted negative inputs, zero writes and no pending query action. Full voice metrics remain separate.
Installer Klippy-Setup-0.4.0-preview.1.exe: 1,489,696,655 bytes.
SHA-256: 5e3d9d8d4221620772df89ee38eb8495b770a35e9cb70efa5b003ed6d3caafac.
CI report, downloaded artifact, sidecar and local distribution copy agree.

Earlier e775c64 frozen/installed attempts failed quiet whole-utterance wake capture; all new
query cases passed. The original report is retained in benchmarks/preview4-frozen-attempt1-failure.json.
Current source passed the explicit engineering-preview envelope in all three processes.
Original full-voice results (frozen/installed/memory): True, True, False.
Original full-voice gates/results remain intact. Production voice thresholds/models/capture/
interruption are unchanged; full acoustic acceptance remains open. The initial local-model semantic-category failure is also retained.

Peak commit 1,953,230,848 bytes / 3 active processes;
155.854 s wall / 249.719 s CPU; host RAM 8,584,425,472 bytes.
This process cap is not actual 16 GB or clean desktop VM acceptance. Evidence is committed
under benchmarks/preview4-release-*.json and summarized in PREVIEW4_REPORT.md. No physical
printer connections/actions, owner installation changes or microphone recordings used.
Next: publish only this exact qualified artifact, retaining all documented limitations.

## 2026-11-12 — Read-only local-model budget and failure diagnostics

Candidate b3a04b9 passed all 368 Windows tests but its frozen unfamiliar-query model call
rejected without distinguishing timeout, malformed output or ambiguity. Trace retained in
benchmarks/preview4-frozen-query-rejection.txt. Prior CI query inference samples took
10–17 seconds against a 20-second request timeout. Increased only the read-only query
budget to 45 seconds; action interpretation remains at 20 seconds and no write retry/policy
changed. Rejections now carry a safe exception-class/status diagnostic without endpoint,
headers, response content or utterance. The native query probe retains all seven case
results and error codes instead of replacing the entire report with a traceback.

Added timeout-redaction and retained-failure-report regressions. Full suite is now 370
cases including original 179 unchanged; Ruff passes. No further app feature changes planned:
qualify exact corrected source, archive preview/full-voice results separately, publish an
accurately labeled query engineering preview. Human acoustics and all physical/clean VM/
actual 16 GB acceptance gates stay open. No physical printer connection/action used.

## 2026-11-12 — Separated query-preview qualification from open acoustic gates

Installed e775c64 reproduced the frozen quiet continuous wake-capture miss; seven native
query cases passed in every process. Did not keep rerunning. Retained both original failed
reports, plus a local raw negative-word KWS candidate diagnostic. Bare Klippy can also be
transcribed as Clipping and is deliberately rejected; no unsafe fuzzy prefix was added.
Production voice thresholds/models/live capture, ASR and interruption remain unchanged.

Added explicit --preview-self-test engineering envelope: separately spoken Hey Klippy,
acknowledgement, then actual captured ASR through the new catalog to a 63% simulated status;
all seven native query cases; six negative PCM inputs opening zero sessions/requests;
standalone KWS, own-echo, interruption and zero-write checks. Each input is tested once.
Original --voice-self-test/full passed/raw metrics remain intact, can fail, and are not
claimed as full acoustic acceptance. CLI modes are mutually exclusive. Stable build guard
and physical/acoustic acceptance checklist stay open. This implements the requested software
preview independently of human microphone calibration without relabeling full-voice failure.

Added regression checks for every required preview gate and for preserving false full-voice
results. Restored progress in the catalog's general status answer; native ASR status now
uses the actual new QueryService instead of the compatibility snapshot route. 368 tests
and Ruff pass; original 179 tests unchanged. Local composite and explicit Hey-Klippy two-turn native probes passed (full and preview
results both true in that final development run); no accepted negative requests/sessions.
Source e775c64 / f1449de... installer is superseded; rebuild and qualify this exact mode.
No physical printer connections/actions, owner installation changes or microphone recordings.

## 2026-11-12 — Moonraker read-only query catalog implementation

Resumed latest main (44c8a8a); reviewed official current Moonraker printer/server/history,
file/metadata, host, accessory and queue APIs plus Klipper's current status reference.
Implemented 41 built-in query types and 13 individually allowlisted GET paths. Discovery
records actual objects/fields/components per printer; optional features are never guessed.
Homing reads toolhead.homed_axes only. Query-only interpretation has no action/G-code/path
schema and never invokes the safety engine. Existing command behavior and Phase 2 remain.

Added named/aliased printer and subject follow-ups, capability refresh/invalidation,
field-scoped two-second cache reuse, stale labels/age, runtime clock reset handling,
unknown/malformed data handling and searchable read/action/macro manager with voice status.
No owner data, microphone or physical printer connection/actions used. All simulated
transports reject writes. API research inventory and exclusions: docs/MOONRAKER_QUERIES.md.

355 tests and Ruff pass (original 179 preserved). Local real-model query probe initially
selected numeric position for an established-reference question. Retained that failed
result; clarified conceptual homing vs numeric-position definitions in the inventory and
query prompt. Corrected native probe passed seven cases, including the unfamiliar local
LLM selection, zero writes and no pending action. Common simulated reads took 0.3–9 ms;
unfamiliar local-model query about 6 s. These are not LAN/acoustic latency measurements.

Found and fixed a delayed-response cache race before publication: endpoint edits or
discovery invalidation now reject old in-flight reads before they can mutate a new
registry/cache generation. Added a delayed-old-endpoint regression, including the monitor
snapshot observer. Canceled candidate run 43248180304; source 8ba42ab is superseded.
356 tests and Ruff pass on the correction.

Preparing 0.4.0-preview.1 qualification with unchanged license-reviewed model payload.
Frozen/installed voice self-tests now include the native query probe; cross-version test
will upgrade 0.3 to 0.4. Next: qualify exact source, archive installed/offline/memory evidence,
update issues and publish only the qualified engineering preview. Hardware, human acoustics,
actual 16 GB host, clean desktop VM and extended soak remain open.

## 2026-11-11 — Published v0.3.0-preview.1

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.3.0-preview.1 at qualified application source 69e5bf7. The SSH-created annotated tag
resolves to the exact CI build source. All five assets uploaded before publication; GitHub's
installer digest equals a711e0744d7f089eab1747c6a41c191b1c9fc3fd6ec06abdcf6267609ad00442.
Release is published, prerelease=true, unsigned, not marked latest/stable. Assets include
installer/checksum, final report, model manifest and self-contained qualification JSON.
The documentation/evidence commit 77fe629 also passed Windows CI; source-tag CI passed.
GitHub issues 2–8 updated with software progress, passed qualification and still-open gates.
Working distribution installer matches the release; no owner installation was changed.

Next: extended semantic macro cases, fleet authentication/subscription/reconnect qualification
and remaining event-history/animation review using simulated services. Obtain a clean desktop
VM/actual 16 GB host separately. Microphone and all consequential physical-printer acceptance
remain separate supervised work; no hardware gate was closed by synthetic evidence.

## 2026-11-11 — Exact 0.3 preview artifact qualified

Windows CI run 43136945820 passed test/build/installer-qualification on source 69e5bf70fef73159606273498790ae1b15a5f2c7.
All 179 tests and Ruff pass; original 99 cases remain unchanged. Frozen and both installed
real-model synthetic probes passed all mandatory gates and reported zero printer writes.
Actual 0.2→0.3 upgrade, same-version reinstall, legacy SQLite fixtures, installed startup
and uninstall preserving data passed on a fresh Windows runner with app/runtime external
egress blocked and Domain/Private/Public firewall profiles enabled.

Exact installer: Klippy-Setup-0.3.0-preview.1.exe, 1,489,710,686 bytes.
SHA-256: a711e0744d7f089eab1747c6a41c191b1c9fc3fd6ec06abdcf6267609ad00442.
Downloaded artifact and distribution copy were independently hashed and match the CI
installer report. Source, installed, memory and complete qualification JSON are committed
under benchmarks/preview3-release-*.json; PREVIEW3_REPORT.md records scope and limitations.

Memory result: Windows 10.0.26100, AMD EPYC 7763, 8,584,425,472 host RAM bytes;
16 GiB inherited job commit cap, peak commit 1,922,932,736 bytes, three active processes,
114.380 s wall / 181.016 s CPU. This is not actual 16 GB total-RAM or clean desktop VM
qualification. Human acoustics, physical fleet/accessories, supervised actuation,
clean desktop/no-development-tools, idle CPU and extended device/sleep/soak gates stay open.
GitHub Phase 2–7 issue bodies now distinguish implemented work from remaining acceptance.
No physical printer connection/action, recordings, private configuration or credentials used.

Next: publish this exact artifact as v0.3.0-preview.1, then record its verified release assets.
Continue extended semantic/authentication/subscription software qualification independently
of human microphone and separately supervised hardware acceptance.

## 2026-11-11 — Exact action review and numeric safety

Before publishing confirmation opt-outs, closed additional review gaps: prompts now name
all-axes homing, heater/temperature, macro and every supplied numeric value. Model-interpreted
writes always require explicit review even when an operational prompt is disabled; explicit
supported heat syntax is parsed deterministically and still checked against reviewed limits.
Bare cancel is a dialogue/request cancellation; cancel print explicitly addresses a print job.

Replaced six-significant-digit G-code formatting, which could change an already-validated
value or emit exponent syntax, with exact fixed-decimal round-trip serialization. Macro
parameter bounds must be finite and ordered. Reviews beyond the complete speech budget
are rejected before a token is created. Added regressions for precision/ranges, heater and
macro echoes, forced model review, explicit heat opt-outs, oversized reviews and cancel
ambiguity. Original 99 tests unchanged; all 179 tests and Ruff passed. All writes simulated.

Run 43132829101 passed the previous source's complete build and combined offline upgrade,
installed-model and memory checks. Its artifact is superseded by these safety corrections.
Next: build/qualify this exact source once, record its artifact identity and publish the preview.
No physical printer connections, commands, recordings or personal transcripts were involved.

## 2026-11-11 — Confirmation overlap and composite model qualification

Corrected-source run 43126897339 passed its 156 tests, complete-model build and stricter
frozen ASR→status/interruption check at wake threshold .22. Its basic installed run missed
one raw KWS-only embedded stop-talking sample, although actual verified interruption and
status both passed. Independent qualification 43128863165 passed upgrade/reinstall/legacy
fixtures/offline installed startup and models plus 16 GiB job-budget testing on the exact
7a4fa54192840faab6e29cc773b1e139c6d2c2f21730d69f086093f62065c6c9 artifact.
Firewall profiles Domain/Private/Public were enabled and app/runtime external egress blocked.
Host RAM: 8,584,425,472 bytes; peak job commit 1,922,396,160 bytes; wall 108.493 s; CPU 173.422 s.
This is an 8 GB CI host with a commit cap, not clean Windows desktop/16 GB acceptance.

The original failed embedded-phrase report is preserved. Qualification now explicitly gates
standalone wake, negative words, actual ASR→status, no self-echo wakes/requests, actual verified
interruption, local LLM and zero writes. Embedded KWS-only recall is reported separately;
the existing ASR fallback is the second interruption path. This does not close acoustic gates.
Tests independently break every mandatory gate to prevent a false pass.

Found and fixed one remaining confirmation-overlap issue before publication: non-turn
speech could consume the response window. Faults stay visible but speech is suppressed
while pending; reaction probes cannot overlap, and new commands/cancel interrupt stale PCM.
167 tests and Ruff pass, original 99 unchanged. The previous artifact is superseded by these
UI/qualification corrections. Next: build and qualify that exact source, then publish.

Release API creation at a non-head workflow-changing commit lacked workflow scope. No
credentials/scopes were changed and no draft was created; after qualification, create the
source tag through the already-authorized SSH remote and release that existing tag.

## 2026-11-11 — Reproduced installed wake qualification failure

The initial installed pilot failed the real-model gate, reproducing the earlier CI failure
signal. Its recorded report showed a raw KWS false hit on synthetic "clipper" (voice 3)
and an empty pipeline transcript because Whisper spelled the wake name "Clip E.".
This was not hidden by an installer pass: publication remains on hold. Failed/passing
numeric evidence is retained in benchmarks/preview3-*.json. The isolated pilot installation
was uninstalled only after verifying its registry InstallLocation matched local/installer-qa.

Paired threshold sweep: 30 fresh synthetic utterances (two voices, three repeats). At .15:
12/12 positives, 2/18 false positives; at .25: 12/12 and 0/18; at .35: 11/12 and 0/18.
An initial .25 candidate missed a whole request after model warm-up; defaults are now .22,
preserving explicit preferences. A second 42-utterance paired sweep at .22 passed 24/24
positives and 0/18 negatives, and the stricter source real-model pipeline passed. Exact "Clip E" ASR segmentation is
recognized; Clipper/Klipper/bare Clip remain rejected by the prefix parser. Strengthened the
real-model gate to require actual ASR input → deterministic intent → simulated printer
status, and added Klipper as a negative sample. Original 99 tests unchanged; 156 tests and
Ruff passed. Keyword candidates now interrupt audio without opening a follow-up session
until ASR accepts the exact prefix; rejection cannot extend the session. Unsolicited
notifications cannot open a voice session; shutdown clears queued holds, and late ASR
activation is serialized against interruption. Each has a regression. Hardware acoustics remain open.

Added reusable qualification-only CI workflow and legacy printer/macro fixture preservation
checks so packaging retries can reuse an exact build. Prior-revision CI run 43122001818 passed build, installed offline model checks and a real
0.2→0.3 upgrade on a fresh 8 GB Windows runner, with external app/runtime egress blocked.
That artifact is superseded by the corrected wake/session settings and is not for release.
Next: frozen/installed qualification on the corrected setting, then publish only its artifact.

## 2026-11-11 — 0.3 software expansion and usability corrections

Resumed latest main from 0.2.0-preview.1 without physical printer connections/actions.
Original TTS measurements reproduced 8.3 s temperature and 11.6 s confirmation delays before
any PCM. Streaming callbacks reduced first PCM to 1.935/2.051 s; repeated responses use an
in-memory bounded cache. Shared session holds cover ASR/interpretation/playback; a specific
prompt delivery arms its exact confirmation after output drain/tail, with total lifetime bound.
Natural temperature/progress requests take the deterministic read-only path.

Expanded phases 3–8 software: bounded fleet polling and Happy Hare notifications; functional
macro warnings/rename diffs/synonyms/explicit numeric parameters; configurable operational
confirmations with fresh mandatory validation; scrollable settings and companion preferences;
validated backups with pre-restore SQLite online backup, revoked approvals and mic-off recovery.
Added explicit per-printer verified heater-limit review in Settings and rejection of method-style
dynamic parameter access, including whitespace variants. All execution tests remain simulated.
Original 99 tests remain unchanged; 146 tests and Ruff passed, including notification/prompt
isolation, muted delivery, cache streaming and unknown-parameter regressions. Real-model source synthetic integration passed; zero printer writes.
Numeric artifacts and qualification scope are in PREVIEW3_REPORT.md and benchmarks/preview3-*.

Preparing 0.3.0-preview.1 build, upgrade/reinstall/installed checks and 16 GiB job-budget probe.
New utterances now cancel only stale LLM interpretation tasks, avoiding queued obsolete inference;
consequential safety-engine transmissions are never canceled/retried by that optimization.
No Windows Sandbox executable, Hyper-V cmdlet, VBoxManage or vmrun is available here; host
RAM is 68,630,749,184 bytes. A memory-budget test cannot close the 16 GB physical-VM gate.
Final failure/concurrency audit added regressions for a TTS failure leaving the speaking flag set
and cancellation racing with prompt completion; speaking reset and pending state transitions
are now synchronized. A pilot 16 GiB job probe passed (2.40 GB peak commit, 70.57 s); final
installer measurement is still required before recording release evidence.
Next: run package qualification and independent Windows CI, record actual evidence, publish
an accurately labeled engineering preview. Hardware/clean-desktop-VM gates stay open.

## 2026-11-11 — Published offline voice preview 0.2.0

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.2.0-preview.1
as a private prerelease, not stable. Assets: complete-model Windows installer (1.39 GiB),
SHA-256 sidecar, PHASE2_REPORT.md and the 57-file model manifest. GitHub's uploaded
installer digest matches 1cd1ccb981b7e7539c42b717e008ef3531ec39d0c1054afc2be34ab1b78e96c7.
The release targets e3eb3b1. Independent Windows build/test run 43062031011 passed and
published its build artifact. All source/frozen/installed/default-audio evidence is recorded.

Phase 2 core wake/pipeline/interruption/bundling work is implemented and packaged.
Keep issue #2/milestone open for human wake/room calibration and optional speaker enrollment;
clean-VM offline, cross-version upgrades and the 16 GB benchmark remain acceptance work.
No live printer action or connection occurred in this Phase 2 session. Audio device tests
saved neither microphone recordings nor transcripts. To resume, read PHASE2_REPORT.md,
benchmarks/phase2-*.json and issue #2. Do not silently promote this preview to stable.

## 2026-11-11 — Independent complete-model Windows build passed

Run 43062031011 passed both jobs: 99 tests and the complete-model installer build. The
independent runner downloaded checksum-pinned sources, reproduced the committed 57-file
manifest, passed frozen offline voice integration and produced the full installer.
Models are cached for builds only; the installed app never downloads them. All local
frozen/installed and default-device smoke evidence remains green. No live printer action.

Preparing v0.2.0-preview.1 publication with the tested local installer, checksum, model
manifest and PHASE2_REPORT.md. Core Phase 2 software is implemented; human wake/room
calibration, unplug/replug, clean VM offline qualification and optional speaker enrollment
remain explicitly open. After publication, verify uploaded checksum and record the URL.

## 2026-11-11 — Phase 2 frozen and installed-model gates passed

99 source tests and Ruff passed, as did Windows test CI. Built one unsigned 0.2.0-preview.1
installer with all 57 model/runtime/data/notice assets: 1,489,177,877 bytes (~1.39 GiB),
SHA256 1cd1ccb981b7e7539c42b717e008ef3531ec39d0c1054afc2be34ab1b78e96c7.
Frozen self-test loaded bundled assets, ran the local CPU LLM, rejected own echo and
interrupted simulated playback at ~0.71 s. No printer writes.

Per-user install, same-version reinstall preserving isolated SQLite, installed startup,
installed complete-model voice gate, uninstall and retained isolated data passed. The
installed probe measured a 1.23 s synthetic interruption, zero own echo requests and zero
printer writes. Actual user settings were untouched. Windows default audio smoke completed
TTS over 884 capture frames with zero own wake/utterance events, no saved microphone
recordings/transcripts and zero printer connections.

Evidence is under benchmarks/phase2-*.json and PHASE2_REPORT.md. Independent complete-model
Windows build run 43062031011 is being followed; test job passed. Next: finish CI, publish
voice prerelease and update issue #2. Human wake/room accuracy, unplug/replug, 16 GB baseline,
clean VM/cross-version and supervised safety gates stay open. Speaker enrollment remains
optional/deferred. No live printer actions permitted or performed.

## 2026-11-11 — Phase 2 offline voice implementation and qualification

User authorized continuing Phase 2 autonomously, with no live printer actions. Read the
logbook and inspected the existing code before changes. No printer endpoint was contacted.

Implemented pronunciation-equivalent Klippy/Hey Klippy BPE token paths; actual synthetic
short-name and stop-talking tests now pass for two voices. Clippy is a homophone and is
documented as acoustically indistinguishable. Klipper/clipper and ordinary speech are
negative probes; full physical accuracy and false-positive rates remain unqualified.

Replaced half-duplex capture with bounded duplex PCM, rendered-audio reference, WebRTC
AEC3, a confidence-checked linear echo path, near-end evidence gating and an exact-prefix
local ASR wake fallback during playback. AEC3 alone suppressed a short wake syllable in
double-talk; real-model simulations found and drove this fix. The recorded real-time
synthetic barge test now stops playback at about 0.74 seconds and transcribes the request,
with zero own-echo wakes/requests. Queued speech and ASR are generation-bound. Added
stale LLM cancellation and capture-time confirmation binding; wake interruption preserves
an already reviewed pending action, while printer changes invalidate audio context.

Model pack: 57 hashed model, binary, data and notice files assembled from pinned inputs.
Selected Kokoro v1.0 with a CMUdict-derived BSD-2-Clause lexicon; discarded VITS and the
unreviewed CMU-in-IPA/eSpeak lexicons. CMUdict's GPL wrapper is build-only and excluded
from freezing. Included license evidence/notices for KWS, Whisper, Qwen, Kokoro, CMUdict,
llama.cpp/LLVM plus WebRTC/Abseil/PFFFT/RNNoise/ONNX Runtime dependencies. The qualified
manifest distinguishes redistribution/integrity review from acoustic stable-release gates.

Tests: 99 local tests passed before final packaging. Real-model probe passed with zero
printer writes and no device opens. A Windows default-device smoke exposed an STA/MTA
COM initialization error after PortAudio import; handling HRESULTs fixed it. A second
physical capture/render smoke opened the default WASAPI pair, processed 884 frames,
completed the short TTS phrase, and produced zero wake/utterance events. No microphone
recordings or transcripts were saved. This is not a human wake/calibration test.

Files: voice/audio/windows_audio/speech_text/models/runtime/conversation/app modules,
voice and model tests, reproducible model assembly, pinned source inventory, license
notices, device-free integration probe, PHASE2_REPORT.md, packaging/CI updates.

In progress: build 0.2.0 offline voice preview with the complete model payload; run frozen
self-test, installed-model checks and independent Windows CI. Then update evidence and
publish accurately labeled preview. Optional speaker enrollment remains deferred; human
microphone/room tests, unplug/replug and clean VM acceptance remain open. Never execute
live printer actions during this task.

## 2026-11-11 — Published private engineering preview

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.1.0-preview.1
as a prerelease (not draft, not stable), targeting 237597f. Uploaded the 53.9 MiB unsigned
installer, SHA-256 sidecar, release report and isolated UI preview. GitHub's uploaded
asset digest matches local SHA256 b45d58b8f7b8048c7bd23cc4eedab679ac4d4bdab98084d20ab1c9e99c2e8971.

Independent Windows CI test + installer pipeline passed (run 43022624225) and uploaded
its preview-build artifact. Local installer lifecycle checks passed, including actual
isolated SQLite preservation. Source tests: 78 passed. No live printer writes performed.

Phase 1 is complete. Remaining phases and hardware/voice/redistribution gates stay open.
Next work is software development in Phase 2: improve short Klippy wake accuracy, qualify
model/lexicon redistribution, implement AEC/hands-free interruption and speaker enrollment,
then finish remaining UI/monitoring and full clean-machine/offline qualification. Actual
microphone calibration and consequential printer tests require the owner's supervised
session. Do not mark stable v1.0 complete. Read RELEASE_REPORT.md and issue #2 to resume;
experimental model files are in ignored local/model-research and never in Git/releases.

## 2026-11-11 — Preview acceptance evidence and publication preparation

Final application suite: 78 passed locally; Ruff clean. Windows CI passed on aa5b30c
(run 43022588573). Independent Windows CI installer build is being followed to completion.
Phase 1 GitHub issue/milestone closed; all later phases retain their incomplete gates.

Final local frozen startup/shutdown including Sherpa and sounddevice native imports passed.
Unsigned installer built: 56,473,009 bytes, SHA256
b45d58b8f7b8048c7bd23cc4eedab679ac4d4bdab98084d20ab1c9e99c2e8971.
Per-user installation, same-version reinstall, actual isolated SQLite sentinel preservation,
installed startup, uninstall and retained isolated data all passed on development host.
Installer contains relevant user docs, GNU license texts and Qt replacement/source notices.
No clean VM/cross-version qualification is claimed. Tests never touched actual user settings.

Added negated-action regressions and print-error notification while firmware stays ready.
No live printer writes. Inspected the rendered native Windows panel visually; fonts/layout
are legible and unclipped. Synthetic engine evidence remains under benchmarks/.

Next action: finish independent CI build, publish v0.1.0-preview.1 as a private prerelease
with installer/checksum/report, record publication, and continue Phase 2's primary wake,
hands-free interruption and model redistribution work. Full project remains incomplete.

## 2026-11-11 — Windows preview packaging and real local engine probes

Completed: source pushed to private repository; eight GitHub milestones/issues created;
Windows test CI passed for the earlier packaging milestone. Local suite now passes 78
tests, including model hallucinations, parameter clarification, cancellation races and
Qt clean shutdown. Implemented managed loopback-only --offline llama.cpp runtime,
animated companion states, wake sensitivity, periodic/reconnect read-only macro refresh,
serialized SQLite access, strict model reference integrity and plain-text response rendering.

Packaging: PyInstaller initially picked up an incompatible Poppler ICU DLL from ambient
PATH. Diagnosed QtCore DLL import failure in a console build; controlled PATH fixed it.
Frozen app now starts/closes and imports actual speech/audio native modules. Inno Setup
7.1.1 compiler installer Authenticode signature verified as valid (Pyrsys B.V.). Built an
unsigned 53.8 MiB engineering preview installer. Initial per-user install, same-version
reinstall with isolated data, installed-app smoke and uninstall passed on development host.
Extended SQLite preservation test and final license/docs repackaging are next.

Actual model tests: downloaded official KWS, Whisper tiny.en, VITS-LJS, llama.cpp b12110,
and pinned Qwen3 1.7B Q4_K_M into ignored local/model-research. Qwen model SHA matches HF
LFS hash; llama binary archive SHA matches GitHub asset digest. Other archive/local file
hashes recorded; no upstream digest claim where unavailable. Candidate manifest is
experimental, separate from empty qualified production manifest. KWS card is Apache-2.0;
VITS lexicon and complete converted-model redistribution review remain open.

Results: synthetic Hey Klippy wakes; short Klippy fails at threshold 0.25. Actual VITS
generated a pause request and Whisper transcribed it. Initial LLM test invented a macro
on vague input; fixed prompt/schema plus independent lexical action evidence gate, with
regressions. Updated probes return temperatures, pause and clarification respectively.
Detailed scoped CPU-only timings are in benchmarks/. Source idle shell measured on a
63.9 GiB Ryzen 7 5800X host; not the requested typical 16 GB baseline. No microphone
accuracy or full-pipeline performance claim. No personal audio or conversation saved.

Files: app/conversation/runtime/safety/storage/models/monitor modules, tests, packaging,
scripts, CI, candidate checksums, benchmark evidence and documentation.

Open work: primary wake-word tuning/qualification, AEC and hands-free barge-in, optional
speaker enrollment, complete licensed bundled model payload, full MMU/subscription flows,
remaining desktop preferences, clean VM/cross-version install qualification, CPU baseline,
sleep/device tests, complete fleet read-only and supervised consequential hardware tests.
No live printer writes or modifications performed. Stable v1.0 remains blocked.

Resume: read this file, inspect git/release/CI status and RELEASE_REPORT.md. Finish final
preview repackaging and evidence commit, verify latest CI, publish accurately labeled
prerelease only; then continue the open software work before supervised hardware acceptance.

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
