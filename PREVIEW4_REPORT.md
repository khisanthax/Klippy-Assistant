# 0.4.0 preview — Moonraker information queries

Unsigned CPU-only engineering preview. Hardware, human acoustics, clean desktop VM and
actual 16 GB host acceptance remain open. No physical printer connection/action was used.

## Coverage

41 built-in query types use 13 individually reviewed GET paths. The catalog covers homing,
measured/target temperatures and heater power, last commanded/G-code/interpolated positions,
motion limits and overrides, print progress/job/layers/time/filament, fans and filament
sensors, errors/readiness/config warnings, mesh/leveling, last recorded endstop/probe data,
pressure advance/retraction, extrusion eligibility, MMU, MCU, server/printer versions,
history/totals, file metadata/listings, estimated remaining time, host telemetry, power
accessory state, queued jobs and configured cameras.

Every query declares its purpose, fields/objects/components, natural examples, validation,
missing-data handling and read-only classification. See
[official API inventory and exclusions](docs/MOONRAKER_QUERIES.md) and
[machine-readable catalog](docs/query_catalog.json). No arbitrary API/G-code explorer is enabled.

The **Queries & Commands** manager searches the same catalog, standard operations and
discovered macros, with printer support, voice state and safety classification. Read-only
queries and state-changing operations have separate tabs; browsing dispatches no command.
Printer aliases can be enrolled/edited there. Existing command safety checks and the complete
license-reviewed 57-file offline model/runtime pack are preserved.

## Query handling

Common question families use deterministic matching and approved named/aliased printer
selection. Session-bound follow-ups retain the previous query/subject, including
“What about the SV08?” and heater target follow-ups. Unknown information wording uses a
separate local-model schema containing only a catalog ID and heater subject. It cannot emit
an operation, target, endpoint or script. Questions never fall through to the action model.
Mixed control/information requests are rejected. Explicit commands retain SafetyEngine.

Homing reads `toolhead.homed_axes` and reports both homed and unhomed Cartesian axes.
Missing/invalid data remains unknown; no `G28` is executed for a question. Optional objects
and components must be discovered for that printer. A two-second per-field cache reuses
fresh monitor/query data. Full reads replace missing fields; subscription deltas refresh
only delivered attributes. Slow/failed-refresh cached answers are explicitly marked stale
with age. Capability TTL is 60 seconds; ready/reconnect/configuration changes invalidate it.
Generation and endpoint identity checks prevent delayed responses from an old enrollment
from overwriting the new printer's cache. Raw settings, private configuration and utterances
are never exported to a cloud service or written by the query engine.

## Tests and measurements

356 tests and Ruff pass; the original 179 tests remain unchanged. New simulated tests cover
every catalog entry and advertised example, ordinary variations, aliases/follow-ups, absent
objects/components/fields, invalid values, missing layers, fresh/stale cache behavior,
configuration/reconnect/clock changes, two-printer and delayed-old-endpoint isolation,
bounded object batches, read-only endpoint/parameter enforcement, query/action phrases,
query-only model output validation, diagnostics and manager search/classification.

The local real-model query probe passed seven synthetic cases with zero writes and no
pending action. Common simulated reads measured roughly 0.3–9 ms; an unfamiliar local-model
query took about 6 seconds, followed by a fresh object read. These are in-process simulated
transport measurements, not actual LAN/audio response times. The diagnostic timing stages
remain available for measurements on the owner's environment without persisting utterances.

The initial native probe confused an established axis reference with numeric position.
That failed result is retained in `benchmarks/preview4-query-initial.json`. The catalog and
model prompt now distinguish those concepts; corrected evidence is
`benchmarks/preview4-query-source.json`. Frozen and installed voice self-tests require the
new native query probe to pass, in addition to all original voice/safety gates.

Exact final build/installer qualification and artifact identity will be recorded here after
all jobs pass. The earlier source candidate was superseded before publication by the cache
generation correction; its artifact is not eligible for release.

## Remaining limits

Read-only does not establish physical truth: coordinates are commanded/interpolated, endstop
and probe values are previously sampled, layers require slicer reporting, and completion time
is a labeled slicer estimate. History exposes recorded outcomes, not a physical failure cause;
last-failure lookup scans only the most recent 50 entries. Optional sensors, fan RPM and host
throttle telemetry can be absent. Long spoken lists are bounded and label omitted results.

Unregistered plugins, full raw configuration/log/file/database access, USB/serial/video scans,
CANbus discovery, metadata regeneration, live camera streams, arbitrary object variables,
all LED/WLED features and exhaustive history pagination are outside this preview's surface.
The local model can still misunderstand unfamiliar wording; the read-only schema prevents
that error from becoming actuation, but it is not an accuracy guarantee for every sentence.
Actual fleet/authentication/accessory behavior, human microphone/room accuracy, supervised
consequential printer tests, clean Windows desktop/no-development-tools qualification,
actual 16 GB host/idle CPU and extended device/sleep/desktop soak remain unverified.
