#!/usr/bin/env python3
"""Build every binary the ROM embeds, then hand off to `make`.

Each family lives in its own module so this stays a driver:

    gen_font.py     the BG2 character sheet -- glyphs, icons, gauges, the
                    window frame -- plus src/gfxmap.h
    gen_world.py    seven regions: tilesets, tilemaps, collision, events,
                    plus src/worldmap.h and worlddata.asm
    gen_battle.py   six battle backdrops, plus src/bgmap.h and bgdata.asm
    gen_sprites.py  the resident OBJ sheet, the streamed enemy blob, and
                    src/sprmap.h
    gen_hdma.py     the per-scanline colour and scroll tables
    gen_mode7.py    the affine battle-warp map, characters and palette
    gen_music.py    the Impulse Tracker modules smconv packs into the SPC
                    soundbank

The generated headers are why this has to run before make and not beside it:
the C code indexes art by names these emit.
"""
import gen_battle
import gen_font
import gen_hdma
import gen_mode7
import gen_music
import gen_title
import gen_sprites
import gen_world


def main():
    gen_font.generate_font()
    gen_world.generate_world()
    gen_battle.generate_battle()
    gen_sprites.generate_sprites()
    gen_hdma.generate_hdma()
    gen_mode7.generate_mode7()
    gen_title.generate_title()

    gen_music.main()

    # The instruments are cut from real recordings, and a loop that does not
    # hold a whole number of periods plays sharp for the whole soundtrack
    # while looking completely fine. Measure the finished samples.
    import checktune
    if checktune.main() != 0:
        raise SystemExit("instruments are out of tune")
    print("Done. Now run 'make'.")


if __name__ == '__main__':
    main()
