import json, sys, glob, os
base = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460'
files = glob.glob(os.path.join(base, '*.jsonl'))
print(files)
for fp in files:
    n = 0
    for ln, line in enumerate(open(fp, encoding='utf-8')):
        try:
            o = json.loads(line)
        except Exception:
            continue
        msg = o.get('message') or {}
        c = msg.get('content')
        if not isinstance(c, list):
            continue
        for b in c:
            if b.get('type') == 'tool_use':
                inp = b.get('input', {})
                s = json.dumps(inp)
                if 'pxc2lua' in s:
                    n += 1
                    print(os.path.basename(fp)[:8], ln, b['name'], (inp.get('file_path') or inp.get('command', ''))[:150].replace('\n', ' '))
    print(fp, n)
