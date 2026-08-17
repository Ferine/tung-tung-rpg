ifeq ($(strip $(PVSNESLIB_HOME)),)
$(error Set PVSNESLIB_HOME to your pvsneslib install, e.g. /path/to/pvsneslib)
endif

# tcc writes src/<unit>.asm next to each .c on the way to an object, and
# snes_rules globs src/*.asm into OFILES. A leftover one is therefore
# *assembled* on the next build rather than compiled from its .c, with
# different flags -- sometimes a duplicate-section link error, sometimes a ROM
# that builds clean and does not run. Clear them before the include computes
# OFILES. Hand-written assembly under src/ would have to be listed here.
HANDASM :=
$(shell rm -f $(filter-out $(HANDASM),$(wildcard src/*.asm)))

# BEFORE including snes_rules: the effects module must come first, because
# smconv assigns effect indices in the order it sees the samples and those
# indices are the SFX_* constants in src/ttrpg.h.
AUDIOFILES := res/ttsfx.it res/ttbgm.it
export SOUNDBANK := res/soundbank
export ROMNAME := tungtung

# This project ships a hand-written registration header.  In particular, it
# declares the 4MB ROM and battery-backed SRAM used by save.c; the SDK defaults
# describe a much smaller ROM-only cartridge and must not replace it.
AUTOHDR := 0

include ${PVSNESLIB_HOME}/devkitsnes/snes_rules

SMCONVFLAGS := -s -o $(SOUNDBANK) -V -b 5 -f

# Same glob, other end: src/main.asm generated from src/main.c also matches, so
# src/main.obj can land in OFILES twice and the linkfile then depends on
# whether a previous build left main.asm behind. Dedupe for determinism.
override OFILES := $(sort $(OFILES))

# pvsneslib releases exist with both the newer `-i in -o out` optimizer CLI
# used by snes_rules and the older `816-opt in > out` CLI.  Some SDK bundles
# contain the newer rules alongside the older binary, so accept either form.
%.asm: %.ps
	@echo Assembling ... $(notdir $<)
	@$(OPT) -i $< -o $@ >/dev/null 2>&1 || $(OPT) $< > $@

.PHONY: all assets clean cleanIntermediates

all: musics $(ROMNAME).sfc checksyms

.PHONY: musics
musics: $(SOUNDBANK).obj

# src/audio.c includes res/soundbank.h, which smconv writes beside
# soundbank.asm. Without this the C is compiled before the header exists on a
# clean build; the `musics` prerequisite above only orders it for serial make.
src/audio.ps: $(SOUNDBANK).asm

# Two things the toolchain will not tell you about: a global defined in two
# translation units (checksyms.py, reading the symbol file just written), and a
# literal string wider than the screen (checktext.py), and a line that names
# a speaker with no portrait, which renders perfectly and faceless
# (checkfaces.py).
.PHONY: checksyms
checksyms: $(ROMNAME).sfc
	@python3 checksyms.py $(ROMNAME).sym
	@python3 checktext.py
	@python3 checkfaces.py
	@python3 checkbank.py
	@python3 checkrom.py $(ROMNAME).sfc

# Everything data.asm .incbin's. All of it is written by the Python
# generators into assets/, not by make, so there is no rule to build them --
# say that plainly instead of failing with "no rule to make target".
ASSETDIR := assets

AREAS := village fields forest shore salt fortress hush
AREA_ASSETS := $(foreach a,$(AREAS),\
                 area_$(a).pic area_$(a).map area_$(a).col area_$(a).pal)

BACKDROPS := night forest shore salt iron void
BG_ASSETS := $(foreach b,$(BACKDROPS),bg_$(b).pic bg_$(b).map bg_$(b).pal)

HDMA_ASSETS := $(foreach s,night forest shore salt iron void field,sky_$(s).tbl) \
               $(foreach i,0 1 2 3 4 5 6 7,wave$(i).tbl)

MODE7_ASSETS := mode7_warp.map mode7_warp.pic mode7_warp.pal

ASSETS := $(addprefix $(ASSETDIR)/,\
            sprites.pic sprites.pal enemies.pic portraits.pic \
            font.pic font.pal fontalert.pal fontgood.pal \
            title.pic title.map title.pal \
            $(HDMA_ASSETS) $(MODE7_ASSETS) \
            $(AREA_ASSETS) $(BG_ASSETS) bg_dawn.pal)

data.obj: hdr.asm worlddata.asm bgdata.asm hdmadata.asm $(ASSETS)
mode7data.obj: hdr.asm $(addprefix $(ASSETDIR)/,$(MODE7_ASSETS))

$(ASSETS):
	@echo "$@ is missing -- run 'python3 gen_assets.py' first" >&2; exit 1

# snes_rules declares no header dependency for the .c -> .ps step and `clean`
# does not remove .ps files, so a stale .ps survives until its own .c is
# touched. Editing a header then yields a ROM that is a *mixture*: units whose
# .c also changed compile against the new header, the rest keep the old one.
# The generated headers are in here too -- regenerating art must rebuild the
# code that indexes it.
PSFILES := $(CFILES:.c=.ps)
$(PSFILES): src/ttrpg.h src/gfxmap.h src/sprmap.h src/worldmap.h \
            src/bgmap.h src/hdmamap.h

# res/music.h carries the order ranges of the thirteen themes and is written by
# gen_music.py, not by make -- they have to come from the module that defines
# them. Same stale-.ps trap as the others, hence the dependency; and since make
# cannot build it, say so rather than failing with "no rule to make target".
$(PSFILES): res/music.h
res/music.h res/ttsfx.it res/ttbgm.it:
	@echo "$@ is missing -- run 'python3 gen_assets.py' first" >&2; exit 1

# Every unit emits the whole .SNESHEADER block to the same addresses, so the
# linked value is whichever object was written last. Without this, editing
# hdr.asm leaves stale objects carrying the old header bytes.
$(OFILES): hdr.asm

assets:
	python3 gen_assets.py

# The generated graphics and tracker modules are part of the source checkout:
# they let a contributor build without downloading the 25MB source recordings.
# pvsneslib's cleanGfx target removes those inputs, so a normal clean must not
# call it.
clean: cleanBuildRes cleanRom cleanAudio cleanIntermediates

cleanIntermediates:
	@rm -f $(PSFILES) $(CFILES:.c=.asm)
