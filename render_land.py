"""The land, pre-rendered: the engine that paints a region's metatiles.

Battle backdrops are one picture each; a region is 1024 cells of 64 kinds of
metatile, and every one has to meet every neighbour it is ever put beside.
This is what renders them, one at a time, so that they do. The looks -- the
lights, the materials, what each character is -- are render_regions.py's;
the keys that say which metatiles a region needs are gen_world.py's.

---- the camera -------------------------------------------------------------

Oblique, the way the field is drawn: the ground is seen straight down, one
unit to eight dots, and a unit of height rises K units up the screen. Every
ray is parallel and runs up and back, so a ray only ever crosses its own
column of cells: a metatile's window shows its own cell, the strip of a tall
south neighbour that rises into it, and -- if it is a pit -- the face of the
cell to its north. Never east or west. That is what makes it possible to
render a cell on its own and have it meet its neighbours.

---- the rule that keeps borders honest ---------------------------------------

Every point is lit by its own cell: its ambient occlusion and its shadows come
from that cell's geometry and nothing else's. A point on the border therefore
looks the same from both of the metatiles it can appear in, whatever they
think of their other neighbours. Detail that straddles a border -- a grass
blade, a pebble -- comes from a lattice whose outer ring is seeded the same in
every cell; the inside of the lattice is seeded per variant.

---- palettes -----------------------------------------------------------------

A region gets seven BG palettes -- 0, 1, 2 and 4-7; 3 is the windows' -- and
every character takes whichever draws it best, the way a battle backdrop
does. Anything that moves is rendered FRAMES times and cut as one picture
with 3 x FRAMES channels, the way the title is: one set of characters, a
palette set per frame. Water ripples, lamps flicker, rifts breathe, and not
one character is rewritten. A pixel that does not move may only take a
colour that does not move either, or the ground would shimmer with the sea.
"""
import math

import numpy as np

from gen_render import _norm

SS = 4                  # supersampling per axis
UNIT = 8                # dots per unit, the field sprites' scale
CU = 2.0                # a cell, in units: 16 dots
PX = 16
K = 0.75                # a unit of height rises K units up the screen
TOP = 3.0               # rays start this high; nothing is taller than
BOTTOM = -3.5           # 2.6, or it would reach two cells north
STEPS = 150
LIP = 0.5               # heightfields are marched at half their distance
FRAMES = 4              # palette sets in a region's animation loop
SLOTS = (0, 1, 2, 4, 5, 6, 7)
BUDGET = 256
NEG = -1e9              # no water here


# ---- hashing and noise: integers, so every machine agrees -------------------

M32 = np.int64(0xFFFFFFFF)


def ihash(*args):
    h = np.int64(0x2545F491)
    for a in args:
        a = np.asarray(a).astype(np.int64) & M32
        h = (h ^ a) & M32
        h = (h * np.int64(0x27D4EB2F)) & M32
        h = h ^ (h >> 15)
        h = (h * np.int64(0x165667B1)) & M32
        h = h ^ (h >> 13)
    return (h & 0xFFFFFF).astype(np.float64) / float(1 << 24)


def vnoise(x, z, n, seed):
    """Value noise, n lattice cells to a metatile, periodic on it. Periodic
    means identical in every cell, so it is only for things that are meant
    to repeat, or are too fine to be seen repeating."""
    s = CU / n
    fx, fz = x / s, z / s
    ix, iz = np.floor(fx).astype(np.int64), np.floor(fz).astype(np.int64)
    tx, tz = fx - ix, fz - iz
    tx = tx * tx * (3 - 2 * tx)
    tz = tz * tz * (3 - 2 * tz)

    def at(a, b):
        return ihash(np.mod(a, n), np.mod(b, n), seed)
    return (at(ix, iz) * (1 - tx) * (1 - tz) + at(ix + 1, iz) * tx * (1 - tz)
            + at(ix, iz + 1) * (1 - tx) * tz + at(ix + 1, iz + 1) * tx * tz)


def scatter(x, z, n, seed, shared, fn):
    """Features on a jittered n-per-metatile lattice: `fn(dx, dz, r3, r4)`
    gives one feature's contribution at an offset from it, with two random
    numbers of its own. Returns the largest contribution and the r3 of the
    feature that gave it. The lattice's outer ring is seeded with `shared`,
    so a feature on a border is the same one in both cells."""
    s = CU / n
    bx = np.floor(x / s).astype(np.int64)
    bz = np.floor(z / s).astype(np.int64)
    best = np.full(x.shape, -1e9)
    tag = np.zeros(x.shape)
    for oz in (-1, 0, 1):
        for ox in (-1, 0, 1):
            ix, iz = bx + ox, bz + oz
            mx, mz = np.mod(ix, n), np.mod(iz, n)
            ring = (mx == 0) | (mz == 0) | (mx == n - 1) | (mz == n - 1)
            sd = np.where(ring, shared, seed)
            px = (ix + 0.2 + 0.6 * ihash(mx, mz, sd, 1)) * s
            pz = (iz + 0.2 + 0.6 * ihash(mx, mz, sd, 2)) * s
            r3 = ihash(mx, mz, sd, 3)
            v = fn(x - px, z - pz, r3, ihash(mx, mz, sd, 4))
            win = v > best
            best = np.where(win, v, best)
            tag = np.where(win, r3, tag)
    return best, tag


def voronoi(x, z, n, seed, shared):
    """(distance to the nearest point, to the second, the nearest's random)
    on the same kind of lattice: cobbles, plates, crazing."""
    s = CU / n
    bx = np.floor(x / s).astype(np.int64)
    bz = np.floor(z / s).astype(np.int64)
    f1 = np.full(x.shape, 1e9)
    f2 = np.full(x.shape, 1e9)
    tag = np.zeros(x.shape)
    for oz in (-1, 0, 1):
        for ox in (-1, 0, 1):
            ix, iz = bx + ox, bz + oz
            mx, mz = np.mod(ix, n), np.mod(iz, n)
            ring = (mx == 0) | (mz == 0) | (mx == n - 1) | (mz == n - 1)
            sd = np.where(ring, shared, seed)
            px = (ix + 0.15 + 0.7 * ihash(mx, mz, sd, 1)) * s
            pz = (iz + 0.15 + 0.7 * ihash(mx, mz, sd, 2)) * s
            d = np.hypot(x - px, z - pz)
            r = ihash(mx, mz, sd, 3)
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            tag = np.where(closer, r, tag)
            f1 = np.where(closer, d, f1)
    return f1, f2, tag


def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def region2d(x, z, open_, inset, rr):
    """Signed distance in xz to a cell's share of a surface or a mass: the
    whole cell, carried on past every side that joins a neighbour, pulled in
    by `inset` from every side that does not (N, E, S, W), convex corners
    rounded by rr."""
    BIG = 50.0
    x0 = inset if open_[3] else -BIG
    x1 = CU - inset if open_[1] else CU + BIG
    z0 = inset if open_[0] else -BIG
    z1 = CU - inset if open_[2] else CU + BIG
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    hx, hz = (x1 - x0) / 2, (z1 - z0) / 2
    qx = np.abs(x - cx) - hx + rr
    qz = np.abs(z - cz) - hz + rr
    return (np.hypot(np.maximum(qx, 0), np.maximum(qz, 0))
            + np.minimum(np.maximum(qx, qz), 0) - rr)


# ---- what a cell holds ------------------------------------------------------

class Content:
    """One metatile's world, in its own coordinates, x and z in [0, CU].

    ground(x, z) -> (height, material, water level or NEG): the heightfield
    everything stands on. parts: (material or fn(q) -> material, sdf(q)).
    top: nothing in parts is higher. lights: (x, y, z, rgb, radius, flicker)
    that light this cell and no other; the radius is across the ground and
    has to stay inside the cell."""

    def __init__(self, ground, parts=(), top=0.3, lights=()):
        self.ground = ground
        self.parts = list(parts)
        self.top = top
        self.lights = list(lights)

    def objects(self, q, want_mat=False):
        d = m = None
        for mat, fn in self.parts:
            dd = fn(q)
            if want_mat:
                mm = mat(q) if callable(mat) else np.full(len(q), mat)
            if d is None:
                d, m = dd, (mm if want_mat else None)
                continue
            if want_mat:
                m = np.where(dd < d, mm, m)
            d = np.minimum(d, dd)
        return d, m


class Context:
    """The column a metatile's window looks down: the cell itself at row 0,
    and whichever of its south (1) and north (-1) neighbours can show."""

    def __init__(self, cells):
        self.cells = cells
        self.lo, self.hi = min(cells), max(cells)

    def owner(self, p):
        return np.clip(np.floor(p[:, 2] / CU), self.lo, self.hi).astype(int)

    def eval(self, p, want_mat=False, only=None):
        """Distance, and material, at world points: an SDF evaluation, not
        Python's eval. `only` asks about one row's content alone, which is
        what that row is lit by."""
        n = len(p)
        d = np.full(n, 1e3)
        m = np.zeros(n, int) if want_mat else None
        wet = np.zeros(n, bool) if want_mat else None
        oj = self.owner(p)
        for j, c in self.cells.items():
            if only is not None and j != only:
                continue
            q = p - np.array([0.0, 0.0, j * CU])
            idx = np.arange(n) if only is not None else np.nonzero(oj == j)[0]
            if len(idx):
                qq = q[idx]
                h, gm, wl = c.ground(np.clip(qq[:, 0], 0, CU),
                                     np.clip(qq[:, 2], 0, CU))
                surf = np.maximum(h, wl)
                dg = (qq[:, 1] - surf) * LIP
                if only is None and len(self.cells) > 1:
                    # A column's ground says nothing about the one beside it:
                    # step no further than the border, or a ray jumps
                    # straight through the face of a raised neighbour.
                    zl = qq[:, 2]
                    dg = np.minimum(dg, np.minimum(np.abs(zl), np.abs(CU - zl))
                                    + 0.01)
                better = dg < d[idx]
                d[idx] = np.where(better, dg, d[idx])
                if want_mat:
                    m[idx] = np.where(better, gm, m[idx])
                    wet[idx] = np.where(better, wl > h, wet[idx])
            if c.parts:
                bx = np.maximum(np.maximum(-0.6 - q[:, 0], q[:, 0] - CU - 0.6),
                                np.maximum(-0.6 - q[:, 2], q[:, 2] - CU - 0.6))
                bd = np.maximum(bx, q[:, 1] - c.top)
                near = np.nonzero(bd < 0.1)[0]
                if len(near):
                    od, om = c.objects(q[near], want_mat)
                    better = od < d[near]
                    d[near] = np.where(better, od, d[near])
                    if want_mat:
                        m[near] = np.where(better, om, m[near])
                        wet[near] = np.where(better, False, wet[near])
                far = np.nonzero(bd >= 0.1)[0]
                if len(far):
                    d[far] = np.minimum(d[far], np.maximum(bd[far], 0.02))
        return (d, m, wet) if want_mat else d


# ---- the march --------------------------------------------------------------

RAYDIR = _norm(np.array([0.0, -1.0, -K]))


def _rays():
    n = PX * SS
    u = (np.arange(n) + 0.5) / (SS * UNIT)
    U, V = np.meshgrid(u, u)
    ro = np.stack([U.ravel(), np.full(U.size, TOP), V.ravel() + K * TOP], 1)
    return ro, np.tile(RAYDIR, (U.size, 1))


def _march(ctx, ro, rd):
    tmax = (TOP - BOTTOM) * math.sqrt(1 + K * K)
    t = np.zeros(len(ro))
    hit = np.zeros(len(ro), bool)
    alive = np.ones(len(ro), bool)
    for _ in range(STEPS):
        idx = np.nonzero(alive)[0]
        if not len(idx):
            break
        d = ctx.eval(ro[idx] + rd[idx] * t[idx, None])
        t[idx] += np.maximum(d, 1e-3)
        done = d < 1.5e-3
        hit[idx[done]] = True
        alive[idx[done | (t[idx] > tmax)]] = False
    return t, hit


def _normals(ctx, p):
    e = 2e-3
    out = np.zeros_like(p)
    for a in range(3):
        o = np.zeros(3)
        o[a] = e
        out[:, a] = ctx.eval(p + o) - ctx.eval(p - o)
    return _norm(out)


def _ao(ctx, p, n, who):
    occ = np.zeros(len(p))
    for j in set(who.tolist()):
        sel = np.nonzero(who == j)[0]
        w = 1.0
        for k in range(1, 5):
            h = 0.05 * k
            occ[sel] += w * np.maximum(
                h - ctx.eval(p[sel] + n[sel] * h, only=j), 0)
            w *= 0.6
    return np.clip(1.0 - 2.0 * occ, 0.0, 1.0)


def _shadow(ctx, p, L, who):
    res = np.ones(len(p))
    for j in set(who.tolist()):
        c = ctx.cells[j]
        if not c.parts:
            continue
        sel = np.nonzero(who == j)[0]
        q = p[sel] - np.array([0.0, 0.0, j * CU])
        t = np.full(len(sel), 0.04)
        r = np.ones(len(sel))
        for _ in range(24):
            d, _m = c.objects(q + L * t[:, None])
            r = np.minimum(r, np.clip(6.0 * d / t, 0, 1))
            t += np.clip(d, 0.03, 0.3)
        res[sel] = r
    return res


def water_normal(x, z, t, amp=0.05):
    """Ripples, periodic on the metatile in x and z and on the loop in t."""
    w = 2 * math.pi / CU
    tt = 2 * math.pi * t
    gx = np.zeros_like(x)
    gz = np.zeros_like(x)
    for a, b, s, sp in ((2, 1, 0.5, 1), (1, -2, 0.35, 1), (3, 2, 0.2, 2)):
        ph = w * (a * x + b * z) - sp * tt
        gx += s * w * a * np.cos(ph)
        gz += s * w * b * np.cos(ph)
    return _norm(np.stack([-amp * gx, np.ones_like(x), -amp * gz], 1))


def render(ctx, look, time=0.0):
    """One metatile as floats, 16 x 16 x 3, at `time` in [0, 1)."""
    ro, rd = _rays()
    t, hit = _march(ctx, ro, rd)
    rgb = np.tile(np.asarray(look['void'], float), (len(ro), 1))
    idx = np.nonzero(hit)[0]
    if len(idx):
        rgb[idx] = _shade(ctx, look, ro[idx] + rd[idx] * t[idx, None],
                          rd[idx], time)
    n = PX * SS
    return rgb.reshape(n, n, 3).reshape(PX, SS, PX, SS, 3).mean(axis=(1, 3))


def _shade(ctx, look, p, rd, time):
    L = _norm(np.asarray(look['light'], float))
    _d, m, wet = ctx.eval(p, want_mat=True)
    n = _normals(ctx, p)
    who = ctx.owner(p)
    if wet.any():
        w = np.nonzero(wet)[0]
        n[w] = water_normal(np.mod(p[w, 0], CU), np.mod(p[w, 2], CU), time)
    a = _ao(ctx, p, n, who)
    s = _shadow(ctx, p + n * 0.02, L, who)
    props = look['table']
    alb = props['alb'][m]
    dif = np.clip(n @ L, 0, 1) * s
    amb = (0.55 + 0.45 * np.clip(n[:, 1], -1, 1)) * a
    col = alb * (np.asarray(look['amb'])[None] * amb[:, None]
                 + np.asarray(look['key'])[None]
                 * (dif * props['dif'][m])[:, None])
    half = _norm(L - rd)
    shine = props['shine'][m]
    sp = (np.clip(np.sum(n * half, 1), 0, 1) ** np.maximum(shine, 1)
          * (shine > 0) * props['spec'][m] * s)
    col += sp[:, None] * np.asarray(look['glint'])[None]
    # Flames flicker: two sines, so the loop does not read as a pulse.
    lvl = (0.5 * math.sin(2 * math.pi * time + 0.7)
           + 0.25 * math.sin(4 * math.pi * time))
    col += props['glow'][m] * (1.0 + props['flicker'][m] * lvl)[:, None]
    for j, c in ctx.cells.items():
        for (lx, ly, lz, lc, lr, lf) in c.lights:
            sel = np.nonzero(who == j)[0]
            if not len(sel):
                continue
            dv = np.array([lx, ly, lz + j * CU])[None] - p[sel]
            dist = np.linalg.norm(dv, axis=1)
            # Falloff by distance across the ground, not through the air:
            # a pool has to die out inside its own cell, because nothing
            # else is lit by it and an edge would show.
            fall = np.clip(1 - np.hypot(dv[:, 0], dv[:, 2]) / lr, 0, 1) ** 2
            lam = np.clip(np.sum(n[sel] * dv, 1) / dist, 0, 1)
            col[sel] += alb[sel] * np.asarray(lc)[None] * (
                lam * fall * (1.0 + lf * lvl))[:, None]
    return np.clip(col, 0, 1)


# ---- the palette cut --------------------------------------------------------

STILL = 1.0 / 255


def _snap(c):
    """To the 15-bit colour CGRAM holds."""
    return np.clip(np.round(c * 31), 0, 31) / 31.0


def _kmeans(x, w, k, seed, iters=14):
    rng = np.random.RandomState(seed)
    k = min(k, len(x))
    if k <= 0:
        return np.zeros((0, x.shape[1]))
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
            sel = lab == j
            if sel.any():
                cent[j] = (x[sel] * w[sel, None]).sum(0) / w[sel].sum()
    return cent


def _collapse(px, w):
    q, qi = np.unique(np.round(px * 255).astype(np.int32), axis=0,
                      return_inverse=True)
    return q / 255.0, np.bincount(qi.ravel(), weights=w)


def _palette(px, w, seed):
    """Fifteen colours for one palette's pixels: some still, some moving,
    shared out by how much of each there is."""
    fr = px.reshape(len(px), FRAMES, 3)
    moving = np.abs(fr - fr[:, :1]).max((1, 2)) > STILL
    ws, wa = w[~moving].sum(), w[moving].sum()
    if wa == 0:
        na = 0
    elif ws == 0:
        na = 15
    else:
        na = int(np.clip(round(15 * wa / (wa + ws) * 1.5), 2, 12))
    out = []
    if 15 - na:
        if ws:
            q, qw = _collapse(fr[~moving, 0], w[~moving])
        else:
            q, qw = np.zeros((1, 3)), np.ones(1)
        out += [np.tile(_snap(e), FRAMES) for e in _kmeans(q, qw, 15 - na,
                                                           seed)]
    if na:
        q, qw = _collapse(px[moving], w[moving])
        out += [_snap(e) for e in _kmeans(q, qw, na, seed + 1)]
    while len(out) < 15:
        out.append(out[0] if out else np.zeros(3 * FRAMES))
    pal = np.array(out[:15])
    fr = pal.reshape(15, FRAMES, 3)
    still = np.abs(fr - fr[:, :1]).max((1, 2)) <= 0.5 / 31
    return pal, still


def _assign(px, moving, pal, still):
    """Nearest colour per pixel; a pixel that does not move may only take a
    colour that does not either."""
    d = ((px[:, None, :] - pal[None]) ** 2).sum(2)
    d[np.ix_(~moving, ~still)] = np.inf
    return np.argmin(d, 1), np.min(d, 1)


def quantise(chars, weights, seed=1):
    """chars (N, 64, 3F), weights (N,) -> palettes (7, 15, 3F), slot (N,)
    as an index into SLOTS, pixel indices (N, 64) in 1-15."""
    N = len(chars)
    fr = chars.reshape(N, 64, FRAMES, 3)
    moving = np.abs(fr - fr[:, :, :1]).max((2, 3)) > STILL
    feat = np.concatenate([chars[:, :, :3].mean(1), chars[:, :, :3].std(1),
                           moving.mean(1, keepdims=True)], 1)
    groups = _kmeans(feat, weights, len(SLOTS), seed)
    lab = np.argmin(((feat[:, None] - groups[None]) ** 2).sum(2), 1)
    flat = chars.reshape(-1, 3 * FRAMES)
    pals, stills = [None] * len(SLOTS), [None] * len(SLOTS)
    for it in range(8):
        for j in range(len(SLOTS)):
            sel = lab == j
            if not sel.any():
                sel = np.ones(N, bool)
            pals[j], stills[j] = _palette(
                chars[sel].reshape(-1, 3 * FRAMES),
                np.repeat(weights[sel], 64).astype(float), seed + j + it * 7)
        err = np.stack([_assign(flat, moving.ravel(), pals[j], stills[j])[1]
                        .reshape(N, 64).sum(1) for j in range(len(SLOTS))], 1)
        new = np.argmin(err, 1)
        if (new == lab).all():
            break
        lab = new
    idx = np.stack([_assign(chars[i], moving[i], pals[lab[i]],
                            stills[lab[i]])[0] + 1 for i in range(N)])
    return np.array(pals), lab, idx


def fit_budget(pals, slot, idx, weights, budget=BUDGET):
    """Distinct characters, merged least-missed first until the page holds
    them: (unique (slot, idx) list, map from input character to it)."""
    keys = [(int(s), tuple(int(v) for v in ix)) for s, ix in zip(slot, idx)]
    uniq, where, cnt = [], {}, []
    for k, w in zip(keys, weights):
        if k not in where:
            where[k] = len(uniq)
            uniq.append(k)
            cnt.append(0.0)
        cnt[where[k]] += w
    remap = list(range(len(uniq)))
    if len(uniq) > budget:
        rgb = np.stack([pals[s][np.array(ix) - 1].reshape(-1)
                        for s, ix in uniq])
        d = ((rgb[:, None, :] - rgb[None]) ** 2).sum(2)
        np.fill_diagonal(d, np.inf)
        alive = np.ones(len(uniq), bool)
        cnt = np.array(cnt)
        while alive.sum() > budget:
            a = np.nonzero(alive)[0]
            sub = d[np.ix_(a, a)]
            cost = sub.min(1) * cnt[a]
            i = a[np.argmin(cost)]
            j = a[np.argmin(sub[np.searchsorted(a, i)])]
            alive[i] = False
            remap = [j if r == i else r for r in remap]
            cnt[j] += cnt[i]
        keep = [i for i in range(len(uniq)) if alive[i]]
        renum = {old: new for new, old in enumerate(keep)}
        remap = [renum[r] for r in remap]
        uniq = [uniq[i] for i in keep]
    return uniq, [remap[where[k]] for k in keys]


def bake(key_grid, render_key, key_str):
    """Render every metatile a region uses and cut them to one page.

    key_grid is the region's 32x32 keys, render_key(key) -> FRAMES images,
    key_str(key) the name the bake is filed under. Returns dict(pals
    [FRAMES][7][15] rgb, chars [(slot, idx)], keys {name: 4 characters},
    raw) where raw is how many characters there were before the cut."""
    count = {}
    for row in key_grid:
        for k in row:
            count[k] = count.get(k, 0) + 1
    order = sorted(count, key=key_str)
    chars, weights = [], []
    for k in order:
        fr = np.stack(render_key(k), 0)                 # (F, 16, 16, 3)
        for cy in (0, 8):
            for cx in (0, 8):
                chars.append(fr[:, cy:cy + 8, cx:cx + 8].transpose(1, 2, 0, 3)
                             .reshape(64, 3 * FRAMES))
                weights.append(count[k])
    chars = np.array(chars)
    weights = np.array(weights, float)
    pals, slot, idx = quantise(chars, weights)
    uniq, which = fit_budget(pals, slot, idx, weights)
    return dict(
        pals=pals.reshape(len(SLOTS), 15, FRAMES, 3).transpose(2, 0, 1, 3),
        chars=uniq,
        keys={key_str(k): which[i * 4:i * 4 + 4] for i, k in enumerate(order)},
        raw=len({(int(s), tuple(ix)) for s, ix in zip(slot, idx)}))
