"""bench_all.py - per-package Lua cost (VM instructions / host calls per frame) for every package, one subprocess each.

  py -3.10 bench_all.py [--msgs 1,2,3,4,5] [--worms 4] [--frames 30] [name-filter ...]  ->  out/bench_all.jsonl + sorted table
Needs HARNESS_BOOT=1 (same path as the game). One sync_runtime up front, children skip it (BENCH_NOSYNC=1).
"""
import os, re, sys, json, subprocess, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev')
sys.path.insert(0, r'C:\Users\Admin\pxrt_dev\harness')
from paths import *
import harness

OUTJ = os.environ.get('BENCH_OUT') or os.path.join(DEV, 'out', 'bench_all.jsonl')
TIMEOUT = int(os.environ.get('PKG_TIMEOUT', '120'))


def work(args):
    pkg, extra = args
    env = dict(os.environ, HARNESS_BOOT='1', BENCH_NOSYNC='1')
    t0 = time.time()
    try:
        cp = subprocess.run([sys.executable, os.path.join(DEV, 'harness', 'bench.py')] + extra + [pkg],
                            capture_output=True, timeout=TIMEOUT, text=True, encoding='utf-8', errors='replace', env=env)
        txt = cp.stdout
        m = re.search(r'VM instructions per frame: (\d+)', txt)
        h = re.search(r'host API calls per frame: (\d+)', txt)
        errs = [l for l in txt.splitlines() if l.startswith('LOG pxrt:') and ('fail' in l or 'error' in l)]
        r = {'pkg': pkg, 'instr': int(m.group(1)) if m else None, 'host': int(h.group(1)) if h else None,
             'errs': errs[:3], 'err': None if m else (txt[-300:] + cp.stderr[-300:])}
    except subprocess.TimeoutExpired:
        r = {'pkg': pkg, 'instr': None, 'host': None, 'err': 'TIMEOUT'}
    r['secs'] = round(time.time() - t0, 1)
    return r


if __name__ == '__main__':
    args = sys.argv[1:]
    extra, filt = [], []
    i = 0
    while i < len(args):
        if args[i] in ('--msgs', '--worms', '--frames', '--warm'):
            extra += args[i:i + 2]; i += 2
        else:
            filt.append(args[i]); i += 1
    if '--frames' not in extra:
        extra += ['--frames', '30']
    harness.sync_runtime()
    pkgs = sorted(d for d in os.listdir(LUA) if d != '@lib' and os.path.isdir(os.path.join(LUA, d)))
    if filt:
        pkgs = [p for p in pkgs if any(a in p for a in filt)]
    res = []
    with ThreadPoolExecutor(max_workers=int(os.environ.get('WORKERS', '6'))) as ex:
        for n, r in enumerate(ex.map(work, [(p, extra) for p in pkgs])):
            res.append(r)
            if (n + 1) % 50 == 0:
                print('progress', n + 1, '/', len(pkgs), flush=True)
    with open(OUTJ, 'w', encoding='utf-8') as f:
        for r in res:
            f.write(json.dumps(r) + '\n')
    ok = [r for r in res if r['instr'] is not None]
    ok.sort(key=lambda r: -r['instr'])
    print('measured %d of %d' % (len(ok), len(res)))
    for r in ok[:int(os.environ.get('TOP', '45'))]:
        print('%8d instr  %6d host  %s%s' % (r['instr'], r['host'] or 0, r['pkg'], '  ERR ' + r['errs'][0][:80] if r.get('errs') else ''))
    bad = [r for r in res if r['instr'] is None]
    print('failed:', [(r['pkg'], (r['err'] or '')[:60]) for r in bad][:12])
    tot = sorted(r['instr'] for r in ok)
    if tot:
        print('median %d  p90 %d  max %d' % (tot[len(tot) // 2], tot[int(len(tot) * 0.9)], tot[-1]))
