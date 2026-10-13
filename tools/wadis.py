"""Disassemble WA.exe functions at canonical addresses (ImageBase 0x400000).
usage: py -3.10 wadis.py 0x51EE60 [count]"""
import struct, sys
import capstone

WA = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe'
data = open(WA, 'rb').read()
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe + 6)[0]
optsz = struct.unpack_from('<H', data, pe + 20)[0]
base = struct.unpack_from('<I', data, pe + 24 + 28)[0]
secs = []
for i in range(nsec):
    o = pe + 24 + optsz + i * 40
    name = data[o:o + 8].rstrip(b'\0').decode()
    vsize, va, rsize, raw = struct.unpack_from('<IIII', data, o + 8)
    secs.append((name, va, vsize, raw, rsize))


def off(addr):
    rva = addr - base
    for name, va, vsize, raw, rsize in secs:
        if va <= rva < va + max(vsize, rsize):
            return raw + rva - va
    raise ValueError(hex(addr))


def dis(addr, count=40):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = off(addr)
    n = 0
    for ins in md.disasm(data[o:o + 4096], addr):
        print('  %08X  %-24s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        n += 1
        if n >= count:
            break


if __name__ == '__main__':
    a = int(sys.argv[1], 16)
    dis(a, int(sys.argv[2]) if len(sys.argv) > 2 else 40)
