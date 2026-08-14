/*
 * TUNG TUNG SAHUR -- the overworld: seven regions, and moving between them.
 *
 * Movement is cell-based with interpolation: the hero is only ever *at* a
 * 16-dot cell, and a step is 8 frames of 2 dots. Collision, encounters and
 * events are then all one array lookup at the destination cell, evaluated once
 * per step rather than per frame -- cheaper, and impossible to get subtly
 * wrong at a cell boundary.
 *
 * ---- regions ---------------------------------------------------------------
 *
 * One region is resident at a time. Changing region is 17KB of tileset, tilemap
 * and palette under forced blank, which is why it happens on the far side of a
 * fade: VRAM is writable in forced blank or V-blank only (ppu-graphics.md,
 * "Access periods"), and 17KB is some six milliseconds -- four V-blanks.
 *
 * ---- events ----------------------------------------------------------------
 *
 * The collision byte's high nibble is an event id, 1-15, meaningful per region.
 * Exits are ids 1-4 and their destinations live in generated tables; everything
 * else is dispatched by (region, id) in story.c. Packing the id into the
 * collision byte keeps the per-step lookup a single read.
 */
#include "ttrpg.h"
#include "worldmap.h"
#include "sprmap.h"

#define CELL      16
#define STEP_PX   2
#define STEP_FRAMES (CELL / STEP_PX)

#define WORLD_PX  (MAP_W * CELL)
#define CAM_MAX_X (WORLD_PX - SCR_W)
#define CAM_MAX_Y (WORLD_PX - SCR_H)

#define DIR_DOWN  0
#define DIR_UP    1
#define DIR_LEFT  2
#define DIR_RIGHT 3

/* heroX, heroY, curArea, pendingArea/X/Y live in globals.c. */

static u8 heroDir;
static u8 stepLeft;
static u8 walkFrame;
static u8 animTimer;
static u8 stepCount;
static u8 encounterAt;
static u8 *colPtr;

u8 fieldCollision(u8 mx, u8 my) {
    if (mx >= MAP_W || my >= MAP_H)
        return COL_BLOCK;
    return colPtr[(u16)my * MAP_W + mx];
}

static void armEncounter(void) {
    /* 14..37 steps. Long enough to cross a region between fights, short enough
     * that the road being safe ground is worth something. */
    encounterAt = 14 + (u8)(rand() & 23);
    stepCount = 0;
}

/* ---- region loading ---------------------------------------------------- */

void fieldLoadArea(u8 area, u8 mx, u8 my) {
    curArea = area;
    heroX = (u16)mx * CELL;
    heroY = (u16)my * CELL;
    stepLeft = 0;
    walkFrame = 0;
    animTimer = 0;
    colPtr = areaCol(area);
    armEncounter();
    /* Before the transfer below, so npcAt() is answering about this region
     * and not the last one if anything asks between here and the first
     * fieldUpdate. */
    npcInit(area);

    /* Forced blank: 16KB of tileset and tilemap is far past a V-blank window,
     * and this is only ever called with the screen already faded out. */
    /* The channels come off before a bulk transfer that is not in
     * V-blank; see ppuHdmaSuspend. ppuSetFieldMode turns them back on. */
    ppuHdmaSuspend();
    REG_INIDISP = 0x80;
    dmaCopyVram(areaPic(area), VRAM_FIELD_GFX, 8192);
    dmaCopyVram(areaMap(area), VRAM_FIELD_MAP, 8192);
    dmaCopyCGram(areaPal(area), 0, 64);

    ppuLoadBackdrop(areaBackdrop[area]);
    REG_INIDISP = fadeLevel;

    ppuSetFieldMode();
    audioMusic(areaMusic[area]);
    battleSetRegion(area, areaBackdrop[area]);
}

/* Queues the spawn rather than loading it. Loading here would swap BG1 to the
 * village while the title screen is still on it, and the fade-out would show
 * the logo sitting over the village for its whole length. */
void fieldInit(void) {
    heroDir = DIR_DOWN;
    pendingArea = SPAWN_AREA;
    pendingX = SPAWN_X;
    pendingY = SPAWN_Y;
}

/* Entering ST_FIELD: either coming back from a battle -- nothing to reload --
 * or arriving somewhere new through an exit. */
void fieldEnter(void) {
    if (pendingArea != 255) {
        fieldLoadArea(pendingArea, pendingX, pendingY);
        pendingArea = 255;
    } else {
        colPtr = areaCol(curArea);
        ppuSetFieldMode();
        audioMusic(areaMusic[curArea]);
    }
}

static void takeExit(u8 ev) {
    u16 slot;

    slot = (u16)curArea * 4 + (ev - EV_EXIT1);
    if (areaExitTo[slot] == 255)
        return;
    if (!storyMayLeave(curArea, ev))
        return;
    pendingArea = areaExitTo[slot];
    pendingX = areaExitX[slot];
    pendingY = areaExitY[slot];
    audioSfx(SFX_CONFIRM);
    requestState(ST_FIELD);
}

/* ---- events ------------------------------------------------------------ */

static void fieldEvent(u8 ev, u8 mx, u8 my) {
    u8 i;

    mx = mx;
    my = my;

    if (ev >= EV_EXIT1 && ev <= EV_EXIT4) {
        takeExit(ev);
        return;
    }

    switch (ev) {
    case EV_INN:
        for (i = 0; i < partyCount; i++) {
            pcStatus[i] &= (u8)~(STAT_SLEEP | STAT_POISON | STAT_SLOW);
            if (!(pcStatus[i] & STAT_DEAD)) {
                pcHP[i] = pcHPMax[i];
                pcMP[i] = pcMPMax[i];
            }
        }
        audioSfx(SFX_HEAL);
        msgOpen("BALLERINA CAPPUCCINA: \"Sit! Eat! Sleep is not rest, it is "
                "SURRENDER.\"  She spins once, which is how she counts. "
                "The party is restored.");
        break;

    case EV_SHOP:
        shopOpen();
        break;

    case EV_SAVE:
        /* Wells rest as well as record. There is no inn between the village
         * and any of the guardians, and arriving at a boss on a third of a
         * bar because the last corridor had two fights in it is not
         * difficulty, it is bookkeeping. */
        for (i = 0; i < partyCount; i++) {
            pcStatus[i] &= (u8)~(STAT_SLEEP | STAT_POISON | STAT_SLOW);
            if (!(pcStatus[i] & STAT_DEAD)) {
                pcHP[i] = pcHPMax[i];
                pcMP[i] = pcMPMax[i];
            }
        }
        saveGame();
        audioSfx(SFX_HEAL);
        msgOpen("Cold water and a moment to sit. The party is restored. "
                "The well writes down where you are, because slop forgets "
                "and wells do not.");
        break;

    default:
        storyEvent(ev);
        break;
    }
}

/* ---- update ------------------------------------------------------------ */

void fieldUpdate(void) {
    u16 dir;
    u8 mx, my;
    u8 flags, ev;

    if (msgActive) {
        msgUpdate();
        return;
    }
    if (storyBusy()) {
        storyUpdate();
        return;
    }
    if (menuActive) {
        menuUpdate();
        return;
    }
    if (padTrig & KEY_START) {
        menuOpen();
        return;
    }

    /* After the guards above, so the world holds still behind a message box
     * or the menu, and before the hero's own step, so a sleepwalker cannot
     * take the cell he is already committed to. */
    npcUpdate();

    /* --- mid-step: no decisions, just move ---------------------------- */
    if (stepLeft) {
        switch (heroDir) {
        case DIR_DOWN:
            heroY += STEP_PX;
            break;
        case DIR_UP:
            heroY -= STEP_PX;
            break;
        case DIR_LEFT:
            heroX -= STEP_PX;
            break;
        default:
            heroX += STEP_PX;
            break;
        }
        stepLeft--;

        animTimer++;
        if (animTimer >= 4) {
            animTimer = 0;
            walkFrame ^= 1;
        }

        if (stepLeft == 0) {
            mx = (u8)(heroX / CELL);
            my = (u8)(heroY / CELL);
            flags = fieldCollision(mx, my);
            if (flags & COL_TRIG) {
                fieldEvent(COL_EVENT(flags), mx, my);
            } else if (flags & COL_ENC) {
                stepCount++;
                if (stepCount >= encounterAt) {
                    armEncounter();
                    battleStartRandom();
                    audioSfx(SFX_DRUM);
                    ppuFlash(12);
                    requestState(ST_BATTLE);
                }
            }
        }
        return;
    }

    /* --- standing: take a direction ----------------------------------- */
    dir = pad & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT);
    if (!dir) {
        walkFrame = 0;
        animTimer = 0;
        return;
    }

    mx = (u8)(heroX / CELL);
    my = (u8)(heroY / CELL);

    if (dir & KEY_UP) {
        heroDir = DIR_UP;
        my--;
    } else if (dir & KEY_DOWN) {
        heroDir = DIR_DOWN;
        my++;
    } else if (dir & KEY_LEFT) {
        heroDir = DIR_LEFT;
        mx--;
    } else {
        heroDir = DIR_RIGHT;
        mx++;
    }

    flags = fieldCollision(mx, my);
    ev = COL_EVENT(flags);

    /* A blocked cell with an event is bumped into, never stood on -- doors,
     * cave mouths, the things that talk back. An open cell with an event fires
     * on arrival, which is what an exit wants. */
    if ((flags & COL_TRIG) && (flags & COL_BLOCK)) {
        fieldEvent(ev, mx, my);
        return;
    }
    if (flags & COL_BLOCK)
        return;
    /* They are solid. Walking through one would say they are scenery, and
     * the one thing they are is people. */
    if (npcAt(mx, my))
        return;

    stepLeft = STEP_FRAMES;
}

/* ---- draw -------------------------------------------------------------- */

void fieldDraw(void) {
    s16 camX, camY;
    s16 sx, sy;
    u16 name;

    camX = (s16)heroX + 8 - (SCR_W / 2);
    camY = (s16)heroY + 8 - (SCR_H / 2);
    if (camX < 0)
        camX = 0;
    if (camX > CAM_MAX_X)
        camX = CAM_MAX_X;
    if (camY < 0)
        camY = 0;
    if (camY > CAM_MAX_Y)
        camY = CAM_MAX_Y;
    scrollX = camX;
    scrollY = camY;

    sx = (s16)heroX - camX;
    sy = (s16)heroY - camY;

    name = SPR_WALK + (u16)(heroDir * 2 + walkFrame) * 2;

    /* Priority 2: in front of BG1, behind the window layer on BG2.1 (A-19). */
    oamSet(0, (u16)sx, (u16)sy, 2, 0, 0, name, OPAL_TUNG);
    oamSetEx(0, OBJ_SMALL, OBJ_SHOW);

    /* Entries 1 upward, and it parks whatever it did not use -- which is
     * what used to be the unconditional park of entry 1 here. */
    npcDraw(camX, camY);
}
