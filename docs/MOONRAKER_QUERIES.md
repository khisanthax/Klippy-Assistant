# Moonraker query inventory and safety review

Reviewed 2026-11-12 against current official documentation. This is a bounded built-in
catalog, not arbitrary API access. The runtime authority is `src/klippy/query_catalog.py`;
`query_catalog.json` exports each identifier, description, field/object requirements,
component, examples/synonyms, formatting validation, missing-data rule and classification.
The searchable **Queries & Commands** tab uses the same runtime inventory.

## Official references

- [Moonraker printer API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)
- [Klipper status reference](https://www.klipper3d.org/Status_Reference.html)
- [Moonraker printer objects](https://moonraker.readthedocs.io/en/latest/printer_objects/)
  explicitly defers to Klipper for current field definitions.
- [Server information](https://moonraker.readthedocs.io/en/latest/external_api/server/)
- [Print history](https://moonraker.readthedocs.io/en/latest/external_api/history/)
- [Files and metadata](https://moonraker.readthedocs.io/en/latest/external_api/file_manager/)
- [Host information and telemetry](https://moonraker.readthedocs.io/en/latest/external_api/machine/)
- [Power/accessories](https://moonraker.readthedocs.io/en/latest/external_api/devices/),
  [webcams](https://moonraker.readthedocs.io/en/latest/external_api/webcams/) and
  [job queue](https://moonraker.readthedocs.io/en/latest/external_api/job_queue/)
- [Happy Hare exposed printer variables](https://moggieuk.github.io/Happy-Hare-Doc/Reference-Printer-Variables/)
  describe the optional MMU extension; these fields are not a universal Klipper API.

## Reviewed read surface

All catalog traffic uses GET against thirteen exact allowlisted paths. Method alone does
not establish safety: the documented GET CANbus discovery request can interact with
unassigned controllers and has explicit operational warnings, so it is excluded.
Control, G-code, service/power operations and arbitrary endpoint strings are not admitted.

| Path | Required capability and bounded parameters | Consumed data / unavailable conditions |
|---|---|---|
| `/server/info` | Core API, authenticated if required | Components, Klipper connection/state, version, failed components; invalid discovery fails closed |
| `/printer/info` | Connected Klipper | Readiness/error message and software version; unavailable when Klipper cannot answer |
| `/printer/objects/list` | Klipper reports ready | Exact object names; optional objects never inferred from printer model |
| `/printer/objects/query` | Verified objects; catalog-selected attributes only | `status` plus optional Klipper `eventtime`; absent attributes remain unknown |
| `/server/history/list` | `history`; newest first, limit 5 or 50 | Jobs and recorded outcomes; last failure search bounded to 50 entries |
| `/server/history/totals` | `history` | Tracked totals since reset, not lifetime counters |
| `/server/files/metadata` | `file_manager`; reported relative G-code filename | Existing slicer metadata; no scans or metadata regeneration |
| `/server/files/list` | `file_manager`; root fixed to `gcodes` | Up to five displayed file names; no arbitrary host-file read |
| `/machine/system_info` | `machine` | CPU/platform/count and memory only with known units; no serials/network identities exposed |
| `/machine/proc_stats` | `proc_stats` | CPU temperature/load, uptime, optional throttle flags; platform-specific omissions remain unknown |
| `/machine/device_power/devices` | `power` | Configured accessory names and reported states; no switching |
| `/server/job_queue/status` | `job_queue` | Names and queue state; never add/start/remove jobs |
| `/server/webcams/list` | `webcam` | Configured camera names; never fetch frames or start recording |

Discovery queries only the reviewed fields, in batches of at most 64 objects. Temperature,
fan, filament-sensor and MCU families are expanded from actual object names. Extra
extruders are recognized; a nozzle temperature answer can list multiple extruders rather
than silently choosing one. Generic heater/sensor names do not imply a heated bed.
Error/status questions fall back to core server/printer information when Klipper is not
ready and ordinary objects cannot be discovered.

## Freshness and lifecycle

Approved enrollment, explicit read-only connection testing and reconnect/ready transitions
refresh discovery. Monitoring refreshes it at most every 60 seconds, independently of the
microphone. Queries also enforce the 60-second capability TTL. Config/restart notification
handling invalidates it; periodic discovery covers changes not represented by notifications.
No synchronous discovery is performed from the GUI thread.

Existing monitor snapshots feed the same in-memory cache. The notification adapter can
ingest authenticated subscription deltas; only attributes actually delivered receive a new
timestamp. The desktop continues using its existing polling monitor, without introducing
a second competing WebSocket subscription. A missing field in a full query removes an
old value. Nested layer data is replaced rather than retaining an omitted old layer.

Current-value cache budget is two seconds, measured with a local monotonic clock starting
before the request. Slow responses and failed-refresh cached answers are explicitly marked
STALE with age and a warning that current state is unverified. A backwards Klipper event
clock invalidates discovery/cache. Endpoint edits never reuse the previous server's cache;
approval/endpoint changes during a read prevent delivery. No cache or utterance is persisted.
The existing diagnostics records `query_response`, `query_format` and optional `query_llm`
durations, without printer names, endpoints or conversations.

## Interpretation and limitations

Common question families use deterministic word/context matching; aliases and printer
names are resolved before query interpretation. A short follow-up carries only the previous
query/subject inside the active session. Conflicting names require clarification. Unknown
questions can use a separate local-model JSON schema containing only a catalog identifier
and optional heater subject. It cannot produce an action, printer target, URL or G-code.
Queries never call `SafetyEngine.propose/confirm` or the client's execution method. Explicit
commands retain the existing engine and confirmation rules. Mixed information/control
requests require separate utterances. The snapshot-only embedded Conversation API retains
its existing status/temperature fast paths; the desktop supplies the full QueryService.

Homing uses only `toolhead.homed_axes`; missing/invalid is not interpreted as unhomed.
Position and live-motion fields represent commanded/interpolated coordinates, not encoder
measurements. Endstop/probe answers describe the last recorded sample and run no probing
command. Layer counters require slicer-supplied print information; Z is not converted to a
layer. Remaining time is explicitly a slicer estimate. History outcomes cannot identify a
physical cause such as a clog. Fan RPM and host throttling are optional platform features.
Long lists are bounded for speech and label omitted results.

Full raw configuration/server configuration, arbitrary macro variables, databases/logs,
file contents, shell commands, peripheral/CANbus scans, LED/WLED control, metadata scans,
unregistered plugins, live camera video and exhaustive history pagination are outside
this preview's query surface. USB/serial/video inventories and additional sensor/WLED
read endpoints are documented upstream but are not enabled here. No physical-printer,
human acoustic, clean desktop VM or actual 16 GB host gate is closed by simulations.

## Catalog coverage

The following table is generated from the runtime inventory. Detailed expected fields,
family expansions and validation rules are in `query_catalog.json` and the manager UI.

| Identifier | Purpose | Objects / endpoint | Component / capabilities | Example |
|---|---|---|---|---|
| homing | Whether Cartesian axes have been homed/zeroed and have an established coordinate reference | toolhead | Verified Klipper objects / core API | Is my printer homed? |
| temperatures | Measured heater and sensor temperatures in Celsius | extruder, heater_bed | Verified Klipper objects / core API | How hot is the bed? |
| targets | Requested heater setpoints, not a request to heat | extruder, heater_bed | Verified Klipper objects / core API | What's the target temperature? |
| heater_power | Current heater output fraction as percent | extruder, heater_bed | Verified Klipper objects / core API | How much heater power is being used? |
| position | Last commanded machine position, not measured physical position | toolhead | Verified Klipper objects / core API | Where's the nozzle? |
| gcode_position | G-code coordinates and origin offsets | gcode_move | Verified Klipper objects / core API | What are the G-code coordinates? |
| motion | Requested interpolated motion, not encoder-measured motion | motion_report | Verified Klipper objects / core API | Is the printer moving? |
| limits | Runtime velocity, acceleration and cornering limits | toolhead | Verified Klipper objects / core API | What's the acceleration? |
| speed | Last commanded feedrate and speed/flow overrides | gcode_move | Verified Klipper objects / core API | What's the speed? |
| progress | Print progress fraction and state | virtual_sdcard, display_status, print_stats | Verified Klipper objects / core API | How far along is my print? |
| job | Current or most recently reported filename and print state | print_stats, pause_resume | Verified Klipper objects / core API | What is printing? |
| layers | Slicer-reported layer counters; may not be supplied | print_stats | Verified Klipper objects / core API | What layer am I on? |
| duration | Active print time and total elapsed job duration | print_stats | Verified Klipper objects / core API | How long has it been printing? |
| filament | Extruded filament length in millimetres for the reported job | print_stats | Verified Klipper objects / core API | How much filament have I used? |
| fans | Available fan duty cycles and optional tachometer RPM | fan | Verified Klipper objects / core API | Are the fans running? |
| filament_sensors | Filament presence and sensor enable state | /printer/objects/query | Verified Klipper objects / core API | Is filament detected? |
| errors | Reported Klipper/print error messages; no diagnosis inferred | webhooks, print_stats | Verified Klipper objects / core API | Does the printer have an error? |
| status | Klipper readiness and reported print state | webhooks, print_stats | Verified Klipper objects / core API | Is the printer ready? |
| configuration | Configured axis bounds and pending-save/warning status | toolhead, configfile | Verified Klipper objects / core API | What are the printer configuration warnings? |
| bed_mesh | Already-loaded mesh profile; never probe or calibrate | bed_mesh | Verified Klipper objects / core API | Which bed mesh is loaded? |
| leveling | Previously reported gantry/Z tilt application status | quad_gantry_level, z_tilt | Verified Klipper objects / core API | Is the gantry leveled? |
| endstops | Last recorded endstop result, not a fresh hardware sample | query_endstops | Verified Klipper objects / core API | What are the endstop states? |
| probe | Last recorded probe result, not a fresh probe action | probe | Verified Klipper objects / core API | Is the probe triggered? |
| pressure_advance | Current pressure advance and smoothing time | extruder | Verified Klipper objects / core API | What's the pressure advance? |
| retraction | Current firmware retraction settings | firmware_retraction | Verified Klipper objects / core API | What is the retraction length? |
| extrusion | Extrusion eligibility and active extruder | extruder, toolhead | Verified Klipper objects / core API | Can it extrude? |
| mmu | Exposed Happy Hare state/tool/gate; notification-only | mmu | Verified Klipper objects / core API | What's the MMU state? |
| mcu | Controller firmware and communication statistics | mcu | Verified Klipper objects / core API | What firmware is on the MCU? |
| server | Moonraker version, Klipper connection and failed components | /server/info | Verified Klipper objects / core API | What Moonraker version is running? |
| printer_info | Klipper version/readiness even during startup or error | /printer/info | Verified Klipper objects / core API | What Klipper version is running? |
| history | Most recent five recorded jobs | /server/history/list | history | Show print history |
| last_failure | Last recorded unsuccessful job and its recorded status, not an invented cause | /server/history/list | history | Why did my last print fail? |
| totals | Recorded job totals since history totals were last reset | /server/history/totals | history | How many prints have I done? |
| metadata | Current file's existing slicer metadata | /server/files/metadata | file_manager | What material is this file sliced for? |
| remaining | Slicer-estimated total less active time; estimate only | /server/files/metadata | file_manager | How much time is left? |
| files | Up to five G-code file names; no reads of arbitrary host paths | /server/files/list | file_manager | What files are available? |
| host | Host platform/CPU/memory summary | /machine/system_info | machine | What host is the printer running on? |
| host_stats | CPU load, temperature, uptime and throttling telemetry | /machine/proc_stats | proc_stats | How hot is the host CPU? |
| power_devices | Reported power accessory states, never power switching | /machine/device_power/devices | power | What power devices are connected? |
| queue | Queued jobs and queue state; never enqueue/start | /server/job_queue/status | job_queue | What jobs are queued? |
| webcams | Configured camera names; no streaming or recording | /server/webcams/list | webcam | What cameras are connected? |
