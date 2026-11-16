"""Synthetic compute/transport/levels regressions; no physical devices or saved audio."""
import json
import uuid
from types import SimpleNamespace

import numpy as np

from klippy.audio import FRAME, AudioDiagnostics, EchoFilter
from klippy.domain import Snapshot
from klippy.history import InteractionHistory
from klippy.macros import discover
from klippy.monitor import Monitor


def test_generated_diagnostic_ids_remain_distinct_without_exempting_arbitrary_secrets(rig):
    history = InteractionHistory(rig[0])
    history.configure(enabled=True)
    try:
        first, second = uuid.uuid4().hex, uuid.uuid4().hex
        history.record('voice_diagnostic', event_id=first, attempt_id=second)
        row = history.entries()[0]
        assert row['event_id'] == first and row['attempt_id'] == second
        secret = 'sk-proj-' + 'X' * 70
        history.record('voice_diagnostic', event_id=secret)
        assert secret not in json.dumps(history.entries())
    finally:
        history.close()


async def test_monitor_never_runs_unused_pairwise_advisory_but_still_revokes_changed_macros(rig, monkeypatch):
    store, sim, _, _ = rig
    config = sim.config
    registry, _ = discover(config, {})
    store.replace_macros("sim", {k:m.model_copy(update={"approved":True,"enabled":True,"reviewed":True}) for k,m in registry.items()})
    def forbidden(registry):
        raise AssertionError("Periodic monitoring must not compute unused pairwise warnings")
    monkeypatch.setattr("klippy.macros.conflicts", forbidden)
    class Client:
        async def snapshot(self):
            return Snapshot(connected=True,ready=True)
        async def macro_config(self):
            return config
        async def mmu_snapshot(self):
            return SimpleNamespace(fault=False)
    monitor = Monitor(store, lambda p:Client())
    await monitor.poll()
    assert all(m.approved for m in store.macros("sim").values())
    config["gcode_macro CHANGED"] = {"gcode":"M105"}
    monitor.cycles = 11
    await monitor.poll()
    assert all(not m.approved for m in store.macros("sim").values())
    assert not sim.writes


def test_advisory_skip_preserves_registry_and_review_still_has_similarity_warnings():
    config={"gcode_macro MESH_FAST":{"gcode":"G28\nG1 X10"},"gcode_macro MESH_FULL":{"gcode":"G28\nG1 X10"}}
    regular, notices = discover(config,{})
    background, _ = discover(config,{},analyze_conflicts=False)
    assert regular == background and any("Similar function" in n for n in notices)


def test_reference_activity_window_has_same_silence_transition_without_rescanning_history():
    echo = EchoFilter()
    signal=np.full(FRAME,.05,np.float32)
    silence=np.zeros(FRAME,np.float32)
    for _ in range(200):
        assert np.array_equal(echo.process(signal,silence),signal)
        assert echo.active_reference_frames == 0
    echo.process(signal,signal)
    assert echo.active_reference_frames == 1
    for _ in range(149):
        echo.process(signal,silence)
    assert echo.active_reference_frames == 1
    assert np.array_equal(echo.process(signal,silence),signal)
    assert echo.active_reference_frames == 0 and len(echo.far) == len(echo.far_active) == 150


def test_numeric_capture_metrics_do_not_keep_pcm_or_block_on_reader():
    stats=AudioDiagnostics()
    pcm=np.full(FRAME,.02,np.float32)
    stats.capture(pcm)
    stats.capture(np.zeros(FRAME,np.float32))
    stats.processing(.004,.025)
    data=stats.snapshot()
    assert .019 < data['input_peak'] < .021 and data['input_rms']==0
    assert data['input_zero_frames']==1 and data['dsp_max_work_ms']==4 and data['dsp_queue_delay_ms']==25
    assert all(isinstance(v,(int,float)) for v in data.values())
    with stats.lock:
        stats.capture(pcm)


def test_timing_optout_removes_capture_timing_but_retains_safe_numeric_levels(rig):
    history=InteractionHistory(rig[0])
    history.configure(enabled=True,timing=False)
    try:
        history.record('voice_diagnostic', capture_metrics={'input_rms':.02,'dsp_max_work_ms':4,'token':'not allowed'})
        row=history.entries()[0]
        assert row['capture_metrics']=={'input_rms':.02}
        assert 'token' not in json.dumps(row)
    finally:
        history.close()
