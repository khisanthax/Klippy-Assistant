"""Read-only active-configuration registry. Unknown values never grant motion authority."""
from __future__ import annotations

import asyncio
import copy
import math
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from .diagnostics import timings
from .domain import digest
from .moonraker import ConnectionFailure


class LimitsUnavailable(Exception):
    pass


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def vector(value):
    if not isinstance(value, list) or len(value) < 3 or any(number(x) is None for x in value):
        raise LimitsUnavailable("The printer's current coordinates are unavailable or invalid.")
    return tuple(value[:3])


def fields(value, names):
    value = value if isinstance(value, dict) else {}
    return {name: number(value.get(name)) for name in names}


@dataclass(frozen=True)
class LimitRecord:
    printer_id: str
    identity: str  # Memory only; never written to diagnostics or exported capability details.
    checked: float
    eventtime: float
    generation: int
    fingerprint: str
    capabilities: dict
    status: dict


REQUEST_FIELDS = {
    "configfile": "settings",
    "webhooks": "state",
    "print_stats": "state",
    "toolhead": "position homed_axes axis_minimum axis_maximum max_velocity max_accel extruder extra_axes cone_start_z",
    "gcode_move": "position gcode_position homing_origin absolute_coordinates absolute_extrude speed speed_factor extrude_factor axis_map",
    "motion_report": "live_position live_velocity live_extruder_velocity",
    "bed_mesh": "profile_name mesh_matrix",
}
HEATER_FIELDS = "min_temp max_temp min_extrude_temp max_extrude_only_distance max_extrude_only_velocity max_extrude_only_accel max_extrude_cross_section nozzle_diameter filament_diameter"
BLOCKED_FEATURES = {"bed_tilt", "skew_correction", "axis_twist_compensation", "z_thermal_adjust", "dual_carriage", "extra_carriage", "extra_axis"}
RESERVED = {"G0", "G1", "G20", "G21", "G90", "G91", "M104", "M140", "M220", "M400", "SAVE_GCODE_STATE", "RESTORE_GCODE_STATE"}


def discover(settings, objects):
    if not isinstance(settings, dict) or not settings:
        raise LimitsUnavailable("Active Klipper configuration is unavailable; no limits can be verified.")
    printer = settings.get("printer", {})
    if not isinstance(printer, dict):
        printer = {}
    kin = printer.get("kinematics")
    kin = kin if isinstance(kin, str) and len(kin) <= 40 else "unknown"
    axes = {}
    if kin in {"cartesian", "corexy"}:
        for axis in "xyz":
            axes[axis] = fields(settings.get("stepper_" + axis), ["position_min", "position_max"])
    heaters = {}
    for name in objects:
        if name == "heater_bed" or name == "extruder" or name.startswith("extruder") and name[8:].isdigit():
            if isinstance(settings.get(name), dict):
                heaters[name] = fields(settings[name], HEATER_FIELDS.split())
    features = sorted({name.split()[0] for name in settings if name.split()[0] in BLOCKED_FEATURES | {
        "bed_mesh", "input_shaper", "firmware_retraction", "safe_z_home", "homing_override", "quad_gantry_level", "z_tilt"}})
    shadowed = sorted({name.split(" ", 1)[1].upper() for name in settings
                       if name.lower().startswith("gcode_macro ") and name.split(" ", 1)[1].upper() in RESERVED})
    return {"kinematics": kin, "axes": axes, "heaters": heaters,
            "motion": fields(printer, ["max_velocity", "max_accel", "max_z_velocity", "max_z_accel"]),
            "native_geometry": fields(printer, ["delta_radius", "minimum_z_position", "print_radius", "minimum_cruise_ratio", "square_corner_velocity"]),
            "native_towers": {axis: fields(settings.get('stepper_' + axis), ['angle', 'arm_length', 'position_endstop'])
                              for axis in 'abc'} if kin == 'delta' else {},
            "features": features, "shadowed_commands": shadowed,
            "motion_scope": "single-axis XYZ" if kin in {"cartesian", "corexy"} else "unsupported kinematics; direct movement blocked"}


def validate_overrides(value, capabilities):
    """Reject expansions and unknown keys; this changes local permissions only."""
    if not isinstance(value, dict) or set(value) - {"axes", "motion", "heaters", "extrusion"}:
        raise LimitsUnavailable("Use only axes, motion, heaters and extrusion overrides.")
    for group, entries in value.items():
        if not isinstance(entries, dict):
            raise LimitsUnavailable("Each stricter-limit group must be an object.")
        if group == "motion":
            pairs = [(key, limit, capabilities["motion"].get(key), False) for key, limit in entries.items()]
        else:
            pairs = []
            for target, limits in entries.items():
                if target not in capabilities["axes" if group == "axes" else "heaters"]:
                    raise LimitsUnavailable("That axis or heater has no verified configured limits.")
                if not isinstance(limits, dict):
                    raise LimitsUnavailable("Each axis or heater override must contain named limits.")
                source = capabilities["axes" if group == "axes" else "heaters"].get(target, {})
                allowed = {"position_min", "position_max"} if group == "axes" else {"min_temp", "max_temp"} if group == "heaters" else set(HEATER_FIELDS.split()) - {"min_temp", "max_temp", "nozzle_diameter", "filament_diameter"}
                for key, limit in limits.items():
                    pairs.append((key, limit, source.get(key) if key in allowed else None, key in {"position_min", "min_temp", "min_extrude_temp"}))
        for key, limit, configured, minimum in pairs:
            if number(limit) is None or number(configured) is None or (limit < configured if minimum else limit > configured):
                raise LimitsUnavailable("Owner limits must be known and at least as strict as Klipper's active limits.")
            if key not in {"position_min", "position_max", "min_temp"} and limit <= 0:
                raise LimitsUnavailable("Speed, acceleration and extrusion limits must be positive.")
    merged = effective(capabilities, value)
    for axis in merged["axes"].values():
        if all(number(axis.get(k)) is not None for k in ("position_min", "position_max")) and axis["position_min"] >= axis["position_max"]:
            raise LimitsUnavailable("An axis minimum must be below its maximum.")
    for heater in merged["heaters"].values():
        if all(number(heater.get(k)) is not None for k in ("min_temp", "max_temp")) and heater["min_temp"] >= heater["max_temp"]:
            raise LimitsUnavailable("A heater minimum must be below its maximum.")
    return copy.deepcopy(value)


def effective(capabilities, overrides):
    result = copy.deepcopy(capabilities)
    for group, entries in overrides.items():
        if group == "motion":
            result["motion"].update(entries)
        elif group in {"axes", "heaters", "extrusion"}:
            for key, limits in entries.items():
                result["axes" if group == "axes" else "heaters"].setdefault(key, {}).update(limits)
    return result


class LimitsRegistry:
    def __init__(self, store, clients, *, clock=time.monotonic, maximum_read_seconds=2):
        self.store, self.clients, self.clock = store, clients, clock
        self.maximum_read_seconds = maximum_read_seconds
        self.records, self.generations, self.locks = {}, {}, {}
        self.watermarks, self.watchers = {}, {}
        self.on_invalidate = None

    def invalidate(self, printer_id):
        self.records.pop(printer_id, None)
        self.generations[printer_id] = self.generations.get(printer_id, 0) + 1
        if self.on_invalidate:
            self.on_invalidate(printer_id)

    def notification(self, printer_id, message):
        if not isinstance(message, dict):
            self.invalidate(printer_id)
            return
        method = message.get("method")
        params = message.get("params", [])
        if method in {"notify_klippy_ready", "notify_klippy_shutdown", "notify_klippy_disconnected"}:
            self.watermarks.pop(printer_id, None)
            self.invalidate(printer_id)
        elif method == "notify_status_update" and isinstance(params, list) and params and isinstance(params[0], dict):
            updates = params[0]
            record = self.records.get(printer_id)
            if "configfile" in updates or any(
                name in updates and (not isinstance(updates[name], dict) or any(
                    not record or record.status.get(name, {}).get(key) != value
                    for key, value in updates[name].items()))
                for name in ("webhooks", "print_stats", "toolhead", "gcode_move", "bed_mesh")
            ):
                self.invalidate(printer_id)

    def watch(self, printer, queries=None):
        """Lifecycle/status notifications can revoke permission, never grant it."""
        client = self.clients(printer)
        if getattr(client, 'transport', None) is not None or not hasattr(client, 'notifications'):
            return  # Injected simulations must never open a real websocket.
        old = self.watchers.get(printer.id)
        if old and old[0] == printer and not old[1].done():
            return
        if old:
            old[1].cancel()
        self.invalidate(printer.id)

        async def observe():
            while printer in self.store.printers() and printer.approved:
                self.invalidate(printer.id)
                try:
                    async for message in client.notifications(objects={
                        key: value.replace(' ', ',').split(',') for key, value in REQUEST_FIELDS.items()
                        if key in {'configfile', 'webhooks', 'print_stats', 'toolhead', 'gcode_move'}
                    }):
                        self.notification(printer.id, message)
                        if queries:
                            queries.notification(printer.id, message)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    pass  # Network details/credentials are deliberately not logged.
                finally:
                    self.invalidate(printer.id)
                await asyncio.sleep(3)
        self.watchers[printer.id] = (printer, asyncio.create_task(observe()))

    async def refresh(self, printer):
        with timings.span('limits_refresh'):
            return await self._refresh(printer)

    async def _refresh(self, printer):
        if not printer.approved:
            self.invalidate(printer.id)
            raise LimitsUnavailable("Select an approved printer before discovering limits.")
        lock = self.locks.setdefault(printer.id, asyncio.Lock())
        async with lock:
            generation = self.generations.get(printer.id, 0)
            began = self.clock()
            try:
                client = self.clients(printer)
                listing = await client.request("GET", "/printer/objects/list")
                objects = listing.get("objects") if isinstance(listing, dict) else None
                if not isinstance(objects, list) or len(objects) > 4096 or any(not isinstance(x, str) for x in objects):
                    raise LimitsUnavailable("Printer object discovery is invalid; limits are unknown.")
                required = {"configfile", "webhooks", "toolhead"}
                if not required <= set(objects):
                    raise LimitsUnavailable("This printer does not expose the objects needed to verify active limits.")
                selected = {k: v.replace(" ", ",") for k, v in REQUEST_FIELDS.items() if k in objects}
                for name in objects:
                    if name in {"extruder", "heater_bed"} or name.startswith("extruder") and name[8:].isdigit():
                        selected[name] = "temperature,can_extrude"
                raw = await client.request("GET", "/printer/objects/query?" + urlencode(selected))
                status = raw.get("status") if isinstance(raw, dict) else None
                eventtime = number(raw.get("eventtime")) if isinstance(raw, dict) else None
                if not isinstance(status, dict) or eventtime is None or eventtime < 0:
                    raise LimitsUnavailable("The active limits snapshot has no valid freshness timestamp.")
                if any(not isinstance(value, dict) for key, value in status.items() if key in REQUEST_FIELDS or key in {'extruder', 'heater_bed'}):
                    raise LimitsUnavailable("The active printer state contains malformed objects.")
                if status.get("webhooks", {}).get("state") != "ready":
                    raise LimitsUnavailable("Klipper is not ready; cached limits cannot authorize an action.")
                old = self.records.get(printer.id)
                previous_time = self.watermarks.get(printer.id)
                if previous_time and previous_time[0] == printer.url and eventtime <= previous_time[1]:
                    raise LimitsUnavailable("The printer returned stale status; request fresh limits and position again.")
                settings = status.get("configfile", {}).get("settings")
                caps = discover(settings, objects)
                fingerprint = digest(settings)
                if self.clock() - began > self.maximum_read_seconds:
                    raise LimitsUnavailable("The limits/position read took too long to be considered current.")
                current = next((p for p in self.store.printers() if p.id == printer.id), None)
                if current != printer or generation != self.generations.get(printer.id, 0):
                    raise LimitsUnavailable("Printer enrollment or configuration changed during discovery.")
                if old and (old.identity != printer.url or old.fingerprint != fingerprint):
                    self.invalidate(printer.id)
                clean_status = {k: v for k, v in status.items() if k != "configfile"}
                record = LimitRecord(printer.id, printer.url, self.clock(), eventtime,
                                     self.generations.get(printer.id, 0), fingerprint, caps, copy.deepcopy(clean_status))
                self.records[printer.id] = record
                self.watermarks[printer.id] = (printer.url, eventtime)
                return record
            except (ConnectionFailure, LimitsUnavailable, ValueError, TypeError, KeyError, AttributeError) as exc:
                self.invalidate(printer.id)
                if isinstance(exc, LimitsUnavailable):
                    raise
                raise LimitsUnavailable("Active printer limits could not be verified. No action was sent.") from None

    def save_review(self, printer, record, overrides, caps=None):
        if self.records.get(printer.id) is not record or record.identity != printer.url:
            raise LimitsUnavailable("Printer or configuration changed. Refresh limits before saving.")
        overrides = validate_overrides(overrides, record.capabilities)
        if caps is not None:
            if not isinstance(caps, dict):
                raise LimitsUnavailable("Enter heater caps as a JSON object.")
            for key, cap in caps.items():
                heater = {'0': 'extruder', '1': 'heater_bed'}.get(key)
                maximum = record.capabilities['heaters'].get(heater, {}).get('max_temp')
                if number(maximum) is None or number(cap) is None or not 0 <= cap <= maximum:
                    raise LimitsUnavailable("Each heater cap must be within the discovered heater limits.")
        self.store.save_reviewed_limits(printer, overrides, caps)
        self.invalidate(printer.id)

    def effective(self, record):
        overrides = self.store.get("printer_limit_overrides", {}).get(record.printer_id, {})
        validate_overrides(overrides, record.capabilities)
        return effective(record.capabilities, overrides)

    def describe(self, printer_id):
        record = self.records.get(printer_id)
        enrolled = next((p for p in self.store.printers() if p.id == printer_id), None)
        if enrolled is None or not enrolled.approved or record and record.identity != enrolled.url:
            record = None
        if record is None:
            return {"status": "unknown; refresh approved printer limits", "motion_authorized": False}
        tool = record.status.get('toolhead', {})
        position = tool.get('position')
        position = position[:3] if isinstance(position, list) and all(number(x) is not None for x in position) else None
        homed = tool.get('homed_axes')
        return {"age_seconds": round(max(0, self.clock() - record.checked), 2),
                "source": "Klipper active configfile.settings; runtime values require fresh execution-time validation",
                "configuration_fingerprint": record.fingerprint,
                "capabilities": copy.deepcopy(record.capabilities),
                "last_observed": {"commanded_machine_xyz": position,
                                  "homed_axes": homed if isinstance(homed, str) and homed in {'', 'x', 'y', 'z', 'xy', 'xz', 'yz', 'xyz'} else None,
                                  "runtime_motion": fields(tool, ['max_velocity', 'max_accel'])},
                "owner_overrides": copy.deepcopy(self.store.get("printer_limit_overrides", {}).get(printer_id, {})),
                "legacy_heater_caps": copy.deepcopy(self.store.get("heater_limits", {}).get(printer_id, {})),
                "motion_authorized": False,
                "warning": "Configured limits do not establish physical clearance or encoder-measured position."}
