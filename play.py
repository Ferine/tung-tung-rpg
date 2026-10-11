#!/usr/bin/env python3
"""Scripted playthrough harness: walks the game with adaptive navigation and
reports what actually happened, so a change can be checked against the whole
act structure rather than one screen."""
import ctypes
import sys

import capture

core = capture.Core()
core.lib.retro_get_memory_data.restype = ctypes.c_void_p
core.lib.retro_get_memory_data.argtypes = [ctypes.c_uint]
core.load('tungtung.sfc')
ptr = core.lib.retro_get_memory_data(2)
if not ptr:
    raise SystemExit('The libretro core must expose WRAM; use Snes9x for regression tests.')
SYM = {}
for line in open('tungtung.sym'):
    p = line.split()
    if len(p) == 2:
        try:
            SYM[p[1]] = int(p[0], 16)
        except ValueError:
            pass


def pk(n, c=1):
    return bytes(ctypes.string_at(ptr + SYM[n] - 0x7e0000, c))


def u16(n):
    return int.from_bytes(pk(n, 2), 'little')


def cell():
    return (u16('heroX') // 16, u16('heroY') // 16)


def state():
    return pk('gameState')[0]


def busy():
    return pk('msgActive')[0] or pk('tccs_src/story.asm_scene')[0]


def clear_text(limit=40):
    for _ in range(limit):
        if not busy():
            return True
        core.press(['a'])
        core.run(4)
        core.press([])
        core.run(26)
    return not busy()


def step(d, n=1):
    for _ in range(n):
        core.press([d])
        core.run(9)
        core.press([])
        core.run(2)


# Pathfinding off the same generator the ROM was built from, so the harness
# walks the map the game actually has rather than guessing at it.
import gen_world as _W
from terrain import Rng as _Rng

_GRID = {}


def grid(area):
    if area not in _GRID:
        r = _W.REGIONS[area]
        rows = r['build'](_Rng(r['seed'])).rows()
        blocked = set()
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in _W.HOUSE_CHARS or (_W.ALPHABET[ch][2] & _W.BLOCK):
                    blocked.add((x, y))
        _GRID[area] = blocked
    return _GRID[area]


def path(area, src, dst):
    """BFS. Returns a list of directions, or None."""
    blocked = grid(area)
    if dst in blocked:
        return None
    seen = {src: None}
    q = [src]
    while q:
        cur = q.pop(0)
        if cur == dst:
            out = []
            while seen[cur]:
                d, prev = seen[cur]
                out.append(d)
                cur = prev
            out.reverse()
            return out
        x, y = cur
        for d, nxt in (('left', (x - 1, y)), ('right', (x + 1, y)),
                       ('up', (x, y - 1)), ('down', (x, y + 1))):
            if not (0 <= nxt[0] < 32 and 0 <= nxt[1] < 32):
                continue
            if nxt in blocked or nxt in seen:
                continue
            seen[nxt] = (d, cur)
            q.append(nxt)
    return None


def goto(tx, ty, tries=200):
    """Walk a BFS path, re-planning if a fight interrupts."""
    for _ in range(tries):
        if state() != 2 or busy():
            return False
        here = cell()
        if here == (tx, ty):
            return True
        route = path(pk('curArea')[0], here, (tx, ty))
        if not route:
            return False
        for d in route:
            step(d)
            if state() != 2 or busy():
                return cell() == (tx, ty)
        if cell() == (tx, ty):
            return True
    return cell() == (tx, ty)


def bump(d):
    core.press([d])
    core.run(10)
    core.press([])
    core.run(30)


def hp_frac():
    hp = int.from_bytes(pk('pcHP', 2), 'little')
    mx = int.from_bytes(pk('pcHPMax', 2), 'little') or 1
    return hp / float(mx)


def fight(limit=600):
    for _ in range(limit):
        core.press(['a'])
        core.run(3)
        core.press([])
        core.run(11)
        if state() != 3:
            return state()
    return state()


def report(tag):
    print("  %-22s area=%d cell=%s act=%d party=%d lv=%s state=%d"
          % (tag, pk('curArea')[0], cell(), pk('act')[0], pk('partyCount')[0],
             list(pk('pcLevel', 5)), state()))


def battle_command(command, parameter=None, target=None):
    """Choose only through controller input, including a specific ally target."""
    prefix='tccs_src/battle.asm_'
    def push(button):
        core.press([button]); core.run(2); core.press([]); core.run(3)
    for _ in range(5):
        if pk(prefix+'cmdIndex')[0]==command: break
        push('down')
    push('a')
    if parameter is not None and pk(prefix+'bstate')[0] in (3,4):
        for _ in range(8):
            if pk(prefix+'subIndex')[0]==parameter: break
            push('down')
        push('a')
    if pk(prefix+'bstate')[0]==5:
        if target is not None:
            for _ in range(6):
                if pk(prefix+'targetIndex')[0]==target: break
                push('right')
        push('a')


def smart_fight(limit=2500):
    """Use available recovery, waking and learned skills through ordinary input.
    Empty item stacks never trap the harness in ITEM forever. No stat edits.
    """
    B = 'tccs_src/battle.asm_'
    for _ in range(limit):
        st = state()
        if st != 3:
            return st
        bs = pk(B + 'bstate')[0]
        if bs == 2:                       # command window open
            actor = pk(B + 'actor')[0]
            count=pk('partyCount')[0]
            status=list(pk('pcStatus',count)); items=list(pk('itemCount',8))
            hp=u16a('pcHP',count); maximum=u16a('pcHPMax',count); mp=u16a('pcMP',count)
            alive=[i for i in range(count) if not status[i]&1]
            target=min(alive,key=lambda i:hp[i]/maximum[i])
            low=hp[target]/maximum[target]<.45
            dead=next((i for i in range(count) if status[i]&1),None)
            if actor==0 and any(s&2 for s in status) and mp[0]>=8:
                battle_command(1,0)
            elif dead is not None and items[6]:
                battle_command(2,6,dead)
            elif actor==3 and pk('pcLevel',5)[3]>=14 and mp[actor]>=22 and sum(hp[i]/maximum[i]<.75 for i in alive)>=3:
                battle_command(1,1)  # CURAGA: respond to the late bosses' party-wide attacks
            elif low and actor==3 and mp[actor]>=6:
                battle_command(1,0,target)  # CURA
            elif low and (items[1] or items[0] or items[7] or items[2]):
                item=1 if items[1] and maximum[target]-hp[target]>90 else (0 if items[0] else (7 if items[7] else (1 if items[1] else 2)))
                battle_command(2,item,target)
            elif pk('battleIsBoss')[0] and mp[actor]>=(6,6,8,99,9)[actor] and actor!=3:
                battle_command(1,1 if actor==0 else 0)
            elif pk('battleIsBoss')[0] and (items[5] or items[4]):
                battle_command(2,5 if items[5] else 4)
            else:
                battle_command(0)
            continue
        core.press(['a']); core.run(3); core.press([]); core.run(11)
    return state()


def u16a(n, c):
    b = pk(n, c * 2)
    return [b[i] | (b[i + 1] << 8) for i in range(0, len(b), 2)]


def travel(tx, ty, budget=60):
    """Walk there, fighting whatever turns up."""
    for _ in range(budget):
        if state() == 4:
            return False
        if goto(tx, ty):
            return True
        if state() == 3:
            smart_fight()
            core.run(60)
            clear_text()
        elif state() == 6 or pk('pendingState')[0] != 255:
            # The encounter first enters its Mode 7 transition. Let that
            # settle before deciding that navigation has hit a dead end.
            core.run(180)
        elif busy():
            clear_text()
        else:
            return False
    return False


def interact(x, y, tries=8):
    """Bump a blocked cell from whichever side is walkable.

    Retries around random encounters: standing next to the target is
    encounter ground, so a fight can land between arriving and bumping and
    the first attempt is often eaten by it.
    """
    for _ in range(tries):
        if state() == 4:
            return False
        for dx, dy, d in ((0, 1, 'up'), (0, -1, 'down'),
                          (1, 0, 'left'), (-1, 0, 'right')):
            if not travel(x + dx, y + dy):
                continue
            bump(d)
            if busy():
                return True
            if state() == 3:
                smart_fight()
                core.run(60)
                clear_text()
                break               # try again once the fight is over
            if state() != 2:
                return True
        else:
            return False
    return busy()


def engage(x, y, limit=400):
    """Walk to a guardian and see the fight actually start.

    A guardian is a scene first and a battle second: interact() only opens the
    conversation, and a test that checks for ST_BATTLE on the next line finds
    the field and concludes the boss does not exist. Wait for the state.
    """
    travel(x, y)
    interact(x, y)
    for _ in range(limit):
        if state() == 3:
            return True
        core.press(['a']); core.run(4); core.press([]); core.run(12)
    return state() == 3


def boss_fight(x, y, limit=12000, phases=8):
    """The whole guardian: scene, fight, and -- for the last one -- the second
    shape, which stays inside ST_BATTLE and so is not a new battle to wait for,
    only a longer one."""
    engage(x, y)
    for _ in range(phases):
        if state() == 3:
            smart_fight(limit)
        core.run(150)
        clear_text(200)
        if state() != 3:
            break
    return state()


def far_cells(area, n=2):
    """Two walkable cells far apart in this region, for grinding laps."""
    blocked = grid(area)
    open_cells = [(x, y) for y in range(32) for x in range(32)
                  if (x, y) not in blocked]
    if not open_cells:
        return []
    a = min(open_cells, key=lambda c: c[0] + c[1])
    b = max(open_cells, key=lambda c: c[0] + c[1])
    return [a, b]


def grind(laps=4):
    area = pk('curArea')[0]
    pts = far_cells(area)
    if len(pts) < 2:
        return
    for i in range(laps * 2):
        if state() == 4:
            return
        travel(*pts[i % 2])
