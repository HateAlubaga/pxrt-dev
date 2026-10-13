"""Classify every wormcallback port block by the ProjectX class it came from.

Block = text between `local __px2j_prev_wormcallback = wormcallback` and the
matching chain wrapper `local prev, cur = __px2j_prev_wormcallback, wormcallback`.
Output: JSON {pkg: [{idx, pxc, kinds, param, usesThis, members, wrapLine}]}
"""
import os, re, glob, json, sys, collections

ROOT = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
re_cls = re.compile(r"^\s*([A-Za-z_]\w*)\s*:\s*([A-Za-z_]\w*)\s*(?:$|//|\{)", re.M)
re_msg = re.compile(r"\b([A-Za-z_]\w*)\s*::\s*Message\s*\(")
re_def = re.compile(r"function\s+wormcallback\s*\(\s*([A-Za-z_]\w*)?")
ENGINE = {"CWorm", "CTurnGame", "CMissile"}


def pxc_kinds(path):
    t = open(path, encoding="latin-1").read()
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"//[^\n]*", "", t)
    script = os.path.splitext(os.path.basename(path))[0]
    bases = {m.group(1): m.group(2) for m in re_cls.finditer(t)}
    kinds = set()
    for m in re_msg.finditer(t):
        cls = m.group(1)
        k = cls if cls in ENGINE else bases.get(cls, cls)
        # resolve one level of user class -> engine base
        k = k if k in ENGINE else bases.get(k, k)
        if cls == script:
            k = "SCRIPT"
        kinds.add(k if k in ENGINE or k == "SCRIPT" else "OTHER:" + k)
    return sorted(kinds)


def strip_comments(s):
    s = re.sub(r"--\[(=*)\[.*?\]\1\]", "", s, flags=re.S)
    return re.sub(r"--[^\n]*", "", s)


out = {}
stats = collections.Counter()
for f in sorted(glob.glob(os.path.join(ROOT, "*", "0.0.1", "main.lua"))):
    pkg = f.split(os.sep)[-3]
    pxdir = os.path.join(os.path.dirname(f), "scripts_px")
    pxcs = {os.path.basename(p).lower(): p for p in glob.glob(os.path.join(pxdir, "*.pxc"))}
    src = open(f, encoding="utf-8", errors="replace").read()
    lines = src.split("\n")
    starts = [i for i, l in enumerate(lines) if l.strip() == "local __px2j_prev_wormcallback = wormcallback"]
    wraps = [i for i, l in enumerate(lines) if l.strip() == "local prev, cur = __px2j_prev_wormcallback, wormcallback"]
    blocks = []
    if not starts:
        if re_def.search(src):
            blocks.append((0, len(lines), None))
    else:
        for s in starts:
            w = next((x for x in wraps if x > s), None)
            blocks.append((s, w if w is not None else len(lines), w))
    res = []
    for idx, (s, e, w) in enumerate(blocks):
        text = "\n".join(lines[s:e])
        # which pxc: header comments name it
        m = re.search(r"([A-Za-z0-9_\-\.]+\.pxc)", text[:3000])
        pxc = m.group(1).lower() if m else None
        if pxc not in pxcs:
            pxc = None
        kinds = pxc_kinds(pxcs[pxc]) if pxc else []
        code = strip_comments(text)
        defs = list(re_def.finditer(code))
        if not defs:
            continue
        param = defs[-1].group(1) or ""
        uses = 0
        members = collections.Counter()
        if param and param not in ("_",):
            body = code[defs[-1].end():]
            # all functions in the block may receive the object, count across the block
            uses = len(re.findall(r"\b%s\b" % re.escape(param), code)) - len(defs)
            for mm in re.finditer(r"\b%s\s*[.:]\s*([A-Za-z_]\w*)" % re.escape(param), code):
                members[mm.group(1)] += 1
        res.append({"idx": idx, "pxc": pxc, "kinds": kinds, "param": param,
                    "usesThis": uses > 0, "members": dict(members.most_common(12)),
                    "wrapLine": (w + 1) if w is not None else None, "start": s + 1})
        key = ("This" if uses > 0 else "noThis") + ":" + "+".join(kinds or ["?"])
        stats[key] += 1
    if res:
        out[pkg] = res
json.dump(out, open(sys.argv[1], "w"), indent=1)
print("pkgs", len(out), "blocks", sum(len(v) for v in out.values()))
for k, v in stats.most_common(40):
    print("%5d  %s" % (v, k))
