# Where the instruments come from

The soundtrack is cut from two sample libraries by Versilian Studios, both
released under **CC0-1.0** — a public domain dedication:

| library | used for | source |
|---|---|---|
| VSCO-2-CE | violin, viola and cello sections, solo violin, contrabass, oboe, flute, clarinet, bassoon, horn, trumpet, tenor trombone, tuba, pipe organ, timpani, pizzicato strings, cymbal, triangle, claves, anvil | <https://github.com/sgossner/VSCO-2-CE> |
| VCSL | concert harp, dan tranh, marimba, balafon, glockenspiel, tubular bell, gong, tambourine, slit drum, rope-tension snare, bass drum, hi-hat | <https://github.com/sgossner/VCSL> |

`python3 fetch_samples.py` downloads the thirty-nine specific recordings into
`samples/`. They are about 58MB of source material for about 25KB of BRR, so
they are not committed. `fetch_samples.PICKS` is the exact list, with the
repository path of each file. `fetch_samples.REVISIONS` pins both source
repositories to exact commits and `fetch_samples.SHA256` verifies every
recording before it is used, so an upstream branch change cannot silently alter
the soundtrack. Which of the thirty-nine a given build uses is the score's
decision (`orchestra.py`): an instrument nothing plays is not built.

## Why CC0 and not a soundfont

The obvious first move is a General MIDI soundfont, and the obvious first
choice is FluidR3, which is widely described as public domain. Its own readme
says *"Released to Public Domain on 12/25/01"* and then, four paragraphs later,
*"the samples are copyrighted, so you may not redistribute any part of my work
to public domain without my written consent."*

Cutting a recording into pieces and shipping the pieces inside a cartridge
image is redistributing part of the work. The two statements cannot both be
honoured, so the file went unused. CC0 has no such ambiguity, which is the
entire reason to prefer it here.

## Octave numbering

The `note` column in `fetch_samples.PICKS` is the **sounding** pitch in
scientific naming (middle C is C4), and it very often disagrees with the
filename it came from. VSCO-2-CE names middle C as C3, and its strings, winds
and brass all measure exactly one octave above their filenames. VCSL names
middle C as C4 for some instruments and C3 for others: the marimba, the balafon,
the dan tranh, the vibraphone and the hand chimes all sound an octave above
theirs, and the glockenspiel labelled C6 sounds C7.

This is not assumed. The build measures every recording and stops if it
disagrees with its declared note by more than 60 cents: sustained instruments
by period (`sfsample.detect_f0`, YIN with a multi-period refinement), struck
bars by spectral peak, plucked strings by period again — a plucked string's
transient is not a partial, and a spectral peak read a violin pizzicato 160
cents out. Two things were found that no filename would have told anyone: the
slit drums the game is named after sound at D♯3 and about A2, not the A4 and D4
the first score assumed, and the wine-glass recordings are inharmonic enough
that neither method can tune them, so they are not used.

## What is done to them

A ten-second 44.1kHz stereo WAV is not a SNES instrument. `sfsample.py`:

- sums to mono — the DSP pans a mono sample per voice
- **low-passes properly** (a Kaiser-windowed sinc) before reducing the rate,
  which the first version did with a box average; that is not a filter, and it
  folded everything above the new Nyquist back into the band as an inharmonic
  shimmer under every note
- keeps `p` samples per cycle of the instrument's pitch (24–32, so 12–16
  harmonics) rather than a fixed sample rate: the number of harmonics is the
  timbre, and the storage cost scales with pitch, so a bass is nearly free
- cuts an attack and a loop that is **contiguous with it**, chosen where the
  source is most periodic over the loop length, and blends the seam
- makes the loop an exact whole number of the instrument's own periods on a
  16-sample BRR block, and makes its last samples equal the samples before its
  start, because smconv's BRR encoder predicts each block from the previous ones
  and at the wrap those are the end of the loop
- shapes the brightest recordings (`tilt`, `bw`) so a solo violin or a trumpet
  is not as bright at the top of its range as the recording is at the middle

After which `C5Speed = 261.63 × (loop length / periods)` puts tracker note 60 on
a middle C by construction. `checktune.py` measures the finished samples and
fails the asset build if any is more than 18 cents out — they are all within a
cent — or if either seam steps by more than the loop's own steepest ordinary
step.

Glockenspiel, harp, marimba, the pizzicati and the like are struck or plucked
and then decay; they are pitched one-shots rather than loops, because looping a
note that has already stopped is the most recognisable way for a sampled
instrument to sound wrong.

## This is how it was done in 1994

FF6 and Chrono Trigger are not synthesised. They are real orchestral
recordings cut down to a few hundred bytes each, looped, and played back
through the SPC700's Gaussian interpolation. Running real orchestral material
through the same process is what makes the result sound like the era rather
than like a chiptune. What separates a loved 16-bit score from a harsh one is
how carefully that is done: a decimation filter that is not a filter, a loop
that ticks once per note, or a trumpet at the top of its register is the
difference between "warm and a little dull, like the cartridge" and "earsplitting".
