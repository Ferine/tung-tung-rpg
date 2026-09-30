#!/usr/bin/env python3
"""The score language, and the compiler that turns it into tracker patterns.

A score is written the way a composer thinks -- a line per voice, a bar at a
time -- and this module makes it the eight-channel Impulse Tracker module the
SPC700 driver plays. It exists because the alternative is writing 4,000 cells
by hand, and because a compiler can check what a person cannot hear:

  * every note is inside the range its instrument can actually play
  * every bar has exactly the right number of rows
  * bass and melody agree with the chord written above them
  * the whole thing fits the driver's limits, and what it costs in ARAM

Notation (space-separated tokens; `|` is a bar line and is checked):

    C4:4      note, duration in rows (default: the current `L`)
    r:2       rest            -:2   tie: hold the previous note two rows longer
                              (a note is released where a *rest* begins; a note
                              that follows another replaces it, legato)
    L2        default duration is now 2 rows
    !mf       dynamic for the notes that follow (ppp pp p mp mf f ff fff, or !44)
    @oboe     the instrument that plays the notes that follow
    #pan5     pan for the notes that follow (0 left .. 15 right)
    #echo1    send this voice to the echo (#echo0 stops it)
    #tempo90  change tempo, in BPM

  a note takes suffixes, in this order:   '  staccato (released at half length)
                                          ^  accent     ~  vibrato
                                          _  accepted and ignored: legato is the default
                                          v44 / v+6 / v-6   explicit / relative volume
    <20,44>   its own token, straight after a note: a volume ramp across it

Time is counted in rows. A row is a sixteenth note at grid 4 (the default), an
eighth at grid 2: the pattern format charges two bytes per row whether or not
anything happens in it, so music that never needs a sixteenth is written on the
coarser grid and costs a quarter less.

Voices are the eight channels, and the *roles* are fixed across the score so
the stereo picture and echo sends are predictable:

    lead  bass  harm  pad  rhy  drum  x1  x2

The last two are the ones the driver hands to sound effects, so nothing
essential is ever written on them: they carry ornament that can vanish for a
few frames without anyone noticing.
"""
import re

import itwriter as it
import orchestra as orc
from itwriter import NOTE_OFF

VOICES = ('lead', 'bass', 'harm', 'pad', 'rhy', 'drum', 'x1', 'x2')
CH = {n: i for i, n in enumerate(VOICES)}

# IT channel pan (0..64), fixed for every theme. Lead and bass near the middle
# so the tune and the floor survive mono; the rest spread.
CHAN_PAN = (30, 32, 44, 20, 40, 32, 12, 52)

DYN = dict(ppp=10, pp=16, p=24, mp=32, mf=40, f=48, ff=56, fff=63)

TICK_TEMPO = 120          # the tracker tempo themes are built around
MIN_TEMPO = 80             # the driver clamps absolute tempo to 80-200
MAX_TEMPO = 200            # (Command_Tempo in sm_spc_wla.asm)

# effects, by IT effect number
FX_SPEED, FX_JUMP, FX_VIB, FX_EXT, FX_TEMPO, FX_GVOL = 1, 2, 8, 19, 20, 22

_NOTE = re.compile(
    r"^(?P<name>[A-Ga-g][#b]?-?\d)(?::(?P<dur>\d+))?(?P<mods>['_^~]*)"
    r"(?:v(?P<vol>[+-]?\d+))?$")


class ScoreError(Exception):
    pass


def midi(name):
    base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[
        name[0].upper()]
    i = 1
    while name[i] in '#b':
        base += 1 if name[i] == '#' else -1
        i += 1
    return (int(name[i:]) + 1) * 12 + base


_PC = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_name(m):
    return "%s%d" % (_PC[m % 12], m // 12 - 1)


# ---- chords, for the checker ------------------------------------------------

_QUAL = [
    ('maj7', (0, 4, 7, 11)), ('m7b5', (0, 3, 6, 10)), ('dim7', (0, 3, 6, 9)),
    ('m7', (0, 3, 7, 10)), ('m9', (0, 3, 7, 10, 14)),
    ('add9', (0, 4, 7, 14)), ('sus4', (0, 5, 7)), ('sus2', (0, 2, 7)),
    ('dim', (0, 3, 6)), ('aug', (0, 4, 8)), ('m6', (0, 3, 7, 9)),
    ('m', (0, 3, 7)), ('9', (0, 4, 7, 10, 14)), ('7', (0, 4, 7, 10)),
    ('6', (0, 4, 7, 9)), ('5', (0, 7)), ('', (0, 4, 7)),
]


def chord_pcs(sym):
    """'Dm7/F' -> (root pitch class, bass pitch class, set of pitch classes)"""
    m = re.match(r"^([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?$", sym)
    if not m:
        raise ScoreError("cannot read chord %r" % sym)
    root = midi(m.group(1) + '4') % 12
    qual = m.group(2)
    for q, ivs in _QUAL:
        if qual == q:
            pcs = {(root + i) % 12 for i in ivs}
            break
    else:
        raise ScoreError("unknown chord quality in %r" % sym)
    bass = midi(m.group(3) + '4') % 12 if m.group(3) else root
    pcs.add(bass)
    return root, bass, pcs


# ---- parsing a part ---------------------------------------------------------

class Ev:
    """One note (or rest) of one voice."""
    __slots__ = ('row', 'dur', 'note', 'inst', 'vol', 'mods', 'ramp', 'pan',
                 'echo', 'tempo', 'tied', 'fixed')

    def __init__(self, row, dur, note, inst, vol, mods='', ramp=None):
        self.row, self.dur, self.note = row, dur, note
        self.inst, self.vol, self.mods, self.ramp = inst, vol, mods, ramp
        self.pan = self.echo = self.tempo = None
        self.tied = 0
        self.fixed = False         # an explicit vNN: never reshaped


def parse_part(text, voice, rows_per_bar, default_inst, where):
    """Text -> list of Ev, plus the bar count. Raises ScoreError with the bar
    and voice named, because 'row 137 is wrong' is not a message anybody can
    act on."""
    evs = []
    row = 0
    bar = 0
    bar_start = 0
    dur = 2
    dyn = DYN['mf']
    inst = default_inst
    pan = echo = tempo = None
    last = None

    def loc():
        return "%s / %s / bar %d" % (where, voice, bar + 1)

    for tok in text.replace('\n', ' ').split():
        if tok == '|':
            if row - bar_start != rows_per_bar:
                raise ScoreError("%s: bar is %d rows, wanted %d"
                                 % (loc(), row - bar_start, rows_per_bar))
            bar += 1
            bar_start = row
            continue
        if tok[0] == 'L' and tok[1:].isdigit():
            dur = int(tok[1:])
            continue
        if tok[0] == '!':
            k = tok[1:]
            dyn = DYN[k] if k in DYN else int(k)
            continue
        if tok[0] == '@':
            if tok[1:] not in orc.INSTRUMENTS:
                raise ScoreError("%s: no instrument %r" % (loc(), tok[1:]))
            inst = tok[1:]
            continue
        if tok.startswith('#pan'):
            pan = int(tok[4:])
            continue
        if tok.startswith('#echo'):
            echo = int(tok[5:])
            continue
        if tok.startswith('#tempo'):
            tempo = int(tok[6:])
            continue
        if tok[0] == '<' and tok.endswith('>'):
            a, b = tok[1:-1].split(',')
            if last is None or last.note is None:
                raise ScoreError("%s: ramp with no note before it" % loc())
            last.ramp = (int(a), int(b))
            continue
        if tok[0] == '-' and (len(tok) == 1 or tok[1] == ':'):
            n = int(tok[2:]) if ':' in tok else dur
            if last is None or last.note is None:
                raise ScoreError("%s: tie with no note before it" % loc())
            last.dur += n
            last.tied += n
            row += n
            continue
        if tok[0] in 'rR' and (len(tok) == 1 or tok[1] == ':'):
            n = int(tok[2:]) if ':' in tok else dur
            evs.append(Ev(row, n, None, inst, 0))
            last = evs[-1]
            row += n
            continue
        m = _NOTE.match(tok)
        if not m:
            raise ScoreError("%s: cannot read %r" % (loc(), tok))
        n = int(m.group('dur')) if m.group('dur') else dur
        mods = m.group('mods') or ''
        vol = dyn
        if '^' in mods:
            vol += 8
        if m.group('vol') is not None:
            v = m.group('vol')
            vol = dyn + int(v) if v[0] in '+-' else int(v)
        vol = max(1, min(64, vol))
        ev = Ev(row, n, midi(m.group('name')), inst, vol, mods)
        ev.fixed = m.group('vol') is not None
        ev.pan, ev.echo, ev.tempo = pan, echo, tempo
        pan = echo = tempo = None
        evs.append(ev)
        last = ev
        row += n
    if row - bar_start not in (0, rows_per_bar):
        raise ScoreError("%s: last bar is %d rows, wanted %d"
                         % (loc(), row - bar_start, rows_per_bar))
    bars = bar + (1 if row - bar_start else 0)
    return evs, bars, row


# ---- themes -----------------------------------------------------------------

class Section:
    def __init__(self, name, chords, parts, inst, rows_per_bar, bars):
        self.name = name
        self.chords = chords
        self.parts = parts          # voice -> [Ev]
        self.inst = inst
        self.rows_per_bar = rows_per_bar
        self.bars = bars
        self.rows = rows_per_bar * bars
        self.bpm = None             # None: the theme's tempo


class Theme:
    """One piece of music: sections, an order, and where it loops to.

    `bpm` is the quarter-note tempo; `grid` how many rows make a quarter
    (4: sixteenths; 2: eighths); `beats` the beats per bar. `trim` is the
    theme's global volume, 0-128, so themes written at different densities can
    be brought to the same loudness without touching a single note.
    `humanize` scales the metric shaping described at `_shape` (0 turns it off).
    """

    def __init__(self, name, bpm, beats=4, grid=4, key='C', trim=128,
                 voices=None, humanize=1.0):
        self.name = name
        self.bpm = bpm
        self.beats = beats
        self.grid = grid
        self.key = key
        self.trim = trim
        self.humanize = humanize
        self.rows_per_bar = int(round(beats * grid))
        # The driver's tick timer cannot run slower than ~32ms a tick, so a
        # tempo under ~78 silently plays too fast: slow music needs more ticks
        # per *row*, not a smaller tempo. Choose the speed that puts the
        # tracker tempo near 120, which leaves room to slow down (to about 2/3)
        # and speed up (to about 1.6x) inside a theme, and makes a tick about
        # 21ms in every theme -- so an instrument's release is the same length
        # in all of them.
        self.speed = max(4, int(round(TICK_TEMPO * 24.0 / (bpm * grid))))
        self.voices = dict(voices or {})    # voice -> default instrument
        self.sections = {}
        self.order = []
        self.loop = 0
        self.warnings = []

    def tempo(self, bpm=None):
        """Tracker tempo for `bpm`: a row lasts speed * 2.5 / T seconds and a
        row is 1/grid of a quarter note, so T = speed * bpm * grid / 24."""
        t = int(round(self.speed * (bpm or self.bpm) * self.grid / 24.0))
        if not MIN_TEMPO <= t <= MAX_TEMPO:
            raise ScoreError("%s: %s BPM at speed %d is tracker tempo %d; the "
                             "driver plays %d-%d" % (
                                 self.name, bpm or self.bpm, self.speed, t,
                                 MIN_TEMPO, MAX_TEMPO))
        return t

    def section(self, name, chords=None, inst=None, bpm=None, **parts):
        if name in self.sections:
            raise ScoreError("%s: section %s defined twice" % (self.name, name))
        for v in parts:
            if v not in CH:
                raise ScoreError("%s/%s: no voice %r (want one of %s)"
                                 % (self.name, name, v, ', '.join(VOICES)))
        where = "%s/%s" % (self.name, name)
        default = dict(self.voices)
        default.update(inst or {})
        evs = {}
        nbars = None
        for v, text in parts.items():
            if v not in default:
                # a voice with no default must name its instrument itself
                default[v] = None
            e, bars, rows = parse_part(text, v, self.rows_per_bar,
                                       default[v], where)
            for ev in e:
                if ev.note is not None and ev.inst is None:
                    raise ScoreError("%s / %s: a note before any @instrument"
                                     % (where, v))
            if nbars is None:
                nbars = bars
            elif bars != nbars:
                raise ScoreError("%s: voice %s is %d bars, others %d"
                                 % (where, v, bars, nbars))
            evs[v] = e
        if nbars is None:
            raise ScoreError("%s: a section needs at least one voice" % where)
        ch = None
        if chords:
            ch = chords.replace('|', ' ').split()
            if len(ch) != nbars:
                raise ScoreError("%s: %d chords for %d bars"
                                 % (where, len(ch), nbars))
        sec = Section(name, ch, evs, default, self.rows_per_bar, nbars)
        sec.bpm = bpm
        if sec.rows > 200:
            raise ScoreError("%s: %d rows; a pattern holds at most 200"
                             % (where, sec.rows))
        self.sections[name] = sec
        self._check(sec)
        return sec

    def play(self, *names, loop=0):
        """The order list. `loop` is the index into it that the theme jumps
        back to; anything before is an introduction, played once."""
        for n in names:
            if n not in self.sections:
                raise ScoreError("%s: no section %r" % (self.name, n))
        self.order = list(names)
        self.loop = loop
        if names.count(names[-1]) > 1:
            raise ScoreError(
                "%s: the last section (%s) is used more than once, but it "
                "carries the jump back to the loop point, so it must be "
                "unique -- end on a section of its own" % (self.name, names[-1]))

    # -- the checker: what a person would hear and the machine can measure --

    def _check(self, sec):
        w = self.warnings
        for v, evs in sec.parts.items():
            for ev in evs:
                if ev.note is None:
                    continue
                lo, hi = orc.RANGE.get(ev.inst, (None, None))
                if lo and not midi(lo) <= ev.note <= midi(hi):
                    raise ScoreError(
                        "%s/%s/%s bar %d: %s is outside the %s's range %s-%s"
                        % (self.name, sec.name, v,
                           ev.row // sec.rows_per_bar + 1,
                           note_name(ev.note), ev.inst, lo, hi))
        if not sec.chords:
            return
        bar_of = lambda row: row // sec.rows_per_bar
        beat = self.grid
        for v in ('bass',):
            for ev in sec.parts.get(v, []):
                if ev.note is None:
                    continue
                if ev.row % sec.rows_per_bar == 0:
                    root, bass, pcs = chord_pcs(sec.chords[bar_of(ev.row)])
                    if ev.note % 12 != bass:
                        w.append("%s/%s bar %d: bass %s under %s"
                                 % (self.name, sec.name, bar_of(ev.row) + 1,
                                    note_name(ev.note),
                                    sec.chords[bar_of(ev.row)]))
        for v in ('lead', 'harm', 'pad'):
            for ev in sec.parts.get(v, []):
                if ev.note is None or ev.dur < beat:
                    continue
                if ev.row % beat:
                    continue
                bar = bar_of(ev.row)
                # a chord covers its bar, or its half if two are written
                root, bass, pcs = chord_pcs(sec.chords[bar])
                if ev.note % 12 not in pcs and not self._scale_ok(ev.note):
                    w.append("%s/%s/%s bar %d: %s is neither in %s nor the key"
                             % (self.name, sec.name, v, bar + 1,
                                note_name(ev.note), sec.chords[bar]))

    def _scale_ok(self, note):
        return True


# ---- compilation ------------------------------------------------------------

class Pattern:
    def __init__(self, rows):
        self.rows = rows
        self.cells = {}         # row -> {ch: [note, inst, vol, cmd, param]}

    def cell(self, row, ch):
        return self.cells.setdefault(row, {}).setdefault(
            ch, [None, None, None, None, 0])

    def free_fx(self, row, prefer=(7, 6, 5, 4, 3, 2, 1, 0)):
        for ch in prefer:
            c = self.cells.get(row, {}).get(ch)
            if c is None or c[3] is None:
                return self.cell(row, ch)
        raise ScoreError("no free effect slot on row %d" % row)

    def key(self):
        out = []
        for r in sorted(self.cells):
            for ch in sorted(self.cells[r]):
                out.append((r, ch, tuple(self.cells[r][ch])))
        return (self.rows, tuple(out))


def _vib_speed(tempo):
    """Hxy speed for ~5.3 Hz at this tempo. A tick is 2.5/tempo seconds and
    the driver advances the LFO 4*x of 256 steps per tick."""
    tick = 2.5 / tempo
    return max(1, min(15, int(round(64.0 * tick * 5.3))))


def _tail_hanging(sec):
    """Voices whose last note runs to the very end of the section on an
    instrument that holds until told to stop: they are still sounding when the
    next pattern begins."""
    out = set()
    for v, evs in sec.parts.items():
        if not evs:
            continue
        last = evs[-1]
        if (last.note is not None and last.row + last.dur >= sec.rows
                and orc.INSTRUMENTS[last.inst]['kind'] == 'loop'):
            out.add(v)
    return out


# How much a note leans, by where it falls, for the voices that carry a line.
# Melody and bass lean hardest; a harp arpeggio a little. Percussion and pads
# are written to their level and left alone.
_SHAPE_DEPTH = {'lead': 1.0, 'x2': 1.0, 'harm': 0.8, 'bass': 0.8, 'rhy': 0.5}


def _shape(theme, sec, voice, ev):
    """The volume a written note actually plays at.

    Every note in a part used to sit at exactly one level for a whole section,
    which is what makes machine-played music feel mechanical and tiring. A
    person leans on the downbeat, lets weak subdivisions fall away, and gives a
    long note a little more. The amounts are small (a few steps of 64, a dB or
    so) and they are the same in every theme: the bar's downbeat +3, another
    beat +1, an off-beat subdivision -2, a note a beat or longer +1. A note
    with an explicit vNN, or a ramp, is left exactly as written."""
    depth = _SHAPE_DEPTH.get(voice)
    if not depth or not theme.humanize or ev.fixed or ev.ramp:
        return ev.vol
    r = ev.row % sec.rows_per_bar
    if r == 0:
        d = 3
    elif ev.row % theme.grid == 0:
        d = 1
    else:
        d = -2
    if ev.dur >= 2 * theme.grid:
        d += 1
    return max(1, min(64, ev.vol + int(round(d * depth * theme.humanize))))


def compile_section(theme, sec, first_order_idx, loop_order_idx, is_last,
                    inst_no, tempo0=None, preds=()):
    """A Section -> Pattern. `preds` are the sections that can play just
    before this one, so a note that hangs across the boundary can be released
    on the first row if this pattern does not immediately replace it."""
    pat = Pattern(sec.rows)
    tempo = tempo0 or theme.tempo(sec.bpm)
    # a #tempo on the very first note *is* the section's tempo: emitting it
    # separately would put two tempo commands on row 0, and the later channel
    # wins, so the section's own default would silently beat the composer's
    for evs in sec.parts.values():
        for ev in evs:
            if ev.row == 0 and ev.note is not None and ev.tempo:
                tempo = theme.tempo(ev.tempo)
    # speed / tempo / global volume: every pattern restates them, so a jump
    # from anywhere (a new theme, the loop point) starts in a known state
    pat.free_fx(0)[3:] = [FX_SPEED, theme.speed]
    pat.free_fx(0)[3:] = [FX_TEMPO, tempo]
    pat.free_fx(0)[3:] = [FX_GVOL, theme.trim]

    for v, evs in sec.parts.items():
        ch = CH[v]
        for i, ev in enumerate(evs):
            if ev.note is None:
                continue
            spec = orc.INSTRUMENTS[ev.inst]
            c = pat.cell(ev.row, ch)
            c[0] = ev.note
            c[1] = inst_no[ev.inst]
            c[2] = ev.ramp[0] if ev.ramp else _shape(theme, sec, v, ev)
            if ev.tempo and ev.row:
                tempo = theme.tempo(ev.tempo)
                fx = pat.free_fx(ev.row)
                fx[3:] = [FX_TEMPO, tempo]
            if ev.pan is not None:
                fx = pat.cell(ev.row, ch)
                if fx[3] is None:
                    fx[3:] = [FX_EXT, 0x80 | max(0, min(15, ev.pan))]
            if ev.echo is not None:
                fx = pat.cell(ev.row, ch)
                if fx[3] is None:
                    fx[3:] = [FX_EXT, 1 if ev.echo else 2]
            nxt = evs[i + 1] if i + 1 < len(evs) else None
            end = ev.row + ev.dur
            sustained = spec['kind'] == 'loop'
            if sustained:
                # A note ends where it ends. If another note follows at once
                # it simply replaces this one (legato: no gap, and no dip when
                # every voice changes on the same beat -- ending each note one
                # *row* early left a hole a third of a second wide at slow
                # grids, where a row is ~17 ticks and the release ~9). The
                # release starts only where a rest begins; staccato starts it
                # at half length.
                gate = end
                if "'" in ev.mods:
                    gate = ev.row + max(1, ev.dur // 2)
                if gate < sec.rows and gate > ev.row and (
                        gate < end or nxt is None or nxt.note is None):
                    off = pat.cell(gate, ch)
                    if off[0] is None:
                        off[0] = NOTE_OFF
            if ev.ramp and ev.dur >= 2:
                a, b = ev.ramp
                for r in range(ev.row + 1, min(end, sec.rows)):
                    t = (r - ev.row) / float(ev.dur)
                    cc = pat.cell(r, ch)
                    if cc[0] is None and cc[2] is None:
                        cc[2] = int(round(a + (b - a) * t))
            if '~' in ev.mods and ev.dur >= 6 and sustained:
                depth = 3
                x = _vib_speed(tempo)
                for r in range(ev.row + 3, end - 1):
                    cc = pat.cell(r, ch)
                    if cc[3] is None and cc[0] is None:
                        cc[3:] = [FX_VIB, (x << 4) | depth]
    # a note left ringing by the previous pattern: release it on row 0 unless
    # this pattern starts a note on that voice right away
    hanging = set()
    for p in preds:
        hanging |= _tail_hanging(p)
    for v in hanging:
        evs = sec.parts.get(v)
        starts_note = bool(evs) and evs[0].row == 0 and evs[0].note is not None
        if not starts_note:
            c = pat.cell(0, CH[v])
            if c[0] is None:
                c[0] = NOTE_OFF
    if is_last:
        # the loop: jump back to the loop point from the last row. The last
        # section of a theme is unique (enforced in Theme.play), so this
        # cannot fire from anywhere else.
        fx = pat.free_fx(sec.rows - 1)
        fx[3:] = [FX_JUMP, loop_order_idx]
    return pat


def estimate_bytes(pat):
    n = 2 * pat.rows
    for r, row in pat.cells.items():
        for ch, c in row.items():
            n += 1 + (c[0] is not None) + (c[1] is not None) \
                + (c[2] is not None) + 2 * (c[3] is not None)
    return n


def used_instruments(themes):
    seen = []
    for th in themes:
        for name in th.order:
            sec = th.sections[name]
            for evs in sec.parts.values():
                for ev in evs:
                    if ev.note is not None and ev.inst not in seen:
                        seen.append(ev.inst)
    return [n for n in orc.INSTRUMENTS if n in seen]


def assemble(mod, themes, inst_no):
    """Add every theme's patterns and orders to `mod`; returns
    [(THEME, first_order, last_order)], the ranges music.h carries."""
    ranges = []
    dedupe = {}
    for th in themes:
        first = len(mod.orders)
        loop_idx = first + th.loop
        for k, name in enumerate(th.order):
            sec = th.sections[name]
            is_last = k == len(th.order) - 1
            preds = []
            if k > 0:
                preds.append(th.sections[th.order[k - 1]])
            if k == th.loop:
                preds.append(th.sections[th.order[-1]])
            pat = compile_section(th, sec, first, loop_idx, is_last, inst_no,
                                  preds=preds)
            key = pat.key()
            if key in dedupe:
                pi = dedupe[key]
            else:
                pi = mod.add_pattern(pat.rows, {
                    r: {ch: tuple(c) for ch, c in row.items()}
                    for r, row in pat.cells.items()})
                dedupe[key] = pi
                nb = estimate_bytes(pat)
                mod.pattern_bytes = getattr(mod, 'pattern_bytes', 0) + nb
                tb = getattr(mod, 'theme_bytes', None)
                if tb is None:
                    tb = mod.theme_bytes = {}
                tb[th.name] = tb.get(th.name, 0) + nb
            mod.orders.append(pi)
        ranges.append((th.name, first, len(mod.orders) - 1))
    return ranges
