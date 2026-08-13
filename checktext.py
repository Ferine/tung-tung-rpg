#!/usr/bin/env python3
"""Fail the build if a literal string would run off the 32-column screen.

textPutTile silently drops anything at x >= 32, so an over-long line is not a
crash or a warning -- it is a sentence that stops mid-word on a TV and nowhere
else. The game-over screen shipped reading "The sun rose over a sleeping" for
exactly that reason.

Only literal calls with literal coordinates are checkable; anything computed at
runtime is the caller's problem. bigPut is counted at two columns a letter and
one a space, which is what the logo alphabet costs.
"""
import glob
import re
import sys

COLS = 32

TEXT = re.compile(r'text(?:Put|PutPal|Num|NumPal)\(\s*(\d+)\s*,\s*(\d+)\s*,'
                  r'\s*"((?:[^"\\]|\\.)*)"')
BIG = re.compile(r'bigPut\(\s*(\d+)\s*,\s*(\d+)\s*,\s*"([^"]*)"')


def main():
    bad = []
    for path in sorted(glob.glob('src/*.c')):
        for n, line in enumerate(open(path), 1):
            for m in TEXT.finditer(line):
                x, s = int(m.group(1)), m.group(3).replace('\\"', '"')
                if x + len(s) > COLS:
                    bad.append((path, n, x, len(s), s))
            for m in BIG.finditer(line):
                x, s = int(m.group(1)), m.group(3)
                w = sum(1 if c == ' ' else 2 for c in s)
                if x + w > COLS:
                    bad.append((path, n, x, w, 'bigPut ' + s))
    if not bad:
        return 0
    print("text runs off the %d-column screen:" % COLS, file=sys.stderr)
    for path, n, x, w, s in bad:
        print("  %s:%d  x=%d width=%d ends at %d  %r"
              % (path, n, x, w, x + w, s), file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
