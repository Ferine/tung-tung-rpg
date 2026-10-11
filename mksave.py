"""Hand-build a save blob, so a test can start where it wants to.

save.c writes its layout out longhand rather than as a struct, on the grounds
that the block outlives the build. The same property lets a script speak it:
drop one of these into the emulator's SRAM, reset, pick CONTINUE, and the
party is standing wherever you said with whatever levels you said.

    import mksave, ctypes
    sram = core.lib.retro_get_memory_data(0)          # RETRO_MEMORY_SAVE_RAM
    ctypes.memmove(sram, mksave.make(area=6, hx=17, hy=9), 96)

Reaching the last well the honest way is a forty-five minute playthrough.
This is a minute, which is the difference between testing the final boss once
and testing it until the balance is right.

Keep the layout constants in step with save.c -- and SAVE_VERSION with them,
or the game will read the block as an empty slot and say nothing about why.
"""
import struct

O_MAGIC, O_ACT, O_FLAGS, O_COUNT, O_AREA = 0, 4, 5, 6, 7
O_HX, O_HY, O_GOLD, O_LEVEL, O_STATUS = 8, 9, 10, 12, 17
O_CHARM, O_HP, O_MP, O_EXP, O_ITEMS, O_OWNED = 22, 27, 37, 47, 57, 65
O_QUEST, O_WELLS, O_PATROLS, O_SUM = 72, 75, 76, 77
SIZE = 96


# Legacy version-2 fixture flags. loadGame migrates completion from the act;
# permanent guardian flags occupy bits 2-6. Bit 1 is reserved.
def make(act=5, flags=0x01, count=5, area=6, hx=16, hy=6, gold=4000,
         level=(24,) * 5, charm=(0,) * 5, items=(9, 9, 9, 5, 9, 3, 2, 1),
         owned=(1,) * 7, hp=(9999,) * 5, mp=(999,) * 5, exp=(30000,) * 5,
         version=2, quests=(0,0,0), wells=0, patrols=0, status=(0,)*5):
    b = bytearray(SIZE)
    assert version in (2,3)
    b[O_MAGIC:O_MAGIC + 4] = b'TTS'+bytes([version])
    b[O_ACT], b[O_FLAGS], b[O_COUNT], b[O_AREA] = act, flags, count, area
    b[O_HX], b[O_HY] = hx, hy
    struct.pack_into('<H', b, O_GOLD, gold)
    for i in range(5):
        b[O_LEVEL + i] = level[i]
        b[O_STATUS + i] = status[i]
        b[O_CHARM + i] = charm[i]
        struct.pack_into('<H', b, O_HP + i * 2, hp[i])   # loadGame clamps to max
        struct.pack_into('<H', b, O_MP + i * 2, mp[i])
        struct.pack_into('<H', b, O_EXP + i * 2, exp[i])
    for i in range(8):
        b[O_ITEMS + i] = items[i]
    for i in range(7):
        b[O_OWNED + i] = owned[i]
    if version == 3:
        b[O_QUEST:O_QUEST+3] = bytes(quests)
        b[O_WELLS], b[O_PATROLS] = wells, patrols
    sum_at = 72 if version == 2 else O_SUM
    s = 0x5A
    for i in range(sum_at):
        s = (s + b[i]) & 0xFF
    b[sum_at] = s
    return bytes(b)
