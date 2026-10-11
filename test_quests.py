#!/usr/bin/env python3
"""Sidequest state-machine regressions through real interactions and battles.

SRAM/region fixtures shorten travel. No fixture marks a quest objective done
or manufactures a battle result. Saves are reloaded from actual cartridge RAM.
"""
import ctypes
from pathlib import Path

import field_layouts
import gen_world as world
import test_game as t
from test_game import p

OUT = Path('build/quests')
OUT.mkdir(parents=True,exist_ok=True)


def states(): return list(p.pk('questState',3))


def reload():
    p.core.press([]); p.core.lib.retro_reset(); p.core.run(300)
    t.tap('down'); t.tap('a'); p.core.run(180)
    assert p.state()==2


def event(area,ev,clear=True):
    key=world.REGIONS[area]['key'].lower()
    e=next(e for e in field_layouts.layout(key)['landmarks'] if e['event']==ev)
    x,y=e['cell']; col=Path('assets/area_'+key+'.col').read_bytes()
    dx,dy,direction=next((dx,dy,d) for dx,dy,d in ((0,1,'up'),(0,-1,'down'),(1,0,'left'),(-1,0,'right'))
                         if not col[(y+dy)*32+x+dx]&1)
    t.enter(area,x+dx,y+dy)
    t.tap(direction)
    if clear:
        assert p.clear_text(250)
        p.core.run(40)


def journal(page,name):
    t.tap('start')
    for _ in range(4): t.tap('down')
    t.tap('a')
    assert p.pk('tccs_src/menu.asm_mode')[0]==7
    for _ in range(page): t.tap('right')
    p.core.image().save(OUT/(name+'.png'))
    t.tap('b'); t.tap('b')
    assert not p.pk('menuActive')[0]


def encounter(area):
    key=world.REGIONS[area]['key'].lower()
    col=Path('assets/area_'+key+'.col').read_bytes()
    x,y=next((x,y) for y in range(3,29) for x in range(3,28)
             if col[y*32+x]==2 and col[y*32+x+1]==2)
    t.enter(area,x,y)
    t.put('tccs_src/field.asm_encounterAt',1)
    t.put('tccs_src/field.asm_stepCount',0)
    p.step('right'); p.core.run(180)
    assert p.state()==3


def win():
    p.smart_fight(12000); p.core.run(180); p.clear_text(250); p.core.run(80)
    assert p.state()==2


def kettle():
    t.boot(act=0,flags=0,count=1,area=0,hx=13,hy=7,owned=(0,)*7)
    assert states()==[0,0,0], 'legacy save invented sidequest progress'
    journal(0,'story-objective')
    event(0,9)
    assert states()==[1,0,0]
    journal(1,'kettle-active'); t.save_reload()
    event(1,5)
    assert states()==[2,0,0]
    journal(1,'kettle-ready'); t.save_reload()
    before=p.u16('gold'); event(0,9)
    assert states()==[3,0,0] and p.u16('gold')==before+100 and p.pk('charmOwned',7)[1]==1
    before=p.u16('gold'); event(0,9); event(1,5); event(0,9)
    assert p.u16('gold')==before and p.pk('act')[0]==0
    t.save_reload(); journal(1,'kettle-complete')
    # Exploration can precede the request, and an already owned charm pays out.
    t.boot(act=5,flags=1,count=5,area=1,hx=24,hy=21,owned=(1,)*7)
    event(1,5); before=p.u16('gold'); event(0,9)
    assert states()==[3,0,0] and p.u16('gold')==before+480
    print('Kettle: accept/find/return, save each stage, early discovery, duplicate-charm compensation, no repeat rewards',flush=True)


def wells():
    t.boot(act=1,flags=1,count=1,area=2,hx=14,hy=20,owned=(0,)*7)
    event(2,11); assert states()==[0,0,0]
    t.boot(act=2,flags=5,count=2,area=2,hx=14,hy=20,owned=(0,)*7)
    event(2,11)
    assert states()[1]==1 and p.pk('questWells')[0]==1
    reload(); assert states()[1]==1 and p.pk('questWells')[0]==1
    event(3,11); event(3,11)
    assert states()[1]==1 and p.pk('questWells')[0]==3
    journal(2,'wells-active'); reload()
    assert p.pk('questWells')[0]==3
    event(4,11)
    assert states()[1]==2 and p.pk('questWells')[0]==7
    reload(); assert states()[1]==2
    before=p.u16('gold'); event(2,11)
    assert states()[1]==3 and p.u16('gold')==before+300 and p.pk('charmOwned',7)[2]==1
    reload(); event(2,11)
    assert states()[1]==3 and p.u16('gold')==before+300
    print('Wells: companion prerequisite, three unique regions, immediate autosave, return/reward once',flush=True)


def patrols():
    t.boot(act=4,flags=1,count=4,area=5,hx=18,hy=12,owned=(0,)*7)
    encounter(5); win()
    assert p.pk('questPatrols')[0]==0, 'unaccepted hunt counted a fight'
    event(5,11)
    assert states()[2]==1 and p.pk('questPatrols')[0]==0
    reload(); assert states()[2]==1
    encounter(4); win()
    assert p.pk('questPatrols')[0]==0, 'wrong region counted'
    encounter(5)
    # RUN is the fifth command; repeated attempts use ordinary battle input.
    for _ in range(800):
        if p.state()!=3: break
        if p.pk('tccs_src/battle.asm_bstate')[0]==2:
            p.core.press(['up']); p.core.run(2); p.core.press([]); p.core.run(2)
            p.core.press(['a']); p.core.run(2); p.core.press([]); p.core.run(20)
        else: p.core.run(8)
    p.core.run(180)
    assert p.state()==2 and p.pk('questPatrols')[0]==0, 'escape counted as a win'
    event(5,12,clear=False)
    for _ in range(400):
        if p.state()==3: break
        t.tap('a')
    assert p.state()==3
    win()
    assert p.pk('questPatrols')[0]==0, 'guardian counted as a patrol'
    for count in range(1,4):
        encounter(5); win()
        assert p.pk('questPatrols')[0]==count, 'victory lost or counted during multiple fade frames'
        t.save_reload()
        assert p.pk('questPatrols')[0]==count
    assert states()[2]==2
    journal(3,'patrols-ready')
    before=p.u16('gold'); event(5,11)
    assert states()[2]==3 and p.u16('gold')==before+400 and p.pk('charmOwned',7)[6]==1
    reload(); event(5,11)
    assert p.u16('gold')==before+400
    encounter(5); win(); assert p.pk('questPatrols')[0]==3
    print('Patrols: only accepted fortress victories count; escapes/bosses excluded; partial saves and exactly-once reward',flush=True)


def save_integrity():
    # Damage only a quest byte of a real v3 save: CONTINUE must be unavailable.
    event(5,11)
    sram=p.core.lib.retro_get_memory_data(0)
    blob=bytearray(ctypes.string_at(sram,96)); blob[72]^=1
    ctypes.memmove(sram,bytes(blob),96)
    p.core.lib.retro_reset(); p.core.run(300)
    t.tap('down'); t.tap('a'); p.core.run(180)
    assert p.state()==1, 'quest bytes were not checksummed'
    # A new game after completed quests clears WRAM and starts with no quests.
    t.tap('up'); t.tap('a'); p.core.run(180); p.clear_text(250)
    assert p.state()==2 and states()==[0,0,0]
    assert p.pk('questWells')[0]==p.pk('questPatrols')[0]==0
    print('Save integrity: version-2 migration, version-3 quest checksum, new-game reset',flush=True)


def recovery():
    for area,ev in ((0,9),(2,11)):
        t.boot(act=2,flags=5,count=2,area=area,hx=16,hy=17,
               hp=(10,0,1,1,1),mp=(0,0,0,0,0),status=(4,1,0,0,0))
        event(area,ev)
        assert list(p.pk('pcStatus',2))==[0,0]
        assert p.u16a('pcHP',2)==p.u16a('pcHPMax',2)
        assert p.u16a('pcMP',2)==p.u16a('pcMPMax',2)
    reload()
    assert list(p.pk('pcStatus',2))==[0,0]
    print('Inns and wells revive fallen companions, cure ailments, restore HP/MP; wells save the recovery',flush=True)


def gates():
    for area in range(2,6):
        t.boot(act=area-1,count=area-1,area=area,hx=16,hy=17,
               version=3,quests=(3,3,3),wells=7,patrols=3)
        event(area,2)
        assert p.pk('curArea')[0]==area and p.pk('act')[0]==area-1, 'sidequests bypassed a guardian gate'
        event(area,12,clear=False)
        for _ in range(400):
            if p.state()==3: break
            t.tap('a')
        assert p.state()==3
        win()
        event(area,2)
        assert p.pk('curArea')[0]==area+1 and p.pk('act')[0]==area, 'guardian victory did not open the next road'
    print('Act gates: all four guardian exits deny early travel even with completed sidequests, then open after victory',flush=True)


if __name__=='__main__':
    kettle(); wells(); patrols(); save_integrity(); recovery(); gates()
    print('All sidequest regressions passed.',flush=True)
