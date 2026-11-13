"""One local name registry shared by editing, testing and conversation selection."""
import re

from .domain import Printer


def matching(printers, text):
    return [p for p in printers if any(re.search(r"(?<!\w)" + re.escape(n.casefold()) + r"(?!\w)", text.casefold())
                                     for n in (p.name, *p.aliases))]


def validate_names(store, printer, name, aliases):
    value = Printer.model_validate({**printer.model_dump(), "name": name, "aliases": tuple(aliases)})
    labels = [value.name.casefold(), *(a.casefold() for a in value.aliases)]
    if len(set(labels)) != len(labels):
        raise ValueError("A name or alias is repeated")
    for other in store.printers():
        if other.id != printer.id and set(labels) & {other.name.casefold(), *(a.casefold() for a in other.aliases)}:
            raise ValueError(f"That name or alias is already used by {other.name}")
    return value


def rename(store, printer, name, aliases):
    value = validate_names(store, printer, name, aliases)
    store.save_printer(value)
    return value
