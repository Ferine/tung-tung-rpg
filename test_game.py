#!/usr/bin/env python3
"""ROM regressions through a WRAM-capable libretro core (Snes9x in CI).

Fixtures seed SRAM or queue ordinary region transitions. Interactions, menus,
battles, recruitment and saves run through the game's real input/state loop.
No test changes campaign flags or battle results to manufacture a victory.
"""
import ctypes
import json
from functools import lru_cache
from pathlib import Path
import struct

import field_layouts
import fieldactors
import gen_world as world
import mksave
import play as p
import preview

OUT = Path('build/regressions')
OUT.mkdir(parents=True, exist_ok=True)
RESULTS = []
PORTRAIT_CHECKS = 0


def put(name, value, size=1):
    offset = p.SYM[name] - 0x7e0000
    assert 0 <= offset <= 131072 - size
    ctypes.memmove(p.ptr + offset, value.to_bytes(size, 'little'), size)


def objects():
    data = p.pk('oamMemory',544)
    result = []
    for slot in range(128):
        x,y,name,attr = data[slot*4:slot*4+4]
        extra = (data[512+slot//4] >> (slot%4*2)) & 3
        if extra & 1: x -= 256
        size = 32 if extra & 2 else 16
        if x + size > 0 and x < 256 and y < 224:
            result.append((slot,x,y,name+((attr&1)<<8),size))
    return result


def check_actor_vram():
    """Check resident actors, streamed guardian and any shown portrait in VRAM."""
    global PORTRAIT_CHECKS
    address = p.core.lib.retro_get_memory_data(3)
    assert address, 'regressions need a core exposing VRAM'
    actual = ctypes.string_at(address,16384)
    expected = bytearray(Path('assets/fieldactors.pic').read_bytes())
    area = p.pk('curArea')[0]
    guardians = Path('assets/fieldguardians.pic').read_bytes()
    for row in range(4):
        offset = 460*32 + row*512
        source = area*512 + row*128
        expected[offset:offset+128] = guardians[source:source+128]
    for tile in range(512):
        if tile not in fieldactors.PORTRAIT_TILES:
            assert actual[tile*32:tile*32+32] == expected[tile*32:tile*32+32], ('field OBJ VRAM',area,tile)
    if p.pk('msgFaceShown')[0]:
        face = p.pk('msgFace')[0]-1
        portraits = Path('assets/portraits.pic').read_bytes()
        for row in range(4):
            source = face*512+row*128
            offset = 448*32+row*512
            assert actual[offset:offset+128] == portraits[source:source+128], 'field restoration clobbered portrait'
        PORTRAIT_CHECKS += 1


def clear_field_text(limit):
    for _ in range(limit):
        if not p.busy(): return
        if p.state()==2: check_actor_vram()
        p.core.press(['a']); p.core.run(4)
        p.core.press([]); p.core.run(26)
    assert not p.busy(), 'dialogue did not finish'


def tap(button):
    p.core.press([button]); p.core.run(20)
    p.core.press([]); p.core.run(60)


def report(message):
    RESULTS.append(message)
    print(message, flush=True)
    (OUT/'results.json').write_text(json.dumps(RESULTS, indent=2)+'\n')


def boot(**fixture):
    p.core.press([])
    p.core.lib.retro_reset()
    blob = mksave.make(exp=(101,202,303,404,505), **fixture)
    ctypes.memmove(p.core.lib.retro_get_memory_data(0), blob, len(blob))
    p.core.run(300)
    tap('down'); tap('a'); p.core.run(180)
    assert p.state() == 2, ('continue failed', p.state())


def enter(area, x, y):
    assert not Path('assets/area_'+world.REGIONS[area]['key'].lower()+'.col').read_bytes()[y*32+x] & 1
    put('pendingArea',area); put('pendingX',x); put('pendingY',y)
    put('pendingState',2); put('fadeTarget',0)
    p.core.run(180)
    assert p.state() == 2 and p.pk('curArea')[0] == area and p.cell() == (x,y)


def save_reload():
    before = {n: p.pk(n, size) for n,size in (
        ('act',1),('storyFlags',1),('partyCount',1),('curArea',1),
        ('heroX',2),('heroY',2),('gold',2),('pcLevel',5),('pcExp',10),
        ('pcHP',10),('pcMP',10),('pcCharm',5),('itemCount',8),
        ('questState',3),('questWells',1),('questPatrols',1))}
    tap('start')
    assert p.pk('menuActive')[0]
    for _ in range(3): tap('down')
    tap('a'); p.clear_text(100); tap('b')
    sram = ctypes.string_at(p.core.lib.retro_get_memory_data(0),96)
    assert sram[:4] == b'TTS\x03' and sram[77] == (0x5a+sum(sram[:77])) & 255
    p.core.lib.retro_reset(); p.core.run(300)
    tap('down'); tap('a'); p.core.run(180)
    assert p.state() == 2
    for name, data in before.items():
        assert p.pk(name,len(data)) == data, ('save round-trip',name,data,p.pk(name,len(data)))


@lru_cache(maxsize=7)
def painting(key):
    stem='assets/area_'+key
    return (preview.read_tiles(stem+'.pic'), preview.read_pal(stem+'.pal'),
            struct.unpack('<4096H',Path(stem+'.map').read_bytes()))


def check_picture():
    """Compare sampled PPU pixels against the packed source, across cache seams.
    Allow sprites, animated patches and the small raster lighting subtraction.
    SNES BG vertical scroll addresses the first visible row at offset +1.
    """
    key=world.REGIONS[p.pk('curArea')[0]]['key'].lower()
    tiles,palettes,attrs=painting(key)
    pixels=p.core.image().load()
    sx=p.u16('scrollX'); sy=p.u16('scrollY')
    matching=total=0
    for y in range(4,218,7):
        for x in range(4,250,7):
            wx=x+sx; wy=y+sy+1; i=(wy//8)*64+wx//8
            expected=palettes[((attrs[i]>>10)&7)*16+tiles[i][wy%8][wx%8]]
            matching += max(abs(a-b) for a,b in zip(expected,pixels[x,y])) <= 24
            total += 1
    assert matching/total > .965, ('painting differs from ROM tiles',key,matching/total)


def fields():
    boot(area=0,hx=16,hy=19)
    for area,(key,x,y) in enumerate((('village',16,19),('fields',10,13),
            ('forest',17,18),('shore',16,10),('salt',15,15),
            ('fortress',16,12),('hush',18,25))):
        enter(area,x,y)
        check_actor_vram()
        check_picture()
        p.core.image().save(OUT/(key+'.png'))
        tap('start'); assert p.pk('menuActive')[0]
        tap('b'); assert not p.pk('menuActive')[0]
        for direction in ('right','left'):
            start=p.u16('frameCounter')
            p.core.press([direction]); p.core.run(30); p.core.press([]); p.core.run(12)
            assert (p.u16('frameCounter')-start)&65535 >= 41, ('region movement slowdown',key)
            check_picture()
        assert p.u16('fieldDmaOverruns') == 0
    report('Seven regions: packed-art pixel comparison, loading, menus and field restoration')
    enter(1,5,13)
    put('tccs_src/field.asm_encounterAt',255)
    for direction in ('right','left','down','up'):
        start = p.u16('frameCounter')
        p.core.press([direction]); p.core.run(60); p.core.press([])
        assert (p.u16('frameCounter')-start)&65535 >= 59, ('walking slowdown',direction)
        assert p.u16('fieldDmaOverruns') == 0, ('DMA outside V-blank',direction)
        p.core.run(20)
        check_picture()
    p.core.run(40)
    report('Scrolling in four directions: 60 Hz, no field DMA overruns')
    enter(1,10,13)
    put('tccs_src/field.asm_encounterAt',1)
    put('tccs_src/field.asm_stepCount',0)
    p.step('right'); seen=set()
    for _ in range(260):
        seen.add(p.state()); p.core.run(1)
        if p.state()==3 and p.pk('fadeLevel')[0]==15: break
    assert 6 in seen and p.state()==3, ('encounter warp',seen)
    p.core.image().save(OUT/'battle.png')
    p.smart_fight(6000); p.core.run(180); p.clear_text(200)
    assert p.state()==2 and p.pk('curArea')[0]==1
    check_actor_vram()
    report('Random encounter: Mode 7, battle, victory, restored field')


def actor_motion():
    enter(1,5,13)
    put('tccs_src/field.asm_encounterAt',255)
    names=set(); frames=[]
    p.core.press(['right'])
    for _ in range(32):
        p.core.run(2)
        hero=next(obj for obj in objects() if obj[3] in {fieldactors.name(i) for i in range(16)})
        assert hero[4]==32
        assert hero[1]+16 == p.u16('heroX')+8-p.u16('scrollX')
        assert hero[2]+28 == p.u16('heroY')+8-p.u16('scrollY')
        names.add(hero[3]); frames.append(p.core.image())
    p.core.press([]); p.core.run(20)
    assert len(names)==4, ('missing walk phases',names)
    frames[0].save(OUT/'walking.gif',save_all=True,append_images=frames[1:],duration=34,loop=0)
    # Place one idle walker partly off the left edge: SHOW must preserve X9.
    enter(1,16,13)
    put('tccs_src/npc.asm_npcN',1)
    put('tccs_src/npc.asm_drawOrder',0x020100,3)
    put('tccs_src/npc.asm_npcKind',0)
    put('tccs_src/npc.asm_npcPX',p.u16('scrollX'),2)
    put('tccs_src/npc.asm_npcPY',p.u16('heroY'),2)
    put('tccs_src/npc.asm_npcStep',0)
    put('tccs_src/npc.asm_npcWait',255)
    p.core.run(2)
    npc=next(obj for obj in objects() if obj[3] in {fieldactors.name(i) for i in range(16,22)})
    assert npc[1]==-8 and npc[4]==32, ('walker wrapped at screen edge',npc)
    report('Larger actors: four walk phases, stable feet, signed screen-edge clipping')


def depth_and_animation():
    enter(0,6,5)
    put('tccs_src/npc.asm_npcN',0)
    put('tccs_src/npc.asm_drawOrder',0x0100,2)
    p.core.run(16)
    masked=p.core.image()
    masked.save(OUT/'behind-roof.png')
    # Remove only the high priority bits in the live map as a control image.
    address=p.ptr+p.SYM['fieldCacheMap']-0x7e0000
    entries=struct.unpack('<2048H',ctypes.string_at(address,4096))
    ctypes.memmove(address,struct.pack('<2048H',*(v&~0x2000 for v in entries)),4096)
    source=p.SYM['fieldCacheMap']
    cmd=source.to_bytes(3,'little')+b'\x80'+struct.pack('<HH',0x7000,4096)
    ctypes.memmove(p.ptr+p.SYM['fieldDma']-0x7e0000,cmd,8)
    put('fieldDmaBytes',8,2); p.core.run(2)
    visible=p.core.image()
    sx=p.u16('heroX')-p.u16('scrollX')-8; sy=p.u16('heroY')-p.u16('scrollY')-20
    a=masked.crop((sx,sy,sx+32,sy+32)).tobytes()
    b=visible.crop((sx,sy,sx+32,sy+32)).tobytes()
    assert sum(x!=y for x,y in zip(a,b)) > 6, 'foreground did not hide the hero'
    enter(0,16,12)
    put('tccs_src/npc.asm_npcN',0)
    put('tccs_src/npc.asm_drawOrder',0x0100,2)
    put('frameCounter',0,2); p.core.run(20)
    a=p.core.image().crop((8,88,24,104)).tobytes()
    p.core.run(32)
    b=p.core.image().crop((8,88,24,104)).tobytes()
    assert a!=b, 'lantern animation is static'
    p.core.image().save(OUT/'animated-lantern.png')
    report('Foreground masks occlude the hero; local lantern tiles animate')


def old_guardians():
    boot(act=5,flags=0,count=5,area=2,hx=16,hy=16)
    for area in range(2,6):
        key=world.REGIONS[area]['key'].lower()
        e=next(e for e in field_layouts.layout(key)['landmarks'] if e['event']==12)
        x,y=e['cell']; col=Path('assets/area_'+key+'.col').read_bytes()
        dx,dy,direction=next((dx,dy,d) for dx,dy,d in ((0,1,'up'),(0,-1,'down'),(1,0,'left'),(-1,0,'right'))
                             if not col[(y+dy)*32+x+dx]&1)
        enter(area,x+dx,y+dy)
        assert not any(obj[3]==460 for obj in objects()), 'defeated guardian still visible'
        before=p.pk('pcExp',10)
        tap(direction); p.clear_text(200); p.core.run(180)
        assert p.state()==2 and p.pk('act')[0]==5 and p.pk('partyCount')[0]==5
        assert p.pk('pcExp',10)==before, 'recruitment reset experience'
    save_reload()
    report('Legacy Act VI save: all four past guardians stay defeated; progression and XP survive save/load')
    boot(area=5,hx=2,hy=2)
    x,y=p.cell()
    assert not Path('assets/area_fortress.col').read_bytes()[y*32+x]&1
    assert (x,y)!=(2,2)
    report('Legacy fortress save on corrected scenery relocates to safe floor')


def campaign():
    portraits_before = PORTRAIT_CHECKS
    boot(act=1,flags=1,count=1,area=2,hx=16,hy=16)
    for area in range(2,7):
        key=world.REGIONS[area]['key'].lower()
        e=next(e for e in field_layouts.layout(key)['landmarks'] if e['event']==12)
        x,y=e['cell']; col=Path('assets/area_'+key+'.col').read_bytes()
        dx,dy,direction=next((dx,dy,d) for dx,dy,d in ((0,1,'up'),(0,-1,'down'),(1,0,'left'),(-1,0,'right'))
                             if not col[(y+dy)*32+x+dx]&1)
        enter(area,x+dx,y+dy)
        assert any(obj[3]==460 for obj in objects()), ('guardian not visible',key)
        check_actor_vram()
        p.core.image().save(OUT/('guardian-'+key+'.png'))
        tap(direction)
        for _ in range(400):
            if p.state()==3: break
            if p.pk('msgFaceShown')[0]: check_actor_vram()
            tap('a')
        assert p.state()==3, ('guardian did not engage',key)
        p.smart_fight(12000); p.core.run(180)
        if p.state()==2:
            check_actor_vram()
            p.core.image().save(OUT/('victory-'+key+'.png'))
        clear_field_text(250); p.core.run(180)
        assert p.pk('act')[0]==area, ('act advancement',key,p.pk('act')[0],p.state())
        assert p.pk('partyCount')[0]==min(area,5), ('recruitment',key)
        assert p.pk('storyFlags')[0] & (1<<area), ('guardian persistence',key)
        if area<6:
            assert p.state()==2
            assert not any(obj[3]==460 for obj in objects()), 'guardian figure survived victory'
            save_reload()
            assert not any(obj[3]==460 for obj in objects()), 'guardian figure returned after reload'
            check_actor_vram()
        else:
            assert p.state()==5
            p.core.image().save(OUT/'ending.png')
        report(key+': guardian victory, persistent completion, recruitment/progression')
    assert PORTRAIT_CHECKS > portraits_before, 'no visible dialogue portrait was verified'


if __name__=='__main__':
    fields()
    actor_motion()
    depth_and_animation()
    old_guardians()
    campaign()
    print('All ROM regressions passed.',flush=True)
