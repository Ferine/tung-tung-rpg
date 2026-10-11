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
 * One region is active at a time. Changing region fills its visible tile cache
 * and palette under forced blank, which is why it happens on the far side of a
 * fade: VRAM is writable in forced blank or V-blank only (ppu-graphics.md,
 * "Access periods"). Battle borrows the scene window, so returning restores it.
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
#include "fieldactormap.h"

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
    u8 x, y, bx, by;
    u16 distance, best;

    if (area >= AREA_COUNT) area = AREA_VILLAGE;
    curArea = area;
    colPtr = areaCol(area);
    /* Older saves can stand on a cell whose painted footprint was corrected.
     * Relocate to the nearest ordinary floor, never onto another event. */
    if (mx >= MAP_W || my >= MAP_H || (fieldCollision(mx, my) & COL_BLOCK)) {
        best = 65535; bx = SPAWN_X; by = SPAWN_Y;
        for (y = 0; y < MAP_H; y++) {
            for (x = 0; x < MAP_W; x++) {
                if (fieldCollision(x, y) & (COL_BLOCK | COL_TRIG)) continue;
                distance = (mx > x ? mx - x : x - mx) + (my > y ? my - y : y - my);
                if (distance < best) { best = distance; bx = x; by = y; }
            }
        }
        mx = bx; my = by;
    }
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

    /* Field and battle share the 32KB scene window. Field mode fills
     * the visible tile cache and palette together under forced blank. */
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

/* Entering ST_FIELD: either restoring its painting after a battle,
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
            pcStatus[i] = 0;
            pcHP[i] = pcHPMax[i];
            pcMP[i] = pcMPMax[i];
        }
        audioSfx(SFX_HEAL);
        questInn();
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
            pcStatus[i] = 0;
            pcHP[i] = pcHPMax[i];
            pcMP[i] = pcMPMax[i];
        }
        audioSfx(SFX_HEAL);
        if (!questWell())
            msgOpen("Cold water and a moment to sit. The party is restored. "
                    "The well writes down where you are, because slop forgets "
                    "and wells do not.");
        saveGame();
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
            walkFrame = (walkFrame + 1) & 3;
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

void fieldCamera(void) {
    s16 camX, camY;

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
}

void fieldDraw(void) {
    s16 camX, camY, sx, sy;
    u16 name, obj;

    fieldCamera();
    camX = scrollX;
    camY = scrollY;
    fieldStreamPrepare();

    sx = (s16)heroX + 8 - FIELD_ANCHOR_X - camX;
    sy = (s16)heroY + 8 - FIELD_ANCHOR_Y - camY;

    name = fieldWalk[heroDir * 4 + walkFrame];

    /* Priority 2: above the painting, below its foreground and BG1 windows. */
    npcDraw(camX, camY);
    obj = (u16)npcHeroSlot() << 2;
    oamSetEx(obj, OBJ_LARGE, OBJ_SHOW);
    oamSet(obj, (u16)sx, (u16)sy, 2, 0, 0, name, OPAL_TUNG);

    /* Entries 1 upward, and it parks whatever it did not use -- which is
     * what used to be the unconditional park of entry 1 here. */
}

void fieldHideActors(void) {
    u8 i;
    /* Leave slot 16 alone: menu messages may still need a portrait. */
    for (i = 0; i < 10; i++)
        oamSetEx((u16)i << 2, OBJ_SMALL, OBJ_HIDE);
}
