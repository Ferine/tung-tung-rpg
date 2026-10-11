#!/usr/bin/env python3
"""Walk the main campaign from NEW GAME using only controller input.

No SRAM, level, inventory, encounter, position or victory fixtures. Uses wells
and starting supplies; sidequest rewards must remain unclaimed. This is a
repeatable route/pace check, not a substitute for varied human playtesting.
"""
import json
from pathlib import Path

import field_layouts
import gen_world as world
import play as p

OUT=Path('build/campaign')
OUT.mkdir(parents=True,exist_ok=True)
RESULTS=[]


def record(label):
    row=dict(stage=label,state=p.state(),area=p.pk('curArea')[0],cell=p.cell(),
             act=p.pk('act')[0],levels=list(p.pk('pcLevel',5)),hp=p.u16a('pcHP',5),
             items=list(p.pk('itemCount',8)),gold=p.u16('gold'),quests=list(p.pk('questState',3)))
    RESULTS.append(row)
    (OUT/'results.json').write_text(json.dumps(RESULTS,indent=2)+'\n')
    print(label, 'act', row['act'], 'levels', row['levels'], 'HP', row['hp'],flush=True)
    assert row['state']!=4, ('game over',label)
    assert 3 not in row['quests'], 'main route required a sidequest reward'


def event(area,ev):
    assert p.pk('curArea')[0]==area
    key=world.REGIONS[area]['key'].lower()
    e=next(e for e in field_layouts.layout(key)['landmarks'] if e['event']==ev)
    x,y=e['cell']
    if ev<=4:
        p.travel(x,y)
    else:
        assert p.interact(x,y), ('unreachable interaction',key,ev,p.state(),p.cell())
    p.core.run(180)
    if ev!=12: assert p.clear_text(250)
    if ev<=4:
        dest=world.EXITS[world.REGIONS[area]['key']][ev][0]
        assert world.REGIONS[p.pk('curArea')[0]]['key']==dest, ('exit did not connect',key,ev)


def boss(area):
    event(area,12)
    for _ in range(400):
        if p.state()==3: break
        p.core.press(['a']); p.core.run(4); p.core.press([]); p.core.run(16)
    assert p.state()==3, ('boss did not engage',area)
    record('guardian-'+str(area)+'-entry')
    p.smart_fight(12000); p.core.run(180); p.clear_text(250); p.core.run(180)
    record('guardian-'+str(area)+'-victory')
    assert p.pk('act')[0]==area and p.state()==(5 if area==6 else 2), ('guardian did not fall',area)
    p.core.image().save(OUT/('act-'+str(area)+'.png'))


def main():
    p.core.run(180)
    p.core.press(['a']); p.core.run(2); p.core.press([]); p.core.run(180)
    assert p.clear_text(250)
    assert p.state()==2 and p.pk('act')[0]==0 and list(p.pk('pcLevel',5))==[1]*5
    record('new-game')
    # The first exit is closed before La Nonna's scene, with a useful hint.
    p.travel(29,15); p.bump('right'); p.core.run(80)
    assert p.pk('curArea')[0]==0
    assert p.clear_text(250)
    event(0,5); assert p.pk('act')[0]==1
    event(0,1); event(1,2)
    for area in range(2,7):
        event(area,11)
        boss(area)
        if area<6: event(area,2)
    assert p.pk('partyCount')[0]==5
    assert p.pk('storyFlags')[0]&0x7c==0x7c
    print('New game to ending: ordinary movement/battles, all gates and recruits, no quest rewards or stat fixtures.',flush=True)


if __name__=='__main__': main()
