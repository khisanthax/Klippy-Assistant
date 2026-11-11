# Phase 2 — offline voice integration

Engineering preview 0.2.0. This is not stable v1.0.

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

The frozen model gate passed with its own bundled files and no device opens. It recognized
the requests, rejected own echo, verified the local LLM and interrupted simulated playback
at about 0.71 s. The 57-file payload is included in the single unsigned installer
(1,489,177,877 bytes; approximately 1.39 GiB). No post-install model download is required.

The Windows default capture/render smoke passed: 884 frames processed, TTS completed,
zero wake/utterance events from the assistant's own phrase, no recordings/transcripts
saved and zero printer connections. It exposed and fixed an existing COM apartment-mode
conflict after PortAudio initialization. This does not qualify human wake accuracy.

99 automated tests and Ruff passed locally; Windows test CI passed for dca8bab. Per-user
install, reinstall with isolated SQLite preservation, installed startup, installed
complete-model voice gate and uninstall/data preservation passed on the developer host.
The installed voice test used the installation files and made zero printer writes; its
synthetic interruption was detected at 1.23 s. Independent complete-model Windows build
CI passed: [run 43062031011](https://github.com/khisanthax/Klippy-Assistant/actions/runs/43062031011).
Source, frozen, installed and device evidence is
under benchmarks/.
Optional speaker enrollment remains deferred.
Microphone wake accuracy, unplug/replug, room echo behavior and supervised hardware
acceptance remain open. No live printer actions are permitted or performed in Phase 2.

## Run the voice preview

Run Klippy-Setup-0.2.0-preview.1.exe as a normal Windows user and open Klippy from Start.
Enable listening with the tray Microphone on/off control. The first local model load
takes several seconds; wait for the ready state. Say Klippy, or Hey Klippy, followed by
your request. Stop speaking is also available in the panel. The microphone starts off
unless a saved listening preference enables it. Spoken responses default on for new users.

The setup is unsigned. SHA256:
1cd1ccb981b7e7539c42b717e008ef3531ec39d0c1054afc2be34ab1b78e96c7.
Models load from the installation; no separate Ollama/Python/developer tool is required.
Human microphone calibration can be conducted without enrolling a printer; missing-printer
clarification is spoken locally. Do not test consequential printer actions unattended.

Release: https://github.com/khisanthax/Klippy-Assistant/releases/tag/v0.2.0-preview.1

Published as a private prerelease. The uploaded installer digest matches the checksum above.
