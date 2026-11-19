from __future__ import annotations

import asyncio
import math
import re
import secrets
import threading
import time
from dataclasses import dataclass, replace
from decimal import Decimal

from .diagnostics import current as reaction_context
from .diagnostics import timings
from .domain import Action, Intent, Snapshot, digest, safe_macro_name
from .limits import LimitsRegistry, LimitsUnavailable, number
from .macros import discover
from .moonraker import ConnectionFailure


class Rejected(Exception):
    def __init__(self, message, *, code="request_rejected"):
        super().__init__(message)
        self.code = code


def validate_intent_fields(intent):
    if intent.query_subject is not None and intent.action != Action.TEMPERATURES:
        raise Rejected(
            "The heater question doesn't match the requested operation. Please restate your request.",
            code="intent_subject_action_mismatch",
        )
    if intent.macro is not None and intent.action != Action.MACRO:
        raise Rejected(
            "The macro name doesn't match the requested operation. Please restate your request.",
            code="intent_macro_action_mismatch",
        )
    if intent.action not in (Action.MACRO, Action.HEAT, Action.MOVE) and intent.params:
        raise Rejected(
            "I couldn't match those settings to a heating or macro request. Please restate the operation and target; I haven't sent a command.",
            code="intent_parameters_for_" + intent.action.value,
        )


class NeedsParameter(Rejected):
    def __init__(self, name):
        self.name = name
        super().__init__(f"Specify parameter {name}")


def numeric_text(value):
    """Round-trip the validated decimal without rounding or G-code exponent syntax."""
    text = format(Decimal(str(value)), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def action_details(intent):
    if intent.action in (Action.PAUSE, Action.RESUME, Action.CANCEL):
        return intent.action.value + " print"
    if intent.action == Action.HOME:
        return "home all axes"
    if intent.action == Action.HEAT:
        heater = "bed" if intent.params["heater"] == 1 else "nozzle"
        return f"heat {heater} to {numeric_text(intent.params['temperature'])} degrees Celsius"
    if intent.action == Action.MACRO:
        values = ", ".join(f"{key}={numeric_text(value)}" for key, value in sorted(intent.params.items()))
        return f"macro {intent.macro}" + (f" with {values}" if values else "")
    return intent.action.value.replace("_", " ")


READ_ONLY = {Action.STATUS, Action.TEMPERATURES, Action.MACROS}


class Validation(tuple):
    def __new__(cls, client, state, script, binding, review=None):
        result = super().__new__(cls, (client, state, script, binding))
        result.review = review
        return result


@dataclass(frozen=True)
class Pending:
    token: str
    intent_json: str
    expires: float
    binding: str
    ready: bool = True
    hard_expires: float = 0.0
    clarification_required: bool = False


CONFIGURABLE_CONFIRMATIONS = (Action.PAUSE, Action.RESUME, Action.CANCEL, Action.HOME, Action.HEAT)
IN_FLIGHT = "Transmission has already started. Check the printer for the outcome."


class SafetyEngine:
    """The single write authority. Each write rechecks enrollment, policy, state and macro freshness."""

    def __init__(self, store, clients, clock=time.monotonic):
        self.store, self.clients, self.clock = store, clients, clock
        self.state_lock = threading.RLock()
        self.pending: Pending | None = None
        self.lock = asyncio.Lock()
        self.generation = 0
        self.dispatch_committed = False
        self.validating = False
        self.last_dispatch_trace = None
        self.confirmation_seconds = 25
        self.history = None
        self.pending_trace = None
        self.limits = LimitsRegistry(store, clients, clock=clock)
        self.limits.on_invalidate = self.limits_invalidated

    def limits_invalidated(self, printer_id):
        with self.state_lock:
            if self.pending:
                intent = Intent.model_validate_json(self.pending.intent_json)
                if intent.printer_id == printer_id and intent.action in {Action.MOVE, Action.HEAT}:
                    self.cancel("capability_changed")

    def audit(self, event, *, trace=None, **fields):
        if self.history:
            try:
                self.history.record(event, trace=trace, **fields)
            except Exception:
                timings.error('history_storage_unavailable')

    def cancel(self, reason="canceled"):
        with self.state_lock:
            if self.pending is not None:
                self.audit(
                    reason,
                    trace=self.pending_trace,
                    outcome=reason if reason in {"canceled", "expired", "failed"} else None,
                )
            had_request = self.pending is not None or self.validating
            self.generation += 1
            self.pending = None
            if self.dispatch_committed:
                return IN_FLIGHT
            return "Pending action canceled." if had_request else "No pending action."

    def confirmation_required(self, action, force=False):
        return (force or action not in CONFIGURABLE_CONFIRMATIONS
                or self.store.get("confirmations", {}).get(action.value) is not False)

    def delivery_finished(self, token, success):
        with self.state_lock:
            pending = self.pending
            if pending is None or pending.token != token or pending.ready or pending.clarification_required:
                return
            if not success or self.clock() >= pending.hard_expires:
                self.cancel("failed" if not success else "expired")
            else:
                self.pending = replace(
                    pending,
                    ready=True,
                    expires=min(pending.hard_expires, self.clock() + self.confirmation_seconds),
                )
                self.audit("prompt_delivered", trace=self.pending_trace)

    def require_clarification(self):
        with self.state_lock:
            self.generation += 1  # Invalidate validation still in flight, without canceling a pending review.
            if self.pending is not None:
                self.audit('clarification_needed',trace=self.pending_trace,outcome='clarification_needed',clarification_requested=True)
                self.pending = replace(self.pending, ready=False, clarification_required=True)

    def select(self, printer_id):
        self.cancel()
        if printer_id not in {p.id for p in self.store.printers()}:
            raise Rejected("Select an enrolled printer")
        self.store.set("selected", printer_id)

    async def validate(self, intent: Intent):
        with timings.span('command_validation'):
            try:
                return await self._validate(intent)
            except LimitsUnavailable as exc:
                raise Rejected(str(exc), code="printer_limits_unavailable") from None

    async def _validate(self, intent: Intent):
        printer = next((p for p in self.store.printers() if p.id == intent.printer_id), None)
        if printer is None or not printer.approved:
            raise Rejected("Printer is not approved")
        if self.store.get("selected") != printer.id:
            raise Rejected("Select the target printer first")
        if (intent.action in {Action.MOVE, Action.HEAT, Action.MACRO, Action.HOME}
                and printer.id in self.store.get('limits_review_required', {})):
            raise Rejected("Review the restored limits for this printer in Settings before requesting that action.")
        validate_intent_fields(intent)
        client = self.clients(printer)
        # Explicit emergency commands bypass the ready-state query but never enrollment/selection.
        state = Snapshot(connected=True) if intent.action == Action.EMERGENCY else await client.snapshot()
        if not state.connected:
            raise Rejected("Printer disconnected")
        script, policy, motion_review = None, {}, None
        if intent.action not in READ_ONLY and intent.action != Action.EMERGENCY:
            if not state.ready:
                raise Rejected("Printer is not ready")
            required = {
                Action.PAUSE: {"printing"},
                Action.RESUME: {"paused"},
                Action.CANCEL: {"printing", "paused"},
                Action.HOME: {"standby", "complete", "cancelled"},
                Action.HEAT: {"standby", "complete", "cancelled", "paused"},
                Action.MOVE: {"standby", "complete", "cancelled"},
                Action.MACRO: {"standby", "complete", "cancelled"},
            }
            if state.state not in required.get(intent.action, set()):
                raise Rejected("Current printer state does not permit this operation")
        if intent.action == Action.HOME:
            script = "G28"
        if intent.action == Action.HEAT:
            # Firmware authority plus optional stricter owner caps; no guessed limits.
            if set(intent.params) != {"temperature", "heater"}:
                raise Rejected("Specify heater (0=nozzle, 1=bed) and temperature")
            heater, temperature = intent.params["heater"], intent.params["temperature"]
            if heater not in (0, 1) or not math.isfinite(temperature):
                raise Rejected("Invalid heater or temperature")
            name = "heater_bed" if heater == 1 else "extruder"
            measured = state.temperatures.get(name)
            if measured is None or not math.isfinite(measured) or measured < -273.15:
                raise Rejected(
                    "The selected printer isn't reporting a valid temperature for that heater. Check its connection before requesting heat.",
                    code="heat_heater_unavailable",
                )
            record = await self.limits.refresh(printer)
            if (heater == 0 and record.status.get('toolhead', {}).get('extruder') != 'extruder'
                    or ('M140' if heater == 1 else 'M104') in record.capabilities['shadowed_commands']):
                raise Rejected("The active heater or overridden heater command cannot be verified; use supervised printer controls.")
            if record.status.get('print_stats', {}).get('state') not in {"standby", "complete", "cancelled", "paused"}:
                raise Rejected("Current printer state does not permit heating")
            reported = record.status.get(name, {}).get('temperature')
            if number(reported) is None or reported < -273.15:
                raise Rejected("The selected heater is not reporting a valid current temperature.", code="heat_heater_unavailable")
            configured = self.limits.effective(record)['heaters'].get(name, {})
            minimum, maximum = configured.get('min_temp'), configured.get('max_temp')
            if number(minimum) is None or number(maximum) is None or minimum >= maximum or maximum <= 0:
                raise Rejected("Active Klipper heater limits are unavailable or invalid; heating is blocked.", code="heat_limits_unknown")
            caps = self.store.get("heater_limits", {}).get(printer.id, {})
            owner_cap = caps.get(str(int(heater)))
            if str(int(heater)) in caps:
                if number(owner_cap) is None or owner_cap < 0:
                    raise Rejected("The owner's heater limits are invalid; review local limits.")
                maximum = min(maximum, owner_cap)
            if not (temperature == 0 or max(0,minimum) <= temperature <= maximum) or temperature > maximum:
                raise Rejected("Temperature is outside the active Klipper or stricter owner heater limits.")
            policy = {"minimum": minimum, "maximum": maximum, "configuration":record.fingerprint,
                      "generation":record.generation, "owner_caps":caps,
                      "owner_overrides":self.store.get('printer_limit_overrides',{}).get(printer.id,{})}
            script = f"{'M104' if heater == 0 else 'M140'} S{numeric_text(temperature)}"
        if intent.action == Action.MOVE:
            from .motion import plan_move
            record = await self.limits.refresh(printer)
            plan = plan_move(intent,record,self.limits.effective(record),self.store.get('printer_limit_overrides',{}).get(printer.id,{}))
            script, policy, motion_review = plan.script, plan.binding, plan.review
        if intent.action == Action.MACRO:
            if not intent.macro or not safe_macro_name(intent.macro):
                raise Rejected("Invalid macro")
            current, _ = discover(await client.macro_config(), self.store.macros(printer.id), analyze_conflicts=False)
            self.store.replace_macros(printer.id, current)
            macro = current.get(intent.macro)
            if macro is None or not (macro.approved and macro.enabled and macro.reviewed):
                raise Rejected("Macro is missing, changed, excluded, or awaiting review")
            if not macro.definition.strip():
                raise Rejected("Macro definition is unavailable")
            if set(intent.params) - set(macro.parameters):
                raise Rejected("Unknown macro parameter")
            for key, rule in macro.parameters.items():
                if (
                    not math.isfinite(rule.minimum)
                    or not math.isfinite(rule.maximum)
                    or rule.minimum > rule.maximum
                ):
                    raise Rejected("Macro parameter bounds need review")
                if not re.fullmatch(r"[A-Z_][A-Z_0-9]*", key):
                    raise Rejected("Invalid parameter schema")
                if key not in intent.params:
                    if rule.required:
                        raise NeedsParameter(key)
                    continue
                v = intent.params[key]
                if (
                    not math.isfinite(v)
                    or not rule.minimum <= v <= rule.maximum
                    or (rule.integer and int(v) != v)
                ):
                    raise Rejected(f"Parameter {key} is outside its reviewed limits")
            # Detect unresolved parameter references, including indirect Jinja access.
            from .macros import inferred_parameters

            if set(inferred_parameters(macro.definition)) - set(macro.parameters):
                raise Rejected("Macro parameter schema needs review")
            if re.search(r"params\s*\[|params\s*\||params\s*\.\s*\w+\s*\(|rawparams", macro.definition):
                raise Rejected("Dynamic macro parameters require additional review; voice execution blocked")
            script = macro.name + "".join(
                f" {key}={numeric_text(value)}" for key, value in sorted(intent.params.items())
            )
            policy = macro.model_dump(mode="json")
            # Discovery can take time. Recheck printer readiness immediately after it.
            fresh = await client.snapshot()
            if fresh.ready != state.ready or fresh.state != state.state:
                raise Rejected("Printer state changed during macro validation")
            state = fresh
        binding = digest(
            {
                "intent": intent.model_dump(mode="json"),
                "printer": printer.model_dump(mode="json"),
                "state": {"ready": state.ready, "state": state.state},
                "policy": policy,
                "confirmations": self.store.get("confirmations", {}),
            }
        )
        return Validation(client, state, script, binding, motion_review)

    async def propose(self, intent: Intent, *, defer_confirmation=False, force_confirmation=False):
        initial = self.generation
        async with self.lock:
            if initial != self.generation:
                raise Rejected("The request changed while waiting for validation.")
            self.cancel()
            generation = self.generation
            validated = await self.validate(intent)
            client, state, _script, binding = validated
            if generation != self.generation:
                raise Rejected("Request was canceled or target changed during validation")
            if intent.action in READ_ONLY:
                if intent.action == Action.TEMPERATURES:
                    values = state.temperatures
                    if intent.query_subject:
                        key = "heater_bed" if intent.query_subject == "bed" else "extruder"
                        value = values.get(key)
                        return (
                            f"{intent.query_subject.capitalize()}: {value:.1f} degrees Celsius"
                            if value is not None
                            else f"{intent.query_subject.capitalize()} temperature unavailable"
                        )
                    return (
                        ". ".join(
                            f"{dict(extruder='Nozzle', heater_bed='Bed').get(k, k)}: {v:.1f} degrees Celsius"
                            for k, v in state.temperatures.items()
                        )
                        or "No temperatures available"
                    )
                if intent.action == Action.MACROS:
                    current, notices = discover(
                        await client.macro_config(), self.store.macros(intent.printer_id)
                    )
                    self.store.replace_macros(intent.printer_id, current)
                    return "Macros: " + ", ".join(current) + (". " + "; ".join(notices) if notices else "")
                progress = (
                    f"{state.progress:.0%} complete" if state.progress is not None else "Progress unavailable"
                )
                return f"{state.state}; {progress}"
            printer = next(p for p in self.store.printers() if p.id == intent.printer_id)
            warning = (
                " Check the bed and toolhead path are clear."
                if intent.action in (Action.HOME, Action.MACRO, Action.MOVE)
                else ""
            )
            provenance = "Model interpretation requires explicit review. " if force_confirmation else ""
            review = (
                f"{provenance}Confirm {validated.review or action_details(intent)} on {printer.name}?{warning} "
                f"Say exactly 'confirm' or choose Confirm within {self.confirmation_seconds} seconds after the prompt finishes."
            )
            if len(review) > 550:
                raise Rejected("Action details exceed the complete voice review limit; use printer controls")
            with self.state_lock:
                if generation != self.generation:
                    raise Rejected("Request was canceled during validation")
                self.pending = Pending(
                    secrets.token_urlsafe(24),
                    intent.model_dump_json(),
                    self.clock() + (180 if defer_confirmation else self.confirmation_seconds),
                    binding,
                    not defer_confirmation,
                    self.clock() + 180,
                )
                self.pending_trace = reaction_context.get() or timings.new()
                self.audit(
                    "proposed",trace=self.pending_trace,
                    intent=intent.action.value,
                    command=intent.macro,
                    printer_id=intent.printer_id,
                    parameters=intent.params,
                    confirmation_requested=self.confirmation_required(intent.action, force_confirmation),
                    outcome="proposed",
                )
            if not self.confirmation_required(intent.action, force_confirmation):
                with self.state_lock:
                    if self.pending is None or generation != self.generation:
                        raise Rejected("Request was canceled")
                    self.pending = replace(self.pending, ready=True)
                    token = self.pending.token
                return await self._confirm_locked(token)
            return review

    async def confirm(self, token):
        async with self.lock:
            return await self._confirm_locked(token)

    async def _confirm_locked(self, token):
        with self.state_lock:
            pending = self.pending
            pending_trace = self.pending_trace
            if pending is not None and pending.clarification_required:
                raise Rejected(
                    "Please restate the complete request before confirming; we're still clarifying it.",
                    code="confirmation_needs_clarification",
                )
            self.cancel(
                "confirmation_consumed"
            )  # Single use, including failure. Never retry a consequential request.
            generation = self.generation
        if (
            pending is None
            or not pending.ready
            or not secrets.compare_digest(token, pending.token)
            or self.clock() >= pending.expires
        ):
            if pending is not None:
                self.audit(
                    "confirmation_invalid",
                    trace=pending_trace,
                    outcome="expired" if self.clock() >= pending.expires else "rejected",
                )
            raise Rejected("Confirmation is missing or expired")
        self.audit("confirmed", trace=pending_trace, outcome="confirmed")
        intent = Intent.model_validate_json(pending.intent_json)
        self.validating = True
        try:
            return await self._dispatch(intent, pending, pending_trace, generation)
        finally:
            with self.state_lock:
                self.validating = self.dispatch_committed = False

    async def _dispatch(self, intent, pending, pending_trace, generation):
        try:
            client, _state, script, binding = await self.validate(intent)
        except Rejected as exc:
            self.audit("confirmation_rejected", trace=pending_trace, outcome="rejected", diagnostic=exc.code)
            raise
        if generation != self.generation or binding != pending.binding:
            raise Rejected("Printer state, macro, or permissions changed; request again")
        try:
            checked = self.clock()
            limited = intent.action in (Action.MOVE, Action.HEAT)
            record = self.limits.records.get(intent.printer_id)
            def commit():
                with self.state_lock:
                    if (generation != self.generation or self.clock() >= pending.expires
                            or self.store.get("selected") != intent.printer_id
                            or client.printer not in self.store.printers()
                            or self.clock() - checked > self.limits.maximum_read_seconds
                            or limited and (record is None or self.limits.records.get(intent.printer_id) is not record)):
                        raise Rejected("Request expired, was canceled, or printer state changed before transmission.")
                    self.dispatch_committed = True
                    self.last_dispatch_trace = reaction_context.get()
            await client.execute(intent, script, before_send=commit)
        except ConnectionFailure:
            if not self.dispatch_committed:
                raise Rejected("The printer connection could not be prepared. No command was sent.") from None
            self.audit(
                "dispatch_uncertain", trace=pending_trace, outcome="failed", diagnostic="outcome_unknown"
            )
            self.audit("dispatch_uncertain", outcome="failed", diagnostic="outcome_unknown")
            self.store.event(intent.printer_id, "outcome_unknown")
            return "Transmission outcome is unknown. I will not retry. Check the printer before requesting another action."
        self.store.event(intent.printer_id, "command_sent")
        self.audit("executed", trace=pending_trace, outcome="executed")
        self.audit("executed", outcome="executed", intent=intent.action.value, printer_id=intent.printer_id)
        if intent.action in (Action.PAUSE, Action.RESUME, Action.CANCEL):
            try:
                after = await client.snapshot()
                expected = {Action.PAUSE: "paused", Action.RESUME: "printing", Action.CANCEL: "cancelled"}
                if after.state == expected[intent.action]:
                    return f"Printer reports {after.state}."
            except ConnectionFailure:
                pass
        return "Request accepted; physical completion has not been verified."
