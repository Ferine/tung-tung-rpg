#!/usr/bin/env python3
"""The two Impulse Tracker modules smconv packs into the SPC soundbank.

  res/ttsfx.it   one-shot effects. The sample order here *is* the index passed
                 to spcEffect(), so it must match the SFX_* constants in
                 src/ttrpg.h -- which is why the Makefile lists this module
                 first in AUDIOFILES.
  res/ttbgm.it   five themes in one module, as five ranges of one order list.

Five themes in one module rather than five modules: spcLoad is a multi-frame
transfer that clears SPC memory (and therefore the loaded effects with it), and
a battle that has to wait for one before the first gauge fills reads as a hitch.
With one module loaded at boot, changing theme is a single spcPlay(order).

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
    ('lead',     'oboe',     11000,   50,     80),   # the melody voice
    ('pad',      'strings',  10000,   60,    100),   # violin section
    ('choir',    'organ',     9000,   50,     90),   # the pad under bosses
    ('horn',     'horn',      9000,   55,     80),   # brass, act openings
    ('flute',    'flute',    10000,   50,     80),   # the light melody voice
    ('cello',    'cello',     8000,   50,     80),   # countermelody
]

#      name       file        rate   ms    pitched as
HITS = [
    # A glockenspiel and a harp are struck and then decay; looping either one
    # holds a note that in life has already stopped, which is the single most
    # recognisable way for a sampled instrument to sound wrong. Both are
    # pitched one-shots instead, which is what the era did with them too.
    ('bell',     'glock',    13000,  210,   'C6'),
    ('pluck',    'harp',     11000,  230,   'C3'),
    ('kick',     'bassdrum',  9000,  200,   None),
    ('snare',    'snare',    12000,  170,   None),
    ('hat',      'hihat',    12000,  110,   None),
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
            "21MB of source for about 16KB of ROM, so they are not committed."
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

MINOR = [0, 2, 3, 5, 7, 8, 10]
MAJOR = [0, 2, 4, 5, 7, 9, 11]
DORIAN = [0, 2, 3, 5, 7, 9, 10]
PHRYG = [0, 1, 3, 5, 7, 8, 10]


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


# ---- style sheets -------------------------------------------------------
#
# A theme is a progression plus one of these. Parameterising rather than
# switching on a name is what makes thirteen tracks affordable: each is a
# dozen numbers, not a dozen functions.

STYLE = {
    # kick/snare/hat are the kit; bass, mel, pad, arp, lead are as before.
    #
    # ctr and accent are the orchestra. CH_CTR and CH_FX sat unused through
    # thirteen themes -- eight channels and six of them doing anything -- so
    # the brass, the cello and the flute now have somewhere to play, and the
    # timpani has somewhere to land.
    #
    #   ctr     instrument for the countermelody
    #   ctrmode sustain = a held chord tone under the melody
    #           stab    = on the beat, for anything with a pulse
    #           answer  = a phrase in the back half of the bar, in the gap
    #                     the melody tends to leave
    #   accent  sixteenths that get a timpani
    #   call    the kentongan figure -- the slit drum, high and low
    #           alternating. Tung Tung Tung. It is the title of the game and
    #           until now it was the one instrument in the bank that never
    #           played.
    'town':     dict(kick=(0, 8), snare=(), hat=0, bass='soft',
                     mel=45, pad='pad', arp=0, lead='bell', drum='drum',
                     ctr='flute', ctrmode='answer', accent=()),
    'field':    dict(kick=(0, 8), snare=(), hat=6, bass='soft',
                     mel=55, pad='pad', arp=0, lead='lead', drum='drum',
                     ctr='horn', ctrmode='sustain', accent=()),
    'forest':   dict(kick=(0,), snare=(), hat=0, bass='low',
                     mel=40, pad='choir', arp=0, lead='pluck', drum='tom',
                     ctr='cello', ctrmode='sustain', accent=()),
    'shore':    dict(kick=(0, 8), snare=(), hat=4, bass='soft',
                     mel=50, pad='pad', arp=1, lead='bell', drum='drum',
                     ctr='flute', ctrmode='answer', accent=()),
    'salt':     dict(kick=(0,), snare=(), hat=0, bass='low',
                     mel=35, pad='choir', arp=1, lead='bell', drum='drum',
                     ctr='cello', ctrmode='sustain', accent=(0,)),
    'fortress': dict(kick=(0, 4, 8, 12), snare=(4, 12), hat=2, bass='drive',
                     mel=60, pad='choir', arp=1, lead='lead', drum='kick',
                     ctr='horn', ctrmode='stab', accent=(0, 8)),
    'hush':     dict(kick=(), snare=(), hat=0, bass='drone',
                     mel=22, pad='choir', arp=0, lead='bell', drum='drum',
                     ctr='cello', ctrmode='sustain', accent=(0,),
                     call=(0, 3, 6)),
    'battle':   dict(kick=(0, 4, 8, 12), snare=(4, 12), hat=2, bass='drive',
                     mel=70, pad='choir', arp=1, lead='lead', drum='kick',
                     ctr='horn', ctrmode='stab', accent=(0,)),
    'boss':     dict(kick=(0, 3, 6, 8, 12), snare=(4, 12), hat=0, bass='drive',
                     mel=70, pad='choir', arp=1, lead='lead', drum='kick',
                     ctr='horn', ctrmode='stab', accent=(0, 8)),
    'final':    dict(kick=(0, 2, 4, 6, 8, 10, 12, 14), snare=(4, 12), hat=1,
                     bass='drive', mel=75, pad='choir', arp=1, lead='lead',
                     drum='kick', ctr='horn', ctrmode='stab',
                     accent=(0, 4, 8, 12)),
    'title':    dict(kick=(), snare=(), hat=0, bass='drone',
                     mel=30, pad='choir', arp=0, lead='bell', drum='drum',
                     ctr='horn', ctrmode='sustain', accent=(0,),
                     call=(0, 2, 4)),
    'ending':   dict(kick=(0, 8), snare=(), hat=0, bass='soft',
                     mel=40, pad='pad', arp=1, lead='bell', drum='drum',
                     ctr='flute', ctrmode='answer', accent=()),
}


def build_theme(mod, ins, name, prog, rows, tempo, speed, style, seed,
                scale=MINOR):
    """One theme: len(prog) patterns of `rows` rows, one chord each.

    The melody is a random walk that lands on a chord tone every strong beat
    and passes through the scale between them -- enough structure to sound
    written rather than shuffled, and far less to author than sixty-four rows
    of notes a pattern, thirteen times over.
    """
    rng = Rng(seed)
    st = STYLE[style]
    first = len(mod.patterns)
    beat = rows // 16

    for pi, (root, quality) in enumerate(prog):
        p = Pat(rows)
        tones = chord_notes(root, quality)
        sc = [root + s for s in scale]

        if pi == 0:
            p.put(0, CH_DRUM, cmd=1, param=speed)     # Axx speed
            p.put(0, CH_BASS, cmd=20, param=tempo)    # Txx tempo

        # --- percussion ----------------------------------------------------
        for s in st['kick']:
            p.put(s * beat, CH_DRUM, UNITY, ins[st['drum']], 60)
        for s in st['snare']:
            p.put(s * beat, CH_DRUM, UNITY, ins['snare'], 54)
        if st['hat']:
            for s in range(0, 16, st['hat']):
                p.put(s * beat, CH_HAT, UNITY, ins['hat'], 24)

        # --- bass ----------------------------------------------------------
        mode = st['bass']
        if mode == 'drive':
            for s in range(16):
                n = tones[0] - 12
                if s % 8 == 6:
                    n = tones[2] - 12
                p.put(s * beat, CH_BASS, n, ins['bass'], 52)
        elif mode == 'soft':
            for s in (0, 6, 8, 14):
                p.put(s * beat, CH_BASS,
                      (tones[0] if s < 8 else tones[1]) - 12, ins['bass'], 46)
        elif mode == 'low':
            for s in (0, 10):
                p.put(s * beat, CH_BASS, tones[0] - 24, ins['bass'], 44)
        else:                                          # drone
            p.put(0, CH_BASS, tones[0] - 24, ins['bass'], 34)
            p.put(rows - 1, CH_BASS, NOTE_CUT)

        # --- pad and arpeggio ----------------------------------------------
        p.put(0, CH_PAD, tones[0], ins[st['pad']], 26)
        p.put(rows - 1, CH_PAD, NOTE_CUT)
        if st['arp']:
            for s in range(16):
                p.put(s * beat, CH_ARP, tones[s % len(tones)] + 12,
                      ins['pluck'], 20)
        else:
            p.put(0, CH_ARP, tones[1], ins['pad'], 18)
            p.put(rows - 1, CH_ARP, NOTE_CUT)

        # --- melody ---------------------------------------------------------
        cur = tones[rng.next() % len(tones)] + 12
        for s in range(16):
            r = s * beat
            strong = (s % 4 == 0)
            if strong:
                cand = [t + 12 for t in tones] + [t + 24 for t in tones]
                cur = min(cand, key=lambda v: abs(v - cur) + rng.next() % 3)
            elif rng.next() % 100 < st['mel']:
                near = min(sc, key=lambda v: abs((v + 12) - cur))
                idx = sc.index(near)
                cur = sc[(idx + rng.pick([-2, -1, 1, 2])) % len(sc)] + 12 \
                    + (12 if cur >= root + 24 else 0)
            else:
                continue
            p.put(r, CH_LEAD, cur, ins[st['lead']], 54 if strong else 42)

        # --- the call -------------------------------------------------------
        # High, low, high: a kentongan has two tones and that is the whole
        # instrument. Only on themes with no kick, because it shares CH_DRUM.
        for i, s in enumerate(st.get('call', ())):
            p.put(s * beat, CH_DRUM, UNITY,
                  ins['drum' if i % 2 == 0 else 'drumlo'], 56 - i * 6)

        # --- countermelody --------------------------------------------------
        ctr = st.get('ctr')
        if ctr:
            mode = st.get('ctrmode', 'sustain')
            if mode == 'sustain':
                # A held third, an octave under the tune. This is the line
                # that turns a melody over a pad into an arrangement.
                p.put(0, CH_CTR, tones[1], ins[ctr], 24)
                p.put(rows - 1, CH_CTR, NOTE_CUT)
            elif mode == 'stab':
                for s in (0, 4, 8, 12):
                    p.put(s * beat, CH_CTR, tones[0] + 12, ins[ctr],
                          32 if s == 0 else 26)
                    p.put(s * beat + max(1, beat // 2), CH_CTR, NOTE_CUT)
            elif mode == 'answer':
                # Four notes up the scale in the back half of the bar, which
                # is where the melody's random walk tends to leave a hole.
                base = sc.index(min(sc, key=lambda v: abs(v - tones[1])))
                for i, s in enumerate((9, 10, 11, 13)):
                    p.put(s * beat, CH_CTR, sc[(base + i) % len(sc)] + 12,
                          ins[ctr], 30 if i == 0 else 24)
                p.put(rows - 1, CH_CTR, NOTE_CUT)

        # --- timpani --------------------------------------------------------
        for s in st.get('accent', ()):
            p.put(s * beat, CH_FX, UNITY, ins['tom'], 44 if s == 0 else 34)

        p.emit(mod)

    last = len(mod.patterns) - 1
    for i in range(first, last + 1):
        mod.orders.append(i)
    return name, first, last


def build_fanfare(mod, ins):
    """The victory jingle: the one piece written out rather than generated,
    because everybody already knows what it is supposed to do."""
    first = len(mod.patterns)
    p = Pat(32)
    p.put(0, CH_DRUM, cmd=1, param=5)
    p.put(0, CH_BASS, cmd=20, param=150)

    root = N('C-5')
    for r, n in ((0, root), (2, root + 4), (4, root + 7), (6, root + 12)):
        p.put(r, CH_LEAD, n, ins['bell'], 60)
        p.put(r, CH_DRUM, UNITY, ins['drum'], 48)
    p.put(8, CH_LEAD, root + 12, ins['bell'], 64)
    p.put(8, CH_PAD, root, ins['choir'], 40)
    p.put(8, CH_ARP, root + 7, ins['pad'], 34)
    p.put(8, CH_BASS, root - 24, ins['bass'], 54)
    p.put(16, CH_LEAD, root + 16, ins['bell'], 60)
    p.put(20, CH_LEAD, root + 19, ins['bell'], 62)
    p.put(24, CH_LEAD, root + 24, ins['bell'], 64)
    p.put(24, CH_DRUM, UNITY, ins['snare'], 48)
    p.put(31, CH_PAD, NOTE_CUT)
    p.put(31, CH_ARP, NOTE_CUT)
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

    add('cursor', _norm(decay(sweep(700, 1400, 1750, shape='sq'), 0.25)))
    add('confirm', _norm(decay(sweep(1400, 900, 1900, shape='sq'), 0.35)))

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
    """Thirteen themes in one module: one per region, three for fights, plus
    the title, the fanfare and the epilogue.

    One module rather than thirteen because spcLoad is a multi-frame transfer
    that also clears the loaded effects; with everything resident, changing
    theme is a single spcPlay(order). The cost is the 64-pattern ceiling, which
    is why regions get two or three patterns and only the fights get four."""
    mod = it.Module('TUNG TUNG SAHUR', speed=6, tempo=110, channels=8)
    ins = build_instruments(mod)
    sections = []

    A, Bb, B = N('A-3'), N('A#3'), N('B-3')
    C, Cs, D, Eb = N('C-4'), N('C#4'), N('D-4'), N('D#4')
    E, F, Fs, G = N('E-4'), N('F-3'), N('F#3'), N('G-3')

    # The order of these calls is the order of the BGM_* constants in
    # src/ttrpg.h; audioMusic maps one to the other by name through
    # res/music.h, so they cannot silently swap.

    # Kampung Sahur: warm, slow, somebody's kitchen at 3am.
    sections.append(build_theme(
        mod, ins, 'TOWN', [(F, 'maj'), (C, 'maj'), (G, 'maj')],
        rows=64, tempo=92, speed=6, style='town', seed=0x1001, scale=MAJOR))

    # The east road: the long walk. Aeolian, unhurried.
    sections.append(build_theme(
        mod, ins, 'FIELD', [(A, 'min'), (F, 'maj'), (C, 'maj'), (G, 'maj')],
        rows=64, tempo=104, speed=6, style='field', seed=0x1111))

    # Hutan: dorian, low, almost no percussion. Something is standing still.
    sections.append(build_theme(
        mod, ins, 'FOREST', [(E, 'min'), (C, 'maj'), (D, 'sus')],
        rows=64, tempo=84, speed=6, style='forest', seed=0x1222, scale=DORIAN))

    # Pantai: wide and open, arpeggios like water.
    sections.append(build_theme(
        mod, ins, 'SHORE', [(G, 'maj'), (E, 'min'), (C, 'maj')],
        rows=64, tempo=98, speed=6, style='shore', seed=0x1333, scale=MAJOR))

    # Padang Garam: high, sparse, nothing has grown here in a month.
    sections.append(build_theme(
        mod, ins, 'SALT', [(D, 'min'), (Bb, 'maj'), (C, 'sus')],
        rows=64, tempo=76, speed=6, style='salt', seed=0x1444))

    # Langit Besi: machinery. Phrygian, because it should feel wrong.
    sections.append(build_theme(
        mod, ins, 'FORTRESS',
        [(E, 'min'), (F, 'maj'), (E, 'min'), (Cs, 'dim')],
        rows=64, tempo=132, speed=6, style='fortress', seed=0x1555,
        scale=PHRYG))

    # Malam Panjang: two chords, no drums, almost nothing. That is the point.
    sections.append(build_theme(
        mod, ins, 'HUSH', [(A, 'min'), (Bb, 'maj')],
        rows=64, tempo=64, speed=6, style='hush', seed=0x1666, scale=PHRYG))

    # The encounter.
    sections.append(build_theme(
        mod, ins, 'BATTLE', [(D, 'min'), (Bb, 'maj'), (C, 'maj'), (A, 'min')],
        rows=64, tempo=152, speed=6, style='battle', seed=0x2222))

    # The guardians: a semitone slide down, the oldest trick there is and
    # still the one that says "this one is different".
    sections.append(build_theme(
        mod, ins, 'BOSS', [(D, 'min'), (Cs, 'maj'), (C, 'maj'), (B, 'dim')],
        rows=64, tempo=168, speed=6, style='boss', seed=0x3333))

    # Il Silenzio.
    sections.append(build_theme(
        mod, ins, 'FINAL', [(Eb, 'min'), (B, 'maj'), (Cs, 'dim'), (D, 'min')],
        rows=64, tempo=182, speed=6, style='final', seed=0x3777, scale=PHRYG))

    sections.append(build_fanfare(mod, ins))

    # The title: the field progression at half speed, on bells.
    sections.append(build_theme(
        mod, ins, 'TITLE', [(A, 'min'), (F, 'maj')],
        rows=64, tempo=76, speed=6, style='title', seed=0x4444))

    # Sahur e servito. Major, at last.
    sections.append(build_theme(
        mod, ins, 'ENDING', [(C, 'maj'), (G, 'maj'), (F, 'maj')],
        rows=64, tempo=88, speed=6, style='ending', seed=0x5555, scale=MAJOR))

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
    """A crude mixer: volume and note only, no effects beyond Axx/Txx. Enough
    to hear whether a theme is music."""
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
                acc = 0.0
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
                    acc += s.data[ip] * gain
                    v[1] = pos + step
                out.append(acc)
                if len(out) >= limit:
                    break
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break

    peak = max((abs(v) for v in out), default=1.0) or 1.0
    import wave
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(b''.join(struct.pack('<h', int(v / peak * 26000))
                           for v in out))
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
