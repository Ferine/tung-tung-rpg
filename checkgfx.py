#!/usr/bin/env python3
"""Validate the ROM-facing prerender assets and the shared VRAM layout.

Standard library only; also checks DMA source banks when a symbol file is
supplied. This checks the actual packed binaries, not only encoder metadata.
"""
import argparse
from pathlib import Path
import re
import struct

import gen_world as world
import gen_sprites
import fieldactors
import prerender
import snesgfx
from terrain import Rng


def defines():
    values = {}
    for name in ('src/ttrpg.h', 'src/worldmap.h', 'src/bgmap.h', 'src/titlemap.h', 'src/fieldactormap.h'):
        for key, value in re.findall(r'^#define\s+(\w+)\s+(\w+)\s*$',
                                     Path(name).read_text(), re.M):
            if value in values:
                values[key] = values[value]
            else:
                try:
                    values[key] = int(value, 0)
                except ValueError:
                    pass
    return values


def check_actors(d):
    actors = fieldactors.load(gen_sprites.PALS)
    pic = Path('assets/fieldactors.pic').read_bytes()
    guardians = Path('assets/fieldguardians.pic').read_bytes()
    assert len(pic) == d['FIELD_ACTOR_BYTES'] == 16384
    assert len(guardians) == 7 * 512 and guardians[:1024] == bytes(1024)
    assert len(Path('assets/fieldactors.pal').read_bytes()) == 7 * 256
    reserved = fieldactors.PORTRAIT_TILES | {
        d['FIELD_GUARDIAN_NAME'] + y * 16 + x for y in range(4) for x in range(4)}
    occupied = set()
    for index, (key, *_rest) in enumerate(fieldactors.poses()):
        base = fieldactors.name(index)
        cells = {base + y * 16 + x for y in range(4) for x in range(4)}
        assert not cells & (occupied | reserved), 'field OBJ overlaps another figure or portrait'
        assert max(cells) < 512 and base % 16 <= 12 and base % 256 // 16 <= 12
        occupied |= cells
        for y in range(4):
            for x in range(4):
                tile = base + y * 16 + x
                expected = snesgfx.tile_bin([row[x*8:x*8+8] for row in actors[key][y*8:y*8+8]])
                assert pic[tile*32:tile*32+32] == expected, key + ': stale packed pose'
    assert occupied | reserved == set(range(512))
    assert all(pic[n*32:n*32+32] == bytes(32) for n in reserved)
    for area, (key, _pal) in enumerate(fieldactors.GUARDIANS, 2):
        expected = b''.join(snesgfx.tile_bin([row[x:x+8] for row in actors[key][y:y+8]])
                            for y in range(0,32,8) for x in range(0,32,8))
        assert guardians[area*512:(area+1)*512] == expected, key + ': stale guardian'
    for key, rows in actors.items():
        assert all(c == 0 for c in rows[31]), key + ': clipped shadow'
        assert rows[d['FIELD_ANCHOR_Y']][d['FIELD_ANCHOR_X']] != 0, key + ': missing foot contact'
    for direction in ('down', 'up', 'left', 'right'):
        phases = {bytes(c for row in actors['walk.'+direction+'.'+str(i)] for c in row) for i in range(4)}
        assert len(phases) >= 3, 'walk cycle lost its alternating contact poses'
    return {'fieldactors_pic':len(pic), 'fieldactors_pal':7*256, 'fieldguardians_pic':len(guardians)}


def main(symbol_file=None):
    d = defines()
    assert d['VRAM_BATTLE_GFX'] == d['VRAM_FIELD_GFX']
    assert d['BACKDROP_PIC_BYTES'] == prerender.PIC_BYTES
    assert d['TITLE_PIC_BYTES'] <= d['FIELD_CACHE_TILES'] * 32
    spans = [(d['VRAM_OBJ'], 0x2000), (d['VRAM_FONT'], 0x1000),
             (d['VRAM_FIELD_GFX'], d['FIELD_CACHE_TILES'] * 16),
             (d['VRAM_FIELD_MAP'], 0x800), (d['VRAM_TEXT_MAP'], 0x400)]
    assert d['VRAM_BATTLE_MAP'] == d['VRAM_FIELD_MAP']
    spans.sort()
    for (start, length), (next_start, _) in zip(spans, spans[1:]):
        assert start + length <= next_start, 'VRAM overlap'
    assert spans[-1][0] + spans[-1][1] <= 0x8000
    assert d['VRAM_FIELD_GFX'] % 0x1000 == 0
    sources = check_actors(d)
    scenes = [('field', r['key'].lower(), 'area', 8192) for r in world.REGIONS]
    scenes += [('battle', key, 'bg', 2048)
               for key in ('night', 'forest', 'shore', 'salt', 'iron', 'void')]
    for kind, key, prefix, map_size in scenes:
        baked = prerender.load(kind, key)
        stem = prefix + '_' + key
        for part in ('pic', 'map', 'pal'):
            data = Path('assets', stem + '.' + part).read_bytes()
            assert data == baked[part], stem + ': stale ' + part
            if kind == 'field' and part == 'pic':
                for strip in range(8):
                    sources[stem + '_pic' + (str(strip) if strip else '')] = 16384
            else:
                sources[stem + '_' + part] = len(data)
        assert len(baked['pic']) == (131072 if kind == 'field' else prerender.PIC_BYTES)
        assert len(baked['map']) == map_size
        assert len(baked['pal']) == (256 if kind == 'field' else 192)
        palette_first = 0 if kind == 'field' else 2
        reserved = (3 - palette_first) * 32
        assert baked['pal'][reserved:reserved + 32] == bytes(32), 'window palette clobbered'
        words = struct.unpack('<%dH' % (map_size // 2), baked['map'])
        for index, entry in enumerate(words):
            name, pal = entry & 1023, (entry >> 10) & 7
            if kind == 'field':
                assert name == 0 and baked['tiles'] == 4096, stem + ': invalid stream attributes'
                name = index
            else:
                assert name < baked['tiles'] <= prerender.TILES, stem + ': invalid tile'
            assert pal != 3 and pal >= palette_first, stem + ': invalid palette'
            tile = baked['pic'][name * 32:(name + 1) * 32]
            for y in range(8):
                assert tile[y * 2] | tile[y * 2 + 1] | tile[y * 2 + 16] | tile[y * 2 + 17] == 255, stem + ': transparent pixel'
        if kind == 'field':
            region = next(r for r in world.REGIONS if r['key'].lower() == key)
            m = region['build'](Rng(region['seed']))
            # Worst case: everyone shares a scanline, including the portrait.
            figures = sum(world.NPC_POP[region['key']]) + 2 + (key not in ('village','fields'))
            assert figures * 4 <= 34, stem + ': 32px actors exceed the OBJ scanline budget'
            assert Path('assets', stem + '.col').read_bytes() == world.collision(region, m, m.rows())
            assert Path('assets', stem + '.fx').read_bytes() == baked['fx']
            assert len(baked['fx']) == baked['effects'] * 132
            sources[stem + '_fx'] = len(baked['fx'])
            assert baked['effects'] <= 16
            assert any(len(set(baked['fx'][i+4+j*32:i+36+j*32] for j in range(4))) > 1
                       for i in range(0, len(baked['fx']), 132)), stem + ': static effects'
    if symbol_file:
        symbols = {}
        for line in Path(symbol_file).read_text().splitlines():
            parts = line.split()
            if len(parts) == 2:
                try:
                    symbols[parts[1]] = int(parts[0], 16)
                except ValueError:
                    pass
        for name, size in sources.items():
            addr = symbols[name] & 0xffff
            assert addr >= 0x8000 and addr + size <= 0x10000, name + ': DMA crosses a LoROM bank'
    print('checkgfx: 7 fields, 6 battles, 30 actor poses, 5 guardians, collision, palettes, VRAM'
          + (', DMA banks' if symbol_file else '') + ' OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbols')
    main(parser.parse_args().symbols)
