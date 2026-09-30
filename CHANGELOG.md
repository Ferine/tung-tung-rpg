# Changelog

All notable public releases are documented here.

## [Unreleased]

The soundtrack, rewritten. The previous one was described by the person who
played it as "literally earsplitting", and measurement agreed for reasons the
loudness figure never showed.

- **Fourteen new themes**, composed rather than generated from templates, on
  twenty-seven real recorded instruments (strings, woodwinds, horns, harp,
  gamelan-flavoured mallets, timpani, the kentongan). Three ideas recur so the
  score is one work: the call (three notes and a leap: TUNG. TUNG. TUNG.), the
  road, and the lullaby. Il Silenzio now has a theme for each shape it fights
  in; the second starts when the second shape stands up (`BGM_FINAL2`).
- **Why it was harsh, all fixed.** Samples were decimated with a box average,
  which is not a low-pass, so everything above the new Nyquist folded back in as
  an inharmonic shimmer (a high trumpet note was 50% harmonic; now 98%). Four of
  nine sustained instruments ticked once per note where the attack met the
  loop. The keyboard was an octave off its own note names, which put trumpet and
  oboe leads at 900-1800Hz. Every phrase ended in a hard cut and the whole
  score dropped out for a beat at each pattern seam. The brass and the oboe
  carried the melody, and a trumpet on a tune is ~15dB harsher in the 2-6kHz
  band than a horn on the same notes; the new leads are horn, clarinet, flute,
  oboe and strings, with brass under the tune.
- **The kentongan was mistuned.** The slit drums the game is named after were
  labelled A4 and D4; they sound D#3 and about A2. The glockenspiel was an
  octave off. Instruments are now tuned to what is measured, not what a file
  is called.
- **Sound effects** are soft, rounded sounds at 8kHz instead of full-scale blips
  at 16kHz (about half the ARAM), and quieter in the mix; the SAHUR! effect is
  the real slit drum.
- **New tooling.** `score.py` (a notation for the score, with range, bar-length
  and harmony checks and an exact ARAM budget), `orchestra.py`, and
  `audition.py`, which plays any theme through an emulated SPC700 and reports
  loudness, clipping, dropouts and shrillness. `checktune.py` now also checks
  every loop seam.
- Requires numpy to regenerate the audio (already needed for `gen_render.py`).

## [0.001] - 2026-08-14

First public binary pre-release.

- Complete six-act campaign across seven regions.
- Active-time battles, five-character party, skills, items, equipment, shops,
  and battery-backed saves.
- Thirteen-track sampled orchestral soundtrack built from pinned CC0 sources.
- Generated graphics, animated tiles, dialogue portraits, battle backdrops,
  H-DMA gradients, and water shimmer.
- Verified 4 MB LoROM image with 2 KB battery-backed SRAM and a valid internal
  checksum.
- Tested through the Mesen-S libretro core and the scripted playthrough tools.

[0.001]: https://github.com/Ferine/tung-tung-rpg/releases/tag/v0.001
