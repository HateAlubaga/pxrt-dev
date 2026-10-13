"""Census over all jelly packages: how wormcallback/This/messagetypes are used."""
import os, re, glob, collections, json, sys

ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
files = sorted(glob.glob(os.path.join(ROOT, "*", "0.0.1", "main.lua")))
this_members = collections.Counter()
this_pkgs = collections.defaultdict(set)
msg_lits = collections.Counter()
msg_pkgs = collections.defaultdict(set)
pxc_msgs = collections.Counter()
calls = collections.Counter()
call_pkgs = collections.defaultdict(set)
defined = collections.Counter()

re_cb = re.compile(r"function\s+wormcallback\s*\(([^)]*)\)")
re_this = re.compile(r"\bThis\s*([.:])\s*([A-Za-z_][A-Za-z0-9_]*)")
re_call = re.compile(r"(?<![.:\w])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
re_def = re.compile(r"function\s+([A-Za-z_][A-Za-z0-9_.:]*)\s*\(|local\s+function\s+([A-Za-z_][A-Za-z0-9_]*)|local\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*function")
KW = set("if elseif while for return and or not function local then do end until repeat in print pairs ipairs type tostring tonumber pcall error assert select setmetatable getmetatable rawget rawset require next unpack table string math os io load loadstring xpcall".split())

per_pkg = {}
for f in files:
    pkg = f.split(os.sep)[-3]
    s = open(f, encoding="utf-8", errors="replace").read()
    s_nc = re.sub(r"--\[\[.*?\]\]", "", s, flags=re.S)
    s_nc = re.sub(r"--[^\n]*", "", s_nc)
    params = re_cb.findall(s_nc)
    mnames = set()
    for p in params:
        ps = [x.strip() for x in p.split(",")]
        if len(ps) >= 3:
            mnames.add(ps[2])
    for mn in mnames:
        for m in re.finditer(r"\b" + re.escape(mn) + r"\s*==\s*(\d+)", s_nc):
            msg_lits[int(m.group(1))] += 1
            msg_pkgs[int(m.group(1))].add(pkg)
    for m in re_this.finditer(s_nc):
        k = m.group(1) + m.group(2)
        this_members[k] += 1
        this_pkgs[k].add(pkg)
    defs = set()
    for m in re_def.finditer(s_nc):
        defs.add((m.group(1) or m.group(2) or m.group(3)).split(".")[0].split(":")[0])
    for m in re_call.finditer(s_nc):
        n = m.group(1)
        if n in KW or n in defs:
            continue
        calls[n] += 1
        call_pkgs[n].add(pkg)
    for px in glob.glob(os.path.join(os.path.dirname(f), "scripts_px", "*.pxc")):
        t = open(px, encoding="latin-1").read()
        for m in re.finditer(r"\bM_[A-Z_]+", t):
            pxc_msgs[m.group(0)] += 1

out = sys.argv[1]
with open(out, "w", encoding="utf-8") as o:
    o.write("packages %d\n\n== messagetype literals (count, pkgs) ==\n" % len(files))
    for k, v in sorted(msg_lits.items()):
        o.write("%4d: %5d uses %4d pkgs\n" % (k, v, len(msg_pkgs[k])))
    o.write("\n== ProjectX M_* in .pxc ==\n")
    for k, v in pxc_msgs.most_common():
        o.write("%-24s %d\n" % (k, v))
    o.write("\n== This members (uses, pkgs) ==\n")
    for k, v in sorted(this_members.items(), key=lambda kv: -len(this_pkgs[kv[0]])):
        o.write("%-28s %5d %4d\n" % (k, v, len(this_pkgs[k])))
    o.write("\n== called globals not defined in-package (pkgs) ==\n")
    for k, v in sorted(calls.items(), key=lambda kv: -len(call_pkgs[kv[0]])):
        o.write("%-36s %5d %4d\n" % (k, v, len(call_pkgs[k])))
print("done", len(files))
