#!/usr/bin/env python3
"""Encoders for the three binary formats the ROM embeds.

Everything here comes straight out of the development manual, so the layouts
are cited rather than described:

  4bpp character data   ppu-graphics.md A-12: 16 words per character, words
                        0-7 carry planes 0/1 (low byte plane 0, high byte
                        plane 1) and words 8-15 planes 2/3.
  CG-RAM colour word    ppu-graphics.md "CGRAM & Color Formats": D14-D10 blue,
                        D9-D5 green, D4-D0 red.
  BG tilemap entry      ppu-graphics.md A-10: D15 V-flip, D14 H-flip,
                        D13 priority, D12-D10 palette, D9-D0 name.

We emit these ourselves instead of running gfx4snes because the OBJ engine
cares about *where* a character lands: a 32x32 OBJ takes its cells row-wise
from the 16-character page (A-4, "NAME 33 -> 33,34,35,36 / 43,44,45,46 / ..."),
so a sprite sheet has to be cut on a 16-tile pitch and the C side has to know
the resulting index. Owning the cut means the index is a number we choose.
"""
import struct

TILE_W = 8


def rgb15(r, g, b):
    """Pack 8-bit RGB into a CG-RAM word, truncating to 5 bits per channel."""
    return ((b >> 3) << 10) | ((g >> 3) << 5) | (r >> 3)


def palette_bin(colors):
    """colors: list of (r,g,b) or None for a slot that is never displayed.

    Entry 0 of every palette is the transparent one -- ppu-graphics.md notes
    "all-zero dot data = transparent (top color entry of each palette never
    shown)" -- so its value is arbitrary and we write black.
    """
    out = bytearray()
    for c in colors:
        if c is None:
            out += struct.pack('<H', 0)
        else:
            out += struct.pack('<H', rgb15(*c))
    return bytes(out)


def tile_bin(px):
    """px: 8 rows of 8 palette indices (0-15) -> 32 bytes of 4bpp character data."""
    out = bytearray(32)
    for y in range(8):
        row = px[y]
        p0 = p1 = p2 = p3 = 0
        for x in range(8):
            v = row[x] & 15
            bit = 0x80 >> x        # leftmost dot is bit 7
            if v & 1:
                p0 |= bit
            if v & 2:
                p1 |= bit
            if v & 4:
                p2 |= bit
            if v & 8:
                p3 |= bit
        out[y * 2] = p0
        out[y * 2 + 1] = p1
        out[16 + y * 2] = p2
        out[16 + y * 2 + 1] = p3
    return bytes(out)


def map_entry(name, pal=0, prio=0, hflip=0, vflip=0):
    return ((vflip & 1) << 15) | ((hflip & 1) << 14) | ((prio & 1) << 13) \
        | ((pal & 7) << 10) | (name & 0x3FF)


def map_bin(entries):
    return b''.join(struct.pack('<H', e) for e in entries)


class Sheet:
    """A grid of 8x8 cells, 16 cells wide.

    16 is not a layout preference: it is the pitch the OBJ engine assumes when
    it assembles a large character (A-4), and BG names are linear so a 16-wide
    page costs BG nothing. One sheet class therefore serves both.

    Cells are addressed by tile index; index n sits at column n%16, row n//16.
    """

    def __init__(self, tiles=256):
        self.tiles = tiles
        self.px = [[0] * (16 * 8) for _ in range((tiles // 16) * 8)]

    @property
    def height(self):
        return len(self.px)

    def origin(self, index):
        return (index % 16) * 8, (index // 16) * 8

    def set(self, x, y, v):
        if 0 <= y < self.height and 0 <= x < 16 * 8:
            self.px[y][x] = v

    def get(self, x, y):
        return self.px[y][x]

    def blit(self, index, rows, transparent='.', pal=None):
        """Draw a list of equal-length strings into the cell at `index`.

        `pal` maps a character to a palette index; digits map to themselves in
        hex when no mapping is given, which is how most of the art is written.
        """
        ox, oy = self.origin(index)
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch == transparent:
                    continue
                v = pal[ch] if pal else int(ch, 16)
                self.set(ox + dx, oy + dy, v)

    def rect(self, index, w, h, v):
        ox, oy = self.origin(index)
        for y in range(h):
            for x in range(w):
                self.set(ox + x, oy + y, v)

    def cell(self, index):
        ox, oy = self.origin(index)
        return [[self.px[oy + y][ox + x] for x in range(8)] for y in range(8)]

    def to_pic(self):
        return b''.join(tile_bin(self.cell(i)) for i in range(self.tiles))

    def to_png(self, path, colors):
        """Preview dump. Not consumed by the build -- for looking at."""
        try:
            from PIL import Image
        except ImportError:
            return
        img = Image.new('P', (16 * 8, self.height))
        flat = []
        for c in colors:
            flat += list(c if c else (255, 0, 255))
        flat += [0] * (768 - len(flat))
        img.putpalette(flat)
        img.putdata([v for row in self.px for v in row])
        img.save(path)


class Canvas:
    """Palette-index raster with the primitives the art is built from.

    Shapes are laid down filled and untouched by any border; `outline()` runs
    once at the end and rings the whole silhouette. Doing it that way means
    overlapping shapes (a bat crossing an arm) do not leave internal seams
    unless we ask for them.
    """

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[0] * w for _ in range(h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = c

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.px[y][x]
        return 0

    def rect(self, x, y, w, h, c):
        for j in range(h):
            for i in range(w):
                self.set(x + i, y + j, c)

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                dx = (x - cx) / float(rx)
                dy = (y - cy) / float(ry)
                if dx * dx + dy * dy <= 1.0:
                    self.set(x, y, c)

    def disc(self, cx, cy, r, c):
        self.ellipse(cx, cy, r, r, c)

    def line(self, x0, y0, x1, y1, c, thick=1):
        steps = int(max(abs(x1 - x0), abs(y1 - y0), 1))
        for i in range(steps + 1):
            x = x0 + (x1 - x0) * i / float(steps)
            y = y0 + (y1 - y0) * i / float(steps)
            if thick <= 1:
                self.set(int(round(x)), int(round(y)), c)
            else:
                self.disc(x, y, thick / 2.0, c)

    def tri(self, p0, p1, p2, c):
        xs = [p0[0], p1[0], p2[0]]
        ys = [p0[1], p1[1], p2[1]]

        def side(ax, ay, bx, by, px, py):
            return (bx - ax) * (py - ay) - (by - ay) * (px - ax)

        for y in range(min(ys), max(ys) + 1):
            for x in range(min(xs), max(xs) + 1):
                d0 = side(p0[0], p0[1], p1[0], p1[1], x, y)
                d1 = side(p1[0], p1[1], p2[0], p2[1], x, y)
                d2 = side(p2[0], p2[1], p0[0], p0[1], x, y)
                neg = (d0 < 0) or (d1 < 0) or (d2 < 0)
                pos = (d0 > 0) or (d1 > 0) or (d2 > 0)
                if not (neg and pos):
                    self.set(x, y, c)

    def replace(self, old, new):
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] == old:
                    self.px[y][x] = new

    def outline(self, c=1):
        """Ring the silhouette. 8-connected, so diagonal steps do not leak."""
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] != 0:
                    continue
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        v = self.get(x + dx, y + dy)
                        if v != 0 and v != c:
                            add.append((x, y))
                            break
                    else:
                        continue
                    break
        for x, y in add:
            self.px[y][x] = c

    def shade(self, light, mid, dark, ox=-1, oy=-1):
        """Cheap directional shading: everything `mid` that has `mid` up-left
        of it stays, everything on the lit edge goes `light`, the far edge
        `dark`. Two passes over one colour, which is all a 32x32 sprite needs
        to stop reading as a flat blob."""
        src = [row[:] for row in self.px]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x] != mid:
                    continue
                nx, ny = x + ox, y + oy
                if 0 <= nx < self.w and 0 <= ny < self.h and src[ny][nx] == 0:
                    self.px[y][x] = light
                nx, ny = x - ox, y - oy
                if 0 <= nx < self.w and 0 <= ny < self.h and src[ny][nx] == 0:
                    self.px[y][x] = dark

    def flip_h(self):
        out = Canvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                out.px[y][self.w - 1 - x] = self.px[y][x]
        return out


def write(path, data):
    with open(path, 'wb') as f:
        f.write(data)
    return len(data)
