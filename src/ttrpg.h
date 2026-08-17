/*
 * TUNG TUNG SAHUR -- an SNES RPG in the Final Fantasy IV idiom.
 *
 * Sahur is the meal before dawn. Tung Tung Sahur walks the night beating his
 * drum to wake the sleeping; three calls, and then the sun. The whole game is
 * one night, and the world does not wake. See STORY.md for the six acts.
 *
 * ---- layer allocation ------------------------------------------------------
 *
 * BG mode 1. ppu-graphics.md's priority table (A-19) for the 3-screen modes
 * reads, rear to front:
 *
 *   back  BG4.0  BG3.0  OBJ.0  BG4.1  BG3.1  OBJ.1  BG2.0  BG1.0  OBJ.2
 *         BG2.1  BG1.1  OBJ.3   [BG3.1 jumps frontmost when $2105 D3 = 1]
 *
 * which is what fixes the assignment below. Windows must cover the party
 * sprites the way FF's do, and the only band that sits above an OBJ without
 * also demanding BG3's four colours is BG2.1 -- it is directly in front of
 * OBJ.2. So:
 *
 *   BG1 (pvsneslib bg 0)  region map / battle backdrop, tiles priority 0
 *   BG2 (pvsneslib bg 1)  text and windows, tiles priority 1
 *   BG3 (pvsneslib bg 2)  unused (its 4-colour palette overlaps BG1's, A-17)
 *   OBJ                   characters at priority 2, under the windows
 *
 * ---- VRAM ------------------------------------------------------------------
 *
 * Word addresses. Character bases are 4K-word granular ($210B/$210C) and
 * tilemap bases 1K-word granular ($2107-$210A), which is what the gaps are.
 *
 *   $0000-$0FFF  OBJ characters 000-0FF   resident: hero, party, effects
 *   $1000-$1FFF  OBJ characters 100-1FF   streamed: this fight's enemies
 *   $2000-$2FFF  font + window tiles (256)      BG2 character base
 *   $3000-$3FFF  region tileset (256)           BG1 character base, field
 *   $4000-$4FFF  region tilemap 64x64           BG1 tilemap base
 *   $5000-$53FF  text tilemap 32x32             BG2 tilemap base
 *   $5400-$57FF  battle tilemap 32x32           BG1 tilemap base, battle
 *   $6000-$6FFF  battle backdrop tileset (256)  BG1 character base, battle
 *
 * The second OBJ page is a scratch window. Thirteen enemy designs and six
 * bosses cannot all be resident in 512 characters, so a fight uploads exactly
 * the ones it needs behind the encounter wipe.
 */
#ifndef TTRPG_H
#define TTRPG_H

#include <snes.h>

/* ---- VRAM map ---------------------------------------------------------- */

#define VRAM_OBJ         0x0000
#define VRAM_OBJ_SCRATCH 0x1000
/* Portrait art. Page-1 character 192 -- a 32x32 OBJ there spans character
 * rows 12-15, which the enemy scratch never reaches: a 64x64 boss at name 256
 * covers rows 0-7 and six small enemies cover rows 0-1. */
#define VRAM_OBJ_FACE    0x1C00
#define FACE_OBJ_NAME    448
#define FACE_OAM         64      /* byte offset: slot 16, clear of battle's */
#define VRAM_FONT        0x2000
#define VRAM_FIELD_GFX   0x3000
#define VRAM_FIELD_MAP   0x4000
#define VRAM_TEXT_MAP    0x5000
#define VRAM_BATTLE_MAP  0x5400
#define VRAM_BATTLE_GFX  0x6000

/* ---- screen ------------------------------------------------------------ */

#define SCR_W       256
#define SCR_H       224
#define SCR_COLS    32
#define SCR_ROWS    28

#define OAM_PARK_Y  240

/* ---- global game state ------------------------------------------------- */

#define ST_BOOT        0
#define ST_TITLE       1
#define ST_FIELD       2
#define ST_BATTLE      3
#define ST_GAMEOVER    4
#define ST_ENDING      5
#define ST_MODE7_WARP  6        /* internal field -> battle transition */
#define ST_NONE      255

extern u8 gameState;
extern u8 pendingState;
extern u16 frameCounter;

#define FADE_MAX 15
extern u8 fadeLevel;
extern u8 animPhase;
extern char portraits_pic;
extern char title_pic, title_map, title_pal;
extern u8 msgY;
extern u8 msgFaceY;
extern u8 msgFace;              /* FACE_* of whoever is speaking, 0 for none */
extern u8 msgFaceRuns;          /* character rows of art still to upload */
extern u8 msgFaceShown;
extern u8 fadeTarget;

void requestState(u8 s);
void globalsInit(void);   /* WRAM is not zeroed at reset; see globals.c */

/* ---- text / window layer ----------------------------------------------- */

extern u8 txtMap[32 * 32 * 2];
extern u8 txtDirty;

#define TILE_GLYPH0   0x00
#define TILE_ICON     0x60
#define TILE_GAUGE    0xC0
#define TILE_WIN      0xE0

/* Palettes on the BG1/BG2 shared CGRAM run ($00-$7F, four 16-colour palettes
 * in mode 1 -- A-17). BG1 art gets 0-2, the window layer gets 3.
 *
 * In battle the backdrop only ever names palette 2, so 0 and 1 are free; the
 * battle setup loads two recolours of the window palette there whose only
 * difference is the glyph colour. Red and green text then cost a palette field
 * in the tilemap entry instead of a second set of characters. Outside battle
 * those two slots are region art and PAL_ALERT/PAL_GOOD must not be used. */
#define PAL_FIELD   0
#define PAL_FIELD2  1
#define PAL_BATTLE  2
#define PAL_WIN     3
#define PAL_ALERT   0           /* battle only: red glyphs */
#define PAL_GOOD    1           /* battle only: green glyphs */

#define TXT_ATTR    ((PAL_WIN << 2) | 0x20)

void textInit(void);
void textClear(void);
void textPutTile(u8 x, u8 y, u8 tile, u8 attr);
void textPut(u8 x, u8 y, const char *s);
void textPutPal(u8 x, u8 y, const char *s, u8 pal);
void textNum(u8 x, u8 y, u16 v, u8 digits);
void textNumPal(u8 x, u8 y, u16 v, u8 digits, u8 pal);
void textFill(u8 x, u8 y, u8 w, u8 h, u8 tile);
void winBox(u8 x, u8 y, u8 w, u8 h);
void winErase(u8 x, u8 y, u8 w, u8 h);
u8 winFillTile(u8 row, u8 h);
void textGauge(u8 x, u8 y, u8 w, u16 cur, u16 max, u8 pal);
void textFlush(void);

/* ---- message box ------------------------------------------------------- */

void msgOpen(const char *s);
void msgOpenAs(const char *s, u8 face);
void msgOpenAtAs(const char *s, u8 y, u8 face);
void msgFaceReset(void);
void msgOpenAt(const char *s, u8 y);
u8 msgUpdate(void);
void msgRepaint(void);
void msgClose(void);
extern u8 msgActive;

/* ---- party ------------------------------------------------------------- */

#define PARTY_MAX 5

#define PC_TUNG     0           /* the drum and the bat */
#define PC_PATAPIM  1           /* a tree with legs; takes the hits */
#define PC_TRALA    2           /* three sneakers, never stops */
#define PC_LIRILI   3           /* cactus elephant; remembers time */
#define PC_BOMBARD  4           /* was on the wrong side, loudly */

#define STAT_DEAD   0x01
#define STAT_SLEEP  0x02
#define STAT_POISON 0x04
#define STAT_HASTE  0x08
#define STAT_SLOW   0x10
#define STAT_DEFEND 0x20

extern u8  partyCount;
extern u16 pcHP[PARTY_MAX], pcHPMax[PARTY_MAX];
extern u16 pcMP[PARTY_MAX], pcMPMax[PARTY_MAX];
extern u8  pcAtk[PARTY_MAX], pcDef[PARTY_MAX], pcMag[PARTY_MAX], pcSpd[PARTY_MAX];
extern u8  pcLevel[PARTY_MAX], pcStatus[PARTY_MAX];
extern u16 pcExp[PARTY_MAX];
extern u8  pcCharm[PARTY_MAX];
extern u16 gold;

/* ---- items ------------------------------------------------------------- */

#define ITEM_HERB    0          /* heal 90, one */
#define ITEM_SALVE   1          /* heal 320, one */
#define ITEM_COFFEE  2          /* wake and 40 HP, one */
#define ITEM_TONIC   3          /* 40 MP, one */
#define ITEM_BOMB    4          /* 80 damage, all enemies */
#define ITEM_THUNDER 5          /* 170 damage, all enemies */
#define ITEM_ELIXIR  6          /* revive at half */
#define ITEM_TEA     7          /* full heal and wake, whole party */
#define ITEM_COUNT   8

extern u8 itemCount[ITEM_COUNT];
const char *itemNameOf(u8 id);
u16 itemPriceOf(u8 id);
u8 itemTargetsAlly(u8 id);

/* ---- charms: one equipment slot each, which is enough ------------------ */

#define CHARM_NONE   0
#define CHARM_STRAP  1          /* +attack */
#define CHARM_BARK   2          /* +defence */
#define CHARM_LACE   3          /* +speed */
#define CHARM_SPECS  4          /* +magic */
#define CHARM_SKIN   5          /* +max HP */
#define CHARM_NOON   6          /* a little of everything */
#define CHARM_COUNT  7

extern u8 charmOwned[CHARM_COUNT];
const char *charmNameOf(u8 id);
u16 charmPriceOf(u8 id);

void partyInit(void);
void partyRecruit(u8 who);
const char *partyNameOf(u8 who);
const char *partyTitleOf(u8 who);
u16 partyExpNext(u8 who);
u8 partyGainExp(u16 amount);
u8 partyAlive(void);
void partyApplyStats(void);

/* ---- skills ------------------------------------------------------------ */

#define SKILL_SAHUR    0        /* Tung */
#define SKILL_SMASH    1
#define SKILL_ROLL     2
#define SKILL_ROOT     3        /* Patapim */
#define SKILL_SHELTER  4
#define SKILL_KICK     5        /* Trala */
#define SKILL_SPRINT   6
#define SKILL_RIPTIDE  7
#define SKILL_CURA     8        /* Lirili */
#define SKILL_CURAGA   9
#define SKILL_ZAP     10
#define SKILL_SLOW    11
#define SKILL_STRAFE  12        /* Bombardiro */
#define SKILL_BOMBRUN 13
#define SKILL_COUNT   14

#define SK_PHYS_ONE     0
#define SK_PHYS_TRIPLE  1
#define SK_MAGIC_ONE    2
#define SK_MAGIC_ALL    3
#define SK_HEAL_ONE     4
#define SK_HEAL_ALL     5
#define SK_HASTE_SELF   6
#define SK_SLOW_ONE     7
#define SK_GUARD_ALL    8

extern const u8 skillMP[SKILL_COUNT];
extern const u8 skillPower[SKILL_COUNT];
extern const u8 skillKind[SKILL_COUNT];
extern const u8 skillLevel[SKILL_COUNT];
const char *skillNameOf(u8 id);
u8 partySkillCount(u8 who);
u8 partySkillAt(u8 who, u8 index);

/* ---- field ------------------------------------------------------------- */

void fieldInit(void);
void fieldEnter(void);
void fieldUpdate(void);
void fieldDraw(void);
void fieldLoadArea(u8 area, u8 mx, u8 my);
u8 fieldCollision(u8 mx, u8 my);
extern u16 heroX, heroY;
extern u8 curArea;
extern u8 pendingArea, pendingX, pendingY;

/* ---- the sleepwalkers -------------------------------------------------- */

void npcInit(u8 area);
void npcUpdate(void);
void npcDraw(s16 camX, s16 camY);
u8 npcAt(u8 mx, u8 my);

/* ---- story ------------------------------------------------------------- */

#define ACT_VILLAGE   0
#define ACT_FOREST    1
#define ACT_SHORE     2
#define ACT_SALT      3
#define ACT_FORTRESS  4
#define ACT_HUSH      5
#define ACT_DONE      6

extern u8 act;
extern u8 storyFlags;

void storyInit(void);
u8 storyBusy(void);
void storyUpdate(void);
void storyEvent(u8 ev);
u8 storyMayLeave(u8 area, u8 ev);
void storyBossWon(void);
void storyPlay(u8 scene);
void storyBegin(void);
const char *storyActName(void);

/* ---- menu, shop, save -------------------------------------------------- */

extern u8 menuActive;
void menuOpen(void);
void menuUpdate(void);
void shopOpen(void);
void saveGame(void);
u8 loadGame(void);
u8 saveExists(void);

/* ---- battle ------------------------------------------------------------ */

#define ENEMY_MAX 6

#define EN_NONE       0
#define EN_SNORFLY    1
#define EN_PILLOWORM  2
#define EN_DREAMBAT   3
#define EN_SANDMAN    4
#define EN_MOTH       5
#define EN_LOG        6
#define EN_JELLY      7
#define EN_HUSK       8
#define EN_DRONE      9
#define EN_TURRET    10
#define EN_WISP      11
#define EN_MURMUR    12
#define EN_PATAPIM   13         /* the bosses */
#define EN_NGANTUK   14
#define EN_SANDKING  15
#define EN_CROCODILO 16
#define EN_SILENZIO  17
#define EN_SILENZIO2 18
/* Six more of the canon, appended after the bosses so nothing renumbers --
 * one face each region gets to itself. */
#define EN_CAPPU     19
#define EN_GUSINI    20
#define EN_AMBALABU  21
#define EN_OCTOPUS   22
#define EN_GLORBO    23
#define EN_SATURNO   24
#define EN_TYPES     25

extern u8  enType[ENEMY_MAX];
extern u16 enHP[ENEMY_MAX];
extern u8  enStatus[ENEMY_MAX];
extern u8  battleIsBoss;

void battleSetRegion(u8 area, u8 backdrop);
void battleStartRandom(void);
void battleStartBoss(u8 type);
void battleUploadEnemies(void);  /* forced blank only */
void battleUpdate(void);
void battleDraw(void);
extern u8 battleResult;
#define BR_RUNNING 0
#define BR_WIN     1
#define BR_LOSE    2
#define BR_FLED    3

/* ---- ppu helpers ------------------------------------------------------- */

void ppuInit(void);
void ppuSetFieldMode(void);
void ppuSetBattleMode(void);
void ppuBattlePalette(u8 which);
void ppuLoadBackdrop(u8 n);
void ppuHdmaSuspend(void);  /* before any GP-DMA outside V-blank */
void ppuMenuPalette(u8 on);
void ppuFlash(u8 frames);
void ppuMosaic(u8 level);
void ppuShake(u8 frames);
void ppuAnimateTiles(void);
void ppuFaceService(void);
void ppuFacePark(void);
void ppuLoadTitle(void);
void ppuTitleCycle(void);
void ppuMode7Start(void);
void ppuMode7Update(void);
void ppuMode7Restore(void);
void ppuUpdate(void);
extern u8 shakeTimer;
extern s16 scrollX, scrollY;

/* ---- audio ------------------------------------------------------------- */

#define BGM_TOWN     0
#define BGM_FIELD    1
#define BGM_FOREST   2
#define BGM_SHORE    3
#define BGM_SALT     4
#define BGM_FORTRESS 5
#define BGM_HUSH     6
#define BGM_BATTLE   7
#define BGM_BOSS     8
#define BGM_FINAL    9
#define BGM_FANFARE  10
#define BGM_TITLE    11
#define BGM_ENDING   12

#define SFX_CURSOR  0
#define SFX_CONFIRM 1
#define SFX_HIT     2
#define SFX_MAGIC   3
#define SFX_HEAL    4
#define SFX_DRUM    5
#define SFX_ERROR   6
#define SFX_DEATH   7

void audioInit(void);
void audioMusic(u8 which);
void audioStop(void);
void audioSfx(u8 which);
void audioProcess(void);

/* ---- input ------------------------------------------------------------- */

extern u16 pad, padTrig;
void inputRead(void);
u16 inputRepeat(u16 mask);

#endif
