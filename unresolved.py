import re, os, collections
base = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad\testout\lua'
defined = set()
used = collections.Counter()
usedpk = collections.defaultdict(set)
for root, ds, fs in os.walk(base):
    for f in fs:
        if not f.endswith('.lua'):
            continue
        s = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
        defined.update(re.findall(r'__P__:func\("(\w+)"', s))
        for n in re.findall(r'__G__\.(\w+)\(', s):
            used[n] += 1
            usedpk[n].add(os.path.basename(os.path.dirname(os.path.join(root, f))))
        # global variable declarations are not functions; skip
un = [(n, c) for n, c in used.most_common() if n not in defined]
print(len(un))
for n, c in un:
    print('%s:%d(%d pk)' % (n, c, len(usedpk[n])), end=' ')
print()
