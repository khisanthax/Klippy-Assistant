import threading
import time
from types import SimpleNamespace

import numpy as np
import pytest
import sounddevice as sd

from klippy.session import Session
from klippy.voice import VoiceLoop


def test_capture_started_before_expiry_holds_context_until_asr_handoff():
    clock = [100.0]
    session = Session(lambda: clock[0])
    session.touch()
    values = []
    backend = SimpleNamespace(wake=lambda _:False, reset_wake=lambda:None,
                              transcribe=lambda _:'status')
    voice = VoiceLoop(backend, values.append, lambda _:None, session=session, clock=lambda:clock[0])
    voice.enabled.set()
    rng = np.random.default_rng(6)
    try:
        clock[0] = 129
        for _ in range(40):
            clock[0] += .01
            voice.process_frame(rng.normal(0,.05,160).astype(np.float32),np.zeros(160,np.float32),clock[0])
        assert session.until == float('inf')
        clock[0] += 2
        assert session.until > clock[0]  # UI expiry must not clear query/printer context.
        for _ in range(1):
            clock[0] += .01
            voice.process_frame(np.zeros(160,np.float32),np.zeros(160,np.float32),clock[0])
        voice.asr_pool.submit(lambda:None).result(timeout=3)
        assert len(values)==1 and values[0].text=='status'
        assert not session.holds and session.until == clock[0]+30
    finally:
        voice.close()


def test_capture_hold_cannot_open_expired_session_or_restore_muted_one():
    clock=[100.0]
    session=Session(lambda:clock[0])
    assert session.begin_active() is None
    session.touch()
    token=session.begin_active()
    session.clear()
    session.finish(token)
    assert session.until==0 and session.begin_active() is None


async def test_three_captured_exchanges_one_wake_and_long_playback_delays(rig):
    from klippy.conversation import Conversation
    _, sim, engine, clock = rig
    conversation = Conversation(engine, clock=lambda: clock[0])
    requests, deliveries = [], []
    class Backend:
        trigger = True
        text = 'Klippy status'
        def reset_wake(self):
            pass
        def wake(self, samples):
            result, self.trigger = self.trigger, False
            return result
        def transcribe(self, samples):
            clock[0] += 90
            return self.text
        def synthesize(self, *args, **kwargs):
            clock[0] += 90
            return SimpleNamespace(samples=np.ones(160,np.float32), sample_rate=16000)
    backend = Backend()
    voice = VoiceLoop(backend, requests.append, lambda _:None, session=conversation.session,
                      clock=lambda:clock[0],on_delivery=lambda *v:deliveries.append(v))
    voice.enabled.set()
    worker = threading.Thread(target=voice._speak)
    worker.start()
    rng = np.random.default_rng(51)
    def feed(count, speaking):
        for _ in range(count):
            clock[0] += .01
            near = rng.normal(0,.05,160).astype(np.float32) if speaking else np.zeros(160,np.float32)
            voice.process_frame(near,np.zeros(160,np.float32),clock[0])
    try:
        for index, phrase in enumerate(['Klippy status','temperatures','status']):
            backend.text = phrase
            feed(40,True)
            feed(70,False)
            voice.asr_pool.submit(lambda:None).result(timeout=3)
            assert len(requests)==index+1
            response = await conversation.hear(requests[-1].text,source='voice')
            assert response
            voice.say(response)
            end=time.monotonic()+3
            while not voice.playback.remaining and time.monotonic()<end:
                time.sleep(.01)
            assert conversation.until==float('inf')
            voice._render(160)
            while len(deliveries)<=index and time.monotonic()<end:
                time.sleep(.01)
            assert deliveries[-1]==(None,True)
            assert conversation.until==clock[0]+30
            clock[0]+=29
        clock[0]+=2
        feed(40,True)
        feed(70,False)
        voice.asr_pool.submit(lambda:None).result(timeout=3)
        assert len(requests)==3 and not sim.writes
    finally:
        voice.close()
        worker.join(2)


@pytest.mark.parametrize("flag,expected", [("output_underflow",2), ("output_overflow",2),
                                         ("input_underflow",1), ("input_overflow",1), ("priming_output",1)])
def test_classifies_real_callback_flags(flag, expected):
    status = sd.CallbackFlags()
    status = sd.CallbackFlags(16) if flag == 'priming_output' else status
    if flag != 'priming_output':
        setattr(status, flag, True)
    assert VoiceLoop.callback_fault(status) == expected


@pytest.mark.parametrize("flag", ["output_underflow", "input_overflow"])
def test_actual_callback_to_dsp_preserves_only_continuous_capture(flag):
    voice = VoiceLoop(SimpleNamespace(reset_wake=lambda: None), lambda _: None, lambda _: None)
    voice.enabled.set()
    voice.session.touch()
    deadline = voice.listen_until
    status = sd.CallbackFlags()
    setattr(status, flag, True)
    voice._callback(np.zeros((160,1),np.float32),np.zeros((160,1),np.float32),160,
                    SimpleNamespace(outputBufferDacTime=1,inputBufferAdcTime=1),status)
    worker = threading.Thread(target=voice._process)
    worker.start()
    try:
        key = 'output_discontinuities' if flag=='output_underflow' else 'discontinuities'
        end = time.monotonic()+2
        while not voice.wake_diagnostics()[key] and time.monotonic()<end:
            time.sleep(.01)
        assert voice.wake_diagnostics()[key] == 1
        assert voice.listen_until == (deadline if flag=='output_underflow' else 0)
        assert voice.enabled.is_set()
    finally:
        voice.close()
        worker.join(2)


def test_configured_shared_timeout_is_used_by_asr_and_mute_cannot_restore_it():
    clock=[100.0]
    session=Session(lambda: clock[0],timeout=75)
    values=[]
    voice=VoiceLoop(SimpleNamespace(transcribe=lambda _: 'Klippy status', reset_wake=lambda: None),values.append,lambda _: None,
                    clock=lambda:clock[0],session=session)
    voice.enabled.set()
    try:
        voice._transcribe(np.ones(3200,np.float32),voice.epoch,True,False)
        voice.asr_pool.submit(lambda:None).result(timeout=3)
        assert values and session.until==175
        voice.enabled.clear()
        voice.reset_session()
        assert session.until==0
        voice.enabled.set()
        voice._reset_dsp()
        assert session.until==0
    finally:
        voice.close()


def test_faulted_confirmation_playback_cannot_arm_but_conversation_can_continue():
    clock=[100.0]
    session=Session(lambda:clock[0])
    session.touch()
    delivered=[]
    voice=VoiceLoop(SimpleNamespace(synthesize=lambda *a,**k:SimpleNamespace(
        samples=np.ones(160,np.float32),sample_rate=16000)),lambda _:None,lambda _:None,
        session=session,clock=lambda:clock[0],on_delivery=lambda *args:delivered.append(args))
    worker=threading.Thread(target=voice._speak)
    worker.start()
    try:
        voice.say('Confirm exact request',token='exact')
        end=time.monotonic()+3
        while not voice.playback.remaining and time.monotonic()<end:
            time.sleep(.01)
        clock[0]+=120
        assert session.until==float('inf')
        status=sd.CallbackFlags()
        status.output_underflow=True
        voice._output_callback(np.zeros((160,1),np.float32),160,None,status)
        while not delivered and time.monotonic()<end:
            time.sleep(.01)
        assert delivered==[('exact',False)]
        assert session.until==clock[0]+30
    finally:
        voice.close()
        worker.join(2)
