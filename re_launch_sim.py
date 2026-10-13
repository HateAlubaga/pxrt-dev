"""Simulate WA 3.8.1 weapon-table init (0x537320..0x53ad7a) incl. rep movsd copies and lea-based pointer regs.
Produces vanilla weapon table (dict offset->value), saved to re_launch_wtab.json
Usage: py -3.10 re_launch_sim.py
"""
import re, sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
SP = r"C:/Users/Admin/AppData/Local/Temp/claude/C--Users-Admin-AppData-Roaming-Claude-scratch-workspaces-14a59e29-aa4e-44dd-b46c-90bdd9bc55d7-4747db79-8adb-4122-ae31-fa8ab3cc0bf8-scratch-2026-09-29-3e8460/871c1252-bf15-404e-ad16-38f2b2c09974/scratchpad"
lines = open(SP + "/re/wtabinit.txt", encoding="latin1").read().splitlines()
R32 = r"(e[a-d]x|e[sd]i|ebp)"
mem = {}        # offset from eax (struct base) -> value (int) or None(unknown)
hist = {}       # offset -> list of (val, addr)
regs = {}       # reg -> ('c', int) | ('p', off) | None
def setreg(r, v): regs[r] = v
def getc(r):
    v = regs.get(r)
    return v[1] if v and v[0] == 'c' else None
M = 0xffffffff
def store(off, val, addr):
    mem[off] = val
    hist.setdefault(off, []).append((val, addr))
def parse_mem(op):
    m = re.match(r"(?:dword ptr )?\[(e[a-d]x|e[sd]i|ebp) \+ (0x[0-9a-f]+)\]$", op)
    if m:
        return m.group(1), int(m.group(2), 16)
    m = re.match(r"(?:dword ptr )?\[(e[a-d]x|e[sd]i|ebp)\]$", op)
    if m:
        return m.group(1), 0
    return None
def ptroff(r, d):
    v = regs.get(r)
    if r == 'eax' and (v is None or v[0] != 'p'):
        # eax is the struct base unless overwritten
        return d
    if v and v[0] == 'p':
        return v[1] + d
    return None
regs['eax'] = ('p', 0)
unk_eax_clobber = 0
for l in lines:
    p = l.split(" ", 1)
    try:
        addr = int(p[0], 16)
    except Exception:
        continue
    ins = p[1].strip()
    mn = ins.split(" ", 1)[0]
    ops = ins[len(mn):].strip()
    if addr in (0x537320, 0x539101, 0x53ad7b) or addr in (0x537320,):
        pass
    # function boundaries: reset at known starts
    if mn == "int3":
        continue
    if mn in ("ret",):
        regs = {'eax': ('p', 0)}
        continue
    if mn == "mov":
        a, b = [x.strip() for x in ops.split(",", 1)]
        # store to memory
        mm = parse_mem(a)
        if mm and a.startswith("dword ptr"):
            off = ptroff(mm[0], mm[1])
            if off is None:
                continue
            if re.match(R32 + "$", b):
                v = regs.get(b)
                val = v[1] if (v and v[0] == 'c') else None
            else:
                try:
                    val = int(b, 0) & M
                except Exception:
                    val = None
            store(off, val, addr)
            continue
        # reg dest
        if re.match(R32 + "$", a):
            if re.match(R32 + "$", b):
                regs[a] = regs.get(b)
            else:
                try:
                    regs[a] = ('c', int(b, 0) & M)
                except Exception:
                    mm2 = parse_mem(b)
                    if mm2 and b.startswith("dword ptr"):
                        off = ptroff(mm2[0], mm2[1])
                        if off is not None and off in mem and mem[off] is not None:
                            regs[a] = ('c', mem[off])
                        else:
                            regs[a] = None
                    else:
                        regs[a] = None
        continue
    if mn == "xor":
        a, b = [x.strip() for x in ops.split(",", 1)]
        if a == b and re.match(R32 + "$", a):
            regs[a] = ('c', 0)
        elif re.match(R32 + "$", a):
            regs[a] = None
        continue
    if mn == "lea":
        a, b = [x.strip() for x in ops.split(",", 1)]
        m = re.match(r"\[(e[a-d]x|e[sd]i|ebp) \+ (0x[0-9a-f]+)\]$", b)
        if m and re.match(R32 + "$", a):
            o = ptroff(m.group(1), int(m.group(2), 16))
            regs[a] = ('p', o) if o is not None else None
        elif re.match(R32 + "$", a):
            regs[a] = None
        continue
    if mn == "rep":
        # rep movsd: ecx, esi, edi
        n = getc('ecx')
        s = regs.get('esi'); d = regs.get('edi')
        if n is None or not s or not d or s[0] != 'p' or d[0] != 'p':
            print("WARN rep unresolved at %x: ecx=%s esi=%s edi=%s" % (addr, regs.get('ecx'), s, d))
        else:
            for i in range(n):
                src = s[1] + 4 * i
                dst = d[1] + 4 * i
                mem[dst] = mem.get(src, 0)  # unwritten == 0 (zeroed table)
                hist.setdefault(dst, []).append((mem[dst], addr))
            regs['esi'] = ('p', s[1] + 4 * n); regs['edi'] = ('p', d[1] + 4 * n); regs['ecx'] = ('c', 0)
        continue
    if mn in ("and", "or"):
        a, b = [x.strip() for x in ops.split(",", 1)]
        mm = parse_mem(a)
        if mm and a.startswith("dword ptr"):
            off = ptroff(mm[0], mm[1])
            if off is not None:
                try:
                    k = int(b, 0) & M
                    cur = mem.get(off, 0)
                    if cur is not None:
                        store(off, (cur & k) if mn == "and" else (cur | k), addr)
                    else:
                        store(off, None, addr)
                except Exception:
                    store(off, None, addr)
            continue
        if re.match(R32 + "$", a):
            c = getc(a)
            try:
                k = int(b, 0) & M
            except Exception:
                k = None
            if c is not None and k is not None:
                regs[a] = ('c', (c & k) if mn == "and" else (c | k))
            else:
                regs[a] = None
        continue
    if mn in ("add", "sub"):
        a, b = [x.strip() for x in ops.split(",", 1)]
        if re.match(R32 + "$", a):
            c = getc(a)
            try:
                k = int(b, 0)
            except Exception:
                k = None
            if k is None and re.match(R32 + "$", b):
                k = getc(b)
            if c is not None and k is not None:
                regs[a] = ('c', ((c + k) if mn == "add" else (c - k)) & M)
            elif regs.get(a) and regs[a][0] == 'p' and k is not None:
                regs[a] = ('p', regs[a][1] + (k if mn == "add" else -k))
            else:
                regs[a] = None
        continue
    # anything else that writes a register -> unknown
    m = re.match(R32 + r"\b", ops)
    if mn in ("movzx", "movsx", "imul", "neg", "sbb", "pop", "setl", "setge", "shl", "shr", "sar", "inc", "dec", "cdq"):
        if mn not in ("setl", "setge"):
            for rr in re.findall(R32, ops.split(",")[0]):
                regs[rr] = None
        if mn in ("setl", "setge"):
            # version compare: assume latest version (WA 3.8.1 >= every threshold)
            regs['ecx'] = ('c', 0 if mn == "setl" else 1)
        continue
    if mn == "call":
        for rr in ('eax', 'ecx', 'edx'):
            regs[rr] = None if rr != 'eax' else regs['eax']
        continue
json.dump({str(k): v for k, v in mem.items()}, open(r"C:/Users/Admin/pxrt_dev/re_launch_wtab.json", "w"))
print("mem entries", len(mem), "unknown", sum(1 for v in mem.values() if v is None))
