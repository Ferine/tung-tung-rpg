#!/usr/bin/env python3
"""The score, part three: the two places that hold their breath.

HUTAN and MALAM PANJANG are the quietest music in the game, and for opposite
reasons. The forest is quiet because something large is standing very still in
it and has decided not to frighten anybody. The last dungeon is quiet because
it is the Sleep's idea of kindness: soft, smooth, unhurried, and never going
to end. Both are written slow, on the eighth grid, with a drone that is struck
once and left sounding -- stillness here is composed, not empty.

  FOREST   E dorian. Patapim's footsteps (bassoon, root and fifth), a low
           bassoon-and-clarinet duet over a drone, drops of harp falling off
           leaves. The Lullaby leaks in once, bent out of shape; the Call is
           struck on a bell twice, the second time with nobody to answer it.
  HUSH     A over a pedal that never moves. The Slide goes down and down and
           never arrives; the Lullaby is hollowed out to its falling thirds
           and tolled on a bell; a string cluster leans on the pedal and
           will not resolve. It ends on a question and loops without a seam.

One thing about the machine shapes both. A note cannot outlive its pattern (the
compiler releases whatever is left hanging on the first row), so a drone can
only be as long as a pattern. Both themes therefore put their whole loop in ONE
pattern -- 24 bars for the forest, 16 for the dungeon; the format allows 200
rows -- and the only place a drone is ever re-struck is the loop point itself,
where it is meant to be: the forest's bass drops from the fifth back to the
tonic, the dungeon's pedal takes one breath while the last cluster dies away.
"""
import re

from score import Theme
from themes_road import xp, stretch, LULLABY_Q, SLIDE, CALL


# ---- small tools ------------------------------------------------------------

def _bars(text, rows=8):
    """A motif written on longer bars, cut into bars of `rows` rows (a list of
    strings). The Lullaby is eight rows a bar; slowed to half speed it is
    sixteen, and this is what puts the bar lines back."""
    out, cur, acc = [], [], 0
    for tok in text.replace('|', ' ').split():
        cur.append(tok)
        acc += int(re.search(r":(\d+)", tok).group(1))
        if acc == rows:
            out.append(' '.join(cur))
            cur, acc = [], 0
        elif acc > rows:
            raise ValueError("a note crosses a bar line in %r" % text)
    return out


def _voice(text, vols):
    """Give each note of a motif its own dynamic, so a borrowed tune can be
    shaped without being retyped."""
    it_ = iter(vols)
    return re.sub(r"([A-G][#b]?-?\d:\d+)",
                  lambda m: "%sv%d" % (m.group(1), next(it_)), text)


def _rests(n):
    return "r:8 | " * n


def _drone(vel, *legs):
    """A drone across a whole pattern. Each leg is (note, bars): struck on the
    first row of the leg and tied to its end, so a change of pitch is the only
    time it is ever struck again."""
    return "!%d " % vel + ''.join(
        "%s:8 | %s" % (note, "-:8 | " * (bars - 1)) for note, bars in legs)


def _join(*segs):
    """Sections of a long pattern, each (bars, {voice: text}), laid end to end.
    A voice a section does not use rests through it."""
    voices = []
    for _, d in segs:
        voices += [v for v in d if v not in voices]
    return {v: ' '.join(d[v] if v in d else _rests(n) for n, d in segs)
            for v in voices}


# ---- FOREST: Hutan, the forest that stopped moving --------------------------

# Patapim's step: the root, heavy, then the fifth, lighter. Two to a bar at
# 56 BPM is a stride of two seconds -- something very large, in no hurry.
STEP = "E2:3^ r:1 B2:3 r:1 | "


def forest():
    """The forest that stopped moving. E dorian, 56 BPM.

    Everything here is held. A bass_lo and an organ drone on E; strings_lo
    leaning on the fifth; the clarinet tells a slow tune in three-bar phrases
    and the fourth bar of each belongs to somebody else -- the bassoon takes
    up the last notes an octave and a half lower, or a bell strikes the Call.
    In the middle the bassoon sings the clarinet's tune again, moved into C
    (the borrowed sixth chord: the same tread in a darker room), and then the
    Lullaby leaks through the
    leaves, bent, and stops; the steps stop with it. Then the two wind
    instruments sing together, in thirds and sixths, and the loop breathes
    back in on the dominant."""
    t = Theme('FOREST', bpm=56, beats=4, grid=2, key='E', voices=dict(
        lead='clarinet', bass='bassoon', harm='bassoon', pad='strings_lo',
        rhy='organ', drum='bass_lo', x1='harp', x2='harp'))

    # -- the intro: the drone rises out of nothing, the first drops fall, and
    # one distant footfall says that the wood is not empty
    t.section('intro', chords="Em | Em",
        drum="!pp E1:8 <8,28> | -:8 |",
        rhy="!ppp E3:8 <6,14> | -:8 |",
        pad="r:8 | !pp B3:8 <8,16> |",
        bass="r:8 | !24 r:4 B2:3 r:1 |",
        x1="!14 r:3 G5:1 r:4 | r:8 |",
        x2="!14 r:8 | r:1 D5:1 r:6 |")

    # -- A: the clarinet tells it. Bar 1 leaps a fourth from the fifth to the
    # tonic -- the Call's lift, said as a tune. Bar 3 is the peak (the ninth
    # over A, hanging); phrase two climbs a step higher, its middle bar
    # falling in three notes instead of two so the tread changes, to the
    # dorian sixth, the only bright note in the mode. Bar 4 is the bassoon's, taking the
    # fall over from the clarinet; bar 8 is the bell's: three strokes on the
    # fifth and the lift to the tonic, which is where the phrase comes home.
    call = xp(stretch(CALL, 0.5), 2)        # B4 B4 B4 E5, a quarter apart
    A = (8, dict(
        lead="!30 B3:6 E4:2 | !32 G4:6 F#4:2 | !36 B4:6~ <36,42> !32 A4:2 | r:8 | "
             "!32 B3:6 E4:2 | !34 A4:4 G4:2 F#4:2 | !38 C#5:6~ <38,44> !34 B4:2 | r:8 |",
        harm="!32 " + _rests(3) + "G3:2 F#3:6~ | " + _rests(3)
             + "@tubebell !30 " + call,
        bass="!32 " + STEP * 3 + "E2:3^ r:5 | " + STEP * 3 + "r:8 |",
        pad="!16 B3:8 | -:8 | C#4:8 | B3:8 | G3:8 | A3:8 | C#4:8 | B3:8 |",
        x1="!14 r:5 G5:1 r:2 | r:8 | r:6 E5:1 r:1 | r:8 | "
           "r:1 B4:1 r:6 | r:8 | r:3 G5:1 r:4 | r:8 |",
        x2="!14 r:8 | r:6 D5:1 r:1 | r:8 | r:3 A4:1 r:4 | "
           "r:8 | r:2 E5:1 r:5 | r:8 | r:8 |"))
    A_CHORDS = "Em | Em | A/E | Em | Em | D/E | A/E | Em"

    # -- B: the bassoon has the tune. It is the clarinet's shape (fifth up to
    # the tonic, a step, a fifth, a step) begun on the fifth of C -- the
    # borrowed sixth chord, and then F major seventh over the E, the
    # phrygian second, the darkest place in the wood. Then the Lullaby:
    # the tune of the Sleep, from the road, taken to E, slowed to half speed,
    # and bent -- the major third flattened, the second flattened -- and it
    # falls to the tonic and gets no further than a step below before the
    # bar runs out. The steps stop while it sounds. The drone alone moves,
    # to the fifth, in the last bar: everything leans forward.
    lull = ' '.join(_bars(xp(stretch(LULLABY_Q, 2), -10))[:3])
    lull = lull.replace('G#4', 'G4').replace('F#4', 'F4').replace('D#4', 'D4')
    l1, l2, l3 = (b.strip() for b in _bars(lull))
    B = (8, dict(
        harm="@bassoon !36 G3:6 C4:2 | !40 E4:6 D4:2 | !44 G4:6 <44,50> !44 F4:2 | "
             "!40 E4:6~ <40,26> r:2 | " + _rests(4),
        lead=_rests(4) + "!30 %s | !32 %s~ <32,20> | !24 %s | r:8 |" % (l1, l2, l3),
        bass="!28 " + "E2:3^ r:5 | " * 4 + _rests(3) + "!30 B2:3^ r:1 F#2:3 r:1 |",
        pad="!20 G3:8 | -:8 | A3:8 | B3:8 | A3:8 | B3:8 | C4:8 | D4:8 <20,28> |",
        x1="!14 r:6 E5:1 r:1 | r:8 | r:2 G5:1 r:5 | r:8 | " + _rests(4),
        x2="!14 r:8 | r:5 B4:1 r:2 | r:8 | r:4 D5:1 r:3 | " + _rests(4)))
    B_CHORDS = "C/E | C/E | Fmaj7/E | Em | Fmaj7/E | Em | Am/E | Bm"

    # -- A': the reprise, and the only place the two winds sing together.
    # The bassoon is a third under the clarinet (a sixth, then a tenth, as the
    # tune climbs), so the duet opens like a pair of hands; the peak is one
    # step higher than before, a D over the A chord that falls to the C# --
    # the fourth resolving into the third. Then the drone goes to the fifth
    # and the bell strikes the Call once more -- and nobody answers: the lift
    # is not played, the strokes get softer, and the wood breathes in.
    unanswered = _voice(' '.join(call.split()[:3]), [32, 26, 20]) + " r:2 |"
    Ap = (8, dict(
        lead="!32 B3:6 E4:2 | !34 G4:6 F#4:2 | !38 B4:6~ <38,44> !34 A4:2 | "
             "!34 E4:2 D4:6~ | "
             "!36 B3:6 E4:2 | !40 A4:4 G4:2 F#4:2 | !44 D5:6~ <44,50> !40 C#5:2 | r:8 |",
        harm="@bassoon !30 G3:6 C#4:2 | !32 E4:6 D4:2 | !36 G4:6 F#4:2 | "
             "!32 G3:2 F#3:6~ | !32 D3:6 A3:2 | !34 C#4:4 B3:2 A3:2 | !38 B3:6 A3:2 | "
             "@tubebell " + unanswered,
        bass="!28 " + STEP * 3 + "E2:3^ r:5 | " + STEP * 3
             + "B2:3^ r:1 F#2:3 r:1 |",
        pad="!18 B3:8 | -:8 | C#4:8 | B3:8 | G3:8 | A3:8 | C#4:8 | D4:8 <18,28> |",
        x1="!16 r:2 G5:1 r:5 | r:6 E5:1 r:1 | r:8 | r:4 D5:1 r:3 | "
           "r:7 B4:1 | r:8 | r:3 G5:1 r:4 | r:8 |",
        x2="!16 r:8 | r:4 D5:1 r:3 | r:1 A4:1 r:6 | r:8 | "
           "r:5 E5:1 r:2 | r:2 G5:1 r:5 | r:8 | r:8 |"))
    Ap_CHORDS = "Em | Em | A/E | Em | Em | D/E | A/E | Bm"

    # -- one pattern, 24 bars. The drones run through all of it: E for seven
    # bars of each section and the fifth for the eighth, and it is struck
    # again only when the pitch changes -- the dominant leaning into the
    # tonic at the top of A' and again at the top of the loop.
    parts = _join(A, B, Ap)
    parts['drum'] = _drone(30, ('E1', 15), ('B1', 1),
                           ('E1', 7), ('B1', 1))
    parts['rhy'] = _drone(14, ('E3', 15), ('B2', 1), ('E3', 7), ('B2', 1))
    t.section('main', chords=' | '.join((A_CHORDS, B_CHORDS, Ap_CHORDS)),
              **parts)

    t.play('intro', 'main', loop=1)
    return t


# ---- HUSH: Malam Panjang ----------------------------------------------------

def hush():
    """The last dungeon. A, 48 BPM, and a pedal that never moves.

    The bass_lo and the organ hold A for the whole of the loop; nothing else
    in the score is as stubborn. Over them the Slide goes down by semitones,
    first in a lone clarinet, then in the clarinet and a flute together
    against a two-note string cluster that leans on the pedal (B against C, a
    semitone, one in each ear). It never arrives: the clarinet stops on the
    B-flat, one step above the pedal it has been falling toward for seven
    bars. In B the Lullaby is hollowed out to its falling thirds and tolled on
    a bell, the cluster's upper note wavers between C and C-sharp (is the
    pedal minor or major? nobody says), the Slide comes back once more in a
    flute barely there, a single slow heartbeat, and the last question is left
    sounding a chord that wants to go on. Then the pedal takes its one breath
    and the clarinet begins again on E."""
    t = Theme('HUSH', bpm=48, beats=4, grid=2, key='A', voices=dict(
        lead='clarinet', bass='bass_lo', harm='strings_lo', pad='strings_lo',
        rhy='flute', drum='organ', x1='timp', x2='tubebell'))

    # -- the intro: the pedal is drawn in
    t.section('intro',
        bass="!pp A1:8 <6,30> | -:8 |",
        drum="r:4 !ppp A2:4 <4,20> | -:8 |")

    # -- A: the Slide. The clarinet, alone and very quiet, gives the four
    # notes of it (E, D#, D, C#: from the fifth to the major third of the
    # pedal, and not one of them is where it wants to be); then the same fall
    # continues, a third lower, and is left in the air on the B-flat.
    # The flute sings the Slide itself an octave above and four bars behind,
    # so the two lines fall in parallel tenths; the strings come in under it
    # and lean on the pedal, and the whole swells to bar 7.
    slide = _voice(xp(SLIDE, -12), [26, 28, 30, 32])
    fall = ' | '.join(b.strip() for b in xp(SLIDE, -16).split('|')[:3]) + ' |'
    fall = _voice(fall, [34, 34, 34]).replace('A#3:8v34', 'A#3:8v34 <34,6>')
    A = (8, dict(
        lead="%s %s r:8 |" % (slide, fall),
        rhy=_rests(4) + _voice(xp(SLIDE, 0), [28, 28, 26, 24]),
        pad=_rests(2) + "!17 B3:8 <8,17> | -:8 | B3:8 <17,25> | -:8 | -:8 | -:8 |",
        harm=_rests(4) + "!15 C4:8 <8,15> | -:8 | C4:8 <15,22> | -:8 |",
        x2="!22 " + _rests(5) + "r:3 G5:1 r:4 | r:8 | r:5 E5:1 r:2 |"))

    # -- B: the Lullaby, hollowed. Its tune is the road's, taken to A minor
    # (the third, the sixth and the second flattened) and thinned to the
    # first and last note of each sigh -- falling thirds, C to A, A to F, F to
    # D -- with the last question (E up to G) left open. A bell tolls each,
    # then a bar of nothing. The cluster's upper note goes C, C#, C, C#: the
    # last of them, under the question, makes the whole thing an A9, and the
    # cluster itself fades as the section goes. The Slide, in a flute barely
    # there, falls once more under the last four bars, and the loop turns it
    # back to the top.
    q = xp(LULLABY_Q, -5)
    q = q.replace('C#5', 'C5').replace('G#4', 'G4').replace('F#4', 'F4')
    thin = re.sub(r"[A-G][#b]?\d:1\s+", "", q).replace(':3', ':4')
    sighs = [b.strip() for b in thin.split('|') if b.strip()]
    toll = ''.join("%s | r:8 | " % s for s in sighs)
    B = (8, dict(
        rhy="@tubebell !30 " + toll,
        pad="!20 B3:8 <20,8> | " + "-:8 | " * 7,
        harm="@strings_lo !14 C4:8 | -:8 | C#4:8 | -:8 | C4:8 | -:8 | "
             "C#4:8 | -:8 |",
        lead=_rests(4) + "@flute " + _voice(xp(SLIDE, 0), [16, 16, 14, 12])
             .replace('C#5:8v12', 'C#5:8v12 <12,4>'),
        x1="!24 " + _rests(5) + "A2:1v24 A2:1v16 r:6 | r:8 | r:8 |"))

    # -- one pattern, 16 bars, and the pedal held straight through it. It is
    # struck again only at the loop point, under the last of the cluster and
    # the first of the clarinet, so the breath is the loop's own; the organ
    # is let go there and comes back half a bar behind the bass, so that the
    # two never dip together.
    parts = _join(A, B)
    parts['bass'] = _drone(30, ('A1', 16))
    parts['drum'] = "r:4 !20 A2:4 | " + "-:8 | " * 15
    t.section('main', **parts)

    t.play('intro', 'main', loop=1)
    return t
