import sys, io, re
sys.path.insert(0, r"C:/Users/Admin/pxrt_dev/rs")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import lib
L = lib.lin()
lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
import json
OC = json.load(open(r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\offsetcache.json"))
REV = {v: k for k, v in OC.items()}
for a, sz, t in L:
    if lo <= a < hi:
        s = "%08x  %s" % (a, t)
        m = re.match(r"call (0x[0-9a-f]+)$", t)
        if m and int(m.group(1), 16) in REV:
            s += "   ; " + REV[int(m.group(1), 16)]
        print(s)
