from dataclasses import dataclass, field

import httpx
import pytest

from klippy.domain import Printer
from klippy.limits_probe import synthetic_settings, synthetic_status
from klippy.moonraker import Moonraker
from klippy.safety import SafetyEngine
from klippy.storage import Store


@dataclass
class Simulator:
    state: str = "standby"
    ready: bool = True
    offline: bool = False
    timeout_on_write: bool = False
    config: dict = field(default_factory=lambda: {"gcode_macro LOAD_FILAMENT": {"gcode": "M83\nG1 E5 F60"}})
    writes: list = field(default_factory=list)
    settings: dict = field(default_factory=synthetic_settings)
    eventtime: int = 0

    def handle(self, request):
        if self.offline:
            raise httpx.ConnectError("simulated private details", request=request)
        if request.method == "POST":
            self.writes.append((request.url.path, request.content))
            if self.timeout_on_write:
                raise httpx.ReadTimeout("secret endpoint and token", request=request)
            if request.url.path.endswith("pause"):
                self.state = "paused"
            elif request.url.path.endswith("resume"):
                self.state = "printing"
            elif request.url.path.endswith("cancel"):
                self.state = "cancelled"
            return httpx.Response(200, json={"result": "ok"})
        if request.url.path.endswith('/list'):
            result = {'objects': list(synthetic_status())}
        elif "configfile=settings" in str(request.url):
            self.eventtime += 1
            status = synthetic_status()
            status['configfile']['settings'] = self.settings
            status['webhooks']['state'] = 'ready' if self.ready else 'shutdown'
            status['print_stats']['state'] = self.state
            result = {'status': status, 'eventtime': self.eventtime}
        elif "configfile" in request.url.query.decode():
            result = {"status": {"configfile": {"config": self.config}}}
        else:
            result = {"status": {"webhooks": {"state": "ready" if self.ready else "shutdown"},
                                 "print_stats": {"state": self.state}, "virtual_sdcard": {"progress": 0.63},
                                 "extruder": {"temperature": 23.0}, "heater_bed": {"temperature": 21.0}}}
        return httpx.Response(200, json={"result": result})


@pytest.fixture
def rig(tmp_path):
    store = Store(tmp_path / "settings.sqlite")
    printer = Printer(id="sim", name="Test Printer", url="http://127.0.0.1:7125", approved=True)
    store.save_printer(printer)
    store.set("selected", printer.id)
    sim = Simulator()
    transport = httpx.MockTransport(sim.handle)
    def factory(p):
        return Moonraker(p, transport=transport)
    clock = [100.0]
    engine = SafetyEngine(store, factory, clock=lambda: clock[0])
    yield store, sim, engine, clock
    store.close()
