/*
 * The audition ROM: the same SPC700 driver and the same soundbank layout as
 * the game, and nothing else, so audition.py can play a theme through an
 * emulated SPC and record exactly what the DSP produced.
 *
 * The host writes a command into WRAM (cmdKind, cmdArg, cmdVol, then cmdSeq
 * last); this polls cmdSeq once a frame. audio.c's load sequence is repeated
 * here on purpose -- if the two ever disagree about how the bank is loaded,
 * the audition is no longer of the game.
 */
#include <snes.h>
#include "res/soundbank.h"
#include "bankdefs.h"       /* written by audition.py: one bank or two */

volatile u8 cmdSeq;         /* the host bumps this after filling the rest */
volatile u8 cmdKind;        /* 1 play order, 2 stop, 3 sound effect */
volatile u8 cmdArg;
volatile u8 cmdVol;
volatile u8 ackSeq;
volatile u8 posNow;
static u8 last;

int main(void) {
    u8 i;

    spcBoot();
#ifdef TWO_BANKS
    spcSetBank(&SOUNDBANK__1);
    spcSetBank(&SOUNDBANK__0);
#else
    spcSetBank(&SOUNDBANK__);
#endif
    spcStop();
    spcLoad(MOD_TTBGM);
    for (i = 0; i < 8; i++)
        spcLoadEffect(i);

    setMode(BG_MODE1, 0);
    setScreenOn();
    for (;;) {
        if (cmdSeq != last) {
            last = cmdSeq;
            if (cmdKind == 1)
                spcPlay(cmdArg);
            else if (cmdKind == 2)
                spcStop();
            else if (cmdKind == 3)
                spcEffect(4, cmdArg, (u8)(cmdVol * 16 + 8));
            ackSeq = last;
        }
        posNow = spcGetMusicPosition();
        spcProcess();
        WaitForVBlank();
    }
    return 0;
}
