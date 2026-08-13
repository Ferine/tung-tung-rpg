#!/usr/bin/env python3
"""The OBJ sheet: field hero, three party battlers, four Sleepers, the boss.

---- why the sheet is cut the way it is -------------------------------------

A large OBJ takes its cells row-wise from the 16-character page
(ppu-graphics.md A-4: "NAME 33 -> 33,34,35,36 / 43,44,45,46 / 53-56 / 63-66"),
so a 32x32 sprite is a 4x4 block of tiles on a 16-wide sheet and a 64x64 one is
an 8x8 block. Every sprite below is therefore placed at a name whose column
leaves room for its block, and those names are exported to src/sprmap.h.

---- and why there are only two sizes ---------------------------------------

$2101 offers exactly two OBJ sizes per frame, and the game wants four: 16x16
walking, 32x32 battlers, 64x64 boss, 8x8 numerals. The field runs
OBJ_SIZE16_L32 and battle runs OBJ_SIZE32_L64; the numerals and the menu cursor
are not sprites at all, they are drawn on the BG2 text layer, which costs
nothing because that layer is already there and already sits above the OBJs.
"""
import math

import snesgfx as g
from snesgfx import Canvas
from terrain import Rng

SHEET_TILES = 384                # 24 rows of 16

# ---- palettes -----------------------------------------------------------

P_TUNG, P_TRALA, P_LIRILI, P_ENEMY, P_BOSS, P_PATAPIM, P_FX, P_ENEMY2 = \
    0, 1, 2, 3, 4, 5, 6, 7

PALS = [None] * 8

PALS[P_TUNG] = [
    (0, 0, 0),          # 0  transparent
    (24, 16, 8),        # 1  outline
    (92, 56, 28),       # 2  wood dark
    (140, 92, 44),      # 3  wood mid
    (188, 136, 76),     # 4  wood light
    (232, 192, 132),    # 5  wood highlight
    (248, 248, 248),    # 6  eye white
    (16, 16, 24),       # 7  pupil
    (160, 108, 60),     # 8  bat
    (216, 168, 108),    # 9  bat highlight
    (200, 48, 40),      # 10 sash / brow
    (128, 24, 24),      # 11 sash dark
    (120, 120, 128),    # 12 metal
    (184, 184, 192),    # 13 metal light
    (56, 32, 16),       # 14 deep shadow
    (255, 255, 255),    # 15 specular
]

PALS[P_TRALA] = [
    (0, 0, 0),
    (12, 20, 40),       # 1  outline
    (28, 56, 108),      # 2  shark dark
    (52, 96, 168),      # 3  shark mid
    (96, 144, 216),     # 4  shark light
    (200, 216, 240),    # 5  belly
    (248, 248, 255),    # 6  white
    (16, 16, 24),       # 7  pupil
    (32, 72, 200),      # 8  sneaker
    (240, 240, 248),    # 9  sneaker white
    (176, 48, 56),      # 10 gums
    (96, 96, 112),      # 11 sole
    (144, 176, 224),    # 12 fin light
    (20, 36, 72),       # 13 deep shadow
    (248, 216, 72),     # 14 swoosh
    (255, 255, 255),    # 15 specular
]

PALS[P_LIRILI] = [
    (0, 0, 0),
    (16, 32, 16),       # 1  outline
    (40, 92, 44),       # 2  cactus dark
    (68, 140, 68),      # 3  cactus mid
    (108, 184, 100),    # 4  cactus light
    (216, 232, 168),    # 5  spines
    (96, 96, 112),      # 6  elephant dark
    (148, 148, 164),    # 7  elephant mid
    (196, 196, 208),    # 8  elephant light
    (140, 96, 48),      # 9  sandal
    (232, 136, 184),    # 10 flower
    (248, 248, 248),    # 11 white
    (16, 16, 24),       # 12 pupil
    (28, 60, 32),       # 13 deep shadow
    (240, 228, 192),    # 14 tusk
    (255, 255, 255),    # 15 specular
]

# One palette serves all four Sleepers: they are variations on the same
# nocturnal pastel, and spending a second OBJ palette on them would cost the
# boss its own.
PALS[P_ENEMY] = [
    (0, 0, 0),
    (24, 16, 40),       # 1  outline
    (72, 48, 112),      # 2  purple dark
    (116, 84, 168),     # 3  purple mid
    (164, 132, 216),    # 4  purple light
    (224, 176, 232),    # 5  pink
    (248, 248, 255),    # 6  white / pillow
    (16, 16, 24),       # 7  pupil
    (216, 208, 176),    # 8  linen
    (176, 160, 128),    # 9  linen shadow
    (88, 88, 104),      # 10 grey
    (248, 216, 96),     # 11 gold
    (216, 72, 88),      # 12 red
    (40, 56, 120),      # 13 night blue
    (96, 120, 200),     # 14 night blue light
    (255, 255, 255),    # 15 specular
]

PALS[P_BOSS] = [
    (0, 0, 0),
    (16, 24, 16),       # 1  outline
    (44, 84, 44),       # 2  croc dark
    (76, 132, 60),      # 3  croc mid
    (116, 176, 84),     # 4  croc light
    (208, 216, 152),    # 5  belly
    (248, 248, 248),    # 6  teeth
    (16, 16, 24),       # 7  pupil
    (72, 76, 88),       # 8  metal dark
    (124, 132, 148),    # 9  metal mid
    (184, 192, 208),    # 10 metal light
    (200, 48, 40),      # 11 red
    (240, 152, 48),     # 12 orange
    (56, 48, 40),       # 13 bomb
    (248, 216, 72),     # 14 yellow
    (255, 255, 255),    # 15 specular
]

PALS[P_FX] = [
    (0, 0, 0),
    (255, 255, 255),
    (248, 232, 160),
    (248, 184, 72),
    (240, 96, 48),
    (200, 48, 40),
    (168, 216, 248),
    (72, 152, 240),
    (40, 72, 176),
    (184, 248, 184),
    (72, 200, 96),
    (232, 176, 248),
    (152, 88, 216),
    (128, 128, 144),
    (48, 48, 64),
    (16, 16, 24),
]


# Patapim is bark and moss: a walking tree needs to read as neither the forest
# behind him nor the Sleepers beside him.
PALS[P_PATAPIM] = [
    (0, 0, 0),
    (18, 16, 12),       # 1  outline
    (58, 44, 30),       # 2  bark dark
    (92, 70, 44),       # 3  bark mid
    (132, 104, 66),     # 4  bark light
    (26, 56, 34),       # 5  moss dark
    (44, 92, 50),       # 6  moss mid
    (74, 136, 72),      # 7  moss light
    (216, 208, 176),    # 8  eye
    (24, 20, 16),       # 9  pupil
    (168, 140, 90),     # 10 grain
    (96, 96, 104),      # 11 stone
    (150, 150, 160),    # 12 stone light
    (52, 40, 26),       # 13 deep shadow
    (200, 176, 120),    # 14 highlight
    (248, 240, 216),    # 15 specular
]

# A second enemy palette: cold machine colours for the fortress, so the
# Sleepers and the things guarding them are not the same purple.
PALS[P_ENEMY2] = [
    (0, 0, 0),
    (14, 16, 22),
    (48, 52, 64), (76, 84, 100), (112, 124, 146),
    (140, 60, 40), (196, 96, 52), (240, 156, 72),
    (16, 16, 24), (216, 224, 240), (96, 108, 128),
    (248, 216, 96), (216, 72, 88), (56, 140, 160),
    (168, 180, 200), (255, 255, 255),
]


# ---- Tung Tung Sahur ----------------------------------------------------
#
# A kentongan -- the hollow wooden slit drum beaten to wake a village for the
# pre-dawn meal -- with eyes, legs, and a bat. Party sprites face left because
# that is where the enemies are.

def _bat(c, x0, y0, x1, y1):
    """A tapered bat: thin at the grip, fat at the business end.

    Drawn heavy on purpose -- at 32x32 a two-dot stick disappears into the
    outline pass and the character stops reading as "wooden thing with a bat".
    """
    steps = 20
    for i in range(steps + 1):
        t = i / float(steps)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        r = 1.2 + 2.3 * t
        c.disc(x, y, r, 8)
    c.disc(x1, y1, 3.4, 8)
    c.disc(x1 - (x1 - x0) * 0.06, y1 - (y1 - y0) * 0.06, 1.8, 9)
    c.disc(x0, y0, 1.4, 2)          # grip


def draw_tung(pose):
    c = Canvas(32, 32)
    lean = -2 if pose == 'attack' else 0

    # legs first, so the body overlaps them
    c.rect(12 + lean, 26, 3, 5, 2)
    c.rect(18 + lean, 26, 3, 5, 2)
    c.rect(11 + lean, 30, 5, 2, 14)
    c.rect(17 + lean, 30, 5, 2, 14)

    # body: a hollow log
    c.rect(10 + lean, 7, 13, 19, 3)
    c.ellipse(16.5 + lean, 7, 6.5, 2.6, 4)
    c.ellipse(16.5 + lean, 25.5, 6.5, 2.4, 2)
    c.line(12 + lean, 9, 12 + lean, 24, 2)      # grain
    c.line(21 + lean, 9, 21 + lean, 24, 2)
    c.rect(12 + lean, 19, 10, 3, 14)            # the slit
    c.rect(12 + lean, 19, 10, 1, 2)

    # face
    c.disc(13.5 + lean, 12.5, 3.3, 6)
    c.disc(20.0 + lean, 12.5, 3.3, 6)
    c.disc(12.4 + lean, 12.5, 1.5, 7)           # looking left, at the enemy
    c.disc(18.9 + lean, 12.5, 1.5, 7)
    c.line(10 + lean, 8, 16 + lean, 10, 10, 2)  # brows: permanently unimpressed
    c.line(23 + lean, 8, 18 + lean, 10, 10, 2)

    if pose == 'attack':
        c.line(10 + lean, 16, 3, 11, 2, 2)      # near arm swung through
        c.line(22 + lean, 15, 14, 9, 2, 2)
        _bat(c, 15, 10, 4, 5)
    else:
        c.line(10 + lean, 17, 4, 20, 2, 2)      # near arm loose
        c.line(22 + lean, 16, 26, 11, 2, 2)
        _bat(c, 25, 12, 28, 4)

    c.outline()
    return c


# ---- Tralalero Tralala --------------------------------------------------
#
# Three-shoed shark. The sneakers are the joke, so they get the detail budget.

def _sneaker(c, x, y):
    c.rect(x, y + 2, 7, 3, 9)
    c.rect(x, y + 4, 8, 2, 11)
    c.ellipse(x + 1.5, y + 2.5, 2.5, 2.0, 8)
    c.line(x + 1, y + 3, x + 5, y + 4, 14)      # the swoosh


def draw_trala(pose):
    c = Canvas(32, 32)
    lunge = -3 if pose == 'attack' else 0

    for i in range(3):                          # three shoes, obviously
        _sneaker(c, 5 + i * 8 + lunge, 25)

    c.ellipse(17 + lunge, 15, 12.5, 7.0, 3)     # body
    c.tri((2 + lunge, 16), (12 + lunge, 9), (12 + lunge, 22), 3)   # snout
    c.ellipse(17 + lunge, 18.5, 10.5, 3.6, 5)   # belly
    c.tri((16 + lunge, 9), (21 + lunge, 1), (24 + lunge, 9), 4)    # dorsal
    c.tri((27 + lunge, 15), (31 + lunge, 5), (31 + lunge, 25), 4)  # tail
    c.tri((15 + lunge, 20), (11 + lunge, 27), (20 + lunge, 22), 12)  # pectoral

    # mouth, open when attacking
    if pose == 'attack':
        c.tri((2 + lunge, 17), (13 + lunge, 13), (13 + lunge, 24), 10)
        for i in range(5):
            c.set(4 + lunge + i * 2, 16 - i // 2, 6)
            c.set(5 + lunge + i * 2, 21 + i // 3, 6)
    else:
        c.line(3 + lunge, 18, 13 + lunge, 20, 1)
        for i in range(4):
            c.set(5 + lunge + i * 2, 18 + i // 2, 6)

    c.disc(10 + lunge, 13, 2.6, 6)
    c.disc(9 + lunge, 13, 1.3, 7)

    c.shade(4, 3, 2, ox=0, oy=-1)
    c.outline()
    return c


# ---- Lirili Larila ------------------------------------------------------
#
# Cactus with an elephant's head. Casts; does not hit things.

def draw_lirili(pose):
    """The head has to dominate or this reads as "cactus with a grey blob".
    Elephant occupies the top half, cactus the bottom, trunk crossing both."""
    c = Canvas(32, 32)
    raise_ = -4 if pose == 'cast' else 0

    c.rect(12, 29, 4, 3, 9)                     # sandals
    c.rect(19, 29, 4, 3, 9)

    c.ellipse(17, 24, 7.0, 6.5, 3)              # cactus trunk-body
    c.ellipse(8.5, 22 + raise_, 3.2, 4.4, 3)    # arm pads
    c.ellipse(26.0, 22 + raise_, 3.2, 4.4, 3)
    c.line(10, 23 + raise_, 13, 25, 3, 3)
    c.line(25, 23 + raise_, 22, 25, 3, 3)

    for sy in range(20, 30, 3):                 # spines
        for sx in range(12, 24, 4):
            c.set(sx + (sy % 6) // 3, sy, 5)
            c.set(sx + (sy % 6) // 3, sy + 1, 5)
    c.set(8, 20 + raise_, 5)
    c.set(26, 20 + raise_, 5)

    c.ellipse(5.5, 11, 5.0, 6.5, 6)             # ears, wide and behind
    c.ellipse(26.5, 11, 5.0, 6.5, 6)
    c.ellipse(6.5, 11, 3.2, 4.6, 7)
    c.ellipse(25.5, 11, 3.2, 4.6, 7)

    c.ellipse(16, 11, 9.0, 8.5, 7)              # head

    c.tri((11, 16), (9, 23), (13, 18), 14)      # tusks
    c.tri((21, 16), (23, 23), (19, 18), 14)

    # trunk: down the middle, then curled forward to the left
    c.line(16, 15, 16, 21, 7, 5)
    c.line(16, 21, 12, 25, 7, 4)
    c.line(12, 25, 9, 24, 7, 3)
    for i in range(4):                          # trunk rings
        c.set(14, 17 + i * 2, 6)
        c.set(18, 17 + i * 2, 6)

    c.disc(12, 9, 2.6, 11)                      # eyes
    c.disc(20, 9, 2.6, 11)
    c.disc(11.2, 9, 1.3, 12)
    c.disc(19.2, 9, 1.3, 12)

    c.disc(27, 3, 2.4, 10)                      # the flower, because cactus
    c.disc(27, 3, 1.1, 5)
    c.line(27, 5, 26, 8, 2)

    c.shade(4, 3, 2, ox=-1, oy=-1)
    c.shade(8, 7, 6, ox=-1, oy=-1)
    c.outline()
    return c




# ---- Brr Brr Patapim ----------------------------------------------------
#
# A tree that walks, on the party's side from act two. Wide, slow, and drawn
# to be the thing standing in front of everyone else.

def draw_patapim(pose):
    c = Canvas(32, 32)
    lean = -2 if pose == 'attack' else 0

    c.rect(6 + lean, 26, 6, 6, 2)               # the long feet
    c.rect(19 + lean, 26, 6, 6, 2)
    c.rect(5 + lean, 30, 8, 2, 13)
    c.rect(18 + lean, 30, 8, 2, 13)

    c.ellipse(15 + lean, 17, 10.0, 10.5, 3)     # trunk
    c.ellipse(13 + lean, 15, 7.0, 8.0, 4)
    for gy in range(9, 26, 4):                  # grain
        c.line(8 + lean, gy, 22 + lean, gy + 1, 2)
    c.line(10 + lean, 8, 10 + lean, 25, 10)

    c.ellipse(15 + lean, 6, 12.0, 5.0, 5)       # moss on top
    c.ellipse(14 + lean, 5, 10.0, 3.6, 6)
    c.ellipse(12 + lean, 4, 6.0, 2.2, 7)

    if pose == 'attack':                        # arms: branches
        c.line(6 + lean, 14, 0, 6, 2, 3)
        c.line(24 + lean, 14, 30, 8, 2, 3)
        c.line(0, 6, 2, 2, 2, 2)
    else:
        c.line(5 + lean, 16, 1, 22, 2, 3)
        c.line(25 + lean, 16, 30, 21, 2, 3)

    c.disc(11 + lean, 14, 3.0, 8)               # the eyes, very old
    c.disc(19 + lean, 14, 3.0, 8)
    c.disc(10 + lean, 14, 1.3, 9)
    c.disc(18 + lean, 14, 1.3, 9)
    c.line(8 + lean, 10, 13 + lean, 12, 13, 2)  # heavy brow
    c.line(22 + lean, 10, 17 + lean, 12, 13, 2)

    c.outline()
    return c


# ---- Bombardiro, as a party member --------------------------------------
#
# The 64x64 boss cut down to a battler: same silhouette, fewer bombs, because
# he used them.

def draw_bombard(pose):
    c = Canvas(32, 32)
    lunge = -3 if pose == 'attack' else 0

    c.tri((16 + lunge, 12), (2, 2), (10, 16), 9)        # wings
    c.tri((16 + lunge, 20), (2, 30), (10, 17), 9)
    c.tri((16 + lunge, 13), (5, 5), (10, 15), 8)

    c.ellipse(17 + lunge, 16, 11.0, 6.0, 3)             # fuselage
    c.ellipse(17 + lunge, 18, 9.0, 3.0, 5)
    for i in range(4):
        c.tri((10 + i * 5 + lunge, 11), (12 + i * 5 + lunge, 7),
              (14 + i * 5 + lunge, 11), 4)

    c.ellipse(27 + lunge, 15, 6.0, 4.0, 3)              # snout
    c.rect(24 + lunge, 12, 8, 6, 3)
    c.rect(24 + lunge, 17, 8, 2, 5)
    for i in range(4):
        c.tri((25 + i * 2 + lunge, 17), (26 + i * 2 + lunge, 20),
              (27 + i * 2 + lunge, 17), 6)
    c.disc(25 + lunge, 11, 2.4, 4)
    c.disc(25 + lunge, 11, 1.4, 11)

    c.rect(10 + lunge, 22, 3, 4, 13)                    # one bomb left
    c.tri((9 + lunge, 26), (11 + lunge, 29), (13 + lunge, 26), 12)
    c.line(6 + lunge, 21, 20 + lunge, 21, 8, 2)

    c.shade(4, 3, 2, ox=0, oy=-1)
    c.outline()
    return c


# ---- the Sleepers -------------------------------------------------------
#
# Enemies stand on the left and face right. Twelve designs across six regions;
# the first four are the ones the road east opens with.

def draw_snorfly():
    """A fly too drowsy to fly straight. The bubble is load-bearing."""
    c = Canvas(32, 32)
    c.ellipse(9, 8, 6.0, 4.5, 14)
    c.ellipse(9, 20, 6.0, 4.5, 14)
    c.line(14, 10, 10, 7, 13)
    c.line(14, 18, 10, 21, 13)

    c.ellipse(17, 15, 8.5, 7.5, 3)
    c.ellipse(24, 13, 5.0, 4.5, 4)
    for i in range(3):
        c.line(13 + i * 4, 9, 13 + i * 4, 21, 2)

    c.disc(26, 11, 2.4, 6)
    c.disc(22, 11, 2.4, 6)
    c.line(24, 11, 28, 11, 7)
    c.line(20, 11, 24, 11, 7)

    c.disc(29, 17, 3.2, 5)
    c.disc(28, 16, 1.2, 6)
    c.line(20, 24, 22, 29, 1)
    c.line(16, 23, 15, 29, 1)
    c.outline()
    return c


def draw_pilloworm():
    """Three pillows in a trench coat."""
    c = Canvas(32, 32)
    for i, (x, y, r) in enumerate(((8, 25, 6.5), (14, 18, 7.0), (21, 10, 7.5))):
        c.ellipse(x, y, r, r * 0.78, 6 if i != 1 else 8)
        c.ellipse(x, y, r * 0.72, r * 0.5, 9 if i == 1 else 8)
        for k in range(4):
            dx = r * (0.9 if k & 1 else -0.9)
            dy = r * (0.6 if k & 2 else -0.6)
            c.disc(x + dx, y + dy, 1.4, 6)

    c.disc(24, 8, 2.3, 6)
    c.disc(19, 8, 2.3, 6)
    c.line(22, 8, 26, 8, 7)
    c.line(17, 8, 21, 8, 7)
    c.ellipse(23, 13, 2.4, 1.6, 2)
    c.outline()
    return c


def draw_dreambat():
    c = Canvas(32, 32)
    c.tri((14, 14), (1, 4), (5, 22), 3)
    c.tri((14, 14), (31, 6), (27, 24), 3)
    c.tri((14, 14), (3, 12), (6, 22), 2)
    c.tri((14, 14), (29, 13), (26, 24), 2)

    c.ellipse(16, 15, 5.0, 6.5, 2)
    c.disc(17, 9, 4.6, 3)
    c.tri((13, 6), (14, 0), (17, 5), 3)
    c.tri((21, 6), (21, 0), (18, 5), 3)

    c.disc(19, 8, 2.0, 6)
    c.disc(15, 8, 2.0, 6)
    c.line(17.5, 8, 20.5, 8, 7)
    c.line(13.5, 8, 16.5, 8, 7)
    c.set(16, 12, 6)
    c.set(19, 12, 6)
    c.outline()
    return c


def draw_sandman():
    """Hood, no face, a fistful of night."""
    c = Canvas(32, 32)
    c.ellipse(15, 20, 9.5, 11.0, 13)
    c.tri((5, 31), (15, 12), (26, 31), 13)
    c.ellipse(16, 9, 6.5, 7.0, 13)
    c.ellipse(16, 10, 4.6, 5.2, 1)
    c.disc(18, 10, 1.4, 11)
    c.disc(14, 10, 1.4, 11)

    c.line(6, 20, 15, 17, 13, 3)
    c.disc(6, 21, 2.2, 9)
    for i in range(7):
        c.set(4 + (i % 3), 24 + i, 11)
        c.set(7 - (i % 2), 25 + i, 8)
    c.ellipse(15, 30, 9.0, 2.0, 2)
    c.outline()
    return c


def draw_moth():
    """Dusk moth: all wing, and a body like a thumb in a fur coat."""
    c = Canvas(32, 32)
    c.tri((16, 16), (2, 2), (8, 20), 4)
    c.tri((16, 16), (30, 4), (24, 21), 4)
    c.tri((16, 18), (4, 30), (12, 24), 3)
    c.tri((16, 18), (28, 30), (20, 24), 3)
    for cx, cy in ((8, 10), (24, 11)):
        c.disc(cx, cy, 2.6, 5)
        c.disc(cx, cy, 1.2, 11)
    c.ellipse(16, 17, 3.2, 8.0, 9)
    c.ellipse(16, 14, 2.4, 3.0, 8)
    for y in range(11, 25, 3):
        c.line(13, y, 19, y, 10)
    c.disc(15, 11, 1.2, 12)
    c.disc(18, 11, 1.2, 12)
    c.line(15, 8, 11, 3, 10)
    c.line(18, 8, 22, 3, 10)
    c.outline()
    return c


def draw_log():
    """A log that snores. Forest-region wall: slow, tough, unbothered."""
    c = Canvas(32, 32)
    c.ellipse(16, 19, 14.0, 8.0, 9)
    c.ellipse(16, 17, 12.5, 6.4, 8)
    c.ellipse(28, 19, 3.6, 7.6, 9)
    for i in range(3):
        c.ellipse(28, 19, 3.0 - i, 6.6 - i * 2, 8 if i % 2 else 9)
    for x in range(4, 26, 5):
        c.line(x, 12, x + 1, 26, 9)
    c.disc(12, 16, 2.6, 6)
    c.disc(19, 16, 2.6, 6)
    c.line(10, 16, 14, 16, 7)
    c.line(17, 16, 21, 16, 7)
    c.ellipse(15, 22, 3.0, 1.8, 2)
    for i in range(3):
        c.disc(6 - i, 8 - i * 3, 1.4 + i * 0.4, 5)
    c.outline()
    return c


def draw_jelly():
    """Tide jelly: a bell and a lot of drift."""
    c = Canvas(32, 32)
    for i in range(7):
        x = 4 + i * 4
        for k in range(10):
            c.set(int(x + 1.6 * math.sin(k * 0.8 + i)), 18 + k, 14 if k % 2 else 13)
    c.ellipse(16, 14, 12.0, 9.0, 13)
    c.ellipse(16, 13, 10.0, 7.2, 14)
    c.ellipse(14, 11, 6.0, 4.0, 6)
    c.ellipse(13, 10, 3.0, 1.8, 15)
    c.disc(12, 14, 1.8, 5)
    c.disc(20, 14, 1.8, 5)
    c.outline()
    return c


def draw_husk():
    """Salt husk: the shape somebody left behind when they lay down."""
    c = Canvas(32, 32)
    c.ellipse(16, 20, 8.0, 11.0, 8)
    c.ellipse(15, 18, 6.0, 8.4, 9)
    c.disc(16, 7, 6.0, 8)
    c.disc(15, 6, 4.6, 9)
    c.ellipse(14, 7, 1.8, 2.4, 1)
    c.ellipse(19, 7, 1.8, 2.4, 1)
    for i in range(6):                          # cracks
        c.line(8 + i * 3, 12 + (i % 3) * 4, 10 + i * 3, 20 + (i % 2) * 5, 1)
    c.line(6, 18, 2, 27, 8, 2)
    c.line(26, 18, 30, 27, 8, 2)
    c.outline()
    return c


def draw_drone():
    """Lull drone: fortress machinery that hums people under."""
    c = Canvas(32, 32)
    c.rect(6, 2, 20, 2, 4)                      # rotor
    for i in range(-9, 10, 3):
        c.set(16 + i, 3 + abs(i) // 5, 3)
    c.line(16, 4, 16, 9, 2, 2)
    c.ellipse(16, 16, 9.0, 7.5, 3)
    c.ellipse(15, 14, 7.0, 5.4, 4)
    c.rect(8, 15, 16, 2, 2)
    c.disc(16, 16, 4.0, 8)
    c.disc(16, 16, 2.6, 11)
    c.disc(16, 16, 1.2, 15)
    c.line(8, 22, 6, 29, 2, 2)
    c.line(24, 22, 26, 29, 2, 2)
    c.rect(4, 28, 6, 2, 3)
    c.rect(22, 28, 6, 2, 3)
    c.outline()
    return c


def draw_turret():
    """Quiet gun: squat, slow, and hits like a dropped anvil."""
    c = Canvas(32, 32)
    c.rect(2, 24, 28, 7, 2)
    c.rect(3, 25, 26, 2, 3)
    for x in range(4, 30, 4):
        c.rect(x, 27, 2, 3, 4)
    c.ellipse(16, 20, 10.0, 7.0, 3)
    c.ellipse(15, 18, 8.0, 5.0, 4)
    c.rect(16, 14, 15, 5, 3)
    c.rect(16, 15, 15, 2, 4)
    c.rect(29, 13, 3, 7, 2)
    c.disc(13, 18, 2.4, 12)
    c.disc(13, 18, 1.2, 11)
    c.outline()
    return c


def draw_wisp():
    """Nod wisp: a light that wants you to follow it and lie down."""
    c = Canvas(32, 32)
    for i in range(12):
        t = i / 11.0
        c.disc(20 - t * 14, 12 + math.sin(t * 4.0) * 7, 1.0 + t * 2.2,
               2 if t > 0.6 else 3)
    c.disc(22, 11, 6.0, 3)
    c.disc(22, 11, 4.4, 4)
    c.disc(22, 10, 2.6, 5)
    c.disc(21, 9, 1.2, 15)
    c.disc(20, 11, 0.9, 1)
    c.disc(24, 11, 0.9, 1)
    c.outline()
    return c


def draw_murmur():
    """Murmur: a mouth with nothing behind it, saying nothing, constantly."""
    c = Canvas(32, 32)
    c.ellipse(16, 16, 12.0, 13.0, 2)
    c.ellipse(16, 16, 9.5, 10.5, 1)
    c.ellipse(16, 17, 6.5, 4.5, 13)
    c.ellipse(16, 17, 5.0, 3.0, 1)
    for i in range(6):                          # teeth
        c.tri((11 + i * 2, 14), (12 + i * 2, 17), (13 + i * 2, 14), 6)
        c.tri((11 + i * 2, 20), (12 + i * 2, 17), (13 + i * 2, 20), 6)
    for i in range(9):
        a = i * 0.7
        c.set(int(16 + 12 * math.cos(a)), int(16 + 13 * math.sin(a)), 4)
    c.outline()
    return c


# ---- six more of the canon, one per region ------------------------------
#
# Added after the bosses in the type list so nothing renumbers: these are the
# faces each region gets to itself.

def draw_cappuccino():
    """CAPPUCCINO ASSASSINO. A cup of coffee with a knife and a grudge."""
    c = Canvas(32, 32)
    c.ellipse(15, 22, 9.5, 8.0, 6)              # the cup
    c.ellipse(15, 20, 8.0, 6.4, 8)
    c.ellipse(15, 14, 9.0, 3.4, 2)              # the crema
    c.ellipse(14, 13, 7.0, 2.4, 9)
    c.ellipse(13, 13, 3.0, 1.2, 6)
    c.ellipse(26, 21, 3.4, 4.4, 6)              # handle
    c.ellipse(26, 21, 1.8, 2.6, 1)
    c.rect(6, 29, 20, 3, 10)                    # saucer
    c.disc(12, 19, 2.4, 6)                      # eyes
    c.disc(19, 19, 2.4, 6)
    c.disc(11, 19, 1.2, 7)
    c.disc(18, 19, 1.2, 7)
    c.line(9, 15, 14, 17, 12, 2)                # eyebrows, furious
    c.line(22, 15, 17, 17, 12, 2)
    c.line(3, 4, 9, 16, 10, 2)                  # the knife
    c.line(3, 4, 5, 2, 10, 1)
    c.line(9, 16, 11, 19, 15, 2)
    c.outline()
    return c


def draw_gusini():
    """BOMBOMBINI GUSINI. A goose. It is also ordnance."""
    c = Canvas(32, 32)
    c.tri((16, 14), (2, 6), (12, 20), 10)       # wings
    c.tri((16, 16), (4, 28), (13, 22), 10)
    c.ellipse(16, 18, 10.0, 7.5, 9)             # body
    c.ellipse(15, 16, 8.0, 5.6, 15)
    c.ellipse(24, 10, 4.2, 4.6, 15)             # head
    c.rect(26, 10, 6, 3, 11)                    # bill
    c.disc(24, 9, 1.6, 6)
    c.disc(24, 9, 0.8, 7)
    c.ellipse(14, 26, 3.0, 4.0, 13)             # a bomb slung under
    c.tri((12, 29), (14, 32), (16, 29), 12)
    c.line(9, 24, 20, 24, 8, 2)
    c.line(20, 26, 22, 31, 11, 2)               # legs
    c.line(14, 27, 12, 31, 11, 2)
    c.outline()
    return c


def draw_ambalabu():
    """BONECA AMBALABU. A frog, a tyre, and a pair of legs. Ask nobody."""
    c = Canvas(32, 32)
    c.ellipse(16, 20, 12.0, 9.0, 1)             # the tyre
    c.ellipse(16, 20, 9.0, 6.4, 10)
    c.ellipse(16, 20, 5.5, 3.8, 1)
    for i in range(8):
        a = i * 0.78
        c.set(int(16 + 11 * math.cos(a)), int(20 + 8 * math.sin(a)), 9)
    c.ellipse(16, 9, 8.0, 6.0, 6)               # the frog head, on top
    c.disc(11, 6, 3.4, 6)
    c.disc(21, 6, 3.4, 6)
    c.disc(11, 6, 2.0, 15)
    c.disc(21, 6, 2.0, 15)
    c.disc(11, 6, 1.0, 7)
    c.disc(21, 6, 1.0, 7)
    c.line(11, 12, 21, 12, 1, 1)                # a wide, patient mouth
    c.line(9, 28, 7, 32, 5, 3)                  # human legs. Yes.
    c.line(23, 28, 25, 32, 5, 3)
    c.outline()
    return c


def draw_octopusini():
    """BLUEBERRINNI OCTOPUSINI. A blueberry. With an octopus in it."""
    c = Canvas(32, 32)
    for i in range(6):                          # arms
        x = 3 + i * 5
        for k in range(9):
            c.set(int(x + 2.2 * math.sin(k * 0.7 + i)), 21 + k,
                  13 if k % 2 else 12)
    c.ellipse(16, 14, 12.0, 11.0, 13)           # the berry
    c.ellipse(15, 12, 9.5, 8.0, 12)
    c.ellipse(13, 9, 5.0, 3.6, 4)
    for i in range(5):                          # the crown of the fruit
        c.tri((13 + i * 2, 3), (14 + i * 2, 0), (15 + i * 2, 3), 5)
    c.disc(12, 14, 3.0, 6)
    c.disc(21, 14, 3.0, 6)
    c.disc(11, 14, 1.4, 7)
    c.disc(20, 14, 1.4, 7)
    c.outline()
    return c


def draw_glorbo():
    """GLORBO FRUTTODRILLO. A crocodile made of fruit, or the other way up."""
    c = Canvas(32, 32)
    c.ellipse(15, 20, 13.0, 7.0, 6)             # body
    c.ellipse(15, 22, 11.0, 4.0, 5)
    c.tri((2, 20), (12, 13), (12, 26), 6)       # snout to the left
    c.rect(2, 19, 11, 5, 6)
    c.rect(2, 22, 11, 2, 8)
    for i in range(5):                          # teeth
        c.tri((3 + i * 2, 22), (4 + i * 2, 25), (5 + i * 2, 22), 15)
    for i in range(6):                          # fruit scutes
        c.disc(11 + i * 3.4, 13 - (i % 2), 2.2, 4)
        c.set(int(11 + i * 3.4), 12 - (i % 2), 11)
    c.disc(13, 16, 2.6, 15)                     # eye
    c.disc(13, 16, 1.2, 7)
    c.line(8, 26, 6, 31, 5, 3)                  # legs
    c.line(22, 26, 24, 31, 5, 3)
    c.tri((27, 20), (31, 10), (31, 28), 6)      # tail
    c.outline()
    return c


def draw_saturnita():
    """LA VACCA SATURNO SATURNITA. A cow. With rings. Asleep, obviously."""
    c = Canvas(32, 32)
    for i in range(2):                          # the rings, behind
        c.ellipse(16, 18, 15.0 - i * 2, 4.0 - i, 4 if i else 11)
    c.ellipse(16, 16, 10.0, 8.0, 15)            # body
    for cx, cy, r in ((11, 13, 2.6), (20, 18, 3.0), (15, 20, 2.0)):
        c.ellipse(cx, cy, r, r * 0.8, 1)        # patches
    c.ellipse(24, 11, 5.0, 4.4, 15)             # head
    c.ellipse(26, 13, 3.0, 2.2, 5)              # muzzle
    c.set(25, 13, 1)
    c.set(27, 13, 1)
    c.disc(23, 9, 1.6, 6)                       # eyes, shut
    c.disc(27, 9, 1.6, 6)
    c.line(22, 9, 24, 9, 7)
    c.line(26, 9, 28, 9, 7)
    c.tri((20, 7), (21, 3), (23, 7), 9)         # horns
    c.tri((28, 7), (29, 3), (31, 7), 9)
    for i in range(2):                          # the rings, in front
        c.ellipse(16, 19, 15.0 - i * 2, 3.4 - i, 11 if i else 4)
    c.outline()
    return c


# ---- the bosses, 64x64 --------------------------------------------------
#
# Each is the thing the act was about, so each gets the whole page-2 block.

def draw_boss_patapim():
    """Brr Brr Patapim, before he sits down: the road, standing up."""
    c = Canvas(64, 64)

    c.rect(14, 52, 12, 12, 2)                   # legs like stumps
    c.rect(38, 52, 12, 12, 2)
    c.rect(11, 60, 18, 4, 13)
    c.rect(35, 60, 18, 4, 13)

    c.ellipse(32, 34, 20.0, 22.0, 3)            # trunk
    c.ellipse(28, 30, 15.0, 17.0, 4)
    for gy in range(16, 54, 6):
        c.line(14, gy, 50, gy + 2, 2)
    for gx in (20, 27, 40):
        c.line(gx, 14, gx + 2, 52, 10)

    c.ellipse(32, 12, 26.0, 11.0, 5)            # crown of moss
    c.ellipse(30, 10, 22.0, 8.0, 6)
    c.ellipse(26, 8, 14.0, 4.6, 7)
    for i in range(9):
        c.disc(10 + i * 6, 6 + (i % 3) * 3, 2.4, 7)

    c.line(12, 30, 1, 14, 2, 5)                 # branch arms
    c.line(1, 14, 6, 6, 2, 3)
    c.line(52, 30, 62, 16, 2, 5)
    c.line(62, 16, 57, 6, 2, 3)

    c.disc(24, 30, 6.0, 8)                      # eyes
    c.disc(41, 30, 6.0, 8)
    c.disc(22, 30, 2.6, 9)
    c.disc(39, 30, 2.6, 9)
    c.line(16, 21, 30, 26, 13, 4)               # brow
    c.line(49, 21, 35, 26, 13, 4)
    c.ellipse(32, 44, 7.0, 3.0, 13)             # a mouth like a knot
    c.outline()
    return c


def draw_boss_ngantuk():
    """NGANTUKAN, the drowsing tide: a head the size of the bay."""
    c = Canvas(64, 64)

    for y in range(46, 64):                     # the water it stands out of
        for x in range(64):
            v = math.sin(x * 0.5 + y * 0.9)
            c.set(x, y, 4 if v > 0.6 else 2)

    c.ellipse(32, 34, 25.0, 20.0, 3)            # head
    c.ellipse(28, 30, 20.0, 15.0, 4)
    c.ellipse(32, 46, 22.0, 8.0, 2)
    for i in range(9):                          # teeth along the jaw
        c.tri((12 + i * 5, 44), (14 + i * 5, 52), (16 + i * 5, 44), 6)

    c.ellipse(20, 24, 7.0, 6.0, 6)              # eyes, half shut
    c.ellipse(44, 24, 7.0, 6.0, 6)
    c.ellipse(20, 26, 6.0, 3.4, 5)
    c.ellipse(44, 26, 6.0, 3.4, 5)
    c.disc(19, 26, 2.2, 1)
    c.disc(43, 26, 2.2, 1)
    c.line(12, 17, 27, 20, 2, 4)
    c.line(52, 17, 37, 20, 2, 4)

    for i, x in enumerate((8, 20, 44, 56)):     # spines
        c.tri((x - 4, 18), (x, 2 + i % 2 * 4), (x + 4, 18), 2)
    c.ellipse(32, 40, 5.0, 3.0, 12)             # a slow bubble
    c.disc(50, 38, 2.6, 15)
    c.outline()
    return c


def draw_boss_sandking():
    """THE SANDMAN KING: the hooded shape, crowned, pouring hours."""
    c = Canvas(64, 64)

    c.tri((6, 63), (32, 18), (58, 63), 13)      # robe
    c.ellipse(32, 52, 24.0, 12.0, 13)
    c.ellipse(32, 50, 20.0, 9.0, 2)
    for i in range(7):
        c.line(10 + i * 7, 40, 8 + i * 7, 63, 1)

    c.ellipse(32, 20, 15.0, 16.0, 13)           # hood
    c.ellipse(32, 22, 11.0, 12.0, 1)
    c.disc(27, 22, 3.0, 11)                     # two lights, no face
    c.disc(38, 22, 3.0, 11)
    c.disc(27, 22, 1.4, 15)
    c.disc(38, 22, 1.4, 15)

    for i in range(5):                          # crown
        c.tri((14 + i * 9, 10), (18 + i * 9, 0), (22 + i * 9, 10), 11)
    c.rect(12, 8, 42, 4, 11)
    c.rect(12, 8, 42, 1, 15)

    c.line(12, 40, 26, 34, 13, 5)               # arm, and the hourglass
    c.disc(11, 41, 4.0, 9)
    c.tri((4, 44), (18, 44), (11, 52), 8)
    c.tri((4, 60), (18, 60), (11, 52), 8)
    for i in range(9):
        c.set(9 + (i % 3), 53 + i, 11)
    c.outline()
    return c


def draw_boss_crocodilo():
    """Bombardiro Crocodilo: the premise, at full size."""
    c = Canvas(64, 64)

    c.tri((32, 24), (2, 2), (14, 30), 9)
    c.tri((32, 40), (2, 62), (14, 34), 9)
    c.tri((32, 26), (6, 8), (13, 29), 8)
    c.tri((32, 38), (6, 56), (13, 35), 8)
    c.rect(10, 12, 5, 5, 10)
    c.rect(10, 47, 5, 5, 10)
    for i in range(-6, 7):
        c.set(12 + i // 3, 14 + i, 10)
        c.set(12 - i // 3, 49 + i, 10)

    c.ellipse(32, 32, 22.0, 10.5, 3)
    c.ellipse(32, 36, 19.0, 5.0, 5)
    for i in range(6):
        c.line(20 + i * 5, 32, 20 + i * 5, 40, 2)
    for i in range(7):
        c.tri((16 + i * 6, 22), (19 + i * 6, 16), (22 + i * 6, 22), 4)

    c.tri((54, 30), (63, 12), (63, 34), 9)
    c.rect(52, 28, 8, 8, 3)

    c.ellipse(50, 30, 12.0, 8.0, 3)
    c.rect(50, 26, 14, 9, 3)
    c.ellipse(62, 30, 4.0, 4.5, 4)
    c.rect(50, 33, 14, 3, 5)
    for i in range(6):
        c.tri((51 + i * 2, 33), (52 + i * 2, 36), (53 + i * 2, 33), 6)
    c.disc(52, 24, 3.6, 4)
    c.disc(52, 24, 2.2, 11)
    c.disc(52, 24, 1.0, 7)

    for bx in (24, 34, 44):
        c.ellipse(bx, 46, 3.0, 4.5, 13)
        c.tri((bx - 2, 50), (bx, 53), (bx + 2, 50), 12)
        c.line(bx, 41, bx, 43, 8)
    c.line(20, 42, 48, 42, 8, 2)

    c.disc(20, 20, 3.0, 11)
    c.disc(20, 20, 1.6, 14)

    c.shade(4, 3, 2, ox=0, oy=-1)
    c.outline()
    return c


def draw_boss_silenzio(second):
    """IL SILENZIO. The first shape pleads and is nearly gentle; the second
    has stopped asking. Same construction, opened out."""
    c = Canvas(64, 64)
    spread = 1.6 if second else 1.0

    # A robe of nothing: the outline is drawn, the inside is the dark.
    c.tri((int(32 - 24 * spread), 63), (32, 8),
          (int(32 + 24 * spread), 63), 2)
    c.tri((int(32 - 20 * spread), 63), (32, 14),
          (int(32 + 20 * spread), 63), 1)

    if second:
        for i in range(6):                      # unfolded arms
            a = 0.5 + i * 0.42
            x = int(32 + 30 * math.cos(a + 3.14))
            y = int(30 + 26 * math.sin(a + 3.14))
            c.line(32, 30, x, y, 3, 3)
            c.disc(x, y, 2.2, 6)

    c.ellipse(32, 20, 15.0, 15.0, 3)            # the head-shape
    c.ellipse(32, 21, 12.0, 12.0, 1)

    # Static where a face would be.
    rng = Rng(0xC0DE if second else 0x51DE)
    for _ in range(120):
        x = rng.span(22, 42)
        y = rng.span(12, 30)
        if math.hypot(x - 32, y - 21) < 11:
            c.set(x, y, rng.pick([4, 5, 6, 1]))
    c.disc(27, 20, 2.4, 7 if second else 6)
    c.disc(37, 20, 2.4, 7 if second else 6)
    c.disc(27, 20, 1.1, 15)
    c.disc(37, 20, 1.1, 15)

    for i in range(10):                         # a hem that never settles
        x = 6 + i * 6
        c.line(x, 58, x + (3 if i % 2 else -3), 63, 3, 2)

    if second:
        for i in range(14):
            c.set(rng.span(2, 61), rng.span(2, 61), 15)

    c.outline()
    return c


# ---- the field hero -----------------------------------------------------

def draw_walk(direction, frame):
    c = Canvas(16, 16)
    step = 1 if frame else 0

    c.rect(5, 13 - step, 2, 3, 2)
    c.rect(9, 13 + step - 1, 2, 3, 2)

    c.rect(4, 3, 8, 11, 3)
    c.ellipse(7.5, 3, 4.0, 1.8, 4)
    c.ellipse(7.5, 13.5, 4.0, 1.6, 2)
    c.rect(5, 9, 6, 2, 14)

    if direction == 'up':
        c.line(5, 5, 10, 5, 2)
        c.line(11, 6, 14, 2, 8, 2)
    else:
        ex = {'down': (6, 10), 'left': (5, 8), 'right': (7, 10)}[direction]
        c.disc(ex[0], 6, 1.8, 6)
        c.disc(ex[1], 6, 1.8, 6)
        px = {'down': 0, 'left': -1, 'right': 1}[direction]
        c.set(ex[0] + px, 6, 7)
        c.set(ex[1] + px, 6, 7)
        if direction == 'left':
            c.line(4, 7, 1, 3, 8, 2)
        else:
            c.line(11, 7, 14, 3, 8, 2)

    c.outline()
    return c


# ---- sheet layout -------------------------------------------------------
#
# The resident page is 256 characters and holds everything that is always on
# screen. Enemies are not: nineteen designs, six of them 64x64, come to 18KB,
# so they live in ROM and the fight uploads what it needs into page 2.
#
# Names are chosen so a large OBJ's block fits its 256-character page in BOTH
# directions: a 32x32 needs name%16 <= 12 and (name%256)/16 <= 12; a 64x64
# needs name%16 <= 8 and (name%256)/16 <= 8. A-4's "taken row-wise from the
# 16x16-character page" means the index wraps inside that page, which the boss
# found out the hard way at name 224.

STATIC_TILES = 256

WALK_BASE = 0            # 8 poses of 16x16 at 0,2,...,14

PARTY_SLOTS = [
    ('TUNG',    32,  36, 'P_TUNG'),
    ('PATAPIM', 40,  44, 'P_PATAPIM'),
    ('TRALA',   96, 100, 'P_TRALA'),
    ('LIRILI', 104, 108, 'P_LIRILI'),
    ('BOMBARD', 160, 164, 'P_BOSS'),
]

WALK_ORDER = [('down', 0), ('down', 1), ('up', 0), ('up', 1),
              ('left', 0), ('left', 1), ('right', 0), ('right', 1)]

# type id -> (painter, palette). Order must match the EN_* constants in
# src/ttrpg.h; enemyArtOffset is indexed by the same number.
ENEMY_ART = [
    (None, None),                       # EN_NONE
    (lambda: draw_snorfly(),   'P_ENEMY'),
    (lambda: draw_pilloworm(), 'P_ENEMY'),
    (lambda: draw_dreambat(),  'P_ENEMY'),
    (lambda: draw_sandman(),   'P_ENEMY'),
    (lambda: draw_moth(),      'P_ENEMY'),
    (lambda: draw_log(),       'P_PATAPIM'),
    (lambda: draw_jelly(),     'P_TRALA'),
    (lambda: draw_husk(),      'P_ENEMY'),
    (lambda: draw_drone(),     'P_ENEMY2'),
    (lambda: draw_turret(),    'P_ENEMY2'),
    (lambda: draw_wisp(),      'P_ENEMY'),
    (lambda: draw_murmur(),    'P_ENEMY'),
    (lambda: draw_boss_patapim(),   'P_PATAPIM'),
    (lambda: draw_boss_ngantuk(),   'P_TRALA'),
    (lambda: draw_boss_sandking(),  'P_ENEMY'),
    (lambda: draw_boss_crocodilo(), 'P_BOSS'),
    (lambda: draw_boss_silenzio(0), 'P_ENEMY'),
    (lambda: draw_boss_silenzio(1), 'P_ENEMY'),
    # Six of the canon, one per region.
    (lambda: draw_cappuccino(),  'P_ENEMY2'),
    (lambda: draw_gusini(),      'P_ENEMY2'),
    (lambda: draw_ambalabu(),    'P_PATAPIM'),
    (lambda: draw_octopusini(),  'P_TRALA'),
    (lambda: draw_glorbo(),      'P_LIRILI'),
    (lambda: draw_saturnita(),   'P_ENEMY'),
]


def place(sheet, canvas, name):
    tiles = max(canvas.w, canvas.h) // 8
    col, row = name % 16, (name % 256) // 16
    if col + tiles > 16 or row + tiles > 16:
        raise SystemExit("sprite at name %d wraps its page (col %d row %d, "
                         "%d tiles)" % (name, col, row, tiles))
    ox, oy = sheet.origin(name)
    for y in range(canvas.h):
        for x in range(canvas.w):
            v = canvas.px[y][x]
            if v:
                sheet.set(ox + x, oy + y, v)


def block_blob(canvas):
    """A canvas as the OBJ engine wants it streamed: block-row-major, so the
    C side can push one row of the block per DMA. A large OBJ's rows are 16
    names apart, which is why they cannot be one contiguous transfer."""
    tiles = canvas.w // 8
    out = bytearray()
    for row in range(canvas.h // 8):
        for col in range(tiles):
            cell = [[canvas.px[row * 8 + y][col * 8 + x] for x in range(8)]
                    for y in range(8)]
            out += g.tile_bin(cell)
    return bytes(out)


# ---- portraits ----------------------------------------------------------
#
# Head-and-shoulders busts for the dialogue box. 32x32 because the field's OBJ
# size pair is 16/32 (ppuSetFieldMode picks OBJ_SIZE16_L32), so one of these is
# a single large OBJ and a single OAM slot rather than four quadrants stitched
# together.
#
# They are streamed into the enemy scratch page, at a block the enemy art never
# reaches: a 64x64 boss at name 256 covers character rows 0-7 and six small
# enemies cover rows 0-1, so rows 12-15 are always free.


def _bust(c, shoulder, cloth):
    """Shoulders and a neck, the part every portrait shares."""
    c.rect(4, 26, 24, 6, cloth)
    c.ellipse(16, 27, 12, 5, cloth)
    c.rect(13, 22, 6, 5, shoulder)


def face_tung():
    c = Canvas(32, 32)
    _bust(c, 3, 2)
    c.rect(6, 4, 20, 21, 3)                 # the log, filling the frame
    c.ellipse(16, 4, 10, 3.2, 4)            # cut end, seen from below
    c.line(9, 7, 9, 23, 2)                  # grain
    c.line(23, 7, 23, 23, 2)
    c.rect(9, 20, 14, 3, 14)                # the slit
    c.rect(9, 20, 14, 1, 2)
    c.disc(12.0, 12.0, 4.4, 6)              # eyes, close enough to loom
    c.disc(20.5, 12.0, 4.4, 6)
    c.disc(11.0, 12.5, 2.0, 7)
    c.disc(19.5, 12.5, 2.0, 7)
    c.line(6, 5, 14, 8, 14, 2)              # brows: unimpressed, as ever
    c.line(26, 5, 18, 8, 14, 2)
    c.outline()
    return c


def face_nonna():
    c = Canvas(32, 32)
    _bust(c, 5, 11)                         # dark red shawl
    c.ellipse(16, 14, 9.5, 11, 5)           # face
    c.ellipse(16, 7, 11, 6.5, 6)            # white hair
    c.ellipse(16, 5, 11.5, 4.5, 13)         # headscarf over it
    c.rect(5, 5, 22, 3, 10)
    c.disc(12, 14, 1.6, 7)
    c.disc(20, 14, 1.6, 7)
    c.line(9, 11, 14, 12, 14)               # brows
    c.line(23, 11, 18, 12, 14)
    c.line(13, 21, 19, 21, 14)              # a flat, patient mouth
    c.line(8, 17, 9, 19, 14)                # cheek lines
    c.line(24, 17, 23, 19, 14)
    c.outline()
    return c


def face_patapim():
    c = Canvas(32, 32)
    _bust(c, 3, 2)
    c.ellipse(16, 16, 11, 12, 3)            # bark head
    c.ellipse(13, 14, 6, 8, 4)              # lit side
    c.ellipse(16, 4, 13, 6, 6)              # canopy
    c.ellipse(10, 6, 6, 4, 7)
    c.ellipse(23, 6, 6, 4, 5)
    c.line(6, 12, 9, 20, 13)                # bark grain
    c.line(25, 12, 23, 20, 13)
    c.disc(12, 16, 3.4, 8)                  # wide pale eyes
    c.disc(20.5, 16, 3.4, 8)
    c.disc(12, 16.5, 1.5, 9)
    c.disc(20.5, 16.5, 1.5, 9)
    c.rect(13, 22, 7, 2, 13)                # a small resigned mouth
    c.outline()
    return c


def face_trala():
    c = Canvas(32, 32)
    _bust(c, 3, 2)
    c.ellipse(17, 15, 13, 11, 3)            # snout, angled at the viewer
    c.ellipse(14, 12, 9, 7, 4)
    c.tri((30, 8), (30, 22), (20, 15), 2)   # the far side falling away
    c.ellipse(11, 22, 10, 4, 6)             # the grin
    for x in range(4, 19, 3):               # teeth
        c.tri((x, 20), (x + 2, 20), (x + 1, 24), 7)
    c.disc(13, 9, 3.2, 6)
    c.disc(22, 10, 3.0, 6)
    c.disc(13, 9.5, 1.4, 7)
    c.disc(22, 10.5, 1.3, 7)
    c.tri((6, 4), (14, 2), (10, 8), 2)      # dorsal fin, over the shoulder
    c.outline()
    return c


def face_lirili():
    c = Canvas(32, 32)
    _bust(c, 3, 13)
    c.ellipse(16, 15, 9.5, 12, 3)           # cactus body
    c.ellipse(13, 13, 5, 9, 4)
    c.ellipse(6, 13, 3.5, 6, 3)             # arms, cropped by the frame
    c.ellipse(26, 13, 3.5, 6, 3)
    for y in range(5, 26, 4):               # spines
        c.set(6, y, 5)
        c.set(26, y, 5)
        c.set(16, y, 5)
    c.disc(12.5, 13, 3.2, 11)               # eyes
    c.disc(19.5, 13, 3.2, 11)
    c.disc(12.5, 13.5, 1.4, 12)
    c.disc(19.5, 13.5, 1.4, 12)
    c.disc(16, 22, 4.5, 8)                  # the clock it wears
    c.disc(16, 22, 3.4, 14)
    c.line(16, 22, 16, 19, 12)
    c.line(16, 22, 18, 23, 12)
    c.outline()
    return c


def face_bombard():
    c = Canvas(32, 32)
    _bust(c, 8, 9)                          # fuselage grey
    c.ellipse(15, 13, 12, 8, 3)             # crocodile head
    c.ellipse(13, 10, 9, 5, 4)
    c.rect(2, 16, 26, 6, 3)                 # long jaw
    c.rect(2, 20, 26, 2, 2)
    for x in range(4, 27, 4):               # teeth
        c.tri((x, 16), (x + 2, 16), (x + 1, 20), 6)
    c.disc(10, 8, 3.4, 14)                  # yellow reptile eyes
    c.disc(21, 8, 3.4, 14)
    c.rect(9, 7, 3, 3, 7)                   # slit pupils
    c.rect(20, 7, 3, 3, 7)
    c.tri((0, 24), (12, 26), (0, 29), 10)   # wing, cropped
    c.tri((32, 24), (20, 26), (32, 29), 10)
    c.disc(26, 27, 2.0, 12)                 # engine glow
    c.outline()
    return c


def face_silenzio():
    c = Canvas(32, 32)
    c.rect(0, 0, 32, 32, 0)
    c.ellipse(16, 17, 12, 14, 2)            # a shape, and nothing in it
    c.ellipse(16, 15, 9, 11, 3)
    c.ellipse(16, 13, 6, 8, 4)
    c.ellipse(16, 11, 3, 4, 5)
    c.rect(7, 12, 5, 2, 7)                  # two absences where eyes go
    c.rect(20, 12, 5, 2, 7)
    for x in range(4, 29, 6):               # the feed, scrolling forever
        c.rect(x, 26, 4, 1, 14)
        c.rect(x + 1, 29, 4, 1, 13)
    c.outline(1)
    return c


def face_cappuccina():
    c = Canvas(32, 32)
    _bust(c, 3, 2)
    c.ellipse(16, 20, 11, 9, 6)             # the cup
    c.ellipse(16, 12, 10.5, 4.5, 3)         # the coffee
    c.ellipse(15, 11, 6, 2.5, 4)            # crema
    c.ellipse(27, 20, 4, 5, 6)              # handle
    c.ellipse(27, 20, 2, 3, 0)
    c.rect(4, 28, 24, 2, 13)                # saucer
    c.disc(12.5, 18, 2.6, 7)                # a face on the cup, obviously
    c.disc(19.5, 18, 2.6, 7)
    c.ellipse(16, 24, 4, 1.6, 10)
    c.line(10, 3, 11, 8, 5)                 # steam
    c.line(16, 1, 15, 7, 5)
    c.line(22, 3, 21, 8, 5)
    c.outline()
    return c


# (face, palette). The order is the FACE_* enum in sprmap.h.
PORTRAIT_ART = [
    (face_tung,       'P_TUNG'),
    (face_nonna,      'P_TUNG'),
    (face_patapim,    'P_PATAPIM'),
    (face_trala,      'P_TRALA'),
    (face_lirili,     'P_LIRILI'),
    (face_bombard,    'P_BOSS'),
    (face_silenzio,   'P_ENEMY'),
    (face_cappuccina, 'P_TUNG'),
]

PORTRAIT_NAMES = ['TUNG', 'NONNA', 'PATAPIM', 'TRALA',
                  'LIRILI', 'BOMBARD', 'SILENZIO', 'CAPPUCCINA']


def generate_sprites():
    sheet = g.Sheet(STATIC_TILES)

    for i, (d, f) in enumerate(WALK_ORDER):
        place(sheet, draw_walk(d, f), WALK_BASE + i * 2)

    place(sheet, draw_tung('idle'), 32)
    place(sheet, draw_tung('attack'), 36)
    place(sheet, draw_patapim('idle'), 40)
    place(sheet, draw_patapim('attack'), 44)
    place(sheet, draw_trala('idle'), 96)
    place(sheet, draw_trala('attack'), 100)
    place(sheet, draw_lirili('idle'), 104)
    place(sheet, draw_lirili('cast'), 108)
    place(sheet, draw_bombard('idle'), 160)
    place(sheet, draw_bombard('attack'), 164)

    pal = b''.join(g.palette_bin(p) for p in PALS)
    g.write('sprites.pic', sheet.to_pic())
    g.write('sprites.pal', pal)

    # The streamed half.
    blob = bytearray()
    offsets = []
    for t, (fn, palname) in enumerate(ENEMY_ART):
        if fn is None:
            offsets.append(0)
            continue
        offsets.append(len(blob))
        blob += block_blob(fn())
    g.write('enemies.pic', bytes(blob))

    # Portraits, in the same block-row-major order: four characters a row,
    # four rows, so the C side pushes one 128-byte row per DMA.
    faces = bytearray()
    for fn, _pal in PORTRAIT_ART:
        faces += block_blob(fn())
    g.write('portraits.pic', bytes(faces))

    with open('src/sprmap.h', 'w') as f:
        f.write("/* Generated by gen_sprites.py -- do not edit.\n"
                " * OBJ character names into the resident sheet at VRAM $0000,\n"
                " * and offsets into the streamed enemy blob. */\n"
                "#ifndef SPRMAP_H\n#define SPRMAP_H\n\n")
        f.write("#define SPR_WALK      %d   /* +i*2: down/up/left/right x2 */\n"
                % WALK_BASE)
        for name, idle, atk, _ in PARTY_SLOTS:
            f.write("#define SPR_%-8s %3d\n#define SPR_%s_ATK %3d\n"
                    % (name, idle, name, atk))
        f.write("/* OBJ palette slots. CGRAM 128 upward, sixteen colours each. */\n")
        for i, nm in enumerate(('P_TUNG', 'P_TRALA', 'P_LIRILI', 'P_ENEMY',
                                'P_BOSS', 'P_PATAPIM', 'P_FX', 'P_ENEMY2')):
            f.write("#define %-9s %d\n" % (nm, i))
        f.write("\n#define OPAL_TUNG   P_TUNG\n#define OPAL_ENEMY  P_ENEMY\n"
                "#define OPAL_BOSS   P_BOSS\n")
        f.write("\n/* Battle sprite name per party member, idle then acting. */\n")
        f.write("static const u16 sprPartyName[%d] = {\n    "
                % (len(PARTY_SLOTS) * 2))
        f.write(", ".join("%d, %d" % (s[1], s[2]) for s in PARTY_SLOTS))
        f.write("\n};\n")
        f.write("static const u8 sprPartyPal[%d] = {\n    " % len(PARTY_SLOTS))
        f.write(", ".join(s[3] for s in PARTY_SLOTS))
        f.write("\n};\n\n")
        f.write("/* Dialogue portraits. 32x32, one large OBJ in the field's\n"
                " * 16/32 size pair, streamed into the scratch page at a block\n"
                " * the enemy art never reaches. */\n")
        f.write("#define FACE_NONE %d\n" % 0)
        for i, nm in enumerate(PORTRAIT_NAMES):
            f.write("#define FACE_%-10s %d\n" % (nm, i + 1))
        f.write("#define FACE_COUNT %d\n\n" % (len(PORTRAIT_ART) + 1))
        f.write("/* Indexed by FACE_* - 1. */\n")
        f.write("static const u8 facePal[%d] = {\n    " % len(PORTRAIT_ART))
        f.write(", ".join(p for _fn, p in PORTRAIT_ART))
        f.write("\n};\n\n")
        f.write("/* Byte offset of each design inside enemies.pic. The blob is\n"
                " * one section and therefore one bank, so base + offset never\n"
                " * needs 24-bit arithmetic. */\n")
        f.write("static const u16 enemyArtOffset[%d] = {\n" % len(offsets))
        for i in range(0, len(offsets), 6):
            f.write("    " + ", ".join("%5d" % v for v in offsets[i:i + 6])
                    + ",\n")
        f.write("};\n\n")
        f.write("static const u8 enemyPal[%d] = {\n    " % len(ENEMY_ART))
        f.write(", ".join((p if p else 'P_ENEMY') for _, p in ENEMY_ART))
        f.write("\n};\n\n#endif\n")

    print("sprites.pic %d bytes (%d resident tiles)"
          % (STATIC_TILES * 32, STATIC_TILES))
    print("enemies.pic %d bytes (%d designs, streamed)"
          % (len(blob), len(ENEMY_ART) - 1))


if __name__ == '__main__':
    generate_sprites()
