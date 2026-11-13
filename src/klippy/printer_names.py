"""One local name registry shared by editing, testing and conversation selection."""
import re

from .domain import Printer
from .language import heat_intent, heating_request, incomplete_heat, normalize
from .safety import Rejected


def complete_heat(text, printer_id):
    try:
        return heat_intent(text, printer_id) is not None
    except Rejected:
        return False


def name_spans(printer, text):
    labels = {normalize(n) for n in (printer.name, *printer.aliases)}
    spans = [(match.start(), match.end()) for label in labels if label
             for match in re.finditer(r"(?<!\w)" + re.escape(label) + r"(?!\w)", text)]
    if not heating_request(text):
        return spans
    # An already complete request names a heater/value/unit, not another printer.
    # Otherwise a name is genuine only if removing that exact span leaves a full
    # heating request. This keeps 90 F intact in 'heat nozzle 90 F on F'.
    if complete_heat(text, printer.id):
        return []
    genuine = []
    for start, end in spans:
        before, after = text[:start], text[end:]
        position = (re.search(r"\b(?:nozzle|hotend|hot end|extruder|bed)\b", after)
                    or re.search(r"\b(?:on|for)(?: the| my)?(?: printer)?\s*$", before))
        remaining = " ".join((before + " " + after).split())
        if position and (complete_heat(remaining, printer.id) or incomplete_heat(remaining)):
            genuine.append((start, end))
    return genuine


def matching(printers, text):
    text = normalize(text)
    return [p for p in printers if name_spans(p, text)]


def remove_names(printer, text):
    text = normalize(text)
    characters = list(text)
    for start, end in name_spans(printer, text):
        characters[start:end] = " " * (end - start)
    return " ".join("".join(characters).split())


def validate_names(store, printer, name, aliases):
    value = Printer.model_validate({**printer.model_dump(), "name": name, "aliases": tuple(aliases)})
    labels = [value.name.casefold(), *(a.casefold() for a in value.aliases)]
    if any(not normalize(label) for label in labels):
        raise ValueError("Use recognizable words or numbers in each printer name or alias")
    if len(set(labels)) != len(labels):
        raise ValueError("A name or alias is repeated")
    for other in store.printers():
        if other.id != printer.id and {normalize(n) for n in (value.name, *value.aliases)} & {normalize(n) for n in (other.name, *other.aliases)}:
            raise ValueError(f"That name or alias is already used by {other.name}")
    return value


def rename(store, printer, name, aliases):
    value = validate_names(store, printer, name, aliases)
    store.save_printer(value)
    return value
