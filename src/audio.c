/*
 * TUNG TUNG SAHUR -- music and sound effects.
 *
 * gen_music.py writes two Impulse Tracker modules (the score is in themes_*.py,
 * the instruments in orchestra.py) and smconv packs them into res/soundbank,
 * which the SPC700 driver plays out of its own 64KB. The 65816 side only ever
 * posts an index and a command.
 *
 * The fourteen themes are fourteen ranges of one module's order list, not
 * fourteen modules. spcLoad is a multi-frame transfer that also clears SPC
 * memory -- and with it every effect loaded into it -- so switching theme by
 * loading a module would drop the sound effects and stall the frame an
 * encounter starts on. Loaded once at boot, a theme change is a single
 * spcPlay(); and since the SPC reports the *order* it is on, and themes share
 * patterns across their order lists, music.h carries order ranges.
 *
 * Nothing here blocks except the boot sequence: spcPlay posts a message and
 * spcGetMusicPosition is a plain read of REG_APUIO3 with no handshake.
 */
#include "ttrpg.h"
/* Both are generated -- soundbank.h by smconv, music.h by
 * gen_music.py -- and the compiler's include path is the project
 * root, so they are named from there. */
#include "res/soundbank.h"
#include "res/music.h"

/* Two symbols, not one: with real instrument samples the bank is over 32KB, and
 * smconv splits anything over 32KB across consecutive ROM banks and renames
 * the label accordingly. checkbank.py fails the build if that ever flips back
 * to the single-bank form, because the failure is a link error a long way from
 * the cause. */
extern char SOUNDBANK__0, SOUNDBANK__1;

static u8 musicFirst, musicLast;
static u8 musicHold;
static u8 audioReady;

/* Frames to ignore the reported position after asking for a theme. The SPC
 * has not started the new order yet, and reading a stale position inside the
 * old range would re-trigger spcPlay every frame. */
#define MUSIC_SETTLE 12

void audioInit(void) {
    spcBoot();
    /* Reverse order, per pvsneslib's own >32K example: spcSetBank keeps only
     * the bank byte of its argument, so the *last* call is the one that sets
     * the base, and the loader walks forward from there. */
    spcSetBank(&SOUNDBANK__1);
    spcSetBank(&SOUNDBANK__0);

    /* Effects must be loaded *after* spcLoad: that call clears SPC memory. */
    spcStop();
    spcLoad(MOD_TTBGM);
    spcLoadEffect(SFX_CURSOR);
    spcLoadEffect(SFX_CONFIRM);
    spcLoadEffect(SFX_HIT);
    spcLoadEffect(SFX_MAGIC);
    spcLoadEffect(SFX_HEAL);
    spcLoadEffect(SFX_DRUM);
    spcLoadEffect(SFX_ERROR);
    spcLoadEffect(SFX_DEATH);

    audioReady = 1;
    musicFirst = 255;
    musicLast = 255;
    musicHold = 0;
}

/* Idempotent: asking for the theme already playing does nothing, so the
 * victory -> field path does not restart the field theme on the way through. */
void audioMusic(u8 which) {
    u8 first, last;

    if (!audioReady)
        return;

    switch (which) {
    case BGM_TOWN:
        first = MUS_TOWN_FIRST;
        last = MUS_TOWN_LAST;
        break;
    case BGM_FOREST:
        first = MUS_FOREST_FIRST;
        last = MUS_FOREST_LAST;
        break;
    case BGM_SHORE:
        first = MUS_SHORE_FIRST;
        last = MUS_SHORE_LAST;
        break;
    case BGM_SALT:
        first = MUS_SALT_FIRST;
        last = MUS_SALT_LAST;
        break;
    case BGM_FORTRESS:
        first = MUS_FORTRESS_FIRST;
        last = MUS_FORTRESS_LAST;
        break;
    case BGM_HUSH:
        first = MUS_HUSH_FIRST;
        last = MUS_HUSH_LAST;
        break;
    case BGM_BATTLE:
        first = MUS_BATTLE_FIRST;
        last = MUS_BATTLE_LAST;
        break;
    case BGM_BOSS:
        first = MUS_BOSS_FIRST;
        last = MUS_BOSS_LAST;
        break;
    case BGM_FINAL:
        first = MUS_FINAL_FIRST;
        last = MUS_FINAL_LAST;
        break;
    case BGM_FINAL2:
        first = MUS_FINAL2_FIRST;
        last = MUS_FINAL2_LAST;
        break;
    case BGM_FANFARE:
        first = MUS_FANFARE_FIRST;
        last = MUS_FANFARE_LAST;
        break;
    case BGM_TITLE:
        first = MUS_TITLE_FIRST;
        last = MUS_TITLE_LAST;
        break;
    case BGM_ENDING:
        first = MUS_ENDING_FIRST;
        last = MUS_ENDING_LAST;
        break;
    default:
        first = MUS_FIELD_FIRST;
        last = MUS_FIELD_LAST;
        break;
    }

    if (first == musicFirst && last == musicLast)
        return;
    musicFirst = first;
    musicLast = last;
    musicHold = MUSIC_SETTLE;
    spcPlay(first);
}

void audioStop(void) {
    if (!audioReady)
        return;
    musicFirst = 255;
    musicLast = 255;
    musicHold = MUSIC_SETTLE;
    spcStop();
}

/* Per-effect level, high nibble of the volpan byte; the low nibble is pan and
 * 8 is centre. The effects are soft, rounded sounds now (sfx.py), and these
 * are set to sit in the music instead of over it: they used to be full-scale
 * blips played at 13-15 of 15 on top of a mix peaking well below that, which
 * is most of why the game felt loud. A menu tick is quieter than a hit, and
 * the hit is quieter than the drum, which is the title of the game. */
static const u8 sfxVol[8] = {
    4,      /* CURSOR  */
    6,      /* CONFIRM */
    10,     /* HIT     */
    9,      /* MAGIC   */
    8,      /* HEAL    */
    11,     /* DRUM    -- it is the title of the game */
    7,      /* ERROR   */
    11      /* DEATH   */
};

/* The effects are stored at 8kHz, which is DSP pitch 2 (8 is 32kHz, and each
 * step is 4kHz). Storing them at half the rate they used to be is what halves
 * their share of the SPC's 64KB. */
#define SFX_PITCH 2

void audioSfx(u8 which) {
    if (!audioReady || which > 7)
        return;
    spcEffect(SFX_PITCH, which, (u8)(sfxVol[which] * 16 + 8));
}

/* Once a frame, from the V-blank window. Each generated theme ends in a Bxx
 * order jump for a clean loop; this range check remains a guard against a
 * dropped/unsupported tracker command rather than being the audible seam. */
void audioProcess(void) {
    u8 pos;

    if (!audioReady)
        return;

    if (musicHold) {
        musicHold--;
    } else if (musicFirst != 255) {
        pos = spcGetMusicPosition();
        if (pos < musicFirst || pos > musicLast) {
            musicHold = MUSIC_SETTLE;
            spcPlay(musicFirst);
        }
    }

    spcProcess();
}
