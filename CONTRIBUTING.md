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

Pillow is optional; install it only for the PNG preview and emulator-capture
tools. numpy is also what re-bakes the pre-rendered sprites with
`python3 gen_render.py`, after changing the renderer, a `render_*.py` scene
module, or the sprite palettes.

## Before submitting

Run the source checks:

```sh
python3 -m compileall -q .
python3 checktext.py
python3 checkfaces.py
```

Then run `make`. A successful build also checks duplicate symbols, soundbank
layout, text width, portrait coverage, and the ROM's mapping, SRAM declaration,
size, and checksum. Gameplay changes should be exercised in an accurate
emulator or on compatible hardware.

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
