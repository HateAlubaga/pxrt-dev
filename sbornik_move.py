"""Move the PX scheme bundles (sbornik_*) out of the folders JellyWorm scans.

  py -3.10 sbornik_move.py move       jelly\\jpx\\sbornik_*  and  jelly\\packages\\jpx  ->  jelly\\sborniki\\
  py -3.10 sbornik_move.py restore    put everything back (from sborniki\\moved.json)
  py -3.10 sbornik_move.py list

jelly\\jpx is scanned by the host at startup (/jpx list, /enable sbornik_*), so after `move` the host sees no bundles.
packages\\jpx is a tracked duplicate inside the packages git repo; the host never reads it (ScanAllPackages=0) but it
clutters the package folder, so it is moved too.
"""
import os, sys, json, shutil, subprocess

JELLY = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly'
DST = os.path.join(JELLY, 'sborniki')
LOG = os.path.join(DST, 'moved.json')
SRC_JPX = os.path.join(JELLY, 'jpx')
SRC_PKG_JPX = os.path.join(JELLY, 'packages', 'jpx')
DST_JPX = os.path.join(DST, 'jpx')
DST_PKG_JPX = os.path.join(DST, 'packages_jpx')


def wa_running():
    out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq WA.exe'], capture_output=True, text=True, errors='replace').stdout
    return 'WA.exe' in out


def load():
    if os.path.isfile(LOG):
        return json.load(open(LOG, encoding='utf-8'))
    return {'jpx': [], 'packages_jpx': False}


def save(d):
    os.makedirs(DST, exist_ok=True)
    json.dump(d, open(LOG, 'w', encoding='utf-8'), indent=1)


def move():
    if wa_running():
        sys.exit('WA.exe is running - close the game first')
    d = load()
    os.makedirs(DST_JPX, exist_ok=True)
    for n in sorted(os.listdir(SRC_JPX)):
        if n.startswith('sbornik_') and os.path.isdir(os.path.join(SRC_JPX, n)):
            tgt = os.path.join(DST_JPX, n)
            if os.path.exists(tgt):
                sys.exit('target exists: ' + tgt)
            shutil.move(os.path.join(SRC_JPX, n), tgt)
            d['jpx'].append(n)
    if os.path.isdir(SRC_PKG_JPX) and not d['packages_jpx']:
        if os.path.exists(DST_PKG_JPX):
            sys.exit('target exists: ' + DST_PKG_JPX)
        shutil.move(SRC_PKG_JPX, DST_PKG_JPX)
        d['packages_jpx'] = True
    save(d)
    print('moved %d bundles from jpx, packages\\jpx moved: %s' % (len(d['jpx']), d['packages_jpx']))


def restore():
    if wa_running():
        sys.exit('WA.exe is running - close the game first')
    d = load()
    for n in d['jpx']:
        shutil.move(os.path.join(DST_JPX, n), os.path.join(SRC_JPX, n))
    if d['packages_jpx']:
        shutil.move(DST_PKG_JPX, SRC_PKG_JPX)
    save({'jpx': [], 'packages_jpx': False})
    print('restored')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'list'
    if cmd == 'move':
        move()
    elif cmd == 'restore':
        restore()
    else:
        d = load()
        print('jpx bundles moved: %d, packages\\jpx moved: %s' % (len(d['jpx']), d['packages_jpx']))
        print('still in jpx: %d' % len([n for n in os.listdir(SRC_JPX) if n.startswith('sbornik_')]))
