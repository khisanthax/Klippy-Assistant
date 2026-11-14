# 0.6.1 preview - conversation continuity and speech playback

Exact-source Windows engineering qualification passed; human/hardware acceptance remains open.

The existing shared Session already holds the countdown during interpretation and speech.
Investigation reproduced another path that bypassed that protection: the duplex callback
collapsed every PortAudio status into `bool(status)`. Even output-only underflow/overflow
then followed the lost-input path and asynchronously cleared the shared session. This is
a reproduced failure class, not recovered owner audio or telemetry. See the official
[CallbackFlags documentation](https://python-sounddevice.readthedocs.io/en/latest/api/misc.html).

Output-only faults now reset the AEC reference and partial capture without closing the
microphone or clearing the shared conversation. They invalidate spoken confirmation
delivery, so a broken prompt cannot arm an action. Actual input loss, unknown flags,
device loss and capture queue overflow still require a fresh wake word. Separate numeric
output-discontinuity/session-reset counters support further diagnosis without recording
audio or transcripts. No output or printer operation is automatically retried.

Speech capture atomically holds an already-active session before VAD/ASR, so a question
started just before expiry retains its context. This hold cannot open an expired session;
mute invalidates it permanently. Generation checks reject old capture frames.

ASR now refreshes the configured shared Session timeout rather than a separate hard-coded
voice-loop duration. Existing processing/playback holds stay intact; countdown begins
after rendered buffers and the DAC/echo tail finish. Muting clears permission before
resetting the session, immediately rejects queued capture and invalidates old generations.
It also invalidates in-flight UI results and clears busy/pending-delivery state, so an
old slow response cannot reappear or play after mute.
Unmuting leaves the session closed until a fresh validated wake. A single stationary orb
click toggles the microphone; dragging still changes position. Existing session snapshots
keep the orb visible/Listening until expiry, followed by its configured fade.

610 tests preserve the previous 568. New regressions cover real CallbackFlags, callback-to-
DSP output/input-loss behavior, three actual captured exchanges after one wake with 90 s
ASR and TTS delays, playback-based countdown, configured timeout, expiry, immediate orb
mute/unmute and failed confirmation delivery. Existing echo, barge-in, background/no-wake,
confirmation token and LLM-delay regressions remain mandatory. Simulated printers only.

The native frozen/installed/budgeted voice probe now requires three unprefixed follow-up
requests after one Hey Klippy wake, and verifies all three simulated status responses.
This is additional to the original preview gates; original broad acoustic results remain
separate. Required before publication: full tests/Ruff, frozen startup/orb/native probes,
actual 0.6 upgrade/reinstall, offline installed runtime, settings/uninstall preservation,
memory budget and release checksum verification.

Human microphone/room, full Windows interactive desktop matrix, clean desktop VM, actual
16 GB hardware and supervised physical printer acceptance remain open. Models unchanged.

## Speech distortion investigation

Compared original 24 kHz Kokoro PCM, SDK chunks, old 16 kHz conversion and the actual
production TTS worker/output callback using synthetic speech only. Original PCM was finite,
unclipped (peak 0.337), and exactly equal to concatenated SDK chunks. The old renderer copied
converted PCM exactly. Two upstream delivery defects were reproduced: independent linear
resampling lost fractional phase at chunk boundaries and had no antialias rejection; on this
loaded host Kokoro generated 8.54 seconds of speech in 10.25 seconds, starving immediate
playback. These establish software defects, not a recovered diagnosis of the owner's recording.

A stateful 97-tap Kaiser-windowed sinc converter now runs on the TTS worker, retaining phase
and history across chunks. A 10 kHz test tone's aliased output improved from -2.73 dB to
-107.42 dB; chunked conversion now equals continuous conversion (old peak difference 0.139).
The actual cached production worker and callback reproduced all 136607 expected samples.
No denoiser is used; original synthesis models and 16 kHz echo-cancellation path are retained.

A 120 ms queue prefill and bounded 0–2 second producer-rate reserve precede playback.
On the identical measured arrival schedule, replay starvation fell from 0.70 seconds to zero,
at a first-audio tradeoff of 3.64 to 4.95 seconds. This is a synthetic schedule replay, not
physical device latency. Conversion used 0.359 versus 0.063 CPU seconds for 273.21 seconds
of speech: about 0.11 percentage points of one CPU core extra, excluding synthesis. Short
CPU measurements are quantized and load-dependent. Cached/complete short replies avoid the
producer reserve. Buffer waits never sleep in the audio callback or pause microphone capture;
interruption discards the stream immediately. A failed, silent, clipped or starved confirmation
cannot authorize an action. No heating or other printer write was tested on physical hardware.

Numeric diagnostics expose queue/device underruns, missing samples, invalid/clipped PCM,
source/render peaks, callback work/gaps and reported device latency, without recordings.
WASAPI shared-mode format checks accepted 16/24/48 kHz against the existing 96 kHz device mix.
Four quiet speaker-only tests, including controlled 30 ms callback stalls, reported no device
underruns or clipping; hardware underruns were not reproduced. Output-only requested buffering
increased reported latency from 26.125 to 90 ms. In the brief duplex check, microphone samples
were immediately discarded: input 22.25 ms/output 36.125 ms were unchanged for both settings.
This driver did not honor the increased output request in duplex. These are PortAudio reports,
not acoustic latency measurements. No device configuration was changed.

Reproduce with `scripts/audio_quality_probe.py` (device-free synthetic PCM),
`scripts/speaker_quality_probe.py` (explicit speaker-only audit), and the existing separate
`audio_device_probe.py` for its established device diagnostics. Numeric evidence is retained
in `benchmarks/audio61-*.json`; no speech recordings are committed. Packaged qualification
now additionally requires the synthetic signal/delivery checks and real cached TTS callback
comparison. Human perceived static/crackle, room/microphone and longer device-load acceptance
remain open even when these numeric gates pass.

Reference: [sounddevice streams/latency](https://python-sounddevice.readthedocs.io/en/latest/api/streams.html)
and [official Sherpa TTS progress API](https://github.com/k2-fsa/sherpa-onnx/blob/master/sherpa-onnx/csrc/offline-tts.h).

CLI argument validation now precedes heavy native/ML imports, correcting a reproduced
15-second invalid-argument timeout without weakening its test. Mute invalidates both success
and error responses from an old in-flight UI request.

## Slower-host correction found by packaged qualification

Candidate cc64a72's frozen audit completed in 137.645 seconds and correctly rejected its
remaining starvation: Kokoro took 13.67 seconds for 8.55 seconds of speech (RTF 1.60).
The two-second streaming reserve still left a 0.96-second gap. Candidate was not released.
When estimated reserve exceeds two seconds, playback now waits for complete generated PCM;
fast/cached replies retain streaming. Replaying the exact CI chunk sizes/arrival schedule
with a synthetic harmonic input gives zero starvation and first PCM at 13.67 seconds, versus
4.80 seconds with 2.95 seconds of gaps originally. This deliberately trades first-audio
latency for continuity on slow hosts; microphone capture, processing/session holds and
immediate interruption remain active throughout. Numeric complete_pcm_fallbacks exposes it.
The regression preserves the observed schedule and tests interruption/EOF behavior. The
original 180-second whole-probe cap was exceeded by an earlier candidate; 300-second
orchestration caps and durable stage checkpoints now retain useful failure evidence.
No behavioral/signal/memory gate was removed. 610 tests preserve all previous cases.

## Exact-source Windows qualification

Qualified app source `f9565e0f9afc1fbb64facbec6e70c750b4565d4d` in [Windows run](https://github.com/khisanthax/Klippy-Assistant/actions/runs/43615190106), attempt 1.
610 tests and Ruff passed. Frozen and installed startup/orb passed. Upgrade from 0.6.0,
reinstall, external-network-blocked runtime, settings preservation and uninstall preservation
passed. The process-tree 16 GiB budget passed; this is not actual 16 GB hardware qualification.

- frozen: all engineering gates passed; audio signal/delivery passed; three follow-ups verified; broad original voice result `True`; probe 87.719 s; generation RTF 0.905; new replay gaps 0.0 s.
- installed: all engineering gates passed; audio signal/delivery passed; three follow-ups verified; broad original voice result `False`; probe 150.171 s; generation RTF 1.745; new replay gaps 0.0 s.
- budgeted: all engineering gates passed; audio signal/delivery passed; three follow-ups verified; broad original voice result `True`; probe 146.424 s; generation RTF 1.637; new replay gaps 0.0 s.

Installer: `Klippy-Setup-0.6.1-preview.1.exe`, 1489813001 bytes.
SHA-256: `311c013d7bae1a1af3d9971a09b4ff2c556346bb1a4c45f7287604cb5ceaf5d3`. Full source-bound evidence:
`benchmarks/preview61-release-qualification.json` and its frozen/installed/memory reports.
Failed/superseded candidate evidence and original broad acoustic results remain retained.
Human perceived sound quality, long device-load, microphone/room, clean desktop VM, actual
16 GB hardware and supervised physical-printer acceptance remain open. This is an unsigned
engineering preview, not stable v1.0. No physical printer actions were executed.
