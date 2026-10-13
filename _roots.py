import os, re, collections, json
base = r'C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua'
cls = {}      # name -> (base, pkg)
for root, dirs, files in os.walk(base):
    for f in files:
        if not f.endswith('.lua'):
            continue
        pkg = os.path.relpath(root, base).split(os.sep)[0]
        s = open(os.path.join(root, f), encoding='utf-8').read()
        for m in re.finditer(r'__P__:class\("(\w+)",\s*"(\w+)"\)', s):
            cls.setdefault(m.group(1), (m.group(2), pkg))
ENGINE = None
def root(n, seen=()):
    b = cls.get(n)
    if not b or n in seen:
        return n
    return root(b[0], seen + (n,))
cnt = collections.Counter()
pk = collections.defaultdict(set)
for n, (b, pkg) in cls.items():
    r = root(n)
    cnt[r] += 1
    pk[r].add(pkg)
for r, c in cnt.most_common():
    print(r, c, 'pkgs=%d' % len(pk[r]))
json.dump({r: sorted(p) for r, p in pk.items()}, open(r'C:\Users\Admin\pxrt_dev\out_roots.json', 'w'))
