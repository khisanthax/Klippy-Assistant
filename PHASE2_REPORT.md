# Phase 2 — offline voice integration

Engineering preview 0.2.0; qualification in progress. This is not stable v1.0.

Implemented local KWS, Whisper tiny.en ONNX, Kokoro v1.0 ONNX speech, Qwen3 1.7B
Q4_K_M through an owned offline llama.cpp process, and Windows full-duplex capture/render.
The app loads its bundled model pack when listening is enabled; runtime never downloads
models. Speech and language inference have no printer execution authority.

The wake model now includes pronunciation-equivalent BPE spellings for Klippy and Hey
Klippy. Clippy is a homophone and cannot be excluded acoustically by spelling. The old
short-word synthetic failure is fixed in the recorded probes. Room/microphone accuracy
and false-positive rates still require labeled recordings and user calibration.

Duplex processing uses WebRTC AEC3 and a confidence-checked, reference-trained linear
echo path that preserves near-end speech. AEC3 alone suppressed a short wake syllable
in a double-talk test. During playback, a second local ASR path may verify the exact
wake prefix; it never forwards an action or confirms a request. Playback buffers,
transcriptions and queued speech are generation-bound. Changing the target, muting,
discontinuity or interruption invalidates stale audio/inference. Spoken confirmations
retain the exact token present when capture began, rather than looking up a later request.

Synthetic real-model probes passed: two voices recognized Klippy, Hey Klippy and the
stop-talking variants; clipper and ordinary-speech probes were rejected. Echo of Klippy's
own wake/action/confirmation text created zero requests. A synthetic near-end interruption
stopped playback around 0.74 s after speech began and transcribed Klippy stop talking.
These are small synthetic tests, not a measured physical-room latency or accuracy claim.

The curated pack excludes the old VITS/CMU-in-IPA lexicon and all eSpeak dictionaries.
It uses Apache-2.0 Kokoro weights/voices and a lexicon generated from BSD-2-Clause
CMUdict data. CMUdict's GPL Python wrapper is a build tool only and is explicitly excluded
from the frozen app. KWS is Apache-2.0, Whisper weights are MIT, Qwen is Apache-2.0,
llama.cpp is MIT with LLVM OpenMP notices. All model/binary/data/notice files are hashed
in models/manifest.json, with license evidence and notices. WebRTC, RNNoise, PFFFT,
Abseil, JSON and ONNX Runtime notices accompany the application.

Remaining checks at this snapshot: final frozen model gate, single-installer build and
installed-model verification, independent Windows build CI, complete default-device smoke
test and updated benchmark evidence. Optional speaker enrollment remains deferred.
Microphone wake accuracy, unplug/replug, room echo behavior and supervised hardware
acceptance remain open. No live printer actions are permitted or performed in Phase 2.
