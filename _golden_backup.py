"""Golden backup: full snapshot of the working state (game jelly lualibs+packages, DLL, ini, pxrt_dev sources, host src)."""
import os, shutil, json, time, hashlib, sys
GAME = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon'
DEV = r'C:\Users\Admin\pxrt_dev'
SRC = r'C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm'
tag = sys.argv[1] if len(sys.argv) > 1 else 'round'
dst = os.path.join(r'C:\Users\Admin\pxrt_backup', 'GOLDEN_' + time.strftime('%Y%m%d_%H%M') + '_' + tag)
os.makedirs(dst)

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

items = [
    (os.path.join(GAME, 'wkJellyWorm.dll'), 'game\\wkJellyWorm.dll'),
    (os.path.join(GAME, 'wkJellyWorm.ini'), 'game\\wkJellyWorm.ini'),
    (os.path.join(GAME, 'jelly', 'lualibs'), 'game\\jelly\\lualibs'),
    (os.path.join(GAME, 'jelly', 'packages'), 'game\\jelly\\packages'),
    (os.path.join(SRC, 'src'), 'host\\src'),
    (os.path.join(SRC, 'CMakeLists.txt'), 'host\\CMakeLists.txt'),
]
for f in os.listdir(DEV):
    p = os.path.join(DEV, f)
    if os.path.isfile(p) and f.endswith(('.lua', '.py', '.sh', '.txt', '.json')):
        items.append((p, 'pxrt_dev\\' + f))
for d in ('harness', 'px_pipeline'):
    items.append((os.path.join(DEV, d), 'pxrt_dev\\' + d))

skip = shutil.ignore_patterns('out', 'testout', '__pycache__', '*.jsonl')
for s, rel in items:
    t = os.path.join(dst, rel)
    os.makedirs(os.path.dirname(t), exist_ok=True)
    if os.path.isdir(s):
        shutil.copytree(s, t, ignore=skip if rel.startswith('pxrt_dev') else None)
    else:
        shutil.copy2(s, t)

man = {}
for root, _, files in os.walk(dst):
    for f in files:
        p = os.path.join(root, f)
        man[os.path.relpath(p, dst)] = md5(p)
json.dump({'created': time.strftime('%Y-%m-%d %H:%M:%S'), 'files': man}, open(os.path.join(dst, 'manifest.json'), 'w'), indent=0)
open(os.path.join(dst, 'RESTORE.txt'), 'w').write(
    'Restore (WA.exe must not run): copy game\\* over the game dir '
    '(wkJellyWorm.dll, wkJellyWorm.ini, jelly\\lualibs, jelly\\packages).\n'
    'Delete files in jelly\\lualibs and jelly\\packages that are not in this snapshot to get an exact copy.\n')
print(dst, len(man), 'files; dll md5', man['game\\wkJellyWorm.dll'])
