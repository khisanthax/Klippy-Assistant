# Printer capability and safety limits registry

The 0.8 engineering preview discovers active limits separately for every approved printer.
Discovery uses only documented `GET /printer/objects/list` and selected fields through
`GET /printer/objects/query`. No printer configuration is modified. Raw configuration,
connection addresses and credentials are not exported by the capability viewer or persisted
in this registry. A configuration fingerprint and sanitized numeric capabilities remain in
memory; each process starts without motion authority.

## Discovered information

| Source | Fields and interpretation |
|---|---|
| `configfile.settings.extruder[N]`, `heater_bed` | Available heater min/max; extrusion minimum temperature, maximum extrusion-only distance/velocity/acceleration/cross-section, nozzle/filament diameters where reported |
| `configfile.settings.printer` | Kinematics, configured velocity/acceleration, Z-specific limits, available native geometry and optional motion features |
| `stepper_x/y/z` | Position bounds for supported Cartesian/CoreXY layouts only |
| Delta printer/tower settings | Native radius, minimum Z, print radius and available tower angles, arm lengths and endstops; never reinterpreted as rectangular XYZ bounds |
| `toolhead` | Homed axes, last commanded machine position, current axis bounds, runtime velocity/acceleration, active extruder and extra axes |
| `gcode_move` | Commanded machine/G-code positions, homing origin, coordinate/extrusion modes, axis mapping, speed override |
| `motion_report` | Interpolated live position and velocities; used to reject outstanding motion, not represented as encoder feedback |
| `webhooks`, `print_stats` | Ready and idle/job state required by the requested operation |
| `bed_mesh` | Loaded/unloaded transform state where exposed |

Absent values remain unknown. The registry does not infer unsupported components, fabricate
defaults or infer rectangular bounds for other kinematics. Extrusion restrictions are
discovered and inspectable; direct voice extrusion/retraction is **unsupported**.

Klipper describes `settings` as values used at the last startup, including consumed defaults;
runtime `SET_VELOCITY_LIMIT` changes are separate. Both configured and current toolhead caps
must pass validation. Missing Z-specific limits block Z moves rather than inventing a value.

## Direct movement envelope

Supported examples: `Move X minus 20 millimeters`, `Go to X 150`, `Raise Z by 10`,
`move X 20 on M1`, and `move X 20 at 5 mm/s`. Printer names/aliases, number words and punctuation
use the existing shared normalizer. An unknown target or ambiguous/unsupported wording fails
closed. Axis/unit/number operands cannot select another printer with a matching alias.

Only **one XYZ axis at a time on verified Cartesian/CoreXY** is supported. Relative moves
compute destination = current commanded machine position + displacement. Absolute destinations
mean **machine coordinates**, explicitly labelled in the review. G-code translation uses the
verified current machine/G-code coordinate difference, including G92 and homing offsets.
Every review names the printer, axis, start, signed displacement, exact destination, translated
G-code target, speed and acceleration ceiling, and asks the operator to check physical clearance.

All XYZ axes must be homed. The printer must be ready and idle (standby/complete/cancelled),
with coherent toolhead, G-code and interpolated positions, zero reported motion/extrusion,
known coordinate modes and a verified 100% speed override. Start and destination must lie in
the intersection of firmware, runtime and optional stricter owner bounds. Runtime acceleration
cannot exceed configured/owner caps; Z acceleration uses Klipper's independent Z restriction.
Default feed is at most 10 mm/s and applicable caps. An explicit excessive feed is rejected,
never clamped. Klippy does not change runtime acceleration or global speed overrides.

Delta, polar, CoreXZ, generic layouts and other unsupported kinematics are blocked for direct
movement. Extra/remapped axes, carriage controls, skew/bed-tilt/axis-twist/Z-thermal transforms,
active or uncertain bed mesh, and macros shadowing the used standard commands also block it.
An explicitly verified unloaded bed mesh is allowed. Physical phrases such as “move the bed
forward” request an explicit axis/direction instead of guessing printer orientation.

The deterministic SafetyEngine builds a bounded sequence: save a uniquely named parser state,
G90, one validated G1, M400, then restore parser state **without MOVE**. It never changes E.
This preserves original coordinate/extrusion modes, offsets and feed settings. Firmware remains
an additional protection layer. Configured limits and commanded positions do **not** establish
physical clearance or actual measured position.

## Freshness, confirmations and configuration changes

Every proposal and confirmation performs a fresh object discovery/status read. Reads taking
more than two seconds, malformed/missing state, and repeated/backward eventtimes are rejected.
Replay watermarks survive failed reads. Explicit Klipper lifecycle/reconnect events reset the
timestamp epoch while invalidating pending requests. Cached values cannot grant write rights.

Enrollment, reconnection and periodic monitoring refresh discovery. Read-only websocket
lifecycle/configuration and relevant state changes revoke cached records and pending motion/
heating reviews. A lost subscription invalidates its record and reconnects with a bounded delay;
polling and the independent execution-time read remain additional guards. Monitoring never
dispatches a corrective action. Mock transports never open real websocket connections.

Configuration digest, registry generation, enrollment, selected printer, exact positions,
offsets/modes, homing, bounds, runtime caps and owner policy bind the single-use confirmation.
Any changed fact requires a new review. Direct movement confirmation is mandatory even if
other command confirmation toggles are off. LLMs cannot select MOVE, generate its G-code or
authorize it. Transmission outcome uncertainty is reported without automatic retry.

## Heating and owner restrictions

Firmware heater min/max are authoritative. Existing `heater_limits` remain optional stricter
maximums, never expanded or removed during upgrade. An explicitly invalid owner record blocks
heating. Unknown firmware limits still block even if a manual cap exists. The selected active
extruder and actual heater telemetry must match; overridden M104/M140 commands are blocked.
Zero means heater off; other targets must satisfy the nonnegative firmware/owner interval.
Existing unit conversion, confirmations and no-retry protections remain.

Under Settings, **Printer capabilities and stricter safety limits** performs read-only discovery
and displays freshness, capabilities and last observed runtime fields. Optional JSON overrides
are per printer. `{}` removes these new optional overrides; existing legacy heater caps remain.
For example, with suitable verified firmware limits:

```json
{"axes":{"x":{"position_min":0,"position_max":200}},"motion":{"max_velocity":100},"heaters":{"extruder":{"max_temp":220}},"extrusion":{"extruder":{"min_extrude_temp":180,"max_extrude_only_distance":25}}}
```

Unknown names/fields, nonfinite values, inverted bounds and expansions are rejected. An owner
velocity/acceleration cap below the actual runtime setting can intentionally block a move;
Klippy does not silently change firmware settings to satisfy it. Saving revokes pending reviews.
Upgrade/reinstall preserves restrictions. Recovery to a different profile clears device-bound
restrictions and approvals, with the pre-restore SQLite backup retained for review.

## Qualification and remaining acceptance

Automated tests use simulated Moonraker only. The packaged limits probe forbids **every HTTP
write**, proposes/cancels valid moves, rejects unsafe examples and checks configuration-change
confirmation invalidation. Frozen, installed/offline and memory-budgeted native reports require
this probe as well as all existing wake, query, dialogue, interruption, audio and safety gates.
Diagnostics include the `limits_refresh` timing span; simulated timings are not LAN latency.

No physical printer action has qualified this feature. Supervised hardware/path/offset checks,
unsupported kinematics/transforms, human acoustic accuracy, clean interactive Windows VM and
an actual 16 GB host remain open. This is an unsigned engineering preview, not stable v1.0.

## Primary references reviewed 2026-11-17

- [Moonraker printer object API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
- [Klipper status reference](https://www.klipper3d.org/Status_Reference.html)
- [Klipper configuration reference](https://www.klipper3d.org/Config_Reference.html)
- [Klipper G-code/state restoration](https://www.klipper3d.org/G-Codes.html)
- [Cartesian constraints](https://github.com/Klipper3d/klipper/blob/master/klippy/kinematics/cartesian.py),
  [CoreXY constraints](https://github.com/Klipper3d/klipper/blob/master/klippy/kinematics/corexy.py),
  [coordinate mapping/state](https://github.com/Klipper3d/klipper/blob/master/klippy/extras/gcode_move.py)
