"""Field sprites, pre-rendered: the hero's walk and the sleepwalkers.

The battlers are rendered and the field was not, so for most of the game the
drum walking around was a rectangle with eyes. These are the same figures in
the same lights, cut to 16x16 for the field's small OBJ.

Three things are different at this size.

  - The camera. The field is drawn in three-quarter view, roofs and house
    fronts at once, so the renders look down at PITCH instead of the
    battlers' near-level -0.2. That tilt also shows the top of the drum,
    which is what makes it read as a log and not a box. It moves things,
    too: anything on the front of a head lands lower on screen than its
    height says, so eyes sit higher on these faces than they would face on.
  - One unit is eight dots. A detail thinner than a dot loses the vote in
    the downsample and is simply not there, so brows slope a whole dot
    across their length -- a flat one is a headband -- and shut eyes are
    painted onto the head as a band a dot tall rather than modelled.
  - Frame 0 is also the standing pose. From the front and back a step is one
    foot a dot higher than the other, and the two frames are mirror images,
    so standing still looks like weight on one foot rather than mid-stride.
    In profile frame 0 has the feet together and frame 1 is the stride.

The sleepwalkers' 'side' is drawn facing right and the OBJ engine mirrors it
for left. The hero has four views, so his left is its own render -- and it
has to be, because the bat changes hands: in profile it is slung across his
back from the far hand, since on the near shoulder it crosses his face.

Scenes only. Which palette each kind uses, the pose list and the sheet names
are gen_sprites.py's, in field_poses(); gen_render.py bakes what that lists.
"""
from gen_render import (figure, sphere, ellipsoid, capsule, cylinder_y, box,
                        render_sprite, np)

SIZE = 16
PITCH = -0.45                   # radians down: the field's three-quarter view

# Not a full ninety in profile: at ninety the far eye is gone and the near one
# is a white dot on the silhouette's edge.
YAW = {'down': 0, 'up': 180, 'left': -70, 'right': 70, 'side': 70}


def _stride(direction, frame):
    """(near foot z, far foot z, lift) for a pose -- see the module note."""
    if direction in ('left', 'right', 'side'):
        return (0.22, -0.22, 0.06) if frame else (0.04, -0.04, 0.0)
    s = 1 if frame else -1
    return (0.14 * s, -0.14 * s, 0.16)


def _legs(s, leg, foot, direction, frame, hip, x=0.13, r=0.08,
          ground=-0.80, foot_r=(0.10, 0.07, 0.14), blend=0.0):
    near, far, lift = _stride(direction, frame)
    for sx, z in ((-1, near), (1, far)):
        up = lift if z > 0.05 else 0.0
        s.add(leg, lambda p, sx=sx, z=z, up=up: capsule(
            p, (x * sx, hip, 0.0), (x * sx, ground + 0.06 + up, z), r),
            blend=blend)
        s.add(foot, lambda p, sx=sx, z=z, up=up: ellipsoid(
            p, (x * sx, ground + up, z + 0.05), foot_r))


def _shut_eyes(skin, lash, y, x0, x1, zmin, half=0.075):
    """A material painter for a head: skin, with a dark band across each eye
    on the front. A dot tall, because a thinner lash loses the downsample
    and the eyes open."""
    def mat(q):
        ax = np.abs(q[:, 0])
        shut = ((np.abs(q[:, 1] - y) < half) & (ax > x0) & (ax < x1)
                & (q[:, 2] > zmin))
        return np.where(shut, lash, skin)
    return mat


def _above(fn, y, slope=0.0):
    """The part of a shape above a plane at height y, tilted so it sits
    higher at the front than the back: hair and caps, off the face."""
    return lambda p: np.maximum(fn(p), y - p[:, 1] + slope * p[:, 2])


# ---- Tung (P_TUNG) -------------------------------------------------------
#
# gen_render.py's battler, nearly: the log a little stouter, the eyes and
# the brows placed for the field camera, and the bat on his shoulder rather
# than raised. Ramps are the battler's.

WOOD, END, EYE, PUPIL, BROW, BAT, FOOT, SLIT, GRIP, GRAIN = range(10)

TUNG_MATERIALS = {
    WOOD:  ((0.62, 0.40, 0.20),    0,    [14, 2, 3, 4, 5]),
    END:   ((0.90, 0.72, 0.48),    0,    [3, 4, 5, 15]),
    EYE:   ((0.96, 0.96, 0.96),   40,    [12, 13, 6, 15], 0.55),
    PUPIL: ((0.04, 0.04, 0.07),   60,    [7, 13, 15]),
    BROW:  ((0.80, 0.18, 0.14),    0,    [11, 10]),
    BAT:   ((0.70, 0.48, 0.28),   12,    [14, 2, 8, 9, 5, 15]),
    # Lighter than the battler's: at 16px a foot in the outline colour is
    # just more outline.
    FOOT:  ((0.30, 0.17, 0.08),    0,    [14, 2, 3]),
    SLIT:  ((0.10, 0.06, 0.03),    0,    [1, 14], -0.3),
    GRIP:  ((0.35, 0.20, 0.10),    0,    [14, 2, 3]),
    GRAIN: ((0.30, 0.18, 0.08),    0,    [14, 2]),
}


def _grain(q):
    # A few dark furrows up the log. The back view has nothing else on it.
    ang = np.arctan2(q[:, 0], q[:, 2])
    w = np.sin(ang * 5 + 1.3 + np.sin(q[:, 1] * 7) * 0.5)
    return np.where(w > 0.9, GRAIN, WOOD)


def walk_scene(direction, frame):
    s = figure(YAW[direction])
    R, TOP, BOT = 0.46, 0.52, -0.46
    cy, hh = (TOP + BOT) / 2, (TOP - BOT) / 2

    def log(p):
        d = cylinder_y(p, (0, cy, 0), R, hh, 0.07)
        slit = box(p, (0, -0.24, R), (0.30, 0.07, 0.16))
        return np.maximum(d, -slit)

    s.add(_grain, log)
    s.add(END, lambda p: cylinder_y(p, (0, TOP - 0.02, 0), R - 0.09, 0.035,
                                    0.02))
    s.add(SLIT, lambda p: box(p, (0, -0.24, R - 0.15), (0.29, 0.06, 0.02)))
    _legs(s, WOOD, FOOT, direction, frame, hip=BOT, x=0.19, r=0.10,
          foot_r=(0.14, 0.08, 0.18), blend=0.06)

    for sx in (-1, 1):
        ex = 0.20 * sx
        s.add(EYE, lambda p, ex=ex: sphere(p, (ex, 0.12, R - 0.10), 0.21))
        s.add(PUPIL, lambda p, ex=ex: sphere(p, (ex, 0.14, R + 0.06), 0.10))
        s.add(BROW, lambda p, sx=sx: capsule(
            p, (0.34 * sx, 0.48, R - 0.06), (0.05 * sx, 0.30, R + 0.06),
            0.065))

    # The bat rides the shoulder, up and back, so it is in the silhouette
    # from the front and behind. In profile it is slung across his back from
    # the far hand instead: on the near shoulder it crosses his face, and
    # straight up behind him it is a periscope.
    h = -1 if direction == 'left' else 1
    if direction in ('left', 'right'):
        grip = np.array([0.40 * h, -0.16, -0.20])
        tip = np.array([0.36 * h, 0.58, -0.78])
    else:
        grip = np.array([0.56 * h, -0.10, 0.10])
        tip = np.array([0.70 * h, 0.66, -0.34])
    s.add(WOOD, lambda p: capsule(p, (h * (R - 0.04), 0.0, 0.02), grip, 0.08),
          blend=0.05)
    s.add(WOOD, lambda p: capsule(p, (-h * (R - 0.04), -0.02, 0.0),
                                  (-0.62 * h, -0.26, 0.08), 0.08), blend=0.05)
    s.add(GRIP, lambda p: capsule(p, grip - (tip - grip) * 0.1, grip, 0.07))
    s.add(BAT, lambda p: capsule(p, grip, tip, 0.08, 0.16))
    return s


# ---- the villager (P_ENEMY) ----------------------------------------------
#
# Nightshirt, nightcap, and both arms out ahead: out and apart, because
# straight ahead they foreshorten from the front into two rings on the chest
# and the villager is wearing spectacles.

V_SKIN, V_SHIRT, V_HEM, V_CAP, V_BOBBLE, V_LASH = range(6)

VILLAGER_MATERIALS = {
    V_SKIN:   ((0.94, 0.74, 0.94),  0,  [4, 5, 6]),
    V_SHIRT:  ((0.80, 0.76, 0.62),  0,  [10, 9, 8]),
    V_HEM:    ((0.30, 0.38, 0.78),  0,  [13, 14]),
    V_CAP:    ((0.46, 0.32, 0.70),  0,  [2, 3, 4]),
    V_BOBBLE: ((0.98, 0.86, 0.38), 20,  [11, 6], 0.2),
    V_LASH:   ((0.28, 0.18, 0.44),  0,  [2]),
}


def villager_scene(direction, frame):
    s = figure(YAW[direction])
    head = (0, 0.28, 0.04)

    s.add(lambda q: np.where(q[:, 1] < -0.40, V_HEM, V_SHIRT),
          lambda p: capsule(p, (0, -0.06, 0), (0, -0.42, 0), 0.24, 0.38))
    s.add(_shut_eyes(V_SKIN, V_LASH, 0.37, 0.07, 0.24, 0.16),
          lambda p: sphere(p, head, 0.34))
    s.add(V_CAP, _above(lambda p: sphere(p, head, 0.37), 0.42, 0.5))
    s.add(V_CAP, lambda p: capsule(p, (0.10, 0.60, -0.08), (0.44, 0.62, -0.20),
                                   0.16, 0.06))
    s.add(V_BOBBLE, lambda p: sphere(p, (0.52, 0.52, -0.20), 0.11))

    for sx in (-1, 1):
        a = np.array([0.20 * sx, -0.06, 0.04])
        b = np.array([0.50 * sx, -0.06, 0.34])
        s.add(V_SHIRT, lambda p, a=a, b=b: capsule(p, a, b, 0.10, 0.08),
              blend=0.04)
        s.add(V_SKIN, lambda p, b=b: sphere(p, b * (1.08, 1, 1.12), 0.09))
    _legs(s, V_SKIN, V_SKIN, direction, frame, hip=-0.42, r=0.07)
    return s


# ---- the drifter (P_PATAPIM) ---------------------------------------------
#
# Still in the day's clothes, hunched, arms hanging. The hunch is the head
# forward of the shoulders and barely above them -- not the figure tipped
# forward, which from this camera shows the top of his head and no face.

D_SKIN, D_HAIR, D_SHIRT, D_TROUSER, D_BELT, D_SHOE, D_LASH = range(7)

DRIFTER_MATERIALS = {
    D_SKIN:    ((0.74, 0.58, 0.38),  0,  [3, 10, 14]),
    D_HAIR:    ((0.18, 0.13, 0.08),  0,  [13, 2, 3]),
    D_SHIRT:   ((0.52, 0.52, 0.58),  0,  [11, 12]),
    D_TROUSER: ((0.40, 0.30, 0.19),  0,  [13, 2, 3, 4]),
    D_BELT:    ((0.12, 0.10, 0.08),  0,  [1, 13]),
    D_SHOE:    ((0.16, 0.12, 0.09),  0,  [13, 2]),
    D_LASH:    ((0.20, 0.15, 0.10),  0,  [13]),
}


def drifter_scene(direction, frame):
    s = figure(YAW[direction])
    head = (0, 0.30, 0.16)

    def torso(q):
        y = q[:, 1]
        return np.where(y > -0.18, D_SHIRT,
                        np.where(y > -0.26, D_BELT, D_TROUSER))

    s.add(torso, lambda p: capsule(p, (0, -0.40, 0), (0, 0.02, 0.02),
                                   0.28, 0.32))
    s.add(_shut_eyes(D_SKIN, D_LASH, 0.36, 0.04, 0.22, 0.30),
          lambda p: sphere(p, head, 0.32))
    s.add(D_HAIR, _above(lambda p: sphere(p, (0, 0.32, 0.12), 0.35), 0.38,
                         0.9))
    for sx in (-1, 1):
        a = np.array([0.32 * sx, 0.0, 0.04])
        b = np.array([0.38 * sx, -0.36, 0.12])
        s.add(D_SHIRT, lambda p, a=a, b=b: capsule(p, a, b, 0.10, 0.08),
              blend=0.04)
        s.add(D_SKIN, lambda p, b=b: sphere(p, b + (0, -0.08, 0), 0.08))
    _legs(s, D_TROUSER, D_SHOE, direction, frame, hip=-0.40, r=0.10,
          foot_r=(0.11, 0.07, 0.16))
    return s


# ---- the cat (P_TUNG) ----------------------------------------------------
#
# From the opening: asleep, standing up, with five legs. It only ever drifts
# sideways, so it is modelled facing +x in a figure that does not turn, and
# the one view is its right side.

C_FUR, C_BELLY, C_LASH, C_NOSE = range(4)

CAT_MATERIALS = {
    C_FUR:   ((0.62, 0.40, 0.20),  0,  [14, 2, 3, 4]),
    C_BELLY: ((0.88, 0.70, 0.46),  0,  [3, 4, 5]),
    C_LASH:  ((0.06, 0.04, 0.02),  0,  [1, 14]),
    C_NOSE:  ((0.74, 0.20, 0.16),  0,  [11, 10]),
}


def cat_scene(_direction, frame):
    s = figure(0)
    s.add(lambda q: np.where(q[:, 1] < -0.30, C_BELLY, C_FUR),
          lambda p: ellipsoid(p, (-0.08, -0.22, 0), (0.50, 0.24, 0.24)))
    head = np.array([0.46, 0.02, 0.06])

    def face(q):
        d = q - head
        eye = ((np.abs(d[:, 1] - 0.04) < 0.08) & (d[:, 0] > 0.02)
               & (np.abs(np.abs(d[:, 2] - 0.02) - 0.10) < 0.08)
               & (d[:, 2] > 0.0))
        return np.where(eye, C_LASH, C_FUR)

    s.add(face, lambda p: sphere(p, head, 0.26))
    s.add(C_NOSE, lambda p: sphere(p, head + (0.24, -0.06, 0.06), 0.05))
    for dz in (-0.14, 0.14):                    # ears
        s.add(C_FUR, lambda p, dz=dz: capsule(
            p, head + (-0.02, 0.14, dz), head + (0.02, 0.36, dz * 1.2),
            0.09, 0.02))
    s.add(C_FUR, lambda p: capsule(p, (-0.54, -0.16, 0), (-0.70, 0.30, -0.04),
                                   0.07, 0.06), blend=0.04)
    # Five legs, and nobody mentions it. Near and far alternate along the
    # body, and a step lifts every other one.
    for i, x in enumerate((-0.46, -0.24, -0.02, 0.18, 0.36)):
        z = 0.12 if i % 2 == 0 else -0.10
        up = 0.08 if (i + frame) % 2 else 0.0
        s.add(C_FUR, lambda p, x=x, z=z, up=up: capsule(
            p, (x, -0.30, z), (x + 0.02, -0.74 + up, z), 0.07), blend=0.03)
    return s


# Keyed by the first part of gen_sprites.field_poses()'s render keys.
FIELD = {
    'walk':     (walk_scene, TUNG_MATERIALS),
    'villager': (villager_scene, VILLAGER_MATERIALS),
    'drifter':  (drifter_scene, DRIFTER_MATERIALS),
    'cat':      (cat_scene, CAT_MATERIALS),
}


def render_pose(kind, direction, frame, palette):
    scene, materials = FIELD[kind]
    return render_sprite(scene(direction, frame), materials, palette,
                         size=SIZE, pitch=PITCH)
