import re, glob, collections, json, os
R = collections.Counter(); F = collections.Counter(); C = collections.Counter(); M = collections.Counter(); P = collections.Counter()
Rp = collections.defaultdict(set); Fp = collections.defaultdict(set); Cp = collections.defaultdict(set); Mp = collections.defaultdict(set)
for f in glob.glob('testout/lua/*/*.lua'):
    pkg = os.path.basename(os.path.dirname(f))
    s = open(f, encoding='utf-8', errors='replace').read()
    for m in re.findall(r'__R__\.(\w+)', s): R[m] += 1; Rp[m].add(pkg)
    for m in re.findall(r'__P__:(\w+)', s): P[m] += 1
    for m in re.findall(r'\bF\.(\w+)', s): F[m] += 1; Fp[m].add(pkg)
    for m in re.findall(r'\bcall\(self, "(\w+)"', s): C[m] += 1; Cp[m].add(pkg)
    for m in re.findall(r'\bmc\([^,()]+?, "(\w+)"', s): M[m] += 1; Mp[m].add(pkg)


def dump(name, c, p):
    print('==', name, len(c))
    print(' '.join('%s:%d/%d' % (k, v, len(p[k]) if p else 0) for k, v in c.most_common()))


dump('R', R, Rp); dump('P', P, None); dump('F', F, Fp); dump('call', C, Cp); dump('mc', M, Mp)
json.dump({'R': {k: len(Rp[k]) for k in R}, 'F': {k: len(Fp[k]) for k in F}, 'call': {k: len(Cp[k]) for k in C},
           'mc': {k: len(Mp[k]) for k in M}}, open('px/surface.json', 'w'), indent=0)
