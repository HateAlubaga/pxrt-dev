import json, sys
SP = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad'
d = json.load(open(SP + r'\re\fieldmap3.json', encoding='utf-8'))
items = d['items'] if isinstance(d, dict) and 'items' in d else d
w = int(sys.argv[1]) if len(sys.argv) > 1 else 110
for it in items:
    print('|'.join(str(it.get(k, '')) for k in ('px_name', 'cls', 'offset', 'kind', 'conf')), '|', str(it.get('note', it.get('notes', '')))[:w])
if isinstance(d, dict):
    for k in d:
        if k != 'items':
            print('KEY', k, str(d[k])[:300])
