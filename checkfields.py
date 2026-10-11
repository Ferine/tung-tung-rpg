#!/usr/bin/env python3
"""Validate authored field geometry and optionally render review overlays."""
import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import struct

import field_layouts
import gen_world as world
from terrain import Rng


def reachable(col, start):
    seen = {start}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for q in ((x-1, y), (x+1, y), (x, y-1), (x, y+1)):
            nx, ny = q
            if 0 <= nx < 32 and 0 <= ny < 32 and q not in seen and not col[ny*32+nx] & world.BLOCK:
                seen.add(q)
                queue.append(q)
    return seen


def main(previews=None):
    for region in world.REGIONS:
        key = region['key'].lower()
        d = field_layouts.layout(key)
        art = Path('assets/prerendered', d['reviewed_art'])
        assert hashlib.sha256(art.read_bytes()).hexdigest() == d['art_sha256'], key + ': artwork changed; review geometry'
        m = region['build'](Rng(region['seed']))
        col = world.collision(region, m, m.rows())
        if region.get('safe'):
            assert not any(c & world.ENC for c in col), key + ': encounters in a safe town'
        else:
            assert any(c & world.ENC and not c & (world.BLOCK | world.TRIG) for c in col), key + ': no ordinary encounter ground'
        exits = [tuple(e['cell']) for e in d['landmarks'] if e['event'] <= 4]
        seen = reachable(col, exits[0])
        for e in d['landmarks']:
            x, y = e['cell']
            x0, y0, x1, y1 = e['bounds']
            assert 0 <= x < 32 and 0 <= y < 32
            assert x0 < (x+1)*16 and x1 > x*16 and y0 < (y+1)*16 and y1 > y*16, (key, 'event misses landmark', e)
            access = [(x, y)] if not col[y*32+x] & world.BLOCK else [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]
            assert any(q in seen for q in access), (key, 'unreachable event', e)
        for origin in world.EXITS.values():
            for dest, x, y in origin.values():
                if dest.lower() == key:
                    assert (x,y) in seen and not col[y*32+x] & (world.BLOCK | world.TRIG), (key, 'invalid arrival', x, y)
        attrs = struct.unpack('<4096H', Path('assets/area_'+key+'.map').read_bytes())
        for y in range(64):
            for x in range(64):
                masked = any(a <= x*8+4 < c and b <= y*8+4 < z for a,b,c,z in d['foreground'])
                assert bool(attrs[y*64+x] & 0x2000) == masked, key + ': stale foreground'
        assert any(v & 0x2000 for v in attrs), key + ': no depth masks'
        if previews:
            overlay(region, m, col, d, previews)
    # The viewport can straddle 33 columns and 29 rows at fractional scroll.
    # No two visible tiles may share a cache slot, including both wrap seams.
    for cy in range(37):
        for cx in range(33):
            slots = {(y % 30)*34+x % 34 for y in range(cy,min(64,cy+29))
                     for x in range(cx,min(64,cx+33))}
            assert len(slots) == min(29,64-cy)*min(33,64-cx)
            assert max(slots) < 1024
    print('checkfields: 7 reviewed paintings, landmarks, routes, arrivals, depth masks, cache seams OK')


def overlay(region, m, col, d, out):
    from PIL import Image, ImageDraw
    key = region['key'].lower()
    im = Image.open(Path('assets/prerendered', d['reviewed_art'])).convert('RGBA').resize((512,512))
    layer = Image.new('RGBA', im.size)
    draw = ImageDraw.Draw(layer)
    for y in range(32):
        for x in range(32):
            if col[y*32+x] & world.BLOCK:
                draw.rectangle((x*16,y*16,x*16+15,y*16+15),fill=(255,30,30,80))
    for a,b,c,z in d['foreground']:
        draw.rectangle((a,b,c-1,z-1),outline=(0,255,255,230),width=1)
    for e in d['landmarks']:
        x,y=e['cell']
        draw.rectangle((x*16,y*16,x*16+15,y*16+15),outline='yellow',width=2)
        draw.text((x*16,y*16),str(e['event']),fill='yellow')
    out = Path(out); out.mkdir(parents=True,exist_ok=True)
    Image.alpha_composite(im,layer).convert('RGB').save(out/(key+'.png'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previews')
    main(parser.parse_args().previews)
