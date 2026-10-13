import sys, struct, pefile
# usage: wacalls.py <hex target> ... : list call/jmp rel32 sites to each target
pe = pefile.PE(r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe', fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
img = pe.get_memory_mapped_image()
targets = [int(a, 16) for a in sys.argv[1:]]
for sec in pe.sections:
    if not sec.Characteristics & 0x20000000:
        continue
    s, e = sec.VirtualAddress, sec.VirtualAddress + sec.Misc_VirtualSize
    for i in range(s, e - 5):
        op = img[i]
        if op not in (0xE8, 0xE9):
            continue
        rel = struct.unpack_from('<i', img, i + 1)[0]
        dst = base + i + 5 + rel
        if dst in targets:
            print('%08X %s %08X' % (base + i, 'call' if op == 0xE8 else 'jmp', dst))
