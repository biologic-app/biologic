#!/usr/bin/env python3
"""Procedurally generate a funk groove (pure stdlib, royalty-free) for demo videos.

Usage: python3 make_funk.py [out.wav] [seconds]
Then mux onto a copy of the video:
  ffmpeg -y -i in.mp4 -i out.wav \\
    -filter_complex "[1:a]afade=t=out:st=<dur-1.5>:d=1.5[a]" \\
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest out-music.mp4
"""
import math, random, struct, sys, wave

OUT = sys.argv[1] if len(sys.argv) > 1 else 'funk.wav'
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 28.5
SR = 44100
BPM = 104.0
STEP = (60.0 / BPM) / 4.0
LOOP_STEPS = 32
LOOP_LEN = int(LOOP_STEPS * STEP * SR)
random.seed(7)

def saw(t, f): return 2.0 * ((t * f) - math.floor(0.5 + t * f))
def sq(t, f): return 1.0 if math.sin(2 * math.pi * f * t) >= 0 else -1.0
def env(i, n, a=0.004, d=2.5):
    t = i / SR
    return min(1.0, t / a) * math.exp(-d * t)

def bass(freq, dur, gain=0.95):
    n = int(dur * SR); out = [0.0] * n
    for i in range(n):
        t = i / SR
        v = 0.6 * saw(t, freq) + 0.5 * math.sin(2 * math.pi * freq * t) + 0.18 * math.sin(math.pi * freq * t)
        out[i] = math.tanh(v * 1.7) * env(i, n, 0.004, 3.2) * gain
    return out

def kick(dur=0.30, gain=1.0):
    n = int(dur * SR); out = [0.0] * n
    for i in range(n):
        t = i / SR
        f = 48 + (130 - 48) * math.exp(-32 * t)
        out[i] = math.tanh(math.sin(2 * math.pi * f * t) * 1.3) * math.exp(-6.5 * t) * gain
    return out

def snare(dur=0.20, gain=0.8):
    n = int(dur * SR); out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = ((random.random() * 2 - 1) * math.exp(-20 * t)
                  + 0.5 * math.sin(2 * math.pi * 185 * t) * math.exp(-26 * t)) * gain
    return out

def hat(dur=0.05, gain=0.32):
    n = int(dur * SR); out = [0.0] * n; prev = 0.0
    for i in range(n):
        t = i / SR; x = random.random() * 2 - 1
        out[i] = (x - prev) * math.exp(-55 * t) * gain; prev = x
    return out

def clav(freqs, dur=0.16, gain=0.5):
    n = int(dur * SR); out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = (sum(sq(t, f) for f in freqs) / len(freqs)) * (min(1.0, t / 0.003) * math.exp(-11 * t)) * gain
    return out

E2, G2, A2, B2, D3, E3 = 82.41, 98.00, 110.00, 123.47, 146.83, 164.81
EM = [E3, G2 * 2, B2]
kick_steps = {0, 6, 8, 11, 16, 22, 24, 27}
snare_steps = {4, 12, 20, 28}
open_steps = {14, 30}
clav_steps = {3, 10, 19, 26}
bass_riff = [E2, None, E3, E2, None, E2, G2, A2, None, E2, E2, D3, None, B2, A2, G2,
             E2, None, E3, E2, None, E2, G2, A2, None, E2, E2, B2, None, D3, A2, G2]

buf = [0.0] * LOOP_LEN
def place(start, s):
    for i, v in enumerate(s):
        j = start + i
        if 0 <= j < LOOP_LEN: buf[j] += v

for step in range(LOOP_STEPS):
    start = int(step * STEP * SR)
    if step in kick_steps: place(start, kick())
    if step in snare_steps: place(start, snare())
    place(start, hat(0.12 if step in open_steps else 0.05, 0.42 if step % 2 else 0.30))
    if step in clav_steps: place(start, clav(EM))
    nf = bass_riff[step]
    if nf is not None:
        place(start, bass(nf, STEP * (1.7 if step % 8 == 0 else 1.05), 1.05 if step % 8 == 0 else 0.9))

peak = max(1e-6, max(abs(x) for x in buf))
buf = [math.tanh(1.2 * x / peak) for x in buf]

total = int(SECONDS * SR)
data = bytearray()
for i in range(total):
    s = buf[i % LOOP_LEN] * 0.92
    if i < int(0.15 * SR): s *= i / (0.15 * SR)
    data += struct.pack('<h', int(max(-1.0, min(1.0, s)) * 32767))

with wave.open(OUT, 'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(bytes(data))
print(f'{OUT} written: {total / SR:.1f}s')
