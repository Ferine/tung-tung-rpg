#!/usr/bin/env python3
"""Raymarch larger field actors, without rebaking the legacy environment art.

Tung has four walking phases per direction. NPCs retain their two-frame poses.
Every sprite uses the same foot anchor and a dithered contact shadow, so walking
does not float or slide when the camera follows. Normal builds read the bake.
"""
import numpy as np

import fieldactors as f
import gen_render as r
import gen_sprites as sprites
import render_field as scenes
import render_bosses as bosses


def stride(direction, frame):
    # Passing poses alternate with opposite contacts; frame zero is also idle.
    swing=(0.,.23,0.,-.23)[frame]
    return swing,-swing,(.03,.10,.03,.10)[frame]


def anchor(canvas,kind):
    size=canvas.w
    occupied=[(x,y) for y,row in enumerate(canvas.px) for x,c in enumerate(row) if c]
    bottom=max(y for x,y in occupied)
    ox=(32-size)//2
    oy=f.ANCHOR_Y-bottom
    out=[[0]*32 for _ in range(32)]
    radius=7 if kind!='cat' else 9
    for y in range(25,32):
        for x in range(32):
            d=((x-15.5)/radius)**2+((y-28)/2.2)**2
            if d<.42 or (d<1 and (x+y)%2==0): out[y][x]=1
    for x,y in occupied:
        assert 0<=y+oy<32
        out[y+oy][x+ox]=canvas.px[y][x]
    return out


def render(kind,direction,frame,palette):
    scene,materials=scenes.FIELD[kind]
    original_stride=scenes._stride
    if kind=='walk': scenes._stride=stride
    figure=scene(direction,frame)
    scenes._stride=original_stride
    r.PALETTE=palette
    r.CREASE=.23
    # Render new geometry samples at the target size; never enlarge 16px art.
    size=28 if kind=='walk' else 26
    canvas=r.render(figure,materials,size=size,pitch=scenes.PITCH,span=1.03)
    canvas.outline()
    return anchor(canvas,kind)


def main():
    lines=['digest '+f.digest(sprites.PALS)]
    for key,pal,direction,frame in f.poses():
        rows=render(key.split('.')[0],direction,frame,sprites.PALS[getattr(sprites,pal)])
        lines.append('sprite '+key)
        lines += [''.join(format(c,'x') for c in row) for row in rows]
        print(key,flush=True)
    for key,pal in f.GUARDIANS:
        scene,materials,_size=bosses.SCENES[key]
        canvas=r.render_sprite(scene(),materials,sprites.PALS[getattr(sprites,pal)],size=28,pitch=scenes.PITCH)
        rows=anchor(canvas,'guardian')
        lines.append('sprite '+key)
        lines += [''.join(format(c,'x') for c in row) for row in rows]
        print(key,flush=True)
    temporary=f.BAKE.with_suffix('.tmp')
    temporary.write_text('\n'.join(lines)+'\n')
    temporary.replace(f.BAKE)
    f.generate(sprites.PALS)


if __name__=='__main__': main()
