"""Deploy round 3 (engine-object ctors via host birth log, GG.queue2, CMine::Explosion) + rebuilt wkJellyWorm.dll.
Runtime files only (does not reconvert packages). Backup + manifest in pxrt_backup\\<stamp>_ctors."""
import os, shutil, json, time, subprocess, sys, hashlib
DEV = r'C:\Users\Admin\pxrt_dev'
GAME = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon'
JELLY = os.path.join(GAME, 'jelly')
BK = r'C:\Users\Admin\pxrt_backup'
DLL_SRC = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\build\Release\wkJellyWorm.dll'

out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
if any(l.startswith(('wa.exe', 'worms')) for l in out.splitlines()):
    sys.exit('WA running')

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

# dst name in jelly\lualibs : source path
files = {
    'pxrt.lua': os.path.join(DEV, 'pxrt_core.lua'),
    'pxrt_e_classes.lua': os.path.join(DEV, 'pxrt_e_classes.lua'),
    'pxrt_e_funcs.lua': os.path.join(DEV, 'pxrt_e_funcs.lua'),
    'pxrt_e_game.lua': os.path.join(DEV, 'pxrt_e_game.lua'),
    'pxrt_e_hooks.lua': os.path.join(DEV, 'pxrt_e_hooks.lua'),
    'pxrt_e_soft.lua': os.path.join(DEV, 'pxrt_e_soft.lua'),
    'pxrt_e_terrain.lua': os.path.join(DEV, 'pxrt_e_terrain.lua'),
    'pxrt_engine.lua': os.path.join(DEV, 'pxrt_engine.lua'),
    'pxl_utils.lua': os.path.join(DEV, 'out', 'lualibs', 'pxl_utils.lua'),
}
stamp = time.strftime('%Y%m%d_%H%M%S')
bk = os.path.join(BK, stamp + '_ctors')
os.makedirs(os.path.join(bk, 'lualibs'))
rep = []
for dst, src in files.items():
    d = os.path.join(JELLY, 'lualibs', dst)
    shutil.copy2(d, os.path.join(bk, 'lualibs', dst))
    shutil.copyfile(src, d)
    if md5(src) != md5(d):
        sys.exit('copy mismatch ' + dst)
    rep.append('lualibs\\' + dst)
# host DLL: backup next to it (same convention as earlier) and in the backup dir
dll = os.path.join(GAME, 'wkJellyWorm.dll')
shutil.copy2(dll, os.path.join(bk, 'wkJellyWorm.dll'))
shutil.copy2(dll, dll + '.bak_claude_' + stamp)
shutil.copyfile(DLL_SRC, dll)
if md5(DLL_SRC) != md5(dll):
    sys.exit('dll copy mismatch')
json.dump({'jelly': JELLY, 'created': [], 'replaced': rep, 'game_replaced': ['wkJellyWorm.dll']},
          open(os.path.join(bk, 'manifest.json'), 'w'), indent=1)
print('deployed', bk, 'dll', md5(dll))
