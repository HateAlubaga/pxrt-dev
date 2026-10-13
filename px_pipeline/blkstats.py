import json, sys, collections
d = json.load(open(sys.argv[1]))
by = collections.defaultdict(collections.Counter)
ex = collections.defaultdict(list)
for pkg, bl in d.items():
    for b in bl:
        if not b["usesThis"]:
            continue
        k = "+".join(x for x in b["kinds"] if not x.startswith("OTHER")) or "?"
        for m, c in b["members"].items():
            by[k][m] += 1
        if len(ex[k]) < 8:
            ex[k].append("%s:%s(%s)" % (pkg, b["start"], b["pxc"]))
for k, c in by.items():
    print("==", k, "examples:", " ".join(ex[k]))
    print("  ", ", ".join("%s:%d" % kv for kv in c.most_common(45)))
