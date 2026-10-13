"""Which global functions do ports call with This (or sender) as an argument?"""
import os, re, glob, collections
ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
calls = collections.Counter(); pk = collections.defaultdict(set)
sendc = collections.Counter(); spk = collections.defaultdict(set)
for f in glob.glob(os.path.join(ROOT, "*", "0.0.1", "main.lua")):
    pkg = f.split(os.sep)[-3]
    s = open(f, encoding="utf-8", errors="replace").read()
    s = re.sub(r"--[^\n]*", "", s)
    for m in re.finditer(r"(?<![.:\w])([A-Za-z_]\w*)\s*\(([^()\n]*)\)", s):
        args = [a.strip() for a in m.group(2).split(",")]
        if "This" in args:
            calls[m.group(1)] += 1; pk[m.group(1)].add(pkg)
        if "sender" in args:
            sendc[m.group(1)] += 1; spk[m.group(1)].add(pkg)
print("This-arg:", ", ".join("%s:%d/%dp" % (k, v, len(pk[k])) for k, v in calls.most_common(60)))
print("sender-arg:", ", ".join("%s:%d/%dp" % (k, v, len(spk[k])) for k, v in sendc.most_common(30)))
