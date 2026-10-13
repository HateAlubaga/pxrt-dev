"""replay Write/Edit tool calls from the session transcript to rebuild the (wiped) scratchpad scripts."""
import json, os, re, subprocess, sys
TR = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974.jsonl'
SP = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad'
os.makedirs(SP, exist_ok=True)
# heredoc patches against pxc2lua.py that were run through Bash
BASH_PATCH = {20766, 22401}
BASH_RUN = {20772: ['cp', 'pxc2lua.py', 'pxc2lua.py.v1'], 20808: ['cp', 'pxc2lua.py', 'pxc2lua.py.v2']}
PY_RUN = {20772: 'patch1.py', 20808: 'patch2.py'}
for ln, line in enumerate(open(TR, encoding='utf-8')):
    try:
        o = json.loads(line)
    except Exception:
        continue
    c = (o.get('message') or {}).get('content')
    if not isinstance(c, list):
        continue
    for b in c:
        if b.get('type') != 'tool_use':
            continue
        inp = b['input']
        if b['name'] in ('Write', 'Edit'):
            p = inp.get('file_path', '').replace('\\', '/')
            if '/scratchpad/' not in p:
                continue
            rel = p.split('/scratchpad/', 1)[1]
            dst = os.path.join(SP, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if b['name'] == 'Write':
                open(dst, 'w', encoding='utf-8', newline='').write(inp['content'])
            else:
                if not os.path.exists(dst):
                    print('EDIT on missing', rel, ln)
                    continue
                s = open(dst, encoding='utf-8', newline='').read()
                old, new = inp['old_string'], inp['new_string']
                n = s.count(old)
                if n == 0:
                    print('EDIT old not found', rel, ln)
                    continue
                s = s.replace(old, new) if inp.get('replace_all') else s.replace(old, new, 1)
                open(dst, 'w', encoding='utf-8', newline='').write(s)
        elif b['name'] == 'Bash':
            if ln in BASH_PATCH:
                cmd = inp['command']
                m = re.search(r"<<'(\w+)'\n(.*?)\n\1\n", cmd, re.S)
                if not m:
                    print('no heredoc at', ln)
                    continue
                code = m.group(2)
                open(os.path.join(SP, '_tmp_patch.py'), 'w', encoding='utf-8', newline='').write(code)
                r = subprocess.run([sys.executable, '_tmp_patch.py'], cwd=SP, capture_output=True, text=True)
                print('bash patch', ln, 'rc', r.returncode, (r.stderr or '')[-300:])
            if ln in BASH_RUN:
                subprocess.run(BASH_RUN[ln], cwd=SP)
                r = subprocess.run([sys.executable, PY_RUN[ln]], cwd=SP, capture_output=True, text=True)
                print('patch run', PY_RUN[ln], 'rc', r.returncode, (r.stderr or '')[-300:])
print('done')
for f in sorted(os.listdir(SP)):
    pass
print(len(os.listdir(SP)), 'files')
