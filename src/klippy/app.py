from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
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
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
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
from .domain import Printer
from .listening import listening_enabled
from .macros import discover, inferred_parameters
from .models import ModelUnavailable, verify_pack
from .monitor import Monitor
from .moonraker import ConnectionFailure, Moonraker
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


def companion_icon():
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#61d6b0"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(5, 12, 54, 44, 14, 14)
    painter.setBrush(QColor("#102524"))
    painter.drawEllipse(18, 25, 7, 10)
    painter.drawEllipse(39, 25, 7, 10)
    painter.drawRoundedRect(23, 43, 18, 3, 1, 1)
    painter.end()
    return QIcon(pixmap)


class Sprite(QWidget):
    def __init__(self, summon):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        icon = QLabel()
        icon.setPixmap(companion_icon().pixmap(64, 64))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel("Klippy")
        self.label.setStyleSheet("background:#17352f;color:#c4f6e5;padding:8px;border-radius:8px")
        layout.addWidget(icon)
        layout.addWidget(self.label)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.summon = summon
        self.offset = QPoint()
        self.move(60, 100)

    def announce(self, text):
        self.label.setText(text[:100])
        self.adjustSize()
        self.show()
        self.timer.start(10000)

    def mousePressEvent(self, event):
        self.offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.offset)

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
        self.speech_pool = ThreadPoolExecutor(max_workers=1)
        self.worker = Worker()
        self.worker.result.connect(self.result)
        self.worker.error.connect(self.failure)
        self.engine = SafetyEngine(store, self.client)
        self.conversation = Conversation(self.engine)
        self.monitor = Monitor(store, self.client)
        self.polling = False
        self.command_busy = False
        self.quitting = False
        self.setWindowTitle(f"Klippy Assistant · {__version__} · Engineering preview")
        self.setWindowIcon(companion_icon())
        self.resize(940, 680)
        self.sprite = Sprite(self.summon)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.make_console()
        self.make_fleet()
        self.make_macros()
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
        return Moonraker(printer, Credentials.get(printer.id))

    def page(self, title):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(14)
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
        self.fleet = QTableWidget(0, 3)
        self.fleet.setHorizontalHeaderLabels(["Name", "Endpoint (private)", "Approval"])
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
        self.spoken.setChecked(self.store.get("spoken", False))
        self.spoken.toggled.connect(lambda v: self.store.set("spoken", v))
        layout.addWidget(self.spoken)
        row = QHBoxLayout()
        row.addWidget(self.button("Export configuration", self.export_config))
        row.addWidget(self.button("Restore configuration", self.restore_config))
        layout.addLayout(row)
        layout.addWidget(QLabel("No recordings or transcripts are saved. Configuration exports contain private printer\n"
                                "addresses and definitions; keep them private. Credentials stay in the Windows vault.\n"
                                "Speaker enrollment and hands-free barge-in are not enabled in this preview."))
        layout.addStretch()

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
            for col, text in enumerate((p.name, p.url, "Approved" if p.approved else "Needs approval")):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, p.id)
                self.fleet.setItem(row, col, item)
        self.fleet.resizeColumnsToContents()
        self.reload_macros()

    def select_printer(self):
        printer_id = self.selected.currentData()
        if printer_id:
            self.engine.select(printer_id)
            self.conversation.clear()
        else:
            self.engine.cancel()
            self.store.set("selected", None)
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
        secret.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Friendly name", name)
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
                printer = Printer(id=uuid.uuid4().hex, name=name.text(), url=url.text(), approved=approve.isChecked())
                Credentials.set(printer.id, secret.text())
                self.store.save_printer(printer)
                self.reload_printers()
            except Exception:
                self.failure("Printer not saved. Check the name, URL and Windows credential vault.")

    def test_printer(self):
        printer = self.fleet_target()
        if printer:
            self.worker.submit("test", self.client(printer).snapshot())

    def approve_printer(self):
        printer = self.fleet_target()
        if printer:
            self.engine.cancel()
            self.store.save_printer(printer.model_copy(update={"approved": True}))
            self.reload_printers()

    def remove_printer(self):
        printer = self.fleet_target()
        if printer:
            self.engine.cancel()
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
        self.definition.setPlainText(f"{macro.description}\n\n{macro.definition}" if macro else "")

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
                value.update(approved=True, enabled=True, reviewed=True, parameters=json.loads(params.text()),
                             aliases=[a.strip() for a in aliases.text().split(",") if a.strip()])
                approved = Macro.model_validate_json(json.dumps(value))
                registry = self.store.macros(printer.id)
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
            self.command_busy = True
            self.send_button.setEnabled(False)
            self.worker.submit("answer", self.conversation.hear(text))

    def confirm(self):
        if self.engine.pending and not self.command_busy:
            self.command_busy = True
            self.worker.submit("answer", self.engine.confirm(self.engine.pending.token))

    def cancel(self):
        self.engine.cancel()
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
        self.sprite.announce(self.active_name() + " · Needs attention")

    def result(self, name, value):
        if name == "poll":
            self.polling = False
            for printer_name, code in value:
                text = f"{printer_name}: {code}. No corrective action taken."
                self.write_message(text)
                self.sprite.announce(text)
                self.tray.showMessage("Klippy · Printer alert", text, QSystemTrayIcon.MessageIcon.Warning, 10000)
                self.say(text)
        elif name == "macros":
            self.reload_macros()
            self.write_message("Macro registry refreshed. " + "; ".join(value))
        elif name == "test":
            self.write_message(f"Read-only connection test: connected={value.connected}, state={value.state}")
        elif name == "voice_loaded":
            from .voice import VoiceLoop
            self.voice = VoiceLoop(value, self.voice_text, lambda text: self.worker.result.emit("voice_state", text))
            self.voice.start()
            self.conversation.llm = self.loaded_llm
            self.model_status.setText("Local speech pack loaded. Manual interruption available; hands-free barge-in disabled.")
        elif name == "voice_state":
            self.model_status.setText(value)
        elif name == "voice_input":
            if not self.command_busy:
                self.command_busy = True
                self.worker.submit("answer", self.conversation.hear(value, source="voice"))
        elif name == "answer":
            self.command_busy = False
            self.send_button.setEnabled(True)
            if value and value != "speech_stopped":
                self.write_message(value)
                self.sprite.announce(self.active_name() + " · Responding")
                self.say(value)
            elif value == "speech_stopped":
                self.stop_speaking()
            self.reload_printers()

    def voice_text(self, text):
        self.worker.result.emit("voice_input", text)

    def say(self, text):
        if self.voice and self.spoken.isChecked():
            self.speech_pool.submit(self.voice.speak, text)

    def load_voice(self):
        path = QFileDialog.getExistingDirectory(self, "Select verified local model pack")
        if path:
            async def load():
                from .voice import SherpaBackend
                root = Path(path)
                manifest = await asyncio.to_thread(verify_pack, root)
                backend = await asyncio.to_thread(SherpaBackend, root, manifest["speech_config"])
                self.loaded_llm = await self.runtime.start(root)
                return backend
            if self.voice:
                self.voice.close()
                self.voice = None
            self.worker.submit("voice_loaded", load())

    def save_schedule(self):
        try:
            windows = json.loads(self.schedule.text())
            if not isinstance(windows, list) or not all(isinstance(w, dict) for w in windows):
                raise ValueError()
            self.store.set("listening", {"mode": self.listening.currentText(), "windows": windows,
                                         "enabled": False})
        except ValueError:
            self.failure("Schedule must be a JSON list of time windows")

    def toggle_listening(self):
        settings = self.store.get("listening", {})
        settings["override"] = not listening_enabled(settings, datetime.now())
        self.store.set("listening", settings)
        self.conversation.clear()

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
                self.store.restore(Path(path))
                self.reload_printers()
                self.write_message("Restored. Printers and macros require reapproval; credentials were not imported.")
            except Exception:
                self.failure("Backup invalid; configuration was not restored")

    def active_name(self):
        printer = self.target()
        return printer.name if printer else "No active printer"

    def show_sprite(self):
        self.sprite.announce(self.active_name())

    def tick(self):
        self.ticks += 1
        enabled = listening_enabled(self.store.get("listening", {}), datetime.now())
        if self.voice:
            (self.voice.enabled.set if enabled else self.voice.enabled.clear)()
        self.state_label.setText(f"{self.active_name()} · Microphone {'enabled' if enabled and self.voice else 'off'} · "
                                 f"Monitoring {'enabled' if self.monitor_enabled.isChecked() else 'off'}")
        pending = self.engine.pending
        if pending and self.engine.clock() >= pending.expires:
            self.engine.cancel()
            pending = None
        self.confirm_button.setEnabled(pending is not None and not self.command_busy)
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
        self.speech_pool.shutdown(wait=False, cancel_futures=True)
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
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget { background:#101c24; color:#e0e9ee; font-family:'Segoe UI'; font-size:13px; }
        QLineEdit,QTextEdit,QTableWidget,QComboBox { background:#182934; border:1px solid #354a58; padding:8px; }
        QPushButton { background:#20483f; border:1px solid #3b7361; padding:9px; border-radius:5px; }
        QPushButton:hover { background:#2d5d50; } QPushButton:disabled { color:#667b84; background:#1b2a32; }
        QTabBar::tab { padding:12px 24px; } QTabBar::tab:selected { color:#70dfbd; }
        QHeaderView::section { background:#233b49; padding:8px; border:0; }
    """)
    import tempfile
    with tempfile.TemporaryDirectory(prefix="klippy-smoke-") as temp:
        try:
            store = Store(Path(temp) / "settings.sqlite" if args.smoke_test else data_directory() / "settings.sqlite")
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
