import json, re, glob, os, sys
base = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460'
files = glob.glob(base + '/*.jsonl') + glob.glob(base + '/*/subagents/*.jsonl')
out = []
for fp in files:
    for ln, line in enumerate(open(fp, encoding='utf-8')):
        if '=== Fields' not in line and '=== Methods' not in line: continue
        try: o = json.loads(line)
        except Exception: continue
        c = (o.get('message') or {}).get('content')
        if not isinstance(c, list): continue
        for b in c:
            texts = []
            if b.get('type') == 'tool_result':
                cc = b.get('content')
                if isinstance(cc, list): texts += [x.get('text', '') for x in cc if isinstance(x, dict)]
                elif isinstance(cc, str): texts.append(cc)
            elif b.get('type') == 'tool_use':
                texts.append(json.dumps(b['input']))
            for t in texts:
                if '=== Fields' in t or '=== Methods' in t:
                    out.append((os.path.basename(fp)[:8], ln, b.get('type'), len(t), t[:200].replace('\n', ' | ')))
for r in out: print(r)
print(len(out))
