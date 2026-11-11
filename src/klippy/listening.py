from datetime import datetime


def listening_enabled(settings: dict, now: datetime) -> bool:
    override = settings.get("override")
    if override is not None:
        return bool(override)
    mode = settings.get("mode", "manual")
    if mode == "always":
        return True
    if mode == "manual":
        return bool(settings.get("enabled", False))
    if mode != "scheduled":
        return False
    minute = now.hour * 60 + now.minute
    for window in settings.get("windows", []):
        start, end = window.get("start", 0), window.get("end", 0)
        days = window.get("days", [])
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < 1440 and 0 <= end < 1440):
            continue
        if start <= end and now.weekday() in days and start <= minute < end:
            return True
        if start > end and ((now.weekday() in days and minute >= start)
                            or ((now.weekday() - 1) % 7 in days and minute < end)):
            return True
    return False
