#!/usr/bin/env python3
"""Which module writes which theme. Themes are imported one at a time, so
working on one does not need the others to exist -- or to compile."""
import importlib

# THEME -> (module, function)
WRITERS = {
    'TOWN': ('themes_warm', 'town'),
    'SHORE': ('themes_warm', 'shore'),
    'FIELD': ('themes_road', 'field'),
    'FOREST': ('themes_dark', 'forest'),
    'HUSH': ('themes_dark', 'hush'),
    'SALT': ('themes_iron', 'salt'),
    'FORTRESS': ('themes_iron', 'fortress'),
    'BATTLE': ('themes_combat', 'battle'),
    'BOSS': ('themes_combat', 'boss'),
    'TITLE': ('themes_hub', 'title'),
    'FANFARE': ('themes_hub', 'fanfare'),
    'FINAL': ('themes_hub', 'final'),
    'FINAL2': ('themes_hub', 'final2'),
    'ENDING': ('themes_hub', 'ending'),
}

NAMES = ('TOWN', 'FIELD', 'FOREST', 'SHORE', 'SALT', 'FORTRESS', 'HUSH',
         'BATTLE', 'BOSS', 'FINAL', 'FINAL2', 'FANFARE', 'TITLE', 'ENDING')


def build(names):
    out = []
    for n in names:
        if n not in WRITERS:
            raise SystemExit("theme %s is not written yet (have: %s)"
                             % (n, ', '.join(sorted(WRITERS))))
        mod, fn = WRITERS[n]
        out.append(getattr(importlib.import_module(mod), fn)())
    return out


def build_all():
    return build(NAMES)
