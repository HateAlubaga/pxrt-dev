import sys, re, glob, os
pat = re.compile(sys.argv[1])
base = r'C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460'
files = glob.glob(base + '/*.jsonl') + glob.glob(base + '/*/subagents/*.jsonl') + glob.glob(base + '/*/tool-results/*') + glob.glob(base + '/*/workflows/**/*', recursive=True)
for fp in files:
    if os.path.isdir(fp): continue
    try:
        t = open(fp, encoding='utf-8', errors='replace').read()
    except Exception: continue
    ms = list(pat.finditer(t))
    if ms:
        print(os.path.relpath(fp, base)[:90], len(ms), len(t))
