"""How do ports interpret This.posX: fixed 16.16 or pixels? And which This:method() calls exist?"""
import os, re, glob, collections
ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
fixed = collections.Counter(); pix = collections.Counter(); meth = collections.Counter()
mpk = collections.defaultdict(set)
samples = collections.defaultdict(list)
for f in glob.glob(os.path.join(ROOT, "*", "0.0.1", "main.lua")):
    pkg = f.split(os.sep)[-3]
    s = open(f, encoding="utf-8", errors="replace").read()
    s = re.sub(r"--[^\n]*", "", s)
    for m in re.finditer(r"\b(?:This|this|obj|worm|self)\.(posX|posY|speedX|speedY)\b([^\n]{0,60})", s):
        tail = m.group(2)
        line_start = s.rfind("\n", 0, m.start()) + 1
        line = s[line_start:s.find("\n", m.end())]
        if re.search(r"65536|>>\s*16|0x10000|fromFixed|FIX|fixed", line, re.I):
            fixed[m.group(1)] += 1
            if len(samples["fixed"]) < 6: samples["fixed"].append(pkg + ": " + line.strip()[:110])
        else:
            pix[m.group(1)] += 1
            if len(samples["pix"]) < 10: samples["pix"].append(pkg + ": " + line.strip()[:110])
    for m in re.finditer(r"\bThis:([A-Za-z_]\w*)\s*\(", s):
        meth[m.group(1)] += 1; mpk[m.group(1)].add(pkg)
print("fixed", fixed); print("plain", pix)
for k, v in samples.items():
    print("--", k); print("\n".join(v))
print("methods:", ", ".join("%s:%d/%dp" % (k, v, len(mpk[k])) for k, v in meth.most_common(40)))
