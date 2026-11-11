"""Render an isolated Qt panel for visual QA without touching user settings."""
import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "windows" if os.name == "nt" else "offscreen")

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from klippy.app import Window  # noqa: E402
from klippy.storage import Store  # noqa: E402
from klippy.theme import STYLE  # noqa: E402

app = QApplication([])
app.setQuitOnLastWindowClosed(False)
app.setStyle("Fusion")
app.setStyleSheet(STYLE)
with tempfile.TemporaryDirectory() as temp:
    store = Store(Path(temp) / "settings.sqlite")
    window = Window(store, smoke=True)
    window.write_message("Klippy is ready for manual enrollment. No printer is connected.")
    window.show()
    def capture():
        output = Path("build/ui-preview.png")
        output.parent.mkdir(exist_ok=True)
        window.grab().save(str(output))
        window.quit()
    QTimer.singleShot(300, capture)
    app.exec()
    store.close()
