#!/usr/bin/env python3
"""Pre-rendered enemies: the shore, the salt, the fortress and the hush.

Scenes for gen_render.py's bake, in the same terms as the party: a figure in
object space facing +z, a materials table whose ramps index the enemy's own
palette (ENEMY_ART in gen_sprites.py says which), and nothing else. Enemies
stand on the left and face right, so the yaws here are positive -- and a
positive yaw turns the object's -x flank toward the camera, which is why the
profile designs keep their detail on that side.
"""
from gen_render import (figure, flat, sphere, ellipsoid, capsule, cylinder_y,
                        box, smin, np, math)


def _torus_z(p, c, R, r, sx=1.0):
    """A ring lying in the xy plane, stretched sideways by sx."""
    q = p - np.asarray(c)
    ring = np.hypot(q[:, 0] / sx, q[:, 1]) - R
    return (np.hypot(ring, q[:, 2]) - r) * min(1.0, sx)


def _cyl_z(p, c, r, h, round_=0.0):
    """cylinder_y turned to lie along z."""
    return cylinder_y(p[:, [0, 2, 1]], (c[0], c[2], c[1]), r, h, round_)


# ---- Tide jelly (P_TRALA) -------------------------------------------------
#
# A bell and a lot of drift. The bell is glassy blue-white with a sleepy face
# on it; what reads is the curtain of tentacles, so they are thick, many, and
# bent by a current that is not there.

J_BELL, J_RIM, J_FRILL, J_TENT, J_EYE, J_PUPIL = range(6)

JELLY_MATERIALS = {
    J_BELL:  ((0.55, 0.70, 0.95),  40,  [2, 3, 4, 12, 5, 15], 0.15),
    J_RIM:   ((0.30, 0.45, 0.80),   0,  [13, 2, 3, 4]),
    J_FRILL: ((0.85, 0.30, 0.38),   0,  [1, 10], 0.2),
    J_TENT:  ((0.40, 0.55, 0.90),   0,  [13, 2, 3, 4, 12], 0.1),
    J_EYE:   ((0.97, 0.97, 1.00),  40,  [5, 6, 15], 0.5),
    J_PUPIL: ((0.05, 0.05, 0.08),  60,  [7, 15]),
}


def jelly_scene():
    s = figure(18, pivot=(0, 0, 0))

    def bell(p):
        d = ellipsoid(p, (0, 0.10, 0), (0.80, 0.62, 0.66))
        return np.maximum(d, -(p[:, 1] + 0.12))      # open underneath

    s.add(J_BELL, bell)
    s.add(J_RIM, lambda p: _torus_z(p[:, [0, 2, 1]], (0, 0, -0.10), 0.72,
                                    0.09, sx=1.0), blend=0.05)

    # The curtain: vertical capsules bent sideways by a sine of their height.
    for i in range(6):
        a = math.pi * (0.08 + 0.84 * i / 5.0)
        x, z = -0.62 * math.cos(a), 0.50 * math.sin(a) - 0.05
        ph = i * 1.3

        def tent(p, x=x, z=z, ph=ph):
            q = p.copy()
            q[:, 0] -= np.sin(q[:, 1] * 5.0 + ph) * 0.09
            return capsule(q, (x, -0.10, z), (x * 0.90, -0.94, z), 0.085,
                           0.045) * 0.9
        s.add(J_TENT, tent)

    # Oral frills, hanging from the middle.
    for sx in (-1, 1):
        def frill(p, sx=sx):
            q = p.copy()
            q[:, 0] -= np.sin(q[:, 1] * 6.0 + sx) * 0.07
            return capsule(q, (0.14 * sx, -0.10, 0.12), (0.18 * sx, -0.62,
                                                         0.16), 0.11,
                           0.06) * 0.9
        s.add(J_FRILL, frill)

    # A face on the bell: big, half-lidded, entirely unbothered.
    for sx in (-1, 1):
        ex = 0.26 * sx
        s.add(J_EYE, lambda p, ex=ex: sphere(p, (ex, 0.22, 0.56), 0.17))
        s.add(J_PUPIL, lambda p, ex=ex: sphere(p, (ex + 0.05, 0.19, 0.68),
                                               0.10))
        s.add(J_BELL, lambda p, ex=ex: capsule(
            p, (ex - 0.17, 0.33, 0.62), (ex + 0.17, 0.33, 0.62), 0.07))
    return s


# ---- Salt husk (P_ENEMY) --------------------------------------------------
#
# The shape somebody left behind when they lay down. A standing shell of
# salt-crusted linen, cracked all over and hollow: there is a hole in its
# chest and nothing inside it, and its eyes are holes too.

H_SHELL, H_CRACK, H_VOID = range(3)

HUSK_MATERIALS = {
    H_SHELL: ((0.72, 0.68, 0.56),   0,  [10, 9, 8]),
    H_CRACK: ((0.30, 0.26, 0.24),   0,  [1, 10]),
    H_VOID:  ((0.05, 0.03, 0.08),   0,  [1], -0.4),
}


def _husk_outer(p):
    d = ellipsoid(p, (0, -0.32, 0), (0.50, 0.58, 0.38))
    d = smin(d, sphere(p, (0.02, 0.44, 0.04), 0.36), 0.14)
    for sx in (-1, 1):                              # arms, hanging
        d = smin(d, capsule(p, (0.40 * sx, 0.02, 0.04), (0.74 * sx, -0.70, 0.14),
                            0.11, 0.08), 0.05)
    return d


def _husk_mat(q):
    outer = _husk_outer(q)
    crack = (np.abs(np.sin(q[:, 0] * 9 + q[:, 1] * 4)
                    + np.sin(q[:, 1] * 11 - q[:, 2] * 7) * 0.8) < 0.16)
    m = np.where(crack, H_CRACK, H_SHELL)
    return np.where(outer < -0.03, H_VOID, m)


def husk_scene():
    s = figure(24)

    def shell(p):
        outer = _husk_outer(p)
        d = np.maximum(outer, -(outer + 0.07))      # hollow
        hole = ellipsoid(p, (0.04, -0.22, 0.40), (0.22, 0.26, 0.30))
        for sx in (-1, 1):                          # eye holes
            hole = np.minimum(hole, sphere(p, (0.15 * sx + 0.03, 0.46, 0.36),
                                           0.12))
        return np.maximum(d, -hole)

    s.add(_husk_mat, shell)
    # The floor of the chest cavity, so the hole reads dark, not see-through.
    s.add(H_VOID, lambda p: ellipsoid(p, (0.03, -0.22, 0.10),
                                      (0.26, 0.30, 0.04)))
    for sx in (-1, 1):
        s.add(H_VOID, lambda p, sx=sx: sphere(p, (0.15 * sx + 0.03, 0.46,
                                                  0.18), 0.10))
    # Legs: two stubs of crust.
    for sx in (-1, 1):
        s.add(_husk_mat, lambda p, sx=sx: capsule(
            p, (0.20 * sx, -0.78, 0), (0.22 * sx, -0.86, 0.04), 0.12),
            blend=0.05)
    return s


# ---- Lull drone (P_ENEMY2) ------------------------------------------------
#
# Fortress machinery that hums people under. What reads is the lens: one big
# gold eye, lit from inside, in a squat hovering hull with a rotor on top.

D_HULL, D_BAND, D_RIM, D_LENS, D_GLINT, D_ROTOR = range(6)

DRONE_MATERIALS = {
    D_HULL:  ((0.46, 0.50, 0.60),  30,  [2, 3, 10, 4, 14, 15]),
    D_BAND:  ((0.16, 0.17, 0.21),   0,  [1, 2, 3]),
    D_RIM:   ((0.22, 0.24, 0.30),  20,  [1, 2, 3, 4]),
    D_LENS:  ((0.95, 0.70, 0.25),  50,  [5, 6, 7, 11, 15], 0.55),
    D_GLINT: ((1.00, 1.00, 1.00),   0,  [15], 1.0),
    D_ROTOR: ((0.60, 0.64, 0.72),   0,  [3, 4, 14]),
}


def drone_scene():
    s = figure(34, pivot=(0, 0, 0))

    s.add(lambda q: np.where(np.abs(q[:, 1] + 0.02) < 0.06, D_BAND, D_HULL),
          lambda p: ellipsoid(p, (0, 0.0, 0), (0.60, 0.48, 0.54)))

    # The eye: a housing out of the front, a glowing lens in it.
    s.add(D_RIM, lambda p: _torus_z(p, (0, 0.04, 0.48), 0.27, 0.08))
    s.add(D_RIM, lambda p: _cyl_z(p, (0, 0.04, 0.40), 0.30, 0.08, 0.03))
    s.add(D_LENS, lambda p: sphere(p, (0, 0.04, 0.36), 0.28))
    s.add(D_GLINT, lambda p: sphere(p, (-0.10, 0.14, 0.60), 0.055))

    # Rotor: a mast and two crossed blades.
    s.add(D_BAND, lambda p: capsule(p, (0, 0.40, 0), (0, 0.72, 0), 0.06))
    s.add(D_ROTOR, lambda p: box(p, (0, 0.76, 0), (0.86, 0.02, 0.07)) - 0.02)
    s.add(D_ROTOR, lambda p: box(p, (0, 0.78, 0), (0.07, 0.02, 0.62)) - 0.02)
    s.add(D_HULL, lambda p: sphere(p, (0, 0.80, 0), 0.08))

    # Landing legs.
    for sx in (-1, 1):
        s.add(D_BAND, lambda p, sx=sx: capsule(
            p, (0.34 * sx, -0.30, 0), (0.52 * sx, -0.80, 0.02), 0.06))
        s.add(D_HULL, lambda p, sx=sx: box(
            p, (0.54 * sx, -0.86, 0.02), (0.16, 0.035, 0.12)) - 0.02)
    return s


# ---- Quiet gun (P_ENEMY2) -------------------------------------------------
#
# Squat, slow, and hits like a dropped anvil. Turned into profile so the
# barrel is the silhouette; the red sensor is the only thing alive on it.

G_HULL, G_DARK, G_TREAD, G_SENSOR, G_BRASS = range(5)

TURRET_MATERIALS = {
    G_HULL:   ((0.48, 0.52, 0.62),  25,  [2, 3, 10, 4, 14, 15]),
    G_DARK:   ((0.20, 0.21, 0.26),  10,  [1, 2, 3]),
    G_TREAD:  ((0.28, 0.30, 0.36),   0,  [1, 2, 3, 10]),
    G_SENSOR: ((0.95, 0.30, 0.30),  40,  [5, 12, 7, 15], 0.6),
    G_BRASS:  ((0.85, 0.62, 0.25),  30,  [5, 6, 7, 11]),
}


def _tread(q):
    return np.where(np.sin(q[:, 2] * 22) > 0.3, G_DARK, G_TREAD)


def turret_scene():
    s = figure(76, pivot=(0, 0, 0), shift=(0, 0, 0.16))

    # Tracks: a rounded slab, ribbed.
    s.add(_tread, lambda p: box(p, (0, -0.70, 0), (0.46, 0.14, 0.78)) - 0.08)
    for z in (-0.6, -0.2, 0.2, 0.6):
        s.add(G_DARK, lambda p, z=z: _cyl_z(p[:, [2, 1, 0]],
                                            (z, -0.70, 0.0), 0.13, 0.50))
    s.add(G_HULL, lambda p: box(p, (0, -0.50, -0.02), (0.40, 0.08, 0.66))
          - 0.04, blend=0.03)

    # The dome.
    s.add(G_HULL, lambda p: ellipsoid(p, (0, -0.30, -0.08), (0.46, 0.40,
                                                            0.52)),
          blend=0.05)

    # The barrel: long, thick, with a muzzle brake and a brass band.
    # Cocked a little upward, so it clears the dome's outline.
    s.add(G_DARK, lambda p: capsule(p, (0, -0.06, 0.20), (0, 0.10, 0.86),
                                    0.14))
    s.add(G_DARK, lambda p: capsule(p, (0, 0.09, 0.82), (0, 0.12, 0.96),
                                    0.20))
    s.add(G_BRASS, lambda p: capsule(p, (0, 0.00, 0.44), (0, 0.02, 0.52),
                                     0.16))
    s.add(G_HULL, lambda p: capsule(p, (0, -0.08, 0.12), (0, -0.06, 0.26),
                                    0.24))

    # The sensor, on the flank that faces the camera.
    s.add(G_DARK, lambda p: sphere(p, (-0.34, -0.22, -0.20), 0.20))
    s.add(G_SENSOR, lambda p: sphere(p, (-0.46, -0.20, -0.18), 0.15))
    return s


# ---- Nod wisp (P_ENEMY) -----------------------------------------------------
#
# A light that wants you to follow it and lie down. A glowing head with a
# drowsy face, trailing a wave of itself off to the left. All of it glows.

W_HEAD, W_TRAIL, W_FACE = range(3)

WISP_MATERIALS = {
    W_HEAD:  ((0.80, 0.58, 0.92),   0,  [3, 4, 5, 6], 0.24),
    W_TRAIL: ((0.46, 0.32, 0.72),   0,  [2, 3, 4], 0.12),
    W_FACE:  ((0.10, 0.06, 0.16),   0,  [1, 2]),
}


def wisp_scene():
    s = figure(0, pivot=(0, 0, 0))
    hx, hy = 0.36, 0.26

    s.add(W_HEAD, lambda p: sphere(p, (hx, hy, 0), 0.36))
    # The trail: a run of blobs down a sine, thinning as it goes.
    n = 9
    for i in range(1, n + 1):
        t = i / float(n)
        x = hx - t * 1.20
        y = hy - 0.05 + math.sin(t * 5.0) * -0.42
        r = 0.22 * (1.0 - t) + 0.08
        s.add(W_TRAIL, lambda p, c=(x, y, -0.05 * t), r=r: sphere(p, c, r),
              blend=0.06)

    # Eyes shut, a small content smile: it is having a lovely time.
    for ex in (0.22, 0.50):
        s.add(W_FACE, lambda p, ex=ex: capsule(
            p, (ex - 0.07, hy + 0.06, 0.37), (ex + 0.07, hy + 0.06, 0.37),
            0.035))
    s.add(W_FACE, lambda p: _torus_z(p, (0.37, hy - 0.08, 0.35), 0.07,
                                     0.03) + np.maximum(0, p[:, 1] - (hy - 0.09)))
    return s


# ---- Murmur (P_ENEMY) -------------------------------------------------------
#
# A mouth with nothing behind it, saying nothing, constantly. A hood-shaped
# shell open to the front with only dark inside, and in the dark, a mouth:
# lips, teeth, no face. Motes circle it.

M_SHELL, M_VOID, M_LIP, M_TOOTH, M_MOTE = range(5)

MURMUR_MATERIALS = {
    M_SHELL: ((0.42, 0.30, 0.66),  15,  [1, 2, 3, 4]),
    M_VOID:  ((0.04, 0.03, 0.08),   0,  [1], -0.5),
    M_LIP:   ((0.20, 0.26, 0.60),  30,  [13, 14], 0.15),
    M_TOOTH: ((0.94, 0.92, 0.86),   0,  [9, 8, 6], 0.35),
    M_MOTE:  ((0.75, 0.62, 0.95),   0,  [4, 5], 0.4),
}


def _murmur_outer(p):
    return ellipsoid(p, (0, 0.02, -0.10), (0.74, 0.84, 0.52))


def murmur_scene():
    s = figure(14, pivot=(0, 0, 0))

    def shell(p):
        outer = _murmur_outer(p)
        d = np.maximum(outer, -(outer + 0.10))
        return np.maximum(d, p[:, 2] - 0.16)        # open to the front

    s.add(lambda q: np.where(_murmur_outer(q) < -0.05, M_VOID, M_SHELL), shell)
    # The mouth, hanging in the dark: wide open, all teeth, nothing else.
    s.add(M_LIP, lambda p: _torus_z(p, (0, -0.04, 0.16), 0.24, 0.05,
                                    sx=1.9))
    s.add(M_VOID, lambda p: ellipsoid(p, (0, -0.04, 0.08),
                                      (0.44, 0.22, 0.03)))
    for i in range(7):
        x = -0.33 + i * 0.11
        top = 0.17 - abs(x) * 0.12
        s.add(M_TOOTH, lambda p, x=x, y=top: capsule(
            p, (x, y, 0.18), (x, y - 0.13, 0.20), 0.05, 0.02))
        s.add(M_TOOTH, lambda p, x=x, y=-0.25 + abs(x) * 0.12: capsule(
            p, (x, y, 0.18), (x, y + 0.13, 0.20), 0.05, 0.02))
    for i in range(7):
        a = 0.4 + i * 0.83
        c = (0.86 * math.cos(a), 0.92 * math.sin(a), 0.05)
        s.add(M_MOTE, lambda p, c=c: sphere(p, c, 0.05))
    return s


SCENES = {
    'jelly':  (jelly_scene,  JELLY_MATERIALS,  32),
    'husk':   (husk_scene,   HUSK_MATERIALS,   32),
    'drone':  (drone_scene,  DRONE_MATERIALS,  32),
    'turret': (turret_scene, TURRET_MATERIALS, 32),
    'wisp':   (wisp_scene,   WISP_MATERIALS,   32),
    'murmur': (murmur_scene, MURMUR_MATERIALS, 32),
}
