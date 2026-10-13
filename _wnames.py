"""Compare weapon names registered by package main.lua against the real ProjectX names inside weapons_raw/*.bin."""
import os, re, sys
GAME = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon'
P = os.path.join(GAME, 'jelly', 'packages')
ini = open(os.path.join(GAME, 'wkJellyWorm.ini'), encoding='latin-1').read()
enabled = set(re.findall(r'^([\w.\-]+)=1\s*$', ini, re.M))
only_enabled = '--all' not in sys.argv
reg = re.compile(r'registerCustomWeapon\((\w+),\s*"[^"]*",\s*"([^"]*)",\s*"([^"]*)"\)')
bad = 0
for pkg in sorted(os.listdir(P)):
    if only_enabled and pkg not in enabled:
        continue
    for ver in os.listdir(os.path.join(P, pkg)):
        d = os.path.join(P, pkg, ver)
        ml = os.path.join(d, 'main.lua')
        if not os.path.isfile(ml):
            continue
        src = open(ml, encoding='utf-8', errors='replace').read()
        for var, n1, n2 in reg.findall(src):
            b = os.path.join(d, 'weapons_raw', var + '.bin')
            if not os.path.isfile(b):
                continue
            s = re.findall(rb'[ -~]{2,}', open(b, 'rb').read())
            real = s[0].decode() if s else '?'
            real2 = s[1].decode() if len(s) > 1 else ''
            if real != n1:
                bad += 1
                print('%s: %s registered as %r, PX name %r / %r' % (pkg, var, n1, real, real2))
print('mismatches:', bad)
