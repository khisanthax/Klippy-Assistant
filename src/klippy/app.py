from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .conversation import Conversation
from .diagnostics import current, timings
from .domain import Printer
from .listening import listening_enabled, validate_windows
from .macros import discover, inferred_parameters
from .models import ModelUnavailable, verify_pack
from .monitor import Monitor
from .moonraker import ConnectionFailure, Moonraker
from .queries import QueryService
from .query_manager import QueryManager
from .runtime import LlamaRuntime
from .safety import Rejected, SafetyEngine
from .storage import Credentials, Store, data_directory


class Worker(QObject):
    result = Signal(str, object)
    error = Signal(str)

    def __init__(self):
        super().__init__()
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def submit(self, name, coroutine):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        def done(f):
            try:
                self.result.emit(name, f.result())
            except (Rejected, ConnectionFailure, ModelUnavailable) as exc:
                self.error.emit(str(exc))
            except Exception:
                self.error.emit("Operation failed safely. No automatic command retry; check the printer if a request was sent.")
        future.add_done_callback(done)

    def close(self):
        async def cancel_all():
            tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        asyncio.run_coroutine_threadsafe(cancel_all(), self.loop).result(timeout=8)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=3)
        self.loop.close()


def companion_icon(state="idle", frame=0):
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor({"error": "#ef8b81", "muted": "#92a3ac", "thinking": "#b6a0e9"}.get(state, "#61d6b0")))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(5, 12, 54, 44, 14, 14)
    painter.setBrush(QColor("#102524"))
    painter.drawEllipse(18, 25, 7, 10)
    painter.drawEllipse(39, 25, 7, 10)
    painter.drawRoundedRect(23, 40 if state == "speaking" and frame % 2 else 43, 18,
                           9 if state == "speaking" and frame % 2 else 3, 2, 2)
    painter.end()
    return QIcon(pixmap)


class Sprite(QWidget):
    def __init__(self, summon, store):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        self.icon = QLabel()
        self.icon.setPixmap(companion_icon().pixmap(64, 64))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("Klippy")
        self.label.setStyleSheet("background:#17352f;color:#c4f6e5;padding:8px;border-radius:8px")
        layout.addWidget(self.icon)
        layout.addWidget(self.label)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.summon = summon
        self.store = store
        self.hide_seconds = store.get("companion_seconds", 10)
        self.notifications = store.get("companion_notifications", True)
        self.offset = QPoint()
        position = store.get("companion_position", [60, 100])
        point = QPoint(*position)
        if not any(screen.availableGeometry().contains(point) for screen in QApplication.screens()):
            point = QPoint(60, 100)
        self.move(point)
        self.state = "idle"
        self.frame = 0
        self.animation = QTimer(self)
        self.animation.timeout.connect(self.animate)
        self.animation.start(180)

    def animate(self):
        if self.isVisible():
            self.frame += 1
            self.icon.setPixmap(companion_icon(self.state, self.frame).pixmap(64, 64))

    def announce(self, text, state="idle", *, force=False):
        if not self.notifications and not force:
            return
        self.state = state
        self.label.setText(text[:100])
        self.adjustSize()
        self.show()
        self.timer.start(int(self.hide_seconds * 1000))

    def mousePressEvent(self, event):
        self.offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)

    def mouseReleaseEvent(self, event):
        self.store.set("companion_position", [self.x(), self.y()])

    def mouseDoubleClickEvent(self, event):
        self.summon()


class Window(QMainWindow):
    def __init__(self, store, *, smoke=False):
        super().__init__()
        self.store = store
        self.smoke = smoke
        self.voice = None
        self.runtime = LlamaRuntime()
        self.discovery = None
        self.turn = 0
        self.voice_loading = False
        self.voice_failed = False
        self.worker = Worker()
        self.worker.result.connect(self.result)
        self.worker.error.connect(self.failure)
        self.client_cache = {}
        self.queries = QueryService(store, self.client)
        self.engine = SafetyEngine(store, self.client)
        self.conversation = Conversation(self.engine, queries=self.queries)
        self.engine.confirmation_seconds = self.store.get("confirmation_seconds", 30)
        self.conversation.timeout = self.conversation.session.timeout = self.store.get("followup_seconds", 30)
        self.monitor = Monitor(store, self.client, queries=self.queries)
        self.polling = False
        self.command_busy = False
        self.quitting = False
        self.setWindowTitle(f"Klippy Assistant · {__version__} · Engineering preview")
        self.setWindowIcon(companion_icon())
        self.resize(940, 680)
        self.sprite = Sprite(self.summon, store)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.make_console()
        self.make_fleet()
        self.make_macros()
        self.query_manager = QueryManager(store, self.queries, self.refresh_capabilities,
                                         self.voice_availability,
                                         self.edit_printer_aliases)
        self.tabs.addTab(self.query_manager, "Queries && Commands")
        self.make_settings()
        self.tray = QSystemTrayIcon(companion_icon(), self)
        menu = QMenu()
        for title, slot in [("Show Klippy", self.summon), ("Show companion", self.show_sprite),
                            ("Microphone on/off", self.toggle_listening), ("Quit", self.quit)]:
            action = QAction(title, self)
            action.triggered.connect(slot)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.summon() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        if not smoke:
            self.tray.show()
        self.reload_printers()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000)
        self.ticks = 0
        self.last_session_until = 0.0

    def client(self, printer):
        key = Credentials.get(printer.id)
        client = self.client_cache.get(printer.id)
        if client is None or client.printer != printer or client.api_key != key:
            client = Moonraker(printer, key)
            client.status_observer = lambda value, acquired: self.queries.observe(printer.id, value, acquired, identity=printer.url)
            self.client_cache[printer.id] = client
        return client

    def voice_availability(self):
        enabled = getattr(self.voice, "enabled", None)
        if enabled and enabled.is_set():
            return "Voice enabled; models loaded"
        return "Models loaded; microphone off" if self.voice else "Typed available; load models for voice"

    def refresh_capabilities(self):
        async def refresh():
            semaphore = asyncio.Semaphore(4)
            async def one(printer):
                async with semaphore:
                    await self.queries.refresh(printer, force=True)
            await asyncio.gather(*(one(p) for p in self.store.printers() if p.approved))
        self.worker.submit("capabilities", refresh())

    def edit_printer_aliases(self):
        from PySide6.QtWidgets import QInputDialog
        printer = self.target()
        if printer is None:
            self.failure("Select an approved printer first")
            return
        text, accepted = QInputDialog.getText(self, "Printer voice aliases", "Comma-separated alternate names", text=", ".join(printer.aliases))
        if accepted:
            try:
                updated = printer.model_copy(update={"aliases": tuple(a.strip() for a in text.split(",") if a.strip())})
                updated = Printer.model_validate(updated.model_dump())
                self.engine.cancel()
                self.store.save_printer(updated)
                self.reload_printers()
            except ValueError:
                self.failure("Use up to twelve short, distinct aliases")

    def page(self, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
        if title == "Settings":
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(widget)
            self.tabs.addTab(scroll, title)
        else:
            self.tabs.addTab(widget, title)
        return layout

    def button(self, label, callback):
        button = QPushButton(label)
        button.clicked.connect(callback)
        return button

    def make_console(self):
        layout = self.page("Companion")
        title = QLabel("KLIPPY  /  Local printer companion")
        title.setStyleSheet("font-size:23px;font-weight:600;color:#70dfbd")
        layout.addWidget(title)
        self.selected = QComboBox()
        self.selected.currentIndexChanged.connect(self.select_printer)
        layout.addWidget(self.selected)
        self.state_label = QLabel("Microphone off · Monitoring enabled · No cloud AI")
        layout.addWidget(self.state_label)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.document().setMaximumBlockCount(50)
        layout.addWidget(self.output)
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask for status, temperatures, pause, or an approved macro…")
        self.input.returnPressed.connect(self.send)
        layout.addWidget(self.input)
        row = QHBoxLayout()
        self.send_button = self.button("Send", self.send)
        self.confirm_button = self.button("Confirm pending action", self.confirm)
        self.confirm_button.setEnabled(False)
        row.addWidget(self.send_button)
        row.addWidget(self.confirm_button)
        row.addWidget(self.button("Cancel request", self.cancel))
        row.addWidget(self.button("Stop speaking", self.stop_speaking))
        layout.addLayout(row)
        layout.addWidget(QLabel("Preview: voice requires a verified local model pack. Every printer action requires confirmation.\n"
                                "Voice control supplements the printer's physical safety controls."))

    def make_fleet(self):
        layout = self.page("Printers")
        layout.addWidget(QLabel("Only explicitly approved printers can be controlled. Discovery never enrolls automatically."))
        self.fleet = QTableWidget(0, 5)
        self.fleet.setHorizontalHeaderLabels(["Name", "Endpoint (private)", "Approval", "Status", "Happy Hare"])
        self.fleet.horizontalHeader().setStretchLastSection(True)
        self.fleet.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.fleet.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.fleet)
        row = QHBoxLayout()
        row.addWidget(self.button("Add printer", self.add_printer))
        row.addWidget(self.button("Test selected", self.test_printer))
        row.addWidget(self.button("Approve selected", self.approve_printer))
        row.addWidget(self.button("Remove selected", self.remove_printer))
        row.addWidget(self.button("Discover LAN", self.discover_printers))
        layout.addLayout(row)
        self.discovered = QLabel("Discovery idle")
        self.discovered.setWordWrap(True)
        layout.addWidget(self.discovered)

    def make_macros(self):
        layout = self.page("Macros")
        layout.addWidget(QLabel("New, renamed, changed, and restored macros require review. Select a row to inspect its definition."))
        self.macro_table = QTableWidget(0, 4)
        self.macro_table.setHorizontalHeaderLabels(["Macro", "Voice approval", "Parameters", "Fingerprint"])
        self.macro_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.macro_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.macro_table.itemSelectionChanged.connect(self.inspect_macro)
        layout.addWidget(self.macro_table)
        self.definition = QTextEdit()
        self.definition.setReadOnly(True)
        layout.addWidget(self.definition)
        row = QHBoxLayout()
        row.addWidget(self.button("Refresh from printer", self.refresh_macros))
        row.addWidget(self.button("Review / approve", self.approve_macro))
        row.addWidget(self.button("Exclude from voice", self.exclude_macro))
        layout.addLayout(row)

    def make_settings(self):
        layout = self.page("Settings")
        self.model_status = QLabel("Voice disabled: verified model pack not loaded")
        self.model_status.setWordWrap(True)
        layout.addWidget(self.model_status)
        layout.addWidget(self.button("Load local voice pack", self.load_voice))
        layout.addWidget(self.button("Review selected printer heater limits", self.review_heater_limits))
        self.sensitivity = QDoubleSpinBox()
        self.sensitivity.setRange(0.01, 1.0)
        self.sensitivity.setSingleStep(0.01)
        self.sensitivity.setValue(self.store.get("wake_threshold", 0.22))
        self.sensitivity.valueChanged.connect(lambda v: self.store.set("wake_threshold", v))
        layout.addWidget(QLabel("Wake detection threshold (lower is more sensitive; reload pack after changing)"))
        layout.addWidget(self.sensitivity)
        for key, label in [("followup_seconds", "Follow-up window after each response (seconds)"),
                           ("confirmation_seconds", "Confirmation response window after speech (seconds)")]:
            spin = QDoubleSpinBox()
            spin.setObjectName(key)
            spin.setRange(10, 120)
            spin.setDecimals(0)
            spin.setValue(self.store.get(key, 30))
            spin.valueChanged.connect(lambda value, setting=key: self.save_timeout(setting, value))
            layout.addWidget(QLabel(label))
            layout.addWidget(spin)
        layout.addWidget(QLabel("Confirmations are enabled by default. Disabling a prompt below allows an explicit request to act immediately. "
                                "Enrollment, state, limits and fresh validation always apply. Macros, critical operations and model interpretations always require confirmation."))
        for action in ("pause", "resume", "cancel", "home", "heat"):
            check = QCheckBox("Confirm " + action)
            check.setChecked(self.store.get("confirmations", {}).get(action, True) is not False)
            check.toggled.connect(lambda enabled, operation=action: self.save_confirmation(operation, enabled))
            layout.addWidget(check)
        self.diagnostics = QLabel(timings.compact())
        self.diagnostics.setWordWrap(True)
        layout.addWidget(self.diagnostics)
        layout.addWidget(self.button("Measure reaction with simulated printer", self.reaction_test))
        self.listening = QComboBox()
        self.listening.addItems(["manual", "scheduled", "always"])
        self.listening.setCurrentText(self.store.get("listening", {}).get("mode", "manual"))
        layout.addWidget(QLabel("Listening mode (independent of printer monitoring)"))
        layout.addWidget(self.listening)
        self.schedule = QLineEdit(json.dumps(self.store.get("listening", {}).get("windows", [])))
        self.schedule.setPlaceholderText('[{"days":[0,1,2,3,4],"start":540,"end":1020}]')
        layout.addWidget(QLabel("Schedule windows: weekdays 0–6, minutes after midnight"))
        layout.addWidget(self.schedule)
        row = QHBoxLayout()
        row.addWidget(self.button("Save schedule", self.save_schedule))
        row.addWidget(self.button("Toggle microphone", self.toggle_listening))
        row.addWidget(self.button("Clear manual override", self.clear_override))
        layout.addLayout(row)
        self.monitor_enabled = QCheckBox("Monitor enrolled printers for faults")
        self.monitor_enabled.setChecked(self.store.get("monitor_enabled", True))
        self.monitor_enabled.toggled.connect(lambda v: self.store.set("monitor_enabled", v))
        layout.addWidget(self.monitor_enabled)
        self.spoken = QCheckBox("Speak responses and fault notifications")
        self.spoken.setChecked(self.store.get("spoken", True))
        self.spoken.toggled.connect(self.save_spoken)
        layout.addWidget(self.spoken)
        row = QHBoxLayout()
        row.addWidget(self.button("Export configuration", self.export_config))
        row.addWidget(self.button("Restore configuration", self.restore_config))
        layout.addLayout(row)
        layout.addWidget(QLabel("No recordings or transcripts are saved. Configuration exports contain private printer\n"
                                "addresses and definitions; keep them private. Credentials stay in the Windows vault.\n"
                                "Voice interruption uses local echo cancellation. Microphone/room calibration remains necessary.\n"
                                "Optional speaker enrollment is not enabled."))
        companion = QCheckBox("Show companion notifications")
        companion.setChecked(self.sprite.notifications)
        companion.toggled.connect(lambda value: (self.store.set("companion_notifications", value),
                                                  setattr(self.sprite, "notifications", value)))
        layout.addWidget(companion)
        duration = QDoubleSpinBox()
        duration.setRange(2, 120)
        duration.setValue(self.sprite.hide_seconds)
        duration.valueChanged.connect(lambda value: (self.store.set("companion_seconds", value),
                                                       setattr(self.sprite, "hide_seconds", value)))
        layout.addWidget(QLabel("Companion auto-hide delay (seconds)"))
        layout.addWidget(duration)
        for label in layout.parentWidget().findChildren(QLabel):
            label.setWordWrap(True)
        layout.addStretch()

    def review_heater_limits(self):
        printer = self.target()
        if not printer or not printer.approved:
            self.failure("Select an approved printer before reviewing heater limits")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Review heater limits for " + printer.name)
        form = QFormLayout(dialog)
        notice = QLabel("Enter maximum temperatures verified against this printer's configuration/specification. "
                        "Unknown limits block heating. Saving changes only local permissions.")
        notice.setWordWrap(True)
        form.addRow(notice)
        limits = self.store.get("heater_limits", {}).get(printer.id, {})
        controls = {}
        for key, label in (("0", "Nozzle maximum Celsius"), ("1", "Bed maximum Celsius")):
            control = QDoubleSpinBox()
            control.setRange(0, 1000)
            control.setValue(limits.get(key, 0))
            controls[key] = control
            form.addRow(label, control)
        verified = QCheckBox("I verified these limits for " + printer.name)
        form.addRow(verified)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted and verified.isChecked():
            current_printer = self.target()
            if current_printer != printer:
                self.failure("Printer changed during review; review its limits again")
                return
            values = self.store.get("heater_limits", {})
            values[printer.id] = {key: control.value() for key, control in controls.items()}
            self.engine.cancel()
            self.store.set("heater_limits", values)
            self.write_message("Locally reviewed heater limits saved for " + printer.name)

    def reaction_test(self):
        if self.engine.pending:
            self.write_message("Finish or cancel the pending action before measuring a reaction.")
            return
        from .reaction_probe import run
        self.worker.submit("reaction", run())

    def save_spoken(self, enabled):
        self.store.set("spoken", enabled)
        if not enabled:
            if self.engine.pending and not self.engine.pending.ready:
                self.engine.delivery_finished(self.engine.pending.token, False)
            self.stop_speaking()

    def save_confirmation(self, action, enabled):
        preferences = self.store.get("confirmations", {})
        preferences[action] = enabled
        self.store.set("confirmations", preferences)
        self.cancel()

    def save_timeout(self, key, value):
        self.store.set(key, int(value))
        if key == "confirmation_seconds":
            self.engine.confirmation_seconds = int(value)
        else:
            self.conversation.timeout = self.conversation.session.timeout = int(value)

    def reload_printers(self):
        printers = self.store.printers()
        self.selected.blockSignals(True)
        self.selected.clear()
        self.selected.addItem("Select an approved printer", None)
        for p in printers:
            if p.approved:
                self.selected.addItem(p.name, p.id)
        index = self.selected.findData(self.store.get("selected"))
        self.selected.setCurrentIndex(max(index, 0))
        self.selected.blockSignals(False)
        self.fleet.setRowCount(len(printers))
        for row, p in enumerate(printers):
            state = self.monitor.previous.get(p.id)
            mmu = self.monitor.mmu.get(p.id)
            progress = f"{state.progress:.0%}" if state and state.progress is not None else "Progress unavailable"
            status = (f"{state.state} · {progress}" if state.connected else "Disconnected") if state else "Not polled"
            mmu_text = f"{mmu.state}; tool {mmu.tool}; gate {mmu.gate}" if mmu and mmu.available else "Unavailable / not fitted"
            for col, text in enumerate((p.name, p.url, "Approved" if p.approved else "Needs approval", status, mmu_text)):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, p.id)
                self.fleet.setItem(row, col, item)
        self.fleet.resizeColumnsToContents()
        self.reload_macros()
        if hasattr(self, "query_manager"):
            self.query_manager.reload()

    def select_printer(self):
        printer_id = self.selected.currentData()
        if printer_id:
            self.engine.select(printer_id)
            self.conversation.clear()
        else:
            self.engine.cancel()
            self.store.set("selected", None)
        if self.voice:
            self.voice.pending_token = None
            self.voice.reset_session()
        self.reload_macros()

    def target(self):
        return next((p for p in self.store.printers() if p.id == self.store.get("selected")), None)

    def fleet_target(self):
        row = self.fleet.currentRow()
        if row < 0:
            return None
        pid = self.fleet.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((p for p in self.store.printers() if p.id == pid), None)

    def add_printer(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Enroll a printer")
        form = QFormLayout(dialog)
        name, url, secret = QLineEdit(), QLineEdit("http://"), QLineEdit()
        aliases = QLineEdit()
        secret.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Friendly name", name)
        form.addRow("Voice aliases (comma-separated)", aliases)
        form.addRow("LAN Moonraker URL", url)
        form.addRow("API key (optional; OS vault)", secret)
        approve = QCheckBox("I approve this printer for control after reviewing commands")
        form.addRow(approve)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                if any(p.name.casefold() == name.text().strip().casefold() for p in self.store.printers()):
                    raise ValueError("Duplicate name")
                printer = Printer(id=uuid.uuid4().hex, name=name.text(), url=url.text(), approved=approve.isChecked(),
                                  aliases=tuple(a.strip() for a in aliases.text().split(",") if a.strip()))
                Credentials.set(printer.id, secret.text())
                self.store.save_printer(printer)
                self.reload_printers()
                self.worker.submit("capabilities", self.queries.refresh(printer, force=True))
            except Exception:
                self.failure("Printer not saved. Check the name, URL and Windows credential vault.")

    def test_printer(self):
        printer = self.fleet_target()
        if printer:
            async def test():
                snapshot = await self.client(printer).snapshot()
                await self.queries.refresh(printer, force=True)
                return snapshot
            self.worker.submit("test", test())

    def approve_printer(self):
        printer = self.fleet_target()
        if printer:
            self.engine.cancel()
            self.store.save_printer(printer.model_copy(update={"approved": True}))
            self.reload_printers()
            self.worker.submit("capabilities", self.queries.refresh(printer, force=True))

    def remove_printer(self):
        printer = self.fleet_target()
        if printer:
            self.engine.cancel()
            self.queries.invalidate(printer.id)
            self.client_cache.pop(printer.id, None)
            Credentials.set(printer.id, "")
            self.store.remove_printer(printer.id)
            self.reload_printers()

    def discover_printers(self):
        from .discovery import Discovery
        try:
            if self.discovery is None:
                self.discovery = Discovery()
            self.discovered.setText("Scanning for Moonraker advertisements. Results appear here; use Add printer to enroll.")
        except Exception:
            self.failure("LAN discovery unavailable. Use manual enrollment.")

    def reload_macros(self):
        registry = self.store.macros(self.store.get("selected"))
        self.macro_table.setRowCount(len(registry))
        for row, macro in enumerate(sorted(registry.values(), key=lambda m: m.name)):
            values = (macro.name, "Enabled" if macro.approved and macro.enabled else "Excluded / needs review",
                      ", ".join(inferred_parameters(macro.definition)), macro.fingerprint[:12])
            for col, value in enumerate(values):
                self.macro_table.setItem(row, col, QTableWidgetItem(value))
        self.macro_table.resizeColumnsToContents()

    def macro_target(self):
        row = self.macro_table.currentRow()
        item = self.macro_table.item(row, 0) if row >= 0 else None
        return self.store.macros(self.store.get("selected")).get(item.text()) if item else None

    def inspect_macro(self):
        macro = self.macro_target()
        if not macro:
            self.definition.clear()
            return
        import difflib

        from .macros import conflicts
        warnings = [*macro.review_notes, *conflicts(self.store.macros(self.store.get("selected")))]
        diff = ""
        if macro.previous_definition is not None:
            diff = "\n\nChanges (previous/current):\n" + "\n".join(difflib.unified_diff(
                macro.previous_definition.splitlines(), macro.definition.splitlines(), fromfile="previous", tofile="current", lineterm=""))
        self.definition.setPlainText("\n".join(warnings) + f"\n{macro.description}\n\n{macro.definition}" + diff)

    def refresh_macros(self):
        printer = self.target()
        if printer:
            async def refresh():
                config = await self.client(printer).macro_config()
                registry, notices = discover(config, self.store.macros(printer.id))
                self.store.replace_macros(printer.id, registry)
                return notices
            self.engine.cancel()
            self.worker.submit("macros", refresh())

    def approve_macro(self):
        macro, printer = self.macro_target(), self.target()
        if not macro or not printer:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Review macro safety")
        form = QFormLayout(dialog)
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(macro.definition)
        form.addRow("Actual definition", view)
        aliases = QLineEdit(", ".join(macro.aliases))
        form.addRow("Optional aliases (comma separated)", aliases)
        params = QLineEdit(json.dumps({k: v.model_dump() for k, v in macro.parameters.items()}))
        form.addRow("Numeric parameter rules (JSON)", params)
        reviewed = QCheckBox("I reviewed the complete macro and its callees; idle-only voice use is appropriate")
        form.addRow(reviewed)
        form.addRow(QLabel("All macros require confirmation. Unknown/dynamic parameters remain blocked."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted and reviewed.isChecked():
            try:
                from .domain import Macro
                value = macro.model_dump(mode="json")
                value.update(approved=True, enabled=True, reviewed=True, previous_definition=None, review_notes=[],
                             parameters=json.loads(params.text()),
                             aliases=[a.strip() for a in aliases.text().split(",") if a.strip()])
                approved = Macro.model_validate_json(json.dumps(value))
                registry = self.store.macros(printer.id)
                if registry.get(macro.name) is None or registry[macro.name].fingerprint != macro.fingerprint:
                    raise ValueError("Registry changed during review")
                registry[macro.name] = approved
                self.engine.cancel()
                self.store.replace_macros(printer.id, registry)
                self.reload_macros()
            except Exception:
                self.failure("Review not saved: invalid parameter rules")

    def exclude_macro(self):
        macro, printer = self.macro_target(), self.target()
        if macro and printer:
            registry = self.store.macros(printer.id)
            registry[macro.name] = macro.model_copy(update={"approved": False, "enabled": False})
            self.engine.cancel()
            self.store.replace_macros(printer.id, registry)
            self.reload_macros()

    def send(self):
        if self.command_busy:
            return
        text = self.input.text().strip()
        self.input.clear()
        if text:
            self.submit_turn(text)

    def submit_turn(self, text, *, source="manual", confirmation_token=None, trace=None):
        if self.voice:
            self.voice.interrupt()
        self.turn += 1
        turn = self.turn
        self.command_busy = True
        self.send_button.setEnabled(False)
        trace = trace or timings.new()
        self.reaction_trace = trace
        defer_confirmation = bool(self.voice and self.spoken.isChecked())
        async def request():
            context = current.set(trace)
            try:
                with timings.span("intent_and_validation"):
                    value = await self.conversation.hear(text, source=source, confirmation_token=confirmation_token,
                                                         defer_confirmation=defer_confirmation)
                return turn, value, False
            except (Rejected, ConnectionFailure) as exc:
                return turn, str(exc), True
            finally:
                current.reset(context)
        self.worker.submit("turn", request())

    def confirm(self):
        if self.engine.pending and self.engine.pending.ready and not self.command_busy:
            self.command_busy = True
            self.submit_turn("confirm", source="voice", confirmation_token=self.engine.pending.token)

    def cancel(self):
        self.turn += 1
        self.conversation.clear()
        if self.voice:
            self.voice.pending_token = None
            self.voice.interrupt()
        self.command_busy = False
        self.send_button.setEnabled(True)
        self.write_message("Pending action canceled.")

    def stop_speaking(self):
        if self.voice:
            self.voice.interrupt()

    def write_message(self, text):
        self.output.insertPlainText(str(text) + "\n")
        self.output.ensureCursorVisible()

    def failure(self, text):
        self.command_busy = False
        self.send_button.setEnabled(True)
        self.polling = False
        self.write_message(text)
        self.sprite.announce(self.active_name() + " · Needs attention", "error")
        self.say(text)

    def result(self, name, value):
        if name == "capabilities":
            self.query_manager.reload()
        elif name == "reaction":
            trace, text = value
            if self.voice and self.spoken.isChecked() and self.engine.pending is None:
                self.voice.say(text, trace=trace)
            self.diagnostics.setText(timings.compact())
        elif name == "poll":
            self.polling = False
            self.reload_printers()
            for printer_name, code in value:
                text = f"{printer_name}: {code}. No corrective action taken."
                self.write_message(text)
                self.sprite.announce(text, "error")
                self.tray.showMessage("Klippy · Printer alert", text, QSystemTrayIcon.MessageIcon.Warning, 10000)
                self.say(text)
        elif name == "macros":
            self.reload_macros()
            self.write_message("Macro registry refreshed. " + "; ".join(value))
        elif name == "test":
            self.write_message(f"Read-only connection test: connected={value.connected}, state={value.state}")
        elif name == "voice_loaded":
            from .voice import VoiceLoop
            backend, llm = value
            self.voice_loading = False
            self.voice = VoiceLoop(backend, self.voice_text, lambda text: self.worker.result.emit("voice_state", text),
                                   lambda epoch: self.worker.result.emit("voice_wake", epoch),
                                   session=self.conversation.session,
                                   on_delivery=lambda token, ok: self.worker.result.emit("delivery", (token, ok)))
            self.voice.start()
            self.conversation.llm = llm
            self.model_status.setText("Offline voice loaded · Echo cancellation and wake-word interruption active" +
                                     (" · LLM unavailable; basic commands available" if llm is None else ""))
        elif name == "delivery":
            token, success = value
            self.engine.delivery_finished(token, success)
        elif name == "voice_wake":
            if self.voice and value == self.voice.epoch and self.voice.enabled.is_set():
                self.turn += 1
                if self.engine.pending and not self.engine.pending.ready:
                    self.engine.delivery_finished(self.engine.pending.token, False)
                self.conversation.interrupt(activate=False)
                self.voice.pending_token = self.engine.pending.token if self.engine.pending else None
                self.command_busy = False
                self.send_button.setEnabled(True)
        elif name == "voice_state":
            self.model_status.setText(value)
            if value == "Listening":
                self.sprite.announce(self.active_name() + " · Listening", "listening")
            elif value == "Speaking":
                self.sprite.state = "speaking"
            elif value == "Speech finished" and self.conversation.until:
                self.sprite.announce(self.active_name() + " · Listening", "listening")
        elif name == "voice_input":
            if self.voice and self.voice.enabled.is_set() and value.epoch == self.voice.epoch:
                self.submit_turn(value.text, source="voice", confirmation_token=value.confirmation_token, trace=value.trace)
        elif name == "turn":
            turn, value, error = value
            if turn != self.turn:
                return
            self.command_busy = False
            self.send_button.setEnabled(True)
            if error:
                self.failure(value)
                return
            if value and value != "speech_stopped":
                self.write_message(value)
                self.sprite.announce(self.active_name() + " · Responding", "speaking")
                self.say(value, confirmation=True)
            elif value == "speech_stopped":
                self.stop_speaking()
            self.reload_printers()
            if self.voice:
                self.voice.pending_token = self.engine.pending.token if self.engine.pending else None

    def voice_text(self, text):
        self.worker.result.emit("voice_input", text)

    def say(self, text, *, confirmation=False):
        if self.engine.pending and not confirmation:
            return  # Alerts remain visible; preserve a quiet confirmation response window.
        if self.voice and self.spoken.isChecked():
            pending = self.engine.pending
            self.voice.say(text, token=pending.token if confirmation and pending and not pending.ready else None,
                           trace=getattr(self, "reaction_trace", None) if confirmation else timings.new())
        elif confirmation and self.engine.pending and not self.engine.pending.ready:
            self.engine.delivery_finished(self.engine.pending.token, True)

    def load_voice(self):
        path = QFileDialog.getExistingDirectory(self, "Select verified local model pack")
        if path:
            self.store.set("model_pack", path)
            self.load_voice_path(Path(path))

    def load_voice_path(self, root):
        if self.voice_loading:
            return
        self.voice_loading = True
        self.voice_failed = False
        self.model_status.setText("Loading local voice models…")
        async def load():
            from .voice import SherpaBackend
            try:
                manifest = await asyncio.to_thread(verify_pack, root, require_qualified=True)
                backend = await asyncio.to_thread(SherpaBackend, root, manifest["speech_config"],
                                                  self.store.get("wake_threshold", 0.22))
                try:
                    llm = await self.runtime.start(root)
                except ModelUnavailable:
                    llm = None
                return backend, llm
            except BaseException:
                self.voice_loading = False
                self.voice_failed = True
                raise
        if self.voice:
            self.voice.close()
            self.voice = None
        self.worker.submit("voice_loaded", load())

    def save_schedule(self):
        try:
            windows = validate_windows(json.loads(self.schedule.text()))
            self.store.set("listening", {"mode": self.listening.currentText(), "windows": windows,
                                         "enabled": False})
        except ValueError:
            self.failure("Schedule must be a JSON list of time windows")

    def toggle_listening(self):
        settings = self.store.get("listening", {})
        settings["override"] = not listening_enabled(settings, datetime.now())
        self.store.set("listening", settings)
        self.conversation.clear()
        if self.voice:
            self.voice.reset_session()

    def clear_override(self):
        settings = self.store.get("listening", {})
        settings.pop("override", None)
        self.store.set("listening", settings)

    def export_config(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export private configuration", "klippy-backup.json", "JSON (*.json)")
        if path:
            self.store.export(Path(path))

    def restore_config(self):
        path, _ = QFileDialog.getOpenFileName(self, "Restore private configuration", "", "JSON (*.json)")
        if path:
            try:
                self.engine.cancel()
                backup = self.store.restore(Path(path))
                self.cancel()
                if self.voice:
                    self.voice.reset_session()
                self.reload_printers()
                for key in ("confirmation_seconds", "followup_seconds"):
                    self.findChild(QDoubleSpinBox, key).setValue(self.store.get(key, 30))
                self.spoken.setChecked(self.store.get("spoken", True))
                self.monitor_enabled.setChecked(self.store.get("monitor_enabled", True))
                self.listening.setCurrentText("manual")
                self.schedule.setText("[]")
                self.write_message("Previous SQLite settings backed up to " + str(backup))
                self.write_message("Restored. Printers and macros require reapproval; credentials were not imported.")
            except Exception:
                self.failure("Backup invalid; configuration was not restored")

    def active_name(self):
        printer = self.target()
        return printer.name if printer else "No active printer"

    def show_sprite(self):
        self.sprite.announce(self.active_name(), force=True)

    def tick(self):
        self.ticks += 1
        self.diagnostics.setText(timings.compact())
        enabled = listening_enabled(self.store.get("listening", {}), datetime.now())
        if self.voice:
            (self.voice.enabled.set if enabled else self.voice.enabled.clear)()
        elif enabled and not self.voice_loading and not self.voice_failed and not self.smoke:
            from .models import bundled_pack
            root = Path(self.store.get("model_pack")) if self.store.get("model_pack") else bundled_pack()
            if root:
                self.load_voice_path(root)
        self.state_label.setText(f"{self.active_name()} · Microphone {'enabled' if enabled and self.voice else 'off'} · "
                                 f"Monitoring {'enabled' if self.monitor_enabled.isChecked() else 'off'}")
        pending = self.engine.pending
        if pending and self.engine.clock() >= pending.expires:
            self.engine.cancel()
            pending = None
        self.confirm_button.setEnabled(pending is not None and pending.ready and not self.command_busy)
        if self.voice:
            self.voice.pending_token = pending.token if pending else None
        if self.runtime.process and self.runtime.process.poll() is not None:
            self.conversation.llm = None
            self.runtime.close()
            self.model_status.setText("Local language engine stopped; basic commands and monitoring remain available")
        if self.ticks % 5 == 0 and not self.polling and self.monitor_enabled.isChecked() and not self.smoke:
            self.polling = True
            self.worker.submit("poll", self.monitor.poll())
        if self.discovery:
            self.discovered.setText("\n".join(self.discovery.found.values()) or "No Moonraker advertisements found")
        if (not self.command_busy and self.conversation.until and
                self.conversation.clock() >= self.conversation.until):
            self.output.clear()
            self.conversation.clear()

    def summon(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        if self.smoke or not QSystemTrayIcon.isSystemTrayAvailable():
            event.accept()
            self.quit()
        else:
            event.ignore()
            self.hide()

    def quit(self):
        if self.quitting:
            return
        self.quitting = True
        self.timer.stop()
        self.engine.cancel()
        if self.voice:
            self.voice.close()
        if self.discovery:
            self.discovery.close()
        self.worker.close()
        self.runtime.close()
        self.tray.hide()
        self.sprite.hide()
        QApplication.instance().quit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--show", action="store_true", help="Open control panel on startup")
    parser.add_argument("--smoke-test", action="store_true", help="Launch/close UI using isolated temporary settings")
    parser.add_argument("--smoke-report", type=Path, help="Write isolated startup diagnostic result")
    parser.add_argument("--voice-self-test", action="store_true", help="Exercise bundled models without opening devices or live printers")
    parser.add_argument("--voice-pack", type=Path, help="Override the voice model pack for a device-free self-test")
    args = parser.parse_args()
    if args.voice_self_test:
        from .models import bundled_pack
        from .voice_probe import run
        report_path = args.smoke_report or Path("voice-self-test.json")
        try:
            root = args.voice_pack or bundled_pack()
            if root is None:
                raise ModelUnavailable("Bundled model pack is missing")
            report = run(root.resolve())
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
            return 0 if report["passed"] else 1
        except Exception:
            import traceback
            report_path.write_text(traceback.format_exc(), encoding="utf-8")
            return 1
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    from .theme import STYLE
    app.setStyleSheet(STYLE)
    import tempfile
    with tempfile.TemporaryDirectory(prefix="klippy-smoke-") as temp:
        try:
            store = Store(Path(temp) / "settings.sqlite" if args.smoke_test else data_directory() / "settings.sqlite")
            if args.smoke_test:
                import pywebrtc_audio  # noqa: F401
                import sherpa_onnx  # noqa: F401
                import sounddevice  # noqa: F401
            window = Window(store, smoke=args.smoke_test)
        except Exception:
            if args.smoke_test:
                import traceback
                if args.smoke_report:
                    args.smoke_report.write_text(traceback.format_exc(), encoding="utf-8")
                elif sys.stderr:
                    traceback.print_exc()
                return 1
            QMessageBox.critical(None, "Klippy could not start", "Settings could not be opened. Existing data has been preserved.")
            return 1
        if args.show or args.smoke_test or not QSystemTrayIcon.isSystemTrayAvailable():
            window.show()
        if args.smoke_test:
            QTimer.singleShot(1200, window.quit)
        result = app.exec()
        store.close()
        if args.smoke_test and args.smoke_report:
            args.smoke_report.write_text("Startup and shutdown completed successfully.\n", encoding="utf-8")
        return result


if __name__ == "__main__":
    raise SystemExit(main())
