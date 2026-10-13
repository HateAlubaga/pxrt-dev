import sys, re, io
sys.path.insert(0, r"C:/Users/Admin/pxrt_dev/rs")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import lib
L = lib.lin()
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
dlo, dhi = int(sys.argv[3], 16), int(sys.argv[4], 16)
pat = re.compile(r"\[(e[a-z]{2}) \+ (0x[0-9a-f]+)\]")
uses = {}
for a, sz, t in L:
    if a < lo or a >= hi: continue
    for m in pat.finditer(t):
        d = int(m.group(2), 16)
        if dlo <= d < dhi:
            uses.setdefault(d, []).append((a, t))
for d in sorted(uses):
    print("== +%x (L=%x if launch copy; DB-L=%x)" % (d, d - 0x15c, d - 0x2d4 + 0x0c))
    for a, t in uses[d]:
        print("   %08x %s" % (a, t))
