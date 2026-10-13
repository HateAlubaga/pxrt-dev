"""pxquarantine: move packages out of jelly\packages so wkJellyWorm does not see them, and move them back.

  py -3.10 pxquarantine.py dirty        move the packages the harness flagged (harness_status) to jelly\packages_disabled
  py -3.10 pxquarantine.py move a b c   move the named packages
  py -3.10 pxquarantine.py restore [a b c]   move named packages (default: all) back into jelly\packages
  py -3.10 pxquarantine.py list         show what is in jelly\packages_disabled

The host scans only jelly\packages (config: jelly\packages_*) so a sibling folder is invisible to it. wkJellyWorm.ini is not touched:
an [autostart] line for a moved package only makes the host log "Package X not found" and go on.
"""
import os, sys, json, shutil, subprocess

sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *

SRC = os.path.join(JELLY, 'packages')
DST = os.path.join(JELLY, 'packages_disabled')
LOG = os.path.join(DST, 'moved.json')


def wa_running():
    try:
        out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    except Exception:
        return True
    return any(l.startswith(('wa.exe', 'worms')) for l in out.splitlines())


def load_log():
    if os.path.exists(LOG):
        return json.load(open(LOG, encoding='utf-8'))
    return {}


def save_log(d):
    json.dump(d, open(LOG, 'w', encoding='utf-8'), indent=1, sort_keys=True)


def move(names):
    if wa_running():
        sys.exit('WA.exe is running - close the game first')
    os.makedirs(DST, exist_ok=True)
    log = load_log()
    done = 0
    for n in names:
        s, d = os.path.join(SRC, n), os.path.join(DST, n)
        if not os.path.isdir(s):
            print('skip (not in packages):', n)
            continue
        if os.path.exists(d):
            print('skip (target exists):', n)
            continue
        shutil.move(s, d)
        log[n] = 'moved'
        done += 1
    save_log(log)
    print('moved %d -> %s' % (done, DST))


def restore(names):
    if wa_running():
        sys.exit('WA.exe is running - close the game first')
    log = load_log()
    names = names or sorted(log)
    done = 0
    for n in names:
        s, d = os.path.join(DST, n), os.path.join(SRC, n)
        if not os.path.isdir(s):
            print('skip (not in packages_disabled):', n)
            continue
        if os.path.exists(d):
            print('skip (already in packages):', n)
            continue
        shutil.move(s, d)
        log.pop(n, None)
        done += 1
    save_log(log)
    print('restored %d -> %s' % (done, SRC))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if cmd == 'dirty':
        import pxdeploy
        st = pxdeploy.harness_status()
        move(sorted(k for k, v in st.items() if v))
    elif cmd == 'move':
        move(sys.argv[2:])
    elif cmd == 'restore':
        restore(sys.argv[2:])
    else:
        print(sorted(os.listdir(DST)) if os.path.isdir(DST) else 'nothing moved yet')
