#!/usr/bin/env python3
"""The score, part two: the two warm places.

  TOWN   Kampung Sahur, the village that will not wake. Everybody is asleep,
         and it is the kindest thing about the place: the music is a lullaby
         sung over a gamelan that has slowed down to the speed of breathing.
  SHORE  La Riva, where the Sleep runs into water and stops. A barcarolle:
         the sea rocks in six, a harp is the wave, and the tune is sung in
         thirds by two winds across a lonely, sunlit bay.

Both take their tunes from the shared motifs (THE CALL, THE LULLABY) so they
read as places in the same world as the road.
"""
from score import Theme
from themes_road import (xp, stretch, LULLABY_Q, LULLABY_A, LULLABY_CHORDS,
                         LULLABY_ANSWER_CHORDS, CALL)


def _bars(text):
    return [b.strip() for b in text.strip().strip('|').split('|')]


def shaped(text, dyns):
    """A passage written bar by bar, each bar opening on its own dynamic.
    The tune stays the shared motif; this only lets it breathe -- a phrase
    that is the same loudness from first note to last is a metronome."""
    return ' '.join('!%d %s |' % (d, b) for b, d in zip(_bars(text), dyns))


def town():
    """Kampung Sahur. D major, 68, four in a bar on the eighth grid.

    Form: intro 2 | A 8 | B 8 | A' 8. The village is asleep, so nothing here
    ever pushes: the tune is the lullaby, the bass is a pedal D that only
    sighs to C# and back, and the gamelan is a music box turning over.

    Gamelan colotomy is the structure. A gong sounds once, when the canon
    returns; the kenong (a tubebell) marks every fourth bar. The mallet
    figure lives on `rhy` and `x1`; every note of it that matters is on `rhy`,
    so when a sound effect takes `x1` the figure thins but does not break."""
    t = Theme('TOWN', bpm=68, beats=4, grid=2, key='D', voices=dict(
        lead='flute', bass='bassoon', harm='strings_lo', pad='strings_lo',
        rhy='marimba', drum='tubebell', x1='marimba'))

    # -- intro: the call, as a memory. Somebody far away is beating the
    # kentongan -- TUNG. TUNG. TUNG. -- and it is the dominant, so the lift on
    # the fourth stroke is the village's own key arriving. The strings sing
    # the lullaby's sighs (F# E D) in the middle voice, unheard, beneath it.
    t.section('intro', chords="D | A",
        rhy="@kentong r:2 A3:2v12 r:2 A3:2v14 | r:2 A3:2v16 r:2 D4:2v26 |",
        pad="!pp A3:8 <8,20> | -:8 |",
        harm="!pp F#4:8 | E4:8 |",
        bass="r:8 | !p A2:8 |")

    # -- A: the lullaby, sung by the flute over the sleeping strings.
    # The four-bar question, then the answer; the last note is a long
    # exhale that fades before the next section. The bass is one held D
    # (the tonic pedal) that only leans down to C# on the two dominants, so
    # the harmony moves above it without the floor ever getting up. The
    # strings hold common tones and move by step (A B C# A ... / D E D E F#),
    # so the chords change without anybody in the orchestra getting up.
    lq = LULLABY_Q.replace("C#5:4 |", "C#5:3 r:1 |")
    la = LULLABY_A.replace("D5:8 |", "D5:7~ <44,22> r:1 |")
    t.section('A', chords="D | Bm/D | G/D | A/C# | D | G/D | A/C# | D",
        lead="@flute " + shaped(lq, (38, 36, 34, 42)) + " " +
             shaped(la, (44, 42, 48, 42)),
        bass="!42 D2:8 | -:8 | -:8 | C#2:8 | D2:8 | -:8 | C#2:8 | D2:8 |",
        harm="!26 D4:8 | -:8 | -:8 | E4:8 | D4:8 | -:8 | E4:8 | F#4:8 |",
        pad="!pp A3:8 | B3:8 | -:8 | C#4:8 | A3:8 | B3:8 | C#4:8 | A3:8 |",
        # the music box: root, fifth, third, octave -- one note every quarter,
        # `rhy` on the beat and `x1` between
        rhy="!30 D4:4 F#4:4 | B3:4 D4:4 | G3:4 B3:4 | A3:4 C#4:4 | "
            "D4:4 F#4:4 | G3:4 B3:4 | A3:4 C#4:4 | D4:4 F#4:4 |",
        x1="!20 r:2 A4:2 r:2 D5:2 | r:2 F#4:2 r:2 B4:2 | r:2 D4:2 r:2 G4:2 | "
           "r:2 E4:2 r:2 A4:2 | r:2 A4:2 r:2 D5:2 | r:2 D4:2 r:2 G4:2 | "
           "r:2 E4:2 r:2 A4:2 | r:2 A4:2 r:2 D5:2 |",
        drum="@tubebell !30 A4:8 | r:8 | r:8 | r:8 | D5:8 | r:8 | r:8 | r:8 |")

    # -- B: the gamelan comes forward and the winds answer it. The mallets
    # beat the call (three equal notes and a lift of a fourth) and the
    # clarinet, then the flute, then the clarinet again reply with the
    # lullaby's own sigh -- but rising, as if the sleeper were turning over.
    # x1 doubles the call an eighth late, an octave up (and, when the figure
    # goes up, an octave down): the two hands of a gender. The snores are the
    # bassoon breathing in (rising, swelling) and out (falling, fading).
    # Bar 8 is the cat with five legs, climbing away up the pentatonic.
    # It builds from a whisper: bars 1-4 are distant, 5-7 are the loudest the
    # village gets, and bar 8 lets go.
    t.section('B', chords="Bm/D | G/D | D/F# | A | Bm/D | G/D | Em | A/C#",
        lead="@clarinet !mp r:8 | r:8 | "
             "!38 D5:3 E5:1 F#5:4 | !36 E5:3 D5:1 C#5:4 | "
             "@flute !26 F#5:8~ | G5:8~ | "
             "@clarinet !50 E5:3 F#5:1 G5:4 | !38 F#5:3 E5:1 C#5:4 |",
        bass="!38 D2:8 | -:8 | F#2:4 <14,38> E2:4 <36,8> | A2:8 | "
             "!46 D2:8 | -:8 | E2:4 <16,48> D2:4 <46,8> | !38 C#2:8 |",
        harm="!24 D4:8 | -:8 | -:8 | E4:8 | !32 D4:8 | -:8 | E4:8 | !24 -:8 |",
        pad="!18 B3:8 | -:8 | A3:8 | -:8 | !26 B3:8 | -:8 | -:8 | !18 A3:8 |",
        rhy="!32 F#4:2 F#4:2 F#4:2 B4:2 | D4:2 D4:2 D4:2 G4:2 | "
            "!26 D4:4 F#4:4 | A3:4 C#4:4 | "
            "!46 B4:2 B4:2 B4:2 E5:2 | D5:2 D5:2 D5:2 G5:2 | "
            "!30 E4:4 G4:4 | !36 A4:1 B4:1 D5:1 E5:1 F#5:1 r:3 |",
        x1="!20 r:1 F#5:2 F#5:2 F#5:2 B5:1 | r:1 D5:2 D5:2 D5:2 G5:1 | "
           "r:2 A4:2 r:2 D5:2 | r:2 E4:2 r:2 A4:2 | "
           "!30 r:1 B3:2 B3:2 B3:2 E4:1 | r:1 D4:2 D4:2 D4:2 G4:1 | "
           "!20 r:2 B4:2 r:2 E5:2 | r:8 |",
        drum="@tubebell !28 F#5:8 | r:8 | r:8 | r:8 | !34 B4:8 | r:8 | r:8 | r:8 |")

    # -- A': the lullaby again, and this time it is a canon. The horn sings
    # it an octave down; the flute follows a bar behind, an octave up, so the
    # two run in tenths. The gong marks the return. Where the canon would
    # grind against the chord the follower bends (the call's own leap, A up
    # to D, replaces the question's C#; E5 replaces D5 over the A chord), and
    # the last bar drops the follower's final statement so both voices arrive
    # on D together. Unique: it carries the jump back to A. The strings are
    # one voice here (the horn has the other), and the last bar fades so the
    # loop begins from nearly nothing.
    t.section('Ap', chords="D | Bm/D | G/D | A/C# | D | G | A | D",
        lead="@flute !26 D5:8 <20,36> | "
             "!38 F#5:3 E5:1 D5:4 | !38 D5:3 C#5:1 B4:4 | !36 B4:3 A4:1 G4:4 | "
             "!40 A4:4 D5:4 | !44 F#5:3 E5:1 D5:4 | !44 B4:3 C#5:1 E5:4 | "
             "!40 E5:3 D5:5 <40,16> |",
        harm="@horn !32 F#4:3 E4:1 D4:4 | !32 D4:3 C#4:1 B3:4 | "
             "!30 B3:3 A3:1 G3:4 | !32 A3:4 C#4:4 | "
             "!38 F#4:3 E4:1 D4:4 | !38 B3:3 C#4:1 D4:4 | "
             "!40 E4:3 D4:1 C#4:4 | !36 D4:8~ <36,14> |",
        bass="!42 D2:8 | -:8 | -:8 | C#2:8 | D2:8 | G2:8 | A2:4 E2:4 | D2:8 |",
        pad="!20 A3:8 | B3:8 | -:8 | C#4:8 | A3:8 | B3:8 | C#4:8 | D4:8 |",
        rhy="!28 D4:4 F#4:4 | B3:4 D4:4 | G3:4 B3:4 | A3:4 C#4:4 | "
            "D4:4 F#4:4 | G3:4 B3:4 | A3:4 C#4:4 | D4:4 F#4:4 |",
        x1="!18 r:2 A4:2 r:2 D5:2 | r:2 F#4:2 r:2 B4:2 | r:2 D4:2 r:2 G4:2 | "
           "r:2 E4:2 r:2 A4:2 | r:2 A4:2 r:2 D5:2 | r:2 D4:2 r:2 G4:2 | "
           "r:2 E4:2 r:2 A4:2 | r:2 A4:2 r:2 D5:2 |",
        drum="@gong !36 C4:8 | r:8 | r:8 | r:8 | @tubebell !30 D5:8 | r:8 | r:8 | r:8 |")

    t.play('intro', 'A', 'B', 'Ap', loop=1)
    return t


# ---- SHORE ------------------------------------------------------------------

def _wave(*chords):
    """One bar of harp per chord: root, fifth, third, octave, then back down --
    six eighths that rise and fall like a swell under the boat. `chords` are
    (root, fifth, third, top) spelled out so each bar's line is its own choice
    of octave; the second half of the bar mirrors the first. The lean is
    written in by hand (root strongest, the crest second, the ebb weakest)
    because the score's automatic metric shaping assumes a duple beat and this
    is a bar of two dotted quarters."""
    return ' '.join("%sv+3 %sv-1 %sv-2 %sv+2 %sv-2 %sv-3 |" % (
        r, f, t, o, t, f) for r, f, t, o in chords)


def shore():
    """La Riva. G major, 6/8 as a barcarolle: six rows a bar, each an eighth,
    two dotted-quarter pulses to the bar. bpm counts the quarter, so the
    pulse is about 61.

    Form: intro 2 | A 8 | B 8 | A' 8. The sea does the accompanying: the harp
    is the swell, every bar one wave. The tune is a yearning leap up a sixth
    and a stepwise fall back, told in thirds by flute over oboe. B goes to the
    relative minor and the tide comes in -- long notes rising a step a bar,
    strings swelling, then the crest and the drawing back. A' returns with the
    cello singing the tune under the flute, one bar of the sun going behind a
    cloud (C minor), and a small run that is Tralalero doing forty knots."""
    t = Theme('SHORE', bpm=92, beats=3, grid=2, key='G', humanize=0, voices=dict(
        lead='flute', harm='oboe', bass='cello', pad='strings_lo',
        rhy='harp', drum='timp', x1='kentong'))

    G = ("G2", "D3", "B3", "G4")
    DF = ("F#2", "D3", "A3", "D4")
    EM = ("E2", "B2", "G3", "E4")
    D = ("D2", "A2", "F#3", "D4")
    C = ("C2", "G2", "E3", "C4")
    D7 = ("D2", "A2", "F#3", "C4")

    # -- intro: the sea and, very far off, the drum. Three even strokes (the
    # call, in the tonic key: 5 5 5, then up a fourth) cut across the six-eight
    # in threes against twos, and are the only thing here that is not rocking.
    t.section('intro', chords="D7 | G",
        rhy="L1 !pp " + _wave(D7) + " !p " + _wave(G),
        x1="@kentong !pp D3:2 D3:2 D3:2 | G3:2 r:4 |",
        pad="!pp A3:6 <8,14> | B3:6 <14,20> |")

    # -- A: flute over oboe in thirds; the cello answers in contrary motion
    # while the tune holds. The bass (the harp's low note) walks down G F# E D.
    t.section('A', chords="G | D/F# | Em | D | G | C | D7 | G",
        lead="@flute " + shaped(
            "G4:3 E5:3 | D5:1 C5:1 B4:1 A4:3 | B4:3 G5:3 | F#5:1 E5:1 D5:1 C5:2 r:1 | "
            "G4:3 E5:3 | E5:1 D5:1 C5:1 G4:3 | A4:3 F#5:3 | E5:1 D5:1 B4:1 G4:2 r:1 |",
            (40, 38, 44, 40, 42, 40, 46, 38)),
        harm="!30 E4:3 G4:3 | B4:1 A4:1 G4:1 F#4:3 | G4:3 E5:3 | "
             "D5:1 C5:1 B4:1 A4:2 r:1 | E4:3 G4:3 | C5:1 B4:1 A4:1 E4:3 | "
             "F#4:3 D5:3 | C5:1 B4:1 G4:1 E4:2 r:1 |",
        bass="!32 G3:3 D3:3 | F#3:3 A3:1 B3:1 C4:1 | E3:3 G3:3 | D3:3 F#3:1 E3:1 D3:1 | "
             "G3:3 D3:3 | C3:3 E3:1 D3:1 C3:1 | D3:3 A3:3 | G3:5 r:1 |",
        pad="!pp B3:6 | A3:6 | G3:6 | A3:6 | !p B3:6 | E4:6 | F#4:6 | D4:6 |",
        rhy="L1 !p " + _wave(G, DF, EM, D, G, C, D7, G),
        x1="@kentong !pp r:6 | r:6 | r:6 | r:6 | r:6 | r:6 | "
           "D3:2 D3:2 D3:2 | G3:2 r:4 |")

    # -- B: E minor and the tide. Bars 1-4 rise a step at a time (B C E D#),
    # oboe a third under; the cello sinks against them; the strings swell and
    # the timpani enters on the leading-tone chord. Bars 5-6 are the crest
    # (everyone up, the harp climbing instead of rocking); 7-8 draw back and
    # the last bar is the dominant, ready for A'. Bar 4's little trill on the
    # leading tone is Tralalero warming up.
    t.section('B', chords="Em | C | Am7 | B7 | Em | C | Am7 | D7",
        lead="@flute !pp B4:6~ | C5:6~ | !p E5:6~ | D#5:3 E5:1 D#5:1 E5:1 | "
             "!48 E5:2 G5:1 B5:3 | !46 B5:3 A5:1 G5:2 | !40 E5:2 D5:1 C5:3 | "
             "!34 C5:3 A4:3 |",
        harm="@oboe !pp G4:6 | A4:6 | !p C5:6 | B4:3 C#5:1 B4:1 C#5:1 | "
             "!34 G4:2 B4:1 G5:3 | !32 G5:3 F5:1 E5:2 | !28 C5:2 B4:1 A4:3 | "
             "!24 A4:3 F#4:3 |",
        bass="!pp E3:3 B3:3 | C3:3 G3:3 | !p A3:3 C4:3 | B3:3 D#4:3 | "
             "!38 E3:3 B3:3 | C4:3 E4:3 | !32 A3:3 C4:3 | !26 D3:3 A3:3 |",
        pad="!pp B3:6 <10,16> | C4:6 <16,28> | -:6 | D#4:6 <28,36> | "
            "E4:6 <36,50> | -:6 | E4:6 <44,26> | F#4:6 <26,14> |",
        rhy="L1 !p " + _wave(EM, C, ("A2", "E3", "G3", "C4"),
                             ("B2", "F#3", "A3", "D#4")) +
            " !mp E2:1 B2:1 G3:1 B3:1 E4:1 G4:1 | C2:1 G2:1 E3:1 G3:1 C4:1 E4:1 | "
            "!p A4:1 E4:1 C4:1 A3:1 E3:1 A2:1 | C4:1 A3:1 F#3:1 D3:1 A2:1 D2:1 |",
        drum="@timp r:6 | r:6 | r:6 | !28 B2:6 | !44 E2:6 | !40 G2:6 | "
             "!26 A2:6 | !30 D2:6 |",
        x1="@kentong !pp B2:2 B2:2 B2:2 | E3:2 r:4 | r:6 | r:6 | r:6 | r:6 | "
           "r:6 | r:6 |")

    # -- A': the tune once more, mp to mf. From bar 5 the cello sings it an
    # octave under the flute; bar 6 goes into C minor (the cloud), the flute
    # turns on the leading tone at the phrase end (bar 4) and the whole bay is
    # steady. Unique: it carries the jump back to A.
    t.section('Ap', chords="G | D/F# | Em | D | G | Cm | D7 | G",
        lead="@flute " + shaped(
            "G4:3 E5:3 | D5:1 C5:1 B4:1 A4:3 | B4:3 G5:3 | F#5:1 G5:1 F#5:1 E5:1 D5:1 C5:1 | "
            "G4:3 E5:3 | Eb5:1 D5:1 C5:1 G4:3 | A4:3 F#5:3 | E5:1 D5:1 B4:1 G4:3 |",
            (44, 42, 48, 44, 46, 42, 48, 42)),
        harm="!32 E4:3 G4:3 | B4:1 A4:1 G4:1 F#4:3 | G4:3 E5:3 | "
             "D5:1 E5:1 D5:1 C5:1 B4:1 A4:1 | @cello !36 G3:3 E4:3 | "
             "Eb4:1 D4:1 C4:1 G3:3 | A3:3 F#4:3 | E4:1 D4:1 B3:1 G3:3 |",
        bass="!34 G3:3 D3:3 | F#3:3 A3:1 B3:1 C4:1 | E3:3 G3:3 | D3:3 F#3:1 E3:1 D3:1 | "
             "G3:6 | C3:6 | D3:6 | G3:6 |",
        pad="!p B3:6 | A3:6 | G3:6 | A3:6 | !mp B3:6 | Eb4:6 | D4:6 | B3:6 |",
        rhy="L1 !mp " + _wave(G, DF, EM, D, G, ("C2", "G2", "Eb3", "C4"), D7, G),
        drum="@timp !24 G2:6 | r:6 | r:6 | r:6 | !30 G2:6 | r:6 | !26 D2:6 | !30 G2:6 |",
        x1="@kentong !pp r:6 | r:6 | r:6 | r:6 | r:6 | r:6 | "
           "D3:2 D3:2 D3:2 | G3:2 r:4 |")

    t.play('intro', 'A', 'B', 'Ap', loop=1)
    return t
