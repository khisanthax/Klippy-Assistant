# 0.6 preview — floating voice waveform orb

Software candidate; publication awaits exact-source Windows build and installed
qualification. All 510 previous regressions and the 0.5.1 safety foundation are preserved.
No physical printer actions, owner recordings or owner-installation changes.

## Behavior

The circular translucent PySide6 orb replaces the rectangular companion. It uses the
existing Klippy mark, glow ring, state label and active-printer name. Settings → Voice Orb
controls enablement, diameter (128–384 logical pixels; default 192), clock/custom position,
three-second default hide delay, printer/status labels, intensity, pinning and animations.
192 pixels means two nominal inches at 96 logical DPI; physical display sizes vary.
Dragging stays within the safe work area; the menu resets above the taskbar clock.
Private backups include validated orb preferences; recovery still revokes printer approval,
heater limits and microphone enablement. Orb settings cannot change those permissions.

Wake candidates immediately show **Verifying wake**, distinct from verified **Listening**.
Listening requires both microphone permission and an opened existing capture stream.
**Thinking** covers transcription, interpretation and TTS preparation; **Speaking** requires
real rendered PCM. **Confirm?** follows the exact SafetyEngine pending action until it
completes, cancels or expires. Errors show brief red **Attention**, manual muted summons
show a slashed microphone, and ordinary idle stays hidden. Existing conversation expiry
drives the fade. Pinning keeps the orb open. Animations off/Windows reduced motion use
static presentation. No independent conversation or authorization clock is added.

Only bounded numeric RMS/peak envelopes come from existing echo-cleaned capture and render
callbacks. A nonblocking producer try-lock drops telemetry when contended. No second
microphone, audio-device thread, network client, PCM recording or transcript store is
created. The visible Qt timer runs at 33 ms, stops when hidden, and uses 100 ms for static
state refresh. Geometry checks run once a second. Render activity has a 150 ms smoothing
tail; numeric peaks expire after 200 ms. Generation-tagged events reject old UI updates;
rejected ASR finishes processing, and old synthesis failures cannot interrupt newer work.

## Geometry and Windows behavior

The tray-icon monitor is preferred, with primary fallback. Read-only native monitor and
taskbar-window observations supplement Qt work areas and detect per-monitor auto-hide.
Native origins also match Qt friendly names when GDI identifiers differ. Conversion is
relative to each monitor's origin; the 10 physical pixel gap rounds within 8–12 pixels at
100/125/150/200%. Auto-hide reserves its full dock strip. Shell-observation failure uses
Qt work areas, reserving a conservative bottom strip if no taskbar exclusion is available.
Custom positions clamp and recover to an available monitor after disconnect.

Topmost frameless tool flags provide no taskbar entry, transparent corners, no keyboard
focus and nonactivating display. Only explicit double-click/Open Klippy opens the panel.
Geometry signals and the bounded refresh respond to display/work-area/DPI changes.
Implementation references: [Qt high DPI](https://doc.qt.io/qt-6/highdpi.html),
[tray geometry](https://doc.qt.io/qt-6/qsystemtrayicon.html),
[Qt window attributes](https://doc.qt.io/qtforpython-6/PySide6/QtCore/Qt.html),
[Windows taskbar geometry](https://learn.microsoft.com/en-us/windows/win32/shell/abm-gettaskbarpos),
[per-monitor auto-hide](https://learn.microsoft.com/en-us/windows/win32/shell/abm-getautohidebarex),
[animation preference](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-systemparametersinfow).

## Development verification

58 new orb regressions cover states, real synthetic capture/render levels, wake candidate
verification, interruption/cancellation, rejected ASR, late synthesis failures, pending
confirmation, microphone readiness, timeouts, malformed preferences/atomic restore,
active-printer/settings controls, window flags and cleanup. Geometry tests cover four DPI
scales, four taskbar edges, auto-hide, tray monitor selection, dragging and disconnects.
The complete 568-case suite and Ruff must pass before packaging.

`--orb-self-test --smoke-report PATH` renders the actual Qt widget using synthetic PCM,
asserts eight states, nonactivation, transparent corners, three sizes, rendered-level
linkage, cleanup and hidden/disabled paint suppression. It writes widget-only captures
and short process CPU/memory samples. Frozen build and installed offline QA require it
alongside all unchanged native model/query/command/voice gates.

![Actual Windows Qt states with synthetic PCM](docs/images/orb-states.png)

[Native development evidence](benchmarks/preview6-orb-native.json): Windows Qt at 125%
rendered **30.43 paints/second**. Active CPU was **21.94% of one core**, versus **14.13%**
with the same 100 Hz synthetic audio producer and orb disabled: about **7.81 percentage
points** incremental CPU in these short, noisy samples. Hidden idle used **0.78%** of one
core and **zero animation paints**. Widget creation increased working set by about
**0.99 MiB** before screenshot buffers; the active interval had no working-set growth.
These process samples are not long-duration or actual 16 GB performance acceptance.

Native observations found bottom taskbars on all four current monitors at 100/125%
scaling. The actual widget remained nonactive in all captures. This verifies current
geometry/rendering, not every interactive desktop scenario.

## Qualification and remaining gates

Next: exact-source Windows CI, frozen startup/orb/native probes, actual 0.5.1 upgrade and
reinstall preserving SQLite/preferences, installed offline probes, uninstall preservation
and process-tree memory budget. Publish only an unsigned engineering prerelease after
matching CI/installer/sidecar digests, tagging the qualified source and verifying all
uploaded assets. The same AppId/settings path upgrades the existing preview.
Issue [#12](https://github.com/khisanthax/Klippy-Assistant/issues/12) tracks acceptance.

Open: real interactive Windows 10/11 100/125/150/200% scaling, auto-hide reveal/retract,
vertical taskbars, multi-monitor tray placement/hot-plug/resolution changes, Explorer
restart, full-screen/focus behavior, reduced motion and sleep/resume. Also open: human
microphone/room wake/interruption accuracy, supervised printer/fleet/MMU safety, clean
desktop VM and actual 16 GB hardware. Original continuous bare-Klippy/ASR failures remain
visible. Synthetic results do not close hardware/acoustic gates.
