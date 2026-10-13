"""Rebuild pxwiki/*.wiki class pages (PX 0.8.0 wiki) from texts preserved in the session transcript,
then run wikiclasses.py to regenerate px/classes.json.  Needed because the wiki sits behind Anubis now."""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
TR = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974.jsonl'
LINES = {24412: None, 24501: None, 24551: None, 16902: None}
for ln, line in enumerate(open(TR, encoding='utf-8')):
    if ln in LINES:
        o = json.loads(line)
        for b in o['message']['content']:
            if b.get('type') == 'tool_result':
                cc = b['content']
                if isinstance(cc, list):
                    cc = '\n'.join(x.get('text', '') for x in cc if isinstance(x, dict))
                LINES[ln] = cc
os.makedirs('pxwiki', exist_ok=True)
pages = {}
for ln in (16902, 24412, 24501, 24551):
    t = LINES[ln]
    if ln == 24551:
        pages['CGameState'] = t
        continue
    parts = re.split(r'(?m)^#### (\w+)\s*$', t)
    # parts: [pre, name1, body1, name2, body2, ...]
    for i in range(1, len(parts), 2):
        pages.setdefault(parts[i], parts[i + 1].strip('\n') + '\n')
# the CGameState page (24551) has no header; CEnv body from 24501 may continue into other pages: cut at CLandscape
for k in list(pages):
    pages[k] = re.sub(r'\n\{\{Classes\}\}.*\Z', '\n{{Classes}}\n', pages[k], flags=re.S) if k not in ('CObject',) else pages[k]
# CObject: the transcript's CObject section is followed by CGame, CWorm in the same blob -> already split by header
# empty-bodied class pages (they have a Fields/Methods header but nothing parseable)
for k in ('CCrate', 'CFilter', 'CGas', 'CMine', 'CMissile', 'COilDrum', 'CWormsApp'):
    pages.setdefault(k, '=== Fields ===\n')
for k, v in pages.items():
    open('pxwiki/%s.wiki' % k, 'w', encoding='utf-8', newline='').write(v)
print(sorted(pages))
