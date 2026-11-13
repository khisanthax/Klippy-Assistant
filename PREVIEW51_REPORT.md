# 0.5.1 preview — heating interpretation and explicit cancellation

Engineering preview under qualification. No physical printer connections or heating actions
are used in development. Human microphone/room, broad continuous wake accuracy, actual fleet,
clean Windows desktop VM and actual 16 GB hardware acceptance remain open.

## Reproduction and correction

The owner's exact request was “Hey Klippy, can you set the Mercury 1 nozzle to 90 degrees
Celsius?”. In 0.5.0, a configured “Mercury One”/“M1” did not resolve spoken “Mercury 1”.
The deterministic heating matcher then failed on the residual name and used the LLM fallback.
“Unexpected parameters” is the safety guard for parameters attached to an action other than
HEAT/MACRO. A simulated model returning TEMPERATURES with heater/temperature parameters
reproduces the reported error without a write. The owner's actual model JSON was not recorded;
that specific output is a reproduction of the failure class, not a recovered owner trace.
Evidence: `benchmarks/preview51-initial-reproduction.json`.

Normalization now shares punctuation/possessive handling and bounded English number-word
parsing across printer names and heating recognition. Mercury One and Mercury 1 match only
configured labels; M1 must be configured as a name/alias. Collisions across printers are
rejected rather than guessed, including collisions in older saved configurations.
Heater/value/unit operands and command words are excluded from printer mentions. An alias F/C/nozzle/90 cannot
select a printer from a heating operand or strip its unit; an explicit “on F” still selects
that configured printer while preserving Fahrenheit conversion. The earlier unit-alias
collision is reproduced in `benchmarks/preview51-unit-alias-reproduction.json`.
Heating names are accepted only in a name position when removing that exact span leaves
a syntactically complete request or a heater request missing its target. Actual names such
as Nozzle One still work for switching, queries and named heating. A complete heating
request without a name keeps the selected printer; no target or unit is invented.

Set/heat/warm/bring instructions support polite wording, nozzle/hotend/hot end/extruder,
bed, printer placement, number words, decimal values and units. They enter the deterministic
HEAT path before temperature queries. Incomplete/ambiguous heating instructions ask for
one printer, heater and target; they never reach an LLM that might invent a value.
Temperature questions remain read-only.

No unit means Celsius, with no unit question. Celsius/C/degrees/degrees Celsius are accepted;
explicit Fahrenheit/F is converted with `(F - 32) * 5 / 9`. Confirmation shows the final
Celsius target. Conversion uses bounded decimal arithmetic and conservative float conversion
so a value just above a reviewed maximum cannot round down into the allowed range. The
selected printer, actual heater telemetry, fresh state and locally reviewed limits are
checked before a proposal and again at confirmation. Missing/malformed limits block heat.
Configured confirmation policies remain; no heating transmission is retried.

Invalid model action/parameter combinations are rejected independently in the model adapter,
conversation and SafetyEngine. They are never reclassified into an executable action.
Model HEAT values must also agree with an independent deterministic Celsius parse. A useful
spoken explanation replaces “Unexpected parameters”; bounded, sanitized error codes appear
only in in-memory Settings diagnostics with their reaction identifier, not normal speech.

## Cancellation and clarification

Only explicit cancellation or negative imperatives cancel a pending request: “No, don't do
that”, “Cancel that request”, “Never mind”, “Don't heat the nozzle”. Ordinary remarks such
as “I'm not sure why it didn't understand”, “That's not what I meant” and “I don't know
what happened” ask for clarification without reporting cancellation or sending an action.

An uncertain/corrective remark leaves an existing pending review present but suspends its
confirmation until a complete new request is stated. Old prompt completion cannot rearm it,
and voice/manual/direct confirmation cannot execute it. This avoids executing a request
the user has just questioned. A fresh request gets fresh validation and a new token; explicit
cancellation still discards the review. In-flight validation is invalidated during clarification.

## Qualification plan and open gates

Final local full suite: **510 passed**, all 408 prior regressions retained; Ruff passed.
Operand/name safety regressions are included. New tests cover the exact owner phrases and variations,
configured/colliding aliases, number words/units, Fahrenheit boundaries, missing heaters and
limits, query/action classification, invalid model output, explicit cancellation, clarification,
confirmation races/policies, Celsius review and single-use/no-retry behavior. All services
are simulated. No microphone recording or owner installation change is needed.

The packaged self-test additionally requires a 21-case heating/cancellation probe through
Conversation and SafetyEngine with a transport that forbids every HTTP write. Supported
requests must use zero LLM calls and leave zero writes/pending actions at completion.
Windows frozen/installed/offline/upgrade and memory qualification must pass before publication.
Existing voice/query and negative-input gates remain; broad acoustic flags stay separate.
Final test counts, exact source, installer identity and verified results will be recorded
here after qualification. The same reviewed 57-file offline model pack is unchanged/outside Git.
