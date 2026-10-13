import json, sys, glob, os
D = r"C:\Users\Admin\.claude\projects\C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460\871c1252-bf15-404e-ad16-38f2b2c09974\subagents\workflows\wf_4c63cb99-707"
ids = sys.argv[1:] or ["af434016b48b62792", "afc157535feeed442"]
for a in ids:
    last = []
    n = 0
    ts = None
    for l in open(os.path.join(D, "agent-%s.jsonl" % a), encoding="utf-8"):
        n += 1
        try:
            d = json.loads(l)
        except Exception:
            continue
        ts = d.get("timestamp")
        if d.get("type") == "assistant":
            for b in d["message"]["content"]:
                if b.get("type") == "text" and b["text"].strip():
                    last.append(b["text"][:400])
                elif b.get("type") == "tool_use":
                    last.append("TOOL " + json.dumps(b["input"])[:200])
    print(a, n, ts)
    for t in last[-4:]:
        print("   ", t.replace("\n", " "))
