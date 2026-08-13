#!/usr/bin/env python3
"""Fail the build if a line names a speaker the portrait table does not know.

The dialogue portrait is chosen by matching the "NAME:" the script already
writes in front of a line. That is nice because nothing has to be annotated --
and dangerous for exactly the same reason: misspell the name, or introduce a
character without adding a bust, and the line still renders perfectly. It just
quietly has no face, in a build where every other line has one.

So: pull every "SOMETHING:" prefix out of the strings, and check each one is in
the table in text.c. Anything that is deliberately faceless goes in ALLOWED.
"""
import glob
import re
import sys

# Prefixes that are speech but intentionally have no bust drawn for them.
ALLOWED = {
    'CHIMPANZINI BANANINI',
}

PREFIX = re.compile(r'"([A-Z][A-Z ]{2,30}):')
TABLE = re.compile(r'case\s+\d+:\s*return\s+"([A-Z][A-Z ]+):";')


def known():
    src = open('src/text.c').read()
    body = src[src.index('static const char *facePrefix('):]
    body = body[:body.index('}')]
    return {m.group(1) for m in TABLE.finditer(body)}


def main():
    table = known()
    if not table:
        print("checkfaces: could not read facePrefix() out of src/text.c",
              file=sys.stderr)
        return 1

    bad = []
    for path in sorted(glob.glob('src/*.c')):
        for n, line in enumerate(open(path), 1):
            for m in PREFIX.finditer(line):
                name = m.group(1)
                if name not in table and name not in ALLOWED:
                    bad.append((path, n, name))

    if not bad:
        return 0
    print("lines name a speaker with no portrait, and will render faceless:",
          file=sys.stderr)
    for path, n, name in bad:
        print("  %s:%d  %r" % (path, n, name), file=sys.stderr)
    print("  known: %s" % ", ".join(sorted(table)), file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
