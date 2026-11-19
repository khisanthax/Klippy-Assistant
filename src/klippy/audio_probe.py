"""Device-free signal/stream audit using synthetic Kokoro speech, never user audio."""
import threading
import time

import numpy as np

from .audio import FRAME, RATE, Playback, resample
from .resampling import SpeechResampler
from .voice import VoiceLoop

TEXT = ("A quiet afternoon is a good time to check the sound. "
        "Smooth speech should remain clear across every sentence. "
        "Listen for crisp consonants and steady vowels.")


def convert_chunks(parts, rate):
    converter = SpeechResampler(rate)
    return [*[converter.push(part) for part in parts],converter.finish()]


def replay(parts, arrivals, progress, generated_at, source_rate, *, improved):
    clock=[0.0]
    playback=Playback(clock=lambda:clock[0])
    stream=playback.begin(0,prefill=1920 if improved else 0)
    converted=convert_chunks(parts,source_rate) if improved else [resample(p,source_rate) for p in parts]
    next_part=0
    source_done=False
    first_pcm=None
    gaps=0
    consumed=[]
    limit=generated_at+sum(len(part) for part in parts)/source_rate+5
    for tick in range(int(limit*100)+1):
        clock[0]=tick/100
        while next_part<len(parts) and arrivals[next_part]<=clock[0]:
            if improved and next_part==0:
                playback.buffer_first_chunk(0, stream, arrivals[0], len(parts[0])/source_rate, progress[0])
            playback.enqueue(converted[next_part],0,stream=stream)
            next_part+=1
        if not source_done and clock[0]>=generated_at and next_part==len(parts):
            tail=converted[-1] if improved else np.empty(0,np.float32)
            playback.enqueue(tail,0,stream=stream,final=True)
            source_done=True
        data,count,_,_=playback.render_packet()
        if count:
            first_pcm=clock[0] if first_pcm is None else first_pcm
            consumed.append(data[:count])
        elif first_pcm is not None and not source_done:
            gaps+=1
        if source_done and not playback.remaining:
            break
    result={'first_pcm_render_seconds':first_pcm,'queue_gap_seconds':gaps/100,
            'receipt':bool(playback.receipt(0,stream)),**playback.diagnostics()}
    return result,np.concatenate(consumed) if consumed else np.empty(0,np.float32)


def audit(raw, parts, rate, arrivals, progress, generated_at, *, repeats=32):
    joined=np.concatenate(parts)
    old=np.concatenate([resample(part,rate) for part in parts])
    new=np.concatenate(convert_chunks(parts,rate))
    batch=SpeechResampler(rate).push(raw,final=True)
    tone=np.sin(2*np.pi*10000*np.arange(24000)/24000).astype(np.float32)
    old_tone=resample(tone,24000)[100:-100]
    new_tone=SpeechResampler(24000).push(tone,final=True)[100:-100]
    def db(data):
        return float(20*np.log10(max(float(np.sqrt(np.mean(data*data))),1e-12)/np.sqrt(.5)))
    before,before_pcm=replay(parts,arrivals,progress,generated_at,rate,improved=False)
    after,after_pcm=replay(parts,arrivals,progress,generated_at,rate,improved=True)
    cpu={}
    for label,convert in [('legacy',lambda:np.concatenate([resample(p,rate) for p in parts])),
                          ('sinc',lambda:np.concatenate(convert_chunks(parts,rate)))]:
        wall,processor=time.perf_counter(),time.process_time()
        for _ in range(repeats):
            convert()
        cpu[label]={'iterations':repeats,'wall_seconds':time.perf_counter()-wall,
                    'cpu_seconds':time.process_time()-processor,
                    'audio_seconds_processed':repeats*len(raw)/rate}
    common=min(len(old),len(resample(raw,rate)))
    legacy_error=old[:common]-resample(raw,rate)[:common]
    checks={
        'original_is_finite_unclipped':bool(np.isfinite(raw).all() and np.max(np.abs(raw))<=1),
        'callback_chunks_match_original':bool(np.array_equal(raw,joined)),
        'converted_length':len(new)==round(len(raw)*RATE/rate),
        'chunk_invariance':bool(np.max(np.abs(new-batch))<1e-6),
        'antialias_rejection':db(new_tone)<-70,
        'render_preserves_converted_pcm':bool(np.array_equal(after_pcm,new)),
        'legacy_render_preserves_legacy_pcm':bool(np.array_equal(before_pcm,old)),
        'buffered_generation_has_no_starvation':after['queue_gap_seconds']==0,
        'non_silent_render_receipt':after['receipt'],
    }
    return {'passed':all(checks.values()),'checks':checks,'source_rate':rate,'target_rate':RATE,
            'source_samples':len(raw),'chunk_samples':[len(part) for part in parts],
            'arrivals_seconds':arrivals,'chunk_progress':progress,'generation_seconds':generated_at,
            'generation_realtime_factor':generated_at/(len(raw)/rate),
            'source_peak':float(np.max(np.abs(raw))),
            'legacy_chunk_vs_batch_peak_error':float(np.max(np.abs(legacy_error))),
            'new_chunk_vs_batch_peak_error':float(np.max(np.abs(new-batch))),
            'legacy_10khz_alias_db':db(old_tone),'new_10khz_alias_db':db(new_tone),
            'before':before,'after':after,'conversion_cpu':cpu,
            'scope':'Synthetic Kokoro PCM and a 10 ms device-free sink; no microphone or printers',
            'limitations':['Numeric signal/queue evidence is not human perceived-quality acceptance',
                           'Short CPU timings depend on host load; Windows CPU time is quantized',
                           '16 kHz AEC/output retained; shared WASAPI mix conversion remains in Windows']}


def cached_pipeline(backend, raw, rate):
    """Exercise the real production TTS worker/render path using its just-created cache."""
    delivered=[]
    voice=VoiceLoop(backend,lambda _:None,lambda _:None,on_delivery=lambda *row:delivered.append(row))
    packets=[]
    original=voice.playback.render_packet
    def traced(size=FRAME):
        packet=original(size)
        if packet[1]:
            packets.append(packet[0][:packet[1]].copy())
        return packet
    voice.playback.render_packet=traced
    worker=threading.Thread(target=voice._speak)
    worker.start()
    began=time.perf_counter()
    try:
        voice.say(TEXT,token='synthetic-quality-review')
        deadline=time.monotonic()+25
        while not delivered and time.monotonic()<deadline:
            voice._output_callback(np.zeros((FRAME,1),np.float32),FRAME,None,False)
            time.sleep(.001)  # Accelerated sink, not a physical latency measurement.
        rendered=np.concatenate(packets) if packets else np.empty(0,np.float32)
        expected=SpeechResampler(rate).push(raw,final=True)
        passed=(delivered==[('synthetic-quality-review',True)] and len(rendered)==len(expected)
                and np.allclose(rendered,expected,atol=1e-6))
        return {'passed':bool(passed),'rendered_samples':len(rendered),'expected_samples':len(expected),
                'wall_seconds':time.perf_counter()-began,'diagnostics':voice.playback_diagnostics(),
                'scope':'Production cached TTS worker and output callback; accelerated synthetic sink, no devices'}
    finally:
        voice.close()
        worker.join(4)


def run(backend):
    parts,arrivals,progress=[],[],[]
    began=time.perf_counter()
    def chunk(samples,rate):
        parts.append(np.asarray(samples,dtype=np.float32).copy())
        arrivals.append(time.perf_counter()-began)
    audio=backend.synthesize(TEXT,on_chunk=chunk,on_progress=progress.append)
    generated=time.perf_counter()-began
    report=audit(audio.samples,parts,audio.sample_rate,arrivals,progress,generated)
    report['production_cached_pipeline']=cached_pipeline(backend,audio.samples,audio.sample_rate)
    report['passed']=report['passed'] and report['production_cached_pipeline']['passed']
    return report
