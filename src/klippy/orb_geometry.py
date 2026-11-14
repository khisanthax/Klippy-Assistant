"""Read-only Windows taskbar observations and pure per-monitor DIP placement."""
import ctypes
import math
import os
from ctypes import wintypes as w
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height


@dataclass(frozen=True)
class Desktop:
    bounds: Rect
    work: Rect
    scale: float = 1.0
    taskbar: Rect | None = None
    edge: str = "bottom"
    auto_hide: bool = False
    native_verified: bool = False


def native_to_logical(rect, native_monitor, logical_monitor, scale):
    # Windows screen origins are not globally scaled by Qt. Convert relative to
    # this monitor's origin, never divide mixed-DPI global coordinates by a scale.
    return Rect(logical_monitor.x + (rect.x - native_monitor.x) / scale,
                logical_monitor.y + (rect.y - native_monitor.y) / scale,
                rect.width / scale, rect.height / scale)


def same_monitor(screen_name, logical_bounds, device, native_bounds):
    # Qt 6 may expose the EDID friendly name rather than GDI's \\.\DISPLAYn.
    # Windows/Qt preserve per-monitor native origins even when sizes use DIPs.
    return (screen_name.casefold() == device.casefold() or
            (logical_bounds.x, logical_bounds.y) == (native_bounds.x, native_bounds.y))


def safe_area(desktop):
    b, area, bar = desktop.bounds, desktop.work, desktop.taskbar
    left, top = max(b.x, area.x), max(b.y, area.y)
    right, bottom = min(b.right, area.right), min(b.bottom, area.bottom)
    if bar:
        if desktop.edge == "bottom":
            bottom = min(bottom, bar.y)
        elif desktop.edge == "top":
            top = max(top, bar.bottom)
        elif desktop.edge == "left":
            left = max(left, bar.right)
        elif desktop.edge == "right":
            right = min(right, bar.x)
    elif area == b:
        bottom -= 48  # Explorer/geometry unavailable: reserve a conservative logical taskbar strip.
    return Rect(left, top, max(1, right-left), max(1, bottom-top))


def placement(desktop, diameter, custom=None):
    area = safe_area(desktop)
    gap = max(1, math.ceil(10 / desktop.scale))  # 8–12 physical pixels across supported scales.
    gap = min(gap, max(0, (min(area.width, area.height)-1)//2))
    size = max(1, min(diameter, int(area.width-2*gap), int(area.height-2*gap)))
    x, y = custom if custom else (area.right-size-gap, area.bottom-size-gap)
    if not custom and desktop.edge == "left":
        x = area.x + gap
    if not custom and desktop.edge == "top":
        y = area.y + gap
    x = min(max(x, area.x+gap), max(area.x+gap, area.right-size-gap))
    y = min(max(y, area.y+gap), max(area.y+gap, area.bottom-size-gap))
    return round(x), round(y), size


def reduced_motion():
    if os.name != "nt":
        return False
    enabled = w.BOOL()
    try:
        return bool(ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)) and not enabled.value
    except (OSError, AttributeError):
        return False


def observe_windows(screen_name, logical_bounds, logical_work, scale):
    fallback = Desktop(logical_bounds, logical_work, scale)
    if os.name != "nt":
        return fallback
    try:
        user, shell = ctypes.windll.user32, ctypes.windll.shell32
        class MonitorInfo(ctypes.Structure):
            _fields_ = [("cbSize", w.DWORD), ("monitor", w.RECT), ("work", w.RECT),
                        ("flags", w.DWORD), ("device", w.WCHAR*32)]
        class AppBar(ctypes.Structure):
            _fields_ = [("cbSize", w.DWORD), ("hwnd", w.HWND), ("message", w.UINT),
                        ("edge", w.UINT), ("rect", w.RECT), ("param", w.LPARAM)]
        user.MonitorFromWindow.argtypes, user.MonitorFromWindow.restype = [w.HWND, w.DWORD], w.HMONITOR
        user.GetMonitorInfoW.argtypes = [w.HMONITOR, ctypes.POINTER(MonitorInfo)]
        user.GetWindowRect.argtypes = [w.HWND, ctypes.POINTER(w.RECT)]
        user.GetClassNameW.argtypes = [w.HWND, w.LPWSTR, ctypes.c_int]
        shell.SHAppBarMessage.argtypes, shell.SHAppBarMessage.restype = [w.DWORD, ctypes.POINTER(AppBar)], ctypes.c_size_t
        callback_type = ctypes.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        user.EnumWindows.argtypes = [callback_type, w.LPARAM]
        observations = []
        def rect(r):
            return Rect(r.left, r.top, r.right-r.left, r.bottom-r.top)
        def visit(hwnd, _):
            name = ctypes.create_unicode_buffer(100)
            user.GetClassNameW(hwnd, name, 100)
            if name.value not in {"Shell_TrayWnd", "Shell_SecondaryTrayWnd"}:
                return True
            monitor = MonitorInfo()
            monitor.cbSize = ctypes.sizeof(monitor)
            handle = user.MonitorFromWindow(hwnd, 2)
            bounds = w.RECT()
            if not user.GetMonitorInfoW(handle, ctypes.byref(monitor)):
                return True
            if not same_monitor(screen_name, logical_bounds, monitor.device, rect(monitor.monitor)):
                return True
            if not user.GetWindowRect(hwnd, ctypes.byref(bounds)):
                return True
            b, bar = rect(monitor.monitor), rect(bounds)
            if bar.width <= 0 or bar.height <= 0:
                return True
            edge = ("top" if abs(bar.y-b.y) < abs(bar.bottom-b.bottom) else "bottom") if bar.width > bar.height else (
                "left" if abs(bar.x-b.x) < abs(bar.right-b.right) else "right")
            abd = AppBar()
            abd.cbSize, abd.edge, abd.rect = ctypes.sizeof(abd), {"left":0,"top":1,"right":2,"bottom":3}[edge], monitor.monitor
            auto = bool(shell.SHAppBarMessage(0xB, ctypes.byref(abd)))  # ABM_GETAUTOHIDEBAREX, read-only.
            if auto and edge in {"top", "bottom"} and bar.height < 16*scale:
                bar = Rect(bar.x, bar.y, bar.width, 48*scale)
            elif auto and edge in {"left", "right"} and bar.width < 16*scale:
                bar = Rect(bar.x, bar.y, 48*scale, bar.height)
            # Reconstruct the full dock strip even when Explorer slides it offscreen.
            if edge in {"top", "bottom"}:
                bar = Rect(b.x, b.y if edge == "top" else b.bottom-bar.height, b.width, bar.height)
            else:
                bar = Rect(b.x if edge == "left" else b.right-bar.width, b.y, bar.width, b.height)
            def convert(value):
                return native_to_logical(value, b, logical_bounds, scale)
            observations.append(Desktop(logical_bounds, convert(rect(monitor.work)), scale,
                                        convert(bar), edge, auto, True))
            return True
        user.EnumWindows(callback_type(visit), 0)
        return observations[0] if observations else fallback
    except (OSError, AttributeError, ValueError):
        return fallback
