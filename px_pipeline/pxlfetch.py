"""Fetch PX library sources (.pxl) as data and extract their text sections.
PXL layout seen: 02 01 <u16?> 00 <count?>... then entries: <u32 type?> <u32 namelen> name <u32 len> body."""
import os, sys, struct, urllib.request, json
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "pxl")
os.makedirs(OUT, exist_ok=True)
API = "https://api.github.com/repos/reddazxfi/wapx-scripts/contents/PXL/"
SMALL = ["utils", "utils_steps", "wosc_lib", "p_sprite_builder", "p_animation", "pxparticles", "particles",
         "utils_pyroman", "pxairstrike", "pxtexbeam", "pxbullet", "utils_r2", "utils_red", "pxeffects",
         "red_sprite_builder", "script_newphysics", "sprite_aim_guns"]
names = sys.argv[1:] or SMALL


def fetch(n):
    p = os.path.join(OUT, n + ".pxl")
    if os.path.exists(p):
        return open(p, "rb").read()
    req = urllib.request.Request(API + n + ".pxl", headers={"Accept": "application/vnd.github.raw"})
    b = urllib.request.urlopen(req, timeout=60).read()
    open(p, "wb").write(b)
    return b


def texts(b):
    """Heuristic: find printable runs > 200 bytes preceded by a u32 length equal to the run length."""
    res = []
    i = 0
    n = len(b)
    while i < n - 4:
        ln = struct.unpack_from("<I", b, i)[0]
        if 16 <= ln <= n - i - 4:
            chunk = b[i + 4:i + 4 + ln]
            # source text: mostly printable
            pr = sum(1 for c in chunk[:400] if 32 <= c < 127 or c in (9, 10, 13))
            if pr >= min(len(chunk), 400) * 0.97 and (b"(" in chunk or b";" in chunk):
                # name just before: u32 namelen + name
                res.append((i, chunk.decode("latin-1")))
                i += 4 + ln
                continue
        i += 1
    return res


for nm in names:
    try:
        b = fetch(nm)
    except Exception as e:
        print("FAIL", nm, e); continue
    ts = texts(b)
    total = 0
    with open(os.path.join(OUT, nm + ".pxc"), "w", encoding="utf-8") as f:
        for off, t in ts:
            f.write("//==== section @%d ====\n" % off)
            f.write(t.replace("\r\n", "\n"))
            f.write("\n")
            total += len(t)
    print(nm, len(b), "sections", len(ts), "chars", total)
