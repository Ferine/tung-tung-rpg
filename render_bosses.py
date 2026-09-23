#!/usr/bin/env python3
"""The six bosses, pre-rendered at 64x64.

This is where the DKC look pays for itself: at 64px one unit is 32 pixels, so
a scute, a tooth or a fold in a robe is a shape rather than a pixel. Bosses
stand on the left and face right, so every figure() here takes a positive
yaw. Ramps index the palette ENEMY_ART assigns each one.
"""
from gen_render import (figure, flat, sphere, ellipsoid, capsule, cylinder_y,
                        box, smin, np, math)

BOSS = 64


def group(fns, center, radius):
    """Union of many small parts behind one bounding sphere.

    A boss has dozens of teeth and scutes, and the march evaluates every part
    at every step for every ray. Outside the sphere the distance to the sphere
    is a safe underestimate of the distance to anything inside it, so the
    parts are only evaluated for points that are near. `radius` must enclose
    every part.
    """
    center = np.asarray(center, float)

    def fn(p):
        d = sphere(p, center, radius)
        near = np.nonzero(d < 0.08)[0]
        if len(near):
            q = p[near]
            d[near] = np.min([g(q) for g in fns], axis=0)
        return d
    return fn


def _hash(q, k):
    """A cheap cell hash in [0,1): the same point always gets the same value,
    which is what keeps a bake reproducible on one machine."""
    c = np.floor(q * k)
    v = np.sin(c[:, 0] * 12.9898 + c[:, 1] * 78.233 + c[:, 2] * 37.719)
    return np.modf(np.abs(v * 43758.5453))[0]


# ---- Brr Brr Patapim, before he sits down --------------------------------
#
# The road, standing up. The party battler's construction at twice the size,
# so the bark gets real furrows, the moss gets lumps, and the brow and the
# knot of a mouth carry the anger the small one only implies. P_PATAPIM.

BK_BARK, BK_GRAIN, BK_MOSS, BK_MOSS_HI, BK_EYE, BK_PUPIL, BK_BROW, BK_FOOT, \
    BK_MOUTH = range(9)

BOSS_PATAPIM_MATERIALS = {
    BK_BARK:    ((0.50, 0.38, 0.24),   0,  [13, 2, 3, 4, 14]),
    BK_GRAIN:   ((0.26, 0.19, 0.12),   0,  [1, 13, 2]),
    BK_MOSS:    ((0.30, 0.58, 0.30),   0,  [5, 6, 7]),
    BK_MOSS_HI: ((0.42, 0.72, 0.40),   0,  [6, 7], 0.1),
    BK_EYE:     ((0.86, 0.82, 0.68),  30,  [10, 8, 15], 0.5),
    BK_PUPIL:   ((0.08, 0.07, 0.05),  60,  [9, 12]),
    BK_BROW:    ((0.20, 0.15, 0.10),   0,  [1, 13, 2]),
    BK_FOOT:    ((0.34, 0.26, 0.16),   0,  [13, 2, 3]),
    BK_MOUTH:   ((0.06, 0.04, 0.03),   0,  [1, 13], -0.3),
}


def _boss_bark(q):
    ang = np.arctan2(q[:, 0], q[:, 2])
    w = np.sin(ang * 9 + np.sin(q[:, 1] * 7) * 1.1)
    return np.where(w > 0.78, BK_GRAIN, BK_BARK)


def _boss_moss(q):
    return np.where(_hash(q, 9.0) > 0.72, BK_MOSS_HI, BK_MOSS)


def boss_patapim_scene():
    s = figure(18)

    def trunk(p):
        d = ellipsoid(p, (0, -0.10, 0), (0.60, 0.66, 0.48))
        return d + 0.018 * np.sin(np.arctan2(p[:, 0], p[:, 2]) * 9)

    def moss(p):
        d = ellipsoid(p, (0, 0.50, -0.02), (0.88, 0.30, 0.66))
        return d + np.sin(p[:, 0] * 13) * np.sin(p[:, 2] * 11) * 0.03

    s.add(_boss_bark, trunk)
    s.add(_boss_moss, moss, blend=0.05)
    clumps = []
    for i in range(7):                          # clumps along the crown edge
        a = i * 2 * math.pi / 7 + 0.3
        c = (0.72 * math.cos(a), 0.52 + 0.06 * (i % 2), 0.52 * math.sin(a))
        clumps.append(lambda p, c=c: sphere(p, c, 0.14))
    s.add(_boss_moss, group(clumps, (0, 0.55, 0), 0.95), blend=0.05)

    # Legs like stumps, and feet that grip.
    for sx in (-1, 1):
        s.add(_boss_bark, lambda p, sx=sx: capsule(
            p, (0.28 * sx, -0.66, 0), (0.30 * sx, -0.84, 0.04), 0.14),
            blend=0.08)
        s.add(BK_FOOT, lambda p, sx=sx: ellipsoid(
            p, (0.31 * sx, -0.90, 0.12), (0.21, 0.07, 0.30)))

    # Branch arms, thrown up: this is the one who has not sat down yet.
    obj = s.obj
    for a, b, twig in (((-0.50, 0.05, 0.1), (-0.88, 0.40, 0.1),
                        (-0.80, 0.86, 0.1)),
                       ((0.50, 0.05, 0.1), (0.90, 0.42, 0.1),
                        (0.84, 0.88, 0.1))):
        a, b, twig = obj(a), obj(b), obj(twig)
        s.add(_boss_bark, lambda p, a=a, b=b: capsule(p, a, b, 0.11, 0.075),
              blend=0.06)
        s.add(_boss_bark, lambda p, b=b, t=twig: capsule(p, b, t, 0.065, 0.03),
              blend=0.02)
        side = b + (twig - b) * 0.45 + np.array([0.12, 0.04, 0.0]) * np.sign(b[0])
        s.add(_boss_bark, lambda p, m=b + (twig - b) * 0.4, t=side: capsule(
            p, m, t, 0.04, 0.02))

    # The eyes, very old and very angry, under a brow like a lintel.
    for sx in (-1, 1):
        ex = 0.21 * sx
        s.add(BK_EYE, lambda p, ex=ex: sphere(p, (ex, 0.04, 0.39), 0.19))
        s.add(BK_PUPIL, lambda p, ex=ex: sphere(p, (ex + 0.07, 0.01, 0.54),
                                                0.10))
        s.add(BK_BROW, lambda p, sx=sx: capsule(
            p, (0.44 * sx, 0.30, 0.34), (0.06 * sx, 0.16, 0.50), 0.07),
            blend=0.02)

    # A mouth like a knot: a dark hollow with a lip of bark round it.
    s.add(BK_MOUTH, lambda p: ellipsoid(p, (0, -0.30, 0.44), (0.17, 0.07, 0.06)))
    s.add(_boss_bark, lambda p: flat(lambda q: capsule(
        q, (-0.2, 0, 0), (0.2, 0, 0), 0.08), 1.0, 0.8, 0.6)(
        p - np.array([0, -0.30, 0.40])), blend=0.03)
    return s


# ---- Ngantukan, the drowsing tide ----------------------------------------
#
# A head the size of the bay, rising out of it. Half-shut eyes -- a heavy lid
# over each -- a jaw of teeth along the waterline, spines down the crown, and
# the water itself: a wavy slab with foam on the crests. P_TRALA.

NG_SKIN, NG_BELLY, NG_LID, NG_EYE, NG_PUPIL, NG_TOOTH, NG_GUM, NG_WATER, \
    NG_FOAM, NG_BUBBLE, NG_SPINE = range(11)

BOSS_NGANTUK_MATERIALS = {
    NG_SKIN:   ((0.20, 0.38, 0.74),   6,  [13, 2, 3, 4, 12]),
    NG_BELLY:  ((0.74, 0.80, 0.92),   0,  [3, 12, 5]),
    NG_LID:    ((0.22, 0.40, 0.76),   0,  [1, 13, 2, 3]),
    NG_EYE:    ((0.94, 0.94, 0.98),  30,  [12, 5, 6], 0.4),
    NG_PUPIL:  ((0.04, 0.04, 0.08),  60,  [1, 7]),
    NG_TOOTH:  ((0.96, 0.96, 0.96),  20,  [5, 6, 15], 0.25),
    NG_GUM:    ((0.62, 0.16, 0.20),   0,  [1, 10], -0.2),
    NG_WATER:  ((0.16, 0.34, 0.74),  40,  [13, 2, 8, 3, 4]),
    NG_FOAM:   ((0.90, 0.94, 1.00),   0,  [12, 5, 6], 0.3),
    NG_BUBBLE: ((0.70, 0.82, 0.98),  60,  [12, 5, 15], 0.3),
    NG_SPINE:  ((0.20, 0.36, 0.70),   0,  [13, 2, 3]),
}


def _ng_skin(q):
    return np.where(q[:, 1] < -0.18, NG_BELLY, NG_SKIN)


def _wave(q):
    return (np.sin(q[:, 0] * 9 + q[:, 2] * 4) * 0.035
            + np.sin(q[:, 0] * 4 - q[:, 2] * 7) * 0.025)


def _ng_water(q):
    return np.where(q[:, 1] > -0.52 + _wave(q) * 0.2 + 0.02, NG_FOAM, NG_WATER)


def boss_ngantuk_scene():
    s = figure(16, pivot=(0, 0, 0))

    def head(p):
        d = ellipsoid(p, (0, 0.06, 0), (0.82, 0.66, 0.58))
        # A heavy lower jaw, wider than the skull: the bay-sized mouth.
        d = smin(d, ellipsoid(p, (0, -0.30, 0.10), (0.78, 0.30, 0.54)), 0.12)
        mouth = ellipsoid(p, (0, -0.24, 0.52), (0.62, 0.07, 0.20))
        return np.maximum(d, -mouth)

    s.add(_ng_skin, head)
    s.add(NG_GUM, lambda p: ellipsoid(p, (0, -0.24, 0.40), (0.56, 0.05, 0.12)))
    # Teeth along the jaw, top and bottom, curving with it.
    teeth = []
    for i in range(9):
        x = -0.48 + i * 0.12
        z = 0.50 - 0.35 * x * x
        teeth.append(lambda p, x=x, z=z: capsule(
            p, (x, -0.16, z), (x, -0.28, z + 0.02), 0.045, 0.01))
        if i % 2 == 0:
            teeth.append(lambda p, x=x, z=z: capsule(
                p, (x + 0.05, -0.34, z - 0.02), (x + 0.05, -0.23, z), 0.04, 0.01))
    s.add(NG_TOOTH, group(teeth, (0, -0.25, 0.4), 0.62))

    # Eyes, half shut: the lid is a shell cut off at the eye's equator.
    for sx in (-1, 1):
        c = np.array([0.33 * sx, 0.22, 0.46])
        s.add(NG_EYE, lambda p, c=c: sphere(p, c, 0.19))
        s.add(NG_PUPIL, lambda p, c=c: flat(lambda q: sphere(q, (0, 0, 0), 1.0),
                                            0.09, 0.07, 0.03)(
            p - (c + np.array([0.06, -0.05, 0.17]))))

        # Half shut: the lid comes down past the middle of the eye.
        def lid(p, c=c):
            shell = sphere(p, c, 0.215)
            return np.maximum(shell, (c[1] + 0.05) - p[:, 1])
        s.add(NG_LID, lid)
        # A heavy, sleepy brow ridge over the lid.
        s.add(NG_SKIN, lambda p, sx=sx: capsule(
            p, (0.54 * sx, 0.44, 0.26), (0.16 * sx, 0.40, 0.46), 0.06),
            blend=0.05)

    # Spines down the crown.
    spines = []
    for i, x in enumerate((-0.50, -0.17, 0.17, 0.50)):
        h = 0.98 if i in (1, 2) else 0.86
        spines.append(lambda p, x=x, h=h: flat(lambda q: capsule(
            q, (0, 0, 0), (x * 0.25, h - 0.46, -0.14), 0.20, 0.02), sx=0.55)(
            p - np.array([x, 0.46, -0.06])))
    s.add(NG_SPINE, group(spines, (0, 0.70, -0.1), 0.9), blend=0.05)

    # The water it stands out of, and a slow bubble breaking the surface.
    s.add(_ng_water, lambda p: box(p, (0, -0.80, 0), (1.9, 0.28, 1.2))
          - _wave(p))
    s.add(NG_BUBBLE, lambda p: sphere(p, (0.66, -0.44, 0.52), 0.08))
    s.add(NG_BUBBLE, lambda p: sphere(p, (0.80, -0.26, 0.46), 0.045))
    return s


# ---- The Sandman King ----------------------------------------------------
#
# The hooded shape, crowned, pouring hours. The hood is a hollow -- there is
# no face, only the dark and two lights in it -- the robe folds, the crown is
# gold points on a band, and the hourglass is held out toward the party with
# the sand running. P_ENEMY.

SK_ROBE, SK_FOLD, SK_VOID, SK_LIGHT, SK_GOLD, SK_GLASS, SK_SAND, SK_HAND, \
    SK_HEM = range(9)

BOSS_SANDKING_MATERIALS = {
    SK_ROBE:  ((0.14, 0.18, 0.42),   8,  [1, 13]),
    SK_FOLD:  ((0.06, 0.07, 0.16),   0,  [1]),
    SK_VOID:  ((0.02, 0.02, 0.04),   0,  [1], -1.0),
    SK_LIGHT: ((0.98, 0.86, 0.40),   0,  [11, 15], 0.45),
    SK_GOLD:  ((0.92, 0.78, 0.30),  30,  [9, 11, 15]),
    SK_GLASS: ((0.60, 0.66, 0.86),  60,  [13, 14, 6, 15], 0.15),
    SK_SAND:  ((0.92, 0.80, 0.42),   0,  [9, 11], 0.2),
    SK_HAND:  ((0.40, 0.30, 0.62),   0,  [2, 3]),
    SK_HEM:   ((0.28, 0.20, 0.50),   0,  [1, 2, 3]),
}


def _robe(q):
    ang = np.arctan2(q[:, 0], q[:, 2])
    fold = np.sin(ang * 7 + q[:, 1] * 1.5) > 0.7
    hem = q[:, 1] < -0.82
    return np.where(hem, SK_HEM, np.where(fold, SK_FOLD, SK_ROBE))


def boss_sandking_scene():
    s = figure(20, pivot=(0, 0, 0), shift=(0.14, 0, 0))

    def robe(p):
        d = capsule(p, (0, -0.88, 0), (0, 0.10, 0), 0.80, 0.34)
        d = np.maximum(d, -0.92 - p[:, 1])          # flat at the floor
        ang = np.arctan2(p[:, 0], p[:, 2])
        return d - 0.03 * np.sin(ang * 7 + p[:, 1] * 1.5)

    s.add(_robe, robe)

    # The hood: a shell with the front scooped out.
    def hood(p):
        d = sphere(p, (0, 0.36, 0), 0.42)
        d = smin(d, capsule(p, (0, 0.30, -0.10), (0, 0.66, -0.26), 0.20, 0.06),
                 0.1)
        cave = ellipsoid(p, (0, 0.32, 0.36), (0.30, 0.30, 0.26))
        return np.maximum(d, -cave)

    s.add(_robe, hood, blend=0.08)
    s.add(SK_VOID, lambda p: ellipsoid(p, (0, 0.32, 0.12), (0.28, 0.28, 0.12)))
    for sx in (-1, 1):
        s.add(SK_LIGHT, lambda p, sx=sx: sphere(p, (0.12 * sx + 0.03, 0.34, 0.25),
                                                0.065))

    # The crown: a band round the hood and five points off it.
    def band(p):
        return cylinder_y(p, (0, 0.62, -0.02), 0.34, 0.05, 0.02)
    s.add(SK_GOLD, band)
    points = []
    for i in range(7):
        a = (i - 3) * 0.42
        c = np.array([0.33 * math.sin(a), 0.64, 0.33 * math.cos(a)])
        tip = c * np.array([1.1, 1, 1.1]) + np.array([0, 0.28 - 0.06 * (i % 2), 0])
        points.append(lambda p, c=c, t=tip: capsule(p, c, t, 0.07, 0.012))
    s.add(SK_GOLD, group(points, (0, 0.78, 0), 0.55), blend=0.02)

    # The arm, out toward the party, and the hourglass in the hand.
    obj = s.obj
    hand = obj((0.52, -0.22, 0.4))
    s.add(_robe, lambda p: capsule(p, (0.30, -0.02, 0.06), hand, 0.13, 0.10),
          blend=0.08)
    s.add(SK_HAND, lambda p: sphere(p, hand + np.array([0.02, -0.06, 0.04]),
                                    0.07))
    g = obj((0.64, -0.52, 0.5))
    up = np.array([0, 1.0, 0])

    def bulbs(p):
        d = ellipsoid(p, g + up * 0.14, (0.14, 0.13, 0.14))
        return smin(d, ellipsoid(p, g - up * 0.14, (0.14, 0.13, 0.14)), 0.04)

    def sand(q):
        # Sand settles in the bottom bulb and runs in a thread through the
        # neck; the top bulb is nearly spent.
        low = q[:, 1] < g[1] - 0.12
        top = (q[:, 1] > g[1] + 0.20)
        return np.where(low | top, SK_SAND, SK_GLASS)

    s.add(sand, bulbs)
    for k in (1, -1):
        s.add(SK_GOLD, lambda p, k=k: cylinder_y(p, g + up * 0.29 * k, 0.16,
                                                 0.025, 0.01))
    for sx in (-1, 1):
        s.add(SK_GOLD, lambda p, sx=sx: capsule(
            p, g + np.array([0.14 * sx, -0.29, 0]),
            g + np.array([0.14 * sx, 0.29, 0]), 0.02))
    return s


# ---- Bombardiro Crocodilo ------------------------------------------------
#
# The premise at full size: the party battler's croc-bomber with room for the
# scutes to be scutes, a jaw full of separate teeth, a propeller, a roundel on
# each wing and all three bombs still on the rack. Banked toward the camera
# so both wings show. P_BOSS.

BC_SKIN, BC_BELLY, BC_SCUTE, BC_TOOTH, BC_EYE, BC_PUPIL, BC_WING, BC_TIP, \
    BC_BOMB, BC_FIN, BC_FUSE, BC_METAL, BC_MOUTH = range(13)

BOSS_CROCODILO_MATERIALS = {
    BC_SKIN:  ((0.34, 0.58, 0.26),  14,  [1, 2, 3, 4, 15]),
    BC_BELLY: ((0.80, 0.82, 0.58),   0,  [3, 4, 5]),
    BC_SCUTE: ((0.24, 0.44, 0.20),   0,  [1, 2, 3]),
    BC_TOOTH: ((0.96, 0.96, 0.96),  20,  [5, 6, 15], 0.3),
    BC_EYE:   ((0.95, 0.86, 0.30),  40,  [12, 14, 15], 0.5),
    BC_PUPIL: ((0.40, 0.04, 0.03),   0,  [1, 11]),
    BC_WING:  ((0.52, 0.56, 0.64),  30,  [8, 9, 10, 15]),
    BC_TIP:   ((0.80, 0.20, 0.16),  10,  [11, 12]),
    BC_BOMB:  ((0.20, 0.17, 0.14),  40,  [1, 13, 9, 10]),
    BC_FIN:   ((0.90, 0.50, 0.18),   0,  [11, 12]),
    BC_FUSE:  ((0.97, 0.85, 0.28),   0,  [14, 15], 0.6),
    BC_METAL: ((0.42, 0.45, 0.52),  40,  [8, 9, 10]),
    BC_MOUTH: ((0.40, 0.08, 0.06),   0,  [1, 11], -0.3),
}


def _boss_croc(q):
    return np.where(q[:, 1] < -0.10, BC_BELLY, BC_SKIN)


def _wing_mat(q):
    x = np.abs(q[:, 0])
    tip = x > 0.74
    # A roundel on each wing: red ring round a pale disc.
    r = np.hypot(x - 0.46, q[:, 2] + 0.02)
    ring = (r > 0.07) & (r < 0.12)
    return np.where(tip | ring, BC_TIP, BC_WING)


def boss_crocodilo_scene():
    s = figure(56, roll=34, pivot=(0, 0, 0), shift=(0, 0.04, 0.06))

    def body(p):
        d = ellipsoid(p, (0, 0, -0.10), (0.30, 0.28, 0.64))
        d = smin(d, box(p, (0, 0.03, 0.58), (0.15, 0.07, 0.26)) - 0.04, 0.08)
        jaw = box(p, (0, -0.16, 0.56), (0.13, 0.04, 0.24)) - 0.03
        d = smin(d, jaw, 0.05)
        d = smin(d, capsule(p, (0, 0.02, -0.6), (0, 0.12, -0.96), 0.14, 0.03),
                 0.1)
        gape = box(p, (0, -0.075, 0.66), (0.20, 0.03, 0.22))
        return np.maximum(d, -gape)

    s.add(_boss_croc, body)
    s.add(BC_MOUTH, lambda p: box(p, (0, -0.075, 0.60), (0.12, 0.028, 0.20)))

    # Scutes in two rows down the spine, and nostrils on the snout tip.
    scutes = []
    for i in range(8):
        z = 0.30 - i * 0.14
        y = 0.25 - abs(z + 0.1) * 0.10
        for sx in (-1, 1):
            scutes.append(lambda p, z=z, y=y, sx=sx: flat(
                lambda q: sphere(q, (0, 0, 0), 1.0), 0.05, 0.06, 0.06)(
                p - np.array([0.05 * sx, y, z])))
    s.add(BC_SCUTE, group(scutes, (0, 0.24, -0.20), 0.62), blend=0.02)
    s.add(BC_SCUTE, group([lambda p, sx=sx: sphere(p, (0.06 * sx, 0.11, 0.80),
                                                   0.035) for sx in (-1, 1)],
                          (0, 0.11, 0.80), 0.12))

    # Eyes: bumps on top of the head, yellow, slit pupils.
    for sx in (-1, 1):
        s.add(BC_SKIN, lambda p, sx=sx: sphere(p, (0.13 * sx, 0.17, 0.32),
                                               0.12), blend=0.03)
        s.add(BC_EYE, lambda p, sx=sx: sphere(p, (0.16 * sx, 0.21, 0.38), 0.09))
        s.add(BC_PUPIL, lambda p, sx=sx: flat(lambda q: sphere(
            q, (0, 0, 0), 1.0), 0.03, 0.07, 0.03)(
            p - np.array([0.17 * sx, 0.21, 0.465])))

    # Teeth, top and bottom, on both sides of the jaw.
    teeth = []
    for i in range(6):
        z = 0.44 + i * 0.075
        for sx in (-1, 1):
            teeth.append(lambda p, z=z, sx=sx: capsule(
                p, (0.15 * sx, -0.03, z), (0.15 * sx, -0.11, z), 0.032, 0.008))
            teeth.append(lambda p, z=z, sx=sx: capsule(
                p, (0.14 * sx, -0.14, z - 0.035), (0.14 * sx, -0.06, z - 0.035),
                0.028, 0.008))
    s.add(BC_TOOTH, group(teeth, (0, -0.08, 0.62), 0.32))

    # Wings: one slab across the fuselage, red-tipped, roundels.
    s.add(_wing_mat, lambda p: box(p, (0, -0.02, -0.04), (0.88, 0.03, 0.24))
          - 0.02)
    # Engine nacelles under each wing with a propeller disc at the front.
    nacelles, spinners, blades = [], [], []
    for sx in (-1, 1):
        x = 0.46 * sx
        nacelles.append(lambda p, x=x: capsule(p, (x, -0.08, -0.14),
                                               (x, -0.08, 0.26), 0.07, 0.06))
        spinners.append(lambda p, x=x: sphere(p, (x, -0.08, 0.32), 0.045))
        blades.append(lambda p, x=x: flat(lambda q: sphere(q, (0, 0, 0), 1.0),
                                          0.22, 0.03, 0.012)(
            p - np.array([x, -0.08, 0.34])))
    s.add(BC_METAL, group(nacelles, (0, -0.08, 0.06), 0.72))
    s.add(BC_TIP, group(spinners, (0, -0.08, 0.32), 0.55))
    s.add(BC_WING, group(blades, (0, -0.08, 0.34), 0.72))
    # Tail fin, upright, and the tailplane.
    s.add(BC_WING, flat(lambda p: capsule(p, (0, 0.10, -0.80), (0, 0.46, -0.96),
                                          0.11, 0.03), sx=0.25))
    s.add(_wing_mat, lambda p: box(p, (0, 0.06, -0.86), (0.30, 0.02, 0.08))
          - 0.015)

    # Three bombs still on the rack under the belly.
    s.add(BC_METAL, lambda p: box(p, (0, -0.33, 0.0), (0.04, 0.02, 0.34)))
    bombs, fins, fuses = [], [], []
    for z in (0.26, 0.0, -0.26):
        bombs.append(lambda p, z=z: capsule(p, (0, -0.47, z + 0.06),
                                            (0, -0.47, z - 0.05), 0.09))
        # flat() squashes about the origin, so squash first, then place.
        fins.append(lambda p, z=z: flat(lambda q: capsule(
            q, (0, 0, 0.05), (0, 0, -0.05), 0.10, 0.10), sz=0.5)(
            p - np.array([0, -0.47, z - 0.13])))
        fuses.append(lambda p, z=z: sphere(p, (0, -0.47, z + 0.16), 0.035))
    s.add(BC_BOMB, group(bombs, (0, -0.47, 0), 0.50))
    s.add(BC_FIN, group(fins, (0, -0.47, -0.04), 0.52))
    s.add(BC_FUSE, group(fuses, (0, -0.47, 0.16), 0.46))
    return s


# ---- Il Silenzio ---------------------------------------------------------
#
# A robe of nothing: the rim of it is lit, the inside is the dark. The head
# is a hollow with static where a face would be and two eyes in it. The
# second form is the same construction opened out: the robe spread wider,
# six arms unfolded, the eyes gone black with a pinprick, and the air around
# it full of sparks. One builder, one parameter. P_ENEMY.

SI_ROBE, SI_RIM, SI_VOID, SI_EYE, SI_EYE_DARK, SI_PIN, SI_ARM, SI_HAND, \
    SI_SPARK, SI_ST_A, SI_ST_B, SI_ST_C, SI_ST_D = range(13)

BOSS_SILENZIO_MATERIALS = {
    SI_ROBE:     ((0.07, 0.05, 0.13),   0,  [1, 2]),
    SI_RIM:      ((0.40, 0.28, 0.66),  20,  [1, 2, 3, 4]),
    SI_VOID:     ((0.02, 0.02, 0.04),   0,  [1], -1.0),
    SI_EYE:      ((0.97, 0.97, 1.00),   0,  [6, 15], 1.0),
    SI_EYE_DARK: ((0.03, 0.03, 0.05),   0,  [7], -0.5),
    SI_PIN:      ((1.00, 1.00, 1.00),   0,  [15], 1.5),
    SI_ARM:      ((0.46, 0.34, 0.72),  10,  [2, 3, 4]),
    SI_HAND:     ((0.96, 0.96, 1.00),   0,  [5, 6], 0.6),
    SI_SPARK:    ((1.00, 1.00, 1.00),   0,  [15], 1.5),
    SI_ST_A:     ((0.64, 0.52, 0.85),   0,  [4], 0.6),
    SI_ST_B:     ((0.88, 0.69, 0.91),   0,  [5], 0.6),
    SI_ST_C:     ((0.97, 0.97, 1.00),   0,  [6], 0.6),
    SI_ST_D:     ((0.02, 0.02, 0.04),   0,  [1], -1.0),
}


def _static(q):
    h = _hash(q, 26.0)
    return np.select([h < 0.16, h < 0.28, h < 0.36],
                     [SI_ST_A, SI_ST_B, SI_ST_C], SI_ST_D)


def _silenzio(second):
    spread = 1.55 if second else 1.0
    s = figure(12, pivot=(0, 0, 0))

    # The robe: a cone, hollowed and opened at the front so what shows is the
    # lit rim and the dark inside it. The hem never settles.
    def shell(p):
        base = 0.60 * spread
        d = capsule(p, (0, -0.86, 0), (0, 0.16, 0), base, 0.20)
        hem = 0.04 * np.sin(np.arctan2(p[:, 0], p[:, 2]) * 9)
        d = np.maximum(d, -0.90 - hem - p[:, 1])
        inner = capsule(p, (0, -0.86, 0.10), (0, 0.18, 0.04), base - 0.07, 0.13)
        return np.maximum(d, -inner)

    def robe_mat(q):
        # Lit only along the lips of the opening and the hem: the robe is an
        # edge round the dark, not a garment.
        ang = np.abs(np.arctan2(q[:, 0], q[:, 2]))
        lip = (ang > 0.62) & (ang < 0.86)
        hem = q[:, 1] < -0.82
        return np.where(lip | hem, SI_RIM, SI_ROBE)

    s.add(robe_mat, shell)
    s.add(SI_VOID, lambda p: capsule(p, (0, -0.86, 0.0), (0, 0.16, -0.02),
                                     0.60 * spread - 0.14, 0.10))

    # The head-shape: a hood round a disc of static.
    def hood(p):
        d = sphere(p, (0, 0.44, 0), 0.40)
        cave = ellipsoid(p, (0, 0.42, 0.36), (0.32, 0.32, 0.22))
        return np.maximum(d, -cave)

    def hood_mat(q):
        # Dark like the robe, lit only round the mouth of the hood: a ring
        # of light around a face that is not there.
        r = np.hypot(q[:, 0], q[:, 1] - 0.42)
        return np.where((r > 0.26) & (r < 0.38) & (q[:, 2] > 0.18),
                        SI_RIM, SI_ROBE)

    s.add(hood_mat, hood, blend=0.06)
    s.add(_static, lambda p: ellipsoid(p, (0, 0.42, 0.24), (0.31, 0.31, 0.08)))
    for sx in (-1, 1):
        c = np.array([0.13 * sx + 0.02, 0.44, 0.30])
        s.add(SI_EYE_DARK if second else SI_EYE,
              lambda p, c=c: sphere(p, c, 0.095))
        s.add(SI_PIN, lambda p, c=c: sphere(p, c + np.array([0.02, 0.0, 0.08]),
                                            0.035))

    if second:
        # Six arms, unfolded from the chest into a fan, each ending in a
        # pale hand.
        obj = s.obj
        root = obj((0.0, 0.08, 0.3))
        arms, hands = [], []
        for i in range(6):
            # A fan from low left, over the top, to low right.
            a = math.radians(200 - i * 44)
            tip = obj((0.86 * math.cos(a), 0.10 + 0.66 * math.sin(a), 0.3))
            mid = (root + tip) / 2 + np.array([0, 0.12, 0])
            arms.append(lambda p, a=root, b=mid: capsule(p, a, b, 0.065, 0.05))
            arms.append(lambda p, a=mid, b=tip: capsule(p, a, b, 0.05, 0.04))
            hands.append(lambda p, b=tip: sphere(p, b, 0.08))
        s.add(SI_ARM, group(arms, root, 1.3), blend=0.03)
        s.add(SI_HAND, group(hands, root, 1.35))

        # Sparks in the air, where the quiet is coming apart.
        rng = np.random.RandomState(0xC0DE)
        sparks = []
        for _ in range(14):
            x, y = rng.uniform(-0.94, 0.94), rng.uniform(-0.9, 0.94)
            if abs(x) < 0.55 and y < 0.6:
                continue
            c = obj((x, y, 0.8))
            sparks.append(lambda p, c=c: sphere(p, c, 0.035))
        s.add(SI_SPARK, group(sparks, obj((0, 0, 0.8)), 1.45))
    return s


def boss_silenzio_scene():
    return _silenzio(False)


def boss_silenzio2_scene():
    return _silenzio(True)


SCENES = {
    'boss_patapim':   (boss_patapim_scene, BOSS_PATAPIM_MATERIALS, BOSS),
    'boss_ngantuk':   (boss_ngantuk_scene, BOSS_NGANTUK_MATERIALS, BOSS),
    'boss_sandking':  (boss_sandking_scene, BOSS_SANDKING_MATERIALS, BOSS),
    'boss_crocodilo': (boss_crocodilo_scene, BOSS_CROCODILO_MATERIALS, BOSS),
    'boss_silenzio':  (boss_silenzio_scene, BOSS_SILENZIO_MATERIALS, BOSS),
    'boss_silenzio2': (boss_silenzio2_scene, BOSS_SILENZIO_MATERIALS, BOSS),
}
