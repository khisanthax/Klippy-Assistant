"""Device-free actual Qt rendering, native geometry and measured orb overhead."""
import ctypes
import math
import os
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PySide6.QtCore import QEventLoop, QRectF, QTimer
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter

from .orb import VoiceOrb
from .orb_geometry import Rect, observe_windows
from .storage import Store
from .voice import VoiceLoop


def memory():
    if os.name != "nt":
        return {}
    from ctypes import wintypes as w
    class Counters(ctypes.Structure):
        _fields_ = [("cb", w.DWORD), ("faults", w.DWORD),
                    *[(key, ctypes.c_size_t) for key in ("peak_working", "working", "peak_paged", "paged",
                                                       "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile", "private")]]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel, psapi = ctypes.windll.kernel32, ctypes.windll.psapi
    kernel.GetCurrentProcess.restype = w.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, ctypes.POINTER(Counters), w.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return {}
    return {"working_set_bytes": counters.working, "private_bytes": counters.private}


def run(app, icon, report_path):
    # Font registration also permits useful offscreen CI captures on headless runners.
    font = Path("C:/Windows/Fonts/segoeui.ttf")
    if font.is_file():
        QFontDatabase.addApplicationFont(str(font))
    images = report_path.parent / (report_path.stem+"-images")
    images.mkdir(parents=True, exist_ok=True)
    checks, frames = {}, []
    with tempfile.TemporaryDirectory(prefix="klippy-orb-") as temp:
        store = Store(Path(temp)/"settings.sqlite")
        backend = SimpleNamespace(wake=lambda _: False, reset_wake=lambda: None)
        voice = VoiceLoop(backend, lambda _: None, lambda _: None)
        data = {"microphone_ready": True, "session_active": False}
        before_orb = memory()
        orb = VoiceOrb(lambda: None, store, icon, source=lambda: {**voice.levels.snapshot(), **data})
        after_orb = memory()
        orb.set_printer("Simulated M1")
        reduced = orb.motion_reduced
        try:
            checks["idle_hidden"] = not orb.isVisible() and not orb.animation.isActive()
            geometry = asdict(orb.desktop)
            desktops = []
            for screen in app.screens():
                def rect(r):
                    return Rect(r.x(), r.y(), r.width(), r.height())
                desktops.append(asdict(observe_windows(screen.name(), rect(screen.geometry()),
                                                       rect(screen.availableGeometry()), screen.devicePixelRatio())))
            checks["clear_of_taskbar"] = (orb.y()+orb.height() <= orb.desktop.work.bottom and
                                          orb.y() >= orb.desktop.work.y)

            def pump(seconds):
                loop = QEventLoop()
                QTimer.singleShot(round(seconds*1000), loop.quit)
                loop.exec()

            def capture(name):
                app.processEvents()
                picture = orb.grab().toImage()
                picture.save(str(images/(name+".png")))
                frames.append((name, picture))
                checks[name] = orb.state == name
                checks["non_activating_"+name] = not orb.isActiveWindow()

            orb.summon()
            capture("idle")
            orb.pipeline_event("Checking wake word")
            for i in range(32):
                voice.levels.publish("microphone", .04+.09*math.sin(i*.3)**2)
                orb.refresh()
            capture("verifying")
            data["session_active"] = True
            orb.pipeline_event("Listening")
            capture("listening")
            orb.pipeline_event("Thinking")
            capture("thinking")
            voice.playback.enqueue(np.full(160*32, .15, dtype=np.float32), voice.epoch)
            for i in range(32):
                voice._render(160)
                orb.refresh()
            capture("speaking")
            data["pending"] = True
            orb.refresh()
            capture("confirmation")
            data["pending"] = False
            voice.interrupt()
            orb.clear_activity()
            checks["interruption_clears_playback"] = not orb.playing and orb.state == "listening"
            orb.pipeline_event("Speech recognition unavailable")
            capture("error")
            orb.clear_activity()
            data.update(microphone_ready=False, session_active=False)
            orb.summon()
            capture("muted")
            checks["transparent_corners"] = frames[-1][1].pixelColor(0, 0).alpha() == 0

            sheet = QImage(4*230, 2*240, QImage.Format.Format_ARGB32)
            sheet.fill(QColor("#101b2a"))
            painter = QPainter(sheet)
            painter.setFont(QFont("Segoe UI", 10))
            painter.setPen(QColor("#d2e2ed"))
            for i, (label, picture) in enumerate(frames):
                x, y = i % 4*230, i//4*240
                painter.drawImage(QRectF(x+19, y+8, 192, 192), picture)
                painter.drawText(QRectF(x, y+204, 230, 30), 0x84, label.capitalize())
            painter.end()
            sheet.save(str(images/"orb-states.png"))
            for diameter in (128, 256, 384):
                orb.configure(diameter=diameter)
                app.processEvents()
                checks["diameter_"+str(diameter)] = orb.width() == diameter
                orb.grab().save(str(images/("diameter-"+str(diameter)+".png")))
            orb.configure(diameter=192)

            def measure(seconds):
                start_cpu, start, paints = time.process_time(), time.perf_counter(), orb.paint_count
                before = memory()
                pump(seconds)
                elapsed = time.perf_counter()-start
                return {"seconds": elapsed, "cpu_percent_of_one_core": (time.process_time()-start_cpu)/elapsed*100,
                        "paints": orb.paint_count-paints, "paints_per_second": (orb.paint_count-paints)/elapsed,
                        "before": before, "after": memory()}

            orb.manual_until = 0
            orb.refresh()
            hidden = measure(2)
            checks["hidden_has_no_animation_paints"] = hidden["paints"] == 0
            data.update(microphone_ready=True, session_active=True)
            orb.pipeline_event("Listening")
            # 100 Hz producer uses the actual capture/render functions; no PortAudio stream.
            voice.enabled.set()
            count = [0]
            def audio():
                count[0] += 1
                level = .03+.1*math.sin(count[0]*.09)**2
                near = np.full(160, level, dtype=np.float32)
                voice.process_frame(near, np.zeros(160, dtype=np.float32), voice.clock())
            producer = QTimer()
            producer.timeout.connect(audio)
            producer.start(10)
            active = measure(3)
            orb.configure(enabled=False)
            disabled = measure(2)
            producer.stop()
            checks["active_animation_rendered"] = active["paints"] >= (1 if reduced else 30)
            checks["disabled_has_no_animation_paints"] = disabled["paints"] == 0
            checks["no_audio_devices_or_printers"] = not voice.threads and not voice.capture_ready.is_set()
            orb.shutdown()
            checks["cleanup"] = not orb.animation.isActive() and not orb.geometry_timer.isActive() and not orb.isVisible()
            from .features_probe import run as features_probe
            features = features_probe(app,images)
            checks['conversation_features'] = features['passed']
            return {"passed": all(checks.values()), "checks": checks, "qt_platform": app.platformName(),
                    'conversation_features':features,
                    "device_pixel_ratio": orb.devicePixelRatioF(), "desktop": geometry,
                    "observed_desktops": desktops,
                    "windows_reduced_motion": reduced, "performance": {"hidden": hidden, "active": active,
                    "disabled_with_same_audio_producer": disabled,
                    "before_widget": before_orb, "after_widget": after_orb}, "screenshots": str(images),
                    "scope": "Actual Qt widget; synthetic PCM and printer label; zero devices/network/hardware actions",
                    "limitations": ["single current desktop only; multi-DPI/auto-hide permutations are unit simulations",
                                    "short process CPU/working-set measurements; not owner room, clean VM or actual 16 GB acceptance"]}
        finally:
            orb.close()
            voice.close()
            store.close()
