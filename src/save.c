/*
 * TUNG TUNG SAHUR -- the save slot.
 *
 * 2KB of battery-backed SRAM at $70:0000 (the cartridge type and SRAM size in
 * hdr.asm are what make it exist). The game needs about eighty bytes of it, so
 * the block is written and read whole through pvsneslib's helpers rather than
 * being poked field by field.
 *
 * The magic is version-stamped. A save written by an earlier build has a
 * different layout and reading it would produce a party with plausible-looking
 * nonsense in it, which is worse than no save at all; a mismatched stamp is
 * treated as an empty slot.
 */
#include "ttrpg.h"

#define SAVE_MAGIC0 'T'
#define SAVE_MAGIC1 'T'
#define SAVE_MAGIC2 'S'
#define SAVE_VERSION 2

#define SAVE_SIZE 96
static u8 blob[SAVE_SIZE];

static void put16(u8 at, u16 v) {
    blob[at] = (u8)(v & 0xFF);
    blob[at + 1] = (u8)(v >> 8);
}

static u16 get16(u8 at) {
    return (u16)blob[at] | ((u16)blob[at + 1] << 8);
}

/* Layout. Written out longhand because a struct here would be at the mercy of
 * whatever padding tcc feels like, and this block outlives the build. */
#define O_MAGIC    0            /* 4 */
#define O_ACT      4
#define O_FLAGS    5
#define O_COUNT    6
#define O_AREA     7
#define O_HX       8
#define O_HY       9
#define O_GOLD     10           /* 2 */
#define O_LEVEL    12           /* 5 */
#define O_STATUS   17           /* 5 */
#define O_CHARM    22           /* 5 */
#define O_HP       27           /* 10 */
#define O_MP       37           /* 10 */
#define O_EXP      47           /* 10 */
#define O_ITEMS    57           /* 8 */
#define O_OWNED    65           /* 7 */
#define O_SUM      72           /* 1 */

static u8 checksum(void) {
    u8 i, s;

    s = 0x5A;
    for (i = 0; i < O_SUM; i++)
        s += blob[i];
    return s;
}

void saveGame(void) {
    u8 i;

    for (i = 0; i < SAVE_SIZE; i++)
        blob[i] = 0;

    blob[O_MAGIC + 0] = SAVE_MAGIC0;
    blob[O_MAGIC + 1] = SAVE_MAGIC1;
    blob[O_MAGIC + 2] = SAVE_MAGIC2;
    blob[O_MAGIC + 3] = SAVE_VERSION;

    blob[O_ACT] = act;
    blob[O_FLAGS] = storyFlags;
    blob[O_COUNT] = partyCount;
    blob[O_AREA] = curArea;
    blob[O_HX] = (u8)(heroX >> 4);
    blob[O_HY] = (u8)(heroY >> 4);
    put16(O_GOLD, gold);

    for (i = 0; i < PARTY_MAX; i++) {
        blob[O_LEVEL + i] = pcLevel[i];
        blob[O_STATUS + i] = pcStatus[i];
        blob[O_CHARM + i] = pcCharm[i];
        put16((u8)(O_HP + i * 2), pcHP[i]);
        put16((u8)(O_MP + i * 2), pcMP[i]);
        put16((u8)(O_EXP + i * 2), pcExp[i]);
    }
    for (i = 0; i < ITEM_COUNT; i++)
        blob[O_ITEMS + i] = itemCount[i];
    for (i = 0; i < CHARM_COUNT; i++)
        blob[O_OWNED + i] = charmOwned[i];

    blob[O_SUM] = checksum();
    consoleCopySram(blob, SAVE_SIZE);
}

u8 saveExists(void) {
    consoleLoadSram(blob, SAVE_SIZE);
    return (blob[O_MAGIC + 0] == SAVE_MAGIC0
            && blob[O_MAGIC + 1] == SAVE_MAGIC1
            && blob[O_MAGIC + 2] == SAVE_MAGIC2
            && blob[O_MAGIC + 3] == SAVE_VERSION
            && blob[O_SUM] == checksum()) ? 1 : 0;
}

u8 loadGame(void) {
    u8 i;

    if (!saveExists())
        return 0;

    act = blob[O_ACT];
    storyFlags = blob[O_FLAGS];
    partyCount = blob[O_COUNT];
    gold = get16(O_GOLD);

    for (i = 0; i < PARTY_MAX; i++) {
        pcLevel[i] = blob[O_LEVEL + i] ? blob[O_LEVEL + i] : 1;
        pcStatus[i] = blob[O_STATUS + i];
        pcCharm[i] = blob[O_CHARM + i];
        pcExp[i] = get16((u8)(O_EXP + i * 2));
    }
    for (i = 0; i < ITEM_COUNT; i++)
        itemCount[i] = blob[O_ITEMS + i];
    for (i = 0; i < CHARM_COUNT; i++)
        charmOwned[i] = blob[O_OWNED + i];

    /* Derived stats are recomputed rather than stored: they are a pure
     * function of level and charm, and storing them is one more thing that can
     * disagree with itself across a version. */
    partyApplyStats();
    for (i = 0; i < PARTY_MAX; i++) {
        pcHP[i] = get16((u8)(O_HP + i * 2));
        pcMP[i] = get16((u8)(O_MP + i * 2));
        if (pcHP[i] > pcHPMax[i])
            pcHP[i] = pcHPMax[i];
        if (pcMP[i] > pcMPMax[i])
            pcMP[i] = pcMPMax[i];
    }

    /* Queued, not loaded: loadGame is called from the title, and loading
     * here would put the saved region on screen behind the logo. */
    pendingArea = blob[O_AREA];
    pendingX = blob[O_HX];
    pendingY = blob[O_HY];
    return 1;
}
