# Logbook

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
Original 99 tests remain unchanged; 141 tests and Ruff passed, including notification/prompt
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
