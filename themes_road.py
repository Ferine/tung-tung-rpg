#!/usr/bin/env python3
"""The score, part one: the themes that belong to the journey.

Every theme is written for the game it plays in, and they share a small number
of ideas so the whole reads as one score rather than thirteen tracks:

  THE CALL      three equal notes on one pitch, then a leap upward. It is the
                kentongan -- TUNG. TUNG. TUNG. -- turned into a tune, and it
                is how the road theme begins.
  THE ROAD      the pilgrim's tune. Bright, bugle-like, singable. It walks the
                field, gets shouted by brass in battle, and is finally sung
                in full, in a major key, at the end.
  THE LULLABY   a slow descending figure. It belongs to the Sleep: kind at
                first, then hollow, then the thing the last boss pleads with.

The kentongan is tuned (D#3 and about A2), so the drum can play the pitch
the tune needs rather than only marking time.
"""
import re

from score import Theme

_FLAT = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
_SHARP = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_NOTE_RE = re.compile(r"\b([A-G])([#b]?)(-?\d)(?=[:'_^~v\s|<]|$)")


def xp(text, semis, flats=False):
    """Transpose every pitch in a passage. The same tune in another key is a
    matter of one call, which is what lets it come back changed."""
    base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
    names = _FLAT if flats else _SHARP

    def sub(m):
        n = (int(m.group(3)) + 1) * 12 + base[m.group(1)] + \
            (1 if m.group(2) == '#' else -1 if m.group(2) == 'b' else 0)
        n += semis
        return "%s%d" % (names[n % 12], n // 12 - 1)
    return _NOTE_RE.sub(sub, text)


# ---- the road, in D ---------------------------------------------------------
# Eight bars. The call, an arpeggio reaching up, a descending answer, and a
# half close; then the call again a step lower, and home.

def stretch(text, k):
    """Multiply every explicit duration by k: a motif written on the eighth
    grid, restated on the sixteenth grid (k=2) or the other way (k=0.5)."""
    return re.sub(r":(\d+)", lambda m: ":%d" % round(int(m.group(1)) * k), text)


# THE ROAD -- the pilgrim's tune, in D, on the sixteenth grid (16 rows a bar).
# The call (three notes, then up a fourth), an arpeggio reaching, a falling
# answer, a half close; the call again a step lower, and home.
ROAD_CHORDS = "D | G | D/F# | A | Bm | G | A | D"

ROAD = ("A4:4 A4:4 A4:4 D5:4 | B4:4 D5:4 G5:8 | F#5:6 E5:2 D5:4 A4:4 | "
        "C#5:4 E5:4 A4:8 | B4:4 B4:4 B4:4 F#5:4 | E5:6 D5:2 B4:8 | "
        "C#5:4 D5:4 E5:4 C#5:4 | D5:12 r:4 |")

# THE CALL alone: TUNG. TUNG. TUNG. -- and the lift. Sixteenth grid.
CALL = "A4:4 A4:4 A4:4 D5:4 |"

# THE LULLABY -- the Sleep's tune, in D, on the *eighth* grid (8 rows a bar).
# Three sighs, each a third lower than the last, then a question left open;
# the second half answers it and comes home. Kind in a major key with warm
# instruments; the same notes in a minor key, thin and slow, are the Hush.
LULLABY_CHORDS = "D | Bm | G | A"
LULLABY_Q = "F#5:3 E5:1 D5:4 | D5:3 C#5:1 B4:4 | B4:3 A4:1 G4:4 | A4:4 C#5:4 |"
LULLABY_ANSWER_CHORDS = "D | G | A | D"
LULLABY_A = "F#5:3 E5:1 D5:4 | B4:3 C#5:1 D5:4 | E5:3 D5:1 C#5:4 | D5:8 |"

# THE SLIDE -- the Silence's tune, in A, eighth grid. Not a melody but a
# direction: down by semitones, forever, over a pedal that never changes,
# smooth because nothing in it asks for anything. Loop it and it never ends.
SLIDE = "E5:8 | D#5:8 | D5:8 | C#5:8 |"


def field():
    """The east road. A pilgrim's walk: the call on the kentongan, then the
    tune passed from flute to oboe over a plucked bass; a lyrical bridge for
    solo violin; and the tune again, with the whole ensemble."""
    t = Theme('FIELD', bpm=104, key='D', voices=dict(
        lead='flute', bass='pizz_cb', harm='clarinet', pad='strings_lo',
        rhy='harp', drum='timp', x1='tambourine', x2='flute'))

    # -- the call: three strokes on the kentongan, the last one lifted. It is
    # on `rhy`, not an ornament voice: if a sound effect took the voice the
    # call is the one thing that must not go missing.
    t.section('intro', chords="D | A",
        bass="!mp L4 D2 A2 D2 A2 | A1 E2 A1 E2 |",
        drum="!mp L4 D2 r:4 D2 r:4 | A2 r:4 A2 r:4 |",
        rhy="@kentong !f L4 A3 A3 A3 D4 | r:16 |",
        pad="!pp A3:16 | A3:16 |")

    # -- the road: flute asks, oboe answers
    t.section('A', chords=ROAD_CHORDS,
        lead="@flute !mf " + ROAD.replace("| B4:4 B4:4", "| @oboe B4:4 B4:4")
             .replace("G5:8 |", "G5:8~ |").replace("D5:12 r:4 |", "D5:12~ r:4 |"),
        bass="!mp D2:4 A2:4 D2:4 A2:4 | G1:4 D2:4 G1:4 D2:4 | "
             "F#1:4 A1:4 D2:4 A1:4 | A1:4 E2:4 A1:4 E2:4 | "
             "B1:4 F#2:4 B1:4 F#2:4 | G1:4 D2:4 G1:4 D2:4 | "
             "A1:4 E2:4 A1:4 C#2:4 | D2:4 A1:4 D2:8 |",
        harm="!p F#4:16 | G4:16 | A4:16 | E4:16 | D4:16 | B3:16 | C#4:16 | A3:16 |",
        pad="!pp A3:16 | B3:16 | D4:16 | A3:16 | F#4:16 | D4:16 | E4:16 | F#4:16 |",
        drum="!mp D2:4 r:12 | G2:4 r:12 | D2:4 r:12 | A2:4 r:12 | "
             "B2:4 r:12 | G2:4 r:12 | A2:4 r:12 | D2:4 r:12 |")

    # -- the bridge: a lyrical tune in solo violin over harp and cello
    t.section('B', chords="G | D/F# | Em | A | G | Bm | Em | A",
        lead="@violin !mf B4:8 D5:6 E5:2 | F#5:10~ G5:2 A5:4 | "
             "G5:6 F#5:2 E5:8 | C#5:6 D5:2 E5:8 | B4:8 D5:6 E5:2 | "
             "F#5:8 D5:8 | E5:6 G5:2 B5:8~ | A5:8 E5:4 C#5:4 |",
        bass="@bass !mp G1:8 D2:8 | F#1:8 A1:8 | E1:8 B1:8 | A1:8 E2:8 | "
             "G1:8 D2:8 | B1:8 F#2:8 | E1:8 G1:8 | A1:16 |",
        harm="@cello !p D4:16 | A3:16 | B3:16 | C#4:16 | D4:16 | D4:16 | B3:16 | C#4:16 |",
        pad="!pp B3:16 | D4:16 | E4:16 | A3:16 | B3:16 | F#4:16 | G4:16 | E4:16 |",
        rhy="!mp L4 G3 B3 D4 G4 | F#3 A3 D4 A3 | E3 G3 B3 G3 | A2 E3 A3 C#4 | "
            "G3 B3 D4 G4 | B2 D3 F#3 B3 | E3 G3 B3 E4 | A2 C#3 E3 A3 |",
        drum="!mp G2:4 r:12 | D2:4 r:12 | E2:4 r:12 | A2:4 r:12 | "
             "G2:4 r:12 | B2:4 r:12 | E2:4 r:12 | A2:4 r:12 |")

    # -- the road again, with everybody: oboe carries it, flute sings above,
    # the horn doubles it an octave down for weight. The brass is under the
    # tune, not on top of it -- a trumpet on these notes is the harshest thing
    # in the palette by 15dB, and this is the theme that plays most.
    t.section('C', chords=ROAD_CHORDS,
        lead="@oboe !mf " + ROAD,
        x2="@flute !mp " + xp(ROAD, 12),
        harm="@horn !f " + xp(ROAD, -12),
        bass="@bass !mf D2:4 A2:4 D2:4 A2:4 | G1:4 D2:4 G1:4 D2:4 | "
             "F#1:4 A1:4 D2:4 A1:4 | A1:4 E2:4 A1:4 E2:4 | "
             "B1:4 F#2:4 B1:4 F#2:4 | G1:4 D2:4 G1:4 D2:4 | "
             "A1:4 E2:4 A1:4 C#2:4 | D2:4 A1:4 D2:8 |",
        pad="!p A3:16 | B3:16 | D4:16 | A3:16 | F#4:16 | D4:16 | E4:16 | F#4:16 |",
        rhy="!mp L4 D3 F#3 A3 D4 | G2 B2 D3 G3 | F#2 A2 D3 A2 | A2 C#3 E3 A3 | "
            "B2 D3 F#3 B3 | G2 B2 D3 G3 | A2 C#3 E3 C#3 | D3 F#3 A3 D4 |",
        drum="@timp !mf D2:4 r:4 D2:4 r:4 | G2:4 r:4 G2:4 r:4 | D2:4 r:4 D2:4 r:4 | A2:4 r:4 A2:4 r:4 | "
             "B2:4 r:4 B2:4 r:4 | G2:4 r:4 G2:4 r:4 | A2:4 r:4 A2:4 r:4 | D2:4 r:4 D2:8 |",
        x1="@tambourine !mp r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | "
           "r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:8 |")

    t.play('intro', 'A', 'B', 'C', loop=1)
    return t
