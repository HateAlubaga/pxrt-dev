"""pxgen: build lualib modules (pxl_<lib>.lua) and per-package pxrt loader blocks from testout/lua."""
import os, json, sys, re
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *

OUT = os.path.join(DEV, 'out')
OUT_LIBS = os.path.join(OUT, 'lualibs')


def long_str(s):
    n = 0
    while (']' + '=' * n + ']') in s or s.endswith(']' + '=' * n):
        n += 1
    eq = '=' * n
    # a leading newline is skipped by Lua, so add one to keep first line intact
    return '[' + eq + '[\n' + s + ']' + eq + ']'


def fix_shadowed(src):
    """A PX class may have a field and a method of the same name (AF_Shield, GravityFactor). Lua `obj:name()` would
    find the field first, so route those calls through mc()."""
    meth = set(re.findall(r'__P__:(?:method|override)\("\w+", "(\w+)"', src))
    if not meth:
        return src
    fields = set(re.findall(r'\b\w+\.(\w+)\s*=[^=]', src))
    for n in sorted(meth & fields):
        src = re.sub(r'\b([A-Za-z_][\w\.]*):' + n + r'\(\s*\)', r'mc(\1, "' + n + '")', src)
        src = re.sub(r'\b([A-Za-z_][\w\.]*):' + n + r'\(', r'mc(\1, "' + n + '", ', src)
    return src


def tag_overloads(src):
    """Same-named P:func / P:method definitions are PX overloads; give each a signature (i/f/s per parameter) so the
    runtime can pick by argument types when the arity is the same."""
    head = re.compile(r'^__P__:(func|method)\((?:"(\w+)", )?"(\w+)", function\(([^)]*)\)[ \t]*$', re.M)
    ms = list(head.finditer(src))
    seen = {}
    for m in ms:
        k = (m.group(1), m.group(2), m.group(3))
        seen[k] = seen.get(k, 0) + 1
    out, last = [], 0
    for m in ms:
        key = (m.group(1), m.group(2), m.group(3))
        if seen[key] < 2:
            continue
        params = [p.strip() for p in m.group(4).split(',') if p.strip()]
        if m.group(1) == 'method':
            params = params[2:]
        body = src[m.end():m.end() + 600]
        sig = ''
        for p in params:
            if re.search(r'^\s*' + re.escape(p) + r' = ti\(' + re.escape(p) + r'\)', body, re.M):
                sig += 'i'
            elif re.search(r'^\s*' + re.escape(p) + r' = tf\(' + re.escape(p) + r'\)', body, re.M):
                sig += 'f'
            else:
                sig += 's'
        out.append(src[last:m.start()])
        out.append('__P__:sig("%s")\n' % sig)
        last = m.start()
    out.append(src[last:])
    return ''.join(out)


_GV_ALL = None


def _all_gvars():
    """name -> set of lua files that declare it with __P__:gvars (whole transpiled tree, built once)."""
    global _GV_ALL
    if _GV_ALL is None:
        _GV_ALL = {}
        for dp, _, fs in os.walk(LUA):
            for f in fs:
                if not f.endswith('.lua'):
                    continue
                p = os.path.join(dp, f)
                s = open(p, encoding='utf-8', errors='replace').read()
                for m in re.finditer(r'__P__:gvars\(\{([^}]*)\}\)', s):
                    for n in re.findall(r'"(\w+)"', m.group(1)):
                        _GV_ALL.setdefault(n, set()).add(p)
    return _GV_ALL


_ENGINE_FIELDS = None


def _engine_fields():
    """field names of the engine classes (FIELDS tables in pxrt_engine.lua)."""
    global _ENGINE_FIELDS
    if _ENGINE_FIELDS is None:
        eng = open(os.path.join(DEV, 'pxrt_engine.lua'), encoding='utf-8').read()
        _ENGINE_FIELDS = set()
        for m in re.finditer(r'FIELDS\.\w+\s*=\s*\{(.*?)\n\}', eng, re.S):
            _ENGINE_FIELDS |= set(re.findall(r'(\w+)\s*=\s*\{\s*0x', m.group(1)))
    return _ENGINE_FIELDS


def fix_xglobals(src, fp):
    """`self.name` where name is a global declared in ANOTHER package and never assigned as a field here: PX resolved
    it to that global, the transpiler could not and emitted a member access. Engine fields are left alone
    (scheme_painter reads CTurnGame::Timer while scheme_dodge declares a global Timer)."""
    gv = _all_gvars()
    eng = _engine_fields()
    for n in sorted(set(re.findall(r'\bself\.(\w+)', src))):
        owners = gv.get(n)
        if not owners or fp in owners or n in eng:
            continue
        if re.search(r'\.' + n + r'\s*=[^=]', src):
            continue
        src = re.sub(r'\bself\.' + n + r'\b', '__G__.' + n, src)
    return src


def read_chunks(d):
    pj = os.path.join(d, 'pxchunks.json')
    if not os.path.exists(pj):
        return [], []
    cj = json.load(open(pj, encoding='utf-8'))
    out = []
    for c in cj['chunks']:
        fp = os.path.join(d, c)
        if os.path.exists(fp):
            out.append((c, tag_overloads(fix_xglobals(fix_shadowed(open(fp, encoding='utf-8', errors='replace').read()), fp))))
    return cj.get('libs', []), out


def lib_dir(name):
    d = os.path.join(LUA, '@lib', name)
    if os.path.isdir(d):
        return d
    return os.path.join(LUA, name)     # a package required as a lib


def pkg_dir(name):
    return os.path.join(LUA, name)


def render_chunks(chunks):
    parts = []
    for fname, src in chunks:
        parts.append('  { %s, %s },' % (json.dumps(fname), long_str(src)))
    return '\n'.join(parts)


def gen_lib(name):
    libs, chunks = read_chunks(lib_dir(name))
    return ('-- generated by pxgen.py (do not edit): ProjectX library %s\n'
            'return {\n requires = {%s},\n chunks = {\n%s\n }\n}\n') % (
        name, ', '.join(json.dumps(l) for l in libs), render_chunks(chunks))


def all_libs():
    root = os.path.join(LUA, '@lib')
    names = set(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    # packages that other units require() as libraries
    for r in (LUA, root):
        for d in os.listdir(r):
            pj = os.path.join(r, d, 'pxchunks.json')
            if os.path.exists(pj):
                for l in json.load(open(pj, encoding='utf-8')).get('libs', []):
                    if l not in names and os.path.isdir(os.path.join(LUA, l)):
                        names.add(l)
    return sorted(names)


def pkg_info(name):
    libs, chunks = read_chunks(pkg_dir(name))
    return libs, chunks


def gen_pkg_table(name):
    libs, chunks = pkg_info(name)
    return ('{ libs = {%s}, chunks = {\n%s\n} }') % (', '.join(json.dumps(l) for l in libs), render_chunks(chunks))


def write_libs(outdir=OUT_LIBS):
    os.makedirs(outdir, exist_ok=True)
    for l in all_libs():
        with open(os.path.join(outdir, 'pxl_%s.lua' % l), 'w', encoding='utf-8', newline='\n') as f:
            f.write(gen_lib(l))
    return outdir


if __name__ == '__main__':
    d = write_libs()
    print('wrote libs to', d, len(all_libs()))
