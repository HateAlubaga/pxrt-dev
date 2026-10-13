import json, sys

p = sys.argv[1]
s = open(p, encoding='utf-8', errors='replace').read()
w = json.loads(s)
print('logs', w.get('logs'))
d = w['result']
print('keys', list(d.keys()))
for k, v in d.items():
    print(k, len(v) if hasattr(v, '__len__') else v)
out = []
for n, f in enumerate(d['confirmed']):
    fn = f['file'].replace('\\', '/').split('/')[-1]
    out.append(f"=== C{n} [{f.get('severity')}] {fn}:{f.get('line')} dim={f.get('dim')}")
    out.append('SUMMARY: ' + f['summary'])
    out.append('SCENARIO: ' + f['failure_scenario'])
    out.append('FIX: ' + f.get('suggested_fix', ''))
    out.append('VERDICT: ' + f['verdict']['reason'])
    out.append('')
rej = d.get('rejected', [])
out.append('######## REJECTED')
for n, f in enumerate(rej):
    fn = f['file'].replace('\\', '/').split('/')[-1]
    out.append(f"--- R{n} [{f.get('severity')}] {fn}:{f.get('line')} dim={f.get('dim')}: {f['summary']}")
    v = f.get('verdict') or {}
    out.append('    WHY: ' + str(v.get('reason', ''))[:400])
open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(out))
print('written')
