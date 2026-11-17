"""Narrow, deterministic single-axis motion semantics and independent bounds validation."""
import re
import secrets
from dataclasses import dataclass
from decimal import Decimal

from .domain import Action, Intent, digest
from .language import normalize
from .limits import BLOCKED_FEATURES, LimitsUnavailable, number, vector


def motion_request(text):
    return bool(re.match(r"^(?:(?:please|can you|could you|would you|will you) )*(?:move|jog|raise|lower|go to|extrude|retract|set (?:the )?[xyz]\b)", normalize(text)))


def parse_motion(text, printer_id):
    if not motion_request(text):
        return None
    text = normalize(text)
    text = re.sub(r'\b(?:minus|negative)\s+(?=\d|\.)', '-', text)
    prefix = r"(?:(?:please|can you|could you|would you|will you) )*"
    numeric = r"[+-]?(?:\d+(?:\.\d{1,6})?|\.\d{1,6})"
    unit = r"(?: (?:mm|millimeters?|millimetres?))?"
    speed = r"(?: at (?P<speed>" + numeric + r") (?:mm/s|mm per second|millimeters? per second|millimetres? per second))?"
    match = re.fullmatch(prefix + r"(?P<verb>move|jog|raise|lower|go to|set) (?:the )?(?P<axis>[xyz])(?: axis)? (?:(?P<mode>by|to) )?(?P<value>" + numeric + r")" + unit + speed + r"(?: please)?", text)
    if match is None:
        raise LimitsUnavailable("Please specify one axis and a signed distance, such as 'move X minus 20 millimeters', or an absolute position, such as 'go to X 150'. Bed and physical directions are ambiguous.")
    verb, axis, mode, value = match['verb'], match['axis'], match['mode'], Decimal(match['value'])
    if verb in {'raise', 'lower'} and (axis != 'z' or value < 0 or mode == 'to'):
        raise LimitsUnavailable("Use 'raise Z by 10' or 'lower Z by 10', with a positive distance.")
    if verb in {'go to', 'set'} and mode == 'by' or verb in {'raise', 'lower'} and mode == 'to':
        raise LimitsUnavailable("Please state either a relative distance or an absolute destination.")
    relative = verb not in {'go to', 'set'} and mode != 'to'
    if verb == 'lower':
        value = -value
    params = {'axis': 'xyz'.index(axis), 'value': float(value), 'relative': int(relative)}
    if match['speed'] is not None:
        params['speed'] = float(match['speed'])
    return Intent(action=Action.MOVE, printer_id=printer_id, params=params)


def decimal(value):
    if number(value) is None:
        raise LimitsUnavailable("A required motion limit or state value is missing or invalid.")
    return Decimal(str(value))


def text(value):
    result = format(value, 'f')
    return result.rstrip('0').rstrip('.') if '.' in result else result


@dataclass(frozen=True)
class MotionPlan:
    script: str
    review: str
    binding: dict


def plan_move(intent, record, caps, owner_policy):
    params, status = intent.params, record.status
    if status.get('print_stats', {}).get('state') not in {'standby', 'complete', 'cancelled'}:
        raise LimitsUnavailable("The printer must be idle before a direct voice move.")
    if set(params) - {'axis', 'value', 'relative', 'speed'} or not {'axis', 'value', 'relative'} <= set(params):
        raise LimitsUnavailable("A movement needs one axis, a distance or position, and relative/absolute mode.")
    if type(params['axis']) is not int or params['axis'] not in (0, 1, 2) or type(params['relative']) is not int or params['relative'] not in (0, 1):
        raise LimitsUnavailable("The movement axis or coordinate mode is invalid.")
    if caps['kinematics'] not in {'cartesian', 'corexy'}:
        raise LimitsUnavailable("Direct voice movement is unsupported for this printer's kinematics. Its limits are not a rectangular XYZ travel envelope.")
    if caps['shadowed_commands']:
        raise LimitsUnavailable("A configured macro overrides a motion or state-restoration command; direct movement is blocked.")
    if set(caps['features']) & BLOCKED_FEATURES:
        raise LimitsUnavailable("This printer has a motion transform or carriage feature that direct voice movement cannot verify.")
    mesh = status.get('bed_mesh')
    if 'bed_mesh' in caps['features'] or mesh is not None:
        if not isinstance(mesh, dict) or mesh.get('mesh_matrix') != [] or mesh.get('profile_name') != '':
            raise LimitsUnavailable("Disable the active bed-mesh transform through supervised printer controls before direct voice movement.")
    tool, move, live = (status.get(k, {}) for k in ('toolhead', 'gcode_move', 'motion_report'))
    if not all(isinstance(x, dict) for x in (tool, move, live)):
        raise LimitsUnavailable("Current motion state is unavailable.")
    homed = tool.get('homed_axes')
    if not isinstance(homed, str) or sorted(homed) != ['x', 'y', 'z']:
        raise LimitsUnavailable("Home all three axes before a direct voice move. I won't home or move them automatically.")
    start = vector(tool.get('position'))
    mapped, gcode, origin = (vector(move.get(k)) for k in ('position', 'gcode_position', 'homing_origin'))
    actual = vector(live.get('live_position'))
    if any(abs(decimal(a)-decimal(b)) > Decimal('0.000001') for a,b in zip(start,mapped)) or any(abs(decimal(a)-decimal(b)) > Decimal('0.000001') for a,b in zip(start,actual)):
        raise LimitsUnavailable("Reported coordinate systems or queued motion do not agree; wait until the printer is stationary.")
    if decimal(live.get('live_velocity')) != 0 or decimal(live.get('live_extruder_velocity')) != 0:
        raise LimitsUnavailable("The printer is already moving or extruding. Wait until it is stationary.")
    if type(move.get('absolute_coordinates')) is not bool or type(move.get('absolute_extrude')) is not bool:
        raise LimitsUnavailable("The printer's coordinate modes are unknown.")
    if decimal(move.get('speed_factor')) != 1:
        raise LimitsUnavailable("Direct voice movement requires a verified 100 percent speed override. Change it through supervised printer controls.")
    if tool.get('extra_axes') not in (None, []) or move.get('axis_map', {'X':0,'Y':1,'Z':2,'E':3}) != {'X':0,'Y':1,'Z':2,'E':3}:
        raise LimitsUnavailable("Extra or remapped motion axes are unsupported for direct voice movement.")
    index, relative = params['axis'], params['relative'] == 1
    value = decimal(params['value'])
    destination = list(map(decimal,start))
    destination[index] = destination[index] + value if relative else value
    if destination[index] == decimal(start[index]):
        raise LimitsUnavailable("That request would not change the axis position.")
    runtime_min, runtime_max = vector(tool.get('axis_minimum')), vector(tool.get('axis_maximum'))
    ranges = []
    for i, axis in enumerate('xyz'):
        configured = caps['axes'].get(axis, {})
        low, high = decimal(configured.get('position_min')), decimal(configured.get('position_max'))
        low, high = max(low, decimal(runtime_min[i])), min(high, decimal(runtime_max[i]))
        if low >= high:
            raise LimitsUnavailable("The configured and current axis limits are invalid or inconsistent.")
        if not low <= decimal(start[i]) <= high:
            raise LimitsUnavailable("The current commanded position is outside its verified range; direct movement is blocked.")
        if not low <= destination[i] <= high:
            raise LimitsUnavailable(f"That would put {axis.upper()} at {text(destination[i])} mm outside its allowed range of {text(low)} to {text(high)} mm, so I won't move it.")
        ranges.append((str(low),str(high)))
    configured = caps['motion']
    velocity, accel = decimal(configured.get('max_velocity')), decimal(configured.get('max_accel'))
    current_velocity, current_accel = decimal(tool.get('max_velocity')), decimal(tool.get('max_accel'))
    if min(velocity, accel, current_velocity, current_accel) <= 0 or current_velocity > velocity or current_accel > accel:
        raise LimitsUnavailable("Current velocity or acceleration exceeds verified configuration/owner limits, or is invalid.")
    # Klipper independently enforces the Z-specific acceleration even when the
    # global toolhead acceleration is greater. We neither modify nor expand it.
    effective_accel = current_accel
    if index == 2:
        z_velocity, z_accel = decimal(configured.get('max_z_velocity')), decimal(configured.get('max_z_accel'))
        if min(z_velocity,z_accel) <= 0:
            raise LimitsUnavailable("Z-specific motion limits are unavailable.")
        firmware_z_accel = decimal(record.capabilities['motion'].get('max_z_accel'))
        effective_accel = min(current_accel,firmware_z_accel)
        if effective_accel > z_accel:
            raise LimitsUnavailable("Current Z acceleration exceeds the owner's stricter limit. Adjust it through supervised printer controls.")
        velocity = min(velocity,z_velocity)
    speed = decimal(params['speed']) if 'speed' in params else min(Decimal(10),velocity,current_velocity)
    if speed <= 0 or speed > min(velocity,current_velocity):
        raise LimitsUnavailable("The requested movement speed is outside the configured/current safe limit. I won't reduce it silently.")
    delta = destination[index]-decimal(start[index])
    command_position = decimal(gcode[index])+delta
    axis = 'XYZ'[index]
    state_name = 'KLIPPY_SAFE_' + secrets.token_hex(8).upper()
    script = f'SAVE_GCODE_STATE NAME={state_name}\nG90\nG1 {axis}{text(command_position)} F{text(speed*60)}\nM400\nRESTORE_GCODE_STATE NAME={state_name}'
    review = f"move {axis} by {text(delta)} mm, from machine {axis} {text(decimal(start[index]))} to {text(destination[index])} mm (G-code {axis} {text(command_position)}), at {text(speed)} mm/s (acceleration limit {text(effective_accel)} mm/s squared)"
    binding = {'configuration':record.fingerprint,'generation':record.generation,'position':start,'gcode_position':gcode,'origin':origin,
               'coordinate_modes':[move['absolute_coordinates'],move['absolute_extrude']], 'axis_map':move.get('axis_map'),
               'homed_axes':homed,'destination':[str(v) for v in destination],'ranges':ranges,
               'runtime_limits':[str(current_velocity),str(current_accel)],'speed':str(speed),'accel':str(effective_accel),
               'owner_policy':digest(owner_policy),'features':caps['features'],'speed_factor':move['speed_factor']}
    return MotionPlan(script,review,binding)
