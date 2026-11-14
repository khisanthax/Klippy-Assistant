from types import SimpleNamespace

import numpy as np

from klippy.audio_probe import audit, cached_pipeline


def test_recorded_slow_producer_schedule_is_buffered_without_dropping_samples():
    sizes=[6001,6002,6004]
    raw=(.2*np.sin(2*np.pi*1200*np.arange(sum(sizes))/24000)).astype(np.float32)
    parts=np.split(raw,np.cumsum(sizes)[:-1])
    result=audit(raw,parts,24000,[.32,.64,.96],[1/3,2/3,1],.97,repeats=1)
    assert result['passed']
    assert result['before']['queue_gap_seconds']>0
    assert result['after']['queue_gap_seconds']==0
    assert result['after']['first_pcm_render_seconds']>result['before']['first_pcm_render_seconds']
    assert result['new_chunk_vs_batch_peak_error']<1e-6


def test_production_tts_worker_and_callback_match_continuous_conversion():
    raw=(.2*np.sin(2*np.pi*1000*np.arange(2400)/24000)).astype(np.float32)
    backend=SimpleNamespace(synthesize=lambda *a,**kw:SimpleNamespace(samples=raw,sample_rate=24000))
    result=cached_pipeline(backend,raw,24000)
    assert result['passed'] and result['rendered_samples']==1600
    assert result['diagnostics']['queue_underruns']==0
