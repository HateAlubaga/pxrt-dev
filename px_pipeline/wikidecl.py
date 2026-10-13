"""Print compact declarations (fields/methods) from given wiki pages."""
import os, re, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
for name in sys.argv[1:]:
    fn = "pxwiki/%s.wiki" % name
    if not os.path.exists(fn):
        print("## missing", name); continue
    t = open(fn, encoding="utf-8", errors="replace").read()
    raw = re.sub(r"<[^>]+>", " ", t)
    raw = re.sub(r"\{\{[^}]*\}\}", "", raw)
    raw = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", raw)
    raw = raw.replace("'''''", "").replace("'''", "").replace("''", "")
    out = []
    for line in raw.splitlines():
        s = re.sub(r"\s+", " ", line).strip()
        if not s:
            continue
        if re.match(r"^(\w[\w\s\*\[\]]*)\s*:\s*[\w\*\[\] ]+$", s) and len(s) < 70:
            out.append(s)
        elif re.match(r"^[\w\*\s\[\]]+\s\w+\s*\(.*\)\s*$", s) and len(s) < 160:
            out.append(s)
        elif s.startswith("Inherit") or s.startswith("enum") or "= (" in s:
            out.append(s)
    # dedupe preserving order
    seen = set(); res = []
    for s in out:
        if s not in seen:
            seen.add(s); res.append(s)
    print("## %s (%d bytes)" % (name, len(t)))
    print(" | ".join(res))
