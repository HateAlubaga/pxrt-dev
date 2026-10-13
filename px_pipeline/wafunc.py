"""Recursive-descent disassembly of one WA.exe function.
usage: wafunc.py <hexaddr|name> <outfile>"""
import sys, re
from wadis import md, read, u32, REV, OC


def func(va, limit=20000):
    seen = {}
    work = [va]
    tables = {}
    while work and len(seen) < limit:
        a = work.pop()
        while a not in seen:
            try:
                code = read(a, 16)
            except Exception:
                break
            ins = next(md.disasm(code, a), None)
            if ins is None:
                break
            s = "%08x  %-6s %s" % (ins.address, ins.mnemonic, ins.op_str)
            if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
                t = int(ins.op_str, 16)
                if t in REV:
                    s += "   ; " + REV[t]
            seen[a] = (ins, s)
            m = ins.mnemonic
            if m.startswith("ret"):
                break
            if m.startswith("j"):
                op = ins.op_str
                if op.startswith("0x"):
                    work.append(int(op, 16))
                else:
                    mt = re.search(r"\[(\w+)\*4 \+ (0x[0-9a-f]+)\]", op)
                    if mt and m == "jmp":
                        tb = int(mt.group(2), 16)
                        ents = []
                        for k in range(512):
                            e = u32(tb + 4 * k)
                            if not (va - 0x10000 <= e <= va + 0x20000):
                                break
                            ents.append(e)
                            work.append(e)
                        tables[a] = ents
                if m == "jmp":
                    break
            a = ins.address + ins.size
    res = [seen[k] for k in sorted(seen)]
    return res, tables


if __name__ == "__main__":
    a = sys.argv[1]
    va = OC[a] if a in OC else int(a, 16)
    res, tables = func(va)
    lines = [s for _, s in res]
    for k, v in tables.items():
        lines.append("TABLE @%08x: %s" % (k, " ".join("%d:%08x" % (i, e) for i, e in enumerate(v))))
    open(sys.argv[2], "w").write("\n".join(lines))
    print(len(lines), "->", sys.argv[2])
