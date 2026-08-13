#!/usr/bin/env python3
"""Fail when the linked ROM no longer describes the cartridge the game uses."""
import sys
from pathlib import Path


ROM_SIZE = 4 * 1024 * 1024
HEADER_OFFSET = 0x7FB0           # Mode 20 / LoROM registration data


def fail(message):
    print("ROM header: " + message, file=sys.stderr)
    return 1


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "tungtung.sfc")
    rom = path.read_bytes()
    if len(rom) != ROM_SIZE:
        return fail("expected a 4MB image, got %d bytes" % len(rom))

    h = rom[HEADER_OFFSET:HEADER_OFFSET + 48]
    if h[0:2] != b"AS" or h[2:6] != b"SNES":
        return fail("extended maker/game code is missing")
    if any(h[6:16]):
        return fail("reserved extended-header bytes are not zero")
    if h[16:37] != b"TUNG TUNG SAHUR      ":
        return fail("title is not the required 21-byte padded string")

    expected = (0x20, 0x02, 0x0C, 0x01, 0x01, 0x33, 0x00)
    actual = tuple(h[37:44])
    if actual != expected:
        return fail("map/cart/ROM/SRAM/region/license/version is %s, expected %s"
                    % (actual, expected))

    complement = int.from_bytes(h[44:46], "little")
    checksum = int.from_bytes(h[46:48], "little")
    if (complement ^ checksum) != 0xFFFF:
        return fail("checksum and complement do not XOR to FFFF")
    if (sum(rom) & 0xFFFF) != checksum:
        return fail("stored checksum does not match the ROM byte sum")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
