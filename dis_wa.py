import sys, struct
import capstone

EXE = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe'
data = open(EXE, 'rb').read()
BASE = 0x400000
TEXT_VA, TEXT_RPTR = 0x401000, 0x400  # fixed below from the PE header
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe + 6)[0]
optsz = struct.unpack_from('<H', data, pe + 20)[0]
off = pe + 24 + optsz
secs = []
for i in range(nsec):
    vsz, va, rsz, rptr = struct.unpack_from('<IIII', data, off + 8)
    secs.append((va + BASE, vsz, rptr, rsz))
    off += 40


def fo_of(va):
    for sva, vsz, rptr, rsz in secs:
        if sva <= va < sva + rsz:
            return rptr + va - sva
    raise ValueError(hex(va))


def dis(va, n, stop_at_ret=True, maxins=400):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    f = fo_of(va)
    cnt = 0
    for ins in md.disasm(data[f:f + n], va):
        print('%08x  %-28s %s %s' % (ins.address, ins.bytes.hex(' '), ins.mnemonic, ins.op_str))
        cnt += 1
        if stop_at_ret and ins.mnemonic == 'ret':
            break
        if cnt >= maxins:
            break


if __name__ == '__main__':
    va = int(sys.argv[1], 16)
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 600
    dis(va, n, stop_at_ret=(len(sys.argv) <= 3))
