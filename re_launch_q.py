import sys
sys.path.insert(0, r"C:/Users/Admin/pxrt_dev")
from re_launch_show import mem, names, fmt
S=0x1d0
# for each launch-field offset in A block, show which weapons have nonzero values
def g(w,L): return mem.get(w*S+0x3c+L)
ws=[w for w in range(1,70) if g(w,0x68) in (1,2,3,4,5)]
print("missile-like weapons:", ws)
for L in [int(x,16) for x in sys.argv[1].split(",")]:
    print("L+%x:"%L, {w:fmt(g(w,L)) for w in ws if g(w,L) not in (0,None)})
