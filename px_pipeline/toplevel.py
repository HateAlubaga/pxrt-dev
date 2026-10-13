"""Census of top-level forms (depth-0 heads) across corpus.json."""
import os, re, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))


def strip(t):
    out = []
    i = 0
    n = len(t)
    while i < n:
        c = t[i]
        if t.startswith("//", i):
            j = t.find("\n", i)
            i = n if j < 0 else j
        elif t.startswith("/*", i):
            j = t.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        elif c == '"':
            j = i + 1
            while j < n and t[j] != '"':
                if t[j] == "\\":
                    j += 1
                j += 1
            out.append('"S"')
            i = j + 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


kinds = collections.Counter()
ex = {}
for k, t in C.items():
    t = strip(t)
    depth = 0
    cur = []
    for c in t:
        if depth == 0:
            if c == "{":
                head = " ".join("".join(cur).split())
                cur = []
                depth = 1
                kind = "FUNC"
                if re.match(r"^(override\s+)?([\w\*\s]+\s+)?\w+\s*::\s*\w+\s*\(", head):
                    kind = "METHOD"
                elif re.match(r"^[\w\*\s]+\s+\w+\s*\(", head):
                    kind = "FREEFUNC"
                elif re.match(r"^(struct|class)\s+\w+", head):
                    kind = "STRUCTDEF"
                else:
                    kind = "OTHER{"
                kinds[kind] += 1
                ex.setdefault(kind, []).append(k + ": " + head[:120])
                continue
            if c == ";":
                head = " ".join("".join(cur).split())
                cur = []
                lines = [x for x in head.split("\n")]
                # strip leading #defs
                h = head
                while True:
                    m = re.match(r"^#\w+\s*", h)
                    if not m:
                        break
                    kinds["#FLAG"] += 1
                    h = h[m.end():]
                if not h:
                    continue
                if re.match(r"^require\b", h):
                    kind = "REQUIRE"
                elif re.match(r"^\w+\s*:\s*\w+$", h):
                    kind = "CLASSDECL"
                elif re.match(r"^(int|fixed|float|bool|string)\s+[\w\[\],\s]+$", h):
                    kind = "VARDECL_PRIM"
                elif re.match(r"^\w+\s*\*\s*[\w\s,\*\[\]]+$", h):
                    kind = "VARDECL_PTR"
                elif "=" in h:
                    kind = "GLOBAL_ASSIGN"
                elif re.match(r"^\w+\s+[\w\[\],\s]+$", h):
                    kind = "VARDECL_OBJ"
                else:
                    kind = "OTHER;"
                kinds[kind] += 1
                ex.setdefault(kind, []).append(k + ": " + h[:120])
                continue
            cur.append(c)
        else:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
    rest = "".join(cur).strip()
    if rest:
        h = rest
        while True:
            m = re.match(r"^#\w+\s*", h)
            if not m:
                break
            kinds["#FLAG"] += 1
            h = h[m.end():]
        if h:
            kinds["TRAILING"] += 1
            ex.setdefault("TRAILING", []).append(k + ": " + h[:120])
for kd, c in kinds.most_common():
    print(kd, c)
    exs = ex.get(kd, [])
    step = max(1, len(exs) // 8)
    for e in exs[::step][:8]:
        print("    ", e)
