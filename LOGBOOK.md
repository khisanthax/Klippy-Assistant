# Logbook

## 2026-11-19 - Final dispatch state and artifact identity

A second review traced edits to the local cap and confirmation policy during final endpoint
lookup. Dispatch now compares the local policy under the settings lock and checks the exact
discovery record returned by validation. Two new simulated races change policy during
lookup. The artifact reviewer also recomputes every native report digest. The installer
harness installs its program-scoped firewall rules before setup and protects the bundled
runtime before application startup. Hosted run 44611591220 was blocked by the Actions
budget before its first step.

## 2026-11-19 - Audit corrections for 0.8.0-preview.2

The simulator now exercises cancellation during endpoint lookup and after HTTP handoff, strict
upstream axis maps and restored owner caps through reapproval. The console renders the current
confirmation policy. Release QA now requires named voice cases, exact source and binary identity,
and SQLite content preservation for two consent profiles after upgrade, reinstall and uninstall.
The focused transport, release-contract and UI run passed 34 tests, including opening both seeded
profiles with the desktop smoke entry point. Full build and qualification results follow separately.
Physical printers and the owner profile were outside testing.

## 2026-11-17 - Unpublished 0.8 draft prepared and all assets verified

Prepared GitHub draft release 449346304 at exact app source 5862ec2. All ten candidate assets,
including the installer, match local sizes and SHA-256 against GitHub server digests. Receipt:
benchmarks/preview8-draft-assets.json. It remains draft=True, prerelease=True, published=False,
qualified_for_publication=False. Latest published 0.7.2 and owner installation are unchanged.
Implementation and evidence pushed to main; no forced history edits or printer actions.

Required next action: enable GitHub Actions budget, rerun workflow 44202364931 on exact source,
complete all Windows and installed/offline/upgrade/memory gates, verify the resulting CI-built
installer and assets, then publish the qualified preview. Do not publish the local candidate
in place of missing CI evidence. Issue #19 and PREVIEW8_REPORT.md explain the open gates.

## 2026-11-17 - 0.8 local frozen package passed; publication blocked by Actions budget

Exact app source 5862ec29cbaa37dc2e7b8501dac3033b135e47d1. Local build reran 886 tests/Ruff and verified
57 unchanged assets; frozen startup, 29 orb/26 feature checks, 25 wake cases/recovery,
eleven query, 21 heating/cancellation, eight new limits cases, dialogue/audio/echo/barge-in
and three follow-ups passed. Budgeted frozen native preview passed at 2.356 GiB peak
process-tree commit (16 GiB limit), 103.232 seconds wall/181.547 CPU seconds.
Raw broad continuous-capture result remains separately False in both contexts. No human
acoustic/clean VM/actual16GB/supervised printer gate closed. No owner installation changed.

Installer compiled: 1489543358 bytes, SHA-256 c4f78386009211369424f013e8165de925275a26734c5f9214751a39b6110256.
Current candidate and sidecar are in dist. Local frozen/memory evidence and full status are
in benchmarks/preview8-local-package-qualification.json and PREVIEW8_REPORT.md.

Windows workflow_dispatch 44202364931 and push 44202365689 ran zero steps. Confirmed GitHub
annotation: "The job was not started because an Actions budget is preventing further use."
This blocks required installed/offline/0.7.2 upgrade/reinstall/history/settings/owner-limit
preservation and fresh-runner qualification. Do not call this CI-passing or publish it as
qualified. Owner asked to enable Actions budget; continue from exact source once available.
Issue #19 updated. Prepare an unpublished draft with candidate and evidence, preserve the
current published 0.7.2 release and installed owner profile. No physical printer actions.

## 2026-11-17 - Capability registry and deterministic direct-motion candidate

Reviewed current official Moonraker object API and Klipper status/config/G-code references,
plus Cartesian/CoreXY and gcode_move implementations. Startup settings differ from runtime
velocity/acceleration; G92 mapping must use current machine/G-code position difference.
Implemented limits.py, motion.py and SafetyEngine integration. No generic endpoint writes,
model motion authority, automatic retries or firmware-setting modifications introduced.

Registry is per approved printer, sanitizes discovered values, tracks configuration digest,
generation/freshness and replay watermark, refreshes on enrollment/reconnect/lifecycle/config
changes and revokes pending motion/heating. Unknown/nonrectangular layouts retain native
capabilities while movement blocks. Exact one-axis destinations, homing, stationary/live
coherence, modes/offsets, global/Z caps and optional stricter owner policy are checked twice.
State is saved/restored without MOVE; confirmation always required for direct motion.

Heating now requires active firmware bounds, actual heater telemetry and selected extruder;
old owner caps remain restrictive. Explicit malformed owner caps and shadowed standard
commands block. Two previous manual-cap-only fixtures now supply real synthetic active
configuration; absent authority remains tested even when an owner cap is supplied.

Added limits Settings inspection/strict-only JSON editor and separate movement inventory.
Native desktop passed 29 orb/26 feature checks, including actual edit controls. Focused 117
limits/motion cases pass; full regression/Ruff and native model/package qualification are in
progress. Earlier local iterations exposed numeric 'minus 200' normalization, an inventory
classification label and test fixtures with colliding aliases; corrected with regressions.
Packaged limits probe forbids all HTTP writes and is a mandatory preview gate. Existing
acoustic/interrupt/query/dialogue/audio/model protections retained. Models unchanged.

Completed all 886 tests and Ruff; additional targeted recovery/limits run 135 passed. Native
real-model engineering-preview gates pass, all eight motion probe cases with zero writes.
Independent broad continuous-capture result remains False and is retained separately in
benchmarks/preview8-local-native.json; no acoustic gate relaxed.

Next: exact-source Windows build/0.7.2 upgrade/offline/
settings/recovery/memory qualification, verify assets and publish accurately labelled preview.
Issue #19 remains open for supervised hardware/unsupported motion scope acceptance. No real
printer connections/actions or owner profile/device changes. Physical clearance, human audio,
clean desktop VM, actual16GB and sustained device-load gates remain open.

## 2026-11-15 - 0.7.2 preview published and owner installation updated

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.7.2-preview.1 at qualified source
64ba81af5e89681b805db57a0c80e75da769b965. Windows run 43782381184 passed all three jobs:
762 tests/Ruff, frozen/installed/native wake/query/orb/voice, 0.7.1 upgrade/reinstall/offline/
settings/history/logging/uninstall preservation and 16 GiB process-tree budget. All fourteen
asset sizes/digests verified before and after publication; remote tag independently verified.
Raw broad voice outcomes remain separately False/False/True, not a human accuracy claim.
See PREVIEW72_REPORT.md, benchmarks/preview72-release-qualification.json and publication JSON.

Owner profile/settings/history backed up privately with SQLite integrity checks immediately
before update. Installer succeeded without reboot; registry 0.7.2-preview.1. Settings, printers
and reviewed macros match the pre-install logical digest exactly; original history IDs all
preserved. Isolated installed startup/shutdown passed. Visible 0.7.2 application responding;
WASAPI input remains Voice Chat Mic (BEACN Mix Create), output System (BEACN Mix Create), and
startup diagnostic reports microphone ready. This proves device open, not live speech pickup.
Logging choices preserved. No microphone audio recorded or physical printer command issued.

Installer 1,489,908,266 bytes, SHA-256
0c308b113082c2bca18ba328d005e4d659ace77b909c497012775b79b0095238.
Current installer/sidecar remain in the qualified C: artifacts directory because D: was full;
previous generated 0.7.1 installer/sidecar archived to C: with hashes verified before removal.
D: source checkout fast-forwarded from clean main; source/model inputs and owner profile kept.
Next: owner live wake/query check using BEACN, sustained device/load, full interactive desktop,
clean VM, actual16GB and supervised-printer acceptance. All these hardware gates remain open.

## 2026-11-15 - 0.7.2 exact-source Windows qualification passed

Qualified 64ba81af5e89681b805db57a0c80e75da769b965; https://github.com/khisanthax/Klippy-Assistant/actions/runs/43782381184. All 762 tests/Ruff, frozen/installed startup,
29 orb/22 feature checks, native wake, eleven query cases, 21 heating/cancellation checks,
three unprefixed follow-ups, actual 0.7.1 upgrade/reinstall/offline/logging/settings/history/
uninstall preservation and 16 GiB process-tree budget passed. All prior 725 cases preserved.
First 3218469 candidate correctly blocked invalid model query/subject pair; failed evidence
retained. Native actual-model probes passed three repetitions after constrained pairs and
independent validation. No silent conversion, gate relaxation or physical printer commands.
Installer 1489908266 bytes; SHA-256 0c308b113082c2bca18ba328d005e4d659ace77b909c497012775b79b0095238.
See PREVIEW72_REPORT.md and benchmarks/preview72-release-qualification.json. Compute benchmark
method reproduced with scripts/query_capture_benchmark.py; original measurements unchanged.
Next: exact-source tag, verified draft assets, accurately labeled engineering publication and
profile-backed settings-preserving owner update. Human acoustic/device-load/desktop/clean VM/
actual16GB/supervised hardware gates remain open; BEACN default selection unchanged.

## 2026-11-15 - First 0.7.2 package candidate blocked by invalid model subject

3218469 / Windows run 43781318946 passed 758 tests/Ruff but failed the frozen query gate:
all ten deterministic cases passed; retained coordinate-reference homing model case rejected.
Reproduced with the actual bundled model after its temperature-action probe: first homing/null
passed; next two homing/x selections rejected before reads. Independent query and subject
enums allowed an invalid pair. Evidence benchmarks/preview72-initial-query-failure.json.
No installer published. Tightened schema to explicit allowed query/subject combinations and
independently validate both LocalLLM output and QueryService input; never convert invalid model
output. Added four invalid-pair regressions. Three repeated native full query probes now pass
(benchmarks/query-capture-native-query.json). Original eleven cases and all package gates stay
required. Next: complete full suite and qualify a fresh exact-source candidate.

## 2026-11-15 - Query/capture reliability candidate

Verified routing defect: correctly transcribed Z-axis height question fell through common
matching and the query model selected temperatures. Added deterministic spatial phrasing,
axis follow-ups, validated XYZ projection, commanded-position/homing qualifiers and model
measurement mismatch clarification before reads. GET allowlist and SafetyEngine unchanged.
Frozen query qualification now includes eleven cases.

An active BEACN endpoint and capture overruns were observed. One live stack sample found
periodic monitoring in pairwise macro similarity work: a hotspot, not proof of every overrun.
Background discovery skips unused advisory comparisons; manual review retains warnings.
Fresh dependency fingerprints, rename detection and approval revocation remain. Per-macro
comparison inputs and safe upper bounds avoid repeated work without changing thresholds.
Cold-reference AEC checks now use a running count; AEC processing and TTS assets unchanged.
Synthetic 2,000-frame median 0.4169 -> 0.0919 ms, p99 0.7269 -> 0.1644 ms, exact cold PCM
preserved. Ten generated macros, three repetitions: background median 26.6834 -> 0.0873 ms.
Evidence benchmarks/query-capture-compute.json; these measure compute, not live wake accuracy.

Numeric peak/RMS/zero frames and DSP-work/queue-delay diagnostics retain no microphone audio.
Owner confirmed BEACN; selection unchanged. Missing optional device-name metadata cannot stop
capture. Generated 32-hex event/attempt IDs survive redaction for correlation; arbitrary
secret-like identifiers stay redacted. Previously redacted IDs cannot be recovered.
New simulated regressions cover phrases/context, malformed data, bad model selection before
reads, macro warnings/approval changes, AEC equality, metrics/consent and ID privacy.
Local validation: all 758 tests passed in 58.69 s; Ruff clean. Exact-source Windows package qualification pending. Human acoustic, BEACN signal,
long-load, clean VM, actual16GB and supervised hardware gates stay open. No physical writes,
owner conversations/configurations/credentials or audio committed. Next: validate and qualify.

## 2026-11-15 - 0.7.1 hotfix published and owner installation updated

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.7.1-preview.1 at qualified source 63ef222582e096e6651c689fb85fd9bf5a47d04d; Windows run
43769019232 passed all three jobs, 725 tests/Ruff, 29 orb/22 feature checks, frozen/installed
strict wake probes, 0.7.0 upgrade/reinstall/offline/logging/settings/uninstall preservation and
16 GiB process-tree budget. All 13 uploaded sizes/digests verified and unchanged after release.
Verified tag independently through GitHub. Publication metadata in
benchmarks/preview71-release-publication.json; qualifications and original broad acoustic
False/True/False outcomes retained independently. No stable/human wake-accuracy claim.
Frozen synthetic natural recovery count 1; installed count 0. Both passed a labeled injected
first-ASR rejection followed by real higher-threshold KWS and exactly two actual ASR passes,
canonical wake-only delivery, no command/token and no added negative acceptance. Natural
variation/rejection remains reported, never forced into acceptance to pass a gate.
Installer 1489919100 bytes, SHA-256 2906d1bf0726b47e9e0b70308345f071b39576e46ba327ee8ef7ecffcdc60c83.
Owner settings/history backed up privately before installation. Installer succeeded without
reboot; registry 0.7.1-preview.1. Settings/printers/reviewed macros matched the pre-install
logical digest exactly; original history IDs preserved and integrity checks passed. Installed
isolated startup/shutdown passed; visible updated window responsive. Existing logging opt-ins
remain enabled; no settings reset or safety-policy change. No owner profile data in Git.
Verified installer/sidecar copied to D:/Users/khisa/Documents/ChatGPT/KlippyAssistant/dist.
Prior 0.7.0 installer archived with SHA verification to C; old generated unpacked build already
archived after comparing all 517 file hashes, preserving source/model inputs and profile.
No physical-printer command or microphone audio recording. TTS/quality algorithms and model
payloads unchanged. Hover/copy reason available; left-click still mutes capture immediately.
Next: owner's microphone/room wake verification, full interactive focus/DPI/taskbar/sleep,
long device-load, clean desktop VM, actual16GB and supervised-printer acceptance; all stay open.


## 2026-11-15 - 0.7.1 exact-source Windows qualification passed

Qualified 63ef222582e096e6651c689fb85fd9bf5a47d04d; https://github.com/khisanthax/Klippy-Assistant/actions/runs/43769019232. All 725 tests/Ruff, frozen/installed startup,
29 orb/22 feature checks, strict native wake probes, actual 0.7.0 upgrade/reinstall,
logging/settings/offline/uninstall preservation and 16 GiB process-tree budget passed.
Every prior engineering voice/audio/query/heating gate retained. Original broad acoustic
results remain independent, not a human accuracy claim. Model/TTS assets unchanged.
Installer 1489919100 bytes; SHA-256 2906d1bf0726b47e9e0b70308345f071b39576e46ba327ee8ef7ecffcdc60c83.
Evidence: benchmarks/preview71-release-qualification.json. First da74984 candidate failed
legacy orb message mapping; no candidate published or unsafe test criterion removed.
Next: exact-source tag, verified draft assets, engineering publication and settings-preserving
owner hotfix installation. Physical/acoustic/interactive desktop/clean VM/actual16GB gates open.


## 2026-11-15 - Discontinuity stale-ASR safety regression blocked first hotfix candidate

Source da74984 passed 723 local tests (62.67 s)/Ruff and Windows unit CI. During the requested
discontinuity audit, added a blocked-ASR simulation: DSP reset cleared Session but retained
playback generation, so the delayed pre-reset transcript reopened Session and reached on_text.
The regression failed before the fix; only a fake callback was used, never printer transport.
No evidence this defect caused the owner's stored prefix rejections or any physical action.
The direct reset is used by input-queue overrun; the input-status discontinuity path already
called reset_session. Resetting DSP now interrupts generation before clearing capture/Session, invalidating
old ASR/TTS and UI state events. Input-queue overrun gets its own capture-stage diagnostic.
Preserve the failing regression and every previous case. Supersede first candidate before
publication; fresh full suite and exact-source Windows qualification required. No automatic
consequential retry, model/audio-quality change or physical-printer command.

Corrected local validation: all 725 cases passed in 64.58 s; Ruff clean. Actual Windows Qt
probe passed all 29 orb and 22 feature checks. Offscreen rendering cannot qualify native focus
and was explicitly excluded for that purpose; no focus assertion was relaxed. Next exact-source
Windows frozen/installed/offline/upgrade/memory and strict native wake qualification follow.

First run 43767542981 failed the retained frozen orb error check: it uses the exact legacy
Speech recognition unavailable fragment, absent from the new explicit map. All 22 new feature
checks passed. Add that exact known alias and regression, never restore substring matching
or relax a check. Keep failed frozen evidence in benchmarks/preview71-initial-frozen-orb.json.


## 2026-11-15 - Investigated wake-only Attention; conservative verification and diagnostics

Existing enabled owner history contains wake_prefix_rejected with a KWS candidate and ASR
prefix mismatch; earlier verified wake/read-only replies/playback succeeded. Reproduced
ASR rejection -> Wake transcript unclear -> orb substring unclear -> red Attention with a
synthetic ASR fixture. No device/TTS exception accompanies those rejected attempts. The old
log lacks orb transition events, so the owner's exact visual frame is not independently
recorded. Do not commit owner transcripts, IDs/timestamps, printer facts or profile data.
Independently reproduced stale Attention timer persisting into a new wake; fixed without
authorizing candidates. Added explicit stage-specific events, hover reason, copy actions,
transition/counter history and consent-filtered transcript correlation, including discards.
Strict short-wake recheck requires a separate higher-threshold/lower-boost KWS verification
and two complete strict ASR results; forwards only wake-only Klippy with no command/token.
No fuzzy wake aliases, guessed commands, TTS change, model payload change or printer writes.
Preliminary 715 then 720 full cases passed; final local suite/Ruff and exact-source CI follow
final strict verifier and frozen/native test integration. See PREVIEW71_REPORT.md for scope.
Native comparison varies naturally: exploratory unqualified silence-only prototype recovered
two positives; final stricter protocol preserves ambiguous rejections. The final native gate
also tests a labeled injected first-ASR failure followed by real KWS/two-ASR and VoiceLoop;
no claim that every generated run naturally needs/reaches recovery. Human acoustic gate open.
D workspace was full. Work continues in C:/Users/khisa/.codex/workspaces/KlippyAssistant-attention.
Archived 517 older ignored generated dist/Klippy files to C, comparing every SHA-256 before
removing that generated D copy; source, owner profile, current installer and models preserved.
Next: final tests, Windows frozen/installed/offline/upgrade qualification and qualified hotfix.


## 2026-11-15 - Owner installation upgraded to 0.7.0-preview.1

At owner's explicit request, verified published installer SHA-256, made an integrity-checked
SQLite online backup in the owner's local profile backups, and upgraded existing per-user
0.6.1 installation in place. Installer closed old Klippy/owned language runtime, completed
successfully without reboot; registry reports 0.7.0-preview.1. Before relaunch, all settings,
enrolled printers and reviewed macros matched the backup's logical digest exactly; integrity
check passed. Installed isolated startup/shutdown smoke passed. Relaunched updated app in
tray and verified process remains running. Backup/installer log/startup evidence remain local
in the profile, never committed. No settings reset, logging opt-in, safety-policy change or
physical-printer command. Initial helper-file write hit full workspace drive; backup was
completed successfully on C before the old application closed. Archived SHA-verified generated
0.1.0 installer/sidecar to existing C archive, retaining current 0.7 installer in dist.
Remaining human/hardware acceptance gates unchanged.


## 2026-11-15 - 0.7.0 conversation controls preview published

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.7.0-preview.1 at qualified app source f6ce887e703b0201c1548e58a06167d7757d815b.
Windows run 43720667146 passed all three jobs: 698 tests/Ruff, frozen and installed native
startup/29 orb/19 feature checks, 0.6.1 upgrade/reinstall/offline/settings/uninstall preservation
and 16 GiB process-tree budget. All ten draft assets were size/SHA-256 verified, then verified
unchanged after publication. Exact-source tag was independently checked through GitHub.
Publication metadata: benchmarks/preview7-release-publication.json; full qualifications in
benchmarks/preview7-release-qualification.json. Native text response timings: routine
2.49/3.00/3.26 ms; actual model explanations 3736.70/6237.54/6220.89 ms frozen/installed/budgeted,
excluding ASR/TTS/playback. Original broad acoustic False/True/True results retained separately.
No unsupported claim of human wake accuracy or stable acceptance.
Verified Klippy-Setup-0.7.0-preview.1.exe and sidecar copied to
D:/Users/khisa/Documents/ChatGPT/KlippyAssistant/dist; 1489871539 bytes,
SHA-256 e828db938485b46b659ab78d17fbcaa42024f1b76cf7069de70772e707489f53.
Owner app/profile/logging were not changed by this release work; install remains a user action.
Personality/length are in Settings; optional History remains off by default; remembered macro
choices remain identities only and never authorize execution. TTS algorithms/models unchanged.
No physical-printer commands. Next acceptance: owner's conversation review, interactive
focus/DPI/taskbar/sleep matrix, long device-load, room/acoustic, clean desktop VM, actual 16 GB
and supervised physical-printer gates. Issues remain open for unverified acceptance.


## 2026-11-15 - 0.7.0 exact-source Windows qualification passed

Source f6ce887e703b0201c1548e58a06167d7757d815b; https://github.com/khisanthax/Klippy-Assistant/actions/runs/43720667146, attempt 1. 698 tests/Ruff passed, prior 610 preserved.
Frozen/installed startup and 29 orb plus 19 conversation-feature checks passed. Actual 0.6.1
upgrade/reinstall/offline/settings/uninstall preservation and 16 GiB process-tree budget
passed. All three native model explanation probes passed with verified facts and no writes;
actual timings are in PREVIEW7_REPORT.md. Prior audio/follow-up/query/heating gates retained.
Installer 1489871539 bytes; SHA-256 e828db938485b46b659ab78d17fbcaa42024f1b76cf7069de70772e707489f53.
Evidence: benchmarks/preview7-release-qualification.json. No audio algorithm/model changes,
owner logging changes or physical printer actions. Next: exact-source tag, digest-verified
draft assets and preview publication. Hardware/acoustic/interactive desktop/clean VM/actual
16 GB acceptance remain open; source 04ddb7e failed dialogue gate and was not published.


## 2026-11-15 - Measured CPU timeout and bounded explanation budget

Source 6be74b8 / run 43719542714 passed 697 tests/Ruff, native Qt and prior voice/safety gates,
but actual explanation hit dialogue_timeout at 3520.39 ms. Retain evidence in
benchmarks/preview7-indexed-dialogue-timeout.json; no installer/release published.
The 1831.87 ms local run did not establish slower CPU performance. Complex explanation HTTP
deadline changes 3.5 to 7.5 seconds, total composition budget 4 to 8 seconds, native allowance
4.5 to 8.5 seconds. This explicitly revises a self-imposed performance gate, not safety,
factuality or actual-model requirements. Routine queries still bypass LLM; interruption cancels
generation, timeouts use verified fallback, aged observations stay labeled, and actions/reviews
never enter generation. Added bounded-timeout regression. Fresh full-suite/CI follows.
Disk-full interrupted source write was restored from Git before changes; its collection errors
are infrastructure failures. Checksum-verified generated 0.5.1/0.6.1 installers archived to
C:/Users/khisa/.codex/artifacts/klippy-archive/previous-dist. No user settings/models removed.
Final local validation: 698 tests passed in 63.67 s, Ruff clean. No audio algorithm, model payload, owner logging or physical-printer changes.


## 2026-11-15 - Frozen dialogue gate blocked release; compact bounded plan output


Final indexed-plan validation: 697 passed in 57.21 s; Ruff clean. All previous 690 cases
preserved, plus compact transport/decoder/diagnostic cases and actual Qt keyboard Escape/
Space-Continue selection regression. Keyboard selection creates a pending review, never a
write. Local actual model accepted indexed plan in 1831.87 ms with 7 completion tokens;
routine 6.09 ms with no model call. No latency threshold, model-required gate, facts or safety
prompt was relaxed. Next exact-source frozen/installed/offline/memory qualification follows.



Source 04ddb7e / Windows run 43716024429 passed 690 tests/Ruff, frozen startup, 29 orb/
19 conversation-feature checks and all prior engineering voice/audio/safety gates. Added
grounded_dialogue gate correctly failed: routine 2.30 ms, explanation fallback 3524.97 ms,
actual_model_composed false. The old report did not capture the fallback cause; timing is
consistent with the 3.5 s HTTP deadline, not proof of a parsing cause. No installer/release.
Retain evidence in benchmarks/preview7-initial-dialogue-frozen.json.

Reduced request/decoder overhead without relaxing the four-second budget or any safety/
publication gate. The local model now chooses one index into prevalidated reply plans;
every plan contains the full verified observation and vetted explanation. Output cannot add
prose, facts, actions, tools or omit observations. Short banks exclude unused extra clauses.
Compact decoder rejects extra fields, invalid/boolean indices; optional numeric token metrics
and specific timeout/HTTP/invalid-response diagnostics are now retained without provider text.
An intermediate o/p/c packet used 32 output tokens/3322.56 ms locally; indexed output used
7 tokens/1831.87 ms, routine 6.09 ms. Single observations on a loaded host, not guaranteed
acoustic/end-to-end latency. Final local evidence: benchmarks/dialogue7-indexed-local.json.
34 focused dialogue cases passed; full 696 cases/Ruff and fresh exact-source CI follow.
No TTS/audio algorithm, model payload, user logging preference or physical printer change.


## 2026-11-15 - Event-only macro identity completion before final qualification


Final metadata candidate validation: 690 passed in 58.93 s, Ruff clean; focused history/
persistence module 13 passed after preserving the original independent reopen assertions.
An earlier run had 689 passes plus one Windows WinError 10055 during pytest-asyncio event-
loop setup, before the affected test ran. The unchanged full rerun passed; no tests or timeouts
were relaxed and no user applications were closed. Fresh Windows CI remains required.



Candidate f94fcfe / Windows run 43715058166 passed 689 tests/Ruff; superseded and canceled
before publication to close a requirement gap in event-only history. With transcript and
response text both off, a proposed macro also needs its reviewed technical identity, not
only action=macro. Added command metadata only after SafetyEngine has validated the macro,
and for reviewed missing-parameter drafts. The field never includes a definition, secret,
connection or confirmation token. Added a no-text regression verifying LOAD_FILAMENT is
identifiable while both text fields remain absent and no write occurs. Preserve the existing
persistence/reopen regression independently. Full 690-case run and exact-source requalification
follow; no acceptance criterion relaxed. No physical actions, owner logging or TTS changes.


## 2026-11-15 - 0.7.0 candidate regression and native checks passed

All 689 tests passed in 72.91 s; Ruff clean. Preserve all previous 610 tests. Native local
Qt orb/conversation probe passed, including personality settings, history/privacy/export,
reviewed choices and countdown. Actual local-model probe passed (7.44 ms routine vs
3530.21 ms explanation). No TTS model/resampling/buffering algorithm changes. Integration
review moved mute permission revocation ahead of storage I/O and queued bounded session
lifecycle events for UI collection outside capture locks. Regressions prove late ASR text
is discarded after mute, log failures cannot prevent session closure or safety cancellation,
and session IDs remain stable through long holds but renew after expiry. History view is
bounded to 200 recent matches while filtered/all JSON export covers all retained matches.
Final additions were justified by those integration/privacy boundaries, not relaxed gates.

Next: commit exact source, dispatch Windows CI/build/installed upgrade/offline/memory probes,
verify source-bound evidence and all release asset sizes/digests, then publish engineering
preview. Keep UI focus/multi-DPI/hardware/clean desktop VM/actual 16 GB gates open. Owner
reports current audio quality satisfactory for now; deeper audio work is deferred.


## 2026-11-15 - Dialogue priority added; audio algorithms preserved

Owner is satisfied with audio quality for now and prioritizes dialogue. Added Friendly/Calm/
Direct personality, response length, basic casual turns without an enrolled/selected printer,
fast routine templates and read-only contextual corrections/explanations. The local model
composes only verified observation and vetted explanatory clauses under a strict index schema:
no freeform invented states/values, action generation/authorization, omitted observation or
safety-prompt rewrite is possible. Missing information remains unknown. Stale/superseded
explanations are labeled/discarded; four-second fallback budget. Existing interpretation and
SafetyEngine write path remain separate and unchanged in authority. Personality backup and
legacy detail migration validated. No TTS/resampling/buffering algorithm changes.

Actual model probe passed: 7.44 ms routine text answer with zero model calls, 3530.21 ms
accepted explanation, one composition call, no pending action/writes. Evidence in
benchmarks/dialogue7-local.json; these timings exclude ASR/TTS/playback. First full integrated
suite 680 passed in 65.00 s; final additions cover spoken macro names, mandatory dialogue
gates and bounded 200-row UI with complete filtered export. Final suite pending. Local Qt
probe passed 18 conversation controls checks in addition to prior orb checks; final UI
personality setting check added. Issues #15 (dialogue) and #16 (history/countdown/popup) created.
Models unchanged. Human acoustic/hardware/clean interactive VM/actual 16 GB gates stay open.
Next: final suite/native captures, exact-source commit and Windows/installer qualification.


## 2026-11-15 - Optional history, shared countdown and clarification popup implementation

Read AGENTS, continuity/roadmap/latest preview report and voice/orb/safety code before edits.
Owner added interactive clarification to the same next-preview scope. Implemented default-off
local WAL history with independent text/timing consent, bounded retention, filters/details/
JSON export, credential-field exclusion and text redaction. Raw ASR is not ground truth and
unlabeled spoken secrets cannot be guaranteed recognizable; opt-in/privacy limits documented.
No audio persistence or cloud upload. Late ASR after mute records a discard code without text.
Session IDs and explicit response-ready snapshots drive the red inner orb ring after rendered
speech plus tail, hiding during holds, mute/expiry, with no additional clock or device stream.
Popup resolves actual reviewed macro ambiguity/required numeric parameters through existing
SafetyEngine, fresh config checks and mandatory macro confirmation. Remembered identity is
printer/request-signature scoped and conservatively invalidated on registry/context changes.

Existing canceled-parameter regression caught choice state surviving cancellation; corrected
and retained that regression. Ordinal tests found normalization changes first one to first 1;
both are recognized now. A UI test initially lacked its injected simulator; corrected the
fixture before testing selection. Another existing UI fixture omitted enabled telemetry;
optional history now handles it without changing speech behavior. Focused 45 new-feature
cases pass; latest three playback-tail/mute/UI-export regressions pass. Ruff clean. Full suite
and final native UI checks pending. Initial actual Qt gate passed with synthetic-only captures;
visual review improved consent control sync, table sizing, safety labels and popup provenance.

D: ran out of space while adding tests. SHA-verified generated 0.4.0 and 0.5.0 installers and
sidecars were archived on C:; source/models/user data preserved. Restored the interrupted test
file before running it. No printer actions, live config modifications or owner logging enabled.
Next: finish regression/native visual validation, commit/push 0.7.0 candidate, exact-source
Windows build/upgrade/offline/memory qualification and publish only if gates pass.


## 2026-11-14 - Published and installed qualified 0.6.1 preview

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.6.1-preview.1, unsigned prerelease/not latest or stable, after all seven asset sizes and
GitHub SHA-256 digests matched local files. Remote tag resolves exactly to qualified app
source f9565e0f9afc1fbb64facbec6e70c750b4565d4d (not later bookkeeping commits).
Publication evidence: benchmarks/preview61-release-publication.json. All Windows jobs passed.
Installed and budgeted audio replay gaps improved from 3.73/3.16 s to zero using complete-PCM
fallback; fast frozen host kept first audio at 2.68 s. Peak job commit 1,965,461,504 bytes.
Original broad acoustic outcomes retained: frozen true, installed false, budgeted true;
this variability is not human accuracy qualification. All engineering gates passed.

Owner-authorized update completed from 0.6.0 to registered 0.6.1-preview.1. Online SQLite
backup verified before setup; exact logical database digest and integrity preserved after
setup and isolated installed startup/shutdown. App left closed; no real-profile microphone
or printer operations started. Checksum-verified installer and sidecar copied to project dist.
No owner audio/configuration/credentials or local backup metadata committed. No physical
printer actions. Remaining: owner listening/room and prolonged device-load acceptance,
clean interactive VM, actual 16 GB hardware and separately supervised printer gates.
Next: gather numeric playback diagnostics during owner listening, with no speech recordings;
retain mandatory safety and do not treat synthetic tests as closed hardware acceptance.


## 2026-11-14 - 0.6.1 exact-source Windows qualification passed

App source f9565e0f9afc1fbb64facbec6e70c750b4565d4d; https://github.com/khisanthax/Klippy-Assistant/actions/runs/43615190106, attempt 1. All 610 tests/Ruff passed.
Frozen and installed startup/orb/native voice and process-tree 16 GiB budget passed,
including audio signal/delivery, three unprefixed follow-ups, 7 native query cases and
21 heating/cancellation safety cases with zero writes. Upgrade 0.6.0/reinstall/offline/
settings/uninstall preservation passed. Retained actual broad acoustic outcomes separately.
Installer 1489813001 bytes, SHA-256 311c013d7bae1a1af3d9971a09b4ff2c556346bb1a4c45f7287604cb5ceaf5d3.
Full evidence: benchmarks/preview61-release-qualification.json. Superseded 13c7adf/54af64b,
timed-out 1ebd45d and starved cc64a72 candidates not published. Audio CI failure led to
complete-PCM fallback, never a relaxed signal gate. Next: verified draft assets, exact-source
tag, preview publication, settings-backed owner update and installer copy to dist.
Human perceived quality/hardware/clean desktop VM/actual 16 GB gates remain open.


## 2026-11-14 - Packaged audit caught slower-producer starvation; complete-PCM fallback

Candidate cc64a72 / run 43614107826 completed frozen probe in 137.645 s but failed the added
audio gate: RTF 1.5996 exceeded the two-second reserve, leaving 0.96 s starvation. All other
engineering gates passed; no installer/release. Preserved exact observed numeric schedule
and quality failure in benchmarks/audio61-ci-buffer-reproduction.json. New policy retains
streaming reserve <=2 s and completes PCM first when estimate exceeds it. Same schedule
replay now has zero gap, with first audio 13.67 s versus immediate 4.80 s/2.95 s gaps.
This is an explicit slow-host latency tradeoff, not a claim of faster speech synthesis.
Mic callbacks never wait; interruption flushes buffered PCM immediately; session holds remain.
Two regressions added for the actual CI schedule and interrupt/EOF fallback. Focused 16 passed,
Ruff clean. Full 610-case suite and exact-source package qualification follow. Physical/acoustic
acceptance remains open, no hardware printer actions or user recordings.


## 2026-11-14 - Expanded native qualification timeout retained and diagnosed

Candidate 1ebd45d / run 43612972932 passed 608 tests/Ruff and frozen startup/orb, but native
voice probe exceeded old 180 s overall cap before a report was emitted; no installer/release.
Added durable stage/elapsed checkpoints. Expanded native source probe completed locally in
110.837 s: all engineering gates passed, including audio quality, actual cached delivery,
three follow-ups, echo/interruption and zero simulated writes. Original broad continuous-
wake/raw acoustic acceptance remains false/open. Set overall frozen/installed/budgeted probe
cap to 300 s for the added workload; no behavioral, individual deadline, memory or signal
criterion relaxed. Next exact-source CI must complete and retain checkpoint/final evidence.


## 2026-11-14 - PCM conversion and producer starvation corrected

Original synthetic Kokoro PCM finite/unclipped and equal to SDK chunks; renderer bit-exact.
Independent linear chunk conversion had peak phase error 0.139 and -2.73 dB 10 kHz alias.
Stateful 97-tap sinc gives zero chunk/batch error and -107.42 dB alias. Generation RTF 1.2006
starved replay by 0.70 s; bounded producer reserve removes gaps; first audio 3.64 -> 4.95 s.
Extra converter CPU about 0.11% of one core (short quantized timing); cached production
callback delivered all 136607 expected samples. Evidence: benchmarks/audio61-*.json.
Four quiet WASAPI speaker-only tests, including 30 ms stalls, showed no hardware underrun
or clipping. Output-only latency 26.125 -> 90 ms; brief duplex check reported unchanged
input 22.25/output 36.125 ms, discarding all input immediately. Driver did not honor output
increase in duplex. AEC/mic preserved; no callback buffering waits. Silent/empty/clipped/
starved prompts cannot authorize actions. Human perceived crackle acceptance remains open.
Early CLI parsing corrects import timeout without weakening test. All 608 tests passed in
55.81 s; Ruff clean. Existing audio_device_probe.py preserved, speaker audit separately named.
No owner audio recordings or physical printer actions. Next: exact-source Windows packaging.


## 2026-11-14 — Audio distortion investigation added to the pending hotfix

Owner added static/crackling investigation before the follow-up hotfix was published.
Keep both scopes in the next qualified preview. Read audio.py Playback/resample and
voice.py SherpaBackend.synthesize, render/callback/device lifecycle. Current output converts
each Kokoro chunk independently with numpy.interp to 16 kHz, without an antialias filter or
cross-chunk phase state. Device block size is 10 ms with default latency and WASAPI shared
auto-conversion; playback begins on any queued PCM without a prefill. These are candidate
causes requiring PCM reproduction/measurement, not yet established owner-device findings.
Next: compare original synthetic Kokoro PCM with chunked and rendered output, measure alias,
chunk continuity, peaks, queue/device underruns and callback timing; test stateful quality
resampling and bounded output buffering while preserving 16 kHz AEC capture and interruption.
Do not use a denoiser to conceal artifacts. No audio-quality fix or benchmark is claimed yet.

The pending UI mute refinement now also tags unexpected request errors with their turn so
neither stale success nor stale error speech can reappear after mute. Latest local run:
581 passed, one existing CLI argument-conflict subprocess timed out at 15 s; focused retry
also timed out. A 90 s diagnostic invocation completed correctly with argparse exit 2 after
26.99 s; import timing shows heavy module imports before argument validation. Host free RAM
was about 260 MiB of 64 GiB. Do not relax the test or treat it as a pass; address early
argument validation and record resource conditions for audio benchmarks. No user apps were
closed to free memory. Current committed source remains 54af64b; UI changes are uncommitted.
Runs 43601805764 and 43602816507 were cancelled/superseded before publication. The latter's
frozen native three-follow-up gate passed and diagnostics are retained under the C: artifact
folder klippy-preview61-final; use a fresh source-specific folder for final qualification
to avoid mixing candidates. There is no published/tagged 0.6.1 yet. Owner install remains
0.6.0. No physical printer actions or owner audio recording occurred.

Final mute-path review also invalidated the UI request generation and cleared busy/pending
delivery state on microphone toggles. A slow response completing after mute is now ignored
rather than reappearing or speaking. Extended the orb regression with an in-flight request.
Candidate 54af64b / run 43602816507 passed frozen native three-follow-up gates, but is
superseded before publication for this UI boundary correction; retain its cancelled record.

## 2026-11-14 — Near-expiry capture hold refinement

Final boundary review found capture had no session hold until VAD completed. A question
starting just before expiry could lose UI query context mid-utterance. Added atomic
`Session.begin_active()` and capture-to-ASR hold transfer, with generation checking so
old/muted frames cannot open a session. Expired sessions cannot acquire this hold and mute
invalidates it permanently. Two boundary regressions added. Candidate 13c7adf / Windows run
43601805764 cancelled before publication; new exact-source qualification follows.
Final validation: 581 passed in 70.80s and Ruff clean. The first boundary test asserted
the deadline after advancing another 700 ms beyond ASR completion; corrected that test's
clock observation to the actual handoff. No production acceptance criterion was relaxed.

## 2026-11-14 — Follow-up capture/session reset correction

Reproduced an output-only PortAudio underflow taking the same reset path as lost microphone
input: `_callback` reduced all status bits to bool, `_process` scheduled `_reset_dsp`, and
the shared Session was cleared. This reproduces a failure class; no owner trace/audio was
retained, so do not claim this is recovered hardware evidence. Existing shared processing/
playback holds already work and are preserved. Output-only faults now reset AEC/partial
capture while retaining the continuous microphone/session; prompt delivery fails safely.
Input loss/unknown status/queue overflow/device changes still require fresh wake. Added
numeric output-discontinuity/session-reset counters, configured Session timeout in ASR,
synchronous mute invalidation and single stationary orb-click microphone toggling.

New synthetic pipeline regression captures three commands after one wake with 90 s ASR/TTS
delays, starts countdown after playback, then verifies expiry. Tests cover callback flags,
DSP input/output distinctions, custom timeout, orb mute/unmute and failed confirmation.
First full extended run: 579 passed / Ruff clean. Final rerun follows numeric-counter
refinement. Native preview probes now require three actual ASR follow-ups/status responses.
See PREVIEW61_REPORT.md. No physical printer connection/action or owner install change.
Next: exact-source Windows qualification, 0.6 upgrade/offline tests, verified 0.6.1 preview.
All physical/acoustic/clean desktop VM/actual 16 GB/interactive desktop gates remain open.

## 2026-11-14 — Published v0.6.0-preview.1 floating voice orb

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.6.0-preview.1
at annotated exact-source tag 0fbab095214e109240d069746e00f9fea3d429e0 after every job
in Windows run 43593883215 attempt 1 passed. Verified all nine uploaded asset sizes and
GitHub SHA-256 digests against local files before publication, and verified the remote tag
resolves to the qualified source. Published prerelease=true, draft=false, unsigned and
not latest/stable. Installer SHA-256 matches CI/sidecar/installed QA:
02f2ea49ea9df3f371d2ddd7380dbc6f05f06c869988c41e9b58d2297f9b0e9b.

568 tests (prior 510 retained), 28 orb checks per packaged process and all native preview
query/command/Hey gates pass. Actual animated Qt evidence is 30.43 FPS; packaged CI correctly
respects Windows reduced motion. Broad original voice False/False/True diagnostics remain
separate. Current models/license-qualified payload unchanged. README and roadmap point to
the new release; issues #6/#8/#12 track implementation and remaining acceptance.
No physical printer action/connection, owner recording or owner-installation change occurred.

Next: preserve 568 regressions and perform the supervised human microphone/room and actual
interactive Windows desktop matrix, clean desktop VM and actual 16 GB gates when available.
Physical printer/fleet/MMU acceptance remains separately supervised. Do not infer stable
acceptance from fresh-runner or synthetic evidence; see PREVIEW6_REPORT.md for exact limits.

## 2026-11-14 — Qualified 0.6 floating orb preview

Exact application source 0fbab095214e109240d069746e00f9fea3d429e0 passed all jobs in
Windows run 43593883215 attempt 1: 568 tests, no failures/skips, Ruff, frozen startup,
28 orb checks in each frozen/installed process, native offline probes, actual 0.5.1
upgrade/reinstall preserving SQLite/name/alias/style/orb settings, uninstall preservation
and process-tree budget. All firewall profiles enabled with external app/llama egress
blocked. The installer digest matches CI, sidecar and installed QA:
02f2ea49ea9df3f371d2ddd7380dbc6f05f06c869988c41e9b58d2297f9b0e9b (1,489,813,453 bytes).

All 21 command and seven query cases passed in frozen/installed/budgeted native reports,
zero printer writes. Hey single-attempt wake-only and combined request/ack/follow-up gates
passed. Original broader voice flags False/False/True are retained: frozen and installed
continuous bare-Klippy speech became Clibby and was rejected; budgeted Clippy passed.
No acoustic/prefix gate was changed. Native orb captures reviewed: CI has Windows reduced
motion enabled, correctly static with zero hidden/disabled paints. Installed short static
CPU 5.23% vs disabled-audio 4.70% of one core; widget increment ~0.57 MiB. Development
animation evidence remains 30.43 FPS. Budgeted voice peak commit 1.82 GiB on an 8 GiB runner
is not actual 16 GB hardware acceptance. Full evidence: PREVIEW6_REPORT.md and
benchmarks/preview6-release-qualification.json plus raw reports.

Next: tag this exact source, verify uploaded release assets and publish the unsigned
engineering prerelease. All physical/acoustic/clean desktop VM/actual 16 GB/interactive
desktop matrix gates remain open. No physical printer connection/action or owner install
change occurred. The two superseded code/build candidates are retained in the evidence.

## 2026-11-14 — Floating voice orb implementation and actual Qt evidence

Implemented passive circular voice orb: real capture/render numeric envelopes, generation-
bound pipeline events, exact-engine pending display, muted/error states, existing-session
fade, taskbar-safe dragging and validated local preferences/backup. Topmost tool flags avoid
activation/taskbar entries. Native read-only taskbar/monitor/auto-hide observations supplement
Qt work areas. Qt friendly EDID names differed from GDI identifiers; matching native monitor
origins fixed the initial fallback. Four attached monitors now return native geometry at
100/125%. Actual widget state/size captures and measurements: docs/images/orb-states.png,
benchmarks/preview6-orb-native.json, PREVIEW6_REPORT.md. Issue #12 tracks remaining acceptance.

Preserved the initial 510-test pass. Added 58 regressions for presentation, audio linkage,
readiness/confirmation, 100/125/150/200%/auto-hide/taskbar-edge geometry, tray/drag/disconnect,
preferences/recovery and cleanup. Review found empty/own-speech ASR could leave Thinking set;
fixed it. TTS failure diagnostics now survive their own interrupt while old-generation
failures cannot interrupt newer work; dedicated regressions cover both. SafetyEngine remains
the only write authority. No physical printer connection or consequential action performed.

Initial 563-case run passed before final regressions. A subsequent 568-case run completed
cases but failed to write JUnit when the development drive filled; do not count that as a
complete check. Moved only explicitly named old generated installers to the larger C: artifact
archive, preserving them and leaving owner settings/installations/models untouched. Focused
58 orb regressions and Ruff pass. Full rerun completed successfully: 568 passed in 49.90s,
zero failures/skips, JUnit written, Ruff and diff whitespace checks pass.
Native Windows orb probe passes all checks: 30.43 FPS; short active/disabled-audio CPU
21.94/14.13% of one core, hidden 0.78%/zero paints, widget working-set increase ~0.99 MiB.

Next: exact-source Windows frozen/0.5.1 upgrade/reinstall/offline installed qualification,
checksum verification and 0.6 engineering preview publication. All physical/acoustic/clean
desktop VM/actual 16 GB/interactive display-matrix gates remain open.

Final UI review added loop identity alongside playback epoch: replacing a VoiceLoop can
reuse epoch numbers, so old queued state events must also match the current loop. Added
that regression to the existing UI case. Candidate 2983975 / run 43593542057 is superseded
before publication; new exact-source qualification follows the complete rerun.
Final rerun after this refinement: 568 passed in 59.53s; Ruff and diff checks pass.
Packaging review found the inherited installer information page still said 0.2.0. Corrected
it to 0.6.0-preview.1 and the orb's actual scope. Source 9a03ca1 / run 43593800687 is also
superseded before publication; this notice-only correction requires a new exact-source build.

## 2026-11-13 — Published v0.5.1-preview.1 heating/cancellation hotfix

Published https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.5.1-preview.1 at
annotated exact-source tag 2eabdfaee0bf0f189f18e5719714b0cbaec2ae63 after all jobs in
43461231046 attempt 1 passed. Every one of seven uploaded asset sizes/SHA-256 digests was
verified against local files before publication. Installer digest matches CI, sidecar and QA:
c3b87742262793490f24511103db577d019fa8353043e3b1a756f636b460424f.
Published, prerelease=true, unsigned and not latest/stable. README/roadmap/issues updated.

510 tests and 21 command cases in each native process passed, all prior 408 retained.
Both failure reproductions are committed; original installed Clibby ASR-prefix rejection
and True/False/True broader voice flags remain visible. No original gate was weakened.
The owner phrase now maps to HEAT(heater=0,temperature=90) deterministically when configured
names/aliases identify the printer, with Celsius default/Fahrenheit conversion and fresh
reviewed-limit/confirmation checks. Uncertain remarks clarify without false cancellation;
pending correction reviews cannot execute until restated. No physical heating/connection,
owner recording or owner installation change occurred. Models unchanged/outside Git.

Next: preserve 510 regressions. Actual owner microphone/room and supervised heater/fleet
acceptance remain unverified, as do clean desktop VM/actual 16 GB, accessory and sleep/resume
gates. Use safe in-memory reaction diagnostics for future reported failures; never infer
hardware acceptance from the simulated/fresh-runner evidence or automatically retry heat.

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
