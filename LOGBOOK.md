# Logbook

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
