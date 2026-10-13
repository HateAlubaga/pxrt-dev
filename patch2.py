p = r'C:\Users\Admin\pxrt_dev\pxgen.py'
s = open(p, encoding='utf-8').read()
s = s.replace("""def lib_dir(name):
    return os.path.join(LUA, '@lib', name)
""", """def lib_dir(name):
    d = os.path.join(LUA, '@lib', name)
    if os.path.isdir(d):
        return d
    return os.path.join(LUA, name)     # a package required as a lib
""")
s = s.replace("""def all_libs():
    root = os.path.join(LUA, '@lib')
    return sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
""", """def all_libs():
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
""")
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
