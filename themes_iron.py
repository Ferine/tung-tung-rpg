#!/usr/bin/env python3
"""The score, part three: the two places built of things that do not change.

  SALT      Padang Garam. A watch that has said twelve minutes past three for a
            month, and a flat that has grown nothing since before the Sleep.
            A stuck clock, so the music is a loop that is honest about being
            one: twelve bars, three phrases, and none of them arrives.
  FORTRESS  Langit Besi. Iron and sky; a bomber who flies orders that *arrive*.
            The road, bent into E minor and handed to the low brass.
"""
from score import Theme
from themes_road import xp, stretch, CALL


# ---- SALT -------------------------------------------------------------------
#
# 3/4, an eighth to the row, six rows to the bar. A Phrygian, and hardly any of
# it: the harmony is bare fifths (root in the bass, fifth in the strings) so the
# mode is decided only by the clarinet, and a fifth cannot say major or minor.
#
# THE STUCK CLOCK.  Every beat, a claves tick, dry, on x1 -- tick tock tock.
# It never stops and never changes, which is the joke and the dread. The tune
# is twelve bars in three four-bar phrases (twelve minutes), and no phrase
# cadences: the first ends on an A hanging over a G and dies into an empty bar
# over E, the second on a B-flat that wants to fall to the A and never does, the
# third in silence over E. The loop is the point;
# the time does not move, so the music does not get anywhere, it only comes
# round. One low tubebell strike at the top of each cycle is the hour.
#
# The tune, in three arches, each a little higher (C, F, G) and each with the
# same rhythm (a long note, then long-short) -- the sarabande stress on beat 2,
# so bars begin with a beat of air. The leap up a minor sixth is its signature.
#   bar:  1 A  2 A  3 G  4 E | 5 A  6 Bb  7 A  8 G | 9 F  10 G  11 F  12 E
#   bass: root of each bar (the line falls A A G E / A Bb A G / F G F E)
#   pad:  the fifth above it, so the strings move in parallel fifths --
#         organum, on purpose: the oldest way of writing something empty.

SALT_CHORDS = "A5 | A5 | G5 | E5 | A5 | Bb5 | A5 | G5 | F5 | G5 | F5 | E5"

# The clock. Tick tock tock -- three equal strokes to the bar: it is THE CALL
# (the kentongan's TUNG TUNG TUNG) with the leap taken away, going on for ever
# with nothing to lift it. The first beat leans a little; the echo is off so
# it is a dry click in a room with no air in it. `first` carries the echo switch.
_TICK = " C4:2v24 C4:2v16 C4:2v16 |"


def _ticks(n, first='', last=''):
    """n bars of clock. `first` and `last` are tokens for the very first and
    very last tick -- the echo switch, which persists across the loop."""
    text = _TICK * n
    if first:
        text = first + text
    if last:
        end = " C4:2v16 |"
        text = text[:-len(end)] + " " + last + end
    return text


def salt():
    t = Theme('SALT', bpm=66, beats=3, grid=2, key='A', voices=dict(
        lead='clarinet', bass='bass', harm='strings_lo', pad='strings_lo',
        rhy='oboe', x1='claves', x2='tubebell'))

    # -- the fifths: bass root, strings on top. Held over two bars where the
    # chord holds; `_` (no release) so the bar lines are not gaps.
    bass = ("!28 A2:6_ | -:6 | G2:6_ | E2:6_ | A2:6_ | Bb2:6_ | A2:6_ | G2:6_ | "
            "F2:6_ | G2:6_ | F2:6_ | E2:6 |")
    fifths = ("!18 E4:6_ | -:6 | D4:6_ | B3:6_ | E4:6_ | F4:6_ | E4:6_ | D4:6_ | "
              "C4:6_ | D4:6_ | C4:6_ | B3:6 |")

    # -- the hour: a single low bell, then twelve bars of nothing to say
    bell = "!mp E4:6v30 | " + "r:6 | " * 11

    # -- the tune, three arches. A cycle is 72 rows; every line is written out
    # because each cycle is a little different.
    p1 = "r:2 E4:4v34 | C5:4v40 B4:2v34 | A4:6~ <38,20> | r:6 | "
    p1b = "r:2 E4:4v36 | C5:4v42 Bb4:2v34 | A4:6~ <40,20> | r:6 | "   # the bent note
    p2 = ("r:2 A4:4v36 | F5:4v42 D5:2v36 | C5:4v38 A4:2v34 | "
          "Bb4:6~ <38,20> | ")
    p3 = "r:2 A4:4v36 | G5:4v44 E5:2v36 | F5:4v40 C5:2v34 |  r:6 |"

    # cycle one: the clarinet alone in the white
    t.section('A', chords=SALT_CHORDS,
        lead="@clarinet !mp " + p1 + p2 + p3,
        bass=bass, pad=fifths, x2=bell,
        x1=_ticks(12, '#echo0'))

    # cycle two: an oboe answers from the far side of the flat, in the rests;
    # a drone on the tonic under everything, so the F and G chords turn into
    # F-major-seventh and G-suspended (the harmony stays put while the fifths
    # walk). Three small changes: the B in bar 2 bent to a B-flat, the bass an
    # octave down for phrase two, and the strings gone from the last two bars
    # -- one voice fewer, so the end of the cycle is the clock, the drone and
    # the oboe.
    t.section('A2', chords=SALT_CHORDS,
        lead="@clarinet !mp " + p1b + p2 + p3,
        rhy="@oboe !p r:6 | r:6 | r:6 | r:2 G4:4 | "
            "C5:6 | Bb4:6 | A4:6 | D5:6 | "
            "r:6 | r:6 | r:6 | r:2 B4:2 G4:2 |",
        harm="@strings_lo !16 A3:6_ | " + "-:6 | " * 11,
        bass="!28 A2:6_ | -:6 | G2:6_ | E2:6_ | A1:6_ | Bb1:6_ | A1:6_ | G1:6_ | "
             "F2:6_ | G2:6_ | F2:6_ | E2:6 |",
        pad="!18 E4:6_ | -:6 | D4:6_ | B3:6_ | E4:6_ | F4:6_ | E4:6_ | D4:6_ | "
            "C4:6_ | D4:6 | r:6 | r:6 |",
        x2=bell, x1=_ticks(12))

    # cycle three, the last: the tune with both voices, and then it thins out
    # and leads back. Phrases two and three go into the clarinet's dark low
    # register with the oboe on the tune at pitch -- an octave apart, which is
    # as bare as two voices can be -- and the G at the top of phrase three is
    # where they are furthest apart. The last bar is the clock, the drone, the
    # bass and one B in the clarinet: the fifth below the E that begins the
    # whole thing again, the call's own leap (B up to E) left half made.
    # (The clarinet's last note of phrase two is a D, not the B-flat an octave
    # down: a B-flat a semitone above the A drone in the same octave would beat.)
    lead_c = ("@clarinet !mp " + p1b +
              "r:2 A3:4v36 | F4:4v42 D4:2v36 | C4:4v38 A3:2v34 | "
              "D4:6~ <38,20> | "
              "r:2 A3:4v36 | G4:4v44 E4:2v36 | F4:4v40 C4:2v34 | "
              "r:4 B3:2v26 |")
    t.section('C', chords=SALT_CHORDS,
        lead=lead_c,
        rhy="@oboe !mp r:6 | r:6 | r:6 | r:2 G4:4v30 | " + p2 +
            "r:2 A4:4v36 | G5:4v46 E5:2v36 | F5:4v40 C5:2v34 | r:6 |",
        harm="@strings_lo !16 A3:6 | " + "-:6 | " * 11,
        bass="!28 A2:6_ | -:6 | G2:6_ | E2:6_ | A2:6_ | Bb2:6_ | A2:6_ | G2:6_ | "
             "F2:6_ | G2:6_ | F2:6_ | E2:6 <28,8> |",
        pad="!18 E4:6_ | -:6 | D4:6_ | B3:6_ | E4:6_ | F4:6_ | E4:6_ | D4:6_ | "
            "C4:6_ | D4:6_ | C4:6_ | B3:6 <20,6> |",
        x2=bell,
        x1=_ticks(12, last='#echo1'))

    t.play('A', 'A2', 'C', loop=0)
    return t


# ---- FORTRESS ---------------------------------------------------------------
#
# 4/4 at 124, E minor with the Phrygian F. Written on the eighth grid (a row is
# an eighth, eight rows a bar): a march needs no sixteenths, and a row costs two
# bytes whether or not anything happens in it.
#
# Iron and sky. The road is bent into E minor and handed to the low brass:
# trombone with the horn an octave above it (brass under and with the tune, no
# trumpet anywhere), the strings answering. The call survives -- three equal
# notes and a leap, B B B up to E -- and it returns in the second half a step
# higher and on C, the relative major, the one bright moment in the iron.
# The F is the bomb: E minor's flat second, the chord that drops on the tonic
# from a half-step above.
#
# THE ROAD, bent (horn octave; the trombone plays it an octave down):
#   bar  chord     what happens
#    1   Em        the call: B B B, up to E
#    2   F         reach: A C F, and hold the F -- the bomb
#    3   Em/G      fall: E D, B, G
#    4   Am | B    climb by step G A B and hold the dominant
#    5   C         the call again, on G, up to C -- a glimpse of major
#    6   F         the reach again
#    7   B         fall: D C B -- and on the B, the call's own leap
#    8   Em        ...up to E, and home. Then a beat of air.
# The bass climbs the Phrygian scale under it (E F G A B C ... B E), so the
# whole eight bars is one ascent with the tune falling through it.

# The call is the shared one -- three equal notes and a leap up a fourth -- moved
# from D to E (bar 1) and to C (bar 5): the same five-to-one gesture in the
# tonic and then in the relative major. The rest of the tune is new.
_CALL_E = stretch(xp(CALL, 2), 0.5)     # B B B E, an eighth to the row
_CALL_C = stretch(xp(CALL, -2), 0.5)    # G G G C

_HT = (_CALL_E + " A4:2 C5:2 F5:4 | E5:3 D5:1 B4:2 G4:2 | G4:2 A4:2 B4:4 | " +
       _CALL_C + " A4:2 C5:2 F5:4 | D5:2 C5:2 B4:4 | E5:6 r:2 |")


def _bars(text, i, j):
    """Bars i..j-1 of a written line."""
    parts = [b.strip() for b in text.split('|') if b.strip()]
    return ' | '.join(parts[i:j]) + ' |'


def fortress():
    t = Theme('FORTRESS', bpm=124, beats=4, grid=2, key='E', voices=dict(
        lead='trombone', bass='tuba', harm='horn', pad='organ',
        rhy='clarinet', drum='timp', x1='cymbal', x2='clarinet'))

    tt = xp(_HT, -12)               # the trombone: the tune an octave down

    # -- intro: the aircraft, far off. A tuba pedal, an organ fifth swelling
    # out of nothing, then the call without its leap on the trombone and timp.
    t.section('intro', chords="Em | Em",
        bass="!mf E1:8 | -:8 |",
        pad="@organ !pp E3:8 <8,30> | -:8 |",
        rhy="@organ !pp B3:8 <8,26> | -:8 |",
        lead="!mf r:8 | B3:2v34 B3:2v40 B3:2v46 r:2 |",
        drum="@timp !mp E2:2v40 r:6 | B2:2v34 B2:2v38 B2:2v44 "
             "@snare C4:1v26 C4:1v34 |",
        x2="@clarinet !mp r:8 | r:4 E3:1'v36 B3:1'v36 E3:1'v40 B3:1'v40 |")

    # -- A: the march. Low brass state the tune; at bar 5 the strings take it
    # (the answer, softer and higher, kept under D so they stay in their
    # compass) and the brass hold the chords under them; bars 7-8 the brass
    # bring it home.
    t.section('A', chords="Em | F | Em/G | Am | C | F | B | Em",
        lead="@trombone !44 " + _bars(tt, 0, 4) + " !p C3:8 | F3:8 | !44 "
             + _bars(tt, 6, 8),
        harm="@horn !mf " + _bars(_HT, 0, 4) + " @strings_lo !mf "
             + _CALL_C + " A4:2 C5:2 D5:4 | @horn !mf "
             + _bars(_HT, 6, 7)
             + " E5:6~ r:2 |",
        pad="@organ !p B3:8_ | C4:8_ | D4:8_ | E4:4_ F#4:4_ | E4:8_ | F4:8_ | "
            "F#4:8_ | G4:8 |",
        bass="@tuba !44 E2:4_ B1:4_ | F2:4_ C2:4_ | G2:4_ D2:4_ | A2:4_ B2:4_ | "
             "C3:4_ G2:4_ | F2:4_ C3:4_ | B1:4_ F#2:4_ | E2:8 |",
        drum="@timp !mf "
             "E2:2v42 @snare C4:2v34 @timp B2:2v38 @snare C4:2v34 | "
             "F2:2v42 @snare C4:2v34 @timp F2:2v38 @snare C4:2v34 | "
             "G2:2v42 @snare C4:2v34 @timp D2:2v38 @snare C4:2v34 | "
             "A2:2v42 @snare C4:2v34 @timp B2:2v38 @snare C4:1v30 C4:1v36 | "
             "G2:2v42 @snare C4:2v34 @timp G2:2v38 @snare C4:2v34 | "
             "F2:2v42 @snare C4:2v34 @timp F2:2v38 @snare C4:2v34 | "
             "B2:2v42 @snare C4:2v34 @timp F#2:2v38 @snare C4:2v34 | "
             "E2:2v44 @snare C4:2v36 r:2 @snare C4:1v32 C4:1v38 |",
        x1="@cymbal !p r:8 | C4:8v24 | r:8 | r:8 | r:8 | C4:8v24 | r:8 | r:8 |",
        x2="@clarinet !mp r:8 | r:8 | r:8 | r:8 | "
           "r:4 G3:1'v36 C4:1'v36 G3:1'v40 C4:1'v40 | "
           "r:4 C4:1'v36 F4:1'v36 C4:1'v40 F4:1'v40 | "
           "r:4 F#3:1'v38 B3:1'v38 F#3:1'v42 B3:1'v42 | "
           "r:4 B3:1'v40 E4:1'v40 B3:1'v44 E4:1'v44 |")

    # -- B: the climb. The tune is gone; what is left is the call with its
    # leap withheld (three strokes, then air), a tuba pedal that never moves,
    # and the organ walking up a chromatic ladder over it in planed triads:
    # Em F F#o G G#o Am A#o B. The bottom voice is the climb (E F F# G G# A A#
    # B); nothing under it changes, which is what makes it float. Bar by bar
    # the timp, the snare, the trombone and the propeller join. It ends on B
    # major over a tuba that has finally moved -- the dominant -- and the leap
    # is given back on the first bar of the next section.
    t.section('B',
        chords="Em | F/E | F#dim/E | G/E | G#dim/E | Am/E | A#dim/E | B",
        rhy="@organ !p E4:8_ | F4:8_ | F#4:8_ | G4:8_ | G#4:8_ | A4:8_ | "
            "A#4:8_ | B4:8 |",
        pad="@organ !p G4:8_ | A4:8_ | -:8 | B4:8_ | -:8 | C5:8_ | C#5:8_ | "
            "D#5:8 |",
        harm="@organ !p B4:8_ | C5:8_ | -:8 | D5:8_ | -:8 | E5:8_ | -:8 | "
             "F#5:8 |",
        bass="@tuba !mf E2:8 | -:8 | -:8 | -:8 | !f E2:8 | -:8 | -:8 | B1:8 |",
        lead="@trombone r:8 | r:8 | r:8 | r:8 | "
             "E3:2_v36 E3:2_v36 E3:2v36 r:2 | E3:2_v40 E3:2_v40 E3:2v40 r:2 | "
             "E3:2_v44 E3:2_v44 E3:2v44 r:2 | B3:2_v48 B3:2_v48 B3:2v48 r:2 |",
        drum="@timp E2:2v26 E2:2v26 E2:2v26 r:2 | E2:2v28 E2:2v28 E2:2v28 r:2 | "
             "E2:2v30 E2:2v30 E2:2v30 r:2 | E2:2v32 E2:2v32 E2:2v32 r:2 | "
             "E2:2v36 E2:2v36 E2:2v36 @snare C4:1v26 C4:1v30 | "
             "@timp E2:2v38 E2:2v38 E2:2v38 @snare C4:1v30 C4:1v34 | "
             "@timp E2:2v40 E2:2v40 E2:2v40 @snare C4:1v34 C4:1v38 | "
             "@timp B2:2v44 B2:2v44 B2:2v44 @snare C4:1v38 C4:1v44 |",
        x1="@cymbal r:8 | r:8 | r:8 | r:8 | C4:8v20 | r:8 | r:8 | C4:8v30 |",
        x2="@clarinet r:8 | r:8 | r:8 | r:8 | "
           "r:4 E3:1'v36 B3:1'v36 E3:1'v40 B3:1'v40 | "
           "r:4 E3:1'v38 B3:1'v38 E3:1'v42 B3:1'v42 | "
           "r:4 E3:1'v40 B3:1'v40 E3:1'v44 B3:1'v44 | "
           "r:4 B3:1'v42 F#4:1'v42 B3:1'v46 F#4:1'v46 |")

    # -- A prime: everyone. The same eight bars, but the trombone and horn
    # play the phrase the strings answered, so the answer is taken up by the
    # whole orchestra; the strings hold a pedal on D (the seventh, so the F bar
    # is F6 and the G bar has its fifth) through the call and double the horn
    # through the answer;
    # the timp and snare fill every bar; the propeller runs the whole way; the
    # cymbal marks the bombs. The last bar drops the tuba an octave into the
    # first bar of A, where the call begins again.
    t.section('Ap', chords="Em | F | Em/G | Am | C | F | B | Em",
        lead="@trombone !52 " + _bars(tt, 0, 7) + " E4:6~ r:2 |",
        harm="@horn !46 " + _bars(_HT, 0, 7) + " E5:6~ r:2 |",
        rhy="@strings_lo !36 D4:8 | -:8 | -:8 | -:8 | " + _CALL_C +
            " A4:2 C5:2 D5:4 | D4:8 | E4:6~ r:2 |",
        pad="@organ !mp B3:8_ | C4:8_ | D4:8_ | E4:4_ F#4:4_ | E4:8_ | F4:8_ | "
            "F#4:8_ | G4:8 |",
        bass="@tuba !52 E2:4_ B1:4_ | F2:4_ C2:4_ | G2:4_ D2:4_ | A2:4_ B2:4_ | "
             "C3:4_ G2:4_ | F2:4_ C3:4_ | B1:4_ F#2:4_ | E2:4 E1:4 |",
        drum="@timp !mf "
             "E2:2v50 @snare C4:2v40 @timp B2:2v46 @snare C4:1v36 C4:1v44 | "
             "F2:2v50 @snare C4:2v40 @timp F2:2v46 @snare C4:1v36 C4:1v44 | "
             "G2:2v50 @snare C4:2v40 @timp D2:2v46 @snare C4:1v36 C4:1v44 | "
             "A2:2v50 @snare C4:2v40 @timp B2:2v46 @snare C4:1v36 C4:1v44 | "
             "G2:2v50 @snare C4:2v40 @timp G2:2v46 @snare C4:1v36 C4:1v44 | "
             "F2:2v50 @snare C4:2v40 @timp F2:2v46 @snare C4:1v36 C4:1v44 | "
             "B2:2v50 @snare C4:2v40 @timp F#2:2v46 @snare C4:1v36 C4:1v44 | "
             "E2:2v52 @snare C4:2v42 @timp E2:2v48 @snare C4:1v38 C4:1v46 |",
        x1="@cymbal !p C4:8v18 | C4:8v30 | r:8 | r:8 | C4:8v18 | C4:8v30 | "
           "r:8 | C4:8v30 |",
        x2="@clarinet !mp "
           "r:4 B3:1'v38 E4:1'v38 B3:1'v42 E4:1'v42 | "
           "r:4 C4:1'v38 F4:1'v38 C4:1'v42 F4:1'v42 | "
           "r:4 D4:1'v38 G4:1'v38 D4:1'v42 G4:1'v42 | "
           "r:4 F#4:1'v38 B4:1'v38 F#4:1'v42 B4:1'v42 | "
           "r:4 G3:1'v40 C4:1'v40 G3:1'v44 C4:1'v44 | "
           "r:4 C4:1'v40 F4:1'v40 C4:1'v44 F4:1'v44 | "
           "r:4 F#3:1'v42 B3:1'v42 F#3:1'v46 B3:1'v46 | "
           "r:4 B3:1'v42 E4:1'v42 B3:1'v46 E4:1'v46 |")

    t.play('intro', 'A', 'B', 'Ap', loop=1)
    return t
