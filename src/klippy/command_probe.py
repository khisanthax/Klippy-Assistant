"""Packaged parser/safety qualification. Mock transport forbids every write."""
import math
import tempfile
from pathlib import Path

import httpx

from .conversation import Conversation
from .domain import Action, Intent, Printer
from .limits_probe import synthetic_status
from .moonraker import Moonraker
from .safety import Rejected, SafetyEngine
from .storage import Store


async def run():
    writes, model_calls, cases = [], [], []
    eventtime = 0
    def transport(request):
        nonlocal eventtime
        if request.method != "GET":
            writes.append(request.url.path)
            raise AssertionError("Command qualification cannot send a heating operation")
        eventtime += 1
        status = synthetic_status()
        result = {'objects': list(status)} if request.url.path.endswith('/list') else {'status': status, 'eventtime': eventtime}
        return httpx.Response(200, json={'result': result})
    class NoModel:
        async def interpret(self, *args):
            model_calls.append(True)
            raise AssertionError("Supported heating request reached LLM")
        interpret_query = interpret
    with tempfile.TemporaryDirectory(prefix="klippy-command-probe-") as root:
        store = Store(Path(root) / "test.sqlite")
        try:
            store.save_printer(Printer(id="sim", name="Mercury One", aliases=("M1",), url="http://127.0.0.1:1", approved=True))
            store.set("selected", "sim")
            store.set("heater_limits", {"sim": {"0": 200, "1": 100}})
            engine = SafetyEngine(store, lambda p: Moonraker(p, transport=httpx.MockTransport(transport)))
            c = Conversation(engine, NoModel())
            for phrase in (
                "Hey Klippy, can you set the Mercury 1 nozzle to 90 degrees Celsius?",
                "Set M1's nozzle to 90 degrees.", "Can you set the Mercury 1 nozzle to 90 Celsius?",
                "Heat Mercury One's hotend to 90.", "Set the nozzle temperature to 90 on M1.",
                "Bring the nozzle up to 90 degrees.", "Heat Mercury One nozzle to ninety",
                "Heat nozzle to 194 F", "Heat nozzle to 90",
            ):
                answer = await c.hear(phrase)
                intent = Intent.model_validate_json(engine.pending.intent_json) if engine.pending else None
                cases.append({"case": "heat_celsius_review", "synthetic_phrase": phrase,
                              "passed": bool(intent and intent.action == Action.HEAT and intent.params == {"heater":0,"temperature":90}
                                             and intent.printer_id == "sim" and "90 degrees Celsius" in answer and not writes)})
            for phrase in ("No, don't do that.", "Cancel that request.", "Never mind.", "Don't heat the nozzle."):
                await c.hear("heat nozzle 90")
                answer = await c.hear(phrase)
                cases.append({"case": "explicit_cancel", "synthetic_phrase": phrase, "passed": "canceled" in answer and engine.pending is None})
            for phrase in ("I'm not sure why it didn't understand.", "That's not what I meant.", "I don't know what happened."):
                await c.hear("heat nozzle 90", defer_confirmation=True)
                token = engine.pending.token
                answer = await c.hear(phrase)
                engine.delivery_finished(token, True)
                blocked = False
                try:
                    await engine.confirm(token)
                except Rejected as exc:
                    blocked = exc.code == "confirmation_needs_clarification"
                cases.append({"case": "clarification_not_cancellation", "synthetic_phrase": phrase, "passed": bool(blocked and engine.pending
                              and engine.pending.token == token and not engine.pending.ready and "canceled" not in answer)})
            for phrase in ("heat nozzle 500 F", "set nozzle temperature", "heat nozzle 90 C F"):
                blocked = False
                try:
                    await c.hear(phrase)
                except Rejected:
                    blocked = True
                cases.append({"case": "ambiguous_or_outside_limits", "synthetic_phrase": phrase, "passed": blocked and engine.pending is None})
            store.save_printer(Printer(id="unit",name="F",url="http://127.0.0.1:2",approved=True))
            store.set("heater_limits", {"sim":{"0":200,"1":100},"unit":{"0":40}})
            correct = True
            for phrase, expected in (("heat nozzle 90 F","sim"), ("heat nozzle 90 F on F","unit")):
                await c.hear(phrase)
                intent = Intent.model_validate_json(engine.pending.intent_json)
                correct = correct and intent.printer_id == expected and math.isclose(intent.params["temperature"], (90-32)*5/9, rel_tol=1e-12)
            cases.append({"case":"temperature_operands_not_printer_mentions","passed":correct and not writes})
            engine.select("sim")
            class WrongModel:
                async def interpret(self, *args):
                    return Intent(action=Action.TEMPERATURES, printer_id="sim", params={"heater":0,"temperature":90})
            blocked = False
            try:
                await Conversation(engine, WrongModel()).hear("adjust nozzle to 90")
            except Rejected as exc:
                blocked = exc.code == "intent_parameters_for_temperatures" and "Unexpected parameters" not in str(exc)
            cases.append({"case": "invalid_model_action_parameters", "passed": blocked and engine.pending is None})
            c.clear()
            return {"scope": "Deterministic heating/cancellation with injected simulated Moonraker; every HTTP write forbidden",
                    "cases": cases, "printer_writes": len(writes), "supported_request_llm_calls": len(model_calls),
                    "pending_write": engine.pending is not None,
                    "passed": all(row["passed"] for row in cases) and not writes and not model_calls and engine.pending is None}
        finally:
            store.close()
