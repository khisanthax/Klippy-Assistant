"""Speaker-only quiet synthetic speech audit; never opens a microphone or printer."""
import argparse
import json
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

from klippy.audio import FRAME, RATE, default_device_pair, resample
from klippy.resampling import SpeechResampler
from klippy.voice import VoiceLoop


def run(source, output):
    raw=np.load(source/'kokoro-original.npy')[:24000*3]
    pair=default_device_pair(sd)
    info=sd.query_devices(pair[1])
    api=sd.query_hostapis(info['hostapi'])['name']
    extra=sd.WasapiSettings(auto_convert=True) if api=='Windows WASAPI' else None
    profiles=[]
    for name,latency,improved,inject in [('legacy_default','high',False,False),
                                       ('sinc_buffered',max(.08,info['default_high_output_latency']),True,False),
                                       ('default_stall','high',True,True),
                                       ('buffered_stall',max(.08,info['default_high_output_latency']),True,True)]:
        pcm=(SpeechResampler(24000).push(raw,final=True) if improved else resample(raw,24000))*.3
        voice=VoiceLoop(object(),lambda _:None,lambda _:None)
        voice.playback.enqueue(pcm,voice.epoch)
        calls=[0]
        def callback(outdata,frames,timing,status):
            calls[0]+=1
            if inject and calls[0] in (100,200):
                time.sleep(.03)  # Controlled diagnostic only; never present in the application.
            voice._output_callback(outdata,frames,timing,status)
        started=time.perf_counter()
        try:
            with sd.OutputStream(device=pair[1],samplerate=RATE,channels=1,dtype='float32',
                                 blocksize=FRAME,latency=latency,extra_settings=extra,callback=callback) as stream:
                voice.audio_metrics.device(stream.latency)
                deadline=time.monotonic()+15
                while voice.playback.remaining and time.monotonic()<deadline:
                    time.sleep(.01)
                if voice.playback.remaining:
                    raise TimeoutError('Synthetic speaker playback did not drain')
                time.sleep(stream.latency+.08)
                row={'case':name,'requested_output_latency':latency,'reported_output_latency':stream.latency,
                     'portaudio_cpu_load':stream.cpu_load,'wall_seconds':time.perf_counter()-started,
                     'injected_callback_stalls':2 if inject else 0,'injected_stall_seconds':.03 if inject else 0,
                     'diagnostics':voice.playback_diagnostics()}
                profiles.append(row)
        finally:
            voice.close()
    report={'scope':'Speaker-only quiet synthetic speech; no input stream, recording or printer connection',
            'api':api,'shared_mode':api=='Windows WASAPI','auto_convert':extra is not None,
            'device_default_sample_rate':info['default_samplerate'],'application_sample_rate':RATE,
            'device_default_high_latency':info['default_high_output_latency'],'profiles':profiles,
            'limitations':['Precomputed synthetic speech; does not measure subjective listening quality',
                           'Injected stalls are a controlled robustness test, not proof of the owner incident']}
    output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.source,args.output)
