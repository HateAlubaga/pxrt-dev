import json, os, collections, sys
fp = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974.jsonl'
ev = []
for ln, line in enumerate(open(fp, encoding='utf-8')):
    try:
        o = json.loads(line)
    except Exception:
        continue
    c = (o.get('message') or {}).get('content')
    if not isinstance(c, list):
        continue
    for b in c:
        if b.get('type') == 'tool_use' and b['name'] in ('Write', 'Edit'):
            p = b['input'].get('file_path', '').replace('\\', '/')
            if '/scratchpad/' in p:
                rel = p.split('/scratchpad/', 1)[1]
                sess = p.split('/scratchpad/', 1)[0].rsplit('/', 1)[1][:8]
                ev.append((ln, b['name'], rel, sess, len(b['input'].get('content') or b['input'].get('new_string') or '')))
byname = collections.OrderedDict()
for e in ev:
    byname.setdefault(e[2], []).append(e)
for k, v in byname.items():
    print('%-34s' % k, ' '.join('%s%s@%d(%d)' % (x[1][0], x[3][:2], x[0], x[4]) for x in v))
print(len(byname))
