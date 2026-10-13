import re, os, json, collections, sys
base = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad\testout\lua'
ENGINE = {'CWorm','CMissile','CMine','CCrate','COilDrum','CGas','CArrow','CCanister','CCross','CGObject','CObject','CTurnGame','CTeam','CFilter','CFire','CAirStrike','CCloud','CSmoke','CFlame','COldWorm','CLand'}
libs_cache = {}

def chunks_of(d):
    pj = os.path.join(d, 'pxchunks.json')
    if not os.path.exists(pj):
        return {'libs': [], 'chunks': []}
    return json.load(open(pj))

def lib_classes(l, seen):
    if l in seen:
        return {}
    seen.add(l)
    d = os.path.join(base, '@lib', l)
    cj = chunks_of(d)
    out = {}
    for c in cj['chunks']:
        s = open(os.path.join(d, c), encoding='utf-8', errors='replace').read()
        for n, b in re.findall(r'__P__:class\("(\w+)", "(\w*)"\)', s):
            out[n] = b
    for x in cj['libs']:
        out.update(lib_classes(x, seen))
    return out

rows = {}
for p in sorted(os.listdir(base)):
    if p == '@lib':
        continue
    d = os.path.join(base, p)
    if not os.path.isdir(d):
        continue
    cj = chunks_of(d)
    cls = {}
    ov = collections.Counter()
    ctorov = collections.Counter()
    usesF = collections.Counter()
    for c in cj['chunks']:
        fp = os.path.join(d, c)
        if not os.path.exists(fp):
            continue
        s = open(fp, encoding='utf-8', errors='replace').read()
        for n, b in re.findall(r'__P__:class\("(\w+)", "(\w*)"\)', s):
            cls[n] = b
        for a, b in re.findall(r'__P__:override\("(\w+)", "(\w+)"', s):
            ov[a + '::' + b] += 1
        for a in re.findall(r'__P__:ctor\("(\w+)", function\([^)]*\)[^\n]*\n(?:.*\n)*?end, true\)', s):
            pass
        for a in re.findall(r'__P__:ctor\("(\w+)",', s):
            pass
        usesF.update(re.findall(r'\bF\.(\w+)', s))
    seen = set()
    libcls = {}
    for l in cj['libs']:
        libcls.update(lib_classes(l, seen))
    # resolve engine root of every class
    allc = dict(libcls); allc.update(cls)
    def root(n, depth=0):
        if n in ENGINE or depth > 12:
            return n
        b = allc.get(n)
        if b is None or b == '':
            return None
        return root(b, depth + 1)
    roots = collections.Counter()
    for n, b in cls.items():
        r = root(n)
        roots[r or 'none'] += 1
    rows[p] = {'roots': dict(roots), 'ov': dict(ov), 'libs': cj['libs']}

json.dump(rows, open(r'C:\Users\Admin\pxrt_dev\census2.json', 'w'), indent=1)
agg = collections.Counter()
ovagg = collections.Counter()
for p, r in rows.items():
    for k in r['roots']:
        agg[k] += 1
    for k in r['ov']:
        ovagg[k] += 1
print('pkgs', len(rows))
print('roots', agg.most_common())
print('overrides', ovagg.most_common(40))
# packages without any script classes and overrides
trivial = [p for p, r in rows.items() if not r['roots'] and not r['ov']]
print('no classes/overrides', len(trivial))
