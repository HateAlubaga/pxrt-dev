import json,sys,io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SP = r"C:/Users/Admin/AppData/Local/Temp/claude/C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460/871c1252-bf15-404e-ad16-38f2b2c09974/scratchpad"
c=json.load(open(SP+"/corpus.json"))
f=sys.argv[1]; a=int(sys.argv[2]); b=int(sys.argv[3])
L=c[f].split('\n')
for i in range(a,b): print(i, L[i][:200])
