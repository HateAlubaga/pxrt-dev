import sys, re, pefile
pe = pefile.PE(r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe', fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
img = pe.get_memory_mapped_image()
pat = bytes.fromhex(sys.argv[1])
for m in re.finditer(re.escape(pat), img):
    print('%08X' % (base + m.start()))
