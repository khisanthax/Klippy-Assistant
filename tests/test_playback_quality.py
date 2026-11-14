import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest

from klippy.audio import FRAME, AudioDiagnostics, Playback
from klippy.voice import VoiceLoop


@pytest.mark.parametrize('samples',[np.empty(0,np.float32),np.zeros(160,np.float32),np.full(160,np.nan,np.float32)])
async def test_unrenderable_spoken_review_cancels_engine_pending_action(rig,samples):
    from klippy.domain import Action, Intent
    _,sim,engine,_=rig
    prompt=await engine.propose(Intent(action=Action.HOME,printer_id='sim'),defer_confirmation=True)
    token=engine.pending.token
    delivered=threading.Event()
    def delivery(value,success):
        engine.delivery_finished(value,success)
        delivered.set()
    voice=VoiceLoop(SimpleNamespace(synthesize=lambda *a,**k:SimpleNamespace(samples=samples,sample_rate=16000)),
                    lambda _:None,lambda _:None,on_delivery=delivery)
    worker=threading.Thread(target=voice._speak)
    worker.start()
    try:
        voice.say(prompt,token=token)
        end=time.monotonic()+3
        while not delivered.is_set() and time.monotonic()<end:
            voice._render(FRAME)
            time.sleep(.01)
        assert delivered.is_set() and engine.pending is None and not sim.writes
    finally:
        voice.close()
        worker.join(2)


def test_prefill_is_bounded_and_interrupt_clears_it_at_next_packet():
    clock=[0.0]
    playback=Playback(clock=lambda:clock[0])
    stream=playback.begin(0,prefill=320)
    playback.enqueue(np.ones(160,np.float32),0,stream=stream)
    assert not playback.render().any() and playback.remaining==160
    playback.enqueue(np.ones(160,np.float32),0,stream=stream)
    assert playback.render().all()
    playback.interrupt()
    assert not playback.render().any() and not playback.receipt(0,stream)


def test_known_eof_drains_short_utterance_without_waiting_for_prefill():
    playback=Playback()
    stream=playback.begin(0)
    playback.enqueue(np.ones(40,np.float32),0,stream=stream,final=True)
    assert np.array_equal(playback.render(),np.r_[np.ones(40),np.zeros(120)])
    assert playback.receipt(0,stream)
    assert playback.diagnostics()['queue_underruns']==0


def test_complete_pcm_fallback_remains_interruptible_and_finishes_on_eof():
    playback=Playback(clock=lambda:0.0)
    stream=playback.begin(0)
    playback.defer_start(0,stream,2.0,complete_first=True)
    playback.enqueue(np.ones(320,np.float32),0,stream=stream)
    assert not playback.render().any()
    playback.interrupt()
    assert not playback.render().any() and not playback.receipt(0,stream)
    stream=playback.begin(1)
    playback.defer_start(1,stream,2.0,complete_first=True)
    playback.enqueue(np.ones(160,np.float32),1,stream=stream,final=True)
    assert playback.render().all() and playback.receipt(1,stream)


def test_starvation_is_distinct_from_eof_and_cannot_arm_delivery():
    playback=Playback()
    stream=playback.begin(0,prefill=0)
    playback.enqueue(np.ones(160,np.float32),0,stream=stream)
    playback.render()
    playback.render()
    playback.render()
    assert playback.diagnostics()['queue_underruns']==1
    assert playback.diagnostics()['missing_samples']==320
    playback.enqueue(np.ones(160,np.float32),0,stream=stream,final=True)
    playback.render()
    assert not playback.receipt(0,stream)


def test_old_chunks_faults_and_receipts_cannot_attach_to_another_speech_job():
    playback=Playback()
    first=playback.begin(0)
    playback.enqueue(np.ones(160,np.float32),0,stream=first,final=True)
    playback.render()
    second=playback.begin(0)
    assert not playback.enqueue(np.ones(160,np.float32),0,stream=first)
    playback.mark_fault(0,first,'device_underflows')
    playback.enqueue(np.ones(160,np.float32),0,stream=second,final=True)
    playback.render()
    assert playback.receipt(0,second) and not playback.receipt(0,first)


def test_deferred_start_does_not_hold_callback_or_survive_interrupt():
    clock=[1.0]
    playback=Playback(clock=lambda:clock[0])
    stream=playback.begin(0,prefill=0)
    playback.defer_start(0,stream,2.0)
    playback.enqueue(np.ones(160,np.float32),0,stream=stream,final=True)
    assert not playback.render().any()
    clock[0]=2
    assert playback.render().all()
    playback.interrupt()
    assert playback.not_before==0 and not playback.render().any()


@pytest.mark.parametrize('samples',[np.empty(0,np.float32),np.zeros(160,np.float32)])
def test_silent_or_empty_tts_is_not_successful_confirmation_delivery(samples):
    deliveries=[]
    voice=VoiceLoop(SimpleNamespace(synthesize=lambda *a,**k:SimpleNamespace(samples=samples,sample_rate=16000)),
                    lambda _:None,lambda _:None,on_delivery=lambda *v:deliveries.append(v))
    worker=threading.Thread(target=voice._speak)
    worker.start()
    try:
        voice.say('Confirmation must render',token='exact')
        end=time.monotonic()+3
        while not deliveries and time.monotonic()<end:
            voice._render(FRAME)
            time.sleep(.01)
        assert deliveries==[('exact',False)]
    finally:
        voice.close()
        worker.join(2)


def test_clipped_dac_samples_are_diagnosed_and_shared_with_aec_exactly():
    voice=VoiceLoop(object(),lambda _:None,lambda _:None)
    try:
        stream=voice.playback.begin(voice.epoch)
        voice.playback.enqueue(np.full(160,1.2,np.float32),voice.epoch,stream=stream,final=True)
        rendered=voice._render(160)
        assert np.max(rendered)==1 and voice.playback_diagnostics()['clipped_samples']==160
        assert not voice.playback.receipt(voice.epoch,stream)
    finally:
        voice.close()


def test_numeric_callback_diagnostics_drop_contention_and_exclude_idle_gaps():
    metrics=AudioDiagnostics()
    with metrics.lock:
        metrics.callback(1.0,.01)
    metrics.callback(1.0,.001)
    metrics.callback(1.01,.002)
    metrics.device((.01,.08))
    metrics.callback(100.0,.001)
    data=metrics.snapshot()
    assert data['callbacks']==3 and data['max_callback_gap_ms']<11
    assert data['max_callback_work_ms']==2 and data['output_latency_ms']==80
    assert all(type(value) in (int,float) for value in data.values())
