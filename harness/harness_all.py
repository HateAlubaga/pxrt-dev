"""run every package through the harness (one subprocess each, hard timeout), aggregate issues
-> out/harness_res.jsonl (incremental) + printed summary"""
import os, re, sys, json, collections, subprocess, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev\harness')
from paths import *
import harness

TIMEOUT = int(os.environ.get('PKG_TIMEOUT', '45'))
OUTJ = os.environ.get('HARNESS_OUT') or os.path.join(DEV, 'out', 'harness_res.jsonl')


def work(p):
    t0 = time.time()
    try:
        cp = subprocess.run([sys.executable, os.path.join(DEV, 'harness', 'harness.py'), '--json', p],
                            capture_output=True, timeout=TIMEOUT, text=True, encoding='utf-8', errors='replace')
        line = [l for l in cp.stdout.splitlines() if l.startswith('@@JSON@@')]
        if line:
            r = json.loads(line[-1][8:])
        else:
            r = {'pkg': p, 'crash': 'no output: ' + (cp.stderr or '')[-300:], 'logs': []}
    except subprocess.TimeoutExpired:
        r = {'pkg': p, 'crash': 'HARD TIMEOUT %ds' % TIMEOUT, 'logs': []}
    except Exception as e:
        r = {'pkg': p, 'crash': 'py: ' + str(e)[:300], 'logs': []}
    r['secs'] = time.time() - t0
    with open(OUTJ, 'a', encoding='utf-8') as f:
        f.write(json.dumps(r) + '\n')
    return r


def norm(l):
    l = re.sub(r'0x[0-9A-Fa-f]+', '0xN', l)
    l = re.sub(r'@[0-9A-F]+', '@N', l)
    l = re.sub(r'\b\d+\b', 'N', l)
    return l[:200]


def summarize(res, top):
    agg = collections.defaultdict(set)
    crashes = []
    for r in res:
        if 'crash' in r:
            crashes.append((r['pkg'], r['crash']))
        for l in r['logs']:
            if l.startswith('H: fire') or l.startswith('H: trace') or l.startswith('H: calls') or l.startswith('H: origCalls') or 'hooks installed' in l:
                continue
            agg[norm(l)].add(r['pkg'])
    print('packages', len(res), 'crashes', len(crashes))
    cc = collections.Counter(re.sub(r'\d+', 'N', c)[:90] for _, c in crashes)
    for k, v in cc.most_common(8):
        print('CRASHKIND %4d %s' % (v, k))
    rows = sorted(agg.items(), key=lambda kv: -len(kv[1]))
    for k, v in rows[:top]:
        print('%4d  %s   e.g. %s' % (len(v), k, sorted(v)[:2]))
    print('distinct issues', len(rows))


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--summary':
        res = []
        for l in open(OUTJ, encoding='utf-8'):
            l = l.strip()
            if not l:
                continue
            try:
                res.append(json.loads(l))
            except ValueError:
                print('skipped bad line', l[:80])
        summarize(res, int(os.environ.get('TOP', '70')))
        sys.exit(0)
    harness.sync_runtime()
    pkgs = sorted(d for d in os.listdir(LUA) if d != '@lib' and os.path.isdir(os.path.join(LUA, d)))
    if len(sys.argv) > 1:
        pkgs = [p for p in pkgs if any(a in p for a in sys.argv[1:])]
    if os.path.exists(OUTJ):
        os.remove(OUTJ)
    done = 0
    res = []
    with ThreadPoolExecutor(6) as ex:
        for r in ex.map(work, pkgs):
            res.append(r)
            done += 1
            if done % 25 == 0:
                print('progress', done, '/', len(pkgs), flush=True)
    summarize(res, int(os.environ.get('TOP', '70')))
