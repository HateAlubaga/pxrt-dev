import json, sys, os
J = sys.argv[1]
out = sys.argv[2]
res = {}
for line in open(J, encoding='utf-8'):
    line = line.strip()
    if not line:
        continue
    d = json.loads(line)
    if d.get('type') == 'result':
        r = d.get('result')
        res[d.get('key')] = r
items = []
notes = []
for k, r in res.items():
    if isinstance(r, dict):
        items += r.get('items', [])
        if r.get('notes'):
            notes.append(r['notes'])
json.dump({'items': items, 'notes': notes}, open(out, 'w', encoding='utf-8'), indent=1)
with open(out.replace('.json', '.txt'), 'w', encoding='utf-8') as f:
    for it in items:
        f.write('%-22s %-24s %-8s %-6s %-6s %s\n' % (it['px_name'], it['cls'][:24], it['offset'], it['vtype'], it['confidence'], it['evidence']))
    f.write('\n==NOTES==\n')
    for n in notes:
        f.write(n + '\n\n')
print(len(items), 'items', len(notes), 'notes')
