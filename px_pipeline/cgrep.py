"""Regex grep over corpus.json (comments stripped unless -c). usage: cgrep.py PATTERN [max] [-c] [-f file_substring]"""
import os, re, json, sys
HERE = os.path.dirname(os.path.abspath(__file__))
C = json.load(open(os.path.join(HERE, "corpus.json"), encoding="utf-8"))
args = sys.argv[1:]
keepc = "-c" in args
fsub = None
if "-f" in args:
    i = args.index("-f")
    fsub = args[i + 1]
    del args[i:i + 2]
args = [a for a in args if a != "-c"]
pat = re.compile(args[0])
mx = int(args[1]) if len(args) > 1 else 40
n = 0
tot = 0
for k, t in C.items():
    if fsub and fsub not in k:
        continue
    if not keepc:
        t = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), t, flags=re.S)
        t = re.sub(r"//[^\n]*", "", t)
    for i, line in enumerate(t.split("\n")):
        if pat.search(line):
            tot += 1
            if n < mx:
                print("%s:%d: %s" % (k, i + 1, line.strip()[:160]))
                n += 1
print("TOTAL", tot)
