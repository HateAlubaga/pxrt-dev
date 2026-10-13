import re, os, collections
base = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad\testout\lua'
mem = collections.Counter()
other = collections.Counter()
for root, ds, fs in os.walk(base):
    for f in fs:
        if not f.endswith('.lua'):
            continue
        s = open(os.path.join(root, f), encoding='utf-8', errors='replace').read()
        names = set(re.findall(r'(?:__G__|self)\.(\w+) = F\.LoadSprite', s))
        names |= set(re.findall(r'local (\w+) = F\.LoadSprite', s))
        for n in names:
            for m in re.findall(r'\b%s\.(\w+)' % re.escape(n), s):
                mem[m] += 1
            # usage as bare value (passed as arg)
            for m in re.findall(r'[(, ]%s[,)]' % re.escape('__G__.' + n), s):
                other['bare'] += 1
print(mem.most_common(30))
print(other)
