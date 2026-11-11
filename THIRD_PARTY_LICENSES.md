# Third-party inventory

The development environment uses the versions in requirements-lock.txt. Complete bundled
license texts must accompany distribution. Model rights are independent of runtime licenses.

| Component | License / action |
|---|---|
| Python | PSF License; include Python notices in frozen distribution |
| PySide6 / Shiboken / Qt | LGPLv3/GPLv3/commercial alternatives; use eligible dynamic libraries, include notices/license texts and preserve replacement/relink rights; review actual bundled Qt modules |
| httpx, httpcore, anyio, websockets | Review installed distribution license metadata and include notices |
| Pydantic, pydantic-core | MIT; include notices |
| keyring and jaraco dependencies | Review installed distribution notices |
| zeroconf | LGPL-2.1-or-later; include license/source reference and preserve rights |
| sherpa-onnx | Apache-2.0 runtime; models need individual license review |
| NumPy | BSD-3-Clause plus bundled binary notices |
| sounddevice / PortAudio | MIT-style; include bundled binary notices |
| PyInstaller | GPL exception permits frozen app distribution; include applicable bootloader notice |
| Inno Setup | Include compiler/distribution obligations as applicable |
| llama.cpp candidate | MIT; not bundled until approved asset inventory exists |
| Qwen3 1.7B GGUF candidate | Apache-2.0 according to official model card; not yet downloaded/qualified |

The Phase 2 model pack is approved for engineering-preview bundling based on the recorded
publisher license statements and notices. models/manifest.json lists every included model,
binary, data and notice hash plus primary license evidence. This is separate from acoustic
accuracy, clean-machine qualification and stable-release acceptance.

| Bundled Phase 2 component | License / provenance |
|---|---|
| GigaSpeech KWS ONNX | Apache-2.0 model card and maintainer clarification |
| Whisper tiny.en ONNX | MIT original weights; converted export under the same weight rights |
| Kokoro v1.0 ONNX and voices | Apache-2.0 upstream card and converted archive license |
| Generated English lexicon | BSD-2-Clause CMUdict data, original ARPABET-to-IPA recipe; no CMU-in-IPA/eSpeak data |
| Qwen3 1.7B Q4_K_M | Apache-2.0; pinned GGUF revision and upstream LFS checksum |
| llama.cpp b12110 CPU DLLs/server | MIT; bundled LLVM OpenMP uses Apache-2.0 with LLVM exception |
| WebRTC DSP wrapper | Apache-2.0; WebRTC BSD/PATENTS, Abseil, PFFFT, RNNoise and JSON notices included |
| ONNX Runtime 1.28.2 | MIT and upstream third-party notices included |

CMUdict's Python wrapper is GPL-3.0-or-later and is a build-time tool only. It is excluded
from the frozen app, as is SentencePiece. The dictionary's independent BSD data notice
is included in the model pack. Old VITS and third-party IPA lexicons are not bundled.

GNU LGPLv3/GPLv3 texts and dynamic Qt replacement/source information are additionally
included under packaging/licenses and copied into the installed license directory. The
Qt source archive directory URLs were checked successfully on 2026-11-11.
Experimental Phase 1 model cards/checksums remain in models/candidates.json for history.
The production manifest and PHASE2_REPORT.md describe the selected replacement assets.

Project code is private. No public license grant is made by this repository.
