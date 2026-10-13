import json, re, os, collections, glob, sys
ini = open(r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\wkJellyWorm.ini', encoding='latin-1').read()
act = [l.split('=')[0] for l in ini.splitlines() if l.endswith('=1') and '_' in l.split('=')[0] and not l.startswith(';')]
act = [a for a in act if a not in ('zz_probe',)]
if len(sys.argv) > 1:
    act = sys.argv[1:]
print(len(act), act)
ov = collections.Counter(); ct = collections.Counter(); F = collections.Counter(); MC = collections.Counter()
CL = collections.Counter(); ME = collections.Counter(); K = collections.Counter(); R = collections.Counter()
libs_seen = set(); miss = []
for p in act + ['darkness2016']:
    d = os.path.join('testout/lua', p)
    if not os.path.isdir(d):
        miss.append(p)
        continue
    pc = json.load(open(os.path.join(d, 'pxchunks.json')))
    files = [os.path.join(d, c) for c in pc['chunks']]
    for l in pc['libs']:
        if l not in libs_seen:
            libs_seen.add(l)
            ld = os.path.join('testout/lua/@lib', l)
            if os.path.isdir(ld):
                lj = os.path.join(ld, 'pxchunks.json')
                if os.path.exists(lj):
                    files += [os.path.join(ld, c) for c in json.load(open(lj))['chunks']]
                else:
                    files += glob.glob(ld + '/*.lua')
            else:
                ld = os.path.join('testout/lua', l)
                if os.path.isdir(ld):
                    files += glob.glob(ld + '/*.lua')
    for f in files:
        if not os.path.exists(f):
            continue
        s = open(f, encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'__P__:override\("(\w+)", "(\w+)"', s):
            ov[m.group(1) + '::' + m.group(2)] += 1
        for m in re.finditer(r'__P__:ctor\("(\w+)"', s):
            ct[m.group(1)] += 1
        for m in re.finditer(r'__P__:method\("(\w+)", "(\w+)"', s):
            ME[m.group(1)] += 1
        for m in re.finditer(r'\bF\.(\w+)', s):
            F[m.group(1)] += 1
        for m in re.finditer(r'\bmc\([^,()]+?, "(\w+)"', s):
            MC[m.group(1)] += 1
        for m in re.finditer(r'\bcall\(self, "(\w+)"', s):
            CL[m.group(1)] += 1
        for m in re.finditer(r'\bK\.(\w+)', s):
            K[m.group(1)] += 1
        for m in re.finditer(r'__R__\.(\w+)', s):
            R[m.group(1)] += 1
print('missing', miss, 'libs', sorted(libs_seen))


def show(n, c, k=80):
    print('==', n, len(c))
    print(' '.join('%s:%d' % kv for kv in c.most_common(k)))


show('override', ov)
show('ctor', ct)
show('method-classes', ME)
show('F', F)
show('mc', MC, 300)
show('call', CL)
show('K', K, 250)
show('R', R)
