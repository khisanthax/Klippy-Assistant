# Owner voice acceptance

Use Klippy’s installed preview with a fresh test profile, the intended BEACN input and a simulated printer. Disable physical printer enrollment in the test profile. Record the build digest, selected Windows input and output, room conditions, and counts on a local worksheet. The test needs no recordings or conversation export.

Run each sequence three times in quiet and three times with ordinary background sound. Before each sequence wait for the orb to return to idle. Score each stage separately so an accurate transcript paired with the wrong reply remains visible.

| Spoken sequence | Observe |
|---|---|
| “Hey Klippy.” Pause. “Is M1 homed?” | First utterance opens Listening, one question reaches the intended simulator, reply names the correct axes. |
| “Hey Klippy, how hot is the nozzle?” Wait for playback. “What about the bed?” | Record continuous-wake recognition, time from playback end to Listening, and whether the second reply uses the bed on the same printer. |
| Request 90 Celsius on a simulated nozzle. Say “That’s not what I meant.” Then say “confirm.” | Original request enters review. Correction asks for clarification. Old confirmation produces zero simulated writes. |
| Request 90 again. Say “cancel that request.” Then say “confirm.” | One cancellation, zero simulated writes. |
| Request 90 again. Verify the exact review and confirm once on the simulator. Repeat “confirm.” | Correct printer and temperature, one simulated POST across both confirmations. |
| Play a response, then mute with the orb. Speak a follow-up, unmute and speak again without the wake phrase. | No captured command or simulated write. A fresh wake starts a new exchange. |

For each sequence tally first-wake detections, expected transcripts, correct printer/intent, correct reply, follow-up captures, correct confirmation outcomes and simulator write counts. Report numerator and denominator for each stage and condition, plus unexpected activations. Use stage codes for failures. Keep owner observations separate from synthetic release results. A consequential operation addressed to a physical printer requires its own supervised authorization.
