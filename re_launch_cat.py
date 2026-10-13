import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, r"C:/Users/Admin/pxrt_dev")
from re_launch_show import mem, names, fmt
S=0x1d0
def g(w,f):
    return mem.get(w*S+f)
print("w name  +30 +34 +38 | L0 L4 L8 | flags(L0c) bias push dmg dmgVar | L68(kind) L6c L70 | expl(Lb4) Lb8 Lbc")
for w in range(1,62):
    nm = names[w] if w < len(names) else "?"
    print(w, nm, [g(w,f) for f in (0x30,0x34,0x38)], "|", [g(w,0x3c+o) for o in (0,4,8)], "|", [fmt(g(w,0x3c+o)) for o in (0x0c,0x10,0x14,0x18,0x1c)], "|", [fmt(g(w,0x3c+o)) for o in (0x68,0x6c,0x70)], "|", [fmt(g(w,0x3c+o)) for o in (0xb4,0xb8,0xbc)])
