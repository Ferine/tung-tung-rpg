#!/usr/bin/env python3
"""The score, part two: the themes where the ideas meet.

The title, the two shapes of the last boss, the victory cadence and the ending
are the places the game's three ideas -- the call, the road, the lullaby --
face each other, so they are written together and share notes on purpose.
The title states the whole story in a minute: the lullaby (the world asleep),
the drum breaks in, the road sets out, and the tune is sung in full. The ending
answers it. Il Silenzio's two shapes are the lullaby at its most seductive, and
then the same tune with its patience gone.
"""
from themes_road import (xp, stretch, ROAD, ROAD_CHORDS, CALL, LULLABY_Q,
                         LULLABY_A, LULLABY_CHORDS, LULLABY_ANSWER_CHORDS,
                         SLIDE)
from score import Theme

# The road's inner line, one bar to a bar, that FIELD and the title share.
_INNER = ["F#4", "G4", "A4", "E4", "D4", "B3", "C#4", "A3"]
_PAD = ["A3", "B3", "D4", "A3", "F#4", "D4", "E4", "F#4"]
_ROOTS = ["D2", "G1", "F#1", "A1", "B1", "G1", "A1", "D2"]
_TIMP = ["D2", "G2", "D2", "A2", "B2", "G2", "A2", "D2"]
_ARP = ["D3 F#3 A3 D4", "G2 B2 D3 G3", "F#2 A2 D3 A2", "A2 C#3 E3 A3",
        "B2 D3 F#3 B3", "G2 B2 D3 G3", "A2 C#3 E3 C#3", "D3 F#3 A3 D4"]


def _bars(items, dur, joiner=" | "):
    """['A3', 'B3'] -> 'A3:8 | B3:8 |'"""
    return joiner.join("%s:%d" % (n, dur) for n in items) + " |"


def title():
    """The title screen, and the whole game in ninety seconds.

    It goes round: the world asleep (the lullaby, barely there); the drum
    breaks in (the call, on the kentongan, answered by a horn a long way off,
    and a roll that will not stop climbing); the road sets out, soft; it is
    sung in full, with the organ under it and a tuba for a floor; and then it
    is sung again a whole step higher by everybody, and the tempo leans
    forward, and the last thing in the room is the drum. Then the big chord
    dies away and the lullaby comes back, because the title is a place you can
    sit in for as long as you like, and it should not resolve and stop.

    The lift is the thing people remember: the same tune, the same four
    notes, and suddenly the key is out of reach of where you started."""
    t = Theme('TITLE', bpm=84, beats=4, grid=2, key='D', voices=dict(
        lead='flute', bass='bass', harm='horn', pad='strings_lo',
        rhy='harp', drum='timp', x1='tubebell', x2='flute'))
    tune = stretch(ROAD, 0.5)           # the road, eight rows a bar

    # -- the world asleep. The bass falls in thirds under a falling tune.
    t.section('dawn', chords=LULLABY_CHORDS,
        lead="@flute !pp " + LULLABY_Q,
        bass="@bass !p D2:8 | B1:8 | G1:8 | A1:8 |",
        pad="@strings_lo !pp A3:8 | F#4:8 | D4:8 | E4:8 |",
        x1="@tubebell !p D5:8 | r:8 | r:8 | r:8 |")

    # -- the drum breaks in: the call, and a horn answering from far off. Then
    # the timpani start to roll and do not stop, swelling into the road.
    t.section('call', chords="D | D | A | A",
        rhy="@kentong !f A3:2 A3:2 A3:2 D4:2 | r:8 | A3:2 A3:2 A3:2 D4:2 | r:8 |",
        harm="@horn !mp r:8 | D3:8 | r:8 | A3:8 |",
        bass="@bass_lo !p D1:8 | -:8 | A1:8 | -:8 |",
        pad="@strings_lo !p A3:8 | -:8 <12,30> | E4:8 | -:8 <14,38> |",
        drum="@timp !p r:8 | D2:8 | !mp A2:2 A2:2 A2:2 A2:2 | "
             "!mp A2:1 A2:1 A2:1 A2:1 !mf A2:1 A2:1 !f A2:1 A2:1 |")

    # -- the road sets out, soft
    t.section('road', chords=ROAD_CHORDS, bpm=88,
        lead="@oboe !mp " + tune,
        harm="@clarinet !p " + _bars(_INNER, 8),
        pad="@strings_lo !pp " + _bars(_PAD, 8),
        bass="@bass !mp D2:4 A1:4 | G1:4 D2:4 | F#1:4 A1:4 | A1:4 E2:4 | "
             "B1:4 F#2:4 | G1:4 D2:4 | A1:4 E2:4 | D2:8 |",
        rhy="@harp !mp " + " | ".join(" ".join("%s:2" % n for n in a.split())
                                      for a in _ARP) + " |",
        drum="@timp !p " + " | ".join("%s:2 r:6" % n for n in _TIMP) + " |",
        x1="@tubebell !p r:8 | r:8 | r:8 | r:6 A5:2 | r:8 | r:8 | r:8 | r:6 A5:2 |")

    # -- and then everyone: the oboe carries it, the flute sings above, the
    # horn doubles it an octave down, the organ fills the room under it and a
    # tuba is the floor. A gong opens it and a cymbal halfway marks the turn.
    t.section('full', chords=ROAD_CHORDS, bpm=92,
        lead="@oboe !f " + tune.replace("D5:6 r:2 |", "D5:6~ r:2 |"),
        x2="@flute !mp " + xp(tune, 12),
        harm="@horn !f " + xp(tune, -12),
        pad="@organ !mp " + _bars(_PAD, 8),
        bass="@tuba !mf D2:4 A1:4 | G1:4 D2:4 | F#1:4 A1:4 | A1:4 E2:4 | "
             "B1:4 F#2:4 | G1:4 D2:4 | A1:4 E2:4 | D2:8 |",
        # the harp gathers pace into the second half -- quarters, then running
        # eighths -- so the second statement of the tune is not merely louder
        rhy="@harp !mp " + " | ".join(
            [" ".join("%s:2" % n for n in a.split()) for a in _ARP[:4]] +
            ["B2:1 D3:1 F#3:1 B3:1 F#3:1 D3:1 B3:1 F#3:1",
             "G2:1 B2:1 D3:1 G3:1 D3:1 B2:1 G3:1 D3:1",
             "A2:1 C#3:1 E3:1 A3:1 E3:1 C#3:1 A3:1 E3:1",
             "D3:1 F#3:1 A3:1 D4:1 A3:1 F#3:1 D4:1 A3:1"]) + " |",
        drum="@gong !mf C4:2 @timp D2:2 r:2 D2:2 | G2:2 r:2 G2:2 r:2 | "
             "D2:2 r:2 D2:2 r:2 | A2:2 r:2 A2:2 r:2 | "
             "B2:2 B2:2 B2:2 B2:2 | G2:2 G2:2 G2:2 G2:2 | "
             "A2:2 A2:2 A2:2 A2:2 | D2:2 D2:2 D2:4 |",
        x1="@cymbal !mp C4:8 | r:8 | r:8 | r:8 | C4:8 | r:8 | r:8 | r:8 |")

    # -- the lift. The same road, a whole step up (D to E), sung by the violins
    # and the oboe together, the flute an octave over them, the horn an octave
    # under, the organ and the tuba holding the floor down, the timpani on
    # every beat, and the tempo leaning forward. Everything in the ensemble
    # is playing the tune; nobody is playing anything else, and that is what
    # makes it large.
    up = xp(tune, 2)
    t.section('climax', chords="E | A | E/G# | B | C#m | A | B | E", bpm=100,
        lead="@strings !f " + up.replace("E5:6 r:2 |", "E5:6~ r:2 |"),
        x2="@oboe !f " + up,
        rhy="@flute !mp " + xp(up, 12),
        harm="@horn !ff " + xp(up, -12),
        pad="@organ !mf " + " | ".join("%s:8" % xp(n, 2) for n in _PAD) + " |",
        bass="@tuba !f E2:4 B1:4 | A1:4 E2:4 | G#1:4 B1:4 | B1:4 F#2:4 | "
             "C#2:4 G#2:4 | A1:4 E2:4 | B1:4 F#2:4 | E2:8 |",
        drum="@timp !f E2:2 E2:2 E2:2 E2:2 | A2:2 A2:2 A2:2 A2:2 | "
             "E2:2 E2:2 E2:2 E2:2 | B2:2 B2:2 B2:2 B2:2 | "
             "E2:2 E2:2 E2:2 E2:2 | A2:2 A2:2 A2:2 A2:2 | "
             "!ff B2:2 B2:2 B2:2 B2:2 | E2:2 E2:2 E2:2 E2:2 |",
        x1="@cymbal !mf C4:8 | r:8 | r:8 | r:8 | C4:8 | r:8 | r:8 | C4:8 |")

    # -- the last word, which is the drum's: TUNG. TUNG. TUNG. -- and the lift,
    # low, under a chord that every instrument holds and then lets go. It
    # is the same call that opened the title, and the thing the whole game is
    # named for. Unique, because it carries the jump back to the lullaby.
    t.section('finale', chords="E | E", bpm=76,
        lead="@strings !ff E5:8 | -:8 <52,4> |",
        x2="@oboe !f B4:8 | -:8 <46,4> |",
        rhy="@flute !mp B5:8 | -:8 <34,4> |",
        harm="@horn !ff E4:8 | -:8 <52,4> |",
        pad="@organ !mf B3:8 | -:8 <40,4> |",
        bass="@tuba !f E2:8 | -:8 <48,4> |",
        drum="@kentong !ff B2:2 B2:2 B2:2 E3:2 | r:8 |",
        x1="@gong !mf C4:8 | r:8 |")

    t.play('dawn', 'call', 'road', 'full', 'climax', 'finale', loop=0)
    return t


def fanfare():
    """Victory. The call, as a rising sequence, and the drum has the last
    word.

    Three statements of the same shout -- three repeated notes and a leap up
    a fourth, da-da-da DAH -- each one a fourth above the last (A to D, then D
    to G, then E to A), so it climbs without changing shape: the thing that
    makes a fanfare sound like a fanfare and not like a chord. The timpani
    echo the rhythm under each one; on the fourth bar everybody arrives and
    the timpani roll, the harp sweeps up, a cymbal opens; and then the
    kentongan answers the orchestra with the call on its own -- TUNG. TUNG.
    TUNG. -- as the whole cadence rings out beneath it. Five bars, about
    seven seconds, and then silence: the last section of every theme is the one
    that jumps, so this one jumps to a bar of nothing, and the game has the
    quiet it needs for the reward screen.

    It is the horn's shout, not a trumpet's. A trumpet on these notes is the
    harshest thing in the palette by some 15dB -- this fanfare measured -6dB
    on the ear-weighted shrillness scale with one, and -16dB without it -- and
    a fanfare is its rhythm and its climb, not its timbre. So the horn calls,
    the violins ring an octave above it, the trombone and tuba are the floor,
    and it is as big as a brass section without the part of one that hurts."""
    t = Theme('FANFARE', bpm=160, beats=4, grid=4, key='D', voices=dict(
        lead='horn', bass='tuba', harm='strings', pad='trombone',
        rhy='harp', drum='timp', x1='cymbal', x2='flute'))
    roll = ("!mf D2:1 D2:1 D2:1 D2:1 !f D2:1 D2:1 D2:1 D2:1 "
            "!ff D2:1 D2:1 D2:1 D2:1")
    t.section('win', chords="D | G | A | D | D",
        lead="@horn !ff A3:2 A3:2 A3:2 D4:8 r:2 | D4:2 D4:2 D4:2 G4:8 r:2 | "
             "E4:2 E4:2 E4:2 A4:8 r:2 | D5:16~ | D5:16 <52,4> |",
        harm="@strings !mf A4:2 A4:2 A4:2 D5:8 r:2 | D5:2 D5:2 D5:2 G5:8 r:2 | "
             "E5:2 E5:2 E5:2 A5:8 r:2 | A5:16 | A5:16 <40,4> |",
        # the flute rides above the violins from the second statement on: the
        # sparkle on top of the brass, at a level that is light rather than shrill
        x2="@flute !mp r:16 | D6:2 D6:2 D6:2 G6:8 r:2 | "
           "E6:2 E6:2 E6:2 A6:8 r:2 | D6:16 | D6:16 <36,4> |",
        pad="@trombone !f D3:16 | G2:16 | A2:16 | D3:16 | D3:16 <44,4> |",
        bass="@tuba !f D2:2 D2:2 D2:2 D2:8 r:2 | G1:2 G1:2 G1:2 G1:8 r:2 | "
             "A1:2 A1:2 A1:2 A1:8 r:2 | D2:16 | D2:16 <48,4> |",
        drum="@timp !f D2:2 D2:2 D2:2 D2:8 r:2 | G2:2 G2:2 G2:2 G2:8 r:2 | "
             "A2:2 A2:2 A2:2 A2:8 r:2 | " + roll + " D2:4 | "
             "@kentong !ff A3:4 A3:4 A3:4 D4:4 |",
        rhy="@harp !mf r:16 | r:16 | r:16 | D3:1 F#3:1 A3:1 D4:1 F#4:1 A4:1 "
            "D5:1 F#5:1 r:8 | r:16 |",
        x1="@cymbal !mf r:16 | r:16 | r:16 | C4:16 | r:16 |")
    t.section('end', chords="D", lead="@flute r:16 |")
    t.play('win', 'end', loop=1)
    return t


# ---- Il Silenzio -------------------------------------------------------------
#
# The last boss is not a monster. It has built something better than the world
# -- no road, no morning, no effort -- and is genuinely bewildered that anybody
# would object. It fights in two shapes: the first pleads, the second stops
# being polite. They are the same tune.

def final():
    """The first shape. The lullaby, at its most seductive.

    Everything about it is kind: a rocking harp that never changes, a horn
    holding one note under the whole second half (nothing changes; that is the
    offer), violins that fall by step over a bass that falls by step -- the
    tune sighing itself down forever. And through it, twice a loop, very
    quietly, the kentongan: TUNG. TUNG. TUNG. -- the only thing in the room
    asking anybody to get up, and the music simply absorbs it."""
    t = Theme('FINAL', bpm=66, beats=4, grid=2, key='D', voices=dict(
        lead='flute', bass='bass', harm='horn', pad='strings_lo',
        rhy='harp', drum='timp', x1='tubebell', x2='clarinet'))

    rock = ("D3:2 A3:2 F#3:2 A3:2", "B2:2 F#3:2 D3:2 F#3:2",
            "G2:2 D3:2 B2:2 D3:2", "A2:2 E3:2 C#3:2 E3:2")

    t.section('intro', chords="D | D",
        rhy="@harp !mp " + rock[0] + " | " + rock[0] + " |",
        pad="@strings_lo !pp A3:8 | -:8 <10,26> |",
        bass="@bass !pp D2:8 | -:8 |")

    # -- the plea, sung by the flute: the lullaby, both halves
    t.section('A', chords=LULLABY_CHORDS + " | " + LULLABY_ANSWER_CHORDS,
        lead="@flute !mf " + LULLABY_Q + " " +
             LULLABY_A.replace("D5:8 |", "D5:8~ |"),
        x2="@clarinet !mp r:8 | r:8 | r:8 | r:8 | " + xp(LULLABY_A, -12),
        harm="@horn !mp F#3:8 | F#3:8 | G3:8 | A3:8 | F#3:8 | G3:8 | A3:8 | D3:8 |",
        pad="@strings_lo !p A3:8 | F#4:8 | D4:8 | E4:8 | A3:8 | D4:8 | E4:8 | F#4:8 |",
        bass="@bass !mp D2:8 | B1:8 | G1:8 | A1:8 | D2:8 | G1:8 | A1:8 | D2:8 |",
        rhy="@harp !mf " + " | ".join([rock[0], rock[1], rock[2], rock[3], rock[0], rock[2], rock[3], rock[0]]) + " |",
        x1="@tubebell !p D5:8 | r:8 | r:8 | r:8 | D5:8 | r:8 | r:8 | r:8 |")

    # -- it presses: the sighs fall in thirds and the bass falls in steps
    # under them (Pachelbel's descent, D to E), while the horn holds A and does
    # not move at all. The drum comes in on the seventh bar and is ignored.
    sighs = ("F#5:3 E5:1 D5:4 | E5:3 D5:1 C#5:4 | D5:3 C#5:1 B4:4 | "
             "C#5:3 B4:1 A4:4 | B4:3 A4:1 G4:4 | A4:3 G4:1 F#4:4 | "
             "G4:3 F#4:1 E4:4 | E4:4 C#5:4 |")
    t.section('B', chords="D | A/C# | Bm | F#m/A | G | D/F# | Em | A",
        lead="@strings !mf " + sighs,
        harm="@horn !mp A3:8 | " + " | ".join(["-:8"] * 7) + " |",
        pad="@strings_lo !p A3:8 | E4:8 | F#4:8 | C#4:8 | D4:8 | D4:8 | G4:8 | E4:8 |",
        bass="@bass !mp D2:8 | C#2:8 | B1:8 | A1:8 | G1:8 | F#1:8 | E1:8 | A1:8 |",
        rhy="@harp !mf D3:2 A3:2 F#3:2 A3:2 | C#3:2 E3:2 A3:2 E3:2 | "
            "B2:2 F#3:2 D3:2 F#3:2 | A2:2 C#3:2 F#3:2 C#3:2 | "
            "G2:2 D3:2 B2:2 D3:2 | F#2:2 A2:2 D3:2 A2:2 | "
            "E3:2 G3:2 B3:2 G3:2 | A2:2 E3:2 C#3:2 E3:2 |",
        drum="@timp !p r:8 | r:8 | r:8 | r:8 | D2:2 r:6 | D2:2 r:6 | "
             "@kentong !mp A3:2 A3:2 A3:2 D4:2 | @timp !p A2:2 r:6 |")

    t.play('intro', 'A', 'B', loop=1)
    return t


# The lullaby with its patience gone: the same falling thirds in D minor, with
# the F, C and B-flat that turn a sigh into a threat. Sixteenth grid.
_MINOR_Q = "F5:6 E5:2 D5:8 | D5:6 C5:2 Bb4:8 | Bb4:6 A4:2 G4:8 | A4:8 C#5:8 |"
_MINOR_A = "F5:6 E5:2 D5:8 | Bb4:6 C5:2 D5:8 | E5:6 D5:2 C#5:8 | D5:16 |"
_MINOR_CHORDS = "Dm | Bb | Gm | A | Dm | Gm | A | Dm"


def _riff(root, third):
    """One bar of the riff, sixteen rows: the root pushed, then a rest, then
    the third for the pull, then home."""
    return "%s:3 %s:1 r:2 %s:2 %s:4 %s:4" % (root, root, root, third, root)


def final2():
    """The second shape. The same tune, and it has stopped being polite.

    The riff underneath is the lullaby's bass -- D, B-flat, G, A: the falling
    thirds -- turned into something with teeth. Then the slide: violins
    descending by semitone over a pedal that never moves, while the
    kentongan hammers the call every single bar. The drum does not stop, and
    neither does the descent, and for the length of the section neither one
    wins. Then the tune, in minor, with everything behind it. The weight is in
    the low brass and the timpani, not the top of the range: this is the loud
    one, and it still must not hurt."""
    t = Theme('FINAL2', bpm=152, beats=4, grid=4, key='D', voices=dict(
        lead='horn', bass='bass', harm='trombone', pad='strings_lo',
        rhy='tuba', drum='kick', x1='cymbal', x2='oboe'))

    riff = [_riff('D2', 'F2'), _riff('Bb1', 'D2'), _riff('G1', 'Bb1'),
            _riff('A1', 'C#2'), _riff('D2', 'F2'), _riff('G1', 'Bb1'),
            _riff('A1', 'C#2'), "D2:3 D2:1 r:2 D2:2 D2:8"]
    kit = "@kick !f C4:4 @snare C4:4 @kick C4:4 @snare C4:4"

    # -- the silence cracks: a roll that will not stop climbing
    t.section('intro', chords="Dm | Dm",
        bass="@bass_lo !mp D1:16 | -:16 |",
        harm="@organ !mp D3:16 | -:16 <20,44> |",
        drum="@timp !p D2:2 D2:2 !mp D2:2 D2:2 !mf D2:2 D2:2 !f D2:2 D2:2 | "
             "!ff D2:4 A2:4 D2:8 |",
        x1="@cymbal !mf r:16 | C4:16 |")

    # -- the riff, and the tune over it
    t.section('A', chords=_MINOR_CHORDS,
        lead="@horn !mf " + _MINOR_Q + " " + _MINOR_A,
        x2="@clarinet !mp " + _MINOR_Q + " " + _MINOR_A,
        bass="@bass !f " + " | ".join(riff) + " |",
        pad="@strings_lo !p A3:16 | F4:16 | D4:16 | E4:16 | A3:16 | D4:16 | E4:16 | F4:16 |",
        drum=" | ".join([kit] * 8) + " |")

    # -- the slide against the call: a chord that will not change, a line that
    # will not stop falling, a drum that will not stop asking. No chord
    # symbols: the line is *meant* to grind against the pedal.
    t.section('B', chords=None,
        bass="@bass !mf D2:16 | " + " | ".join(["-:16"] * 7) + " |",
        rhy="@tuba !mp D1:16 | " + " | ".join(["-:16"] * 7) + " |",
        pad="@strings !mf E5:16 | D#5:16 | D5:16 | C#5:16 | C5:16 | B4:16 | Bb4:16 | A4:16 |",
        harm="@trombone !mp D3:16 | -:16 | F3:16 | -:16 | Bb2:16 | -:16 | A2:16 | -:16 |",
        drum="@kentong !f " + " | ".join(["A3:4 A3:4 A3:4 D4:4"] * 8) + " |")

    # -- and then everything: the tune with the whole orchestra, the low brass
    # under it, and a fill into the loop. Unique, because it holds the jump.
    t.section('C', chords=_MINOR_CHORDS,
        lead="@horn !f " + _MINOR_Q + " " + _MINOR_A,
        x2="@oboe !mp " + _MINOR_Q + " " + _MINOR_A,
        harm="@trombone !mf D3:16 | Bb2:16 | G2:16 | A2:16 | D3:16 | G2:16 | A2:16 | D3:16 |",
        rhy="@tuba !mf D2:16 | Bb1:16 | G1:16 | A1:16 | D2:16 | G1:16 | A1:16 | D2:16 |",
        pad="@strings_lo !mp A3:16 | F4:16 | D4:16 | E4:16 | A3:16 | D4:16 | E4:16 | F4:16 |",
        bass="@bass !f " + " | ".join(riff) + " |",
        drum="@kick !f C4:4 @snare C4:4 @kick C4:4 @snare C4:4 | " +
             " | ".join([kit] * 6) + " | "
             "@snare !f C4:2 C4:2 !ff C4:2 C4:2 C4:2 C4:2 C4:2 C4:2 |",
        x1="@cymbal !mf C4:16 | " + " | ".join(["r:16"] * 7) + " |")

    t.play('intro', 'A', 'B', 'C', loop=1)
    return t


# ---- the ending --------------------------------------------------------------

def ending():
    """SAHUR E SERVITO. One by one the windows light; somebody puts a pot on,
    somebody complains about the hour, and a shark, a tree, a cactus and a
    bomber stand in a village square at four in the morning arguing about
    breakfast. It is the one unambiguous sunrise in the score.

    It is built from all three ideas coming right. The windows are the call,
    passed up the instruments one by one. The pot is the road, in a major key
    with everybody singing. The argument is the call again, thrown between
    the woodwinds like an insult. And the last section is the lullaby -- the
    Sleep's own tune, now just a thing you hum -- and the road's ending, and
    three strokes of the kentongan, which is also where the next loop starts:
    somebody wakes up the village every four in the morning."""
    t = Theme('ENDING', bpm=108, beats=4, grid=4, key='D', voices=dict(
        lead='flute', bass='pizz_cb', harm='horn', pad='strings_lo',
        rhy='harp', drum='timp', x1='tambourine', x2='flute'))

    # -- windows: the call, one voice at a time, each a little higher
    t.section('windows', chords="D | D | A | D",
        rhy="@kentong !mf A3:4 A3:4 A3:4 D4:4 | r:16 | r:16 | @kentong !f A3:4 A3:4 A3:4 D4:4 |",
        lead="r:16 | @marimba !mf D5:2 F#5:2 A5:2 F#5:2 D5:2 E5:2 F#5:4 | "
             "@harp !mf A4:2 C#5:2 E5:2 C#5:2 A4:2 B4:2 C#5:4 | "
             "@flute !mf A5:4 A5:4 A5:4 D6:4 |",
        bass="r:16 | r:16 | @pizz_cb !mp A1:4 E2:4 A1:4 E2:4 | D2:4 A1:4 D2:8 |",
        pad="r:16 | r:16 | @strings_lo !p E4:16 | A3:16 |",
        harm="r:16 | r:16 | r:16 | @horn !mp D3:16 |")

    # -- the pot: the road, sung in a major key by everyone
    t.section('pot', chords=ROAD_CHORDS,
        lead="@flute !mf " + ROAD.replace("| B4:4 B4:4", "| @oboe B4:4 B4:4"),
        x2="@flute !mp r:16 | r:16 | r:16 | r:16 | " + xp("B4:4 B4:4 B4:4 F#5:4 | E5:6 D5:2 B4:8 | C#5:4 D5:4 E5:4 C#5:4 | D5:12 r:4 |", 12),
        harm="@horn !mp " + xp(ROAD, -12),
        pad="@strings_lo !p A3:16 | B3:16 | D4:16 | A3:16 | F#4:16 | D4:16 | E4:16 | F#4:16 |",
        bass="@pizz_cb !mf D2:4 A1:4 D2:4 A1:4 | G1:4 D2:4 G1:4 D2:4 | "
             "F#1:4 A1:4 D2:4 A1:4 | A1:4 E2:4 A1:4 E2:4 | "
             "B1:4 F#2:4 B1:4 F#2:4 | G1:4 D2:4 G1:4 D2:4 | "
             "A1:4 E2:4 A1:4 C#2:4 | D2:4 A1:4 D2:8 |",
        rhy="@marimba !mp r:2 D4:2 r:2 F#4:2 r:2 A4:2 r:2 F#4:2 | r:2 D4:2 r:2 G4:2 r:2 B4:2 r:2 G4:2 | "
            "r:2 D4:2 r:2 F#4:2 r:2 A4:2 r:2 F#4:2 | r:2 C#4:2 r:2 E4:2 r:2 A4:2 r:2 E4:2 | "
            "r:2 D4:2 r:2 F#4:2 r:2 B4:2 r:2 F#4:2 | r:2 D4:2 r:2 G4:2 r:2 B4:2 r:2 G4:2 | "
            "r:2 C#4:2 r:2 E4:2 r:2 A4:2 r:2 E4:2 | r:2 D4:2 r:2 F#4:2 r:2 A4:2 D5:4 |",
        drum="@timp !mp D2:4 r:12 | G2:4 r:12 | D2:4 r:12 | A2:4 r:12 | "
             "B2:4 r:12 | G2:4 r:12 | A2:4 r:12 | D2:4 r:12 |",
        x1="@tambourine !p r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | "
           "r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:4 C4:4 | r:4 C4:4 r:8 |")

    # -- the argument: the call thrown between the woodwinds
    t.section('argue', chords="D | D | G | G | A | A | D | D",
        lead="@bassoon !mf A2:2 A2:2 A2:2 D3:6 r:4 | r:16 | "
             "@bassoon G2:2 G2:2 G2:2 C3:6 r:4 | r:16 | "
             "@oboe E5:2 E5:2 E5:2 A5:6 r:4 | r:16 | "
             "@flute A5:2 A5:2 A5:2 D6:6 r:4 | @flute D6:12 r:4 |",
        harm="@clarinet !mf r:16 | A4:2 A4:2 A4:2 D5:6 r:4 | r:16 | "
             "G4:2 G4:2 G4:2 C5:6 r:4 | r:16 | E5:2 E5:2 E5:2 A5:6 r:4 | r:16 | F#5:12 r:4 |",
        pad="@strings_lo !p A3:16 | -:16 | D4:16 | -:16 | E4:16 | -:16 | A3:16 | -:16 |",
        bass="@pizz_cb !mf D2:4 r:4 A1:4 r:4 | D2:4 r:4 A1:4 r:4 | G1:4 r:4 D2:4 r:4 | "
             "G1:4 r:4 D2:4 r:4 | A1:4 r:4 E2:4 r:4 | A1:4 r:4 E2:4 r:4 | "
             "D2:4 r:4 A1:4 r:4 | D2:16 |",
        rhy="@harp !mp D3:2 A3:2 F#4:2 A3:2 D3:2 A3:2 F#4:2 A3:2 | D3:2 A3:2 F#4:2 A3:2 D3:2 A3:2 F#4:2 A3:2 | "
            "G2:2 D3:2 B3:2 D3:2 G2:2 D3:2 B3:2 D3:2 | G2:2 D3:2 B3:2 D3:2 G2:2 D3:2 B3:2 D3:2 | "
            "A2:2 E3:2 C#4:2 E3:2 A2:2 E3:2 C#4:2 E3:2 | A2:2 E3:2 C#4:2 E3:2 A2:2 E3:2 C#4:2 E3:2 | "
            "D3:2 A3:2 F#4:2 A3:2 D3:2 A3:2 F#4:2 A3:2 | D3:16 |",
        drum="@timp !mp r:16 | r:16 | r:16 | r:16 | r:16 | r:16 | r:16 | @timp !mf D2:4 r:12 |")

    # -- sahur e servito: the lullaby, hummed; the road's last phrase, sung;
    # and three strokes on the kentongan, which is also the first thing the
    # windows do.
    t.section('sahur', chords=LULLABY_CHORDS + " | Bm | G | A | D",
        lead="@flute !mp " + stretch(LULLABY_Q, 2) + " @oboe !mf B4:4 B4:4 B4:4 F#5:4 | "
             "E5:6 D5:2 B4:8 | C#5:4 D5:4 E5:4 C#5:4 | D5:8~ r:8 |",
        harm="@horn !p " + xp(stretch(LULLABY_Q, 2), -12) + " !mf " +
             xp("B4:4 B4:4 B4:4 F#5:4 | E5:6 D5:2 B4:8 | C#5:4 D5:4 E5:4 C#5:4 | D5:12 r:4 |", -12),
        pad="@strings_lo !p A3:16 | F#4:16 | D4:16 | E4:16 | F#4:16 | D4:16 | E4:16 | F#4:16 |",
        bass="@bass !mp D2:16 | B1:16 | G1:16 | A1:16 | B1:16 | G1:16 | A1:16 | D2:16 |",
        rhy="@harp !mp D3:4 A3:4 F#4:4 A3:4 | B2:4 F#3:4 D4:4 F#3:4 | G2:4 D3:4 B3:4 D3:4 | "
            "A2:4 E3:4 C#4:4 E3:4 | B2:4 F#3:4 D4:4 F#3:4 | G2:4 D3:4 B3:4 D3:4 | "
            "A2:4 E3:4 C#4:4 E3:4 | D3:4 F#3:4 A3:4 D4:4 |",
        drum="@timp !mp r:16 | r:16 | r:16 | r:16 | r:16 | r:16 | @timp !mf A2:4 r:12 | "
             "@kentong !f r:4 A3:4 A3:4 D4:4 |")

    t.play('windows', 'pot', 'argue', 'sahur', loop=0)
    return t
