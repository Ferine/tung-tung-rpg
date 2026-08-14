.include "hdr.asm"

; WLA's .SNESHEADER block does not emit $FFB0-$FFBF, so without these the
; linker drops whatever section happens to fit into the middle of the
; registration header. cartridge-rom.md gives $FFB6-$FFBC as seven mandatory
; zero bytes and $FFB0-$FFB1 as the two-character maker code, which is only
; read at all because hdr.asm sets LICENSEECODE to $33.
;
; They live here and not in hdr.asm because hdr.asm is .included by every
; translation unit; there they would be emitted once per unit at one address.
; $FFB2-$FFB5 is skipped -- WLA writes that from the header block's `ID`.
.BANK 0 SLOT 0
.ORGA $FFB0
.DB "AS"

.BANK 0 SLOT 0
.ORGA $FFB6
.DSB 7, $00                     ; FFB6-FFBC fixed 00
.DB $00                         ; FFBD expansion RAM: none
.DB $00                         ; FFBE special version: normal
.DB $00                         ; FFBF cartridge sub-number

; Each family gets its own `superfree` section. A WLA section cannot straddle
; a bank boundary in 32KB LoROM, and the sprite sheet alone is 12KB, so keeping
; them separate is what lets the linker pack them without a "no room for
; section" failure.

.section ".rodata_spr" superfree
sprites_til: .incbin "assets/sprites.pic"
sprites_til_end:
sprites_pal: .incbin "assets/sprites.pal"
sprites_pal_end:
.ends

; The streamed half of the cast: eighteen designs, six of them 64x64. One
; section so it lands in one bank -- the C indexes it with a 16-bit offset
; added to the base, which only holds if base and blob share a bank.
.section ".rodata_enemies" superfree
enemies_pic: .incbin "assets/enemies.pic"
.ends

; Eight dialogue portraits, 512 bytes each, block-row-major. Its own section
; for the same reason as the cast: one bank, so ppuFaceService can index it
; with 16-bit arithmetic off the base.
; The title illustration: its own 191-character tileset and a 32x32 map. It
; borrows BG1's battle window, which is already the right shape.
.section ".rodata_title" superfree
title_pic: .incbin "assets/title.pic"
title_map: .incbin "assets/title.map"
title_pal: .incbin "assets/title.pal"
.ends

.section ".rodata_faces" superfree
portraits_pic: .incbin "assets/portraits.pic"
.ends

.section ".rodata_font" superfree
font_til: .incbin "assets/font.pic"
font_til_end:
font_pal: .incbin "assets/font.pal"
font_pal_end:

; Two recolours of the same palette, loaded over BG palettes 0 and 1 for the
; duration of a battle so red and green text cost a palette field rather than a
; second set of characters.
fontalert_pal: .incbin "assets/fontalert.pal"
fontgood_pal: .incbin "assets/fontgood.pal"
.ends

; The regions live in worlddata.asm and the backdrops in bgdata.asm, both
; generated and both assembled as units of their own.
