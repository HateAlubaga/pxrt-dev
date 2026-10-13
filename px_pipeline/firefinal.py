"""How did the port translate CWorm::FireFinal (240 packages)?"""
import os, re, glob, collections
ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
re_ff = re.compile(r"CWorm\s*::\s*FireFinal\s*\(")
c = collections.Counter(); ex = collections.defaultdict(list)
for d in sorted(glob.glob(os.path.join(ROOT, "*", "0.0.1"))):
    pkg = d.split(os.sep)[-2]
    has = False
    for p in glob.glob(os.path.join(d, "scripts_px", "*.pxc")):
        t = open(p, encoding="latin-1").read()
        if re_ff.search(re.sub(r"//[^\n]*", "", t)):
            has = True
    if not has:
        continue
    f = os.path.join(d, "main.lua")
    if not os.path.exists(f):
        c["nomain"] += 1; continue
    s = open(f, encoding="utf-8", errors="replace").read()
    code = re.sub(r"--[^\n]*", "", s)
    tags = []
    if "registerCallback_fireWeapon" in code: tags.append("fireWeapon")
    if "registerCallback_wormStartFiringWeapon" in code: tags.append("startFiring")
    if "registerCallback_weaponRelease" in code: tags.append("release")
    if re.search(r"essage[tT]ype\s*==\s*26", code): tags.append("mt26")
    if re.search(r"function\s+FireFinal|FireFinal\s*=|fire_final|firefinal", code, re.I): tags.append("FireFinalFn")
    if re.search(r"params\.weapon_name|params\.weaponName|params\.weapon\b", code): tags.append("params.weapon")
    k = "+".join(tags) or "NONE"
    c[k] += 1
    if len(ex[k]) < 6: ex[k].append(pkg)
for k, v in c.most_common():
    print("%4d %s   e.g. %s" % (v, k, " ".join(ex[k])))
