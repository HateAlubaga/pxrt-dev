import json,sys
exec(open(r'C:/Users/Admin/pxrt_dev/re_launch_sim.py').read().replace('json.dump','_x=lambda *a,**k:0;_x'))
unk=[(o,h) for o,h in hist.items() if any(v is None for v,a in h)]
import collections
c=collections.Counter()
for o,h in unk:
    for v,a in h:
        if v is None: c[a>>12]+=1
print(sorted(c.items()))
# list first 30 unknown stores with addr
n=0
for o,h in sorted(hist.items()):
    for v,a in h:
        if v is None and n<40:
            print(hex(o),hex(a)); n+=1
