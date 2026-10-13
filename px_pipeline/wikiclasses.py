"""Parse pxwiki class pages into px/classes.json: {cls:{inherits, fields:[[name,type]], methods:[sig]}}"""
import os, re, json, glob
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs("px", exist_ok=True)
out = {}
for fn in glob.glob("pxwiki/*.wiki"):
    name = os.path.basename(fn)[:-5]
    t = open(fn, encoding="utf-8", errors="replace").read()
    if "=== Fields ===" not in t and "=== Methods ===" not in t:
        continue
    raw = re.sub(r"<[^>]+>", "", t)
    raw = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", raw)
    raw = raw.replace("'''''", "").replace("'''", "").replace("''", "")
    inh = re.search(r"Inherits\s+(\w+)", raw)
    fields, methods = [], []
    sec = None
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("=== Fields"):
            sec = "f"; continue
        if s.startswith("=== Methods"):
            sec = "m"; continue
        if s.startswith("=="):
            sec = None; continue
        if not s:
            continue
        if sec == "f":
            m = re.match(r"^(\w+)\s*:\s*(.+)$", s)
            if m:
                fields.append([m.group(1), m.group(2).strip()])
        elif sec == "m":
            if "(" in s:
                methods.append(s)
    out[name] = {"inherits": inh.group(1) if inh else None, "fields": fields, "methods": methods}
json.dump(out, open("px/classes.json", "w"), indent=1)
for k, v in sorted(out.items()):
    print(k, "<", v["inherits"], "F%d M%d" % (len(v["fields"]), len(v["methods"])), " ".join(f[0] for f in v["fields"])[:300])
