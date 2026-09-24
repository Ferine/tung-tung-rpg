#!/usr/bin/env python3
"""Pre-rendered sprites: signed distance fields, raymarched, cut to 4bpp.

The DKC route, minus the SGI workstation. A character is a union of distance
functions -- capsules, rounded cylinders, spheres -- marched at four times the
target resolution with real lighting (key, fill, rim, ambient occlusion, a soft
shadow), then boxed down to 32x32 and quantised.

The quantiser is the part that makes it look like DKC rather than a JPEG. It
does not search the whole palette: every surface carries a material, and a
material may only land on its own ramp of palette indices. Wood can be any of
the five wood browns and the specular white, never the sash red, however close
the colour. That keeps shading bands clean, the way a hand-built ramp is,
instead of letting a shadow on the log pick up the bat's colour because it
happened to be nearer in RGB.

It also means a rendered character keeps the palette the hand-drawn one had,
so everything else sharing that palette (the cat shares P_TUNG) is untouched.
"""
import math

import numpy as np

from snesgfx import Canvas

SS = 4                      # supersampling factor per axis
MAX_STEPS = 96
EPS = 1e-3


# ---- vector helpers ------------------------------------------------------

def _norm(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def _rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


# ---- distance functions (p is (N,3)) -------------------------------------

def sphere(p, c, r):
    return np.linalg.norm(p - np.asarray(c), axis=1) - r


def ellipsoid(p, c, r):
    """Not exact, but bounded well enough to march (iq's approximation)."""
    q = (p - np.asarray(c)) / np.asarray(r)
    k0 = np.linalg.norm(q, axis=1)
    k1 = np.linalg.norm(q / np.asarray(r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def capsule(p, a, b, ra, rb=None):
    """A capsule, or a round cone when the two radii differ."""
    rb = ra if rb is None else rb
    a, b = np.asarray(a, float), np.asarray(b, float)
    pa, ba = p - a, b - a
    # A zero-length capsule is a sphere; without the floor it is 0/0 and a
    # NaN distance that the marcher never hits.
    h = np.clip((pa @ ba) / max(ba @ ba, 1e-12), 0.0, 1.0)
    return np.linalg.norm(pa - h[:, None] * ba, axis=1) - (ra + (rb - ra) * h)


def cylinder_y(p, c, r, h, round_=0.0):
    """Vertical cylinder, radius r, half-height h, edges rounded by round_."""
    q = p - np.asarray(c)
    d = np.stack([np.hypot(q[:, 0], q[:, 2]) - r + round_,
                  np.abs(q[:, 1]) - h + round_], axis=1)
    return (np.minimum(np.maximum(d[:, 0], d[:, 1]), 0.0)
            + np.linalg.norm(np.maximum(d, 0.0), axis=1) - round_)


def box(p, c, half):
    q = np.abs(p - np.asarray(c)) - np.asarray(half)
    return (np.linalg.norm(np.maximum(q, 0.0), axis=1)
            + np.minimum(np.max(q, axis=1), 0.0))


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


# ---- the scene -----------------------------------------------------------

class Scene:
    """A list of (name, material, sdf-of-object-space-p, blend) parts.

    Distance is the min over parts, softened by `blend` where a part asks for
    it; the material is whichever part is nearest, so a smooth join between
    an arm and the log still has a hard material boundary, which is what the
    quantiser wants.

    A material may also be a function of the object-space point, for
    surfaces that change along themselves: a shark's back and belly, the
    spines on a cactus, bark grain.
    """

    def __init__(self, to_object):
        self.parts = []
        self.to_object = to_object       # world (N,3) -> object (N,3)

    def add(self, mat, fn, blend=0.0):
        self.parts.append((mat, fn, blend))

    def eval(self, p, want_mat=False):
        q = self.to_object(p)
        dist = None
        best = None
        mat = None
        for m, fn, blend in self.parts:
            d = fn(q)
            if want_mat and callable(m):
                m = m(q)
            if dist is None:
                dist, best = d, d.copy()
                mat = np.broadcast_to(m, d.shape).copy() if want_mat else None
                continue
            dist = smin(dist, d, blend) if blend else np.minimum(dist, d)
            if want_mat:
                closer = d < best
                best = np.where(closer, d, best)
                mat = np.where(closer, m, mat)
        return (dist, mat) if want_mat else dist


def figure(yaw, lean=0.0, tilt=0.0, roll=0.0, shift=(0, 0, 0),
           pivot=(0.0, -0.9, 0.0)):
    """A Scene whose object space faces +z, posed into the world.

    Degrees throughout. `yaw` turns the figure (negative is toward screen-
    left), `lean` tips it about the screen axis at `pivot` -- the feet, where
    the weight is -- and `tilt` and `roll` pitch and bank it about its own x
    and z, which is what a shark or an aeroplane does instead of leaning.
    `shift` is in object space.
    """
    r = math.radians
    m = (_rot_z(-r(roll)) @ _rot_x(-r(tilt)) @ _rot_y(-r(yaw))
         @ _rot_z(-r(lean)))
    pivot, shift = np.asarray(pivot), np.asarray(shift, float)

    def to_object(p):
        return (p - pivot) @ m.T + pivot + shift

    s = Scene(to_object)
    # World point -> object point, for parts that have to be placed by where
    # they land on screen rather than where they sit on the body.
    s.obj = lambda w: to_object(np.array([w], float))[0]
    return s


def flat(fn, sx=1.0, sy=1.0, sz=1.0):
    """Squash a distance function along its axes. The result is a bound
    rather than exact, which marching at 0.9 of a step tolerates."""
    k = np.array([sx, sy, sz], float)
    lo = k.min()
    return lambda p: fn(p / k) * lo


def _normals(scene, p):
    e = 1e-3
    out = np.zeros_like(p)
    for k in range(3):
        o = np.zeros(3)
        o[k] = e
        out[:, k] = scene.eval(p + o) - scene.eval(p - o)
    return _norm(out)


def _march(scene, ro, rd, tmax):
    t = np.zeros(len(ro))
    alive = np.ones(len(ro), bool)
    hit = np.zeros(len(ro), bool)
    for _ in range(MAX_STEPS):
        idx = np.nonzero(alive)[0]
        if not len(idx):
            break
        d = scene.eval(ro[idx] + rd[idx] * t[idx, None])
        t[idx] += d * 0.9
        done = d < EPS
        hit[idx[done]] = True
        alive[idx[done | (t[idx] > tmax)]] = False
    return t, hit


def _ao(scene, p, n):
    occ = np.zeros(len(p))
    w = 1.0
    for i in range(1, 6):
        h = 0.02 + 0.06 * i
        occ += w * (h - scene.eval(p + n * h))
        w *= 0.7
    return np.clip(1.0 - 2.2 * occ, 0.0, 1.0)


def _shadow(scene, p, l):
    res = np.ones(len(p))
    t = np.full(len(p), 0.03)
    for _ in range(32):
        d = scene.eval(p + l * t[:, None])
        res = np.minimum(res, np.clip(10.0 * d / t, 0.0, 1.0))
        t += np.clip(d, 0.02, 0.2)
    return np.clip(res, 0.0, 1.0)


# ---- rendering and quantisation ------------------------------------------

KEY = _norm(np.array([-0.55, 0.75, 0.55]))     # upper left, toward camera
FILL = _norm(np.array([0.8, 0.1, 0.4]))
RIM = _norm(np.array([0.6, 0.3, -0.8]))


def render(scene, materials, size=32, pitch=-0.2, span=1.0):
    """Returns a Canvas of palette indices.

    `materials` maps a material id to (albedo rgb 0-1, shininess, ramp,
    glow) where ramp is the list of palette indices that material may use and
    glow is light it gives off regardless of the key -- eyes need it, or an
    eye in shadow goes grey and the character stops looking at anything. The camera is
    orthographic; the frame covers [-span, span] in x and y.
    """
    n = size * SS
    xs = (np.arange(n) + 0.5) / n * 2 - 1
    u, v = np.meshgrid(xs * span, -xs * span)
    cam = _rot_x(pitch)
    ro = np.stack([u.ravel(), v.ravel(), np.full(n * n, 4.0)], 1) @ cam.T
    rd = np.tile(np.array([0, 0, -1.0]) @ cam.T, (n * n, 1))

    t, hit = _march(scene, ro, rd, 8.0)
    rgb = np.zeros((n * n, 3))
    mat = np.full(n * n, -1)

    idx = np.nonzero(hit)[0]
    p = ro[idx] + rd[idx] * t[idx, None]
    _, m = scene.eval(p, want_mat=True)
    nrm = _normals(scene, p)
    ao = _ao(scene, p, nrm)
    sh = _shadow(scene, p + nrm * 0.01, KEY)

    alb = np.array([materials[k][0] for k in m])
    shin = np.array([materials[k][1] for k in m])
    glow = np.array([materials[k][3] if len(materials[k]) > 3 else 0.0
                     for k in m])
    dif = np.clip(nrm @ KEY, 0, 1) * sh
    fil = np.clip(nrm @ FILL, 0, 1)
    vdir = -rd[idx]
    rim = np.clip(1 - np.sum(nrm * vdir, 1), 0, 1) ** 3 * np.clip(nrm @ RIM + 0.3, 0, 1)
    half = _norm(KEY + vdir)
    spec = np.clip(np.sum(nrm * half, 1), 0, 1) ** shin * sh * (shin > 0)

    light = 0.28 * ao + 0.95 * dif + 0.18 * fil * ao + glow
    col = alb * light[:, None] + (0.5 * rim + 0.6 * spec)[:, None]
    rgb[idx] = np.clip(col, 0, 1) ** (1 / 1.25)     # a touch of display gamma
    mat[idx] = m

    depth = np.where(hit, t, np.inf)
    return _downsample(rgb.reshape(n, n, 3), mat.reshape(n, n),
                       depth.reshape(n, n), size, materials)


CREASE = 0.15        # depth step, in units, that earns an internal outline


def _downsample(rgb, mat, depth, size, materials):
    c = Canvas(size, size)
    z = np.full((size, size), np.inf)
    for y in range(size):
        for x in range(size):
            bm = mat[y * SS:(y + 1) * SS, x * SS:(x + 1) * SS].ravel()
            cover = bm >= 0
            if cover.sum() * 2 < SS * SS:
                continue
            # Majority material, and the mean colour of just those samples:
            # averaging across a material edge would invent a colour neither
            # ramp owns.
            vals, counts = np.unique(bm[cover], return_counts=True)
            m = vals[np.argmax(counts)]
            sel = bm == m
            col = rgb[y * SS:(y + 1) * SS, x * SS:(x + 1) * SS].reshape(-1, 3)[sel].mean(0)
            c.px[y][x] = _nearest(col, materials[m][2])
            z[y, x] = depth[y * SS:(y + 1) * SS, x * SS:(x + 1) * SS].ravel()[sel].mean()
    # Internal outlines, Mario RPG style: a pixel goes dark where something
    # clearly nearer sits right beside it -- the far side of an overlap, never
    # a fold in one surface. Without it a light bat over a light log is one
    # shape.
    for y in range(size):
        for x in range(size):
            if not c.px[y][x]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < size and 0 <= ny < size and \
                        z[ny, nx] < z[y, x] - CREASE:
                    c.px[y][x] = 1
                    break
    return c


PALETTE = None       # set by the caller: the 16 (r,g,b) the ramps index into


def _nearest(col, ramp):
    """Closest ramp entry, weighted toward luma so bands follow the light."""
    best, bd = ramp[0], 1e9
    c = col * 255
    for i in ramp:
        r, g, b = PALETTE[i]
        dr, dg, db = c[0] - r, c[1] - g, c[2] - b
        dl = (0.3 * dr + 0.59 * dg + 0.11 * db)
        d = dr * dr + dg * dg + db * db + 3 * dl * dl
        if d < bd:
            best, bd = i, d
    return best


# ---- Tung Tung Sahur -----------------------------------------------------
#
# Object space: y up, the character faces +z, 1 unit is 16 pixels. The yaw
# turns that face toward screen-left, where the enemies stand.

WOOD, END, EYE, PUPIL, BROW, BAT, FOOT, SLIT, GRIP = range(9)

TUNG_MATERIALS = {
    #        albedo               shine  ramp (palette indices, P_TUNG)
    WOOD:  ((0.62, 0.40, 0.20),    0,    [14, 2, 3, 4, 5]),
    END:   ((0.90, 0.72, 0.48),    0,    [3, 4, 5, 15]),
    EYE:   ((0.96, 0.96, 0.96),   40,    [12, 13, 6, 15], 0.55),
    PUPIL: ((0.04, 0.04, 0.07),   60,    [7, 13, 15]),
    BROW:  ((0.80, 0.18, 0.14),    0,    [11, 10]),
    BAT:   ((0.70, 0.48, 0.28),   12,    [14, 2, 8, 9, 5, 15]),
    FOOT:  ((0.22, 0.12, 0.06),    0,    [1, 14, 2]),
    SLIT:  ((0.10, 0.06, 0.03),    0,    [1, 14], -0.3),
    GRIP:  ((0.35, 0.20, 0.10),    0,    [14, 2, 3]),
}


def tung_scene(pose):
    s = figure(-26, lean=10 if pose == 'attack' else 0, shift=(0.02, 0, 0))
    obj = s.obj
    R, TOP, BOT = 0.40, 0.52, -0.58
    cy, hh = (TOP + BOT) / 2, (TOP - BOT) / 2

    def log(p):
        d = cylinder_y(p, (0, cy, 0), R, hh, 0.06)
        # The slit: the thing that makes it a drum rather than a stump.
        slit = box(p, (0, -0.24, R), (0.30, 0.06, 0.16))
        return np.maximum(d, -slit)

    def end_grain(p):
        # A thin disc riding the top face, so the cut end is its own material.
        return cylinder_y(p, (0, TOP - 0.02, 0), R - 0.07, 0.035, 0.02)

    def slit_floor(p):
        return box(p, (0, -0.24, R - 0.15), (0.29, 0.05, 0.02))

    s.add(WOOD, log)
    s.add(END, end_grain)
    s.add(SLIT, slit_floor)

    # Legs and feet.
    for sx in (-1, 1):
        s.add(WOOD, lambda p, sx=sx: capsule(p, (0.16 * sx, BOT, 0.02),
                                             (0.18 * sx, -0.80, 0.06), 0.085),
              blend=0.06)
        s.add(FOOT, lambda p, sx=sx: ellipsoid(p, (0.18 * sx, -0.86, 0.12),
                                               (0.12, 0.07, 0.17)))

    # Eyes, set into the front face, looking the way he is facing and a
    # little off toward screen-left.
    for sx in (-1, 1):
        ex = 0.17 * sx
        s.add(EYE, lambda p, ex=ex: sphere(p, (ex, 0.20, R - 0.07), 0.21))
        s.add(PUPIL, lambda p, ex=ex: sphere(p, (ex - 0.05, 0.19, R + 0.07),
                                             0.10))
        # Brows: permanently unimpressed. Low at the middle, high outside.
        s.add(BROW, lambda p, sx=sx: capsule(
            p, (0.34 * sx, 0.48, R - 0.02), (0.05 * sx, 0.38, R + 0.05),
            0.06))

    # Arms, and the bat. The bat is placed in *world* space: authored in
    # object space, a swing toward the enemy points half into the camera and
    # foreshortens to a stub, and the bat is the silhouette.
    if pose == 'attack':
        grip, tip = obj((-0.18, 0.30, 0.5)), obj((-0.80, 0.56, 0.5))
        s.add(WOOD, lambda p: capsule(p, (-R + 0.02, 0.02, 0.08), grip, 0.07),
              blend=0.05)
        s.add(WOOD, lambda p: capsule(p, (R - 0.02, 0.05, 0.05), grip, 0.07),
              blend=0.05)
    else:
        grip, tip = obj((0.50, 0.08, 0.1)), obj((0.70, 0.70, -0.2))
        s.add(WOOD, lambda p: capsule(p, (-R + 0.02, -0.02, 0.0),
                                      (-0.62, -0.22, 0.18), 0.07), blend=0.05)
        s.add(WOOD, lambda p: capsule(p, (R - 0.02, 0.02, 0.0), grip, 0.07),
              blend=0.05)

    s.add(GRIP, lambda p: capsule(p, grip - (tip - grip) * 0.08, grip, 0.05))
    s.add(BAT, lambda p: capsule(p, grip, tip, 0.06, 0.16))
    return s


def render_sprite(scene, materials, palette, size=32):
    global PALETTE
    PALETTE = palette
    c = render(scene, materials, size=size)
    c.outline()
    return c


def render_tung(pose, palette):
    return render_sprite(tung_scene(pose), TUNG_MATERIALS, palette)


# ---- Brr Brr Patapim -----------------------------------------------------
#
# A tree that walks. Wide, low and mossy: the thing standing in front of
# everyone else. Bark grain is a material, not geometry -- at 32px a groove
# is a pixel, and a pixel is cheaper to pick than to model.

BARK, GRAIN, MOSS, P_EYE, P_PUPIL, P_BROW, P_FOOT = range(7)

PATAPIM_MATERIALS = {
    BARK:    ((0.50, 0.38, 0.24),   0,  [13, 2, 3, 4, 14]),
    GRAIN:   ((0.26, 0.19, 0.12),   0,  [13, 2]),
    MOSS:    ((0.30, 0.58, 0.30),   0,  [5, 6, 7]),
    P_EYE:   ((0.86, 0.82, 0.68),  30,  [10, 8, 15], 0.5),
    P_PUPIL: ((0.08, 0.07, 0.05),  60,  [9, 12]),
    P_BROW:  ((0.20, 0.15, 0.10),   0,  [13, 2]),
    P_FOOT:  ((0.34, 0.26, 0.16),   0,  [13, 2, 3]),
}


def _bark(q):
    ang = np.arctan2(q[:, 0], q[:, 2])
    # Grain runs up the trunk and wanders; a few dark furrows, not stripes.
    w = np.sin(ang * 7 + np.sin(q[:, 1] * 9) * 0.8)
    return np.where(w > 0.82, GRAIN, BARK)


def patapim_scene(pose):
    s = figure(-22, lean=8 if pose == 'attack' else 0)
    R = 0.58

    def trunk(p):
        d = ellipsoid(p, (0, -0.12, 0), (R, 0.62, 0.48))
        return d + 0.015 * np.sin(np.arctan2(p[:, 0], p[:, 2]) * 7)

    def moss(p):
        d = ellipsoid(p, (0, 0.42, -0.02), (0.74, 0.30, 0.60))
        lumps = np.sin(p[:, 0] * 11) * np.sin(p[:, 2] * 9) * 0.035
        return d + lumps

    s.add(_bark, trunk)
    s.add(MOSS, moss, blend=0.04)

    # Legs are stumps, feet are long: he is rooted even when he walks.
    for sx in (-1, 1):
        s.add(BARK, lambda p, sx=sx: capsule(p, (0.26 * sx, -0.62, 0),
                                             (0.30 * sx, -0.78, 0.05), 0.11),
              blend=0.08)
        s.add(P_FOOT, lambda p, sx=sx: ellipsoid(
            p, (0.31 * sx, -0.85, 0.14), (0.17, 0.08, 0.28)))

    # Eyes, very old, under one heavy brow each.
    for sx in (-1, 1):
        ex = 0.20 * sx
        s.add(P_EYE, lambda p, ex=ex: sphere(p, (ex, 0.06, 0.40), 0.18))
        s.add(P_PUPIL, lambda p, ex=ex: sphere(p, (ex - 0.06, 0.05, 0.53),
                                               0.09))
        s.add(P_BROW, lambda p, sx=sx: capsule(
            p, (0.36 * sx, 0.28, 0.36), (0.07 * sx, 0.19, 0.47), 0.06))

    # Branch arms. Placed in world space for the same reason as Tung's bat.
    obj = s.obj
    if pose == 'attack':
        arms = [((-0.52, -0.02, 0.2), (-0.84, 0.46, 0.2), (-0.94, 0.72, 0.2)),
                ((0.52, 0.0, -0.1), (0.86, 0.34, -0.1), (0.92, 0.60, -0.1))]
    else:
        arms = [((-0.52, -0.08, 0.2), (-0.84, -0.30, 0.2), (-0.92, -0.46, 0.2)),
                ((0.52, -0.06, -0.1), (0.86, -0.26, -0.1), (0.95, -0.42, -0.1))]
    for a, b, twig in arms:
        a, b, twig = obj(a), obj(b), obj(twig)
        s.add(BARK, lambda p, a=a, b=b: capsule(p, a, b, 0.10, 0.07),
              blend=0.06)
        s.add(BARK, lambda p, b=b, t=twig: capsule(p, b, t, 0.06, 0.035))
    return s


# ---- Tralalero Tralala ---------------------------------------------------
#
# Three-shoed shark. Turned nearly into profile: a shark head-on is a circle.
# Countershaded by material -- dark back, pale belly -- because that line is
# the thing that says "shark" before anything else does.

SKIN, BELLY, T_EYE, T_PUPIL, SHOE, SHOE_W, SOLE, SWOOSH, GUM, TOOTH = range(10)

TRALA_MATERIALS = {
    SKIN:    ((0.30, 0.50, 0.85),  16,  [13, 2, 3, 4, 12, 15]),
    BELLY:   ((0.82, 0.86, 0.94),   0,  [3, 12, 5, 6]),
    T_EYE:   ((0.96, 0.96, 1.00),  40,  [5, 6, 15], 0.5),
    T_PUPIL: ((0.05, 0.05, 0.08),  60,  [7, 15]),
    SHOE:    ((0.14, 0.30, 0.85),  10,  [13, 8, 4]),
    SHOE_W:  ((0.94, 0.94, 0.97),   0,  [11, 5, 9, 6]),
    SOLE:    ((0.38, 0.38, 0.44),   0,  [13, 11]),
    SWOOSH:  ((0.97, 0.85, 0.28),   0,  [14], 0.4),
    GUM:     ((0.70, 0.18, 0.22),   0,  [1, 10]),
    TOOTH:   ((0.96, 0.96, 0.96),   0,  [5, 6], 0.3),
}


def _countershade(q):
    return np.where(q[:, 1] - 0.25 * q[:, 0] < 0.0, BELLY, SKIN)


def trala_scene(pose):
    attack = pose == 'attack'
    s = figure(-66, tilt=-8 if attack else 0, pivot=(0, -0.1, 0),
               shift=(0, 0, -0.18 if attack else 0.0))

    def body(p):
        d = ellipsoid(p, (0, 0.0, 0.0), (0.36, 0.34, 0.72))
        # The snout: a long ellipsoid blended on, so the head tapers.
        d = smin(d, ellipsoid(p, (0, -0.03, 0.52), (0.24, 0.22, 0.38)), 0.12)
        # The tail stock narrows before the fin.
        d = smin(d, capsule(p, (0, 0.02, -0.5), (0, 0.06, -0.86), 0.14, 0.06),
                 0.1)
        if attack:
            mouth = ellipsoid(p, (0.06, -0.12, 0.80), (0.34, 0.17, 0.40))
            d = np.maximum(d, -mouth)
        return d

    s.add(_countershade, body)

    fin = lambda a, b, r0, r1: flat(lambda p: capsule(p, a, b, r0, r1), sx=0.3)
    s.add(SKIN, fin((0, 0.24, 0.05), (0, 0.72, -0.18), 0.14, 0.02), blend=0.05)
    s.add(SKIN, fin((0, 0.06, -0.84), (0, 0.52, -1.02), 0.10, 0.02), blend=0.03)
    s.add(SKIN, fin((0, 0.02, -0.84), (0, -0.34, -0.98), 0.09, 0.02),
          blend=0.03)
    s.add(SKIN, lambda p: flat(lambda q: capsule(
        q, (0, 0, 0), (0, -0.30, -0.18), 0.10, 0.02), sx=0.4)(
        p - np.array([0.34, -0.14, 0.18])))

    # Eye on the near flank, looking where he is going.
    s.add(T_EYE, lambda p: sphere(p, (0.20, 0.10, 0.50), 0.10))
    s.add(T_PUPIL, lambda p: sphere(p, (0.26, 0.10, 0.55), 0.055))

    if attack:
        s.add(GUM, lambda p: ellipsoid(p, (0, -0.12, 0.62), (0.18, 0.10, 0.22)))
        for i in range(5):
            z = 0.62 + i * 0.06
            s.add(TOOTH, lambda p, z=z: sphere(p, (0.15, -0.03, z), 0.035))
            s.add(TOOTH, lambda p, z=z: sphere(p, (0.15, -0.21, z - 0.03),
                                               0.035))
    else:
        # A grin: a crease along the jaw, and teeth along it.
        s.add(GUM, lambda p: capsule(p, (0.19, -0.15, 0.46),
                                     (0.12, -0.12, 0.84), 0.025))
        for i in range(4):
            z = 0.52 + i * 0.08
            s.add(TOOTH, lambda p, z=z: sphere(p, (0.20 - (z - 0.5) * 0.2,
                                                   -0.12, z), 0.03))

    # Three shoes, obviously, each on a stub of a leg.
    for i, z in enumerate((0.40, 0.0, -0.40)):
        x = 0.1 if i % 2 else -0.06
        s.add(BELLY, lambda p, x=x, z=z: capsule(p, (x, -0.22, z),
                                                 (x, -0.56, z), 0.06),
              blend=0.05)
        s.add(SHOE, lambda p, x=x, z=z: ellipsoid(p, (x, -0.62, z + 0.04),
                                                  (0.13, 0.10, 0.20)))
        s.add(SHOE_W, lambda p, x=x, z=z: ellipsoid(p, (x, -0.66, z + 0.16),
                                                    (0.12, 0.08, 0.10)))
        s.add(SOLE, lambda p, x=x, z=z: ellipsoid(p, (x, -0.72, z + 0.06),
                                                  (0.14, 0.04, 0.24)))
        s.add(SWOOSH, lambda p, x=x, z=z: capsule(
            p, (x + 0.12, -0.60, z - 0.08), (x + 0.12, -0.66, z + 0.10), 0.02))
    return s


# ---- Lirili Larila -------------------------------------------------------
#
# A cactus with an elephant's head. The head has to dominate or this reads as
# "cactus with a grey blob". Casts; does not hit things.

CACTUS, SPINE, ELE, L_EYE, L_PUPIL, TUSK, SANDAL, FLOWER = range(8)

LIRILI_MATERIALS = {
    CACTUS:  ((0.30, 0.62, 0.30),   0,  [13, 2, 3, 4]),
    SPINE:   ((0.88, 0.92, 0.70),   0,  [5], 0.3),
    ELE:     ((0.44, 0.44, 0.50),   0,  [6, 7, 8]),
    L_EYE:   ((0.97, 0.97, 0.97),  40,  [11, 15], 0.5),
    L_PUPIL: ((0.05, 0.05, 0.08),  60,  [12, 15]),
    TUSK:    ((0.94, 0.90, 0.76),  20,  [8, 14, 11]),
    SANDAL:  ((0.55, 0.38, 0.19),   0,  [13, 9]),
    FLOWER:  ((0.92, 0.52, 0.72),   0,  [10], 0.2),
}

RIBS = 8


def _cactus(q):
    ang = np.arctan2(q[:, 0], q[:, 2])
    ridge = np.cos(ang * RIBS) > 0.8
    tuft = np.modf(q[:, 1] * 5 + 10)[0] < 0.22
    return np.where(ridge & tuft, SPINE, CACTUS)


def lirili_scene(pose):
    cast = pose == 'cast'
    s = figure(-24)

    def body(p):
        ang = np.arctan2(p[:, 0], p[:, 2])
        d = capsule(p, (0, -0.60, 0), (0, -0.14, 0), 0.34, 0.30)
        return d - 0.025 * np.cos(ang * RIBS)

    s.add(_cactus, body)

    # Cactus arms: out, then up. Higher when casting.
    up = 0.30 if cast else 0.0
    for sx in (-1, 1):
        elbow = (0.62 * sx, -0.38 + up * 0.4, 0.02)
        hand = (0.66 * sx, -0.08 + up, 0.04)
        s.add(_cactus, lambda p, e=elbow: capsule(
            p, (0.24 * np.sign(e[0]), -0.42, 0), e, 0.10), blend=0.06)
        s.add(_cactus, lambda p, e=elbow, h=hand: capsule(p, e, h, 0.10, 0.09),
              blend=0.04)
        s.add(SANDAL, lambda p, sx=sx: ellipsoid(
            p, (0.16 * sx, -0.86, 0.08), (0.12, 0.06, 0.18)))
        s.add(_cactus, lambda p, sx=sx: capsule(
            p, (0.14 * sx, -0.66, 0), (0.16 * sx, -0.82, 0.04), 0.07),
            blend=0.05)

    # The head, and ears spread wide behind it.
    s.add(ELE, lambda p: sphere(p, (0, 0.34, 0.06), 0.38), blend=0.0)
    for sx in (-1, 1):
        s.add(ELE, lambda p, sx=sx: flat(lambda q: sphere(q, (0, 0, 0), 1.0),
                                         0.26, 0.34, 0.06)(
            p - np.array([0.42 * sx, 0.36, -0.14])))

    # Trunk: down the middle, then curled forward. Raised when casting.
    pts = [(0, 0.24, 0.38), (0, 0.02, 0.46), (-0.04, -0.16, 0.50)]
    pts += ([(-0.16, -0.04, 0.62), (-0.18, 0.12, 0.66)] if cast else
            [(-0.14, -0.28, 0.56), (-0.26, -0.24, 0.60)])
    radii = [0.11, 0.095, 0.08, 0.065, 0.055]
    for (a, b), ra, rb in zip(zip(pts, pts[1:]), radii, radii[1:]):
        s.add(ELE, lambda p, a=a, b=b, ra=ra, rb=rb: capsule(p, a, b, ra, rb),
              blend=0.04)

    for sx in (-1, 1):
        s.add(TUSK, lambda p, sx=sx: capsule(
            p, (0.15 * sx, 0.16, 0.34), (0.20 * sx, -0.06, 0.50), 0.045, 0.015))
        ex = 0.17 * sx
        s.add(L_EYE, lambda p, ex=ex: sphere(p, (ex, 0.42, 0.37), 0.16))
        s.add(L_PUPIL, lambda p, ex=ex: sphere(p, (ex - 0.06, 0.41, 0.51),
                                               0.08))

    # The flower, because cactus.
    for a in range(5):
        t = a * 2 * math.pi / 5
        c = (0.30 + 0.08 * math.cos(t), 0.74, 0.02 + 0.08 * math.sin(t))
        s.add(FLOWER, lambda p, c=c: sphere(p, c, 0.07))
    s.add(SPINE, lambda p: sphere(p, (0.30, 0.76, 0.02), 0.05))
    return s


# ---- Bombardiro Crocodilo -------------------------------------------------
#
# The boss cut down to a battler: a crocodile that is also a bomber. Banked
# toward the camera so both wings show, turned into profile like the shark.

C_SKIN, C_BELLY, C_TOOTH, C_EYE, C_PUPIL, WING, WING_TIP, BOMB, BOMB_FIN, \
    FUSE = range(10)

BOMBARD_MATERIALS = {
    C_SKIN:   ((0.34, 0.58, 0.26),  12,  [1, 2, 3, 4, 15]),
    C_BELLY:  ((0.80, 0.82, 0.58),   0,  [3, 4, 5]),
    C_TOOTH:  ((0.96, 0.96, 0.96),   0,  [5, 6], 0.3),
    C_EYE:    ((0.92, 0.84, 0.30),  30,  [12, 14, 15], 0.4),
    C_PUPIL:  ((0.40, 0.04, 0.03),   0,  [1, 11]),
    WING:     ((0.52, 0.56, 0.64),  30,  [8, 9, 10, 15]),
    WING_TIP: ((0.80, 0.20, 0.16),   0,  [11, 12]),
    BOMB:     ((0.20, 0.17, 0.14),  40,  [1, 13, 9, 10]),
    BOMB_FIN: ((0.90, 0.50, 0.18),   0,  [11, 12]),
    FUSE:     ((0.97, 0.85, 0.28),   0,  [14], 0.5),
}


def _croc(q):
    return np.where(q[:, 1] < -0.10, C_BELLY, C_SKIN)


def bombard_scene(pose):
    attack = pose == 'attack'
    s = figure(-56, tilt=-10 if attack else 0, roll=-38, pivot=(0, 0, 0),
               shift=(0, 0.02, -0.16 if attack else 0.0))

    def body(p):
        d = ellipsoid(p, (0, 0, -0.08), (0.30, 0.28, 0.66))
        # Long flat snout, and a lower jaw hinged open when he attacks.
        d = smin(d, box(p, (0, 0.0, 0.62), (0.15, 0.07, 0.26)) - 0.04, 0.08)
        drop = 0.10 if attack else 0.0
        jaw = box(p, (0, -0.14 - drop * 0.5, 0.58), (0.13, 0.04, 0.24)) - 0.03
        d = smin(d, jaw, 0.05)
        # The tail, tapering behind.
        d = smin(d, capsule(p, (0, 0.02, -0.6), (0, 0.10, -0.98), 0.14, 0.03),
                 0.1)
        return d

    s.add(_croc, body)

    # Scutes down the spine.
    for i in range(6):
        z = 0.30 - i * 0.18
        s.add(C_SKIN, lambda p, z=z: sphere(p, (0, 0.26 - abs(z) * 0.08, z),
                                            0.06), blend=0.03)

    # Eyes: bumps on top of the head, which is where a crocodile keeps them.
    for sx in (-1, 1):
        s.add(C_SKIN, lambda p, sx=sx: sphere(p, (0.13 * sx, 0.16, 0.34), 0.12),
              blend=0.03)
        s.add(C_EYE, lambda p, sx=sx: sphere(p, (0.16 * sx, 0.20, 0.40), 0.09))
        s.add(C_PUPIL, lambda p, sx=sx: flat(lambda q: sphere(
            q, (0, 0, 0), 1.0), 0.03, 0.07, 0.03)(
            p - np.array([0.17 * sx, 0.20, 0.485])))

    # Teeth along both jaws, on the near side.
    drop = 0.10 if attack else 0.0
    for i in range(5):
        z = 0.46 + i * 0.09
        s.add(C_TOOTH, lambda p, z=z: sphere(p, (0.15, -0.07, z), 0.03))
        s.add(C_TOOTH, lambda p, z=z: sphere(p, (0.14, -0.09 - drop, z - 0.04),
                                             0.028))

    # Wings: one slab across the fuselage, red-tipped.
    s.add(lambda q: np.where(np.abs(q[:, 0]) > 0.72, WING_TIP, WING),
          lambda p: box(p, (0, -0.02, -0.02), (0.84, 0.03, 0.26)) - 0.02)
    # The tail fin, upright.
    s.add(WING, flat(lambda p: capsule(p, (0, 0.06, -0.82), (0, 0.42, -0.96),
                                       0.10, 0.03), sx=0.25))

    # One bomb left, under the belly.
    s.add(BOMB, lambda p: capsule(p, (0, -0.44, 0.14), (0, -0.44, -0.16), 0.11))
    s.add(BOMB_FIN, flat(lambda p: capsule(p, (0, -0.44, -0.22),
                                           (0, -0.44, -0.34), 0.12, 0.12),
                         sy=1.0, sx=1.0, sz=0.5))
    s.add(WING, lambda p: capsule(p, (0, -0.28, 0.0), (0, -0.36, 0.0), 0.03))
    return s


PARTY = {
    'tung':    (tung_scene, TUNG_MATERIALS),
    'patapim': (patapim_scene, PATAPIM_MATERIALS),
    'trala':   (trala_scene, TRALA_MATERIALS),
    'lirili':  (lirili_scene, LIRILI_MATERIALS),
    'bombard': (bombard_scene, BOMBARD_MATERIALS),
}


def render_party(who, pose, palette):
    scene, materials = PARTY[who]
    return render_sprite(scene(pose), materials, palette)


def enemy_scenes():
    """Every render_*.py module's SCENES, merged: key -> (scene_fn, materials,
    size). The keys are ENEMY_ART's and PORTRAIT_ART's; a module that
    registers one takes that sprite over from its hand-drawn painter."""
    import glob
    import importlib
    out = {}
    for path in sorted(glob.glob('render_*.py')):
        mod = importlib.import_module(path[:-3])
        for key, entry in getattr(mod, 'SCENES', {}).items():
            if key in out:
                raise SystemExit('%s: %s is already rendered elsewhere'
                                 % (path, key))
            out[key] = entry
    return out


def bake():
    """Render everything that has a scene and write RENDERS, the file
    gen_sprites.py reads.

    The renders are baked rather than produced on every build because they are
    floating point: numpy's transcendentals and its BLAS differ between
    versions and machines, and one ulp on the wrong side of a ramp boundary is
    a different pixel. The baked file is the artwork; this is the tool that
    paints it. gen_sprites.py checks the file's digest against the renderer,
    the scene modules and the palettes, so a render that is out of date is an
    error, not a surprise.
    """
    import gen_sprites as gs
    out = ['# Pre-rendered sprites, one hex digit per pixel.',
           '# Generated by gen_render.py -- do not edit; run it again instead.',
           'digest ' + gs.render_digest()]

    def emit(key, c):
        out.append('sprite %s %d %d' % (key, c.w, c.h))
        out.extend(''.join('%x' % v for v in row) for row in c.px)
        print('rendered', key)

    for who, pal, _idle, _act, pose in gs.PARTY_RENDERS:
        for p in ('idle', pose):
            emit(who + '.' + p, render_party(who, p, gs.PALS[pal]))

    scenes = enemy_scenes()
    table = [e for e in gs.ENEMY_ART + gs.PORTRAIT_ART if e[0]]
    known = {key for key, _fn, _pal in table}
    for key in scenes:
        if key not in known:
            raise SystemExit('render key %r is in neither ENEMY_ART nor '
                             'PORTRAIT_ART' % key)
    for key, _fn, pal in table:
        if key in scenes:
            scene, materials, size = scenes[key]
            emit(key, render_sprite(scene(), materials,
                                    gs.PALS[getattr(gs, pal)], size))
    # Battle backdrops: five palettes, the dawn's five for the one that has
    # it, the palette slot of every character, and the dots.
    import render_backdrops as rb

    def pal_line(tag, pal):
        return tag + ' ' + ' '.join('%02x%02x%02x' % tuple(
            int(round(v * 31)) for v in c) for c in pal)

    for key in sorted(rb.BACKDROPS):
        r = rb.bake_backdrop(key)
        out.append('backdrop %s %d' % (key, 1 if 'dawn' in r else 0))
        out.extend(pal_line('pal', p) for p in r['pals'])
        if 'dawn' in r:
            out.extend(pal_line('dawn', p) for p in r['dawn'])
        out.extend(''.join('%d' % v for v in row) for row in r['slot'])
        out.extend(''.join('%x' % v for v in row) for row in r['idx'])
        print('rendered backdrop', key, '(%d characters)' % r['chars'])

    # The title: one set of characters and a palette set per animation step.
    import render_title as rt
    r = rt.bake_title()
    out.append('title %d %d' % (len(r['pals']), len(r['slot'])))
    for frame in r['pals']:
        out.extend(pal_line('pal', p) for p in frame)
    out.extend(''.join('%d' % v for v in row) for row in r['slot'])
    out.extend(''.join('%x' % v for v in row) for row in r['idx'])
    print('rendered title (%d characters)' % r['chars'])

    with open(gs.RENDERS, 'w', newline='\n') as f:
        f.write('\n'.join(out) + '\n')


if __name__ == '__main__':
    bake()
