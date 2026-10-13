import json, sys, glob, os
fp = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974.jsonl'
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
            nm = b['name']
            if nm in ('Write', 'Edit'):
                p = inp.get('file_path', '')
                if p.endswith('pxc2lua.py'):
                    print(ln, nm, len(inp.get('content', '') or inp.get('new_string', '')), (inp.get('old_string') or '')[:60].replace('\n', ' '))
            elif nm == 'Bash':
                cmd = inp.get('command', '')
                if 'pxc2lua' in cmd and ('sed -i' in cmd or 'open(' in cmd and 'write' in cmd or 'replace(' in cmd):
                    print(ln, 'BASH-MOD', cmd[:200].replace('\n', ' | '))
