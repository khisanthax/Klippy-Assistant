"""Phase-continuous, band-limited PCM conversion on the TTS worker, never callbacks."""
import math

import numpy as np


class SpeechResampler:
    def __init__(self, source_rate, target_rate=16000, half=48):
        if type(source_rate) is not int or type(target_rate) is not int or not (
                8000 <= source_rate <= 192000 and 8000 <= target_rate <= 192000):
            raise ValueError("Unsupported PCM sample rate")
        self.source, self.target, self.half = source_rate, target_rate, half
        self.total = self.emitted = self.start = 0
        self.buffer = np.empty(0, dtype=np.float32)
        self.closed = False
        self.phases = target_rate // math.gcd(source_rate, target_rate)
        cutoff = .94 * min(1.0, target_rate/source_rate)
        offsets = np.arange(-half, half+1)
        self.filters = []
        for phase in range(self.phases):
            distance = offsets-phase/self.phases
            window = np.i0(8.6*np.sqrt(np.maximum(0, 1-(distance/half)**2)))/np.i0(8.6)
            window[np.abs(distance)>half] = 0
            weights = cutoff*np.sinc(cutoff*distance)*window
            self.filters.append((weights/weights.sum()).astype(np.float32))

    def push(self, samples, *, final=False):
        if self.closed:
            raise ValueError("PCM resampler already finished")
        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim != 1 or not np.isfinite(samples).all():
            raise ValueError("TTS PCM must be finite mono samples")
        self.total += len(samples)
        if self.source == self.target:
            self.closed = final
            self.emitted += len(samples)
            return samples.copy()
        self.buffer = np.concatenate((self.buffer, samples))
        limit = (round(self.total*self.target/self.source) if final else
                 max(0, ((self.total-1-self.half)*self.target)//self.source+1))
        count = max(0, limit-self.emitted)
        output = np.empty(count, dtype=np.float32)
        if count:
            indexes = np.arange(self.emitted, limit, dtype=np.int64)
            bases = indexes*self.source//self.target
            phases = (indexes*(self.source//math.gcd(self.source,self.target))) % self.phases
            if self.phases <= 8:
                # The Kokoro 24->16 kHz path needs only two small C convolutions.
                padded = np.pad(self.buffer, (self.half, self.half))
                for phase in np.unique(phases):
                    selected = phases == phase
                    convolved = np.convolve(padded, self.filters[phase][::-1], mode='valid')
                    output[selected] = convolved[bases[selected]-self.start]
            else:
                offsets = np.arange(-self.half, self.half+1)
                filters = np.asarray(self.filters)
                for left in range(0,count,1024):
                    right = min(left+1024,count)
                    positions = bases[left:right,None]+offsets-self.start
                    valid = (positions>=0) & (positions<len(self.buffer))
                    values = self.buffer[np.clip(positions,0,len(self.buffer)-1)]*valid
                    output[left:right] = np.sum(values*filters[phases[left:right]],axis=1)
            self.emitted = limit
            keep_from = max(self.start, (self.emitted*self.source)//self.target-self.half)
            remove = min(len(self.buffer),keep_from-self.start)
            self.buffer = self.buffer[remove:].copy()
            self.start += remove
        if final:
            self.closed = True
            self.buffer = np.empty(0,dtype=np.float32)
        return output

    def finish(self):
        return self.push(np.empty(0,dtype=np.float32),final=True)
