/*
 * TUNG TUNG SAHUR -- the text and window layer.
 *
 * BG2 is a 32x32 tilemap at VRAM $5000 whose characters are the font sheet at
 * $2000. We keep the whole map shadowed in RAM and transfer it whole when
 * something changed, rather than poking VRAM per glyph: VRAM is writable only
 * in forced blank or V-blank (ppu-graphics.md, "Access periods"), and 2KB is
 * one ~0.8ms DMA against a ~2.4ms V-blank at 224 lines -- comfortably inside,
 * and it means drawing code can run anywhere in the frame.
 *
 * Every entry carries the priority bit. In the 3-screen priority order (A-19)
 * BG2.1 sits directly in front of OBJ.2, which is where the party and enemy
 * sprites are, so a window drawn here covers them the way FF's do.
 */
#include "ttrpg.h"
#include "gfxmap.h"
#include "sprmap.h"   /* FACE_* */

u8 txtMap[32 * 32 * 2];
u8 txtDirty;

/* ---- primitives -------------------------------------------------------- */

void textPutTile(u8 x, u8 y, u8 tile, u8 attr) {
    u16 o;

    if (x >= 32 || y >= 32)
        return;
    o = ((u16)y << 6) + ((u16)x << 1);
    txtMap[o] = tile;
    txtMap[o + 1] = attr;
    txtDirty = 1;
}

/* Walked with a pointer rather than indexed with i<<1: tcc recomputes the
 * shifted index and the array base on every one of the 2048 stores otherwise,
 * and this runs whenever a battle window opens or closes. */
void textClear(void) {
    u8 *p;
    u16 i;

    p = txtMap;
    for (i = 0; i < 32 * 32; i++) {
        *p++ = 0;                       /* glyph 0 is ' ', fully transparent */
        *p++ = TXT_ATTR;
    }
    txtDirty = 1;
}

void textFill(u8 x, u8 y, u8 w, u8 h, u8 tile) {
    u8 i, j;

    for (j = 0; j < h; j++)
        for (i = 0; i < w; i++)
            textPutTile(x + i, y + j, tile, TXT_ATTR);
}

/* A space leaves the cell alone rather than writing glyph 0.
 *
 * Glyph 0 *is* a space, and it is fully transparent -- which is right over the
 * field and wrong inside a window, where transparent means the battle backdrop
 * shows through the box. Written as a glyph, every gap in "TUNG  130  12"
 * punched a hole in the window fill and the status box came out striped with
 * rock texture.
 *
 * The invariant this depends on: callers that need a cell actually cleared use
 * textFill(), and every screen that draws text into windows repaints the whole
 * layer from textClear() each frame, so nothing stale survives.
 */
void textPutPal(u8 x, u8 y, const char *s, u8 pal) {
    u8 attr;

    attr = (pal << 2) | 0x20;
    while (*s) {
        if (*s != ' ')
            /* The sheet stores printable ASCII at charcode-32, so the whole
             * run is contiguous and this is the entire mapping. */
            textPutTile(x, y, (u8)(*s) - 32, attr);
        x++;
        s++;
    }
}

void textPut(u8 x, u8 y, const char *s) {
    textPutPal(x, y, s, PAL_WIN);
}

void textNumPal(u8 x, u8 y, u16 v, u8 digits, u8 pal) {
    u8 buf[6];
    u8 n;
    u8 attr;

    attr = (pal << 2) | 0x20;
    n = 0;
    do {
        /* One division per digit, not two. tcc has no hardware divide to reach
         * for -- a 16-bit divide is a software routine of several hundred
         * cycles -- and `v % 10` beside `v / 10` calls it twice. The remainder
         * comes back out with a multiply by ten, which is three shifts. */
        u16 q = v / 10;
        buf[n] = (u8)(v - (q * 10));
        v = q;
        n++;
    } while (v && n < 5);

    /* Right-aligned. The padding is skipped, not written: see textPutPal --
     * a written blank is a transparent hole in whatever window this sits in. */
    while (digits > n) {
        x++;
        digits--;
    }
    while (n) {
        n--;
        textPutTile(x, y, buf[n] + '0' - 32, attr);
        x++;
    }
}

void textNum(u8 x, u8 y, u16 v, u8 digits) {
    textNumPal(x, y, v, digits, PAL_WIN);
}

/* ---- windows ----------------------------------------------------------- */

/* The frame carries the gradient step of the row it is on, so a box of any
 * height maps its rows onto the six steps and picks matching edge tiles.
 *
 * Table rather than (row * 5) / (h - 1): every window cell asks for this, and
 * the menu cursors ask again every frame. A divide each was a measurable slice
 * of the battle frame.  Rows and heights above 15 fall back to the division;
 * no window in the game is that tall.
 */
static const u8 gradTable[16 * 16] = {
/* The h<2 rows are never read -- gradStep returns 0 before it gets here -- but
 * the divisor still has to be non-zero, because tcc folds both arms of the
 * ternary when it evaluates a constant initialiser and rejects the file for a
 * division by zero it would never execute. */
#define GDIV(h) ((h) < 2 ? 1 : ((h) - 1))
#define GS(r, h) (((r) * (GRAD_STEPS - 1)) / GDIV(h) > (GRAD_STEPS - 1) \
                  ? (GRAD_STEPS - 1) : ((r) * (GRAD_STEPS - 1)) / GDIV(h))
#define GROW(h) GS(0,h),GS(1,h),GS(2,h),GS(3,h),GS(4,h),GS(5,h),GS(6,h),GS(7,h), \
                GS(8,h),GS(9,h),GS(10,h),GS(11,h),GS(12,h),GS(13,h),GS(14,h),GS(15,h)
    GROW(0), GROW(1), GROW(2), GROW(3), GROW(4), GROW(5), GROW(6), GROW(7),
    GROW(8), GROW(9), GROW(10), GROW(11), GROW(12), GROW(13), GROW(14), GROW(15)
#undef GROW
#undef GS
#undef GDIV
};

static u8 gradStep(u8 row, u8 h) {
    if (h <= 1)
        return 0;
    if (h < 16 && row < 16)
        return gradTable[((u16)h << 4) | row];
    return (u8)(((u16)row * (GRAD_STEPS - 1)) / (h - 1));
}

/* The interior tile for a given row of a box of a given height. Callers that
 * update one cell in place -- a menu cursor moving down a list -- need this to
 * put back what winBox would have drawn, without repainting the box. */
u8 winFillTile(u8 row, u8 h) {
    return (u8)(WIN_F0 + gradStep(row, h));
}

void winBox(u8 x, u8 y, u8 w, u8 h) {
    u8 i, j, s;

    if (w < 2 || h < 2)
        return;

    textPutTile(x, y, WIN_TL, TXT_ATTR);
    textPutTile(x + w - 1, y, WIN_TR, TXT_ATTR);
    textPutTile(x, y + h - 1, WIN_BL, TXT_ATTR);
    textPutTile(x + w - 1, y + h - 1, WIN_BR, TXT_ATTR);

    for (i = 1; i < w - 1; i++) {
        textPutTile(x + i, y, WIN_T, TXT_ATTR);
        textPutTile(x + i, y + h - 1, WIN_B, TXT_ATTR);
    }

    for (j = 1; j < h - 1; j++) {
        s = gradStep(j, h);
        textPutTile(x, y + j, WIN_L0 + s, TXT_ATTR);
        textPutTile(x + w - 1, y + j, WIN_R0 + s, TXT_ATTR);
        for (i = 1; i < w - 1; i++)
            textPutTile(x + i, y + j, WIN_F0 + s, TXT_ATTR);
    }
}

void winErase(u8 x, u8 y, u8 w, u8 h) {
    textFill(x, y, w, h, 0);
}

void textGauge(u8 x, u8 y, u8 w, u16 cur, u16 max, u8 pal) {
    u16 pixels;
    u16 filled;
    u8 i, n;
    u8 attr;

    attr = (pal << 2) | 0x20;
    if (max == 0)
        max = 1;
    if (cur > max)
        cur = max;

    /* cur * w * 8 overflows 16 bits once HP passes ~1000, and there is no
     * 32-bit multiply worth spending here. Halve both until the product is
     * safe; the gauge is 64 dots wide at most, so the lost precision is
     * invisible. */
    while (max > 255) {
        max >>= 1;
        cur >>= 1;
    }

    pixels = (u16)w << 3;
    if (max == 255) {
        /* The ATB gauge, drawn three times a frame: cur*w*8/255 is within a
         * dot of (cur*w)/32, and a shift is not a software division. */
        filled = ((u16)cur * w) >> 5;
    } else {
        filled = ((u16)cur * pixels) / max;
    }

    for (i = 0; i < w; i++) {
        if (filled >= 8) {
            n = 8;
            filled -= 8;
        } else {
            n = (u8)filled;
            filled = 0;
        }
        textPutTile(x + i, y, GAUGE0 + n, attr);
    }
}

/* ---- message box ------------------------------------------------------- */
/*
 * A three-line box that types itself out, then waits for A. Battle drives it
 * from the top of the screen and the field from the bottom, so the row is a
 * parameter.
 */

#define MSG_W    30
#define MSG_LINES 3
#define MSG_COLS 27

u8 msgActive;
u8 msgFace;                     /* FACE_* of the speaker, 0 = narration */
u8 msgFaceRuns;                 /* rows of art still to push into VRAM */
u8 msgFaceShown;                /* 1 once all four rows have landed */

/* The dialogue portrait sits in its own frame directly on top of the message
 * box, the way a JRPG puts a bust above the text rather than inside it. Six
 * tiles square: four of interior, which is exactly the 32x32 art.
 *
 * Only when the message box is low enough to have six rows above it. Battle
 * messages open at row 1 and would put the frame off the top of the screen --
 * and the space under a battle message is where the enemies are. */
#define FACE_BOX_W 6
#define FACE_BOX_H 6

/* Where the frame actually went. Normally directly above the message box;
 * for a forced face on a box that is already at the top of the screen -- the
 * ending, which opens at row 2 -- directly below it instead. */
static u8 faceBoxRow;
static u8 msgLine[MSG_LINES][MSG_COLS + 1];
static u8 msgLines;
u8 msgY;
u8 msgFaceY;                    /* pixel row of the portrait itself */
static u8 msgShown;             /* characters revealed so far, across lines */
static u8 msgDrawn;             /* characters actually on the layer */
static u8 msgTotal;
static u8 msgHold;

/* Who is talking, worked out from the line itself.
 *
 * The script already writes "LA NONNA:" in front of her lines, because that is
 * how the box read before there were portraits. Matching on that means no call
 * site has to be told twice who is speaking, and a line without a known name
 * in front of it is narration and gets no face -- which is the correct default
 * for the two thirds of the script that is narration.
 *
 * Longest first: BRR BRR PATAPIM has to be tested before PATAPIM, or every
 * line of his would match the short form at the wrong offset.
 *
 * Written as a switch rather than an array of pointers: tcc emits pointer
 * tables into a section this build cannot address cheaply, and the same
 * pattern is already how storyActName and sceneLine hand out strings.
 */
static const char *facePrefix(u8 i) {
    switch (i) {
    case 0:  return "BALLERINA CAPPUCCINA:";
    case 1:  return "BOMBARDIRO CROCODILO:";
    case 2:  return "TRALALERO TRALALA:";
    case 3:  return "BRR BRR PATAPIM:";
    case 4:  return "LIRILI LARILA:";
    case 5:  return "IL SILENZIO:";
    case 6:  return "BOMBARDIRO:";
    case 7:  return "TRALALERO:";
    case 8:  return "LA NONNA:";
    case 9:  return "PATAPIM:";
    case 10: return "LIRILI:";
    default: return 0;
    }
}

static u8 facePrefixId(u8 i) {
    switch (i) {
    case 0:  return FACE_CAPPUCCINA;
    case 1:  return FACE_BOMBARD;
    case 2:  return FACE_TRALA;
    case 3:  return FACE_PATAPIM;
    case 4:  return FACE_LIRILI;
    case 5:  return FACE_SILENZIO;
    case 6:  return FACE_BOMBARD;
    case 7:  return FACE_TRALA;
    case 8:  return FACE_NONNA;
    case 9:  return FACE_PATAPIM;
    case 10: return FACE_LIRILI;
    default: return FACE_NONE;
    }
}

/* Whoever spoke last, so a continued line keeps their portrait up.
 *
 * The script marks continuation for free: a line that carries on from the one
 * before opens with a quote and no name, because that is how the dialogue was
 * already written. Narration never opens with a quote -- checked across the
 * whole script -- so the two cases do not overlap and nothing had to be
 * annotated after the fact.
 */
static u8 faceLast;

/* Set by msgOpenAs for the lines the script does not name a speaker in --
 * the opening and the ending, where Tung is plainly the one doing it. */
static u8 msgFaceForced;

/* Clears both pieces of speaker state. Called at scene start, and once from
 * globalsInit -- these are file statics, and WRAM is not zeroed at reset, so
 * without that the first line of the first conversation after a CONTINUE reads
 * whoever was in that byte at power-on and asks for portrait 222. */
void msgFaceReset(void) {
    faceLast = FACE_NONE;
    msgFaceForced = FACE_NONE;
}

static u8 faceFromLine(const char *s) {
    u8 i, j;
    const char *p;

    if (s[0] == '"' && faceLast)
        return faceLast;                /* still them, still talking */

    for (i = 0; i < 11; i++) {
        p = facePrefix(i);
        for (j = 0; p[j]; j++) {
            if (s[j] != p[j])
                break;
        }
        if (!p[j]) {
            faceLast = facePrefixId(i);
            return faceLast;
        }
    }
    faceLast = FACE_NONE;
    return FACE_NONE;
}

static void msgWrap(const char *s) {
    u8 line, col, i;
    u8 wordLen;
    const char *w;

    for (line = 0; line < MSG_LINES; line++)
        msgLine[line][0] = 0;

    line = 0;
    col = 0;
    msgTotal = 0;

    while (*s && line < MSG_LINES) {
        if (*s == '\n') {
            msgLine[line][col] = 0;
            line++;
            col = 0;
            s++;
            continue;
        }
        if (*s == ' ') {
            if (col > 0 && col < MSG_COLS) {
                msgLine[line][col] = ' ';
                col++;
                msgTotal++;
            }
            s++;
            continue;
        }

        /* Measure the next word so it can be moved down whole. */
        w = s;
        wordLen = 0;
        while (*w && *w != ' ' && *w != '\n') {
            wordLen++;
            w++;
        }
        if (col + wordLen > MSG_COLS) {
            msgLine[line][col] = 0;
            line++;
            col = 0;
            if (line >= MSG_LINES)
                break;
        }
        for (i = 0; i < wordLen && col < MSG_COLS; i++) {
            msgLine[line][col] = (u8)s[i];
            col++;
            msgTotal++;
        }
        s += wordLen;
    }

    if (line < MSG_LINES)
        msgLine[line][col] = 0;
    msgLines = line + 1;
    if (msgLines > MSG_LINES)
        msgLines = MSG_LINES;
}

void msgOpenAt(const char *s, u8 y) {
    u8 forced;

    msgWrap(s);
    msgY = y;
    msgShown = 0;
    msgDrawn = 0;
    msgHold = 0;
    msgActive = 1;

    forced = msgFaceForced;
    msgFaceForced = FACE_NONE;
    msgFace = forced ? forced : faceFromLine(s);
    if (msgFace) {
        if (msgY >= FACE_BOX_H + 1) {
            faceBoxRow = (u8)(msgY - FACE_BOX_H);
        } else if (forced && msgY + MSG_LINES + 2 + FACE_BOX_H <= SCR_ROWS) {
            faceBoxRow = (u8)(msgY + MSG_LINES + 2);
        } else {
            /* No room either side, or an auto-detected speaker on a box that
             * is not a conversation box. Battle messages land here, and the
             * space under one of those is where the enemies are drawn. */
            msgFace = FACE_NONE;
        }
    }
    msgFaceRuns = msgFace ? 4 : 0;
    msgFaceShown = 0;
    if (!msgFace)
        ppuFacePark();

    winBox(1, msgY, MSG_W, MSG_LINES + 2);
    if (msgFace) {
        winBox(1, faceBoxRow, FACE_BOX_W, FACE_BOX_H);
        msgFaceY = (u8)((faceBoxRow + 1) * 8);
    }
}

void msgOpen(const char *s) {
    msgOpenAt(s, SCR_ROWS - 6);
}

void msgOpenAs(const char *s, u8 face) {
    msgFaceForced = face;
    msgOpen(s);
}

void msgOpenAtAs(const char *s, u8 y, u8 face) {
    msgFaceForced = face;
    msgOpenAt(s, y);
}

void msgClose(void) {
    if (!msgActive)
        return;
    winErase(1, msgY, MSG_W, MSG_LINES + 2);
    if (msgFace) {
        winErase(1, faceBoxRow, FACE_BOX_W, FACE_BOX_H);
        ppuFacePark();
    }
    msgFace = FACE_NONE;
    msgFaceRuns = 0;
    msgFaceShown = 0;
    msgActive = 0;
}

/* Draw the characters revealed so far. Battle repaints the whole text layer
 * every frame, so this has to be callable independently of the reveal step. */
/* Draws characters [from, msgShown). Typing passes the count already on the
 * layer, so a frame costs the two characters it revealed rather than all
 * eighty-one it has revealed so far. */
static void msgDrawFrom(u8 from) {
    u8 line, col, drawn;

    drawn = 0;
    for (line = 0; line < msgLines; line++) {
        for (col = 0; msgLine[line][col]; col++) {
            if (drawn >= msgShown)
                return;
            /* Spaces are left alone for the same reason textPutPal leaves
             * them: glyph 0 is transparent, and writing it into a window
             * punches the backdrop through the gap between two words. */
            if (drawn >= from && msgLine[line][col] != ' ')
                textPutTile(2 + col, msgY + 1 + line,
                            msgLine[line][col] - 32, TXT_ATTR);
            drawn++;
        }
    }
}

void msgRepaint(void) {
    if (!msgActive)
        return;
    msgDrawFrom(0);
    msgDrawn = msgShown;
}

/* Returns 1 while the box is still on screen. The caller polls it and stops
 * doing anything else until it goes to 0, which is what makes dialogue modal
 * without a separate state in every caller. */
u8 msgUpdate(void) {
    if (!msgActive)
        return 0;

    if (msgShown < msgTotal) {
        /* Two characters a frame: fast enough not to annoy, slow enough to
         * read as typing. A on the pad skips to the end. */
        msgShown += 2;
        if (msgShown > msgTotal)
            msgShown = msgTotal;
        if (padTrig & KEY_A)
            msgShown = msgTotal;
        msgDrawFrom(msgDrawn);
        msgDrawn = msgShown;
        return 1;
    }

    /* Fully typed: a short unskippable beat, then A closes it. Without the
     * beat, the A that skipped the typing also closes the box. */
    if (msgHold < 6) {
        msgHold++;
        return 1;
    }
    if (padTrig & (KEY_A | KEY_B | KEY_START)) {
        msgClose();
        return 0;
    }
    return 1;
}

/* ---- transfer ---------------------------------------------------------- */

void textFlush(void) {
    if (!txtDirty)
        return;
    dmaCopyVram(txtMap, VRAM_TEXT_MAP, sizeof(txtMap));
    txtDirty = 0;
}

void textInit(void) {
    txtDirty = 0;
    msgActive = 0;
    textClear();
}
