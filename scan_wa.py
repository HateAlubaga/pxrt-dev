import re, struct, sys

EXE = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe'
data = open(EXE, 'rb').read()

# PE sections -> map file offset to VA
pe = struct.unpack_from('<I', data, 0x3C)[0]
nsec = struct.unpack_from('<H', data, pe + 6)[0]
optsz = struct.unpack_from('<H', data, pe + 20)[0]
base = struct.unpack_from('<I', data, pe + 24 + 28)[0]
secs = []
off = pe + 24 + optsz
for i in range(nsec):
    name = data[off:off + 8].rstrip(b'\0').decode()
    vsz, va, rsz, rptr = struct.unpack_from('<IIII', data, off + 8)
    secs.append((name, va, vsz, rptr, rsz))
    off += 40
print('size', len(data), 'base', hex(base), [(s[0], hex(s[1] + base)) for s in secs])


def va_of(fo):
    for n, va, vsz, rptr, rsz in secs:
        if rptr <= fo < rptr + rsz:
            return base + va + fo - rptr
    return None


def fo_of(va):
    for n, sva, vsz, rptr, rsz in secs:
        if base + sva <= va < base + sva + rsz:
            return rptr + va - base - sva
    return None


def scan(name, pat, mask):
    pat = pat.encode('latin1').decode('unicode_escape').encode('latin1') if '\\x' in pat else pat.encode('latin1')
    assert len(pat) == len(mask), (name, len(pat), len(mask))
    rx = b''.join(re.escape(bytes([b])) if m == 'x' else b'.' for b, m in zip(pat, mask))
    hits = [m.start() for m in re.finditer(rx, data, re.S)]
    print(name, 'hits', len(hits), [hex(va_of(h)) for h in hits[:5]])
    return hits


h1 = scan('GetSchemeSettingsFromWam',
          r'\x57\x6A\x04\x68\x00\x00\x00\x00\x8B\xF8\xE8\x00\x00\x00\x00\x83\xF8\xFF\x75\x04\x0B\xC0\x5F\xC3\x8B\x47\x0C\x56\x8B\x35\x00\x00\x00\x00\x50\x6A\x00\x68\x00\x00\x00\x00\x68\x00\x00\x00\x00\xFF\xD6',
          '????????xxx????xxxxxxxxxxxxxxx????xxxx????x????xx')
h2 = scan('SetWscScheme',
          r'\x6A\xFF\x68\x00\x00\x00\x00\x64\xA1\x00\x00\x00\x00\x50\x64\x89\x25\x00\x00\x00\x00\x81\xEC\x00\x00\x00\x00\x53\x55\x8B\xAC\x24\x00\x00\x00\x00\x56\x8B\xB4\x24\x00\x00\x00\x00\x57\x8D\x4C\x24\x20',
          '???????xx????xxxx????xx????xxxxx????xxxx????xxxxx')
if h1:
    fo = h1[0]
    st = struct.unpack_from('<I', data, fo + 4)[0]
    rel = struct.unpack_from('<i', data, fo + 0xB)[0]
    setb = va_of(fo) + 0xF + rel
    print('schemeStruct', hex(st), 'SetBuiltinScheme', hex(setb))
    f = fo_of(setb)
    print('SetBuiltinScheme bytes', data[f:f + 24].hex(' '))
if h2:
    f = h2[0]
    print('SetWscScheme bytes', data[f:f + 32].hex(' '))
