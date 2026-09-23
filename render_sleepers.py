#!/usr/bin/env python3
"""Pre-rendered Sleepers: the six things the road east opens with.

Scenes for gen_render.py's bake. Enemies stand on the left and face right, so
every figure here turns with a positive yaw. Same lights as the party; the
ramps index each enemy's own palette in gen_sprites.PALS.

The lesson from the party applies double here: a render drifts toward
realism, and a Sleeper that looks realistic stops being funny. So the eyes
are too big, the props are too big, and the gag each docstring promises is
the thing each scene spends its pixels on.
"""
from gen_render import (figure, flat, sphere, ellipsoid, capsule, cylinder_y,
                        box, smin, np, math)


def _slab(pts, z, half, round_=0.02):
    """A flat convex polygon in the xy plane, `half` thick about z: bat and
    moth wings are shapes first and surfaces second."""
    pts = [np.asarray(v, float) for v in pts]
    area = sum(a[0] * b[1] - b[0] * a[1]
               for a, b in zip(pts, pts[1:] + pts[:1]))
    if area < 0:                  # the inside test wants counter-clockwise
        pts = pts[::-1]

    def fn(p):
        xy = p[:, :2]
        inside = np.ones(len(p), bool)
        d = np.full(len(p), np.inf)
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            e, w = b - a, xy - a
            h = np.clip((w @ e) / (e @ e), 0, 1)
            d = np.minimum(d, np.linalg.norm(w - h[:, None] * e, axis=1))
            inside &= (e[0] * w[:, 1] - e[1] * w[:, 0]) >= 0
        d2 = np.where(inside, -d, d)
        dz = np.abs(p[:, 2] - z) - half
        q = np.stack([d2, dz], 1)
        return (np.minimum(np.maximum(q[:, 0], q[:, 1]), 0)
                + np.linalg.norm(np.maximum(q, 0), axis=1) - round_)
    return fn


def _sleepy_eye(s, c, r, eye, lid, pupil, lid_at=0.25, look=(0.0, 0.0)):
    """A half-shut eye: the upper part of the ball is lid, so the whole cast
    reads as drowsy from the silhouette of the white alone."""
    cx, cy, cz = c
    s.add(lambda q: np.where(q[:, 1] > cy + r * lid_at, lid, eye),
          lambda p: sphere(p, c, r))
    s.add(pupil, lambda p: sphere(
        p, (cx + look[0], cy - r * 0.3 + look[1], cz + r * 0.78), r * 0.42))


# ---- Snorfly -------------------------------------------------------------
#
# A fly too drowsy to fly straight. The bubble is load-bearing: it is the
# biggest single shape after the body, and it is pink and glossy so it is the
# first thing you see.

F_BODY, F_STRIPE, F_HEAD, F_EYE, F_LID, F_PUPIL, F_WING, F_BUBBLE, F_LEG = \
    range(9)

SNORFLY_MATERIALS = {
    F_BODY:   ((0.46, 0.34, 0.66),   0,  [1, 2, 3, 4]),
    F_STRIPE: ((0.26, 0.18, 0.42),   0,  [1, 2]),
    F_HEAD:   ((0.56, 0.44, 0.78),  10,  [2, 3, 4, 15]),
    F_EYE:    ((0.97, 0.97, 1.00),  40,  [6, 15], 0.5),
    F_LID:    ((0.56, 0.44, 0.78),   0,  [3, 4]),
    F_PUPIL:  ((0.05, 0.05, 0.08),   0,  [7]),
    F_WING:   ((0.40, 0.50, 0.85),  30,  [13, 14, 6, 15], 0.15),
    F_BUBBLE: ((0.92, 0.66, 0.90),  60,  [5, 6, 15], 0.35),
    F_LEG:    ((0.16, 0.12, 0.26),   0,  [1, 2]),
}


def snorfly_scene():
    s = figure(40, pivot=(0, 0, 0), shift=(0, 0.05, 0.08))

    def abdomen(p):
        return ellipsoid(p, (0, -0.05, -0.28), (0.40, 0.38, 0.52))

    s.add(lambda q: np.where(np.sin(q[:, 2] * 13 + 1.0) > 0.45,
                             F_STRIPE, F_BODY), abdomen)
    s.add(F_HEAD, lambda p: sphere(p, (0, 0.08, 0.30), 0.34), blend=0.08)

    for sx in (-1, 1):
        _sleepy_eye(s, (0.19 * sx, 0.20, 0.46), 0.24, F_EYE, F_LID, F_PUPIL,
                    lid_at=0.35, look=(0.04, 0.02))
        # Wings: two glassy blades laid back over the body.
        s.add(F_WING, lambda p, sx=sx: flat(
            lambda q: capsule(q, (0, 0, 0), (0, 0.22, -0.42), 0.12, 0.24),
            sx=0.2)(p - np.array([0.24 * sx, 0.36, -0.12])))
        # Legs: dangling, because it is not landing so much as sagging.
        for z in (0.1, -0.3):
            s.add(F_LEG, lambda p, sx=sx, z=z: capsule(
                p, (0.18 * sx, -0.32, z), (0.24 * sx, -0.66, z + 0.1), 0.035))

    # The bubble, off the end of the nose.
    s.add(F_BUBBLE, lambda p: sphere(p, (0.02, -0.14, 0.78), 0.26))
    return s


# ---- Pilloworm -----------------------------------------------------------
#
# Three pillows in a trench coat: a caterpillar of pillows climbing to the
# right, the head one awake enough to be annoyed. Alternating white and linen
# so the three read as three, with tassels at the corners.

W_WHITE, W_LINEN, W_TASSEL, W_EYE, W_LID, W_PUPIL, W_MOUTH = range(7)

PILLOWORM_MATERIALS = {
    W_WHITE:  ((0.95, 0.95, 1.00),   0,  [10, 9, 8, 6]),
    W_LINEN:  ((0.80, 0.74, 0.58),   0,  [10, 9, 8]),
    W_TASSEL: ((0.94, 0.80, 0.30),   0,  [9, 11], 0.2),
    W_EYE:    ((0.97, 0.97, 1.00),  40,  [6, 15], 0.5),
    W_LID:    ((0.80, 0.74, 0.58),   0,  [9, 8]),
    W_PUPIL:  ((0.05, 0.05, 0.08),   0,  [7]),
    W_MOUTH:  ((0.35, 0.22, 0.45),   0,  [1, 2]),
}


def _pillow(c, half, tilt):
    ca, sa = math.cos(tilt), math.sin(tilt)

    def fn(p):
        q = p - np.asarray(c)
        # Tilt about z so the pillows step up the slope.
        x = q[:, 0] * ca + q[:, 1] * sa
        y = -q[:, 0] * sa + q[:, 1] * ca
        r = np.stack([x, y, q[:, 2]], 1)
        d = box(r, (0, 0, 0), half) - 0.13
        # Puff: fatter in the middle than at the seams.
        return d - 0.06 * np.cos(np.clip(x / half[0], -1, 1) * 1.5) \
                        * np.cos(np.clip(y / half[1], -1, 1) * 1.5)
    return fn


def pilloworm_scene():
    s = figure(18, pivot=(0, 0, 0))
    segs = [((-0.58, -0.62, -0.30), (0.24, 0.14, 0.22), 0.30, W_LINEN),
            ((-0.16, -0.18, -0.10), (0.27, 0.15, 0.24), 0.55, W_WHITE),
            ((0.30, 0.34, 0.14), (0.34, 0.24, 0.26), 0.20, W_LINEN)]
    for c, half, tilt, mat in segs:
        s.add(mat, _pillow(c, half, tilt))
        ca, sa = math.cos(tilt), math.sin(tilt)
        for kx in (-1, 1):
            for ky in (-1, 1):
                lx, ly = kx * (half[0] + 0.12), ky * (half[1] + 0.10)
                t = (c[0] + lx * ca - ly * sa, c[1] + lx * sa + ly * ca,
                     c[2] + 0.18)
                s.add(W_TASSEL, lambda p, t=t: sphere(p, t, 0.07))

    # The face, on the top pillow.
    hx, hy, hz = 0.34, 0.38, 0.50
    for sx in (-1, 1):
        _sleepy_eye(s, (hx + 0.17 * sx, hy + 0.08, hz), 0.15, W_EYE, W_LID,
                    W_PUPIL, lid_at=0.3, look=(0.04, 0))
    s.add(W_MOUTH, lambda p: ellipsoid(p, (hx + 0.02, hy - 0.14, hz + 0.02),
                                       (0.10, 0.06, 0.06)))
    return s


# ---- Dreambat ------------------------------------------------------------
#
# All wing and ear, wings spread wide so the silhouette is the bat before
# anything else. Big sleepy eyes and two tiny fangs.

B_BODY, B_WING, B_BONE, B_EYE, B_LID, B_PUPIL, B_FANG, B_EAR = range(8)

DREAMBAT_MATERIALS = {
    B_BODY:  ((0.30, 0.22, 0.48),   0,  [1, 2, 3]),
    B_WING:  ((0.45, 0.34, 0.68),   0,  [1, 2, 3, 4]),
    B_BONE:  ((0.28, 0.20, 0.44),   0,  [1, 2]),
    B_EYE:   ((0.97, 0.97, 1.00),  40,  [6, 15], 0.5),
    B_LID:   ((0.46, 0.35, 0.70),   0,  [3, 4]),
    B_PUPIL: ((0.05, 0.05, 0.08),   0,  [7]),
    B_FANG:  ((0.97, 0.97, 1.00),   0,  [6], 0.3),
    B_EAR:   ((0.86, 0.60, 0.86),   0,  [2, 3, 5]),
}


def dreambat_scene():
    s = figure(14, pivot=(0, 0, 0), shift=(0, 0.02, 0))

    s.add(B_BODY, lambda p: ellipsoid(p, (0, -0.18, 0), (0.24, 0.34, 0.22)))
    s.add(B_WING, lambda p: sphere(p, (0, 0.24, 0.02), 0.32), blend=0.08)

    for sx in (-1, 1):
        # Membrane: a pointed slab, scalloped along the trailing edge, so
        # the silhouette is a bat's and not a cape's.
        tri = [(0.14 * sx, 0.20), (0.98 * sx, 0.62), (0.78 * sx, -0.46),
               (0.16 * sx, -0.22)]

        def wing(p, tri=tri, sx=sx):
            d = _slab(tri, -0.04, 0.02)(p)
            for k in range(3):
                d = np.maximum(d, -sphere(p, (sx * (0.30 + k * 0.24), -0.50,
                                              -0.04), 0.16))
            return d
        s.add(B_WING, wing)
        # Finger bones, dark, fanning out to the points between scallops.
        for tip in ((0.98 * sx, 0.60), (0.66 * sx, -0.30), (0.42 * sx, -0.34)):
            s.add(B_BONE, lambda p, t=tip, sx=sx: capsule(
                p, (0.18 * sx, 0.18, 0.0), (t[0], t[1], -0.01), 0.04, 0.02))
        # Ears: tall, pink inside.
        s.add(B_EAR, lambda p, sx=sx: capsule(
            p, (0.16 * sx, 0.40, 0.0), (0.26 * sx, 0.86, -0.02), 0.13, 0.03),
            blend=0.04)
        _sleepy_eye(s, (0.13 * sx, 0.28, 0.24), 0.16, B_EYE, B_LID, B_PUPIL,
                    lid_at=0.3, look=(0.04, 0))
        s.add(B_FANG, lambda p, sx=sx: capsule(
            p, (0.06 * sx, 0.06, 0.30), (0.06 * sx, -0.04, 0.30), 0.035,
            0.01))
    return s


# ---- Sandman -------------------------------------------------------------
#
# Hood, no face, a fistful of night. The face is a hole with two gold lights
# in it, and the sand pours out of the fist toward the party in a stream you
# can follow.

S_ROBE, S_VOID, S_LIGHT, S_FIST, S_SAND, S_HEM = range(6)

SANDMAN_MATERIALS = {
    S_ROBE:  ((0.16, 0.20, 0.46),   0,  [1, 13, 14]),
    S_VOID:  ((0.02, 0.02, 0.04),   0,  [1]),
    S_LIGHT: ((1.00, 0.86, 0.36),   0,  [11, 15], 1.0),
    S_FIST:  ((0.80, 0.74, 0.56),   0,  [9, 8]),
    S_SAND:  ((0.96, 0.84, 0.40),   0,  [9, 11], 0.4),
    S_HEM:   ((0.30, 0.22, 0.50),   0,  [1, 2]),
}


def sandman_scene():
    s = figure(22, pivot=(0, 0, 0))

    def robe(p):
        d = capsule(p, (0, -0.70, 0), (0, 0.05, 0), 0.52, 0.24)
        return np.maximum(d, -(p[:, 1] + 0.90))

    s.add(S_ROBE, robe)
    s.add(S_HEM, lambda p: cylinder_y(p, (0, -0.85, 0), 0.55, 0.05, 0.03))

    def hood(p):
        d = sphere(p, (0, 0.40, -0.02), 0.38)
        d = smin(d, capsule(p, (0, 0.40, -0.1), (0, 0.78, -0.30), 0.2, 0.04),
                 0.1)
        return np.maximum(d, -sphere(p, (0, 0.36, 0.30), 0.25))

    s.add(S_ROBE, hood, blend=0.08)
    s.add(S_VOID, lambda p: sphere(p, (0, 0.36, 0.12), 0.24))
    for sx in (-1, 1):
        s.add(S_LIGHT, lambda p, sx=sx: sphere(p, (0.10 * sx, 0.40, 0.30),
                                               0.075))

    # The arm reaches toward the party, and the fist leaks.
    obj = s.obj
    fist = obj((0.62, 0.02, 0.2))
    s.add(S_ROBE, lambda p: capsule(p, (0.18, 0.02, 0.1), fist, 0.13, 0.10),
          blend=0.06)
    s.add(S_FIST, lambda p: sphere(p, fist, 0.13))
    for k in range(6):
        w = obj((0.66 + 0.03 * math.sin(k * 1.7), -0.18 - k * 0.12, 0.2))
        s.add(S_SAND, lambda p, w=w, k=k: sphere(p, w, 0.07 - k * 0.006))
    return s


# ---- Dusk moth -----------------------------------------------------------
#
# All wing, and a body like a thumb in a fur coat. The eyespots are the face
# you actually look at, so they are big, pink, and gold in the middle.

M_WING, M_HIND, M_SPOT, M_SPOT_C, M_FUR, M_STRIPE, M_EYE, M_FEELER = range(8)

MOTH_MATERIALS = {
    M_WING:   ((0.62, 0.52, 0.86),   0,  [2, 3, 4]),
    M_HIND:   ((0.44, 0.34, 0.66),   0,  [1, 2, 3]),
    M_SPOT:   ((0.90, 0.68, 0.90),   0,  [4, 5], 0.2),
    M_SPOT_C: ((0.97, 0.85, 0.38),   0,  [11], 0.5),
    M_FUR:    ((0.84, 0.80, 0.66),   0,  [9, 8]),
    M_STRIPE: ((0.36, 0.36, 0.42),   0,  [10]),
    M_EYE:    ((0.84, 0.28, 0.34),  40,  [12, 15], 0.3),
    M_FEELER: ((0.36, 0.36, 0.42),   0,  [1, 10]),
}


def _spots(cx, cy):
    def m(q):
        out = np.full(len(q), M_WING)
        for sx in (-1, 1):
            d = np.hypot(q[:, 0] - cx * sx, q[:, 1] - cy)
            out = np.where(d < 0.22, M_SPOT, out)
            out = np.where(d < 0.10, M_SPOT_C, out)
        return out
    return m


def moth_scene():
    s = figure(10, pivot=(0, 0, 0))

    for sx in (-1, 1):
        s.add(_spots(0.54, 0.40), flat(lambda q, sx=sx: capsule(
            q, (0.08 * sx, 0.02, 0), (0.62 * sx, 0.52, 0), 0.14, 0.38),
            sz=0.14))
        s.add(M_HIND, flat(lambda q, sx=sx: capsule(
            q, (0.08 * sx, -0.10, 0), (0.50 * sx, -0.56, 0), 0.12, 0.30),
            sz=0.14))
        s.add(M_FEELER, lambda p, sx=sx: capsule(
            p, (0.06 * sx, 0.56, 0.14), (0.32 * sx, 0.92, 0.1), 0.03))
        s.add(M_FEELER, lambda p, sx=sx: sphere(p, (0.33 * sx, 0.92, 0.1),
                                                0.05))
        s.add(M_EYE, lambda p, sx=sx: sphere(p, (0.08 * sx, 0.52, 0.26),
                                             0.07))

    def body(p):
        return ellipsoid(p, (0, -0.02, 0.14), (0.18, 0.52, 0.18))

    s.add(lambda q: np.where(np.sin(q[:, 1] * 19) > 0.55, M_STRIPE, M_FUR),
          body)
    s.add(M_FUR, lambda p: sphere(p, (0, 0.46, 0.16), 0.16), blend=0.05)
    return s


# ---- Snoring log ---------------------------------------------------------
#
# A log that snores. Lying down, which is the point: turned nearly side-on so
# the cut end with its rings faces the party, a face on the flank, eyes shut,
# mouth open, and a snore bubble on the go.

L_BARK, L_FURROW, L_RING, L_RING_D, L_LID, L_LASH, L_MOUTH, L_MOSS, \
    L_BUBBLE = range(9)

LOG_MATERIALS = {
    L_BARK:   ((0.50, 0.38, 0.24),   0,  [13, 2, 3, 4, 14]),
    L_FURROW: ((0.24, 0.18, 0.11),   0,  [13, 2]),
    L_RING:   ((0.86, 0.78, 0.58),   0,  [10, 14, 8]),
    L_RING_D: ((0.56, 0.44, 0.28),   0,  [3, 10]),
    L_LID:    ((0.62, 0.48, 0.30),   0,  [3, 4, 14]),
    L_LASH:   ((0.08, 0.07, 0.05),   0,  [1, 9]),
    L_MOUTH:  ((0.06, 0.05, 0.04),   0,  [1, 9]),
    L_MOSS:   ((0.30, 0.58, 0.30),   0,  [5, 6, 7]),
    L_BUBBLE: ((0.80, 0.80, 0.86),  60,  [11, 12, 15], 0.3),
}

LOG_R, LOG_H = 0.42, 0.78


def _log_surface(q):
    ang = np.arctan2(q[:, 1], q[:, 0])
    bark = np.where(np.sin(ang * 9 + np.sin(q[:, 2] * 5) * 0.6) > 0.7,
                    L_FURROW, L_BARK)
    r = np.hypot(q[:, 0], q[:, 1])
    ring = np.where(np.sin(r * 34) > 0.0, L_RING, L_RING_D)
    return np.where(q[:, 2] > LOG_H - 0.04, ring, bark)


def log_scene():
    s = figure(62, pivot=(0, 0, 0), shift=(0, 0.16, 0.04))

    def log(p):
        # A cylinder along object z, the cut end toward the party.
        q = np.stack([p[:, 0], p[:, 2], p[:, 1]], 1)
        d = np.stack([np.hypot(q[:, 0], q[:, 2]) - LOG_R + 0.04,
                      np.abs(q[:, 1]) - LOG_H + 0.04], 1)
        return (np.minimum(np.maximum(d[:, 0], d[:, 1]), 0.0)
                + np.linalg.norm(np.maximum(d, 0.0), axis=1) - 0.04)

    s.add(_log_surface, log)
    s.add(L_MOSS, lambda p: ellipsoid(p, (0.02, 0.38, -0.22),
                                      (0.30, 0.10, 0.40))
          + 0.03 * np.sin(p[:, 2] * 18) * np.sin(p[:, 0] * 14), blend=0.03)

    # Face on the near flank (-x faces the camera at this yaw). Eyes shut:
    # bulging lids with a dark lash line across each.
    fx = -LOG_R + 0.02
    for z in (0.14, 0.50):
        s.add(L_LID, lambda p, z=z: sphere(p, (fx, 0.10, z), 0.15))
        s.add(L_LASH, lambda p, z=z: capsule(p, (fx - 0.13, 0.07, z - 0.12),
                                             (fx - 0.13, 0.07, z + 0.12),
                                             0.035))
    s.add(L_MOUTH, lambda p: ellipsoid(p, (fx, -0.18, 0.32),
                                       (0.07, 0.09, 0.11)))
    # The snore.
    s.add(L_BUBBLE, lambda p: sphere(p, (fx - 0.16, -0.30, 0.52), 0.14))
    return s


SCENES = {
    'snorfly':   (snorfly_scene, SNORFLY_MATERIALS, 32),
    'pilloworm': (pilloworm_scene, PILLOWORM_MATERIALS, 32),
    'dreambat':  (dreambat_scene, DREAMBAT_MATERIALS, 32),
    'sandman':   (sandman_scene, SANDMAN_MATERIALS, 32),
    'moth':      (moth_scene, MOTH_MATERIALS, 32),
    'log':       (log_scene, LOG_MATERIALS, 32),
}
