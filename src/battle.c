/*
 * TUNG TUNG SAHUR -- the battle engine.
 *
 * Final Fantasy IV's arrangement: enemies on the left, the party staggered in
 * two columns on the right, an ATB gauge each, a command window that opens for
 * whoever fills theirs first, and a message box at the top.
 *
 * ---- one index space -------------------------------------------------------
 *
 * Party and enemies share a combatant index (0-4 party, 5-10 enemies) because
 * the gauge, the status flags and the target cursor all want to treat them the
 * same. The halves diverge only where they must: HP lives in pcHP[] or enHP[],
 * and only the party half opens a menu.
 *
 * ---- streamed enemies ------------------------------------------------------
 *
 * Nineteen designs, six of them 64x64, cannot be resident in 512 OBJ
 * characters. The second character page ($1000-$1FFF, names 100-1FF) is a
 * scratch window: battleStart uploads exactly the designs this fight uses,
 * behind the encounter wipe. A 32x32 design is four transfers of 128 bytes,
 * one per row of its 4x4 block, because a large OBJ's rows are 16 names apart.
 *
 * ---- what SLEEP is for -----------------------------------------------------
 *
 * A sleeping combatant's gauge does not fill. Every Sleeper inflicts it, and
 * Tung's SAHUR CALL clears it from the whole party at once -- which is the
 * game: the drum exists to wake people, so the drum has to be the answer to
 * being put to sleep. In the last act the Hush puts everyone under in one move
 * and SAHUR CALL is the only reply in the game.
 */
#include "ttrpg.h"
#include "gfxmap.h"
#include "sprmap.h"
#include "worldmap.h"

extern char enemies_pic;

/* ---- combatant index space --------------------------------------------- */

#define CB_ENEMY0  PARTY_MAX
#define CB_MAX     (CB_ENEMY0 + ENEMY_MAX)

#define IS_ENEMY(i) ((i) >= CB_ENEMY0)
#define EN_OF(i)    ((i) - CB_ENEMY0)

/* ---- layout ------------------------------------------------------------ */

/* Staggered two columns, the way FF4 stands five people up without a
 * 160-dot-tall party. */
static const u8 pcSprX[PARTY_MAX] = {212, 186, 212, 186, 212};
static const u8 pcSprY[PARTY_MAX] = {20, 47, 74, 101, 128};

static const u8 enSlotX[ENEMY_MAX] = {24, 68, 26, 70, 22, 74};
static const u8 enSlotY[ENEMY_MAX] = {40, 20, 96, 74, 128, 122};
#define BOSS_X 26
#define BOSS_Y 46

#define CMD_X  0
#define CMD_Y  20
#define CMD_W  10
#define CMD_H  8

#define STA_X  10
#define STA_Y  20
#define STA_W  22
#define STA_H  8

#define STA_ROW(i)  (STA_Y + 1 + (i))
#define STA_NAME_X  11
#define STA_HP_X    19
#define STA_MP_X    24
#define STA_GAUGE_X 28

#define MSG_Y  1

/* ---- enemy data -------------------------------------------------------- */

/* Bosses are tuned against the level the road actually delivers by the time
 * the player reaches them -- roughly 6, 10, 14, 16, 22 -- not against a
 * theoretical maximum. Il Silenzio's two shapes come to 4600 between them,
 * which is the largest fight in the game by some way and still resolves
 * inside a couple of minutes; at 6600 it was ten, which is not tension, it
 * is a queue. */
static const u16 enBaseHP[EN_TYPES] = {
    0, 38, 70, 52, 92, 64, 120, 88, 140, 110, 190, 96, 160,
    420, 850, 1500, 2400, 2000, 2600,
    36, 130, 95, 110, 165, 200
};
static const u8 enAtkT[EN_TYPES] = {
    0, 11, 15, 17, 20, 16, 22, 19, 26, 30, 34, 28, 32,
    20, 26, 32, 40, 44, 50,
    10, 30, 18, 21, 27, 33
};
static const u8 enDefT[EN_TYPES] = {
    0, 4, 10, 6, 12, 8, 16, 11, 18, 14, 24, 9, 16,
    16, 18, 22, 26, 26, 30,
    6, 15, 13, 12, 19, 18
};
static const u8 enSpdT[EN_TYPES] = {
    0, 9, 5, 11, 9, 12, 6, 8, 7, 16, 4, 20, 11,
    8, 10, 12, 13, 14, 16,
    9, 13, 7, 11, 9, 10
};
static const u16 enExpT[EN_TYPES] = {
    0, 30, 46, 50, 88, 58, 110, 92, 150, 165, 210, 180, 240,
    400, 700, 1100, 1700, 2200, 3000,
    45, 180, 80, 105, 160, 260
};
static const u16 enGoldT[EN_TYPES] = {
    0, 14, 24, 20, 48, 26, 55, 44, 72, 80, 96, 70, 110,
    260, 420, 650, 900, 1200, 1500,
    26, 85, 38, 50, 78, 120
};

/* The Sleepers are slop that stopped moving, and they are named accordingly:
 * the same nonsense-Italian diminutives as everything else in this world,
 * because they came out of the same bucket. */
static const char *enemyNameOf(u8 t) {
    switch (t) {
    case EN_SNORFLY:
        return "RONFLINI MOSCHINI";
    case EN_PILLOWORM:
        return "CUSCINO PESANTE";
    case EN_DREAMBAT:
        return "PIPISTRELLO SOGNI";
    case EN_SANDMAN:
        return "SABBIONE SLOPPONE";
    case EN_MOTH:
        return "FARFALLINA NOTTE";
    case EN_LOG:
        return "TRONCO RONFONE";
    case EN_JELLY:
        return "MEDUSINI PISOLINI";
    case EN_HUSK:
        return "SALINO VUOTINI";
    case EN_DRONE:
        return "DRONI NINNANANNI";
    case EN_TURRET:
        return "CANNONE ZITTONE";
    case EN_WISP:
        return "LUCINA PISOLINA";
    case EN_MURMUR:
        return "MORMORINI SLOPPI";
    case EN_PATAPIM:
        return "BRR BRR PATAPIM";
    case EN_NGANTUK:
        return "TRIPPI TROPPI";
    case EN_SANDKING:
        return "SABBIONE IMPERATORE";
    case EN_CROCODILO:
        return "BOMBARDIRO CROCODILO";
    case EN_SILENZIO:
        return "IL SILENZIO";
    case EN_SILENZIO2:
        return "IL SILENZIO ASSOLUTO";
    case EN_CAPPU:
        return "CAPPUCCINO ASSASSINO";
    case EN_GUSINI:
        return "BOMBOMBINI GUSINI";
    case EN_AMBALABU:
        return "BONECA AMBALABU";
    case EN_OCTOPUS:
        return "BLUEBERRINNI OCTOPUS";
    case EN_GLORBO:
        return "GLORBO FRUTTODRILLO";
    default:
        return "VACCA SATURNITA";
    }
}

/* Bosses occupy one bounded run. Six 32x32 encounter designs were appended
 * after EN_SILENZIO2 so existing type ids would not change; a one-sided test
 * misclassified all six, uploaded 2KB from their 512-byte art blocks, and ran
 * their turns through bossAct. */
#define IS_BOSS_TYPE(t) ((t) >= EN_PATAPIM && (t) <= EN_SILENZIO2)

/* Which designs a region's random encounters draw from, weakest first. A
 * small party only ever rolls in the first half of its region's list; see
 * battleStartRandom. */
static const u8 regionPool[AREA_COUNT * 4] = {
    EN_SNORFLY,  EN_SNORFLY,   EN_SNORFLY,  EN_SNORFLY,     /* VILLAGE: safe */
    EN_SNORFLY,  EN_CAPPU,     EN_DREAMBAT, EN_PILLOWORM,   /* FIELDS   */
    EN_MOTH,     EN_AMBALABU,  EN_PILLOWORM, EN_LOG,        /* FOREST   */
    EN_JELLY,    EN_DREAMBAT,  EN_OCTOPUS,  EN_MOTH,        /* SHORE    */
    EN_HUSK,     EN_GLORBO,    EN_SANDMAN,  EN_JELLY,       /* SALT     */
    EN_DRONE,    EN_GUSINI,    EN_TURRET,   EN_HUSK,        /* FORTRESS */
    EN_WISP,     EN_MURMUR,    EN_SATURNO,  EN_DRONE        /* HUSH     */
};

static u8 regionEnemy(u8 area, u8 pick) {
    if (area >= AREA_COUNT)
        return EN_SNORFLY;
    return regionPool[(u16)area * 4 + (pick & 3)];
}

/* ---- battle state ------------------------------------------------------ */

#define BS_INTRO    0
#define BS_ACTIVE   1
#define BS_CMD      2
#define BS_SKILL    3
#define BS_ITEM     4
#define BS_TARGET   5
#define BS_EXEC     6
#define BS_WIN      8
#define BS_LOSE     9
#define BS_FLED    10

#define CMD_FIGHT  0
#define CMD_SKILL  1
#define CMD_ITEM   2
#define CMD_GUARD  3
#define CMD_RUN    4
#define CMD_COUNT  5

#define ACT_FIGHT   0
#define ACT_SKILL   1
#define ACT_ITEM    2
#define ACT_RUN     3
#define ACT_ENEMY   4
#define ACT_GUARD   5

static u8 bstate;
static u8 atb[CB_MAX];
static u8 sleepTimer[CB_MAX];
static u8 actor;
static u8 cmdIndex, subIndex, targetIndex;
static u8 targetIsAlly;
static u8 actKind, actParam, actUser, actTarget;
static u8 execPhase, execTimer;
static u8 hurtTimer[CB_MAX];
static u8 poseTimer[CB_MAX];
static u8 enSlot[ENEMY_MAX];    /* which scratch block each enemy draws from */
#define UPLOAD_MAX 4
static u8 uploadType[UPLOAD_MAX];
static u8 uploadCount;
static u16 winExp, winGold;
static u8 introTimer;
static u8 escapeTries;
static u8 bossPhase;
static u8 levelled;
static u8 battleArea, battleBackdrop;

#define POP_MAX 4
static u16 popVal[POP_MAX];
static u8 popX[POP_MAX], popY[POP_MAX], popTime[POP_MAX], popPal[POP_MAX];
static u8 popShown[POP_MAX];

static u8 lastBstate, lastMsg, lastActor, lastTarget, lastExec;
static u8 cursorX, cursorY, cursorShown;
static u16 shownHP[PARTY_MAX], shownMP[PARTY_MAX];
static u8 shownStatus[PARTY_MAX];
static u8 shownCmd, shownSub;
static u8 objUsed;

/* ---- small helpers ----------------------------------------------------- */

static u8 cbAlive(u8 i) {
    u8 e;

    if (IS_ENEMY(i)) {
        e = EN_OF(i);
        return (enType[e] != EN_NONE && enHP[e] > 0) ? 1 : 0;
    }
    if (i >= partyCount)
        return 0;
    return (pcStatus[i] & STAT_DEAD) ? 0 : 1;
}

static u8 cbStatus(u8 i) {
    return IS_ENEMY(i) ? enStatus[EN_OF(i)] : pcStatus[i];
}

static void cbSetStatus(u8 i, u8 flags) {
    if (IS_ENEMY(i))
        enStatus[EN_OF(i)] = flags;
    else
        pcStatus[i] = flags;
}

static u8 cbSpeed(u8 i) {
    return IS_ENEMY(i) ? enSpdT[enType[EN_OF(i)]] : pcSpd[i];
}

static u8 cbDef(u8 i) {
    u8 d;

    if (IS_ENEMY(i))
        return enDefT[enType[EN_OF(i)]];
    d = pcDef[i];
    if (pcStatus[i] & STAT_DEFEND)
        d = (u8)(d + (d >> 1));
    return d;
}

static u8 enemyCount(void) {
    u8 i, n;

    n = 0;
    for (i = 0; i < ENEMY_MAX; i++)
        if (enType[i] != EN_NONE && enHP[i] > 0)
            n++;
    return n;
}

static u8 firstLiveEnemy(void) {
    u8 i;

    for (i = CB_ENEMY0; i < CB_MAX; i++)
        if (cbAlive(i))
            return i;
    return CB_ENEMY0;
}

static u8 firstLiveAlly(void) {
    u8 i;

    for (i = 0; i < partyCount; i++)
        if (cbAlive(i))
            return i;
    return 0;
}

static u8 firstDeadAlly(void) {
    u8 i;

    for (i = 0; i < partyCount; i++)
        if (pcStatus[i] & STAT_DEAD)
            return i;
    return 255;
}

static void popAdd(u8 cb, u16 value, u8 pal) {
    u8 i, best;

    best = 0;
    for (i = 0; i < POP_MAX; i++) {
        if (popTime[i] == 0) {
            best = i;
            break;
        }
        if (popTime[i] < popTime[best])
            best = i;
    }
    popVal[best] = value;
    popPal[best] = pal;
    popTime[best] = 34;
    if (IS_ENEMY(cb)) {
        popX[best] = (u8)((battleIsBoss ? BOSS_X : enSlotX[EN_OF(cb)]) >> 3);
        popY[best] = (u8)((battleIsBoss ? BOSS_Y : enSlotY[EN_OF(cb)]) >> 3);
    } else {
        popX[best] = (u8)(pcSprX[cb] >> 3);
        popY[best] = (u8)(pcSprY[cb] >> 3);
    }
    if (popY[best] < 1)
        popY[best] = 1;
    if (popX[best] > 27)
        popX[best] = 27;
}

/* ---- damage ------------------------------------------------------------ */

static u16 physDamage(u8 atk, u8 def, u8 level) {
    s16 base, spread;

    base = (s16)atk * 3 + (s16)level - ((s16)def * 3) / 2;
    if (base < 2)
        base = 2;
    spread = base >> 3;
    if (spread > 0)
        base += (s16)(rand() % (u16)(spread * 2 + 1)) - spread;
    if (base < 1)
        base = 1;
    return (u16)base;
}

/* Enemies hit on a flatter curve than the party's. Run through physDamage, a
 * Sandman took a third of Lirili's bar per swing and a random encounter was a
 * coin toss; the target here is 10-20% of a bar.
 *
 * Bosses use the steeper term. On the flat one a level-10 Tung's defence had
 * outgrown Brr Brr Patapim entirely -- nine points a swing, from the thing the
 * whole act is about. */
static u16 enemyDamage2(u8 atk, u8 def, u8 boss) {
    s16 base, spread;

    base = boss ? ((s16)atk * 3 - (s16)def)
                : ((s16)atk * 2 - ((s16)def * 3) / 2);
    if (base < 3)
        base = 3;
    spread = base >> 3;
    if (spread > 0)
        base += (s16)(rand() % (u16)(spread * 2 + 1)) - spread;
    if (base < 1)
        base = 1;
    return (u16)base;
}

static u16 enemyDamage(u8 atk, u8 def) {
    return enemyDamage2(atk, def, 0);
}

static u16 magDamage(u8 power, u8 mag, u8 def) {
    s16 base, spread;

    base = (s16)power + (s16)mag * 2 - (s16)(def >> 1);
    if (base < 2)
        base = 2;
    spread = base >> 3;
    if (spread > 0)
        base += (s16)(rand() % (u16)(spread * 2 + 1)) - spread;
    if (base < 1)
        base = 1;
    return (u16)base;
}

static void dealDamage(u8 cb, u16 dmg) {
    u8 e;

    hurtTimer[cb] = 12;
    /* White over an enemy, red over one of ours -- FF's convention, and the
     * only thing that makes a screen with six numbers on it readable. */
    popAdd(cb, dmg, IS_ENEMY(cb) ? PAL_WIN : PAL_ALERT);

    if (IS_ENEMY(cb)) {
        e = EN_OF(cb);
        if (enHP[e] > dmg)
            enHP[e] -= dmg;
        else
            enHP[e] = 0;
    } else {
        if (pcHP[cb] > dmg) {
            pcHP[cb] -= dmg;
        } else {
            pcHP[cb] = 0;
            pcStatus[cb] |= STAT_DEAD;
            pcStatus[cb] &= (u8)~STAT_SLEEP;
        }
    }

    /* A hard enough knock wakes you. Not always -- otherwise SLEEP would be
     * worth nothing and SAHUR CALL would have no job. */
    if (cbStatus(cb) & STAT_SLEEP)
        if ((rand() & 3) == 0)
            cbSetStatus(cb, cbStatus(cb) & (u8)~STAT_SLEEP);
}

static void healTarget(u8 cb, u16 amount) {
    hurtTimer[cb] = 0;
    popAdd(cb, amount, PAL_GOOD);
    if (IS_ENEMY(cb))
        return;
    pcHP[cb] += amount;
    if (pcHP[cb] > pcHPMax[cb])
        pcHP[cb] = pcHPMax[cb];
}

/* Tung is never asleep.
 *
 * Not a difficulty concession -- the point of the character. Without it the
 * Hush's party-wide sleep is a loop with no exit: every gauge stops, the boss
 * keeps acting, and the one move in the game that answers being put to sleep
 * belongs to somebody who is asleep. With it, the drummer stays up and SAHUR
 * CALL is the reply, which is what the whole game has been saying. */
static void putToSleep(u8 who) {
    if (who == PC_TUNG)
        return;
    pcStatus[who] |= STAT_SLEEP;
}

static void wakeParty(void) {
    u8 i;

    for (i = 0; i < partyCount; i++)
        pcStatus[i] &= (u8)~STAT_SLEEP;
}

/* ---- enemy art streaming ----------------------------------------------- */

/* enemyArtOffset[] and the 32x32/64x64 split come from gen_sprites.py. A large
 * OBJ's rows are 16 names apart (A-4), so a 4x4 block is four transfers of
 * four characters and an 8x8 block is eight of eight. */
static void uploadEnemy(u8 type, u8 slot) {
    u8 *src;
    u16 dest;
    u8 r, rows;
    u16 bytes;

    src = (u8 *)&enemies_pic + enemyArtOffset[type];
    rows = IS_BOSS_TYPE(type) ? 8 : 4;
    bytes = IS_BOSS_TYPE(type) ? 256 : 128;
    dest = (u16)(VRAM_OBJ_SCRATCH + (u16)slot * 64);
    for (r = 0; r < rows; r++)
        dmaCopyVram(src + (u16)r * bytes, (u16)(dest + (u16)r * 256), bytes);
}

static u16 enemyName(u8 slot) {
    return (u16)(256 + (u16)slot * 4);
}

/* Called from enterState(ST_BATTLE), on the far side of the transition fade
 * and inside forced blank. Up to three designs, so at most 6KB. */
void battleUploadEnemies(void) {
    u8 i;

    for (i = 0; i < uploadCount; i++)
        uploadEnemy(uploadType[i], i);
}

/* ---- setting up a fight ------------------------------------------------ */

void battleSetRegion(u8 area, u8 backdrop) {
    battleArea = area;
    battleBackdrop = backdrop;
}

static void spawn(u8 slot, u8 type) {
    enType[slot] = type;
    enHP[slot] = enBaseHP[type];
    enStatus[slot] = 0;
}

static void battleBegin(void) {
    u8 i, distinct[UPLOAD_MAX], nd, t, s;

    for (i = 0; i < CB_MAX; i++) {
        /* A stagger at the start, so the party does not act in a block and
         * the enemies get a share of the first move. */
        atb[i] = (u8)(rand() & 63);
        hurtTimer[i] = 0;
        poseTimer[i] = 0;
        sleepTimer[i] = 0;
    }
    for (i = 0; i < POP_MAX; i++) {
        popTime[i] = 0;
        popShown[i] = 0;
    }
    for (i = 0; i < partyCount; i++)
        pcStatus[i] &= (u8)STAT_DEAD;   /* clear carried-over SLEEP/HASTE */

    /* Work out which designs this fight needs and which scratch block each
     * enemy will draw from. The transfer itself happens later, in
     * battleUploadEnemies -- battleStart is called from the field update, in
     * the middle of a visible frame, and VRAM is writable in forced blank or
     * V-blank only (ppu-graphics.md, "Access periods"). Uploading here wrote
     * nothing at all and every enemy came out invisible. */
    nd = 0;
    for (i = 0; i < ENEMY_MAX; i++) {
        if (enType[i] == EN_NONE)
            continue;
        t = enType[i];
        for (s = 0; s < nd; s++)
            if (distinct[s] == t)
                break;
        if (s == nd && nd < UPLOAD_MAX) {
            distinct[nd] = t;
            uploadType[nd] = t;
            nd++;
        }
        enSlot[i] = s < nd ? s : 0;
    }
    uploadCount = nd;

    winExp = 0;
    winGold = 0;
    escapeTries = 0;
    bossPhase = 0;
    levelled = 0;
    battleResult = BR_RUNNING;
    bstate = BS_INTRO;
    introTimer = 40;
    actor = 0;
    cmdIndex = 0;
    lastBstate = 255;
    lastMsg = 255;
    lastActor = 255;
    lastTarget = 255;
    lastExec = 255;
    cursorShown = 0;
    shownCmd = 0;
    shownSub = 0;
    objUsed = 16;
    for (i = 0; i < PARTY_MAX; i++)
        shownHP[i] = 0xFFFF;

    audioMusic(battleIsBoss
               ? (enType[0] >= EN_SILENZIO ? BGM_FINAL : BGM_BOSS)
               : BGM_BATTLE);
}

/* The encounter is sized to the party, not to the region.
 *
 * Tung walks out of the village alone and does not get a second character
 * until the end of act two, and a fixed two-to-four pack of forest enemies
 * simply killed him: one character, 130 HP, against four things that hit for
 * 28. Scaling both the count and how far up the region's pool the roll is
 * allowed to reach keeps the early road survivable without making the late
 * road trivial. Each region's three designs are listed weakest first. */
void battleStartRandom(void) {
    u8 i, n, span;

    for (i = 0; i < ENEMY_MAX; i++)
        enType[i] = EN_NONE;
    battleIsBoss = 0;

    n = (u8)(1 + rand() % (partyCount >= 4 ? 4 : partyCount + 1));
    if (n > 4)
        n = 4;
    span = (u8)(partyCount >= 3 ? 4 : 2);
    for (i = 0; i < n; i++)
        spawn(i, regionEnemy(battleArea, (u8)(rand() % span)));
    battleBegin();
}

void battleStartBoss(u8 type) {
    u8 i;

    for (i = 0; i < ENEMY_MAX; i++)
        enType[i] = EN_NONE;
    battleIsBoss = 1;
    spawn(0, type);
    battleBegin();
}

/* ---- menus ------------------------------------------------------------- */

static void openCommandFor(u8 who) {
    actor = who;
    cmdIndex = 0;
    bstate = BS_CMD;
}

static const char *cmdLabel(u8 i) {
    switch (i) {
    case CMD_FIGHT:
        return "FIGHT";
    case CMD_SKILL:
        return "SKILL";
    case CMD_ITEM:
        return "ITEM";
    case CMD_GUARD:
        return "GUARD";
    default:
        return "RUN";
    }
}

static void drawCommandWindow(void) {
    u8 i;

    winBox(CMD_X, CMD_Y, CMD_W, CMD_H);
    for (i = 0; i < CMD_COUNT; i++)
        textPut(CMD_X + 3, (u8)(CMD_Y + 2 + i), cmdLabel(i));
}

/* Five cells rewritten per frame: the selected one gets the hand, the rest get
 * back the window interior they sit on. Repainting the box to move a cursor is
 * what made this screen cost eight frames. */
static void drawCommandCursor(void) {
    u8 i;

    if (bstate != BS_CMD && bstate != BS_SKILL && bstate != BS_ITEM
        && bstate != BS_TARGET)
        return;
    if (shownCmd == cmdIndex + 1)
        return;
    shownCmd = (u8)(cmdIndex + 1);
    for (i = 0; i < CMD_COUNT; i++)
        textPutTile(CMD_X + 2, (u8)(CMD_Y + 2 + i),
                    (bstate == BS_CMD && i == cmdIndex)
                        ? ICON_CURSOR : winFillTile((u8)(2 + i), CMD_H),
                    TXT_ATTR);
}

#define SUB_W 17

static void drawSubWindow(void) {
    u8 n, i, top, sk;

    if (bstate == BS_SKILL) {
        n = partySkillCount(actor);
        top = (u8)(CMD_Y - n - 2);
        winBox(CMD_X, top, SUB_W, (u8)(n + 2));
        for (i = 0; i < n; i++) {
            sk = partySkillAt(actor, i);
            /* Grey out what cannot be paid for -- the alternative is finding
             * out only after pressing A. */
            textPutPal(CMD_X + 2, (u8)(top + 1 + i), skillNameOf(sk),
                       pcMP[actor] >= skillMP[sk] ? PAL_WIN : PAL_ALERT);
            textNum(CMD_X + 14, (u8)(top + 1 + i), skillMP[sk], 2);
        }
    } else if (bstate == BS_ITEM) {
        top = (u8)(CMD_Y - ITEM_COUNT - 2);
        winBox(CMD_X, top, SUB_W, ITEM_COUNT + 2);
        for (i = 0; i < ITEM_COUNT; i++) {
            textPutPal(CMD_X + 2, (u8)(top + 1 + i), itemNameOf(i),
                       itemCount[i] ? PAL_WIN : PAL_ALERT);
            textNum(CMD_X + 14, (u8)(top + 1 + i), itemCount[i], 2);
        }
    }
}

static void drawSubCursor(void) {
    u8 n, i, top;

    if (bstate == BS_SKILL) {
        n = partySkillCount(actor);
        top = (u8)(CMD_Y - n - 2);
    } else if (bstate == BS_ITEM) {
        n = ITEM_COUNT;
        top = (u8)(CMD_Y - ITEM_COUNT - 2);
    } else {
        return;
    }
    if (shownSub == subIndex + 1)
        return;
    shownSub = (u8)(subIndex + 1);
    for (i = 0; i < n; i++)
        textPutTile(CMD_X + 1, (u8)(top + 1 + i),
                    i == subIndex ? ICON_CURSOR
                                  : winFillTile((u8)(1 + i), (u8)(n + 2)),
                    TXT_ATTR);
}

/* ---- target selection -------------------------------------------------- */

static void targetNext(s8 dir) {
    u8 i, start, e;

    start = targetIndex;
    for (i = 0; i < CB_MAX; i++) {
        if (targetIsAlly) {
            targetIndex = (u8)((targetIndex + (dir > 0 ? 1 : partyCount - 1))
                               % partyCount);
        } else {
            e = EN_OF(targetIndex);
            e = (u8)((e + (dir > 0 ? 1 : ENEMY_MAX - 1)) % ENEMY_MAX);
            targetIndex = (u8)(CB_ENEMY0 + e);
        }
        if (targetIsAlly && actKind == ACT_ITEM && actParam == ITEM_ELIXIR) {
            if (pcStatus[targetIndex] & STAT_DEAD)
                return;
        } else if (cbAlive(targetIndex)) {
            return;
        }
    }
    targetIndex = start;
}

static void beginExec(void) {
    bstate = BS_EXEC;
    execPhase = 0;
    execTimer = 0;
}

static void beginTarget(u8 kind, u8 param) {
    u8 k;

    actKind = kind;
    actParam = param;
    actUser = actor;

    if (kind == ACT_FIGHT) {
        targetIsAlly = 0;
    } else if (kind == ACT_SKILL) {
        k = skillKind[param];
        if (k == SK_HEAL_ONE) {
            targetIsAlly = 1;
        } else if (k == SK_HEAL_ALL || k == SK_MAGIC_ALL || k == SK_HASTE_SELF
                   || k == SK_GUARD_ALL) {
            actTarget = actor;
            beginExec();
            return;
        } else {
            targetIsAlly = 0;
        }
    } else {                    /* ACT_ITEM */
        if (!itemTargetsAlly(param)) {
            actTarget = firstLiveEnemy();
            beginExec();
            return;
        }
        targetIsAlly = 1;
    }

    targetIndex = targetIsAlly ? firstLiveAlly() : firstLiveEnemy();
    if (kind == ACT_ITEM && param == ITEM_ELIXIR) {
        /* The one item that wants a dead ally. Using the ordinary live-target
         * predicate made every fallen member except slot zero impossible to
         * select, and consumed the item as a full heal when slot zero lived. */
        targetIndex = firstDeadAlly();
        if (targetIndex == 255) {
            audioSfx(SFX_ERROR);
            bstate = BS_ITEM;
            return;
        }
    }
    bstate = BS_TARGET;
}

/* ---- executing --------------------------------------------------------- */

static void beginMessage(const char *s) {
    msgOpenAt(s, MSG_Y);
}

static void execFight(void) {
    u16 dmg;
    u8 crit;

    if (!cbAlive(actTarget))
        actTarget = firstLiveEnemy();

    crit = ((rand() & 15) == 0) ? 1 : 0;
    dmg = physDamage(pcAtk[actUser], cbDef(actTarget), pcLevel[actUser]);
    if (crit)
        dmg <<= 1;
    dealDamage(actTarget, dmg);
    poseTimer[actUser] = 18;
    audioSfx(SFX_HIT);
    ppuShake(crit ? 8 : 4);
}

static void execSkill(void) {
    u8 kind, power, i, hits;
    u16 dmg;

    kind = skillKind[actParam];
    power = skillPower[actParam];
    poseTimer[actUser] = 20;

    switch (kind) {
    case SK_PHYS_ONE:
        if (!cbAlive(actTarget))
            actTarget = firstLiveEnemy();
        /* power is a percentage bonus on the finished number, not a bonus to
         * the attack stat. Added to the stat it goes through the x3 in
         * physDamage as well, and BAT SMASH came out at four times a normal
         * swing for five MP. */
        dmg = physDamage(pcAtk[actUser], cbDef(actTarget), pcLevel[actUser]);
        dmg = (u16)((dmg * (100 + power)) / 100);
        dealDamage(actTarget, dmg);
        audioSfx(SFX_HIT);
        ppuShake(10);
        break;

    case SK_PHYS_TRIPLE:
        hits = 3;
        for (i = 0; i < hits; i++) {
            if (!cbAlive(actTarget))
                actTarget = firstLiveEnemy();
            if (!cbAlive(actTarget))
                break;
            dmg = physDamage(pcAtk[actUser], cbDef(actTarget),
                             pcLevel[actUser]);
            dmg = (u16)((dmg * (100 + power)) / 100);
            dealDamage(actTarget, dmg);
        }
        audioSfx(SFX_HIT);
        ppuShake(8);
        break;

    case SK_MAGIC_ONE:
        if (!cbAlive(actTarget))
            actTarget = firstLiveEnemy();
        dmg = magDamage(power, pcMag[actUser], cbDef(actTarget));
        dealDamage(actTarget, dmg);
        audioSfx(SFX_MAGIC);
        ppuFlash(10);
        break;

    case SK_MAGIC_ALL:
        for (i = CB_ENEMY0; i < CB_MAX; i++) {
            if (!cbAlive(i))
                continue;
            dmg = magDamage(power, pcMag[actUser], cbDef(i));
            dealDamage(i, dmg);
        }
        /* SAHUR CALL is the drum: it wakes the party as it lands. */
        if (actParam == SKILL_SAHUR) {
            wakeParty();
            audioSfx(SFX_DRUM);
        } else {
            audioSfx(SFX_MAGIC);
        }
        ppuFlash(14);
        ppuShake(14);
        break;

    case SK_HEAL_ONE:
        if (!cbAlive(actTarget))
            actTarget = firstLiveAlly();
        healTarget(actTarget, (u16)power + pcMag[actUser]);
        audioSfx(SFX_HEAL);
        break;

    case SK_HEAL_ALL:
        for (i = 0; i < partyCount; i++)
            if (cbAlive(i))
                healTarget(i, (u16)power + pcMag[actUser]);
        audioSfx(SFX_HEAL);
        break;

    case SK_HASTE_SELF:
        pcStatus[actUser] |= STAT_HASTE;
        pcStatus[actUser] &= (u8)~STAT_SLOW;
        audioSfx(SFX_MAGIC);
        break;

    case SK_GUARD_ALL:
        for (i = 0; i < partyCount; i++)
            if (cbAlive(i))
                pcStatus[i] |= STAT_DEFEND;
        audioSfx(SFX_HEAL);
        break;

    default:                    /* SK_SLOW_ONE */
        if (!cbAlive(actTarget))
            actTarget = firstLiveEnemy();
        cbSetStatus(actTarget, cbStatus(actTarget) | STAT_SLOW);
        audioSfx(SFX_MAGIC);
        break;
    }

    pcMP[actUser] -= skillMP[actParam];
}

static void execItem(void) {
    u8 i;

    itemCount[actParam]--;
    switch (actParam) {
    case ITEM_HERB:
        healTarget(actTarget, 90);
        audioSfx(SFX_HEAL);
        break;
    case ITEM_SALVE:
        healTarget(actTarget, 320);
        audioSfx(SFX_HEAL);
        break;
    case ITEM_COFFEE:
        pcStatus[actTarget] &= (u8)~STAT_SLEEP;
        healTarget(actTarget, 40);
        audioSfx(SFX_HEAL);
        break;
    case ITEM_TONIC:
        pcMP[actTarget] += 40;
        if (pcMP[actTarget] > pcMPMax[actTarget])
            pcMP[actTarget] = pcMPMax[actTarget];
        audioSfx(SFX_HEAL);
        break;
    case ITEM_BOMB:
    case ITEM_THUNDER:
        for (i = CB_ENEMY0; i < CB_MAX; i++)
            if (cbAlive(i))
                dealDamage(i, actParam == ITEM_BOMB ? 80 : 170);
        audioSfx(SFX_MAGIC);
        ppuFlash(12);
        ppuShake(12);
        break;
    case ITEM_TEA:
        for (i = 0; i < partyCount; i++) {
            pcStatus[i] &= (u8)~(STAT_SLEEP | STAT_POISON);
            if (cbAlive(i))
                healTarget(i, pcHPMax[i]);
        }
        audioSfx(SFX_DRUM);
        break;
    default:                    /* ELIXIR */
        pcStatus[actTarget] &= (u8)~STAT_DEAD;
        pcHP[actTarget] = pcHPMax[actTarget] >> 1;
        popAdd(actTarget, pcHP[actTarget], PAL_GOOD);
        audioSfx(SFX_HEAL);
        break;
    }
}

/* ---- enemy turns ------------------------------------------------------- */

static void bossAct(u8 cb, u8 type) {
    u8 i, victim;
    u16 dmg;

    victim = firstLiveAlly();
    for (i = 0; i < 8; i++) {
        u8 t = (u8)(rand() % partyCount);
        if (cbAlive(t)) {
            victim = t;
            break;
        }
    }
    bossPhase++;

    switch (type) {
    case EN_PATAPIM:
        if ((bossPhase % 4) == 0) {
            beginMessage("PATAPIM plants all three feet. The road stops "
                         "being a road. BRR.");
            for (i = 0; i < partyCount; i++)
                if (cbAlive(i))
                    dealDamage(i, enemyDamage2(enAtkT[type], pcDef[i], 1));
            ppuShake(18);
            audioSfx(SFX_HIT);
            return;
        }
        break;

    case EN_NGANTUK:
        if ((bossPhase % 3) == 0) {
            beginMessage("TRIPPI TROPPI yawns. The whole bay yawns with it.");
            for (i = 0; i < partyCount; i++)
                if (cbAlive(i) && (rand() & 1))
                    putToSleep(i);
            audioSfx(SFX_MAGIC);
            return;
        }
        break;

    case EN_SANDKING:
        if ((bossPhase % 4) == 0) {
            beginMessage("SABBIONE IMPERATORE pours an entire hour over the "
                         "party. Mamma mia.");
            for (i = 0; i < partyCount; i++)
                if (cbAlive(i)) {
                    pcStatus[i] |= STAT_SLOW;
                    dealDamage(i, magDamage(38, enAtkT[type], pcDef[i]));
                }
            ppuFlash(14);
            audioSfx(SFX_MAGIC);
            return;
        }
        break;

    case EN_CROCODILO:
        if ((bossPhase % 5) == 0) {
            beginMessage("BOMBARDIRO CROCODILO OPENS THE BAY.");
            for (i = 0; i < partyCount; i++)
                if (cbAlive(i))
                    dealDamage(i, magDamage(50, enAtkT[type], pcDef[i]));
            ppuFlash(16);
            ppuShake(20);
            audioSfx(SFX_MAGIC);
            return;
        }
        if ((bossPhase % 3) == 0) {
            beginMessage("BOMBARDIRO drones a lullaby. Badly. Very loudly.");
            for (i = 0; i < partyCount; i++)
                if (cbAlive(i) && (rand() & 1))
                    putToSleep(i);
            audioSfx(SFX_MAGIC);
            return;
        }
        break;

    default:                    /* IL SILENZIO, both shapes */
        if ((bossPhase % 4) == 0) {
            beginMessage("IL SILENZIO: \"Rest. Just scroll. I insist.\"");
            for (i = 0; i < partyCount; i++)
                if (cbAlive(i))
                    putToSleep(i);
            audioSfx(SFX_MAGIC);
            ppuFlash(20);
            return;
        }
        if ((bossPhase % 3) == 0) {
            beginMessage("The feed closes over everyone at once. So smooth. "
                         "So comfortable.");
            for (i = 0; i < partyCount; i++)
                if (cbAlive(i))
                    dealDamage(i, magDamage(56, enAtkT[type], pcDef[i]));
            ppuFlash(18);
            ppuShake(16);
            return;
        }
        break;
    }

    dmg = enemyDamage2(enAtkT[type], cbDef(victim), 1);
    dealDamage(victim, dmg);
    audioSfx(SFX_HIT);
    ppuShake(8);
}

static void enemyAct(u8 cb) {
    u8 e, type, victim, i;
    u16 dmg;

    e = EN_OF(cb);
    type = enType[e];
    poseTimer[cb] = 16;

    if (IS_BOSS_TYPE(type)) {
        bossAct(cb, type);
        return;
    }

    victim = firstLiveAlly();
    /* A random living target rather than always the first: being able to
     * predict who gets hit removes most of the reason to heal. */
    for (i = 0; i < 8; i++) {
        u8 t = (u8)(rand() % partyCount);
        if (cbAlive(t)) {
            victim = t;
            break;
        }
    }

    if ((type == EN_SANDMAN || type == EN_WISP || type == EN_MURMUR)
        && (rand() % 100) < 38) {
        beginMessage(type == EN_SANDMAN
                     ? "SABBIONE SLOPPONE throws a handful of night."
                     : "A drowsiness arrives from nowhere in particular, "
                       "fully formed.");
        if (cbAlive(victim))
            putToSleep(victim);
        audioSfx(SFX_MAGIC);
        return;
    }

    dmg = enemyDamage(enAtkT[type], cbDef(victim));
    dealDamage(victim, dmg);
    audioSfx(SFX_HIT);
    ppuShake(3);
}

/* ---- end conditions ---------------------------------------------------- */

static void tallyRewards(void) {
    u8 i;

    winExp = 0;
    winGold = 0;
    for (i = 0; i < ENEMY_MAX; i++) {
        if (enType[i] == EN_NONE)
            continue;
        winExp += enExpT[enType[i]];
        winGold += enGoldT[enType[i]];
    }
}

static u8 checkEnd(void) {
    u8 i;

    if (enemyCount() == 0) {
        /* Il Silenzio stands up a second time. The first shape pleads; this
         * one does not. */
        if (battleIsBoss && enType[0] == EN_SILENZIO) {
            for (i = 0; i < ENEMY_MAX; i++)
                enType[i] = EN_NONE;
            spawn(0, EN_SILENZIO2);
            /* Mid-battle, so this one has to make its own window: forced
             * blank for the length of the transfer. It is 2KB and the screen
             * is white from the flash anyway. */
            ppuHdmaSuspend();
            REG_INIDISP = 0x80;
            uploadEnemy(EN_SILENZIO2, 0);
            ppuSetBattleMode();
            enSlot[0] = 0;
            bossPhase = 0;
            beginMessage("The shape does not fall. It straightens, and stops "
                         "being polite about any of this.");
            ppuFlash(24);
            ppuShake(24);
            bstate = BS_EXEC;
            execPhase = 1;
            execTimer = 0;
            return 1;
        }
        tallyRewards();
        gold += winGold;
        bstate = BS_WIN;
        execPhase = 0;
        audioMusic(BGM_FANFARE);
        textClear();
        beginMessage(battleIsBoss ? "It stops."
                                  : "The slop wakes up and legs it.");
        return 1;
    }
    if (partyAlive() == 0) {
        bstate = BS_LOSE;
        audioStop();
        textClear();
        beginMessage("Dawn came. Nobody was awake to see it. "
                     "Very smooth. Very comfortable.");
        return 1;
    }
    return 0;
}

/* ---- the ATB tick ------------------------------------------------------ */

static void tickGauges(void) {
    u8 i, rate, st;

    for (i = 0; i < CB_MAX; i++) {
        if (!cbAlive(i)) {
            atb[i] = 0;
            continue;
        }
        st = cbStatus(i);
        if (st & STAT_SLEEP) {
            /* Sleep does not tick, but it does time out: an unbreakable sleep
             * on the whole party is a soft lock, not a mechanic. */
            atb[i] = 0;
            sleepTimer[i]++;
            if (sleepTimer[i] > 200) {
                sleepTimer[i] = 0;
                cbSetStatus(i, st & (u8)~STAT_SLEEP);
            }
            continue;
        }
        sleepTimer[i] = 0;

        rate = (u8)((cbSpeed(i) >> 1) + 2);
        if (st & STAT_HASTE)
            rate <<= 1;
        if (st & STAT_SLOW)
            rate >>= 1;
        if (rate == 0)
            rate = 1;

        if (atb[i] < 255 - rate)
            atb[i] += rate;
        else
            atb[i] = 255;
    }
}

/* Enemies act the moment their gauge fills. The party queues instead: only one
 * command window can be open, so a second ready character waits with a full
 * gauge, which is exactly FF4's behaviour. */
static u8 serviceReady(void) {
    u8 i;

    for (i = CB_ENEMY0; i < CB_MAX; i++) {
        if (cbAlive(i) && atb[i] == 255) {
            atb[i] = 0;
            actKind = ACT_ENEMY;
            actUser = i;
            beginExec();
            return 1;
        }
    }
    for (i = 0; i < partyCount; i++) {
        if (cbAlive(i) && atb[i] == 255 && !(pcStatus[i] & STAT_SLEEP)) {
            /* A turn coming round clears the guard put up on the last one. */
            pcStatus[i] &= (u8)~STAT_DEFEND;
            openCommandFor(i);
            return 1;
        }
    }
    return 0;
}

/* ---- update ------------------------------------------------------------ */

static void updateMenus(void) {
    u16 t;
    u8 n, sk;

    t = inputRepeat(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT);

    switch (bstate) {
    case BS_CMD:
        if (t & KEY_UP) {
            cmdIndex = (u8)((cmdIndex + CMD_COUNT - 1) % CMD_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            cmdIndex = (u8)((cmdIndex + 1) % CMD_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_A) {
            audioSfx(SFX_CONFIRM);
            subIndex = 0;
            switch (cmdIndex) {
            case CMD_FIGHT:
                beginTarget(ACT_FIGHT, 0);
                break;
            case CMD_SKILL:
                bstate = BS_SKILL;
                break;
            case CMD_ITEM:
                bstate = BS_ITEM;
                break;
            case CMD_GUARD:
                actKind = ACT_GUARD;
                actUser = actor;
                beginExec();
                break;
            default:
                actKind = ACT_RUN;
                actUser = actor;
                beginExec();
                break;
            }
        }
        break;

    case BS_SKILL:
        n = partySkillCount(actor);
        if (t & KEY_UP) {
            subIndex = (u8)((subIndex + n - 1) % n);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            subIndex = (u8)((subIndex + 1) % n);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            bstate = BS_CMD;
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_A) {
            sk = partySkillAt(actor, subIndex);
            if (pcMP[actor] < skillMP[sk]) {
                audioSfx(SFX_ERROR);
            } else {
                audioSfx(SFX_CONFIRM);
                beginTarget(ACT_SKILL, sk);
            }
        }
        break;

    case BS_ITEM:
        if (t & KEY_UP) {
            subIndex = (u8)((subIndex + ITEM_COUNT - 1) % ITEM_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            subIndex = (u8)((subIndex + 1) % ITEM_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            bstate = BS_CMD;
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_A) {
            if (itemCount[subIndex] == 0) {
                audioSfx(SFX_ERROR);
            } else {
                audioSfx(SFX_CONFIRM);
                beginTarget(ACT_ITEM, subIndex);
            }
        }
        break;

    default:                    /* BS_TARGET */
        if (t & (KEY_UP | KEY_LEFT)) {
            targetNext(-1);
            audioSfx(SFX_CURSOR);
        }
        if (t & (KEY_DOWN | KEY_RIGHT)) {
            targetNext(1);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            bstate = BS_CMD;
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_A) {
            audioSfx(SFX_CONFIRM);
            actTarget = targetIndex;
            beginExec();
        }
        break;
    }
}

static void updateExec(void) {
    if (execPhase == 0) {
        /* A beat before anything resolves, so the pose starts before the
         * number arrives. */
        execTimer++;
        if (execTimer < 6)
            return;
        execTimer = 0;
        execPhase = 1;

        switch (actKind) {
        case ACT_FIGHT:
            execFight();
            break;
        case ACT_SKILL:
            execSkill();
            break;
        case ACT_ITEM:
            execItem();
            break;
        case ACT_GUARD:
            pcStatus[actUser] |= STAT_DEFEND;
            audioSfx(SFX_CONFIRM);
            break;
        case ACT_ENEMY:
            enemyAct(actUser);
            break;
        default:                /* ACT_RUN */
            escapeTries++;
            if (battleIsBoss) {
                beginMessage("There is nowhere behind you. There is nowhere "
                             "anywhere. Andiamo.");
            } else if ((rand() % 100) < 40 + escapeTries * 20) {
                battleResult = BR_FLED;
                bstate = BS_FLED;
                return;
            } else {
                beginMessage("Cut off! Porca miseria.");
            }
            break;
        }

        if (actKind != ACT_ENEMY)
            atb[actUser] = 0;
        return;
    }

    if (msgActive) {
        msgUpdate();
        return;
    }
    execTimer++;
    if (execTimer < 22)
        return;

    if (checkEnd())
        return;
    bstate = BS_ACTIVE;
}

void battleUpdate(void) {
    u8 i;

    for (i = 0; i < POP_MAX; i++)
        if (popTime[i])
            popTime[i]--;
    for (i = 0; i < CB_MAX; i++) {
        if (hurtTimer[i])
            hurtTimer[i]--;
        if (poseTimer[i])
            poseTimer[i]--;
    }

    switch (bstate) {
    case BS_INTRO:
        if (introTimer) {
            introTimer--;
            return;
        }
        bstate = BS_ACTIVE;
        break;

    case BS_ACTIVE:
        tickGauges();
        if (!serviceReady())
            if (checkEnd())
                return;
        break;

    case BS_CMD:
    case BS_SKILL:
    case BS_ITEM:
    case BS_TARGET:
        /* Gauges keep filling while a menu is open -- that is the whole point
         * of an active-time battle. */
        tickGauges();
        updateMenus();
        break;

    case BS_EXEC:
        updateExec();
        break;

    case BS_WIN:
        if (msgUpdate())
            return;
        if (execPhase < 20) {
            execPhase = 20;
            levelled = partyGainExp(winExp);
            return;             /* the spoils box is drawn by drawLayout */
        }
        if (execPhase == 20) {
            if (!(padTrig & (KEY_A | KEY_B | KEY_START)))
                return;
            execPhase = 21;
            if (levelled)
                beginMessage("Level up! The drum sounds deeper. Bellissimo.");
            return;
        }
        battleResult = BR_WIN;
        if (battleIsBoss) {
            requestState(ST_FIELD);
            storyBossWon();
        } else {
            requestState(ST_FIELD);
        }
        break;

    case BS_LOSE:
        if (msgUpdate())
            return;
        battleResult = BR_LOSE;
        requestState(ST_GAMEOVER);
        break;

    default:                    /* BS_FLED */
        requestState(ST_FIELD);
        break;
    }
}

/* ---- drawing ----------------------------------------------------------- */

static void drawStatusFrame(void) {
    u8 i;

    winBox(STA_X, STA_Y, STA_W, STA_H);
    for (i = 0; i < partyCount; i++)
        textPut(STA_NAME_X, (u8)STA_ROW(i), partyNameOf(i));
}

/* HP, MP, the status icon and the gauge -- about forty tile writes a frame,
 * against the ~1400 a full repaint costs. */
static void drawStatusValues(void) {
    u8 i, row;

    for (i = 0; i < partyCount; i++) {
        row = (u8)STA_ROW(i);
        textGauge(STA_GAUGE_X, row, 3, atb[i], 255, PAL_WIN);

        if (pcHP[i] == shownHP[i] && pcMP[i] == shownMP[i]
            && pcStatus[i] == shownStatus[i])
            continue;
        shownHP[i] = pcHP[i];
        shownMP[i] = pcMP[i];
        shownStatus[i] = pcStatus[i];

        if (pcStatus[i] & STAT_DEAD) {
            textPutTile(STA_NAME_X + 7, row, ICON_DEAD, TXT_ATTR);
            textPut(STA_HP_X, row, "----");
        } else {
            if (pcStatus[i] & STAT_SLEEP)
                textPutTile(STA_NAME_X + 7, row, ICON_SLEEP, TXT_ATTR);
            else if (pcStatus[i] & STAT_HASTE)
                textPutTile(STA_NAME_X + 7, row, ICON_HASTE, TXT_ATTR);
            else if (pcStatus[i] & STAT_SLOW)
                textPutTile(STA_NAME_X + 7, row, ICON_SLOW, TXT_ATTR);
            else if (pcStatus[i] & STAT_DEFEND)
                textPutTile(STA_NAME_X + 7, row, ICON_DRUM, TXT_ATTR);
            else
                textPutTile(STA_NAME_X + 7, row,
                            winFillTile((u8)(row - STA_Y), STA_H), TXT_ATTR);

            /* Red once a quarter is left, which is the only warning the player
             * gets that a heal is overdue. */
            textNumPal(STA_HP_X, row, pcHP[i], 4,
                       (pcHP[i] * 4 <= pcHPMax[i]) ? PAL_ALERT : PAL_WIN);
        }
        textNum(STA_MP_X, row, pcMP[i], 3);
    }
}

static void drawPops(void) {
    u8 i, row;

    for (i = 0; i < POP_MAX; i++) {
        if (popTime[i] == 0) {
            if (popShown[i]) {
                textFill(popX[i], (u8)(popY[i] - 1), 4, 2, 0);
                popShown[i] = 0;
            }
            continue;
        }
        row = (u8)(popY[i] - (popTime[i] > 17 ? 0 : 1));
        if (popShown[i] == row + 1)
            continue;
        textFill(popX[i], (u8)(popY[i] - 1), 4, 2, 0);
        textNumPal(popX[i], row, popVal[i], 4, popPal[i]);
        popShown[i] = (u8)(row + 1);
    }
}

static void targetCell(u8 *tx, u8 *ty) {
    if (targetIsAlly) {
        *tx = (u8)((pcSprX[targetIndex] - 12) >> 3);
        *ty = (u8)((pcSprY[targetIndex] + 12) >> 3);
    } else if (battleIsBoss) {
        *tx = (u8)((BOSS_X + 66) >> 3);
        *ty = (u8)((BOSS_Y + 28) >> 3);
    } else {
        *tx = (u8)((enSlotX[EN_OF(targetIndex)] + 34) >> 3);
        *ty = (u8)((enSlotY[EN_OF(targetIndex)] + 12) >> 3);
    }
}

static void drawTargetName(void) {
    if (bstate != BS_TARGET || targetIsAlly)
        return;
    /* Wide enough for BOMBARDIRO CROCODILO and IL SILENZIO ASSOLUTO, which
     * are the two longest things in the game. */
    winBox(4, 0, 24, 3);
    textPut(5, 1, enemyNameOf(enType[EN_OF(targetIndex)]));
}

static void drawTargetCursor(void) {
    u8 tx, ty;

    if (bstate != BS_TARGET) {
        if (cursorShown) {
            textPutTile(cursorX, cursorY, 0, TXT_ATTR);
            cursorShown = 0;
        }
        return;
    }

    targetCell(&tx, &ty);
    if (cursorShown && (tx != cursorX || ty != cursorY))
        textPutTile(cursorX, cursorY, 0, TXT_ATTR);

    if (frameCounter & 8)
        textPutTile(tx, ty, ICON_CURSOR, TXT_ATTR);
    else
        textPutTile(tx, ty, 0, TXT_ATTR);
    cursorX = tx;
    cursorY = ty;
    cursorShown = 1;
}

/* Which windows are on screen is a function of (bstate, actor, msgActive,
 * target) and nothing else, so frames and labels are repainted only when one
 * of those changes. Everything that moves every frame goes through the
 * volatile path.
 *
 * This split is not a micro-optimisation. Repainting the layer wholesale was
 * ~1400 tile writes plus a 1024-iteration clear, and the 65816 got through it
 * about once every eight frames: the ATB crawled, and a one-frame padsDown
 * pulse was missed seven times out of eight. */
static void drawLayout(void) {
    textClear();
    drawStatusFrame();
    if (bstate == BS_CMD || bstate == BS_SKILL || bstate == BS_ITEM
        || bstate == BS_TARGET) {
        drawCommandWindow();
        drawSubWindow();
    }
    drawTargetName();
    if (bstate == BS_WIN && execPhase >= 20) {
        winBox(8, 8, 16, 6);
        textPut(10, 10, "EXP");
        textNum(17, 10, winExp, 5);
        textPut(10, 11, "GOLD");
        textNum(17, 11, winGold, 5);
    }
    if (msgActive) {
        winBox(1, MSG_Y, 30, 5);
        msgRepaint();
    }
}

void battleDraw(void) {
    u8 i, e, obj, pose;
    u16 name;
    s16 x, y;

    e = (u8)(bstate == BS_WIN ? execPhase : 0);
    if (bstate != lastBstate || msgActive != lastMsg || actor != lastActor
        || targetIndex != lastTarget || e != lastExec) {
        lastExec = e;
        lastBstate = bstate;
        lastMsg = msgActive;
        lastActor = actor;
        lastTarget = targetIndex;
        cursorShown = 0;
        for (i = 0; i < POP_MAX; i++)
            popShown[i] = 0;
        for (i = 0; i < PARTY_MAX; i++)
            shownHP[i] = 0xFFFF;
        shownCmd = 0;
        shownSub = 0;
        drawLayout();
    }

    drawStatusValues();
    drawCommandCursor();
    drawSubCursor();
    drawTargetCursor();
    drawPops();

    /* --- sprites --------------------------------------------------------- */
    obj = 0;

    for (i = 0; i < partyCount; i++) {
        if (!cbAlive(i))
            continue;
        if (hurtTimer[i] && (hurtTimer[i] & 2))
            continue;

        pose = poseTimer[i] ? 1 : 0;
        name = (u16)(sprPartyName[i * 2 + pose]);

        x = pcSprX[i];
        y = pcSprY[i];
        if (poseTimer[i])
            x -= 10;            /* step into the swing */
        if (pcStatus[i] & STAT_SLEEP)
            y += 4;
        /* A slow idle bob, out of phase per character, so a waiting party is
         * not five statues. */
        else if (((frameCounter >> 4) + i) & 1)
            y -= 1;

        oamSet((u16)(obj << 2), (u16)x, (u16)y, 2, 0, 0, name, sprPartyPal[i]);
        oamSetEx((u16)(obj << 2), OBJ_SMALL, OBJ_SHOW);
        obj++;
    }

    for (e = 0; e < ENEMY_MAX; e++) {
        if (enType[e] == EN_NONE || enHP[e] == 0)
            continue;
        i = (u8)(CB_ENEMY0 + e);
        if (hurtTimer[i] && (hurtTimer[i] & 2))
            continue;

        if (battleIsBoss) {
            x = BOSS_X;
            y = BOSS_Y;
        } else {
            x = enSlotX[e];
            y = enSlotY[e];
        }
        if (poseTimer[i])
            x += 8;

        /* Each design brings its own palette: the shared Sleeper purple is
         * right for a pilloworm and wrong for a mossy tree the size of the
         * road. */
        oamSet((u16)(obj << 2), (u16)x, (u16)y, 2, 0, 0,
               enemyName(enSlot[e]), enemyPal[enType[e]]);
        oamSetEx((u16)(obj << 2), battleIsBoss ? OBJ_LARGE : OBJ_SMALL,
                 OBJ_SHOW);
        obj++;
    }

    /* Park only what was in use and no longer is. An OBJ left at a stale
     * position still counts against the 32-per-line limit (Range Over) even
     * when hidden behind a window -- but re-parking all sixteen slots every
     * frame was pure waste, and tcc pushes eight arguments for each call. */
    while (obj < objUsed) {
        oamSet((u16)(obj << 2), 0, OAM_PARK_Y, 2, 0, 0, 0, 0);
        oamSetEx((u16)(obj << 2), OBJ_SMALL, OBJ_HIDE);
        obj++;
    }
    objUsed = obj;
}
