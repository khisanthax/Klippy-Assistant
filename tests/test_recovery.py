import json
import sqlite3

import pytest

from klippy.listening import validate_windows
from klippy.storage import Store


def test_recovery_preserves_prior_wal_settings_and_resets_sensitive_preferences(rig, tmp_path):
    store, _, _, _ = rig
    store.set("followup_seconds", 45)
    path = tmp_path / "export.json"
    store.export(path)
    store.set("followup_seconds", 90)
    store.set("confirmations", {"home": False})
    store.set("heater_limits", {"sim": {"0": 300}})
    store.set('printer_limit_overrides', {'sim':{'motion':{'max_velocity':100}}})
    backup = store.restore(path)
    assert backup.is_file()
    previous = Store(backup)
    try:
        assert previous.get("followup_seconds") == 90
        assert previous.printers()[0].approved
        assert previous.get('printer_limit_overrides') == {'sim':{'motion':{'max_velocity':100}}}
    finally:
        previous.close()
    assert store.get("followup_seconds") == 45
    assert store.get("confirmations") == {}
    assert store.get("heater_limits") is None
    assert store.get('printer_limit_overrides') is None
    assert store.get("listening") == {"mode": "manual", "enabled": False}
    assert not store.printers()[0].approved
    assert store.get("selected") is None


@pytest.mark.parametrize("preferences", [{"confirmation_seconds": 999}, {"spoken": "yes"}, {"model_pack": "other"}])
def test_invalid_recovery_preferences_leave_data_untouched(rig, tmp_path, preferences):
    store, _, _, _ = rig
    path = tmp_path / "bad.json"
    store.export(path)
    value = json.loads(path.read_text())
    value["preferences"] = preferences
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        store.restore(path)
    assert store.printers()[0].approved
    assert store.get("selected") == "sim"


def test_sqlite_recovers_committed_state_after_abrupt_process_exit(tmp_path):
    import subprocess
    import sys
    path = tmp_path / "crash.sqlite"
    code = "from pathlib import Path; from klippy.storage import Store; import sys,os; s=Store(Path(sys.argv[1])); s.set('sentinel',123); os._exit(0)"
    subprocess.run([sys.executable, "-c", code, str(path)], check=True, timeout=15)
    store = Store(path)
    try:
        assert store.get("sentinel") == 123
        assert store.db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    finally:
        store.close()
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM settings").fetchone() == (1,)


@pytest.mark.parametrize("value", [[{"days": [8], "start": 5, "end": 10}], [{"days": [1], "start": -1, "end": 10}],
                                   [{"days": [True], "start": 5, "end": 10}], [{"days": [1]}], "bad"])
def test_schedule_rejects_invalid_windows(value):
    with pytest.raises(ValueError):
        validate_windows(value)


def test_offline_qualification_guard_denies_egress_before_os_connect():
    import subprocess
    import sys
    code = """
import socket
from klippy.offline_probe import deny_external_network
deny_external_network()
socket.getaddrinfo('127.0.0.1', 80)
for operation in (lambda: socket.getaddrinfo('example.invalid', 80),
                  lambda: socket.socket().connect(('192.0.2.1', 80))):
    try:
        operation()
    except RuntimeError:
        pass
    else:
        raise AssertionError('egress guard did not reject')
"""
    subprocess.run([sys.executable, "-c", code], check=True, timeout=10)
