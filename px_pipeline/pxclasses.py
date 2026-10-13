"""Survey ProjectX .pxc: which classes define Message(), and what they derive from."""
import os, re, glob, collections
ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
base_count = collections.Counter()
base_pkgs = collections.defaultdict(set)
msg_kinds = collections.Counter()
examples = collections.defaultdict(list)
re_cls = re.compile(r"^\s*([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)\s*(?:$|//|\{)", re.M)
re_msg = re.compile(r"\b([A-Za-z_]\w*)\s*::\s*Message\s*\(")
for px in glob.glob(os.path.join(ROOT, "*", "0.0.1", "scripts_px", "*.pxc")):
    pkg = px.split(os.sep)[-4]
    script = os.path.splitext(os.path.basename(px))[0]
    t = open(px, encoding="latin-1").read()
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    bases = {m.group(1): m.group(2) for m in re_cls.finditer(t)}
    for m in re_msg.finditer(t):
        cls = m.group(1)
        if cls == script:
            kind = "SCRIPT"
        else:
            kind = bases.get(cls, "?" + cls)
        msg_kinds[kind] += 1
        base_pkgs[kind].add(pkg)
        if len(examples[kind]) < 4:
            examples[kind].append("%s/%s:%s" % (pkg, script, cls))
for k, v in msg_kinds.most_common(40):
    print("%-22s %4d msgs %4d pkgs  e.g. %s" % (k, v, len(base_pkgs[k]), ", ".join(examples[k])))
