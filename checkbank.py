#!/usr/bin/env python3
"""Fail the build if audio.c and smconv disagree about the soundbank symbol.

smconv emits `SOUNDBANK__` for a bank that fits in 32KB and `SOUNDBANK__0`,
`SOUNDBANK__1`, ... for one that does not. Adding or removing a few hundred
bytes of instrument can therefore silently rename the symbol the C is linked
against, and what you get is `Unresolved reference to "SOUNDBANK__"` from the
linker, which says nothing about samples.
"""
import re
import sys

ASM = 'res/soundbank.asm'
SRC = 'src/audio.c'


def main():
    try:
        asm = open(ASM).read()
        src = open(SRC).read()
    except OSError as exc:
        print("checkbank: %s" % exc, file=sys.stderr)
        return 1

    emitted = set(re.findall(r'^(SOUNDBANK__\d*):', asm, re.M))
    used = set(re.findall(r'\bSOUNDBANK__\d*\b', src))
    if not emitted:
        print("checkbank: no SOUNDBANK__ label in %s" % ASM, file=sys.stderr)
        return 1

    missing = used - emitted
    unused = emitted - used
    if missing or unused:
        size = re.search(r'total size:\s*(\d+)', asm)
        print("soundbank symbols do not match:", file=sys.stderr)
        print("  %s emits: %s" % (ASM, ', '.join(sorted(emitted))),
              file=sys.stderr)
        print("  %s uses:  %s" % (SRC, ', '.join(sorted(used)) or '(none)'),
              file=sys.stderr)
        if size:
            print("  bank is %s bytes; smconv splits above 32768"
                  % size.group(1), file=sys.stderr)
        if unused:
            print("  never set: %s -- spcSetBank each, in reverse order"
                  % ', '.join(sorted(unused)), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
