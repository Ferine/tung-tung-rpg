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
    return decode_tiles(data)


def decode_tiles(data):
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


def render_map(pic, pal, mapfile, w, h, out, backdrop=(0, 0, 0), quads=False,
               pal_first=0):
    """quads: the file is in the PPU's SC0 SC1 / SC2 SC3 order (A-14) rather
    than one w-wide array, which is how a 64x64 tilemap has to be stored.
    pal_first: the CGRAM palette the file's first sixteen colours load into
    (a battle backdrop's file starts at 2)."""
    from PIL import Image
    tiles = read_tiles(pic)
    streamed = len(tiles) == 4096 and w == h == 64
    if streamed:
        quads = False
    pals = read_pal(pal) if isinstance(pal, str) else pal
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
            if streamed:
                name = my * w + mx
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
                        pals[((palno - pal_first) * 16 + v) % len(pals)]
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


def render_fieldactors(out, area=0):
    """Unpack every larger pose and guardian using the chosen region's light."""
    from PIL import Image, ImageDraw
    import fieldactors as f
    import gen_sprites as s
    assert 0 <= area < 7
    tiles = read_tiles(g.asset('fieldactors.pic'))
    guardians = read_tiles(g.asset('fieldguardians.pic'))
    palette = read_pal(g.asset('fieldactors.pal'))[area*128:(area+1)*128]
    poses = [(key, getattr(s,pal), [tiles[f.name(i)+y*16+x] for y in range(4) for x in range(4)])
             for i,(key,pal,*_) in enumerate(f.poses())]
    poses += [(key.removeprefix('boss_'), getattr(s,pal), guardians[a*16:(a+1)*16])
              for a,(key,pal) in enumerate(f.GUARDIANS,2)]
    img = Image.new('RGB',(5*144,7*116),(26,30,40))
    draw = ImageDraw.Draw(img)
    for i,(key,pal,cells) in enumerate(poses):
        ox,oy = i%5*144+24,i//5*116
        for y in range(32):
            for x in range(32):
                c = cells[y//8*4+x//8][y%8][x%8]
                if c:
                    draw.rectangle((ox+x*3,oy+y*3,ox+x*3+2,oy+y*3+2),fill=palette[pal*16+c])
        draw.text((i%5*144+4,oy+98),key,fill=(224,224,232))
    img.save(out)
    return img


def render_anim(key, out):
    """A rendered region under each of its palette sets, two by two. The
    land animates by palette (gen_world.py), so the .anm file is one copy
    of CGRAM 0-7 per frame and every frame is the same map recoloured."""
    from PIL import Image
    from pathlib import Path

    fx = Path(g.asset('area_%s.fx' % key))
    if fx.exists() and fx.stat().st_size:
        base = render_map(g.asset('area_%s.pic' % key), g.asset('area_%s.pal' % key),
                          g.asset('area_%s.map' % key), 64, 64, out)
        pals = read_pal(g.asset('area_%s.pal' % key))
        attrs = struct.unpack('<4096H', Path(g.asset('area_%s.map' % key)).read_bytes())
        data = fx.read_bytes()
        sheet = Image.new('RGB', (1024,1024))
        for phase in range(4):
            frame = base.copy(); pixels = frame.load()
            for offset in range(0,len(data),132):
                x,y = data[offset:offset+2]
                palno = (attrs[y*64+x] >> 10) & 7
                tile = decode_tiles(data[offset+4+phase*32:offset+36+phase*32])[0]
                for py in range(8):
                    for px in range(8):
                        pixels[x*8+px,y*8+py] = pals[palno*16+tile[py][px]]
            sheet.paste(frame, ((phase%2)*512,(phase//2)*512))
        sheet.save(out)
        return sheet

    data = open(g.asset('area_%s.anm' % key), 'rb').read()
    if len(data) < 512:
        return None
    frames = []
    for f in range(len(data) // 256):
        chunk = data[f * 256:(f + 1) * 256]
        frames.append([((w & 31) << 3, ((w >> 5) & 31) << 3,
                        ((w >> 10) & 31) << 3)
                       for w in struct.unpack('<128H', chunk)])
    img = Image.new('RGB', (1024, 512 * ((len(frames) + 1) // 2)))
    for f, pal in enumerate(frames):
        tile = render_map(g.asset('area_%s.pic' % key), pal,
                          g.asset('area_%s.map' % key), 64, 64, out,
                          quads=True)
        img.paste(tile, ((f % 2) * 512, (f // 2) * 512))
    img.save(out)
    return len(frames)


def render_portraits(out):
    """The dialogue busts, side by side, each in its own palette."""
    from PIL import Image
    import gen_sprites as S

    scale = 4
    n = len(S.PORTRAIT_ART)
    img = Image.new('RGB', (n * 32 * scale, 32 * scale), (40, 40, 48))
    px = img.load()
    renders = S.load_renders()
    for i, (key, fn, palname) in enumerate(S.PORTRAIT_ART):
        c = renders[key] if key in renders else fn()
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
                       g.asset('bg_%s.map' % key), 32, 32, out,
                       pal_first=2)
            print('%-24s 256x256' % out)

    elif what == 'sprites':
        palno = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        render_sheet(g.asset('sprites.pic'), g.asset('sprites.pal'),
                     'preview-sprites.png', palno=palno)
        print('preview-sprites.png')
        render_sheet(g.asset('enemies.pic'), g.asset('sprites.pal'),
                     'preview-enemies.png', palno=palno)
        print('preview-enemies.png')

    elif what == 'actors':
        area = int(sys.argv[2]) if len(sys.argv)>2 else 0
        render_fieldactors('preview-actors.png',area)
        print('preview-actors.png')

    elif what == 'anim':
        for key in ('village', 'fields', 'forest', 'shore',
                    'salt', 'fortress', 'hush'):
            out = 'preview-anim-%s.png' % key
            n = render_anim(key, out)
            if n:
                print('%-26s %d palette sets' % (out, n))

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
        print('usage: preview.py [world|battle|sprites|actors [area 0-6]|anim|portraits|title]')
