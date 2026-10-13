"""harness.py - run transpiled ProjectX packages through pxrt inside a mock WA world (lupa, Lua 5.3)."""
import os, re, sys, json, shutil, collections, time
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *
import pxgen
from lupa.lua53 import LuaRuntime

RT_FILES = ['pxrt_engine.lua', 'pxrt_e_consts.lua', 'pxrt_e_game.lua', 'pxrt_e_funcs.lua', 'pxrt_e_structs.lua',
            'pxrt_e_classes.lua', 'pxrt_e_terrain.lua', 'pxrt_e_pseudo.lua', 'pxrt_e_soft.lua', 'pxrt_e_extra.lua', 'pxrt_e_hooks.lua']


def sync_runtime():
    out = pxgen.OUT_LIBS
    os.makedirs(out, exist_ok=True)
    shutil.copyfile(os.path.join(DEV, 'pxrt_core.lua'), os.path.join(out, 'pxrt.lua'))
    for f in os.listdir(DEV):
        if f.startswith('pxrt_') and f.endswith('.lua') and f != 'pxrt_core.lua':
            shutil.copyfile(os.path.join(DEV, f), os.path.join(out, f))
    shutil.copyfile(os.path.join(DEV, 'pxboot.lua'), os.path.join(out, 'pxboot.lua'))
    pxgen.write_libs(out)
    base = os.environ.get('HARNESS_BASE')
    if base:
        import glob
        for f in glob.glob(os.path.join(base, 'pxrt*.lua')) + [os.path.join(base, 'pxboot.lua')]:
            shutil.copyfile(f, os.path.join(out, os.path.basename(f)))
    return out


def weapons_of(pkg):
    libs, chunks = pxgen.pkg_info(pkg)
    names = []
    for fname, src in chunks:
        names += re.findall(r'"CheckName", "([^"]+)"', src)
        names += re.findall(r'GetWeaponByName\("([^"]+)"', src)
    seen = []
    for n in names:
        if n not in seen:
            seen.append(n)
    return seen[:12]


def lua_str(s):
    return json.dumps(s)


def run_pkg(pkg, frames=20, weapons=None):
    out = pxgen.OUT_LIBS
    lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False, encoding='utf-8')
    g = lua.globals()
    g.DEV = DEV
    lua.execute('package.path = %s' % lua_str(out.replace('\\', '/') + '/?.lua;' + DEV.replace('\\', '/') + '/?.lua'))
    if weapons is None:
        weapons = weapons_of(pkg)
    pk = pxgen.gen_pkg_table(pkg)
    if os.environ.get('HARNESS_BOOT'):
        # same path as the game: main.lua -> pxboot.claim at load, pxboot.boot inside initialize()
        with open(os.path.join(out, 'pxp_%s.lua' % pkg), 'w', encoding='utf-8') as f:
            f.write('return ' + pk + chr(10))
    wl = '{' + ', '.join(lua_str(w) for w in weapons) + '}'
    lua.execute('SCEN = { pkg = %s, frames = %d, weapons = %s, pkgtable = %s }' % (lua_str(pkg), frames, wl, pk))
    t0 = time.time()
    try:
        logs, H = lua.execute('return dofile(%s)' % lua_str(os.path.join(DEV, 'harness', 'run.lua').replace('\\', '/')))
    except Exception as e:
        return {'pkg': pkg, 'crash': str(e)[:500], 'logs': [], 'secs': time.time() - t0}
    lst = [logs[i] for i in range(1, len(logs) + 1)]
    return {'pkg': pkg, 'logs': lst, 'secs': time.time() - t0, 'weapons': weapons}


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--json':
        r = run_pkg(sys.argv[2])
        print('@@JSON@@' + json.dumps(r))
        sys.exit(0)
    sync_runtime()
    pkgs = sys.argv[1:]
    for p in pkgs:
        r = run_pkg(p)
        print('==', p, '%.2fs' % r['secs'])
        if 'crash' in r:
            print('CRASH', r['crash'])
        for l in r['logs'][:120]:
            print('  ', l)
