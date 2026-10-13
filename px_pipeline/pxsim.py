"""Offline replica of PxWeaponArt::apply over every package, to preview what the DLL will do."""
import os, re, glob, struct, collections, sys

root = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages'


def norm(name):
    s = ''.join(c.lower() if c.isascii() and c.isalnum() else '_' for c in name)
    return re.sub('_+', '_', s)


def resolve(pkgdir, f):
    if not f:
        return None
    bare = os.path.basename(f.replace('\\', '/'))
    for c in (os.path.join(pkgdir, f), os.path.join(pkgdir, 'assets', f), os.path.join(pkgdir, 'assets', bare)):
        if os.path.isfile(c):
            return c
    ad = os.path.join(pkgdir, 'assets')
    if not os.path.isdir(ad):
        return None
    m = [x for x in os.listdir(ad) if os.path.isfile(os.path.join(ad, x)) and norm(x) == norm(bare)]
    return os.path.join(ad, m[0]) if len(m) == 1 else None


class R:
    def __init__(s, d, p):
        s.d, s.p, s.ok = d, p, True

    def u32(s):
        if not s.ok or s.p + 4 > len(s.d):
            s.ok = False
            return 0
        v = struct.unpack_from('<I', s.d, s.p)[0]
        s.p += 4
        return v

    def u8(s):
        if not s.ok or s.p + 1 > len(s.d):
            s.ok = False
            return 0
        s.p += 1
        return s.d[s.p - 1]

    def str(s):
        n = s.u32()
        if not s.ok or n > 260 or s.p + n > len(s.d):
            s.ok = False
            return ''
        v = s.d[s.p:s.p + n]
        s.p += n
        return v.decode('latin1')


def anims(d, start, strv):
    r = R(d, start)
    r.u32(); r.u32(); r.u8()
    if strv:
        r.str(); r.str()
    else:
        r.u32(); r.u32()
    a = [r.str() for _ in range(9)]
    if not r.ok or r.p + 4 != len(d):
        return None
    return a[0]


def trailer(d):
    if len(d) < 0x1E0 + 8:
        return None
    r = R(d, 0x1E0)
    r.u32()
    n1 = r.str(); r.str(); r.str(); r.str()
    spr = [r.str() for _ in range(3)]
    if not r.ok:
        return None
    aim = anims(d, r.p, False)
    if aim is None:
        aim = anims(d, r.p, True)
    return n1, spr, aim


def sim(d, fields):
    if len(d) < 4 + 0x1D0:
        return 0
    c = e = 0
    for off in range(8, 0x1D0, 4):
        b = struct.unpack_from('<i', d, 4 + off)[0]
        m = fields.get(off, 0)
        if not b and not m:
            continue
        c += 1
        e += b == m
    return e / c if c else 0


stats = collections.Counter()
for main in sorted(glob.glob(os.path.join(root, '*', '*', 'main.lua'))):
    pkgdir = os.path.dirname(main)
    pkg = os.path.relpath(pkgdir, root).split(os.sep)[0]
    raw = os.path.join(pkgdir, 'weapons_raw')
    if not os.path.isdir(raw):
        continue
    bins = []
    for f in os.listdir(raw):
        if f.lower().endswith('.bin'):
            d = open(os.path.join(raw, f), 'rb').read()
            t = trailer(d)
            if t:
                bins.append((f, d, t))
    text = open(main, encoding='utf-8', errors='replace').read()
    weps = collections.defaultdict(dict)
    for m in re.finditer(r'^\s*(\w+)\.unknown([0-9A-Fa-f]+)\s*=\s*(-?\d+)', text, re.M):
        v = int(m.group(3))
        v = (v + 2**31) % 2**32 - 2**31
        weps[m.group(1)][int(m.group(2), 16)] = v
    regs = dict(re.findall(r'registerCustomWeapon\((\w+),\s*"[^"]*",\s*"([^"]*)"', text))
    for var, fields in weps.items():
        if var not in regs:
            continue
        name1 = regs[var]
        best = None
        for f, d, t in bins:
            s = sim(d, fields)
            if t[0] and name1.lower().startswith(t[0].lower()):
                s += 0.01
            if best is None or s > best[0]:
                best = (s, f, t)
        if not best or best[0] < 0.85:
            stats['nomatch'] += 1
            if any(fields.get(o) == 100000 for o in (0x60, 0x124, 0x170)):
                print(f'NOMATCH {pkg:30} {name1:28} best={best and round(best[0], 2)} {best and best[1]}')
            continue
        stats['match'] += 1
        s, f, (n1, spr, aim) = best
        out = []
        for o, sf in zip((0x60, 0x124, 0x170), spr):
            if fields.get(o) == 100000:
                rp = resolve(pkgdir, sf)
                out.append(f'{o:#x}:{sf!r}->{"OK" if rp else "MISSING"}')
                stats['slot_ok' if rp else 'slot_missing'] += 1
        ra = resolve(pkgdir, aim) if aim else None
        stats['aim_ok' if ra else ('aim_missing' if aim else 'aim_none')] += 1
        if out or '-v' in sys.argv or (aim and not ra):
            print(f'{pkg:30} {name1:28} {s:.2f} {f:28} {" ".join(out)} aim={aim!r}:{"OK" if ra else "-"}')
print(stats)
