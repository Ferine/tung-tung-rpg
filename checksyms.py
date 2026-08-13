#!/usr/bin/env python3
"""Fail the build if any global is defined in more than one translation unit.

tcc has no common-symbol merging. `u16 heroX;` at file scope in two units links
as two separate objects at two addresses, and nothing warns: one unit writes
its copy, another reads the other, and the value is simply always the initial
one. It shipped that way here for heroX, heroY, encounterSeed and battleResult
before this check existed -- harmlessly, because the readers and writers
happened to be in the same unit, which is precisely the kind of luck that stops
holding the moment the code moves.

Run after linking; the symbol file is what the linker actually resolved.
"""
import re
import sys

IGNORE = re.compile(r'^(__local_|tcc__|tccs_|__)')


def main(path):
    seen = {}
    for line in open(path):
        parts = line.split()
        if len(parts) != 2:
            continue
        addr, name = parts
        if IGNORE.match(name):
            continue
        try:
            a = int(addr, 16)
        except ValueError:
            continue
        # WRAM and direct page only: a ROM label appearing twice is a section
        # symbol, not a variable.
        if not (0x7e0000 <= a < 0x800000 or a < 0x2000):
            continue
        seen.setdefault(name, set()).add(a)

    dupes = {n: sorted(a) for n, a in seen.items() if len(a) > 1}
    if not dupes:
        return 0
    print("duplicate global definitions -- each is two variables, not one:",
          file=sys.stderr)
    for n, addrs in sorted(dupes.items()):
        print("  %-24s %s" % (n, ' '.join('%06x' % a for a in addrs)),
              file=sys.stderr)
    print("Define each exactly once (globals.c) and declare it extern in"
          " ttrpg.h.", file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'tungtung.sym'))
