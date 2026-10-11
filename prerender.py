"""Read the checked-in prerender bake without image-processing dependencies.

The source PNGs and encoder are fingerprinted; ordinary asset generation and
CI only need the standard library. Run gen_prerender.py after changing art.
"""
import hashlib
import json
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parent
ART = ROOT / 'assets' / 'prerendered'
BAKE = ART / 'baked.zip'
TILES = 768
PIC_BYTES = TILES * 32
FIELD_TILES = 4096
FIELD_CHUNK_BYTES = 16384
_cache = None


def digest():
    h = hashlib.sha256()
    paths = [ROOT / 'gen_prerender.py', ROOT / 'prerender.py',
             ROOT / 'render_backdrops.py', ROOT / 'snesgfx.py',
             ROOT / 'field_layouts.py', ART / 'layouts.json']
    paths += sorted(ART.glob('*.png'))
    for path in paths:
        h.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
        data = path.read_bytes()
        h.update(data.replace(b'\r\n', b'\n') if path.suffix == '.py' else data)
    return h.hexdigest()


def load(kind, key):
    global _cache
    if _cache is None:
        with zipfile.ZipFile(BAKE) as z:
            manifest = json.loads(z.read('manifest.json'))
            if manifest['digest'] != digest():
                raise SystemExit('Prerender bake is stale: run python3 gen_prerender.py '
                                 '(requires numpy and Pillow).')
            _cache = {name: z.read(name) for name in z.namelist()}
            _cache['manifest'] = manifest
    stem = kind + '-' + key.lower()
    meta = _cache['manifest']['scenes'][stem]
    parts = ('pic', 'map', 'pal', 'dawn') if stem == 'battle-night' else ('pic', 'map', 'pal')
    if kind == 'field':
        parts += ('fx',)
    return dict(meta, **{part: _cache[stem + '.' + part] for part in parts})


class BakedSheet:
    """The to_pic() interface used by the existing asset generators."""
    def __init__(self, data):
        self.data = data

    def to_pic(self):
        return self.data


def entries(data):
    return list(struct.unpack('<%dH' % (len(data) // 2), data))
