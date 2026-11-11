from __future__ import annotations

import asyncio
import math
import re
import secrets
import time
from dataclasses import dataclass

from .domain import Action, Intent, Snapshot, digest, safe_macro_name
from .macros import discover
from .moonraker import ConnectionFailure


class Rejected(Exception):
    pass


class NeedsParameter(Rejected):
    def __init__(self, name):
        self.name = name
        super().__init__(f"Specify parameter {name}")


READ_ONLY = {Action.STATUS, Action.TEMPERATURES, Action.MACROS}


@dataclass(frozen=True)
class Pending:
    token: str
    intent_json: str
    expires: float
    binding: str


class SafetyEngine:
    """The single write authority. Each write rechecks enrollment, policy, state and macro freshness."""

    def __init__(self, store, clients, clock=time.monotonic):
        self.store, self.clients, self.clock = store, clients, clock
        self.pending: Pending | None = None
        self.lock = asyncio.Lock()
        self.generation = 0

    def cancel(self):
        self.generation += 1
        self.pending = None

    def select(self, printer_id):
        self.cancel()
        if printer_id not in {p.id for p in self.store.printers()}:
            raise Rejected("Select an enrolled printer")
        self.store.set("selected", printer_id)

    async def validate(self, intent: Intent):
        printer = next((p for p in self.store.printers() if p.id == intent.printer_id), None)
        if printer is None or not printer.approved:
            raise Rejected("Printer is not approved")
        if self.store.get("selected") != printer.id:
            raise Rejected("Select the target printer first")
        if intent.macro is not None and intent.action != Action.MACRO:
            raise Rejected("Unexpected macro field")
        if intent.action not in (Action.MACRO, Action.HEAT) and intent.params:
            raise Rejected("Unexpected parameters")
        client = self.clients(printer)
        # Explicit emergency commands bypass the ready-state query but never enrollment/selection.
        state = Snapshot(connected=True) if intent.action == Action.EMERGENCY else await client.snapshot()
        if not state.connected:
            raise Rejected("Printer disconnected")
        script, policy = None, {}
        if intent.action not in READ_ONLY and intent.action != Action.EMERGENCY:
            if not state.ready:
                raise Rejected("Printer is not ready")
            required = {Action.PAUSE: {"printing"}, Action.RESUME: {"paused"},
                        Action.CANCEL: {"printing", "paused"}, Action.HOME: {"standby", "complete", "cancelled"},
                        Action.HEAT: {"standby", "complete", "cancelled", "paused"},
                        Action.MACRO: {"standby", "complete", "cancelled"}}
            if state.state not in required.get(intent.action, set()):
                raise Rejected("Current printer state does not permit this operation")
        if intent.action == Action.HOME:
            script = "G28"
        if intent.action == Action.HEAT:
            # No guessed heater limits. Installations must have verified limits in settings.
            if set(intent.params) != {"temperature", "heater"}:
                raise Rejected("Specify heater (0=nozzle, 1=bed) and temperature")
            heater, temperature = intent.params["heater"], intent.params["temperature"]
            if heater not in (0, 1) or not math.isfinite(temperature):
                raise Rejected("Invalid heater or temperature")
            limits = self.store.get("heater_limits", {}).get(printer.id, {})
            maximum = limits.get(str(int(heater)))
            if maximum is None or not 0 <= temperature <= maximum:
                raise Rejected("Temperature is outside locally reviewed heater limits")
            policy = {"maximum": maximum}
            script = f"{'M104' if heater == 0 else 'M140'} S{temperature:g}"
        if intent.action == Action.MACRO:
            if not intent.macro or not safe_macro_name(intent.macro):
                raise Rejected("Invalid macro")
            current, _ = discover(await client.macro_config(), self.store.macros(printer.id))
            self.store.replace_macros(printer.id, current)
            macro = current.get(intent.macro)
            if macro is None or not (macro.approved and macro.enabled and macro.reviewed):
                raise Rejected("Macro is missing, changed, excluded, or awaiting review")
            if not macro.definition.strip():
                raise Rejected("Macro definition is unavailable")
            if set(intent.params) - set(macro.parameters):
                raise Rejected("Unknown macro parameter")
            for key, rule in macro.parameters.items():
                if not re.fullmatch(r"[A-Z_][A-Z_0-9]*", key):
                    raise Rejected("Invalid parameter schema")
                if key not in intent.params:
                    if rule.required:
                        raise NeedsParameter(key)
                    continue
                v = intent.params[key]
                if not math.isfinite(v) or not rule.minimum <= v <= rule.maximum or (rule.integer and int(v) != v):
                    raise Rejected(f"Parameter {key} is outside its reviewed limits")
            # Detect unresolved parameter references, including indirect Jinja access.
            from .macros import inferred_parameters
            if set(inferred_parameters(macro.definition)) - set(macro.parameters):
                raise Rejected("Macro parameter schema needs review")
            if re.search(r"params\s*\[|params\s*\||rawparams", macro.definition):
                raise Rejected("Dynamic macro parameters require additional review; voice execution blocked")
            script = macro.name + "".join(f" {key}={value:g}" for key, value in sorted(intent.params.items()))
            policy = macro.model_dump(mode="json")
            # Discovery can take time. Recheck printer readiness immediately after it.
            fresh = await client.snapshot()
            if fresh.ready != state.ready or fresh.state != state.state:
                raise Rejected("Printer state changed during macro validation")
            state = fresh
        binding = digest({"intent": intent.model_dump(mode="json"), "printer": printer.model_dump(mode="json"),
                          "state": {"ready": state.ready, "state": state.state}, "policy": policy})
        return client, state, script, binding

    async def propose(self, intent: Intent):
        async with self.lock:
            self.cancel()
            generation = self.generation
            client, state, _script, binding = await self.validate(intent)
            if generation != self.generation:
                raise Rejected("Request was canceled or target changed during validation")
            if intent.action in READ_ONLY:
                if intent.action == Action.TEMPERATURES:
                    return "; ".join(f"{k}: {v:.1f} degrees" for k, v in state.temperatures.items()) or "No temperatures available"
                if intent.action == Action.MACROS:
                    current, notices = discover(await client.macro_config(), self.store.macros(intent.printer_id))
                    self.store.replace_macros(intent.printer_id, current)
                    return "Macros: " + ", ".join(current) + (". " + "; ".join(notices) if notices else "")
                return f"{state.state}; {state.progress:.0%} complete"
            self.pending = Pending(secrets.token_urlsafe(24), intent.model_dump_json(), self.clock() + 25, binding)
            printer = next(p for p in self.store.printers() if p.id == intent.printer_id)
            warning = " Check the bed and toolhead path are clear." if intent.action in (Action.HOME, Action.MACRO) else ""
            return f"Confirm {intent.action.value} on {printer.name}?{warning} Say exactly 'confirm' or choose Confirm within 25 seconds."

    async def confirm(self, token):
        async with self.lock:
            pending = self.pending
            self.cancel()  # Single use, including failure. Never retry a consequential request.
            generation = self.generation
            if pending is None or not secrets.compare_digest(token, pending.token) or self.clock() >= pending.expires:
                raise Rejected("Confirmation is missing or expired")
            intent = Intent.model_validate_json(pending.intent_json)
            client, _state, script, binding = await self.validate(intent)
            if generation != self.generation or binding != pending.binding:
                raise Rejected("Printer state, macro, or permissions changed; request again")
            try:
                await client.execute(intent, script)
            except ConnectionFailure:
                self.store.event(intent.printer_id, "outcome_unknown")
                return "Transmission outcome is unknown. I will not retry. Check the printer before requesting another action."
            self.store.event(intent.printer_id, "command_sent")
            if intent.action in (Action.PAUSE, Action.RESUME, Action.CANCEL):
                try:
                    after = await client.snapshot()
                    expected = {Action.PAUSE: "paused", Action.RESUME: "printing", Action.CANCEL: "cancelled"}
                    if after.state == expected[intent.action]:
                        return f"Printer reports {after.state}."
                except ConnectionFailure:
                    pass
            return "Request accepted; physical completion has not been verified."
