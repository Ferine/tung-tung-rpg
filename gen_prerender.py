#!/usr/bin/env python3
"""Bake full field paintings and battle stages to SNES Mode 1 graphics.

Each 8x8 tile chooses one 15-colour palette. Fields retain all 4096 spatial
tiles for viewport streaming; battle stages fit a resident 768-tile window.
Authored foreground masks and four-frame local effects accompany each field.
Only the offline bake needs numpy/Pillow. The deterministic ZIP is consumed
by gen_world.py and gen_battle.py with the standard library.
"""
import hashlib
import json
import zipfile

import numpy as np
from PIL import Image

import gen_world as world
import field_layouts
import prerender as p
import render_backdrops as rb
import snesgfx as g
from terrain import Rng

FIELD_SLOTS = (0, 1, 2, 4, 5, 6, 7)
BATTLE_SLOTS = (2, 4, 5, 6, 7)
BATTLES = ('night', 'forest', 'shore', 'salt', 'iron', 'void')


def quantise(image, slots):
    """Alternate tile-to-palette assignment and 15-bit palette fitting."""
    height, width, channels = image.shape
    rows, cols = height // 8, width // 8
    tiles = image.reshape(rows, 8, cols, 8, channels).transpose(0, 2, 1, 3, 4)
    tiles = tiles.reshape(-1, 64, channels)
    features = np.concatenate((tiles.mean(1), tiles.std(1)), axis=1)
    groups = rb._kmeans(features, np.ones(len(tiles)), len(slots), 41)
    labels = np.argmin(((features[:, None] - groups[None]) ** 2).sum(2), 1)
    palettes = np.zeros((len(slots), 15, channels))
    # Broad ground colours must agree across palette boundaries. Otherwise
    # two almost identical greens draw a checkerboard in an open clearing.
    colors, counts = np.unique(np.round(image.reshape(-1, channels) * 31),
                               axis=0, return_counts=True)
    anchors = colors[np.argsort(-counts, kind='stable')[:32]] / 31.
    for iteration in range(5):
        for j in range(len(slots)):
            pixels = tiles[labels == j].reshape(-1, channels)
            if not len(pixels):
                pixels = tiles.reshape(-1, channels)
            colors, counts = np.unique(np.round(pixels * 255).astype(np.int32),
                                       axis=0, return_counts=True)
            centers = rb._kmeans(colors / 255., counts, 15, 71 + j)
            palettes[j, :len(centers)] = rb._snap(centers)
            palettes[j, len(centers):] = palettes[j, 0]
            delta = ((palettes[j, :, None] - anchors[None]) ** 2).sum(2)
            near = delta.argmin(1)
            close = delta[np.arange(15), near] < channels * (0.8 / 31) ** 2
            palettes[j, close] = anchors[near[close]]
        errors = np.stack([
            np.min(((tiles[:, :, None] - pal[None, None]) ** 2).sum(3), 2).sum(1)
            for pal in palettes], axis=1)
        new = errors.argmin(1)
        if np.array_equal(labels, new):
            break
        labels = new
    indices = np.empty((len(tiles), 64), dtype=np.uint8)
    for j, pal in enumerate(palettes):
        which = labels == j
        indices[which] = np.argmin(
            ((tiles[which, :, None] - pal[None, None]) ** 2).sum(3), 2) + 1
    return palettes, indices, labels, (rows, cols)


def fit_tiles(palettes, indices, labels, budget, protect=None):
    """Weighted farthest-first tile dictionary, with protected event tiles.

    O(budget * tiles * 64), with bounded memory; the previous all-pairs
    merger would allocate several GiB for a 512x512 field painting.
    """
    keys = np.column_stack((indices, labels)).astype(np.uint8)
    unique, inverse, counts = np.unique(keys, axis=0, return_inverse=True,
                                        return_counts=True)
    inverse = inverse.ravel()
    rgb = np.stack([palettes[u[-1], u[:64] - 1] for u in unique]).astype(np.float32)
    # Luma and low-frequency shape matter more than texture at this scale.
    rgb *= np.tile([0.85, 1.15, 0.95], rgb.shape[-1] // 3)
    vectors = rgb.reshape(len(unique), -1)
    distance = np.full(len(unique), np.inf, np.float32)
    nearest = np.zeros(len(unique), np.int32)
    selected = []

    def choose(i):
        d = ((vectors - vectors[i]) ** 2).sum(1)
        better = d < distance
        nearest[better] = len(selected)
        distance[better] = d[better]
        selected.append(i)

    pinned = sorted(set(inverse[protect])) if protect is not None else []
    if len(pinned) > budget:
        raise ValueError('Protected event art exceeds the field tile budget')
    for i in pinned:
        choose(i)
    if not selected:
        choose(int(counts.argmax()))
    while len(selected) < min(budget, len(unique)):
        score = distance * np.sqrt(counts)
        score[selected] = -1
        choose(int(score.argmax()))
    # Farthest-first preserves silhouettes, but over-spends on unusual
    # texture. Refine each unpinned representative toward its cluster's
    # weighted centre, always choosing an actual source tile (a medoid).
    for _ in range(3):
        for j in range(len(pinned), len(selected)):
            members = np.flatnonzero(nearest == j)
            if not len(members):
                continue
            mean = np.average(vectors[members], axis=0, weights=counts[members])
            selected[j] = int(members[((vectors[members] - mean) ** 2).sum(1).argmin()])
        distance.fill(np.inf)
        for j, i in enumerate(selected):
            d = ((vectors - vectors[i]) ** 2).sum(1)
            better = d < distance
            nearest[better] = j
            distance[better] = d[better]
    return unique[selected], nearest[inverse], float(distance[inverse].mean())


def encode(image, slots, field=False, protect=None):
    pals, indices, labels, shape = quantise(image, slots)
    if field:
        # Preserve every spatial tile. A 34 x 30 runtime cache streams the
        # viewport; palette quantisation is now the only lossy conversion.
        pic = b''.join(g.tile_bin(c.reshape(8, 8)) for c in indices)
        tilemap = [g.map_entry(0, pal=slots[int(label)]) for label in labels]
        banks = {slot: [(0, 0, 0)] + [tuple(int(v) << 3 for v in np.round(c * 31))
                 for c in pals[j]] for j, slot in enumerate(slots)}
        palette = b''.join(g.palette_bin(banks.get(i, [(0, 0, 0)] * 16)) for i in range(8))
        return dict(pic=pic, map=g.map_bin(tilemap), pal=palette), pals, indices, labels
    chars, names, error = fit_tiles(pals, indices, labels, p.TILES, protect)
    pic = b''.join(g.tile_bin(c[:64].reshape(8, 8)) for c in chars)
    pic += bytes(p.PIC_BYTES - len(pic))
    tilemap = [g.map_entry(int(n), pal=slots[int(chars[n, -1])]) for n in names]
    if field:
        tilemap = world.quadrants(tilemap)
    palettes = {}
    for offset, suffix in ((0, 'pal'), (3, 'dawn')):
        if offset >= image.shape[2]:
            break
        banks = {slot: [(0, 0, 0)] + [tuple(int(v) << 3 for v in np.round(c * 31))
                   for c in pals[j, :, offset:offset + 3]] for j, slot in enumerate(slots)}
        first = 0 if field else 2
        palettes[suffix] = b''.join(g.palette_bin(banks.get(i, [(0, 0, 0)] * 16))
                                    for i in range(first, 8))
    return dict(pic=pic, map=g.map_bin(tilemap), **palettes), len(chars), error


def event_tiles(region):
    """Keep doors, wells, exits and bosses legible through tile compression."""
    m = region['build'](Rng(region['seed']))
    protected = set()
    for x, y in m.events:
        for ty in range(max(0, y * 2 - 2), min(64, y * 2 + 2)):
            for tx in range(max(0, x * 2 - 1), min(64, x * 2 + 3)):
                protected.add(ty * 64 + tx)
    return np.array(sorted(protected), dtype=int)


def main():
    files, scenes = {}, {}
    for region in world.REGIONS:
        key = region['key'].lower()
        with Image.open(p.ART / ('field-' + key + '.png')) as source:
            if source.width != source.height:
                raise ValueError(key + ': field source must be square')
            image = np.asarray(source.convert('RGB').resize((512, 512), Image.Resampling.LANCZOS)) / 255.
        data, pals, indices, labels = encode(image, FIELD_SLOTS, field=True)
        layout = field_layouts.layout(key)
        attrs = list(p.entries(data['map']))
        for y in range(64):
            for x in range(64):
                if field_layouts.foreground(key, x, y):
                    attrs[y * 64 + x] |= 0x2000
        data['map'] = g.map_bin(attrs)
        effects = bytearray()
        for effect in layout['animation']:
            for x, y in field_layouts.cells(effect['rect']):
                i = y * 64 + x
                pal = pals[labels[i]]
                source = indices[i].reshape(8, 8)
                effects += bytes((x, y, 0, 0))
                for phase in range(4):
                    pixels = pal[source - 1].copy()
                    if effect['kind'] in ('light', 'rift'):
                        strength = (0, .16, 0, -.12)[phase]
                        pixels = np.clip(pixels * (1 + strength), 0, 1)
                    else:
                        shift = (0, 1, 0, -1)[phase]
                        # Only the interior moves: stable borders keep the
                        # animated patch from tearing against the painting.
                        pixels[1:7, 1:7] = np.roll(pixels[1:7, 1:7], shift, axis=1)
                    converted = np.argmin(((pixels[:, :, None] - pal) ** 2).sum(3), 2) + 1
                    effects += g.tile_bin(converted)
        data['fx'] = bytes(effects)
        count, error = p.FIELD_TILES, 0
        m = region['build'](Rng(region['seed']))
        collision = world.collision(region, m, m.rows())
        stem = 'field-' + key
        scenes[stem] = dict(tiles=count, error=round(error, 6), effects=len(effects) // 132,
                            collision=hashlib.sha256(collision).hexdigest())
        files.update({stem + '.' + part: blob for part, blob in data.items()})
        print(stem, count, 'tiles; error', round(error, 4), flush=True)
    with Image.open(p.ART / 'battles.png') as source:
        width, height = source.size
        if width % 2 or height % 3:
            raise ValueError('Battle atlas must divide exactly into 2 x 3 panels')
        for i, key in enumerate(BATTLES):
            x, y = i % 2, i // 2
            panel = source.crop((x * width // 2, y * height // 3,
                                 (x + 1) * width // 2, (y + 1) * height // 3))
            image = np.empty((256, 256, 3))
            image[:168] = np.asarray(panel.convert('RGB').resize((256, 168), Image.Resampling.LANCZOS)) / 255.
            image[168:] = rb.UNDER_WINDOWS
            if key == 'night':
                # The epilogue repaints this exact geometry at dawn.
                dawn = np.clip(image * [1.15, 1.0, 0.72] + [0.13, 0.07, 0.02], 0, 1)
                dawn[168:] = rb.UNDER_WINDOWS
                image = np.concatenate((image, dawn), axis=2)
            data, count, error = encode(image, BATTLE_SLOTS)
            stem = 'battle-' + key
            scenes[stem] = dict(tiles=count, error=round(error, 6))
            files.update({stem + '.' + part: blob for part, blob in data.items()})
            print(stem, count, 'tiles; error', round(error, 4), flush=True)
    files['manifest.json'] = (json.dumps(dict(digest=p.digest(), scenes=scenes),
                                        indent=2, sort_keys=True) + '\n').encode()
    # Fixed timestamps/order make repeated bakes byte-for-byte comparable.
    temp = p.BAKE.with_suffix('.tmp')
    with zipfile.ZipFile(temp, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    temp.replace(p.BAKE)
    print('Wrote', p.BAKE)


if __name__ == '__main__':
    main()
