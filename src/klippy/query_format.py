"""Typed bounded factual formatting. Remote messages are data, never instructions."""
import math
import re

UNKNOWN = "unavailable"


def mapping(value):
    return value if isinstance(value, dict) else {}


def clean(value, limit=120):
    return re.sub(r"[\x00-\x1f\x7f]", " ", value)[:limit] if isinstance(value, str) else UNKNOWN


def numeric(value, low=None, high=None):
    if type(value) not in (int, float):
        return None
    try:
        if not math.isfinite(value):
            return None
    except OverflowError:
        return None
    return value if (low is None or value >= low) and (high is None or value <= high) else None


def num(value, unit="", low=None, high=None, factor=1):
    value = numeric(value, low, high)
    return UNKNOWN if value is None else f"{value * factor:.3f}".rstrip("0").rstrip(".") + unit


def boolean(value):
    return "yes" if value is True else "no" if value is False else UNKNOWN


def vector(value):
    if not isinstance(value, (list, tuple)) or len(value) < 3 or any(numeric(v) is None for v in value[:3]):
        return UNKNOWN
    return ", ".join(f"{axis.upper()} {num(v, ' mm')}" for axis, v in zip("xyz", value))


def render(identifier, status, result, subject=None):
    def obj(name):
        return mapping(status.get(name))
    tool, stats, move = obj("toolhead"), obj("print_stats"), obj("gcode_move")
    if identifier == "homing":
        axes = tool.get("homed_axes")
        if not isinstance(axes, str) or any(a not in "xyz" for a in axes) or len(set(axes)) != len(axes):
            return "Homing status unavailable; homed axes were not validly reported."
        homed = ", ".join(a.upper() for a in "xyz" if a in axes) or "none"
        missing = ", ".join(a.upper() for a in "xyz" if a not in axes) or "none"
        return f"Homed axes: {homed}. Not homed: {missing}."
    if identifier in {"temperatures", "targets", "heater_power"}:
        rows = []
        for name, raw in status.items():
            if not (name in {"extruder", "heater_bed"} or name.startswith(("extruder", "heater_generic ",
                    "temperature_sensor ", "temperature_fan "))):
                continue
            if subject == "bed" and name != "heater_bed" or subject == "nozzle" and not name.startswith("extruder"):
                continue
            if subject == "sensors" and not name.startswith(("temperature_sensor ", "temperature_fan ")):
                continue
            value = mapping(raw)
            label = "bed" if name == "heater_bed" else "nozzle" if name == "extruder" else clean(name)
            if identifier == "heater_power":
                detail = "power " + num(value.get("power"), "%", 0, 1, 100)
            elif identifier == "targets":
                detail = "target " + num(value.get("target"), " degrees Celsius", 0, 2000)
            else:
                detail = num(value.get("temperature"), " degrees Celsius", -273.15, 2000)
                if "target" in value:
                    detail += ", target " + num(value.get("target"), " degrees Celsius", 0, 2000)
            rows.append(f"{label}: {detail}")
        return "; ".join(rows) if rows else "Requested heater/sensor data unavailable."
    if identifier == "position":
        axes = tool.get("homed_axes")
        valid = isinstance(axes, str) and all(a in "xyz" for a in axes) and len(set(axes)) == len(axes)
        qualifier = ("Cartesian axes homed" if set(axes) == set("xyz") else "axes not all homed") if valid else "homing status unavailable"
        if subject in {"x", "y", "z"}:
            values = tool.get("position")
            value = values["xyz".index(subject)] if vector(values) != UNKNOWN else None
            axis_homing = f"{subject.upper()} {'homed' if subject in axes else 'not homed'}" if valid else "homing status unavailable"
            return f"Last commanded {subject.upper()} position: {num(value, ' mm')}; {axis_homing}. Not measured physical position."
        return f"Last commanded machine position: {vector(tool.get('position'))}; {qualifier}. Not measured physical position."
    if identifier == "gcode_position":
        if subject in {"x", "y", "z"}:
            values = move.get("gcode_position")
            value = values["xyz".index(subject)] if vector(values) != UNKNOWN else None
            return f"G-code {subject.upper()} position: {num(value, ' mm')}; origin offset: {vector(move.get('homing_origin'))}. Not measured physical position."
        return f"G-code position: {vector(move.get('gcode_position'))}; origin offset: {vector(move.get('homing_origin'))}."
    if identifier == "motion":
        motion = obj("motion_report")
        return (f"Requested interpolated position: {vector(motion.get('live_position'))}; "
                f"velocity {num(motion.get('live_velocity'), ' mm/s', 0)}; "
                f"extruder velocity {num(motion.get('live_extruder_velocity'), ' mm/s')}. Not encoder-measured motion.")
    if identifier == "limits":
        return "; ".join(f"{label}: {num(tool.get(field), unit, 0, high)}" for field, label, unit, high in (
            ("max_velocity", "max velocity", " mm/s", None), ("max_accel", "max acceleration", " mm/s squared", None),
            ("square_corner_velocity", "square corner velocity", " mm/s", None),
            ("minimum_cruise_ratio", "minimum cruise ratio", "", 1)))
    if identifier == "speed":
        return (f"Last commanded feedrate {num(move.get('speed'), ' mm/s', 0)}; "
                f"speed override {num(move.get('speed_factor'), '%', 0, factor=100)}; "
                f"flow override {num(move.get('extrude_factor'), '%', 0, factor=100)}.")
    if identifier == "progress":
        sd = numeric(obj("virtual_sdcard").get("progress"), 0, 1)
        display = numeric(obj("display_status").get("progress"), 0, 1)
        progress = display if display is not None else sd
        return f"Reported job: {clean(stats.get('state'))}; {num(progress, '%', 0, 1, 100)} complete."
    if identifier == "job":
        return (f"Reported file: {clean(stats.get('filename')) or 'none'}; state: {clean(stats.get('state'))}; "
                f"paused: {boolean(obj('pause_resume').get('is_paused'))}.")
    if identifier == "layers":
        info = mapping(stats.get("info"))
        def layer(key):
            value = numeric(info.get(key), 1)
            return str(int(value)) if value is not None and value == int(value) else UNKNOWN
        return f"Slicer-reported layer {layer('current_layer')} of {layer('total_layer')}; state {clean(stats.get('state'))}."
    if identifier == "duration":
        return f"Active print time: {num(stats.get('print_duration'), ' seconds', 0)}; total job time: {num(stats.get('total_duration'), ' seconds', 0)}."
    if identifier == "filament":
        return f"Reported job filament used: {num(stats.get('filament_used'), ' mm', 0)}."
    if identifier == "fans":
        return "; ".join(f"{clean(name)}: {num(mapping(v).get('speed'), '%', 0, 1, 100)}, RPM {num(mapping(v).get('rpm'), low=0)}"
                         for name, v in status.items() if name == "fan" or name.startswith(("fan_generic ", "heater_fan ", "controller_fan ", "temperature_fan "))) or "No supported fan telemetry reported."
    if identifier == "filament_sensors":
        return "; ".join(f"{clean(name)}: filament detected {boolean(mapping(v).get('filament_detected'))}, enabled {boolean(mapping(v).get('enabled'))}"
                         for name, v in status.items() if name.startswith(("filament_switch_sensor ", "filament_motion_sensor "))) or "No filament sensor telemetry reported."
    if identifier in {"errors", "status"}:
        web = obj("webhooks")
        return (f"Klipper: {clean(web.get('state'))}; {clean(web.get('state_message'))}. "
                f"Job: {clean(stats.get('state'))}; message: {clean(stats.get('message'))}." +
                (f" Reported progress: {num(obj('virtual_sdcard').get('progress'), '%', 0, 1, 100)}." if identifier == "status" else ""))
    if identifier == "configuration":
        cfg = obj("configfile")
        warnings = cfg.get("warnings")
        descriptions = "; ".join(clean(mapping(w).get("message"), 80) for w in warnings[:3]) if isinstance(warnings, list) else UNKNOWN
        return (f"Configured minimum: {vector(tool.get('axis_minimum'))}; maximum: {vector(tool.get('axis_maximum'))}. "
                f"Unsaved config pending: {boolean(cfg.get('save_config_pending'))}; warnings: {descriptions or 'none reported'}.")
    if identifier == "bed_mesh":
        mesh = obj("bed_mesh")
        return f"Loaded mesh profile: {clean(mesh.get('profile_name')) or 'none'}."
    if identifier == "leveling":
        return f"Gantry leveling applied: {boolean(obj('quad_gantry_level').get('applied'))}; Z tilt applied: {boolean(obj('z_tilt').get('applied'))}."
    if identifier == "endstops":
        states = obj("query_endstops").get("last_query")
        return "Last recorded endstop sample (not a fresh measurement): " + ("; ".join(f"{clean(k)}: {boolean(v)}" for k, v in list(states.items())[:8]) if isinstance(states, dict) else UNKNOWN)
    if identifier == "probe":
        return f"Probe {clean(obj('probe').get('name'))}; last recorded triggered state: {boolean(obj('probe').get('last_query'))}. Not a fresh probe measurement."
    if identifier == "pressure_advance":
        return f"Pressure advance: {num(obj('extruder').get('pressure_advance'), low=0)}; smooth time: {num(obj('extruder').get('smooth_time'), ' seconds', 0)}."
    if identifier == "retraction":
        return "; ".join(f"{key.replace('_', ' ')}: {num(obj('firmware_retraction').get(key), unit)}" for key, unit in (
            ("retract_length", " mm"), ("retract_speed", " mm/s"), ("unretract_extra_length", " mm"), ("unretract_speed", " mm/s")))
    if identifier == "extrusion":
        return f"Active extruder: {clean(tool.get('extruder'))}; primary extruder can extrude: {boolean(obj('extruder').get('can_extrude'))}."
    if identifier == "mmu":
        mmu = obj("mmu")
        return f"MMU state: {clean(mmu.get('print_state', mmu.get('print_job_state')))}; tool: {num(mmu.get('tool'), low=-1)}; gate: {num(mmu.get('gate'), low=-1)}; locked: {boolean(mmu.get('is_locked'))}."
    if identifier == "mcu":
        return "; ".join(f"{clean(name)} firmware: {clean(mapping(v).get('mcu_version'))}, last task average: {num(mapping(mapping(v).get('last_stats')).get('task_avg'), ' seconds', 0)}" for name, v in status.items() if name == "mcu" or name.startswith("mcu ")) or "Controller firmware unavailable."
    value = mapping(result)
    if identifier == "server":
        failed = value.get("failed_components")
        return f"Moonraker {clean(value.get('moonraker_version'))}; Klipper connected: {boolean(value.get('klippy_connected'))}; state: {clean(value.get('klippy_state'))}; failed components: {', '.join(clean(x) for x in failed[:6]) if isinstance(failed, list) else UNKNOWN}."
    if identifier == "printer_info":
        return f"Klipper {clean(value.get('software_version'))}; state: {clean(value.get('state'))}; {clean(value.get('state_message'))}."
    if identifier in {"history", "last_failure"}:
        jobs = value.get("jobs")
        if not isinstance(jobs, list):
            return "History data unavailable."
        if identifier == "last_failure":
            failed = [j for j in jobs if isinstance(j, dict) and j.get("status") in {
                "cancelled", "error", "klippy_shutdown", "klippy_disconnect", "interrupted"}]
            if not failed:
                return "No unsuccessful job reported in the most recent 50 history entries. No failure cause can be established."
            job = failed[0]
            return f"Last unsuccessful recorded job: {clean(job.get('filename'))}; recorded outcome: {clean(job.get('status'))}. History does not establish a physical root cause."
        return "Recent recorded jobs: " + ("; ".join(f"{clean(mapping(j).get('filename'))}: {clean(mapping(j).get('status'))}" for j in jobs[:5]) or "none")
    if identifier == "totals":
        total = mapping(value.get("job_totals"))
        return f"Recorded jobs since totals reset: {num(total.get('total_jobs'), low=0)}; print time: {num(total.get('total_print_time'), ' seconds', 0)}; filament: {num(total.get('total_filament_used'), ' mm', 0)}."
    if identifier == "metadata":
        return (f"File {clean(value.get('filename'))}; slicer {clean(value.get('slicer'))}; material {clean(value.get('filament_type'))}; "
                f"layer height {num(value.get('layer_height'), ' mm', 0)}; slicer estimated total {num(value.get('estimated_time'), ' seconds', 0)}.")
    if identifier == "remaining":
        estimate, elapsed = numeric(value.get("estimated_time"), 0), numeric(stats.get("print_duration"), 0)
        return (f"Slicer-based remaining estimate: {num(max(0, estimate-elapsed), ' seconds')} of active printing; pauses and runtime changes can invalidate it."
                if estimate is not None and elapsed is not None else "Remaining time unavailable; slicer estimate and active duration are required.")
    if identifier == "files":
        return "Available G-code files: " + ("; ".join(clean(mapping(v).get("path")) for v in result[:5]) if isinstance(result, list) else UNKNOWN)
    if identifier == "host":
        system = mapping(value.get("system_info"))
        cpu = mapping(system.get("cpu_info"))
        dist = mapping(system.get("distribution"))
        memory = num(cpu.get('total_memory'), ' kB', 0) if cpu.get('memory_units') == 'kB' else UNKNOWN
        return f"Host platform: {clean(dist.get('name'))}; CPU: {clean(cpu.get('cpu_desc'))}; CPUs: {num(cpu.get('cpu_count'), low=1)}; reported total memory: {memory}."
    if identifier == "host_stats":
        flags = mapping(value.get("throttled_state")).get("flags")
        return (f"Host CPU load: {num(mapping(value.get('system_cpu_usage')).get('cpu'), '%', 0, 100)}; "
                f"CPU temperature: {num(value.get('cpu_temp'), ' degrees Celsius', -273.15, 200)}; "
                f"uptime: {num(value.get('system_uptime'), ' seconds', 0)}; throttle flags: "
                + (", ".join(clean(f) for f in flags[:4]) or "none reported" if isinstance(flags, list) else UNKNOWN))
    if identifier in {"power_devices", "queue", "webcams"}:
        key = {"power_devices": "devices", "queue": "queued_jobs", "webcams": "webcams"}[identifier]
        rows = value.get(key)
        if not isinstance(rows, list):
            return "Accessory/queue information unavailable."
        def label(row):
            row = mapping(row)
            return clean(row.get("filename" if identifier == "queue" else "name"))
        detail = "; ".join(label(row) + (": " + clean(mapping(row).get("status")) if identifier == "power_devices" else "") for row in rows[:5]) or "none reported"
        return (f"Queue state: {clean(value.get('queue_state'))}; " if identifier == "queue" else "") + detail
    raise ValueError("Uncatalogued formatter")
