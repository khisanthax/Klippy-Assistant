"""Searchable inventory; browsing never dispatches a printer operation."""
import json
from dataclasses import asdict

from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .domain import Action
from .query_catalog import CATALOG
from .safety import READ_ONLY


class QueryManager(QWidget):
    def __init__(self, store, service, refresh, voice_state, aliases):
        super().__init__()
        self.store, self.service, self.voice_state = store, service, voice_state
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Read-only information and state-changing operations are listed separately. Select a row for details."))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search questions, synonyms, operations, macros or printer names")
        self.search.textChanged.connect(self.reload)
        layout.addWidget(self.search)
        for title, callback in (("Refresh approved-printer capabilities (read-only)", refresh),
                                ("Edit selected printer's voice aliases", aliases)):
            button = QPushButton(title)
            button.clicked.connect(callback)
            layout.addWidget(button)
        tabs = QTabWidget()
        self.queries, self.operations = QTableWidget(0, 6), QTableWidget(0, 6)
        for table, title in ((self.queries, "Read-only queries"), (self.operations, "State-changing operations && macros")):
            table.setHorizontalHeaderLabels(["Identifier", "Purpose / aliases", "Printers", "Voice availability", "Safety", "Capabilities / approval"])
            table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.itemSelectionChanged.connect(lambda table=table: self.inspect(table))
            tabs.addTab(table, title)
        layout.addWidget(tabs)
        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(160)
        layout.addWidget(self.detail)
        self.details = {}
        self.reload()

    def reload(self):
        search = self.search.text().casefold()
        printers = self.store.printers()
        names = "; ".join(p.name + (" / " + ", ".join(p.aliases) if p.aliases else "") for p in printers) or "No enrolled printers"
        queries, operations = [], []
        self.details = {}
        for spec in CATALOG.values():
            supported = "; ".join(f"{p.name}: {self.service.support(p.id, spec) if p.approved else 'not approved'}" for p in printers) or "Not verified"
            queries.append((spec.id, spec.description + " / " + "; ".join(spec.examples), names,
                            self.voice_state(), "READ ONLY", supported))
            self.details[spec.id] = json.dumps(asdict(spec), indent=2)
        for action in Action:
            if action in READ_ONLY:
                continue
            key = "operation:" + action.value
            operations.append((key, action.value.replace("_", " "), names, self.voice_state(),
                               "CHANGES PRINTER STATE", "Mandatory safety validation; confirmation policy applies"))
            self.details[key] = "Review and execution occur through the safety engine. Browsing this inventory sends no command."
        for printer in printers:
            for macro in self.store.macros(printer.id).values():
                key = f"macro:{printer.id}:{macro.name}"
                approved = printer.approved and macro.approved and macro.enabled and macro.reviewed
                operations.append((key, macro.description + " / " + ", ".join(macro.aliases), printer.name,
                                   self.voice_state() if approved else "Unavailable: review/approval required",
                                   "MACRO: STATE CHANGE / ALWAYS CONFIRM", "Reviewed" if approved else "Needs review / excluded"))
                self.details[key] = "Macro " + macro.name + "\n" + "\n".join(macro.review_notes) + "\n" + macro.definition
        for table, rows in ((self.queries, queries), (self.operations, operations)):
            rows = [row for row in rows if search in " ".join(row).casefold()]
            table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    table.setItem(i, j, QTableWidgetItem(value))
            table.resizeColumnsToContents()
            table.setColumnWidth(0, 170)
            table.setColumnWidth(1, 280)
            table.setColumnWidth(2, 160)
            table.setColumnWidth(3, 190)
            table.setColumnWidth(4, 150)
            table.setColumnWidth(5, 300)

    def inspect(self, table):
        row = table.currentRow()
        item = table.item(row, 0) if row >= 0 else None
        if item:
            self.detail.setPlainText(self.details.get(item.text(), ""))
