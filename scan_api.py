import re, os, json, collections, sys
B = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad\testout\lua'
pk = sys.argv[1:]
files = []
libs = set()
for p in pk:
    d = os.path.join(B, p)
    pc = json.load(open(os.path.join(d, 'pxchunks.json')))
    files += [os.path.join(d, x) for x in pc['chunks']]
    libs.update(pc['libs'])


def addlib(l):
    d = os.path.join(B, '@lib', l)
    if not os.path.isdir(d):
        return
    pc = json.load(open(os.path.join(d, 'pxchunks.json')))
    for x in pc['chunks']:
        files.append(os.path.join(d, x))
    for dep in pc.get('libs', []):
        if dep not in libs:
            libs.add(dep)
            addlib(dep)


for l in list(libs):
    addlib(l)
F = collections.Counter()
K = collections.Counter()
MC = collections.Counter()
CALL = collections.Counter()
G = collections.Counter()
for f in set(files):
    s = open(f, encoding='utf-8', errors='replace').read()
    for m in re.finditer(r'\bF\.(\w+)', s):
        F[m.group(1)] += 1
    for m in re.finditer(r'\bK\.(\w+)', s):
        K[m.group(1)] += 1
    for m in re.finditer(r'\bmc\([^,]+,\s*"(\w+)"', s):
        MC[m.group(1)] += 1
    for m in re.finditer(r'\bcall\(\s*"(\w+)"', s):
        CALL[m.group(1)] += 1
    for m in re.finditer(r'__G__\.(\w+)', s):
        G[m.group(1)] += 1
print('files', len(set(files)), 'libs', sorted(libs))
print('F', dict(F))
print('K', len(K), ' '.join(sorted(K)))
print('MC', dict(MC))
print('CALL', dict(CALL))
print('G', ' '.join(sorted(G)))
