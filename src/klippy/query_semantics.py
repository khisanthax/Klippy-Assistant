"""Requested measurement semantics. Never creates an action or guesses a value."""
import re


def axis(text):
    found = re.search(r"\b([xyz]|zed|zee)(?: axis)?\b", text)
    return ("z" if found[1] in {"zed", "zee"} else found[1]) if found else None


def position_hint(text, previous=None):
    subject = axis(text)
    if re.fullmatch(r"(?:and|what about|how about)(?: the)? (?:[xyz]|zed|zee)(?: axis)?", text):
        if previous and previous.query_id in {"position", "gcode_position"}:
            return previous.query_id, subject
        if previous and previous.query_id == "homing":
            return "homing", None
        raise ValueError("Do you mean the axis position or whether it is homed?")
    if re.search(r"\b(?:layer height|build height|build volume|axis limits|maximum|min(?:imum)?|max|travel limit|z hop|retract)\b", text):
        return None
    if re.search(r"\b(?:homed|homing|acceleration|velocity|speed|feedrate)\b", text):
        return None
    spatial = bool(re.search(r"\b(?:height|elevation|position|coordinates?|location|offset|origin|how high|where)\b", text))
    if not spatial or not (subject or re.search(r"\b(?:nozzle|toolhead|printhead|head|vertical)\b", text)):
        return None
    thermal = bool(re.search(r"\b(?:temperatures?|hot|cold|degrees|target)\b", text))
    if thermal:
        if re.search(r"\b(?:and|also|as well)\b", text):
            raise ValueError("Please ask position and temperature questions separately so I can answer each accurately.")
        return None  # 'temperature at Z height' requests temperature, not a new coordinate.
    if subject is None and re.search(r"\b(?:height|elevation|how high|vertical)\b", text):
        subject = "z"
    return ("gcode_position" if re.search(r"\b(?:offset|origin|gcode|g code)\b", text) else "position"), subject


def model_query_compatible(text, query_id):
    # A model must not answer an unrecognized spatial measurement with heater readings.
    # Unknown intent stays unknown; no endpoint/value/action is inferred here.
    length = re.search(r"\b(?:height|elevation|distance|diameter|length|width|depth|coordinates?)\b", text)
    thermal = re.search(r"\b(?:temperatures?|hot|cold|degrees|target)\b", text)
    if length and not thermal:
        allowed = {"position", "gcode_position"}
        readiness = re.match(r"(?:has|have|is|are|does)\b", text) and re.search(r"\b(?:established|zeroed|referenced|reference)\b", text)
        if readiness and not re.search(r"\b(?:height|elevation|distance|diameter|length|width|depth)\b", text):
            allowed.add("homing")
        if re.search(r"\b(?:maximum|minimum|max|min|build|limit|bounds|travel)\b", text):
            allowed.add("configuration")
        if re.search(r"\blayer\b", text):
            allowed.add("metadata")
        if re.search(r"\bfilament\b", text) and re.search(r"\b(?:used|consumed|usage|total)\b", text):
            allowed |= {"filament", "totals"}
        if re.search(r"\bretract", text):
            allowed.add("retraction")
        if re.search(r"\bmesh\b", text):
            allowed.add("bed_mesh")
        return query_id in allowed
    return True
