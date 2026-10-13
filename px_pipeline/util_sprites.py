import os, re, shutil, time
from PIL import Image

G = r"C:/Program Files (x86)/by Decepticon/Worms Armageddon/jelly/packages/"
TS = time.strftime("%Y%m%d_%H%M%S")

def pkg(p):
    return G + p + "/0.0.1/"

def backup(path):
    b = path + ".bak_claude_" + TS
    shutil.copy2(path, b)
    return b

def read(path):
    return open(path, encoding="utf-8").read()

def write(path, s):
    open(path, "w", encoding="utf-8", newline="").write(s)

MARK = "-- [claude] weapon-scoped sprite overrides"

def wrapper(lines):
    body = "\n".join("    " + l for l in lines)
    return f"""

{MARK}
-- ProjectX swapped the shared parachute / jetpack sprites only for its own
-- weapon. SetWeaponSpriteOverride holds only while that weapon is active, so
-- other utilities keep their own (or the native) graphics.
do
  local __prev_init_ws = initialize
  function initialize()
    local ok, r = true, 0
    if __prev_init_ws then ok, r = pcall(__prev_init_ws) end
    if not ok then print("[claude] initialize failed: " .. tostring(r)) end
    if SetWeaponSpriteOverride then
{body}
    end
    return (ok and r) or 0
  end
end
"""

def blank(path):
    if not os.path.exists(path):
        Image.new("RGBA", (1, 1), (0, 0, 0, 0)).save(path)

def frames(path, n):
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    fh = h // n
    return [im.crop((0, i * fh, w, (i + 1) * fh)) for i in range(n)]

def sheet(frs, path):
    w, h = frs[0].size
    out = Image.new("RGBA", (w, h * len(frs)), (0, 0, 0, 0))
    for i, f in enumerate(frs):
        out.alpha_composite(f, (0, i * h))
    out.save(path)

# ---- generated assets ----
# Glider: slot 288 (canopy held open) shows the fully opened glider only.
a = pkg("utility_hangglider") + "assets/"
sheet([frames(a + "wgldlnk.png", 10)[-1]], a + "wgldopen.png")

# Balloon: ProjectX drew the balloon 46px above the hanging worm, tinted with
# the team colour. Bake both into one sprite (worm 6px forward, red balloon).
a = pkg("utility_balloon") + "assets/"
worm = frames(a + "wballoon.png", 17)     # 90x90
ball = frames(a + "balloon.png", 16)      # 80x80
FW, FH = 104, 170                         # centred on the worm position
cx, cy = FW // 2, FH // 2
out = []
for i in range(17):
    f = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    b = ball[min(15, i * 16 // 17)]
    r, g, bl, al = b.split()
    lum = b.convert("L")
    tint = Image.merge("RGBA", (lum.point(lambda v: min(255, 60 + v * 3)),
                                lum.point(lambda v: v // 2),
                                lum.point(lambda v: v // 2), al))
    # facing left (sprites face left; WA mirrors for right): forward = -x
    f.alpha_composite(tint, (cx - 6 - 40, cy - 43 - 40))
    f.alpha_composite(worm[i], (cx - 6 - 45, cy + 3 - 45))
    out.append(f)
sheet(out, a + "wballoon_full.png")

for p in ("utility_helicopter_revised", "utility_ufo", "utility_spitfire"):
    blank(pkg(p) + "assets/blank.png")

# ---- per-package edits ----
JET = [167, 168, 169, 170, 331, 332, 333]

def jet_lines(name, file, n):
    l = [f'SetWeaponSpriteOverride("{name}", {t}, "{file}", {n}, 1)' for t in JET]
    l += [f'SetWeaponSpriteOverride("{name}", {t}, "blank.png", 1, 0)' for t in (171, 172)]
    return l

PLAN = {
    "utility_umbrella": [
        'SetWeaponSpriteOverride("Umbrella Wep", 287, "wparalnk.png", 17, 0)',
        'SetWeaponSpriteOverride("Umbrella Wep", 288, "wparacht.png", 13, 3)',
        'SetWeaponSpriteOverride("Umbrella Wep", 289, "wparbak.png", 6)',
        'SetWeaponSpriteOverride("Umbrella Wep", 290, "wparbaku.png", 6)',
        'SetWeaponSpriteOverride("Umbrella Wep", 291, "wparbakd.png", 6)',
    ],
    "utility_hangglider": [
        'SetWeaponSpriteOverride("Glider", 287, "wgldlnk.png", 10, 0)',
        'SetWeaponSpriteOverride("Glider", 288, "wgldopen.png", 1, 0)',
        'SetWeaponSpriteOverride("Glider", 289, "wgldbak.png", 6)',
        'SetWeaponSpriteOverride("Glider", 290, "wgldbak.png", 6)',
        'SetWeaponSpriteOverride("Glider", 291, "wgldbak.png", 6)',
    ],
    "utility_wings": [
        'SetWeaponSpriteOverride("Wings Wep", 287, "wflyspr.png", 10, 1)',
        'SetWeaponSpriteOverride("Wings Wep", 288, "wflyspr.png", 10, 1)',
        'SetWeaponSpriteOverride("Wings Wep", 289, "wflybak.png", 6)',
        'SetWeaponSpriteOverride("Wings Wep", 290, "wflybaku.png", 6)',
        'SetWeaponSpriteOverride("Wings Wep", 291, "wflybakd.png", 6)',
    ],
    "utility_yoshi": [
        'SetWeaponSpriteOverride("Yoshi Wep", 287, "wflyspr.png", 2, 1)',
        'SetWeaponSpriteOverride("Yoshi Wep", 288, "wflyspr.png", 2, 1)',
        'SetWeaponSpriteOverride("Yoshi Wep", 289, "wflybak.png", 4)',
        'SetWeaponSpriteOverride("Yoshi Wep", 290, "wflybaku.png", 4)',
        'SetWeaponSpriteOverride("Yoshi Wep", 291, "wflybakd.png", 4)',
    ],
    "utility_balloon": [
        'SetWeaponSpriteOverride("Balloon W", 287, "wballoon_full.png", 17, 3)',
        'SetWeaponSpriteOverride("Balloon W", 288, "wballoon_full.png", 17, 3)',
        'SetWeaponSpriteOverride("Balloon W", 289, 272)',
        'SetWeaponSpriteOverride("Balloon W", 290, 273)',
        'SetWeaponSpriteOverride("Balloon W", 291, 274)',
    ],
    "utility_helicopter_revised": jet_lines("Helicopter", "heli-anim.png", 10),
    "utility_ufo": jet_lines("Ufo", "ufo-anim.png", 3),
    "utility_spitfire": jet_lines("Spitfire", "spitfire-anim-l.png", 3),
}

for p, lines in PLAN.items():
    path = pkg(p) + "main.lua"
    s = read(path)
    if MARK in s:
        print(p, "already patched, skip")
        continue
    print(p, "backup", os.path.basename(backup(path)))
    if p == "utility_umbrella":
        s2 = re.sub(r"-- BEGIN ported ProjectX sprite overrides\n.*?-- END ported ProjectX sprite overrides\n?",
                    "", s, flags=re.S)
        assert s2 != s, "umbrella block not found"
        s = s2
    if p == "utility_spitfire":
        i = s.index("local spitfire_weapon_id = registerCustomWeapon(")
        j = s.index('    "spitfire-anim-l.png",\n    "Spitfire",\n    ""\n)\n', i)
        j += len('    "spitfire-anim-l.png",\n    "Spitfire",\n    ""\n)\n')
        s = s[:i] + ("-- [claude] the weapon is registered in initialize(); this load-time\n"
                     "-- duplicate passed WeaponStruct.new a table and aborted the package.\n"
                     "local spitfire_weapon_id = nil\n") + s[j:]
    s = s.rstrip("\n") + "\n" + wrapper(lines)
    write(path, s)
    print(p, "patched", len(lines), "overrides")
print("TS", TS)
