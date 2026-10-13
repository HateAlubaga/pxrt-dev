import json, sys, os
SP = r'C:\Users\Admin\AppData\Local\Temp\claude\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\scratchpad'
keys = sys.argv[1:]
for fn in ['fieldmap1.json', 'fieldmap2.json', 'fieldmap3.json', 'wf_fieldmap1.json']:
    p = os.path.join(SP, 're', fn)
    try:
        d = json.load(open(p, encoding='utf-8'))
    except Exception as e:
        print(fn, e)
        continue
    items = d['items'] if isinstance(d, dict) and 'items' in d else d
    print(fn, len(items))
    for it in [x for x in items if isinstance(x, dict)]:
        n = str(it.get('px_name', ''))
        if any(k in n for k in keys):
            print('  ', n, '|', it.get('cls'), '|', it.get('offset'), '|', str(it.get('note', it.get('notes', '')))[:240])
