import sys, glob
from lupa import LuaRuntime
L = LuaRuntime()
chk = L.eval("function(src, name) local f, e = load(src, name) return e end")
paths = sys.argv[1:] or glob.glob(r"C:/Program Files (x86)/by Decepticon/Worms Armageddon/jelly/packages/*/0.0.1/main.lua")
bad = 0
for p in paths:
    e = chk(open(p, encoding="utf-8", errors="replace").read(), "@" + p)
    if e:
        bad += 1
        print("ERR", e)
print("checked", len(paths), "bad", bad, L.eval("_VERSION"))
