#!/usr/bin/env python3
"""Pre-rendered scenes for six of the canon, one per region.

These are the famous faces, so each one's gag gets the detail budget: the
knife and the brows on the coffee, the bomb under the goose, the tyre and the
human legs under the frog, the octopus in the blueberry, the fruit down the
crocodile's back, the cow's rings. Eyes are drawn half as large again as
anatomy would have them and props are oversized -- at 32px a correctly
proportioned eye is two pixels and says nothing.

Enemies stand on the left and face right, so every yaw here is positive --
which turns object -x toward the camera. Near-side details sit at -x.
Each palette is borrowed from whoever ENEMY_ART says, and every ramp indexes
that palette only.
"""
from gen_render import (figure, flat, sphere, ellipsoid, capsule, cylinder_y,
                        box, smin, np, math)


def torus(p, c, big, small, axis=2):
    """A ring of radius `big`, tube `small`, around the given axis."""
    q = p - np.asarray(c)
    a, b = [k for k in range(3) if k != axis]
    ring = np.hypot(q[:, a], q[:, b]) - big
    return np.hypot(ring, q[:, axis]) - small


def tapered(p, y0, y1, r0, r1, rnd=0.03):
    """Vertical frustum from radius r0 at y0 to r1 at y1, edges rounded."""
    rad = np.hypot(p[:, 0], p[:, 2])
    t = np.clip((p[:, 1] - y0) / (y1 - y0), 0, 1)
    k = math.cos(math.atan2(r1 - r0, y1 - y0))
    side = (rad - (r0 + (r1 - r0) * t) + rnd) * k
    cap = np.maximum(y0 - p[:, 1], p[:, 1] - y1) + rnd
    return (np.minimum(np.maximum(side, cap), 0.0)
            + np.hypot(np.maximum(side, 0), np.maximum(cap, 0)) - rnd)


# ---- CAPPUCCINO ASSASSINO (P_ENEMY2) -------------------------------------
#
# A cup of coffee with a knife and a grudge. The cup goes white rather than
# the hand-drawn terracotta: white is what a cappuccino cup is, and it lets
# the red brows and the steel do the shouting.

CUP, COFFEE, FOAM, CA_EYE, CA_PUPIL, CA_BROW, BLADE, HILT, GUARD, SAUCER = \
    range(10)

CAPPUCCINO_MATERIALS = {
    CUP:      ((0.86, 0.88, 0.94),  20,  [3, 4, 14, 9, 15], 0.2),
    COFFEE:   ((0.50, 0.24, 0.12),   0,  [8, 5, 6]),
    FOAM:     ((0.94, 0.66, 0.36),   0,  [6, 7]),
    CA_EYE:   ((0.97, 0.97, 1.00),  40,  [14, 9, 15], 0.5),
    CA_PUPIL: ((0.04, 0.04, 0.06),  60,  [8, 14]),
    CA_BROW:  ((0.84, 0.26, 0.30),   0,  [5, 12], 0.2),
    BLADE:    ((0.70, 0.74, 0.82),  50,  [10, 4, 14, 9, 15]),
    HILT:     ((0.22, 0.20, 0.22),   0,  [8, 2, 3]),
    GUARD:    ((0.95, 0.80, 0.30),  30,  [6, 11, 15]),
    SAUCER:   ((0.70, 0.74, 0.82),  10,  [2, 3, 4, 14]),
}

CUP_Y0, CUP_Y1, CUP_R0, CUP_R1 = -0.56, 0.26, 0.42, 0.62


def _cup_top(q):
    rad = np.hypot(q[:, 0], q[:, 2])
    top = (q[:, 1] > CUP_Y1 - 0.13) & (rad < CUP_R1 - 0.05)
    heart = np.hypot(q[:, 0] + 0.06, q[:, 2] - 0.08) < 0.17
    return np.where(top, np.where(heart, FOAM, COFFEE), CUP)


def cappuccino_scene():
    s = figure(18, shift=(-0.06, 0.06, 0))

    def cup(p):
        d = tapered(p, CUP_Y0, CUP_Y1, CUP_R0, CUP_R1)
        bowl = cylinder_y(p, (0, CUP_Y1 + 0.02, 0), CUP_R1 - 0.06, 0.09)
        return np.maximum(d, -bowl)

    s.add(_cup_top, cup)
    s.add(CUP, lambda p: torus(p, (0.62, -0.12, 0.0), 0.17, 0.06, axis=2),
          blend=0.03)
    s.add(SAUCER, lambda p: cylinder_y(p, (0, -0.63, 0), 0.80, 0.035, 0.03))

    # The face on the cup: big eyes, and brows at war with each other.
    for sx in (-1, 1):
        ex = 0.20 * sx
        s.add(CA_EYE, lambda p, ex=ex: sphere(p, (ex, -0.14, 0.47), 0.19))
        s.add(CA_PUPIL, lambda p, ex=ex: sphere(p, (ex + 0.07, -0.15, 0.63),
                                                0.09))
        s.add(CA_BROW, lambda p, sx=sx: capsule(
            p, (0.42 * sx, 0.24, 0.50), (0.06 * sx, 0.12, 0.60), 0.06))

    # The knife: raised overhead, placed on screen so it cannot foreshorten.
    obj = s.obj
    grip, hilt_end = obj((-0.74, -0.10, 0.5)), obj((-0.76, 0.08, 0.5))
    tip = obj((-0.86, 0.92, 0.5))
    s.add(CUP, lambda p: capsule(p, (-0.46, -0.20, 0.1), grip, 0.075),
          blend=0.05)
    s.add(HILT, lambda p: capsule(p, grip, hilt_end, 0.06))
    s.add(GUARD, lambda p: sphere(p, hilt_end, 0.085))
    s.add(BLADE, lambda p: flat(lambda q: capsule(
        q, (0, 0, 0), tip - hilt_end, 0.12, 0.02), sz=0.4)(p - hilt_end))
    return s


# ---- BOMBOMBINI GUSINI (P_ENEMY2) ----------------------------------------
#
# A goose. It is also ordnance. In profile, because a goose is a neck, and a
# neck head-on is nothing; the bomb slung under it is as big as its body.

G_BODY, G_WING, G_BILL, G_EYE, G_PUPIL, G_BOMB, G_FIN, G_STRAP = range(8)

GUSINI_MATERIALS = {
    G_BODY:  ((0.90, 0.92, 0.96),  10,  [4, 14, 9, 15]),
    G_WING:  ((0.74, 0.78, 0.86),   0,  [3, 4, 14, 9]),
    G_BILL:  ((0.96, 0.66, 0.26),  20,  [5, 6, 7, 11]),
    G_EYE:   ((0.97, 0.97, 1.00),  40,  [9, 15], 0.5),
    G_PUPIL: ((0.04, 0.04, 0.06),  60,  [8, 14]),
    G_BOMB:  ((0.20, 0.22, 0.26),  50,  [8, 2, 3, 4, 15]),
    G_FIN:   ((0.84, 0.28, 0.32),   0,  [5, 12]),
    G_STRAP: ((0.16, 0.12, 0.10),   0,  [1, 8]),
}


def gusini_scene():
    s = figure(62, shift=(0, 0.02, 0.06))

    s.add(G_BODY, lambda p: ellipsoid(p, (0, 0.0, -0.08), (0.34, 0.32, 0.54)))
    s.add(G_BODY, lambda p: capsule(p, (0, 0.14, 0.30), (0, 0.50, 0.44),
                                    0.14, 0.11), blend=0.08)
    s.add(G_BODY, lambda p: sphere(p, (0, 0.60, 0.48), 0.19), blend=0.05)
    s.add(G_BODY, lambda p: capsule(p, (0, 0.06, -0.5), (0, 0.22, -0.72),
                                    0.14, 0.04), blend=0.05)
    s.add(G_BILL, lambda p: ellipsoid(p, (0, 0.56, 0.74), (0.09, 0.065, 0.2)))
    s.add(G_EYE, lambda p: sphere(p, (-0.13, 0.66, 0.55), 0.09))
    s.add(G_PUPIL, lambda p: sphere(p, (-0.16, 0.66, 0.61), 0.05))

    # Wings folded along the flanks, the near one lifted off the body.
    s.add(G_WING, lambda p: flat(lambda q: sphere(q, (0, 0, 0), 1.0),
                                 0.06, 0.16, 0.36)(
        p - np.array([-0.32, 0.16, -0.20])))
    s.add(G_WING, lambda p: flat(lambda q: sphere(q, (0, 0, 0), 1.0),
                                 0.07, 0.18, 0.40)(
        p - np.array([0.32, 0.10, -0.12])))

    # The bomb, slung on the near flank where it can be seen, fins aft.
    BX, BY = -0.40, -0.36
    s.add(G_BOMB, lambda p: capsule(p, (BX, BY, 0.24), (BX, BY, -0.18),
                                    0.19, 0.15))
    s.add(G_STRAP, lambda p: torus(p, (BX, BY, 0.04), 0.195, 0.03, axis=2))
    s.add(G_STRAP, lambda p: capsule(p, (BX * 0.6, BY + 0.14, 0.04),
                                     (-0.2, -0.12, 0.04), 0.035))
    for half in ((0.02, 0.24, 0.09), (0.24, 0.02, 0.09)):
        s.add(G_FIN, lambda p, h=half: box(p, (BX, BY, -0.38), h) - 0.01)

    # Legs, behind the bomb.
    for sx in (-1, 1):
        s.add(G_BILL, lambda p, sx=sx: capsule(p, (0.16 * sx, -0.26, -0.20),
                                               (0.18 * sx, -0.86, -0.18), 0.045))
        s.add(G_BILL, lambda p, sx=sx: ellipsoid(
            p, (0.18 * sx, -0.88, -0.08), (0.09, 0.035, 0.14)))
    return s


# ---- BONECA AMBALABU (P_PATAPIM) -----------------------------------------
#
# A frog, a tyre, and a pair of legs. Ask nobody. The tyre faces the camera,
# because a tyre's whole identity is the hole in it.

TYRE, TREAD, HUB, FROG, FROG_BELLY, AB_EYE, AB_PUPIL, AB_MOUTH, LEG = range(9)

AMBALABU_MATERIALS = {
    TYRE:       ((0.20, 0.20, 0.23),  20,  [1, 11, 12]),
    TREAD:      ((0.16, 0.16, 0.18),   0,  [1, 11]),
    HUB:        ((0.70, 0.58, 0.38),  30,  [3, 10, 14, 15]),
    FROG:       ((0.30, 0.58, 0.30),  10,  [5, 6, 7, 15]),
    FROG_BELLY: ((0.80, 0.74, 0.54),   0,  [10, 14, 8]),
    AB_EYE:     ((0.92, 0.90, 0.80),  40,  [8, 15], 0.5),
    AB_PUPIL:   ((0.06, 0.05, 0.04),  60,  [9, 12]),
    AB_MOUTH:   ((0.10, 0.08, 0.06),   0,  [1, 13]),
    LEG:        ((0.72, 0.56, 0.38),   0,  [2, 3, 4, 14]),
}

TYRE_C = (0.0, -0.20, 0.0)


def _tread(q):
    ang = np.arctan2(q[:, 1] - TYRE_C[1], q[:, 0])
    rad = np.hypot(q[:, 0], q[:, 1] - TYRE_C[1])
    groove = (np.cos(ang * 16) > 0.55) & (rad > 0.54)
    return np.where(groove, TREAD, TYRE)


def ambalabu_scene():
    s = figure(18)

    s.add(_tread, lambda p: torus(p, TYRE_C, 0.46, 0.17, axis=2))
    s.add(HUB, lambda p: torus(p, TYRE_C, 0.27, 0.035, axis=2))

    # The frog head, sat on top of the tyre like it was always going to be.
    s.add(FROG, lambda p: ellipsoid(p, (0, 0.38, 0.04), (0.50, 0.30, 0.38)),
          blend=0.04)
    s.add(FROG_BELLY, lambda p: ellipsoid(p, (0, 0.26, 0.12),
                                          (0.42, 0.14, 0.32)))
    for sx in (-1, 1):
        ex = 0.26 * sx
        s.add(FROG, lambda p, ex=ex: sphere(p, (ex, 0.64, 0.12), 0.20),
              blend=0.06)
        s.add(AB_EYE, lambda p, ex=ex: sphere(p, (ex, 0.67, 0.24), 0.155))
        s.add(AB_PUPIL, lambda p, ex=ex: sphere(p, (ex + 0.04, 0.67, 0.37),
                                                0.07))
    # A wide, patient mouth.
    s.add(AB_MOUTH, lambda p: capsule(p, (-0.34, 0.36, 0.36),
                                      (0.34, 0.36, 0.36), 0.03))

    # Human legs. Yes.
    for sx in (-1, 1):
        s.add(LEG, lambda p, sx=sx: capsule(p, (0.26 * sx, -0.56, 0.0),
                                            (0.30 * sx, -0.84, 0.04), 0.08))
        s.add(LEG, lambda p, sx=sx: ellipsoid(
            p, (0.31 * sx, -0.89, 0.12), (0.09, 0.05, 0.14)))
    return s


# ---- BLUEBERRINNI OCTOPUSINI (P_TRALA) -----------------------------------
#
# A blueberry. With an octopus in it. The berry is dark and dusty, the arms
# lighter, so the two things it is stay two things.

BERRY, CALYX, TENTACLE, SUCKER, OC_EYE, OC_PUPIL = range(6)

OCTOPUSINI_MATERIALS = {
    BERRY:    ((0.10, 0.16, 0.46),  30,  [13, 2, 8, 12]),
    CALYX:    ((0.20, 0.30, 0.56),   0,  [13, 2, 3]),
    TENTACLE: ((0.56, 0.72, 0.94),  12,  [3, 4, 12, 5]),
    SUCKER:   ((0.84, 0.30, 0.34),   0,  [10]),
    OC_EYE:   ((0.97, 0.97, 1.00),  40,  [5, 6, 15], 0.5),
    OC_PUPIL: ((0.04, 0.04, 0.06),  60,  [7, 12]),
}


def octopusini_scene():
    s = figure(16)

    s.add(BERRY, lambda p: ellipsoid(p, (0, 0.14, 0), (0.60, 0.56, 0.56)))
    # The crown of the fruit: a five-point calyx, sunk into the top.
    for a in range(5):
        t = a * 2 * math.pi / 5 + 0.3
        tip = (0.24 * math.cos(t), 0.80, 0.24 * math.sin(t))
        s.add(CALYX, lambda p, tip=tip: capsule(p, (0, 0.72, 0), tip,
                                                0.08, 0.035), blend=0.02)

    for sx in (-1, 1):
        ex = 0.24 * sx
        s.add(OC_EYE, lambda p, ex=ex: sphere(p, (ex, 0.10, 0.42), 0.20))
        s.add(OC_PUPIL, lambda p, ex=ex: sphere(p, (ex + 0.06, 0.09, 0.59),
                                                0.095))

    # Arms: six, out from under the berry, curling up at the ends.
    for i in range(6):
        t = i * 2 * math.pi / 6 + 0.5
        cx, cz = math.cos(t), math.sin(t)
        pts = [(0.30 * cx, -0.26, 0.30 * cz), (0.46 * cx, -0.56, 0.46 * cz),
               (0.66 * cx, -0.78, 0.60 * cz), (0.80 * cx, -0.68, 0.70 * cz)]
        radii = [0.12, 0.09, 0.065, 0.04]
        for (a, b), ra, rb in zip(zip(pts, pts[1:]), radii, radii[1:]):
            s.add(TENTACLE, lambda p, a=a, b=b, ra=ra, rb=rb:
                  capsule(p, a, b, ra, rb), blend=0.04)
        tip = pts[2]
        s.add(SUCKER, lambda p, c=(tip[0] * 0.96, tip[1] - 0.05,
                                   tip[2] * 0.96): sphere(p, c, 0.04))
    return s


# ---- GLORBO FRUTTODRILLO (P_LIRILI) --------------------------------------
#
# A crocodile made of fruit, or the other way up. In profile, snout right.
# The fruit is the scutes: pink berries and lemons down the spine, which is
# where a crocodile keeps its armour and this one keeps its lunch.

GL_SKIN, GL_BELLY, GL_TOOTH, GL_EYE, GL_PUPIL, BERRY_P, LEMON, GL_LEG = \
    range(8)

GLORBO_MATERIALS = {
    GL_SKIN:  ((0.30, 0.60, 0.30),  12,  [13, 2, 3, 4]),
    GL_BELLY: ((0.80, 0.86, 0.60),   0,  [3, 4, 5]),
    GL_TOOTH: ((0.97, 0.97, 0.97),   0,  [14, 11], 0.3),
    GL_EYE:   ((0.95, 0.92, 0.80),  40,  [14, 11, 15], 0.5),
    GL_PUPIL: ((0.04, 0.04, 0.06),  60,  [12, 7]),
    BERRY_P:  ((0.92, 0.44, 0.64),  40,  [9, 10, 15]),
    LEMON:    ((0.92, 0.90, 0.52),  30,  [4, 5, 14, 15]),
    GL_LEG:   ((0.24, 0.50, 0.26),   0,  [13, 2, 3]),
}


def _croc_belly(q):
    return np.where(q[:, 1] < -0.24, GL_BELLY, GL_SKIN)


def glorbo_scene():
    s = figure(60, pivot=(0, 0, 0), shift=(0, 0.06, 0.02))

    def body(p):
        d = ellipsoid(p, (0, -0.14, -0.12), (0.30, 0.26, 0.56))
        d = smin(d, sphere(p, (0, -0.04, 0.34), 0.27), 0.1)
        d = smin(d, box(p, (0, -0.12, 0.64), (0.16, 0.09, 0.26)) - 0.05,
                 0.08)
        d = smin(d, capsule(p, (0, -0.12, -0.6), (0, 0.02, -0.98), 0.16,
                            0.03), 0.08)
        return d

    s.add(_croc_belly, body)

    # Fruit down the spine.
    for i in range(5):
        z = 0.20 - i * 0.19
        mat = BERRY_P if i % 2 == 0 else LEMON
        s.add(mat, lambda p, z=z, r=0.15 - 0.012 * abs(i - 2): sphere(
            p, (-0.03, 0.12, z), r))

    # Eye, on a bump on top of the head.
    s.add(GL_SKIN, lambda p: sphere(p, (-0.12, 0.16, 0.38), 0.14), blend=0.03)
    s.add(GL_EYE, lambda p: sphere(p, (-0.16, 0.20, 0.43), 0.13))
    s.add(GL_PUPIL, lambda p: sphere(p, (-0.20, 0.21, 0.51), 0.065))

    # Teeth, both jaws, near side.
    for i in range(5):
        z = 0.52 + i * 0.08
        s.add(GL_TOOTH, lambda p, z=z: sphere(p, (-0.19, -0.09, z), 0.045))
        s.add(GL_TOOTH, lambda p, z=z: sphere(p, (-0.18, -0.19, z - 0.04),
                                              0.04))

    # Four stubby legs.
    for sx in (-1, 1):
        for z in (0.24, -0.40):
            s.add(GL_LEG, lambda p, sx=sx, z=z: capsule(
                p, (0.2 * sx, -0.30, z), (0.26 * sx, -0.66, z + 0.06), 0.08),
                blend=0.04)
    return s


# ---- LA VACCA SATURNO SATURNITA (P_ENEMY) --------------------------------
#
# A cow. With rings. Asleep, obviously. The rings are tilted open toward the
# camera; a ring seen edge-on is a line through a cow, which is only a cow.

COW, PATCH, MUZZLE, HORN, LID, HOOF, RING_A, RING_B = range(8)

SATURNITA_MATERIALS = {
    COW:    ((0.96, 0.94, 0.88),   0,  [10, 9, 8, 6], 0.15),
    PATCH:  ((0.22, 0.16, 0.30),   0,  [1, 2]),
    MUZZLE: ((0.92, 0.66, 0.84),  20,  [3, 4, 5, 6]),
    HORN:   ((0.86, 0.80, 0.62),  20,  [9, 8, 6]),
    LID:    ((0.10, 0.08, 0.14),   0,  [1]),
    HOOF:   ((0.30, 0.30, 0.36),   0,  [1, 10]),
    RING_A: ((0.96, 0.84, 0.40),  30,  [9, 11, 15]),
    RING_B: ((0.40, 0.48, 0.80),  20,  [13, 14]),
}


def _patches(q):
    n = (np.sin(q[:, 0] * 5.0 + 1.3) * np.sin(q[:, 1] * 6.0 + 0.4)
         * np.sin(q[:, 2] * 5.0 + 2.1))
    return np.where(n > 0.34, PATCH, COW)


def saturnita_scene():
    s = figure(40, pivot=(0, 0, 0), shift=(0, 0.02, 0.02))

    s.add(_patches, lambda p: ellipsoid(p, (0, -0.06, -0.12),
                                        (0.42, 0.38, 0.58)))
    s.add(COW, lambda p: ellipsoid(p, (0, 0.16, 0.48), (0.27, 0.25, 0.28)),
          blend=0.08)
    s.add(MUZZLE, lambda p: ellipsoid(p, (0, 0.06, 0.72), (0.20, 0.15, 0.14)))
    for sx in (-1, 1):
        s.add(LID, lambda p, sx=sx: sphere(p, (0.07 * sx, 0.07, 0.855), 0.03))
        # Eyes shut: a dark crescent on each side of the head.
        s.add(LID, lambda p, sx=sx: capsule(
            p, (0.15 * sx, 0.28, 0.66), (0.24 * sx, 0.26, 0.56), 0.035))
        s.add(HORN, lambda p, sx=sx: capsule(
            p, (0.14 * sx, 0.36, 0.42), (0.24 * sx, 0.60, 0.38), 0.055, 0.02))
        s.add(COW, lambda p, sx=sx: flat(lambda q: sphere(q, (0, 0, 0), 1.0),
                                         0.12, 0.05, 0.08)(
            p - np.array([0.29 * sx, 0.30, 0.42])))
        for z in (0.22, -0.42):
            s.add(COW, lambda p, sx=sx, z=z: capsule(
                p, (0.20 * sx, -0.34, z), (0.22 * sx, -0.62, z), 0.08),
                blend=0.04)
            s.add(HOOF, lambda p, sx=sx, z=z: sphere(p, (0.22 * sx, -0.66, z),
                                                     0.08))

    # The rings: two, gold outside and night-blue within, placed by their
    # normal in *world* space -- tipped toward the camera so they open into an
    # ellipse whichever way the cow is turned.
    n = np.array([0.22, 0.95, 0.24])
    n = s.obj(n / np.linalg.norm(n)) - s.obj((0, 0, 0))
    c = s.obj((0.0, -0.02, 0.0))

    def ring(p, big, small):
        q = p - c
        h = q @ n
        return np.hypot(np.linalg.norm(q - h[:, None] * n, axis=1) - big,
                        h) - small

    s.add(RING_A, lambda p: ring(p, 0.90, 0.045))
    s.add(RING_B, lambda p: ring(p, 0.78, 0.035))
    return s


SCENES = {
    'cappuccino': (cappuccino_scene, CAPPUCCINO_MATERIALS, 32),
    'gusini':     (gusini_scene, GUSINI_MATERIALS, 32),
    'ambalabu':   (ambalabu_scene, AMBALABU_MATERIALS, 32),
    'octopusini': (octopusini_scene, OCTOPUSINI_MATERIALS, 32),
    'glorbo':     (glorbo_scene, GLORBO_MATERIALS, 32),
    'saturnita':  (saturnita_scene, SATURNITA_MATERIALS, 32),
}
