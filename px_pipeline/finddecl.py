"""Find where identifiers are declared across all package pxc + pxl libs.
usage: finddecl.py name1 name2 ..."""
import glob, re, sys, os
PK = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
HERE = os.path.dirname(os.path.abspath(__file__))
files = glob.glob(PK + r"\*\0.0.1\scripts_px\*.pxc") + glob.glob(HERE + r"\pxl\*.pxc")
names = sys.argv[1:]
TYPES = r"(?:int|fixed|bool|float|string|local|CWorm\s*\*|CGObject\s*\*|CSprite\s*\*|CSoundFile\s*\*|\w+\s*\*)"
for fn in files:
    t = open(fn, encoding="latin-1").read()
    for n in names:
        for m in re.finditer(r"(?m)^[ \t]*" + TYPES + r"\s+(?:\w+\s*,\s*)*" + re.escape(n) + r"\b[^;(]*;", t):
            ln = t.count("\n", 0, m.start()) + 1
            print("%s:%d: %s" % (os.path.relpath(fn, PK) if fn.startswith(PK) else os.path.basename(fn), ln, m.group(0).strip()[:100]))
