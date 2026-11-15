"""Passive Qt presentation of existing voice/session/confirmation state."""
import json
import math
import time
from collections import deque

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient, QRegion
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .orb_geometry import Rect, observe_windows, placement, reduced_motion
from .orb_settings import OrbPreferences, preferences
from .voice_diagnostics import definition, snapshot

COLORS = {
    "idle": ("#6c8ca5", "#3d566c"), "muted": ("#7a8795", "#434e5d"),
    "verifying": ("#54d8d2", "#d2a951"), "listening": ("#43e3d3", "#5df5a8"),
    "thinking": ("#b88aff", "#f4aa63"), "speaking": ("#63b6ff", "#eecf81"),
    "confirmation": ("#ffc069", "#e6a13d"), "error": ("#ff787f", "#b63c59"),
}
LABELS = {"idle":"Ready", "muted":"Mic off", "verifying":"Verifying wake", "listening":"Listening",
          "thinking":"Thinking", "speaking":"Speaking", "confirmation":"Confirm?", "error":"Attention"}


class VoiceOrb(QWidget):
    preferences_changed = Signal()

    def __init__(self, summon, store, icon, *, source=None, tray_geometry=None, clock=time.monotonic, mute=None, on_transition=None, diagnostic_provider=None):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle("Klippy Voice Orb")
        self.setAccessibleName("Klippy voice status")
        self.store, self.open_panel, self.clock, self.icon = store, summon, clock, icon
        self.source = source or (lambda: {})
        self.on_transition = on_transition or (lambda event: None)
        self.diagnostic_provider = diagnostic_provider
        self.latest_diagnostic = None
        self.event_epoch = -1
        self.event_owner = None
        self.toggle_microphone = mute
        self.tray_geometry = tray_geometry or (lambda: None)
        try:
            self.prefs = preferences(store.get("voice_orb", {}))
        except ValueError:
            self.prefs = OrbPreferences()
        self.state = "muted"
        self.phase, self.phase_at = "idle", clock()
        self.printer = "No active printer"
        self.error_until = self.manual_until = 0.0
        self.inactive_since = None
        self.microphone = deque([0.0]*32, maxlen=32)
        self.playback = deque([0.0]*32, maxlen=32)
        self.last_levels = (0.0, 0.0)
        self.playing = False
        self.countdown = 0.0
        self.motion_reduced = reduced_motion()
        self.drag_offset = None
        self.dragged = False
        self.stopped = False
        self.paint_count = 0
        self.animation = QTimer(self)
        self.animation.setTimerType(Qt.TimerType.PreciseTimer)
        self.animation.timeout.connect(self.refresh)
        self.geometry_timer = QTimer(self)
        self.geometry_timer.setInterval(1000)
        self.geometry_timer.timeout.connect(self.reposition)
        self.geometry_timer.start()
        app = QApplication.instance()
        app.screenAdded.connect(self.display_changed)
        app.screenRemoved.connect(self.display_changed)
        for screen in app.screens():
            self.watch_screen(screen)
        self.reposition()
        self.refresh()

    @property
    def notifications(self):
        return self.prefs.enabled

    @property
    def hide_seconds(self):
        return self.prefs.hide_delay

    @property
    def moving(self):
        return self.prefs.animations and not self.motion_reduced and self.prefs.intensity > 0

    def watch_screen(self, screen):
        for signal in (screen.geometryChanged, screen.availableGeometryChanged, screen.logicalDotsPerInchChanged):
            signal.connect(self.reposition)

    def display_changed(self, screen):
        if screen in QApplication.screens():
            self.watch_screen(screen)
        self.reposition()

    def configure(self, **changes):
        if self.stopped:
            return
        value = {**self.prefs.model_dump(mode="json"), **changes}
        self.prefs = preferences(value)
        self.store.set("voice_orb", self.prefs.model_dump(mode="json"))
        self.reposition()
        self.refresh()
        self.update()
        self.preferences_changed.emit()

    def reload_preferences(self):
        self.prefs = preferences(self.store.get("voice_orb", {}))
        self.reposition()
        self.refresh()
        self.update()
        self.preferences_changed.emit()

    def set_printer(self, text):
        if text != self.printer:
            self.printer = text
            self.update()

    def reposition(self, *_):
        if self.stopped or self.drag_offset is not None:
            return
        app = QApplication.instance()
        screens = app.screens()
        if not screens:
            return
        screen = app.primaryScreen() or screens[0]
        custom = None
        if self.prefs.position == "custom" and self.prefs.custom_position:
            custom = self.prefs.custom_position
            screen = next((s for s in screens if s.name() == self.prefs.custom_monitor),
                          app.screenAt(QPoint(*custom)) or screen)
        else:
            tray = self.tray_geometry()
            if tray and not tray.isEmpty():
                screen = app.screenAt(tray.center()) or screen
        bounds, work = screen.geometry(), screen.availableGeometry()
        def as_rect(r):
            return Rect(r.x(), r.y(), r.width(), r.height())
        self.desktop = observe_windows(screen.name(), as_rect(bounds), as_rect(work), screen.devicePixelRatio())
        self.monitor_name = screen.name()
        self.motion_reduced = reduced_motion()
        x, y, size = placement(self.desktop, self.prefs.diameter, custom)
        if self.width() != size or self.height() != size:
            self.setFixedSize(size, size)
            self.setMask(QRegion(self.rect(), QRegion.RegionType.Ellipse))
        if self.pos() != QPoint(x, y):
            self.move(x, y)

    def pipeline_event(self, text):
        epoch, owner = getattr(text, "epoch", None), getattr(text, "owner", None)
        if epoch is not None:
            if owner is self.event_owner and epoch < self.event_epoch:
                return
            if owner is not self.event_owner or epoch > self.event_epoch:
                self.error_until = 0
            self.event_epoch, self.event_owner = epoch, owner
        event = definition(text)
        message = str(text)
        if event and event.attention:
            self.latest_diagnostic = snapshot(text)
            self.phase = "idle"
            self.error_until = self.clock() + 2.5
        elif message == "Checking wake word":
            self.error_until = 0  # A previous attempt's warning cannot color a new verification.
            self.phase = "verifying"
        elif message in {"Thinking", "Speaking"}:
            self.phase = "thinking"
        elif message in {"Listening", "Microphone ready", "Speech finished", "Speech interrupted or failed",
                         "Default audio device changed; reconnecting"}:
            self.phase = "idle"
            if message == "Listening" or (message == "Microphone ready" and self.latest_diagnostic
                                          and self.latest_diagnostic["voice_stage"] == "device"):
                self.error_until = 0
        self.phase_at = self.clock()
        self.refresh()

    def copy_latest_diagnostic(self):
        value = self.diagnostic_provider() if self.diagnostic_provider else self.latest_diagnostic
        value = value or {"diagnostic": "none_available", "reason": "No recent voice diagnostic is available."}
        QApplication.clipboard().setText(json.dumps(value, indent=2))
        return value

    def announce(self, text, state="idle", *, force=False, code="application_error"):
        # Compatibility with companion notifications: never interprets or dispatches commands.
        if state == "error":
            self.latest_diagnostic = snapshot(text, code=code)
            self.error_until = self.clock()+2.5
            self.phase = "idle"
        if force:
            self.summon()
        self.refresh()

    def summon(self):
        self.manual_until = self.clock() + max(3, self.prefs.hide_delay)
        self.refresh()

    def clear_activity(self):
        self.phase, self.phase_at, self.error_until = "idle", self.clock(), 0
        self.microphone.clear()
        self.playback.clear()
        self.refresh()

    def refresh(self):
        if self.stopped:
            return
        data, now = self.source(), self.clock()
        mic = data.get("microphone_ready", False)
        session = data.get("session_active", False)
        self.playing = data.get("playing", False)
        levels = (data.get("microphone", 0.0) if mic else 0.0, data.get("playback", 0.0))
        self.last_levels = levels
        self.microphone.append(max(0.0, min(1.0, levels[0])))
        self.playback.append(max(0.0, min(1.0, levels[1])))
        old = self.state
        old_countdown = self.countdown
        if now < self.error_until:
            self.state = "error"
        elif data.get("pending", False):
            self.state = "confirmation"
        elif self.playing:
            self.state = "speaking"
        elif data.get("busy", False) or self.phase == "thinking":
            if now-self.phase_at < 95:
                self.state = "thinking"
            else:
                self.phase = "idle"
                self.latest_diagnostic = snapshot("", code="processing_timeout")
                self.error_until = now+2.5
                self.state = "error"
        elif mic and self.phase == "verifying":
            self.state = "verifying" if now-self.phase_at < 10 else "idle"
        elif mic and session:
            self.state = "listening"
        else:
            self.state = "idle" if mic else "muted"
        self.countdown = (max(0.0,min(1.0,data.get('followup_fraction',0.0)))
                          if self.prefs.show_countdown and mic and data.get('followup_ready',False)
                          and not data.get('busy',False) and self.phase != 'thinking'
                          and self.state in {'listening','confirmation'} else 0.0)
        active = self.state not in {"idle", "muted"} or data.get('clarification_active',False)
        manual = self.prefs.pinned or now < self.manual_until
        if active or manual:
            self.inactive_since = None
        elif self.inactive_since is None:
            self.inactive_since = now
        delay = now-(self.inactive_since if self.inactive_since is not None else now)-self.prefs.hide_delay
        visible = self.prefs.enabled and (active or manual or (self.isVisible() and mic and delay < .3))
        if visible:
            opacity = 1.0 if active or manual or delay < 0 or not self.moving else max(0, 1-delay/.3)
            if not self.moving and not active and not manual and delay >= 0:
                visible = False
            if visible:
                self.setWindowOpacity(opacity)
                if not self.isVisible():
                    self.reposition()
                    self.show()  # WA_ShowWithoutActivating; never activate/raise the main panel.
                interval = 33 if self.moving else 100
                if self.animation.interval() != interval or not self.animation.isActive():
                    self.animation.start(interval)
                if self.moving or old != self.state or old_countdown != self.countdown:
                    self.update()
        if not visible:
            self.hide()
            self.animation.stop()
        reason = self.latest_diagnostic["reason"] if self.state == "error" and self.latest_diagnostic else ""
        self.setToolTip(reason or "Klippy voice status. Right-click for the latest diagnostic.")
        self.setAccessibleDescription(f"{LABELS[self.state]} · {self.printer}" + (" · " + reason if reason else ""))
        if old != self.state and (old == "error" or self.state == "error") and self.latest_diagnostic:
            try:
                self.on_transition({**self.latest_diagnostic, "orb_from": old, "orb_to": self.state})
            except Exception:
                pass  # Optional diagnostics cannot affect capture or safety.


    def paintEvent(self, event):
        self.paint_count += 1
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scale = self.width()/192
        painter.scale(scale, scale)
        phase = self.clock() if self.moving else 0
        intensity = self.prefs.intensity if self.moving else 0
        a, b = (QColor(c) for c in COLORS[self.state])
        pulse = 1 + math.sin(phase*2.4)*.018*intensity
        gradient = QRadialGradient(96, 96, 96)
        for at, alpha in ((0,0), (.78,0), (.89,65), (.94,85), (1,0)):
            color = QColor(a)
            color.setAlpha(alpha)
            gradient.setColorAt(at, color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawEllipse(QRectF(0, 0, 192, 192))
        body = QRadialGradient(72, 58, 140)
        body.setColorAt(0, QColor(24, 36, 56, 244))
        body.setColorAt(1, QColor(7, 14, 26, 226))
        painter.setBrush(body)
        painter.setPen(QPen(QColor(76, 101, 131, 120), 1))
        painter.drawEllipse(QRectF(12, 12, 168, 168))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(a, 2.2*pulse))
        painter.drawArc(QRectF(11, 11, 170, 170), 18*16, 250*16)
        painter.setPen(QPen(b, 2.3))
        angle = int(phase*75) % 360 if self.state in {"thinking", "verifying"} else 285
        painter.drawArc(QRectF(11, 11, 170, 170), angle*16, 56*16)
        if self.countdown>0:
            painter.setPen(QPen(QColor('#ff444f'),3.5,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap))
            painter.drawArc(QRectF(22,22,148,148),90*16,-round(self.countdown*360*16))
        mark = self.icon.pixmap(round(26*scale*self.devicePixelRatioF()))
        painter.drawPixmap(QRectF(83, 29, 26, 26), mark, QRectF(mark.rect()))
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        painter.setPen(QColor("#a8bfd0"))
        painter.drawText(QRectF(38, 57, 116, 16), Qt.AlignmentFlag.AlignCenter, "K L I P P Y")
        if self.state == "muted":
            painter.setPen(QPen(a, 2.2))
            painter.drawRoundedRect(QRectF(90, 83, 12, 21), 6, 6)
            painter.drawArc(QRectF(84, 86, 24, 25), 180*16, 180*16)
            painter.drawLine(96, 110, 96, 116)
            painter.drawLine(81, 81, 111, 116)
        elif self.state == "thinking":
            painter.setPen(QPen(QColor(83, 66, 126, 140), 1))
            painter.drawEllipse(QRectF(64, 78, 64, 38))
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(3):
                painter.setBrush(a if i != 1 else b)
                y = 96 + math.sin(phase*3+i)*4*intensity
                painter.drawEllipse(QRectF(78+i*15, y-3, 6, 6))
        else:
            history = self.playback if self.playing else self.microphone if self.state in {"listening", "verifying"} else ()
            values = list(history)[-28:] if self.moving else []
            values = [0.0]*(28-len(values)) + values
            for i, level in enumerate(values):
                height = 2 + min(44, math.log1p(level*60)/math.log(61)*44)
                color = QColor(a if i % 4 else b)
                color.setAlpha(210)
                painter.setBrush(color)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(29+i*4.9, 97-height/2, 2.7, height), 1.3, 1.3)
        if self.prefs.show_status:
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
            painter.setPen(a)
            painter.drawText(QRectF(28, 123, 136, 22), Qt.AlignmentFlag.AlignCenter, LABELS[self.state])
        if self.prefs.show_printer:
            painter.setFont(QFont("Segoe UI", 8))
            painter.setPen(QColor("#b8c7d6"))
            name = painter.fontMetrics().elidedText(self.printer, Qt.TextElideMode.ElideRight, 132)
            painter.drawText(QRectF(30, 146, 132, 18), Qt.AlignmentFlag.AlignCenter, name)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.globalPosition().toPoint()-self.pos()
            self.dragged = False

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.dragged = True
            point = event.globalPosition().toPoint()-self.drag_offset
            screen = QApplication.screenAt(event.globalPosition().toPoint()) or QApplication.primaryScreen()
            def rect(r):
                return Rect(r.x(), r.y(), r.width(), r.height())
            desktop = observe_windows(screen.name(), rect(screen.geometry()), rect(screen.availableGeometry()),
                                      screen.devicePixelRatio())
            x, y, _ = placement(desktop, self.width(), (point.x(), point.y()))
            self.move(x, y)

    def mouseReleaseEvent(self, event):
        if self.drag_offset is not None:
            self.drag_offset = None
            if self.dragged:
                screen = QApplication.screenAt(self.geometry().center()) or QApplication.primaryScreen()
                self.configure(position="custom", custom_position=[self.x(), self.y()], custom_monitor=screen.name())
            elif self.toggle_microphone:
                self.toggle_microphone()

    def mouseDoubleClickEvent(self, event):
        self.open_panel()  # Focus only after this explicit user action.

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        if self.latest_diagnostic:
            reason = menu.addAction(self.latest_diagnostic["reason"])
            reason.setEnabled(False)
        menu.addAction("Copy latest diagnostic", self.copy_latest_diagnostic)
        menu.addSeparator()
        pin = menu.addAction("Pin open")
        pin.setCheckable(True)
        pin.setChecked(self.prefs.pinned)
        pin.triggered.connect(lambda value: self.configure(pinned=value))
        reset = menu.addAction("Reset above taskbar clock")
        reset.triggered.connect(lambda: self.configure(position="clock", custom_position=None))
        menu.addAction("Open Klippy", self.open_panel)
        menu.exec(event.globalPos())

    def shutdown(self):
        if self.stopped:
            return
        self.stopped = True
        self.animation.stop()
        self.geometry_timer.stop()
        self.hide()
        self.source = lambda: {}
        app = QApplication.instance()
        app.screenAdded.disconnect(self.display_changed)
        app.screenRemoved.disconnect(self.display_changed)
        for screen in app.screens():
            for signal in (screen.geometryChanged, screen.availableGeometryChanged, screen.logicalDotsPerInchChanged):
                try:
                    signal.disconnect(self.reposition)
                except RuntimeError:
                    pass

    def closeEvent(self, event):
        self.shutdown()
        event.accept()
