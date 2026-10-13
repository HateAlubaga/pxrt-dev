"""Which number do the Lua ports associate with each ProjectX M_* name?"""
import os, re, glob, collections
ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
pairs = collections.defaultdict(collections.Counter)
pk = collections.defaultdict(lambda: collections.defaultdict(set))
for f in glob.glob(os.path.join(ROOT, "*", "0.0.1", "main.lua")):
    pkg = f.split(os.sep)[-3]
    for line in open(f, encoding="utf-8", errors="replace"):
        # local M_FRAME = 3   |  M_FRAME = 3,  | == 3 then -- M_FRAME
        for m in re.finditer(r"\b(M_[A-Z_]+)\s*=\s*(\d+)", line):
            pairs[m.group(1)][int(m.group(2))] += 1; pk[m.group(1)][int(m.group(2))].add(pkg)
        m = re.search(r"==\s*(\d+)\s*(?:then|and|or|\))[^\n]*--[^\n]*?\b(M_[A-Z_]+)", line)
        if m:
            pairs[m.group(2)][int(m.group(1))] += 1; pk[m.group(2)][int(m.group(1))].add(pkg)
        m = re.search(r"--[^\n]*?\b(M_[A-Z_]+)\s*\(?\s*(\d+)\s*\)?", line)
        if m:
            pairs[m.group(1)][int(m.group(2))] += 1; pk[m.group(1)][int(m.group(2))].add(pkg)
for name, c in sorted(pairs.items(), key=lambda kv: -sum(kv[1].values())):
    print("%-24s" % name, ", ".join("%d:%d(%dp)" % (k, v, len(pk[name][k])) for k, v in c.most_common(6)))
