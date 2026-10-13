"""Census over every .pxc: requires, overrides, identifiers, sizes, where libs live."""
import os, re, glob, collections, json
J = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly"
files = glob.glob(os.path.join(J, "packages", "*", "0.0.1", "scripts_px", "*.pxc"))
allpxc = []
for root, dirs, fs in os.walk(J):
    if "packages_backup" in root:
        continue
    for f in fs:
        if f.lower().endswith(".pxc") or f.lower().endswith(".pxl") or f.lower().endswith(".pxh"):
            allpxc.append(os.path.join(root, f))
print("pxc in packages:", len(files), " all px-like files under jelly:", len(allpxc))
ext = collections.Counter(os.path.splitext(f)[1].lower() for f in allpxc)
print("ext:", ext)
req = collections.Counter(); reqpk = collections.defaultdict(set)
ovr = collections.Counter(); ovrpk = collections.defaultdict(set)
cls = collections.Counter()
idents = collections.Counter()
sizes = []
kw = collections.Counter()
for p in files:
    pkg = p.split(os.sep)[-4]
    t = open(p, encoding="latin-1").read()
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    sizes.append(len(t.splitlines()))
    for m in re.finditer(r"^\s*require\s+([^;]+);", t, re.M):
        for r in m.group(1).split(","):
            r = r.strip(); req[r] += 1; reqpk[r].add(pkg)
    for m in re.finditer(r"\boverride\s+[\w\*\s]*?\b(\w+)\s*::\s*(\w+)\s*\(", t):
        k = m.group(1) + "::" + m.group(2); ovr[k] += 1; ovrpk[k].add(pkg)
    for m in re.finditer(r"\bclass\s+(\w+)", t):
        cls[m.group(1)] += 1
    for w in re.findall(r"[A-Za-z_]\w*", t):
        idents[w] += 1
    for k in ["switch", "case", "for", "while", "do", "new", "delete", "struct", "class", "enum", "sizeof",
              "goto", "?", "->", "::", "super", "override", "static", "const", "#define", "#include", "typedef", "virtual", "template"]:
        if k in ("?", "->", "::", "#define", "#include"):
            kw[k] += t.count(k)
        else:
            kw[k] += len(re.findall(r"\b%s\b" % k, t))
print("lines total", sum(sizes), "max", max(sizes), "median", sorted(sizes)[len(sizes)//2])
print("requires:", ", ".join("%s:%d" % (k, len(reqpk[k])) for k, _ in req.most_common(40)))
print("keywords:", kw)
print("classes:", cls.most_common(30))
print("overrides:")
for k, v in ovr.most_common(60):
    print("  %4d %3dp %s" % (v, len(ovrpk[k]), k))
json.dump({"ident": idents.most_common(1500)}, open(os.path.join(os.path.dirname(__file__), "pxident.json"), "w"))
# locate library sources
names = set(req)
for f in allpxc:
    b = os.path.splitext(os.path.basename(f))[0]
    if b in names:
        print("LIB", b, f)
