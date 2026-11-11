from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Action(StrEnum):
    STATUS = "status"
    TEMPERATURES = "temperatures"
    MACROS = "macros"
    PAUSE = "pause"
    RESUME = "resume"
    CANCEL = "cancel"
    HOME = "home"
    HEAT = "heat"
    MACRO = "macro"
    EMERGENCY = "emergency_stop"


class Intent(StrictModel):
    action: Action
    printer_id: str
    query_subject: Literal["nozzle", "bed"] | None = None
    macro: str | None = None
    params: dict[str, Annotated[float | int, Field(allow_inf_nan=False)]] = Field(default_factory=dict)


class Printer(StrictModel):
    id: str
    name: str
    url: str
    approved: bool = False

    @field_validator("id", "name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip() or len(value) > 80 or any(ord(c) < 32 for c in value):
            raise ValueError("A short, nonempty name is required")
        return value.strip()

    @field_validator("url")
    @classmethod
    def valid_url(cls, value):
        from urllib.parse import urlsplit
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError("Use an HTTP(S) host and port, without credentials or a path")
        # LAN locality is checked at connection time as well, after DNS resolution.
        return value.rstrip("/")


class Parameter(StrictModel):
    minimum: float
    maximum: float
    integer: bool = False
    required: bool = True


class Macro(StrictModel):
    name: str
    definition: str
    description: str = ""
    previous_definition: str | None = None
    review_notes: tuple[str, ...] = ()
    dependency_fingerprint: str = ""
    approved: bool = False
    enabled: bool = False
    reviewed: bool = False
    aliases: tuple[str, ...] = ()
    parameters: dict[str, Parameter] = Field(default_factory=dict)

    @property
    def fingerprint(self):
        return digest({"definition": self.definition, "name": self.name, "dependencies": self.dependency_fingerprint})


class Snapshot(StrictModel):
    connected: bool
    ready: bool = False
    state: str = "unknown"
    progress: float | None = None
    temperatures: dict[str, float] = Field(default_factory=dict)
    message: str = ""


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def safe_macro_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]{0,79}", name))
