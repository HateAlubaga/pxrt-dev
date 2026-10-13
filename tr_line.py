import json, sys
fp = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974.jsonl'
if len(sys.argv) > 3: fp = sys.argv[3]
want = set(int(x) for x in sys.argv[1].split(','))
mx = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
for ln, line in enumerate(open(fp, encoding='utf-8')):
    if ln not in want: continue
    o = json.loads(line)
    c = (o.get('message') or {}).get('content')
    print('=== line', ln)
    if isinstance(c, str): print(c[:mx]); continue
    for b in c:
        if b.get('type') == 'text': print('[text]', b['text'][:mx])
        elif b.get('type') == 'tool_use': print('[use]', json.dumps(b['input'])[:mx])
        elif b.get('type') == 'tool_result':
            cc = b.get('content')
            if isinstance(cc, list): cc = '\n'.join(x.get('text', '') for x in cc if isinstance(x, dict))
            print('[result]', (cc or '')[:mx])
