"""Fully synthetic active Klipper data and packaged read-only motion qualification."""
import copy
import tempfile
import time
from pathlib import Path

import httpx

from .domain import Action, Intent, Printer
from .moonraker import Moonraker
from .motion import parse_motion
from .safety import Rejected, SafetyEngine
from .storage import Store


def synthetic_settings(kinematics='cartesian'):
    return {
        'printer': {'kinematics': kinematics, 'max_velocity': 300, 'max_accel': 3000,
                    'max_z_velocity': 15, 'max_z_accel': 100},
        **{'stepper_' + axis: {'position_min': -10, 'position_max': 300} for axis in 'xyz'},
        'extruder': {'min_temp': 0, 'max_temp': 250, 'min_extrude_temp': 170,
                     'max_extrude_only_distance': 50, 'max_extrude_only_velocity': 25,
                     'max_extrude_only_accel': 500, 'max_extrude_cross_section': 0.64,
                     'nozzle_diameter': 0.4, 'filament_diameter': 1.75},
        'heater_bed': {'min_temp': 0, 'max_temp': 110},
    }


def synthetic_status(settings=None):
    position = [100.0, 100.0, 20.0, 0.0]
    return {'configfile': {'settings': settings or synthetic_settings()},
            'webhooks': {'state': 'ready'}, 'print_stats': {'state': 'standby'},
            'extruder': {'temperature': 23.0, 'can_extrude': False},
            'heater_bed': {'temperature': 21.0},
            'toolhead': {'position': position.copy(), 'homed_axes': 'xyz',
                         'axis_minimum': [-10, -10, -10, 0], 'axis_maximum': [300, 300, 300, 0],
                         'max_velocity': 300, 'max_accel': 3000, 'extruder': 'extruder', 'extra_axes': {'extruder': 3}},
            'gcode_move': {'position': position.copy(), 'gcode_position': position.copy(),
                           'homing_origin': [0, 0, 0, 0], 'absolute_coordinates': True,
                           'absolute_extrude': False, 'speed': 50, 'speed_factor': 1,
                           'extrude_factor': 1, 'axis_map': {'X': 0, 'Y': 1, 'Z': 2, 'E': 3}},
            'motion_report': {'live_position': position.copy(), 'live_velocity': 0, 'live_extruder_velocity': 0}}


async def run():
    """No physical services and every POST forbidden, including valid-move cases."""
    status = synthetic_status()
    eventtime, writes, cases = 0, [], []
    def handle(request):
        nonlocal eventtime
        if request.method != 'GET':
            writes.append(request.url.path)
            raise AssertionError('Limits qualification forbids every printer write')
        if request.url.path.endswith('/list'):
            result = {'objects': list(status)}
        else:
            eventtime += 1
            result = {'status': copy.deepcopy(status), 'eventtime': eventtime}
        return httpx.Response(200, json={'result': result})
    with tempfile.TemporaryDirectory(prefix='klippy-limits-probe-') as root:
        store = Store(Path(root) / 'settings.sqlite')
        try:
            printer = Printer(id='sim', name='Synthetic printer', url='http://127.0.0.1:1', approved=True)
            store.save_printer(printer)
            store.set('selected', printer.id)
            engine = SafetyEngine(store, lambda p: Moonraker(p, transport=httpx.MockTransport(handle)))
            for phrase in ('Move X minus 20 millimeters.', 'Go to X 150.', 'Raise Z by 10.'):
                began = time.perf_counter()
                review = await engine.propose(parse_motion(phrase, printer.id))
                cases.append({'case': phrase, 'proposal_ms':round((time.perf_counter()-began)*1000,3),
                              'passed': engine.pending is not None and 'machine' in review and printer.name in review})
                engine.cancel()
            for phrase in ('Move X minus 200 millimeters.', 'Go to X 301.', 'Move X 20 at 400 mm/s', 'Move the bed forward 20 millimeters.'):
                blocked = False
                try:
                    await engine.propose(parse_motion(phrase, printer.id))
                except (Rejected, ValueError):
                    blocked = True
                except Exception as exc:
                    from .limits import LimitsUnavailable
                    if not isinstance(exc, LimitsUnavailable):
                        raise
                    blocked = True
                cases.append({'case': phrase, 'passed': blocked and engine.pending is None})
            await engine.propose(parse_motion('move X 10', printer.id))
            token = engine.pending.token
            status['configfile']['settings']['stepper_x']['position_max'] = 200
            blocked = False
            try:
                await engine.confirm(token)
            except Rejected:
                blocked = True
            cases.append({'case': 'changed configuration invalidates confirmation', 'passed': blocked and engine.pending is None})
            del status['gcode_move']['axis_map']
            try:
                await engine.propose(parse_motion('move X 10', printer.id))
                missing_blocked = False
            except Rejected:
                missing_blocked = engine.pending is None
            cases.append({'case': 'absent axis mapping blocks review', 'passed': missing_blocked})
            store.set('heater_limits', {printer.id: {'0': 80}})
            backup = Path(root) / 'synthetic-backup.json'
            store.export(backup)
            store.restore(backup)
            store.save_printer(printer)
            engine.select(printer.id)
            target = Intent(action=Action.HEAT, printer_id=printer.id, params={'heater': 0, 'temperature': 90})
            try:
                await engine.propose(target)
                recovery_blocked = False
            except Rejected as exc:
                recovery_blocked = 'restored limits' in str(exc) and engine.pending is None
            record = await engine.limits.refresh(printer)
            engine.limits.save_review(printer, record, {}, {'0': 80})
            try:
                await engine.propose(target)
                cap_preserved = False
            except Rejected as exc:
                cap_preserved = 'outside' in str(exc) and engine.pending is None
            cases.append({'case': 'restore requires device limits review and respects prior heater cap',
                          'passed': recovery_blocked and cap_preserved})
            return {'scope': 'Synthetic configuration and motion; every HTTP write forbidden', 'cases': cases,
                    'printer_writes': len(writes), 'passed': all(row['passed'] for row in cases) and not writes and engine.pending is None}
        finally:
            store.close()
