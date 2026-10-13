"""Print the verification bytes (offset 8..23) of WA functions and check that no base relocation touches them.
usage: py -3.10 wasig.py 0x51EE60 0x512E80 ..."""
import struct, sys
from wadis import data, off, base, pe

# base relocation directory: data directory #5 of the optional header
opt = pe + 24
reloc_rva, reloc_size = struct.unpack_from('<II', data, opt + 96 + 5 * 8)
relocs = set()
p = off(base + reloc_rva)
end = p + reloc_size
while p < end:
    page, size = struct.unpack_from('<II', data, p)
    if size == 0:
        break
    for i in range((size - 8) // 2):
        e = struct.unpack_from('<H', data, p + 8 + 2 * i)[0]
        if e >> 12 == 3:   # IMAGE_REL_BASED_HIGHLOW
            r = base + page + (e & 0xFFF)
            relocs.update(range(r, r + 4))
    p += size

for arg in sys.argv[1:]:
    a = int(arg, 16)
    o = off(a)
    head = data[o:o + 24]
    bad = [hex(x) for x in range(a, a + 24) if x in relocs]
    sig = head[8:24]
    print('%s head=%s sig=%s relocs_in_0_24=%s' % (arg, head.hex(), ''.join('\\x%02X' % b for b in sig), bad or 'none'))
