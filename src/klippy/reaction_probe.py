"""Repeatable local reaction using a simulated printer; never uses saved enrollment."""
import tempfile
from pathlib import Path

import httpx

from .conversation import Conversation
from .diagnostics import current, timings
from .domain import Printer
from .moonraker import Moonraker
from .safety import SafetyEngine
from .storage import Store


async def run():
    trace = timings.new()
    context = current.set(trace)
    try:
        with tempfile.TemporaryDirectory(prefix="klippy-reaction-") as directory:
            store = Store(Path(directory) / "probe.sqlite")
            try:
                printer = Printer(id="simulation", name="Simulated printer", url="http://127.0.0.1:7125", approved=True)
                store.save_printer(printer)
                store.set("selected", printer.id)
                def handle(request):
                    if request.method != "GET":
                        raise AssertionError("Reaction probe must remain read-only")
                    return httpx.Response(200, json={"result": {"status": {
                        "webhooks": {"state": "ready"}, "print_stats": {"state": "printing"},
                        "virtual_sdcard": {"progress": .63}, "extruder": {"temperature": 23},
                        "heater_bed": {"temperature": 21}}}})
                engine = SafetyEngine(store, lambda p: Moonraker(p, transport=httpx.MockTransport(handle)))
                with timings.span("intent_and_validation"):
                    text = await Conversation(engine).hear("Klippy tell me the temperatures", source="voice")
                return trace, text
            finally:
                store.close()
    finally:
        current.reset(context)
