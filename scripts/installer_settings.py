"""Installer QA helper, constrained to the workspace's isolated test directory."""
import json
import sys
from pathlib import Path

from klippy.domain import Macro, Printer
from klippy.storage import Store, data_directory

expected = Path(__file__).resolve().parent.parent / "local" / "installer-qa" / "data" / "KlippyAssistant"
actual = data_directory().resolve()
if actual != expected.resolve():
    raise RuntimeError("Installer QA refuses to use real application settings")
store = Store(actual / "settings.sqlite")
try:
    if sys.argv[1] == "prepare":
        store.set("qa_sentinel", "preserve-me")
        store.save_printer(Printer(id="qa-simulation", name="QA simulation", url="http://127.0.0.1:17125"))
        # Emulate the v0.2 record shape, before optional review-history fields existed.
        legacy = Macro(name="QA_STATUS", definition="M105").model_dump(mode="json")
        legacy.pop("previous_definition")
        legacy.pop("review_notes")
        with store.db:
            store.db.execute("INSERT OR REPLACE INTO macros VALUES (?,?,?)",
                             ("qa-simulation", "QA_STATUS", json.dumps(legacy)))
    elif sys.argv[1] == "verify":
        assert store.get("qa_sentinel") == "preserve-me"
        assert any(p.id == "qa-simulation" and not p.approved for p in store.printers())
        macro = store.macros("qa-simulation")["QA_STATUS"]
        assert macro.definition == "M105" and not macro.approved and macro.previous_definition is None
    else:
        raise ValueError("Unknown QA action")
finally:
    store.close()
