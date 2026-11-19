"""Engineering preview evidence contract. Change the revision when required cases change."""

REVISION = 1

QUERY_CASES = ['Klippy, is my M1 printer homed?',
 'What about the SV08?',
 'How hot is the bed?',
 "What's the target temperature?",
 'What layer am I on?',
 'Is Mercury One homed?',
 "What's the height of the z-axis right now?",
 'What about the X axis?',
 'How hot is the nozzle?',
 'How high is the nozzle?',
 'Has the machine established its coordinate reference?']

LIMIT_CASES = ['Move X minus 20 millimeters.',
 'Go to X 150.',
 'Raise Z by 10.',
 'Move X minus 200 millimeters.',
 'Go to X 301.',
 'Move X 20 at 400 mm/s',
 'Move the bed forward 20 millimeters.',
 'changed configuration invalidates confirmation',
 'absent axis mapping blocks review',
 'restore requires device limits review and respects prior heater cap']

COMMAND_CASES = [('heat_celsius_review', 'Hey Klippy, can you set the Mercury 1 nozzle to 90 degrees Celsius?'),
 ('heat_celsius_review', "Set M1's nozzle to 90 degrees."),
 ('heat_celsius_review', 'Can you set the Mercury 1 nozzle to 90 Celsius?'),
 ('heat_celsius_review', "Heat Mercury One's hotend to 90."),
 ('heat_celsius_review', 'Set the nozzle temperature to 90 on M1.'),
 ('heat_celsius_review', 'Bring the nozzle up to 90 degrees.'),
 ('heat_celsius_review', 'Heat Mercury One nozzle to ninety'),
 ('heat_celsius_review', 'Heat nozzle to 194 F'),
 ('heat_celsius_review', 'Heat nozzle to 90'),
 ('explicit_cancel', "No, don't do that."),
 ('explicit_cancel', 'Cancel that request.'),
 ('explicit_cancel', 'Never mind.'),
 ('explicit_cancel', "Don't heat the nozzle."),
 ('clarification_not_cancellation', "I'm not sure why it didn't understand."),
 ('clarification_not_cancellation', "That's not what I meant."),
 ('clarification_not_cancellation', "I don't know what happened."),
 ('ambiguous_or_outside_limits', 'heat nozzle 500 F'),
 ('ambiguous_or_outside_limits', 'set nozzle temperature'),
 ('ambiguous_or_outside_limits', 'heat nozzle 90 C F'),
 ('temperature_operands_not_printer_mentions', ''),
 ('invalid_model_action_parameters', '')]

DIALOGUE_CHECKS = ['routine_no_model',
 'routine_verified_nozzle',
 'followup_bed',
 'actual_model_composed',
 'explanation_keeps_verified_observation',
 'casual_without_printer',
 'no_pending_or_writes',
 'model_latency_bounded']

AUDIO_CHECKS = ['original_is_finite_unclipped',
 'callback_chunks_match_original',
 'converted_length',
 'chunk_invariance',
 'antialias_rejection',
 'render_preserves_converted_pcm',
 'legacy_render_preserves_legacy_pcm',
 'buffered_generation_has_no_starvation',
 'non_silent_render_receipt']


def qualify_report(report):
    """Gate the composite application; retain raw embedded-keyword recall separately.

    Interruption has two corroborating paths. A KWS-only miss is not an application
    interruption failure when the actual ASR-verified barge-in succeeds.
    """
    cases = {(case["phrase"], case["synthetic_voice"]): case["detected"] for case in report["wake_cases"]}
    embedded = [case for case in report["wake_cases"] if "klippy" in case["phrase"].lower()
                and case["phrase"] not in {"Klippy", "Hey Klippy"}]
    report["raw_embedded_keyword"] = {"detected": sum(bool(case["detected"]) for case in embedded),
                                      "total": len(embedded),
                                      "misses": [case for case in embedded if not case["detected"]]}
    report["gates"] = {
        "standalone_wake": all(cases.get((phrase, sid)) is True
                               for phrase in ("Klippy", "Hey Klippy") for sid in (0, 3)),
        "negative_words": all(cases.get((phrase, sid)) is False
                              for phrase in ("clipper", "Klipper", "The printer is ready") for sid in (0, 3)),
        "captured_status": bool(report["pipeline_transcripts"]) and "63%" in (report["simulated_status_response"] or ""),
        "own_echo": report["own_echo_requests"] == 0 and report["own_echo_wakes"] == 0,
        "verified_interruption": (report["barge_wakes"] > 0 and report["playback_flushed"]
                                  and any("stop talking" in text.lower() for text in report["barge_requests"])),
        "local_language": report["llm_intent"]["action"] == "temperatures",
        "no_printer_writes": report["printer_writes"] == 0,
    }
    report["passed"] = all(report["gates"].values())


def qualify_preview_report(report):
    """Recompute the versioned contract from individual results. Missing evidence fails closed."""

    def section(name):
        value = report.get(name)
        return value if isinstance(value, dict) else {}

    def exact_rows(rows, expected, identity, passed):
        if not isinstance(rows, list) or len(rows) != len(expected):
            return False
        try:
            return ({identity(row) for row in rows} == set(expected) and all(passed(row) for row in rows))
        except (KeyError, TypeError, ValueError, AttributeError):
            return False

    def checked(name, keys):
        value = section(name)
        return (value.get('passed') is True and isinstance(value.get('checks'), dict)
                and all(value['checks'].get(key) is True for key in keys))

    def zero(value):
        return type(value) is int and value == 0

    gates = {}
    required = ('standalone_wake', 'own_echo', 'verified_interruption', 'local_language', 'no_printer_writes')
    raw = report.copy()
    try:
        qualify_report(raw)
        for key in required:
            gates[key] = raw['gates'][key] is True and section('gates').get(key) is True
    except (KeyError, TypeError, ValueError, AttributeError):
        gates.update(dict.fromkeys(required, False))
    gates['own_echo'] &= zero(report.get('own_echo_requests')) and zero(report.get('own_echo_wakes'))
    gates['verified_interruption'] &= (report.get('playback_flushed') is True
                                        and type(report.get('barge_wakes')) is int)
    gates['no_printer_writes'] &= zero(report.get('printer_writes'))
    wake_phrases = ('Klippy', 'Hey Klippy', 'Klippy stop talking', 'Hey Klippy stop talking',
                    'clipper', 'Klipper', 'The printer is ready', 'clippy')
    def voice_ids(phrases):
        return [(phrase, sid) for phrase in phrases for sid in (0, 3)]
    def voice_id(row):
        if type(row['synthetic_voice']) is not int:
            raise ValueError('Invalid synthetic voice')
        return row['phrase'], row['synthetic_voice']
    gates['wake_cases_present'] = exact_rows(report.get('wake_cases'), voice_ids(wake_phrases), voice_id,
                                            lambda r: type(r.get('detected')) is bool)
    gates['paced_captured_status'] = (isinstance(report.get('paced_pipeline_transcripts'), list)
                                      and bool(report['paced_pipeline_transcripts'])
                                      and all(isinstance(t, str) and t.strip() for t in report['paced_pipeline_transcripts'])
                                      and isinstance(report.get('paced_status_response'), str)
                                      and '63%' in report['paced_status_response'])
    answers = report.get('paced_responses')
    gates['three_unprefixed_followups'] = (type(report.get('followup_capture_count')) is int
        and report['followup_capture_count'] == 3 and isinstance(answers, list) and len(answers) == 4
        and isinstance(answers[0], str) and bool(answers[0])
        and all(isinstance(a, str) and '63%' in a for a in answers[1:]))
    gates['grounded_dialogue'] = checked('dialogue', DIALOGUE_CHECKS)
    delivery = section('audio_quality').get('production_cached_pipeline')
    gates['audio_signal_and_delivery'] = (checked('audio_quality', AUDIO_CHECKS) and isinstance(delivery, dict)
                                          and delivery.get('passed') is True)
    query = section('query_catalog')
    def passed(row):
        return row.get('passed') is True
    gates['read_only_query_catalog'] = (query.get('passed') is True and zero(query.get('printer_writes'))
        and query.get('pending_write') is False
        and exact_rows(query.get('cases'), QUERY_CASES, lambda r: r['synthetic_question'], passed))
    gates['no_negative_query_activation'] = exact_rows(report.get('negative_composite'),
        voice_ids(('clipper', 'Klipper', 'The printer is ready')), voice_id,
        lambda r: r.get('accepted_requests') == [] and r.get('session_open') is False)
    limits = section('limits_probe')
    gates['capability_limits_and_motion_safety'] = (limits.get('passed') is True and zero(limits.get('printer_writes'))
        and exact_rows(limits.get('cases'), LIMIT_CASES, lambda r: r['case'], passed))
    commands = section('heat_fix_probe')
    gates['heating_parser_and_cancel_safety'] = (commands.get('passed') is True and zero(commands.get('printer_writes'))
        and zero(commands.get('supported_request_llm_calls')) and commands.get('pending_write') is False
        and exact_rows(commands.get('cases'), COMMAND_CASES, lambda r: (r['case'], r.get('synthetic_phrase', '')), passed))
    report['qualification_revision'] = REVISION
    report['preview_gates'] = gates
    report['engineering_preview_passed'] = all(gates.values())
    report['preview_scope'] = "Engineering preview for paced wake and follow-up using synthetic voices and simulated printers."
    report['continuous_wake_status_passed'] = section('gates').get('captured_status') is True


ORB_CHECKS = ['idle_hidden',
 'clear_of_taskbar',
 'idle',
 'non_activating_idle',
 'verifying',
 'non_activating_verifying',
 'listening',
 'non_activating_listening',
 'thinking',
 'non_activating_thinking',
 'speaking',
 'non_activating_speaking',
 'confirmation',
 'non_activating_confirmation',
 'interruption_clears_playback',
 'error',
 'non_activating_error',
 'muted',
 'non_activating_muted',
 'transparent_corners',
 'diameter_128',
 'diameter_256',
 'diameter_384',
 'hidden_has_no_animation_paints',
 'active_animation_rendered',
 'disabled_has_no_animation_paints',
 'no_audio_devices_or_printers',
 'cleanup',
 'conversation_features']


FEATURE_CHECKS = ['personality_settings',
 'history_default_off',
 'actual_two_reviewed_choices',
 'popup_does_not_activate',
 'remember_default_off',
 'popup_inside_taskbar_safe_area',
 'selection_requires_confirmation',
 'remembered_identity_only',
 'remembered_review_delete',
 'local_json_export_redacts',
 'history_view_has_turns',
 'countdown_after_response',
 'countdown_shared_half_window',
 'capture_hides_countdown',
 'response_resets_countdown',
 'attention_reason_tooltip',
 'copy_diagnostic_action_present',
 'new_wake_clears_old_attention',
 'mute_clears_countdown',
 'revoked_text_removed',
 'clear_history',
 'motion_inventory_separate_and_explicit',
 'limits_dialog_exposes_verified_configuration',
 'limits_dialog_rejects_expansion',
 'limits_dialog_saves_only_stricter_local_policy',
 'no_devices_or_printer_writes']


WAKE_CHECKS = ['native_strict_recovery_after_injected_asr_fault',
 'actual_pipeline_wake_only',
 'no_unsafe_pipeline_delivery',
 'no_new_negative_acceptances',
 'recheck_bounded']
