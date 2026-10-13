"""Census: which PX methods do .pxc scripts override / define, and which
messagetype numbers the Lua port uses in the same package."""
import os, re, glob, collections
ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
meth = collections.Counter(); mpk = collections.defaultdict(set)
re_m = re.compile(r"^\s*(?:override\s+)?[A-Za-z_][\w\*\s]*?\b([A-Za-z_]\w*)\s*::\s*([A-Za-z_]\w*)\s*\(", re.M)
pkg_methods = {}
for d in glob.glob(os.path.join(ROOT, "*", "0.0.1")):
    pkg = d.split(os.sep)[-2]
    ms = set()
    for p in glob.glob(os.path.join(d, "scripts_px", "*.pxc")):
        t = open(p, encoding="latin-1").read()
        t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
        t = re.sub(r"//[^\n]*", "", t)
        for m in re_m.finditer(t):
            k = m.group(1) + "::" + m.group(2)
            meth[k] += 1; mpk[k].add(pkg); ms.add(k)
    pkg_methods[pkg] = ms
print("methods:")
for k, v in meth.most_common(80):
    print("%5d %4dp  %s" % (v, len(mpk[k]), k))
# messagetypes used in lua
mt = collections.Counter(); mtp = collections.defaultdict(set)
for f in glob.glob(os.path.join(ROOT, "*", "0.0.1", "main.lua")):
    pkg = f.split(os.sep)[-3]
    s = open(f, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"\b[mM]essage[tT]ype\s*==\s*(\d+)|\bmsgType\s*==\s*(\d+)|\bmtype\s*==\s*(\d+)", s):
        n = next(g for g in m.groups() if g)
        mt[n] += 1; mtp[n].add(pkg)
print("messagetypes:", ", ".join("%s:%d/%dp" % (k, v, len(mtp[k])) for k, v in mt.most_common(40)))
