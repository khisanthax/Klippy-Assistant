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

No model is currently approved for redistribution. models/manifest.json intentionally has
an empty asset inventory. Stable build gates reject it. A package license collector copies
installed distribution license files; final binary inventory/legal review remains a gate.

Project code is private. No public license grant is made by this repository.
