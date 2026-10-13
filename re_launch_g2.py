import json,re,sys,io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SP = r"C:/Users/Admin/AppData/Local/Temp/claude/C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460/871c1252-bf15-404e-ad16-38f2b2c09974/scratchpad"
c=json.load(open(SP+"/corpus.json"))
pat=re.compile(sys.argv[1])
n=0
for f,s in c.items():
    for i,l in enumerate(s.split('\n')):
        if pat.search(l):
            print(f,i,l.strip()[:200]); n+=1
            if n>int(sys.argv[2]): sys.exit()
