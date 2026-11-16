"""Capability-aware read authority. Deliberately has no SafetyEngine/execute reference."""
from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlencode

from .diagnostics import timings
from .domain import StrictModel
from .moonraker import ConnectionFailure
from .query_catalog import CATALOG, object_fields
from .query_format import mapping, numeric, render
from .query_semantics import position_hint

# Reviewed individually against the upstream API. In particular GET is not an
# authorization rule: device power actions and remote commands are NOT admitted.
READ_ROUTES = {
    "/server/info": set(), "/printer/info": set(), "/printer/objects/list": set(),
    "/printer/objects/query": None,
    "/server/history/list": {"limit", "order"}, "/server/history/totals": set(),
    "/server/files/metadata": {"filename"}, "/server/files/list": {"root"},
    "/machine/system_info": set(), "/machine/proc_stats": set(),
    "/machine/device_power/devices": set(), "/server/job_queue/status": set(),
    "/server/webcams/list": set(),
}
MISSING = object()


class QueryRequest(StrictModel):
    query_id: str
    subject: str | None = None


class QueryUnavailable(Exception):
    pass


@dataclass
class Capabilities:
    checked: float
    objects: frozenset[str]
    components: frozenset[str]
    fields: dict[str, frozenset[str]] = field(default_factory=dict)
    identity: str = ""


async def read(client, endpoint, params=None):
    params = params or {}
    if not isinstance(endpoint, str) or endpoint not in READ_ROUTES or not isinstance(params, dict):
        raise QueryUnavailable("Endpoint is not in the reviewed read-only catalog")
    allowed = READ_ROUTES[endpoint]
    if allowed is not None and set(params) - allowed:
        raise QueryUnavailable("Unreviewed read parameters")
    if endpoint == "/printer/objects/query":
        # Independently restrict object/field selection, including callers outside QueryService.
        valid = {}
        for spec in CATALOG.values():
            for name, fields in object_fields(spec, params).items():
                valid.setdefault(name, set()).update(fields)
        if not params or len(params) > 128 or any(
            not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_ ]{1,100}", name)
            or not isinstance(fields, str) or not set(fields.split(",")) <= valid.get(name, set())
            for name, fields in params.items()
        ):
            raise QueryUnavailable("Object/fields outside the reviewed catalog")
    if endpoint == "/server/history/list" and (
        params.get("limit") not in (5, 50) or params.get("order") != "desc"
    ):
        raise QueryUnavailable("History reads must be bounded and newest first")
    if endpoint == "/server/files/list" and params != {"root": "gcodes"}:
        raise QueryUnavailable("Only G-code file listings are admitted")
    if endpoint == "/server/files/metadata":
        name = params.get("filename")
        if (not isinstance(name, str) or not name or len(name) > 512 or name.startswith(("/", "\\"))
                or any(p == ".." for p in name.replace("\\", "/").split("/"))
                or ":" in name or "\\" in name or any(ord(c) < 32 for c in name)):
            raise QueryUnavailable("Invalid G-code metadata filename")
    path = endpoint + ("?" + urlencode(params) if params else "")
    result = await client.request("GET", path)
    if endpoint != "/server/files/list" and not isinstance(result, dict):
        raise ConnectionFailure("Invalid read-only response")
    return result


class QueryService:
    def __init__(self, store, clients, clock=time.monotonic, fresh_seconds=2, capability_seconds=60):
        self.store, self.clients, self.clock = store, clients, clock
        self.fresh_seconds, self.capability_seconds = fresh_seconds, capability_seconds
        self.capabilities = {}
        self.cache = {}  # Per printer, endpoint/field; never persisted or supplied to the LLM.
        self.events = {}
        self.locks = {}
        self.generations = {}
        self.invalidated_at = {}

    def invalidate(self, printer_id):
        self.generations[printer_id] = self.generations.get(printer_id, 0) + 1
        self.invalidated_at[printer_id] = self.clock()
        self.capabilities.pop(printer_id, None)
        self.events.pop(printer_id, None)
        for key in list(self.cache):
            if key[0] == printer_id:
                self.cache.pop(key, None)

    def printer(self, printer_id):
        printer = next((p for p in self.store.printers() if p.id == printer_id and p.approved), None)
        if printer is None:
            raise QueryUnavailable("Select an enrolled, approved printer for information queries")
        return printer

    def observe(self, printer_id, value, received=None, *, delta=False, identity=None):
        """Ingest GET or subscription status; a delta refreshes only fields actually sent."""
        if identity is not None:
            current = next((p for p in self.store.printers() if p.id == printer_id), None)
            if current is None or current.url != identity:
                return
        cap = self.capabilities.get(printer_id)
        if received is not None and received < max(self.invalidated_at.get(printer_id, 0), cap.checked if cap else 0):
            return  # Snapshot started before a restart/configuration/endpoint invalidation.
        status = mapping(mapping(value).get("status"))
        event = value.get("eventtime") if isinstance(value, dict) else None
        if event is not None and numeric(event, 0) is None:
            raise ConnectionFailure("Invalid status timestamp")
        prior = self.events.get(printer_id)
        if event is not None and prior is not None and event < prior:
            self.invalidate(printer_id)
            raise ConnectionFailure("Printer status clock changed; capabilities must be refreshed")
        if event is not None:
            self.events[printer_id] = event
        now = self.clock() if received is None else received
        allowed = {}
        for spec in CATALOG.values():
            for name, keys in object_fields(spec, status).items():
                allowed.setdefault(name, set()).update(keys)
        for name, fields in status.items():
            if isinstance(fields, dict):
                for key, item in fields.items():
                    if key not in allowed.get(name, set()):
                        continue
                    # Replacement at the attribute level; never deep-merge an old nested layer value.
                    self.cache[(printer_id, name, key)] = (item, now)

    def notification(self, printer_id, message):
        """Accept already-authenticated Moonraker notifications, never remote instructions."""
        method = message.get("method")
        if method in {"notify_klippy_ready", "notify_klippy_shutdown", "notify_klippy_disconnected"}:
            self.invalidate(printer_id)
        elif method == "notify_status_update":
            params = message.get("params")
            if not isinstance(params, list) or not params or not isinstance(params[0], dict):
                raise ConnectionFailure("Invalid subscription status")
            if "configfile" in params[0]:
                self.invalidate(printer_id)
                return
            self.observe(printer_id, {"status": params[0], "eventtime": params[1] if len(params) > 1 else None}, delta=True)

    async def discover(self, printer, *, force=False):
        identity = printer.url  # In memory only; changed endpoint never reuses another server's data.
        cap = self.capabilities.get(printer.id)
        if cap and cap.identity != identity:
            self.invalidate(printer.id)
            cap = None
        if cap and not force and self.clock() - cap.checked < self.capability_seconds:
            return cap
        lock = self.locks.setdefault(printer.id, asyncio.Lock())
        async with lock:
            cap = self.capabilities.get(printer.id)
            if cap and not force and cap.identity == identity and self.clock() - cap.checked < self.capability_seconds:
                return cap
            client = self.clients(printer)
            started = self.clock()
            server = await read(client, "/server/info")
            raw_components = server.get("components")
            if not isinstance(raw_components, list) or any(not isinstance(c, str) for c in raw_components):
                raise ConnectionFailure("Invalid component discovery")
            objects = frozenset()
            if server.get("klippy_connected") is True and server.get("klippy_state") == "ready":
                listing = await read(client, "/printer/objects/list")
                names = listing.get("objects")
                if not isinstance(names, list) or any(not isinstance(n, str) for n in names) or len(names) > 4096:
                    raise ConnectionFailure("Invalid object discovery")
                objects = frozenset(n for n in names if re.fullmatch(r"[A-Za-z0-9_ ]{1,100}", n))
            self.invalidate(printer.id)
            cap = Capabilities(started, objects, frozenset(raw_components), identity=identity)
            self.capabilities[printer.id] = cap
            self.cache[(printer.id, "/server/info", "", "endpoint")] = (server, started)
            fields = {}
            for spec in CATALOG.values():
                for name, keys in object_fields(spec, objects).items():
                    fields.setdefault(name, set()).update(keys)
            if fields:
                await self._objects(printer, fields)
            cap.fields = {name: frozenset(key[2] for key in self.cache if len(key) == 3 and key[:2] == (printer.id, name)
                                        and self.cache[key][0] is not MISSING)
                          for name in objects}
            return cap

    async def _objects(self, printer, fields):
        if len(fields) > 64:
            items = list(fields.items())
            combined = {}
            for start in range(0, len(items), 64):
                result = await self._objects(printer, dict(items[start:start + 64]))
                combined.update(result["status"])
            return {"status": combined}
        started = self.clock()
        generation = self.generations.get(printer.id, 0)
        result = await read(self.clients(printer), "/printer/objects/query",
                            {name: ",".join(sorted(keys)) for name, keys in fields.items()})
        current = next((p for p in self.store.printers() if p.id == printer.id), None)
        if current is None or current.url != printer.url or generation != self.generations.get(printer.id, 0):
            raise ConnectionFailure("Printer discovery changed during the read")
        if not isinstance(result.get("status"), dict):
            raise ConnectionFailure("Invalid object query response")
        # A complete requested-field read supersedes absent old attributes too.
        for name, keys in fields.items():
            for key in keys:
                self.cache[(printer.id, name, key)] = (MISSING, started)
        self.observe(printer.id, result, started, identity=printer.url)
        cap = self.capabilities.get(printer.id)
        if cap:
            for name, keys in fields.items():
                actual = set(mapping(result["status"].get(name))) & set(keys)
                cap.fields[name] = frozenset((set(cap.fields.get(name, ())) - set(keys)) | actual)
        return result

    async def refresh(self, printer, *, force=False):
        try:
            await self.discover(printer, force=force)
        except (ConnectionFailure, QueryUnavailable):
            self.invalidate(printer.id)

    def support(self, printer_id, spec):
        cap = self.capabilities.get(printer_id)
        if cap is None or self.clock() - cap.checked >= self.capability_seconds:
            return "not verified"
        if spec.component and spec.component not in cap.components:
            return f"unsupported: {spec.component} component absent"
        if spec.endpoint == "/printer/objects/query":
            fields = object_fields(spec, cap.objects)
            if not fields:
                return "unsupported: objects absent"
            if not any(set(keys) & cap.fields.get(name, set()) for name, keys in fields.items()):
                return "unavailable: fields not reported"
        return "available (verified capabilities; individual fields may be unavailable)"

    def _status(self, printer_id, fields):
        status, times = {}, []
        for name, keys in fields.items():
            for key in keys:
                record = self.cache.get((printer_id, name, key))
                if record:
                    if record[0] is not MISSING:
                        status.setdefault(name, {})[key] = record[0]
                    times.append(record[1])
        return status, times

    async def answer(self, printer_id, request):
        from .presentation import Response, present
        if not isinstance(request, QueryRequest) or request.query_id not in CATALOG or request.subject not in {None, "bed", "nozzle", "sensors", "x", "y", "z"}:
            raise QueryUnavailable("Unknown or invalid information query")
        if request.subject in {"x", "y", "z"} and request.query_id not in {"position", "gcode_position"}:
            raise QueryUnavailable("Axis projection requires a position query")
        printer = self.printer(printer_id)
        spec = CATALOG[request.query_id]
        with timings.span("query_response"):
            cap = await self.discover(printer)
            if spec.component and spec.component not in cap.components:
                return Response(f"{printer.name}: {spec.description} unsupported; {spec.component} component not reported.",
                                f"{printer.name} doesn't report that information.")
            fields = object_fields(spec, cap.objects)
            status, times = self._status(printer_id, fields)
            stale = False
            if spec.endpoint == "/printer/objects/query":
                if not fields:
                    if spec.id in {"errors", "status"}:
                        acquired = self.clock()
                        server = await read(self.clients(printer), "/server/info")
                        result = (await read(self.clients(printer), "/printer/info")
                                  if server.get("klippy_connected") is True else server)
                        identifier = "printer_info" if server.get("klippy_connected") is True else "server"
                        if self.printer(printer_id) != printer:
                            raise QueryUnavailable("Printer enrollment changed")
                        age = self.clock() - acquired
                        label = f"STALE observation ({age:.1f} seconds old): " if age > self.fresh_seconds else ""
                        return f"{printer.name}: {label}{render(identifier, {}, result)}"[:550]
                    return Response(f"{printer.name}: {spec.description} unavailable; required objects not reported.",
                                    f"{printer.name} doesn't report that information.")
                # Missing fields are probed again instead of being assumed supported or permanently absent.
                complete = all((printer_id, name, key) in self.cache for name, keys in fields.items() for key in keys)
                if not complete or not times or self.clock() - min(times) > self.fresh_seconds:
                    try:
                        await self._objects(printer, fields)
                        status, times = self._status(printer_id, fields)
                    except ConnectionFailure:
                        if not status:
                            raise QueryUnavailable("Current printer information unavailable") from None
                        stale = True
                result = {}
            else:
                params = {}
                if spec.id in {"metadata", "remaining"}:
                    job_fields = {"print_stats": ("filename", "state", "print_duration")}
                    if "print_stats" not in cap.objects:
                        return f"{printer.name}: Current file information unavailable; print_stats is absent."
                    await self._objects(printer, job_fields)
                    status, times = self._status(printer_id, job_fields)
                    stats = mapping(status.get("print_stats"))
                    if spec.id == "remaining" and stats.get("state") not in {"printing", "paused"}:
                        return f"{printer.name}: No active print for a remaining-time estimate."
                    filename = stats.get("filename")
                    if not isinstance(filename, str) or not filename:
                        return f"{printer.name}: No reported job filename; metadata unavailable."
                    params = {"filename": filename}
                elif spec.id in {"history", "last_failure"}:
                    params = {"limit": 50 if spec.id == "last_failure" else 5, "order": "desc"}
                elif spec.id == "files":
                    params = {"root": "gcodes"}
                cache_key = (printer_id, spec.endpoint, urlencode(params), "endpoint")
                cached = self.cache.get(cache_key)
                if cached and self.clock() - cached[1] <= self.fresh_seconds:
                    result, acquired = cached
                else:
                    acquired = self.clock()
                    generation = self.generations.get(printer_id, 0)
                    try:
                        result = await read(self.clients(printer), spec.endpoint, params)
                        if self.printer(printer_id) != printer or generation != self.generations.get(printer_id, 0):
                            raise QueryUnavailable("Printer discovery changed during the read")
                        self.cache[cache_key] = result, acquired
                    except ConnectionFailure:
                        if cached is None:
                            raise QueryUnavailable("Requested information unavailable or unauthorized") from None
                        result, acquired = cached
                        stale = True
                times.append(acquired)
            if self.printer(printer_id) != printer:  # Revocation/endpoint edits during reads prevent delivery.
                raise QueryUnavailable("Printer enrollment changed; request information again")
            age = max(0, self.clock() - min(times)) if times else 0
            stale = stale or age > self.fresh_seconds
            label = f"STALE cached observation ({age:.1f} seconds old); cannot verify current: " if stale else ""
            with timings.span("query_format"):
                answer = render(spec.id, status, result, request.subject)
            # Fits the existing spoken response budget; manager provides full spec detail separately.
            response = f"{printer.name}: {label}{answer}"
            detail = response if len(response) <= 550 else response[:520] + "; further results omitted."
            presented = present(printer.name, spec.id, status, detail, request.subject,
                                self.store.get("response_style", "brief"), stale)
            presented.verified = True
            presented.capabilities = ['read_only:'+spec.id]
            presented.stale = stale
            presented.fresh_until = min(times)+self.fresh_seconds if times else None
            presented.explanation_fact = detail.replace('_',' ')
            return presented


def normalize(text):
    text = text.lower().replace("’", "'")
    for old, new in (("what's", "what is"), ("where's", "where is"), ("how's", "how is"),
                     ("isn't", "is not"), ("aren't", "are not"), ("it's", "it is")):
        text = text.replace(old, new)
    return " ".join(re.sub(r"[^a-z0-9_ ]", " ", text).split())


def information_request(text):
    text = normalize(text)
    return bool(re.match(r"(?:what|where|when|why|how|is|are|was|were|has|have|does|did|which)\b", text)
                or re.match(r"(?:tell me|show|report|read|list|check|get|find out|give me|let me know)\b", text)
                or re.search(r"\b(?:homed|homing status)\b", text)
                or text in {"homed", "homing status", "status", "printer status", "temperatures", "temperature",
                            "position", "progress", "history", "fans", "layers", "speed", "acceleration", "mmu status",
                            "and", "and the", "and it", "and that printer"}
                or bool(re.fullmatch(r"(?:and|what about|how about)(?: the)? (?:bed|nozzle|extruder|hotend)", text))
                or bool(re.fullmatch(r"(?:[xyz]|zed|zee)(?: axis)? (?:height|position|coordinate)", text))
                or bool(re.fullmatch(r"(?:and|what about|how about)(?: the)? (?:[xyz]|zed|zee)(?: axis)?", text))
                or text.startswith("can it extrude"))


def match_query(text, previous=None):
    text = normalize(text)
    if not information_request(text):
        return None
    # Mixed requests cannot accidentally fall through to actuation or silently drop an action.
    if re.search(r"\b(?:and|then|also) (?:please )?(?:home|heat|move|set|start|pause|resume|cancel|run|stop|turn|save|restart|reboot)\b", text):
        raise QueryUnavailable("Ask information and printer actions separately; no action sent")
    if re.fullmatch(r"(?:(?:what|how) about|and)(?: the| it| that printer)?", text):
        return previous
    try:
        hint = position_hint(text, previous)
    except ValueError as exc:
        raise QueryUnavailable(str(exc)) from None
    if hint:
        return QueryRequest(query_id=hint[0], subject=hint[1])
    subject = "bed" if re.search(r"\bbed\b", text) else "nozzle" if re.search(r"\b(?:nozzle|extruder|hotend|hot end)\b", text) else None
    if subject is None and re.search(r"\b(?:sensors?|chamber|enclosure)\b", text):
        subject = "sensors"
    if previous and subject and re.fullmatch(r"(?:and|what about|how about)(?: the)? (?:bed|nozzle|extruder|hotend)", text):
        if previous.query_id in {"temperatures", "targets", "heater_power"}:
            return QueryRequest(query_id=previous.query_id, subject=subject)
        raise QueryUnavailable("Would you like the temperature or target for that heater?")
    patterns = (
        ("homing", r"\b(?:homed|homing|axes home|axis home)\b"),
        ("host_stats", r"\b(?:cpu (?:temperature|load|usage)|host.*(?:hot|temperature|load|throttl)|throttl|uptime)"),
        ("printer_info", r"\bklipper (?:version|firmware)\b"),
        ("server", r"\bmoonraker\b|\bserver (?:info|version|component)"),
        ("last_failure", r"\b(?:last|previous|recent).*\b(?:fail|failed|failure|unsuccessful)\b"),
        ("totals", r"\b(?:how many prints|total prints|job totals|total filament|total print time)\b"),
        ("history", r"\b(?:history|last print|previous print|recent jobs)\b"),
        ("queue", r"\b(?:queue|queued)\b"),
        ("files", r"\bfiles\b"),
        ("remaining", r"\b(?:time.*left|time.*remaining|when.*finish|remaining time)\b"),
        ("metadata", r"\b(?:slicer|sliced|material|metadata|layer height|file.*filament)\b"),
        ("targets", r"\btarget\b|\b(?:bed|nozzle|extruder).*\bset to\b"),
        ("heater_power", r"\bheater.*\bpower\b"),
        ("temperatures", r"\b(?:temperature|temperatures|hot|cold|degrees)\b"),
        ("gcode_position", r"\b(?:gcode coordinates|g code coordinates|gcode position|g code position|origin|offset)\b"),
        ("limits", r"\b(?:acceleration|accel|velocity limit|velocity limits|corner velocity|cruise ratio)\b"),
        ("pressure_advance", r"\bpressure advance\b"),
        ("retraction", r"\b(?:retraction|retract length|retract speed)\b"),
        ("extrusion", r"\b(?:can.*extrude|extruder.*active|active extruder)\b"),
        ("motion", r"\b(?:moving|in motion|live velocity)\b"),
        ("speed", r"\b(?:speed|feedrate|flow override|flow rate)\b"),
        ("position", r"\b(?:position|coordinates|where.*(?:nozzle|toolhead|head))\b"),
        ("layers", r"\blayers?\b"),
        ("duration", r"\b(?:how long|elapsed|duration)\b"),
        ("filament_sensors", r"\b(?:runout|filament.*(?:detect|present|sensor)|filament loaded)"),
        ("filament", r"\bfilament.*\b(?:used|use|usage|consumed)\b"),
        ("bed_mesh", r"\b(?:mesh|mesh profile)\b"),
        ("leveling", r"\b(?:gantry|z tilt|leveled|levelled)\b"),
        ("endstops", r"\bendstops?\b"),
        ("probe", r"\bprobe\b"),
        ("mmu", r"\b(?:mmu|happy hare|filament gate|selected tool|selected gate)\b"),
        ("mcu", r"\b(?:mcu|controller firmware)\b"),
        ("fans", r"\bfans?\b"),
        ("power_devices", r"\bpower devices?\b"),
        ("webcams", r"\b(?:webcams?|cameras?)\b"),
        ("host", r"\b(?:host|system info|cpu|memory|ram|operating system)\b"),
        ("configuration", r"\b(?:configuration|config|build volume|build height|axis limits|axis bounds|axis travel|(?:maximum|minimum|max|min) (?:[xyz] (?:axis )?)?(?:height|travel|position))\b"),
        ("errors", r"\b(?:error|errors|fault|shutdown|wrong|problem)\b"),
        ("progress", r"\b(?:progress|percent|percentage|far along|done|complete)\b"),
        ("job", r"\b(?:printing|paused|current job|current print|current file|filename)\b"),
        ("status", r"\b(?:status|ready|connected|happening)\b"),
    )
    # Fan speed and host temperature must not become generic speed/temperature queries.
    if re.search(r"\b(?:host|cpu)\b", text) and re.search(r"\b(?:hot|temperature|load|usage|throttling|uptime)\b", text):
        identifier = "host_stats"
    elif re.search(r"\bfans?\b", text):
        identifier = "fans"
    else:
        identifier = next((identifier for identifier, pattern in patterns if re.search(pattern, text)), None)
    if identifier is None:
        return None
    if subject is None and previous and identifier in {"targets", "temperatures", "heater_power"}:
        subject = previous.subject if previous.query_id in {"targets", "temperatures", "heater_power"} else None
    return QueryRequest(query_id=identifier, subject=subject)
