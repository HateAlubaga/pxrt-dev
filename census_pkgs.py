import re, sys, os, json, collections
base = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad\testout\lua'
pk = sys.argv[1:]
libs = set()
files = []
for p in pk:
    d = os.path.join(base, p)
    cj = json.load(open(os.path.join(d, 'pxchunks.json')))
    libs.update(cj['libs'])
    files += [os.path.join(d, c) for c in cj['chunks']]


def addlibs(l):
    d = os.path.join(base, '@lib', l)
    pj = os.path.join(d, 'pxchunks.json')
    cj = json.load(open(pj)) if os.path.exists(pj) else {'libs': [], 'chunks': []}
    for x in cj.get('libs', []):
        if x not in libs:
            libs.add(x)
            addlibs(x)
    for c in cj.get('chunks', []):
        files.append(os.path.join(d, c))


for l in list(libs):
    addlibs(l)
print('libs', sorted(libs), 'files', len(files))
F = collections.Counter(); C = collections.Counter(); M = collections.Counter()
KK = collections.Counter(); NEW = collections.Counter(); OV = collections.Counter()
for f in files:
    s = open(f, encoding='utf-8', errors='replace').read()
    F.update(re.findall(r'\bF\.(\w+)', s))
    C.update(re.findall(r'\bcall\(self, "(\w+)"', s))
    M.update(re.findall(r'\bmc\([^,]+, "(\w+)"', s))
    KK.update(re.findall(r'\bK\.(\w+)', s))
    NEW.update(re.findall(r'__R__\.new\("(\w+)"', s))
    for a, b in re.findall(r'__P__:(?:override|ctor)\("(\w+)", "?(\w*)', s):
        OV[a + '::' + b] += 1
for n, c in (('F', F), ('call', C), ('mc', M), ('K', KK), ('new', NEW), ('ov', OV)):
    print('==', n)
    print(' '.join('%s:%d' % x for x in c.most_common()))
