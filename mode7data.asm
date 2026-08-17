; Generated assets from gen_mode7.py. Mode 7's map and character bytes are
; separate ROM objects because bgInitMapTileSet7 interleaves them into VRAM's
; low and high byte planes respectively (ppu-graphics.md A-11/A-15).
.include "hdr.asm"

.section ".rodata_mode7_map" superfree
mode7_warp_map: .incbin "assets/mode7_warp.map"
.ends

.section ".rodata_mode7_pic" superfree
mode7_warp_pic: .incbin "assets/mode7_warp.pic"
mode7_warp_pic_end:
.ends

.section ".rodata_mode7_pal" superfree
mode7_warp_pal: .incbin "assets/mode7_warp.pal"
.ends
