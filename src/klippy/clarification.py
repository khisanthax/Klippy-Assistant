"""Printer-bound identity choices. Selection is never execution permission."""

import re
import uuid
from dataclasses import dataclass, field

from .diagnostics import current
from .domain import Action, Intent, digest
from .macros import semantic_words


def registry_signature(registry):
    return digest({key: macro.model_dump(mode="json") for key, macro in registry.items()})


def request_key(printer, text):
    text = re.sub(r"\b[a-z_]+\s*(?:=|is|of|at)?\s*-?\d+(?:\.\d+)?\b", " ", text.lower())
    filler = {"run", "please", "the", "macro", "can", "could", "you", "my", "a", "some", "with"}
    return digest({"printer": printer, "words": sorted(semantic_words(text) - filler)})


@dataclass
class Choice:
    printer_id: str
    request: str
    names: list[str]
    signature: str
    session_id: str
    created: float
    parameter: Intent | None = None
    remember: bool = False
    identity: str = field(default_factory=lambda: uuid.uuid4().hex)
    trace: int | None = field(default_factory=lambda: current.get())

    def selected(self, text):
        text = text.strip().lower().rstrip(".!?")
        ordinals = {"first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4, "sixth": 5}
        match = re.fullmatch(
            r"(?:the )?(first|second|third|fourth|fifth|sixth)(?: one| 1| option| command)?", text
        )
        if match:
            index = ordinals[match[1]]
            return self.names[index] if index < len(self.names) else None
        exact = next((name for name in self.names if name.casefold() == text), None)
        if exact:
            return exact
        spoken = [name for name in self.names if re.sub(r"[_\s]+", " ", name.casefold()).strip() == text]
        return spoken[0] if len(spoken) == 1 else None


def macro_intent(text, macro, printer):
    params = {}
    for key, value in re.findall(r"\b([a-z_]+)\s*(?:=|is|of|at)?\s*(-?\d+(?:\.\d+)?)\b", text.lower()):
        key = key.upper()
        if key not in macro.parameters or key in params:
            raise ValueError("Specify each reviewed macro parameter once; unknown parameters are blocked")
        params[key] = float(value)
    return Intent(action=Action.MACRO, printer_id=printer, macro=macro.name, params=params)


def popup_position(orb, work, width, height):
    width, height = min(width, work.width), min(height, work.height)
    x = max(work.x, min(orb.x + (orb.width - width) // 2, work.x + work.width - width))
    y = max(work.y, min(orb.y - height - 8, work.y + work.height - height))
    return x, y, width, height
