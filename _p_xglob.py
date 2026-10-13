D = r'C:\Users\Admin\pxrt_dev'


def patch(path, old, new, count=1):
    s = open(path, encoding='utf-8', newline='').read()
    assert s.count(old) == count, (path, old[:60], s.count(old))
    s = s.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='').write(s)


CODE = '''_GV_ALL = None


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
                for m in re.finditer(r'__P__:gvars\\(\\{([^}]*)\\}\\)', s):
                    for n in re.findall(r'"(\\w+)"', m.group(1)):
                        _GV_ALL.setdefault(n, set()).add(p)
    return _GV_ALL


def fix_xglobals(src, fp):
    """`self.name` where name is a global declared in ANOTHER package and never assigned as a field here: PX resolved
    it to that global, the transpiler could not and emitted a member access."""
    gv = _all_gvars()
    for n in sorted(set(re.findall(r'\\bself\\.(\\w+)', src))):
        owners = gv.get(n)
        if not owners or fp in owners:
            continue
        if re.search(r'\\.' + n + r'\\s*=[^=]', src):
            continue
        src = re.sub(r'\\bself\\.' + n + r'\\b', '__G__.' + n, src)
    return src


def read_chunks(d):'''

patch(D + r'\pxgen.py', "def read_chunks(d):", CODE)
patch(D + r'\pxgen.py',
      "tag_overloads(fix_shadowed(open(fp, encoding='utf-8', errors='replace').read()))",
      "tag_overloads(fix_xglobals(fix_shadowed(open(fp, encoding='utf-8', errors='replace').read()), fp))")
print('ok')
