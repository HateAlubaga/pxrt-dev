import re, os, json, collections, sys
B = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad\testout\lua'
ov = collections.Counter(); ct = collections.Counter(); cl = collections.Counter()
pk = [d for d in os.listdir(B) if d != '@lib' and os.path.isdir(os.path.join(B, d))]
only = sys.argv[1:]
for p in pk:
    if only and p not in only: continue
    d = os.path.join(B, p)
    try: pc = json.load(open(os.path.join(d, 'pxchunks.json')))
    except Exception: continue
    for x in pc['chunks']:
        s = open(os.path.join(d, x), encoding='utf-8', errors='replace').read()
        for m in re.finditer(r'__P__:override\(("?\w+"?), "(\w+)"', s): ov[(m.group(1), m.group(2))] += 1
        for m in re.finditer(r'__P__:ctor\("(\w+)"', s): ct[m.group(1)] += 1
        for m in re.finditer(r'__P__:class\("(\w+)", "(\w*)"', s): cl[(m.group(1), m.group(2))] += 1
print(len(pk), 'pkgs')
print('OVERRIDES', sorted(ov.items(), key=lambda x: -x[1])[:80])
print('CTOR', ct.most_common(30))
print('BASES', collections.Counter(b for (_, b) in cl).most_common(30))
