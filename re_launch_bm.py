import sys, struct
exec(open(r"C:/Users/Admin/pxrt_dev/re_launch_jt.py").read().split("for a in")[0])
tbl = struct.unpack("<%dI" % 12, rd(0x50bee4, 48))
print([hex(x) for x in tbl])
bm = rd(0x50bf08, 0x7d)
out = {}
for i, b in enumerate(bm):
    out.setdefault(b, []).append(i+2)
for b, ms in sorted(out.items()):
    print(b, hex(tbl[b]) if b < len(tbl) else '?', [hex(m) for m in ms][:20], len(ms))
