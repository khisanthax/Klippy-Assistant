# 0.6.1 preview — follow-up capture and conversation recovery

Candidate pending exact-source Windows qualification; no physical printer actions.

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

ASR now refreshes the configured shared Session timeout rather than a separate hard-coded
voice-loop duration. Existing processing/playback holds stay intact; countdown begins
after rendered buffers and the DAC/echo tail finish. Muting clears permission before
resetting the session, immediately rejects queued capture and invalidates old generations.
Unmuting leaves the session closed until a fresh validated wake. A single stationary orb
click toggles the microphone; dragging still changes position. Existing session snapshots
keep the orb visible/Listening until expiry, followed by its configured fade.

579 tests preserve the previous 568. New regressions cover real CallbackFlags, callback-to-
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
