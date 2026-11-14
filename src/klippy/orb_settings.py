"""Locally persisted presentation preferences. No voice/control permissions."""
import json
from typing import Annotated, Literal

from pydantic import Field, field_validator

from .domain import StrictModel


class OrbPreferences(StrictModel):
    enabled: bool = True
    diameter: Annotated[int, Field(ge=128, le=384)] = 192  # 2 nominal inches at 96 logical DPI.
    position: Literal["clock", "custom"] = "clock"
    custom_position: tuple[int, int] | None = None
    custom_monitor: Annotated[str, Field(max_length=100)] = ""
    hide_delay: Annotated[float, Field(ge=0, le=30, allow_inf_nan=False)] = 3.0
    show_printer: bool = True
    show_status: bool = True
    intensity: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] = .65
    animations: bool = True
    pinned: bool = False

    @field_validator("custom_position")
    @classmethod
    def bounded_position(cls, value):
        if value is not None and any(abs(n) > 100000 for n in value):
            raise ValueError("Orb position is outside supported display coordinates")
        return value


def preferences(value):
    return OrbPreferences.model_validate_json(json.dumps(value))
