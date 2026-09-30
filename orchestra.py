#!/usr/bin/env python3
"""The orchestra: every instrument the score can ask for, and how it is cut.

An instrument here is one CC0 recording (see SAMPLES.md) plus the decisions
that turn it into SPC700 material: how many samples per cycle, how long an
attack to keep, how it ends. Only the instruments a score actually plays are
built into the module, so an unused one costs no ARAM.

Three kinds:

  loop   sustained: an attack and a loop of whole periods, tuned so that
         tracker note 60 is middle C. `p` is samples per cycle -- it sets how
         many harmonics survive (p/2) and, with the pitch, what the sample
         costs. `release` is how many ticks a note-off takes to die away.
  shot   struck or plucked and pitched: it plays once and stops. Tuned like a
         loop, so the same note numbers mean the same pitches everywhere.
  hit    unpitched percussion, triggered at note 60.

Levels: every sample is normalised to the same peak, and `gv` (0-64, a
multiplier that can only turn things down) balances them so that a given
tracker volume means about the same loudness on any instrument. The numbers
were set by rendering each instrument through the emulated DSP at volume 40
and matching loudness, not by ear; see calibrate.py.
"""
import hashlib
import json
import os

import numpy as np

import fetch_samples
import itwriter as it
import sfsample as sf

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples')
CACHE_DIR = os.path.join(SAMPLE_DIR, 'cache')


def _loop(file, label, p=32, attack=80, loop=100, max_loop=480, steady=None,
          tilt=0.0, release=8, swell=0, gv=64, bw=None):
    return dict(kind='loop', file=file, label=label, p=p, attack=attack,
                loop=loop, max_loop=max_loop, steady=steady, tilt=tilt,
                release=release, swell=swell, gv=gv, bw=bw)


def _shot(file, label, rate=10000, ms=240, tail=40, tilt=0.0, gv=64,
          measure='spectrum', lp=None):
    return dict(kind='shot', file=file, label=label, rate=rate, ms=ms,
                tail=tail, tilt=tilt, gv=gv, measure=measure, lp=lp)


def _hit(file, rate=10000, ms=170, tail=40, tilt=0.0, gv=64, lp=None):
    return dict(kind='hit', file=file, rate=rate, ms=ms, tail=tail, tilt=tilt,
                gv=gv, lp=lp)


# name: spec. Labels are the *sounding* scientific pitch of the recording,
# which for the VSCO strings, winds and brass is one octave above the number
# in the file name; the build measures every one and stops if it disagrees.
INSTRUMENTS = {
    # ---- strings ----
    'bass':     _loop('contra',     'E3',  p=32, attack=90, loop=120, release=10),
    'bass_lo':  _loop('bass_lo',    'A#1', p=32, attack=110, loop=200, release=10),
    'cello':    _loop('cello',      'C4',  p=32, attack=90, loop=110, release=9),
    'cello_lo': _loop('cello_lo',   'C2',  p=32, attack=120, loop=200, release=10),
    'viola':    _loop('viola',      'D4',  p=32, attack=90, loop=110, release=9),
    'strings':  _loop('strings',    'C5',  p=24, attack=70, loop=90, release=9,
                      tilt=-1.5),
    'strings_lo': _loop('strings_lo', 'G3', p=32, attack=90, loop=110, release=9),
    'violin':   _loop('violin',     'A4',  p=24, attack=80, loop=100, release=8,
                      tilt=-6.0, bw=9),
    # ---- winds ----
    'flute':    _loop('flute',      'C5',  p=24, attack=70, loop=90, release=7,
                      tilt=-1.5),
    'oboe':     _loop('oboe',       'D5',  p=24, attack=70, loop=90, release=6,
                      tilt=-2.5),
    'clarinet': _loop('clarinet',   'F4',  p=32, attack=80, loop=110, release=7),
    'bassoon':  _loop('bassoon',    'G3',  p=32, attack=90, loop=140, release=7),
    # ---- brass ----
    'horn':     _loop('horn',       'C4',  p=32, attack=80, loop=110, release=8),
    'trumpet':  _loop('trumpet',    'C4',  p=24, attack=60, loop=90, release=5,
                      tilt=-6.0, bw=7),
    'trombone': _loop('trombone',   'D3',  p=32, attack=80, loop=130, release=7),
    'tuba':     _loop('tuba',       'D3',  p=32, attack=90, loop=150, release=7),
    # ---- keys ----
    'organ':    _loop('organ',      'C4',  p=24, attack=50, loop=100, release=6,
                      tilt=-6.0, bw=8),
    # ---- plucked and struck, pitched ----
    'harp':     _shot('harp',       'C3',  rate=10000, ms=220, measure='yin',
                      tilt=-3.0, lp=5000),
    'dantranh': _shot('dantranh',   'B4',  rate=10000, ms=200, measure='yin',
                      tilt=-2.5, lp=6000),
    'marimba':  _shot('marimba',    'C5',  rate=9000, ms=200),
    'balafon':  _shot('balafon',    'C5',  rate=9000, ms=210, tilt=-1.5),
    'glock':    _shot('glock',      'C7',  rate=10000, ms=180, tilt=-2.0),
    'tubebell': _shot('tubebell',   'C5',  rate=9000, ms=260, measure=False,
                      tilt=-3.0, lp=6000),
    'pizz_vln': _shot('pizz_vln',   'A4',  rate=9000, ms=150, measure='yin',
                      tilt=-2.5),
    'pizz_vlc': _shot('pizz_vlc',   'A3',  rate=8000, ms=170, measure='yin'),
    'pizz_cb':  _shot('pizz_cb',    'A2',  rate=5000, ms=240, measure='yin'),
    'spicc':    _shot('viola_spic', 'C5',  rate=9000, ms=150, tilt=-3.0),
    # A timpani part is tuned. Its perceived pitch is not its strongest
    # partial (the (1,1) mode); measured with the period detector it is F#2.
    'timp':     _shot('timpani',    'F#2', rate=7000, ms=240, measure=False),
    # ---- kentongan: the slit drum the game is named after ----
    'kentong':  _shot('slitdrum',   'D#3', rate=9000, ms=160),
    'kentong_lo': _shot('slitlow',  'A2',  rate=9000, ms=170),
    # ---- percussion ----
    'kick':     _hit('bassdrum',    rate=8000, ms=180),
    'snare':    _hit('snare',       rate=9000, ms=150, tilt=-2.0),
    'hat':      _hit('hihat',       rate=8000, ms=90, tilt=-2.0, lp=5500),
    'gong':     _hit('gong',        rate=6000, ms=380),
    'cymbal':   _hit('cymbal',      rate=9000, ms=230, tilt=-3.0, lp=6000),
    'tambourine': _hit('tambourine', rate=9000, ms=120, tilt=-3.0, lp=5500),
    'triangle': _hit('triangle',    rate=10000, ms=170, tilt=-3.0, lp=6500),
    'claves':   _hit('claves',      rate=9000, ms=60, tilt=-2.0),
    'anvil':    _hit('anvil',       rate=9000, ms=170, tilt=-2.0),
}


# Calibrated by playing each instrument at tracker volume 40 through the
# emulated DSP and matching K-weighted loudness to the quietest of the sustained
# voices (the trumpet, at -26 LUFS). A voice can only be turned *down* by its
# sample volume, so the loud ones are attenuated and the trumpet stays at
# unity. The consequence worth knowing when writing a part: on any sustained
# instrument, volume 40 is "mezzo-forte" and means the same loudness.
LEVELS = {
    'bass': 45, 'bass_lo': 42, 'cello': 41, 'cello_lo': 39, 'viola': 33,
    'strings': 39, 'strings_lo': 34, 'violin': 57, 'flute': 28, 'oboe': 39,
    'clarinet': 27, 'bassoon': 37, 'horn': 39, 'trumpet': 64, 'trombone': 51,
    'tuba': 51, 'organ': 34,
    'tubebell': 48, 'hat': 40, 'cymbal': 40, 'tambourine': 40, 'triangle': 40,
    'gong': 50, 'snare': 56, 'claves': 56, 'anvil': 56,
}
for _n, _g in LEVELS.items():
    INSTRUMENTS[_n]['gv'] = _g


# The compass each instrument is written in, as sounding pitch: the outer
# limits, past which the recording stretched over the note stops sounding like
# the instrument. The score checker enforces these; the numbers are the real
# instruments' ranges pulled in by how far a single recording can be pitched
# before it goes hollow or nasal (about an octave and a half either way).
RANGE = {
    'bass': ('E1', 'G3'), 'bass_lo': ('C1', 'A#2'),
    'cello': ('C3', 'E5'), 'cello_lo': ('C2', 'G3'),
    'viola': ('G3', 'C6'), 'strings': ('C4', 'E6'),
    'strings_lo': ('G3', 'D5'), 'violin': ('G3', 'A6'),
    'flute': ('D4', 'C7'), 'oboe': ('C4', 'G6'), 'clarinet': ('E3', 'G6'),
    'bassoon': ('C2', 'C5'),
    'horn': ('A2', 'F5'), 'trumpet': ('G3', 'C6'), 'trombone': ('E2', 'F4'),
    'tuba': ('D1', 'D3'),
    'organ': ('C2', 'C7'),
    'harp': ('C2', 'G5'), 'dantranh': ('A3', 'E6'), 'marimba': ('F3', 'C6'),
    'balafon': ('G3', 'C6'), 'glock': ('G5', 'C8'), 'tubebell': ('C4', 'C6'),
    'pizz_vln': ('G3', 'A5'), 'pizz_vlc': ('C3', 'E5'),
    'pizz_cb': ('E1', 'A3'), 'spicc': ('G3', 'C6'),
    'kentong': ('D#2', 'D#4'), 'kentong_lo': ('A1', 'A3'),
    'timp': ('D2', 'B2'),
}


def _key(name, spec):
    """A cache key that changes when the recording, the recipe, or the code
    that applies it changes."""
    src = fetch_samples.SHA256.get(spec['file']) or ''
    with open(sf.__file__.replace('.pyc', '.py'), 'rb') as f:
        code = hashlib.sha256(f.read()).hexdigest()[:16]
    blob = json.dumps([name, spec, src, code], sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:20]


def _make(name, spec):
    path = os.path.join(SAMPLE_DIR, spec['file'] + '.wav')
    if spec['kind'] == 'loop':
        s = sf.looped(path, spec['label'], p=spec['p'],
                      attack_ms=spec['attack'], loop_ms=spec['loop'],
                      max_loop=spec['max_loop'], steady_ms=spec['steady'],
                      tilt_db=spec['tilt'], bw_harm=spec['bw'])
    elif spec['kind'] == 'shot':
        s = sf.oneshot(path, rate=spec['rate'], ms=spec['ms'],
                       tail_ms=spec['tail'], label=spec['label'],
                       tilt_db=spec['tilt'], measure=spec['measure'],
                       lp=spec['lp'])
    else:
        s = sf.oneshot(path, rate=spec['rate'], ms=spec['ms'],
                       tail_ms=spec['tail'], tilt_db=spec['tilt'],
                       lp=spec['lp'])
    s.name = name
    s.gv = spec['gv']
    if spec['kind'] == 'loop':
        _sustain(s, spec['release'], spec['swell'])
    return s


def _sustain(s, release, swell):
    """Give a sustained instrument its envelope and release.

    The envelope is not decoration. In this SNESMOD build an instrument with
    no envelope starts its fadeout the instant a note is *struck* (the test in
    Channel_ProcessEnvelope is the wrong way round for its own comment), so
    the note dies in a few ticks whatever the score says. With an envelope the
    driver holds at the sustain node while the key is down, runs on to the last
    node at key-off, and only then starts the fade -- which is what a note-off
    is supposed to be. `swell` (ticks) is an optional rise from a quarter
    level, for the bowed and blown instruments whose attack is not instant."""
    s.fadeout = int(round(1020.0 / release))
    if swell:
        s.env = [(0, 24), (swell, 64), (swell + 1, 64)]
        s.sustain = 1
    else:
        s.env = [(0, 64), (1, 64)]
        s.sustain = 0


def build(name):
    """One instrument, from cache if the recipe and code are unchanged."""
    spec = INSTRUMENTS[name]
    os.makedirs(CACHE_DIR, exist_ok=True)
    key = _key(name, spec)
    path = os.path.join(CACHE_DIR, '%s-%s.npz' % (name, key))
    if os.path.exists(path):
        z = np.load(path, allow_pickle=False)
        s = it.Sample(name, z['data'].tolist(), int(z['rate']),
                      loop=bool(z['loop']), loop_start=int(z['loop_start']),
                      gv=spec['gv'])
        s.fadeout = int(z['fadeout'])
        if s.loop:
            _sustain(s, spec['release'], int(z['swell']))
        s.cycle = float(z['cycle'])
        s.periods = int(z['periods'])
        s.f0 = float(z['f0'])
        s.root = str(z['root'])
        return s
    for old in os.listdir(CACHE_DIR):
        if old.startswith(name + '-') and old.endswith('.npz'):
            os.remove(os.path.join(CACHE_DIR, old))
    s = _make(name, spec)
    np.savez(path, data=np.asarray(s.data), rate=s.rate, loop=int(s.loop),
             loop_start=s.loop_start, fadeout=s.fadeout,
             swell=spec.get('swell', 0), cycle=getattr(s, 'cycle', 0.0),
             periods=getattr(s, 'periods', 0),
             f0=float(getattr(s, 'f0', 0.0) or 0.0),
             root=str(getattr(s, 'root', '') or ''))
    return s


def build_instruments(mod, names, report=False):
    """Add the named instruments to `mod`; returns name -> instrument number.
    Order follows `names`, so the module layout is the score's decision."""
    ins = {}
    rows = []
    for name in names:
        if name not in INSTRUMENTS:
            raise KeyError("no instrument called %r" % name)
        s = build(name)
        ins[name] = mod.add_sample(s)
        rows.append((name, len(s.data), sf.brr_bytes(s),
                     'loop@%d x%d' % (s.loop_start, getattr(s, 'periods', 0))
                     if s.loop else 'one-shot'))
    if report:
        total = sum(r[2] for r in rows)
        print("instruments: %d, %d bytes of BRR" % (len(rows), total))
        for n, ln, br, how in rows:
            print("   %-11s %5d samples %5d B  %s" % (n, ln, br, how))
    return ins


if __name__ == '__main__':
    import sys
    m = it.Module('orchestra')
    build_instruments(m, sys.argv[1:] or list(INSTRUMENTS), report=True)
