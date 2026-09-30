#!/usr/bin/env python3
"""The score, part three: the fights.

Two themes, and they are the ones played most, so they are written to be lived
in rather than merely survived: they drive, but they breathe, and the tune is
never in the trumpet. Brass is the floor here (trombone, tuba, horn); the tune
lives in clarinet, oboe, horn and strings.

  BATTLE   an ordinary fight. The road, gone minor and quick: the pilgrim's
           call is now a bugle rally, and it is the thing the whole theme is
           built from.
  BOSS     a guardian who is not evil, only wrong. The call again, but falling:
           the same three strokes, and the leap goes down. The lullaby turns up
           in the strings in the middle, because the boss is one of the sleepers.

A note on the numbers, because they look odd. Every sustained instrument is
calibrated so that volume 40 is the same loudness on all of them, but the
drums are not: a kick or a snare at 40 is five or six dB under a clarinet at
40, because it is a transient and the meter averages it with the silence around
it. So the drums are written at 50-60 where the winds are at 40-46, and that
is a balance, not a shout.
"""
import re

from score import Theme
from themes_road import xp, stretch, ROAD, ROAD_CHORDS, CALL, LULLABY_Q, LULLABY_A


# ---- BATTLE -----------------------------------------------------------------

def battle():
    """D minor, 152. Written on the eighth grid: a fight at this speed needs
    nothing shorter than an eighth, and the pattern format charges two bytes a
    row, so the sixteenth grid would have spent a third of the budget on rows
    that hold nothing.

    The tune is the road's call (three equal notes, then the leap) sped up and
    turned minor. It comes back four times a section, each time on a new chord
    and with a new leap: from A up to D on Dm, from D up to G on Gm (higher --
    the reach), from G up to C on C (the low answer). Between the calls, a
    falling answer with a dotted rhythm (3-1-2-2), the same shape each time so
    the ear learns it.

    The floor is bass and kick; the syncopation is trombone stabs on the "and"
    of two and on four, so the bar leans forward. Nothing above the clarinet is
    brass."""
    t = Theme('BATTLE', bpm=152, beats=4, grid=2, key='D', voices=dict(
        lead='clarinet', bass='bass', harm='horn', pad='strings_lo',
        rhy='trombone', drum='kick', x1='hat', x2='flute'))

    # ---- the tune, in pieces, so the sections can say what changes
    call_d = "A4:1 A4:1 A4:1 D5:3 F5:2"      # A A A, up a fourth to D, on to F
    fall_b = "G5:3 F5:1 D5:2 Bb4:1 r:1"      # the answer: 3-1-2-2, falling, and a breath
    call_g = "D5:1 D5:1 D5:1 G5:3 A5:2"      # the call a step up: the reach
    hold_a = "-:3 G5:1 F5:2 E5:1 r:1"        # the peak, held over the barline; a breath
    call_c = "G4:1 G4:1 G4:1 C5:3 E5:2"      # the low call on C, and home
    home   = "D5:6~ r:2"
    bars = [call_d, fall_b, call_g, hold_a, call_d, fall_b, call_c, home]
    first, second = " | ".join(bars[:4]) + " |", " | ".join(bars[4:]) + " |"

    kick, snare = "@kick C4:2", "@snare C4:2"
    groove = "%s %s %s %s |" % (kick, snare, kick, snare)
    groove_fill = "%s %s %s @snare C4:1 C4:1 |" % (kick, snare, kick)
    groove_push = "@kick C4:2 @snare C4:1 @kick C4:1 @kick C4:2 @snare C4:2 |"
    call_timp = "@kick C4:2 @snare C4:2 @timp !52 D2:1 D2:1 D2:1 G2:1 |"
    drums = " ".join([groove, groove_push, groove, groove_fill,
                      groove, groove_push, groove, call_timp])

    # root, root, fifth, root -- and on the way to each new chord an eighth
    # pick-up a semitone under its root, so the line leans into every change
    bass_line = ("D2:2 D2:2 A1:2 D2:2 | Bb1:2 Bb1:2 F2:2 Bb1:1 F#1:1 | "
                 "G1:2 G1:2 D2:2 G1:1 G#1:1 | A1:2 A1:2 E2:2 C#2:2 | "
                 "D2:2 D2:2 A1:2 D2:2 | Bb1:2 Bb1:2 F2:2 Bb1:1 B1:1 | "
                 "C2:2 C2:2 G1:2 C2:1 C#2:1 | D2:4 r:4 |")
    # the trombone stabs: the "and" of two, and four
    stabs = ("r:3 D3:2' r:1 A3:2' | r:3 Bb2:2' r:1 F3:2' | r:3 G2:2' r:1 D3:2' | "
             "r:3 A2:2' r:1 E3:2' | r:3 D3:2' r:1 A3:2' | r:3 Bb2:2' r:1 F3:2' | "
             "r:3 C3:2' r:1 G3:2' | ")

    # -- the rally: timpani strike the call slowly, then a horn answers it in
    # eighths on the dominant, and a snare roll pushes into the tune. The horn's
    # D over the A chord is a suspension; the clarinet's D over Dm is home.
    t.section('intro', chords="Dm | A",
        drum="@timp !46 " + xp(stretch(CALL, 0.5), -31) + " !40 A2:2 r:2 @snare "
             "C4:1v30 C4:1v38 C4:1v46 C4:1v56 |",
        bass="!mp D2:8 | A1:8 |",
        pad="!pp A3:8 | !p C#4:8 |",
        harm="r:8 | !mf A3:1 A3:1 A3:1 D4:3 r:2 |")

    # -- A: the tune, twice four bars. Dm Bb Gm A is a bass falling in thirds
    # and then stepping up to the dominant; the second half swaps the last two
    # for Bb-C-Dm, the bugle cadence. The horn holds the middle of the chord
    # and moves by step (F F D C# | D D E F); the strings come in for the second
    # half, when the tune needs something to lean on.
    t.section('A', chords="Dm | Bb | Gm | A | Dm | Bb | C | Dm",
        lead="!48 " + first + " " + second,
        harm="!34 F4:8 | -:8 | D4:8 | C#4:8 | D4:8 | -:8 | E4:8 | F4:8 |",
        pad="r:8 | r:8 | r:8 | r:8 | !28 A3:8 | Bb3:8 | C4:8 | D4:8 |",
        rhy="!48 " + stabs + "r:3 D3:2' r:3 |",
        bass="!50 " + bass_line,
        drum="!60 " + drums)

    # -- B: the road loses its footing. Horn and clarinet trade the reach and
    # the fall (they are ROAD's second and third bars, in the minor: an arpeggio
    # that reaches, and the 3-1-2-2 answer; the horn asks, the clarinet
    # answers, and each is silent while the other speaks, which is also what
    # keeps this half cheap). Then the strings run over a chromatic climb to
    # the dominant: the horn creeps up a semitone a bar (Bb B C C#) against the
    # D the strings hold, and in the last bar the D steps up to E so that the
    # A7 opens instead of grinding.
    t.section('B', chords="Bb | F | Gm | A | Gm | G#dim7 | Dm/A | A7",
        harm="!42 D4:2 F4:2 Bb4:4 | r:8 | D4:2 G4:2 D5:4 | r:8 | "
             "!34 Bb3:8 | B3:8 | C4:8 | C#4:8 |",
        lead="r:8 | !42 A4:3 G4:1 F4:2 C4:2 | r:8 | C#5:3 A4:1 G4:2 E4:2 | "
             "@strings !34 G4:1 Bb4:1 D5:1 G5:1 Bb4:1 D5:1 G5:1 Bb5:1 | "
             "!36 G#4:1 B4:1 D5:1 F5:1 B4:1 D5:1 F5:1 G#5:1 | "
             "!40 A4:1 D5:1 F5:1 A5:1 F5:1 D5:1 F5:1 A5:1 | "
             "!44 A4:1 C#5:1 E5:1 G5:1 A5:2 E5:2 |",
        pad="!26 D4:8 | C4:8 | Bb3:8 | A3:8 | !28 D4:8 | !30 D4:8 | "
            "!34 D4:8 | !38 E4:8 |",
        bass="!46 Bb1:4 F2:4 | F2:4 C2:4 | G1:4 D2:4 | A1:4 E2:4 | "
             "G1:2 D2:2 G1:2 D2:2 | G#1:2 D2:2 G#1:2 D2:2 | "
             "A1:2 D2:2 A1:2 F2:2 | A1:2 A2:2 A1:2 A2:2 |",
        drum="!54 @kick C4:4 @snare C4:4 | @kick C4:4 @snare C4:4 | "
             "@kick C4:4 @snare C4:4 | @kick C4:4 @snare C4:2 C4:2 | "
             "@kick C4:2 @snare C4:2 @kick C4:2 @snare C4:2 | "
             "@kick C4:2 @snare C4:2 @kick C4:2 @snare C4:2 | "
             "@kick C4:2 @snare C4:2 @kick C4:2 @snare C4:2 | "
             "@timp !40 A2:2 r:2 @snare C4:1v30 C4:1v38 C4:1v46 C4:1v56 |",
        x1="r:8 | r:8 | r:8 | r:8 | @hat !44 r:1 C4:1 r:1 C4:1 r:1 C4:1 r:1 C4:1 | "
           "!50 r:1 C4:1 r:1 C4:1 r:1 C4:1 r:1 C4:1 | "
           "!56 r:1 C4:1 r:1 C4:1 r:1 C4:1 r:1 C4:1 | r:8 |")

    # -- A again, and bigger. First half: the horn doubles the tune an octave
    # down, and the strings answer it in contrary motion (up while the tune
    # falls, down while it rises), the second line the theme has been missing.
    # Second half: oboe takes the tune, brighter; the hat ticks on the off-
    # beats; the last bar is the section's own, and ends the way A ended, on the
    # timpani's call, so the loop lands on the clarinet's call.
    counter = ("F4:4 D4:4 | D4:4 F4:4 | D4:4 Bb3:4 | E4:4 C#4:4 | "
               "F4:4 D4:4 | D4:4 F4:4 | E4:4 C4:4 | F4:8 |")
    off = "@hat !60 r:1 C4:1 r:1 C4:1 r:1 C4:1 r:1 C4:1 |"
    t.section('A2', chords="Dm | Bb | Gm | A | Dm | Bb | C | Dm",
        lead="!52 " + first + " @oboe !50 " + second,
        harm="!42 " + xp(first, -12) + " !36 A3:8 | Bb3:8 | G3:8 | A3:8 |",
        pad="!32 " + counter,
        rhy="!50 " + stabs + "D3:6 r:2 |",
        bass="!52 " + bass_line,
        drum="!62 " + drums,
        x1="r:8 | r:8 | r:8 | r:8 | " + " ".join([off] * 3) + " r:8 |")

    t.play('intro', 'A', 'B', 'A2', loop=1)
    return t


# ---- BOSS -------------------------------------------------------------------

def _short(text):
    """A passage on the eight-row bar, on the seven-row one: every bar loses
    one row, taken from its last note. Applied to the lullaby it is the same
    tune with the last beat of every bar swallowed."""
    def bar(b):
        notes = b.split()
        m = re.match(r"^(.*:)(\d+)$", notes[-1])
        notes[-1] = "%s%d" % (m.group(1), int(m.group(2)) - 1)
        return " ".join(notes)
    return " | ".join(bar(b) for b in text.strip().rstrip('|').split("|")) + " |"


def boss():
    """B minor, 130, seven eighths to the bar (2+2+3). A guardian who is not
    evil, only wrong, and whose whole gait is off by one: he has been told what
    to do and is doing it, heavily, with a limp.

    THE CALL, falling. The road's call is three strokes and a leap up; here it
    is three strokes on the dominant (F#), a breath -- the seventh eighth of the
    bar is a rest, the row the bar is short of -- and a fall to C#. The A section
    is built on the Andalusian descent B-A-G-F# in the tuba, the lament bass,
    with the organ a tenth above it (D C# B A#) and, in the second phrase, the
    trombone a fifth above the bass, so the weight is real and the harmony is
    grief. The tune peaks on G,
    the flat sixth, and the second time it holds that G into the F# chord --
    a ninth, the ache -- before it sighs down onto F#.

    C is the order he was given, three strokes on a fifth every bar, in trombone
    and timpani, while the strings sing over it what he cannot say. It ends on
    A7, which is the one chord that wants D, and D is where the lullaby is.

    The lullaby: the boss is one of the sleepers. D major is B minor's relative,
    so the floor opens onto it, and the tune is sung in the strings, one beat
    short in every bar (the seventh row is swallowed: see _short); the answer
    goes hollow, to flute. Nobody is being unkind; that is the whole difficulty.
    Then the whole weight comes back."""
    t = Theme('BOSS', bpm=130, beats=3.5, grid=2, key='B', voices=dict(
        lead='cello', bass='tuba', harm='horn', pad='organ',
        rhy='trombone', drum='timp', x1='hat', x2='flute'))

    # ---- the tune
    call_in = "F#4:2 F#4:2 F#4:2 r:1"        # TUNG. TUNG. TUNG. (breath)
    fall_a = "C#4:3 E4:2 A4:2"               # ...and down; up the A chord
    reach_g = "B4:3 D5:4 <40,54>"            # up the G chord to D5, swelling
    fall_f = "C#5:3 <54,46> A#4:2 F#4:1 r:1" # down the F# chord, and a breath before the phrase turns
    reach_g2 = "B4:3 D5:2 G5:2"              # the second time it reaches the flat sixth
    sigh = "-:2 F#5:3 C#5:2"                 # G held into the F# chord, then onto F#, then down the call's fourth
    ph1 = " | ".join([call_in, fall_a, reach_g, fall_f]) + " |"
    ph2 = " | ".join([call_in, fall_a, reach_g2, sigh]) + " |"
    lam = "Bm | A | G | F#"

    # the groove: timp on the two long beats, a snare tap between and a
    # pick-up before the bar -- 2+2+2+1, so the bar always trips over itself
    def drums(notes, snare=36):
        a, b = notes
        return ("@timp %s:2 @snare C4:2v%d @timp %s:2 @snare C4:1v%d |"
                % (a, snare, b, snare - 6))

    # -- the guardian wakes: a pedal, a heartbeat, the call in the horn, a roll
    t.section('intro', chords="Bm | F#",
        bass="!mp B1:7 | F#1:7 |",
        harm="r:7 | @horn !32 F#3:2' F#3:2' F#3:2' r:1 |",
        pad="!pp D3:7 <10,26> | A#2:7 <26,42> |",
        drum="@timp !40 B2:4 F#2:3 | !36 r:3 F#2:1v30 F#2:1v38 F#2:1v46 F#2:1v54 |")

    # -- A: weight. Phrase one is the cello alone over the tolling; phrase two
    # is the oboe, with the horn an octave under it and the trombone joining.
    # Bar four ends on a three-note timpani roll that turns the phrase over.
    turn = "@timp F#2:2 @snare C4:2v36 @timp F#2:1v40 F#2:1v46 F#2:1v52 |"
    t.section('A', chords=lam + " | " + lam,
        lead="!44 " + ph1 + " @oboe !46 " + ph2,
        harm="r:7 | r:7 | r:7 | r:7 | @horn !40 " + xp(ph2, -12),
        pad="!30 D3:7 | C#3:7 | B2:7 | A#2:7 | D3:7 | C#3:7 | B2:7 | A#2:7 |",
        rhy="r:7 | r:7 | r:7 | r:7 | !36 F#3:7 | E3:7 | D3:7 | C#3:7 |",
        bass="!44 B1:4 F#2:3 | A1:4 E2:3 | G1:4 D2:3 | F#1:4 C#2:3 | "
             "B1:4 F#2:3 | A1:4 E2:3 | G1:4 D2:3 | F#1:4 C#2:3 |",
        drum="!46 " + " ".join([drums(('B2', 'F#2')), drums(('A2', 'E2')),
                                drums(('G2', 'D2')), turn,
                                drums(('B2', 'F#2'), 42), drums(('A2', 'E2'), 42),
                                drums(('G2', 'D2'), 42), "@timp F#2:3 r:4 |"]))

    # -- C: the order. He counts it out (three strokes on a fifth, every bar)
    # and the strings sing over the count. The line climbs by step (B A B D | E
    # D C# A#), the A# a leading tone that the next bar's B resolves; then it
    # reaches up a fifth, touches the flat sixth again, and falls a fourth like
    # the call, to the third of A7. The organ and tuba keep their tenths (D B G
    # A# over B G E F#), so the harmony is a sequence of falling thirds.
    p1 = "B4:5 A4:2 | B4:3 D5:4 | E5:5 D5:2 | C#5:3 A#4:4 |"
    p2 = "B4:3 F#5:4 | G5:5 F#5:2 | E5:3 B4:4 | C#5:7~ <46,28> |"
    count = " | ".join("%s:2' %s:2' %s:2' r:1" % ((n,) * 3)
                       for n in ("F#3", "D3", "B2", "C#3", "F#3", "D3", "B2", "E3")) + " |"
    t.section('C', chords="Bm | G | Em | F# | Bm | G | Em | A7",
        lead="@strings !44 " + p1 + " !50 " + p2,
        harm="r:7 | r:7 | r:7 | r:7 | @horn !40 " + xp(p2, -12),
        pad="!30 D3:7 | B2:7 | G2:7 | A#2:7 | D3:7 | B2:7 | G2:7 | C#3:7 |",
        rhy="!44 " + count,
        bass="!44 B1:4 F#2:3 | G1:4 D2:3 | E2:4 B1:3 | F#1:4 C#2:3 | "
             "B1:4 F#2:3 | G1:4 D2:3 | E2:4 B1:3 | A1:4 E2:3 |",
        drum="!46 " + " ".join([drums(('B2', 'F#2')), drums(('G2', 'D2')),
                                drums(('E2', 'B2')), drums(('F#2', 'F#2')),
                                drums(('B2', 'F#2'), 42), drums(('G2', 'D2'), 42),
                                drums(('E2', 'B2'), 42), "@timp !34 A2:3 r:4 |"]))

    # -- B: the lullaby, in D major, in the strings. The tuba and the horn hold
    # the chords under it; the cello rises a third a bar against the tune's
    # falling; the timpani keep the guardian's pulse, quietly, because he is
    # still at his post. The answer goes to the flute, and hollow. Bar eight
    # swells back into the weight.
    lull_q = _short(LULLABY_Q)
    lull_a = _short(LULLABY_A).replace("D5:7 |", "D5:7~ <36,50> |")
    t.section('B', chords="D | Bm | G | A | D | G | A | D",
        lead="@strings !32 " + lull_q + " @flute !40 " + lull_a,
        harm="@horn !26 A3:7 | F#3:7 | D4:7 | E4:7 | A3:7 | D4:7 | E4:7 | F#4:7 |",
        pad="@cello !30 F#3:4 A3:3 | B3:4 D4:3 | B3:4 D4:3 | C#4:4 E4:3 | "
            "F#3:4 A3:3 | B3:4 D4:3 | C#4:4 E4:3 | D4:7 |",
        bass="!38 D2:7 | B1:7 | G1:7 | A1:7 | D2:7 | G1:7 | A1:7 | D2:7 |",
        drum="@timp !24 D2:7 | D2:7 | D2:7 | D2:7 | D2:7 | D2:7 | D2:7 | "
             "r:1 D2:1v26 D2:1v32 D2:1v38 D2:1v44 D2:1v50 D2:1v56 |")

    # -- A again, bigger. Phrase one: strings and horn, the trombone and organ
    # under them. Phrase two: the oboe an octave above the strings, then the
    # sigh held for the whole bar over a roll, and the loop drops back to the
    # cello alone.
    ph2b = " | ".join([xp(call_in, 12), xp(fall_a, 12), "B5:3 A5:2 G5:2", "-:2 F#5:5"]) + " |"
    t.section('A2', chords=lam + " | " + lam,
        lead="@strings !50 " + ph1 + " @oboe !52 " + ph2b,
        harm="@horn !44 " + ph1 + " @strings !46 " + xp(ph2b, -12),
        pad="!34 D3:7 | C#3:7 | B2:7 | A#2:7 | D3:7 | C#3:7 | B2:7 | A#2:7 |",
        rhy="!42 F#3:7 | E3:7 | D3:7 | C#3:7 | F#3:7 | E3:7 | D3:7 | C#3:7 |",
        bass="!48 B1:4 F#2:3 | A1:4 E2:3 | G1:4 D2:3 | F#1:4 C#2:3 | "
             "B1:4 F#2:3 | A1:4 E2:3 | G1:4 D2:3 | F#1:7 |",
        drum="!52 " + " ".join([drums(('B2', 'F#2'), 44), drums(('A2', 'E2'), 44),
                                drums(('G2', 'D2'), 44),
                                "@timp F#2:2 @snare C4:2v44 @timp F#2:1v46 F#2:1v52 F#2:1v58 |",
                                drums(('B2', 'F#2'), 50), drums(('A2', 'E2'), 50),
                                drums(('G2', 'D2'), 50),
                                "@timp F#2:1v40 F#2:1v44 F#2:1v48 F#2:1v52 "
                                "F#2:1v56 F#2:1v60 F#2:1v64 |"]))

    t.play('intro', 'A', 'C', 'B', 'A2', loop=1)
    return t
