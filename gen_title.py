#!/usr/bin/env python3
"""The title screen: a full-screen BG1 illustration and its own tileset.

The old title was the font drawing big letters over an empty gradient. This is
a picture -- the village asleep under a moon, ridgelines behind it, and the
logo built into the image rather than spelled out of the text layer.

Two things make it move without costing a frame:

**The shine.** The logo's pixels are not one colour, they are four, chosen by
a horizontal band across the letterform. Rotating those four palette entries in
CGRAM walks the bright band down the logo -- a four-word write in V-blank buys
a metallic sweep. It is the oldest trick on the machine and still the best
value on it.

The band runs across rather than diagonally for a reason that is nothing to do
with taste: a diagonal ramp depends on x, so the same letter at two different
places on the line becomes two different sets of tiles, and the logo alone came
to 181 of the 256 characters a page holds. Banding by y only means every 'T' in
the title is the same 'T'.

**The stars.** Same idea, three entries rotated at a different rate, so the
field twinkles without a single tile being rewritten.

Everything else is static. The sky is one flat colour and the H-DMA gradient
already on channel 1 does the shading, which is why it costs one tile.
"""
import math

import snesgfx as g

W, H = 32, 28                   # tiles
PX, PY = W * 8, H * 8           # 256 x 224

# Palette. Slot 0 is the backdrop and is never drawn.
INK      = 0
SKY      = 1
HAZE     = 2
STAR_A   = 3
STAR_B   = 4
STAR_C   = 5
MOON     = 6
MOON_HI  = 7
RIDGE_F  = 8
RIDGE_N  = 9
TREE     = 10
WINDOW   = 11
LOGO0    = 12                   # four-step shine ramp, rotated in CGRAM
LOGO1    = 13
LOGO2    = 14
LOGO3    = 15

PAL = [
    (0x08, 0x08, 0x18),         # 0 ink
    (0x20, 0x20, 0x50),         # 1 sky      (H-DMA darkens it upward)
    (0x48, 0x38, 0x70),         # 2 haze
    (0x60, 0x60, 0x90),         # 3 star dim
    (0xA8, 0xA8, 0xD0),         # 4 star mid
    (0xF8, 0xF8, 0xFF),         # 5 star bright
    (0xD8, 0xD0, 0xA8),         # 6 moon
    (0xF8, 0xF8, 0xE0),         # 7 moon highlight
    (0x30, 0x2C, 0x58),         # 8 far ridge
    (0x20, 0x1C, 0x3C),         # 9 near ridge
    (0x14, 0x12, 0x24),         # 10 trees and roofs
    (0xF8, 0xC0, 0x50),         # 11 a lit window
    (0x70, 0x48, 0x18),         # 12 logo, bronze
    (0xB8, 0x84, 0x28),         # 13 logo, gold
    (0xF0, 0xC8, 0x60),         # 14 logo, bright gold
    (0xF8, 0xF0, 0xC0),         # 15 logo, pale
]


class Img:
    """A plain indexed bitmap. Big enough that drawing straight into it and
    cutting tiles afterwards is simpler than thinking in tiles."""

    def __init__(self, w, h, fill=0):
        self.w, self.h = w, h
        self.px = [[fill] * w for _ in range(h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return 0

    def rect(self, x, y, w, h, c):
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.set(i, j, c)

    def disc(self, cx, cy, r, c):
        for j in range(int(cy - r) - 1, int(cy + r) + 2):
            for i in range(int(cx - r) - 1, int(cx + r) + 2):
                if (i - cx) ** 2 + (j - cy) ** 2 <= r * r:
                    self.set(i, j, c)


class Rng:
    def __init__(self, seed):
        self.s = seed & 0x7FFFFFFF

    def next(self):
        self.s = (self.s * 1103515245 + 12345) & 0x7FFFFFFF
        return self.s >> 16

    def span(self, a, b):
        return a + self.next() % (b - a + 1)

    def chance(self, pct):
        return self.next() % 100 < pct


# ---- the letterform ------------------------------------------------------
#
# A 5x7 block alphabet, scaled up and given a shine ramp. Only the letters the
# title needs -- there is no reason for the title screen to carry a font.

GLYPHS = {
    'T': ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    'U': ["#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."],
    'N': ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
    'G': [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    'S': [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    'A': [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    'H': ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    'R': ["####.", "#...#", "#...#", "####.", "#..#.", "#...#", "#...#"],
    ' ': [".....", ".....", ".....", ".....", ".....", ".....", "....."],
}


def draw_word(img, word, x0, y0, scale, band=6):
    """Letters at `scale`, filled with the four-step ramp chosen by a diagonal
    band. Rotating those four palette entries is what makes the shine travel.

    Drawn twice: once as a hard outline one pixel out in every direction, then
    the face on top. Without the outline the gold sits directly on the sky and
    the whole thing reads as flat."""
    pen = x0
    for chx in word:
        rows = GLYPHS[chx]
        for ry, row in enumerate(rows):
            for rx, cell in enumerate(row):
                if cell != '#':
                    continue
                px = pen + rx * scale
                py = y0 + ry * scale
                for dy in range(-1, scale + 1):
                    for dx in range(-1, scale + 1):
                        img.set(px + dx, py + dy, INK)
        pen += (len(rows[0]) + 1) * scale

    pen = x0
    for chx in word:
        rows = GLYPHS[chx]
        for ry, row in enumerate(rows):
            for rx, cell in enumerate(row):
                if cell != '#':
                    continue
                px = pen + rx * scale
                py = y0 + ry * scale
                for dy in range(scale):
                    for dx in range(scale):
                        x, y = px + dx, py + dy
                        step = (y // band) % 4
                        img.set(x, y, LOGO0 + step)
        pen += (len(rows[0]) + 1) * scale
    return pen - x0 - scale


def word_width(word, scale):
    return sum((len(GLYPHS[c][0]) + 1) * scale for c in word) - scale


# ---- the picture ---------------------------------------------------------

def ridgeline(img, base, amp, wavelen, colour, seed, jag=0):
    """A silhouette: everything under the curve is filled. Two of these with
    different colours is most of what a night skyline is."""
    rng = Rng(seed)
    prev = None
    for x in range(img.w):
        h = base + amp * math.sin(x / wavelen) \
            + (amp * 0.4) * math.sin(x / (wavelen * 0.37) + 1.1)
        if jag:
            h += rng.span(-jag, jag)
        # Snapped to even scanlines. A smooth curve gives almost every tile
        # along the edge a different profile; halving the distinct heights
        # halves the characters the skyline costs, and at this scale nobody
        # can see the difference between a ridge and a ridge rounded to two
        # pixels.
        top = int(h) & ~1
        if prev is not None and abs(top - prev) > 1:
            step = 1 if top > prev else -1
            for t in range(prev, top, step):
                img.rect(x, t, 1, img.h - t, colour)
        img.rect(x, top, 1, img.h - top, colour)
        prev = top


def build():
    img = Img(PX, PY, SKY)
    rng = Rng(0x7A17)

    # --- sky ---------------------------------------------------------------
    # One flat colour: the H-DMA gradient on channel 1 does the shading, so a
    # painted gradient would only fight it and cost a hundred tiles.
    img.rect(0, PY - 90, PX, 30, HAZE)

    # --- stars -------------------------------------------------------------
    # At most one star per 8x8 cell, and only ever at one of four offsets
    # inside it. Scattered freely, a one-pixel star lands at an arbitrary place
    # in its tile and so makes that tile unique -- a hundred and fifty stars is
    # a hundred and fifty characters, which is more than half the page for
    # something the player reads as texture. Four offsets and three colours is
    # twelve characters for the same sky.
    SPOTS = ((2, 3), (5, 1), (1, 6), (6, 4))
    for ty in range(0, (PY - 88) // 8):
        for tx in range(W):
            if not rng.chance(26):
                continue
            if 4 <= ty <= 15 and 1 <= tx <= 30:
                continue                    # the logo lives here
            if ty > (PY - 128) // 8 and rng.chance(55):
                continue                    # thin them towards the haze
            ox, oy = SPOTS[rng.next() % 4]
            img.set(tx * 8 + ox, ty * 8 + oy,
                    STAR_C if rng.chance(18)
                    else STAR_B if rng.chance(40) else STAR_A)

    # --- moon --------------------------------------------------------------
    mx, my, mr = 216, 26, 15
    img.disc(mx, my, mr + 1, HAZE)
    img.disc(mx, my, mr, MOON)
    img.disc(mx - 4, my - 5, mr - 6, MOON_HI)
    for _ in range(9):                      # craters, so it is not a disc
        cx = rng.span(mx - mr + 5, mx + mr - 5)
        cy = rng.span(my - mr + 5, my + mr - 5)
        if (cx - mx) ** 2 + (cy - my) ** 2 < (mr - 4) ** 2:
            img.disc(cx, cy, rng.span(1, 3), MOON)

    # --- ridges ------------------------------------------------------------
    ridgeline(img, PY - 74, 9, 41, RIDGE_F, 0x1234)
    ridgeline(img, PY - 52, 7, 29, RIDGE_N, 0x5678)

    # --- the village -------------------------------------------------------
    # Roofs along the bottom, a few windows still lit. Somebody is awake; it
    # is just not enough of them.
    ground = PY - 30
    img.rect(0, ground, PX, PY - ground, TREE)
    # Roofs from three fixed shapes on an 8-pixel grid. A free-form skyline
    # makes almost every tile along it unique; three motifs that always start
    # on a tile boundary repeat all the way across.
    ROOFS = ((16, 10), (24, 14), (16, 14))
    x = 0
    while x < PX - 8:
        w, h = ROOFS[rng.next() % 3]
        if x + w > PX:
            break
        top = ground - h
        for i in range(w):
            d = abs(i - w // 2)
            img.rect(x + i, top + d // 2, 1, ground - top - d // 2, TREE)
        if rng.chance(50):
            img.rect(x + w // 2 - 1, top + h // 2 + 2, 3, 3, WINDOW)
        x += w + 8 * rng.span(0, 1)

    # palms along the ridge, because it is Indonesia and not Lombardy
    for _ in range(10):
        px = 8 * rng.span(1, (PX // 8) - 2) + 4
        py = ground - 4
        img.rect(px, py - 14, 1, 14, TREE)
        for a in range(-3, 4):
            img.rect(px + a, py - 15 - abs(a) // 2, 1, 2, TREE)

    # --- the logo ----------------------------------------------------------
    # Two sizes, because "TUNG TUNG" is nine characters and "SAHUR" is five:
    # set at one scale the top line runs off both edges of a 256-pixel screen.
    band = 6
    w1 = word_width('TUNG TUNG', 4)
    draw_word(img, 'TUNG TUNG', (PX - w1) // 2, 46, 4, band)
    w2 = word_width('SAHUR', 5)
    draw_word(img, 'SAHUR', (PX - w2) // 2, 84, 5, band)

    return img


# ---- tiles ---------------------------------------------------------------

def cut(img):
    """Dedup 8x8 cells, with horizontal and vertical flips counted as the same
    tile -- a symmetric skyline pays for that several times over, and the
    tilemap entry has the flip bits anyway."""
    pool = {}
    order = []
    entries = []
    for ty in range(H):
        for tx in range(W):
            cell = tuple(tuple(img.px[ty * 8 + y][tx * 8 + x] for x in range(8))
                         for y in range(8))
            hf = tuple(tuple(reversed(r)) for r in cell)
            vf = tuple(reversed(cell))
            hv = tuple(reversed(hf))
            for key, fh, fv in ((cell, 0, 0), (hf, 1, 0),
                                (vf, 0, 1), (hv, 1, 1)):
                if key in pool:
                    entries.append((pool[key], fh, fv))
                    break
            else:
                idx = len(order)
                pool[cell] = idx
                order.append(cell)
                entries.append((idx, 0, 0))
    return order, entries


def generate_title():
    img = build()
    tiles, entries = cut(img)
    if len(tiles) > 256:
        raise SystemExit("title needs %d characters, a page holds 256"
                         % len(tiles))

    sheet = g.Sheet(256)
    for i, cell in enumerate(tiles):
        ox, oy = sheet.origin(i)
        for y in range(8):
            for x in range(8):
                sheet.set(ox + x, oy + y, cell[y][x])

    # Palette 2. Slots 0 and 1 are the field's, 3 is the text layer's, and
    # the title borrows BG1's battle window -- which is already pointed at
    # palette 2 by the tilemap the backdrops use.
    words = []
    for idx, fh, fv in entries:
        words.append(g.map_entry(idx, pal=2, hflip=fh, vflip=fv))

    total = 0
    total += g.write('title.pic', sheet.to_pic())
    total += g.write('title.map', g.map_bin(words))
    total += g.write('title.pal', g.palette_bin(PAL))
    with open('src/titlemap.h', 'w') as f:
        f.write("/* Generated by gen_title.py -- do not edit. */\n"
                "#ifndef TITLEMAP_H\n#define TITLEMAP_H\n\n"
                "/* The two runs of CGRAM entries the title rotates. Rotating\n"
                " * the logo ramp walks the shine down the letters; rotating\n"
                " * the star ramp makes the field twinkle. Both are a handful\n"
                " * of $2122 writes and no tile is ever touched. */\n")
        f.write("#define TITLE_LOGO0 %d\n#define TITLE_LOGO_N 4\n" % LOGO0)
        f.write("#define TITLE_STAR0 %d\n#define TITLE_STAR_N 3\n\n" % STAR_A)
        f.write("static const u16 titleLogoRamp[4] = {\n    ")
        f.write(", ".join("0x%04X" % g.rgb15(*PAL[c])
                          for c in (LOGO0, LOGO1, LOGO2, LOGO3)))
        f.write("\n};\n\n")
        f.write("static const u16 titleStarRamp[3] = {\n    ")
        f.write(", ".join("0x%04X" % g.rgb15(*PAL[c])
                          for c in (STAR_A, STAR_B, STAR_C)))
        f.write("\n};\n\n#endif\n")
    print("title: %d characters, %d bytes" % (len(tiles), total))
    return len(tiles)


if __name__ == '__main__':
    generate_title()
