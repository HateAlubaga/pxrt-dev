import sys, pefile
# usage: wasig.py <hex addr> ... : bytes 8..23 of each function as a Lua string literal (for E.waFn)
pe = pefile.PE(r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe', fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
img = pe.get_memory_mapped_image()
for arg in sys.argv[1:]:
    a = int(arg, 16)
    s = img[a - base + 8:a - base + 24]
    print('%X "%s"' % (a, ''.join('\\x%02X' % c for c in s)))
