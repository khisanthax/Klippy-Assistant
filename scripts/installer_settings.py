"""Installer QA helper, constrained to the workspace's isolated test directory."""
import sys
from pathlib import Path

from klippy.storage import Store, data_directory

expected = Path(__file__).resolve().parent.parent / "local" / "installer-qa" / "data" / "KlippyAssistant"
actual = data_directory().resolve()
if actual != expected.resolve():
    raise RuntimeError("Installer QA refuses to use real application settings")
store = Store(actual / "settings.sqlite")
try:
    if sys.argv[1] == "prepare":
        store.set("qa_sentinel", "preserve-me")
    elif sys.argv[1] == "verify":
        assert store.get("qa_sentinel") == "preserve-me"
    else:
        raise ValueError("Unknown QA action")
finally:
    store.close()
