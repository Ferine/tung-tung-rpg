# TUNG TUNG SAHUR — Le Tre Chiamate

A six-act SNES RPG in the Final Fantasy IV idiom, cast entirely from the
Italian brainrot canon.

Sahur is the meal before dawn, and the drum is what wakes a village to eat it.
Tung Tung Tung Sahur walks the night beating his slit drum to wake the
sleeping. Tonight nobody wakes — something came up the east road and took the
WAKING out of people. Took it, like a wallet.

<p align="center">
  <img src="media/title-cycle.gif" width="440" alt="The title screen, its logo shine and star field animating">
</p>

<p align="center">
  <img src="media/prerender-battle.png" width="384" alt="An active-time battle: five-character party, gauges, command window">
  <img src="media/dialogue.png" width="384" alt="LA NONNA speaking, her portrait framed above the message box">
</p>

It is a real 4MB LoROM `.sfc` that runs on hardware and on any accurate
emulator. **[Download the ROM from the v0.001
release.](https://github.com/Ferine/tung-tung-rpg/releases/tag/v0.001)**

---

## The story

A pilgrim walks east. At each stage he meets a guardian who is not evil, only
wrong — beats them, and gains them. By the last act the party is five things
that should not be able to stand each other, walking in step.

SLOP is the material of this world. Not an insult, the substance. Everyone here
was generated, everyone knows it, and none of them find it interesting. A shark
has three shoes. A tree has legs, and the wrong number of them. A crocodile is
also an aeroplane. That is simply what they were made out of, in about four
seconds, and they have all had a month to get over it.

The antagonist is slop that wants to stay smooth: an infinite, comfortable,
frictionless feed where nothing else ever happens and everybody is very relaxed
about that. The party is slop that decided to **get up**. That is the only
difference between them and it is the whole game.

The places are Indonesian, because Tung Tung Tung Sahur is. The people are
Italian, because they are. That collision is the genre, not a mistake in it.

**[`STORY.md`](STORY.md) has all six acts, the cast and the cameos.**

## The party

Each companion is a different argument against lying down.

| | how they refuse | joins |
|---|---|---|
| **TUNG TUNG TUNG SAHUR** — il tamburo | on principle | the start |
| **BRR BRR PATAPIM** — le radici | by standing there, and taking the hits so nobody else has to | Atto II |
| **TRALALERO TRALALA** — tre scarpe | by never stopping | Atto III |
| **LIRILÌ LARILÀ** — il tempo | by remembering | Atto IV |
| **BOMBARDIRO CROCODILO** — l'ordigno | loudly, having been on the wrong side | Atto V |

## The world

Seven regions, each with its own tileset, palette and battle backdrop:
**Kampung Sahur** the village, the east road, **Hutan** the forest that stopped
moving, **Pantai** where the Sleep runs into water and stops, **Padang Garam**
where nothing has grown since before the Sleep, **Langit Besi** a fortress held
up by nothing anybody can point at, and **Malam Panjang** — not a place so much
as a held breath.

The fields are complete prerendered backgrounds inspired by Super Mario RPG
and Final Fantasy VII: sculpted foliage, modeled buildings, warm lantern
pools and baked shadows. Each 512×512 scene scrolls beneath the characters;
an authored collision grid, doors, exits and encounters drive play. The
renderer streams every field tile without dictionary substitution. Foreground
roofs and foliage hide characters as they pass behind them; local water,
lantern, foliage and rift animations bring the paintings to life. The six
battle stages use the same art direction.

Larger modeled characters have contact shadows, four-phase walking and
lighting matched to each region. Guardians now appear on the field at their
encounter locations and disappear after their defeat.

<img src="media/prerender-walk.gif" width="384" alt="Tung walking through the prerendered east road with the larger shaded field sprite">

| | | | |
|:---:|:---:|:---:|:---:|
| <img src="media/prerender-village.png" width="200" alt="Kampung Sahur"> | <img src="media/prerender-fields.png" width="200" alt="The east road"> | <img src="media/prerender-forest.png" width="200" alt="Hutan"> | <img src="media/prerender-shore.png" width="200" alt="Pantai"> |
| **Kampung Sahur** | **the east road** | **Hutan** | **Pantai** |
| <img src="media/prerender-salt.png" width="200" alt="Padang Garam"> | <img src="media/prerender-fortress.png" width="200" alt="Langit Besi"> | <img src="media/prerender-hush.png" width="200" alt="Malam Panjang"> | |
| **Padang Garam** | **Langit Besi** | **Malam Panjang** | |

The field and battle lighting is baked into the scenery. The title screen is a picture: a village under a moon, with the logo's
shine and the star field animated without redrawing a single tile. Encounters
drop through a 256-colour Mode 7 night vortex: the field rotates and rushes at
the camera before the existing mosaic wipe closes over it.

### The sleepwalkers

The regions are not empty, and the people in them are not awake. Twenty-two
figures drift about the seven maps — villagers in nightcaps with their arms out
in front of them, taller ones still in the day's clothes, and the five-legged
cat from the opening, asleep, standing up. They wander a few cells from wherever
the night caught them, they walk into walls and stand there facing them, and
they never say a word, because there is nobody home to say it. They are solid:
you can no more walk through one than talk to them.

The village has six. The salt flat has two, which is as many as the salt flat
has ever had.

<p align="center">
  <img src="media/sleepwalkers.png" width="384" alt="Two sleepwalkers and the five-legged cat, drifting through the village">
</p>


## Battles

Active-time, in the FF4 shape: a gauge per combatant, FIGHT / SKILL / ITEM /
GUARD / RUN, a staggered two-column party of up to five, target selection with
the enemy named, damage numbers. Fourteen skills learned by level, eight items,
charms that take one equipment slot each.

Six acts, five guardians, and a final boss that fights in two shapes: the first
pleads, the second stops being polite.

Twenty-four enemy designs, six of them 64x64 bosses. Six are the canon itself —
Cappuccino Assassino, Bombombini Gusini, Boneca Ambalabu, Blueberrinni
Octopusini, Glorbo Fruttodrillo and La Vacca Saturno Saturnita — one face per
region.

Dialogue is JRPG-style: eight 32x32 busts in a frame above the message box, and
the game works out who is speaking from the line itself.

<p align="center">
  <img src="media/battle.gif" width="384" alt="An exchange in battle: gauges filling, an attack, damage numbers">
  <img src="media/boss.gif" width="384" alt="BRR BRR PATAPIM, a 64x64 guardian, in the forest">
</p>

## Playing it

| button | does |
|---|---|
| **D-pad** | walk; move the cursor |
| **A** | confirm; advance dialogue |
| **B** | cancel, back out of a menu |
| **START** | open the field menu; also advances dialogue |
| **L / R** | flip the shop page |

There is no talk button — walk into somebody, or into a door, and it happens.

<p align="center">
  <img src="media/menu.png" width="384" alt="The field menu: party status, levels, HP and MP">
  <img src="media/shop.png" width="384" alt="The village shop, supplies on one shelf and charms on the other">
</p>

Talk to LA NONNA before the village will let you east. After that the road is
gated one act at a time. **START → QUESTS** opens the journal: the first page
tracks the main objective, and left/right switches between optional quests.
Wells revive fallen companions, restore HP/MP, clear ailments *and* save; there is one before
each guardian, because arriving at a boss on a third of a bar is bookkeeping,
not difficulty. The shop in the village sells supplies and charms. The save is
battery-backed, so CONTINUE picks up where you left it.

Three optional sidequests run alongside the story. Their progress, carried
quest objects and rewards survive saving; none is needed to unlock an act.

| Quest | Start and objective | Reward |
|---|---|---|
| **A Hot Breakfast** | Visit Cappuccina's village inn, recover the kettle at the campfire south of the east road, and return it. Finding it before the request also works. | CINGHIA charm + 100 gold |
| **Water Remembers** | After recruiting Patapim, revisit the Hutan well. Restore the wells in Hutan, Pantai and Padang Garam, then return to Hutan. | CORTECCIA charm + 300 gold |
| **The Last Shift** | Read the ledger at the Langit Besi well. Win three ordinary fortress battles and return. Escapes and guardians do not count. | MEZZOGIORNO charm + 400 gold |

Rewards can be claimed once. A charm you already own pays its shop price
instead. Earlier regions remain accessible throughout the story; finish any
remaining errands before facing Il Silenzio and the ending. Existing version-2
saves load with the new quests unstarted; subsequent saves use version 3.

<img src="media/quest-journal.png" width="384" alt="The quest journal tracking Patapim's three wells and their reward">

**SLEEP is the mechanic to actually think about.** The Sleepers inflict it, a
sleeping character's gauge stops, and Tung's **SAHUR!** clears it from the whole
party at once while hitting everything on the field. Tung himself never sleeps.
In the last act that stops being a convenience and becomes the only reply the
game has.

## The music

Fourteen original themes, written for an orchestra of real recorded instruments
— strings, woodwinds, horns and low brass, harp and mallets, timpani, and the
kentongan, the slit drum the game is named after — cut down to a few hundred
bytes each and played back through the SPC700. Three ideas recur so it reads as
one score: **the call** (three equal notes and a leap: TUNG. TUNG. TUNG.),
**the road** (the pilgrim's tune, bright and bugle-like) and **the lullaby**
(the Sleep's own tune, kind in the village and hollow in the Hush). Il Silenzio
gets two themes, one for each shape it fights in: the first pleads, the second
is the same tune with its patience gone.

It is written in a small score language (`score.py`) and checked by machine:
notes outside an instrument's range and bars of the wrong length are build
errors, and a bass note under the wrong chord is reported. `audition.py` plays any theme through an
emulated SPC700 and reports what the DSP actually produced — loudness,
clipping, dropouts, and how shrill it is.

The instruments are cut from CC0 recordings rather than synthesised, which is
what a 16-bit RPG score actually is: FF6 and Chrono Trigger are an orchestra
sliced into a few hundred bytes per instrument and played back through the
SPC700. See [`SAMPLES.md`](SAMPLES.md) for the sources and the licence. The
eight sound effects are synthesised, soft and short, except the drum.

---

## Build

Prerequisites: Python 3.10 or newer, GNU Make, and
[pvsneslib](https://github.com/alekmaul/pvsneslib).

```sh
export PVSNESLIB_HOME=/path/to/pvsneslib
make
```

That is the whole build — the generated graphics and tracker modules are kept in
the repository, so nothing has to be downloaded first. The ROM is a build
artifact and is deliberately not stored here.

Field and battle source paintings live in `assets/prerendered/`.
`gen_prerender.py` converts them into a checked-in bake; normal builds and
`gen_assets.py` use that bake without image-processing dependencies. The
characters, portraits and title still come from the procedural 3D renderer.
See `assets/prerendered/prompts.json` for the image-generation prompts.

**[`TECHNICAL.md`](TECHNICAL.md)** is the hardware side — the layer and VRAM
layout, the raster effects, how the art and the orchestra are generated, the
tools, and the eight bugs worth writing down.

## Contributing

Bug reports and focused patches are welcome; see
[`CONTRIBUTING.md`](CONTRIBUTING.md). Generated ROMs, downloaded sample WAVs,
compiler output, emulator saves, and development captures should not be
committed.

## License

The project's original code and assets are available under the MIT License; see
[`LICENSE`](LICENSE). The source recordings used by the music pipeline are
independently dedicated under CC0-1.0; see [`SAMPLES.md`](SAMPLES.md).
