# Contributing

Issues and focused patches are welcome. Before opening a large feature change,
start with an issue so the gameplay, ROM-space, and hardware tradeoffs can be
agreed before implementation.

## Development setup

You need Python 3.10 or newer, GNU Make, and a pvsneslib checkout:

```sh
export PVSNESLIB_HOME=/path/to/pvsneslib
make
```

The checked-in graphics and tracker modules are sufficient for a normal build.
If you change the score or the audio-generation pipeline, fetch its pinned CC0
inputs first (numpy is required for this):

```sh
python3 fetch_samples.py
python3 gen_music.py         # both modules and res/music.h; prints the ARAM budget
python3 checktune.py         # every instrument's tuning and loop seams
make
```

The score is `themes_*.py`, written in the notation documented at the top of
`score.py`; the instruments are `orchestra.py`. To hear what a theme does on
the console rather than what it looks like on paper, play it through an
emulated SPC700 — it reports loudness, clipping, dropouts and shrillness, and
writes a WAV:

```sh
export MESEN_S_CORE=/path/to/mesens_libretro.dylib   # the emulator core
python3 audition.py FIELD --spectrogram
```

Pillow is needed for PNG previews, emulator captures and the offline
`gen_prerender.py` environment bake. Normal asset regeneration reads the
checked-in environment bake and needs neither Pillow nor numpy. Changing a
painting requires reviewing `assets/prerendered/layouts.json`, then
`python3 gen_prerender.py`, `gen_world.py` and
`gen_battle.py`. Keep the source PNGs, bake and generated assets together.
Changing procedural character/title scenes or sprite palettes requires
`python3 gen_render.py` (numpy). The larger field actors and guardian figures
have a separate numpy bake: run `python3 gen_fieldactors.py`, followed by
`python3 gen_sprites.py`. Commit `assets/fieldactors.txt`, the packed OBJ
files and `src/fieldactormap.h` together. Map geometry changes need a matching field
painting; collision hashes reject a bake made for a different layout.

## Before submitting

Run the source checks:

```sh
python3 -m compileall -q .
python3 checktext.py
python3 checkfaces.py
python3 checkgfx.py
python3 checkfields.py
```

Then run `make`. A successful build also checks duplicate symbols, soundbank
layout, text width, portrait coverage, and the ROM's mapping, SRAM declaration,
size, and checksum. Gameplay changes should be exercised in an accurate
emulator or on compatible hardware. Run the repeatable ROM suite with a
WRAM-capable Snes9x libretro core (Pillow is needed for pixel comparisons):

```sh
MESEN_S_CORE=/path/to/snes9x_libretro.so python3 test_game.py
MESEN_S_CORE=/path/to/snes9x_libretro.so python3 test_quests.py
MESEN_S_CORE=/path/to/snes9x_libretro.so python3 test_campaign.py
python3 checkfields.py --previews build/field-review
```

The suite covers all regions, scrolling pixels and timing, foreground depth,
animation, field sprite/portrait VRAM, walk phases, screen-edge clipping,
guardian visibility, legacy saves, backtracking, guardian victories, recruitment, and
save/load through the ending. It uses high-level parties to exercise
progression quickly; it is not a balance test. `test_quests.py` checks quest
stages, prerequisites, exclusions, single rewards, autosaves, legacy migration
and full-party recovery. `test_campaign.py` walks from NEW GAME to the ending
using starting stats/supplies and ordinary encounters, without claiming
sidequest rewards or editing game state. It checks one repeatable route;
varied human playtesting remains useful for difficulty and pacing.
CI builds the ROM with pinned
pvsneslib and Snes9x revisions and runs this same suite. Screenshots and
scenario results are written to `build/regressions/`.
Quest captures are in `build/quests/`; natural campaign checkpoints are in
`build/campaign/results.json`.

If a non-audio generator changes, run the corresponding generator and commit
its deterministic binary/header output. For audio-pipeline changes, fetch the
pinned recordings, run `python3 gen_music.py` and `python3 checktune.py`, and
commit `res/ttsfx.it`, `res/ttbgm.it`, and `res/music.h`; do not commit
`samples/`, `build/`, or `res/soundbank.*`. A theme should read `ok` in
`audition.py` before it is submitted.

Do not commit ROM images, compiler/linker products, emulator saves or states,
bulk screenshots, caches, or machine-specific paths. Only contribute code,
writing, art, and audio you have the right to submit.

## Contribution terms

By submitting a code or asset contribution, you agree that it may be
distributed under the project's MIT License. You must have the right to submit
the contribution under those terms. Issues and review feedback do not transfer
copyright.
