"""bench.py - load the user's enabled packages together in the mock world and report per-frame Lua cost.

  py -3.10 bench.py [--worms 4] [--frames 60] [--extra 20] pkg1 pkg2 ...      (no pkgs = the set from jelly\\pxboot.log)
"""
import os, re, sys
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev\harness')
from paths import *
import pxgen, harness
from lupa.lua53 import LuaRuntime


def enabled_set():
    p = os.path.join(JELLY, 'pxboot.log')
    names = []
    for l in open(p, encoding='utf-8', errors='replace'):
        m = re.match(r'(\w+): claimed', l)
        if m:
            names.append(m.group(1))
    return names


def main():
    args = sys.argv[1:]
    worms, frames, extra, callprof, incl, warm = 4, 60, 0, False, False, 40
    msgs = '2'
    trace = ''
    base = ''
    pkgs = []
    i = 0
    while i < len(args):
        if args[i] == '--worms':
            worms = int(args[i + 1]); i += 2
        elif args[i] == '--frames':
            frames = int(args[i + 1]); i += 2
        elif args[i] == '--msgs':
            msgs = args[i + 1]; i += 2
        elif args[i] == '--warm':
            warm = int(args[i + 1]); i += 2
        elif args[i] == '--trace':
            trace = args[i + 1]; i += 2
        elif args[i] == '--base':
            base = args[i + 1]; i += 2
        elif args[i] == '--incl':
            incl = True; i += 1
        elif args[i] == '--callprof':
            callprof = True; i += 1
        elif args[i] == '--extra':
            extra = int(args[i + 1]); i += 2
        else:
            pkgs.append(args[i]); i += 1
    if not pkgs:
        pkgs = enabled_set()
    out = pxgen.OUT_LIBS if os.environ.get('BENCH_NOSYNC') else harness.sync_runtime()
    if base:
        import glob, shutil
        for f in glob.glob(os.path.join(base, 'pxrt*.lua')) + [os.path.join(base, 'pxboot.lua')]:
            shutil.copyfile(f, os.path.join(out, os.path.basename(f)))
    for p in pkgs:
        with open(os.path.join(out, 'pxp_%s.lua' % p), 'w', encoding='utf-8') as f:
            f.write('return ' + pxgen.gen_pkg_table(p) + chr(10))
    lua = LuaRuntime(unpack_returned_tuples=True, register_eval=False, encoding='utf-8')
    g = lua.globals()
    g.DEV = DEV
    lua.execute('package.path = %s' % harness.lua_str(out.replace(chr(92), '/') + '/?.lua;' + DEV.replace(chr(92), '/') + '/?.lua'))
    lua.execute('SCEN = { pkgs = {%s}, frames = %d, worms = %d, extra = %d, callprof = %s, incl = %s, warm = %d, msgs = {%s} }' % (
        ','.join(harness.lua_str(p) for p in pkgs), frames, worms, extra, 'true' if callprof else 'false',
        'true' if incl else 'false', warm, msgs))
    if os.environ.get('NOHOOK'):
        lua.execute('SCEN.nohook = true')
    if os.environ.get('HOSTSITE'):
        lua.execute('SCEN.hostsite = true')
    if trace:
        lua.execute('SCEN.trace = %s' % harness.lua_str(trace.replace(chr(92), '/')))
    rep = lua.execute('return dofile(%s)' % harness.lua_str(os.path.join(DEV, 'harness', 'bench.lua').replace(chr(92), '/')))
    for i in range(1, len(rep) + 1):
        print(rep[i])


if __name__ == '__main__':
    main()
