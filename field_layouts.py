"""Authored geometry for the field paintings, in world pixel coordinates.

The JSON is the editable source of collision corrections, foreground masks,
landmarks and local animation. This module has no image dependencies: ROM
generation, pathfinding and CI all use exactly the same geometry.
"""
import json
from functools import lru_cache
from pathlib import Path

PATH = Path(__file__).resolve().parent / 'assets/prerendered/layouts.json'


@lru_cache(maxsize=None)
def layout(key):
    return json.loads(PATH.read_text())[key.lower()]


def cells(rect):
    x0, y0, x1, y1 = rect
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            yield x, y


def apply(key, m):
    d = layout(key)
    if 'floor_rects' in d:
        m.g = [['v'] * 32 for _ in range(32)]
        for rect in d['floor_rects']:
            for x, y in cells(rect):
                m.put(x, y, 'I')
    for rect in d.get('walk', []):
        for x, y in cells(rect):
            m.put(x, y, '.' if key != 'FORTRESS' else 'I')
    for rect in d.get('block', []):
        for x, y in cells(rect):
            m.put(x, y, 'O')
    m.events = {}
    for event in d['landmarks']:
        x, y = event['cell']
        m.put(x, y, event['terrain'])
        m.event(x, y, event['event'])
    return m


def foreground(key, tx, ty):
    """Tile-granular masks; terrain stays opaque so no extra BG is needed."""
    x, y = tx * 8 + 4, ty * 8 + 4
    return any(x0 <= x < x1 and y0 <= y < y1
               for x0, y0, x1, y1 in layout(key)['foreground'])
