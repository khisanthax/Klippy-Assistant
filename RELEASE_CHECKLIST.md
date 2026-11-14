# Release gates

Stable release is blocked until every applicable item has evidence.

For the 0.6 orb preview, preserve all prior 510 regressions and require the complete extended
suite/Ruff, frozen and offline-installed `--orb-self-test` reports/captures and upgrade/reinstall
orb-preference preservation. Record measured CPU/memory and current native geometry without
claiming the full Windows 10/11 interactive DPI/auto-hide/hot-plug/focus/sleep-resume matrix.

- [x] Private repository pushed; CI passes on Windows.
- [ ] Current LOGBOOK, roadmap, architecture, user guide, license notices.
- [x] Application launches and closes cleanly from installed package (development host).
- [x] Complete local speech and LLM assets with reviewed redistribution rights, versions,
      immutable sources, checksums and included license texts.
- [ ] Verified Klippy wake word on actual microphone; no unrelated substitute.
- [ ] Natural ASR/TTS, clarification, conversation expiry and hands-free interruption.
- [ ] Default audio device changes and unavailable devices tested.
- [ ] Active printer persistence, enrollment/authentication and multi-printer operation.
- [ ] Macro discovery/changes/renames/conflicts/parameters validated on fleet.
- [ ] Safety suite and supervised hazardous operation tests pass.
- [ ] Fault monitoring never controls hardware; Happy Hare faults tested where available.
- [ ] Companion visibility/animation/tray and listening schedule verified.
- [x] CPU-only synthetic benchmark results with host specifications (0.4 preview evidence);
      actual 16 GB host / idle CPU acceptance remains open. 0.5 evidence is in PREVIEW5_REPORT.md.
- [x] Single installer with all required runtime/model assets; no post-install downloads (0.4.0 preview).
- [ ] Clean-machine install/upgrade/uninstall and offline runtime verified.
- [ ] No critical/high defects; limitations documented; release artifact checksums.
- [x] Digital signing status accurate (currently unsigned).

Engineering preview packages may omit the voice pack only if labeled explicitly. A preview
must never claim that a mock test satisfies hardware, acoustic or clean-machine gates.

For the conversational UX preview, publication also checks exactly one accepted Hey
wake-only attempt, exactly one Hey-plus-temperature attempt, wake acknowledgement and the
unprefixed follow-up in frozen/installed/memory reports. Keep original full-voice results
and failures separate. Match the installer digest to CI, the sidecar and installed-QA
evidence, and tag the exact qualified application source. These synthetic checks do not
close human microphone/room or physical-printer gates.

For the 0.5.1 heating/cancellation hotfix, all 21 packaged command-probe cases must pass
in frozen/installed/memory reports, with zero HTTP writes, supported-request LLM calls or
pending action. Check converted Celsius targets, configured-name/unit separation, explicit
cancellation and clarification-safe confirmation. Keep initial failure reproductions and
cancelled code candidates visible. Physical heater acceptance remains supervised and open.
