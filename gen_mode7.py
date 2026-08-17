#!/usr/bin/env python3
"""The 256-colour Mode 7 vortex used between the field and a battle.

Mode 7 has one fixed 128x128-character map in VRAM's low-byte plane and 256
8x8 characters in its high-byte plane (development manual Appendix A-11 and
A-15).  Keeping those two byte planes as separate files lets
bgInitMapTileSet7 interleave them while it uploads the scene.

The picture is deliberately a tile vocabulary rather than a 1024x1024 bitmap:
concentric wake-rings, spokes and stars select from fewer than 256 hand-built
characters.  Rotation and scale do the motion; no frame of art is streamed.
"""
import math

import snesgfx as g


PALETTE = [
    (0, 0, 0),          # 0 backdrop
    (3, 4, 13),         # 1 deepest night
    (7, 9, 27),         # 2 navy
    (13, 14, 45),       # 3 blue violet
    (23, 22, 67),       # 4 indigo
    (39, 34, 91),       # 5 lit indigo
    (15, 63, 91),       # 6 deep teal
    (25, 111, 134),     # 7 teal
    (66, 177, 174),     # 8 wake glow
    (165, 231, 201),    # 9 pale wake
    (91, 52, 127),      # 10 purple
    (166, 82, 161),     # 11 orchid
    (211, 132, 65),     # 12 old gold
    (244, 197, 111),    # 13 lamplight
    (255, 235, 181),    # 14 flare
    (235, 247, 235),    # 15 star
] + [None] * 240


def tile(base, motif):
    """Return one 8bpp Mode 7 character from a small patterned vocabulary."""
    if base <= 5:
        dim = max(1, base - 1)
        glow = 7 if base < 4 else 8
    elif base <= 9:
        dim = 6
        glow = 9
    elif base <= 11:
        dim = 4
        glow = 11
    else:
        dim = 10
        glow = 14

    px = [[base] * 8 for _ in range(8)]
    for y in range(8):
        for x in range(8):
            if ((x * 3 + y * 5 + motif) & 15) == 0:
                px[y][x] = dim

    if motif == 1:                       # one distant star
        px[3][3] = glow
        px[3][4] = glow
    elif motif == 2:                     # four-point star
        for x, y in ((3, 1), (3, 2), (3, 3), (3, 4), (3, 5),
                     (1, 3), (2, 3), (4, 3), (5, 3)):
            px[y][x] = glow
        px[3][3] = 15
    elif motif == 3:                     # slash, one half of a spoke
        for y in range(8):
            px[y][7 - y] = glow
            if y & 1:
                px[y][6 - y] = glow
    elif motif == 4:                     # backslash, the other half
        for y in range(8):
            px[y][y] = glow
            if y & 1 and y < 7:
                px[y][y + 1] = glow
    elif motif == 5:                     # diamond wake
        for y in range(8):
            for x in range(8):
                if abs(x * 2 - 7) + abs(y * 2 - 7) in (6, 8):
                    px[y][x] = glow
    elif motif == 6:                     # cell edge / circuit trace
        for i in range(8):
            px[0][i] = glow
            px[i][0] = glow
    elif motif == 7:
        for y in (2, 5):
            for x in range(8):
                px[y][x] = glow
    elif motif == 8:
        for x in (2, 5):
            for y in range(8):
                px[y][x] = glow
    elif motif == 9:                     # dust
        for x, y in ((1, 1), (6, 2), (3, 5), (7, 7)):
            px[y][x] = glow
    elif motif == 10:                    # small hollow pulse
        for x, y in ((3, 2), (4, 2), (2, 3), (5, 3),
                     (2, 4), (5, 4), (3, 5), (4, 5)):
            px[y][x] = glow
    elif motif == 11:                    # checker shimmer
        for y in range(8):
            for x in range(8):
                if ((x >> 1) ^ (y >> 1)) & 1:
                    px[y][x] = dim
    elif motif == 12:                    # large flare
        for i in range(8):
            px[3][i] = glow
            px[i][3] = glow
        for x, y in ((2, 2), (4, 2), (2, 4), (4, 4)):
            px[y][x] = 15
        px[3][3] = 14
    elif motif == 13:
        for y in range(8):
            for x in range(8):
                if (x + y) % 4 == 0:
                    px[y][x] = glow
    elif motif == 14:                    # solid core with a lit rim
        for y in range(1, 7):
            for x in range(1, 7):
                px[y][x] = glow
        for y in range(2, 6):
            for x in range(2, 6):
                px[y][x] = 13
    elif motif == 15:
        for y in range(8):
            for x in range(8):
                px[y][x] = glow if ((x + y) & 1) else 14

    return bytes(v for row in px for v in row)


def generate_mode7():
    chars = []
    names = {}

    def name(base, motif):
        key = (base, motif)
        if key not in names:
            names[key] = len(chars)
            chars.append(tile(base, motif))
        return names[key]

    screen = bytearray()
    for y in range(128):
        for x in range(128):
            dx = x - 64
            dy = y - 64
            radius = math.hypot(dx, dy)
            angle = math.atan2(dy, dx)
            ripple = int(radius * 1.45 + math.sin(angle * 5.0) * 2.2) % 14
            spoke = abs(math.sin(angle * 8.0)) * max(1.0, radius)
            noise = (x * 73 + y * 151 + x * y * 3) & 255

            if radius < 3.5:
                base, motif = 12, 15
            elif radius < 7.0:
                base, motif = 10, 14
            elif ripple <= 1:
                base = 10 if (int(radius) & 8) else 6
                motif = 5
            elif spoke < 2.4:
                base = 4
                motif = 4 if dx * dy >= 0 else 3
            elif noise in (0, 1):
                base, motif = 3, 12
            elif noise < 13:
                base, motif = 2 + ((x ^ y) & 1), 1 + (noise & 1)
            else:
                base = 2 + ((int(radius / 7.0) + (x >> 3) + (y >> 3)) & 3)
                motif = 9 if noise < 36 else (11 if ripple > 10 else 0)

            screen.append(name(base, motif))

    assert len(screen) == 128 * 128
    assert len(chars) <= 256
    tile_data = b''.join(chars)

    total = 0
    total += g.write('mode7_warp.map', bytes(screen))
    total += g.write('mode7_warp.pic', tile_data)
    total += g.write('mode7_warp.pal', g.palette_bin(PALETTE))
    print("mode7: %d bytes (%d of 256 characters)" % (total, len(chars)))


if __name__ == '__main__':
    generate_mode7()
