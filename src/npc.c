/*
 * TUNG TUNG SAHUR -- the sleepwalkers.
 *
 * Nobody in this game is awake, so the figures in the regions are not
 * villagers going about their business: they are the people the WAKING was
 * taken out of, still on their feet, drifting. They never speak. They walk
 * into walls and turn to face them. That is the whole design.
 *
 * ---- movement ---------------------------------------------------------
 *
 * The same cell-based step the hero uses -- a 16-dot cell, eight frames of
 * two dots -- so a sleepwalker is only ever *at* a cell or between two of
 * them, and everything that has to ask where one is can ask in cell units.
 * Between steps they wait, a good while, which is what makes them read as
 * asleep rather than as patrolling guards.
 *
 * ---- who owns which cell ----------------------------------------------
 *
 * A walker owns two cells for the length of a step: the one it left and the
 * one it is heading for. Owning only the destination would let the hero walk
 * into the cell being vacated and stand inside somebody; owning only the
 * origin would let him walk into the one being entered, with the same result
 * one step later.
 *
 * ---- randomness -------------------------------------------------------
 *
 * Their own generator, not rand(). The encounter counter is armed off rand()
 * and a shared sequence would mean the pacing of random battles depended on
 * how many sleepwalkers happened to be deciding something that frame.
 */
#include "ttrpg.h"
#include "worldmap.h"
#include "sprmap.h"

#define CELL        16
#define STEP_PX     2
#define STEP_FRAMES (CELL / STEP_PX)

#define NPC_MAX     8           /* per region; OAM entries 1..8 */

#define DIR_DOWN    0
#define DIR_UP      1
#define DIR_LEFT    2
#define DIR_RIGHT   3

/* Pose rows inside sprNpcName: down, up, side. */
#define POSE_DOWN   0
#define POSE_UP     1
#define POSE_SIDE   2

/* WRAM is not zeroed at reset and file statics are not in globalsInit's list
 * -- see the note in text.c about msgFaceForced. npcInit writes every one of
 * these before anything reads it, on every region load. */
static u8 npcN;
static u8 npcKind[NPC_MAX];
static u8 npcCX[NPC_MAX], npcCY[NPC_MAX];       /* the cell being entered */
static u8 npcOX[NPC_MAX], npcOY[NPC_MAX];       /* the one being left */
static u8 npcHX[NPC_MAX], npcHY[NPC_MAX];       /* where it started the night */
static u16 npcPX[NPC_MAX], npcPY[NPC_MAX];      /* dots, for the OBJ */
static u8 npcDir[NPC_MAX];
static u8 npcStep[NPC_MAX];
static u8 npcFrame[NPC_MAX];
static u8 npcAnim[NPC_MAX];
static u8 npcWait[NPC_MAX];
static u8 npcObjUsed;
static u16 npcSeed;

static u8 npcRand(void) {
    npcSeed = (u16)(npcSeed * 25173 + 13849);
    return (u8)(npcSeed >> 8);
}

void npcInit(u8 area) {
    u8 i, first, n;

    first = npcAreaFirst[area];
    n = (u8)(npcAreaFirst[area + 1] - first);
    if (n > NPC_MAX)
        n = NPC_MAX;
    npcN = n;

    /* Park everything on the first draw: the region just changed and the
     * count with it, and an OBJ left at a stale position still costs a slot
     * against the 32-per-line limit even where nothing can see it. */
    npcObjUsed = NPC_MAX;
    npcSeed = (u16)(0x2A6D + area * 0x3B9D);

    for (i = 0; i < n; i++) {
        npcKind[i] = npcKindAt[first + i];
        npcHX[i] = npcHomeX[first + i];
        npcHY[i] = npcHomeY[first + i];
        npcCX[i] = npcHX[i];
        npcCY[i] = npcHY[i];
        npcOX[i] = npcHX[i];
        npcOY[i] = npcHY[i];
        npcPX[i] = (u16)npcHX[i] * CELL;
        npcPY[i] = (u16)npcHY[i] * CELL;
        npcDir[i] = DIR_DOWN;
        npcStep[i] = 0;
        npcFrame[i] = 0;
        npcAnim[i] = 0;
        /* Stagger the first move, or all six set off on the same frame. */
        npcWait[i] = (u8)(20 + (npcRand() & 63));
    }
}

u8 npcAt(u8 mx, u8 my) {
    u8 i;

    for (i = 0; i < npcN; i++) {
        if ((npcCX[i] == mx && npcCY[i] == my)
            || (npcOX[i] == mx && npcOY[i] == my))
            return 1;
    }
    return 0;
}

/* The hero occupies one cell standing and two mid-step, the same way a
 * sleepwalker does; heroX/heroY interpolate, so the pair falls out of the
 * rounding at each end. */
static u8 heroOn(u8 mx, u8 my) {
    if (my != (u8)(heroY / CELL) && my != (u8)((heroY + CELL - 1) / CELL))
        return 0;
    return mx == (u8)(heroX / CELL) || mx == (u8)((heroX + CELL - 1) / CELL);
}

static void npcChoose(u8 i) {
    u8 d, nx, ny, flags;

    d = (u8)(npcRand() & 3);
    /* The cat is drawn from the side and only from the side, so it is only
     * ever allowed to want to go sideways. */
    if (npcKind[i] == NPC_CAT)
        d = (u8)(DIR_LEFT + (d & 1));

    nx = npcCX[i];
    ny = npcCY[i];
    switch (d) {
    case DIR_UP:
        ny--;
        break;
    case DIR_DOWN:
        ny++;
        break;
    case DIR_LEFT:
        nx--;
        break;
    default:
        nx++;
        break;
    }

    /* Turn to face it either way: a sleeper who tries a wall and stands
     * there facing it is the whole joke, and it costs nothing. */
    npcDir[i] = d;
    npcWait[i] = (u8)(30 + (npcRand() & 63));

    /* Stay near where the night caught them. The u8 arithmetic wraps on both
     * ends of the subtraction, which is what makes one comparison enough. */
    if ((u8)(nx - npcHX[i] + NPC_ROAM) > (u8)(NPC_ROAM * 2))
        return;
    if ((u8)(ny - npcHY[i] + NPC_ROAM) > (u8)(NPC_ROAM * 2))
        return;

    flags = fieldCollision(nx, ny);
    if (flags & (COL_BLOCK | COL_TRIG))
        return;                         /* walls, and never onto a doorway */
    if (npcAt(nx, ny) || heroOn(nx, ny))
        return;

    npcCX[i] = nx;
    npcCY[i] = ny;
    npcStep[i] = STEP_FRAMES;
    npcWait[i] = 0;
}

void npcUpdate(void) {
    u8 i;

    for (i = 0; i < npcN; i++) {
        if (npcStep[i]) {
            switch (npcDir[i]) {
            case DIR_DOWN:
                npcPY[i] += STEP_PX;
                break;
            case DIR_UP:
                npcPY[i] -= STEP_PX;
                break;
            case DIR_LEFT:
                npcPX[i] -= STEP_PX;
                break;
            default:
                npcPX[i] += STEP_PX;
                break;
            }
            npcStep[i]--;

            /* Half the hero's cadence. They are not in a hurry. */
            npcAnim[i]++;
            if (npcAnim[i] >= 8) {
                npcAnim[i] = 0;
                npcFrame[i] ^= 1;
            }

            if (npcStep[i] == 0) {
                npcOX[i] = npcCX[i];
                npcOY[i] = npcCY[i];
                npcFrame[i] = 0;
                npcAnim[i] = 0;
                npcWait[i] = (u8)(30 + (npcRand() & 63));
            }
            continue;
        }

        if (npcWait[i]) {
            npcWait[i]--;
            continue;
        }
        npcChoose(i);
    }
}

void npcDraw(s16 camX, s16 camY) {
    u8 i, obj, pose, flip;
    s16 sx, sy;
    u16 name;

    obj = 1;                            /* entry 0 is the hero */
    for (i = 0; i < npcN; i++) {
        sx = (s16)npcPX[i] - camX;
        sy = (s16)npcPY[i] - camY;
        /* Off screen costs an OAM slot and a line's worth of the 32-OBJ
         * budget for nothing. A region is 512 dots across and the window is
         * 256, so most of them are outside it at any time. */
        if (sx < -CELL || sx >= SCR_W || sy < -CELL || sy >= SCR_H)
            continue;

        flip = 0;
        switch (npcDir[i]) {
        case DIR_UP:
            pose = POSE_UP;
            break;
        case DIR_LEFT:
            pose = POSE_SIDE;
            flip = 1;               /* drawn facing right, mirrored for left */
            break;
        case DIR_RIGHT:
            pose = POSE_SIDE;
            break;
        default:
            pose = POSE_DOWN;
            break;
        }
        name = sprNpcName[npcKind[i] * 6 + pose * 2 + npcFrame[i]];

        oamSet((u16)(obj << 2), (u16)sx, (u16)sy, 2, flip, 0,
               name, sprNpcPal[npcKind[i]]);
        oamSetEx((u16)(obj << 2), OBJ_SMALL, OBJ_SHOW);
        obj++;
    }

    while (obj < npcObjUsed) {
        oamSet((u16)(obj << 2), 0, OAM_PARK_Y, 2, 0, 0, 0, 0);
        oamSetEx((u16)(obj << 2), OBJ_SMALL, OBJ_HIDE);
        obj++;
    }
    npcObjUsed = obj;
}
