#!/usr/bin/env python3
"""The seven regions: tilesets, 64x64 tilemaps, collision, palettes, events.

Each region is 32x32 metatiles (512x512 dots) and gets its own 256-character
tileset. Only one region is resident in VRAM at a time; changing region is a
forced-blank transfer behind the fade, which is why they can all be different.

The whole overworld is one night. Every palette here is moonlit -- there is no
daylight in the game until the epilogue, and that is the point.

---- collision byte --------------------------------------------------------

    bit 0   blocked
    bit 1   encounters happen here
    bit 2   has an event
    bits 4-7  event id, 1-15, meaningful per region

Packing the event id into the same byte means the field's per-step lookup stays
one array read.
"""
import math

import snesgfx as g
import terrain as T
from terrain import Rng

MAP_W = MAP_H = 32
TILE_MAP_W = TILE_MAP_H = 64

WALK, BLOCK, ENC, TRIG = 0x00, 0x01, 0x02, 0x04

# Event ids. The C dispatches on (region, id).
EV_EXIT1, EV_EXIT2, EV_EXIT3, EV_EXIT4 = 1, 2, 3, 4
EV_TALK1, EV_TALK2, EV_TALK3, EV_TALK4 = 5, 6, 7, 8
EV_INN, EV_SHOP, EV_SAVE, EV_BOSS, EV_STORY = 9, 10, 11, 12, 13

# ---- palettes ----------------------------------------------------------
#
# Slot meanings are terrain.py's semantic layout: 2-4 ground, 5-7 feature,
# 8-10 liquid, 11-13 stone, 14 accent, 15 bright.

NIGHT_GRASS = [
    (0, 0, 0), (16, 14, 24),
    (26, 44, 38), (40, 66, 52), (62, 92, 70),
    (20, 40, 36), (34, 62, 50), (56, 92, 68),
    (18, 26, 54), (34, 50, 92), (74, 104, 150),
    (44, 44, 58), (76, 76, 94), (116, 116, 138),
    (108, 96, 80), (196, 200, 220),
]

BUILT = [
    (0, 0, 0), (16, 14, 24),
    (78, 34, 38), (116, 52, 50), (150, 78, 66),      # roof
    (62, 54, 46), (104, 90, 72), (144, 128, 102),    # wall
    (48, 36, 28), (22, 18, 20), (240, 206, 110),     # beam, doorway, lamp
    (44, 44, 58), (76, 76, 94),                      # stone
    (26, 44, 38), (40, 66, 52), (62, 92, 70),        # ground echo, matches above
]

# Ground pulled down and canopy pushed up: at the first pass these two ramps
# were four points apart and the forest read as a flat dark field with faint
# rings on it. A tree has to be lighter than what it stands on.
FOREST_PAL = [
    (0, 0, 0), (8, 14, 14),
    (12, 20, 18), (18, 30, 26), (26, 42, 34),
    (18, 50, 36), (34, 86, 56), (60, 128, 76),
    (14, 32, 40), (26, 54, 66), (52, 92, 108),
    (38, 40, 44), (64, 68, 72), (96, 102, 106),
    (74, 62, 46), (186, 214, 176),
]

SHORE_PAL = [
    (0, 0, 0), (14, 14, 22),
    (74, 64, 52), (108, 96, 76), (146, 132, 106),
    (22, 44, 38), (38, 72, 56), (62, 104, 74),
    (14, 28, 62), (28, 52, 106), (70, 110, 178),
    (48, 46, 52), (80, 78, 86), (118, 116, 126),
    (150, 138, 110), (222, 230, 246),
]

SALT_PAL = [
    (0, 0, 0), (26, 24, 34),
    (72, 68, 88), (118, 114, 136), (172, 170, 190),
    (44, 70, 54), (70, 110, 76), (104, 150, 100),
    (48, 52, 84), (74, 84, 126), (120, 134, 180),
    (60, 54, 64), (98, 92, 104), (144, 138, 150),
    (176, 158, 122), (252, 252, 255),
]

IRON_PAL = [
    (0, 0, 0), (14, 14, 18),
    (40, 42, 50), (64, 68, 80), (94, 100, 116),
    (56, 44, 40), (88, 68, 56), (124, 96, 74),
    (16, 44, 52), (28, 78, 92), (52, 124, 144),
    (46, 48, 58), (84, 88, 102), (126, 132, 150),
    (142, 78, 44), (248, 196, 96),
]

HUSH_PAL = [
    (0, 0, 0), (8, 6, 14),
    (18, 14, 28), (30, 24, 46), (46, 38, 68),
    (72, 30, 96), (112, 48, 148), (164, 88, 208),
    (20, 20, 40), (34, 34, 64), (56, 56, 96),
    (34, 32, 46), (58, 56, 76), (88, 86, 110),
    (96, 88, 124), (238, 234, 255),
]

# A second palette for regions that have no buildings: the same colours, so the
# tilemap can name palette 1 harmlessly.
def echo(p):
    return list(p)


# ---- the terrain alphabet ----------------------------------------------
#
# char -> (painter, palette, flags). Regions pick a subset; a char missing from
# a region's alphabet is a build error rather than a silent blank.

ALPHABET = {
    '.': ('ground',     0, ENC),
    ',': ('tufted',     0, ENC),
    'f': ('flowers',    0, ENC),
    # Roads carry encounters too. They did not, and since one road runs from
    # the village to the last act the player could walk the entire game
    # without a single fight and arrive at act two still level 1.
    '-': ('path',       0, ENC),
    'o': ('stonefloor', 0, WALK),
    'T': ('tree',       0, BLOCK),
    'Y': ('pine',       0, BLOCK),
    'y': ('deadtree',   0, BLOCK),
    'b': ('bush',       0, BLOCK),
    'r': ('reeds',      0, ENC),
    'c': ('cactus',     0, BLOCK),
    'm': ('mushroom',   0, BLOCK),
    '~': ('water',      0, BLOCK),
    's': ('shallow',    0, BLOCK),
    '_': ('shore',      0, BLOCK),
    '=': ('bridge',     0, ENC),
    'O': ('rock',       0, BLOCK),
    '^': ('mountain',   0, BLOCK),
    '#': ('cliff',      0, BLOCK),
    'x': ('crack',      0, ENC),
    'd': ('dune',       0, BLOCK),
    'B': ('bones',      0, ENC),
    '|': ('fence',      0, BLOCK),
    'C': ('cavemouth',  0, BLOCK),
    '!': ('lantern',    1, BLOCK),
    'W': ('well',       1, BLOCK),
    'I': ('ironfloor',  0, WALK),
    'H': ('ironwall',   0, BLOCK),
    'P': ('pipe',       0, BLOCK),
    'w': ('catwalk',    0, WALK),
    'F': ('furnace',    0, BLOCK),
    'v': ('void',       0, BLOCK),
    'p': ('platform',   0, ENC),
    'R': ('rift',       0, BLOCK),
}

HOUSE_CHARS = '1234'


# ---- map-building helpers ----------------------------------------------

class Map:
    def __init__(self, fill='.'):
        self.g = [[fill] * MAP_W for _ in range(MAP_H)]
        self.events = {}            # (x, y) -> event id

    def put(self, x, y, ch):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            self.g[y][x] = ch

    def get(self, x, y):
        if 0 <= x < MAP_W and 0 <= y < MAP_H:
            return self.g[y][x]
        return None

    def event(self, x, y, ev):
        self.events[(x, y)] = ev

    def rect(self, x0, y0, x1, y1, ch):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.put(x, y, ch)

    def border(self, ch, rng, thick=1.4, wobble=1.0):
        for y in range(MAP_H):
            for x in range(MAP_W):
                d = min(x, y, MAP_W - 1 - x, MAP_H - 1 - y)
                t = thick + wobble * math.sin(x * 0.7) * math.sin(y * 0.5)
                if d < t:
                    self.put(x, y, ch)

    def belt(self, ch, rng, depth=2.4, wobble=1.1, over='.'):
        for y in range(MAP_H):
            for x in range(MAP_W):
                if self.g[y][x] != over:
                    continue
                d = min(x, y, MAP_W - 1 - x, MAP_H - 1 - y)
                e = depth + wobble * math.sin(x * 0.55 + 2.0) * math.cos(y * 0.6)
                if d < e:
                    self.put(x, y, ch)

    def road(self, x0, y0, x1, y1, ch='-', over_water='='):
        x, y = x0, y0
        self.put(x, y, over_water if self.get(x, y) in '~s_' else ch)
        while x != x1:
            x += 1 if x1 > x else -1
            self.put(x, y, over_water if self.get(x, y) in '~s_' else ch)
        while y != y1:
            y += 1 if y1 > y else -1
            self.put(x, y, over_water if self.get(x, y) in '~s_' else ch)

    def scatter(self, ch, rng, n, over='.', margin=2):
        for _ in range(n):
            for _try in range(40):
                x = rng.span(margin, MAP_W - 1 - margin)
                y = rng.span(margin, MAP_H - 1 - margin)
                if self.g[y][x] == over:
                    self.put(x, y, ch)
                    break

    def house(self, x, y, door_event):
        for j in range(-1, 3):
            for i in range(-1, 3):
                if self.get(x + i, y + j) not in (None,):
                    self.put(x + i, y + j, '.')
        self.put(x, y, '1')
        self.put(x + 1, y, '2')
        self.put(x, y + 1, '3')
        self.put(x + 1, y + 1, '4')
        self.event(x, y + 1, door_event)     # the '3' quadrant is the door

    def gate(self, x, y, ev):
        """A road cell that is also an exit."""
        self.put(x, y, '-')
        self.event(x, y, ev)

    def rows(self):
        return [''.join(r) for r in self.g]


# ---- the regions -------------------------------------------------------

def build_village(rng):
    m = Map('.')
    m.border('T', rng, thick=2.0, wobble=1.0)
    m.belt('b', rng, depth=3.0, wobble=0.9)

    m.rect(9, 11, 22, 19, 'o')                      # the plaza
    for hx, hy, ev in ((6, 5, EV_TALK1), (13, 5, EV_INN), (20, 5, EV_SHOP),
                       (6, 22, EV_TALK2), (20, 22, EV_TALK3)):
        m.house(hx, hy, ev)
    m.rect(15, 8, 16, 26, '-')
    m.road(16, 15, 31, 15)
    # After the roads, not before: the crossroads runs straight through the
    # square and would otherwise pave over the well.
    m.put(15, 14, 'W')
    m.event(15, 14, EV_SAVE)
    for lx in (9, 22):
        for ly in (11, 19):
            m.put(lx, ly, '!')
    m.gate(30, 15, EV_EXIT1)                        # east, to the fields
    m.scatter('f', rng, 10)
    m.scatter('O', rng, 4)
    return m


def build_fields(rng):
    m = Map('.')
    m.border('^', rng, thick=1.2, wobble=0.9)
    m.belt('T', rng, depth=2.4, wobble=1.1)

    for y in range(MAP_H):                          # the river
        cx = 19.0 + 2.6 * math.sin(y * 0.36) + 1.2 * math.sin(y * 0.14 + 1.0)
        hw = 1.5 if abs(y - 13) > 2 else 1.0
        for x in range(MAP_W):
            if abs(x - cx) <= hw:
                m.put(x, y, '~')

    m.road(1, 13, 30, 13)
    m.gate(1, 13, EV_EXIT1)                         # west, back to the village
    m.gate(30, 13, EV_EXIT2)                        # east, into the forest
    m.scatter('f', rng, 14)
    m.scatter('O', rng, 8)
    m.scatter(',', rng, 30)
    m.put(24, 20, 'C')
    m.event(24, 20, EV_TALK1)                       # an empty cave, for flavour
    return m


def build_forest(rng):
    m = Map('T')
    # Carve a winding clearing rather than placing trees: a forest reads as a
    # forest when the *gaps* are the deliberate shape.
    for y in range(MAP_H):
        cx = 16.0 + 7.0 * math.sin(y * 0.28) + 3.0 * math.sin(y * 0.11 + 2.0)
        w = 2.6 + 1.4 * math.sin(y * 0.4)
        for x in range(MAP_W):
            if abs(x - cx) <= w:
                m.put(x, y, '.')
    for x in range(MAP_W):
        cy = 16.0 + 5.0 * math.sin(x * 0.3)
        for y in range(MAP_H):
            if abs(y - cy) <= 2.2:
                m.put(x, y, '.')
    m.border('Y', rng, thick=1.6, wobble=0.8)

    m.rect(13, 14, 19, 20, '.')                     # Patapim's clearing
    m.put(16, 15, 'C')
    m.event(16, 15, EV_BOSS)
    m.put(14, 19, 'W')                              # a spring, before the fight
    m.event(14, 19, EV_SAVE)
    m.road(1, 17, 8, 17)
    m.gate(1, 17, EV_EXIT1)
    m.road(24, 17, 30, 17)
    m.gate(30, 17, EV_EXIT2)
    m.scatter('m', rng, 12)
    m.scatter('b', rng, 10)
    m.scatter(',', rng, 20)
    m.scatter('y', rng, 6)
    return m


def build_shore(rng):
    m = Map('.')
    for y in range(MAP_H):                          # sea to the south-east
        for x in range(MAP_W):
            edge = 9 + 12 * math.sin((x + 4) * 0.09) - (y - 16) * 0.15
            if y > edge + 12:
                m.put(x, y, '~')
            elif y > edge + 10:
                m.put(x, y, 's')
            elif y > edge + 9:
                m.put(x, y, '_')
    m.border('#', rng, thick=1.1, wobble=0.7)
    m.belt('T', rng, depth=1.8, wobble=0.8)

    m.road(1, 9, 30, 9)
    m.gate(1, 9, EV_EXIT1)
    m.road(26, 9, 26, 1)
    m.gate(26, 1, EV_EXIT2)
    m.rect(11, 12, 17, 15, '.')
    m.put(14, 13, 'C')
    m.event(14, 13, EV_BOSS)
    m.put(16, 15, 'W')
    m.event(16, 15, EV_SAVE)
    m.scatter('r', rng, 14)
    m.scatter('O', rng, 10)
    m.scatter('T', rng, 6)
    return m


def build_salt(rng):
    m = Map('x')
    m.border('d', rng, thick=1.6, wobble=1.0)
    for y in range(MAP_H):
        for x in range(MAP_W):
            if m.get(x, y) == 'x' and math.sin(x * 0.4) * math.cos(y * 0.33) > 0.72:
                m.put(x, y, 'd')
    m.road(1, 22, 30, 22)
    m.gate(1, 22, EV_EXIT1)                         # south-west, to the shore
    m.road(28, 22, 28, 3)
    m.gate(28, 3, EV_EXIT2)                         # north-east, to the fortress
    m.rect(11, 8, 19, 15, 'x')
    m.put(15, 11, 'c')
    m.event(15, 11, EV_BOSS)
    m.put(18, 14, 'W')
    m.event(18, 14, EV_SAVE)
    m.scatter('B', rng, 14)
    m.scatter('c', rng, 8)
    m.scatter('y', rng, 6)
    m.scatter('O', rng, 6)
    return m


def build_fortress(rng):
    m = Map('H')
    # Corridors: a grid of rooms with gaps knocked through.
    for ry in range(1, 5):
        for rx in range(1, 5):
            x0, y0 = rx * 6 + 1, ry * 6 + 1
            m.rect(x0, y0, x0 + 4, y0 + 4, 'I')
    for ry in range(1, 5):
        for rx in range(1, 4):
            m.rect(rx * 6 + 5, ry * 6 + 3, rx * 6 + 7, ry * 6 + 3, 'w')
    for rx in range(1, 5):
        for ry in range(1, 4):
            m.rect(rx * 6 + 3, ry * 6 + 5, rx * 6 + 3, ry * 6 + 7, 'w')
    m.rect(1, 26, 30, 30, 'I')
    m.rect(7, 1, 7, 6, 'P')
    m.rect(19, 1, 19, 6, 'P')
    m.put(9, 28, 'F')
    m.put(22, 28, 'F')

    m.rect(13, 7, 19, 12, 'I')
    m.put(16, 9, 'F')
    m.event(16, 9, EV_BOSS)
    m.put(18, 11, 'W')
    m.event(18, 11, EV_SAVE)
    m.gate(3, 28, EV_EXIT1)
    m.put(3, 28, 'I')
    m.gate(28, 8, EV_EXIT2)
    m.put(28, 8, 'I')
    m.scatter('P', rng, 10, over='I')
    return m


def build_hush(rng):
    m = Map('v')
    # Islands of platform in the dark, joined loosely.
    centres = [(6, 26), (12, 22), (17, 26), (22, 20), (16, 16),
               (10, 12), (17, 9), (23, 12), (16, 4)]
    for i, (cx, cy) in enumerate(centres):
        r = 2.6 + (i % 3) * 0.7
        for y in range(MAP_H):
            for x in range(MAP_W):
                if math.hypot(x - cx, (y - cy) * 1.15) <= r:
                    m.put(x, y, 'p')
    for a, b in zip(centres, centres[1:]):
        x, y = a
        while (x, y) != b:
            if x != b[0]:
                x += 1 if b[0] > x else -1
            elif y != b[1]:
                y += 1 if b[1] > y else -1
            m.put(x, y, 'p')
    m.scatter('R', rng, 10, over='v', margin=1)
    m.gate(6, 28, EV_EXIT1)
    m.put(6, 28, 'p')
    m.put(16, 4, 'R')
    m.event(16, 4, EV_BOSS)
    m.put(17, 9, 'W')
    m.event(17, 9, EV_SAVE)
    return m


# ---- region table ------------------------------------------------------
#
# spawn is where the player lands when the region is entered from its first
# exit; the per-exit landing cells are in EXITS below.

REGIONS = [
    # safe: nothing jumps you inside the walls. A town that rolls encounters
    # is a town nobody shops in.
    dict(key='VILLAGE',  name='KAMPUNG SAHUR', build=build_village,
         pals=(NIGHT_GRASS, BUILT), music='TOWN',  backdrop=0, seed=0x1001,
         safe=True),
    dict(key='FIELDS',   name='THE EAST ROAD', build=build_fields,
         pals=(NIGHT_GRASS, BUILT), music='FIELD', backdrop=0, seed=0x1002),
    dict(key='FOREST',   name='HUTAN',         build=build_forest,
         pals=(FOREST_PAL, echo(FOREST_PAL)), music='FOREST', backdrop=1,
         seed=0x1003),
    dict(key='SHORE',    name='PANTAI',        build=build_shore,
         pals=(SHORE_PAL, echo(SHORE_PAL)), music='SHORE', backdrop=2,
         seed=0x1004),
    dict(key='SALT',     name='PADANG GARAM',  build=build_salt,
         pals=(SALT_PAL, echo(SALT_PAL)), music='SALT', backdrop=3,
         seed=0x1005),
    dict(key='FORTRESS', name='LANGIT BESI',   build=build_fortress,
         pals=(IRON_PAL, echo(IRON_PAL)), music='FORTRESS', backdrop=4,
         seed=0x1006),
    dict(key='HUSH',     name='MALAM PANJANG', build=build_hush,
         pals=(HUSH_PAL, echo(HUSH_PAL)), music='HUSH', backdrop=5,
         seed=0x1007),
]

REGION_INDEX = {r['key']: i for i, r in enumerate(REGIONS)}

# Where each exit goes: region key -> exit id -> (dest region, dest x, dest y).
EXITS = {
    'VILLAGE':  {EV_EXIT1: ('FIELDS', 2, 13)},
    'FIELDS':   {EV_EXIT1: ('VILLAGE', 29, 15),
                 EV_EXIT2: ('FOREST', 2, 17)},
    'FOREST':   {EV_EXIT1: ('FIELDS', 29, 13),
                 EV_EXIT2: ('SHORE', 2, 9)},
    'SHORE':    {EV_EXIT1: ('FOREST', 29, 17),
                 EV_EXIT2: ('SALT', 2, 22)},
    'SALT':     {EV_EXIT1: ('SHORE', 25, 2),
                 EV_EXIT2: ('FORTRESS', 4, 28)},
    'FORTRESS': {EV_EXIT1: ('SALT', 27, 4),
                 EV_EXIT2: ('HUSH', 6, 27)},
    'HUSH':     {EV_EXIT1: ('FORTRESS', 27, 8)},
}

SPAWN = ('VILLAGE', 16, 20)


# ---- tile animation ----------------------------------------------------
#
# The liquid painters all take a `phase`, so the same metatile can be cut four
# times with its crests moved along. Animating it costs one VRAM transfer per
# region per few frames -- but only if the characters involved are contiguous,
# because V-blank has room for one small DMA and not for eight scattered ones.
# So the animated characters are reserved at the *head* of the region's pool,
# before anything else is added, and the runtime copies characters
# 0..ANIM_TILES-1 of the region tileset.
#
# 8 characters x 32 bytes = 256 bytes a frame. At the ~2.6 MB/s of a DMA that
# is under 100 us inside a V-blank of over 215 us (cpu-system.md), with the
# OAM copy on channel 7 already done by then.

ANIM_PAINTERS = ('water', 'shallow', 'lantern', 'furnace', 'rift',
                 'mushroom')
ANIM_PHASES = 4
ANIM_MAX = 8


# ---- build -------------------------------------------------------------

class Pool:
    """8x8 dedup, per region."""

    def __init__(self):
        self.index = {}
        self.tiles = []

    def add(self, c):
        key = tuple(tuple(r) for r in c)
        if key not in self.index:
            self.index[key] = len(self.tiles)
            self.tiles.append(c)
        return self.index[key]


def anim_variants(painter_name):
    """How many variants of a painter the map is allowed to use. Animated
    painters are capped: every variant costs four characters out of the
    per-frame transfer budget."""
    nvar = T.PAINTERS[painter_name][1]
    if painter_name in ANIM_PAINTERS:
        return min(nvar, ANIM_MAX // 4)
    return nvar


def cut(px16, ox=0, oy=0):
    out = []
    for cy in (0, 8):
        for cx in (0, 8):
            out.append([[px16[oy + cy + y][ox + cx + x] for x in range(8)]
                        for y in range(8)])
    return out


def build_region(region):
    rng = Rng(region['seed'])
    m = region['build'](rng)
    rows = m.rows()

    pool = Pool()
    variants = {}          # (char, variant) -> (names, palette)
    used = sorted({ch for row in rows for ch in row})

    # Reserve the animated characters first so they land at pool index 0 and
    # upward, contiguous, and record the other three phases of each.
    frames = [[] for _ in range(ANIM_PHASES)]     # phase -> [cell, ...]
    for ch in used:
        if ch in HOUSE_CHARS or ch not in ALPHABET:
            continue
        painter_name, pal, flags = ALPHABET[ch]
        if painter_name not in ANIM_PAINTERS:
            continue
        painter, _ = T.PAINTERS[painter_name]
        for v in range(anim_variants(painter_name)):
            seed = region['seed'] * 7 + ord(ch) * 131 + v * 977
            phases = [cut(painter(Rng(seed), phase=p).px)
                      for p in range(ANIM_PHASES)]
            names = []
            for i, c in enumerate(phases[0]):
                n = pool.add(c)
                names.append(n)
                if n == len(frames[0]):            # a genuinely new character
                    for p in range(ANIM_PHASES):
                        frames[p].append(phases[p][i])
            variants[(ch, v)] = (names, pal)
    nanim = len(frames[0])
    if nanim > ANIM_MAX:
        raise SystemExit("%s wants %d animated characters, V-blank affords %d"
                         % (region['key'], nanim, ANIM_MAX))
    # Past this point an ordinary tile that happens to equal a water tile must
    # get its own character, or it would ripple along with the sea.
    pool.index = {}

    for ch in used:
        if ch in HOUSE_CHARS:
            continue
        if ch not in ALPHABET:
            raise SystemExit("%s uses terrain %r with no painter"
                             % (region['key'], ch))
        painter_name, pal, flags = ALPHABET[ch]
        if painter_name in ANIM_PAINTERS:
            continue                    # already reserved, above
        painter, nvar = T.PAINTERS[painter_name]
        for v in range(nvar):
            c = painter(Rng(region['seed'] * 7 + ord(ch) * 131 + v * 977))
            variants[(ch, v)] = ([pool.add(k) for k in cut(c.px)], pal)

    if any(ch in HOUSE_CHARS for row in rows for ch in row):
        hp = T.house_block(Rng(region['seed'] ^ 0xA5A5))
        for qi, (qx, qy) in enumerate(((0, 0), (16, 0), (0, 16), (16, 16))):
            cells = []
            for cy in (0, 8):
                for cx in (0, 8):
                    cells.append([[hp[qy + cy + y][qx + cx + x]
                                   for x in range(8)] for y in range(8)])
            variants[(HOUSE_CHARS[qi], 0)] = ([pool.add(k) for k in cells], 1)

    tilemap = [0] * (TILE_MAP_W * TILE_MAP_H)
    collide = bytearray(MAP_W * MAP_H)
    vr = Rng(region['seed'] ^ 0x5EED)

    for my in range(MAP_H):
        for mx in range(MAP_W):
            ch = rows[my][mx]
            nvar = 1 if ch in HOUSE_CHARS \
                else anim_variants(ALPHABET[ch][0])
            key = (ch, vr.next() % nvar)
            names, pal = variants[key]
            for i, name in enumerate(names):
                tx, ty = mx * 2 + (i & 1), my * 2 + (i >> 1)
                tilemap[ty * TILE_MAP_W + tx] = g.map_entry(name, pal=pal)

            flags = BLOCK if ch in HOUSE_CHARS else ALPHABET[ch][2]
            if region.get('safe'):
                flags &= ~ENC
            ev = m.events.get((mx, my), 0)
            if ev:
                flags |= TRIG
            collide[my * MAP_W + mx] = flags | (ev << 4)

    if len(pool.tiles) > 256:
        raise SystemExit("%s needs %d characters, a page holds 256"
                         % (region['key'], len(pool.tiles)))

    sheet = g.Sheet(256)
    for i, c in enumerate(pool.tiles):
        ox, oy = sheet.origin(i)
        for y in range(8):
            for x in range(8):
                sheet.set(ox + x, oy + y, c[y][x])

    # A 64x64 tilemap is four 32x32 screens stored consecutively (A-14).
    quads = []
    for qy in (0, 32):
        for qx in (0, 32):
            for row in range(32):
                base = (qy + row) * TILE_MAP_W + qx
                quads.extend(tilemap[base:base + 32])

    anim = b''.join(g.tile_bin(c) for phase in frames for c in phase)
    return sheet, quads, collide, len(pool.tiles), rows, anim, nanim


def generate_world():
    total = 0
    report = []
    anims = []
    for r in REGIONS:
        sheet, quads, collide, ntiles, rows, anim, nanim = build_region(r)
        key = r['key'].lower()
        anims.append(nanim)
        total += g.write('area_%s.anm' % key, anim if anim else bytes(32))
        total += g.write('area_%s.pic' % key, sheet.to_pic())
        total += g.write('area_%s.map' % key, g.map_bin(quads))
        total += g.write('area_%s.col' % key, bytes(collide))
        total += g.write('area_%s.pal' % key,
                         g.palette_bin(r['pals'][0]) + g.palette_bin(r['pals'][1]))
        walkable = sum(1 for row in rows for ch in row
                       if not (ALPHABET.get(ch, ('', 0, BLOCK))[2] & BLOCK)
                       and ch not in HOUSE_CHARS)
        report.append((r['key'], ntiles, walkable, nanim))

    with open('src/worldmap.h', 'w') as f:
        f.write("/* Generated by gen_world.py -- do not edit. */\n"
                "#ifndef WORLDMAP_H\n#define WORLDMAP_H\n\n")
        f.write("#define MAP_W %d\n#define MAP_H %d\n\n" % (MAP_W, MAP_H))
        f.write("#define COL_BLOCK 0x%02X\n#define COL_ENC   0x%02X\n"
                "#define COL_TRIG  0x%02X\n#define COL_EVENT(c) ((c) >> 4)\n\n"
                % (BLOCK, ENC, TRIG))
        for i, r in enumerate(REGIONS):
            f.write("#define AREA_%-9s %d\n" % (r['key'], i))
        f.write("#define AREA_COUNT     %d\n\n" % len(REGIONS))
        for n, v in (('EXIT1', EV_EXIT1), ('EXIT2', EV_EXIT2),
                     ('EXIT3', EV_EXIT3), ('EXIT4', EV_EXIT4),
                     ('TALK1', EV_TALK1), ('TALK2', EV_TALK2),
                     ('TALK3', EV_TALK3), ('TALK4', EV_TALK4),
                     ('INN', EV_INN), ('SHOP', EV_SHOP), ('SAVE', EV_SAVE),
                     ('BOSS', EV_BOSS), ('STORY', EV_STORY)):
            f.write("#define EV_%-6s %d\n" % (n, v))
        f.write("\n#define SPAWN_AREA AREA_%s\n#define SPAWN_X %d\n"
                "#define SPAWN_Y %d\n\n" % (SPAWN[0], SPAWN[1], SPAWN[2]))

        # Exit destinations, flat so tcc never sees a 2-D const array.
        f.write("/* Exit id 1-4 of area a is at index a * 4 + (id - 1). */\n")
        for arr, idx in (('areaExitTo', 0), ('areaExitX', 1), ('areaExitY', 2)):
            vals = []
            for r in REGIONS:
                ex = EXITS.get(r['key'], {})
                for e in (EV_EXIT1, EV_EXIT2, EV_EXIT3, EV_EXIT4):
                    if e in ex:
                        dest, dx, dy = ex[e]
                        vals.append((REGION_INDEX[dest], dx, dy)[idx])
                    else:
                        vals.append(255 if idx == 0 else 0)
            f.write("static const u8 %s[AREA_COUNT * 4] = {\n" % arr)
            for i in range(0, len(vals), 8):
                f.write("    " + ", ".join("%3d" % v for v in vals[i:i + 8])
                        + ",\n")
            f.write("};\n\n")
        # Asset accessors. A switch rather than a table of pointers: tcc will
        # build a `const u8 *const[]` but the relocations it emits for one in a
        # LoROM bank are not worth the argument.
        f.write("/* Region assets. Defined in worlddata.asm, which this file\n"
                " * also generates, so a region cannot exist in one and not the\n"
                " * other. */\n")
        for r in REGIONS:
            k = r['key'].lower()
            for part in ('pic', 'map', 'col', 'pal', 'anm'):
                f.write("extern char area_%s_%s;\n" % (k, part))
        f.write("\n")
        for part in ('pic', 'map', 'col', 'pal', 'anm'):
            f.write("static u8 *area%s(u8 a) {\n    switch (a) {\n"
                    % part.capitalize())
            for i, r in enumerate(REGIONS[:-1]):
                f.write("    case AREA_%s:\n        return (u8 *)&area_%s_%s;\n"
                        % (r['key'], r['key'].lower(), part))
            last = REGIONS[-1]
            f.write("    default:\n        return (u8 *)&area_%s_%s;\n"
                    % (last['key'].lower(), part))
            f.write("    }\n}\n\n")

        f.write("/* Characters 0..areaAnimTiles-1 of a region's tileset are\n"
                " * rewritten from areaAnm() every few frames -- see fieldAnimate.\n"
                " * Zero means the region has no moving water. */\n")
        f.write("static const u8 areaAnimTiles[AREA_COUNT] = {\n    ")
        f.write(", ".join(str(n) for n in anims))
        f.write("\n};\n\n")
        f.write("static const u8 areaMusic[AREA_COUNT] = {\n    ")
        f.write(", ".join("BGM_" + r['music'] for r in REGIONS))
        f.write("\n};\n\n")
        f.write("static const u8 areaBackdrop[AREA_COUNT] = {\n    ")
        f.write(", ".join(str(r['backdrop']) for r in REGIONS))
        f.write("\n};\n\n")
        f.write("#endif\n")

    # The .incbin fragment, so adding a region does not mean editing assembly.
    with open('worlddata.asm', 'w') as f:
        f.write("; Generated by gen_world.py -- do not edit.\n"
                ";\n"
                "; A standalone unit, not an .include: snes_rules globs every\n"
                "; root *.asm into OFILES, so a file that is also included\n"
                "; from data.asm would have its labels linked twice.\n"
                ".include \"hdr.asm\"\n"
                ";\n"
                "; One section per region: a tileset and a tilemap are 8KB each\n"
                "; and a WLA section cannot straddle a bank boundary in 32KB\n"
                "; LoROM, so they are kept apart region by region.\n\n")
        for r in REGIONS:
            k = r['key'].lower()
            f.write('.section ".rodata_%s" superfree\n' % k)
            for part in ('pic', 'map', 'col', 'pal', 'anm'):
                f.write('area_%s_%s: .incbin "area_%s.%s"\n' % (k, part, k, part))
            f.write('.ends\n\n')

    print("world: %d bytes across %d regions" % (total, len(REGIONS)))
    for key, ntiles, walk, na in report:
        print("   %-9s %3d characters, %4d walkable cells, %d animated"
              % (key, ntiles, walk, na))


if __name__ == '__main__':
    generate_world()
