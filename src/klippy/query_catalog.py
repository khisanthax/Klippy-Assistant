"""Reviewed data queries, not an HTTP/G-code command generator.

Sources and exclusions: docs/MOONRAKER_QUERIES.md. No remote configuration,
status strings or model output can extend this inventory at runtime.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class QuerySpec:
    id: str
    description: str
    objects: tuple[tuple[str, tuple[str, ...]], ...]
    examples: tuple[str, ...]
    endpoint: str = "/printer/objects/query"
    component: str | None = None
    response_fields: tuple[str, ...] = ()
    classification: str = "read-only information; no printer actuation"
    missing: str = "Report unavailable/unsupported; never invent values or run a command"
    validation: str = "Typed finite values, bounded strings/lists; units and provenance retained"
    fallback_endpoints: tuple[str, ...] = ()


def object_query(identifier, description, objects, *examples):
    return QuerySpec(identifier, description,
                     tuple((name, tuple(fields.split())) for name, fields in objects.items()), tuple(examples),
                     response_fields=tuple(f"{name}.{field}" for name, fields in objects.items()
                                           for field in fields.split()))


def endpoint_query(identifier, description, endpoint, component, fields, *examples):
    return QuerySpec(identifier, description, (), tuple(examples), endpoint, component, tuple(fields.split()))


CATALOG = {q.id: q for q in (
    object_query("homing", "Whether Cartesian axes have been homed/zeroed and have an established coordinate reference", {"toolhead": "homed_axes"},
                 "Is my printer homed?", "Have all axes been homed?", "Which axes are not homed?"),
    object_query("temperatures", "Measured heater and sensor temperatures in Celsius",
                 {"extruder": "temperature target", "heater_bed": "temperature target"},
                 "How hot is the bed?", "What is the nozzle temperature?", "Read temperatures"),
    object_query("targets", "Requested heater setpoints, not a request to heat",
                 {"extruder": "target", "heater_bed": "target"},
                 "What's the target temperature?", "What is the bed set to?"),
    object_query("heater_power", "Current heater output fraction as percent",
                 {"extruder": "power", "heater_bed": "power"}, "How much heater power is being used?"),
    object_query("position", "Last commanded machine position, not measured physical position",
                 {"toolhead": "position homed_axes"}, "Where's the nozzle?", "What is the toolhead position?"),
    object_query("gcode_position", "G-code coordinates and origin offsets",
                 {"gcode_move": "gcode_position homing_origin"}, "What are the G-code coordinates?", "What is my Z offset?"),
    object_query("motion", "Requested interpolated motion, not encoder-measured motion",
                 {"motion_report": "live_position live_velocity live_extruder_velocity"},
                 "Is the printer moving?", "How fast is the toolhead moving?"),
    object_query("limits", "Runtime velocity, acceleration and cornering limits",
                 {"toolhead": "max_velocity max_accel square_corner_velocity minimum_cruise_ratio"},
                 "What's the acceleration?", "What are the velocity limits?"),
    object_query("speed", "Last commanded feedrate and speed/flow overrides",
                 {"gcode_move": "speed speed_factor extrude_factor"}, "What's the speed?", "What is the flow override?"),
    object_query("progress", "Print progress fraction and state",
                 {"virtual_sdcard": "progress", "display_status": "progress", "print_stats": "state"},
                 "How far along is my print?", "What percent is done?"),
    object_query("job", "Current or most recently reported filename and print state",
                 {"print_stats": "filename state message", "pause_resume": "is_paused"},
                 "What is printing?", "What is the current job?", "Is it paused?"),
    object_query("layers", "Slicer-reported layer counters; may not be supplied",
                 {"print_stats": "info state"}, "What layer am I on?", "How many layers?"),
    object_query("duration", "Active print time and total elapsed job duration",
                 {"print_stats": "print_duration total_duration state"}, "How long has it been printing?"),
    object_query("filament", "Extruded filament length in millimetres for the reported job",
                 {"print_stats": "filament_used state"}, "How much filament have I used?"),
    object_query("fans", "Available fan duty cycles and optional tachometer RPM",
                 {"fan": "speed rpm"}, "Are the fans running?", "What's the fan speed?"),
    object_query("filament_sensors", "Filament presence and sensor enable state", {},
                 "Is filament detected?", "Are the runout sensors enabled?"),
    object_query("errors", "Reported Klipper/print error messages; no diagnosis inferred",
                 {"webhooks": "state state_message", "print_stats": "state message"}, "Does the printer have an error?"),
    object_query("status", "Klipper readiness and reported print state",
                 {"webhooks": "state state_message", "print_stats": "state"}, "Is the printer ready?", "Printer status"),
    object_query("configuration", "Configured axis bounds and pending-save/warning status",
                 {"toolhead": "axis_minimum axis_maximum", "configfile": "save_config_pending warnings"},
                 "What are the printer configuration warnings?", "What is the build volume?"),
    object_query("bed_mesh", "Already-loaded mesh profile; never probe or calibrate",
                 {"bed_mesh": "profile_name mesh_min mesh_max"}, "Which bed mesh is loaded?"),
    object_query("leveling", "Previously reported gantry/Z tilt application status",
                 {"quad_gantry_level": "applied", "z_tilt": "applied"}, "Is the gantry leveled?"),
    object_query("endstops", "Last recorded endstop result, not a fresh hardware sample",
                 {"query_endstops": "last_query"}, "What are the endstop states?"),
    object_query("probe", "Last recorded probe result, not a fresh probe action",
                 {"probe": "name last_query"}, "Is the probe triggered?"),
    object_query("pressure_advance", "Current pressure advance and smoothing time",
                 {"extruder": "pressure_advance smooth_time"}, "What's the pressure advance?"),
    object_query("retraction", "Current firmware retraction settings",
                 {"firmware_retraction": "retract_length retract_speed unretract_extra_length unretract_speed"},
                 "What is the retraction length?"),
    object_query("extrusion", "Extrusion eligibility and active extruder",
                 {"extruder": "can_extrude", "toolhead": "extruder"}, "Can it extrude?", "Which extruder is active?"),
    object_query("mmu", "Exposed Happy Hare state/tool/gate; notification-only", {"mmu": "print_state print_job_state tool gate is_locked"},
                 "What's the MMU state?", "Which filament gate is selected?"),
    object_query("mcu", "Controller firmware and communication statistics", {"mcu": "mcu_version last_stats"},
                 "What firmware is on the MCU?"),
    endpoint_query("server", "Moonraker version, Klipper connection and failed components", "/server/info", None,
                   "moonraker_version klippy_connected klippy_state failed_components warnings", "What Moonraker version is running?"),
    endpoint_query("printer_info", "Klipper version/readiness even during startup or error", "/printer/info", None,
                   "state state_message software_version", "What Klipper version is running?"),
    endpoint_query("history", "Most recent five recorded jobs", "/server/history/list", "history", "jobs count",
                   "Show print history", "What was my last print?"),
    endpoint_query("last_failure", "Last recorded unsuccessful job and its recorded status, not an invented cause",
                   "/server/history/list", "history", "jobs count", "Why did my last print fail?"),
    endpoint_query("totals", "Recorded job totals since history totals were last reset", "/server/history/totals", "history",
                   "job_totals", "How many prints have I done?"),
    endpoint_query("metadata", "Current file's existing slicer metadata", "/server/files/metadata", "file_manager",
                   "filename slicer layer_height filament_type estimated_time filament_total", "What material is this file sliced for?"),
    endpoint_query("remaining", "Slicer-estimated total less active time; estimate only", "/server/files/metadata", "file_manager",
                   "estimated_time", "How much time is left?", "When will the print finish?"),
    endpoint_query("files", "Up to five G-code file names; no reads of arbitrary host paths", "/server/files/list", "file_manager",
                   "path size modified", "What files are available?"),
    endpoint_query("host", "Host platform/CPU/memory summary", "/machine/system_info", "machine", "system_info",
                   "What host is the printer running on?"),
    endpoint_query("host_stats", "CPU load, temperature, uptime and throttling telemetry", "/machine/proc_stats", "proc_stats",
                   "system_cpu_usage cpu_temp system_uptime throttled_state", "How hot is the host CPU?", "Is the host throttling?"),
    endpoint_query("power_devices", "Reported power accessory states, never power switching", "/machine/device_power/devices", "power",
                   "devices", "What power devices are connected?"),
    endpoint_query("queue", "Queued jobs and queue state; never enqueue/start", "/server/job_queue/status", "job_queue",
                   "queued_jobs queue_state", "What jobs are queued?"),
    endpoint_query("webcams", "Configured camera names; no streaming or recording", "/server/webcams/list", "webcam",
                   "webcams", "What cameras are connected?"),
)}


FAMILIES = {
    "temperatures": {"heater_generic": ("temperature", "target"), "temperature_sensor": ("temperature",),
                     "temperature_fan": ("temperature", "target")},
    "targets": {"heater_generic": ("target",), "temperature_fan": ("target",)},
    "heater_power": {"heater_generic": ("power",)},
    "fans": {"heater_fan": ("speed", "rpm"), "controller_fan": ("speed", "rpm"),
             "fan_generic": ("speed", "rpm"), "temperature_fan": ("speed", "rpm")},
    "filament_sensors": {"filament_switch_sensor": ("enabled", "filament_detected"),
                         "filament_motion_sensor": ("enabled", "filament_detected")},
    "mcu": {"mcu": ("mcu_version", "last_stats")},
}

VALIDATION = {
    "homing": "Distinct lowercase x/y/z characters; empty string means no axes homed; absent/invalid is unknown",
    "temperatures": "Finite numeric Celsius >= -273.15; sensors and targets distinguished",
    "targets": "Finite numeric Celsius >= 0; setpoint only, never request heating",
    "heater_power": "Finite fraction 0..1, formatted as percent",
    "position": "At least three finite Cartesian coordinates in mm; last commanded, not measured; homing uncertainty labeled",
    "gcode_position": "Finite XYZ values in mm; G-code origin and configured coordinates distinguished",
    "motion": "Finite requested interpolated coordinates/velocity; no encoder or physical motion claim",
    "progress": "Finite fraction 0..1, display/M73 preferred with virtual SD fallback; reported job state included",
    "layers": "Positive integral counters; missing/null/zero means unavailable; no layer inferred from Z",
    "fans": "Finite duty cycle 0..1; optional finite nonnegative RPM; absence is not zero",
    "filament_sensors": "Strict boolean enabled and filament_detected; unknown does not mean no filament",
    "endstops": "Previously sampled strict booleans only; never query hardware through a G-code action",
    "probe": "Previously sampled strict boolean only; never probe hardware",
    "last_failure": "Newest-first bounded history scan; reported failure classification only; physical root cause unknown",
    "remaining": "Active printing/paused state plus finite nonnegative slicer estimate and active duration; label as estimate",
    "configuration": "Finite XYZ bounds, strict pending-save flag, bounded warning messages; no raw config/secrets exposed",
}
CATALOG = {key: replace(spec,
           response_fields=spec.response_fields or tuple(f"{family} *.{column}" for family, keys in FAMILIES.get(key, {}).items() for column in keys),
           validation=VALIDATION.get(key, spec.validation),
           fallback_endpoints=("/server/info", "/printer/info") if key in {"status", "errors"} else ())
           for key, spec in CATALOG.items()}


def object_fields(spec, available):
    result = {name: fields for name, fields in spec.objects if name in available}
    for name in available:
        family = name.split(" ", 1)[0]
        fields = FAMILIES.get(spec.id, {}).get(family)
        if fields:
            result[name] = fields
        if spec.id in {"temperatures", "targets", "heater_power", "extrusion", "pressure_advance"}:
            # Klipper names extra extruders extruder1, extruder2, etc.
            if name.startswith("extruder") and name[8:].isdigit():
                result[name] = dict(spec.objects).get("extruder", ())
    return result
