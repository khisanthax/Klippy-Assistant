import json
import socket
from datetime import datetime
from unittest.mock import patch

import httpx
import pytest

from klippy.domain import Action, Intent, Printer
from klippy.listening import listening_enabled
from klippy.macros import discover
from klippy.models import ModelUnavailable, verify_pack
from klippy.monitor import Monitor
from klippy.moonraker import ConnectionFailure, Moonraker, lan_addresses
from klippy.storage import Store


def test_last_printer_survives_restart(tmp_path):
    path = tmp_path / "state.sqlite"
    first = Store(path)
    first.set("selected", "sim")
    first.close()
    second = Store(path)
    assert second.get("selected") == "sim"
    second.close()


def test_renamed_macro_does_not_inherit_approval():
    old, _ = discover({"gcode_macro OLD_LOAD": {"gcode": "M83"}}, {})
    old["OLD_LOAD"] = old["OLD_LOAD"].model_copy(update={"approved": True, "enabled": True})
    new, notices = discover({"gcode_macro NEW_LOAD": {"gcode": "M83"}}, old)
    assert not new["NEW_LOAD"].approved
    assert "OLD_LOAD" not in new
    assert any("Possible rename" in n for n in notices)


@pytest.mark.parametrize("mode,enabled", [("manual", False), ("always", True), ("invalid", False)])
def test_listening_modes(mode, enabled):
    assert listening_enabled({"mode": mode}, datetime(2026, 11, 11, 12)) == enabled


def test_schedule_including_overnight_previous_day():
    settings = {"mode": "scheduled", "windows": [{"days": [0], "start": 1320, "end": 120}]}
    assert listening_enabled(settings, datetime(2026, 11, 9, 23))
    assert listening_enabled(settings, datetime(2026, 11, 10, 1))
    assert not listening_enabled(settings, datetime(2026, 11, 10, 23))
    assert not listening_enabled(settings, datetime(2026, 11, 10, 2))
    assert not listening_enabled({**settings, "override": False}, datetime(2026, 11, 9, 23))


async def test_monitor_fault_is_notification_only_when_microphone_off(rig):
    store, sim, engine, _ = rig
    store.set("listening", {"mode": "manual", "enabled": False})
    monitor = Monitor(store, engine.clients)
    sim.ready = False
    assert await monitor.poll() == [("Test Printer", "fault")]
    assert await monitor.poll() == []
    assert not sim.writes
    assert store.db.execute("SELECT code FROM events").fetchone() == ("fault",)


async def test_print_error_alerts_when_firmware_still_ready(rig):
    store, sim, engine, _ = rig
    sim.state = "error"
    assert await Monitor(store, engine.clients).poll() == [("Test Printer", "fault")]
    assert not sim.writes


async def test_disconnect_alert_deduplicated(rig):
    store, sim, engine, _ = rig
    monitor = Monitor(store, engine.clients)
    sim.offline = True
    assert await monitor.poll() == [("Test Printer", "disconnected")]
    assert await monitor.poll() == []
    assert not sim.writes


async def test_reconnect_refreshes_macro_registry_readonly(rig):
    store, sim, engine, _ = rig
    monitor = Monitor(store, engine.clients)
    await monitor.poll()
    assert "LOAD_FILAMENT" in store.macros("sim")
    sim.offline = True
    await monitor.poll()
    sim.offline = False
    sim.config = {"gcode_macro REPLACEMENT": {"gcode": "M83"}}
    await monitor.poll()
    assert "LOAD_FILAMENT" not in store.macros("sim")
    assert not store.macros("sim")["REPLACEMENT"].approved
    assert not sim.writes


def test_missing_models_fail_visibly(tmp_path):
    with pytest.raises(ModelUnavailable):
        verify_pack(tmp_path)
    (tmp_path / "manifest.json").write_text('{"assets": []}')
    with pytest.raises(ModelUnavailable, match="incomplete"):
        verify_pack(tmp_path)


def test_model_path_traversal_blocked(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"assets": [{"path": "../outside"}]}))
    with pytest.raises(ModelUnavailable, match="path"):
        verify_pack(tmp_path)


def test_integrity_mismatch_blocked(tmp_path):
    (tmp_path / "model.onnx").write_bytes(b"not an onnx")
    (tmp_path / "manifest.json").write_text(json.dumps({"assets": [{
        "path": "model.onnx", "role": "wake", "source": "https://example.invalid/model", "version": "1",
        "license": "Apache-2.0", "sha256": "0" * 64}]}))
    with pytest.raises(ModelUnavailable, match="integrity"):
        verify_pack(tmp_path)


@pytest.mark.parametrize("address", ["8.8.8.8", "169.254.169.254", "0.0.0.0", "224.1.1.1"])
def test_public_and_unsafe_addresses_rejected(address):
    answer = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 7125))]
    with patch("socket.getaddrinfo", return_value=answer):
        with pytest.raises(ConnectionFailure):
            lan_addresses("http://printer.local:7125")


async def test_authentication_details_do_not_leak():
    printer = Printer(id="p", name="p", url="http://127.0.0.1")
    client = Moonraker(printer, api_key="TEST-SECRET", transport=httpx.MockTransport(
        lambda r: httpx.Response(401, text="TEST-SECRET")))
    with pytest.raises(ConnectionFailure) as exc:
        await client.snapshot()
    assert "TEST-SECRET" not in str(exc.value)


async def test_offline_basic_command_and_monitoring(rig):
    # No cloud/API service is involved; transport is a local-only simulated printer.
    _, sim, engine, _ = rig
    with patch("socket.getaddrinfo", side_effect=OSError("Internet unavailable")):
        assert "standby" in await engine.propose(Intent(action=Action.STATUS, printer_id="sim"))
    assert not sim.writes


def test_export_has_no_credentials_and_restore_revokes(rig, tmp_path):
    store, sim, _, _ = rig
    registry, _ = discover(sim.config, {})
    store.replace_macros("sim", {n: m.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                                 for n, m in registry.items()})
    path = tmp_path / "backup.json"
    store.export(path)
    assert "api_key" not in path.read_text()
    store.restore(path)
    assert not store.printers()[0].approved
    assert not store.macros("sim")["LOAD_FILAMENT"].approved


def test_invalid_restore_preserves_existing_data(rig, tmp_path):
    store, _, _, _ = rig
    path = tmp_path / "bad.json"
    path.write_text('{"version": 1, "printers": [{"invalid": true}]}')
    with pytest.raises(ValueError):
        store.restore(path)
    assert store.printers()[0].id == "sim"


def test_no_transcript_events(rig):
    store, _, _, _ = rig
    with pytest.raises(ValueError):
        store.event("sim", "user said a private phrase")
