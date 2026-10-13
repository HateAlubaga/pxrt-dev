"""Switch wkJellyWorm.ini [autostart] to the packages of one ProjectX scheme bundle (sbornik_*).

  py -3.10 pxsbornik.py list               bundles with package counts and what is missing
  py -3.10 pxsbornik.py show <name>        packages of one bundle
  py -3.10 pxsbornik.py on <name>          enable exactly that bundle's packages, disable the rest
  py -3.10 pxsbornik.py off                restore the [autostart] set saved by the first `on`
  py -3.10 pxsbornik.py prep               for the in-game /sb: restore every bundle's quarantined packages and
                                           write all missing pxp_/pxl_ runtime files

<name> may be a unique part of the bundle name ("spec5", "fortress_4", "kaos_0rang3_2"). Words are matched in order.
`on` refuses while WA.exe runs, backs the ini up next to itself (wkJellyWorm.ini.sbornik_<stamp>) and writes any
missing pxp_<package>.lua / pxl_<lib>.lua runtime files for ProjectX packages. The WA scheme (.wsc) and maps are not
part of the bundles: pick a fitting scheme in the lobby yourself.
"""
import os, re, sys, json, time, shutil, subprocess
DEV = r'C:\Users\Admin\pxrt_dev'
sys.path.insert(0, DEV)
import pxgen
GAME = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon'
INI = os.path.join(GAME, 'wkJellyWorm.ini')
JELLY = os.path.join(GAME, 'jelly')
PKGS = os.path.join(JELLY, 'packages')
LL = os.path.join(JELLY, 'lualibs')
BUNDLES = os.path.join(JELLY, 'sborniki', 'jpx')
SAVED = os.path.join(JELLY, 'sborniki', 'autostart_saved.json')
ALWAYS = {'zz_probe'}   # keys left as they are


def bundles():
    out = {}
    for b in sorted(os.listdir(BUNDLES)):
        d = os.path.join(BUNDLES, b)
        for ver in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            m = os.path.join(d, ver, 'manifest.json')
            if os.path.isfile(m):
                j = json.load(open(m, encoding='utf-8-sig'))
                out[b] = (j.get('description', ''), j.get('dependencies', []))
    return out


def find(name, bs):
    if name in bs:
        return name
    words = [w for w in re.split(r'[\s_]+', name.lower()) if w]
    hits = [b for b in bs if re.search('.*'.join(map(re.escape, words)), b.lower())]
    if len(hits) == 1:
        return hits[0]
    sys.exit('no bundle matches %r' % name if not hits else '%r matches several: %s' % (name, ', '.join(hits)))


def deps_closure(pkgs):
    """packages plus their own manifest dependencies"""
    seen, todo = [], list(pkgs)
    while todo:
        p = todo.pop(0)
        if p in seen:
            continue
        seen.append(p)
        d = os.path.join(PKGS, p)
        if os.path.isdir(d):
            for ver in os.listdir(d):
                m = os.path.join(d, ver, 'manifest.json')
                if os.path.isfile(m):
                    try:
                        todo += json.load(open(m, encoding='utf-8-sig')).get('dependencies', [])
                    except Exception:
                        pass
    return seen


def is_px(p):
    return os.path.isdir(pxgen.pkg_dir(p))


def libs_of(p, acc):
    try:
        libs, _ = pxgen.pkg_info(p)
    except Exception:
        return acc
    for l in libs:
        lib_closure(l, acc)
    return acc


def lib_closure(l, acc):
    if l in acc:
        return
    acc.add(l)
    try:
        sub, _ = pxgen.read_chunks(pxgen.lib_dir(l))
    except Exception:
        return
    for s in sub:
        lib_closure(s, acc)


def plan(b, bs):
    pk = deps_closure(bs[b][1])
    missing_pkg = [p for p in pk if not os.path.isdir(os.path.join(PKGS, p))]
    need_pxp, need_pxl = [], set()
    for p in pk:
        if p not in missing_pkg and is_px(p):
            if not os.path.isfile(os.path.join(LL, 'pxp_%s.lua' % p)):
                need_pxp.append(p)
            libs_of(p, need_pxl)
    need_pxl = sorted(l for l in need_pxl if not os.path.isfile(os.path.join(LL, 'pxl_%s.lua' % l)))
    return pk, missing_pkg, need_pxp, need_pxl


def read_ini():
    return open(INI, encoding='latin-1').read()


def autostart_span(s):
    a = re.search(r'^\[autostart\]', s, re.M).start()
    m = re.search(r'^\[', s[a + 1:], re.M)
    return a, (a + 1 + m.start()) if m else len(s)


def current_set(s):
    a, e = autostart_span(s)
    return {k: v for k, v in re.findall(r'^([^;\s=][^=\r\n]*)=(\S*)', s[a:e], re.M)}


def write_set(s, values):
    a, e = autostart_span(s)
    sec = s[a:e]
    keys = set(current_set(s))

    def sub(m):
        k = m.group(1)
        return '%s=%s' % (k, values[k]) if k in values else m.group(0)
    sec = re.sub(r'^([^;\s=][^=\r\n]*)=(\S*)', sub, sec, flags=re.M)
    extra = [k for k in values if k not in keys]
    if extra:
        sec = sec.rstrip('\r\n') + '\n' + ''.join('%s=%s\n' % (k, values[k]) for k in extra) + '\n'
    return s[:a] + sec + s[e:]


def wa_running():
    out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    return any(l.startswith(('wa.exe', 'worms')) for l in out.splitlines())


def backup_ini():
    dst = INI + '.sbornik_' + time.strftime('%Y%m%d_%H%M%S')
    shutil.copy2(INI, dst)
    return dst


def cmd_list(bs):
    for b, (desc, deps) in bs.items():
        pk, mp, xp, xl = plan(b, bs)
        dis = [p for p in mp if os.path.isdir(os.path.join(JELLY, 'packages_disabled', p))]
        mp = [p for p in mp if p not in dis]
        miss = (('  quarantined (on restores): ' + ', '.join(dis)) if dis else '') + \
            (('  NO PACKAGE: ' + ', '.join(mp)) if mp else '')
        gen = ('  (+%d runtime files)' % (len(xp) + len(xl))) if xp or xl else ''
        print('%-52s %3d pkgs%s%s' % (b, len(pk), gen, miss))


def cmd_on(name, bs):
    if wa_running():
        sys.exit('WA is running: close it first')
    b = find(name, bs)
    pk, mp, xp, xl = plan(b, bs)
    # packages the harness once quarantined (jelly\packages_disabled) come back when a bundle needs them
    back = [p for p in mp if os.path.isdir(os.path.join(JELLY, 'packages_disabled', p))]
    if back:
        subprocess.run([sys.executable, os.path.join(DEV, 'pxquarantine.py'), 'restore'] + back, check=True)
        print('restored from packages_disabled: ' + ', '.join(back))
        pk, mp, xp, xl = plan(b, bs)
    s = read_ini()
    cur = current_set(s)
    if not os.path.isfile(SAVED):
        json.dump(cur, open(SAVED, 'w', encoding='utf-8'), indent=0)
    want = {k: ('0' if k not in ALWAYS else v) for k, v in cur.items()}
    for p in pk:
        if p not in mp:
            want[p] = '1'
    bk = backup_ini()
    open(INI, 'w', encoding='latin-1', newline='').write(write_set(s, want))
    for p in xp:
        src = '-- generated by pxsbornik.py: ProjectX scripts of package %s\nreturn %s\n' % (p, pxgen.gen_pkg_table(p))
        open(os.path.join(LL, 'pxp_%s.lua' % p), 'w', encoding='utf-8', newline='\n').write(src)
    for l in xl:
        open(os.path.join(LL, 'pxl_%s.lua' % l), 'w', encoding='utf-8', newline='\n').write(pxgen.gen_lib(l))
    print('%s: %s' % (b, bs[b][0]))
    print('enabled %d packages, everything else in [autostart] off; ini backup %s' % (len(pk) - len(mp), bk))
    if xp or xl:
        print('wrote runtime files: %s' % ', '.join(['pxp_' + p for p in xp] + ['pxl_' + l for l in xl]))
    if mp:
        print('not installed, skipped: ' + ', '.join(mp))
    print('restore your old set: py -3.10 pxsbornik.py off')


def cmd_prep(bs):
    """for the in-game /sb command: every bundle's quarantined packages back, missing runtime files written"""
    if wa_running():
        sys.exit('WA is running: close it first')
    back = set()
    for b in bs:
        _, mp, _, _ = plan(b, bs)
        back |= {p for p in mp if os.path.isdir(os.path.join(JELLY, 'packages_disabled', p))}
    if back:
        subprocess.run([sys.executable, os.path.join(DEV, 'pxquarantine.py'), 'restore'] + sorted(back), check=True)
    xp_all, xl_all, missing = set(), set(), set()
    for b in bs:
        _, mp, xp, xl = plan(b, bs)
        xp_all |= set(xp)
        xl_all |= set(xl)
        missing |= set(mp)
    for p in sorted(xp_all):
        src = '-- generated by pxsbornik.py: ProjectX scripts of package %s\nreturn %s\n' % (p, pxgen.gen_pkg_table(p))
        open(os.path.join(LL, 'pxp_%s.lua' % p), 'w', encoding='utf-8', newline='\n').write(src)
    for l in sorted(xl_all):
        open(os.path.join(LL, 'pxl_%s.lua' % l), 'w', encoding='utf-8', newline='\n').write(pxgen.gen_lib(l))
    print('restored: %s' % (', '.join(sorted(back)) or '-'))
    print('wrote: %s' % (', '.join(['pxp_' + p for p in sorted(xp_all)] + ['pxl_' + l for l in sorted(xl_all)]) or '-'))
    print('not installed anywhere (%d): %s' % (len(missing), ', '.join(sorted(missing))))


def cmd_off():
    if wa_running():
        sys.exit('WA is running: close it first')
    if not os.path.isfile(SAVED):
        sys.exit('nothing saved: `on` was not used')
    saved = json.load(open(SAVED, encoding='utf-8'))
    s = read_ini()
    cur = current_set(s)
    want = {k: saved.get(k, '0') for k in cur}
    bk = backup_ini()
    open(INI, 'w', encoding='latin-1', newline='').write(write_set(s, want))
    os.remove(SAVED)
    print('restored %d enabled packages; ini backup %s' % (sum(1 for v in want.values() if v != '0'), bk))


def main():
    a = sys.argv[1:]
    bs = bundles()
    if not a or a[0] == 'list':
        cmd_list(bs)
    elif a[0] == 'show' and len(a) > 1:
        b = find(' '.join(a[1:]), bs)
        pk, mp, xp, xl = plan(b, bs)
        print('%s: %s' % (b, bs[b][0]))
        for p in pk:
            print('  %s%s' % (p, '  (not installed)' if p in mp else ''))
    elif a[0] == 'on' and len(a) > 1:
        cmd_on(' '.join(a[1:]), bs)
    elif a[0] == 'off':
        cmd_off()
    elif a[0] == 'prep':
        cmd_prep(bs)
    else:
        print(__doc__)


main()
