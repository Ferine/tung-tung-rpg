# How it is built

The hardware side of TUNG TUNG SAHUR: what sits in which layer, what the eight
bugs were, and how the art and the orchestra get made. `README.md` is about the
game.

The Python pipeline converts both procedural 3D characters and generated
prerendered environment paintings into native SNES graphics. `gen_assets.py`
is the build driver; the source paintings and their bake are checked in.

The music is the one thing not made from nothing, and deliberately: the
instruments are real recordings, because that is what a 16-bit RPG score is.
FF6 and Chrono Trigger are not synthesised — they are an orchestra cut into a
few hundred bytes per instrument and played back through the SPC700. Same
process here, on CC0 material. `SAMPLES.md` has the details and the licence.

---

## Layers

BG mode 1. The priority order for the 3-screen modes (development manual
Appendix A-19) reads, rear to front:

```
back  BG4.0  BG3.0  OBJ.0  BG4.1  BG3.1  OBJ.1  BG2.0  BG1.0  OBJ.2
      BG2.1  BG1.1  OBJ.3      [BG3.1 jumps frontmost when $2105 D3 = 1]
```

Fields use BG2 for the painting, with priority 1 on authored foreground
masks. OBJ characters sit at priority 2, and BG1 priority-1 windows cover
both the characters and foreground. Battle/title modes swap the layer roles.
Characters are sorted by their feet: nearer characters use lower OAM numbers.

| layer | field | battle/title |
|---|---|---|
| BG1 | text and windows | scenery |
| BG2 | scenery and foreground masks | text and windows |
| OBJ | actors, guardian and portrait | party, enemies and portrait |

VRAM word addresses are shared across modes:

| range | use |
|---|---|
| `0000–1FFF` | OBJ art, including the portrait reservation |
| `2000–5FFF` | 1024-tile field cache, or battle/title art |
| `6000–6FFF` | font and UI tiles |
| `7000–77FF` | 64×32 field tilemap; battles use the first half |
| `7800–7BFF` | text tilemap |
| `7C00–7FFF` | spare |

Each field keeps all 4096 source tiles in ROM. A 34×30 cache covers the
scrolling viewport; entering rows and columns are prepared during game logic
and transferred by `fielddma.asm` during V-blank. The tilemap wraps separately
from the graphics cache. At most 1216 bytes are queued for a scrolling edge;
`fieldDmaOverruns` and the emulator suite check the transfer timing. Local
effects replace one tile per frame from the area's baked animation records.

Field actors are freshly raymarched at 26–28 pixels into 32×32 OBJ frames.
Their shared `(16,28)` foot anchor preserves the original 16×16 collision
cells. Tung has four walking phases in each direction; villagers, drifters
and cats retain two poses. Dithered contact shadows and seven subtle OBJ
palette variations tie the figures to each region's light.

The field sheet fills 16KB of OBJ VRAM. Thirty frames occupy separate 4×4
tile blocks; name 448 remains reserved for dialogue portraits, and name 460
receives the current guardian. Guardian positions come from the actual boss
event cells, and their persistent completion flags control visibility.
Actors, guardians and the hero share the foot-depth sort. Entering battle
restores the battle sheet; returning restores field art while preserving
portrait rows that a victory conversation may already have uploaded.

`gen_fieldactors.py` needs numpy for the offline bake. `fieldactors.py` packs
its checked-in `assets/fieldactors.txt` without external dependencies.
`checkgfx.py` verifies packed poses, reserved tiles, walk phases, VRAM limits
and ROM bank boundaries. Emulator tests additionally compare the actual
actor and portrait bytes in VRAM and check signed sprite clipping.

`checkfields.py` verifies every event is reachable, exit arrivals are on safe
floor, event cells intersect their reviewed landmark bounds, depth attributes
match the authoring data, and visible cache slots never alias. Its optional
`--previews build/field-review` output overlays collisions (red), foreground
masks (cyan) and events (yellow) on the source art for human inspection.
Changing source art invalidates its recorded review hash.

## Progression and regression tests

Each guardian has a persistent bit in `storyFlags`. Advancing an act no longer
clears completion, and recruitment ignores companions already in the party.
Version-2 SRAM remains readable: completed guardians are inferred from the
saved act. A saved position that became an obstacle after geometry correction
moves to the nearest ordinary floor when the region loads.

`quests.c` owns three monotonic states (unknown, active, ready, completed),
a three-bit well mask and a capped patrol count. The kettle is independent of
consumable inventory. Only accepted, ordinary fortress victories advance the
patrol count, once per battle despite the multi-frame return fade. Claiming
sets the completed state before opening reward dialogue. Already-owned charm
rewards convert to their shop price; gold saturates instead of wrapping.

The 96-byte SRAM block is now version 3. The original party/inventory fields
remain at bytes 4–71; quest states use 72–74, wells 75, patrols 76, checksum 77.
Version 2 checks its original byte-72 checksum and starts all quests unknown.
Unknown versions and checksum failures disable CONTINUE. Wells change quest
progress and restore all companions before writing SRAM, so an immediate
reset preserves both. Inns also revive fallen companions.

The journal is a four-page field menu: the main act objective and three
sidequest pages, with status, next steps, counters and reward. Quest status
never participates in `storyMayLeave`. Iron floors now enable encounters;
`checkfields.py` rejects a combat region without encounter ground.

`test_game.py` drives the built ROM through Snes9x's libretro API, with fixed
SRAM fixtures and ordinary controller input for interactions. It checks seven
field scenes against their packed pixels, scrolling and DMA timing, depth,
animation, menus, random encounters, old-guardian backtracking, save/load,
recruitment and all guardian victories through the ending. High-level fixtures
keep progression checks quick; campaign balance and physical hardware still
require playtesting. CI builds pinned pvsneslib/Snes9x revisions and runs the
same suite. Captures and results are written to `build/regressions/`.
`test_quests.py` exercises all three quests, saved intermediate stages,
out-of-order discovery, reward idempotence, excluded fights/escapes, save
checksums and recovery. `test_campaign.py` follows the complete main route
from NEW GAME with no injected stats, position or encounter changes and no
sidequest rewards. Its checkpoints report the actual levels and supplies.

---

## The orchestra

Twenty-seven instruments cut from two CC0 libraries (`SAMPLES.md`), 19.9KB
of BRR between them. Only the instruments the score actually plays are built
into the module, so an unused recording costs no ARAM.

Three kinds, all in `orchestra.py`:

- **loop** — sustained: strings, winds, brass, organ. An attack, then a loop
  that is an exact whole number of the instrument's own periods.
- **shot** — pitched and struck or plucked: harp, marimba, tubular bell,
  pizzicato bass, timpani, the kentongan. Tuned like a loop, plays once, stops.
- **hit** — unpitched percussion, triggered at note 60.

**Tracker note 60 is middle C** (261.63 Hz) and every instrument is tuned to
it, so a note number means one pitch everywhere. The score is written in
sounding pitch, scientific naming. (The previous soundtrack had the whole
keyboard an octave off its own note names, which put every trumpet and oboe
line at 900–1800 Hz, where those instruments are at their harshest.)

### What has to happen to a recording

A ten-second 44.1 kHz stereo WAV is not a SNES instrument, and every step
below is here because doing it carelessly once produced an audible fault.

- **A real low-pass before decimation.** The first version averaged groups of
  samples, which is not a filter: everything above the new Nyquist folded back
  into the band as a fixed shimmer of inharmonic partials under every note.
  `sfsample.sample_at` is a Kaiser-windowed sinc, the same for every ratio.
  Measured on the DSP, the share of a trumpet's energy that sits on harmonics
  of the note rose from 50% (high notes) to 98%.
- **The loop is contiguous with its attack.** It used to be cut one loop-length
  *past* the attack, so the two did not meet, and four of nine instruments
  ticked once per note (a 5–7× step). The loop start is now chosen where the
  source is most periodic over the loop length and best matches the tail of the
  attack, and the head is blended into it.
- **The loop wraps into what precedes it.** smconv's BRR encoder predicts each
  block from the samples before it, and at the wrap those are the *end* of the
  loop. If the end and the attack's tail differ, the first loop block decodes
  wrong on every pass. The loop's last samples are made to equal the samples
  before its start.
- **Whole periods, on 16-sample blocks.** A loop can only re-enter at a BRR
  block boundary, so its length is a multiple of 16 — and 16 has no reason to
  divide a violin's period. Cut at a round number the loop is 11½ periods
  long, and what you hear is the loop frequency itself, a warble under a
  sustained note. The source is resampled by a fraction of a percent until *k*
  periods fit the block-aligned length, after which
  `C5Speed = 261.63 × (loop length / periods)`.
- **Samples per cycle is the timbre.** `p` samples per cycle keeps `p/2`
  harmonics, independent of pitch; 24–32 is the range used. It also fixes the
  cost: bytes scale with `p × f₀`, so a bass is nearly free and a piccolo is
  not.
- **Pitch is measured, never assumed.** `checktune.py` measures the finished
  loops (upsampled 8×) and fails the build over 18 cents; they all measure
  within a cent. It also checks the seams: no join or wrap may step more than
  the loop's own steepest ordinary step. Pitched one-shots are measured from the
  recording — by spectral peak for bars, by period for strings — and tuned to
  the *measured* pitch, because a zither string and a marimba bar are not on
  the equal-tempered grid. Both libraries name files an octave below where they
  sound, and the kentongan and the glockenspiel of the old score were
  mislabelled by 1½ octaves and one octave; the title theme's slit-drum figure
  never sounded like what was written.
- **Shape the top.** `tilt` (dB per octave above 1 kHz) and `bw` (harmonics
  kept) soften the brightest recordings before they are pitched around the
  keyboard: solo violin, trumpet, organ, oboe, the metal percussion.

**Levels.** Every sample is normalised to the same peak; `gv`, the sample's
global volume (0–64, unity at 64, so it can only turn things *down*), balances
them. `LEVELS` in `orchestra.py` was set by rendering each instrument at
tracker volume 40 through the emulated DSP and matching K-weighted loudness, so
on any sustained instrument **volume 40 is mezzo-forte and means the same
loudness**. Measured: every sustained instrument lands within ±0.2 LUFS.

Warm to harsh, same tune, same accompaniment, equal loudness, ear-weighted
share of energy in 2–6 kHz: horn (−20 dB), clarinet, flute, oboe, strings
section, viola, cello, organ, solo violin, **trumpet (−4 dB)**. That table is the
reason the score has no trumpet lead.

## Music

Fourteen original themes, written in a small score language and compiled to an
Impulse Tracker module for smconv:

| file | role |
|---|---|
| `score.py` | the notation (a line per voice, a bar at a time), the checker, the compiler |
| `orchestra.py` | the instruments and how each is cut |
| `themes_*.py` | the music |
| `gen_music.py` | assembles the modules and writes `res/music.h` |
| `sfx.py` | the eight sound effects |
| `audition.py` | plays a theme through an emulated SPC and measures it |

A theme is sections; a section is a line per voice. The compiler rejects notes
outside an instrument's range and bars of the wrong length, and reports bass
that disagrees with the written chord. Pattern data costs two bytes per *row*
(empty or not) and about four per note, so slow music is written on an
eighth-note grid, sections that repeat are compiled once, and the byte cost of
every theme is printed.

**The score is one work, not a playlist.** Three ideas recur. *The call* is
three equal notes and a leap upward — the kentongan, TUNG. TUNG. TUNG. — and it
opens the road tune. *The road* is the pilgrim's tune, bright and bugle-like:
walked in the field, bent into E minor for the fortress, and sung in full, in a
major key, in the ending. *The lullaby* is the Sleep's tune, three sighs each
falling a third: warm in the village, hollowed out in the Hush, and the thing
Il Silenzio pleads with. That boss now has two themes, one per shape: the
plea, and the same tune with its patience gone (`BGM_FINAL2`, started by
`battle.c` at the moment the second shape stands up).

### What the SPC700 driver does and does not do

Everything here was read from `sm_spc_wla.asm` or measured, and each one cost
something to learn.

- **It ignores the DSP's ADSR entirely.** Every voice runs on direct GAIN and
  the driver does its own envelope, a tick at a time. Voice volume is *only*
  pan; loudness is `sample × instrument × channel × envelope × fade`, 7 bits at
  the end.
- **A note-off needs an envelope.** `Channel_ProcessEnvelope` tests the key the
  wrong way round for an instrument *without* an envelope, so its fadeout
  starts the instant the note is struck and the note dies in a few ticks. With
  a volume envelope the driver holds at the sustain node while the key is down
  and starts the fade only after key-off. Every sustained instrument therefore
  carries a two-node envelope with a sustain node, and a fadeout (the release:
  `1020 / fadeout` ticks). The old score never used note-off at all, only a
  hard `NOTE_CUT`, and every phrase ended in a chop.
- **Tempo is clamped to 80–200.** The SPC's tick timer cannot run slower than
  about 32 ms, and the driver clamps an absolute tempo to that range. Slow
  music gets its slowness from more ticks per *row* (speed), at a tempo near
  120, which also makes a tick about 21 ms in every theme so an instrument's
  release means the same thing in all of them. `score.Theme` chooses the speed.
- **Sound effects steal voices 7 and 8**, and a sustained note on a stolen
  voice is gone for good. Nothing essential is ever written there; they carry
  ornament.
- **`spcPlay` resets the module's state** (echo enables, pans, volumes, the
  echo buffer), so per-voice echo switches cannot leak from one theme into the
  next. They *do* persist across a loop point inside a theme.
- **Position is an order number**, not a pattern number, so themes share
  patterns across their order lists and `music.h` carries order ranges.
- Vibrato, volume slides, pan, echo switches and tempo work. Tremolo,
  panbrello, tremor and fine vibrato do not.

### Not chopping the music

Two faults shipped in the first version of the new compiler, and the second
survived for hours because no loudness figure shows it.

Every sustained note was ended one *row* early. At a slow grid a row is ~17
ticks, about 350 ms, and the release is ~9 ticks, so every voice fell silent for
roughly 180 ms at every bar line. The rule now: a note ends where it ends; a
following note simply replaces it (legato); the release starts only where a
rest begins; and a note left ringing at the end of a pattern is released on the
first row of the next one unless that pattern starts a note there.
`audition.py` counts these holes (a dip to under a twelfth of the median level
inside sustained music) and fails the theme on any; it reads 0 on the score and
11 on the compiler before the fix.

Every note in a part also used to sit at exactly one volume for a whole section.
The compiler now leans on the downbeat (+3), lets off-beat subdivisions fall
away (−2) and gives long notes a step more, for the voices that carry a line.

### The mix

The echo is one set of parameters for the whole module — 48 ms, low-passed,
with the bass and the drums kept dry — and the sends are chosen per voice:
`EON` covers the tune, the harmony and the ornaments. The soundtrack sits at
about −18 LUFS with peaks around −5 dB and no clipped frame; the previous score
sat about −18 as well, but with an ear-weighted 2–6 kHz share of −7.7 dB where
this one sits near −13 dB.

The sound effects are soft, rounded sounds now (a tick, a chime, a thud, a
shimmer) stored at 8 kHz — a slit drum for the SAHUR! effect, the real
recording — played at DSP pitch 2, and quiet enough to sit in the music: they
were full-scale blips played at 13–15 of 15 on a mix peaking far lower.

### Budget

The SPC has 64 KB and smconv leaves 57,957 bytes of it for modules. The score
spends 57,460 of 57,957 bytes: 19.9KB of instruments, 26.0KB of pattern data, 6KB of
echo buffer and 5.4KB of effects, with 0.5KB free.

Every theme, played for a full loop through the emulated SPC700 (`python3 audition.py`), reads `ok`:

| theme | peak | LUFS | presence | theme | peak | LUFS | presence |
|---|---|---|---|---|---|---|---|
| TOWN | −8.0 dB | −19.2 | −15.1 dB | BATTLE | −4.1 dB | −17.6 | −14.9 dB |
| FIELD | −5.7 dB | −18.9 | −11.5 dB | BOSS | −4.0 dB | −16.6 | −12.4 dB |
| FOREST | −8.2 dB | −20.3 | −19.8 dB | FINAL | −6.9 dB | −18.5 | −15.3 dB |
| SHORE | −5.7 dB | −19.1 | −15.1 dB | FINAL2 | −4.7 dB | −17.4 | −16.6 dB |
| SALT | −10.4 dB | −21.2 | −13.8 dB | FANFARE | −4.1 dB | −15.4 | −15.0 dB |
| FORTRESS | −4.4 dB | −16.2 | −13.1 dB | TITLE | −3.0 dB | −17.2 | −14.1 dB |
| HUSH | −11.2 dB | −22.3 | −17.0 dB | ENDING | −5.8 dB | −19.3 | −15.0 dB |

No clipped frame and no dropout in any of them. "Presence" is the A-weighted
share of energy in 2-6 kHz; the score it replaced measured -7.8 dB (town) and
-7.7 dB (battle) on the same instrument.

---

## Cartridge

Mode 20 (LoROM), `$FFB0`–`$FFDF` registration header per cartridge-rom.md:
`$FFD5 = $20` LoROM/SlowROM, `$FFD6 = $02` ROM+RAM+battery, `$FFD8 = $01` for
2KB of SRAM, `$FFDA = $33` — the licensee code that tells the reader to look in
the extended header at `$FFB0`. The checksum is the sum of every byte modulo
$10000 with the two checksum words counted as $00; complement and checksum must
XOR to $FFFF, which they do.

The cartridge is declared 4MB (`ROMSIZE $0C`, 128 banks) and about 1.4MB of it
is code and data. The rest is headroom — the declaration is what a mapper and
an emulator read, and the size is deliberate, not filled.

## Tools

Every binary the ROM embeds — tilesets, tilemaps, collision, palettes,
animation strips, H-DMA tables — is written into `assets/`. The generators name
them, the `.incbin` lines in `data.asm` and the generated `worlddata.asm`,
`bgdata.asm`, and `hdmadata.asm` read them from there, and the assembly units
themselves stay in the root because `snes_rules` globs root `*.asm` into
`OFILES`.

| file | does |
|---|---|
| `gen_assets.py` | driver: runs every generator below |
| `gen_font.py` | BG2 sheet — glyphs, icons, gauges, window frame, logo letters |
| `terrain.py` | metatile painters, shared by every region |
| `gen_world.py` | seven regions: maps, collision, events, exits, the land keys, and tilesets and tilemaps cut from the baked land |
| `gen_battle.py` | writes the six prerendered battle stages and dawn palette from the checked-in bake |
| `gen_prerender.py` / `prerender.py` | offline environment conversion / dependency-free bake loading |
| `checkgfx.py` | packed graphics, collision, VRAM allocation and DMA bank validation |
| `gen_sprites.py` | resident OBJ sheet, streamed enemy blob, dialogue portraits, the sleepwalkers |
| `gen_fieldactors.py` / `fieldactors.py` | offline larger actor/guardian rendering and dependency-free field OBJ packing |
| `gen_render.py` | raymarches the pre-rendered party and every scene in `render_*.py`, and bakes them into `assets/renders.txt` (needs numpy; not run by `gen_assets.py`) |
| `render_land.py` | the land engine: the oblique camera, a cell's column, the region palette cut |
| `render_*.py` | scenes for `gen_render.py`: `sleepers`, `wilds`, `canon`, `bosses`, `portraits`, `backdrops`, `title`, `field`, `regions`; a key in `SCENES` replaces that `ENEMY_ART` or `PORTRAIT_ART` painter, a key in `BACKDROPS` that region's painted backdrop, a key in `FIELD` that kind's walking poses, a key in `LOOKS` that region's tileset |
| `gen_hdma.py` | per-scanline colour and scroll tables |
| `gen_mode7.py` | 256-colour Mode 7 encounter-warp map, characters and palette |
| `gen_music.py` | assembles the score and the effects into two `.it` modules and `res/music.h`; prints the ARAM budget |
| `score.py` | the score language: notation, checker, compiler |
| `orchestra.py` | every instrument, how it is cut, its range and its level |
| `themes.py` `themes_*.py` | the music: fourteen themes |
| `sfx.py` | the eight sound effects |
| `audition.py` | plays a theme through an emulated SPC700 and measures loudness, clipping, dropouts and shrillness |
| `audition/` | the audition ROM (driver and soundbank, no game) |
| `snesgfx.py` | 4bpp/CGRAM/tilemap encoders and the drawing surface |
| `itwriter.py` | a minimal Impulse Tracker writer |
| `preview.py` | renders the converted binaries back to PNG — `world`, `battle`, `sprites`, `actors`, `anim`, `portraits`, `title` |
| `capture.py` | runs the ROM headless in the Mesen-S libretro core |
| `play.py` | scripted playthrough: BFS pathing, fights, act checks |
| `perf.py` | frames advanced per 60, per game state |
| `mksave.py` | hand-builds an SRAM save block, so a test can start at any point |
| `checksyms.py` | fails the build on a global defined twice |
| `checktext.py` | fails the build on a string wider than the screen |
| `checkfaces.py` | fails the build on a speaker with no portrait |
| `checkbank.py` | fails the build when audio.c and smconv disagree on the soundbank symbol |
| `checkrom.py` | fails the build if the 4MB LoROM/battery-SRAM header or checksum changes |
| `checktune.py` | fails the asset build on an instrument more than 18 cents out, or a loop seam that steps |
| `gen_title.py` | cuts the baked title into 512 characters and eight palette steps; the painted title is its fallback |
| `sfsample.py` | conditions real recordings into looped SNES samples: proper low-pass, contiguous loops, whole periods |
| `fetch_samples.py` | downloads the CC0 source recordings into `samples/` |

`preview.py` shows what the *generators* produced. `capture.py` shows what the
console actually put on screen, which is the only way to observe a mistake made
between the `.pic` file and the PPU — and it is how most of the bugs above were
found. `play.py` builds on it with BFS pathfinding taken from the same
generator the ROM was built from, so a change can be checked against the whole
six-act structure rather than one screen:

```python
exec(open('play.py').read())
travel(29, 13)          # BFS across the region's own collision map
boss_fight(16, 15)      # scene, battle, and any second shape
```

`mksave.py` is the other half of that: the save block's layout is written out
longhand in `save.c` because it outlives the build, and the same property lets
Python write one. Injecting a blob into the core's SRAM and choosing CONTINUE
puts a level-24 party at the last well in about a minute, instead of the
forty-five a legitimate route takes — which is the difference between testing
the final boss once and testing it until it is right.

Two things about driving that core from Python: it wants `retro_init()` called
*before* the video/audio/input setters (its setters dereference a pointer that
`retro_init` constructs, so the documented order segfaults), and the ROM buffer
has to outlive `retro_load_game`.

## Regenerating the assets

The generated graphics and tracker modules needed for a normal build are kept
in the repository, so a contributor can build without downloading the 58MB of
source recordings. To rebuild them from their Python sources:

```sh
python3 fetch_samples.py
python3 gen_assets.py
make
```

The procedural character and title renders are checked in as
`assets/renders.txt`. After changing their scenes or palettes, run
`python3 gen_render.py` (requires numpy), then the corresponding generators.
Larger field actors have a separate bake: after changing their scenes or
palettes, run `python3 gen_fieldactors.py`, then `python3 gen_sprites.py`.

To update a field or battle painting, preserve its geometry relative to the
collision map, replace its source PNG, then run:

```sh
python3 -m pip install numpy Pillow
python3 gen_prerender.py
python3 gen_world.py
python3 gen_battle.py
python3 gen_hdma.py
python3 checkgfx.py
make
```

Commit the source art, `baked.zip` and generated binaries/headers together.
The bake has fixed ZIP timestamps and refuses stale source fingerprints.
Do not run the floating-point art bake as part of an ordinary build or CI;
use the checked-in result. No API key or network access is needed to build.

Pillow also supports the binary previews and emulator screenshots:

```sh
python3 preview.py world
python3 preview.py battle
python3 preview.py actors 2  # field poses and guardians under forest lighting
python3 capture.py --core /path/to/mesen-s_libretro --out shots
```

`capture.py`, `play.py`, and `perf.py` also accept the Mesen-S core through the
`MESEN_S_CORE` environment variable. `TUNGTUNG_ROM` can override the ROM path.
