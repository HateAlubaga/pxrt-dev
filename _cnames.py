"""Which CheckName / GetWeaponByName literals of the enabled pxrt packages (and their libs) match a weapon only through
the ProjectX name table (pxrt_wnames.lua), i.e. were dead before round 7."""
import os, re, sys
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
import pxgen
GAME = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon'
P = os.path.join(GAME, 'jelly', 'packages')
ini = open(os.path.join(GAME, 'wkJellyWorm.ini'), encoding='latin-1').read()
enabled = set(re.findall(r'^([\w.\-]+)=1\s*$', ini, re.M))
reg = set()
for pkg in enabled:
    d = os.path.join(P, pkg)
    if not os.path.isdir(d):
        continue
    for ver in os.listdir(d):
        ml = os.path.join(d, ver, 'main.lua')
        if os.path.isfile(ml):
            reg |= set(m[0] for m in re.findall(r'registerCustomWeapon\(\w+,\s*"[^"]*",\s*"([^"]*)",\s*"([^"]*)"\)',
                                                 open(ml, encoding='utf-8', errors='replace').read()))
wn = dict(re.findall(r'\[("[^"]*")\] = ("[^"]*")', open(r'C:\Users\Admin\pxrt_dev\pxrt_wnames.lua', encoding='utf-8').read()))
alias = {k.strip('"'): v.strip('"') for k, v in wn.items()}
norm = lambda s: re.sub(r'[^0-9a-z]', '', s.lower())
direct = {norm(r) for r in reg}
via = {norm(alias[r]): r for r in reg if r in alias}
claimed = set(re.findall(r'^(\S+): claimed', open(os.path.join(GAME, 'jelly', 'pxboot.log'), encoding='latin-1').read(), re.M))
wanted = {}
for pkg in sorted(claimed):
    libs, chunks = pxgen.pkg_info(pkg)
    srcs = list(chunks)
    for fname, src in srcs:
        for n in re.findall(r'"(?:CheckName|Check)", "([^"]+)"', src) + re.findall(r'GetWeaponByName\("([^"]+)"', src):
            wanted.setdefault(n, set()).add(pkg + '/' + fname)
for n in sorted(wanted):
    k = norm(n)
    st = 'direct' if k in direct else ('ALIAS ' + via[k] if k in via else 'none')
    if st != 'direct':
        print('%-28s %-34s %s' % (n, st, ', '.join(sorted(wanted[n]))[:90]))
