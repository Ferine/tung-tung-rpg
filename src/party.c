/*
 * TUNG TUNG SAHUR -- the party: who they are, what they learn, what they carry.
 *
 * The party grows across the acts: Tung alone, then Patapim, Tralalero,
 * Lirili, Bombardiro. partyCount is the number recruited and every loop in the
 * battle engine is bounded by it, so a character who has not joined yet simply
 * does not exist rather than existing and being hidden.
 *
 * Names and skill names come back as literals from a switch rather than out of
 * a table of pointers. tcc will build a `const char *const[]`, but the
 * relocations it emits for one in a LoROM bank are not worth the argument; a
 * switch costs a few bytes and is unambiguous.
 */
#include "ttrpg.h"

/* ---- who they are ------------------------------------------------------ */

const char *partyNameOf(u8 who) {
    switch (who) {
    case PC_TUNG:
        return "TUNG";
    case PC_PATAPIM:
        return "PATAPIM";
    case PC_TRALA:
        return "TRALA";
    case PC_LIRILI:
        return "LIRILI";
    default:
        return "BOMBARD";
    }
}

/* What each of them refuses to lie down with. */
const char *partyTitleOf(u8 who) {
    switch (who) {
    case PC_TUNG:
        return "il tamburo";
    case PC_PATAPIM:
        return "le radici";
    case PC_TRALA:
        return "tre scarpe";
    case PC_LIRILI:
        return "il tempo";
    default:
        return "l ordigno";
    }
}

/* Base stats and per-level gains. Tung is the middle of everything, Patapim
 * the wall, Tralalero the gauge, Lirili the magic, Bombardiro the artillery
 * that arrives late and hits like it. */
static void statsFor(u8 who, u8 level) {
    u16 lv;

    lv = level - 1;
    switch (who) {
    case PC_TUNG:
        pcHPMax[who] = 155 + lv * 26;
        pcMPMax[who] = 12 + lv * 3;
        pcAtk[who] = 15 + lv * 3;
        pcDef[who] = 11 + lv * 2;
        pcMag[who] = 5 + lv;
        /* 7 left him acting once for every two swings of anything quick, and
         * act one is walked alone. */
        pcSpd[who] = 9 + (lv >> 1);
        break;
    case PC_PATAPIM:
        pcHPMax[who] = 185 + lv * 34;
        pcMPMax[who] = 8 + lv * 2;
        pcAtk[who] = 13 + lv * 3;
        pcDef[who] = 18 + lv * 3;
        pcMag[who] = 4 + lv;
        pcSpd[who] = 5 + (lv / 3);
        break;
    case PC_TRALA:
        pcHPMax[who] = 100 + lv * 19;
        pcMPMax[who] = 10 + lv * 3;
        pcAtk[who] = 13 + lv * 3;
        pcDef[who] = 8 + lv;
        pcMag[who] = 6 + lv;
        pcSpd[who] = 15 + lv;
        break;
    case PC_LIRILI:
        pcHPMax[who] = 82 + lv * 15;
        pcMPMax[who] = 32 + lv * 7;
        pcAtk[who] = 8 + lv;
        pcDef[who] = 7 + lv;
        pcMag[who] = 15 + lv * 3;
        pcSpd[who] = 9 + (lv >> 1);
        break;
    default:
        pcHPMax[who] = 150 + lv * 28;
        pcMPMax[who] = 20 + lv * 5;
        pcAtk[who] = 17 + lv * 3;
        pcDef[who] = 13 + lv * 2;
        pcMag[who] = 12 + lv * 2;
        pcSpd[who] = 8 + (lv >> 1);
        break;
    }
}

/* ---- charms ------------------------------------------------------------ */

const char *charmNameOf(u8 id) {
    switch (id) {
    case CHARM_STRAP:
        return "CINGHIA";
    case CHARM_BARK:
        return "CORTECCIA";
    case CHARM_LACE:
        return "LACCIO";
    case CHARM_SPECS:
        return "SEI DITA";     /* an extra finger or two. It happens. */
    case CHARM_SKIN:
        return "PELLACCIA";
    case CHARM_NOON:
        return "MEZZOGIORNO";
    default:
        return "-";
    }
}

u16 charmPriceOf(u8 id) {
    switch (id) {
    case CHARM_STRAP:
        return 380;
    case CHARM_BARK:
        return 420;
    case CHARM_LACE:
        return 360;
    case CHARM_SPECS:
        return 460;
    case CHARM_SKIN:
        return 500;
    case CHARM_NOON:
        return 1400;
    default:
        return 0;
    }
}

static void applyCharm(u8 who) {
    switch (pcCharm[who]) {
    case CHARM_STRAP:
        pcAtk[who] += 8;
        break;
    case CHARM_BARK:
        pcDef[who] += 8;
        break;
    case CHARM_LACE:
        pcSpd[who] += 6;
        break;
    case CHARM_SPECS:
        pcMag[who] += 8;
        break;
    case CHARM_SKIN:
        pcHPMax[who] += 120;
        break;
    case CHARM_NOON:
        pcAtk[who] += 5;
        pcDef[who] += 5;
        pcMag[who] += 5;
        pcSpd[who] += 3;
        pcHPMax[who] += 60;
        break;
    default:
        break;
    }
}

/* Recomputes every derived stat from level and charm. Called after a level-up
 * and after any charm change, so there is exactly one place where a stat is
 * decided and no way for the two to disagree. */
void partyApplyStats(void) {
    u8 i;

    for (i = 0; i < PARTY_MAX; i++) {
        statsFor(i, pcLevel[i]);
        applyCharm(i);
        if (pcHP[i] > pcHPMax[i])
            pcHP[i] = pcHPMax[i];
        if (pcMP[i] > pcMPMax[i])
            pcMP[i] = pcMPMax[i];
    }
}

/* ---- lifecycle --------------------------------------------------------- */

void partyInit(void) {
    u8 i;

    for (i = 0; i < PARTY_MAX; i++) {
        pcLevel[i] = 1;
        pcExp[i] = 0;
        pcStatus[i] = 0;
        pcCharm[i] = CHARM_NONE;
        statsFor(i, 1);
        pcHP[i] = pcHPMax[i];
        pcMP[i] = pcMPMax[i];
    }
    for (i = 0; i < ITEM_COUNT; i++)
        itemCount[i] = 0;
    for (i = 0; i < CHARM_COUNT; i++)
        charmOwned[i] = 0;

    itemCount[ITEM_HERB] = 5;
    itemCount[ITEM_COFFEE] = 3;
    itemCount[ITEM_BOMB] = 2;
    gold = 150;
    partyCount = 1;             /* Tung walks out of the village alone */
}

/* A new member arrives at the party's current level, not at level 1: an act
 * five recruit at level 1 is a corpse with a name. */
void partyRecruit(u8 who) {
    u8 i, best;

    best = 1;
    for (i = 0; i < partyCount; i++)
        if (pcLevel[i] > best)
            best = pcLevel[i];

    pcLevel[who] = best;
    pcExp[who] = 0;
    pcStatus[who] = 0;
    statsFor(who, best);
    applyCharm(who);
    pcHP[who] = pcHPMax[who];
    pcMP[who] = pcMPMax[who];

    if (partyCount <= who)
        partyCount = (u8)(who + 1);
}

u16 partyExpNext(u8 who) {
    u16 lv;

    lv = pcLevel[who];
    return (u16)(lv * 20) + (u16)(lv * lv * 4);
}

/* Experience is shared, not split -- a party that loses a member should not
 * fall behind for it. Returns 1 if anyone gained a level. */
u8 partyGainExp(u16 amount) {
    u8 i;
    u8 levelled;
    u16 hpGain, mpGain;

    levelled = 0;
    for (i = 0; i < partyCount; i++) {
        if (pcStatus[i] & STAT_DEAD)
            continue;
        pcExp[i] += amount;
        while (pcExp[i] >= partyExpNext(i) && pcLevel[i] < 60) {
            pcExp[i] -= partyExpNext(i);
            pcLevel[i]++;

            /* Current HP moves with the maximum, so a level-up mid-fight is a
             * reward rather than a bar getting longer behind you. */
            hpGain = pcHPMax[i];
            mpGain = pcMPMax[i];
            statsFor(i, pcLevel[i]);
            applyCharm(i);
            pcHP[i] += pcHPMax[i] - hpGain;
            pcMP[i] += pcMPMax[i] - mpGain;
            levelled = 1;
        }
    }
    return levelled;
}

u8 partyAlive(void) {
    u8 i, n;

    n = 0;
    for (i = 0; i < partyCount; i++)
        if (!(pcStatus[i] & STAT_DEAD))
            n++;
    return n;
}

/* ---- skills ------------------------------------------------------------ */

const u8 skillMP[SKILL_COUNT] = {
    8, 6, 14,           /* Tung:    SAHUR, SMASH, ROLL      */
    6, 10,              /* Patapim: ROOT, SHELTER           */
    8, 6, 16,           /* Trala:   KICK, SPRINT, RIPTIDE   */
    6, 22, 8, 6,        /* Lirili:  CURA, CURAGA, ZAP, SLOW */
    9, 20               /* Bombard: STRAFE, BOMBRUN         */
};

/* For the physical kinds this is a percentage bonus on the finished damage;
 * for the magic and healing kinds it is the flat base the formula starts from.
 * The two are not the same scale and never were. */
const u8 skillPower[SKILL_COUNT] = {
    26, 60, 44,
    70, 0,
    0, 0, 40,
    64, 46, 34, 0,
    10, 58
};

const u8 skillKind[SKILL_COUNT] = {
    SK_MAGIC_ALL, SK_PHYS_ONE, SK_MAGIC_ALL,
    SK_PHYS_ONE, SK_GUARD_ALL,
    SK_PHYS_TRIPLE, SK_HASTE_SELF, SK_MAGIC_ALL,
    SK_HEAL_ONE, SK_HEAL_ALL, SK_MAGIC_ONE, SK_SLOW_ONE,
    SK_PHYS_TRIPLE, SK_MAGIC_ALL
};

/* The level each is learned at. A character joining in act five arrives at the
 * party's level and therefore arrives with their whole list. */
const u8 skillLevel[SKILL_COUNT] = {
    1, 1, 9,
    1, 5,
    1, 1, 11,
    1, 14, 1, 4,
    1, 1
};

const char *skillNameOf(u8 id) {
    switch (id) {
    case SKILL_SAHUR:
        return "SAHUR!";
    case SKILL_SMASH:
        return "MAZZATA";
    case SKILL_ROLL:
        return "TAMBURATA";
    case SKILL_ROOT:
        return "RADICI!";
    case SKILL_SHELTER:
        return "RIPARO";
    case SKILL_KICK:
        return "TRE SCARPE";
    case SKILL_SPRINT:
        return "VELOCE!";
    case SKILL_RIPTIDE:
        return "RISACCA";
    case SKILL_CURA:
        return "CURA";
    case SKILL_CURAGA:
        return "CURAGA";
    case SKILL_ZAP:
        return "ZAPPO";
    case SKILL_SLOW:
        return "LENTISSIMO";
    case SKILL_STRAFE:
        return "MITRAGLIA";
    default:
        return "BOMBARDATA";
    }
}

static u8 skillBase(u8 who) {
    switch (who) {
    case PC_TUNG:
        return SKILL_SAHUR;
    case PC_PATAPIM:
        return SKILL_ROOT;
    case PC_TRALA:
        return SKILL_KICK;
    case PC_LIRILI:
        return SKILL_CURA;
    default:
        return SKILL_STRAFE;
    }
}

static u8 skillTotal(u8 who) {
    switch (who) {
    case PC_TUNG:
        return 3;
    case PC_PATAPIM:
        return 2;
    case PC_TRALA:
        return 3;
    case PC_LIRILI:
        return 4;
    default:
        return 2;
    }
}

u8 partySkillCount(u8 who) {
    u8 i, n, base;

    base = skillBase(who);
    n = 0;
    for (i = 0; i < skillTotal(who); i++)
        if (pcLevel[who] >= skillLevel[base + i])
            n++;
    return n;
}

/* Walks the list skipping what is not learned yet, so an unlearned skill in
 * the middle does not leave a hole in the menu. */
u8 partySkillAt(u8 who, u8 index) {
    u8 i, n, base;

    base = skillBase(who);
    n = 0;
    for (i = 0; i < skillTotal(who); i++) {
        if (pcLevel[who] < skillLevel[base + i])
            continue;
        if (n == index)
            return (u8)(base + i);
        n++;
    }
    return base;
}

/* ---- items ------------------------------------------------------------- */

/* The healing items are literally slop. It is the raw material, so of course
 * you eat it to get better; nobody in this world finds that strange. */
const char *itemNameOf(u8 id) {
    switch (id) {
    case ITEM_HERB:
        return "SLOP FRESCO";
    case ITEM_SALVE:
        return "SLOP DENSO";
    case ITEM_COFFEE:
        return "CAPPUCCINO";
    case ITEM_TONIC:
        return "TONICO";
    case ITEM_BOMB:
        return "BOMBETTA";
    case ITEM_THUNDER:
        return "TUONO VASO";
    case ITEM_ELIXIR:
        return "ELISIR";
    default:
        return "TE DI SAHUR";
    }
}

u16 itemPriceOf(u8 id) {
    switch (id) {
    case ITEM_HERB:
        return 30;
    case ITEM_SALVE:
        return 150;
    case ITEM_COFFEE:
        return 50;
    case ITEM_TONIC:
        return 120;
    case ITEM_BOMB:
        return 90;
    case ITEM_THUNDER:
        return 300;
    case ITEM_ELIXIR:
        return 400;
    default:
        return 900;
    }
}

/* Which items want an ally under the cursor. The rest either hit everything or
 * affect the whole party, and asking who to point a bomb at is a menu step
 * that answers itself. */
u8 itemTargetsAlly(u8 id) {
    switch (id) {
    case ITEM_BOMB:
    case ITEM_THUNDER:
    case ITEM_TEA:
        return 0;
    default:
        return 1;
    }
}
