"""Scan `override X::Message` bodies of the enabled packages (+ their libs): what runs BEFORE the first top-level `if`."""
import os, re, sys, json, collections
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
from paths import *
import pxgen

PKGS = sys.argv[1:]
out = collections.OrderedDict()
for pkg in PKGS:
    libs, chunks = pxgen.pkg_info(pkg)
    srcs = list(chunks)
    # libs: pxgen.pkg_info returns lib names; read their chunks too
    for l in libs:
        try:
            _, lc = pxgen.pkg_info(l)
        except Exception:
            lc = []
        srcs += lc
    for fname, src in srcs:
        lines = src.split(chr(10))
        i = 0
        while i < len(lines):
            m = re.match(r'__P__:override\("(\w+)", "Message", function\(self, super, sender, (\w+), (\w+), (\w+)\)', lines[i])
            if not m:
                i += 1
                continue
            cls = m.group(1)
            j = i + 1
            body = []
            while j < len(lines) and not lines[j].startswith('end)'):
                body.append(lines[j])
                j += 1
            top = [b for b in body if b.startswith('  ') and not b.startswith('   ')]
            prefix = []
            for b in top:
                s = b.strip()
                if s.startswith('if ') or s.startswith('while ') or s.startswith('for '):
                    break
                if re.match(r'(\w+) = ti\(\1\)$', s):
                    continue
                prefix.append(s)
            key = '%s::%s (%s)' % (cls, 'Message', fname)
            out.setdefault(pkg, []).append((key, len(body), prefix))
            i = j
for pkg, lst in out.items():
    print('==', pkg)
    for key, n, prefix in lst:
        print('  %-60s body=%3d prefix=%d' % (key[:60], n, len(prefix)))
        for p in prefix[:6]:
            print('       ', p[:110])
