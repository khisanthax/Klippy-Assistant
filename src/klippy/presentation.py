"""Deterministic presentation; never creates an intent or authorizes an action."""
import math

from .query_format import clean, mapping, numeric, vector


class Response(str):
    def __new__(cls, detail, spoken):
        value = super().__new__(cls, detail)
        value.spoken = spoken
        value.verified = False
        value.capabilities = []
        value.stale = False
        value.fresh_until = None
        value.explanation_fact = None
        value.model_composed = False
        value.dialogue_ms = 0.0
        return value


def friendly_error(text):
    if text in {"Please clarify the information query; no action sent",
                "Please clarify the intended printer operation; no action sent",
                "Please specify a status query, printer action, or approved macro"}:
        return "I'm not sure what you're asking. Could you say that another way?"
    if text in {"Which single printer do you mean?", "Select an approved printer first"}:
        return "Which printer would you like to use?"
    if text.startswith("Which printer information do you want?"):
        return "What would you like to know about the printer?"
    if text in {"Requested information unavailable or unauthorized", "Current printer information unavailable",
                "Local language engine unavailable or request ambiguous; no action sent"}:
        return "I couldn't get that information just now. Please check the printer connection."
    return text  # Never remove an unknown safety warning or uncertain-outcome notice.


def present(name, identifier, status, detail, subject=None, style="brief", stale=False):
    if stale:
        return Response(detail, f"I can't verify {name}'s current state. The cached information may be out of date.")
    tool = mapping(status.get("toolhead"))
    speech = None
    if identifier == "homing":
        axes = tool.get("homed_axes")
        valid = isinstance(axes, str) and set(axes) <= set("xyz") and len(set(axes)) == len(axes)
        if valid:
            if set(axes) == set("xyz"):
                speech = f"{name} is fully homed."
                if style == "conversational":
                    speech += " All three axes are homed."
                elif style == "detailed":
                    speech = f"{name} reports X, Y and Z as homed."
            else:
                missing = ", ".join(a.upper() for a in "xyz" if a not in axes)
                speech = f"{name} isn't fully homed. {missing} {'is' if len(missing) == 1 else 'are'} not homed."
        else:
            speech = f"{name} hasn't reported which axes are homed."
    elif identifier in {"temperatures", "targets"}:
        rows, targets = [], []
        heaters = [("extruder", "nozzle"), ("heater_bed", "bed")]
        if subject == "sensors":
            heaters = [(key, clean(key.split(" ", 1)[1])) for key in status
                       if key.startswith(("temperature_sensor ", "temperature_fan "))]
        for key, label in heaters:
            if subject in {"bed", "nozzle"} and subject != label:
                continue
            data = mapping(status.get(key))
            value = numeric(data.get("target" if identifier == "targets" else "temperature"),
                            0 if identifier == "targets" else -273.15, 2000)
            if value is None:
                rows.append(f"the {label} temperature isn't available")
            elif identifier == "targets" and value == 0:
                rows.append(f"the {label} has no active heating target")
            else:
                rounded = f"{value:g}" if style == "detailed" else str(math.floor(value + .5))
                rows.append(f"the {label} {'target is' if identifier == 'targets' else 'is at'} {rounded} degrees")
            targets.append(numeric(data.get("target"), 0, 2000))
        speech = f"{name}: " + " and ".join(rows) + "." if rows else f"{name} hasn't reported those temperatures."
        if identifier == "temperatures" and targets and all(t == 0 for t in targets):
            speech += " No active heating targets."
    elif identifier == "progress":
        p = numeric(mapping(status.get("display_status")).get("progress"), 0, 1)
        if p is None:
            p = numeric(mapping(status.get("virtual_sdcard")).get("progress"), 0, 1)
        speech = f"{name} is {round(p*100)} percent complete." if p is not None else f"{name}'s progress isn't available."
        state = clean(mapping(status.get("print_stats")).get("state"))
        if state not in {"printing", "unavailable"}:
            speech += f" The reported job is {state}."
    elif identifier == "position":
        speech = f"{name}'s last commanded position is {vector(tool.get('position'))}."
        axes = tool.get("homed_axes")
        if not isinstance(axes, str) or set(axes) != set("xyz") or len(axes) != 3:
            speech += " The axes aren't confirmed as fully homed."
        speech += " This isn't a measured physical position."
    elif identifier == "status" and mapping(status.get("webhooks")).get("state") == "ready":
        state = clean(mapping(status.get("print_stats")).get("state"))
        if state in {"printing", "paused", "complete", "cancelled", "standby"}:
            speech = f"{name} is {'ready' if state == 'standby' else state}."
            progress = numeric(mapping(status.get("virtual_sdcard")).get("progress"), 0, 1)
            if state in {"printing", "paused"} and progress is not None:
                speech += f" The job is {round(progress * 100)} percent complete."
            if mapping(status.get("print_stats")).get("message"):
                speech += " " + clean(mapping(status.get("print_stats"))["message"])
            message = clean(mapping(status.get("webhooks")).get("state_message"))
            if message != "unavailable" and message.strip().lower().rstrip(".! ") not in {"", "ready", "printer is ready"}:
                speech += " " + message
    elif identifier == "layers":
        info = mapping(mapping(status.get("print_stats")).get("info"))
        layer, total = numeric(info.get("current_layer"), 1), numeric(info.get("total_layer"), 1)
        if layer is not None and total is not None and layer == int(layer) and total == int(total):
            speech = f"{name} reports layer {int(layer)} of {int(total)}."
    if speech is None:
        speech = detail.replace("_", " ")
        if "unsupported;" in detail or "required objects not reported" in detail:
            speech = f"{name} doesn't report that information."
    return Response(detail, speech)
