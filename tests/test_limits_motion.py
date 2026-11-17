import asyncio
import copy
import json

import httpx
import pytest

from klippy.conversation import Conversation
from klippy.domain import Action, Intent, Printer
from klippy.limits import LimitsUnavailable, discover, validate_overrides
from klippy.limits_probe import run, synthetic_settings, synthetic_status
from klippy.moonraker import Moonraker
from klippy.motion import parse_motion
from klippy.safety import Rejected, SafetyEngine
from klippy.storage import Store


@pytest.fixture
def motion_rig(tmp_path):
    store = Store(tmp_path / 'motion.sqlite')
    printer = Printer(id='sim', name='Mercury One', aliases=('M1',), url='http://127.0.0.1:1', approved=True)
    store.save_printer(printer)
    store.set('selected', printer.id)
    data = {'status': synthetic_status(), 'eventtime': 1, 'writes': [], 'freeze': False,
            'timeout': False, 'read_delay': 0, 'clock': 100.0, 'reads': []}
    def handle(request):
        data['reads'].append((request.method, request.url.path))
        if request.method != 'GET':
            data['writes'].append(json.loads(request.content)['script'])
            if data['timeout']:
                raise httpx.ReadTimeout('synthetic uncertain write', request=request)
            return httpx.Response(200, json={'result': 'ok'})
        if request.url.path.endswith('/list'):
            result = {'objects': list(data['status'])}
        else:
            if not data['freeze']:
                data['eventtime'] += 1
            data['clock'] += data['read_delay']
            result = {'status': copy.deepcopy(data['status']), 'eventtime': data['eventtime']}
        return httpx.Response(200, json={'result': result})
    transport = httpx.MockTransport(handle)
    engine = SafetyEngine(store, lambda p: Moonraker(p, transport=transport), clock=lambda: data['clock'])
    yield store, data, engine, printer
    store.close()


def move(phrase='move X 20'):
    return parse_motion(phrase, 'sim')


@pytest.mark.parametrize('phrase,axis,value,relative', [
    ('Move X minus 200 millimeters.', 0, -200, 1),
    ('Go to X 150.', 0, 150, 0), ('Raise Z by 10.', 2, 10, 1),
    ('lower Z by five', 2, -5, 1), ('Can you move Y to -5 mm?', 1, -5, 0),
    ('please jog X negative twenty', 0, -20, 1), ('set the Y axis 150', 1, 150, 0),
])
def test_deterministic_motion_semantics(phrase, axis, value, relative):
    assert move(phrase).params == {'axis': axis, 'value': value, 'relative': relative}


@pytest.mark.parametrize('phrase', [
    'Move the bed forward 20 millimeters.', 'move left 20', 'move X 20 and Y 20',
    'raise X by 10', 'lower Z by -10', 'go to X by 10', 'extrude 10', 'retract 5',
    'move X 20 G28', 'move X 1e5', 'move X nan', 'move X 2 inches',
])
def test_ambiguous_or_unsupported_motion_needs_clarification(phrase):
    with pytest.raises(LimitsUnavailable):
        move(phrase)


async def test_valid_relative_absolute_and_negative_positions(motion_rig):
    _, data, engine, _ = motion_rig
    for count, (phrase, destination) in enumerate([('move X -110', '-10'), ('go to X 150', '150'), ('raise Z 10', '30')]):
        review = await engine.propose(move(phrase))
        assert 'Mercury One' in review and f'to {destination} mm' in review and 'path are clear' in review
        assert len(data['writes']) == count
        await engine.confirm(engine.pending.token)
    assert len(data['writes']) == 3
    assert all('M400\nRESTORE_GCODE_STATE' in script and 'MOVE=1' not in script for script in data['writes'])


@pytest.mark.parametrize('phrase', ['move X -111', 'move X 201', 'go to X -11', 'go to X 301', 'move X 0', 'move X 20 at 301 mm/s', 'raise Z 10 at 16 mm/s'])
async def test_reject_boundaries_and_explicit_speed_without_clamping(motion_rig, phrase):
    _, data, engine, _ = motion_rig
    with pytest.raises(Rejected):
        await engine.propose(move(phrase))
    assert not data['writes'] and engine.pending is None


async def test_coordinate_offsets_and_relative_parser_modes_restored(motion_rig):
    _, data, engine, _ = motion_rig
    state = data['status']['gcode_move']
    state.update(gcode_position=[90, 80, 15, 0], homing_origin=[4, 3, 2, 0], absolute_coordinates=False, absolute_extrude=True)
    review = await engine.propose(move('go to X 150'))
    assert 'machine X 100 to 150' in review and 'G-code X 140' in review
    await engine.confirm(engine.pending.token)
    script = data['writes'][0]
    assert '\nG90\nG1 X140 F600\nM400\n' in script
    assert script.startswith('SAVE_GCODE_STATE NAME=KLIPPY_SAFE_')
    assert script.splitlines()[0].split('NAME=')[1] == script.splitlines()[-1].split('NAME=')[1]
    assert ' E' not in script and 'G28' not in script


@pytest.mark.parametrize('object_name,field,value', [
    ('toolhead', 'homed_axes', ''), ('toolhead', 'homed_axes', 'xy'),
    ('toolhead', 'homed_axes', 'xyzx'), ('toolhead', 'position', [float('nan'), 0, 0]),
    ('toolhead', 'position', [100, 100]), ('toolhead', 'axis_maximum', None),
    ('toolhead', 'max_velocity', 500), ('toolhead', 'max_accel', 5000),
    ('toolhead', 'extra_axes', ['A']), ('gcode_move', 'absolute_coordinates', 1),
    ('gcode_move', 'absolute_extrude', None), ('gcode_move', 'speed_factor', 0.5),
    ('gcode_move', 'position', [99, 100, 20, 0]),
    ('gcode_move', 'axis_map', {'X': 1, 'Y': 0, 'Z': 2, 'E': 3}),
    ('motion_report', 'live_position', [90, 100, 20, 0]),
    ('motion_report', 'live_velocity', 1), ('motion_report', 'live_extruder_velocity', 1),
    ('motion_report', 'live_velocity', None), ('print_stats', 'state', 'printing'),
    ('print_stats', 'state', 'paused'),
])
async def test_unknown_or_unsafe_motion_state_blocks(motion_rig, object_name, field, value):
    _, data, engine, _ = motion_rig
    # JSON itself forbids NaN: malformed HTTP payloads must fail safely too.
    if isinstance(value, list) and any(isinstance(v, float) and v != v for v in value):
        value = ['nan', 0, 0]
    data['status'][object_name][field] = value
    with pytest.raises(Rejected):
        await engine.propose(move())
    assert not data['writes']


@pytest.mark.parametrize('section,key,value', [
    ('stepper_x', 'position_min', None), ('stepper_x', 'position_max', -11),
    ('stepper_y', 'position_max', '300'), ('printer', 'max_velocity', 0),
    ('printer', 'max_accel', None), ('printer', 'max_z_velocity', None),
    ('printer', 'max_z_accel', 0),
])
async def test_invalid_active_limits_block(motion_rig, section, key, value):
    _, data, engine, _ = motion_rig
    data['status']['configfile']['settings'][section][key] = value
    with pytest.raises(Rejected):
        await engine.propose(move('raise Z by 10'))
    assert not data['writes']


@pytest.mark.parametrize('kinematics,allowed', [('corexy', True), ('cartesian', True), ('delta', False), ('polar', False), ('corexz', False), ('generic_cartesian', False), ('unknown', False)])
async def test_actual_kinematics_scope(motion_rig, kinematics, allowed):
    _, data, engine, printer = motion_rig
    data['status']['configfile']['settings']['printer']['kinematics'] = kinematics
    record = await engine.limits.refresh(printer)
    assert record.capabilities['kinematics'] == kinematics
    if allowed:
        await engine.propose(move())
    else:
        assert not record.capabilities['axes']
        with pytest.raises(Rejected, match='kinematics'):
            await engine.propose(move())
    assert not data['writes']


@pytest.mark.parametrize('feature', ['bed_tilt', 'skew_correction', 'axis_twist_compensation', 'z_thermal_adjust', 'dual_carriage', 'extra_axis a', 'gcode_macro G1', 'gcode_macro RESTORE_GCODE_STATE'])
async def test_unsupported_transforms_and_shadowed_commands(motion_rig, feature):
    _, data, engine, _ = motion_rig
    data['status']['configfile']['settings'][feature] = {}
    with pytest.raises(Rejected):
        await engine.propose(move())
    assert not data['writes']


async def test_active_and_unknown_mesh_block_unloaded_mesh_supported(motion_rig):
    _, data, engine, _ = motion_rig
    data['status']['configfile']['settings']['bed_mesh'] = {}
    with pytest.raises(Rejected):
        await engine.propose(move())
    data['status']['bed_mesh'] = {'profile_name': 'default', 'mesh_matrix': [[0.1]]}
    with pytest.raises(Rejected):
        await engine.propose(move())
    data['status']['bed_mesh'] = {'profile_name': '', 'mesh_matrix': []}
    await engine.propose(move())
    assert engine.pending and not data['writes']


@pytest.mark.parametrize('change', ['position', 'mode', 'origin', 'config', 'owner', 'speed', 'homed', 'restart', 'selection'])
async def test_confirmation_invalidated_by_changed_facts(motion_rig, change):
    store, data, engine, printer = motion_rig
    await engine.propose(move())
    token = engine.pending.token
    if change == 'position':
        for obj, key in [('toolhead', 'position'), ('gcode_move', 'position'), ('gcode_move', 'gcode_position'), ('motion_report', 'live_position')]:
            data['status'][obj][key][0] = 101
    elif change == 'mode':
        data['status']['gcode_move']['absolute_coordinates'] = False
    elif change == 'origin':
        data['status']['gcode_move']['homing_origin'][0] = 1
    elif change == 'config':
        data['status']['configfile']['settings']['stepper_x']['position_max'] = 250
    elif change == 'owner':
        store.set('printer_limit_overrides', {'sim': {'axes': {'x': {'position_max': 250}}}})
    elif change == 'speed':
        data['status']['toolhead']['max_velocity'] = 200
    elif change == 'homed':
        data['status']['toolhead']['homed_axes'] = 'xy'
    elif change == 'restart':
        engine.limits.notification('sim', {'method': 'notify_klippy_ready'})
        assert engine.pending is None
    else:
        store.save_printer(printer.model_copy(update={'id': 'other', 'name': 'Other'}))
        engine.select('other')
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert not data['writes'] and engine.pending is None


async def test_mandatory_confirmation_single_use_uncertain_write_no_retry(motion_rig):
    store, data, engine, _ = motion_rig
    store.set('confirmations', {'move': False})
    await engine.propose(move())
    assert not data['writes']
    token = engine.pending.token
    data['timeout'] = True
    assert 'will not retry' in await engine.confirm(token)
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert len(data['writes']) == 1


async def test_stale_slow_and_replayed_snapshots(motion_rig):
    _, data, engine, printer = motion_rig
    await engine.propose(move())
    token = engine.pending.token
    data['freeze'] = True
    with pytest.raises(Rejected, match='stale'):
        await engine.confirm(token)
    # Invalidating the cached record cannot erase the replay watermark.
    with pytest.raises(Rejected, match='stale'):
        await engine.propose(move())
    data['freeze'] = False
    data['read_delay'] = 3
    with pytest.raises(Rejected, match='too long'):
        await engine.propose(move())
    assert not data['writes'] and printer.id not in engine.limits.records


@pytest.mark.parametrize('overrides', [
    {'axes': {'x': {'position_min': -11}}}, {'axes': {'x': {'position_max': 301}}},
    {'axes': {'a': {}}}, {'motion': {'max_velocity': 301}}, {'motion': {'invalid': 1}},
    {'motion': {'max_accel': True}}, {'heaters': {'extruder': {'max_temp': 251}}},
    {'extrusion': {'extruder': {'min_extrude_temp': 169}}},
    {'extrusion': {'extruder': {'max_extrude_only_distance': 51}}},
    {'heaters': {'unknown': {}}}, {'axes': {'x': {'position_min': 299, 'position_max': 298}}},
])
def test_owner_overrides_cannot_expand_or_invent_limits(overrides):
    with pytest.raises(LimitsUnavailable):
        validate_overrides(overrides, discover(synthetic_settings(), list(synthetic_status())))


async def test_stricter_owner_limits_and_z_acceleration(motion_rig):
    store, data, engine, _ = motion_rig
    store.set('printer_limit_overrides', {'sim': {'axes': {'x': {'position_max': 110}}, 'motion': {'max_z_accel': 50}}})
    with pytest.raises(Rejected):
        await engine.propose(move())
    with pytest.raises(Rejected, match='Z acceleration'):
        await engine.propose(move('raise Z 10'))
    data['status']['toolhead']['max_accel'] = 40
    await engine.propose(move('raise Z 10'))
    assert not data['writes']


async def test_limits_are_individual_per_printer(motion_rig):
    store, data, engine, printer = motion_rig
    first = await engine.limits.refresh(printer)
    second_printer = printer.model_copy(update={'id': 'other', 'name': 'Other', 'url': 'http://127.0.0.1:2'})
    store.save_printer(second_printer)
    data['status']['configfile']['settings']['stepper_x']['position_max'] = 150
    second = await engine.limits.refresh(second_printer)
    assert first.capabilities['axes']['x']['position_max'] == 300
    assert second.capabilities['axes']['x']['position_max'] == 150
    assert len(engine.limits.records) == 2


@pytest.mark.parametrize('message', [
    {'method': 'notify_klippy_shutdown'}, {'method': 'notify_klippy_disconnected'},
    {'method': 'notify_status_update', 'params': [{'configfile': {'settings': {}}}]},
    {'method': 'notify_status_update', 'params': [{'toolhead': {'position': [101, 100, 20, 0]}}]},
    {'method': 'notify_status_update', 'params': [{'webhooks': None}]},
])
async def test_notifications_revoke_but_never_execute(motion_rig, message):
    _, data, engine, _ = motion_rig
    await engine.propose(move())
    engine.limits.notification('sim', message)
    assert engine.pending is None and not data['writes'] and not engine.limits.records


async def test_invalidation_during_discovery_cannot_restore_permission(motion_rig):
    _, data, engine, printer = motion_rig
    client = engine.clients(printer)
    original = client.request
    async def request(method, path, payload=None):
        value = await original(method, path, payload)
        if path.startswith('/printer/objects/query') and 'configfile=' in path:
            engine.limits.invalidate('sim')
        return value
    client.request = request
    engine.clients = engine.limits.clients = lambda p: client
    with pytest.raises(Rejected):
        await engine.propose(move())
    assert not data['writes'] and not engine.limits.records


async def test_conversation_aliases_and_model_cannot_choose_moves(motion_rig):
    _, data, engine, _ = motion_rig
    class Model:
        async def interpret(self, *args):
            return move()
    c = Conversation(engine, Model())
    assert 'Mercury One' in await c.hear('Hey Klippy, move M1 X minus 20 millimeters')
    assert engine.pending
    engine.cancel()
    with pytest.raises(Rejected, match='model cannot authorize'):
        await c.hear('shift the carriage a little')
    assert not data['writes']


async def test_discovery_has_no_write_authority_or_private_config_export(motion_rig):
    _, data, engine, printer = motion_rig
    data['status']['configfile']['settings']['gcode_macro PRIVATE'] = {'gcode': 'PRIVATE SECRET'}
    await engine.limits.refresh(printer)
    exported = json.dumps(engine.limits.describe(printer.id))
    assert 'PRIVATE SECRET' not in exported and printer.url not in exported
    assert not data['writes'] and all(method == 'GET' for method, _ in data['reads'])


async def test_packaged_limits_probe_is_strictly_read_only():
    report = await run()
    assert report['passed'] and report['printer_writes'] == 0 and len(report['cases']) == 8


@pytest.mark.parametrize('phrase', ['move M1 X minus 20', 'move X minus 20 on M1', 'go to X 150 for Mercury One'])
async def test_named_motion_and_axis_alias_collisions(motion_rig, phrase):
    store, data, engine, printer = motion_rig
    store.save_printer(printer.model_copy(update={'id':'axis', 'name':'X', 'aliases':()}))
    answer = await Conversation(engine).hear(phrase)
    assert 'Mercury One' in answer and store.get('selected') == 'sim'
    assert not data['writes']


async def test_complete_motion_does_not_select_printer_named_axis(motion_rig):
    store, data, engine, printer = motion_rig
    store.save_printer(printer.model_copy(update={'id':'axis', 'name':'X', 'aliases':()}))
    await Conversation(engine).hear('move X 10')
    assert store.get('selected') == 'sim' and not data['writes']


@pytest.mark.parametrize('alteration', ['missing_heater', 'other_extruder', 'shadowed_command', 'minimum', 'owner_cap', 'missing_state'])
async def test_heating_uses_verified_active_configuration(motion_rig, alteration):
    store, data, engine, _ = motion_rig
    settings = data['status']['configfile']['settings']
    if alteration == 'missing_heater':
        settings.pop('extruder')
    elif alteration == 'other_extruder':
        data['status']['toolhead']['extruder'] = 'extruder1'
    elif alteration == 'shadowed_command':
        settings['gcode_macro M104'] = {'gcode':'CUSTOM'}
    elif alteration == 'minimum':
        settings['extruder']['min_temp'] = 100
    elif alteration == 'owner_cap':
        store.set('heater_limits', {'sim':{'0':80}})
    else:
        data['status'].pop('print_stats')
    with pytest.raises(Rejected):
        await engine.propose(Intent(action=Action.HEAT,printer_id='sim',params={'heater':0,'temperature':90}))
    assert not data['writes']


async def test_heat_works_with_firmware_limits_without_manual_caps(motion_rig):
    _, data, engine, _ = motion_rig
    await engine.propose(Intent(action=Action.HEAT,printer_id='sim',params={'heater':0,'temperature':90}))
    token = engine.pending.token
    data['status']['configfile']['settings']['extruder']['max_temp'] = 200
    with pytest.raises(Rejected):
        await engine.confirm(token)
    assert not data['writes']


async def test_subscription_reconnect_revokes_pending_without_any_write(motion_rig):
    _, data, engine, printer = motion_rig
    queue, subscribed = asyncio.Queue(), asyncio.Event()
    original = engine.clients(printer)
    class ReadOnlyNotifications:
        transport = None
        request = original.request
        async def notifications(self, objects=None):
            assert objects['configfile'] == ['settings']
            subscribed.set()
            while True:
                yield await queue.get()
    engine.limits.clients = lambda p: ReadOnlyNotifications()
    engine.limits.watch(printer)
    task = engine.limits.watchers[printer.id][1]
    try:
        await asyncio.wait_for(subscribed.wait(), 1)
        await engine.propose(move())
        await queue.put({'method':'notify_klippy_shutdown'})
        await asyncio.sleep(0)
        assert engine.pending is None and not data['writes']
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def test_injected_transport_cannot_start_network_subscription(motion_rig):
    _, data, engine, printer = motion_rig
    engine.limits.watch(printer)
    assert not engine.limits.watchers and not data['reads']


@pytest.mark.parametrize('defect', ['missing','summary','write','case','count'])
def test_limits_qualification_cannot_be_skipped(defect):
    from pathlib import Path

    from klippy.voice_probe import qualify_preview_report
    report = json.loads((Path(__file__).parents[1] / 'benchmarks/preview72-release-frozen.json').read_text())
    limits = {'passed':True,'printer_writes':0,'cases':[{'passed':True} for _ in range(8)]}
    report['limits_probe'] = limits
    qualify_preview_report(report)
    assert report['engineering_preview_passed']
    if defect == 'missing':
        report.pop('limits_probe')
    elif defect == 'summary':
        limits['passed'] = False
    elif defect == 'write':
        limits['printer_writes'] = 1
    elif defect == 'case':
        limits['cases'][0]['passed'] = False
    else:
        limits['cases'].pop()
    qualify_preview_report(report)
    assert not report['engineering_preview_passed']


@pytest.mark.parametrize('change', ['disconnect', 'configuration'])
async def test_monitor_discovery_and_reconnection_revoke_reviews(motion_rig, change):
    store, data, engine, _ = motion_rig
    from klippy.monitor import Monitor
    monitor = Monitor(store, engine.clients, limits=engine.limits)
    await monitor.poll()
    assert engine.limits.records
    await engine.propose(move())
    if change == 'disconnect':
        data['status']['webhooks']['state'] = 'shutdown'
    else:
        monitor.cycles = 11
        data['status']['configfile']['settings']['printer']['max_velocity'] = 250
    await monitor.poll()
    assert engine.pending is None and not data['writes']
