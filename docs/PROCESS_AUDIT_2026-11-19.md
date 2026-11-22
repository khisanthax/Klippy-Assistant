# Klippy process audit, 19 November 2026

The corrections from this audit landed in application source `6e69120`. The qualification
record includes the local installer digest, test results and open acceptance gates.
[Preview.2 status](../benchmarks/preview82-release-status.json)

The budgeted run then exposed a late audio chunk. Preview.3 includes a replay of the
measured timings and a fast-stream control. [Preview.3 status](../benchmarks/preview83-release-status.json)

Reviewed main at 9081c56. Three fresh experiments used temporary profiles and synthetic status through the conversation and safety paths. One recorded a POST inside HTTPX MockTransport. No network connection to a printer or access to the owner's history was needed. The 886-test result belongs to the candidate's existing qualification evidence. This audit did not rerun the suite.

| Priority | Finding and evidence | Corrective action and acceptance criterion |
|---|---|---|
| Before release | Cancel can report success while a confirmed command is still preparing to send. Held the final endpoint lookup after all six simulation reads, canceled, then resumed. The mock received one POST. Window.cancel prints “Pending action canceled.” | Define the send commitment point in SafetyEngine and expose it to the UI. Allow revocation until that point and report an in-flight/unknown outcome afterwards. Use deterministic barriers around lookup, commitment, send and receipt. Every “canceled” result must correspond to zero later sends. Preserve single-use tokens and no retry. |
| Before release | The ordinary upstream toolhead mapping with extruder at index 3 is rejected. Removing both axis metadata fields lets the same move enter confirmation. Packaged probes and tests share a fixture with an empty list instead of the upstream dictionary. | Pin independently sourced response contracts for supported firmware revisions. Validate the ordinary extruder mapping and block additional, ambiguous or unknown axes. Verify both directions through the same command entry point. |
| Before release | Recovery deletes device-specific limits. With an 80°C owner cap, 90°C was rejected. Restore revoked approval as designed. Ordinary reapproval and selection then made 90°C eligible for confirmation on the same synthetic printer. | Retain a restriction-review requirement through restore. Offer previous caps for explicit review against the freshly identified printer. Require an explicit decision before broader targets can be proposed. Exercise export, restore, reapproval and a previously forbidden request as one test. |
| Before publication | Previous audit reproduced a passing preview verdict after removing required voice evidence. Several gates in voice_probe.py are added only when their sections exist. | Establish one versioned verifier that requires all expected sections and checks case identities and outcomes. Delete, duplicate and corrupt required cases in negative tests. Use the verifier on frozen, installed and budgeted reports before promoting the exact installer digest. |
| Before claiming upgrade/history preservation | installer_settings.py seeds preferences and a macro using the current source helper. It checks logging preferences but does not seed a conversation-history row. After uninstall test_installer.ps1 checks the executable and a sentinel file. | Seed traceable synthetic rows in an old-version profile. Compare settings, approvals, history IDs and row content before and after upgrade, reinstall and uninstall. Exercise consent-off and consent-on profiles. Keep the separate owner-upgrade observations scoped to that particular upgrade. |
| Next UI pass | Console text says every printer action requires confirmation. Settings and SafetyEngine permit disabling confirmation for specific deterministic operations including heating. | Generate policy labels from the effective policy and show the selected printer. A UI test with heat confirmation disabled should agree with the engine while direct movement still requires confirmation. |

## Review changes

Assign an owner to each claim. The motion reviewer owns the upstream status contract, the safety reviewer owns dispatch and recovery transitions, and the release reviewer owns preservation assertions and artifact identity. An independent fixture or behavioral check matters more than a second pass over the same simulated success path.

Add three questions to consequential-change reviews. What happens if a field is absent? What happens if cancellation, reconnect or recovery occurs between two individually correct steps? What stored evidence would make a false success visible? Require an observable answer for each applicable question.

Keep the local model, Qt, mock-transport and memory-budget checks. Add a small handoff test set beside them. Run source tests once per CI commit, then build and test the frozen and installed artifacts. Track release-ready claims in one manifest with separate values for passed, failed, missing and infrastructure-blocked. Keep continuous human speech, supervised printer behavior, clean desktop and actual 16 GB host acceptance separate in the release notes.

Evidence locations: src/klippy/safety.py (confirmation and dispatch), moonraker.py (endpoint lookup), app.py (Cancel and console text), motion.py (axis validation), limits_probe.py (fixture), storage.py (restore), voice_probe.py (preview verdict), scripts/installer_settings.py and scripts/test_installer.ps1 (preservation).

Upstream toolhead mapping implementation: https://github.com/Klipper3d/klipper/blob/a86759335197374d2787c87477b21e2af6fa07e1/klippy/toolhead.py . This establishes a firmware contract for the reviewed upstream source. The owner's firmware revision and live configuration were not inspected.
