#!/usr/bin/env python3
"""The BG2 character sheet: glyphs, status icons, gauges, window frame.

One 256-character 4bpp sheet at VRAM $2000 holds everything the text layer can
ever draw. Its palette is the one FF-style windows need -- white text on a
blue vertical gradient -- and 16 colours is why the window layer is a 16-colour
BG at all rather than BG3's four (see the layer notes in src/ttrpg.h).

Glyphs are a 5x7 cell drawn at (1,0) with a one-dot shadow at (+1,+1). The
shadow is the whole reason the text reads over a mid-blue fill: pure white on
blue is legible but flat, and every FF window font has the dark offset.
"""
import snesgfx as g

# ---- palette ------------------------------------------------------------
#
# Slots 5-10 are the window gradient, dark at the top edge to light at the
# bottom. Slot 0 is never displayed (A-17) but the window fill needs to be
# opaque, so nothing in a window uses it.

PAL = [
    (0, 0, 0),          # 0  transparent
    (248, 248, 248),    # 1  text
    (32, 32, 64),       # 2  text shadow
    (144, 160, 208),    # 3  frame inner bevel
    (248, 248, 248),    # 4  frame outer
    (16, 24, 56),       # 5  gradient 0 (top)
    (24, 36, 72),       # 6
    (32, 48, 88),       # 7
    (40, 60, 104),      # 8
    (48, 72, 120),      # 9
    (56, 84, 136),      # 10 gradient 5 (bottom)
    (248, 216, 72),     # 11 gold -- gauges, cursors, numbers that matter
    (248, 88, 56),      # 12 red -- damage, critical HP
    (88, 216, 88),      # 13 green -- healing
    (144, 144, 160),    # 14 grey -- disabled menu entries
    (0, 0, 0),          # 15 black -- letterbox, shadow under the title
]

C_TEXT, C_SHADOW, C_BEVEL, C_FRAME = 1, 2, 3, 4
GRAD0 = 5
C_GOLD, C_RED, C_GREEN, C_GREY, C_BLACK = 11, 12, 13, 14, 15

# ---- 5x7 glyph table ----------------------------------------------------

FONT = {
    ' ': "...../...../...../...../...../...../.....",
    '!': "..#../..#../..#../..#../..#../...../..#..",
    '"': ".#.#./.#.#./...../...../...../...../.....",
    '#': ".#.#./#####/.#.#./#####/.#.#./...../.....",
    '$': "..#../.####/#.#../.###./..#.#/####./..#..",
    '%': "##..#/##..#/...#./..#../.#.../#..##/#..##",
    '&': ".##../#..#./.##../#.#.#/#..##/#..#./.##.#",
    "'": "..#../..#../...../...../...../...../.....",
    '(': "...#./..#../.#.../.#.../.#.../..#../...#.",
    ')': ".#.../..#../...#./...#./...#./..#../.#...",
    '*': "...../#.#.#/.###./#####/.###./#.#.#/.....",
    '+': "...../..#../..#../#####/..#../..#../.....",
    ',': "...../...../...../...../..##./..#../.#...",
    '-': "...../...../...../#####/...../...../.....",
    '.': "...../...../...../...../...../..##./..##.",
    '/': "....#/...#./..#../.#.../#..../...../.....",
    '0': ".###./#...#/#..##/#.#.#/##..#/#...#/.###.",
    '1': "..#../.##../..#../..#../..#../..#../.###.",
    '2': ".###./#...#/....#/...#./..#../.#.../#####",
    '3': "#####/...#./..##./....#/....#/#...#/.###.",
    '4': "...#./..##./.#.#./#..#./#####/...#./...#.",
    '5': "#####/#..../####./....#/....#/#...#/.###.",
    '6': "..##./.#.../#..../####./#...#/#...#/.###.",
    '7': "#####/....#/...#./..#../.#.../.#.../.#...",
    '8': ".###./#...#/#...#/.###./#...#/#...#/.###.",
    '9': ".###./#...#/#...#/.####/....#/...#./.##..",
    ':': "...../..##./..##./...../..##./..##./.....",
    ';': "...../..##./..##./...../..##./..#../.#...",
    '<': "...#./..#../.#.../#..../.#.../..#../...#.",
    '=': "...../...../#####/...../#####/...../.....",
    '>': ".#.../..#../...#./....#/...#./..#../.#...",
    '?': ".###./#...#/....#/...#./..#../...../..#..",
    '@': ".###./#...#/....#/.##.#/#.#.#/#.#.#/.####",
    'A': "..#../.#.#./#...#/#...#/#####/#...#/#...#",
    'B': "####./#...#/#...#/####./#...#/#...#/####.",
    'C': ".###./#...#/#..../#..../#..../#...#/.###.",
    'D': "###../#..#./#...#/#...#/#...#/#..#./###..",
    'E': "#####/#..../#..../####./#..../#..../#####",
    'F': "#####/#..../#..../####./#..../#..../#....",
    'G': ".###./#...#/#..../#.###/#...#/#...#/.####",
    'H': "#...#/#...#/#...#/#####/#...#/#...#/#...#",
    'I': ".###./..#../..#../..#../..#../..#../.###.",
    'J': "....#/....#/....#/....#/#...#/#...#/.###.",
    'K': "#...#/#..#./#.#../##.../#.#../#..#./#...#",
    'L': "#..../#..../#..../#..../#..../#..../#####",
    'M': "#...#/##.##/#.#.#/#.#.#/#...#/#...#/#...#",
    'N': "#...#/##..#/#.#.#/#..##/#...#/#...#/#...#",
    'O': ".###./#...#/#...#/#...#/#...#/#...#/.###.",
    'P': "####./#...#/#...#/####./#..../#..../#....",
    'Q': ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#",
    'R': "####./#...#/#...#/####./#.#../#..#./#...#",
    'S': ".####/#..../#..../.###./....#/....#/####.",
    'T': "#####/..#../..#../..#../..#../..#../..#..",
    'U': "#...#/#...#/#...#/#...#/#...#/#...#/.###.",
    'V': "#...#/#...#/#...#/#...#/#...#/.#.#./..#..",
    'W': "#...#/#...#/#...#/#.#.#/#.#.#/##.##/#...#",
    'X': "#...#/#...#/.#.#./..#../.#.#./#...#/#...#",
    'Y': "#...#/#...#/.#.#./..#../..#../..#../..#..",
    'Z': "#####/....#/...#./..#../.#.../#..../#####",
    '[': "..###/..#../..#../..#../..#../..#../..###",
    '\\': "#..../.#.../..#../...#./....#/...../.....",
    ']': "###../..#../..#../..#../..#../..#../###..",
    '^': "..#../.#.#./#...#/...../...../...../.....",
    '_': "...../...../...../...../...../...../#####",
    '`': ".#.../..#../...../...../...../...../.....",
    'a': "...../.###./....#/.####/#...#/#...#/.####",
    'b': "#..../#..../####./#...#/#...#/#...#/####.",
    'c': "...../.####/#..../#..../#..../#..../.####",
    'd': "....#/....#/.####/#...#/#...#/#...#/.####",
    'e': "...../.###./#...#/#####/#..../#..../.###.",
    'f': "..##./.#.../####./.#.../.#.../.#.../.#...",
    'g': "...../.####/#...#/#...#/.####/....#/.###.",
    'h': "#..../#..../####./#...#/#...#/#...#/#...#",
    'i': "..#../...../.##../..#../..#../..#../.###.",
    'j': "...#./...../...#./...#./...#./#..#./.##..",
    'k': "#..../#..../#..#./#.#../##.../#.#../#..#.",
    'l': ".##../..#../..#../..#../..#../..#../.###.",
    'm': "...../##.#./#.#.#/#.#.#/#.#.#/#.#.#/#.#.#",
    'n': "...../####./#...#/#...#/#...#/#...#/#...#",
    'o': "...../.###./#...#/#...#/#...#/#...#/.###.",
    'p': "...../####./#...#/#...#/####./#..../#....",
    'q': "...../.####/#...#/#...#/.####/....#/....#",
    'r': "...../#.##./##..#/#..../#..../#..../#....",
    's': "...../.####/#..../.###./....#/....#/####.",
    't': ".#.../.#.../####./.#.../.#.../.#..#/..##.",
    'u': "...../#...#/#...#/#...#/#...#/#..##/.##.#",
    'v': "...../#...#/#...#/#...#/#...#/.#.#./..#..",
    'w': "...../#...#/#...#/#.#.#/#.#.#/#.#.#/.#.#.",
    'x': "...../#...#/.#.#./..#../..#../.#.#./#...#",
    'y': "...../#...#/#...#/#...#/.####/....#/.###.",
    'z': "...../#####/...#./..#../.#.../#..../#####",
    '{': "...##/..#../..#../.#.../..#../..#../...##",
    '|': "..#../..#../..#../..#../..#../..#../..#..",
    '}': "##.../..#../..#../...#./..#../..#../##...",
    '~': "...../..#.#/.#.#./...../...../...../.....",
}

# ---- 8x8 icons ----------------------------------------------------------
#
# Drawn as full cells because they carry more than one colour. Digits in the
# art are palette indices; see PAL above. 'b' = 11 (gold), 'c' = 12 (red),
# 'd' = 13 (green), 'e' = 14 (grey), 'f' = 15 (black).

ICONS = {
    'cursor': [           # the hand FF points at a menu entry with
        "........",
        "..bb....",
        "..bbbb..",
        "..bbbbbb",
        "..bbbbbb",
        "..bbbb..",
        "..bb....",
        "........",
    ],
    'sleep': [            # Z -- the enemy status the whole game is about
        "........",
        ".111111.",
        ".2222#1.",
        "....#12.",
        "...#12..",
        "..#1....",
        ".111111.",
        "..222222",
    ],
    'dead': [
        "........",
        "..1111..",
        ".111111.",
        ".1f11f1.",
        ".111111.",
        "..1111..",
        ".1.1.1..",
        "........",
    ],
    'poison': [
        "........",
        "...dd...",
        "..dddd..",
        ".dddddd.",
        ".dd11dd.",
        ".dddddd.",
        "..dddd..",
        "...22...",
    ],
    'haste': [
        "........",
        "....bb..",
        "...bb...",
        "..bbbb..",
        "...bb...",
        "..bb....",
        ".bb.....",
        "........",
    ],
    'slow': [
        "........",
        "..eeee..",
        ".e1111e.",
        ".e11e1e.",
        ".e1eeee.",
        ".e1111e.",
        "..eeee..",
        "........",
    ],
    'mp': [                # the little star next to MP totals
        "........",
        "...1....",
        "..111...",
        ".11111..",
        "..111...",
        ".1...1..",
        "........",
        "........",
    ],
    'drum': [              # Tung's kentongan -- the ITEM/skill marker
        "........",
        ".bbbbbb.",
        ".b1111b.",
        ".b1111b.",
        ".bbbbbb.",
        "..b..b..",
        "..b..b..",
        "........",
    ],
}

ICON_ORDER = ['cursor', 'sleep', 'dead', 'poison', 'haste', 'slow', 'mp', 'drum']

TILE_GLYPH0 = 0x00
TILE_ICON = 0x60
TILE_BIG = 0x70          # 16x16 logo letters, 2x2 characters each
TILE_GAUGE = 0xC0        # 0xC0-0xC8: 0..8 dots of fill
TILE_WIN = 0xE0

# "TUNG TUNG SAHUR" needs eight distinct letters, and eight 16x16 letters is
# exactly the two sheet rows at 0x70/0x80. A full 16x16 alphabet would cost
# 104 characters for a screen that shows fifteen of them.
BIG_LETTERS = "TUNGSAHR"


def _glyph(sheet, index, art):
    rows = art.split('/')
    ox, oy = sheet.origin(index)
    # Shadow first, then the glyph over it: where they overlap the glyph wins,
    # which is what makes the shadow a rim rather than a smear.
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == '#':
                sheet.set(ox + dx + 2, oy + dy + 1, C_SHADOW)
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == '#':
                sheet.set(ox + dx + 1, oy + dy, C_TEXT)


def _big_letters(sheet):
    """The title logo alphabet: the 5x7 glyph at 2x, ramped white-gold-orange
    top to bottom, ringed in black, with a hard shadow one dot down-right.

    Letter i occupies characters (0x70+i*2, +1) over (0x80+i*2, +1) -- the same
    2x2 arrangement a 16x16 OBJ would use, though these are BG characters and
    the title screen places them into the tilemap itself.
    """
    RAMP = [C_TEXT, C_TEXT, 11, 11, 11, 11, 12, 12]      # by scaled row / 2

    for i, ch in enumerate(BIG_LETTERS):
        rows = FONT[ch].split('/')
        base = TILE_BIG + i * 2
        ox, oy = sheet.origin(base)

        body = set()
        for dy, row in enumerate(rows):
            for dx, c in enumerate(row):
                if c != '#':
                    continue
                for sy in range(2):
                    for sx in range(2):
                        body.add((3 + dx * 2 + sx, 1 + dy * 2 + sy))

        for (x, y) in body:                              # shadow
            sheet.set(ox + x + 1, oy + y + 1, C_SHADOW)
        for (x, y) in body:                              # outline
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (x + dx, y + dy) not in body:
                        sheet.set(ox + x + dx, oy + y + dy, C_BLACK)
        for (x, y) in body:                              # the letter itself
            sheet.set(ox + x, oy + y, RAMP[min(7, (y - 1) // 2)])


def _gauges(sheet):
    """Nine tiles: a 1-dot track with 0..8 dots of gold fill.

    Rows 2-5 only, so a gauge drawn on a text row still leaves a gap above and
    below and reads as a bar rather than a solid block.
    """
    for n in range(9):
        base = TILE_GAUGE + n
        ox, oy = sheet.origin(base)
        for y in range(2, 6):
            for x in range(8):
                if x < n:
                    sheet.set(ox + x, oy + y, C_GOLD if y < 4 else 9)
                else:
                    sheet.set(ox + x, oy + y, 7)
        for x in range(8):          # top and bottom rule
            sheet.set(ox + x, oy + 1, C_BEVEL)
            sheet.set(ox + x, oy + 6, 5)


# Window frame tile indices, exported to C so the two cannot drift.
WIN_TL, WIN_T, WIN_TR = TILE_WIN + 0, TILE_WIN + 1, TILE_WIN + 2
WIN_BL, WIN_B, WIN_BR = TILE_WIN + 3, TILE_WIN + 4, TILE_WIN + 5
WIN_L0 = TILE_WIN + 6            # +0..+5, one per gradient step
WIN_R0 = TILE_WIN + 12
WIN_F0 = TILE_WIN + 18
WIN_BLACK = TILE_WIN + 24
GRAD_STEPS = 6


def _window(sheet):
    """The frame: a white outer rule, a steel bevel one dot in, gradient fill.

    Corners and edges carry the gradient step of the row they belong to, which
    is why the left and right edges need one tile per step: a box of any height
    maps its rows onto 0..5 and picks the matching edge tile.
    """
    def fill_cell(index, step, gradient_row=None):
        ox, oy = sheet.origin(index)
        for y in range(8):
            # Inside a fill cell the gradient also steps per dot-row, so a tall
            # box reads as a smooth ramp instead of six visible bands.
            v = GRAD0 + step if gradient_row is None else GRAD0 + gradient_row(y)
            for x in range(8):
                sheet.set(ox + x, oy + y, v)

    for s in range(GRAD_STEPS):
        fill_cell(WIN_F0 + s, s)

        ox, oy = sheet.origin(WIN_L0 + s)
        for y in range(8):
            for x in range(8):
                sheet.set(ox + x, oy + y, GRAD0 + s)
            sheet.set(ox + 0, oy + y, C_FRAME)
            sheet.set(ox + 1, oy + y, C_BEVEL)

        ox, oy = sheet.origin(WIN_R0 + s)
        for y in range(8):
            for x in range(8):
                sheet.set(ox + x, oy + y, GRAD0 + s)
            sheet.set(ox + 7, oy + y, C_FRAME)
            sheet.set(ox + 6, oy + y, C_BEVEL)

    # Top edge: the fill under it is gradient step 0.
    ox, oy = sheet.origin(WIN_T)
    for y in range(8):
        for x in range(8):
            sheet.set(ox + x, oy + y, GRAD0)
    for x in range(8):
        sheet.set(ox + x, oy + 0, C_FRAME)
        sheet.set(ox + x, oy + 1, C_BEVEL)

    ox, oy = sheet.origin(WIN_B)
    for y in range(8):
        for x in range(8):
            sheet.set(ox + x, oy + y, GRAD0 + GRAD_STEPS - 1)
    for x in range(8):
        sheet.set(ox + x, oy + 7, C_FRAME)
        sheet.set(ox + x, oy + 6, C_BEVEL)

    def corner(index, step, left, top):
        ox, oy = sheet.origin(index)
        for y in range(8):
            for x in range(8):
                sheet.set(ox + x, oy + y, GRAD0 + step)
        for i in range(8):
            sheet.set(ox + (0 if left else 7), oy + i, C_FRAME)
            sheet.set(ox + i, oy + (0 if top else 7), C_FRAME)
            sheet.set(ox + (1 if left else 6), oy + i, C_BEVEL)
            sheet.set(ox + i, oy + (1 if top else 6), C_BEVEL)
        # Redo the outer rule: the bevel loop above crosses it at the corner.
        for i in range(8):
            sheet.set(ox + (0 if left else 7), oy + i, C_FRAME)
            sheet.set(ox + i, oy + (0 if top else 7), C_FRAME)

    corner(WIN_TL, 0, True, True)
    corner(WIN_TR, 0, False, True)
    corner(WIN_BL, GRAD_STEPS - 1, True, False)
    corner(WIN_BR, GRAD_STEPS - 1, False, False)

    sheet.rect(WIN_BLACK, 8, 8, C_BLACK)


def generate_font():
    sheet = g.Sheet(256)

    for code in range(32, 128):
        art = FONT.get(chr(code))
        if art:
            _glyph(sheet, TILE_GLYPH0 + code - 32, art)

    pal = {str(d): d for d in range(10)}
    pal.update({'a': 10, 'b': 11, 'c': 12, 'd': 13, 'e': 14, 'f': 15, '#': 15})
    for i, name in enumerate(ICON_ORDER):
        sheet.blit(TILE_ICON + i, ICONS[name], pal=pal)

    _big_letters(sheet)
    _gauges(sheet)
    _window(sheet)

    g.write('font.pic', sheet.to_pic())
    g.write('font.pal', g.palette_bin(PAL))

    # Two recolours of the same 16 slots, differing only in what the glyph
    # body and its shadow are. Battle loads them into BG palettes 0 and 1 --
    # free there, because the backdrop's tilemap only ever names palette 2 --
    # and then red or green text is a palette field in the tilemap entry
    # rather than a second set of characters.
    alert = list(PAL)
    alert[1] = (248, 96, 72)
    alert[2] = (72, 8, 8)
    g.write('fontalert.pal', g.palette_bin(alert))

    good = list(PAL)
    good[1] = (120, 248, 128)
    good[2] = (8, 56, 16)
    g.write('fontgood.pal', g.palette_bin(good))

    sheet.to_png('font-preview.png', PAL)

    with open('src/gfxmap.h', 'w') as f:
        f.write("/* Generated by gen_font.py -- do not edit.\n"
                " * Tile indices into the BG2 character sheet at $2000. */\n"
                "#ifndef GFXMAP_H\n#define GFXMAP_H\n\n")
        f.write("#define WIN_TL   0x%02X\n" % WIN_TL)
        f.write("#define WIN_T    0x%02X\n" % WIN_T)
        f.write("#define WIN_TR   0x%02X\n" % WIN_TR)
        f.write("#define WIN_BL   0x%02X\n" % WIN_BL)
        f.write("#define WIN_B    0x%02X\n" % WIN_B)
        f.write("#define WIN_BR   0x%02X\n" % WIN_BR)
        f.write("#define WIN_L0   0x%02X\n" % WIN_L0)
        f.write("#define WIN_R0   0x%02X\n" % WIN_R0)
        f.write("#define WIN_F0   0x%02X\n" % WIN_F0)
        f.write("#define WIN_BLACK 0x%02X\n" % WIN_BLACK)
        f.write("#define GRAD_STEPS %d\n\n" % GRAD_STEPS)
        for i, name in enumerate(ICON_ORDER):
            f.write("#define ICON_%-8s 0x%02X\n" % (name.upper(), TILE_ICON + i))
        f.write("\n#define GAUGE0   0x%02X\n" % TILE_GAUGE)
        f.write("\n/* Title logo: bigLetterTile(c) gives the top-left character\n"
                " * of a 16x16 letter; +1 is its right half and +0x10 the row\n"
                " * below. Returns 0xFF for a character with no big form. */\n")
        f.write("#define BIG_BASE 0x%02X\n" % TILE_BIG)
        f.write('#define BIG_LETTERS "%s"\n' % BIG_LETTERS)
        f.write("\n#endif\n")

    print("font.pic  %d bytes (256 tiles)" % (256 * 32))


if __name__ == '__main__':
    generate_font()
