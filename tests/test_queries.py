import asyncio
import json

import httpx
import pytest

from klippy.conversation import Conversation, LocalLLM
from klippy.diagnostics import current, timings
from klippy.domain import Action, Intent, Printer
from klippy.moonraker import ConnectionFailure, Moonraker
from klippy.queries import QueryRequest, QueryService, QueryUnavailable, match_query, read
from klippy.query_catalog import CATALOG
from klippy.query_format import render
from klippy.safety import Rejected


class QuerySimulator:
    def __init__(self):
        self.calls = []
        self.fail = False
        self.status = {
            "toolhead": {"homed_axes": "xy", "position": [1, 2, 3, 0], "axis_minimum": [0, 0, 0],
                         "axis_maximum": [300, 300, 300], "max_velocity": 300, "max_accel": 5000,
                         "square_corner_velocity": 5, "minimum_cruise_ratio": .5, "extruder": "extruder"},
            "extruder": {"temperature": 205.5, "target": 210, "power": .3, "can_extrude": True,
                         "pressure_advance": .04, "smooth_time": .04},
            "heater_bed": {"temperature": 59.5, "target": 60, "power": .2},
            "gcode_move": {"gcode_position": [1, 2, 3, 0], "homing_origin": [0, 0, .1], "speed": 80,
                           "speed_factor": 1.2, "extrude_factor": 1},
            "print_stats": {"filename": "folder/test & safe.gcode", "state": "printing", "message": "",
                            "print_duration": 120, "total_duration": 150, "filament_used": 1234,
                            "info": {"current_layer": 3, "total_layer": 100}},
            "webhooks": {"state": "ready", "state_message": "Printer is ready"},
            "virtual_sdcard": {"progress": .63}, "pause_resume": {"is_paused": False},
            "motion_report": {"live_position": [1, 2, 3, 0], "live_velocity": 5, "live_extruder_velocity": -.2},
            "fan": {"speed": .5, "rpm": 2000}, "heater_fan hotend": {"speed": 1},
            "fan_generic enclosure": {"speed": .3},
            "filament_switch_sensor runout": {"enabled": True, "filament_detected": False},
            "temperature_sensor chamber": {"temperature": 35},
            "configfile": {"save_config_pending": False, "warnings": []},
            "bed_mesh": {"profile_name": "default", "mesh_min": [0, 0], "mesh_max": [290, 290]},
            "quad_gantry_level": {"applied": True}, "z_tilt": {"applied": False},
            "probe": {"name": "probe", "last_query": False}, "query_endstops": {"last_query": {"x": False}},
            "firmware_retraction": {"retract_length": .5, "retract_speed": 30, "unretract_extra_length": 0, "unretract_speed": 30},
            "mmu": {"print_state": "printing", "tool": 1, "gate": 2, "is_locked": False},
            "mcu": {"mcu_version": "v-synthetic", "last_stats": {"task_avg": .001}},
        }
        self.components = ["history", "file_manager", "machine", "proc_stats", "power", "webcam", "job_queue"]
        self.event = 10
        self.overrides = {}
        self.jobs = [{"filename": "failed.gcode", "status": "klippy_shutdown"},
                     {"filename": "ok.gcode", "status": "completed"}]

    def handle(self, request):
        self.calls.append((request.method, request.url.path, dict(request.url.params)))
        assert request.method == "GET", "Query attempted consequential HTTP"
        assert request.url.path not in {"/printer/gcode/script", "/printer/restart", "/printer/emergency_stop"}
        if self.fail:
            raise httpx.ConnectError("private endpoint/token details", request=request)
        path = request.url.path
        if path in self.overrides:
            value = self.overrides[path]
        elif path == "/server/info":
            value = {"components": self.components, "klippy_connected": True, "klippy_state": "ready", "moonraker_version": "synthetic"}
        elif path == "/printer/objects/list":
            value = {"objects": list(self.status)}
        elif path == "/printer/objects/query":
            value = {"eventtime": self.event, "status": {name: {key: item for key, item in self.status.get(name, {}).items()
                      if not fields or key in fields.split(",")} for name, fields in request.url.params.items() if name in self.status}}
        elif path == "/printer/info":
            value = {"state": "ready", "state_message": "Ready", "software_version": "synthetic-klipper"}
        elif path == "/server/history/list":
            value = {"jobs": self.jobs, "count": len(self.jobs)}
        elif path == "/server/history/totals":
            value = {"job_totals": {"total_jobs": 2, "total_print_time": 400, "total_filament_used": 500}}
        elif path == "/server/files/metadata":
            assert request.url.params["filename"] == "folder/test & safe.gcode"
            value = {"filename": request.url.params["filename"], "slicer": "Synthetic", "filament_type": "PLA",
                     "estimated_time": 600, "layer_height": .2}
        elif path == "/server/files/list":
            value = [{"path": "test.gcode", "size": 123}]
        elif path == "/machine/system_info":
            value = {"system_info": {"cpu_info": {"cpu_desc": "Synthetic CPU", "cpu_count": 4}, "distribution": {"name": "Linux"}}}
        elif path == "/machine/proc_stats":
            value = {"system_cpu_usage": {"cpu": 12.5}, "cpu_temp": 45, "system_uptime": 1000, "throttled_state": {"flags": []}}
        elif path == "/machine/device_power/devices":
            value = {"devices": [{"name": "plug", "status": "on"}]}
        elif path == "/server/job_queue/status":
            value = {"queued_jobs": [{"filename": "next.gcode"}], "queue_state": "paused"}
        elif path == "/server/webcams/list":
            value = {"webcams": [{"name": "toolhead camera"}]}
        else:
            pytest.fail("Unreviewed endpoint: " + path)
        return httpx.Response(200, json={"result": value})


@pytest.fixture
def queries(rig):
    store, _, engine, clock = rig
    sim = QuerySimulator()
    store.save_printer(Printer(id="sim", name="M1", aliases=("Mercury One",), url="http://127.0.0.1:7125", approved=True))
    factory = lambda p: Moonraker(p, transport=httpx.MockTransport(sim.handle))  # noqa: E731
    engine.clients = factory
    service = QueryService(store, factory, clock=lambda: clock[0])
    return sim, service, engine, clock


@pytest.mark.parametrize("identifier", list(CATALOG))
async def test_entire_catalog_has_typed_realistic_read_only_simulation(queries, identifier):
    sim, service, _, _ = queries
    answer = await service.answer("sim", QueryRequest(query_id=identifier))
    assert answer.startswith("M1:") and len(answer) <= 550
    assert not any("unsupported" in answer.lower() for _ in [0])
    assert all(method == "GET" for method, _, _ in sim.calls)
    spec = CATALOG[identifier]
    assert spec.examples and spec.response_fields or identifier == "filament_sensors"
    assert spec.classification.startswith("read-only")


@pytest.mark.parametrize("phrase,identifier", [
    ("Is my M1 printer homed?", "homing"), ("Have all axes been homed", "homing"),
    ("Which axes are not homed?", "homing"), ("Is the Z axis homed yet", "homing"),
    ("Where's the nozzle?", "position"), ("What's the target temperature?", "targets"),
    ("What layer am I on?", "layers"), ("How hot is the bed?", "temperatures"),
    ("How fast are the fans spinning?", "fans"), ("What is the acceleration?", "limits"),
    ("What is the G-code position?", "gcode_position"), ("How far along is my print", "progress"),
    ("Why did my last print fail?", "last_failure"), ("What files are available", "files"),
    ("What is the speed override", "speed"), ("How long has it been printing", "duration"),
    ("Is the printer moving", "motion"), ("Is filament detected", "filament_sensors"),
    ("What power devices are connected", "power_devices"), ("What is the MMU state", "mmu"),
    ("What's the host CPU temperature", "host_stats"), ("Is the probe triggered", "probe"),
    ("Which mesh profile is loaded", "bed_mesh"), ("What jobs are queued", "queue"),
    ("When will the print finish", "remaining"), ("What is the Klipper version", "printer_info"),
    ("How many prints have I done", "totals"), ("What is the flow override", "speed"),
])
def test_language_variants(phrase, identifier):
    assert match_query(phrase).query_id == identifier


class NoActionLLM:
    async def interpret(self, *args):
        pytest.fail("Information query reached action interpreter")

    async def interpret_query(self, *args):
        pytest.fail("Common deterministic question reached query LLM")


async def test_homing_alias_and_cross_printer_followups_never_call_action_engine(queries):
    sim, service, engine, _ = queries
    engine.store.save_printer(Printer(id="sv", name="SV08", aliases=("big printer",), url="http://127.0.0.1:7126", approved=True))
    conversation = Conversation(engine, NoActionLLM(), queries=service)
    assert "Not homed: Z" in await conversation.hear("Klippy, is my Mercury One printer homed?")
    sim.status["toolhead"]["homed_axes"] = "xyz"
    assert "SV08: Homed axes: X, Y, Z" in await conversation.hear("What about the SV08?")
    assert engine.store.get("selected") == "sv"
    assert engine.pending is None and all(method == "GET" for method, _, _ in sim.calls)


async def test_heater_followup_retains_subject_and_expires(queries):
    _, service, engine, clock = queries
    c = Conversation(engine, NoActionLLM(), queries=service, clock=lambda: clock[0])
    assert "59.5" in await c.hear("How hot is the bed?")
    target = await c.hear("What's the target temperature?")
    assert "bed" in target and "60" in target and "210" not in target
    clock[0] += 31
    c.query_fallback = service
    c.llm = None
    with pytest.raises(Rejected):
        await c.hear("What about it?")


@pytest.mark.parametrize("axes,expected", [("", "Homed axes: none"), ("x", "Not homed: Y, Z"),
                                            ("xyz", "Not homed: none"), (None, "unavailable"),
                                            (True, "unavailable"), ("q", "unavailable"), ("xx", "unavailable")])
async def test_homed_axes_validated_not_inferred(queries, axes, expected):
    sim, service, _, _ = queries
    sim.status["toolhead"]["homed_axes"] = axes
    assert expected in await service.answer("sim", QueryRequest(query_id="homing"))


@pytest.mark.parametrize("identifier,obj", [("homing", "toolhead"), ("bed_mesh", "bed_mesh"),
                                           ("mmu", "mmu"), ("retraction", "firmware_retraction")])
async def test_missing_objects_explicit_not_automatic_actions(queries, identifier, obj):
    sim, service, _, _ = queries
    sim.status.pop(obj)
    assert "unavailable" in await service.answer("sim", QueryRequest(query_id=identifier))


async def test_optional_component_is_verified_before_endpoint(queries):
    sim, service, _, _ = queries
    sim.components.remove("history")
    assert "unsupported" in await service.answer("sim", QueryRequest(query_id="last_failure"))
    assert not any(path.startswith("/server/history") for _, path, _ in sim.calls)


async def test_fresh_cache_and_field_scoped_subscription_age(queries):
    sim, service, engine, clock = queries
    request = QueryRequest(query_id="homing")
    await service.answer("sim", request)
    count = len(sim.calls)
    await service.answer("sim", request)
    assert len(sim.calls) == count
    clock[0] += 3
    service.notification("sim", {"method": "notify_status_update", "params": [{"extruder": {"temperature": 200}}, 11]})
    sim.fail = True
    result = await service.answer("sim", request)
    assert "STALE" in result and "3.0 seconds old" in result and "cannot verify current" in result
    assert engine.pending is None


async def test_new_read_replaces_omitted_fields_not_merges_old_layer(queries):
    sim, service, _, clock = queries
    await service.answer("sim", QueryRequest(query_id="layers"))
    sim.status["print_stats"]["info"] = {"total_layer": 100}
    clock[0] += 3
    answer = await service.answer("sim", QueryRequest(query_id="layers"))
    assert "layer unavailable of 100" in answer


async def test_config_and_reconnect_invalidate_capabilities(queries):
    sim, service, engine, _ = queries
    await service.discover(engine.store.printers()[0])
    sim.status.pop("mmu")
    sim.status["filament_motion_sensor feeder"] = {"enabled": True, "filament_detected": True}
    service.notification("sim", {"method": "notify_status_update", "params": [{"configfile": {"save_config_pending": False}}, 12]})
    assert "sim" not in service.capabilities
    assert "required objects not reported" in await service.answer("sim", QueryRequest(query_id="mmu"))
    assert "feeder" in await service.answer("sim", QueryRequest(query_id="filament_sensors"))
    service.notification("sim", {"method": "notify_klippy_ready"})
    assert "sim" not in service.capabilities


@pytest.mark.parametrize("method,path,params", [("GET", "/printer/gcode/script", {"script": "G28"}),
    ("GET", "/machine/device_power/on", {}), ("GET", "/printer/restart", {}),
    ("GET", "/server/files/metascan", {}), ("GET", "/server/history/reset_totals", {}),
    ("GET", "/printer/objects/query", {"gcode_macro EVIL": "variable"}),
    ("GET", "/printer/objects/query", {"toolhead": "homed_axes;G28"}),
    ("GET", "/server/files/metadata", {"filename": "../config/printer.cfg"}),
    ("GET", "/server/files/list", {"root": "config"}),
    ("GET", "/server/history/list", {"limit": 100000})])
async def test_explicit_read_allowlist_blocks_mutating_get_and_parameter_injection(queries, method, path, params):
    sim, service, engine, _ = queries
    client = service.clients(engine.store.printers()[0])
    with pytest.raises(QueryUnavailable):
        await read(client, path, params)
    assert not sim.calls


@pytest.mark.parametrize("question", ["Is it homed and then home it", "What is the temperature and heat the bed",
                                      "How far along is it then cancel print"])
async def test_mixed_query_and_actuation_blocked(queries, question):
    _, service, engine, _ = queries
    with pytest.raises(Rejected):
        await Conversation(engine, NoActionLLM(), queries=service).hear(question)
    assert engine.pending is None


async def test_question_cannot_become_action_through_model(queries):
    _, service, engine, _ = queries
    class Malicious:
        async def interpret_query(self, text):
            return Intent(action=Action.HOME, printer_id="sim")
        async def interpret(self, *args):
            pytest.fail("Question fell through into action LLM")
    with pytest.raises(Rejected):
        await Conversation(engine, Malicious(), queries=service).hear("What is the mysterious printer thing?")
    assert engine.pending is None


async def test_unfamiliar_information_uses_only_constrained_query_interpreter(queries):
    _, service, engine, _ = queries
    class Model(NoActionLLM):
        async def interpret_query(self, text):
            return QueryRequest(query_id="homing")
    assert "Not homed: Z" in await Conversation(engine, Model(), queries=service).hear("Has the machine established its coordinate reference?")


async def test_explicit_home_still_requires_safety_confirmation(queries):
    _, service, engine, _ = queries
    # The simulator's fixed print state is printing; safety must refuse homing.
    with pytest.raises(Rejected, match="state"):
        await Conversation(engine, NoActionLLM(), queries=service).hear("home")
    assert engine.pending is None


async def test_query_does_not_confirm_pending_write(queries):
    _, service, engine, _ = queries
    await engine.propose(Intent(action=Action.PAUSE, printer_id="sim"))
    assert engine.pending
    await Conversation(engine, NoActionLLM(), queries=service).hear("Is M1 homed?")
    assert engine.pending is None


@pytest.mark.parametrize("value", [None, "12", True, float("nan"), float("inf"), -300, {}, []])
def test_malformed_temperature_not_coerced(value):
    answer = render("temperatures", {"extruder": {"temperature": value}}, {})
    assert "unavailable" in answer


async def test_history_reports_recorded_status_without_root_cause_invention(queries):
    sim, service, _, _ = queries
    answer = await service.answer("sim", QueryRequest(query_id="last_failure"))
    assert "klippy_shutdown" in answer and "does not establish a physical root cause" in answer
    assert "clog" not in answer
    sim.jobs = []
    service.invalidate("sim")
    assert "No unsuccessful job" in await service.answer("sim", QueryRequest(query_id="last_failure"))


async def test_diagnostics_have_query_response_and_no_transcripts(queries):
    _, service, _, _ = queries
    key = timings.new()
    token = current.set(key)
    try:
        await service.answer("sim", QueryRequest(query_id="homing"))
    finally:
        current.reset(token)
    row = next(r for r in timings.snapshot() if r["reaction"] == key)
    assert row["milliseconds"]["query_response"] >= 0
    assert row["milliseconds"]["query_format"] >= 0
    assert "M1" not in json.dumps(row)


async def test_query_model_schema_cannot_return_extra_action(monkeypatch):
    import klippy.conversation as conversation
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"query_id": "homing", "action": "home"})}}]}
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, url, **kwargs):
            schema = kwargs["json"]["response_format"]["json_schema"]["schema"]
            for branch in schema["oneOf"]:
                assert "action" not in branch["properties"] and branch["additionalProperties"] is False
                if "homing" in branch["properties"]["query_id"].get("enum", []):
                    assert branch["properties"]["subject"] == {"enum": [None]}
            return Response()
    monkeypatch.setattr(conversation.httpx if hasattr(conversation, "httpx") else httpx, "AsyncClient", Client)
    with pytest.raises(Rejected):
        await LocalLLM().interpret_query("Is it homed?")


async def test_revoked_printer_and_unknown_query_never_read(queries):
    sim, service, engine, _ = queries
    p = engine.store.printers()[0]
    engine.store.save_printer(p.model_copy(update={"approved": False}))
    with pytest.raises(QueryUnavailable):
        await service.answer("sim", QueryRequest(query_id="homing"))
    with pytest.raises(QueryUnavailable):
        await service.answer("sim", QueryRequest(query_id="/printer/gcode/script"))
    assert not sim.calls


@pytest.mark.parametrize("spec", list(CATALOG.values()), ids=lambda s: s.id)
def test_every_advertised_example_routes_to_its_catalog_entry(spec):
    for phrase in spec.examples:
        assert match_query(phrase).query_id == spec.id
    assert spec.response_fields


@pytest.mark.parametrize("phrase", ["Check whether my M1 printer is homed", "M1 is homed?", "Show the homing status"])
async def test_non_wh_homing_information_never_becomes_home_command(queries, phrase):
    sim, service, engine, _ = queries
    answer = await Conversation(engine, NoActionLLM(), queries=service).hear(phrase)
    assert "Not homed: Z" in answer
    assert all(method == "GET" for method, _, _ in sim.calls) and engine.pending is None


@pytest.mark.parametrize("path,bad", [("/server/info", {"components": "history"}),
                                      ("/server/info", []),
                                      ("/printer/objects/list", {"objects": [None]}),
                                      ("/printer/objects/query", {"status": []}),
                                      ("/printer/objects/query", {"status": {}, "eventtime": float("inf")})])
async def test_malformed_discovery_and_status_fail_closed(queries, path, bad):
    sim, service, _, _ = queries
    sim.overrides[path] = bad
    with pytest.raises((ConnectionFailure, QueryUnavailable)):
        await service.answer("sim", QueryRequest(query_id="homing"))


async def test_slow_response_is_labeled_with_observation_age(queries):
    _, service, engine, clock = queries
    factory = service.clients
    class Slow:
        async def request(self, *args, **kwargs):
            value = await factory(engine.store.printers()[0]).request(*args, **kwargs)
            clock[0] += 3
            return value
    service.clients = lambda p: Slow()
    answer = await service.answer("sim", QueryRequest(query_id="homing"))
    assert "STALE" in answer and "cannot verify current" in answer


async def test_missing_fields_not_inferred_and_cached_without_repeat_read(queries):
    sim, service, _, _ = queries
    sim.status["toolhead"].pop("homed_axes")
    assert "unavailable" in await service.answer("sim", QueryRequest(query_id="homing"))
    count = len(sim.calls)
    assert "unavailable" in await service.answer("sim", QueryRequest(query_id="homing"))
    assert len(sim.calls) == count
    assert "fields not reported" in service.support("sim", CATALOG["homing"])


async def test_endpoint_change_never_reuses_cached_old_printer_values(queries):
    sim, service, engine, _ = queries
    assert "Not homed: Z" in await service.answer("sim", QueryRequest(query_id="homing"))
    old = engine.store.printers()[0]
    engine.store.save_printer(old.model_copy(update={"url": "http://127.0.0.1:7128"}))
    sim.status["toolhead"]["homed_axes"] = "xyz"
    assert "Not homed: none" in await service.answer("sim", QueryRequest(query_id="homing"))
    assert sum(path == "/server/info" for _, path, _ in sim.calls) == 2


async def test_unapproved_named_printer_not_replaced_with_selected_target(queries):
    sim, service, engine, _ = queries
    engine.store.save_printer(Printer(id="other", name="M10", url="http://127.0.0.1:7128"))
    with pytest.raises(Rejected, match="not approved"):
        await Conversation(engine, NoActionLLM(), queries=service).hear("Is M10 homed?")
    assert not sim.calls


async def test_conflicting_aliases_clarify_without_selecting_or_reading(queries):
    sim, service, engine, _ = queries
    engine.store.save_printer(Printer(id="other", name="Other", aliases=("Mercury One",), url="http://127.0.0.1:7128", approved=True))
    with pytest.raises(Rejected, match="single printer"):
        await Conversation(engine, NoActionLLM(), queries=service).hear("Is Mercury One homed?")
    assert engine.store.get("selected") == "sim" and not sim.calls


async def test_failed_endpoint_refresh_is_explicitly_stale(queries):
    sim, service, _, clock = queries
    request = QueryRequest(query_id="host_stats")
    await service.answer("sim", request)
    clock[0] += 3
    sim.fail = True
    assert "STALE cached observation" in await service.answer("sim", request)


async def test_backward_server_clock_invalidates_registry(queries):
    sim, service, _, clock = queries
    await service.answer("sim", QueryRequest(query_id="homing"))
    clock[0] += 3
    sim.event = 1
    answer = await service.answer("sim", QueryRequest(query_id="homing"))
    assert "STALE" in answer and "sim" not in service.capabilities


def test_missing_position_homing_does_not_claim_unhomed():
    answer = render("position", {"toolhead": {"position": [0, 0, 0]}}, {})
    assert "homing status unavailable" in answer


def test_query_manager_search_and_safety_separation(queries):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from klippy.query_manager import QueryManager
    _, service, engine, _ = queries
    app = QApplication.instance() or QApplication([])
    manager = QueryManager(engine.store, service, lambda: None, lambda: "Voice off", lambda: None)
    try:
        assert manager.queries.rowCount() == len(CATALOG)
        assert all(manager.queries.item(i, 4).text() == "READ ONLY" for i in range(len(CATALOG)))
        assert all("STATE" in manager.operations.item(i, 4).text() for i in range(manager.operations.rowCount()))
        manager.search.setText("homed")
        assert manager.queries.rowCount() == 1 and manager.queries.item(0, 0).text() == "homing"
        manager.search.setText("Mercury One")
        assert manager.queries.rowCount() == len(CATALOG)
    finally:
        manager.close()
        manager.deleteLater()
        app.processEvents()


async def test_printer_errors_remain_available_when_klipper_not_ready(queries):
    sim, service, _, _ = queries
    sim.overrides["/server/info"] = {"components": [], "klippy_connected": True, "klippy_state": "error"}
    sim.overrides["/printer/info"] = {"state": "error", "state_message": "Synthetic MCU configuration error"}
    answer = await service.answer("sim", QueryRequest(query_id="errors"))
    assert "Synthetic MCU configuration error" in answer
    assert not any(path == "/printer/objects/query" for _, path, _ in sim.calls)


async def test_large_accessory_inventory_uses_bounded_read_batches(queries):
    sim, service, _, _ = queries
    for i in range(140):
        sim.status[f"temperature_sensor chamber_{i}"] = {"temperature": 30}
    assert "Not homed: Z" in await service.answer("sim", QueryRequest(query_id="homing"))
    assert all(len(params) <= 64 for _, path, params in sim.calls if path == "/printer/objects/query")


async def test_query_probe_cannot_pass_when_model_selects_wrong_information(queries):
    from klippy.query_probe import run
    class Wrong:
        async def interpret_query(self, text):
            return QueryRequest(query_id="position")
    assert not (await run(Wrong()))["passed"]


async def test_delayed_old_endpoint_response_cannot_poison_new_printer_cache(queries):
    sim, service, engine, clock = queries
    request = QueryRequest(query_id="homing")
    await service.answer("sim", request)
    entered, release = asyncio.Event(), asyncio.Event()
    factory = service.clients
    class Delayed:
        def __init__(self, printer):
            self.printer = printer
        async def request(self, method, path):
            result = await factory(self.printer).request(method, path)
            if self.printer.url.endswith(":7125") and path.startswith("/printer/objects/query"):
                entered.set()
                await release.wait()
            return result
    service.clients = lambda p: Delayed(p)
    clock[0] += 3
    old = asyncio.create_task(service.answer("sim", request))
    await asyncio.wait_for(entered.wait(), 2)
    printer = engine.store.printers()[0]
    engine.store.save_printer(printer.model_copy(update={"url": "http://127.0.0.1:7128"}))
    clock[0] += 1
    sim.status["toolhead"]["homed_axes"] = "xyz"
    assert "Not homed: none" in await service.answer("sim", request)
    release.set()
    with pytest.raises(QueryUnavailable):
        await old
    assert "Not homed: none" in await service.answer("sim", request)
    service.observe("sim", {"status": {"toolhead": {"homed_axes": ""}}}, clock[0], identity=printer.url)
    assert "Not homed: none" in await service.answer("sim", request)


@pytest.mark.parametrize("broken", [None, "negative_accept", "negative_session", "standalone_wake", "own_echo", "verified_interruption",
                                      "local_language", "no_printer_writes", "paced_status", "query", "query_write"])
def test_preview_envelope_never_changes_or_claims_full_voice_acceptance(broken):
    from klippy.voice_probe import qualify_preview_report
    report = {"passed": False, "gates": {"captured_status": False, "negative_words": False,
              "standalone_wake": True, "own_echo": True, "verified_interruption": True,
              "local_language": True, "no_printer_writes": True},
              "paced_pipeline_transcripts": ["Klippy", "status"], "paced_status_response": "63% complete",
              "query_catalog": {"passed": True, "printer_writes": 0, "pending_write": False},
              "negative_composite": [{"accepted_requests": [], "session_open": False} for _ in range(6)]}
    if broken in report["gates"]:
        report["gates"][broken] = False
    elif broken == "paced_status":
        report["paced_status_response"] = None
    elif broken == "query":
        report["query_catalog"]["passed"] = False
    elif broken == "query_write":
        report["query_catalog"]["printer_writes"] = 1
    elif broken == "negative_accept":
        report["negative_composite"][0]["accepted_requests"] = ["Klippy status"]
    elif broken == "negative_session":
        report["negative_composite"][0]["session_open"] = True
    qualify_preview_report(report)
    assert report["passed"] is False and report["continuous_wake_status_passed"] is False
    assert report["engineering_preview_passed"] is (broken is None)


def test_full_voice_and_preview_qualification_modes_cannot_be_combined():
    import subprocess
    import sys
    result = subprocess.run([sys.executable, "-m", "klippy.app", "--voice-self-test", "--preview-self-test"],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 2 and "not allowed with argument" in result.stderr


async def test_read_only_model_timeout_has_safe_diagnostic_code(monkeypatch):
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            raise httpx.ReadTimeout("private endpoint and response details")
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(Rejected) as caught:
        await LocalLLM().interpret_query("Has the machine established a reference?")
    assert caught.value.code == "ReadTimeout"
    assert "private" not in str(caught.value)


async def test_native_query_probe_retains_all_cases_when_model_rejects():
    from klippy.query_probe import run
    class Model:
        async def interpret_query(self, text):
            rejection = Rejected("private details must not enter the report")
            rejection.code = "ReadTimeout"
            raise rejection
    report = await run(Model())
    assert not report["passed"] and len(report["cases"]) == 11
    assert all(row["passed"] for row in report["cases"][:-1])
    assert report["cases"][-1]["error_code"] == "ReadTimeout"
    assert "private details" not in json.dumps(report)


@pytest.mark.parametrize("phrase,axis", [
    ("What's the height of the z-axis right now?", "z"),
    ("What is my Z height?", "z"), ("How high is the nozzle?", "z"),
    ("What's the nozzle elevation?", "z"), ("Tell me the Z axis location", "z"),
    ("Where is the X axis right now?", "x"), ("What is the y coordinate?", "y"),
    ("Z position", "z"), ("What is the zed axis height?", "z"),
])
def test_spatial_measurement_variations_are_deterministic(phrase, axis):
    q = match_query(phrase, QueryRequest(query_id="temperatures", subject="nozzle"))
    assert q.query_id == "position" and q.subject == axis


@pytest.mark.parametrize("phrase,identifier", [
    ("What's the layer height?", "metadata"), ("What's the maximum Z height?", "configuration"),
    ("Is the Z axis homed?", "homing"), ("What's the Z axis acceleration?", "limits"),
    ("What's the nozzle temperature at Z height 10?", "temperatures"),
    ("What's my Z offset?", "gcode_position"),
])
def test_position_height_does_not_steal_other_measurements(phrase, identifier):
    assert match_query(phrase).query_id == identifier


async def test_temperature_homing_z_height_sequence_cannot_inherit_wrong_query(queries):
    sim, service, engine, _ = queries
    c = Conversation(engine, NoActionLLM(), queries=service)
    await c.hear("how hot is the nozzle?")
    await c.hear("is the printer homed?")
    start = len(sim.calls)
    answer = await c.hear("What's the height of the Z-axis right now?")
    assert "Z position: 3 mm" in answer and "Z not homed" in answer
    assert "Not measured physical position" in answer and "degrees" not in answer
    assert c.last_query.query_id == "position" and c.last_query.subject == "z"
    assert all(method == "GET" for method, _, _ in sim.calls[start:])
    assert engine.pending is None
    followup = await c.hear("what about the X axis?")
    assert "X position: 1 mm" in followup


@pytest.mark.parametrize("wrong", ["temperatures", "homing", "job", "fans", "targets"])
async def test_model_cannot_answer_an_unknown_spatial_measurement_with_unrelated_information(queries, wrong):
    sim, service, engine, _ = queries
    class Wrong:
        async def interpret_query(self, text):
            return QueryRequest(query_id=wrong)
    c = Conversation(engine, Wrong(), queries=service)
    with pytest.raises(Rejected, match="couldn't match that measurement") as exc:
        await c.hear("What length is reported?")
    assert exc.value.code == "query_measurement_mismatch" and not sim.calls and engine.pending is None


async def test_mixed_position_temperature_question_clarifies_before_any_read(queries):
    sim, service, engine, _ = queries
    c = Conversation(engine, NoActionLLM(), queries=service)
    with pytest.raises(Rejected, match="separately"):
        await c.hear("What's the Z height and bed temperature?")
    assert not sim.calls and engine.pending is None


@pytest.mark.parametrize("value", [None, [1,2], [1,2,float("nan")], [1,2,True]])
def test_axis_projection_keeps_malformed_or_missing_data_unknown(value):
    text = render("position", {"toolhead":{"position":value,"homed_axes":""}}, {}, "z")
    assert "unavailable" in text and "Z not homed" in text


def test_bare_axis_after_temperature_requires_clarification():
    with pytest.raises(QueryUnavailable, match="position or whether"):
        match_query("what about Z", QueryRequest(query_id="temperatures", subject="bed"))


@pytest.mark.parametrize("identifier,subject", [("homing", "x"), ("homing", "nozzle"),
                                               ("position", "bed"), ("temperatures", "z")])
async def test_model_query_subject_must_belong_to_selected_query_even_if_server_ignores_schema(monkeypatch, identifier, subject, queries):
    sim, service, engine, _ = queries
    with pytest.raises(QueryUnavailable, match="doesn't match"):
        await service.answer("sim", QueryRequest(query_id=identifier, subject=subject))
    assert not sim.calls and engine.pending is None
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": json.dumps({"query_id": identifier, "subject": subject})}}]}
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            return Response()
    monkeypatch.setattr(httpx, "AsyncClient", Client)
    with pytest.raises(Rejected) as error:
        await LocalLLM().interpret_query("Has the machine established its coordinate reference?")
    assert error.value.code == "ValueError"
