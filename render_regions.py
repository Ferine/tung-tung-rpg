"""The seven regions' looks, and everything standing in them.

render_land.py is the engine; this says what a character *is* in each place:
the moonlight, the materials, and a Content for every key gen_world.py asks
for. A region with no LOOKS entry is not rendered and keeps its painted
tileset.

Coordinates are a metatile's own: x east, z south, both 0-2 across, y up;
eight dots to the unit. Something standing in a cell has to fit its window
unless it is TALL in gen_world.py, in which case it may rise into the cell
north of it -- by up to 2.6 units, or it would reach the one beyond.

Everything that meets a border is built so both sides agree about it: a
surface blends to the region's ground by the border it does not share, a mass
runs straight through the border it does, and texture near a border comes
from the lattice ring every cell seeds the same way (render_land.scatter).
"""
import math

import numpy as np

import gen_world
from gen_render import sphere, ellipsoid, capsule, cylinder_y, box
from render_land import (CU, NEG, Content, Context, ihash, vnoise, scatter,
                         voronoi, smooth, region2d, render, FRAMES)

# ---- materials --------------------------------------------------------------

NAMES = """grass grass_l grass_d dirt dirt_d pebble cobble cobble2 cobble3
mortar leaf leaf2 leaf_d bark flower_y flower_w flower_r rock rock_l rock_d
roof roof_d wall beam door window post glass wellstone wellwater wood water
water_s water_d foam bank sand sand_l sand_d shell snow cliff cliff_l moss
litter salt salt_l crack sparkle iron iron_l iron_d rivet rust stripe pit pipe
pipe_l ember stem cap cap_spot pine pine_d deadwood reed cactus spine bone cave
void star slab slab_l rune rift rift_halo plank rail fern glint plate plate_l
slab_d""".split()
M = type('M', (), {n.upper(): i for i, n in enumerate(NAMES)})


def table(mats):
    """A region's material properties as arrays indexed by id. A material a
    region uses but does not define renders magenta, so it cannot hide."""
    n = len(NAMES)
    t = dict(alb=np.tile([1.0, 0.0, 1.0], (n, 1)), shine=np.zeros(n),
             spec=np.zeros(n), glow=np.zeros((n, 3)), flicker=np.zeros(n),
             dif=np.ones(n))
    for name, p in mats.items():
        i = NAMES.index(name)
        t['alb'][i] = p['alb']
        t['shine'][i] = p.get('shine', 0)
        t['spec'][i] = p.get('spec', 0.0)
        t['glow'][i] = p.get('glow', (0, 0, 0))
        t['flicker'][i] = p.get('flicker', 0.0)
        t['dif'][i] = p.get('dif', 1.0)
    return t


SHARED = 7          # the lattice ring every cell agrees on


# ---- grounds ----------------------------------------------------------------

def grass(x, z, var, tufts=0.0, tuft_mat=None):
    """Blades on a lattice, lit: grass is a texture of highlights and the
    shadows between them, not a speckle."""
    seed = 100 + var

    def blade(dx, dz, r3, r4):
        rad = 0.07 + 0.05 * r4
        return (0.07 + 0.08 * r3) * np.clip(1 - np.hypot(dx, dz) / rad, 0, 1)
    h, tag = scatter(x, z, 11, seed, SHARED, blade)
    h = np.maximum(h, 0)
    mat = np.where(h > 0.075, M.GRASS_L,
                   np.where(tag < 0.3, M.GRASS_D, M.GRASS))
    if tufts:
        def tuft(dx, dz, r3, r4):
            return np.where(r3 < tufts, (0.26 + 0.1 * r4) * np.clip(
                1 - np.hypot(dx * 1.3, dz) / 0.22, 0, 1) ** 0.7, 0)
        th, _ = scatter(x, z, 4, seed + 50, SHARED + 50, tuft)
        tm = tuft_mat if tuft_mat is not None else M.GRASS_L
        mat = np.where(th > h, np.where(th > 0.16, tm, M.GRASS), mat)
        h = np.maximum(h, th)
    return h, mat


def flowers(x, z, var):
    h, mat = grass(x, z, var)

    def head(dx, dz, r3, r4):
        return np.where(r4 < 0.75, 0.24 * np.clip(
            1 - np.hypot(dx, dz) / 0.17, 0, 1) ** 0.5, -1)
    fh, tag = scatter(x, z, 4, 300 + var, SHARED + 300, head)
    col = np.where(tag < 0.4, M.FLOWER_Y,
                   np.where(tag < 0.75, M.FLOWER_W, M.FLOWER_R))
    top = fh > 0.03
    return np.where(top, np.maximum(h, fh), h), np.where(top, col, mat)


def forest_floor(x, z, var, tufts=0.0):
    """Moss and leaf litter under the canopy."""
    h, mat = grass(x, z, var, tufts, M.FERN)
    mat = np.where(mat == M.GRASS_D, M.MOSS, mat)

    def leaf(dx, dz, r3, r4):
        return np.where(r4 < 0.5, 0.05 * np.clip(
            1 - np.hypot(dx * 1.6, dz) / 0.10, 0, 1), -1)
    lh, _ = scatter(x, z, 8, 400 + var, SHARED + 400, leaf)
    top = lh > 0.01
    return np.where(top, np.maximum(h, lh), h), np.where(top, M.LITTER, mat)


def sand(x, z, var):
    """Grains, lit, with the odd pebble and shell."""
    def grain(dx, dz, r3, r4):
        return 0.03 * r3 * np.clip(1 - np.hypot(dx, dz) / 0.08, 0, 1)
    h, tag = scatter(x, z, 12, 500 + var, SHARED + 500, grain)
    h = np.maximum(h, 0)
    mat = np.where(tag < 0.25, M.SAND_D,
                   np.where(h > 0.018, M.SAND_L, M.SAND))

    def bit(dx, dz, r3, r4):
        return np.where(r4 < 0.35, 0.06 * np.clip(
            1 - np.hypot(dx, dz) / 0.08, 0, 1) ** 0.5, -1)
    bh, btag = scatter(x, z, 5, 520 + var, SHARED + 520, bit)
    top = bh > 0.01
    return (np.where(top, np.maximum(h, bh), h),
            np.where(top, np.where(btag < 0.5, M.SHELL, M.PEBBLE), mat))


def salt(x, z, var):
    """Crust: raised plates with dark seams between them, and a glint here
    and there where a crystal catches the moon."""
    # Coarse texture cannot come from the shared ring the way grass does: on
    # a lattice this coarse the ring is most of the points, every cell is
    # the same cell, and the flat is a quilt. So the cracks are seeded per
    # variant everywhere and die out before the border, where there is then
    # nothing for two cells to disagree about.
    f1, f2, tag = voronoi(x, z, 4, 600 + var, 600 + var)
    e = f2 - f1
    inner = np.minimum(np.minimum(x, CU - x), np.minimum(z, CU - z))
    crack = (e < 0.028) & (tag < 0.6) & (inner > 0.14)
    h = np.where(crack, -0.012, 0.0)
    mat = np.where(crack, M.CRACK, np.where(tag < 0.35, M.SALT_L, M.SALT))

    def glint(dx, dz, r3, r4):
        return np.where(r3 < 0.3, np.clip(1 - np.hypot(dx, dz) / 0.05, 0, 1),
                        0)
    gl, _ = scatter(x, z, 7, 640 + var, SHARED + 640, glint)
    mat = np.where((gl > 0.3) & ~crack, M.SPARKLE, mat)
    return h, mat


def iron_floor(x, z, var):
    """Deck plate: a seam round every metatile and across its middle,
    rivets at the corners, rust where it has been walked on."""
    ex = np.minimum(np.abs(x - 0.0), np.abs(x - CU))
    ez = np.minimum(np.abs(z - 0.0), np.abs(z - CU))
    em = np.minimum(np.minimum(ex, ez), np.abs(z - 1.0))
    seam = em < 0.05
    h = np.where(seam, -0.03, 0.0)
    rivet = (np.hypot(np.mod(x, 1.0) - 0.15, np.mod(z, 1.0) - 0.15) < 0.05) \
        | (np.hypot(np.mod(x, 1.0) - 0.85, np.mod(z, 1.0) - 0.15) < 0.05)
    h = np.where(rivet, 0.03, h)

    def scuff(dx, dz, r3, r4):
        return np.where(r3 < 0.25, np.clip(1 - np.hypot(dx * 0.7, dz) / 0.2,
                                           0, 1), 0)
    sc, _ = scatter(x, z, 4, 700 + var, SHARED + 700, scuff)
    mat = np.where(seam, M.IRON_D, np.where(rivet, M.RIVET,
                   np.where(sc > 0.4, M.RUST, np.where(sc > 0.1, M.PLATE_L,
                                                       M.PLATE))))
    return h, mat


def void_floor(x, z, var):
    """The floor of the dark, a long way down: stars."""
    def star(dx, dz, r3, r4):
        return np.where(r3 < 0.45, np.clip(1 - np.hypot(dx, dz) / (0.04 + 0.05
                                                                   * r4), 0,
                                           1), 0)
    st, _ = scatter(x, z, 6, 800, 800, star)
    h = np.full(x.shape, -3.0)
    return h, np.where(st > 0.2, M.STAR, M.VOID)


def base_ground(look, x, z, var, ch):
    style = look['ground']
    if style == 'grass':
        if ch == ',':
            return grass(x, z, var, tufts=0.6)
        if ch == 'f':
            return flowers(x, z, var)
        return grass(x, z, var)
    if style == 'forest':
        return forest_floor(x, z, var, tufts=0.6 if ch == ',' else 0.12)
    if style == 'sand':
        return sand(x, z, var)
    if style == 'salt':
        return salt(x, z, var)
    if style == 'iron':
        return iron_floor(x, z, var)
    return void_floor(x, z, var)


# ---- surfaces ---------------------------------------------------------------

def path(x, z, open_, look):
    """Packed earth with a ragged verge, pebbles, and darker wear."""
    d2 = region2d(x, z, open_, 0.40, 0.55)
    edge = (vnoise(x, z, 8, 11) - 0.5) * 0.24
    w = smooth(0.05, -0.05, d2 + edge)

    def pebble(dx, dz, r3, r4):
        return np.where(r3 < 0.3, 0.05 * np.clip(
            1 - np.hypot(dx, dz) / (0.06 + 0.04 * r4), 0, 1) ** 0.5, 0)
    ph, _ = scatter(x, z, 9, 21, 21, pebble)

    def wear(dx, dz, r3, r4):
        return np.where(r3 < 0.5, np.clip(1 - np.hypot(dx, dz) / 0.12, 0, 1),
                        0)
    wr, _ = scatter(x, z, 10, 22, 22, wear)
    hp = -0.03 + ph - 0.015 * wr
    mp = np.where(ph > 0.02, M.PEBBLE, np.where(wr > 0.3, M.DIRT_D, M.DIRT))
    rim = (d2 + edge > -0.12) & (w > 0.5)
    mp = np.where(rim & (ph <= 0.02), M.DIRT_D, mp)
    return w, hp, mp


def plaza(x, z, open_, look):
    """Cobbles: a Voronoi lattice, so no two rows line up."""
    d2 = region2d(x, z, open_, 0.08, 0.08)
    w = smooth(0.03, -0.03, d2)
    f1, f2, tag = voronoi(x, z, 4, 31, 32)
    stone = smooth(0.02, 0.09, f2 - f1)
    hp = 0.06 * stone - 0.02
    mp = np.where(stone < 0.35, M.MORTAR,
                  np.where(tag < 0.33, M.COBBLE2,
                           np.where(tag < 0.66, M.COBBLE, M.COBBLE3)))
    return w, hp, mp


DEPTH = {'d': -0.75, 's': -0.30, 'b': -0.16}
KIND_DEPTH = {'deep': 'd', 'shallow': 's', 'beach': 'b', 'bridge': 'd'}


def water(x, z, kind, codes, look, land_h, land_m, t):
    """A river or the sea: a bank that shelves where the neighbour is land,
    depth that meets its neighbour's halfway, a tide on the shore and foam
    where the water runs out. The moon's glints are points, each twinkling
    on its own phase: a glint worked out from ripples would repeat every
    metatile, and a river of identical diamonds is a quilt."""
    own = DEPTH[KIND_DEPTH[kind]]
    open_ = [c in '0p' for c in codes]
    inset = 0.9 if kind == 'beach' else 0.42
    d2 = region2d(x, z, open_, inset, 0.7)
    edge = (vnoise(x, z, 6, 13) - 0.5) * 0.3
    w = smooth(0.3, -0.55, d2 + edge)
    depth = np.full(x.shape, own)
    dist = (z, CU - x, CU - z, x)                   # to N, E, S, W
    for c, dd in zip(codes, dist):
        if c in DEPTH and DEPTH[c] != own:
            depth += ((DEPTH[c] + own) / 2 - own) * (1 - smooth(0.0, 0.9, dd))
    bed_n = (vnoise(x, z, 5, 14) - 0.5) * 0.08
    h = land_h * (1 - w) + (depth + bed_n) * w * w
    wl = look['water'] + look.get('tide', 0.0) * math.sin(2 * math.pi * t)
    dry = h > wl
    mat = np.where(w < 0.1, land_m, M.BANK)
    under = wl - h

    def glint(dx, dz, r3, r4):
        lvl = np.maximum(np.cos(2 * math.pi * (t + r3)), 0) ** 3
        return lvl * np.clip(1 - np.hypot(dx * 0.6, dz) / (0.07 + 0.05 * r4),
                             0, 1)
    gl, _ = scatter(x, z, 7, 1000, 1000, glint)
    wet = np.where(under < 0.035, M.FOAM,
                   np.where((gl > 0.3) & (under > 0.08), M.GLINT,
                            np.where(under < 0.2, M.WATER_S,
                                     np.where(under < 0.5, M.WATER,
                                              M.WATER_D))))
    return h, np.where(dry, mat, wet), np.full(x.shape, wl)


# ---- masses -----------------------------------------------------------------

def _open(mtok):
    return [c == '0' for c in mtok]


def canopy(look, mtok):
    """Treetops joined into one mass wherever trees stand together: a dome
    at every open edge, lumps on top, a trunk showing under the south one."""
    open_ = _open(mtok)
    lump = look.get('lump', 0.34)

    def lumps(q):
        def blob(dx, dz, r3, r4):
            return (0.16 + 0.14 * r3) * np.clip(
                1 - (dx * dx + dz * dz) / (lump + 0.12 * r4) ** 2, 0, 1) ** 0.7
        return scatter(q[:, 0], q[:, 2], 3, 71, 71, blob)

    def sdf(q):
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.18, 0.75)
        shape = np.sqrt(np.clip(-d2 / 0.55, 0, 1))
        bump, _ = lumps(q)
        top = 0.95 + 0.85 * shape + bump * shape
        bot = 0.95 - 0.30 * shape
        return np.maximum(np.maximum((q[:, 1] - top) * 0.5,
                                     (bot - q[:, 1]) * 0.5), d2 - bump * 0.3)

    def mat(q):
        b, tag = lumps(q)
        # Dark where it is underneath, and down between the crowns.
        return np.where((q[:, 1] < 0.98) | (b < 0.05), M.LEAF_D,
                        np.where(tag < 0.5, M.LEAF, M.LEAF2))

    def trunk(q):
        return capsule(q, (1.0, -0.1, 1.62), (1.0, 1.2, 1.5), 0.15, 0.10)
    return [(M.BARK, trunk), (mat, sdf)], 2.3


def mountain(look, mtok):
    """A ridge of rock, peaks on a lattice, snow where it is highest."""
    open_ = _open(mtok)

    def peaks(q):
        def cone(dx, dz, r3, r4):
            return (0.45 + 0.35 * r3) * np.clip(
                1 - np.hypot(dx, dz) / (0.55 + 0.2 * r4), 0, 1)
        return scatter(q[:, 0], q[:, 2], 2, 91, 91, cone)

    def sdf(q):
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.12, 0.8)
        shape = np.clip(-d2 / 0.8, 0, 1) ** 0.8
        pk, _ = peaks(q)
        rough = (vnoise(q[:, 0] + q[:, 1], q[:, 2] - q[:, 1] * 0.5, 8, 92)
                 - 0.5) * 0.14
        top = np.minimum(0.25 + 1.45 * shape + pk * shape + rough, 2.5)
        return np.maximum((q[:, 1] - top) * 0.35, d2 + rough)

    def mat(q):
        n = vnoise(q[:, 0] * 2, q[:, 2] * 2, 6, 93)
        return np.where(q[:, 1] > 1.95 + 0.25 * n, M.SNOW,
                        np.where(q[:, 1] > 1.2 + 0.3 * n, M.ROCK_L,
                                 np.where(n < 0.35, M.ROCK_D, M.ROCK)))
    return [(mat, sdf)], 2.6


def cliff(look, mtok):
    """A plateau: a flat top with scrub on it and a stratified drop."""
    open_ = _open(mtok)

    def sdf(q):
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.08, 0.3)
        rough = (vnoise(q[:, 0] + q[:, 1] * 0.6, q[:, 2] + q[:, 1] * 0.6, 8,
                        95) - 0.5) * 0.12
        top = 1.35 + 0.05 * vnoise(q[:, 0], q[:, 2], 4, 96)
        return np.maximum((q[:, 1] - top) * 0.7, d2 + rough)

    def mat(q):
        band = np.mod(q[:, 1] * 3.3 + 0.3 * vnoise(q[:, 0], q[:, 2], 4, 97),
                      1.0)
        face = q[:, 1] < 1.30
        a, b = look.get('cliff_top', (M.GRASS, M.GRASS_D))
        topm = np.where(vnoise(q[:, 0], q[:, 2], 6, 98) < 0.45, a, b)
        return np.where(face, np.where(band < 0.35, M.CLIFF_L, M.CLIFF),
                        topm)
    return [(mat, sdf)], 1.5


def dune(look, mtok):
    """Wind-laid sand."""
    open_ = _open(mtok)

    def sdf(q):
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.15, 0.9)
        # Smoothstep, not a power: a profile whose slope runs to infinity
        # at the foot is a face the march bands on.
        shape = smooth(0.0, 0.9, -d2)
        top = 0.05 + 0.85 * shape
        return np.maximum((q[:, 1] - top) * 0.35, d2)

    def mat(q):
        # Grain, not ripples: three bold ripples to a metatile read as
        # striped cloth.
        return sand(q[:, 0], q[:, 2], 0)[1]
    return [(mat, sdf)], 1.0


def iron_wall(look, mtok):
    """Plate on ribs, a stripe at waist height, rivets along the top."""
    open_ = _open(mtok)
    TOPY = 1.5

    def sdf(q):
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.04, 0.04)
        return np.maximum(q[:, 1] - TOPY, d2)

    def mat(q):
        x, y, z = q[:, 0], q[:, 1], q[:, 2]
        top = y > TOPY - 0.02
        tseam = (np.minimum(np.mod(x, 1.0), 1 - np.mod(x, 1.0)) < 0.04) \
            | (np.minimum(np.mod(z, 1.0), 1 - np.mod(z, 1.0)) < 0.04)
        rib = np.minimum(np.mod(x + 0.25, 0.5), 0.5 - np.mod(x + 0.25, 0.5)) \
            < 0.05
        band = np.abs(y - 0.75) < 0.12
        stripe = band & (np.mod(np.floor((x + y) / 0.18), 2) == 0)
        face = np.where(stripe, M.STRIPE, np.where(band, M.IRON_D,
                        np.where(rib, M.IRON_L, np.where(y < 0.12, M.RUST,
                                                         M.IRON))))
        return np.where(top, np.where(tseam, M.PIT, M.IRON_D), face)
    return [(mat, sdf)], 1.6


def pipes(look, mtok):
    """Mains along every side that joins another pipe; a tank where one
    stands alone."""
    links = [c == '1' for c in mtok]
    Y, R = 0.42, 0.26
    parts = []
    ends = ((1.0, -0.1), (2.1, 1.0), (1.0, 2.1), (-0.1, 1.0))
    for on, (ex, ez) in zip(links, ends):
        if on:
            parts.append((M.PIPE, lambda q, ex=ex, ez=ez: capsule(
                q, (1.0, Y, 1.0), (ex, Y, ez), R)))
    if not any(links):
        parts.append((M.PIPE, lambda q: cylinder_y(q, (1.0, 0.55, 1.2), 0.55,
                                                   0.55, 0.08)))
        parts.append((M.PIPE_L, lambda q: cylinder_y(q, (1.0, 1.12, 1.2),
                                                     0.35, 0.04, 0.02)))
        parts.append((M.RUST, lambda q: box(q, (1.0, 0.55, 1.78),
                                            (0.2, 0.1, 0.04))))
    else:
        parts.append((M.PIPE_L, lambda q: cylinder_y(q, (1.0, Y, 1.0),
                                                     R + 0.07, 0.16, 0.03)))
    for on, (ex, ez) in zip(links, ends):
        if on:
            fx, fz = 1.0 + (ex - 1.0) * 0.45, 1.0 + (ez - 1.0) * 0.45
            parts.append((M.RUST, lambda q, fx=fx, fz=fz: sphere(
                q, (fx, Y, fz), R + 0.05)))
    return parts, 1.2


def deck(look, mtok):
    """A plank bridge: it runs on across every side that joins road or
    bridge, rails along the two that do not."""
    open_ = _open(mtok)

    def slab(q):
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.36, 0.04)
        return np.maximum(d2, np.abs(q[:, 1] - 0.08) - 0.07)

    def planks(q):
        gap = np.mod(q[:, 0], 0.25) < 0.035
        return np.where(gap, M.RAIL, M.PLANK)
    parts = [(planks, slab)]
    for side, zr in ((0, 0.42), (2, 1.58)):
        if open_[side]:
            parts.append((M.RAIL, lambda q, zr=zr: capsule(
                q, (-0.1, 0.46, zr), (2.1, 0.46, zr), 0.045)))
            for px in (0.25, 1.25):
                parts.append((M.RAIL, lambda q, zr=zr, px=px: capsule(
                    q, (px, 0.1, zr), (px, 0.48, zr), 0.05)))
    return parts, 0.6


def platform(look, mtok):
    """An island of stone hung over the dark: a slab a unit thick, runes
    cut in its top, its edge rounded where the dark comes in."""
    open_ = _open(mtok)

    def sdf(q):
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.15, 0.7)
        rough = (vnoise(q[:, 0] + q[:, 1], q[:, 2] - q[:, 1], 6, 150) - 0.5) \
            * 0.12
        under = -1.0 - 0.5 * np.clip(-d2 / 0.8, 0, 1)   # deeper inland
        return np.maximum.reduce([q[:, 1], under - q[:, 1],
                                  d2 + rough * (q[:, 1] < -0.05)])

    def mat(q):
        f1, f2, tag = voronoi(q[:, 0], q[:, 2], 3, 151, 152)
        seam = (f2 - f1) < 0.06
        top = q[:, 1] > -0.02
        d2 = region2d(q[:, 0], q[:, 2], open_, 0.15, 0.7)
        rim = top & (d2 > -0.14)
        rune = top & (tag < 0.06) & (f1 < 0.12)
        return np.where(rune, M.RUNE,
                        np.where(rim, M.SLAB_L,
                                 np.where(top, np.where(seam, M.SLAB_D,
                                                        np.where(tag < 0.5,
                                                                 M.SLAB,
                                                                 M.SLAB_L)),
                                          M.SLAB_D)))
    return [(mat, sdf)], 0.1


# ---- things standing --------------------------------------------------------

def bush(var):
    c = (1.0, 0.28, 1.28)

    def sdf(q):
        def blob(dx, dz, r3, r4):
            return 0.08 * r3 * np.clip(1 - (dx * dx + dz * dz) / 0.05, 0, 1)
        b, _ = scatter(q[:, 0], q[:, 2], 7, 80 + var, 80 + var, blob)
        return ellipsoid(q, c, (0.66, 0.52, 0.56)) - b

    def mat(q):
        k = ihash(np.floor(q[:, 0] * 6), np.floor(q[:, 2] * 6), 9)
        return np.where(q[:, 1] < 0.18, M.LEAF_D,
                        np.where(k < 0.5, M.LEAF, M.LEAF2))
    return [(mat, sdf)], 1.0


def rock(var):
    c = (0.95 + 0.1 * var, 0.16, 1.28)

    def sdf(q):
        n = vnoise(q[:, 0] + q[:, 1], q[:, 2] - q[:, 1], 6, 90 + var)
        return ellipsoid(q, c, (0.72, 0.50, 0.56)) + (n - 0.5) * 0.14

    def mat(q):
        return np.where(q[:, 1] > 0.42, M.ROCK_L,
                        np.where(q[:, 1] < 0.12, M.ROCK_D, M.ROCK))
    return [(mat, sdf)], 0.9


def lantern():
    px, pz = 1.0, 1.45
    parts = [
        (M.POST, lambda q: capsule(q, (px, 0.0, pz), (px, 1.34, pz), 0.08)),
        (M.POST, lambda q: box(q, (px, 0.04, pz), (0.16, 0.06, 0.16))),
        (M.POST, lambda q: box(q, (px, 1.92, pz), (0.36, 0.05, 0.36))),
        (M.POST, lambda q: box(q, (px, 1.60, pz), (0.30, 0.28, 0.30))),
        (M.GLASS, lambda q: box(q, (px, 1.60, pz), (0.32, 0.22, 0.32))),
    ]
    # A pool of light on the square, round the foot of the post and kept
    # inside the cell: the cell next door is not lit by it.
    return parts, 2.0, [(px, 1.55, 1.0, (1.5, 0.95, 0.42), 0.92, 0.3)]


def roof_x(q, cx, cz, hx, hz, y0, y1, th):
    """A gable whose ridge runs along z at x = cx: eaves at y0, hx either
    side, the ridge at y1."""
    s = (y1 - y0) / hx
    k = np.sqrt(1 + s * s)
    surf = y1 - s * np.abs(q[:, 0] - cx)
    return np.maximum.reduce([(q[:, 1] - surf) / k, (surf - th - q[:, 1]) / k,
                              np.abs(q[:, 0] - cx) - hx,
                              np.abs(q[:, 2] - cz) - hz])


def well(style):
    """The save point: a well with a roof over it in the villages, a spring
    in the forest, a tank in the fortress, a basin hung in the dark."""
    c = (1.0, 0.0, 1.3)
    low = style in ('spring', 'basin')
    ry = 0.10 if low else 0.24
    y0 = -0.35 if style == 'basin' else 0.0

    def ring(q):
        if style == 'tank':
            return np.maximum(cylinder_y(q, (c[0], 0.40, c[2]), 0.62, 0.40,
                                         0.06),
                              -cylinder_y(q, (c[0], 0.6, c[2]), 0.48, 0.3))
        outer = cylinder_y(q, (c[0], y0 + ry, c[2]), 0.66, ry, 0.05)
        inner = cylinder_y(q, (c[0], y0 + ry + 0.1, c[2]), 0.46, ry + 0.2)
        return np.maximum(outer, -inner)

    def ringmat(q):
        if style == 'tank':
            band = np.abs(q[:, 1] - 0.4) < 0.06
            return np.where(band, M.RUST, M.PIPE_L)
        a = np.arctan2(q[:, 0] - c[0], q[:, 2] - c[2])
        k = np.floor(a / (2 * np.pi) * 11 + np.floor(q[:, 1] / 0.16) * 0.5)
        stone = np.where(ihash(np.mod(k, 11), 3, 5) < 0.5, M.WELLSTONE,
                         M.ROCK)
        if style == 'spring':
            stone = np.where(q[:, 1] > 0.14, M.MOSS, stone)
        return stone
    wy = {'tank': 0.62, 'spring': 0.06, 'basin': y0 + 0.08}.get(style, 0.18)
    parts = [(ringmat, ring),
             (M.WELLWATER, lambda q: cylinder_y(q, (c[0], wy, c[2]), 0.47,
                                                0.02))]
    if style == 'well':
        parts += [
            (M.WOOD, lambda q: capsule(q, (0.40, 0.2, 1.3), (0.40, 1.22, 1.3),
                                       0.07)),
            (M.WOOD, lambda q: capsule(q, (1.60, 0.2, 1.3), (1.60, 1.22, 1.3),
                                       0.07)),
            (M.WOOD, lambda q: capsule(q, (0.40, 1.0, 1.3), (1.60, 1.0, 1.3),
                                       0.045)),
            (M.ROOF, lambda q: roof_x(q, 1.0, 1.3, 0.78, 0.34, 1.16, 1.62,
                                      0.08)),
        ]
    if style == 'tank':
        parts.append((M.PIPE, lambda q: capsule(q, (1.55, 0.5, 1.3),
                                                (1.9, 0.5, 1.3), 0.08)))
    return parts, 1.7


HOUSE_AT = {'1': (0, 0), '2': (2, 0), '3': (0, 2), '4': (2, 2)}


def house(quadrant):
    """Two by two metatiles, gable end on to the camera: two slopes the
    moon lights differently, a front wall with the door and two lit windows.
    Every quadrant builds the whole house where it stands relative to that
    quadrant, so the four agree about it."""
    ox, oz = HOUSE_AT[quadrant]
    off = np.array([ox, 0.0, oz])
    X0, X1, Z0, Z1, EAVE, RIDGE = 0.55, 3.45, 1.75, 3.55, 1.05, 2.05

    def walls(q):
        b = q + off
        body = box(b, (2.0, EAVE / 2, (Z0 + Z1) / 2),
                   ((X1 - X0) / 2, EAVE / 2, (Z1 - Z0) / 2))
        s = (RIDGE - EAVE) / ((X1 - X0) / 2)
        gable = np.maximum.reduce([
            (b[:, 1] - (RIDGE - s * np.abs(b[:, 0] - 2.0)))
            / np.sqrt(1 + s * s),
            EAVE - 0.01 - b[:, 1], np.abs(b[:, 2] - (Z0 + Z1) / 2)
            - (Z1 - Z0) / 2, np.abs(b[:, 0] - 2.0) - (X1 - X0) / 2])
        door = box(b, (2.0, 0.42, Z1), (0.26, 0.43, 0.08))
        return np.maximum(np.minimum(body, gable), -door)

    def wallmat(q):
        b = q + off
        front = b[:, 2] > Z1 - 0.03
        beam = ((np.abs(b[:, 0] - X0) < 0.09) | (np.abs(b[:, 0] - X1) < 0.09)
                | (np.abs(b[:, 1] - EAVE) < 0.06) | (b[:, 1] < 0.1))
        win = (front & (np.abs(b[:, 1] - 0.58) < 0.17)
               & ((np.abs(b[:, 0] - 1.02) < 0.20)
                  | (np.abs(b[:, 0] - 2.98) < 0.20)))
        loft = front & (np.hypot(b[:, 0] - 2.0, b[:, 1] - 1.42) < 0.15)
        return np.where(win | loft, M.WINDOW, np.where(beam, M.BEAM, M.WALL))

    def door(q):
        return box(q + off, (2.0, 0.42, Z1 - 0.04), (0.25, 0.42, 0.02))

    def roofs(q):
        return roof_x(q + off, 2.0, (Z0 + Z1) / 2, 1.72, (Z1 - Z0) / 2 + 0.16,
                      EAVE - 0.08, RIDGE + 0.06, 0.12)

    def roofmat(q):
        course = np.mod(np.abs((q + off)[:, 0] - 2.0) / 0.21, 1.0)
        return np.where(course < 0.25, M.ROOF_D, M.ROOF)

    def chimney(q):
        return box(q + off, (2.9, 1.75, 2.3), (0.13, 0.36, 0.13))
    return [(wallmat, walls), (M.DOOR, door), (roofmat, roofs),
            (M.BEAM, chimney)], 2.3


def pine(var):
    """Three tiers and a trunk; tall enough to stand into the cell north."""
    cx, cz = 1.0 + 0.08 * (var - 0.5), 1.45
    tiers = ((0.45, 1.20, 0.78, 0.10), (0.95, 1.75, 0.60, 0.07),
             (1.45, 2.45, 0.42, 0.03))

    def sdf(q):
        d = None
        for y0, y1, r0, r1 in tiers:
            t = capsule(q, (cx, y0, cz), (cx, y1, cz), r0, r1)
            d = t if d is None else np.minimum(d, t)
        return d

    def mat(q):
        k = np.mod(q[:, 1] - 0.45, 0.5)
        return np.where(k < 0.16, M.PINE_D, M.PINE)
    def trunk(q):
        return capsule(q, (cx, -0.1, cz), (cx, 0.8, cz), 0.12)
    return [(M.BARK, trunk), (mat, sdf)], 2.6


def deadtree(var):
    """Bare, pale, with its arms up."""
    s = 1 if var else -1
    base = np.array([1.0, 0.0, 1.55])
    limbs = [((0, 0, 0), (0.05, 1.05, -0.05), 0.12, 0.07),
             ((0.02, 0.60, 0), (0.45 * s, 1.15, -0.1), 0.06, 0.03),
             ((0.04, 0.85, 0), (-0.40 * s, 1.45, -0.05), 0.05, 0.025),
             ((0.05, 1.0, -0.05), (0.18 * s, 1.60, -0.15), 0.04, 0.02),
             ((-0.2 * s, 1.22, -0.03), (-0.55 * s, 1.35, 0.0), 0.03, 0.02)]
    parts = []
    for a, b, r0, r1 in limbs:
        parts.append((M.DEADWOOD, lambda q, a=a, b=b, r0=r0, r1=r1: capsule(
            q, base + a, base + b, r0, r1)))
    return parts, 1.7


def mushrooms(var):
    """A stand of caps with spots that glow and breathe."""
    caps = [(1.0, 1.35, 0.52, 0.62), (0.45, 1.70, 0.28, 0.35),
            (1.55, 1.05, 0.32, 0.42)]
    if var:
        caps = [(0.9, 1.4, 0.48, 0.58), (1.5, 1.6, 0.3, 0.38),
                (0.5, 1.05, 0.26, 0.34)]
    parts = []
    for cx, cz, r, hgt in caps:
        parts.append((M.STEM, lambda q, cx=cx, cz=cz, r=r, hgt=hgt: capsule(
            q, (cx, 0.0, cz), (cx, hgt, cz), r * 0.28, r * 0.22)))

        def cap(q, cx=cx, cz=cz, r=r, hgt=hgt):
            d = ellipsoid(q, (cx, hgt, cz), (r, r * 0.6, r))
            return np.maximum(d, (hgt - 0.02) - q[:, 1])

        def capmat(q, cx=cx, cz=cz, r=r):
            a = np.arctan2(q[:, 0] - cx, q[:, 2] - cz)
            rr = np.hypot(q[:, 0] - cx, q[:, 2] - cz) / r
            band = np.abs(np.mod(a * 5 / math.pi + rr * 2, 2.0) - 1.0)
            spot = (band < 0.28) & (rr > 0.25) & (rr < 0.8)
            return np.where(spot, M.CAP_SPOT, M.CAP)
        parts.append((capmat, cap))
    lights = [(1.0, 0.8, 1.2, (0.35, 0.9, 0.8), 0.78, 0.6)]
    return parts, 1.1, lights


def reeds(var):
    """Stems standing out of the wet: a heightfield of spikes, which is all
    a reed bed is from above."""
    def g(x, z, base):
        def stem(dx, dz, r3, r4):
            return (0.10 + 0.10 * r3) * np.clip(
                1 - np.hypot(dx, dz) / (0.07 + 0.04 * r4), 0, 1)
        h, tag = scatter(x, z, 11, 900 + var, SHARED + 900, stem)
        # A bed, round and kept off the borders, so it needs no neighbour.
        bed = np.hypot(x - 1.0, (z - 1.05) * 1.1) \
            + (vnoise(x, z, 6, 910 + var) - 0.5) * 0.35
        return np.where(bed < 0.78, h + 0.03, -1), tag
    return g


def cactus(var):
    s = 1 if var else -1
    cx, cz = 1.0, 1.5
    parts = [
        (None, lambda q: capsule(q, (cx, 0.0, cz), (cx, 1.25, cz), 0.22)),
        (None, lambda q: capsule(q, (cx, 0.55, cz), (cx + 0.45 * s, 0.62, cz),
                                 0.12)),
        (None, lambda q: capsule(q, (cx + 0.45 * s, 0.62, cz),
                                 (cx + 0.45 * s, 1.05, cz), 0.12)),
        (None, lambda q: capsule(q, (cx, 0.80, cz), (cx - 0.38 * s, 0.85, cz),
                                 0.10)),
        (None, lambda q: capsule(q, (cx - 0.38 * s, 0.85, cz),
                                 (cx - 0.38 * s, 1.15, cz), 0.10)),
    ]

    def mat(q):
        a = np.arctan2(q[:, 0] - cx, q[:, 2] - cz)
        rib = np.abs(np.mod(a * 4 / math.pi, 1.0) - 0.5) < 0.12
        return np.where(rib, M.SPINE, M.CACTUS)
    return [(mat, fn) for _m, fn in parts], 1.4


def bones(var):
    """A ribcage half in the salt, and the skull that went with it."""
    s = 1 if var else -1
    parts = []
    for i in range(4):
        x = 0.55 + 0.26 * i

        def rib(q, x=x):
            r = np.hypot(q[:, 1] - 0.0, q[:, 2] - 1.25) - 0.42
            return np.maximum(np.hypot(r, q[:, 0] - x) - 0.045,
                              -q[:, 1] + 0.0)
        parts.append((M.BONE, rib))
    parts.append((M.BONE, lambda q: capsule(q, (0.45, 0.42, 1.25),
                                            (1.40, 0.42, 1.25), 0.05)))
    parts.append((M.BONE, lambda q: ellipsoid(q, (1.0 + 0.55 * s, 0.14, 1.72),
                                              (0.20, 0.15, 0.17))))
    return parts, 0.6


def cave():
    """A mound of rock with a black mouth to the south."""
    def sdf(q):
        n = vnoise(q[:, 0] + q[:, 1], q[:, 2] - q[:, 1], 6, 160)
        mound = ellipsoid(q, (1.0, 0.0, 1.05), (0.98, 1.05, 0.82)) \
            + (n - 0.5) * 0.14
        mouth = ellipsoid(q, (1.0, 0.25, 1.85), (0.40, 0.55, 0.40))
        return np.maximum(mound, -mouth)

    def mat(q):
        inside = (np.abs(q[:, 0] - 1.0) < 0.42) & (q[:, 1] < 0.78) \
            & (q[:, 2] > 1.3)
        return np.where(inside, M.CAVE,
                        np.where(q[:, 1] > 0.7, M.ROCK_L, M.ROCK))
    return [(mat, sdf)], 1.1


def furnace():
    """A forge: a brick body, a stack, and a mouth that breathes."""
    body = lambda q: box(q, (1.0, 0.55, 1.35), (0.62, 0.55, 0.45))
    mouth = lambda q: box(q, (1.0, 0.42, 1.82), (0.30, 0.22, 0.10))

    def bodyf(q):
        return np.maximum(body(q), -mouth(q))
    parts = [
        (M.IRON_D, bodyf),
        # In front of the back of the mouth, not flush with it: on a tie the
        # body wins the surface and the fire is never seen.
        (M.EMBER, lambda q: box(q, (1.0, 0.42, 1.75), (0.28, 0.20, 0.02))),
        (M.IRON, lambda q: cylinder_y(q, (1.25, 1.10, 1.30), 0.16, 0.30,
                                      0.03)),
        (M.RUST, lambda q: box(q, (1.0, 1.12, 1.35), (0.64, 0.04, 0.47))),
    ]
    return parts, 1.45, []


def rift():
    """A tear standing in the dark, the light inside it breathing."""
    parts = [
        (M.RIFT, lambda q: ellipsoid(q, (1.0, 0.1, 1.0), (0.10, 1.25, 0.05))),
        (M.RIFT_HALO, lambda q: ellipsoid(q, (1.0, 0.1, 1.0),
                                          (0.24, 1.45, 0.03))),
    ]
    return parts, 1.5, []


# ---- the regions ------------------------------------------------------------

NIGHT_KEY = dict(light=(-0.55, 0.85, -0.50), key=(0.86, 0.90, 1.05),
                 amb=(0.28, 0.30, 0.46), glint=(0.75, 0.82, 1.0),
                 void=(0.0, 0.0, 0.0), water=-0.12)

GRASSY = dict(
    grass=dict(alb=(0.22, 0.38, 0.26)),
    grass_l=dict(alb=(0.30, 0.50, 0.30)),
    grass_d=dict(alb=(0.15, 0.28, 0.22)),
    dirt=dict(alb=(0.46, 0.39, 0.30)),
    dirt_d=dict(alb=(0.33, 0.28, 0.23)),
    pebble=dict(alb=(0.55, 0.53, 0.52)),
    leaf=dict(alb=(0.17, 0.40, 0.26)),
    leaf2=dict(alb=(0.22, 0.46, 0.25)),
    leaf_d=dict(alb=(0.10, 0.22, 0.17)),
    bark=dict(alb=(0.38, 0.28, 0.20)),
    flower_y=dict(alb=(1.0, 0.86, 0.40)),
    flower_w=dict(alb=(0.95, 0.95, 1.0)),
    flower_r=dict(alb=(0.95, 0.46, 0.55)),
    rock=dict(alb=(0.46, 0.43, 0.40)),
    rock_l=dict(alb=(0.58, 0.55, 0.50)),
    rock_d=dict(alb=(0.30, 0.28, 0.28)),
    wellstone=dict(alb=(0.48, 0.47, 0.50)),
    wellwater=dict(alb=(0.04, 0.06, 0.12), shine=40, spec=0.8),
    wood=dict(alb=(0.42, 0.30, 0.20)),
    roof=dict(alb=(0.66, 0.28, 0.24)),
    water=dict(alb=(0.16, 0.26, 0.52), dif=0.35),
    water_s=dict(alb=(0.22, 0.36, 0.56), dif=0.45),
    water_d=dict(alb=(0.10, 0.17, 0.42), dif=0.30),
    glint=dict(alb=(0.6, 0.68, 0.85), glow=(0.30, 0.36, 0.50)),
    foam=dict(alb=(0.80, 0.86, 0.95)),
    bank=dict(alb=(0.30, 0.26, 0.20)),
    cave=dict(alb=(0.02, 0.02, 0.03)),
    snow=dict(alb=(0.85, 0.88, 0.95)),
)

VILLAGE = dict(NIGHT_KEY, ground='grass', mats=dict(
    GRASSY,
    cobble=dict(alb=(0.48, 0.43, 0.37)),
    cobble2=dict(alb=(0.40, 0.35, 0.30)),
    cobble3=dict(alb=(0.56, 0.50, 0.42)),
    mortar=dict(alb=(0.17, 0.15, 0.14)),
    roof_d=dict(alb=(0.42, 0.17, 0.16)),
    wall=dict(alb=(0.66, 0.58, 0.46)),
    beam=dict(alb=(0.28, 0.20, 0.15)),
    door=dict(alb=(0.10, 0.07, 0.08), glow=(0.06, 0.03, 0.02)),
    window=dict(alb=(0.2, 0.15, 0.05), glow=(0.95, 0.76, 0.34)),
    post=dict(alb=(0.22, 0.20, 0.22), shine=20, spec=0.3),
    glass=dict(alb=(0.3, 0.25, 0.1), glow=(1.0, 0.84, 0.44), flicker=0.25),
))

FIELDS = dict(NIGHT_KEY, ground='grass', mats=dict(
    GRASSY,
    plank=dict(alb=(0.46, 0.34, 0.22)),
    rail=dict(alb=(0.26, 0.19, 0.14)),
))

FOREST = dict(NIGHT_KEY, ground='forest', lump=0.30,
              amb=(0.22, 0.28, 0.40), key=(0.74, 0.84, 0.98), mats=dict(
    GRASSY,
    grass=dict(alb=(0.14, 0.30, 0.22)),
    grass_l=dict(alb=(0.22, 0.42, 0.26)),
    grass_d=dict(alb=(0.08, 0.18, 0.14)),
    moss=dict(alb=(0.12, 0.30, 0.18)),
    litter=dict(alb=(0.36, 0.28, 0.18)),
    fern=dict(alb=(0.20, 0.46, 0.28)),
    leaf=dict(alb=(0.08, 0.27, 0.20)),
    leaf2=dict(alb=(0.12, 0.33, 0.21)),
    leaf_d=dict(alb=(0.03, 0.11, 0.10)),
    pine=dict(alb=(0.10, 0.30, 0.24)),
    pine_d=dict(alb=(0.05, 0.17, 0.15)),
    deadwood=dict(alb=(0.52, 0.50, 0.48)),
    stem=dict(alb=(0.78, 0.74, 0.64)),
    cap=dict(alb=(0.62, 0.22, 0.30)),
    cap_spot=dict(alb=(0.8, 1.0, 0.9), glow=(0.35, 0.85, 0.70), flicker=0.7),
))

SHORE = dict(NIGHT_KEY, ground='sand', tide=0.045,
             cliff_top=(M.SAND_D, M.SAND_D), mats=dict(
    GRASSY,
    sand=dict(alb=(0.68, 0.58, 0.42)),
    sand_l=dict(alb=(0.78, 0.68, 0.50)),
    sand_d=dict(alb=(0.54, 0.45, 0.34)),
    shell=dict(alb=(0.90, 0.86, 0.80)),
    bank=dict(alb=(0.44, 0.38, 0.30)),
    dirt=dict(alb=(0.66, 0.60, 0.48)),
    dirt_d=dict(alb=(0.52, 0.47, 0.38)),
    cliff=dict(alb=(0.50, 0.42, 0.36)),
    cliff_l=dict(alb=(0.62, 0.54, 0.44)),
    reed=dict(alb=(0.50, 0.58, 0.34)),
    water=dict(alb=(0.12, 0.30, 0.52), dif=0.35),
    water_s=dict(alb=(0.20, 0.44, 0.56), dif=0.45),
    water_d=dict(alb=(0.07, 0.17, 0.44), dif=0.30),
))

SALT = dict(NIGHT_KEY, ground='salt', key=(0.84, 0.86, 1.0),
            amb=(0.28, 0.28, 0.42), mats=dict(
    GRASSY,
    salt=dict(alb=(0.62, 0.62, 0.66)),
    salt_l=dict(alb=(0.70, 0.70, 0.74)),
    crack=dict(alb=(0.30, 0.29, 0.36)),
    shell=dict(alb=(0.78, 0.76, 0.78)),
    sparkle=dict(alb=(1.0, 1.0, 1.0), glow=(0.3, 0.3, 0.35)),
    sand=dict(alb=(0.66, 0.60, 0.54)),
    sand_l=dict(alb=(0.76, 0.70, 0.62)),
    sand_d=dict(alb=(0.52, 0.46, 0.44)),
    dirt=dict(alb=(0.58, 0.52, 0.46)),
    dirt_d=dict(alb=(0.46, 0.41, 0.38)),
    cactus=dict(alb=(0.28, 0.46, 0.32)),
    spine=dict(alb=(0.72, 0.78, 0.60)),
    bone=dict(alb=(0.86, 0.84, 0.76)),
    deadwood=dict(alb=(0.54, 0.50, 0.50)),
))

FORTRESS = dict(NIGHT_KEY, ground='iron', key=(0.80, 0.84, 0.98),
                amb=(0.26, 0.28, 0.38), mats=dict(
    iron=dict(alb=(0.34, 0.36, 0.42), shine=16, spec=0.25),
    plate=dict(alb=(0.46, 0.45, 0.44), shine=12, spec=0.2),
    plate_l=dict(alb=(0.55, 0.54, 0.52), shine=12, spec=0.2),
    iron_l=dict(alb=(0.46, 0.48, 0.54), shine=16, spec=0.3),
    iron_d=dict(alb=(0.18, 0.19, 0.24)),
    rivet=dict(alb=(0.60, 0.62, 0.68), shine=30, spec=0.5),
    rust=dict(alb=(0.42, 0.30, 0.24)),
    stripe=dict(alb=(0.85, 0.62, 0.18)),
    pit=dict(alb=(0.02, 0.02, 0.03)),
    pipe=dict(alb=(0.30, 0.40, 0.44), shine=20, spec=0.4),
    pipe_l=dict(alb=(0.44, 0.54, 0.58), shine=20, spec=0.4),
    ember=dict(alb=(0.6, 0.2, 0.05), glow=(1.0, 0.52, 0.16), flicker=0.45),
    wellwater=dict(alb=(0.04, 0.10, 0.14), shine=40, spec=0.8),
))

HUSH = dict(NIGHT_KEY, ground='void', key=(0.74, 0.70, 0.92),
            amb=(0.24, 0.18, 0.36), light=(-0.45, 0.85, -0.45), mats=dict(
    void=dict(alb=(0.02, 0.01, 0.04)),
    star=dict(alb=(0.9, 0.9, 1.0), glow=(0.85, 0.80, 1.0)),
    slab=dict(alb=(0.34, 0.33, 0.40)),
    slab_l=dict(alb=(0.45, 0.44, 0.52)),
    slab_d=dict(alb=(0.17, 0.16, 0.22)),
    rune=dict(alb=(0.5, 0.4, 0.8), glow=(0.50, 0.32, 0.85)),
    rift=dict(alb=(0.9, 0.7, 1.0), glow=(0.95, 0.72, 1.0), flicker=0.6),
    rift_halo=dict(alb=(0.3, 0.1, 0.5), glow=(0.40, 0.14, 0.60),
                   flicker=0.6),
    rock=dict(alb=(0.30, 0.26, 0.40)),
    wellstone=dict(alb=(0.40, 0.36, 0.52)),
    wellwater=dict(alb=(0.3, 0.3, 0.5), glow=(0.30, 0.34, 0.70),
                   flicker=0.4),
))

LOOKS = {'VILLAGE': VILLAGE, 'FIELDS': FIELDS, 'FOREST': FOREST,
         'SHORE': SHORE, 'SALT': SALT, 'FORTRESS': FORTRESS, 'HUSH': HUSH}
for _look in LOOKS.values():
    _look['table'] = table(_look['mats'])

WELL_STYLE = {'FOREST': 'spring', 'FORTRESS': 'tank', 'HUSH': 'basin'}
MOVES = set('!~s_=mFRW')        # anything that renders differently per frame


# ---- a key, as the world it stands for --------------------------------------

def ground(region, look, key, t):
    ch, var, ftok, _mtok, _s, _n = key
    surf = gen_world.land_surface(region, ch) if ftok else None
    base_ch = ch if ch in ',f' else '.'
    gvar = var if ch in gen_world.BASE_GROUND else 0
    rd = reeds(var) if ch == 'r' else None

    def g(x, z):
        h, m = base_ground(look, x, z, gvar, base_ch)
        if rd is not None:
            rh, _tag = rd(x, z, None)
            m = np.where(rh > h, np.where(rh > 0.15, M.GRASS_L, M.REED), m)
            h = np.maximum(h, rh)
        wl = np.full(x.shape, NEG)
        if surf in ('path', 'plaza'):
            w, hp, mp = (path if surf == 'path' else plaza)(
                x, z, [c == '0' for c in ftok], look)
            h = h * (1 - w) + hp * w
            m = np.where(w > 0.5, mp, m)
        elif surf in gen_world.WATER:
            if 'p' in ftok:
                w, hp, mp = path(x, z, [c != 'p' for c in ftok], look)
                h = h * (1 - w) + hp * w
                m = np.where(w > 0.5, mp, m)
            h, m, wl = water(x, z, surf, ftok, look, h, m, t)
        elif surf == 'grate':
            gx = np.mod(x, 0.25) < 0.08
            gz = np.mod(z, 0.25) < 0.08
            open_ = [c == '0' for c in ftok]
            d2 = region2d(x, z, open_, 0.12, 0.02)
            bar = gx | gz | (d2 > -0.08)
            h = np.where(bar, 0.0, -0.6)
            m = np.where(bar, np.where(d2 > -0.08, M.IRON_L, M.IRON), M.PIT)
        return h, m, wl
    return g


def content(region, key, t=0.0):
    ch, var, _ftok, mtok, _s, _n = key
    look = LOOKS[region['key']]
    c = Content(ground(region, look, key, t))
    mass = gen_world.land_mass(region, ch)
    if mass:
        kind = mass[0]
        c.parts, c.top = {'canopy': canopy, 'mountain': mountain,
                          'cliff': cliff, 'dune': dune, 'iron': iron_wall,
                          'pipe': pipes, 'deck': deck,
                          'platform': platform}[kind](look, mtok)
    if ch == 'b':
        c.parts, c.top = bush(var)
    elif ch == 'O':
        c.parts, c.top = rock(var)
    elif ch == '!':
        c.parts, c.top, c.lights = lantern()
    elif ch == 'W':
        style = WELL_STYLE.get(region['key'], 'well')
        wp, top = well(style)
        c.parts, c.top = c.parts + wp, max(c.top, top)
    elif ch in HOUSE_AT:
        c.parts, c.top = house(ch)
    elif ch == 'Y':
        c.parts, c.top = pine(var)
    elif ch == 'y':
        c.parts, c.top = deadtree(var)
    elif ch == 'm':
        c.parts, c.top, c.lights = mushrooms(var)
    elif ch == 'c':
        c.parts, c.top = cactus(var)
    elif ch == 'B':
        c.parts, c.top = bones(var)
    elif ch == 'C':
        c.parts, c.top = cave()
    elif ch == 'F':
        c.parts, c.top, c.lights = furnace()
    elif ch == 'R':
        c.parts, c.top, c.lights = rift()
    return c


VOID = ('v', 0, '', '', None, None)


def render_key(region, key):
    """FRAMES images of one metatile."""
    look = LOOKS[region['key']]
    moves = any(k and k[0] in MOVES for k in (key, key[4], key[5]))
    out = []
    for f in range(FRAMES if moves else 1):
        t = f / FRAMES
        cells = {0: content(region, key, t)}
        if key[4]:
            cells[1] = content(region, key[4], t)
        if key[5]:
            cells[-1] = content(region, key[5], t)
        elif look['ground'] == 'void':
            # Everything here stands over the same floor, and a ray looking
            # down it runs north: give it a row to find the floor in.
            cells[-1] = content(region, VOID, t)
        out.append(render(Context(cells), look, t))
    return out if moves else out * FRAMES
