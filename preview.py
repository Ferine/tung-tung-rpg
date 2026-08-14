#!/usr/bin/env python3
"""Render the converted assets back to PNG, the way the PPU would.

Reads the same .pic/.pal/.map files the ROM embeds and reassembles them, so
what comes out is a check on the *binaries*, not on the generator's intent --
if the plane packing or the tilemap entry format were wrong, this would show it.
"""
import struct
import sys

import snesgfx as g


def read_pal(path):
    data = open(path, 'rb').read()
    out = []
    for i in range(0, len(data), 2):
        w = struct.unpack_from('<H', data, i)[0]
        r = (w & 31) << 3
        g = ((w >> 5) & 31) << 3
        b = ((w >> 10) & 31) << 3
        out.append((r, g, b))
    return out


def read_tiles(path):
    """Undo the 4bpp plane packing of ppu-graphics.md A-12."""
    data = open(path, 'rb').read()
    tiles = []
    for t in range(len(data) // 32):
        base = t * 32
        cell = []
        for y in range(8):
            p0 = data[base + y * 2]
            p1 = data[base + y * 2 + 1]
            p2 = data[base + 16 + y * 2]
            p3 = data[base + 16 + y * 2 + 1]
            row = []
            for x in range(8):
                bit = 0x80 >> x
                v = ((1 if p0 & bit else 0) | (2 if p1 & bit else 0)
                     | (4 if p2 & bit else 0) | (8 if p3 & bit else 0))
                row.append(v)
            cell.append(row)
        tiles.append(cell)
    return tiles


def render_map(pic, pal, mapfile, w, h, out, backdrop=(0, 0, 0), quads=False):
    """quads: the file is in the PPU's SC0 SC1 / SC2 SC3 order (A-14) rather
    than one w-wide array, which is how a 64x64 tilemap has to be stored."""
    from PIL import Image
    tiles = read_tiles(pic)
    pals = read_pal(pal)
    data = open(mapfile, 'rb').read()

    def at(mx, my):
        if not quads:
            return (my * w + mx) * 2
        q = (1 if mx >= 32 else 0) + (2 if my >= 32 else 0)
        return (q * 1024 + (my % 32) * 32 + (mx % 32)) * 2
    img = Image.new('RGB', (w * 8, h * 8), backdrop)
    px = img.load()
    for my in range(h):
        for mx in range(w):
            e = struct.unpack_from('<H', data, at(mx, my))[0]
            name = e & 0x3FF
            palno = (e >> 10) & 7
            hf = (e >> 14) & 1
            vf = (e >> 15) & 1
            cell = tiles[name]
            for y in range(8):
                sy = 7 - y if vf else y
                for x in range(8):
                    sx = 7 - x if hf else x
                    v = cell[sy][sx]
                    if v == 0:
                        continue
                    # A region ships two palettes and a backdrop one; a
                    # backdrop's map still names palette 1, so wrap rather
                    # than run off the end of a short file.
                    px[mx * 8 + x, my * 8 + y] = \
                        pals[(palno * 16 + v) % len(pals)]
    img.save(out)
    return img


def render_sheet(pic, pal, out, palno=0, cols=16):
    from PIL import Image
    tiles = read_tiles(pic)
    pals = read_pal(pal)
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new('RGB', (cols * 8, rows * 8), (255, 0, 255))
    px = img.load()
    for i, cell in enumerate(tiles):
        ox, oy = (i % cols) * 8, (i // cols) * 8
        for y in range(8):
            for x in range(8):
                v = cell[y][x]
                px[ox + x, oy + y] = (255, 0, 255) if v == 0 \
                    else pals[palno * 16 + v]
    img.save(out)
    return img


def render_anim(key, out):
    """The four phases of a region's animated block, side by side. The
    characters are the head of the region's tileset by construction, so the
    strip is simply the .anm file cut into ANIM_PHASES rows."""
    from PIL import Image

    pal = read_pal(g.asset('area_%s.pal' % key))
    tiles = read_tiles(g.asset('area_%s.anm' % key))
    if not tiles:
        return None
    n = len(tiles) // 4
    scale = 6
    img = Image.new('RGB', (n * 8 * scale, 4 * 8 * scale))
    px = img.load()
    for p in range(4):
        for i in range(n):
            cell = tiles[p * n + i]
            for y in range(8):
                for x in range(8):
                    col = pal[cell[y][x]]
                    for sy in range(scale):
                        for sx in range(scale):
                            px[(i * 8 + x) * scale + sx,
                               (p * 8 + y) * scale + sy] = col
    img.save(out)
    return n


def render_portraits(out):
    """The dialogue busts, side by side, each in its own palette."""
    from PIL import Image
    import gen_sprites as S

    scale = 4
    n = len(S.PORTRAIT_ART)
    img = Image.new('RGB', (n * 32 * scale, 32 * scale), (40, 40, 48))
    px = img.load()
    for i, (fn, palname) in enumerate(S.PORTRAIT_ART):
        c = fn()
        pal = S.PALS[getattr(S, palname)]
        for y in range(32):
            for x in range(32):
                v = c.px[y][x]
                if not v:
                    continue
                col = pal[v]
                for sy in range(scale):
                    for sx in range(scale):
                        px[(i * 32 + x) * scale + sx, y * scale + sy] = col
    img.save(out)
    return S.PORTRAIT_NAMES


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'world'

    if what == 'world':
        for key in ('village', 'fields', 'forest', 'shore',
                    'salt', 'fortress', 'hush'):
            out = 'preview-%s.png' % key
            render_map(g.asset('area_%s.pic' % key), g.asset('area_%s.pal' % key),
                       g.asset('area_%s.map' % key), 64, 64, out, quads=True)
            print('%-24s 512x512' % out)

    elif what == 'battle':
        for key in ('night', 'forest', 'shore', 'salt', 'iron', 'void'):
            out = 'preview-bg-%s.png' % key
            render_map(g.asset('bg_%s.pic' % key), g.asset('bg_%s.pal' % key),
                       g.asset('bg_%s.map' % key), 32, 32, out)
            print('%-24s 256x256' % out)

    elif what == 'sprites':
        palno = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        render_sheet(g.asset('sprites.pic'), g.asset('sprites.pal'),
                     'preview-sprites.png', palno=palno)
        print('preview-sprites.png')
        render_sheet(g.asset('enemies.pic'), g.asset('sprites.pal'),
                     'preview-enemies.png', palno=palno)
        print('preview-enemies.png')

    elif what == 'anim':
        for key in ('village', 'fields', 'forest', 'shore',
                    'fortress', 'hush'):
            out = 'preview-anim-%s.png' % key
            n = render_anim(key, out)
            if n:
                print('%-26s %d characters x 4 phases' % (out, n))

    elif what == 'title':
        import gen_title as t
        from PIL import Image
        img = t.build()
        scale = 2
        out = Image.new('RGB', (t.PX * scale, t.PY * scale))
        px = out.load()
        for y in range(t.PY):
            for x in range(t.PX):
                c = t.PAL[img.px[y][x]]
                for sy in range(scale):
                    for sx in range(scale):
                        px[x * scale + sx, y * scale + sy] = c
        out.save('preview-title.png')
        print('preview-title.png  %dx%d' % out.size)

    elif what == 'portraits':
        names = render_portraits('preview-portraits.png')
        print('preview-portraits.png  ' + ' '.join(names))

    else:
        print('usage: preview.py [world|battle|sprites|anim|portraits|title]')
