# The audition ROM: driver and soundbank, no game. Built and driven by
# audition.py, which copies this directory to build/audition first so the
# generated soundbank never lands in the source tree.
ifeq ($(strip $(PVSNESLIB_HOME)),)
$(error set PVSNESLIB_HOME to your pvsneslib install)
endif

# Same order as the game's Makefile: the effects module first.
AUDIOFILES := res/ttsfx.it res/ttbgm.it
export SOUNDBANK := res/soundbank
export ROMNAME := aud

include ${PVSNESLIB_HOME}/devkitsnes/snes_rules

SMCONVFLAGS := -s -o $(SOUNDBANK) -V -b 5 -f

musics: $(SOUNDBANK).obj
all: musics $(ROMNAME).sfc
clean: cleanBuildRes cleanRom cleanAudio

# Accept either optimizer command line, as the game's Makefile does.
%.asm: %.ps
	@echo Assembling ... $(notdir $<)
	@$(OPT) -i $< -o $@ >/dev/null 2>&1 || $(OPT) $< > $@
