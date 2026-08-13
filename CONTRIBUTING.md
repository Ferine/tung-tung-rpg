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
If you change the audio-generation pipeline, fetch its pinned CC0 inputs first:

```sh
python3 fetch_samples.py
python3 gen_assets.py
make
```

Pillow is optional; install it only for the PNG preview and emulator-capture
tools.

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
pinned recordings, run `python3 gen_assets.py` (which includes the tuning
check), and commit `res/ttsfx.it`, `res/ttbgm.it`, and `res/music.h`; do not
commit `samples/*.wav` or `res/soundbank.*`.

Do not commit ROM images, compiler/linker products, emulator saves or states,
bulk screenshots, caches, or machine-specific paths. Only contribute code,
writing, art, and audio you have the right to submit.

## Contribution terms

By submitting a code or asset contribution, you agree that it may be
distributed under the project's MIT License. You must have the right to submit
the contribution under those terms. Issues and review feedback do not transfer
copyright.
