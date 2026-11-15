"""Non-activating, orb-anchored identity/value review; never dispatches commands."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .clarification import popup_position, registry_signature
from .orb_geometry import Rect, observe_windows, safe_area


class ClarificationPopup(QWidget):
    def __init__(self, orb, conversation, store, submit, cancel):
        super().__init__(
            None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle("Klippy clarification")
        self.orb, self.conversation, self.store, self.submit, self.cancel = (
            orb,
            conversation,
            store,
            submit,
            cancel,
        )
        self.identity = None
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.layout = QVBoxLayout(self)

    def refresh(self):
        choice = self.conversation.expire_choice()
        if choice is None or not self.orb.prefs.enabled:
            self.hide()
            self.identity = None
            return
        if choice.identity != self.identity:
            self.identity = choice.identity
            while self.layout.count():
                item = self.layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.layout.addWidget(
                QLabel(
                    "Which command did you mean?"
                    if choice.parameter is None
                    else "Which values would you like?"
                )
            )
            printer = next(
                (p.name for p in self.store.printers() if p.id == choice.printer_id), "Unavailable printer"
            )
            printer_label = QLabel(printer + " · Selection still requires validation and confirmation.")
            printer_label.setWordWrap(True)
            printer_label.setTextFormat(Qt.TextFormat.PlainText)
            self.layout.addWidget(printer_label)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            form = QFormLayout(content)
            self.radios, self.values = [], {}
            registry = self.store.macros(choice.printer_id)
            if choice.parameter:
                macro = registry.get(choice.parameter.macro)
                if macro:
                    form.addRow(QLabel(macro.name + " · Reviewed macro · Confirmation required"))
                    for key, rule in macro.parameters.items():
                        if key not in choice.parameter.params and rule.required:
                            edit = QLineEdit()
                            edit.setPlaceholderText(f"{rule.minimum:g} to {rule.maximum:g}")
                            self.values[key] = edit
                            form.addRow(key, edit)
            else:
                for index, name in enumerate(choice.names):
                    macro = registry.get(name)
                    if macro:
                        radio = QRadioButton(
                            f"{index + 1}. "
                            + name.replace("_", " ").title()
                            + "\n"
                            + name
                            + "\nChanges printer state; confirmation required\n"
                            + macro.description[:180]
                        )
                        self.radios.append((name, radio))
                        form.addRow(radio)
            scroll.setWidget(content)
            self.layout.addWidget(scroll)
            self.remember = QCheckBox("Remember my choice for this printer")
            self.remember.setChecked(False)
            self.remember.setVisible(choice.parameter is None)
            self.layout.addWidget(self.remember)
            buttons = QWidget()
            row = QHBoxLayout(buttons)
            for label, slot in [("Continue", self.continue_choice), ("Cancel", self.cancel)]:
                button = QPushButton(label)
                button.clicked.connect(slot)
                row.addWidget(button)
            self.layout.addWidget(buttons)
            self.resize(400, 340)
            self.orb.summon()
            self.show()  # WA_ShowWithoutActivating; clicking permits normal keyboard navigation.
        screen = QApplication.screenAt(self.orb.geometry().center()) or self.orb.screen()
        desktop = self.orb.desktop
        if screen.name() != self.orb.monitor_name:

            def rect(value):
                return Rect(value.x(), value.y(), value.width(), value.height())

            desktop = observe_windows(
                screen.name(),
                rect(screen.geometry()),
                rect(screen.availableGeometry()),
                screen.devicePixelRatio(),
            )
        work = safe_area(desktop)
        box = self.orb.geometry()
        x, y, width, height = popup_position(
            Rect(box.x(), box.y(), box.width(), box.height()),
            work,
            self.width(),
            self.height(),
        )
        self.setGeometry(x, y, width, height)

    def continue_choice(self):
        choice = self.conversation.expire_choice()
        if choice is None or choice.identity != self.identity:
            self.refresh()
            return
        if self.values:
            text = " ".join(k + "=" + v.text().strip() for k, v in self.values.items())
        else:
            text = next((name for name, radio in self.radios if radio.isChecked()), None)
            if text is None:
                return
        choice.remember = self.remember.isChecked()
        self.submit(text)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel()
        else:
            super().keyPressEvent(event)


class RememberedChoicesPage(QWidget):
    def __init__(self, store):
        super().__init__()
        self.store = store
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Remembered choices select identity only. Validation and confirmation always apply. Changed registries invalidate choices."
            )
        )
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Printer", "Command", "Request signature"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        for title, slot in [
            ("Refresh", self.reload),
            ("Delete selected", self.delete_selected),
            ("Delete all", self.delete_all),
        ]:
            button = QPushButton(title)
            button.clicked.connect(slot)
            layout.addWidget(button)
        self.reload()

    def reload(self):
        entries = self.store.get("remembered_choices", {})
        entries = {
            k: v
            for k, v in entries.items()
            if v.get("signature") == registry_signature(self.store.macros(v.get("printer_id", "")))
        }
        self.store.set("remembered_choices", entries)
        self.keys = list(entries)
        self.table.setRowCount(len(entries))
        printers = {p.id: p.name for p in self.store.printers()}
        for row, key in enumerate(self.keys):
            value = entries[key]
            for col, text in enumerate(
                [printers.get(value["printer_id"], "Removed printer"), value["macro"], key[:12]]
            ):
                self.table.setItem(row, col, QTableWidgetItem(text))
        self.table.resizeColumnsToContents()

    def delete_selected(self):
        values = self.store.get("remembered_choices", {})
        for row in {i.row() for i in self.table.selectedIndexes()}:
            values.pop(self.keys[row], None)
        self.store.set("remembered_choices", values)
        self.reload()

    def delete_all(self):
        self.store.set("remembered_choices", {})
        self.reload()
