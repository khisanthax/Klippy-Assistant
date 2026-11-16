# 0.7.2 engineering preview qualification

Qualified app source `64ba81af5e89681b805db57a0c80e75da769b965` in [Windows validation](https://github.com/khisanthax/Klippy-Assistant/actions/runs/43782381184), attempt 1.
762 tests/Ruff passed, preserving all prior 725 regressions. Frozen/installed startup,
29 orb checks, 22 conversation-feature checks, strict native wake probes and eleven native
query cases passed. Actual 0.7.1 upgrade/reinstall preserved isolated settings/history/logging
choices; external-network-blocked runtime, uninstall preservation and 16 GiB process-tree
budget passed. Fresh CI is not a clean interactive desktop VM or actual 16 GB host.

A correctly transcribed Z-height question previously fell through deterministic matching and
was classified as temperatures. Spatial height/elevation/coordinate/position phrasing and axis
follow-ups now resolve deterministically to the existing position catalog entry. Replies
validate coordinates and label commanded position and homing uncertainty. They never claim
measured physical position. Mixed measurements ask for clarification. Model-selected spatial
queries must match the measurement category before any read. All 41 catalog entries and
13 reviewed read routes remain; SafetyEngine/confirmation/authorization are unchanged.

First candidate 3218469 / run 43781318946 passed 758 tests but failed the retained model
coordinate-reference case. Actual local model reproduction returned homing/x, an invalid pair,
and was rejected before reads. The corrected output schema constrains complete query/subject
pairs; independent adapter/service validation still rejects invalid output. No silent coercion,
retry, omitted assertion or relaxed gate. Four additional regressions and three repeated
actual-model eleven-case probes pass. Initial failure evidence is retained separately.

Native query timings exclude ASR, TTS and playback:

| Context | Deterministic Z height ms | Model homing wording ms | Original broad voice result |
|---|---:|---:|---|
| frozen | 0.896 | 12522.17 | False |
| installed/offline | 1.769 | 16194.342 | False |
| memory-budgeted | 1.13 | 16159.098 | True |

The original broad acoustic result is independent and retained; preview qualification does
not establish human wake accuracy. All 21 heating/cancellation, audio signal/delivery,
three unprefixed follow-ups and wake-only/no-token checks remain required and passed.
No physical printer transport or commands in qualification probes.

Capture investigation observed input overruns and a periodic macro similarity hotspot.
Monitoring skips unused pairwise advisory warnings while retaining fingerprints, rename
checks and changed-config approval revocation. Manual review retains full warnings with
cached per-macro inputs and unchanged similarity thresholds. Cold-reference AEC activity is
tracked exactly rather than rescanning 150 arrays per frame; AEC/TTS algorithms, model assets,
sensitivity, default device and safety behavior are unchanged.

Synthetic 2,000-frame median cold-path compute: 0.4169 -> 0.0919 ms; p99 0.7269 -> 0.1644 ms,
with exact cold PCM equality. Ten generated macros/three repetitions: background discovery
26.6834 -> 0.0873 ms. benchmarks/query-capture-compute.json preserves original measurements;
scripts/query_capture_benchmark.py reproduces the method against trusted baseline f604ef7.
These are illustrative compute timings, not a controlled live-load/acoustic acceptance result
or proof of the cause of every observed overrun. Owner printer definitions/audio were not used.

Numeric diagnostics retain lifetime input peak, last captured-block RMS, zero-frame count,
maximum DSP work and latest queue delay, with timing opt-out respected. They do not retain
microphone audio. Device metadata does not change selection. Generated event/attempt IDs now
remain correlatable while arbitrary secret-like fields stay redacted; old redacted IDs cannot
be reconstructed. Existing logging/transcript choices are preserved, including logging OFF
for fresh profiles. The owner-confirmed BEACN input remains selected for this installation.

Installer `Klippy-Setup-0.7.2-preview.1.exe`: 1489908266 bytes.
SHA-256: `0c308b113082c2bca18ba328d005e4d659ace77b909c497012775b79b0095238`.

Evidence: benchmarks/preview72-release-qualification.json and frozen/installed/wake/memory
reports; benchmarks/preview72-initial-query-failure.json and query-capture-native-query.json.
Unsigned engineering preview, not stable v1.0. Human microphone/room recognition, sustained
BEACN/device load, interactive focus/DPI/taskbar/sleep, clean Windows VM, actual 16 GB machine
and supervised physical-printer acceptance remain open. No microphone recordings or owner
conversations/configurations/credentials committed.
