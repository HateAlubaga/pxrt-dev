"""Override / method census from corpus.json."""
import os, re, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))
ov = collections.Counter(); ovp = collections.defaultdict(set)
defs = collections.Counter()
sig = {}
re_m = re.compile(r"(?m)^\s*(override\s+)?([A-Za-z_][\w\*\s]*?)?\b([A-Za-z_]\w*)\s*::\s*([A-Za-z_]\w*)\s*\(([^)]*)\)")
for k, t in C.items():
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    pkg = k.split("/")[0]
    for m in re_m.finditer(t):
        name = m.group(3) + "::" + m.group(4)
        if m.group(1):
            ov[name] += 1; ovp[name].add(pkg)
            sig.setdefault(name, re.sub(r"\s+", " ", m.group(0).strip()))
        else:
            defs[m.group(3)] += 1
print("OVERRIDES (count, pkgs):")
for n, c in ov.most_common():
    print("%5d %4d  %s" % (c, len(ovp[n]), sig[n][:150]))
print("\nnon-override method owners (top 40):")
print(", ".join("%s:%d" % kv for kv in defs.most_common(40)))
