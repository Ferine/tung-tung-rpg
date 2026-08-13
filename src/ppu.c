/*
 * TUNG TUNG SAHUR -- video setup, the field/battle switch, raster effects.
 *
 * Everything here writes PPU registers, so with one marked exception it is
 * called either from the V-blank window in main() or under forced blank.
 */
#include "ttrpg.h"
#include "gfxmap.h"
#include "sprmap.h"
#include "bgmap.h"
#include "hdmamap.h"
#include "titlemap.h"
#include "worldmap.h"

extern char sprites_til, sprites_til_end;
extern char sprites_pal, sprites_pal_end;
extern char font_til;
extern char font_pal;
extern char fontalert_pal;
extern char fontgood_pal;

s16 scrollX, scrollY;
u8 shakeTimer;
static u8 flashLevel;
static u8 lastFlash;

/* The OBJ size pair currently in force. Re-asserted into $2101 every frame
 * from ppuUpdate rather than once at a mode change: $2101 is write-only, so a
 * stray write from anywhere else would be undetectable after the fact, and
 * re-asserting costs one store. */
static u8 objSizeMode;
static u8 curBackdrop;
static u8 hdmaOn;               /* channels 1 and 2 are live */
static u8 wavePhase;
static u8 waveActive;           /* this region's water moves */
static u8 menuPalettePending;   /* 0 none, 1 open, 2 close; serviced in V-blank */

static void hdmaProgram(u8 *skyTbl, u8 *waveTbl);
static void battlePaletteLoad(u8 which);

/* The tables live in ROM and the linker places them in whichever bank they
 * fit, so the bank byte has to come out of the pointer at run time.
 * dmaMemory is pvsneslib's own union for exactly this: a void* overlaid with
 * an {addr, bank} pair, which gets the bank without a 32-bit shift. */
static dmaMemory tblPtr;

/* CGRAM colour indices. In mode 1 the BG1/BG2 palettes share $00-$7F and OBJ
 * owns $80-$FF (ppu-graphics.md A-17), so the four BG palettes pack in below
 * 64 and the eight OBJ ones start at 128. */
#define CG_FIELD    (PAL_FIELD * 16)
#define CG_BATTLE   (PAL_BATTLE * 16)
#define CG_WIN      (PAL_WIN * 16)

void ppuInit(void) {
    /* Forced blank for all of this: the resident sprite sheet and the font are
     * 16KB of DMA, some six milliseconds, against a 2.4ms V-blank.
     * ppu-graphics.md is explicit that VRAM is accessible in forced blank or
     * V-blank only. */
    REG_INIDISP = 0x80;

    oamInitGfxSet((u8 *)&sprites_til,
                  (u16)(&sprites_til_end - &sprites_til),
                  (u8 *)&sprites_pal,
                  (u16)(&sprites_pal_end - &sprites_pal),
                  0, VRAM_OBJ, OBJ_SIZE16_L32);

    dmaCopyVram((u8 *)&font_til, VRAM_FONT, 8192);
    dmaCopyCGram((u8 *)&font_pal, CG_WIN, 32);

    /* BG1 carries the world, BG2 the windows. BG3 stays off: its four colours
     * would land on CGRAM $00-$1F, which BG1's palette 0 already owns. */
    bgSetGfxPtr(0, VRAM_FIELD_GFX);
    bgSetMapPtr(0, VRAM_FIELD_MAP, SC_64x64);
    bgSetGfxPtr(1, VRAM_FONT);
    bgSetMapPtr(1, VRAM_TEXT_MAP, SC_32x32);

    setMode(BG_MODE1, 0);
    bgSetEnable(0);
    bgSetEnable(1);
    bgSetDisable(2);

    bgSetScroll(1, 0, 0);       /* the text layer never scrolls */

    REG_CGADSUB = 0x00;
    flashLevel = 0;
    lastFlash = 255;
    shakeTimer = 0;
    objSizeMode = OBJ_SIZE16_L32;
    curBackdrop = 255;
    menuPalettePending = 0;
}

/* Called from fieldLoadArea, which is already inside forced blank. Each region
 * brings its own backdrop, so a fight starting in the salt flats does not open
 * on the village's sky. */
void ppuLoadBackdrop(u8 n) {
    if (n == curBackdrop)
        return;
    curBackdrop = n;
    dmaCopyVram(backdropPic(n), VRAM_BATTLE_GFX, 8192);
    dmaCopyVram(backdropMap(n), VRAM_BATTLE_MAP, 2048);
}

/* The title screen is a picture, not a font trick, so it arrives the same way
 * a battle backdrop does -- and through the same VRAM window, because a 32x32
 * map with an 8KB tileset is exactly what a backdrop is.
 *
 * curBackdrop is invalidated on the way out: ppuLoadBackdrop skips the
 * transfer when the region asks for the backdrop it thinks is already there,
 * and after this it is not. */
void ppuLoadTitle(void) {
    ppuHdmaSuspend();
    REG_INIDISP = 0x80;
    dmaCopyVram((u8 *)&title_pic, VRAM_BATTLE_GFX, 8192);
    dmaCopyVram((u8 *)&title_map, VRAM_BATTLE_MAP, 2048);
    dmaCopyCGram((u8 *)&title_pal, CG_BATTLE, 32);
    REG_INIDISP = fadeLevel;
    curBackdrop = 255;
}


/* Two runs of CGRAM rotated in place: four entries walk the shine down the
 * logo, three make the stars twinkle. Nothing in VRAM moves, no tile is
 * rewritten, and the whole effect is fourteen writes to $2122.
 *
 * CGRAM takes writes in forced blank, V-blank or H-blank (ppu-graphics.md);
 * this is called from main()'s V-blank window. $2121 sets the entry and $2122
 * is written twice per colour -- low byte then high -- with the address
 * stepping after the second, which is what lets a run be written without
 * touching $2121 again. */
void ppuTitleCycle(void) {
    u8 i, phase;
    u16 c;

    if (gameState != ST_TITLE)
        return;

    phase = (u8)((frameCounter >> 2) & 3);
    REG_CGADD = (u8)(CG_BATTLE + TITLE_LOGO0);
    for (i = 0; i < TITLE_LOGO_N; i++) {
        c = titleLogoRamp[(i + phase) & 3];
        *CGRAM_PALETTE = (u8)c;
        *CGRAM_PALETTE = (u8)(c >> 8);
    }

    phase = (u8)(((frameCounter >> 4) & 0xFF) % TITLE_STAR_N);
    REG_CGADD = (u8)(CG_BATTLE + TITLE_STAR0);
    for (i = 0; i < TITLE_STAR_N; i++) {
        c = titleStarRamp[(i + phase) % TITLE_STAR_N];
        *CGRAM_PALETTE = (u8)c;
        *CGRAM_PALETTE = (u8)(c >> 8);
    }
}


/* The two modes differ only in which VRAM windows BG1 points at and which pair
 * of OBJ sizes $2101 offers, so switching is register writes, not transfers. */
void ppuSetFieldMode(void) {
    bgSetGfxPtr(0, VRAM_FIELD_GFX);
    bgSetMapPtr(0, VRAM_FIELD_MAP, SC_64x64);
    objSizeMode = OBJ_SIZE16_L32;
    REG_OBSEL = objSizeMode | (VRAM_OBJ >> 13);

    /* Put the region's own palettes back. Battle borrows slots 0 and 1 for
     * red and green glyphs, and without this the world came back from every
     * fight wearing them -- pale lavender ground and orange trees, for the
     * rest of the session. CGRAM is writable in forced blank, V-blank or
     * H-blank (ppu-graphics.md); this is called from a state change, which is
     * none of them, so it makes its own window. */
    ppuHdmaSuspend();
    REG_INIDISP = 0x80;
    dmaCopyCGram(areaPal(curArea), 0, 64);
    REG_INIDISP = fadeLevel;
    /* Top-down, so no sky -- just a vignette, and no shimmer: the scroll
     * table would have to be rebuilt from the camera every frame. */
    waveActive = 0;
    hdmaProgram((u8 *)&sky_field_tbl, 0);
}

void ppuSetBattleMode(void) {
    /* State changes are driven from the visible-frame logic after the fade
     * reaches brightness zero.  Brightness zero is still an active display,
     * not forced blank, so keep the complete mode/palette change blanked.
     * CGRAM DMA is only valid in forced blank, V-blank or H-blank. */
    ppuHdmaSuspend();
    REG_INIDISP = 0x80;

    bgSetGfxPtr(0, VRAM_BATTLE_GFX);
    bgSetMapPtr(0, VRAM_BATTLE_MAP, SC_32x32);
    objSizeMode = OBJ_SIZE32_L64;
    REG_OBSEL = objSizeMode | (VRAM_OBJ >> 13);
    /* The size pair changes underneath any OBJ still on screen: a portrait
     * left showing would come back as a 64x64 read of whatever follows it. */
    ppuFacePark();

    /* Zero the camera, not just the scroll registers: ppuUpdate rewrites BG1's
     * scroll from scrollX/scrollY every frame, so leaving the field camera in
     * them slides the backdrop by wherever the player was standing. */
    scrollX = 0;
    scrollY = 0;
    bgSetScroll(0, 0, 0);

    /* Red and green glyphs for the duration. The backdrop's tilemap only ever
     * names palette 2, so 0 and 1 are free here. */
    dmaCopyCGram((u8 *)&fontalert_pal, PAL_ALERT * 16, 32);
    dmaCopyCGram((u8 *)&fontgood_pal, PAL_GOOD * 16, 32);
    battlePaletteLoad(0);

    /* Water for the shore, heat for the salt, drift for the void. */
    waveActive = (curBackdrop == 2 || curBackdrop == 3 || curBackdrop == 5);
    wavePhase = 0;
    hdmaProgram(skyTable(curBackdrop),
                waveActive ? waveTable(0) : (u8 *)0);
    REG_INIDISP = fadeLevel;
}

/* The field menu wants red and green glyphs, which live in BG palettes 0 and
 * 1 -- and on the field those two are region art. The menu covers the screen
 * with windows, so BG1 is not visible while it is open and the swap is safe;
 * closing it puts the region back. */
void ppuMenuPalette(u8 on) {
    /* Menu input is processed during the visible frame. Queue the CGRAM DMA
     * for ppuUpdate instead of relying on brightness or emulator tolerance;
     * CGRAM is not generally writable during active display. */
    menuPalettePending = on ? 1 : 2;
}

/* 0 = the region's own sky, 1 = the dawn recolour the epilogue runs on. */
static void battlePaletteLoad(u8 which) {
    dmaCopyCGram(which ? (u8 *)&bg_dawn_pal : backdropPal(curBackdrop),
                 CG_BATTLE, 32);
}

void ppuBattlePalette(u8 which) {
    /* This is used by the ending state from visible-frame logic, just like a
     * mode transition. Suspend H-DMA before the general DMA, keep CGRAM in a
     * legal access period, then restore the raster program for the new frame. */
    ppuHdmaSuspend();
    REG_INIDISP = 0x80;
    battlePaletteLoad(which);
    hdmaProgram(skyTable(curBackdrop),
                waveActive ? waveTable(wavePhase) : (u8 *)0);
    REG_INIDISP = fadeLevel;
}

/* ---- raster effects ----------------------------------------------------
 *
 * Two H-DMA channels. The eight DMA channels are shared between general
 * purpose and H-DMA and the manual is explicit that one channel must not do
 * both (cpu-system.md, $420B). Two are already spoken for: channel 0 by every
 * pvsneslib GP-DMA, channel 7 by the OAM copy the library's NMI issues. So the
 * raster takes 1 and 2.
 *
 *   ch1 -> $2132 COLDATA   one byte a line: the sky gradient and vignette
 *   ch2 -> $210D BG1HOFS   two bytes a line, write-twice: the water shimmer
 *
 * Colour math is left on permanently in subtract mode and the table decides
 * how much lands on each line, so there is no "off" state to switch to -- a
 * level of zero subtracts nothing.
 */
static void hdmaProgram(u8 *skyTbl, u8 *waveTbl) {
    /* Write mode 000: one byte to one address. */
    REG_DMAP1 = 0x00;
    REG_BBAD1 = 0x32;
    tblPtr.mem.p = skyTbl;
    REG_A1T1LH = tblPtr.mem.c.addr;
    REG_A1B1 = tblPtr.mem.c.bank;

    if (waveTbl) {
        /* Write mode 010: two bytes to one address, which is exactly the
         * low-then-high protocol a write-twice scroll register wants
         * (cpu-system.md, table 2-17-2). */
        REG_DMAP2 = 0x02;
        REG_BBAD2 = 0x0D;
        tblPtr.mem.p = waveTbl;
        REG_A1T2LH = tblPtr.mem.c.addr;
        REG_A1B2 = tblPtr.mem.c.bank;
    }

    REG_CGWSEL = 0x00;          /* the constant, not the sub screen */
    REG_CGADSUB = 0xA1;         /* subtract, BG1 and the backdrop */
    REG_HDMAEN = waveTbl ? 0x06 : 0x02;
    hdmaOn = 1;
}

/* Programming Caution #1: a general-purpose DMA that *finishes* during the
 * first 2.24us of an H-Blank on lines 0-224 while H-DMA is in use may hang the
 * CPU. The stated fix is to confine GP-DMA to V-blank. The text-layer transfer
 * already obeys that; a region load does not and cannot -- it moves 16KB in
 * one go, forty times the V-blank window, which is why it runs under forced
 * blank. Forced blank stops the PPU fetching pixels but it does not stop
 * H-Blank happening, so the hazard is live and the channels come off first. */
void ppuHdmaSuspend(void) {
    REG_HDMAEN = 0x00;
    hdmaOn = 0;
}

void ppuFlash(u8 frames) {
    flashLevel = frames;
}

/* $2106: high nibble is the block size, low nibble the per-BG enables. Only
 * BG1 is mosaicked -- running it over the window layer turns the text into
 * porridge, and the transition is about the world dissolving, not the UI. */
void ppuMosaic(u8 level) {
    REG_MOSAIC = (u8)((level << 4) | (level ? 0x01 : 0x00));
}

void ppuShake(u8 frames) {
    shakeTimer = frames;
}

/* Called once a frame from the V-blank window. */
/* --- tile animation ------------------------------------------------------
 *
 * Five regions keep their moving characters at the head of the tileset --
 * gen_world.py reserves them there precisely so this is one transfer and not
 * eight. Four phases live in ROM; the frame counter picks one and DMAs 128 or
 * 256 bytes over characters 0..n-1 of the BG1 field base.
 *
 * This must run inside the V-blank window and nowhere else: ppu-graphics.md is
 * explicit that VRAM takes writes in forced blank or V-blank only, and the
 * silent failure mode -- a transfer that simply does nothing -- is the same one
 * that made every enemy in the game invisible. Called from main()'s V-blank
 * block, after the NMI's own OAM copy on channel 7 has finished.
 */
void ppuAnimateTiles(void) {
    u8 n = areaAnimTiles[curArea];

    if (!n || gameState != ST_FIELD)
        return;
    if ((frameCounter & 7) != 0)      /* eight frames a phase, 1.9 Hz round */
        return;

    animPhase = (animPhase + 1) & 3;
    dmaCopyVram(areaAnm(curArea) + (u16)animPhase * (u16)n * 32,
                VRAM_FIELD_GFX, (u16)n * 32);
}


/* --- dialogue portraits --------------------------------------------------
 *
 * 512 bytes of art per speaker. That will not fit in a V-blank next to the
 * OAM copy the NMI already issued and the text-layer DMA behind it, so it goes
 * one character row -- 128 bytes, four characters -- per frame, and the OBJ is
 * not shown until all four have landed. The box types its text in over rather
 * more than four frames, so the wait is invisible.
 *
 * A 32x32 OBJ's rows sit 16 names apart (A-4), which is why this is four
 * transfers rather than one, and why gen_sprites writes the art block-row-
 * major in the first place.
 *
 * Frames where ppuAnimateTiles runs are skipped: it wants the same V-blank and
 * neither of them is urgent.
 */
void ppuFaceService(void) {
    u8 run;

    if (!msgFaceRuns)
        return;
    if ((frameCounter & 7) == 0)
        return;

    run = (u8)(4 - msgFaceRuns);
    dmaCopyVram(&portraits_pic + ((u16)(msgFace - 1) * 512) + (u16)run * 128,
                (u16)(VRAM_OBJ_FACE + (u16)run * 256), 128);
    msgFaceRuns--;

    if (!msgFaceRuns) {
        /* Priority 3. A-19 puts OBJ.3 in front of BG2.1, and BG2.1 is the
         * window the portrait has to sit on top of; at the priority 2 the rest
         * of the game uses, the frame would be drawn over its own face. */
        oamSet(FACE_OAM, 16, (u16)msgFaceY, 3, 0, 0,
               FACE_OBJ_NAME, facePal[msgFace - 1]);
        oamSetEx(FACE_OAM, OBJ_LARGE, OBJ_SHOW);
        msgFaceShown = 1;
    }
}

void ppuFacePark(void) {
    oamSet(FACE_OAM, 0, OAM_PARK_Y, 3, 0, 0, FACE_OBJ_NAME, 0);
    oamSetEx(FACE_OAM, OBJ_SMALL, OBJ_HIDE);
    msgFaceShown = 0;
}


void ppuUpdate(void) {
    s16 sx, sy;
    u8 level;

    REG_OBSEL = objSizeMode | (VRAM_OBJ >> 13);

    if (menuPalettePending) {
        if (menuPalettePending == 1) {
            /* BG1 goes off with the field palettes. A glyph's background is
             * transparent, so leaving BG1 visible shows recoloured map pixels
             * through every letter. */
            bgSetDisable(0);
            dmaCopyCGram((u8 *)&fontalert_pal, PAL_ALERT * 16, 32);
            dmaCopyCGram((u8 *)&fontgood_pal, PAL_GOOD * 16, 32);
        } else {
            dmaCopyCGram(areaPal(curArea), 0, 64);
            bgSetEnable(0);
        }
        menuPalettePending = 0;
    }

    /* --- white flash ---------------------------------------------------
     *
     * Constant-colour addition rather than a brightness spike: $2100 would
     * wash the whole frame including the windows, and it fights the fade.
     * ppu-graphics.md 7.2 gives the sequence -- clear $2130 D1 so the constant
     * is used instead of the sub screen, enable the layers in $2131, write the
     * level to $2132. $E0 selects all three channels at once, so the add stays
     * neutral. */
    if (flashLevel) {
        /* The flash and the gradient both want $2132, so the channel comes
         * off for the duration and goes back on when it is done. */
        level = flashLevel;
        if (level > 31)
            level = 31;
        REG_HDMAEN = 0x00;
        REG_CGWSEL = 0x00;
        REG_CGADSUB = 0x3F;             /* add, every layer and the backdrop */
        REG_COLDATA = 0xE0 | level;
        flashLevel--;
        lastFlash = 1;
    } else if (lastFlash) {
        REG_CGADSUB = 0xA1;             /* back to subtract for the gradient */
        REG_HDMAEN = waveActive ? 0x06 : 0x02;
        hdmaOn = 1;
        lastFlash = 0;
    }

    /* Advance which phase table channel 2 reads. The tables are in ROM and
     * never change; only the address does, which is three stores a frame
     * instead of rebuilding 450 bytes. */
    if (waveActive && hdmaOn && (frameCounter & 3) == 0) {
        u8 *w;

        wavePhase = (u8)((wavePhase + 1) & (WAVE_PHASES - 1));
        w = waveTable(wavePhase);
        tblPtr.mem.p = w;
        REG_A1T2LH = tblPtr.mem.c.addr;
        REG_A1B2 = tblPtr.mem.c.bank;
    }

    /* --- shake ---------------------------------------------------------
     *
     * Offsetting BG1's scroll, not the camera: the camera is what collision
     * and the tile lookup use, and shaking it would move the world. */
    sx = scrollX;
    sy = scrollY;
    if (shakeTimer) {
        shakeTimer--;
        sx += (shakeTimer & 2) ? 3 : -3;
        sy += (shakeTimer & 4) ? 2 : -2;
    }
    bgSetScroll(0, (u16)sx, (u16)sy);
}
