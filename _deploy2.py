import os, shutil, json, time, subprocess, sys
DEV = r'C:\Users\Admin\pxrt_dev'
JELLY = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly'
BK = r'C:\Users\Admin\pxrt_backup'
out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
if any(l.startswith(('wa.exe', 'worms')) for l in out.splitlines()):
    sys.exit('WA running')
files = ['pxrt.lua:pxrt_core.lua', 'pxrt_e_classes.lua', 'pxrt_e_funcs.lua', 'pxrt_e_hooks.lua', 'pxrt_engine.lua']
bk = os.path.join(BK, time.strftime('%Y%m%d_%H%M%S') + '_perf2')
os.makedirs(os.path.join(bk, 'lualibs'))
rep = []
for spec in files:
    dstname, _, srcname = spec.partition(':')
    srcname = srcname or dstname
    dst = os.path.join(JELLY, 'lualibs', dstname)
    shutil.copy2(dst, os.path.join(bk, 'lualibs', dstname))
    shutil.copyfile(os.path.join(DEV, srcname), dst)
    rep.append('lualibs\\' + dstname)
json.dump({'jelly': JELLY, 'created': [], 'replaced': rep}, open(os.path.join(bk, 'manifest.json'), 'w'), indent=1)
print('deployed', bk)
