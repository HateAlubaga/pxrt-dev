"""pxdeploy: stage / apply / rollback the pxrt runtime + converted package main.lua files.

  py -3.10 pxdeploy.py stage              build out/deploy (nothing in the game dir is touched)
  py -3.10 pxdeploy.py apply              back up, then copy the staged files into the game dir (WA.exe must not run)
  py -3.10 pxdeploy.py rollback <dir>     restore a backup made by apply
  py -3.10 pxdeploy.py plan               print what stage decided

A package is converted when its ProjectX scripts transpiled, the harness ran it without a pxrt error and its main.lua has the
standard px2jelly layout. The old draft code of a converted package is skipped at load time (pxboot.claim) and its PX scripts
run through pxrt instead. Packages that do not qualify are left exactly as they are.
"""
import os, re, sys, json, shutil, time, subprocess

sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *
import pxgen

STAGE = os.path.join(DEV, 'out', 'deploy')
RES = os.path.join(DEV, 'out', 'harness_res.jsonl')
PKGDIR = os.path.join(JELLY, 'packages')
LIBDIR = os.path.join(JELLY, 'lualibs')
BACKUP_ROOT = r'C:\Users\Admin\pxrt_backup'

M1 = '-- [px2jelly] merged drafts below'
M2 = '-- [pxcompat] autowire'

# never converted: glider works as it is (user request); layout oddities found by the scan
EXCLUDE = {
    'utility_hangglider': 'glider works, keep untouched',
    'cweps': 'header registers more weapons than weapons_raw bins',
    'weapon_super_torch': 'header registers fewer weapons than weapons_raw bins',
}
# harness messages that do not matter in game (dependency on a package the harness did not load, null-weapon checks)
BENIGN = {
    'weapon_nuke_rocket': 'CheckName on a null weapon (soft missile has no launching weapon)',
    'weapon_underwater_bomb': 'CheckName on a null weapon (soft missile has no launching weapon)',
    'weapon_petrol_rocket': 'needs weapon_smart_bomb_sb (global smartb_aiming), harness loads one package',
}


def harness_status():
    rows = {}
    with open(RES, encoding='utf-8') as f:
        for l in f:
            l = l.strip()
            if not l:
                continue
            try:
                r = json.loads(l)
            except Exception:
                continue
            rows[r['pkg']] = r
    st = {}
    for p, r in rows.items():
        bad = [x for x in r.get('logs', []) if x.strip().startswith('pxrt:') and 'hooks installed' not in x]
        if r.get('crash'):
            bad.append('CRASH ' + str(r['crash'])[:120])
        st[p] = bad
    return st


def read_main(pkg):
    fp = os.path.join(PKGDIR, pkg, '0.0.1', 'main.lua')
    if not os.path.exists(fp):
        return None
    return open(fp, encoding='utf-8', errors='surrogateescape', newline='').read()


def transform(src, pkg):
    """Return the converted main.lua or (None, reason)."""
    nl = '\r\n' if '\r\n' in src else '\n'
    lines = src.split(nl)
    i2 = next((i for i, l in enumerate(lines) if l.startswith(M2)), None)
    if i2 is None:
        return None, 'no pxcompat autowire block'
    if any('pxboot' in l for l in lines):
        return None, 'already converted'
    i1 = next((i for i, l in enumerate(lines) if l.startswith(M1) and i < i2), None)
    q = '"%s"' % pkg
    out = []
    if i1 is not None:
        out += lines[:i1]
        out.append('-- [pxrt] claim: when pxrt runs this package the old draft code below is skipped (see pxboot.lua)')
        out.append('if not require("pxboot").claim(%s) then' % q)
        out += lines[i1:i2]
        out.append('end')
        out.append('')
    else:
        out += lines[:i2]
        out.append('-- [pxrt] claim (see pxboot.lua)')
        out.append('require("pxboot").claim(%s)' % q)
        out.append('')
    out.append('-- [pxrt] boot: ProjectX scripts of this package run from initialize(), after the weapons are registered')
    out.append('if require("pxboot").claimed(%s) then' % q)
    out.append('  local __pxrt_init0 = initialize')
    out.append('  function initialize()')
    out.append('    local r = 0')
    out.append('    if __pxrt_init0 then r = __pxrt_init0() end')
    out.append('    require("pxboot").boot(%s)' % q)
    out.append('    return r or 0')
    out.append('  end')
    out.append('else')
    out += lines[i2:]
    out.append('end')
    return nl.join(out) + nl, None


def lua_compiles(text):
    from lupa.lua53 import LuaRuntime
    lua = LuaRuntime(register_eval=False, encoding='utf-8')
    f = lua.eval('function(s) local f, e = load(s, "=main", "t", {}); return e end')
    return f(text)


def select_packages():
    st = harness_status()
    plan = {'convert': [], 'skip': {}}
    for pkg in sorted(st):
        why = None
        if pkg in EXCLUDE:
            why = EXCLUDE[pkg]
        elif st[pkg] and pkg not in BENIGN:
            why = 'harness: ' + st[pkg][0][:110]
        elif not os.path.exists(os.path.join(pkg_dir_lua(pkg), 'pxchunks.json')):
            why = 'no transpiled scripts'
        else:
            src = read_main(pkg)
            if src is None:
                why = 'not in the game directory'
            else:
                new, err = transform(src, pkg)
                if new is None:
                    why = err
                else:
                    e = lua_compiles(new)
                    if e:
                        why = 'transformed main.lua does not compile: %s' % e
        if why:
            plan['skip'][pkg] = why
        else:
            plan['convert'].append(pkg)
    return plan


def pkg_dir_lua(pkg):
    return os.path.join(LUA, pkg)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', errors='surrogateescape', newline='') as f:
        f.write(text)


def stage():
    if os.path.isdir(STAGE):
        shutil.rmtree(STAGE)
    sl = os.path.join(STAGE, 'lualibs')
    os.makedirs(sl)
    plan = select_packages()
    # runtime
    shutil.copyfile(os.path.join(DEV, 'pxrt_core.lua'), os.path.join(sl, 'pxrt.lua'))
    for f in sorted(os.listdir(DEV)):
        if f.startswith('pxrt_') and f.endswith('.lua') and f != 'pxrt_core.lua':
            shutil.copyfile(os.path.join(DEV, f), os.path.join(sl, f))
    shutil.copyfile(os.path.join(DEV, 'pxboot.lua'), os.path.join(sl, 'pxboot.lua'))
    pxgen.write_libs(sl)
    # launch field map (pxl_launch.lua) is produced by the generator step of the harness sync
    lf = os.path.join(pxgen.OUT_LIBS, 'pxl_launch.lua')
    if os.path.exists(lf):
        shutil.copyfile(lf, os.path.join(sl, 'pxl_launch.lua'))
    # packages
    for pkg in plan['convert']:
        write(os.path.join(sl, 'pxp_%s.lua' % pkg),
              '-- generated by pxdeploy.py: ProjectX scripts of package %s\nreturn %s\n' % (pkg, pxgen.gen_pkg_table(pkg)))
        new, _ = transform(read_main(pkg), pkg)
        write(os.path.join(STAGE, 'packages', pkg, '0.0.1', 'main.lua'), new)
    json.dump(plan, open(os.path.join(STAGE, 'plan.json'), 'w', encoding='utf-8'), indent=1)
    print('staged: %d packages converted, %d left alone -> %s' % (len(plan['convert']), len(plan['skip']), STAGE))
    return plan


def wa_running():
    try:
        out = subprocess.run(['tasklist'], capture_output=True, text=True, errors='replace').stdout.lower()
    except Exception:
        return True
    return any(l.startswith(('wa.exe', 'worms')) for l in out.splitlines())


def apply():
    if not os.path.isdir(STAGE):
        sys.exit('run stage first')
    if wa_running():
        sys.exit('WA.exe is running - close the game first')
    stamp = time.strftime('%Y%m%d_%H%M%S')
    bk = os.path.join(BACKUP_ROOT, stamp)
    os.makedirs(bk)
    created, replaced = [], []
    for dp, _, fs in os.walk(STAGE):
        for f in fs:
            if f == 'plan.json':
                continue
            src = os.path.join(dp, f)
            rel = os.path.relpath(src, STAGE)           # lualibs\x.lua | packages\pkg\0.0.1\main.lua
            dst = os.path.join(JELLY, rel)
            if os.path.exists(dst):
                b = os.path.join(bk, rel)
                os.makedirs(os.path.dirname(b), exist_ok=True)
                shutil.copy2(dst, b)
                replaced.append(rel)
            else:
                created.append(rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
    json.dump({'jelly': JELLY, 'created': created, 'replaced': replaced}, open(os.path.join(bk, 'manifest.json'), 'w'), indent=1)
    print('applied: %d replaced (backed up to %s), %d created' % (len(replaced), bk, len(created)))


def rollback(bk):
    m = json.load(open(os.path.join(bk, 'manifest.json')))
    if wa_running():
        sys.exit('WA.exe is running - close the game first')
    for rel in m['replaced']:
        shutil.copyfile(os.path.join(bk, rel), os.path.join(m['jelly'], rel))
    for rel in m['created']:
        p = os.path.join(m['jelly'], rel)
        if os.path.exists(p):
            os.remove(p)
    print('rolled back: %d restored, %d removed' % (len(m['replaced']), len(m['created'])))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'plan'
    if cmd == 'stage':
        stage()
    elif cmd == 'apply':
        apply()
    elif cmd == 'rollback':
        rollback(sys.argv[2])
    elif cmd == 'plan':
        p = select_packages()
        print(len(p['convert']), 'convert;', len(p['skip']), 'skip')
        for k, v in sorted(p['skip'].items()):
            print('  skip', k, '-', v)
