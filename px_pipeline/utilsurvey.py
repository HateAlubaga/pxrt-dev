"""Survey utility packages: registered weapons, native WA behaviour of their
WeaponStruct (type 0x30 / subtype 0x34 compared to vanilla), script shape."""
import os, re, glob, json, sys, collections

J = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly"
P = os.path.join(J, "packages")
van = json.load(open(os.path.join(J, "vanilla_weapons.json")))["weapons"]

def off(i):  # vanilla fields[i] -> struct offset
    return 8 + 4 * i

VAN = []
for w in van:
    f = {off(i): v for i, v in enumerate(w["fields"])}
    VAN.append((w["id"], w["name1"], f))

def native(fields):
    """Closest vanilla weapon by (0x30 type, 0x34 subtype) then field overlap."""
    t, s = fields.get(0x30, 0), fields.get(0x34, 0)
    best, bs = None, -1
    for vid, name, vf in VAN:
        if vid == 0:
            continue
        score = 0
        if vf.get(0x30, 0) == t: score += 10
        if vf.get(0x34, 0) == s: score += 10
        # utility subtypes (type 4, sub 19) differ by 0x3C
        if vf.get(0x3C, 0) == fields.get(0x3C, 0): score += 3
        if vf.get(0x38, 0) == fields.get(0x38, 0): score += 1
        if score > bs:
            bs, best = score, name
    return best, t, s

FIELD_RE = re.compile(r"^\s*(\w+)\.(panelRow|unknown[0-9A-F]+)\s*=\s*(-?\d+)", re.M)
REG_RE = re.compile(r"registerCustomWeapon\(\s*(\w+)\s*,\s*\"([^\"]*)\"\s*,\s*\"([^\"]*)\"\s*,\s*\"([^\"]*)\"")
CLONE_RE = re.compile(r"weaponFrom\(|cloneVanillaWeapon\(")

rows = []
names = sorted(d for d in os.listdir(P) if d.startswith(("utility", "utils")))
for pkg in names:
    vers = sorted(glob.glob(os.path.join(P, pkg, "*", "main.lua")))
    if not vers:
        rows.append((pkg, "NO main.lua", "", "", ""))
        continue
    src = open(vers[-1], encoding="latin1").read()
    structs = collections.defaultdict(dict)
    for var, fld, val in FIELD_RE.findall(src):
        o = 0x8 if fld == "panelRow" else int(fld[7:], 16)
        structs[var][o] = int(val)
    regs = REG_RE.findall(src)
    pxc = glob.glob(os.path.join(os.path.dirname(vers[-1]), "scripts_px", "*.pxc"))
    pxlines = sum(len(open(f, encoding="latin1").read().splitlines()) for f in pxc)
    this_uses = len(re.findall(r"\bThis\.\w+", src))
    hooks = []
    for h in ("registerCallback_onFrame", "registerCallback_fireWeapon", "CTaskWorm_RegisterCallback", "drawSprite", "autowire"):
        if h in src:
            hooks.append(h.replace("registerCallback_", "rc_"))
    req = re.findall(r"require\s*\(?\s*\"(\w+)\"", src)
    wl = []
    for var, img, n1, n2 in regs:
        nat = native(structs.get(var, {}))
        wl.append("%s [%s t%d/s%d]" % (n1, nat[0], nat[1], nat[2]))
    rows.append((pkg, "; ".join(wl) or "-", "pxc=%d" % pxlines, "This.=%d" % this_uses, ",".join(hooks), ",".join(r for r in req if r not in ("pxcompat", "json"))))

for r in rows:
    print(" | ".join(str(x) for x in r))
