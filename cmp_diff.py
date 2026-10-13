"""compare per-package trace hashes / logs of two harness_all runs (res_base.jsonl vs res_new.jsonl)"""
import json, re, sys

def load(p):
    d = {}
    for l in open(p, encoding='utf-8'):
        l = l.strip()
        if not l:
            continue
        try:
            r = json.loads(l)
        except ValueError:
            continue
        d[r['pkg']] = r
    return d

A = load(sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\Admin\pxrt_dev\out\res_base.jsonl')
B = load(sys.argv[2] if len(sys.argv) > 2 else r'C:\Users\Admin\pxrt_dev\out\res_new.jsonl')

def trace(r):
    for l in r.get('logs', []):
        m = re.match(r'H: trace events=(\d+) hash=([0-9a-f]+)', l)
        if m:
            return m.group(1), m.group(2)
    return None

def pxlogs(r):
    return sorted(l for l in r.get('logs', []) if l.startswith('pxrt:') and 'hooks installed' not in l)

same = diff = notrace = 0
diffs = []
for p in sorted(set(A) | set(B)):
    a, b = A.get(p), B.get(p)
    if not a or not b:
        diffs.append((p, 'missing in one run'))
        continue
    ta, tb = trace(a), trace(b)
    ca, cb = a.get('crash'), b.get('crash')
    if ca or cb:
        if ca != cb:
            diffs.append((p, 'crash differs: %r vs %r' % (str(ca)[:80], str(cb)[:80])))
        else:
            notrace += 1
        continue
    if ta is None or tb is None:
        notrace += 1
        continue
    if ta != tb or pxlogs(a) != pxlogs(b):
        diffs.append((p, 'trace %s vs %s%s' % (ta, tb, '' if pxlogs(a) == pxlogs(b) else '  (pxrt log lines differ)')))
        diff += 1
    else:
        same += 1
print('packages: base %d new %d | identical %d | different %d | no trace/crash %d' % (len(A), len(B), same, diff, notrace))
for p, m in diffs[:60]:
    print('  DIFF', p, m)
tot_a = sum(r.get('secs', 0) for r in A.values())
tot_b = sum(r.get('secs', 0) for r in B.values())
print('total package run seconds: base %.0f new %.0f' % (tot_a, tot_b))
