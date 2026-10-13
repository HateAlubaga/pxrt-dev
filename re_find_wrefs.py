import sys, io, re
sys.path.insert(0, r"C:/Users/Admin/pxrt_dev/rs")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import lib
L = lib.lin()
# find instrs that load weapon entry pointer from [x + 0x36c] then use that reg with disp in targets within N insns
targets = set(int(x, 16) for x in sys.argv[1].split(","))
N = int(sys.argv[2]) if len(sys.argv) > 2 else 40
pat_load = re.compile(r"mov (e[a-z]{2}), dword ptr \[(e[a-z]{2}) \+ 0x36c\]")
for k, (a, sz, t) in enumerate(L):
    m = pat_load.match(t)
    if not m: continue
    r = m.group(1)
    for j in range(k + 1, min(k + N, len(L))):
        a2, s2, t2 = L[j]
        mm = re.search(r"\[%s \+ (0x[0-9a-f]+)\]" % r, t2)
        if mm and int(mm.group(1), 16) in targets:
            print("%08x  %s   ->  %08x %s" % (a, t, a2, t2))
        if re.match(r"mov %s," % r, t2) and j > k + 1: break
        if t2.startswith("ret"): break
