# 0.7.1 engineering preview - wake verification and Attention diagnostics

Candidate: exact-source full tests, Windows CI, frozen and installer qualification pending.
Unsigned preview; human/acoustic, interactive desktop/clean VM, actual 16 GB and supervised
printer gates remain open. No physical printer command is part of this work.

## Verified cause and limits of the evidence

The owner authorized inspection of existing local history; logging was already enabled.
The relevant stored attempts contain wake_prefix_rejected after ASR, with wake_detected true.
That means the keyword detector produced a candidate, but the ASR transcript did not match
the strict wake-prefix allowlist. Earlier records include verified wake, read-only follow-ups
and completed playback. The affected records do not show a device failure or TTS exception.
The history stores ASR output, not independent evidence of what was spoken. No microphone
audio exists or was recorded. Owner transcripts, printer facts, timestamps, IDs, configuration
and credentials are not copied into this repository or release evidence.

0.7.0's deterministic path is:
KWS candidate -> ASR -> failed strict prefix -> wake_prefix_rejected -> message
Wake transcript unclear -> VoiceOrb.pipeline_event substring unclear -> Attention for 2.5 s.
A synthetic rejected-ASR fixture reproduces this complete path without devices or printers.
The old history did not save orb transitions, so the exact visual frame of the owner's
attempt cannot be reconstructed from storage alone. The matching code path is reproduced.

A second bug is independently reproduced: starting a new wake verification does not clear
an older Attention timer. Old errors can therefore color a new attempt red, even though
old VoiceLoop owners and playback generations are already filtered by the application.
There is no evidence that stale delivery, rather than prefix rejection, caused the reported
attempts. Both paths now have regression coverage and explicit diagnostic timestamps/status.

## Recognition recovery without uncertain acceptance

Primary KWS sensitivity and strict textual wake allowlist stay unchanged. For a short
candidate (250 ms-3 s, at most three recognized words), outside output/echo context, the
ASR worker may retry verification once as a bounded protocol:

1. A separate verifier using the same qualified KWS weights must pass a threshold at least
   0.5 and at least the configured primary threshold, with lower keyword boost (1 vs 2).
2. Two fresh ASR streams transcribe the same unmodified clip with different silence context.
   Both results must match the complete strict wake-only allowlist.
3. Only canonical Klippy is forwarded, with no command and no confirmation token.

No fuzzy spelling, LLM interpretation, synthetic spoken prompt or guessed command is used.
Disagreement, cancellation, mute, changed generation, echo context or an unverified phonetic
result remains rejected. Normal combined wake/command behavior and all SafetyEngine policies
remain. Any wake-only input also drops old confirmation context; it cannot approve an action.
No consequential operation is retried. PCM stays bounded in memory and is never recorded.
The extra verifier uses existing licensed model assets; no new model download or TTS change.

## Attention reasons and local diagnostics

Broad substring classification is replaced with explicit event definitions for wake rejection,
empty/failed ASR, capture discontinuity, DSP/device failure, queue saturation, TTS failure,
playback receipt failure, processing timeout, application error and printer alert. A successful
new wake clears the previous attempt's Attention timer; stale owner/generation and muted ASR
failures are logged as discarded and cannot affect the orb. Rejected input remains rejected.

Hover over Attention for its reason; the accessible description includes it. The orb's
right-click menu shows the reason and Copy latest diagnostic. Diagnostics / History also has
Copy latest diagnostic. Single-click still mutes capture immediately; the reason does not
change that established safety control. No recent diagnostic copies an explicit none_available
message rather than leaving unrelated clipboard contents to be mistaken for a diagnostic.

Optional history remains default OFF for new profiles; existing preferences are preserved.
Enabled history records exact code, voice stage, event and transition timestamp, epoch,
attempt ID, session ID/state, accepted/discarded status, bounded voice counters and orb
transitions. A pre-verification attempt is explicitly not_opened; it never creates an
authorized conversation just for logging. Events correlate with the existing reaction/ASR row.
Original/recheck transcripts are consent-filtered and redacted; revoking text consent removes
nested event text too. Copy includes associated transcript only from consent-filtered history.
No raw device/provider error, audio, credential, endpoint or confirmation token is copied.

## Qualification

New regressions cover rejected wake -> Attention, stale warnings, muted/replaced loops,
stage distinction, timestamps/attempt IDs, consent revocation, clipboard copying, strict
phonetic verification, two strict decodes, command/token exclusion, cancellation and echo.
The original 698 tests and every previous voice/query/heating/safety gate remain required.

The device-free native probe uses generated speech and the actual bundled ASR/KWS, no saved
PCM. It compares 18 positive variations and seven negatives; naturally ambiguous outputs
remain rejected. Natural recovery counts vary between generated-speech runs and are reported,
not required to be nonzero. A separately labeled injected first-ASR rejection is followed by
real stricter KWS and exactly two real ASR passes, then actual VoiceLoop wake-only delivery.
It must pass without new negative acceptances, command/token delivery or unbounded rechecks.
Frozen and installed --wake-self-test now qualify this path independently of the existing
full voice/acoustic diagnostic. This is not human microphone/room accuracy evidence.
