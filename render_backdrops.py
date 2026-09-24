"""Battle backdrops, pre-rendered: six landscapes and the dawn that ends it.

The DKC way to paint a background on this machine is Mode 1 and a lot of
palettes, not Mode 3: 8bpp would share CGRAM with the sprite palettes and still
be held to the same 256-character page. So a backdrop here is a raymarched
landscape cut to five BG palettes -- 2, 4, 5, 6 and 7; 0 and 1 carry the red
and green glyphs in a fight and 3 is the windows -- with every character
choosing whichever of the five suits it.

Two constraints shape the camera.

  - The page. A 256x168 view is 672 characters and the page holds 256, so
    the picture has to repeat. The camera is orthographic across and
    perspective down: a ray's x is the screen column's world x, so anything
    periodic in world x is periodic on screen, exactly, and the dedup pass
    sees whole rows of the same characters. The ground repeats every half
    screen; ridges and skies get the full width.
  - The raster. gen_hdma.py darkens the sky toward the top with COLDATA
    subtract, and bends lines sideways for water and heat. So the sky is one
    flat colour, the brightest it gets, and the image wraps at 256 dots
    without a seam, because the wobble shows the seam if there is one.

The horizons are gen_hdma.py's SKIES; the two must agree or the gradient ends
in the middle of a hill.
"""
import math

import numpy as np

from gen_render import _norm

W = H = 256
SS = 2                          # supersampling per axis
VISIBLE = 168                   # the command windows cover the rest
PERIOD = 16.0                   # world units across the screen
SLOTS = (2, 4, 5, 6, 7)         # BG palettes a backdrop may use
BUDGET = 256                    # characters in the battle page
STEPS = 200
UNDER_WINDOWS = (33 / 255, 49 / 255, 90 / 255)    # gen_font.py's mid fill


def k(n):
    """An x frequency that repeats n times across the screen."""
    return 2 * math.pi * n / PERIOD


def _hash(i, seed=0.0):
    return np.modf(np.abs(np.sin(i * 12.9898 + seed * 78.233)) * 43758.5453)[0]


def _cell(x, width, per=PERIOD):
    """(index, local coordinate) of x in cells that tile `per` -- the whole
    screen, or half of it for anything on the ground."""
    n = int(round(per / width))
    i = np.floor(x / width)
    return np.mod(i, n), x - (i + 0.5) * width


def _smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ---- the camera and the march ------------------------------------------

class Land:
    """A landscape: `sdf(p)` -> distance, `shade(p, n)` -> (albedo, shine,
    glow). Everything in world space; x repeats on PERIOD."""

    def __init__(self, sdf, shade):
        self.sdf, self.shade = sdf, shade

    def eval(self, p):
        return self.sdf(p)


def _rays(horizon, cam_h, focal, height=H):
    n = W * SS
    xs = (np.arange(n) + 0.5) / n * PERIOD
    ys = (np.arange(height * SS) + 0.5) / SS
    X, Y = np.meshgrid(xs, ys)
    slope = (horizon - Y) / focal
    ro = np.stack([X.ravel(), np.full(X.size, cam_h), np.zeros(X.size)], 1)
    rd = _norm(np.stack([np.zeros(X.size), slope.ravel(), -np.ones(X.size)], 1))
    return ro, rd


def _march(land, ro, rd, tmax):
    t = np.full(len(ro), 0.01)
    hit = np.zeros(len(ro), bool)
    alive = np.ones(len(ro), bool)
    for _ in range(STEPS):
        idx = np.nonzero(alive)[0]
        if not len(idx):
            break
        d = land.eval(ro[idx] + rd[idx] * t[idx, None])
        t[idx] += np.maximum(d, 0.002 * t[idx])
        done = d < 0.002 * t[idx]
        hit[idx[done]] = True
        alive[idx[done | (t[idx] > tmax)]] = False
    return t, hit


def _normals(land, p):
    e = 2e-3
    out = np.zeros_like(p)
    for a in range(3):
        o = np.zeros(3)
        o[a] = e
        out[:, a] = land.eval(p + o) - land.eval(p - o)
    return _norm(out)


def _ao(land, p, n):
    occ = np.zeros(len(p))
    w = 1.0
    for i in range(1, 5):
        h = 0.06 * i
        occ += w * np.maximum(h - land.eval(p + n * h), 0)
        w *= 0.6
    return np.clip(1.0 - 1.6 * occ, 0.0, 1.0)


def _shadow(land, p, l):
    res = np.ones(len(p))
    t = np.full(len(p), 0.05)
    for _ in range(28):
        d = land.eval(p + l * t[:, None])
        res = np.minimum(res, np.clip(8.0 * d / t, 0.0, 1.0))
        t += np.clip(d, 0.05, 0.6)
    return res


def render_rgb(b, light=None):
    """The backdrop `b` as floats in [0,1], H x W x 3, before any palette.
    `light` overrides the lighting (the dawn pass)."""
    L = dict(b['light'], **(light or {}))
    h = b.get('height', H)
    ro, rd = _rays(b['horizon'], b['cam_h'], b['focal'], h)
    land = b['land']
    t, hit = _march(land, ro, rd, b['far'])
    rgb = np.tile(np.asarray(L['sky'], float), (len(ro), 1))

    idx = np.nonzero(hit)[0]
    p = ro[idx] + rd[idx] * t[idx, None]
    n = _normals(land, p)
    alb, shine, glow = land.shade(p, n)
    key = _norm(np.asarray(L['key'], float))
    dif = np.clip(n @ key, 0, 1) * _shadow(land, p + n * 0.02, key)
    ao = _ao(land, p, n)
    v = -rd[idx]
    rim = np.clip(1 - np.sum(n * v, 1), 0, 1) ** 3 * L['rim']
    half = _norm(key + v)
    spec = np.clip(np.sum(n * half, 1), 0, 1) ** np.maximum(shine, 1) \
        * (shine > 0) * dif
    col = alb * (L['amb'] * ao + L['sun'] * dif)[:, None] \
        * np.asarray(L['tint'], float) + (rim + 0.7 * spec)[:, None] \
        * np.asarray(L['rimcol'], float) + alb * glow[:, None]
    fog = 1 - np.exp(-t[idx] * L['fog_k'])
    col = col * (1 - fog)[:, None] + np.asarray(L['fog'], float) * fog[:, None]
    rgb[idx] = np.clip(col, 0, 1)

    # A ray that ran out below the horizon found ground too far to march:
    # it is fog, not sky, or a notch of sky opens at the foot of every hill.
    lost = ~hit & (rd[:, 1] < 0)
    rgb[lost] = L['fog']

    img = rgb.reshape(h * SS, W * SS, 3)
    img = img.reshape(h, SS, W, SS, 3).mean(axis=(1, 3))
    sky = ~hit.reshape(h * SS, W * SS) & ~lost.reshape(h * SS, W * SS)
    sky = sky.reshape(h, SS, W, SS).all(axis=(1, 3))
    _sky_details(img, sky, b, L)
    # Under the windows: one flat colour, one character -- and the windows'
    # own navy, not the floor's. A glyph's background is transparent, so
    # whatever sits under the status box shows round every letter in it.
    img[b.get('visible', VISIBLE):] = UNDER_WINDOWS
    if b.get('want_sky'):
        return img, sky
    return img


def _sky_details(img, sky, b, L):
    """Stars and the disc are drawn on the finished image: a point of light
    is one dot, not something to antialias into the sky colour."""
    rng = np.random.RandomState(b['seed'])
    for _ in range(b['stars']):
        x, y = rng.randint(0, W), rng.randint(2, max(3, b['horizon'] - 14))
        if sky[y, x]:
            img[y, x] = L['star']
            if rng.rand() < 0.12 and 0 < x < W - 1 and sky[y - 1:y + 2, x].all():
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    img[y + dy, x + dx] = np.asarray(L['star']) * 0.7 \
                        + np.asarray(L['sky']) * 0.3
    if b.get('disc'):
        cx, cy, r = b['disc']
        ys, xs = np.mgrid[0:img.shape[0], 0:W]
        dx, dy = (xs + 0.5 - cx) / r, (ys + 0.5 - cy) / r
        dd = dx * dx + dy * dy
        inside = (dd < 1) & sky
        nz = np.sqrt(np.clip(1 - dd, 0, 1))
        lit = np.clip(-0.5 * dx - 0.4 * dy + 0.75 * nz, 0, 1)
        # Maria: a few soft dark patches, so it is a moon and not a lamp.
        mar = sum(np.exp(-((dx - mx) ** 2 + (dy - my) ** 2) / s)
                  for mx, my, s in ((-0.3, -0.2, 0.08), (0.25, 0.3, 0.05),
                                    (0.1, -0.45, 0.03)))
        c = np.asarray(L['disc'], float)
        shade = (0.55 + 0.45 * lit) * (1 - 0.28 * np.clip(mar, 0, 1))
        img[inside] = (c[None, :] * shade[inside][:, None])
        halo = (dd >= 1) & (dd < 1.7) & sky
        a = (1 - (dd[halo] - 1) / 0.7)[:, None] * 0.25
        img[halo] = img[halo] * (1 - a) + c * a


# ---- the palette cut ----------------------------------------------------

def _kmeans(x, w, k, seed, iters=12):
    """Weighted k-means with a deterministic k-means++ start."""
    rng = np.random.RandomState(seed)
    k = min(k, len(x))
    cent = [x[np.argmax(w)]]
    for _ in range(1, k):
        d = np.min(((x[:, None, :] - np.array(cent)[None]) ** 2).sum(2), 1) * w
        if d.sum() <= 0:
            break
        cent.append(x[rng.choice(len(x), p=d / d.sum())])
    cent = np.array(cent)
    for _ in range(iters):
        lab = np.argmin(((x[:, None, :] - cent[None]) ** 2).sum(2), 1)
        for j in range(len(cent)):
            m = lab == j
            if m.any():
                cent[j] = (x[m] * w[m, None]).sum(0) / w[m].sum()
    return cent


def _snap(c):
    """To the 15-bit colour the CGRAM will actually hold."""
    return np.clip(np.round(c * 31), 0, 31) / 31.0


def quantise(img, seed=1):
    """img (H,W,C) -> (palettes [5][15][C], pixel indices 1-15 (H,W), slot
    per character (32,32) as 0-4). C is 3, or 6 when a second lighting of
    the same scene has to share the characters (see bake_backdrop).

    Characters are grouped five ways, each group gets fifteen colours by
    k-means over its own pixels, every character then moves to whichever
    palette draws it best, and that repeats until it settles."""
    C = img.shape[2]
    R, K = img.shape[0] // 8, img.shape[1] // 8
    tiles = img.reshape(R, 8, K, 8, C).transpose(0, 2, 1, 3, 4) \
        .reshape(R * K, 64, C)
    # Unique characters only, weighted by how often they appear: the flat
    # sky is one character however much of the screen it covers.
    flat = tiles.reshape(R * K, -1)
    uniq, inv, cnt = np.unique(np.round(flat * 255).astype(np.int32), axis=0,
                               return_inverse=True, return_counts=True)
    inv = inv.ravel()
    ut = uniq.reshape(-1, 64, C) / 255.0
    feat = np.concatenate([ut.mean(1), ut.std(1)], 1)
    # The commonest dot on the screen: the sky, or the iron roof.
    vals, counts = np.unique(np.round(img.reshape(-1, C) * 255).astype(np.int32),
                             axis=0, return_counts=True)
    anchor = _snap(vals[np.argmax(counts)] / 255.0)
    groups = _kmeans(feat, cnt.astype(float), len(SLOTS), seed)
    lab = np.argmin(((feat[:, None] - groups[None]) ** 2).sum(2), 1)

    pals = np.zeros((len(SLOTS), 15, C))
    for it in range(6):
        for j in range(len(SLOTS)):
            m = lab == j
            if not m.any():
                m = np.ones(len(ut), bool)
            px = ut[m].reshape(-1, C)
            pw = np.repeat(cnt[m], 64).astype(float)
            # Collapse identical pixels first: k-means over a few thousand
            # distinct colours, not a hundred thousand dots.
            q, qi = np.unique(np.round(px * 255).astype(np.int32), axis=0,
                              return_inverse=True)
            qw = np.bincount(qi.ravel(), weights=pw)
            c = _kmeans(q / 255.0, qw, 15, seed + j + it * 7)
            pals[j, :len(c)] = _snap(c)
            pals[j, len(c):] = pals[j, 0]
            # The flat sky is one colour and must stay one colour: two
            # palettes that each round it their own way draw a visible
            # square round every star that moved a character to the other.
            near = np.abs(pals[j] - anchor).max(1) < 2.5 / 31
            pals[j, near] = anchor
        # Reassign each character to the palette with the least error.
        err = np.stack([
            np.min(((ut[:, :, None, :] - pals[j][None, None]) ** 2).sum(3),
                   2).sum(1) for j in range(len(SLOTS))], 1)
        new = np.argmin(err, 1)
        if (new == lab).all():
            break
        lab = new

    idx_u = np.stack([
        np.argmin(((ut[i][:, None, :] - pals[lab[i]][None]) ** 2).sum(2), 1)
        for i in range(len(ut))])                     # (U, 64) in 0..14
    slot = lab[inv].reshape(R, K)
    idx = idx_u[inv].reshape(R, K, 8, 8).transpose(0, 2, 1, 3) \
        .reshape(R * 8, K * 8) + 1
    return pals, idx, slot


def fit_budget(pals, idx, slot, budget=BUDGET):
    """Merge the least-missed characters into their nearest neighbours until
    the page holds them. A character that appears once and looks like
    another is the cheapest thing on screen to lose."""
    R, K = slot.shape
    cells = idx.reshape(R, 8, K, 8).transpose(0, 2, 1, 3).reshape(R * K, 64)
    keys = np.concatenate([cells, slot.reshape(R * K, 1)], 1)
    uniq, inv, cnt = np.unique(keys, axis=0, return_inverse=True,
                               return_counts=True)
    inv = inv.ravel()
    if len(uniq) <= budget:
        return idx, slot, len(uniq)
    rgb = np.stack([pals[u[64]][u[:64] - 1] for u in uniq]).reshape(len(uniq), -1)
    d = ((rgb[:, None, :] - rgb[None]) ** 2).sum(2)
    np.fill_diagonal(d, np.inf)
    alive = np.ones(len(uniq), bool)
    target = np.arange(len(uniq))
    cnt = cnt.astype(float)
    while alive.sum() > budget:
        a = np.nonzero(alive)[0]
        sub = d[np.ix_(a, a)]
        cost = sub.min(1) * cnt[a]
        i = a[np.argmin(cost)]
        j = a[np.argmin(sub[np.searchsorted(a, i)])]
        alive[i] = False
        target[target == i] = j
        cnt[j] += cnt[i]
    final = uniq[target[inv]]
    idx = final[:, :64].reshape(R, K, 8, 8).transpose(0, 2, 1, 3) \
        .reshape(R * 8, K * 8)
    return idx, final[:, 64].reshape(R, K), int(alive.sum())


# ---- the six places --------------------------------------------------------

def _dunes(amp):
    """Ground swell. Even frequencies only, so it repeats every half screen:
    the ground is most of the picture and cannot afford a full width of
    characters per row."""
    def h(x, z):
        return (amp * np.sin(k(2) * x + 0.35 * z)
                + 0.6 * amp * np.sin(k(4) * x - 0.55 * z + 1.3)
                + 0.3 * amp * np.sin(k(6) * x + 1.1 * z + 0.4))
    return h


def _ridge(x, n, amp, seed):
    """A skyline repeating once per screen: a few octaves of sines."""
    y = 0.0
    for o in range(n):
        f = 2 + o * 3
        y = y + amp / (o + 1) * np.sin(k(f) * x + seed * (o + 1.7))
    return y


def _rocks(p, h, cw, cz, zmin, zmax, rmax, seed):
    """Boulders strewn on the ground in cells that tile the period."""
    ix, lx = _cell(p[:, 0], cw, PERIOD / 2)
    iz = np.floor(p[:, 2] / cz)
    lz = p[:, 2] - (iz + 0.5) * cz
    r = rmax * (0.4 + 0.6 * _hash(ix * 7 + iz, seed))
    ox = (_hash(ix + iz * 3, seed + 1) - 0.5) * (cw - 2 * rmax)
    oz = (_hash(ix * 5 - iz, seed + 2) - 0.5) * (cz - 2 * rmax)
    d = np.sqrt((lx - ox) ** 2 + ((p[:, 1] - h * 0.6) / 0.7) ** 2
                + (lz - oz) ** 2) - r
    band = (p[:, 2] < zmax) & (p[:, 2] > zmin) & (_hash(ix * 3 + iz * 11,
                                                         seed + 3) > 0.45)
    return np.where(band, d * 0.7, 1e3)


def _landscape(ground, ridges, extra=None, lip=0.5):
    """ground(x,z) -> height; ridges: [(z_at, height_fn(x))] walls of hills
    standing at a distance."""
    def sdf(p):
        d = (p[:, 1] - ground(p[:, 0], p[:, 2])) * lip
        for z_at, hf in ridges:
            hh = hf(p[:, 0])
            # Solid below the skyline and behind the line it stands on.
            wall = np.maximum(p[:, 1] - hh, p[:, 2] - z_at) * 0.6
            d = np.minimum(d, wall)
        if extra is not None:
            d = np.minimum(d, extra(p))
        return d
    return sdf


def night():
    """The village and the fields: purple dunes under a full moon, two lines
    of hills, and stones in the grass."""
    g = _dunes(0.10)
    ridges = [(-26.0, lambda x: 1.9 + _ridge(x, 3, 0.55, 0.3)),
              (-55.0, lambda x: 3.6 + _ridge(x, 3, 0.9, 2.2))]

    def extra(p):
        return _rocks(p, g(p[:, 0], p[:, 2]), 2.0, 2.5, -9, -1.5, 0.28, 1)

    def shade(p, n):
        far = np.clip((-p[:, 2] - 20) / 30, 0, 1)
        hill = np.where(p[:, 2] < -20, 1.0, 0.0)
        rock = extra(p) < 0.01
        grass = np.array([0.34, 0.33, 0.46])
        tone = 0.9 + 0.1 * np.sin(k(10) * p[:, 0] + 3 * p[:, 2])
        alb = grass[None] * tone[:, None]
        alb = np.where(hill[:, None] > 0, np.array([0.20, 0.20, 0.38]) * (1 - 0.3 * far)[:, None], alb)
        alb = np.where(rock[:, None], np.array([0.46, 0.44, 0.52]), alb)
        return alb, np.where(rock, 8.0, 0.0), np.zeros(len(p))

    return dict(key='night', horizon=108, cam_h=1.1, focal=150, far=90,
                seed=11, stars=30, disc=(208, 34, 13),
                land=Land(_landscape(g, ridges, extra), shade),
                light=dict(sky=(0.38, 0.41, 0.66), fog=(0.30, 0.31, 0.52),
                           fog_k=0.022, key=(-0.4, 0.8, -0.5), sun=0.85,
                           amb=0.32, rim=0.35, tint=(0.85, 0.88, 1.0),
                           rimcol=(0.75, 0.78, 0.95), star=(0.97, 0.97, 0.91),
                           disc=(0.97, 0.97, 0.91)))


# The epilogue's sky: the night, lit from a sun just under the far hills.
DAWN_LIGHT = dict(sky=(0.97, 0.66, 0.40), fog=(0.86, 0.46, 0.34), fog_k=0.03,
                  key=(0.2, 0.25, -1.0), sun=1.1, amb=0.42, rim=0.8,
                  tint=(1.0, 0.72, 0.56), rimcol=(1.0, 0.8, 0.55),
                  star=(1.0, 0.94, 0.84), disc=(1.0, 0.96, 0.85))


def forest():
    """Two walls of spruce under a starry, moonless sky; a mossy floor."""
    g = _dunes(0.06)

    def spruce(p, z0, depth, cw, hmin, hmax, seed):
        ix, lx = _cell(p[:, 0], cw)
        hgt = hmin + (hmax - hmin) * _hash(ix, seed)
        base = g(p[:, 0], np.full(len(p), z0)) - 0.2
        y = p[:, 1] - base
        lz = p[:, 2] - z0
        r = np.hypot(lx, lz / depth)
        d = 1e3
        # Three tiers, the top one narrowest: a spruce, not a cone.
        for tier in range(3):
            y0 = hgt * tier * 0.28
            th = hgt - y0
            rad = cw * 0.62 * (1 - tier * 0.22)
            yy = y - y0
            cone = (r - rad * (1 - np.clip(yy / th, 0, 1))) * 0.6
            cone = np.maximum(cone, np.maximum(-yy, yy - th))
            d = np.minimum(d, cone)
        return d

    def extra(p):
        return np.minimum(spruce(p, -16.0, 1.0, 1.0, 2.0, 3.4, 4),
                          spruce(p, -34.0, 1.2, 1.6, 3.6, 5.6, 9))

    def shade(p, n):
        tree = extra(p) < 0.02
        moss = np.array([0.18, 0.34, 0.26])
        tone = 0.85 + 0.15 * np.sin(k(12) * p[:, 0] + 2.5 * p[:, 2]) \
            * np.sin(4 * p[:, 2])
        alb = moss[None] * tone[:, None]
        needle = np.array([0.10, 0.24, 0.20]) * \
            (0.8 + 0.2 * np.sin(p[:, 1] * 30))[:, None]
        alb = np.where(tree[:, None], needle, alb)
        return alb, np.zeros(len(p)), np.zeros(len(p))

    return dict(key='forest', horizon=120, cam_h=1.0, focal=150, far=80,
                seed=12, stars=16, disc=None,
                land=Land(_landscape(g, [], extra), shade),
                light=dict(sky=(0.24, 0.40, 0.34), fog=(0.16, 0.30, 0.26),
                           fog_k=0.03, key=(-0.5, 0.8, -0.3), sun=0.7,
                           amb=0.36, rim=0.3, tint=(0.8, 0.95, 0.9),
                           rimcol=(0.7, 0.95, 0.85), star=(0.88, 0.95, 0.85)))


def shore():
    """Sand, then the sea to a low headland, and the moon over the water."""
    def g(x, z):
        beach = _smooth(-7.5, -5.0, z)          # 0 under water, 1 on sand
        # The sea gets ripples small enough to march and big enough to
        # break the moonlight into glints; the swell is the H-DMA's job.
        ripple = 0.012 * np.sin(k(10) * x + 3.1 * z) \
            * np.sin(k(4) * x - 1.7 * z + 0.6)
        return (0.05 * np.sin(k(4) * x + 0.9 * z)) * beach \
            + (ripple - 0.05) * (1 - beach)

    ridges = [(-60.0, lambda x: 1.3 + _ridge(x, 2, 0.35, 1.0)
               - 1.2 * _smooth(0.0, 1.0, np.cos(k(1) * x - 1.0)))]

    def shade(p, n):
        wet = p[:, 2] < -6.2
        hill = p[:, 2] < -50
        sand = np.array([0.62, 0.52, 0.38]) * \
            (0.9 + 0.1 * np.sin(k(12) * p[:, 0] + 5 * p[:, 2]))[:, None]
        sea = np.array([0.10, 0.18, 0.36])
        alb = np.where(wet[:, None], sea, sand)
        alb = np.where(hill[:, None], np.array([0.12, 0.14, 0.26]), alb)
        return alb, np.where(wet & ~hill, 24.0, 0.0), np.zeros(len(p))

    return dict(key='shore', horizon=96, cam_h=1.0, focal=140, far=90,
                seed=13, stars=50, disc=(48, 30, 15),
                land=Land(_landscape(g, ridges), shade),
                light=dict(sky=(0.36, 0.49, 0.75), fog=(0.20, 0.28, 0.50),
                           fog_k=0.02, key=(-0.6, 0.5, -0.9), sun=0.8,
                           amb=0.34, rim=0.3, tint=(0.85, 0.9, 1.0),
                           rimcol=(0.9, 0.95, 1.0), star=(0.97, 0.98, 0.93),
                           disc=(0.97, 0.98, 0.93)))


def salt():
    """The salt flats: a pale crazed pan to a low line of hills, and a white
    disc too hot to be the moon."""
    def g(x, z):
        return 0.015 * np.sin(k(4) * x + 0.4 * z)

    ridges = [(-70.0, lambda x: 1.5 + _ridge(x, 3, 0.35, 0.7))]

    def cracks(x, z, size=1.0, per=PERIOD / 2):
        """F2 - F1 of a jittered grid: small near the border between two
        cells. The x cells tile half a screen so the pan repeats."""
        n = int(round(per / size))
        cx, cz = np.floor(x / size), np.floor(z / size)
        f1 = np.full(len(x), 9.0)
        f2 = np.full(len(x), 9.0)
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                ix, iz = cx + dx, cz + dz
                h = np.mod(ix, n) * 17 + iz * 5
                px = (ix + 0.5 + 0.7 * (_hash(h, 1) - 0.5)) * size
                pz = (iz + 0.5 + 0.7 * (_hash(h, 2) - 0.5)) * size
                d = np.hypot(x - px, z - pz)
                f2 = np.where(d < f1, f1, np.minimum(f2, d))
                f1 = np.minimum(f1, d)
        return f2 - f1

    def shade(p, n):
        crack = (cracks(p[:, 0], p[:, 2]) < 0.07) & (p[:, 2] > -30)
        hill = p[:, 2] < -60
        pan = np.array([0.72, 0.72, 0.80])
        alb = np.where(crack[:, None], np.array([0.36, 0.35, 0.44]), pan)
        alb = np.where(hill[:, None], np.array([0.40, 0.38, 0.50]), alb)
        return alb, np.where(hill | crack, 0.0, 6.0), np.zeros(len(p))

    return dict(key='salt', horizon=104, cam_h=1.0, focal=150, far=90,
                seed=14, stars=40, disc=(196, 28, 11),
                land=Land(_landscape(g, ridges), shade),
                light=dict(sky=(0.50, 0.48, 0.67), fog=(0.52, 0.50, 0.66),
                           fog_k=0.025, key=(0.5, 0.6, -0.7), sun=0.75,
                           amb=0.4, rim=0.2, tint=(0.9, 0.9, 1.0),
                           rimcol=(1.0, 1.0, 1.0), star=(0.98, 0.97, 1.0),
                           disc=(0.99, 0.98, 1.0)))


def iron():
    """Inside the fortress: girders for a sky, lamps in them, riveted plate
    underfoot and a wall of pipes at the back."""
    ceil = 2.6

    def girders(p):
        ix, lx = _cell(p[:, 0], 4.0)
        lz = np.mod(p[:, 2], 6.0) - 3.0
        beam_x = np.maximum(np.abs(lx) - 0.18, np.abs(p[:, 1] - ceil + 0.25)
                            - 0.25)
        beam_z = np.maximum(np.abs(lz) - 0.22, np.abs(p[:, 1] - ceil + 0.2)
                            - 0.2)
        return np.minimum(beam_x, beam_z)

    def lamps(p):
        ix, lx = _cell(p[:, 0], 4.0)
        lz = np.mod(p[:, 2] + 3.0, 6.0) - 3.0
        return np.sqrt(lx ** 2 + ((p[:, 1] - ceil + 0.55) / 0.6) ** 2
                       + lz ** 2) - 0.16

    def pipes(p):
        d = 1e3
        for y, r in ((0.5, 0.22), (1.1, 0.14), (1.6, 0.28)):
            d = np.minimum(d, np.hypot(p[:, 1] - y, p[:, 2] + 30 - r) - r)
        return d

    def sdf(p):
        floor = p[:, 1]
        roof = ceil - p[:, 1]
        wall = p[:, 2] + 30.0
        d = np.minimum(np.minimum(floor, roof), wall)
        return np.minimum(np.minimum(d, girders(p)),
                          np.minimum(lamps(p), pipes(p)))

    def shade(p, n):
        lamp = lamps(p) < 0.02
        pipe = pipes(p) < 0.02
        girder = girders(p) < 0.02
        roof = p[:, 1] > ceil - 0.05
        _, lx = _cell(p[:, 0], 2.0)
        lz = np.mod(p[:, 2], 2.0) - 1.0
        seam = (np.abs(lx) > 0.95) | (np.abs(lz) > 0.94)
        rivet = (np.abs(np.abs(lx) - 0.8) < 0.06) & (np.abs(np.abs(lz) - 0.8)
                                                     < 0.08)
        plate = np.array([0.34, 0.36, 0.44])
        alb = np.where(seam[:, None], np.array([0.14, 0.14, 0.18]), plate)
        alb = np.where(rivet[:, None], np.array([0.58, 0.60, 0.70]), alb)
        alb = np.where((roof | girder)[:, None], np.array([0.20, 0.20, 0.26]),
                       alb)
        alb = np.where(pipe[:, None], np.array([0.40, 0.30, 0.24]), alb)
        alb = np.where(lamp[:, None], np.array([0.97, 0.77, 0.38]), alb)
        glow = np.where(lamp, 1.4, 0.0)
        shine = np.where(pipe | rivet, 20.0, np.where(roof | girder, 0, 4.0))
        return alb, shine, glow

    return dict(key='iron', horizon=96, cam_h=1.0, focal=150, far=40,
                seed=15, stars=0, disc=None, land=Land(sdf, shade),
                light=dict(sky=(0.10, 0.10, 0.14), fog=(0.16, 0.14, 0.16),
                           fog_k=0.04, key=(-0.3, 0.9, 0.2), sun=0.9,
                           amb=0.5, rim=0.25, tint=(1.0, 0.86, 0.66),
                           rimcol=(1.0, 0.8, 0.5), star=(1, 1, 1)))


def void():
    """The Hush: a black mirror of a floor with a faint grid in it, shards of
    something hanging over it, and far too many stars."""
    def shards(p):
        ix, lx = _cell(p[:, 0], 2.0)
        lz = np.mod(p[:, 2], 7.0) - 3.5
        iz = np.floor(p[:, 2] / 7.0)
        y0 = 1.0 + 1.6 * _hash(ix + iz * 5, 3)
        on = (_hash(ix * 3 + iz, 5) > 0.5) & (p[:, 2] < -6) & (p[:, 2] > -40)
        a = _hash(ix + iz, 7) * 3.0
        c, s = np.cos(a), np.sin(a)
        qx, qy = c * lx - s * (p[:, 1] - y0), s * lx + c * (p[:, 1] - y0)
        q = np.abs(np.stack([qx, qy, lz], 1)) - np.array([0.10, 0.34, 0.10])
        d = np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)
        return np.where(on, d, 1e3)

    def sdf(p):
        return np.minimum(p[:, 1], shards(p))

    def shade(p, n):
        shard = shards(p) < 0.02
        _, lx = _cell(p[:, 0], 1.0)
        lz = np.mod(p[:, 2], 1.0) - 0.5
        grid = (np.abs(lx) > 0.47) | (np.abs(lz) > 0.47)
        alb = np.where(grid[:, None], np.array([0.30, 0.22, 0.48]),
                       np.array([0.04, 0.03, 0.07]))
        alb = np.where(shard[:, None], np.array([0.60, 0.52, 0.86]), alb)
        glow = np.where(grid & ~shard, 0.5, np.where(shard, 0.3, 0.0))
        return alb, np.where(shard, 30.0, 60.0), glow

    return dict(key='void', horizon=150, cam_h=1.0, focal=180, far=60,
                seed=16, stars=110, disc=None, land=Land(sdf, shade),
                light=dict(sky=(0.20, 0.15, 0.32), fog=(0.10, 0.07, 0.16),
                           fog_k=0.05, key=(-0.3, 0.7, -0.6), sun=0.6,
                           amb=0.2, rim=0.5, tint=(0.8, 0.75, 1.0),
                           rimcol=(0.75, 0.65, 1.0), star=(0.95, 0.93, 1.0)))


# key -> builder. The keys are gen_battle.REGIONS' and the order does not
# matter here; gen_battle.py looks each one up.
BACKDROPS = {b.__name__: b for b in (night, forest, shore, salt, iron, void)}


def bake_backdrop(key):
    """Everything gen_battle.py needs for one region, as plain data: five
    palettes, the index image, the slot per character, and for the night the
    dawn palettes that repaint it."""
    b = BACKDROPS[key]()
    img = render_rgb(b)
    dawn = key == 'night'
    if dawn:
        # Quantised as one six-channel picture, night and dawn side by side
        # in every dot, so each palette entry is right for both lightings.
        # Cut separately, two dots that match at night could need different
        # colours at dawn and share a palette entry anyway.
        img = np.concatenate([img, render_rgb(b, DAWN_LIGHT)], 2)
    pals, idx, slot = quantise(img)
    idx, slot, n = fit_budget(pals, idx, slot)
    if dawn:
        return dict(pals=pals[:, :, :3], dawn=pals[:, :, 3:], idx=idx,
                    slot=slot, chars=n)
    return dict(pals=pals, idx=idx, slot=slot, chars=n)
