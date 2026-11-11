"""Read-only Happy Hare status normalization; unknown fields grant no authority."""
from .domain import StrictModel


class MmuStatus(StrictModel):
    state: str = "unknown"
    tool: int | None = None
    gate: int | None = None
    available: bool = False
    fault: bool = False


def normalize(value):
    if not isinstance(value, dict) or not value:
        return MmuStatus()
    state = value.get("print_state", value.get("print_job_state", "unknown"))
    state = state if isinstance(state, str) else "unknown"
    return MmuStatus(state=state[:40], available=True,
                     fault=state in {"pause_locked", "error"} or value.get("is_locked") is True,
                     tool=value.get("tool") if type(value.get("tool")) is int else None,
                     gate=value.get("gate") if type(value.get("gate")) is int else None)
