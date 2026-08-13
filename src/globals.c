/*
 * TUNG TUNG SAHUR -- shared state.
 *
 * One definition each, in one unit, because tcc has no common-symbol merging:
 * a `u8 x;` at file scope in two units links as two objects and the second
 * write goes somewhere the first reader never looks. checksyms.py fails the
 * build if that creeps back in.
 */
#include "ttrpg.h"

u8 gameState;
u8 pendingState;
u16 frameCounter;

u8 fadeLevel;
u8 animPhase;
u8 fadeTarget;

u16 pad, padTrig;

/* story */
u8 act;
u8 storyFlags;

/* party */
u8 partyCount;
u16 pcHP[PARTY_MAX], pcHPMax[PARTY_MAX];
u16 pcMP[PARTY_MAX], pcMPMax[PARTY_MAX];
u8 pcAtk[PARTY_MAX], pcDef[PARTY_MAX], pcMag[PARTY_MAX], pcSpd[PARTY_MAX];
u8 pcLevel[PARTY_MAX], pcStatus[PARTY_MAX];
u16 pcExp[PARTY_MAX];
u8 pcCharm[PARTY_MAX];
u16 gold;
u8 itemCount[ITEM_COUNT];
u8 charmOwned[CHARM_COUNT];

/* field */
u16 heroX, heroY;
u8 curArea;
u8 pendingArea, pendingX, pendingY;

/* battle */
u8 enType[ENEMY_MAX];
u16 enHP[ENEMY_MAX];
u8 enStatus[ENEMY_MAX];
u8 battleIsBoss;
u8 battleResult;

/* WRAM is not zeroed at reset. pvsneslib's crt0 clears the direct page and the
 * stack, not the whole of bank $7E, so every global read before it is first
 * written has to be set here. menuActive came up 64 on a cold boot, which made
 * main() skip fieldDraw and left the hero invisible for a whole session --
 * with the OAM entry sitting there parked and correct, which is exactly the
 * kind of bug that eats an afternoon. */
void globalsInit(void) {
    u8 i;

    gameState = ST_BOOT;
    pendingState = ST_NONE;
    frameCounter = 0;
    fadeLevel = 0;
    animPhase = 0;
    msgFace = 0;
    msgFaceReset();
    msgFaceRuns = 0;
    msgFaceShown = 0;
    fadeTarget = 0;
    pad = 0;
    padTrig = 0;

    act = 0;
    storyFlags = 0;

    partyCount = 1;
    gold = 0;
    for (i = 0; i < PARTY_MAX; i++) {
        pcHP[i] = 0;
        pcHPMax[i] = 1;
        pcMP[i] = 0;
        pcMPMax[i] = 1;
        pcAtk[i] = 1;
        pcDef[i] = 1;
        pcMag[i] = 1;
        pcSpd[i] = 1;
        pcLevel[i] = 1;
        pcStatus[i] = 0;
        pcExp[i] = 0;
        pcCharm[i] = 0;
    }
    for (i = 0; i < ITEM_COUNT; i++)
        itemCount[i] = 0;
    for (i = 0; i < CHARM_COUNT; i++)
        charmOwned[i] = 0;

    heroX = 0;
    heroY = 0;
    curArea = 0;
    pendingArea = 255;
    pendingX = 0;
    pendingY = 0;

    for (i = 0; i < ENEMY_MAX; i++) {
        enType[i] = 0;
        enHP[i] = 0;
        enStatus[i] = 0;
    }
    battleIsBoss = 0;
    battleResult = 0;

    menuActive = 0;
    msgActive = 0;
    txtDirty = 0;
    shakeTimer = 0;
    scrollX = 0;
    scrollY = 0;
}
