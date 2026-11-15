"""Synthetic multi-turn factual dialogue, actual optional local model, no hardware."""

import tempfile
import time
from pathlib import Path

import httpx

from .conversation import Conversation
from .domain import Printer
from .moonraker import Moonraker
from .queries import QueryService
from .safety import SafetyEngine
from .storage import Store


def simulator():
    writes = []
    status = {
        "toolhead": {"homed_axes": "xyz"},
        "extruder": {"temperature": 27.0, "target": 0.0},
        "heater_bed": {"temperature": 25.0, "target": 0.0},
        "webhooks": {"state": "ready"},
        "print_stats": {"state": "standby"},
    }

    def handle(request):
        if request.method != "GET":
            writes.append(request.url.path)
            raise AssertionError("No hardware writes permitted in dialogue qualification")
        if request.url.path == "/server/info":
            result = {"components": [], "klippy_connected": True, "klippy_state": "ready"}
        elif request.url.path == "/printer/objects/list":
            result = {"objects": list(status)}
        elif request.url.path == "/printer/objects/query":
            result = {
                "status": {
                    name: {
                        key: value
                        for key, value in status.get(name, {}).items()
                        if not fields or key in fields.split(",")
                    }
                    for name, fields in request.url.params.items()
                }
            }
        else:
            raise AssertionError("Unreviewed query route")
        return httpx.Response(200, json={"result": result})

    return httpx.MockTransport(handle), writes


async def run(model):
    with tempfile.TemporaryDirectory(prefix="klippy-dialogue-") as temp:
        store = Store(Path(temp) / "settings.sqlite")
        store.save_printer(Printer(id="sim", name="Simulated M1", url="http://127.0.0.1:1", approved=True))
        store.set("selected", "sim")
        transport, writes = simulator()

        def clients(p):
            return Moonraker(p, transport=transport)

        engine = SafetyEngine(store, clients)
        queries = QueryService(store, clients)

        class Observed:
            calls = 0

            async def compose_reply(self, *args):
                self.calls += 1
                return await model.compose_reply(*args)

        observed = Observed()
        conversation = Conversation(engine, observed, queries=queries)
        try:
            start = time.perf_counter()
            routine = await conversation.hear("Klippy how hot is the nozzle?")
            routine_ms = (time.perf_counter() - start) * 1000
            calls_after_routine = observed.calls
            bed = await conversation.hear("and the bed?")
            start = time.perf_counter()
            explanation = await conversation.hear("why is that?")
            explanation_ms = (time.perf_counter() - start) * 1000
            thanks = await conversation.hear("thank you")
            store.set("selected", None)
            greeting = await conversation.hear("hello")
            checks = {
                "routine_no_model": calls_after_routine == 0,
                "routine_verified_nozzle": "27" in getattr(routine, "spoken", routine),
                "followup_bed": "25" in getattr(bed, "spoken", bed),
                "actual_model_composed": bool(getattr(explanation, "model_composed", False)),
                "explanation_keeps_verified_observation": "25" in str(explanation),
                "casual_without_printer": bool(greeting and thanks),
                "no_pending_or_writes": not writes and engine.pending is None,
                "model_latency_bounded": explanation_ms < 4500,
            }
            return {
                "passed": all(checks.values()),
                "checks": checks,
                "routine_ms": round(routine_ms, 2),
                "explanation_ms": round(explanation_ms, 2),
                "model_calls": observed.calls,
                "dialogue_diagnostic": getattr(explanation, "dialogue_diagnostic", None),
                "model_tokens": getattr(model, "dialogue_metrics", {}),
                "scope": "Actual local model; fresh simulated Moonraker facts and constrained clause composition; no devices/printer writes",
            }
        finally:
            store.close()
