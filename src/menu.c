/*
 * TUNG TUNG SAHUR -- the field menu, and the shop.
 *
 * One state machine with a mode, because the field menu and the shop want the
 * same furniture: a list, a cursor, a party panel, and B to go back. Drawing
 * is layout-on-change plus volatile cells -- the same split the battle screen
 * uses, and for the same reason: repainting 1024 text cells a frame costs more
 * than a frame.
 */
#include "ttrpg.h"
#include "gfxmap.h"

u8 menuActive;

#define M_MAIN     0
#define M_ITEM     1
#define M_TARGET   2
#define M_STATUS   3
#define M_CHARM    4
#define M_CHARMWHO 5
#define M_SHOP     6

static u8 mode;
static u8 cur;                  /* cursor in the current list */
static u8 who;                  /* character the list is acting on */
static u8 shopPage;             /* 0 supplies, 1 charms */
static u8 dirty;
static u8 lastMode, lastCur, lastWho;

/* A menu opened by walking into a door inherits the direction that is still
 * held, and the cursor jumps before the player has seen the list. The shop
 * opened on ELIXIR every time for exactly this reason. Input is ignored until
 * the D-pad is let go. */
static u8 openGuard;

#define CMD_ITEM   0
#define CMD_STATUS 1
#define CMD_CHARM  2
#define CMD_SAVE   3
#define CMD_CLOSE  4
#define CMD_COUNT  5

/* Shop stock. Deliberately short: the shop exists to give gold a job, not to
 * be an inventory game. */
#define SHOP_ITEMS 6
static const u8 shopItem[SHOP_ITEMS] = {
    ITEM_HERB, ITEM_SALVE, ITEM_COFFEE, ITEM_TONIC, ITEM_BOMB, ITEM_ELIXIR
};
#define SHOP_CHARMS 6
static const u8 shopCharm[SHOP_CHARMS] = {
    CHARM_STRAP, CHARM_BARK, CHARM_LACE, CHARM_SPECS, CHARM_SKIN, CHARM_NOON
};

void menuOpen(void) {
    menuActive = 1;
    ppuMenuPalette(1);
    mode = M_MAIN;
    cur = 0;
    who = 0;
    shopPage = 0;
    lastMode = 255;
    dirty = 1;
    openGuard = 1;
    audioSfx(SFX_CONFIRM);
}

void shopOpen(void) {
    menuActive = 1;
    ppuMenuPalette(1);
    mode = M_SHOP;
    cur = 0;
    who = 0;
    shopPage = 0;
    lastMode = 255;
    dirty = 1;
    openGuard = 1;
    audioSfx(SFX_CONFIRM);
}

static void menuClose(void) {
    menuActive = 0;
    ppuMenuPalette(0);
    textClear();
    audioSfx(SFX_CURSOR);
}

/* ---- drawing ----------------------------------------------------------- */

static void drawFooter(void) {
    winBox(0, 22, 32, 6);
    textPut(2, 24, "GOLD");
    textNum(7, 24, gold, 5);
    textPut(14, 24, "ACT");
    textPut(18, 24, storyActName());
}

static void drawPartyPanel(void) {
    u8 i, row;

    winBox(10, 0, 22, 22);
    for (i = 0; i < partyCount; i++) {
        row = (u8)(1 + i * 4);
        textPut(12, row, partyNameOf(i));
        textPut(21, row, "LV");
        textNum(24, row, pcLevel[i], 2);
        if (pcStatus[i] & STAT_DEAD)
            textPutTile(28, row, ICON_DEAD, TXT_ATTR);
        else if (pcStatus[i] & STAT_SLEEP)
            textPutTile(28, row, ICON_SLEEP, TXT_ATTR);

        textPut(12, (u8)(row + 1), "HP");
        textNum(15, (u8)(row + 1), pcHP[i], 4);
        textPut(19, (u8)(row + 1), "/");
        textNum(20, (u8)(row + 1), pcHPMax[i], 4);
        textPut(25, (u8)(row + 1), "MP");
        textNum(28, (u8)(row + 1), pcMP[i], 3);

        textPut(12, (u8)(row + 2), charmNameOf(pcCharm[i]));
    }
}

static const char *mainLabel(u8 i) {
    switch (i) {
    case CMD_ITEM:
        return "ITEM";
    case CMD_STATUS:
        return "STATUS";
    case CMD_CHARM:
        return "CHARM";
    case CMD_SAVE:
        return "SAVE";
    default:
        return "CLOSE";
    }
}

static void drawMain(void) {
    u8 i;

    winBox(0, 0, 10, 22);
    for (i = 0; i < CMD_COUNT; i++)
        textPut(3, (u8)(2 + i * 2), mainLabel(i));
    drawPartyPanel();
    drawFooter();
}

static void drawItemList(void) {
    u8 i;

    winBox(0, 0, 20, 22);
    textPut(2, 1, "PROVVISTE");
    for (i = 0; i < ITEM_COUNT; i++) {
        textPutPal(3, (u8)(3 + i * 2), itemNameOf(i),
                   itemCount[i] ? PAL_WIN : PAL_ALERT);
        textNum(16, (u8)(3 + i * 2), itemCount[i], 2);
    }
    winBox(20, 0, 12, 22);
    for (i = 0; i < partyCount; i++) {
        textPut(23, (u8)(2 + i * 4), partyNameOf(i));
        textNum(23, (u8)(3 + i * 4), pcHP[i], 4);
    }
    drawFooter();
}

static void drawStatus(void) {
    winBox(0, 0, 32, 22);
    textPut(3, 2, partyNameOf(who));
    textPut(12, 2, "-");
    textPut(14, 2, partyTitleOf(who));
    textPut(3, 5, "LEVEL");
    textNum(12, 5, pcLevel[who], 3);
    textPut(3, 7, "EXP TO GO");
    textNum(15, 7, (u16)(partyExpNext(who) - pcExp[who]), 5);
    textPut(3, 10, "HP");
    textNum(8, 10, pcHP[who], 4);
    textPut(12, 10, "/");
    textNum(13, 10, pcHPMax[who], 4);
    textPut(3, 12, "MP");
    textNum(8, 12, pcMP[who], 4);
    textPut(12, 12, "/");
    textNum(13, 12, pcMPMax[who], 4);
    textPut(20, 10, "ATK");
    textNum(26, 10, pcAtk[who], 3);
    textPut(20, 12, "DEF");
    textNum(26, 12, pcDef[who], 3);
    textPut(20, 14, "MAG");
    textNum(26, 14, pcMag[who], 3);
    textPut(20, 16, "SPD");
    textNum(26, 16, pcSpd[who], 3);
    textPut(3, 15, "CHARM");
    textPut(10, 15, charmNameOf(pcCharm[who]));
    textPut(3, 19, "UP/DOWN switches, B goes back");
    drawFooter();
}

static void drawCharm(void) {
    u8 i;

    winBox(0, 0, 20, 22);
    textPut(2, 1, "PORTAFORTUNA");
    textPut(3, 3, "TAKE OFF");
    for (i = 1; i < CHARM_COUNT; i++)
        textPutPal(3, (u8)(3 + i * 2), charmNameOf(i),
                   charmOwned[i] ? PAL_WIN : PAL_ALERT);
    winBox(20, 0, 12, 22);
    for (i = 0; i < partyCount; i++) {
        textPut(23, (u8)(2 + i * 4), partyNameOf(i));
        textPut(22, (u8)(3 + i * 4), charmNameOf(pcCharm[i]));
    }
    drawFooter();
}

static void drawShop(void) {
    u8 i, n;

    winBox(0, 0, 22, 22);
    textPut(2, 1, shopPage ? "PORTAFORTUNA" : "PROVVISTE");
    n = shopPage ? SHOP_CHARMS : SHOP_ITEMS;
    for (i = 0; i < n; i++) {
        if (shopPage) {
            textPutPal(3, (u8)(3 + i * 3), charmNameOf(shopCharm[i]),
                       charmOwned[shopCharm[i]] ? PAL_ALERT : PAL_WIN);
            textNum(15, (u8)(3 + i * 3), charmPriceOf(shopCharm[i]), 5);
        } else {
            textPut(3, (u8)(3 + i * 3), itemNameOf(shopItem[i]));
            textNum(14, (u8)(3 + i * 3), itemPriceOf(shopItem[i]), 5);
            textNum(20, (u8)(3 + i * 3), itemCount[shopItem[i]], 2);
        }
    }
    winBox(22, 0, 10, 22);
    textPut(24, 2, "GOLD");
    textNum(24, 4, gold, 5);
    textPut(23, 9, "L / R");
    textPut(23, 11, "swaps");
    textPut(23, 13, "shelf");
    textPut(23, 18, "B out");
    drawFooter();
}

static void drawLayout(void) {
    textClear();
    switch (mode) {
    case M_MAIN:
        drawMain();
        break;
    case M_ITEM:
    case M_TARGET:
        drawItemList();
        break;
    case M_STATUS:
        drawStatus();
        break;
    case M_CHARM:
    case M_CHARMWHO:
        drawCharm();
        break;
    default:
        drawShop();
        break;
    }
}

static void cursorColumn(u8 x, u8 y0, u8 dy, u8 n, u8 sel) {
    u8 i, row;

    for (i = 0; i < n; i++) {
        row = (u8)(y0 + i * dy);
        textPutTile(x, row, i == sel ? ICON_CURSOR : winFillTile(row, 22),
                    TXT_ATTR);
    }
}

static void drawCursor(void) {
    switch (mode) {
    case M_MAIN:
        cursorColumn(2, 2, 2, CMD_COUNT, cur);
        break;
    case M_ITEM:
        cursorColumn(2, 3, 2, ITEM_COUNT, cur);
        break;
    case M_TARGET:
        cursorColumn(22, 2, 4, partyCount, who);
        break;
    case M_CHARM:
        cursorColumn(2, 3, 2, CHARM_COUNT, cur);
        break;
    case M_CHARMWHO:
        cursorColumn(21, 2, 4, partyCount, who);
        break;
    case M_SHOP:
        cursorColumn(2, 3, 3, shopPage ? SHOP_CHARMS : SHOP_ITEMS, cur);
        break;
    default:
        break;
    }
}

/* ---- actions ----------------------------------------------------------- */

static void useItem(u8 id, u8 target) {
    u8 i;

    if (itemCount[id] == 0) {
        audioSfx(SFX_ERROR);
        return;
    }
    switch (id) {
    case ITEM_HERB:
    case ITEM_SALVE:
        if (pcStatus[target] & STAT_DEAD) {
            audioSfx(SFX_ERROR);
            return;
        }
        pcHP[target] += (id == ITEM_HERB) ? 90 : 320;
        if (pcHP[target] > pcHPMax[target])
            pcHP[target] = pcHPMax[target];
        break;
    case ITEM_COFFEE:
        pcStatus[target] &= (u8)~STAT_SLEEP;
        pcHP[target] += 40;
        if (pcHP[target] > pcHPMax[target])
            pcHP[target] = pcHPMax[target];
        break;
    case ITEM_TONIC:
        pcMP[target] += 40;
        if (pcMP[target] > pcMPMax[target])
            pcMP[target] = pcMPMax[target];
        break;
    case ITEM_ELIXIR:
        if (!(pcStatus[target] & STAT_DEAD)) {
            audioSfx(SFX_ERROR);
            return;
        }
        pcStatus[target] &= (u8)~STAT_DEAD;
        pcHP[target] = pcHPMax[target] >> 1;
        break;
    case ITEM_TEA:
        for (i = 0; i < partyCount; i++) {
            pcStatus[i] &= (u8)~(STAT_SLEEP | STAT_POISON);
            if (!(pcStatus[i] & STAT_DEAD)) {
                pcHP[i] = pcHPMax[i];
                pcMP[i] = pcMPMax[i];
            }
        }
        break;
    default:
        /* Bombs do nothing out here, and refusing is kinder than silently
         * eating one. */
        audioSfx(SFX_ERROR);
        return;
    }
    itemCount[id]--;
    audioSfx(SFX_HEAL);
    dirty = 1;
}

static void buy(void) {
    u16 price;
    u8 id;

    if (shopPage) {
        id = shopCharm[cur];
        price = charmPriceOf(id);
        if (charmOwned[id] || gold < price) {
            audioSfx(SFX_ERROR);
            return;
        }
        charmOwned[id] = 1;
    } else {
        id = shopItem[cur];
        price = itemPriceOf(id);
        if (gold < price || itemCount[id] >= 99) {
            audioSfx(SFX_ERROR);
            return;
        }
        itemCount[id]++;
    }
    gold -= price;
    audioSfx(SFX_CONFIRM);
    dirty = 1;
}

/* ---- update ------------------------------------------------------------ */

void menuUpdate(void) {
    u16 t;
    u8 n, i;

    if (msgActive) {
        msgUpdate();
        return;
    }

    t = inputRepeat(KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT);
    if (openGuard) {
        if (pad & (KEY_UP | KEY_DOWN | KEY_LEFT | KEY_RIGHT | KEY_A
                   | KEY_START)) {
            t = 0;
            padTrig = 0;
        } else {
            openGuard = 0;
        }
    }

    switch (mode) {
    case M_MAIN:
        if (t & KEY_UP) {
            cur = (u8)((cur + CMD_COUNT - 1) % CMD_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            cur = (u8)((cur + 1) % CMD_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            menuClose();
            return;
        }
        if (padTrig & KEY_A) {
            audioSfx(SFX_CONFIRM);
            switch (cur) {
            case CMD_ITEM:
                mode = M_ITEM;
                cur = 0;
                break;
            case CMD_STATUS:
                mode = M_STATUS;
                who = 0;
                break;
            case CMD_CHARM:
                mode = M_CHARM;
                cur = 0;
                break;
            case CMD_SAVE:
                saveGame();
                msgOpen("Written down. The night keeps it. La nonna approves.");
                break;
            default:
                menuClose();
                return;
            }
            dirty = 1;
        }
        break;

    case M_ITEM:
        if (t & KEY_UP) {
            cur = (u8)((cur + ITEM_COUNT - 1) % ITEM_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            cur = (u8)((cur + 1) % ITEM_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            mode = M_MAIN;
            cur = CMD_ITEM;
            dirty = 1;
        }
        if (padTrig & KEY_A) {
            if (itemCount[cur] == 0) {
                audioSfx(SFX_ERROR);
            } else if (itemTargetsAlly(cur)) {
                mode = M_TARGET;
                who = 0;
                audioSfx(SFX_CONFIRM);
            } else {
                useItem(cur, 0);
            }
        }
        break;

    case M_TARGET:
        if (t & KEY_UP) {
            who = (u8)((who + partyCount - 1) % partyCount);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            who = (u8)((who + 1) % partyCount);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            mode = M_ITEM;
            dirty = 1;
        }
        if (padTrig & KEY_A) {
            useItem(cur, who);
            mode = M_ITEM;
            dirty = 1;
        }
        break;

    case M_STATUS:
        if (t & (KEY_LEFT | KEY_UP)) {
            who = (u8)((who + partyCount - 1) % partyCount);
            audioSfx(SFX_CURSOR);
        }
        if (t & (KEY_RIGHT | KEY_DOWN)) {
            who = (u8)((who + 1) % partyCount);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & (KEY_A | KEY_B)) {
            mode = M_MAIN;
            cur = CMD_STATUS;
            dirty = 1;
        }
        break;

    case M_CHARM:
        if (t & KEY_UP) {
            cur = (u8)((cur + CHARM_COUNT - 1) % CHARM_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            cur = (u8)((cur + 1) % CHARM_COUNT);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            mode = M_MAIN;
            cur = CMD_CHARM;
            dirty = 1;
        }
        if (padTrig & KEY_A) {
            if (cur != CHARM_NONE && !charmOwned[cur]) {
                audioSfx(SFX_ERROR);
            } else {
                mode = M_CHARMWHO;
                who = 0;
                audioSfx(SFX_CONFIRM);
            }
        }
        break;

    case M_CHARMWHO:
        if (t & KEY_UP) {
            who = (u8)((who + partyCount - 1) % partyCount);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            who = (u8)((who + 1) % partyCount);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & KEY_B) {
            mode = M_CHARM;
            dirty = 1;
        }
        if (padTrig & KEY_A) {
            /* One of each exists, so taking it off whoever had it is implied
             * rather than another menu step. */
            if (cur != CHARM_NONE)
                for (i = 0; i < PARTY_MAX; i++)
                    if (pcCharm[i] == cur)
                        pcCharm[i] = CHARM_NONE;
            pcCharm[who] = cur;
            partyApplyStats();
            audioSfx(SFX_CONFIRM);
            mode = M_CHARM;
            dirty = 1;
        }
        break;

    default:                    /* M_SHOP */
        n = shopPage ? SHOP_CHARMS : SHOP_ITEMS;
        if (t & KEY_UP) {
            cur = (u8)((cur + n - 1) % n);
            audioSfx(SFX_CURSOR);
        }
        if (t & KEY_DOWN) {
            cur = (u8)((cur + 1) % n);
            audioSfx(SFX_CURSOR);
        }
        if (padTrig & (KEY_L | KEY_R | KEY_LEFT | KEY_RIGHT)) {
            shopPage ^= 1;
            cur = 0;
            audioSfx(SFX_CURSOR);
            dirty = 1;
        }
        if (padTrig & KEY_B) {
            menuClose();
            return;
        }
        if (padTrig & KEY_A)
            buy();
        break;
    }

    if (dirty || mode != lastMode || who != lastWho) {
        lastMode = mode;
        lastWho = who;
        lastCur = 255;
        dirty = 0;
        drawLayout();
    }
    if (cur != lastCur) {
        lastCur = cur;
        drawCursor();
    }
}
