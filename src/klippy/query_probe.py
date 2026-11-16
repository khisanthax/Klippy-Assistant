"""Frozen/source query qualification; injected loopback simulator, no physical APIs."""
import tempfile
import time
from pathlib import Path

import httpx

from .conversation import Conversation
from .diagnostics import current, timings
from .domain import Printer
from .moonraker import Moonraker
from .queries import QueryService
from .query_catalog import CATALOG
from .safety import Rejected, SafetyEngine
from .storage import Store


async def run(model):
    calls, writes = [], []
    def transport(request):
        calls.append(request.url.path)
        if request.method != "GET":
            writes.append(request.url.path)
            raise AssertionError("Query probe cannot actuate")
        status = {"toolhead": {"homed_axes": "xy" if request.url.port == 1 else "xyz", "position": [0, 0, 10]},
                  "extruder": {"temperature": 23.0, "target": 210.0},
                  "heater_bed": {"temperature": 55.0, "target": 60.0},
                  "print_stats": {"state": "printing", "info": {"current_layer": 3, "total_layer": 100}},
                  "webhooks": {"state": "ready"}, "virtual_sdcard": {"progress": .63}}
        if request.url.path == "/server/info":
            value = {"components": [], "klippy_connected": True, "klippy_state": "ready"}
        elif request.url.path == "/printer/objects/list":
            value = {"objects": list(status)}
        elif request.url.path == "/printer/objects/query":
            value = {"eventtime": time.monotonic(), "status": {name: {k: v for k, v in status.get(name, {}).items()
                     if not fields or k in fields.split(",")} for name, fields in request.url.params.items() if name in status}}
        else:
            raise AssertionError("Unexpected probe endpoint")
        return httpx.Response(200, json={"result": value})
    with tempfile.TemporaryDirectory(prefix="klippy-query-probe-") as temp:
        store = Store(Path(temp)/"test.sqlite")
        try:
            for pid, name, port, aliases in (("m1", "M1", 1, ("Mercury One",)), ("sv", "SV08", 2, ())):
                store.save_printer(Printer(id=pid, name=name, url=f"http://127.0.0.1:{port}", aliases=aliases, approved=True))
            store.set("selected", "m1")
            def clients(printer):
                return Moonraker(printer, transport=httpx.MockTransport(transport))
            service = QueryService(store, clients)
            engine = SafetyEngine(store, clients)
            conversation = Conversation(engine, model, queries=service)
            cases = []
            for text, expected in (
                ("Klippy, is my M1 printer homed?", "Not homed: Z"),
                ("What about the SV08?", "Not homed: none"),
                ("How hot is the bed?", "55"),
                ("What's the target temperature?", "60"),
                ("What layer am I on?", "layer 3 of 100"),
                ("Is Mercury One homed?", "Not homed: Z"),
                ("What's the height of the z-axis right now?", "Z position: 10 mm"),
                ("What about the X axis?", "X position: 0 mm"),
                ("How hot is the nozzle?", "23"),
                ("How high is the nozzle?", "Z position: 10 mm"),
                ("Has the machine established its coordinate reference?", "Not homed: Z"),
            ):
                trace = timings.new()
                token = current.set(trace)
                start = time.perf_counter()
                count = len(calls)
                error = None
                try:
                    try:
                        answer = await conversation.hear(text)
                    except Rejected as exc:
                        answer = None
                        error = getattr(exc, "code", "Rejected")
                finally:
                    current.reset(token)
                cases.append({"synthetic_question": text, "answer": answer,
                              "milliseconds": round((time.perf_counter()-start)*1000, 3),
                              "http_reads": len(calls)-count, "error_code": error,
                              "passed": isinstance(answer, str) and expected in answer})
            return {"scope": "Real local query LLM, deterministic parser and injected simulated printers; no hardware/network APIs",
                    "catalog_queries": len(CATALOG), "cases": cases, "printer_writes": len(writes),
                    "pending_write": engine.pending is not None,
                    "passed": all(row["passed"] for row in cases) and not writes and engine.pending is None}
        finally:
            store.close()
