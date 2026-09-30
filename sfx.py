#!/usr/bin/env python3
"""The eight sound effects: what a menu, a hit and a heal sound like.

The order is a contract -- index here == the SFX_* constant in src/ttrpg.h, and
the order audio.c loads them -- so do not reorder.

They used to be full-scale swept sines at 16kHz, played at nearly full volume
over the music: a bright 1-1.3kHz blip on every cursor move, twelve kilobytes
of them. Now they are soft and short and stored at 8kHz (they are played at
pitch 2, audio.c's SFX_PITCH, which is 8kHz on the DSP), which is half the ARAM,
and every one is a low, rounded sound: a tick, a chime, a thud, a shimmer.
Nothing here has energy above 3kHz worth mentioning, because the top of that
range is where the old ones lived.

The drum is the real thing. Tung Tung Tung Sahur is a slit drum; the SAHUR!
effect is the same recording the title theme plays, cut down.
"""
import math
import os

import numpy as np

import itwriter as it
import sfsample as sf

RATE = 8000            # stored rate; audio.c plays effects at pitch 2 = 8kHz
NAMES = ('cursor', 'confirm', 'hit', 'magic', 'heal', 'drum', 'error', 'death')


def _t(n):
    return np.arange(n) / float(RATE)


def _fade(x, ins=0.003, outs=0.02):
    n = len(x)
    a, b = int(RATE * ins), int(RATE * outs)
    if a:
        x[:a] *= np.linspace(0, 1, a)
    if b:
        x[n - b:] *= np.linspace(1, 0, b)
    return x


def _tone(f0, f1, n, decay, shape=1.0):
    """A sine gliding from f0 to f1 over n samples, decaying exponentially."""
    t = _t(n)
    f = f0 * (f1 / float(f0)) ** (np.arange(n) / float(n))
    ph = 2 * np.pi * np.cumsum(f) / RATE
    wave = np.sin(ph) + 0.18 * np.sin(2 * ph) * shape
    return wave * np.exp(-t / decay)


def _lp(x, k=3):
    for _ in range(k):
        x = (x + np.concatenate([[x[0]], x[:-1]])) / 2.0
    return x


def _noise(n, seed):
    r = np.random.RandomState(seed)
    return _lp(r.uniform(-1, 1, n), 3)


def _pad16(x):
    n = -(-len(x) // 16) * 16
    return np.concatenate([x, np.zeros(n - len(x))])


def _norm(x, peak=0.9):
    m = float(np.abs(x).max()) or 1.0
    return x * peak / m


def build():
    mod = it.Module('TUNGTUNG SFX', speed=6, tempo=125, channels=1)

    def add(name, x):
        x = _pad16(_fade(_norm(x)))
        mod.add_sample(it.Sample(name, x.tolist(), RATE))

    # a wooden tick, a little rising: something to hear, nothing to wince at
    add('cursor', _tone(560, 760, 400, 0.030))
    # two soft notes, a fifth apart: yes
    n = 380
    add('confirm', np.concatenate([_tone(523, 523, n, 0.05),
                                   _tone(784, 784, n, 0.07)]))
    # a thud: a low sine dropping away with a short rounded noise attack
    n = 1000
    thud = _tone(190, 62, n, 0.06) + 0.5 * _noise(n, 1) * np.exp(-_t(n) / 0.012)
    add('hit', thud)
    # a shimmer: a slow rise with a wobble, soft at both ends
    n = 1700
    t = _t(n)
    sweep = _tone(380, 1500, n, 0.15, shape=0.3)
    add('magic', sweep * (0.75 + 0.25 * np.sin(2 * np.pi * 14 * t))
        * np.sin(np.pi * np.minimum(1, t / 0.22)))
    # heal: four rising notes, each a soft bell
    notes = [523.25, 659.25, 783.99, 1046.5]
    add('heal', np.concatenate([_tone(f, f, 400, 0.08) for f in notes]))
    # drum: the kentongan, cut down
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'samples', 'slitdrum.wav')
    if not os.path.exists(path):
        raise SystemExit("samples/slitdrum.wav is missing -- run "
                         "'python3 fetch_samples.py' first.")
    d = sf.oneshot(path, rate=RATE, ms=150, tail_ms=40)
    mod.add_sample(it.Sample('drum', d.data, RATE))
    # error: a low, dull buzz, soft-edged
    n = 1000
    add('error', _lp(np.sign(np.sin(2 * np.pi * 95 * _t(n))), 5)
        * np.exp(-_t(n) / 0.09))
    # death: a long fall
    n = 1800
    add('death', _tone(420, 70, n, 0.22))

    mod.add_pattern(4, {})
    mod.orders.append(0)
    return mod


if __name__ == '__main__':
    m = build()
    total = sum(sf.brr_bytes(s) for s in m.samples)
    print("effects: %d, %d bytes of BRR" % (len(m.samples), total))
    for s in m.samples:
        print("   %-8s %5d samples %5d B" % (s.name, len(s.data), sf.brr_bytes(s)))
