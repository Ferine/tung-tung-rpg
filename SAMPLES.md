# Where the instruments come from

The soundtrack is cut from two sample libraries by Versilian Studios, both
released under **CC0-1.0** — a public domain dedication:

| library | used for | source |
|---|---|---|
| VSCO-2-CE | violin section, cello section, contrabass, oboe, flute, horn, pipe organ, timpani | <https://github.com/sgossner/VSCO-2-CE> |
| VCSL | concert harp, glockenspiel, slit drum, rope-tension snare, bass drum, hi-hat | <https://github.com/sgossner/VCSL> |

`python3 fetch_samples.py` downloads the fifteen specific recordings into
`samples/`. They are 21MB of source material for about 14KB of ROM, so they are
not committed. `fetch_samples.PICKS` is the exact list, with the repository
path of each file. `fetch_samples.REVISIONS` pins both source repositories to
exact commits and `fetch_samples.SHA256` verifies every recording before it is
used, so an upstream branch change cannot silently alter the soundtrack.

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

VSCO-2-CE names middle C as **C3**. VCSL names it **C4**, which is scientific
pitch. The `note` column in `fetch_samples.PICKS` is always scientific, so half
the entries deliberately disagree with the filename they came from.

This was not assumed. `sfsample.detect_f0` measures every recording at build
time and stops the build if one disagrees with its declared note by more than
60 cents. Five separate VSCO instruments each measured exactly one octave above
their filename — which is what a naming convention looks like from the outside,
and what a systematically detuned soundtrack looks like from the inside.

## What is done to them

A ten-second 44.1kHz stereo WAV is not a SNES instrument. `sfsample.py`:

- sums to mono — the DSP pans a mono sample per voice
- resamples to 7–13kHz, per instrument, because 64KB of ARAM holds the whole
  soundtrack and a contrabass has nothing above 3kHz worth paying for
- cuts an attack plus a loop, and crossfades the seam
- makes the loop an exact whole number of the instrument's own periods

That last one is the whole job. A loop can only re-enter at a BRR block
boundary, so its length must be a multiple of 16 samples — and 16 has no reason
to divide the period of a violin. Cut at a round number instead and the loop is
11.5 periods long, so every wrap restarts the waveform half a cycle out of
phase. A crossfade hides the click but not the pitch: what you hear is the loop
frequency itself, a 14Hz warble under a sustained note, worse the lower the
instrument. So the source is resampled by a fraction of a percent until k
periods fit the block-aligned length exactly, after which

    C5Speed = 523.25 * (loop length / periods)

puts note 60 on a C5 by construction. `checktune.py` measures the finished
samples and fails the asset build if any is more than 18 cents out.

Glockenspiel and harp are struck and then decay; both are pitched one-shots
rather than loops, because looping a note that has already stopped is the most
recognisable way for a sampled instrument to sound wrong.

## This is how it was done in 1994

FF6 and Chrono Trigger are not synthesised. They are real orchestral
recordings cut down to a few hundred bytes each, looped, and played back
through the SPC700's Gaussian interpolation. Running real orchestral material
through the same process is what makes the result sound like the era rather
than like a chiptune — the compression artefacts are the period sound.
