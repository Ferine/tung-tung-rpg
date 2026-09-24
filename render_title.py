"""The title screen, pre-rendered: the village asleep, and the logo in gold.

It keeps the old title's two tricks -- a shine that walks over the logo and
stars that twinkle, with no tile ever rewritten -- but not their mechanism.
The painted title rotated four CGRAM entries through horizontal bands of a
flat logo; a shaded logo has no bands to rotate, and rotating its ramp would
scramble the shading. So the title is rendered FRAMES times with a light
circling the letters and the stars at different strengths, and all of those
pictures are cut together as one image with 3 x FRAMES channels, the way the
epilogue's dawn is cut with the night. What comes out is one set of
characters and FRAMES sets of palettes; the animation is a palette upload.

The logo is gen_title.py's own letterforms, bevelled: a distance transform
inside each letter gives a height, the height gives a normal, and the normal
catches the light. Nothing here marches a ray through a letter -- it is a
relief, and a relief is what a logo on a title screen is.

The page. BG1 on the title borrows the field's character window, $3000 up to
the text map at $5000, which nothing uses until a region loads: 512
characters, twice a backdrop's. The logo alone wants more than half of that.
"""
import math

import numpy as np

import gen_title
from render_backdrops import (Land, render_rgb, quantise, fit_budget,
                              _landscape, _ridge, _cell, _hash, _dunes, k,
                              PERIOD)

FRAMES = 8                      # palette sets in the loop (gen_title's STEP
                                # says how long each is shown)
HEIGHT = 224
HORIZON = 150                   # gen_hdma's default sky: the title's
BUDGET = 512
LOGO_SS = 4

SKY = (0.16, 0.15, 0.36)
GOLD = np.array([0.86, 0.60, 0.20])


# ---- the village -----------------------------------------------------------

def _house(p, cw, z0, depth, seed, per):
    ix, lx = _cell(p[:, 0], cw, per)
    w = cw * (0.55 + 0.25 * _hash(ix, seed))
    hgt = 0.55 + 0.35 * _hash(ix, seed + 1)
    roof = 0.30 + 0.15 * _hash(ix, seed + 2)
    on = _hash(ix, seed + 3) > 0.25
    lz = p[:, 2] - z0
    y = p[:, 1]
    body = np.maximum(np.maximum(np.abs(lx) - w / 2, np.abs(y - hgt / 2)
                                 - hgt / 2), np.abs(lz) - depth / 2)
    half = w / 2 + 0.08
    slope = np.hypot(roof, half)
    prism = np.maximum((np.abs(lx) * roof + (y - hgt) * half - roof * half)
                       / slope, hgt - y)
    prism = np.maximum(prism, np.abs(lz) - depth / 2 - 0.06)
    return np.where(on, np.minimum(body, prism), 1e3), (ix, lx, lz, hgt, w)


def _palm(p, cw, z0, seed, per):
    ix, lx = _cell(p[:, 0], cw, per)
    on = _hash(ix, seed) > 0.55
    q = np.stack([lx - 0.25 * cw, p[:, 1], p[:, 2] - z0], 1)
    bend = 0.18 * (q[:, 1] / 1.7) ** 2
    trunk = np.hypot(q[:, 0] - bend, q[:, 2]) - 0.045
    trunk = np.maximum(trunk, np.maximum(-q[:, 1], q[:, 1] - 1.7))
    top = np.array([0.18, 1.72, 0.0])
    d = trunk
    # Six fronds, drooping from the crown: long flat leaves, each laid along
    # its own direction, thick enough to survive being one dot tall.
    for a in range(6):
        t = a * math.pi / 3 + 0.3
        c, s_ = math.cos(t), math.sin(t)
        rel = q - (top + np.array([0.40 * c, -0.14, 0.40 * s_]))
        along = rel[:, 0] * c + rel[:, 2] * s_
        across = -rel[:, 0] * s_ + rel[:, 2] * c
        droop = rel[:, 1] + 0.35 * (along / 0.5) ** 2
        r = np.stack([along / 0.5, droop / 0.09, across / 0.16], 1)
        d = np.minimum(d, (np.linalg.norm(r, axis=1) - 1.0) * 0.09)
    return np.where(on, d, 1e3)


def village():
    g = _dunes(0.04)
    per = PERIOD / 2                # the village repeats every half screen
    ridges = [(-30.0, lambda x: 4.1 + _ridge(x, 2, 0.5, 0.9)),
              (-60.0, lambda x: 8.0 + _ridge(x, 3, 1.1, 2.4))]

    def houses(p):
        a, _ = _house(p, 1.6, -5.0, 0.8, 1, per)
        b, _ = _house(p + np.array([0.8, 0, 0]), 1.6, -7.6, 0.8, 5, per)
        return np.minimum(a, b)

    def palms(p):
        return np.minimum(_palm(p, 2.0, -6.2, 9, per),
                          _palm(p + np.array([1.0, 0, 0]), 2.0, -9.0, 12, per))

    def extra(p):
        return np.minimum(houses(p), palms(p))

    def shade(p, n):
        hs = houses(p) < 0.02
        pl = palms(p) < 0.02
        far = p[:, 2] < -20
        # Which house row, and is this dot a lit window on a front wall.
        lit = np.zeros(len(p), bool)
        roof = np.zeros(len(p), bool)
        for off, z0, seed in ((0.0, -5.0, 1), (0.8, -7.6, 5)):
            _, (ix, lx, lz, hgt, w) = _house(p + np.array([off, 0, 0]), 1.6,
                                             z0, 0.8, seed, per)
            front = np.abs(lz - 0.4) < 0.03
            win = (np.abs(np.abs(lx) - w * 0.22) < 0.07) \
                & (np.abs(p[:, 1] - hgt * 0.55) < 0.09)
            lit |= front & win & (_hash(ix * 3 + np.sign(lx), seed + 7) > 0.45)
            roof |= (p[:, 1] > hgt + 0.005) & (np.abs(lz) < 0.5)
        alb = np.tile(np.array([0.13, 0.13, 0.24]), (len(p), 1))
        alb[far] = np.array([0.20, 0.18, 0.40])
        alb[hs] = np.array([0.24, 0.21, 0.32])
        alb[hs & roof] = np.array([0.34, 0.17, 0.20])
        alb[pl] = np.array([0.09, 0.13, 0.14])
        alb[lit] = np.array([0.98, 0.74, 0.30])
        glow = np.where(lit, 1.6, 0.0)
        return alb, np.zeros(len(p)), glow

    return dict(key='title', horizon=HORIZON, cam_h=2.0, focal=150, far=90,
                seed=21, stars=0, disc=(216, 26, 15), height=HEIGHT,
                visible=HEIGHT, want_sky=True,
                land=Land(_landscape(g, ridges, extra), shade),
                light=dict(sky=SKY, fog=(0.20, 0.18, 0.40), fog_k=0.02,
                           key=(0.5, 0.6, -0.7), sun=0.55, amb=0.35,
                           rim=0.6, tint=(0.8, 0.82, 1.0),
                           rimcol=(0.7, 0.72, 1.0), star=(1, 1, 1),
                           disc=(0.94, 0.92, 0.80)))


# ---- stars -----------------------------------------------------------------

def _star_field(sky, logo_zone):
    """(y, x, group) for each star: one per chosen 8x8 cell at one of four
    offsets, so a star never makes more than a handful of distinct tiles --
    the painted title's rule, and still the right one."""
    rng = np.random.RandomState(0x7A17)
    spots = ((2, 3), (5, 1), (1, 6), (6, 4))
    out = []
    for ty in range(HORIZON // 8 - 2):
        for tx in range(32):
            if rng.rand() > 0.24:
                continue
            oy, ox = spots[rng.randint(4)]
            y, x = ty * 8 + oy, tx * 8 + ox
            if sky[y, x] and not logo_zone[y, x]:
                out.append((y, x, rng.randint(3)))
    return out


# ---- the logo --------------------------------------------------------------

def _logo_mask():
    img = gen_title.Img(gen_title.PX, gen_title.PY, 0)
    w1 = gen_title.word_width('TUNG TUNG', 4)
    gen_title.draw_word(img, 'TUNG TUNG', (gen_title.PX - w1) // 2, 46, 4, 6)
    w2 = gen_title.word_width('SAHUR', 5)
    gen_title.draw_word(img, 'SAHUR', (gen_title.PX - w2) // 2, 84, 5, 6)
    return np.array(img.px) != 0


def _relief(mask):
    """Height and normal of the bevelled letters, at LOGO_SS times size."""
    from scipy import ndimage
    big = np.kron(mask, np.ones((LOGO_SS, LOGO_SS), bool))
    d = ndimage.distance_transform_edt(big)
    bevel = 2.4 * LOGO_SS
    t = np.clip(d / bevel, 0, 1)
    h = t * t * (3 - 2 * t)
    gy, gx = np.gradient(h * bevel * 0.9)
    n = np.stack([-gx, -gy, np.ones_like(gx)], 2)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return big, n


def _logo_frame(big, n, f):
    """The logo lit by the light at step f of its circle, LOGO_SS-sized."""
    a = 2 * math.pi * f / FRAMES
    # Screen coordinates: x right, y *down*, z out of the glass.
    light = np.array([0.85 * math.cos(a), -0.35 + 0.45 * math.sin(a), 0.55])
    light /= np.linalg.norm(light)
    half = light + np.array([0, 0, 1.0])
    half /= np.linalg.norm(half)
    dif = np.clip(n @ light, 0, 1)
    spec = np.clip(n @ half, 0, 1) ** 28
    col = GOLD[None, None] * (0.34 + 0.80 * dif)[..., None] \
        + spec[..., None] * np.array([1.0, 0.95, 0.80])
    return np.clip(col, 0, 1)


def _down(a):
    h, w = a.shape[0] // LOGO_SS, a.shape[1] // LOGO_SS
    return a.reshape(h, LOGO_SS, w, LOGO_SS, *a.shape[2:]).mean(axis=(1, 3))


def frames():
    """FRAMES pictures of the title, (HEIGHT, 256, 3) each."""
    from scipy import ndimage
    base, sky = render_rgb(village())
    mask = _logo_mask()
    big, n = _relief(mask)
    cover = _down(big.astype(float))[:HEIGHT]
    solid = cover > 0.02
    # A dark rule round the letters and a drop shadow under them: gold on a
    # night sky needs both to sit on the picture instead of floating in it.
    ring = ndimage.binary_dilation(solid, iterations=1) & ~solid
    shadow = np.zeros_like(solid)
    shadow[3:, 2:] = ndimage.binary_dilation(solid, iterations=1)[:-3, :-2]
    shadow &= ~solid & ~ring
    zone = ndimage.binary_dilation(solid, iterations=6)
    stars = _star_field(sky, zone)

    out = []
    for f in range(FRAMES):
        img = base.copy()
        img[shadow] *= 0.45
        for y, x, grp in stars:
            s = 0.5 + 0.5 * math.cos(2 * math.pi * (f / FRAMES + grp / 3))
            img[y, x] = np.asarray(SKY) + (1.0 - np.asarray(SKY)) \
                * (0.35 + 0.65 * s)
        gold = _down(_logo_frame(big, n, f))[:HEIGHT]
        img = img * (1 - cover[..., None]) + gold * cover[..., None]
        img[ring] = np.array([0.18, 0.09, 0.03])
        out.append(img)
    return out


def bake_title():
    """One set of characters, FRAMES sets of five palettes."""
    fr = frames()
    img = np.concatenate(fr, 2)
    pals, idx, slot = quantise(img, seed=3)
    idx, slot, n = fit_budget(pals, idx, slot, BUDGET)
    return dict(pals=[pals[:, :, 3 * f:3 * f + 3] for f in range(FRAMES)],
                idx=idx, slot=slot, chars=n)
