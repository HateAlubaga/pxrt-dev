import pefile, capstone, sys
path = sys.argv[1]
pe = pefile.PE(path)
base = pe.OPTIONAL_HEADER.ImageBase
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True
name = b'FireWeapon\0'
# find exact string "FireWeapon" (not a suffix of a longer name)
strva = []
i = img.find(name)
while i >= 0:
    if img[i - 1] == 0:
        strva.append(base + i)
    i = img.find(name, i + 1)
text = [s for s in pe.sections if s.Name.startswith(b'.text')][0]
code = img[text.VirtualAddress:text.VirtualAddress + text.Misc_VirtualSize]
ins_list = list(md.disasm(code, base + text.VirtualAddress))
for k, ins in enumerate(ins_list):
    if ins.mnemonic == 'push' and any(ins.op_str == hex(v) for v in strva):
        window = ins_list[max(0, k - 8):k + 6]
        pushes = [w for w in window if w.mnemonic in ('push', 'mov', 'lea')]
        for w in window:
            print('%08x %s %s' % (w.address, w.mnemonic, w.op_str))
        print('---')
        # candidate hook addresses: immediate pushes into .text
        for w in window:
            if w.mnemonic in ('push', 'mov') and '0x100' in w.op_str:
                try:
                    v = int(w.op_str.split(',')[-1].strip(), 16)
                except ValueError:
                    continue
                if base + text.VirtualAddress <= v < base + text.VirtualAddress + len(code):
                    print('candidate %08x:' % v)
                    rva = v - base
                    for j, x in enumerate(md.disasm(img[rva:rva + 60], v)):
                        print('   %08x %s %s' % (x.address, x.mnemonic, x.op_str))
                        if j > 14:
                            break
