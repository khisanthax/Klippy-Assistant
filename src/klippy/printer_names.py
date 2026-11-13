"""One local name registry shared by editing, testing and conversation selection."""
import re

from .domain import Printer
from .language import normalize


def matching(printers, text):
    text = normalize(text)
    return [p for p in printers if any(label and re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", text)
                                     for label in (normalize(n) for n in (p.name, *p.aliases)))]


def remove_names(printer, text):
    text = normalize(text)
    for label in sorted({normalize(n) for n in (printer.name, *printer.aliases)}, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(label) + r"(?!\w)", " ", text)
    return " ".join(text.split())


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
