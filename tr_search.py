import json, sys, re, glob, os
pat = re.compile(sys.argv[1])
maxn = int(sys.argv[2]) if len(sys.argv) > 2 else 20
ctx = int(sys.argv[3]) if len(sys.argv) > 3 else 200
base = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460'
files = [os.path.join(base, '871c1252-bf15-404e-ad16-38f2b2c09974.jsonl')]
files += glob.glob(os.path.join(base, '871c1252-bf15-404e-ad16-38f2b2c09974', 'subagents', '*.jsonl'))
files += glob.glob(os.path.join(base, '871c1252-bf15-404e-ad16-38f2b2c09974', 'tool-results', '*.txt'))
n = 0
for fp in files:
    if fp.endswith('.txt'):
        t = open(fp, encoding='utf-8', errors='replace').read()
        for m in pat.finditer(t):
            print(os.path.basename(fp), 'txt@%d' % m.start(), t[max(0, m.start() - 50):m.start() + ctx].replace('\n', ' | '))
            n += 1
            if n >= maxn:
                sys.exit(0)
        continue
    for ln, line in enumerate(open(fp, encoding='utf-8')):
        if not pat.search(line):
            continue
        try:
            o = json.loads(line)
        except Exception:
            continue
        c = (o.get('message') or {}).get('content')
        texts = []
        if isinstance(c, list):
            for b in c:
                if b.get('type') == 'tool_result':
                    cc = b.get('content')
                    if isinstance(cc, list):
                        texts += [x.get('text', '') for x in cc if isinstance(x, dict)]
                    elif isinstance(cc, str):
                        texts.append(cc)
        for t in texts:
            m = pat.search(t)
            if m:
                print(os.path.basename(fp)[:12], ln, len(t), t[max(0, m.start() - 50):m.start() + ctx].replace('\n', ' | '))
                n += 1
                if n >= maxn:
                    sys.exit(0)
