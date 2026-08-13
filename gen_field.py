#!/usr/bin/env python3
"""The overworld: BG1 tileset ($3000), 64x64 tilemap ($4000), collision table.

The world is authored as 16x16-dot metatiles because that is the unit the game
actually reasons in -- one walking step, one collision cell, one encounter
cell. The PPU is given 8x8 characters (A-12) and a 64x64 tilemap, so a metatile
is four map entries; the split happens here and the C side never sees it.

Tiles are deduplicated on their 8x8 pixel content, which is what keeps a
speckled grass field from spending 256 characters on noise: every grass
metatile draws from the same small pool of textures.
"""
import snesgfx as g

MAP_W = MAP_H = 32               # metatiles
TILE_MAP_W = TILE_MAP_H = 64     # 8x8 characters

# ---- palettes -----------------------------------------------------------

PAL0 = [                          # nature
    (0, 0, 0),          # 0  transparent (backdrop shows through)
    (24, 32, 24),       # 1  outline
    (40, 96, 48),       # 2  grass dark
    (64, 136, 64),      # 3  grass mid
    (104, 176, 88),     # 4  grass light
    (24, 64, 40),       # 5  tree dark
    (40, 104, 56),      # 6  tree mid
    (72, 152, 80),      # 7  tree light
    (24, 48, 112),      # 8  water dark
    (48, 88, 176),      # 9  water mid
    (120, 168, 232),    # 10 water light
    (72, 64, 72),       # 11 rock dark
    (120, 112, 112),    # 12 rock mid
    (168, 160, 152),    # 13 rock light
    (216, 192, 136),    # 14 sand / path
    (248, 240, 216),    # 15 highlight
]

# Palette 1 carries the built world -- and the grass it stands on. A house is
# one metatile block with transparent corners, and colour 0 of a BG palette is
# not "grass", it is the backdrop showing through (ppu-graphics.md: "all-zero
# dot data = transparent"), which would ring every roof in black. So the last
# three slots duplicate PAL0's grass ramp exactly and the art fills its own
# background.
PAL1 = [
    (0, 0, 0),          # 0  transparent
    (24, 16, 24),       # 1  outline
    (112, 40, 40),      # 2  roof dark
    (168, 64, 56),      # 3  roof mid
    (216, 112, 88),     # 4  roof light
    (96, 80, 64),       # 5  wall dark
    (152, 128, 96),     # 6  wall mid
    (200, 176, 136),    # 7  wall light
    (72, 48, 32),       # 8  wood / beam
    (48, 32, 24),       # 9  doorway
    (248, 216, 96),     # 10 lamplight
    (64, 64, 80),       # 11 stone dark
    (112, 112, 128),    # 12 stone mid
    (40, 96, 48),       # 13 grass dark   ) identical to PAL0 2/3/4
    (64, 136, 64),      # 14 grass mid    )
    (104, 176, 88),     # 15 grass light  )
]

# ---- a deterministic noise source ---------------------------------------
#
# Texture has to be identical on every run or the tile dedup pool -- and with
# it every name in the tilemap -- reshuffles between builds.


class Noise:
    def __init__(self, seed):
        self.s = seed & 0xFFFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s >> 16

    def chance(self, n):
        return (self.next() % 100) < n


# ---- metatile art -------------------------------------------------------
#
# 16 rows of 16 characters. Hex digit = palette index; '.' = leave whatever the
# background pass put there, which is how a tree keeps grass under its gaps.

ART = {}

# The trunk is outline + rock-dark rather than a brown: palette 0 spends its
# middle slots on water and has none to spare, and a dark grey trunk under a
# green canopy reads correctly anyway.
ART['TREE'] = [
    "................",
    ".....555556.....",
    "...5566666655...",
    "..556777766655..",
    ".5567777776665..",
    ".5677777777665..",
    "556777777776655.",
    "56677777777765..",
    ".56677777766655.",
    ".5566777766655..",
    "..556666665.5...",
    "...5556655......",
    "......1b1.......",
    "......1b1.......",
    ".....51b15......",
    "................",
]

ART['MOUNTAIN'] = [
    "................",
    "................",
    ".......bb.......",
    "......bddb......",
    "......bdfdb.....",
    ".....bddfddb....",
    "....bdddddccb...",
    "...bddccdccccb..",
    "..bddcccccccccb.",
    ".bddccccccccccb.",
    "bddccccccccccbb.",
    "bdcccccbccccbb..",
    "bcccbbb..bbb....",
    "bbbb............",
    "................",
    "................",
]

ART['WATER'] = [
    "8888888888888888",
    "8998888899988888",
    "899988889a988888",
    "8899888889988888",
    "8888888888888888",
    "8888899988888999",
    "888899a9888899a9",
    "8888899988888999",
    "8888888888888888",
    "8999888888888888",
    "89a9888889998888",
    "8999888889a98888",
    "8888888888999888",
    "8888888888888888",
    "8888999888888888",
    "8888999888888888",
]

ART['PATH'] = [
    "eeeeeeeeeeeeeeee",
    "eeeedeeeeeeeeeee",
    "eeeeeeeeeedeeeee",
    "eeeeeeeeeeeeeeee",
    "eedeeeeeeeeeeede",
    "eeeeeeeeedeeeeee",
    "eeeeeeeeeeeeeeee",
    "eeeeedeeeeeeeeee",
    "eeeeeeeeeeeedeee",
    "eeeeeeeeeeeeeeee",
    "eedeeeeeeeeeeeee",
    "eeeeeeeedeeeeeee",
    "eeeeeeeeeeeeeeee",
    "eeeeedeeeeeeedee",
    "eeeeeeeeeeeeeeee",
    "eeeeeeeeeeeeeeee",
]

ART['FLOWERS'] = [
    "................",
    "....f...........",
    "...ff......f....",
    "....f.....ff....",
    "...........f....",
    ".......f........",
    "......ff........",
    ".......f...f....",
    "..........ff....",
    "...f.......f....",
    "..ff............",
    "...f......f.....",
    ".........ff.....",
    "..........f.....",
    "................",
    "................",
]

ART['BRIDGE'] = [
    "8888888888888888",
    "1111111111111111",
    "eeeeeeeeeeeeeeee",
    "eeeeeeeeeeeeeeee",
    "1e1e1e1e1e1e1e1e",
    "eeeeeeeeeeeeeeee",
    "eeeeeeeeeeeeeeee",
    "1e1e1e1e1e1e1e1e",
    "eeeeeeeeeeeeeeee",
    "eeeeeeeeeeeeeeee",
    "1e1e1e1e1e1e1e1e",
    "eeeeeeeeeeeeeeee",
    "eeeeeeeeeeeeeeee",
    "1111111111111111",
    "8888888888888888",
    "8888888888888888",
]

ART['STONE'] = [                   # village square, palette 1
    "bbbbbbbbbbbbbbbb",
    "bcccbbbcccbbcccb",
    "bcccbbbcccbbcccb",
    "bbbbbbbbbbbbbbbb",
    "cccbbcccbbcccbbc",
    "cccbbcccbbcccbbc",
    "bbbbbbbbbbbbbbbb",
    "bcccbbbcccbbcccb",
    "bcccbbbcccbbcccb",
    "bbbbbbbbbbbbbbbb",
    "cccbbcccbbcccbbc",
    "cccbbcccbbcccbbc",
    "bbbbbbbbbbbbbbbb",
    "bcccbbbcccbbcccb",
    "bcccbbbcccbbcccb",
    "bbbbbbbbbbbbbbbb",
]

ART['CAVE'] = [                    # palette 1: a mouth cut into the rock
    "eeeeeeeeeeeeeeee",
    "ebbbbbbbbbbbbbbe",
    "ebbccccccccccbbe",
    "ebcc11111111ccbe",
    "ebc1111111111cbe",
    "ebc1111111111cbe",
    "ebc1111111111cbe",
    "ebc1111111111cbe",
    "ebc1111111111cbe",
    "ebc1111111111cbe",
    "ebc1111111111cbe",
    "ebcc11111111ccbe",
    "ebbcccccccccbbbe",
    "eebbbbbbbbbbbbee",
    "eeeebbbbbbbbeeee",
    "eeeeeeeeeeeeeeee",
]

# Houses are 2x2 metatiles, authored as one 32x32 block and cut up below.
# Palette 1 throughout: 1 outline, 2-4 roof, 5-7 wall, 8 beam, 9 doorway,
# a lamplight, and '.' meaning "leave the grass the background pass drew".
HOUSE = [
    "................................",
    "..............1111..............",
    "............11222211............",
    "..........112233332211..........",
    "........1122333443332211........",
    "......11223333444433332211......",
    "....112233333344443333332211....",
    "..1122333333334444333333332211..",
    "11223333333333444433333333332211",
    "12233333333333444433333333333221",
    "11111111111111111111111111111111",
    "18666666666666666666666666666681",
    "18677777777777777777777777777681",
    "1867aaaa77777777777777aaaa777681",
    "1867aaaa7777799999777aaaa7777681",
    "18677777777799999977777777777681",
    "18666666667799999977766666666681",
    "18677777777999999997777777777681",
    "18677777777999999997777777777681",
    "18666666667999999997766666666681",
    "18677777777999999997777777777681",
    "18677777777999999997777777777681",
    "18666666667999999997766666666681",
    "18677777777999999997777777777681",
    "18555555557999999997755555555681",
    "18555555557999999997755555555681",
    "11111111117999999997711111111111",
    "..........1999999991............",
    "..........1999999991............",
    "..........11111111111...........",
    "................................",
    "................................",
]

# ---- collision ----------------------------------------------------------

WALK, BLOCK, ENC, TRIG = 0x00, 0x01, 0x02, 0x04

TERRAIN = {
    # char : (art name, palette, flags)
    '.': ('GRASS',    0, ENC),
    'T': ('TREE',     0, BLOCK),
    '^': ('MOUNTAIN', 0, BLOCK),
    '~': ('WATER',    0, BLOCK),
    '=': ('BRIDGE',   0, WALK),
    '-': ('PATH',     0, WALK),
    'f': ('FLOWERS',  0, ENC),
    'o': ('STONE',    1, WALK),
    # BLOCK as well as TRIG: the mouth is bumped into, never stood on.
    # Walking onto it would fire the trigger and then leave the player
    # parked on the cell, with no way to enter it a second time.
    'C': ('CAVE',     1, BLOCK | TRIG),
}

# ---- the world ----------------------------------------------------------
#
# 32x32 metatiles = 512x512 dots, which is exactly a 64x64 tilemap at SC size 3
# (A-14). Built rather than typed: a hand-drawn 32x32 grid of characters is
# both tedious to keep 32 wide and bad at the one thing an overworld needs,
# which is a river that meanders and a coastline that is not a rectangle.
#
# Landmarks the C side depends on are exported to src/fieldmap.h so the spawn
# point and the boss trigger cannot drift from the art.

import math

VILLAGE_X, VILLAGE_Y = 5, 6      # plaza top-left, metatiles
CAVE_X, CAVE_Y = 27, 25
SPAWN_X, SPAWN_Y = 7, 8

HOUSES = ((4, 3), (8, 3), (12, 3))

ROAD_X = 27                      # the east leg, clear of the lake
FORD_Y = 12                      # where the road crosses the river


def build_world():
    W = [['.' for _ in range(MAP_W)] for _ in range(MAP_H)]

    def put(x, y, ch):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            W[y][x] = ch

    def river_x(y):
        """A meander. Two out-of-phase sines so it never repeats visibly."""
        return 16.0 + 2.5 * math.sin(y * 0.38) + 1.2 * math.sin(y * 0.13 + 1.0)

    # --- water: a river down the map, swelling into a lake in the south ---
    for y in range(MAP_H):
        cx = river_x(y)
        # Half-width: pinched at the ford so the bridge is one span, opening
        # into the lake from y=15 down.
        hw = 1.4
        if y > 15:
            hw = 1.4 + 2.4 * math.sin(min(1.0, (y - 15) / 7.0) * math.pi * 0.5)
        if abs(y - FORD_Y) <= 1:
            hw = 1.0
        for x in range(MAP_W):
            if abs(x - cx) <= hw:
                put(x, y, '~')

    # --- mountains: a ring, with a noisy inner edge ---
    for y in range(MAP_H):
        for x in range(MAP_W):
            d = min(x, y, MAP_W - 1 - x, MAP_H - 1 - y)
            wobble = 1.1 + 0.9 * math.sin(x * 0.7) * math.sin(y * 0.5)
            if d < wobble:
                put(x, y, '^')

    # --- forest: a belt just inside the mountains, plus a wood in the east ---
    for y in range(MAP_H):
        for x in range(MAP_W):
            if W[y][x] != '.':
                continue
            d = min(x, y, MAP_W - 1 - x, MAP_H - 1 - y)
            edge = 2.3 + 1.1 * math.sin(x * 0.55 + 2.0) * math.cos(y * 0.6)
            in_wood = (20 <= x <= 25 and 5 <= y <= 10
                       and math.sin(x * 1.1) + math.cos(y * 0.9) > -0.2)
            if d < edge or in_wood:
                put(x, y, 'T')

    # --- village: a stone plaza with a row of houses along the north ---
    for hx, hy in HOUSES:                   # clear the plot first
        for y in range(hy - 1, hy + 3):
            for x in range(hx - 1, hx + 3):
                put(x, y, '.')
    for y in range(VILLAGE_Y, VILLAGE_Y + 4):
        for x in range(VILLAGE_X, VILLAGE_X + 9):
            put(x, y, 'o')
    for hx, hy in HOUSES:
        put(hx, hy, '1')
        put(hx + 1, hy, '2')
        put(hx, hy + 1, '3')
        put(hx + 1, hy + 1, '4')

    # --- the road: village -> ford -> east leg -> cave ---
    def road(x0, y0, x1, y1):
        """Axis-aligned, horizontal leg first. Water on the way becomes a
        bridge; mountain and forest are cut through."""
        x, y = x0, y0
        put(x, y, '=' if W[y][x] == '~' else '-')
        while x != x1:
            x += 1 if x1 > x else -1
            put(x, y, '=' if W[y][x] == '~' else '-')
        while y != y1:
            y += 1 if y1 > y else -1
            put(x, y, '=' if W[y][x] == '~' else '-')

    road(SPAWN_X, VILLAGE_Y + 4, SPAWN_X, FORD_Y)
    road(SPAWN_X, FORD_Y, ROAD_X, FORD_Y)
    road(ROAD_X, FORD_Y, ROAD_X, CAVE_Y)

    # --- flowers, for the parts of the field that are only field ---
    for y in range(MAP_H):
        for x in range(MAP_W):
            if W[y][x] == '.' and math.sin(x * 2.3) * math.cos(y * 1.7) > 0.93:
                put(x, y, 'f')

    # --- the Sleepers' cave, in a clearing ---
    for y in range(CAVE_Y - 1, CAVE_Y + 2):
        for x in range(CAVE_X - 1, CAVE_X + 2):
            if W[y][x] in ('T', '^'):
                put(x, y, '.')
    put(CAVE_X, CAVE_Y, 'C')

    return [''.join(r) for r in W]


WORLD = build_world()


class TilePool:
    """Dedup on 8x8 pixel content. Names come out in first-seen order."""

    def __init__(self):
        self.index = {}
        self.tiles = []

    def add(self, cell):
        key = tuple(tuple(r) for r in cell)
        if key not in self.index:
            self.index[key] = len(self.tiles)
            self.tiles.append(cell)
        return self.index[key]


def grass_cell(noise):
    """A 16x16 grass metatile with speckle -- the background under everything."""
    px = [[3] * 16 for _ in range(16)]
    for y in range(16):
        for x in range(16):
            r = noise.next() % 100
            if r < 8:
                px[y][x] = 2
            elif r < 14:
                px[y][x] = 4
    return px


def art_cell(name, noise, over_grass=True):
    px = grass_cell(noise) if over_grass else [[0] * 16 for _ in range(16)]
    rows = ART[name]
    for y in range(16):
        for x in range(16):
            ch = rows[y][x]
            if ch != '.':
                px[y][x] = int(ch, 16)
    return px


def cut(px16, ox=0, oy=0):
    """Split a 16x16 metatile into the four 8x8 cells, reading order."""
    out = []
    for cy in (0, 8):
        for cx in (0, 8):
            out.append([[px16[oy + cy + y][ox + cx + x] for x in range(8)]
                        for y in range(8)])
    return out


def _validate():
    for name, rows in ART.items():
        assert len(rows) == 16, "%s has %d rows" % (name, len(rows))
        for i, r in enumerate(rows):
            assert len(r) == 16, "%s row %d is %d wide" % (name, i, len(r))
    assert len(HOUSE) == 32, "HOUSE has %d rows" % len(HOUSE)
    for i, r in enumerate(HOUSE):
        assert len(r) == 32, "HOUSE row %d is %d wide" % (i, len(r))
    assert len(WORLD) == MAP_H, "WORLD has %d rows" % len(WORLD)
    for i, r in enumerate(WORLD):
        assert len(r) == MAP_W, "WORLD row %d is %d wide" % (i, len(r))
        for ch in r:
            assert ch in TERRAIN or ch in '1234', \
                "WORLD row %d has unknown terrain %r" % (i, ch)


def generate_field():
    _validate()
    noise = Noise(0xC0FFEE)
    pool = TilePool()

    # Every distinct metatile gets built once. Grass and flowers get several
    # variants so a wide field does not visibly repeat; the pool dedups the
    # 8x8 cells they share anyway.
    variants = {}

    def build(ch, vseed):
        name, pal, flags = TERRAIN[ch]
        if name == 'GRASS':
            px = grass_cell(Noise(vseed))
        elif name in ('WATER', 'STONE', 'CAVE', 'PATH', 'BRIDGE'):
            px = art_cell(name, Noise(vseed), over_grass=False)
        else:
            px = art_cell(name, Noise(vseed))
        return [pool.add(c) for c in cut(px)], pal

    GRASS_VARIANTS = 6
    for i in range(GRASS_VARIANTS):
        variants[('.', i)] = build('.', 0x1000 + i * 977)
    for ch in TERRAIN:
        if ch != '.':
            variants[(ch, 0)] = build(ch, 0x2000 + ord(ch) * 131)

    # House: one 32x32 block cut into four metatiles, keyed '1'..'4'. Its '.'
    # cells are grass, not transparency -- see the PAL1 comment.
    hn = Noise(0xA5A5)
    house_px = [[0] * 32 for _ in range(32)]
    for y in range(32):
        for x in range(32):
            ch = HOUSE[y][x]
            if ch == '.':
                r = hn.next() % 100
                house_px[y][x] = 13 if r < 8 else (15 if r < 14 else 14)
            else:
                house_px[y][x] = int(ch, 16)
    for qi, (qx, qy) in enumerate(((0, 0), (16, 0), (0, 16), (16, 16))):
        cells = []
        for cy in (0, 8):
            for cx in (0, 8):
                cells.append([[house_px[qy + cy + y][qx + cx + x]
                               for x in range(8)] for y in range(8)])
        variants[(str(qi + 1), 0)] = ([pool.add(c) for c in cells], 1)

    HOUSE_FLAGS = {'1': BLOCK, '2': BLOCK, '3': BLOCK, '4': BLOCK}

    tilemap = [0] * (TILE_MAP_W * TILE_MAP_H)
    collide = bytearray(MAP_W * MAP_H)
    gv = Noise(0x5EED)

    for my in range(MAP_H):
        for mx in range(MAP_W):
            ch = WORLD[my][mx]
            if ch == '.':
                key = ('.', gv.next() % GRASS_VARIANTS)
            elif ch in HOUSE_FLAGS:
                key = (ch, 0)
            else:
                key = (ch, 0)
            names, pal = variants[key]

            for i, name in enumerate(names):
                tx = mx * 2 + (i & 1)
                ty = my * 2 + (i >> 1)
                tilemap[ty * TILE_MAP_W + tx] = g.map_entry(name, pal=pal, prio=0)

            if ch in HOUSE_FLAGS:
                collide[my * MAP_W + mx] = HOUSE_FLAGS[ch]
            else:
                collide[my * MAP_W + mx] = TERRAIN[ch][2]

    # The doorway of the lower-left/lower-right house quadrants is walkable so
    # the player can stand in it and trigger the shop/inn text.
    for my in range(MAP_H):
        for mx in range(MAP_W):
            if WORLD[my][mx] == '3' and mx + 1 < MAP_W and WORLD[my][mx + 1] == '4':
                collide[my * MAP_W + mx] = BLOCK | TRIG

    if len(pool.tiles) > 256:
        raise SystemExit("field tileset overflows one 4K-word page: %d tiles"
                         % len(pool.tiles))

    sheet = g.Sheet(256)
    for i, cell in enumerate(pool.tiles):
        ox, oy = sheet.origin(i)
        for y in range(8):
            for x in range(8):
                sheet.set(ox + x, oy + y, cell[y][x])

    # A 64x64 tilemap is not one 64-wide array. ppu-graphics.md A-14: SC size 3
    # is four 32x32 screens laid out SC0 SC1 / SC2 SC3, stored consecutively --
    # SC0 at n+000-3FF, SC1 at n+400-7FF, SC2 at n+800-BFF, SC3 at n+C00-FFF --
    # each with a 32-entry row stride.
    #
    # Written row-major across all 64 columns instead, the PPU reads screen row
    # r from what is actually map row r/2, and the display comes out
    # interleaved: recognisable near the origin, with a stripe of the map's
    # eastern half showing down the left edge.
    quads = []
    for qy in (0, 32):
        for qx in (0, 32):
            for row in range(32):
                base = (qy + row) * TILE_MAP_W + qx
                quads.extend(tilemap[base:base + 32])

    g.write('field.pic', sheet.to_pic())
    g.write('field.pal', g.palette_bin(PAL0) + g.palette_bin(PAL1))
    g.write('field.map', g.map_bin(quads))
    g.write('field.col', bytes(collide))
    sheet.to_png('field-preview.png', PAL0)

    with open('src/fieldmap.h', 'w') as f:
        f.write("/* Generated by gen_field.py -- do not edit. */\n"
                "#ifndef FIELDMAP_H\n#define FIELDMAP_H\n\n")
        f.write("#define MAP_W %d\n#define MAP_H %d\n\n" % (MAP_W, MAP_H))
        f.write("#define COL_BLOCK 0x%02X\n" % BLOCK)
        f.write("#define COL_ENC   0x%02X\n" % ENC)
        f.write("#define COL_TRIG  0x%02X\n\n" % TRIG)
        f.write("/* Landmarks, in metatiles. The C side spawns and triggers on\n"
                " * these, so they cannot be typed in twice. */\n")
        f.write("#define SPAWN_X %d\n#define SPAWN_Y %d\n" % (SPAWN_X, SPAWN_Y))
        f.write("#define CAVE_X  %d\n#define CAVE_Y  %d\n" % (CAVE_X, CAVE_Y))
        for i, (hx, hy) in enumerate(HOUSES):
            f.write("#define HOUSE%d_X %d   /* door cell is (x, y+1) */\n"
                    % (i, hx))
        f.write("\n#endif\n")

    print("field: %d unique tiles, map 64x64, collision %d bytes"
          % (len(pool.tiles), len(collide)))
    return tilemap


if __name__ == '__main__':
    generate_field()
