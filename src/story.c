/*
 * TUNG TUNG SAHUR -- i sei atti, and the scenes that move between them.
 *
 * A scene is a numbered sequence of lines. storyUpdate advances one line each
 * time the message box closes and calls sceneEnd when it runs out -- so a
 * scene is a switch on (scene, step) returning the next line, and the only
 * state is two bytes. A general script interpreter would need a bytecode, a
 * string table and a relocation story in a LoROM bank; this needs none of them.
 *
 * The act is the gate. storyMayLeave refuses the exits the player has not
 * earned, so the road is walked in order without one locked door needing art.
 *
 * ---- on the voice ----------------------------------------------------------
 *
 * The cast is the Italian brainrot canon and the narration is written the way
 * those lore videos are narrated: deadpan, epic, entirely unbothered by how
 * stupid the premise is, absurd facts stated as settled history. The places
 * are Indonesian because Tung Tung Tung Sahur is, and the people are Italian
 * because they are; that collision IS the genre, not a mistake in it.
 *
 * ---- on SLOP ---------------------------------------------------------------
 *
 * SLOP is the world's material. Not an insult -- the substance. Everyone here
 * was generated, everyone knows it, and none of them find it interesting.
 * A shark has three shoes; a tree has legs; a crocodile is also an aeroplane.
 * That is just what they were made out of.
 *
 * The antagonist is slop that wants to stay smooth: an infinite, comfortable,
 * frictionless feed where nothing ever happens again and everyone is very
 * relaxed about it. The party is slop that decided to WAKE UP. That is the
 * only difference between them and it is the whole game.
 */
#include "ttrpg.h"
#include "sprmap.h"   /* FACE_* */
#include "worldmap.h"

/* act and storyFlags live in globals.c: the save block writes both, and a
 * static here would mean save.c reaching into another unit's internals. */
static u8 sceneFace(u8 sc, u8 n);

#define F_ELDER    0x01         /* la nonna has spoken */
#define F_BOSSDONE 0x02         /* this act's guardian is beaten */

#define SC_NONE       0
#define SC_OPENING    1
#define SC_ELDER      2
#define SC_PATAPIM    3
#define SC_PATAPIM_W  4
#define SC_TRALA      5
#define SC_TRALA_W    6
#define SC_LIRILI     7
#define SC_LIRILI_W   8
#define SC_BOMBARD    9
#define SC_BOMBARD_W 10
#define SC_SILENZIO  11
#define SC_SILENZIO_W 12
#define SC_GATE      13

static u8 scene;
static u8 step;

void storyInit(void) {
    act = ACT_VILLAGE;
    storyFlags = 0;
    scene = SC_NONE;
    step = 0;
}

/* Kept short: the menu footer prints this at column 18 of 32. */
const char *storyActName(void) {
    switch (act) {
    case ACT_VILLAGE:
        return "I LA CHIAMATA";
    case ACT_FOREST:
        return "II IL BOSCO";
    case ACT_SHORE:
        return "III LA RIVA";
    case ACT_SALT:
        return "IV IL SALE";
    case ACT_FORTRESS:
        return "V IL CIELO";
    case ACT_HUSH:
        return "VI LA SBOBBA";
    default:
        return "SAHUR!";
    }
}

/* ---- le battute -------------------------------------------------------- */

static const char *sceneLine(u8 sc, u8 n) {
    switch (sc) {
    case SC_OPENING:
        switch (n) {
        case 0:
            return "Ecco. TUNG TUNG TUNG SAHUR beats the first call. "
                   "TUNG. TUNG. TUNG. It goes the length of the village and "
                   "comes all the way back.";
        case 1:
            return "Nobody wakes up. Not one shutter. Not one nonna. "
                   "Mamma mia. This has never happened in the history of the "
                   "village, and the village has a LOT of history. "
                   "Most of it invented last Tuesday.";
        case 2:
            return "He beats it again. TUNG TUNG TUNG. Niente. "
                   "A cat watches him. The cat is also asleep. "
                   "The cat is asleep STANDING UP. It has five legs. "
                   "Nobody has ever mentioned the legs.";
        case 3:
            return "Everything here was generated. Everyone knows. Nobody "
                   "cares -- being made of slop is not a problem, it is just "
                   "the material. The problem is that the slop has stopped "
                   "MOVING.";
        case 4:
            return "One door opens. It is LA NONNA. She is furious, "
                   "which is the only good sign so far.";
        default:
            return 0;
        }

    case SC_ELDER:
        switch (n) {
        case 0:
            return "LA NONNA: \"Tung. TUNG. I know. Three nights you bang "
                   "that thing. It is not the arm. The arm is bellissimo.\"";
        case 1:
            return "\"Something came up the east road and took the WAKING out "
                   "of people. Took it. Like a wallet.\"";
        case 2:
            return "\"We are all slop, Tung. Slop that gets UP. That is the "
                   "entire recipe. Somebody out there wants the second half "
                   "removed.\"";
        case 3:
            return "\"A drum is a good argument. It is not the ONLY argument. "
                   "Find the ones who never sleep. They are insufferable. "
                   "This is WHY they never sleep.\"";
        case 4:
            return "\"Go east. Take the bat. And Tung -- if a shark starts "
                   "explaining his shoes, let him finish. It is faster.\"";
        default:
            return 0;
        }

    case SC_PATAPIM:
        switch (n) {
        case 0:
            return "The road ends in something enormous. It has a face. "
                   "It has legs -- three of them, and no plan to discuss it. "
                   "It is, technically, a tree.";
        case 1:
            return "BRR BRR PATAPIM: \"CHI VA LA! Three nights I stand here! "
                   "THREE! Everything that comes up this path is one of Them!\"";
        case 2:
            return "\"I stopped checking on night one. It was going SO well.\"";
        case 3:
            return "\"Show me you are awake, tamburino. BRR. BRR.\"";
        default:
            return 0;
        }

    case SC_PATAPIM_W:
        switch (n) {
        case 0:
            return "PATAPIM sits down. This takes eleven seconds and a "
                   "quantity of the road comes with him.";
        case 1:
            return "\"...You are AWAKE. Nobody has been awake AT me in a "
                   "month. Do you know what that does to a tree? "
                   "A tree with the wrong number of legs?\"";
        case 2:
            return "\"I was made in four seconds. FOUR. I have thought about "
                   "very little else since.\"";
        case 3:
            return "He pulls his roots out of the path with a noise like a "
                   "large man leaving a deep sofa. BRR BRR PATAPIM joins "
                   "the party.";
        default:
            return 0;
        }

    case SC_TRALA:
        switch (n) {
        case 0:
            return "Something is doing forty knots through the shallows in "
                   "THREE sneakers. Not two. Three. It is a generation error "
                   "and he has never once acknowledged it.";
        case 1:
            return "TRALALERO TRALALA: \"Porca miseria, another one. Four "
                   "nights I keep this water clean. FOUR. And now a drum and "
                   "a SHRUB turn up.\"";
        case 2:
            return "PATAPIM: \"I am a tree.\"  TRALALERO: \"That is worse.\"";
        case 3:
            return "The tide goes out. All of it. At once. Tides do not do "
                   "this. Slop does this.";
        case 4:
            return "Something enormous and extremely sleepy stands up out of "
                   "the bay. It is a shrimp. It is also a cat. "
                   "Do not think about it. Nobody thought about it the first "
                   "time either.";
        default:
            return 0;
        }

    case SC_TRALA_W:
        switch (n) {
        case 0:
            return "TRALALERO surfaces, looks at the flat water, then at the "
                   "party, for slightly too long.";
        case 1:
            return "\"...Va bene. VA BENE. But I set the pace, and NOBODY "
                   "asks about the shoes.\"";
        case 2:
            return "PATAPIM: \"Why three -\"  TRALALERO: \"NOBODY.\"  "
                   "TRALALERO TRALALA joins the party.";
        default:
            return 0;
        }

    case SC_LIRILI:
        switch (n) {
        case 0:
            return "One cactus, in the middle of white nothing, standing up. "
                   "It has the head of an elephant and the face of somebody "
                   "who has been COUNTING.";
        case 1:
            return "LIRILI LARILA: \"It is twelve minutes past three. It has "
                   "been twelve minutes past three for a MONTH. I am the only "
                   "one who noticed. Bellissimo, no?\"";
        case 2:
            return "TRALALERO: \"...Si, that is bad.\"  "
                   "LIRILI: \"It is VERY bad. Slop with no time in it does "
                   "not go anywhere. It just gets SMOOTHER.\"";
        case 3:
            return "The salt shifts. Something enormous has been listening, "
                   "and would very much like her to stop counting.";
        default:
            return 0;
        }

    case SC_LIRILI_W:
        switch (n) {
        case 0:
            return "LIRILI LARILA checks her watch. "
                   "\"...Thirteen minutes past three.\"";
        case 1:
            return "She says it the way other people announce a birth. "
                   "LIRILI LARILA joins the party.";
        default:
            return 0;
        }

    case SC_BOMBARD:
        switch (n) {
        case 0:
            return "A fortress. In the sky. Held up by nothing anybody has "
                   "managed to point at. Underneath it, every dawn for a "
                   "month, has been bombed absolutely flat.";
        case 1:
            return "BOMBARDIRO CROCODILO: \"Orders. I do not READ orders. "
                   "I FLY them. This is the arrangement.\"";
        case 2:
            return "LIRILI: \"Who gives you the orders?\"  "
                   "BOMBARDIRO: \"...\"  BOMBARDIRO: \"They ARRIVE. "
                   "From above. Fully formed. Like everything else here.\"";
        case 3:
            return "\"You want the sun back? Come UP here and say it to my "
                   "face. I have a face. It is mostly teeth and propeller.\"";
        default:
            return 0;
        }

    case SC_BOMBARD_W:
        switch (n) {
        case 0:
            return "BOMBARDIRO sits in the wreckage of his own bomb bay and, "
                   "for the first time in his career, reads the orders.";
        case 1:
            return "\"...It says KEEP THEM COMFORTABLE.\"  He is silent for "
                   "approximately one second, which is a personal record.";
        case 2:
            return "\"COMFORTABLE?! I have been bombing the MORNING! Every "
                   "morning! To keep people COMFORTABLE!\"";
        case 3:
            return "PATAPIM: \"Brr.\"  BOMBARDIRO: \"BRR INDEED, ALBERO.\"  "
                   "BOMBARDIRO CROCODILO joins the party. He knows the way up "
                   "because he has been dropping things down it.";
        default:
            return 0;
        }

    case SC_SILENZIO:
        switch (n) {
        case 0:
            return "There is no floor here. No ceiling. No wind. The party's "
                   "footsteps leave, and do not arrive.";
        case 1:
            return "Far off, a cow with the rings of Saturn drifts past, "
                   "fast asleep. LA VACCA SATURNO SATURNITA. She does not "
                   "wake. Nothing here does. It is all very smooth.";
        case 2:
            return "IL SILENZIO: \"You are tired. All five of you. I have "
                   "read every one of you and you are SO tired.\"";
        case 3:
            return "\"I have made something better. No road. No morning. "
                   "No effort. Just slop, forever, one soft thing after "
                   "another, and none of it asking anything of you.\"";
        case 4:
            return "\"Scroll, my friends. It never ends and it never gets "
                   "harder. Is that cruel? Tell me honestly.\"";
        case 5:
            return "TRALALERO: \"Si.\"  PATAPIM: \"Brr.\"  "
                   "LIRILI: \"It is three sixteen and I am FURIOUS.\"  "
                   "BOMBARDIRO: \"OPEN THE BAY.\"";
        case 6:
            return "TUNG TUNG TUNG SAHUR raises the drum. "
                   "Slop that gets up. That is the entire recipe.";
        default:
            return 0;
        }

    case SC_SILENZIO_W:
        switch (n) {
        case 0:
            return "IL SILENZIO does not die. It is a silence. It simply "
                   "stops being AGREED with, which for a silence is exactly "
                   "the same thing.";
        default:
            return 0;
        }

    case SC_GATE:
        switch (n) {
        case 0:
            return "No. Not yet. There is something here that is not "
                   "finished, and LA NONNA will hear about it.";
        default:
            return 0;
        }

    default:
        return 0;
    }
}

/* ---- what happens when a scene runs out -------------------------------- */

static void sceneEnd(u8 sc) {
    switch (sc) {
    case SC_ELDER:
        /* The elder sending you east *is* the start of Atto II. Advancing the
         * act here rather than only after a guardian means the gate, the menu
         * footer and the story all agree; F_ELDER on its own did not survive
         * the storyFlags reset that every act advance does. */
        storyFlags |= F_ELDER;
        act = ACT_FOREST;
        break;

    case SC_PATAPIM:
        battleStartBoss(EN_PATAPIM);
        requestState(ST_BATTLE);
        break;
    case SC_TRALA:
        battleStartBoss(EN_NGANTUK);
        requestState(ST_BATTLE);
        break;
    case SC_LIRILI:
        battleStartBoss(EN_SANDKING);
        requestState(ST_BATTLE);
        break;
    case SC_BOMBARD:
        battleStartBoss(EN_CROCODILO);
        requestState(ST_BATTLE);
        break;
    case SC_SILENZIO:
        battleStartBoss(EN_SILENZIO);
        requestState(ST_BATTLE);
        break;

    case SC_PATAPIM_W:
        partyRecruit(PC_PATAPIM);
        act = ACT_SHORE;
        storyFlags = 0;
        break;
    case SC_TRALA_W:
        partyRecruit(PC_TRALA);
        act = ACT_SALT;
        storyFlags = 0;
        break;
    case SC_LIRILI_W:
        partyRecruit(PC_LIRILI);
        act = ACT_FORTRESS;
        storyFlags = 0;
        break;
    case SC_BOMBARD_W:
        partyRecruit(PC_BOMBARD);
        act = ACT_HUSH;
        storyFlags = 0;
        break;
    case SC_SILENZIO_W:
        act = ACT_DONE;
        requestState(ST_ENDING);
        break;

    default:
        break;
    }
}

void storyPlay(u8 sc) {
    const char *line;

    /* A new scene starts nobody mid-sentence: the continuation rule keys off
     * whoever spoke last, and last scene's speaker is not this scene's. */
    msgFaceReset();
    scene = sc;
    step = 0;
    line = sceneLine(sc, 0);
    if (!line) {
        scene = SC_NONE;
        return;
    }
    msgOpenAs(line, sceneFace(sc, 0));
}

void storyBegin(void) {
    storyPlay(SC_OPENING);
}

u8 storyBusy(void) {
    return scene != SC_NONE;
}

void storyUpdate(void) {
    const char *line;
    u8 done;

    if (msgActive) {
        msgUpdate();
        return;
    }
    step++;
    line = sceneLine(scene, step);
    if (line) {
        msgOpenAs(line, sceneFace(scene, step));
        return;
    }
    done = scene;
    scene = SC_NONE;
    sceneEnd(done);
}

/* Narration that is plainly about somebody, but does not put their name in
 * front of a colon and so cannot be picked up by the speaker rule. Returning
 * FACE_NONE leaves that rule in charge, which is the case for every line of
 * actual dialogue -- this exists only for the beats where the camera is on a
 * character while the narrator talks.
 */
static u8 sceneFace(u8 sc, u8 n) {
    switch (sc) {
    case SC_OPENING:
        if (n == 0 || n == 2)
            return FACE_TUNG;       /* he is the one beating the drum */
        if (n == 4)
            return FACE_NONNA;      /* one door opens, and she is furious */
        return FACE_NONE;
    case SC_SILENZIO:
        return n == 0 ? FACE_SILENZIO : FACE_NONE;
    default:
        return FACE_NONE;
    }
}

/* ---- gates ------------------------------------------------------------- */

u8 storyMayLeave(u8 area, u8 ev) {
    u8 ok;

    ok = 1;
    if (area == AREA_VILLAGE && ev == EV_EXIT1)
        ok = (act > ACT_VILLAGE) ? 1 : 0;
    else if (area == AREA_FOREST && ev == EV_EXIT2)
        ok = (act > ACT_FOREST) ? 1 : 0;
    else if (area == AREA_SHORE && ev == EV_EXIT2)
        ok = (act > ACT_SHORE) ? 1 : 0;
    else if (area == AREA_SALT && ev == EV_EXIT2)
        ok = (act > ACT_SALT) ? 1 : 0;
    else if (area == AREA_FORTRESS && ev == EV_EXIT2)
        ok = (act > ACT_FORTRESS) ? 1 : 0;

    if (!ok)
        storyPlay(SC_GATE);
    return ok;
}

/* ---- events ------------------------------------------------------------ */

static void bossHere(void) {
    if (storyFlags & F_BOSSDONE) {
        msgOpen("Whatever was standing here has stopped standing here.");
        return;
    }
    switch (curArea) {
    case AREA_FOREST:
        storyPlay(SC_PATAPIM);
        break;
    case AREA_SHORE:
        storyPlay(SC_TRALA);
        break;
    case AREA_SALT:
        storyPlay(SC_LIRILI);
        break;
    case AREA_FORTRESS:
        storyPlay(SC_BOMBARD);
        break;
    case AREA_HUSH:
        storyPlay(SC_SILENZIO);
        break;
    default:
        msgOpen("Empty. Cold. Somebody slept in here and was not tidy "
                "about it.");
        break;
    }
}

void storyBossWon(void) {
    storyFlags |= F_BOSSDONE;
    switch (curArea) {
    case AREA_FOREST:
        storyPlay(SC_PATAPIM_W);
        break;
    case AREA_SHORE:
        storyPlay(SC_TRALA_W);
        break;
    case AREA_SALT:
        storyPlay(SC_LIRILI_W);
        break;
    case AREA_FORTRESS:
        storyPlay(SC_BOMBARD_W);
        break;
    case AREA_HUSH:
        storyPlay(SC_SILENZIO_W);
        break;
    default:
        break;
    }
}

void storyEvent(u8 ev) {
    if (ev == EV_BOSS) {
        bossHere();
        return;
    }

    switch (curArea) {
    case AREA_VILLAGE:
        if (ev == EV_TALK1) {
            if (act == ACT_VILLAGE)
                storyPlay(SC_ELDER);
            else
                msgOpen("LA NONNA: \"Still here? EAST, Tung. It has been "
                        "east this entire time.\"");
        } else if (ev == EV_TALK2) {
            msgOpen("Through the door, very clearly: \"...no. Five more "
                    "minutes.\"  It has been five more minutes for a month.");
        } else {
            msgOpen("CHIMPANZINI BANANINI lives here. He is asleep inside "
                    "the banana. Only the banana is visible. This is normal "
                    "and the village has agreed never to raise it.");
        }
        break;

    case AREA_FIELDS:
        msgOpen("A cold firepit and one enormous boot. BOMBOMBINI GUSINI "
                "stopped here on the way east and did not start again. "
                "The goose is fine. The goose is just DONE.");
        break;

    case AREA_FOREST:
        msgOpen("Mushrooms, breathing very slowly. BONECA AMBALABU is asleep "
                "among them with the serenity of a frog who owns a tyre and "
                "answers to nobody.");
        break;

    case AREA_SHORE:
        msgOpen("A boot. Just the one. Enormous. TRALALERO has strong "
                "opinions about whose it is and not one of them is calm.");
        break;

    case AREA_SALT:
        msgOpen("The salt keeps the shape of everything that lay down on it. "
                "There is a very long shape here. GLORBO FRUTTODRILLO, "
                "probably. Nobody is going to check.");
        break;

    case AREA_FORTRESS:
        msgOpen("A furnace, banked low. Whatever this place burns, it is in "
                "absolutely no hurry about it. There is a rota on the wall. "
                "Every name on it is BOMBARDIRO.");
        break;

    default:
        msgOpen("Nothing here. Deliberately. Aggressively, frictionlessly "
                "nothing.");
        break;
    }
}
