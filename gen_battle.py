#!/usr/bin/env python3
"""Six battle backdrops, one per region, plus the dawn recolour.

Battle keeps its own character and tilemap windows ($6000 and $5400), so
entering a fight is a register write. The backdrop for the current region is
uploaded when the region loads -- the party is already behind a fade at that
point and the transfer is free.

Every backdrop is the same builder with different knobs: a sky band, a horizon
silhouette, and a floor. That is not laziness, it is what keeps six of them
inside 256 characters each -- the dedup pass only collapses what repeats, and a
repeating dither is the only way a 256x256 image fits a 256-character page.

Nothing uses palette index 0. Index 0 is transparent (ppu-graphics.md,
"all-zero dot data = transparent") and a backdrop is the one thing that has to
be opaque everywhere.
"""
import math

import snesgfx as g

W = H = 256
COLS = ROWS = 32

# Slot layout, same idea as terrain.py: 1 zenith .. 5 haze, 6 light source,
# 7-8 horizon shapes, 9-13 floor ramp, 14 dust, 15 specular.
NIGHT = [
    (0, 0, 0), (8, 8, 24), (16, 16, 48), (28, 28, 76), (48, 48, 112),
    (96, 104, 168), (248, 248, 232), (24, 24, 56), (40, 40, 80),
    (56, 48, 72), (80, 68, 92), (108, 96, 120), (140, 128, 148),
    (36, 32, 52), (168, 160, 184), (232, 232, 248),
]

FOREST = [
    (0, 0, 0), (6, 14, 14), (10, 24, 22), (16, 36, 32), (24, 52, 44),
    (44, 84, 68), (196, 224, 190), (10, 20, 18), (18, 34, 28),
    (20, 34, 26), (30, 50, 38), (44, 70, 52), (62, 94, 68),
    (12, 22, 18), (90, 128, 92), (222, 240, 214),
]

SHORE = [
    (0, 0, 0), (8, 10, 30), (14, 20, 52), (22, 34, 82), (36, 56, 122),
    (92, 124, 190), (248, 250, 236), (12, 18, 44), (20, 30, 66),
    (56, 50, 42), (86, 76, 60), (122, 108, 84), (160, 144, 112),
    (34, 30, 26), (200, 188, 156), (248, 250, 255),
]

SALT = [
    (0, 0, 0), (18, 16, 34), (30, 26, 54), (46, 40, 78), (70, 62, 108),
    (128, 122, 170), (250, 248, 255), (34, 30, 52), (52, 46, 76),
    (96, 92, 110), (134, 130, 148), (176, 174, 190), (212, 210, 224),
    (62, 58, 76), (232, 230, 242), (255, 255, 255),
]

IRON = [
    (0, 0, 0), (10, 10, 14), (18, 18, 26), (28, 28, 40), (44, 42, 56),
    (96, 74, 60), (248, 196, 96), (16, 16, 22), (30, 30, 40),
    (38, 40, 50), (60, 64, 78), (88, 94, 112), (122, 130, 152),
    (24, 24, 32), (150, 160, 184), (240, 240, 248),
]

VOID = [
    (0, 0, 0), (4, 4, 10), (8, 6, 16), (14, 10, 26), (22, 16, 40),
    (58, 40, 88), (240, 236, 255), (10, 8, 18), (18, 14, 30),
    (16, 14, 26), (26, 22, 40), (40, 34, 60), (58, 50, 84),
    (10, 8, 16), (96, 84, 132), (255, 255, 255),
]

# The sky the Hush spent a month preventing. Same characters, repainted.
DAWN = [
    (0, 0, 0), (72, 16, 40), (120, 32, 48), (176, 56, 48), (232, 104, 56),
    (248, 176, 96), (255, 248, 216), (88, 32, 48), (120, 48, 56),
    (96, 56, 56), (136, 88, 72), (176, 124, 96), (216, 168, 128),
    (64, 36, 40), (232, 200, 160), (255, 240, 216),
]


def build(horizon, stars, disc, ridges, floor_style, ceiling):
    px = [[1] * W for _ in range(H)]

    # --- sky: a four-band ramp, dithered at the seams ---------------------
    for y in range(horizon):
        t = y / float(horizon)
        band = 1 + int(t * 4.0)
        frac = (t * 4.0) - int(t * 4.0)
        for x in range(W):
            v = band
            # An ordered dither across the boundary. A hard seam across a
            # 256-dot sky is the one thing that gives a gradient away.
            if frac > 0.5 and ((x + y) & 3) == 0:
                v = min(5, band + 1)
            px[y][x] = min(5, v)

    if ceiling:
        # A roof rather than a sky: girders instead of a gradient.
        for y in range(horizon):
            for x in range(W):
                px[y][x] = 2 if (y // 12 + x // 40) & 1 else 3
            if y % 24 < 3:
                for x in range(W):
                    px[y][x] = 8
            if y % 24 == 3:
                for x in range(0, W, 40):
                    for k in range(4):
                        px[y][min(W - 1, x + k)] = 6

    # --- stars ------------------------------------------------------------
    for i in range(stars):
        sx = int((math.sin(i * 12.9898) * 43758.5453) % 1.0 * W)
        sy = int((math.sin(i * 78.233) * 12345.6789) % 1.0 * (horizon - 12))
        if sy < 2:
            continue
        px[sy][sx] = 6
        if i % 11 == 0:
            px[sy - 1][sx] = 5
            px[sy + 1][sx] = 5
            px[sy][(sx - 1) % W] = 5
            px[sy][(sx + 1) % W] = 5

    # --- the light source, if this region has one -------------------------
    if disc:
        mx, my, mr = disc
        for y in range(my - mr - 1, my + mr + 2):
            for x in range(mx - mr - 1, mx + mr + 2):
                if not (0 <= y < H and 0 <= x < W):
                    continue
                d = math.hypot(x - mx, y - my)
                if d <= mr:
                    px[y][x] = 6
                elif d <= mr + 1.2:
                    px[y][x] = 5
        for y in range(my - mr, my + mr):
            for x in range(mx - mr, mx + mr):
                if not (0 <= y < H and 0 <= x < W):
                    continue
                if math.hypot(x - mx + 4, y - my + 3) < 3.0 and px[y][x] == 6:
                    px[y][x] = 5

    # --- horizon silhouettes ---------------------------------------------
    def ridge(amp, base, freq, phase, colour, spiky=False):
        for x in range(W):
            if spiky:
                h = base - amp * (0.5 + 0.5 * abs(math.sin(x * freq + phase)))
            else:
                h = base - amp * (0.6 * math.sin(x * freq + phase)
                                  + 0.4 * math.sin(x * freq * 2.3 + phase * 1.7))
            for y in range(int(h), horizon):
                if 0 <= y < H:
                    px[y][x] = colour

    for amp, base, freq, phase, colour, spiky in ridges:
        ridge(amp, horizon + base, freq, phase, colour, spiky)

    # --- floor ------------------------------------------------------------
    #
    # The dither repeats every 8 dots horizontally on purpose: a whole band
    # then collapses to one or two characters instead of thirty-two.
    for y in range(horizon, H):
        t = (y - horizon) / float(H - horizon)
        base = 9 + int(t * 3.0)
        for x in range(W):
            v = base
            if floor_style == 'plate':
                if (y % 16) < 2 or (x % 32) < 2:
                    v = 9
                elif ((x // 32) + (y // 16)) & 1:
                    v = min(12, base + 1)
            elif floor_style == 'void':
                v = 9 if ((x * 7 + y * 3) % 97) else 12
            else:
                p = ((x & 7) + (y & 7) * 3) & 7
                if p < 2:
                    v = min(12, base + 1)
                elif p == 7:
                    v = max(9, base - 1)
            px[y][x] = v

    if floor_style == 'dunes':
        for i in range(3):
            y0 = horizon + 16 + i * 40
            for x in range(W):
                h = y0 + int(5 * math.sin(x * 0.028 + i * 1.9))
                for k in range(3):
                    if h + k < H:
                        px[h + k][x] = 13 if k else 12
    return px


REGIONS = [
    dict(key='night', pal=NIGHT, horizon=108, stars=52, disc=(208, 34, 13),
         ridges=[(11, -6, 0.021, 0.0, 7, False), (7, -1, 0.037, 2.2, 8, False)],
         floor='dunes', ceiling=False),
    dict(key='forest', pal=FOREST, horizon=120, stars=18, disc=None,
         ridges=[(26, 4, 0.11, 0.0, 7, True), (18, 10, 0.17, 1.4, 8, True)],
         floor='dunes', ceiling=False),
    dict(key='shore', pal=SHORE, horizon=96, stars=64, disc=(48, 30, 15),
         ridges=[(8, -2, 0.018, 1.0, 7, False)],
         floor='flat', ceiling=False),
    dict(key='salt', pal=SALT, horizon=104, stars=70, disc=(196, 28, 11),
         ridges=[(6, -2, 0.014, 0.5, 7, False)],
         floor='dunes', ceiling=False),
    dict(key='iron', pal=IRON, horizon=96, stars=0, disc=None,
         ridges=[(14, 2, 0.09, 0.0, 8, True)],
         floor='plate', ceiling=True),
    dict(key='void', pal=VOID, horizon=150, stars=110, disc=None,
         ridges=[],
         floor='void', ceiling=False),
]


def cut(px, name):
    index = {}
    tiles = []
    entries = []
    for ty in range(ROWS):
        for tx in range(COLS):
            cell = [[px[ty * 8 + y][tx * 8 + x] for x in range(8)]
                    for y in range(8)]
            key = tuple(tuple(r) for r in cell)
            if key not in index:
                index[key] = len(tiles)
                tiles.append(cell)
            entries.append(g.map_entry(index[key], pal=2, prio=0))
    if len(tiles) > 256:
        raise SystemExit("backdrop %s needs %d characters, a page holds 256"
                         % (name, len(tiles)))
    sheet = g.Sheet(256)
    for i, c in enumerate(tiles):
        ox, oy = sheet.origin(i)
        for y in range(8):
            for x in range(8):
                sheet.set(ox + x, oy + y, c[y][x])
    return sheet, entries, len(tiles)


def generate_battle():
    lines = []
    for r in REGIONS:
        px = build(r['horizon'], r['stars'], r['disc'], r['ridges'],
                   r['floor'], r['ceiling'])
        sheet, entries, n = cut(px, r['key'])
        g.write('bg_%s.pic' % r['key'], sheet.to_pic())
        g.write('bg_%s.map' % r['key'], g.map_bin(entries))
        g.write('bg_%s.pal' % r['key'], g.palette_bin(r['pal']))
        lines.append((r['key'], n))

    # The epilogue reuses the first backdrop's characters under a dawn palette.
    g.write('bg_dawn.pal', g.palette_bin(DAWN))

    with open('bgdata.asm', 'w') as f:
        f.write("; Generated by gen_battle.py -- do not edit.\n"
                "; Standalone unit; see the note in worlddata.asm.\n"
                '.include "hdr.asm"\n\n')
        for r in REGIONS:
            k = r['key']
            f.write('.section ".rodata_bg_%s" superfree\n' % k)
            f.write('bg_%s_pic: .incbin "bg_%s.pic"\n' % (k, k))
            f.write('bg_%s_map: .incbin "bg_%s.map"\n' % (k, k))
            f.write('bg_%s_pal: .incbin "bg_%s.pal"\n' % (k, k))
            f.write('.ends\n\n')
        f.write('.section ".rodata_bg_dawn" superfree\n'
                'bg_dawn_pal: .incbin "bg_dawn.pal"\n.ends\n')

    with open('src/bgmap.h', 'w') as f:
        f.write("/* Generated by gen_battle.py -- do not edit. */\n"
                "#ifndef BGMAP_H\n#define BGMAP_H\n\n")
        f.write("#define BACKDROP_COUNT %d\n\n" % len(REGIONS))
        for r in REGIONS:
            k = r['key']
            f.write("extern char bg_%s_pic, bg_%s_map, bg_%s_pal;\n" % (k, k, k))
        f.write("extern char bg_dawn_pal;\n\n")
        for part in ('pic', 'map', 'pal'):
            f.write("static u8 *backdrop%s(u8 n) {\n    switch (n) {\n"
                    % part.capitalize())
            for i, r in enumerate(REGIONS[:-1]):
                f.write("    case %d:\n        return (u8 *)&bg_%s_%s;\n"
                        % (i, r['key'], part))
            f.write("    default:\n        return (u8 *)&bg_%s_%s;\n"
                    % (REGIONS[-1]['key'], part))
            f.write("    }\n}\n\n")
        f.write("#endif\n")

    print("backdrops:")
    for k, n in lines:
        print("   %-6s %3d characters" % (k, n))


if __name__ == '__main__':
    generate_battle()
