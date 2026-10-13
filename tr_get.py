import json, sys
fp = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974.jsonl'
want = set(int(x) for x in sys.argv[2:])
mode = sys.argv[1]
for ln, line in enumerate(open(fp, encoding='utf-8')):
    if ln not in want:
        continue
    o = json.loads(line)
    for b in o['message']['content']:
        if b.get('type') == 'tool_use':
            inp = b['input']
            if mode == 'write':
                open(r'C:\Users\Admin\pxrt_dev\pxc2lua_recovered.py', 'w', encoding='utf-8', newline='\n').write(inp['content'])
                print('written', len(inp['content']))
            else:
                print('=== line', ln, b['name'])
                print(inp.get('command') or json.dumps(inp)[:3000])
