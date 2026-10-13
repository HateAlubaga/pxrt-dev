import pefile, capstone, sys, re
pe = pefile.PE(r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\wkJellyWorm.dll')
base = pe.OPTIONAL_HEADER.ImageBase
img = pe.get_memory_mapped_image()
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
md.skipdata = True

def s_at(va):
    rva = va - base
    if 0 <= rva < len(img):
        b = img[rva:rva + 80]
        z = b.split(b'\0')[0]
        if len(z) >= 3 and all(32 <= c < 127 for c in z):
            return z.decode()
    return None

def dis(rva, before, after):
    start = rva - before
    for ins in md.disasm(img[start:rva + after], base + start):
        note = ''
        for m in re.findall(r'0x[0-9a-f]{6,8}', ins.op_str):
            s = s_at(int(m, 16))
            if s:
                note += '  ; "%s"' % s
        mark = '>>' if ins.address - base == rva else '  '
        print('%s %05x %s %s%s' % (mark, ins.address - base, ins.mnemonic, ins.op_str, note))

print('imagebase', hex(base))
for a in sys.argv[1:]:
    print('=== rva', a)
    dis(int(a, 16), 0x60, 0x30)
