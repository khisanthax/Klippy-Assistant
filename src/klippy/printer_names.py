"""One local name registry shared by editing, testing and conversation selection."""
import re

from .domain import Printer
from .language import normalize


def name_surface(text):
    # Mask heater/value/unit operands, retaining offsets. A configured F/C/90/nozzle
    # label must not select a different printer or be removed from a target value.
    operand = re.compile(r"\b(?:nozzle|hotend|hot end|extruder|heated bed|bed)(?: temperature)? "
                         r"(?:up to |to |at )?[+-]?(?:\d+(?:\.\d+)?|\.\d+)\s*"
                         r"(?:(?:degrees?\s*)?(?:celsius|fahrenheit|c|f)\b|degrees?\b)?")
    return operand.sub(lambda match: " " * len(match[0]), text)


def name_spans(printer, text):
    surface = name_surface(text)
    labels = {normalize(n) for n in (printer.name, *printer.aliases)}
    return [(match.start(), match.end()) for label in labels if label
            for match in re.finditer(r"(?<!\w)" + re.escape(label) + r"(?!\w)", surface)]


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
