; Drain field_stream.c's prepared list. Channel 0 is GP-DMA; HDMA owns 1/2
; and pvsneslib OAM owns 7. No CPU tile calculations run in V-blank.
.include "hdr.asm"
.accu 16
.index 16
.section ".text_field_dma" superfree
fieldStreamFlush:
    php
    rep #$30
    phx
    lda.l fieldDmaBytes
    beq _field_dma_done
    sep #$20
    lda #$80
    sta.l $2115
    lda #$01
    sta.l $4300
    lda #$18
    sta.l $4301
    rep #$20
    ldx #0
_field_dma_next:
    lda.l fieldDma+4,x
    sta.l $2116
    lda.l fieldDma+6,x
    sta.l $4305
    lda.l fieldDma,x
    sta.l $4302
    sep #$20
    lda.l fieldDma+3,x
    sta.l $2115
    lda.l fieldDma+2,x
    sta.l $4304
    lda #$01
    sta.l $420B
    rep #$20
    txa
    clc
    adc #8
    tax
    cmp.l fieldDmaBytes
    bcc _field_dma_next
    lda #0
    sta.l fieldDmaBytes
    sep #$20
    lda.l $4212
    bmi _field_dma_in_blank
    rep #$20
    lda.l fieldDmaOverruns
    inc a
    sta.l fieldDmaOverruns
_field_dma_in_blank:
    rep #$20
_field_dma_done:
    plx
    plp
    rtl
.ends

; Build one cache edge during visible-frame game logic. The compiler's
; banked pointer arithmetic per tile was too expensive at walking speed.
; No hardware writes here. DBR temporarily addresses the region attributes.
.section ".text_field_plan" superfree
fieldQueueLine:
    php
    rep #$30
    phx
    phy
    phb
    sep #$20
    lda.l fieldAttributes+2
    pha
    plb
    rep #$20
_field_plan_next:
    lda.l fieldPlanY
    asl a
    tax
    lda.l fieldMapY,x
    sta.l fieldWork
    lda.l fieldSlotY,x
    sta.l fieldWork+2
    lda.l fieldPlanX
    asl a
    tax
    lda.l fieldSlotX,x
    clc
    adc.l fieldWork+2
    sta.l fieldWork+2
    lda.l fieldMapX,x
    clc
    adc.l fieldWork
    sta.l fieldWork

    lda.l fieldPlanY
    xba
    lsr a
    sta.l fieldWork+4
    lda.l fieldPlanX
    asl a
    clc
    adc.l fieldWork+4
    adc.l fieldAttributes
    tay
    lda.w $0000,y
    sta.l fieldWork+4
    lda.l fieldWork+2
    lsr a
    lsr a
    lsr a
    lsr a
    ora.l fieldWork+4
    pha
    lda.l fieldWork
    tax
    pla
    sta.l fieldCacheMap,x
    pha
    lda.l fieldPlanY
    and #31
    asl a
    tax
    pla
    sta.l fieldColumn,x

    lda.l fieldPlanY
    lsr a
    and #$001C
    tax
    lda.l fieldStrips,x
    sta.l fieldWork+4
    lda.l fieldStrips+2,x
    sta.l fieldWork+6
    lda.l fieldPlanY
    and #7
    xba
    asl a
    asl a
    asl a
    clc
    adc.l fieldWork+4
    sta.l fieldWork+4
    lda.l fieldPlanX
    asl a
    asl a
    asl a
    asl a
    asl a
    clc
    adc.l fieldWork+4
    pha
    lda.l fieldDmaBytes
    tax
    pla
    sta.l fieldDma,x
    lda.l fieldWork+6
    and #$00FF
    ora #$8000
    sta.l fieldDma+2,x
    lda.l fieldWork+2
    clc
    adc #$2000
    sta.l fieldDma+4,x
    lda #32
    sta.l fieldDma+6,x
    txa
    clc
    adc #8
    sta.l fieldDmaBytes
    lda.l fieldPlanX
    clc
    adc.l fieldPlanDX
    sta.l fieldPlanX
    lda.l fieldPlanY
    clc
    adc.l fieldPlanDY
    sta.l fieldPlanY
    lda.l fieldPlanN
    dec a
    sta.l fieldPlanN
    beq _field_plan_done
    jmp _field_plan_next
_field_plan_done:
    plb
    ply
    plx
    plp
    rtl
.ends

.section ".rodata_field_cache_tables" superfree
fieldSlotX:
    .dw 0, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464, 480, 496, 512, 528, 0, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240, 256, 272, 288, 304, 320, 336, 352, 368, 384, 400, 416, 432, 448, 464
fieldSlotY:
    .dw 0, 544, 1088, 1632, 2176, 2720, 3264, 3808, 4352, 4896, 5440, 5984, 6528, 7072, 7616, 8160, 8704, 9248, 9792, 10336, 10880, 11424, 11968, 12512, 13056, 13600, 14144, 14688, 15232, 15776, 0, 544, 1088, 1632, 2176, 2720, 3264, 3808, 4352, 4896, 5440, 5984, 6528, 7072, 7616, 8160, 8704, 9248, 9792, 10336, 10880, 11424, 11968, 12512, 13056, 13600, 14144, 14688, 15232, 15776, 0, 544, 1088, 1632
fieldMapX:
    .dw 0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58, 60, 62, 2048, 2050, 2052, 2054, 2056, 2058, 2060, 2062, 2064, 2066, 2068, 2070, 2072, 2074, 2076, 2078, 2080, 2082, 2084, 2086, 2088, 2090, 2092, 2094, 2096, 2098, 2100, 2102, 2104, 2106, 2108, 2110
fieldMapY:
    .dw 0, 64, 128, 192, 256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344, 1408, 1472, 1536, 1600, 1664, 1728, 1792, 1856, 1920, 1984, 0, 64, 128, 192, 256, 320, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280, 1344, 1408, 1472, 1536, 1600, 1664, 1728, 1792, 1856, 1920, 1984
.ends
