/* Optional journeys. Tokens and counters never occupy consumable inventory.
 * All changes are monotonic; a reward is committed before its message opens. */
#include "ttrpg.h"
#include "worldmap.h"

u8 questState[QUEST_COUNT];
u8 questWells, questPatrols;

void questInit(void) {
    u8 i;
    for (i = 0; i < QUEST_COUNT; i++) questState[i] = QUEST_UNKNOWN;
    questWells = 0;
    questPatrols = 0;
}

static void reward(u8 quest, u8 charm, u16 coins) {
    questState[quest] = QUEST_DONE;
    /* Someone who bought the charm already receives its full shop value. */
    if (charmOwned[charm]) coins += charmPriceOf(charm);
    else charmOwned[charm] = 1;
    if (gold > 65535 - coins) gold = 65535;
    else gold += coins;
    audioSfx(SFX_CONFIRM);
}

void questInn(void) {
    switch (questState[QUEST_KETTLE]) {
    case QUEST_UNKNOWN:
        questState[QUEST_KETTLE] = QUEST_ACTIVE;
        msgOpen("BALLERINA CAPPUCCINA: \"Restored, every one of you! Now, a favour. "
                "Gusini borrowed my kettle. Check the cold campfire SOUTH of "
                "the east road and bring it back to this inn. There is a "
                "CINGHIA charm and 100 gold in it.\"  Added to the JOURNAL.");
        break;
    case QUEST_READY:
        reward(QUEST_KETTLE, CHARM_STRAP, 100);
        msgOpen("BALLERINA CAPPUCCINA: \"My kettle! Breakfast has been saved. "
                "Nobody is awake to eat it, but PRINCIPLES.\"  Party restored. "
                "You receive CINGHIA and 100 gold. An owned charm pays its "
                "shop value instead. Equip charms from the field menu.");
        break;
    case QUEST_ACTIVE:
        msgOpen("BALLERINA CAPPUCCINA: \"All rested. The kettle is at the cold "
                "campfire, south of the EAST ROAD. Bring it here. I cannot "
                "boil breakfast by spinning at it. I have tried.\"");
        break;
    default:
        msgOpen("BALLERINA CAPPUCCINA: \"The kettle sings again. Sit! Eat! "
                "Sleep is not rest, it is SURRENDER.\"  The party is restored.");
        break;
    }
}

u8 questEvent(u8 ev) {
    if (curArea != AREA_FIELDS || ev != EV_TALK1) return 0;
    if (questState[QUEST_KETTLE] < QUEST_READY) {
        questState[QUEST_KETTLE] = QUEST_READY;
        audioSfx(SFX_CONFIRM);
        msgOpen("Under Gusini's enormous boot is a kettle. On it, very firmly, "
                "BALLERINA CAPPUCCINA has written INN, KAMPUNG SAHUR. "
                "You take it. Return it to the village inn. JOURNAL updated.");
    } else if (questState[QUEST_KETTLE] == QUEST_READY) {
        msgOpen("You have the kettle. The village inn is waiting for it. "
                "Gusini has kept the boot. A fair division of property.");
    } else {
        msgOpen("The kettle is home. The boot remains. Gusini calls this "
                "travelling light.");
    }
    return 1;
}

u8 questWell(void) {
    u8 bit;
    /* The normal well heal still happens, and the caller saves AFTER this. */
    if (curArea == AREA_FORTRESS) {
        if (questState[QUEST_SHIFT] == QUEST_UNKNOWN) {
            questState[QUEST_SHIFT] = QUEST_ACTIVE;
            msgOpen("A shift ledger hangs by the well. CLEAR THREE PATROLS IN "
                    "LANGIT BESI. REPORT BACK HERE. The pay is a MEZZOGIORNO "
                    "charm and 400 gold. Someone has signed every line "
                    "BOMBARDIRO. JOURNAL updated. Party restored and saved.");
        } else if (questState[QUEST_SHIFT] == QUEST_READY) {
            reward(QUEST_SHIFT, CHARM_NOON, 400);
            msgOpen("Three patrols quiet. The ledger stamps itself OFF DUTY. "
                    "You receive MEZZOGIORNO and 400 gold; an owned charm "
                    "pays its shop value instead. The shift is over. "
                    "The party is restored and saved.");
        } else if (questState[QUEST_SHIFT] == QUEST_ACTIVE) {
            msgOpen("The ledger is still open. Win three ordinary battles "
                    "in LANGIT BESI, then return to this well. Escapes and "
                    "guardian fights do not count. Check the JOURNAL. "
                    "The party is restored and saved.");
        } else return 0;
        return 1;
    }
    if (curArea < AREA_FOREST || curArea > AREA_SALT) return 0;
    if (curArea == AREA_FOREST && questState[QUEST_WELLS] == QUEST_UNKNOWN) {
        if (partyCount <= PC_PATAPIM) return 0;
        questState[QUEST_WELLS] = QUEST_ACTIVE;
        questWells = 1;
        msgOpen("BRR BRR PATAPIM: \"The wells remember waking. My roots can "
                "carry it. This one first. Visit the wells in PANTAI and "
                "PADANG GARAM, then bring me back to this HUTAN well.\" "
                "JOURNAL updated. The party is restored and saved.");
        return 1;
    }
    if (questState[QUEST_WELLS] == QUEST_ACTIVE && partyCount > PC_PATAPIM) {
        bit = (u8)(1 << (curArea - AREA_FOREST));
        if (!(questWells & bit)) {
            questWells |= bit;
            if (questWells == 7) {
                questState[QUEST_WELLS] = QUEST_READY;
                msgOpen("BRR BRR PATAPIM: \"All THREE. Hear it? Water that is "
                        "going somewhere. Take me back to the HUTAN well.\" "
                        "JOURNAL updated. The party is restored and saved.");
            } else {
                msgOpen("Patapim lowers a root into the water. The well "
                        "answers, faintly. Another well restored. "
                        "JOURNAL updated. The party is restored and saved.");
            }
            return 1;
        }
    }
    if (curArea == AREA_FOREST && questState[QUEST_WELLS] == QUEST_READY) {
        reward(QUEST_WELLS, CHARM_BARK, 300);
        msgOpen("BRR BRR PATAPIM: \"Three wells. One current. Even a forest "
                "must learn to move.\"  You receive CORTECCIA and 300 gold; "
                "an owned charm pays its shop value instead. "
                "The party is restored and saved.");
        return 1;
    }
    return 0;
}

void questBattleWon(void) {
    if (curArea != AREA_FORTRESS || battleIsBoss ||
        questState[QUEST_SHIFT] != QUEST_ACTIVE) return;
    if (questPatrols < 3) questPatrols++;
    if (questPatrols == 3) questState[QUEST_SHIFT] = QUEST_READY;
}

const char *questName(u8 id) {
    switch (id) {
    case QUEST_KETTLE: return "A HOT BREAKFAST";
    case QUEST_WELLS: return "WATER REMEMBERS";
    default: return "THE LAST SHIFT";
    }
}

const char *questStatus(u8 id) {
    switch (questState[id]) {
    case QUEST_ACTIVE: return "IN PROGRESS";
    case QUEST_READY: return "RETURN FOR REWARD";
    case QUEST_DONE: return "COMPLETE";
    default: return "NOT STARTED";
    }
}

const char *questHint(u8 id, u8 line) {
    switch (id) {
    case QUEST_KETTLE:
        if (questState[id] == QUEST_DONE) {
            if (!line) return "The kettle is home.";
            if (line == 1) return "Breakfast is possible again.";
            return "Cappuccina still offers rest.";
        }
        if (questState[id] == QUEST_UNKNOWN) {
            if (!line) return "Visit Cappuccina at the inn";
            if (line == 1) return "in northern Kampung Sahur.";
            return "She has lost her kettle.";
        }
        if (questState[id] == QUEST_ACTIVE) {
            if (!line) return "Search the cold campfire";
            if (line == 1) return "south of the east road.";
            return "Bring the kettle to the inn.";
        }
        if (!line) return "Kettle recovered.";
        if (line == 1) return "Return to Cappuccina's inn";
        return "in northern Kampung Sahur.";
    case QUEST_WELLS:
        if (questState[id] == QUEST_DONE) {
            if (!line) return "Three wells share a current.";
            if (line == 1) return "Patapim's roots remember.";
            return "The water is awake again.";
        }
        if (questState[id] == QUEST_UNKNOWN) {
            if (!line) return "Recruit Patapim, then visit";
            if (line == 1) return "the well south of his old";
            return "guard post in Hutan.";
        }
        if (questState[id] == QUEST_READY) {
            if (!line) return "All three wells restored.";
            if (line == 1) return "Return to the Hutan well";
            return "with Patapim to finish.";
        }
        if (!line) return (questWells & 1) ? "HUTAN          RESTORED" : "HUTAN          WAITING";
        if (line == 1) return (questWells & 2) ? "PANTAI         RESTORED" : "PANTAI         WAITING";
        return (questWells & 4) ? "PADANG GARAM   RESTORED" : "PADANG GARAM   WAITING";
    default:
        if (questState[id] == QUEST_DONE) {
            if (!line) return "The fortress shift is over.";
            if (line == 1) return "Three patrols stood down.";
            return "The ledger is closed.";
        }
        if (questState[id] == QUEST_UNKNOWN) {
            if (!line) return "Read the shift ledger at";
            if (line == 1) return "the well in LANGIT BESI.";
            return "The fortress needs relief.";
        }
        if (questState[id] == QUEST_READY) {
            if (!line) return "Three patrols defeated.";
            if (line == 1) return "Return to the fortress well";
            return "to collect your pay.";
        }
        if (!line) return "Win three ordinary battles";
        if (line == 1) return "in LANGIT BESI, then return";
        return "to the fortress well.";
    }
}

u8 questProgress(u8 id) {
    if (id == QUEST_KETTLE) return questState[id] >= QUEST_READY;
    if (id == QUEST_SHIFT) return questPatrols;
    return (questWells & 1) + ((questWells >> 1) & 1) + ((questWells >> 2) & 1);
}

const char *questReward(u8 id) {
    switch (id) {
    case QUEST_KETTLE: return "CINGHIA + 100 GOLD";
    case QUEST_WELLS: return "CORTECCIA + 300 GOLD";
    default: return "MEZZOGIORNO + 400 GOLD";
    }
}
