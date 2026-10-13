"""Disassemble WA.exe functions. usage: dis.py <hexaddr|name> [maxinsn] [outfile]
Stops at first ret (unless maxinsn reached). Names resolved via jelly/offsetcache.json."""
import sys, json, pefile, capstone
WA = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe"
OC = json.load(open(r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\offsetcache.json"))
_pe = None


def pe():
    global _pe
    if _pe is None:
        _pe = pefile.PE(WA, fast_load=True)
    return _pe


def read(va, n):
    p = pe()
    rva = va - p.OPTIONAL_HEADER.ImageBase
    return p.get_data(rva, n)


def u32(va):
    import struct
    return struct.unpack("<I", read(va, 4))[0]


md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.detail = True
REV = {v: k for k, v in OC.items()}


def dis(va, maxn=3000, stop_ret=True, maxbytes=0x4000):
    code = read(va, maxbytes)
    out = []
    for i in md.disasm(code, va):
        s = "%08x  %-6s %s" % (i.address, i.mnemonic, i.op_str)
        if i.mnemonic == "call" and i.op_str.startswith("0x"):
            t = int(i.op_str, 16)
            if t in REV:
                s += "   ; " + REV[t]
        out.append((i, s))
        if len(out) >= maxn:
            break
        if stop_ret and i.mnemonic in ("ret", "retn"):
            break
    return out


if __name__ == "__main__":
    a = sys.argv[1]
    va = OC[a] if a in OC else int(a, 16)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
    lines = [s for _, s in dis(va, n)]
    if len(sys.argv) > 3:
        open(sys.argv[3], "w").write("\n".join(lines))
        print(len(lines), "lines ->", sys.argv[3])
    else:
        print("\n".join(lines))
