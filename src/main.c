/*
 * TUNG TUNG SAHUR -- boot, the screen state machine, and the frame loop.
 *
 * The loop's shape is load-bearing. PPU registers, VRAM, OAM and CGRAM may
 * only be touched in the V-blank window right after WaitForVBlank
 * (ppu-graphics.md, "Access periods"), so everything that writes them runs at
 * the top; the game's own logic runs afterwards, in the visible frame, where
 * it has time.
 */
#include "ttrpg.h"
#include "gfxmap.h"
#include "sprmap.h"
#include "worldmap.h"

static void enterState(u8 s);
static void updateTitle(void);
static void updateGameOver(void);
static void updateEnding(void);
static void drawTitle(void);

static u8 openingPending;

/* ---- input ------------------------------------------------------------- */

static u8 repeatTimer;

void inputRead(void) {
    pad = padsCurrent(0);
    padTrig = padsDown(0);

    /* cpu-system.md Caution #8: D3-D0 of $4218 is the controller ID -- 0000
     * standard pad, 0001 Mouse, 1111 Super Scope -- and a game built for the
     * pad must ignore input when it reads anything else, or a Mouse in port 1
     * drives the game with motion data. Read straight after padsCurrent so it
     * inherits the library's auto-read timing; $4218 sampled while the
     * auto-read is still running returns garbage. */
    if ((REG_JOYxLH(0) & 0x000F) != 0) {
        pad = 0;
        padTrig = 0;
    }
}

/* Press fires at once, then a long delay, then a fast repeat -- the standard
 * menu feel. Without it a five-entry list is unusable: one frame of held
 * D-pad scrolls it end to end. */
u16 inputRepeat(u16 mask) {
    u16 held, fresh;

    fresh = padTrig & mask;
    if (fresh) {
        repeatTimer = 20;
        return fresh;
    }
    held = pad & mask;
    if (!held) {
        repeatTimer = 0;
        return 0;
    }
    if (repeatTimer) {
        repeatTimer--;
        return 0;
    }
    repeatTimer = 5;
    return held;
}

/* ---- state ------------------------------------------------------------- */

void requestState(u8 s) {
    if (pendingState != ST_NONE)
        return;
    pendingState = s;
    fadeTarget = 0;
}

static void enterState(u8 s) {
    gameState = s;
    textClear();
    oamClear(0, 0);

    switch (s) {
    case ST_TITLE:
        ppuSetBattleMode();
        ppuLoadTitle();
        audioMusic(BGM_TITLE);
        drawTitle();
        break;

    case ST_FIELD:
        fieldEnter();
        if (openingPending) {
            openingPending = 0;
            storyBegin();
        }
        break;

    case ST_BATTLE:
        /* On the far side of the fade, so the wipe dissolves the field the
         * player was standing in rather than the screen they are going to --
         * and inside forced blank, because this is where the fight's enemy
         * art goes into the second OBJ page. */
        ppuHdmaSuspend();
        REG_INIDISP = 0x80;
        battleUploadEnemies();
        ppuSetBattleMode();
        break;

    case ST_GAMEOVER:
        ppuSetBattleMode();
        audioStop();
        break;

    case ST_ENDING:
        ppuSetBattleMode();
        ppuBattlePalette(1);        /* the sky they were trying to prevent */
        audioMusic(BGM_ENDING);
        break;

    default:
        break;
    }
}

/* ---- title ------------------------------------------------------------- */

/* The logo alphabet is 2x2 characters per letter, laid out as a 16x16 block
 * would be for an OBJ: +1 right, +0x10 down. Anything not in BIG_LETTERS is a
 * space and advances one column. */
static u8 bigTile(char c) {
    const char *p;
    u8 i;

    p = BIG_LETTERS;
    for (i = 0; p[i]; i++)
        if (p[i] == c)
            return (u8)(BIG_BASE + i * 2);
    return 0xFF;
}

static void bigPut(u8 x, u8 y, const char *s) {
    u8 t;

    while (*s) {
        t = bigTile(*s);
        if (t == 0xFF) {
            x++;
        } else {
            textPutTile(x, y, t, TXT_ATTR);
            textPutTile(x + 1, y, (u8)(t + 1), TXT_ATTR);
            textPutTile(x, y + 1, (u8)(t + 0x10), TXT_ATTR);
            textPutTile(x + 1, y + 1, (u8)(t + 0x11), TXT_ATTR);
            x += 2;
        }
        s++;
    }
}

static u8 titleCur;
static u8 titleHasSave;

/* The logo is in the picture now, not spelled out of the font, so the text
 * layer only carries what has to be readable and what has to blink. */
static void drawTitle(void) {
    textClear();
    textPut(6, 15, "-  LE  TRE  CHIAMATE  -");
    winBox(9, 17, 14, 6);
    textPut(12, 18, "NEW  NIGHT");
    textPutPal(12, 20, "CONTINUE", titleHasSave ? PAL_WIN : PAL_ALERT);
    textPut(2, 25, "(c) 1994 SLOPWORKS  KAMPUNG");
}

static void updateTitle(void) {
    u16 t;

    /* Tung on the ridge, in front of the village and behind the menu box:
     * priority 2 puts an OBJ under BG2.1, which is where the window is.
     * OBJ_SMALL here is 32x32 -- the title runs in the battle size pair. */
    oamSet(0, 24, 140, 2, 0, 0, SPR_TUNG, OPAL_TUNG);
    oamSetEx(0, OBJ_SMALL, OBJ_SHOW);

    t = inputRepeat(KEY_UP | KEY_DOWN);
    if (t & (KEY_UP | KEY_DOWN)) {
        titleCur ^= 1;
        audioSfx(SFX_CURSOR);
    }
    textPutTile(11, 18, titleCur == 0 ? ICON_CURSOR : winFillTile(1, 6),
                TXT_ATTR);
    textPutTile(11, 20, titleCur == 1 ? ICON_CURSOR : winFillTile(3, 6),
                TXT_ATTR);

    if (padTrig & (KEY_START | KEY_A)) {
        if (titleCur == 1 && !titleHasSave) {
            audioSfx(SFX_ERROR);
            return;
        }
        audioSfx(SFX_CONFIRM);
        if (titleCur == 1) {
            partyInit();
            storyInit();
            loadGame();
            requestState(ST_FIELD);
        } else {
            partyInit();
            storyInit();
            fieldInit();
            openingPending = 1;
            requestState(ST_FIELD);
        }
    }
}

/* ---- game over --------------------------------------------------------- */

static u8 overTimer;

static void updateGameOver(void) {
    textPut(11, 12, "GAME  OVER");
    textPut(4, 16, "The sun came up over a");
    textPut(6, 17, "world still scrolling.");

    if (overTimer < 120) {
        overTimer++;
        return;
    }
    if (frameCounter & 32)
        textPut(9, 20, "PRESS  START");
    else
        textFill(9, 20, 12, 1, 0);

    if (padTrig & (KEY_START | KEY_A)) {
        overTimer = 0;
        titleHasSave = saveExists();
        requestState(ST_TITLE);
    }
}

/* ---- ending ------------------------------------------------------------ */

static u8 endStep;
static u16 endTimer;

static void updateEnding(void) {
    if (msgActive) {
        msgUpdate();
        return;
    }

    switch (endStep) {
    case 0:
        msgOpenAtAs("IL SILENZIO does not leave. It stops being agreed with, "
                    "which for a silence turns out to be the same thing.", 2,
                    FACE_SILENZIO);
        endStep++;
        break;
    case 1:
        msgOpenAtAs("One by one the windows light. Somebody puts a pot on. "
                    "Somebody complains about the hour. Mamma mia, the NOISE "
                    "of a place that is awake.", 2, FACE_NONNA);
        endStep++;
        break;
    case 2:
        msgOpenAtAs("A shark, a tree, a cactus and a bomber stand in a village "
                    "square at four in the morning arguing about breakfast. "
                    "None of it was drawn by a person. All of it is AWAKE.", 2,
                    FACE_TRALA);
        endStep++;
        break;
    case 3:
        msgOpenAtAs("TUNG TUNG TUNG SAHUR lowers the bat and beats the third "
                    "call -- gently, because it is no longer necessary. "
                    "Slop that gets up. That is the whole recipe.", 2,
                    FACE_TUNG);
        endStep++;
        break;
    case 4:
        textClear();
        textPut(9, 11, "SAHUR  E  SERVITO");
        textPut(12, 14, "THE  END");
        endStep++;
        endTimer = 0;
        break;
    default:
        endTimer++;
        if (endTimer > 240 && (padTrig & (KEY_START | KEY_A))) {
            endStep = 0;
            titleHasSave = saveExists();
            requestState(ST_TITLE);
        }
        break;
    }
}

/* ---- boot -------------------------------------------------------------- */

int main(void) {
    globalsInit();
    setBrightness(0);
    audioInit();

    ppuInit();
    textInit();
    oamClear(0, 0);

    frameCounter = 0;
    scrollX = 0;
    scrollY = 0;
    fadeLevel = 0;
    fadeTarget = FADE_MAX;
    pendingState = ST_NONE;
    overTimer = 0;
    endStep = 0;
    titleCur = 0;

    partyInit();
    storyInit();
    fieldInit();
    openingPending = 0;
    titleHasSave = saveExists();

    gameState = ST_TITLE;
    enterState(ST_TITLE);
    setScreenOn();

    while (1) {
        WaitForVBlank();

        /* --- V-blank window --------------------------------------------
         * Brightness, the text-layer DMA, scroll and colour math. Nothing
         * below this point may write a PPU register. */
        setBrightness(fadeLevel);
        textFlush();
        ppuAnimateTiles();
        ppuTitleCycle();
        ppuFaceService();
        ppuUpdate();

        /* The encounter wipe: BG1 dissolves into blocks as the screen fades
         * out, and snaps back on arrival. Driven off the fade rather than its
         * own timer so the two cannot disagree about how long it takes. */
        ppuMosaic(pendingState == ST_BATTLE
                  ? (u8)((FADE_MAX - fadeLevel) >> 1) : 0);

        /* Right after the NMI rather than at the tail of the loop: the SPC
         * handshake spins without a timeout, and at the end of a frame the
         * next NMI -- carrying the text-map DMA -- lands in the middle of one. */
        audioProcess();

        inputRead();
        frameCounter++;

        /* Logic is frozen while the screen fades into the next state. */
        if (pendingState == ST_NONE) {
            switch (gameState) {
            case ST_TITLE:
                updateTitle();
                break;
            case ST_FIELD:
                fieldUpdate();
                if (!menuActive)
                    fieldDraw();
                break;
            case ST_BATTLE:
                battleUpdate();
                battleDraw();
                break;
            case ST_GAMEOVER:
                updateGameOver();
                break;
            case ST_ENDING:
                updateEnding();
                break;
            default:
                break;
            }
        }

        if (fadeLevel < fadeTarget)
            fadeLevel++;
        else if (fadeLevel > fadeTarget)
            fadeLevel--;

        if (pendingState != ST_NONE && fadeLevel == 0) {
            enterState(pendingState);
            pendingState = ST_NONE;
            fadeTarget = FADE_MAX;
        }
    }

    return 0;
}
