"""Dialogue portraits, pre-rendered: eight head-and-shoulders busts.

A portrait is a battler seen from a metre away: turned almost to face the
camera, cropped at the shoulders, the head filling the 32x32 frame. The
battle renders showed that a face at this size survives only if it is
exaggerated, and a portrait is nothing but a face, so eyes here are bigger
again than on the battlers.

Nonna and Cappuccina borrow P_TUNG, a palette built for a wooden drum: skin
is the wood highlight, a headscarf is the bat's metal band. The ramps below
are what those fifteen colours can be made to mean.
"""
from gen_render import (figure, flat, sphere, ellipsoid, capsule,
                        cylinder_y, box, smin, np, math)

SIZE = 32
TURN = -12           # a portrait looks at you, nearly


def _eyes(s, eye, pupil, x, y, z, r, look=(-0.04, 0.0), pr=0.45):
    """Two eyes and their pupils, set into a surface at depth z. `look` nudges
    the pupils; a portrait looks slightly past you, toward the other
    speaker."""
    for sx in (-1, 1):
        c = np.array([x * sx, y, z])
        s.add(eye, lambda p, c=c: sphere(p, c, r))
        pc = c + np.array([look[0], look[1], r * 0.72])
        s.add(pupil, lambda p, pc=pc: sphere(p, pc, r * pr))


def _shoulders(s, mat, width=0.86):
    """The bust every portrait stands on, cropped by the bottom of the frame."""
    s.add(mat, lambda p: ellipsoid(p, (0, -1.08, -0.08), (width, 0.34, 0.42)))


# ---- Tung Tung Sahur -------------------------------------------------------
#
# The log, filling the frame, the cut end catching the light above. Eyes close
# enough to loom; the brows as red as his battler's.

T_WOOD, T_END, T_EYE, T_PUPIL, T_BROW, T_SLIT = range(6)

TUNG_MATERIALS = {
    T_WOOD:  ((0.62, 0.40, 0.20),   0,  [14, 2, 3, 4, 5]),
    T_END:   ((0.90, 0.72, 0.48),   0,  [3, 4, 5, 15]),
    T_EYE:   ((0.96, 0.96, 0.96),  40,  [12, 13, 6, 15], 0.55),
    T_PUPIL: ((0.04, 0.04, 0.07),  60,  [7, 13, 15]),
    T_BROW:  ((0.80, 0.18, 0.14),   0,  [11, 10]),
    T_SLIT:  ((0.10, 0.06, 0.03),   0,  [1, 14], -0.3),
}


def face_tung():
    s = figure(TURN, pivot=(0, 0, 0))
    R = 0.74

    def log(p):
        d = cylinder_y(p, (0, -0.4, 0), R, 1.1, 0.08)
        slit = box(p, (0, -0.62, R), (0.44, 0.08, 0.2))
        return np.maximum(d, -slit)

    s.add(T_WOOD, log)
    s.add(T_END, lambda p: cylinder_y(p, (0, 0.68, 0), R - 0.12, 0.03, 0.02))
    s.add(T_SLIT, lambda p: box(p, (0, -0.62, R - 0.19), (0.43, 0.07, 0.02)))
    _eyes(s, T_EYE, T_PUPIL, 0.30, 0.12, R - 0.10, 0.28)
    for sx in (-1, 1):
        s.add(T_BROW, lambda p, sx=sx: capsule(
            p, (0.62 * sx, 0.56, R - 0.04), (0.10 * sx, 0.42, R + 0.06), 0.08))
    return s


# ---- La Nonna -------------------------------------------------------------
#
# The only door that opens. A round face under white hair and a headscarf,
# a red shawl, and brows down hard: she is furious, which is the only sane
# response in the village.

N_SKIN, N_HAIR, N_SCARF, N_BAND, N_SHAWL, N_EYE, N_PUPIL, N_MOUTH = range(8)

NONNA_MATERIALS = {
    N_SKIN:  ((0.86, 0.66, 0.44),   0,  [3, 4, 9, 5]),
    N_HAIR:  ((0.95, 0.95, 0.97),  10,  [13, 6, 15]),
    N_SCARF: ((0.60, 0.60, 0.64),   0,  [12, 13]),
    N_BAND:  ((0.74, 0.16, 0.12),   0,  [11, 10]),
    N_SHAWL: ((0.46, 0.08, 0.08),   0,  [1, 11, 10]),
    N_EYE:   ((0.96, 0.96, 0.96),   0,  [6], 0.5),
    N_PUPIL: ((0.05, 0.04, 0.03),  40,  [7, 13]),
    N_MOUTH: ((0.30, 0.15, 0.08),   0,  [14, 2]),
}


def face_nonna():
    s = figure(TURN, pivot=(0, 0, 0))
    s.add(N_SKIN, lambda p: ellipsoid(p, (0, -0.02, 0.0), (0.56, 0.66, 0.52)))
    s.add(N_SKIN, lambda p: sphere(p, (0, -0.06, 0.52), 0.11), blend=0.05)
    for sx in (-1, 1):     # cheeks, round
        s.add(N_SKIN, lambda p, sx=sx: sphere(p, (0.30 * sx, -0.22, 0.32),
                                              0.18), blend=0.1)
    s.add(N_HAIR, lambda p: ellipsoid(p, (0, 0.38, -0.04), (0.62, 0.34, 0.54)))
    s.add(N_SCARF, lambda p: ellipsoid(p, (0, 0.52, -0.08), (0.70, 0.36, 0.58)))
    s.add(N_BAND, lambda p: np.maximum(
        ellipsoid(p, (0, 0.50, -0.06), (0.72, 0.38, 0.60)),
        np.abs(p[:, 1] - 0.36) - 0.06))
    # Scarf ends, knotted under the chin.
    s.add(N_SCARF, lambda p: capsule(p, (0.40, 0.2, 0.2), (0.22, -0.66, 0.26),
                                     0.09, 0.07))
    s.add(N_SCARF, lambda p: capsule(p, (-0.40, 0.2, 0.2), (-0.22, -0.66, 0.26),
                                     0.09, 0.07))
    s.add(N_SHAWL, lambda p: ellipsoid(p, (0, -1.0, -0.06), (0.92, 0.42, 0.5)))
    _eyes(s, N_EYE, N_PUPIL, 0.22, 0.10, 0.45, 0.13, pr=0.62)
    for sx in (-1, 1):     # brows, down at the middle: furious
        s.add(N_MOUTH, lambda p, sx=sx: capsule(
            p, (0.38 * sx, 0.32, 0.42), (0.08 * sx, 0.21, 0.52), 0.045))
    s.add(N_MOUTH, lambda p: capsule(p, (-0.16, -0.36, 0.46),
                                     (0.16, -0.36, 0.46), 0.035))
    return s


# ---- Brr Brr Patapim ------------------------------------------------------

BARK, GRAIN, MOSS, P_EYE, P_PUPIL, P_BROW, P_MOUTH = range(7)

PATAPIM_MATERIALS = {
    BARK:    ((0.50, 0.38, 0.24),   0,  [13, 2, 3, 4, 14]),
    GRAIN:   ((0.26, 0.19, 0.12),   0,  [13, 2]),
    MOSS:    ((0.30, 0.58, 0.30),   0,  [5, 6, 7]),
    P_EYE:   ((0.86, 0.82, 0.68),  30,  [10, 8, 15], 0.5),
    P_PUPIL: ((0.08, 0.07, 0.05),  60,  [9, 12]),
    P_BROW:  ((0.20, 0.15, 0.10),   0,  [13, 2]),
    P_MOUTH: ((0.10, 0.08, 0.05),   0,  [1, 13], -0.2),
}


def _bark(q):
    ang = np.arctan2(q[:, 0], q[:, 2])
    w = np.sin(ang * 9 + np.sin(q[:, 1] * 7) * 0.8)
    return np.where(w > 0.84, GRAIN, BARK)


def face_patapim():
    s = figure(TURN, pivot=(0, 0, 0))

    def head(p):
        d = ellipsoid(p, (0, -0.18, 0), (0.72, 0.86, 0.56))
        return d + 0.015 * np.sin(np.arctan2(p[:, 0], p[:, 2]) * 9)

    def canopy(p):
        d = ellipsoid(p, (0, 0.62, -0.04), (0.98, 0.36, 0.70))
        return d + np.sin(p[:, 0] * 9) * np.sin(p[:, 2] * 8) * 0.04

    s.add(_bark, head)
    s.add(MOSS, canopy, blend=0.04)
    _eyes(s, P_EYE, P_PUPIL, 0.27, 0.0, 0.40, 0.24)
    for sx in (-1, 1):
        s.add(P_BROW, lambda p, sx=sx: capsule(
            p, (0.54 * sx, 0.30, 0.34), (0.10 * sx, 0.22, 0.52), 0.07))
    s.add(P_MOUTH, lambda p: ellipsoid(p, (0, -0.52, 0.48), (0.16, 0.05, 0.06)))
    return s


# ---- Tralalero Tralala -----------------------------------------------------
#
# The snout angled at the viewer and the grin that is most of him. The dorsal
# fin rides over the shoulder so he is a shark even cropped.

SKIN, BELLY, T2_EYE, T2_PUPIL, GUM, TOOTH = range(6)

TRALA_MATERIALS = {
    SKIN:     ((0.30, 0.50, 0.85),  16,  [13, 2, 3, 4, 12, 15]),
    BELLY:    ((0.82, 0.86, 0.94),   0,  [3, 12, 5, 6]),
    T2_EYE:   ((0.96, 0.96, 1.00),  40,  [5, 6, 15], 0.5),
    T2_PUPIL: ((0.05, 0.05, 0.08),  60,  [7, 15]),
    GUM:      ((0.70, 0.18, 0.22),   0,  [1, 10], -0.2),
    TOOTH:    ((0.96, 0.96, 0.96),   0,  [5, 6], 0.4),
}


def face_trala():
    s = figure(-18, pivot=(0, 0, 0))

    def head(p):
        d = ellipsoid(p, (0, 0.10, -0.24), (0.66, 0.60, 0.80))
        d = smin(d, ellipsoid(p, (0, -0.04, 0.36), (0.56, 0.44, 0.42)), 0.2)
        # The grin is cut across the front, where the camera is, not under
        # the chin where a real shark keeps it.
        mouth = ellipsoid(p, (0, -0.18, 0.74), (0.58, 0.24, 0.32))
        return np.maximum(d, -mouth)

    s.add(lambda q: np.where(q[:, 1] < -0.22, BELLY, SKIN), head)
    s.add(GUM, lambda p: ellipsoid(p, (0, -0.18, 0.48), (0.50, 0.18, 0.14)))
    for i in range(9):     # the grin, all the way round the front
        a = math.radians(-64 + i * 16)
        x, z = 0.46 * math.sin(a), 0.44 + 0.20 * math.cos(a)
        s.add(TOOTH, lambda p, x=x, z=z: capsule(
            p, (x, 0.0, z), (x, -0.13, z + 0.02), 0.07, 0.025))
        s.add(TOOTH, lambda p, x=x, z=z: capsule(
            p, (x * 0.94, -0.36, z - 0.02), (x * 0.94, -0.24, z), 0.065, 0.02))
    # The dorsal fin. flat() squashes about the origin, so the fin is built
    # there and moved into place afterwards.
    fin = flat(lambda q: capsule(q, (0, 0, 0), (0, 0.5, -0.3), 0.24, 0.03),
               sx=0.3)
    s.add(SKIN, lambda p: fin(p - np.array([0.0, 0.56, -0.44])), blend=0.06)
    _eyes(s, T2_EYE, T2_PUPIL, 0.30, 0.34, 0.40, 0.21, pr=0.5)
    _shoulders(s, SKIN, 0.9)
    return s


# ---- Lirili Larila ---------------------------------------------------------
#
# The elephant's head, ears spread to the edges of the frame, the cactus
# shoulders below -- and the clock she wears, because she is the one who
# remembers. The hand-drawn portrait had the clock and forgot the elephant.

CACTUS, SPINE, ELE, L_EYE, L_PUPIL, TUSK, FLOWER, CLOCK, FACE, HANDS = range(10)

LIRILI_MATERIALS = {
    CACTUS:  ((0.30, 0.62, 0.30),   0,  [13, 2, 3, 4]),
    SPINE:   ((0.88, 0.92, 0.70),   0,  [5], 0.3),
    ELE:     ((0.44, 0.44, 0.50),   0,  [6, 7, 8]),
    L_EYE:   ((0.97, 0.97, 0.97),  40,  [11, 15], 0.5),
    L_PUPIL: ((0.05, 0.05, 0.08),  60,  [12, 15]),
    TUSK:    ((0.94, 0.90, 0.76),  20,  [8, 14, 11]),
    FLOWER:  ((0.92, 0.52, 0.72),   0,  [10], 0.2),
    CLOCK:   ((0.70, 0.70, 0.76),  30,  [7, 8, 11]),
    FACE:    ((0.94, 0.90, 0.76),   0,  [14, 11], 0.3),
    HANDS:   ((0.05, 0.05, 0.08),   0,  [12]),
}


def _cactus(q):
    ang = np.arctan2(q[:, 0], q[:, 2])
    ridge = np.cos(ang * 8) > 0.8
    tuft = np.modf(q[:, 1] * 5 + 10)[0] < 0.22
    return np.where(ridge & tuft, SPINE, CACTUS)


def face_lirili():
    s = figure(TURN, pivot=(0, 0, 0))
    s.add(_cactus, lambda p: ellipsoid(p, (0, -1.0, -0.1), (0.78, 0.42, 0.46)))
    s.add(ELE, lambda p: sphere(p, (0, 0.18, 0.0), 0.56))
    for sx in (-1, 1):
        s.add(ELE, lambda p, sx=sx: flat(lambda q: sphere(q, (0, 0, 0), 1.0),
                                         0.34, 0.46, 0.07)(
            p - np.array([0.66 * sx, 0.20, -0.20])))
    pts = [(0, 0.02, 0.50), (0, -0.28, 0.60), (-0.04, -0.52, 0.62),
           (-0.18, -0.64, 0.66)]
    radii = [0.16, 0.13, 0.10, 0.08]
    for (a, b), ra, rb in zip(zip(pts, pts[1:]), radii, radii[1:]):
        s.add(ELE, lambda p, a=a, b=b, ra=ra, rb=rb: capsule(p, a, b, ra, rb),
              blend=0.05)
    for sx in (-1, 1):
        s.add(TUSK, lambda p, sx=sx: capsule(
            p, (0.22 * sx, -0.08, 0.44), (0.30 * sx, -0.40, 0.62), 0.06, 0.02))
    _eyes(s, L_EYE, L_PUPIL, 0.22, 0.26, 0.46, 0.15)
    for a in range(5):
        t = a * 2 * math.pi / 5
        c = (0.42 + 0.1 * math.cos(t), 0.74, 0.10 + 0.1 * math.sin(t))
        s.add(FLOWER, lambda p, c=c: sphere(p, c, 0.09))
    s.add(SPINE, lambda p: sphere(p, (0.42, 0.76, 0.10), 0.06))
    # The clock, worn on the chest, just above the crop.
    s.add(CLOCK, lambda p: np.maximum(
        sphere(p, (0.44, -0.76, 0.34), 0.24), np.abs(p[:, 2] - 0.40) - 0.05))
    s.add(FACE, lambda p: np.maximum(
        sphere(p, (0.44, -0.76, 0.38), 0.18), np.abs(p[:, 2] - 0.44) - 0.02))
    s.add(HANDS, lambda p: capsule(p, (0.44, -0.76, 0.47), (0.44, -0.62, 0.47),
                                   0.025))
    s.add(HANDS, lambda p: capsule(p, (0.44, -0.76, 0.47), (0.54, -0.80, 0.47),
                                   0.025))
    return s


# ---- Bombardiro Crocodilo --------------------------------------------------
#
# The long jaw across the frame, teeth first; yellow reptile eyes up on the
# skull; a wing cropped at each shoulder and one engine still glowing.

C_SKIN, C_BELLY, C_TOOTH, C_EYE, C_PUPIL, WING, GLOW = range(7)

BOMBARD_MATERIALS = {
    C_SKIN:  ((0.34, 0.58, 0.26),  12,  [1, 2, 3, 4, 15]),
    C_BELLY: ((0.80, 0.82, 0.58),   0,  [3, 4, 5]),
    C_TOOTH: ((0.96, 0.96, 0.96),   0,  [5, 6], 0.4),
    C_EYE:   ((0.92, 0.84, 0.30),  30,  [12, 14, 15], 0.5),
    C_PUPIL: ((0.10, 0.08, 0.06),   0,  [7]),
    WING:    ((0.52, 0.56, 0.64),  30,  [8, 9, 10, 15]),
    GLOW:    ((0.95, 0.60, 0.20),   0,  [12, 14], 0.8),
}


def face_bombard():
    s = figure(-30, pivot=(0, 0, 0))

    def head(p):
        d = ellipsoid(p, (0, 0.12, -0.3), (0.56, 0.46, 0.62))
        d = smin(d, box(p, (0, 0.02, 0.46), (0.32, 0.14, 0.52)) - 0.07, 0.15)
        jaw = box(p, (0, -0.28, 0.42), (0.30, 0.08, 0.50)) - 0.05
        return smin(d, jaw, 0.08)

    s.add(lambda q: np.where(q[:, 1] < -0.2, C_BELLY, C_SKIN), head)
    for i in range(6):
        z = 0.12 + i * 0.16
        for sx in (-1, 1):
            s.add(C_TOOTH, lambda p, z=z, sx=sx: capsule(
                p, (0.34 * sx, -0.12, z), (0.34 * sx, -0.22, z), 0.045, 0.015))
    for sx in (-1, 1):
        s.add(C_SKIN, lambda p, sx=sx: sphere(p, (0.26 * sx, 0.46, 0.06), 0.18),
              blend=0.06)
        s.add(C_EYE, lambda p, sx=sx: sphere(p, (0.28 * sx, 0.50, 0.16), 0.14))
        s.add(C_PUPIL, lambda p, sx=sx: flat(lambda q: sphere(
            q, (0, 0, 0), 1.0), 0.03, 0.11, 0.03)(
            p - np.array([0.28 * sx, 0.50, 0.29])))
    # Wings at the shoulders, and the engine on the near one.
    s.add(WING, lambda p: box(p, (0, -0.86, -0.3), (1.2, 0.05, 0.3)) - 0.03)
    s.add(C_SKIN, lambda p: ellipsoid(p, (0, -0.86, -0.3), (0.5, 0.3, 0.6)))
    s.add(WING, lambda p: cylinder_y(p, (-0.66, -0.92, -0.1), 0.16, 0.2, 0.05))
    s.add(GLOW, lambda p: sphere(p, (-0.66, -0.92, 0.08), 0.1))
    return s


# ---- Il Silenzio ------------------------------------------------------------
#
# A shape, and nothing in it: the hood of the boss, ring-lit round a face of
# static, two absences where eyes go. Below it, the feed, scrolling forever.

SI_ROBE, SI_RIM, SI_EYE, SI_FEED, SI_FEED2, SI_ST_A, SI_ST_B, SI_ST_D = range(8)

SILENZIO_MATERIALS = {
    SI_ROBE:  ((0.07, 0.05, 0.13),   0,  [1, 2]),
    SI_RIM:   ((0.40, 0.28, 0.66),  20,  [2, 3, 4]),
    SI_EYE:   ((0.02, 0.02, 0.04),   0,  [7], -1.0),
    SI_FEED:  ((0.40, 0.50, 0.90),   0,  [13, 14], 0.6),
    SI_FEED2: ((0.22, 0.30, 0.60),   0,  [13], 0.3),
    SI_ST_A:  ((0.64, 0.52, 0.85),   0,  [4, 5], 0.6),
    SI_ST_B:  ((0.97, 0.97, 1.00),   0,  [6], 0.6),
    SI_ST_D:  ((0.03, 0.02, 0.06),   0,  [1], -1.0),
}


def _static(q):
    # A hash of the cell a point falls in: deterministic grain, no RNG state.
    k = np.floor(q[:, :2] * 22.0)
    h = np.modf(np.abs(np.sin(k[:, 0] * 12.9898 + k[:, 1] * 78.233)) * 43758.5)[0]
    return np.select([h < 0.18, h < 0.30], [SI_ST_A, SI_ST_B], SI_ST_D)


def face_silenzio():
    s = figure(0, pivot=(0, 0, 0))

    def hood(p):
        d = sphere(p, (0, 0.12, 0), 0.70)
        d = smin(d, ellipsoid(p, (0, -0.8, -0.1), (0.9, 0.5, 0.5)), 0.2)
        cave = ellipsoid(p, (0, 0.10, 0.58), (0.52, 0.56, 0.36))
        return np.maximum(d, -cave)

    def hood_mat(q):
        r = np.hypot(q[:, 0], (q[:, 1] - 0.10) * 0.93)
        return np.where((r > 0.44) & (r < 0.62) & (q[:, 2] > 0.3),
                        SI_RIM, SI_ROBE)

    s.add(hood_mat, hood)
    s.add(_static, lambda p: ellipsoid(p, (0, 0.10, 0.34),
                                       (0.50, 0.54, 0.08)))
    for sx in (-1, 1):
        s.add(SI_EYE, lambda p, sx=sx: box(p, (0.22 * sx, 0.18, 0.42),
                                           (0.12, 0.035, 0.03)))
    for i in range(5):                          # the feed
        x = -0.72 + i * 0.36
        s.add(SI_FEED if i % 2 else SI_FEED2,
              lambda p, x=x: box(p, (x, -0.72, 0.5), (0.13, 0.03, 0.02)))
        s.add(SI_FEED2 if i % 2 else SI_FEED,
              lambda p, x=x: box(p, (x + 0.1, -0.88, 0.5), (0.13, 0.03, 0.02)))
    return s


# ---- Ballerina Cappuccina ---------------------------------------------------
#
# Runs the inn and spins once. A cup with a face, crema on top, steam rising,
# on a saucer.

CUP, COFFEE, CREMA, SAUCER, CP_EYE, CP_PUPIL, CP_MOUTH, STEAM = range(8)

CAPPUCCINA_MATERIALS = {
    CUP:      ((0.94, 0.94, 0.96),  30,  [12, 13, 6, 15]),
    COFFEE:   ((0.40, 0.24, 0.12),   0,  [14, 2, 3]),
    CREMA:    ((0.84, 0.64, 0.40),   0,  [4, 9, 5]),
    SAUCER:   ((0.70, 0.70, 0.74),  30,  [12, 13, 6]),
    CP_EYE:   ((0.96, 0.96, 0.96),   0,  [13, 6], 0.3),
    CP_PUPIL: ((0.05, 0.04, 0.03),  60,  [7, 15]),
    CP_MOUTH: ((0.74, 0.16, 0.12),   0,  [11, 10]),
    STEAM:    ((0.90, 0.90, 0.94),   0,  [13, 6], 0.6),
}


def face_cappuccina():
    s = figure(TURN, pivot=(0, 0, 0))

    def cup(p):
        d = cylinder_y(p, (0, -0.24, 0), 0.62, 0.42, 0.18)
        d = smin(d, sphere(p, (0, -0.40, 0), 0.62), 0.1)
        well = cylinder_y(p, (0, 0.22, 0), 0.52, 0.12)
        return np.maximum(d, -well)

    s.add(CUP, cup)
    s.add(lambda q: np.where(np.hypot(q[:, 0] + 0.1, q[:, 2] - 0.06) < 0.24,
                             CREMA, COFFEE),
          lambda p: cylinder_y(p, (0, 0.10, 0), 0.52, 0.03))
    # The handle: a torus, stood on its side.
    s.add(CUP, lambda p: np.hypot(
        np.hypot(p[:, 0] - 0.74, p[:, 1] + 0.22) - 0.22, p[:, 2]) - 0.07)
    s.add(SAUCER, lambda p: cylinder_y(p, (0, -0.86, 0), 0.94, 0.04, 0.03))
    _eyes(s, CP_EYE, CP_PUPIL, 0.22, -0.18, 0.54, 0.15)
    s.add(CP_MOUTH, lambda p: ellipsoid(p, (0, -0.52, 0.58),
                                        (0.14, 0.06, 0.05)))
    for i, x in enumerate((-0.30, 0.0, 0.30)):  # steam, three lazy curls
        pts = [(x, 0.20, 0), (x + 0.08, 0.44, 0.02),
               (x - 0.06, 0.66, 0.04), (x + 0.04, 0.88, 0.02)]
        for a, b in zip(pts, pts[1:]):
            s.add(STEAM, lambda p, a=a, b=b: capsule(p, a, b, 0.05, 0.04))
    return s


SCENES = {
    'face_tung':       (face_tung, TUNG_MATERIALS, SIZE),
    'face_nonna':      (face_nonna, NONNA_MATERIALS, SIZE),
    'face_patapim':    (face_patapim, PATAPIM_MATERIALS, SIZE),
    'face_trala':      (face_trala, TRALA_MATERIALS, SIZE),
    'face_lirili':     (face_lirili, LIRILI_MATERIALS, SIZE),
    'face_bombard':    (face_bombard, BOMBARD_MATERIALS, SIZE),
    'face_silenzio':   (face_silenzio, SILENZIO_MATERIALS, SIZE),
    'face_cappuccina': (face_cappuccina, CAPPUCCINA_MATERIALS, SIZE),
}
