; TUNG TUNG SAHUR -- LoROM memory map and cartridge registration header.
;
; Keep this hand-written: save.c uses 2KB of battery-backed SRAM, and the ROM
; is deliberately padded to 4MB.  Makefile sets AUTOHDR=0 so snes_rules does
; not replace these values with its ROM-only defaults.

.MEMORYMAP
  SLOTSIZE $8000
  DEFAULTSLOT 0
  SLOT 0 $8000
  SLOT 1 $0000 $2000
  SLOT 2 $2000 $E000
  SLOT 3 $0000 $10000
.ENDME

.ROMBANKSIZE $8000
.ROMBANKS 128

.SNESHEADER
  ID "SNES"
  NAME "TUNG TUNG SAHUR      "
  SLOWROM
  LOROM
  CARTRIDGETYPE $02            ; ROM + RAM + battery
  ROMSIZE $0C                  ; 17-32 Mbit (4MB image)
  SRAMSIZE $01                 ; 16 Kbit / 2KB
  COUNTRY $01
  LICENSEECODE $33             ; extended header at $FFB0
  VERSION $00
.ENDSNES

.SNESNATIVEVECTOR
  COP EmptyHandler
  BRK EmptyHandler
  ABORT EmptyHandler
  NMI VBlank
  IRQ EmptyHandler
.ENDNATIVEVECTOR

.SNESEMUVECTOR
  COP EmptyHandler
  ABORT EmptyHandler
  NMI EmptyHandler
  RESET tcc__start
  IRQBRK EmptyHandler
.ENDEMUVECTOR
