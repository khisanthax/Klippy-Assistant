"""Measure the isolated desktop shell. Models, microphones and printers stay inactive."""
import ctypes
import json
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from klippy.app import Window
from klippy.storage import Store
from klippy.theme import STYLE


class Counters(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                *[(name, ctypes.c_size_t) for name in ["PeakWorkingSetSize", "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage"]]]


app = QApplication([])
app.setQuitOnLastWindowClosed(False)
app.setStyleSheet(STYLE)
with tempfile.TemporaryDirectory() as temp:
    store = Store(Path(temp) / "settings.sqlite")
    window = Window(store, smoke=True)
    started, cpu = time.perf_counter(), time.process_time()
    QTimer.singleShot(15000, window.quit)
    app.exec()
    elapsed, consumed = time.perf_counter() - started, time.process_time() - cpu
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32")
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi")
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb)
    report = {"date": "2026-11-11", "scope": "Source desktop shell, hidden, no models/devices/printers",
              "host": "Windows 11 build 26200; Ryzen 7 5800X; 63.9 GiB RAM",
              "elapsed_seconds": round(elapsed, 3), "cpu_seconds": round(consumed, 4),
              "cpu_percent_of_one_core": round(100 * consumed / elapsed, 3),
              "working_set_mib": round(counters.WorkingSetSize / 2**20, 2),
              "peak_working_set_mib": round(counters.PeakWorkingSetSize / 2**20, 2)}
    Path("local/idle-benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    store.close()
