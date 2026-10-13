import os, json, sys
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *
libdirs = set(os.listdir(os.path.join(LUA, '@lib')))
pk = set(d for d in os.listdir(LUA) if d != '@lib')
need = {}
for root in [LUA, os.path.join(LUA, '@lib')]:
    for d in os.listdir(root):
        pj = os.path.join(root, d, 'pxchunks.json')
        if not os.path.exists(pj): continue
        j = json.load(open(pj, encoding='utf-8'))
        for l in j.get('libs', []):
            if l not in libdirs:
                need.setdefault(l, []).append(d)
for l, u in sorted(need.items()):
    print(l, 'PKG' if l in pk else 'MISSING', len(u), u[:3])
