"""Actual Qt history/countdown/clarification checks with simulated transport only."""

import asyncio
import tempfile
from pathlib import Path

import httpx

from .domain import Printer
from .limits_probe import synthetic_status
from .macros import discover
from .moonraker import Moonraker
from .orb_geometry import safe_area
from .safety import Rejected
from .storage import Store


def run(app, images):
    from .app import Window

    checks = {}
    writes = []
    with tempfile.TemporaryDirectory(prefix="klippy-features-") as temp:
        store = Store(Path(temp) / "settings.sqlite")
        store.save_printer(Printer(id="sim", name="Simulated M1", url="http://127.0.0.1:1", approved=True))
        store.set("selected", "sim")
        config = {
            "gcode_macro BED_MESH_FAST": {
                "gcode": "G28\nG1 X10",
                "description": "Reviewed fast mesh wrapper",
            },
            "gcode_macro BED_MESH_FULL": {
                "gcode": "G28\nG1 X20",
                "description": "Reviewed full mesh wrapper",
            },
        }
        registry, _ = discover(config, {})
        store.replace_macros(
            "sim",
            {
                k: m.model_copy(update={"approved": True, "enabled": True, "reviewed": True})
                for k, m in registry.items()
            },
        )

        eventtime = 0
        def transport(request):
            nonlocal eventtime
            if request.method != "GET":
                writes.append(request.url.path)
                raise AssertionError("No writes allowed in desktop feature qualification")
            eventtime += 1
            status = synthetic_status()
            status['configfile']['config'] = config
            result = {'objects':list(status)} if request.url.path.endswith('/list') else {'status':status,'eventtime':eventtime}
            return httpx.Response(200, json={'result':result})

        window = Window(store, smoke=True)
        window.timer.stop()
        window.engine.clients = lambda printer: Moonraker(printer, transport=httpx.MockTransport(transport))
        window.engine.limits.clients = window.engine.clients
        try:
            window.personality_style.setCurrentText("Calm")
            window.response_style.setCurrentText("Detailed")
            checks["personality_settings"] = (
                store.get("personality") == {"style": "calm", "length": "detailed"}
                and store.get("response_style") == "detailed"
            )
            window.personality_style.setCurrentText("Friendly")
            window.response_style.setCurrentText("Short")
            history = window.history
            checks["history_default_off"] = not history.prefs.enabled and not history.path.exists()
            window.history_page.configure(enabled=True, transcripts=True, responses=True)
            try:
                asyncio.run(window.conversation.hear("run a bed mesh"))
            except Rejected:
                pass
            popup = window.clarification_popup
            popup.refresh()
            app.processEvents()
            checks["actual_two_reviewed_choices"] = popup.isVisible() and len(popup.radios) == 2
            checks["popup_does_not_activate"] = not popup.isActiveWindow()
            checks["remember_default_off"] = not popup.remember.isChecked()
            area = safe_area(window.sprite.desktop)
            checks["popup_inside_taskbar_safe_area"] = (
                area.x <= popup.x()
                and area.y <= popup.y()
                and popup.x() + popup.width() <= area.right
                and popup.y() + popup.height() <= area.bottom
            )
            popup.grab().save(str(images / "clarification-popup.png"))
            popup.radios[0][1].setChecked(True)
            popup.remember.setChecked(True)
            jobs = []
            window.worker.submit = lambda name, job: jobs.append(job)
            popup.continue_choice()
            result = asyncio.run(jobs.pop())
            window.result("turn", result)
            checks["selection_requires_confirmation"] = window.engine.pending is not None and not writes
            window.choices_page.reload()
            checks["remembered_identity_only"] = window.choices_page.table.rowCount() == 1 and not writes
            window.choices_page.table.selectRow(0)
            window.choices_page.delete_selected()
            checks["remembered_review_delete"] = store.get("remembered_choices") == {}
            history.record(
                "synthetic_privacy",
                user_transcript="password: syntheticSecret https://user:pw@example.test/private",
                response="Bearer syntheticToken",
            )
            export = Path(temp) / "history.json"
            history.export(export)
            exported = export.read_text(encoding="utf-8")
            checks["local_json_export_redacts"] = all(
                word not in exported
                for word in ["syntheticSecret", "user:pw", "example.test", "syntheticToken"]
            )
            window.history_page.reload()
            checks["history_view_has_turns"] = window.history_page.table.rowCount() >= 2
            window.resize(1100, 800)
            window.tabs.setCurrentWidget(window.history_page)
            window.grab().save(str(images / "diagnostics-history.png"))
            session = window.conversation.session

            def source():
                s = session.snapshot()
                return {
                    "microphone_ready": True,
                    "session_active": s["active"],
                    "followup_ready": s["ready"],
                    "followup_fraction": s["fraction"],
                }

            window.sprite.source = source
            window.sprite.pipeline_event("Speech finished")
            checks["countdown_after_response"] = window.sprite.countdown > 0.9
            window.sprite.grab().save(str(images / "followup-full.png"))
            session.deadline = session.clock() + session.timeout / 2
            window.sprite.refresh()
            checks["countdown_shared_half_window"] = 0.45 < window.sprite.countdown < 0.55
            window.sprite.grab().save(str(images / "followup-half.png"))
            hold = session.begin_active()
            window.sprite.refresh()
            checks["capture_hides_countdown"] = window.sprite.countdown == 0
            session.finish(hold, response=True)
            window.sprite.refresh()
            checks["response_resets_countdown"] = window.sprite.countdown > 0.9
            window.sprite.pipeline_event("Wake transcript unclear")
            checks["attention_reason_tooltip"] = window.sprite.state == "error" and "Wake phrase wasn't recognized" in window.sprite.toolTip()
            from PySide6.QtWidgets import QPushButton
            checks["copy_diagnostic_action_present"] = any(button.text() == "Copy latest diagnostic"
                                                          for button in window.history_page.findChildren(QPushButton))
            window.sprite.grab().save(str(images / "attention-reason.png"))
            window.sprite.pipeline_event("Checking wake word")
            checks["new_wake_clears_old_attention"] = window.sprite.state == "verifying"
            store.set("listening", {"mode": "always"})
            window.toggle_listening()
            checks["mute_clears_countdown"] = window.sprite.countdown == 0
            history.configure(transcripts=False, responses=False)
            checks["revoked_text_removed"] = all(
                "user_transcript" not in r and "response" not in r for r in history.entries()
            )
            history.clear()
            checks["clear_history"] = history.entries() == []
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QDialogButtonBox, QTextEdit
            printer = store.printers()[0]
            record = asyncio.run(window.engine.limits.refresh(printer))
            window.query_manager.reload()
            checks['motion_inventory_separate_and_explicit'] = 'MACHINE coordinates' in window.query_manager.details['operation:move']
            def edit_limits():
                dialog = app.activeModalWidget()
                if dialog is None:
                    return
                editor = dialog.findChild(QTextEdit, 'printer_limit_overrides')
                buttons = dialog.findChild(QDialogButtonBox)
                checks['limits_dialog_exposes_verified_configuration'] = 'max_extrude_cross_section' in ' '.join(
                    item.toPlainText() for item in dialog.findChildren(QTextEdit) if item.isReadOnly())
                editor.setPlainText('{"motion":{"max_velocity":500}}')
                buttons.button(QDialogButtonBox.StandardButton.Save).click()
                checks['limits_dialog_rejects_expansion'] = dialog.isVisible() and store.get('printer_limit_overrides',{}) == {}
                editor.setPlainText('{"axes":{"x":{"position_max":200}}}')
                dialog.grab().save(str(images / 'printer-limits.png'))
                buttons.button(QDialogButtonBox.StandardButton.Save).click()
            QTimer.singleShot(0, edit_limits)
            window.show_printer_limits(printer, record)
            checks['limits_dialog_saves_only_stricter_local_policy'] = store.get('printer_limit_overrides') == {'sim':{'axes':{'x':{'position_max':200}}}}
            checks["no_devices_or_printer_writes"] = window.voice is None and not writes
            return {
                "passed": all(checks.values()),
                "checks": checks,
                "scope": "Actual Qt controls, temporary local history, simulated Moonraker; zero audio devices or printer writes",
            }
        finally:
            window.quit()
            window.deleteLater()
            app.processEvents()
            store.close()
