#!/usr/bin/env python3
"""The two Impulse Tracker modules smconv packs into the SPC soundbank.

  res/ttsfx.it   one-shot effects. The sample order here *is* the index passed
                 to spcEffect(), so it must match the SFX_* constants in
                 src/ttrpg.h -- which is why the Makefile lists this module
                 first in AUDIOFILES.
  res/ttbgm.it   thirteen themes in one module, as ranges of one order list.

Thirteen themes in one module rather than thirteen modules: spcLoad is a
multi-frame transfer that clears SPC memory (and therefore the loaded effects
with it), and a battle that has to wait for one before the first gauge fills
reads as a hitch. With one module loaded at boot, changing theme is a single
spcPlay(order).

It also writes res/music.h with those ranges, so the module and the C cannot
drift.

    python3 gen_music.py --preview out.wav    audition every theme, no SNES

---- how the samples are tuned ---------------------------------------------

Every pitched instrument is one waveform of PERIOD samples repeated to a
multiple of 16 (the BRR block size) and looped whole, so the loop is
click-free by construction. A sample plays back at exactly C5Speed at note 60,
so C5Speed = 523.25 * PERIOD makes note 60 sound a C5 and every other note
land where a tracker would put it. Percussion carries its own rate and is
therefore only ever triggered at note 60.
"""
import math
import struct
import sys

import itwriter as it
import sfsample as sf
from fetch_samples import NOTES
from itwriter import N, NOTE_CUT, UNITY

SAMPLE_DIR = 'samples'

PERIOD = 32                         # samples per cycle of a pitched waveform
TONE_RATE = int(round(523.25 * PERIOD))
SFX_RATE = 16000

# ---- deterministic noise ------------------------------------------------


class Rng:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s >> 16

    def rand(self):
        return self.next() / 32768.0

    def pick(self, seq):
        return seq[self.next() % len(seq)]


# ---- waveform helpers ---------------------------------------------------

def _norm(buf, peak=0.92):
    m = max(abs(v) for v in buf) or 1.0
    return [v * peak / m for v in buf]


def _pad16(buf):
    while len(buf) % 16:
        buf.append(buf[len(buf) % len(buf)] if buf else 0.0)
    return buf


def harmonic_wave(cycles, partials, phase_drift=0.0):
    """A looping waveform: `cycles` periods built from (harmonic, amplitude)
    pairs. phase_drift walks the partials' phase across the sample, which is
    what keeps a pad from sounding like one frozen cycle."""
    n = cycles * PERIOD
    out = []
    for i in range(n):
        t = i / float(PERIOD)
        v = 0.0
        for k, (h, a) in enumerate(partials):
            ph = phase_drift * (i / float(n)) * (k + 1)
            v += a * math.sin(2 * math.pi * (h * t + ph))
        out.append(v)
    return _norm(out)


def pulse_wave(cycles, duty=0.25, soften=2):
    n = cycles * PERIOD
    out = []
    for i in range(n):
        ph = (i % PERIOD) / float(PERIOD)
        out.append(1.0 if ph < duty else -1.0)
    for _ in range(soften):             # a cheap one-pole smooth, twice
        out = [(out[i - 1] + out[i] * 2 + out[(i + 1) % n]) / 4.0
               for i in range(n)]
    return _norm(out)


def noise(n, rng, lp=0, hp=0):
    out = [rng.rand() * 2 - 1 for _ in range(n)]
    for _ in range(lp):
        out = [(out[max(0, i - 1)] + out[i]) / 2.0 for i in range(n)]
    for _ in range(hp):
        out = [out[i] - out[max(0, i - 1)] for i in range(n)]
    return _norm(out)


def decay(buf, tau):
    n = len(buf)
    return [v * math.exp(-i / (tau * n)) for i, v in enumerate(buf)]


def sweep(n, f0, f1, rate=SFX_RATE, shape='sin'):
    out = []
    ph = 0.0
    for i in range(n):
        t = i / float(n)
        f = f0 * ((f1 / f0) ** t)
        ph += 2 * math.pi * f / rate
        out.append(math.sin(ph) if shape == 'sin'
                   else (1.0 if math.sin(ph) > 0 else -1.0))
    return out


# ---- the instrument set -------------------------------------------------

# The orchestra. Each entry is what the tracker calls it, which file it is
# cut from, and how it is cut.
#
# Sustained instruments get an attack plus a looped body; the loop length is
# the whole budget decision, because BRR costs nine bytes per sixteen samples
# and all of this has to live in 64KB of ARAM alongside the sound effects.
#
# Rates are per instrument rather than global: a contrabass has nothing above
# 3kHz worth spending bytes on, and a glockenspiel is nothing but.
#
#      name       file        rate   attack  loop     what it is for
TONES = [
    ('bass',     'contra',    7000,   40,     70),   # low sustained strings
    ('lead',     'oboe',      9500,   50,     80),   # the melody voice
    ('pad',      'strings',   9000,   60,    100),   # violin section
    ('choir',    'organ',     9000,   50,     90),   # the pad under bosses
    ('horn',     'horn',      8500,   55,     80),   # brass, act openings
    ('brass',    'trumpet',   9000,   45,     80),   # bright heroic statements
    ('lowbrass', 'trombone',  8000,   55,     85),   # weight under battles
    ('flute',    'flute',     9000,   50,     80),   # the light melody voice
    ('cello',    'cello',     8000,   50,     80),   # countermelody
]

#      name       file        rate   ms    pitched as
HITS = [
    # A glockenspiel and a harp are struck and then decay; looping either one
    # holds a note that in life has already stopped, which is the single most
    # recognisable way for a sampled instrument to sound wrong. Both are
    # pitched one-shots instead, which is what the era did with them too.
    ('bell',     'glock',    10500,  210,   'C6'),
    ('pluck',    'harp',     10000,  230,   'C3'),
    ('spicc',    'viola_spic', 10000, 180,   'C5'),
    ('kick',     'bassdrum',  9000,  200,   None),
    ('snare',    'snare',    10000,  170,   None),
    ('hat',      'hihat',     9000,  110,   None),
    ('tom',      'timpani',   8000,  210,   None),
    # The kentongan. Pitched, so the title theme can play a figure on the
    # instrument the character is named after rather than just hitting it.
    ('drum',     'slitdrum', 10000,  180,   'A4'),
    ('drumlo',   'slitlow',  10000,  190,   'D4'),
]

# The glockenspiel's bars are inharmonic enough that the pitch detector locks
# a shared partial: its C5 and C6 recordings measure the same frequency. The
# filename is right and the measurement is not, so it is exempt.
NO_PITCH_CHECK = {'glock'}


def build_instruments(mod, report=False):
    """Returns a name -> instrument-number map, cut from the CC0 recordings in
    samples/. Pitched samples loop; percussion is one-shot.

    This is the same thing the 16-bit RPG soundtracks did: those scores are not
    synthesised, they are real instruments recorded, cut to a few hundred bytes,
    looped and played back through the SPC700. Feeding real orchestral material
    through the same meat grinder is what makes it sound like the era rather
    than like a chiptune.
    """
    import os

    if not os.path.isdir(SAMPLE_DIR):
        raise SystemExit(
            "%s/ is missing -- run 'python3 fetch_samples.py' first.\n"
            "It pulls the CC0 recordings the soundtrack is cut from; they are\n"
            "25MB of source for about 15KB of BRR, so they are not committed."
            % SAMPLE_DIR)

    ins = {}
    rows = []

    for name, fname, rate, attack, loop in TONES:
        path = os.path.join(SAMPLE_DIR, fname + '.wav')
        s = sf.looped(path, NOTES[fname], rate=rate, attack_ms=attack,
                      loop_ms=loop, check=fname not in NO_PITCH_CHECK)
        s.name = name
        ins[name] = mod.add_sample(s)
        rows.append((name, fname, len(s.data), sf.brr_bytes(s), 'loop@%d'
                     % s.loop_start))

    for name, fname, rate, ms, note in HITS:
        path = os.path.join(SAMPLE_DIR, fname + '.wav')
        s = sf.oneshot(path, rate=rate, ms=ms, note=note)
        s.name = name
        ins[name] = mod.add_sample(s)
        rows.append((name, fname, len(s.data), sf.brr_bytes(s),
                     note or 'one-shot'))

    if report:
        total = sum(r[3] for r in rows)
        print("instruments: %d, %d bytes of BRR" % (len(rows), total))
        for n, f, ln, br, how in rows:
            print("   %-7s %-9s %5d samples %5d B  %s" % (n, f, ln, br, how))
    return ins


# ---- pattern building ---------------------------------------------------

class Pat:
    def __init__(self, rows):
        self.rows = rows
        self.cells = {}

    def put(self, row, ch, note=None, inst=None, vol=None, cmd=None, param=0):
        if 0 <= row < self.rows:
            self.cells.setdefault(row, {})[ch] = (note, inst, vol, cmd, param)

    def emit(self, mod):
        return mod.add_pattern(self.rows, self.cells)


# Channel allocation, the same in every theme so the mix stays predictable.
CH_DRUM, CH_BASS, CH_LEAD, CH_ARP, CH_PAD, CH_CTR, CH_HAT, CH_FX = range(8)

def chord_notes(root, quality):
    if quality == 'min':
        return [root, root + 3, root + 7]
    if quality == 'maj':
        return [root, root + 4, root + 7]
    if quality == 'dim':
        return [root, root + 3, root + 6]
    if quality == 'sus':
        return [root, root + 5, root + 7]
    return [root, root + 4, root + 7, root + 10]


# ---- authored symphonic language ---------------------------------------
# Each original leitmotif is two bars of eighth-note slots. None sustains and
# 'r' breathes. Themes pair them into four-bar patterns, then develop the same
# ideas through different orchestration instead of generating random walks.

MOTIFS = {
    'noble':   (0, None, 7, 'r', 8, None, 7, 5,
                3, None, 5, 3, 2, None, 0, 'r'),
    'hymn':    (0, None, 4, 5, 7, None, 9, 7,
                5, None, 4, 2, 0, None, 'r', None),
    'answer':  (7, None, 8, 7, 5, 3, 2, 'r',
                3, None, 5, 7, 8, 7, 5, 'r'),
    'mystery': (0, None, 3, 'r', 7, None, 8, 7,
                3, None, 2, 'r', -2, None, 0, 'r'),
    'tide':    (0, 4, 7, 9, 7, 4, 2, 4,
                5, 9, 12, 9, 7, 5, 4, 2),
    'lament':  (12, None, 11, None, 8, None, 7, 'r',
                5, None, 3, None, 2, 1, 0, 'r'),
    'iron':    (0, 1, 0, -5, 0, 1, 3, 1,
                0, -2, -3, -2, 0, 1, 0, 'r'),
    'silence': (0, None, None, 'r', 1, None, None, 'r',
                6, None, 5, None, 1, None, 0, 'r'),
    'battle':  (0, 0, 3, 5, 7, 5, 3, 2,
                0, 0, 7, 8, 7, 5, 3, 'r'),
    'dread':   (0, None, 1, 0, 6, None, 5, 1,
                0, 1, 3, 1, 0, -2, -1, 'r'),
    'ascent':  (0, 2, 4, 5, 7, None, 9, 7,
                5, 4, 2, None, 0, None, 'r', None),
}


ORCHESTRATION = {
    'pastoral': dict(lead='flute', leadvol=40, pad='pad', pad2='pad',
                     padvol=17, counter='cello', counter_mode='answer',
                     ostinato='harp', bass='lyrical', percussion='gentle'),
    'overture': dict(lead='horn', leadvol=43, pad='pad', pad2='cello',
                     padvol=18, counter='brass', counter_mode='chorale',
                     ostinato='strings', bass='march',
                     percussion='procession', accent='lowbrass'),
    'mystic': dict(lead='flute', leadvol=37, pad='choir', pad2='pad',
                   padvol=15, counter='cello', counter_mode='contrary',
                   ostinato='harp_sparse', bass='pedal',
                   percussion='sparse'),
    'seascape': dict(lead='flute', leadvol=40, pad='pad', pad2='cello',
                     padvol=16, counter='cello', counter_mode='answer',
                     ostinato='harp_roll', bass='lyrical',
                     percussion='gentle'),
    'desolate': dict(lead='lead', leadvol=36, pad='choir', pad2='pad',
                     padvol=14, counter='cello', counter_mode='lament',
                     ostinato='harp_sparse', bass='pedal',
                     percussion='sparse'),
    'cathedral': dict(lead='brass', leadvol=44, pad='choir', pad2='pad',
                      padvol=17, counter='lowbrass',
                      counter_mode='brass_stab', ostinato='spicc',
                      bass='drive', percussion='martial',
                      accent='lowbrass'),
    'void': dict(lead='bell', leadvol=31, pad='choir', pad2='cello',
                 padvol=13, counter='cello', counter_mode='chorale',
                 ostinato='none', bass='pedal', percussion='ritual'),
    'combat': dict(lead='brass', leadvol=45, pad='pad', pad2='choir',
                   padvol=16, counter='horn', counter_mode='brass_stab',
                   ostinato='spicc', bass='drive', percussion='battle',
                   accent='lowbrass'),
    'boss': dict(lead='brass', leadvol=47, pad='choir', pad2='pad',
                 padvol=17, counter='lowbrass', counter_mode='contrary',
                 ostinato='spicc', bass='drive', percussion='siege',
                 accent='lowbrass'),
    'title': dict(lead='bell', leadvol=33, pad='choir', pad2='horn',
                  padvol=14, counter='horn', counter_mode='chorale',
                  ostinato='none', bass='pedal', percussion='ritual'),
    'resolution': dict(lead='flute', leadvol=40, pad='pad', pad2='cello',
                       padvol=17, counter='horn', counter_mode='answer',
                       ostinato='harp', bass='lyrical',
                       percussion='procession'),
}


def _command(p, row, ch, cmd, param):
    """Attach a command without erasing a note already in that tracker cell."""
    old = p.cells.get(row, {}).get(ch, (None, None, None, None, 0))
    p.put(row, ch, old[0], old[1], old[2], cmd, param)


def _write_harmony(p, ins, progression, st):
    for bar, (root, quality) in enumerate(progression):
        tones = chord_notes(root, quality)
        row = bar * 16
        p.put(row, CH_PAD, tones[0], ins[st['pad']], st['padvol'])
        p.put(row, CH_HAT, tones[1], ins[st['pad2']], st['padvol'] - 3)
    p.put(63, CH_PAD, NOTE_CUT)
    p.put(63, CH_HAT, NOTE_CUT)


def _write_bass(p, ins, progression, mode):
    for bar, (root, quality) in enumerate(progression):
        tones = chord_notes(root, quality)
        base = bar * 8
        if mode == 'pedal':
            events = ((0, tones[0] - 24, 31),)
        elif mode == 'lyrical':
            events = ((0, tones[0] - 12, 36),
                      (5, tones[2] - 12, 31))
        elif mode == 'march':
            events = ((0, tones[0] - 12, 38),
                      (4, tones[2] - 12, 34))
        else:
            events = tuple((slot, tones[0 if slot != 6 else 2] - 12,
                            39 if slot == 0 else 34)
                           for slot in (0, 2, 4, 6))
        for slot, note, vol in events:
            p.put((base + slot) * 2, CH_BASS, note, ins['bass'], vol)
    p.put(63, CH_BASS, NOTE_CUT)


def _write_ostinato(p, ins, progression, mode):
    if mode == 'none':
        return
    for bar, (root, quality) in enumerate(progression):
        tones = chord_notes(root, quality)
        base = bar * 8
        if mode == 'harp_sparse':
            slots, inst, vol = (0, 4), 'pluck', 15
        elif mode == 'harp':
            slots, inst, vol = (0, 2, 4, 6), 'pluck', 17
        elif mode == 'harp_roll':
            slots, inst, vol = range(8), 'pluck', 15
        elif mode == 'strings':
            slots, inst, vol = (0, 2, 4, 6), 'spicc', 19
        else:
            slots, inst, vol = range(8), 'spicc', 22
        for i, slot in enumerate(slots):
            p.put((base + slot) * 2, CH_ARP,
                  tones[i % len(tones)] + 12, ins[inst], vol)


def _write_counter(p, ins, progression, st):
    inst = st['counter']
    mode = st['counter_mode']
    if mode == 'answer':
        for phrase in (0, 16):
            for i, slot in enumerate((phrase + 11, phrase + 12,
                                      phrase + 13, phrase + 14)):
                root, quality = progression[min(slot // 8, 3)]
                tones = chord_notes(root, quality)
                p.put(slot * 2, CH_CTR, tones[(3 - i) % 3] + 12,
                      ins[inst], 24 if i == 0 else 20)
    else:
        for bar, (root, quality) in enumerate(progression):
            tones = chord_notes(root, quality)
            base = bar * 8
            if mode == 'chorale':
                p.put(base * 2, CH_CTR, tones[2], ins[inst], 20)
            elif mode == 'contrary':
                p.put(base * 2, CH_CTR, tones[2], ins[inst], 23)
                p.put((base + 4) * 2, CH_CTR, tones[1], ins[inst], 19)
            elif mode == 'lament':
                for i, slot in enumerate((0, 3, 6)):
                    p.put((base + slot) * 2, CH_CTR,
                          tones[(2 - i) % 3], ins[inst], 21 - i * 2)
            else:
                for slot in (0, 4):
                    row = (base + slot) * 2
                    p.put(row, CH_CTR, tones[0] + 12, ins[inst], 26)
                    p.put(row + 3, CH_CTR, NOTE_CUT)
    p.put(63, CH_CTR, NOTE_CUT)


def _write_percussion(p, ins, mode):
    patterns = {
        'gentle': ((0, 'tom', 31), (16, 'tom', 27)),
        'sparse': ((0, 'tom', 28), (24, 'drumlo', 22)),
        'procession': ((0, 'tom', 38), (4, 'snare', 25),
                       (8, 'kick', 31), (12, 'snare', 25),
                       (16, 'tom', 36), (20, 'snare', 25),
                       (24, 'kick', 31), (28, 'snare', 27)),
        'ritual': ((0, 'drum', 37), (2, 'drumlo', 31),
                   (4, 'drum', 34), (16, 'drum', 35),
                   (18, 'drumlo', 29), (20, 'drum', 32)),
        'martial': ((0, 'tom', 41), (4, 'snare', 31),
                    (8, 'kick', 36), (12, 'snare', 31),
                    (16, 'tom', 39), (20, 'snare', 31),
                    (24, 'kick', 36), (28, 'snare', 33)),
        'battle': ((0, 'kick', 40), (3, 'kick', 33),
                   (4, 'snare', 34), (7, 'kick', 34),
                   (8, 'tom', 41), (12, 'snare', 35),
                   (16, 'kick', 39), (19, 'kick', 33),
                   (20, 'snare', 34), (24, 'tom', 40),
                   (28, 'snare', 36), (30, 'kick', 34)),
        'siege': ((0, 'tom', 44), (4, 'snare', 35),
                  (6, 'kick', 37), (8, 'tom', 40),
                  (12, 'snare', 36), (14, 'kick', 36),
                  (16, 'tom', 43), (20, 'snare', 36),
                  (22, 'kick', 37), (24, 'tom', 41),
                  (28, 'snare', 38), (30, 'kick', 36)),
    }
    for slot, inst, vol in patterns[mode]:
        p.put(slot * 2, CH_DRUM, UNITY, ins[inst], vol)


def _write_accents(p, ins, progression, instrument):
    if not instrument:
        return
    for bar in (0, 2):
        root, quality = progression[bar]
        row = bar * 16
        p.put(row, CH_FX, chord_notes(root, quality)[0], ins[instrument], 27)
        p.put(row + 5, CH_FX, NOTE_CUT)


def build_theme(mod, ins, name, progressions, tempo, character, tonic,
                motif_pairs, speed=6, lead_sequence=None):
    """Build four-measure phrases with moving harmony and six musical parts."""
    if len(progressions) != len(motif_pairs):
        raise ValueError('%s: progression/motif count mismatch' % name)
    st = ORCHESTRATION[character]
    first = len(mod.patterns)

    for pi, (progression, pair) in enumerate(zip(progressions, motif_pairs)):
        if len(progression) != 4 or len(pair) != 2:
            raise ValueError('%s pattern %d: want four bars/two phrases'
                             % (name, pi))
        p = Pat(64)
        _write_harmony(p, ins, progression, st)
        _write_bass(p, ins, progression, st['bass'])
        _write_ostinato(p, ins, progression, st['ostinato'])
        _write_counter(p, ins, progression, st)
        _write_percussion(p, ins, st['percussion'])
        _write_accents(p, ins, progression, st.get('accent'))

        lead = (lead_sequence[pi % len(lead_sequence)] if lead_sequence
                else st['lead'])
        for phrase, motif_name in enumerate(pair):
            for i, event in enumerate(MOTIFS[motif_name]):
                row = (phrase * 16 + i) * 2
                if event is None:
                    continue
                if event == 'r':
                    p.put(row, CH_LEAD, NOTE_CUT)
                else:
                    p.put(row, CH_LEAD, tonic + 12 + event, ins[lead],
                          st['leadvol'] if i % 4 == 0 else st['leadvol'] - 6)
        p.put(63, CH_LEAD, NOTE_CUT)

        if pi == 0:
            _command(p, 0, CH_DRUM, 1, speed)
            _command(p, 0, CH_BASS, 20, tempo)
        if pi == len(progressions) - 1:
            _command(p, 63, CH_FX, 2, first)
        p.emit(mod)

    last = len(mod.patterns) - 1
    mod.orders.extend(range(first, last + 1))
    return name, first, last


def build_fanfare(mod, ins):
    """A compact brass-and-timpani victory cadence."""
    first = len(mod.patterns)
    p = Pat(32)
    root = N('C-4')
    for r, n in ((0, root), (2, root + 4), (4, root + 7),
                 (6, root + 12), (12, root + 7), (16, root + 16),
                 (20, root + 19), (24, root + 24)):
        p.put(r, CH_LEAD, n, ins['brass'], 46 if r < 16 else 49)
    for r, n in ((0, root + 7), (8, root + 12), (16, root + 12),
                 (24, root + 16)):
        p.put(r, CH_CTR, n, ins['horn'], 27)
    p.put(0, CH_DRUM, UNITY, ins['tom'], 42)
    p.put(8, CH_DRUM, UNITY, ins['snare'], 31)
    p.put(24, CH_DRUM, UNITY, ins['tom'], 44)
    p.put(0, CH_BASS, root - 24, ins['bass'], 39)
    p.put(8, CH_PAD, root, ins['choir'], 24)
    p.put(8, CH_ARP, root + 7, ins['pad'], 20)
    p.put(24, CH_HAT, root + 24, ins['bell'], 38)
    p.put(31, CH_PAD, NOTE_CUT)
    p.put(31, CH_ARP, NOTE_CUT)
    p.put(31, CH_CTR, NOTE_CUT)
    _command(p, 0, CH_DRUM, 1, 5)
    _command(p, 0, CH_BASS, 20, 150)
    _command(p, 31, CH_FX, 2, first)
    p.emit(mod)
    mod.orders.append(first)
    return 'FANFARE', first, first
# ---- the effects module -------------------------------------------------
#
# Order is the contract: index here == the SFX_* constant in src/ttrpg.h.

def build_sfx():
    mod = it.Module('TUNGTUNG SFX', speed=6, tempo=125, channels=1)
    rng = Rng(0xBEE5)

    def add(name, data):
        mod.add_sample(it.Sample(name, _pad16(list(data)), SFX_RATE))

    # Sine blips retain clear UI feedback without a square wave's permanent
    # stack of bright harmonics on every menu movement.
    add('cursor', _norm(decay(sweep(700, 1050, 1300), 0.25)))
    add('confirm', _norm(decay(sweep(1400, 750, 1250), 0.35)))

    hit_n = noise(1600, rng, lp=1)
    hit_t = sweep(1600, 260, 90)
    add('hit', _norm(decay([hit_n[i] * 0.7 + hit_t[i] * 0.8
                            for i in range(1600)], 0.20)))

    mg = sweep(4200, 300, 2600)
    mgn = noise(4200, rng, hp=1)
    add('magic', _norm(decay([mg[i] * 0.75 + mgn[i] * 0.3
                              for i in range(4200)], 0.55)))

    heal = []
    for k, f in enumerate((523.25, 659.25, 783.99, 1046.5)):
        seg = sweep(900, f, f)
        heal += decay(seg, 0.45)
    add('heal', _norm(heal))

    wood = noise(1500, rng, lp=2, hp=1)
    body = sweep(1500, 620, 380)
    add('drum', _norm(decay([wood[i] * 0.55 + body[i] * 0.8
                             for i in range(1500)], 0.18)))

    add('error', _norm(decay(sweep(2200, 190, 120, shape='sq'), 0.5)))
    add('death', _norm(decay(sweep(6000, 700, 90), 0.6)))

    # smconv wants at least one pattern and one order even for a bank that is
    # only ever used as a sample source.
    p = Pat(4)
    p.emit(mod)
    mod.orders.append(0)
    return mod


# ---- the music module ---------------------------------------------------

def build_bgm():
    """The complete original symphonic score, resident as one SPC module."""
    mod = it.Module(
        'TUNG TUNG SAHUR', speed=6, tempo=110, channels=8,
        global_volume=100,
        channel_pans=(32, 32, 23, 43, 38, 21, 45, 28),
        message=('[[SNESMOD]]\n'
                 'edl 3\n'
                 'efb 12\n'
                 'evol 14 14\n'
                 'efir -1 8 23 36 36 23 8 -1\n'
                 'eon 3 5 6\n'))
    ins = build_instruments(mod, report=True)
    sections = []

    C3, Cs3, D3, Eb3 = N('C-3'), N('C#3'), N('D-3'), N('D#3')
    E3, F3, Fs3, G3 = N('E-3'), N('F-3'), N('F#3'), N('G-3')
    Ab3, A3, Bb3, B3 = N('G#3'), N('A-3'), N('A#3'), N('B-3')
    C4, Cs4, D4, Eb4 = N('C-4'), N('C#4'), N('D-4'), N('D#4')
    E4 = N('E-4')

    def bars(*chords):
        return list(chords)

    # Kampung Sahur: woodwind hymn, harp and warm chamber strings.
    sections.append(build_theme(
        mod, ins, 'TOWN', [
            bars((F3, 'maj'), (C4, 'maj'), (D3, 'min'), (Bb3, 'maj')),
            bars((G3, 'min'), (C4, 'maj'), (F3, 'maj'), (C4, 'maj')),
            bars((F3, 'maj'), (A3, 'min'), (Bb3, 'maj'), (C4, 'maj')),
        ], 92, 'pastoral', F3,
        [('hymn', 'answer'), ('noble', 'hymn'), ('hymn', 'ascent')],
        lead_sequence=('flute', 'lead', 'flute')))

    # East road overture: the score's noble idea first appears in brass.
    sections.append(build_theme(
        mod, ins, 'FIELD', [
            bars((A3, 'min'), (F3, 'maj'), (C4, 'maj'), (G3, 'maj')),
            bars((D3, 'min'), (A3, 'min'), (E3, 'maj'), (E3, 'maj')),
            bars((A3, 'min'), (G3, 'maj'), (F3, 'maj'), (E3, 'maj')),
            bars((A3, 'min'), (C4, 'maj'), (D4, 'min'), (E4, 'maj')),
        ], 112, 'overture', A3,
        [('noble', 'ascent'), ('answer', 'noble'),
         ('lament', 'ascent'), ('noble', 'hymn')],
        lead_sequence=('horn', 'brass', 'lead', 'brass')))

    # Hutan: modal organ haze with fragments answering in the cello.
    sections.append(build_theme(
        mod, ins, 'FOREST', [
            bars((E3, 'min'), (D3, 'maj'), (C4, 'maj'), (E3, 'min')),
            bars((G3, 'maj'), (D4, 'maj'), (A3, 'min'), (B3, 'maj')),
            bars((E3, 'min'), (C4, 'maj'), (D4, 'sus'), (E3, 'min')),
        ], 82, 'mystic', E3,
        [('mystery', 'answer'), ('silence', 'mystery'),
         ('mystery', 'lament')], lead_sequence=('flute', 'lead', 'flute')))

    # Pantai: rolling harp figures give the harmony a broad tidal motion.
    sections.append(build_theme(
        mod, ins, 'SHORE', [
            bars((G3, 'maj'), (D4, 'maj'), (E3, 'min'), (C4, 'maj')),
            bars((A3, 'min'), (E3, 'min'), (C4, 'maj'), (D4, 'maj')),
            bars((G3, 'maj'), (B3, 'min'), (C4, 'maj'), (D4, 'maj')),
        ], 98, 'seascape', G3,
        [('tide', 'answer'), ('hymn', 'tide'), ('tide', 'ascent')],
        lead_sequence=('flute', 'lead', 'flute')))

    # Padang Garam: exposed oboe over organ, with no conventional drum kit.
    sections.append(build_theme(
        mod, ins, 'SALT', [
            bars((D3, 'min'), (Bb3, 'maj'), (G3, 'min'), (A3, 'maj')),
            bars((D3, 'min'), (C4, 'maj'), (Bb3, 'maj'), (A3, 'maj')),
            bars((G3, 'min'), (D3, 'min'), (Eb3, 'maj'), (A3, 'maj')),
        ], 74, 'desolate', D3,
        [('lament', 'silence'), ('mystery', 'lament'),
         ('silence', 'mystery')], lead_sequence=('lead', 'flute', 'lead')))

    # Langit Besi: pipe organ, chromatic trumpet and relentless low strings.
    sections.append(build_theme(
        mod, ins, 'FORTRESS', [
            bars((E3, 'min'), (F3, 'maj'), (E3, 'min'), (D3, 'dim')),
            bars((E3, 'min'), (C4, 'maj'), (F3, 'maj'), (B3, 'dim')),
            bars((E3, 'min'), (Eb3, 'maj'), (D3, 'dim'), (F3, 'maj')),
            bars((E3, 'min'), (F3, 'maj'), (B3, 'dim'), (E3, 'min')),
        ], 134, 'cathedral', E3,
        [('iron', 'dread'), ('battle', 'iron'),
         ('dread', 'battle'), ('iron', 'ascent')],
        lead_sequence=('brass', 'horn', 'brass', 'brass')))

    # Malam Panjang: ritual wood and a near-static, dissonant organ field.
    sections.append(build_theme(
        mod, ins, 'HUSH', [
            bars((A3, 'min'), (Bb3, 'maj'), (A3, 'min'), (Eb3, 'maj')),
            bars((A3, 'min'), (Fs3, 'dim'), (Bb3, 'maj'), (A3, 'min')),
        ], 62, 'void', A3,
        [('silence', 'mystery'), ('dread', 'silence')],
        lead_sequence=('bell', 'cello')))

    sections.append(build_theme(
        mod, ins, 'BATTLE', [
            bars((D3, 'min'), (Bb3, 'maj'), (C4, 'maj'), (A3, 'maj')),
            bars((D3, 'min'), (F3, 'maj'), (G3, 'min'), (A3, 'maj')),
            bars((Bb3, 'maj'), (C4, 'maj'), (D4, 'min'), (A3, 'maj')),
            bars((D3, 'min'), (C4, 'maj'), (Bb3, 'maj'), (A3, 'maj')),
        ], 154, 'combat', D3,
        [('battle', 'iron'), ('noble', 'battle'),
         ('dread', 'ascent'), ('battle', 'noble')],
        lead_sequence=('brass', 'horn', 'brass', 'brass')))

    sections.append(build_theme(
        mod, ins, 'BOSS', [
            bars((D3, 'min'), (Cs3, 'maj'), (C3, 'maj'), (B3, 'dim')),
            bars((D3, 'min'), (Ab3, 'maj'), (G3, 'min'), (Cs3, 'dim')),
            bars((D3, 'min'), (Eb3, 'maj'), (C3, 'min'), (Cs3, 'dim')),
            bars((D3, 'min'), (C3, 'maj'), (Bb3, 'maj'), (Cs3, 'dim')),
        ], 166, 'boss', D3,
        [('dread', 'battle'), ('iron', 'dread'),
         ('battle', 'lament'), ('dread', 'ascent')],
        lead_sequence=('lowbrass', 'brass', 'horn', 'brass')))

    # Il Silenzio: the same heroic contour is twisted before its final rise.
    sections.append(build_theme(
        mod, ins, 'FINAL', [
            bars((Eb3, 'min'), (B3, 'maj'), (Cs4, 'dim'), (D4, 'min')),
            bars((Eb3, 'min'), (E3, 'maj'), (B3, 'maj'), (D4, 'dim')),
            bars((Ab3, 'min'), (E3, 'maj'), (Fs3, 'dim'), (D4, 'min')),
            bars((Eb3, 'min'), (B3, 'maj'), (D4, 'dim'), (Eb3, 'min')),
        ], 178, 'boss', Eb3,
        [('dread', 'iron'), ('battle', 'silence'),
         ('lament', 'dread'), ('iron', 'ascent')],
        lead_sequence=('lowbrass', 'brass', 'horn', 'brass')))

    sections.append(build_fanfare(mod, ins))

    # Title begins with the namesake three-beat slit-drum call and grows from
    # bell to horn to full trumpet without borrowing another game's melody.
    sections.append(build_theme(
        mod, ins, 'TITLE', [
            bars((A3, 'min'), (F3, 'maj'), (C4, 'maj'), (E3, 'maj')),
            bars((A3, 'min'), (C4, 'maj'), (D4, 'min'), (E4, 'maj')),
            bars((F3, 'maj'), (G3, 'maj'), (A3, 'min'), (E3, 'maj')),
        ], 76, 'title', A3,
        [('silence', 'noble'), ('hymn', 'ascent'), ('noble', 'ascent')],
        lead_sequence=('bell', 'horn', 'brass')))

    # The epilogue resolves the road motif in C major and hands it from flute
    # to horn to trumpet, the score's one unambiguous sunrise.
    sections.append(build_theme(
        mod, ins, 'ENDING', [
            bars((C3, 'maj'), (G3, 'maj'), (A3, 'min'), (F3, 'maj')),
            bars((D3, 'min'), (A3, 'min'), (F3, 'maj'), (G3, 'maj')),
            bars((C3, 'maj'), (E3, 'min'), (F3, 'maj'), (G3, 'maj')),
            bars((F3, 'maj'), (G3, 'maj'), (C4, 'maj'), (C4, 'maj')),
        ], 90, 'resolution', C3,
        [('hymn', 'answer'), ('noble', 'hymn'),
         ('ascent', 'noble'), ('hymn', 'ascent')],
        lead_sequence=('flute', 'lead', 'horn', 'brass')))

    if len(mod.patterns) >= 64:
        raise ValueError('soundtrack exceeds SNESMOD 64-pattern budget')
    return mod, sections


def write_music_header(sections, path):
    with open(path, 'w') as f:
        f.write("/* Generated by gen_music.py -- do not edit.\n"
                " *\n"
                " * Order ranges of the themes inside res/ttbgm.it. The game\n"
                " * keeps one looping by watching spcGetMusicPosition() and\n"
                " * re-issuing spcPlay when the position leaves the range.\n"
                " * Every order plays the pattern of the same number, so these\n"
                " * hold whether that call reports an order or a pattern. */\n"
                "#ifndef TT_MUSIC_H\n#define TT_MUSIC_H\n\n")
        for name, first, last in sections:
            f.write("#define MUS_%s_FIRST %d\n" % (name, first))
            f.write("#define MUS_%s_LAST  %d\n" % (name, last))
        f.write("\n#endif\n")


# ---- preview render -----------------------------------------------------

def render(mod, path, rate=32000, max_seconds=140.0):
    """A crude stereo mixer: volume, pan and note, with no tracker effects
    beyond Axx/Txx. Enough to hear whether a theme is music."""
    speed, tempo = mod.speed, mod.tempo
    voices = [None] * mod.channels
    out = []
    limit = int(rate * max_seconds)

    for order in mod.orders:
        rows, cells = mod.patterns[order]
        for r in range(rows):
            row = cells.get(r, {})
            for ch, (note, inst, vol, cmd, param) in row.items():
                if cmd == 1:
                    speed = param or speed
                elif cmd == 20:
                    tempo = param or tempo
                if note is None:
                    continue
                if note >= 254:
                    voices[ch] = None
                    continue
                s = mod.samples[inst - 1] if inst else None
                if s is None:
                    continue
                step = (s.rate * (2.0 ** ((note - 60) / 12.0))) / rate
                voices[ch] = [s, 0.0, step, (vol if vol is not None else 48) / 64.0]

            frames = int(rate * (speed * 2.5 / tempo))
            for i in range(frames):
                left = right = 0.0
                for ch in range(mod.channels):
                    v = voices[ch]
                    if v is None:
                        continue
                    s, pos, step, gain = v
                    ip = int(pos)
                    if ip >= len(s.data):
                        if s.loop:
                            pos = s.loop_start + (pos - len(s.data))
                            ip = int(pos)
                        else:
                            voices[ch] = None
                            continue
                    pan = mod.channel_pans[ch] / 64.0
                    left += s.data[ip] * gain * math.cos(pan * math.pi / 2)
                    right += s.data[ip] * gain * math.sin(pan * math.pi / 2)
                    v[1] = pos + step
                out.append((left, right))
                if len(out) >= limit:
                    break
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break

    peak = max((max(abs(l), abs(r)) for l, r in out), default=1.0) or 1.0
    import wave
    w = wave.open(path, 'wb')
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(b''.join(struct.pack('<hh', int(l / peak * 26000),
                                       int(r / peak * 26000))
                           for l, r in out))
    w.close()
    return len(out) / float(rate)


def main():
    import os
    os.makedirs('res', exist_ok=True)

    sfx = build_sfx()
    n = it.write_it(sfx, 'res/ttsfx.it')
    print("res/ttsfx.it   %d bytes, %d effects" % (n, len(sfx.samples)))

    bgm, sections = build_bgm()
    n = it.write_it(bgm, 'res/ttbgm.it')
    print("res/ttbgm.it   %d bytes, %d patterns, %d samples"
          % (n, len(bgm.patterns), len(bgm.samples)))
    for name, first, last in sections:
        print("   %-8s orders %2d..%-2d" % (name, first, last))

    write_music_header(sections, 'res/music.h')

    if '--preview' in sys.argv:
        out = sys.argv[sys.argv.index('--preview') + 1]
        secs = render(bgm, out)
        print("rendered %.1fs to %s" % (secs, out))


if __name__ == '__main__':
    main()
