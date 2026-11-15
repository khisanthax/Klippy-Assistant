"""Local, explicitly opted-in troubleshooting history and export UI."""

import json
import time
from datetime import datetime

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class HistoryPage(QWidget):
    def __init__(self, history, store):
        super().__init__()
        self.history, self.store = history, store
        layout = QVBoxLayout(self)
        self.controls = {}
        for key, label in [
            ("enabled", "Enable local diagnostics log (off by default)"),
            ("transcripts", "Include user/ASR transcript and normalized request text"),
            ("responses", "Include Klippy response and spoken text"),
            ("timing", "Include timing breakdown"),
        ]:
            check = QCheckBox(label)
            check.setChecked(getattr(history.prefs, key))
            check.toggled.connect(lambda value, k=key: self.configure(**{k: value}))
            self.controls[key] = check
            layout.addWidget(check)
        row = QHBoxLayout()
        for key, label, high in [
            ("retention_days", "Retention days", 30),
            ("max_entries", "Maximum entries", 10000),
        ]:
            spin = QSpinBox()
            spin.setRange(1, high)
            spin.setValue(getattr(history.prefs, key))
            spin.valueChanged.connect(lambda value, k=key: self.configure(**{k: value}))
            row.addWidget(QLabel(label))
            row.addWidget(spin)
        layout.addLayout(row)
        self.notice = QLabel()
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        row = QHBoxLayout()
        self.printer = QComboBox()
        self.printer.addItem("All printers", "")
        for p in store.printers():
            self.printer.addItem(p.name, p.id)
        self.outcome = QComboBox()
        self.outcome.addItems(
            [
                "All outcomes",
                "success",
                "clarification_needed",
                "proposed",
                "confirmed",
                "executed",
                "rejected",
                "failed",
                "canceled",
                "expired",
            ]
        )
        self.period = QComboBox()
        for label, hours in [
            ("All retained time", 0),
            ("Last hour", 1),
            ("Last day", 24),
            ("Last 7 days", 168),
        ]:
            self.period.addItem(label, hours)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search retained, redacted fields")
        for control in [self.printer, self.outcome, self.period]:
            control.currentIndexChanged.connect(self.reload)
            row.addWidget(control)
        row.addWidget(self.search)
        self.search.textChanged.connect(self.reload)
        layout.addLayout(row)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Time", "Printer", "User / ASR heard", "Klippy replied", "Result"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(False)
        for column, width in [(0, 195), (1, 120), (2, 210), (4, 125)]:
            self.table.setColumnWidth(column, width)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.itemSelectionChanged.connect(self.details)
        layout.addWidget(self.table)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        layout.addWidget(self.detail)
        row = QHBoxLayout()
        for index, (title, slot) in enumerate(
            [
                ("Refresh", self.reload),
                ("Clear history", self.clear),
                ("Export selected JSON", lambda: self.export(True)),
                ("Export filtered JSON", lambda: self.export(False)),
                ("Export all JSON", self.export_all),
            ]
        ):
            button = QPushButton(title)
            button.clicked.connect(slot)
            row.addWidget(button)
            if index == 1:
                layout.addLayout(row)
                row = QHBoxLayout()
        layout.addLayout(row)
        self.rows = []
        self.timer = QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(lambda: self.reload() if self.isVisible() else None)
        self.timer.start()
        self.reload()

    def configure(self, **changes):
        self.history.configure(**changes)
        self.reload()

    def reload(self, *_):
        prefs = self.history.prefs
        available = [(p.name, p.id) for p in self.store.printers()]
        if available != [
            (self.printer.itemText(i), self.printer.itemData(i)) for i in range(1, self.printer.count())
        ]:
            selected_printer = self.printer.currentData()
            self.printer.blockSignals(True)
            self.printer.clear()
            self.printer.addItem("All printers", "")
            for name, identity in available:
                self.printer.addItem(name, identity)
            self.printer.setCurrentIndex(max(0, self.printer.findData(selected_printer)))
            self.printer.blockSignals(False)
        for key, control in self.controls.items():
            control.blockSignals(True)
            control.setChecked(getattr(prefs, key))
            control.blockSignals(False)
        selected = {
            self.rows[i.row()]["id"] for i in self.table.selectedIndexes() if i.row() < len(self.rows)
        }
        self.notice.setText(
            ("Local logging ON. " if prefs.enabled else "Local logging OFF; no new interactions saved. ")
            + ("Transcript text enabled. " if prefs.transcripts else "Transcript text disabled. ")
            + ("Klippy response text enabled. " if prefs.responses else "Klippy response text disabled. ")
            + "Showing up to 200 recent matches. No audio is recorded. Exports may contain opted-in text; review before sharing. Turning off a text option removes it from retained entries."
            + (" History storage unavailable." if self.history.error else "")
        )
        hours = self.period.currentData() or 0
        self.filters = dict(
            printer=self.printer.currentData() or None,
            outcome=None if self.outcome.currentIndex() == 0 else self.outcome.currentText(),
            since=time.time() - hours * 3600 if hours else None,
            search=self.search.text() or None,
        )
        rows = self.history.entries(**self.filters, limit=200)
        if rows == self.rows:
            return
        self.rows = rows
        self.table.setRowCount(len(self.rows))
        for index, row in enumerate(self.rows):
            values = [
                datetime.fromtimestamp(row["timestamp"]).astimezone().isoformat(timespec="seconds"),
                row.get("printer", ""),
                row.get("user_transcript", "Not recorded"),
                row.get("response", "Not recorded"),
                row["outcome"],
            ]
            for column, value in enumerate(values):
                self.table.setItem(index, column, QTableWidgetItem(str(value)))
            if row["id"] in selected:
                self.table.selectRow(index)

    def details(self):
        row = self.table.currentRow()
        self.detail.setPlainText(json.dumps(self.rows[row], indent=2) if 0 <= row < len(self.rows) else "")

    def clear(self):
        self.history.clear()
        self.reload()
        self.detail.clear()

    def export(self, selected):
        ids = (
            {self.rows[i.row()]["id"] for i in self.table.selectedIndexes()}
            if selected
            else {r["id"] for r in self.rows}
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Export local history", "klippy-history.json", "JSON (*.json)"
        )
        if path:
            self.history.export(path, ids=ids if selected else None, **({} if selected else self.filters))

    def export_all(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export all retained history", "klippy-history.json", "JSON (*.json)"
        )
        if path:
            self.history.export(path)
