#!/usr/bin/env python3
"""Metatile painters, shared by every region.

---- the semantic palette --------------------------------------------------

Every region's palette 0 follows one fixed layout, so a painter can draw "a
tree" without knowing whether it is a jungle tree, a salt-flat husk or an iron
pylon. Repainting a region is then a matter of swapping sixteen colours rather
than redrawing thirty metatiles:

    0  transparent (terrain art never uses it -- colour 0 is the backdrop)
    1  outline / darkest
    2  ground dark          3  ground mid        4  ground light
    5  feature dark         6  feature mid       7  feature light
    8  liquid dark          9  liquid mid       10  liquid light
    11 stone dark          12  stone mid        13  stone light
    14 accent (path, sand, rust, bone)
    15 bright (highlight, star, lamp)

Palette 1 is the region's own: buildings, machinery, whatever that place has
that nowhere else does.

---- why everything is 16x16 -----------------------------------------------

A metatile is one walking step, one collision cell and one encounter cell. The
PPU is handed 8x8 characters and a 64x64 tilemap; the split happens in
gen_world.py and neither the painters nor the C ever see it.
"""
import math

from snesgfx import Canvas

# semantic slots
TRANSP = 0
INK = 1
GND_D, GND_M, GND_L = 2, 3, 4
FEA_D, FEA_M, FEA_L = 5, 6, 7
LIQ_D, LIQ_M, LIQ_L = 8, 9, 10
STO_D, STO_M, STO_L = 11, 12, 13
ACCENT = 14
BRIGHT = 15

CELL = 16


class Rng:
    """Deterministic. Texture must be identical on every run or the tile dedup
    pool -- and with it every name in every tilemap -- reshuffles."""

    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s >> 16

    def chance(self, pct):
        return (self.next() % 100) < pct

    def pick(self, seq):
        return seq[self.next() % len(seq)]

    def span(self, lo, hi):
        return lo + self.next() % (hi - lo + 1)


def cell(fill=GND_M):
    c = Canvas(CELL, CELL)
    c.rect(0, 0, CELL, CELL, fill)
    return c


# ---- ground ------------------------------------------------------------

def ground(rng, dark=6, light=8):
    """The base texture under everything. Speckle rather than flat: a flat
    16x16 fill repeated across a 512-dot field reads as a bug."""
    c = cell(GND_M)
    for y in range(CELL):
        for x in range(CELL):
            r = rng.next() % 100
            if r < dark:
                c.set(x, y, GND_D)
            elif r < dark + light:
                c.set(x, y, GND_L)
    return c


def tufted(rng):
    """Ground with a few blades standing up -- grass, or whatever the region
    grows instead."""
    c = ground(rng)
    for _ in range(rng.span(2, 4)):
        x, y = rng.span(1, 14), rng.span(2, 13)
        c.set(x, y, FEA_M)
        c.set(x, y - 1, FEA_L)
        c.set(x + 1, y, FEA_D)
    return c


def path(rng):
    c = cell(ACCENT)
    for y in range(CELL):
        for x in range(CELL):
            if rng.chance(7):
                c.set(x, y, STO_L)
            elif rng.chance(5):
                c.set(x, y, GND_D)
    return c


def flowers(rng):
    c = tufted(rng)
    for _ in range(rng.span(3, 5)):
        x, y = rng.span(2, 13), rng.span(2, 13)
        c.set(x, y, BRIGHT)
        c.set(x - 1, y, FEA_L)
        c.set(x + 1, y, FEA_L)
        c.set(x, y - 1, FEA_L)
        c.set(x, y + 1, FEA_M)
    return c


# ---- vegetation --------------------------------------------------------

def tree(rng, tall=False):
    c = ground(rng)
    cx = 8
    top = 1 if tall else 2
    c.line(cx - 1, 10, cx - 1, 15, INK, 3)          # trunk, wide enough to see
    c.line(cx + 1, 10, cx + 1, 15, STO_D, 1)
    c.ellipse(cx, top + 5, 7.2, 5.6, INK)           # a dark rim under the leaves
    c.ellipse(cx, top + 5, 6.4, 4.9, FEA_D)
    c.ellipse(cx, top + 4, 5.4, 4.0, FEA_M)
    c.ellipse(cx - 1, top + 3, 3.6, 2.6, FEA_L)
    for _ in range(6):                              # leaf breakup
        c.set(rng.span(3, 12), rng.span(top + 1, top + 8), FEA_D)
    return c


def pine(rng):
    c = ground(rng)
    c.line(7, 11, 7, 15, INK, 2)
    for i, w in enumerate((6.5, 5.0, 3.4)):
        y = 11 - i * 3
        c.tri((int(8 - w), y), (8, y - 5), (int(8 + w), y), FEA_D)
        c.tri((int(8 - w + 1), y - 1), (8, y - 4), (int(8 + w - 1), y - 1), FEA_M)
    c.tri((6, 4), (8, 0), (10, 4), FEA_L)
    return c


def deadtree(rng):
    c = ground(rng)
    c.line(8, 15, 8, 5, STO_D, 2)
    c.line(8, 9, 3, 4, STO_D, 1)
    c.line(8, 8, 13, 3, STO_D, 1)
    c.line(8, 6, 5, 1, STO_M, 1)
    c.line(4, 4, 2, 2, STO_M, 1)
    return c


def bush(rng):
    c = ground(rng)
    c.ellipse(8, 10, 6.0, 4.5, FEA_D)
    c.ellipse(7, 9, 4.4, 3.2, FEA_M)
    c.ellipse(6, 8, 2.4, 1.8, FEA_L)
    for _ in range(4):
        c.set(rng.span(3, 12), rng.span(6, 13), FEA_D)
    return c


def reeds(rng):
    c = ground(rng)
    for x in range(1, 15, 3):
        h = rng.span(6, 11)
        c.line(x, 15, x + rng.span(-1, 1), 15 - h, FEA_M, 1)
        c.set(x, 15 - h, FEA_L)
    return c


def cactus(rng):
    c = ground(rng)
    c.ellipse(8, 10, 3.0, 6.0, FEA_M)
    c.ellipse(4, 9, 1.8, 3.0, FEA_M)
    c.ellipse(12, 8, 1.8, 3.0, FEA_M)
    c.ellipse(7, 9, 1.6, 4.6, FEA_L)
    for y in range(5, 16, 3):
        c.set(5, y, BRIGHT)
        c.set(11, y, BRIGHT)
    return c


def mushroom(rng, phase=0):
    """Hutan's caps. The spots take it in turns to be lit, so the forest floor
    reads as breathing rather than blinking."""
    c = ground(rng)
    c.rect(7, 9, 3, 6, STO_L)
    c.ellipse(8, 8, 5.5, 3.2, FEA_D)
    c.ellipse(8, 7, 4.6, 2.4, FEA_M)
    glow = (0.0, 1.4, 2.3, 1.4)[phase & 3]
    if glow:
        c.ellipse(8, 7, glow * 1.6, glow * 0.9, FEA_L)
    spots = ((6, 6), (10, 7), (8, 5), (9, 9))
    for i, (x, y) in enumerate(spots):
        c.set(x, y, BRIGHT if (i - phase) % 4 < 2 else FEA_L)
    return c


# ---- water -------------------------------------------------------------

def water(rng, phase=0):
    """Deep water. `phase` shifts the crests, which is what the animated
    variants are cut from."""
    c = cell(LIQ_D)
    for y in range(CELL):
        for x in range(CELL):
            v = math.sin((x + phase * 2) * 0.7 + y * 1.1) \
                + math.sin((x - phase) * 0.31 + y * 0.5)
            if v > 1.15:
                c.set(x, y, LIQ_L)
            elif v > 0.35:
                c.set(x, y, LIQ_M)
    return c


def shallow(rng, phase=0):
    c = water(rng, phase)
    for y in range(CELL):
        for x in range(CELL):
            if c.get(x, y) == LIQ_D and rng.chance(18):
                c.set(x, y, LIQ_M)
    return c


def shore(rng, phase=0):
    """Sand at the top, surf at the bottom -- the coastline metatile."""
    c = cell(ACCENT)
    for y in range(CELL):
        for x in range(CELL):
            if rng.chance(9):
                c.set(x, y, GND_D)
    edge = 7
    for x in range(CELL):
        h = edge + int(1.6 * math.sin(x * 0.55 + phase))
        for y in range(h, CELL):
            c.set(x, y, LIQ_M if y < h + 2 else LIQ_D)
        c.set(x, h, BRIGHT)
        c.set(x, h + 1, LIQ_L)
    return c


def bridge(rng):
    c = water(rng)
    c.rect(0, 2, CELL, 12, ACCENT)
    c.rect(0, 2, CELL, 1, INK)
    c.rect(0, 13, CELL, 1, INK)
    for x in range(0, CELL, 3):
        c.line(x, 3, x, 12, STO_D, 1)
    return c


# ---- stone -------------------------------------------------------------

def rock(rng):
    c = ground(rng)
    c.ellipse(8, 10, 6.0, 4.6, STO_D)
    c.ellipse(7, 9, 4.8, 3.4, STO_M)
    c.ellipse(6, 8, 2.6, 1.8, STO_L)
    return c


def mountain(rng):
    c = ground(rng)
    c.tri((0, 15), (7, 1), (15, 15), STO_D)
    c.tri((3, 15), (7, 3), (12, 15), STO_M)
    c.tri((5, 10), (7, 3), (10, 10), STO_L)
    c.tri((6, 7), (7, 3), (9, 7), BRIGHT)
    for _ in range(5):
        c.set(rng.span(1, 14), rng.span(8, 15), STO_D)
    return c


def cliff(rng):
    """A wall face: flat top, stratified drop."""
    c = cell(STO_M)
    for y in range(CELL):
        for x in range(CELL):
            if rng.chance(12):
                c.set(x, y, STO_D)
            elif rng.chance(10):
                c.set(x, y, STO_L)
    for y in (4, 9, 13):
        for x in range(CELL):
            c.set(x, y + (x % 3 == 0), STO_D)
    return c


def stonefloor(rng):
    c = cell(STO_M)
    for y in range(0, CELL, 4):
        for x in range(CELL):
            c.set(x, y, STO_D)
    for x in range(0, CELL, 5):
        for y in range(CELL):
            c.set(x + (y // 4) * 2 % 5, y, STO_D)
    for _ in range(6):
        c.set(rng.span(0, 15), rng.span(0, 15), STO_L)
    return c


def crack(rng):
    """Dried salt: pale plates with dark seams."""
    c = cell(GND_L)
    for _ in range(3):
        x, y = rng.span(0, 15), rng.span(0, 15)
        for _ in range(rng.span(6, 12)):
            c.set(x, y, GND_D)
            x = max(0, min(15, x + rng.span(-1, 1)))
            y = max(0, min(15, y + rng.span(-1, 1)))
    for _ in range(10):
        c.set(rng.span(0, 15), rng.span(0, 15), BRIGHT)
    return c


def dune(rng):
    c = cell(GND_M)
    for x in range(CELL):
        h = 6 + int(3.5 * math.sin(x * 0.4))
        for y in range(CELL):
            c.set(x, y, GND_L if y < h else GND_M)
        c.set(x, h, BRIGHT)
        c.set(x, h + 1, GND_D)
    for _ in range(8):
        c.set(rng.span(0, 15), rng.span(0, 15), ACCENT)
    return c


def bones(rng):
    c = ground(rng)
    c.ellipse(8, 11, 5.5, 2.2, BRIGHT)
    for i in range(4):
        c.line(4 + i * 3, 9, 4 + i * 3, 13, GND_L, 1)
    c.disc(4, 6, 2.2, BRIGHT)
    c.set(4, 6, INK)
    return c


# ---- built -------------------------------------------------------------

def fence(rng):
    c = ground(rng)
    for x in (2, 13):
        c.line(x, 4, x, 14, STO_D, 2)
    for y in (6, 10):
        c.rect(0, y, CELL, 2, ACCENT)
        c.rect(0, y, CELL, 1, STO_D)
    return c


def cavemouth(rng):
    c = cliff(rng)
    c.ellipse(8, 9, 6.5, 6.5, STO_D)
    c.ellipse(8, 10, 5.0, 5.5, INK)
    c.rect(3, 12, 10, 4, INK)
    return c


def lantern(rng, phase=0):
    """A village lamp. `phase` breathes the flame -- the glass keeps its
    outline and only the body of the light moves, which is what makes four
    frames read as a flicker instead of a blink."""
    c = ground(rng)
    c.line(8, 15, 8, 6, STO_D, 2)
    c.rect(5, 2, 7, 5, INK)
    grow = (-1, 0, 1, 0)[phase & 3]
    c.rect(6, 3, 5, 3, ACCENT)
    c.rect(6, 3 + (grow < 0), 5, 3 + grow - (grow < 0), BRIGHT)
    c.rect(4, 1, 9, 1, STO_M)
    return c


def well(rng):
    c = stonefloor(rng)
    c.ellipse(8, 10, 6.5, 4.5, STO_D)
    c.ellipse(8, 10, 5.0, 3.2, INK)
    c.ellipse(8, 9, 4.0, 2.2, LIQ_D)
    c.line(3, 8, 3, 1, STO_D, 2)
    c.line(13, 8, 13, 1, STO_D, 2)
    c.rect(2, 0, 13, 2, ACCENT)
    return c


# ---- machinery (the fortress) ------------------------------------------

def ironfloor(rng):
    c = cell(STO_M)
    c.rect(0, 0, CELL, 1, STO_D)
    c.rect(0, 0, 1, CELL, STO_D)
    c.rect(0, 15, CELL, 1, INK)
    c.rect(15, 0, 1, CELL, INK)
    for y in (3, 12):
        for x in (3, 12):
            c.set(x, y, STO_L)
            c.set(x + 1, y, STO_D)
    for _ in range(5):
        c.set(rng.span(2, 13), rng.span(2, 13), STO_L)
    return c


def ironwall(rng):
    c = cell(STO_D)
    for y in range(0, CELL, 5):
        c.rect(0, y, CELL, 1, INK)
        c.rect(0, y + 1, CELL, 1, STO_M)
    for x in range(2, CELL, 6):
        c.set(x, 3, ACCENT)
        c.set(x, 8, ACCENT)
        c.set(x, 13, ACCENT)
    return c


def pipe(rng):
    c = ironfloor(rng)
    c.rect(4, 0, 8, CELL, STO_D)
    c.rect(5, 0, 6, CELL, STO_M)
    c.rect(6, 0, 2, CELL, STO_L)
    for y in (2, 9):
        c.rect(3, y, 10, 2, STO_D)
    return c


def catwalk(rng):
    c = cell(INK)
    c.rect(0, 3, CELL, 10, STO_D)
    for x in range(1, CELL, 3):
        c.rect(x, 4, 2, 8, STO_M)
    c.rect(0, 3, CELL, 1, STO_L)
    c.rect(0, 12, CELL, 1, STO_L)
    return c


def furnace(rng, phase=0):
    """The forge mouths of Langit Besi. The core swells and falls back."""
    c = ironwall(rng)
    k = (0.0, 0.55, 0.9, 0.45)[phase & 3]
    c.ellipse(8, 9, 5.5, 4.5, INK)
    c.ellipse(8, 9, 4.2 + k * 0.5, 3.4 + k * 0.4, ACCENT)
    c.ellipse(8, 10 - k * 0.5, 2.8 + k, 2.2 + k * 0.8, BRIGHT)
    return c


# ---- the void ----------------------------------------------------------

def voidcell(rng):
    c = cell(INK)
    for _ in range(rng.span(0, 3)):
        c.set(rng.span(0, 15), rng.span(0, 15), BRIGHT if rng.chance(40)
              else STO_M)
    return c


def platform(rng):
    c = voidcell(rng)
    c.rect(0, 4, CELL, 9, STO_D)
    c.rect(0, 4, CELL, 1, STO_L)
    c.rect(0, 12, CELL, 1, INK)
    for x in range(1, CELL, 4):
        c.set(x, 7, STO_M)
        c.set(x + 2, 10, STO_M)
    return c


def rift(rng, phase=0):
    """A tear in the dark, for the last region's impassable edges. `phase`
    walks the tear's waist down its own length, so the crack looks like it is
    being pulled open rather than flashing."""
    c = voidcell(rng)
    for y in range(CELL):
        w = 2 + int(2.5 * math.sin(y * 0.5 + phase * 0.9))
        for x in range(8 - w, 8 + w):
            c.set(x, y, FEA_D if abs(x - 8) > 1 else FEA_L)
    return c


# ---- the house, a 32x32 block cut into four metatiles -------------------

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


def house_block(rng, ground_slots=(13, 14, 15)):
    """The 32x32 house on palette 1. Its '.' cells are ground, not
    transparency: colour 0 of a BG palette is the backdrop showing through, and
    would ring every roof in black."""
    px = [[0] * 32 for _ in range(32)]
    for y in range(32):
        for x in range(32):
            ch = HOUSE[y][x]
            if ch == '.':
                r = rng.next() % 100
                px[y][x] = (ground_slots[0] if r < 8
                            else (ground_slots[2] if r < 14 else ground_slots[1]))
            else:
                px[y][x] = int(ch, 16)
    return px


# ---- registry ----------------------------------------------------------
#
# Name -> (painter, how many variants to cut). Variants exist so a wide field
# does not visibly repeat; the 8x8 dedup pass collapses whatever they share.

PAINTERS = {
    'ground':     (ground, 6),
    'tufted':     (tufted, 4),
    'path':       (path, 3),
    'flowers':    (flowers, 3),
    'tree':       (tree, 3),
    'pine':       (pine, 2),
    'deadtree':   (deadtree, 2),
    'bush':       (bush, 2),
    'reeds':      (reeds, 2),
    'cactus':     (cactus, 2),
    'mushroom':   (mushroom, 2),
    'water':      (water, 1),
    'shallow':    (shallow, 1),
    'shore':      (shore, 1),
    'bridge':     (bridge, 1),
    'rock':       (rock, 2),
    'mountain':   (mountain, 3),
    'cliff':      (cliff, 2),
    'stonefloor': (stonefloor, 2),
    'crack':      (crack, 4),
    'dune':       (dune, 2),
    'bones':      (bones, 2),
    'fence':      (fence, 1),
    'cavemouth':  (cavemouth, 1),
    'lantern':    (lantern, 1),
    'well':       (well, 1),
    'ironfloor':  (ironfloor, 3),
    'ironwall':   (ironwall, 2),
    'pipe':       (pipe, 1),
    'catwalk':    (catwalk, 1),
    'furnace':    (furnace, 1),
    'void':       (voidcell, 4),
    'platform':   (platform, 2),
    'rift':       (rift, 1),
}
