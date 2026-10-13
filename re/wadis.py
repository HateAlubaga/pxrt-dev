import sys, pefile, capstone
pe = pefile.PE(r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe', fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
addr = int(sys.argv[1], 16)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 120
code = img[addr - base: addr - base + n * 8]
for i, ins in enumerate(md.disasm(code, addr)):
    if i >= n:
        break
    print('%08X  %-8s %s' % (ins.address, ins.mnemonic, ins.op_str))
