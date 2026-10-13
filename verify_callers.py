import struct, sys, re

path = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe"
data = open(path, "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
optsz = struct.unpack_from("<H", data, pe + 20)[0]
imgbase = struct.unpack_from("<I", data, pe + 24 + 28)[0]
secs = []
off = pe + 24 + optsz
for i in range(nsec):
    name = data[off:off + 8].rstrip(b"\0").decode()
    vsize, va, rsize, raw = struct.unpack_from("<IIII", data, off + 8)
    secs.append((name, va, vsize, raw, rsize))
    off += 40
print("imagebase", hex(imgbase), [(s[0], hex(s[1]), hex(s[2])) for s in secs])


def va2off(va):
    rva = va - imgbase
    for n, sva, vs, raw, rs in secs:
        if sva <= rva < sva + max(vs, rs):
            return raw + (rva - sva)
    return None


def off2va(o):
    for n, sva, vs, raw, rs in secs:
        if raw <= o < raw + rs:
            return imgbase + sva + (o - raw)
    return None


# GetSchemeSettingsFromWam pattern (? = wildcard)
pat = b"\x57\x6A\x04\x68????\x8B\xF8\xE8????\x83\xF8\xFF\x75\x04\x0B\xC0\x5F\xC3\x8B\x47\x0C\x56\x8B\x35????\x50\x6A\x00\x68????\x68????\xFF\xD6"
rx = re.compile(re.escape(pat).replace(rb"\?", b"."), re.S)
rx = re.compile(b"".join(b"." if c == ord("?") else re.escape(bytes([c])) for c in pat), re.S)
m = list(rx.finditer(data))
print("matches", len(m))
o = m[0].start()
g = off2va(o)
print("GetSchemeSettingsFromWam static", hex(g))
rel = struct.unpack_from("<i", data, o + 0xB)[0]
sbs = g + 0xF + rel
print("SetBuiltinScheme static", hex(sbs))

# SetWscScheme
pat2 = b"\x6A\xFF\x68????\x64\xA1????\x50\x64\x89\x25????\x81\xEC????\x53\x55\x8B\xAC\x24????\x56\x8B\xB4\x24????\x57\x8D\x4C\x24\x20"
rx2 = re.compile(b"".join(b"." if c == ord("?") else re.escape(bytes([c])) for c in pat2), re.S)
m2 = list(rx2.finditer(data))
print("wsc matches", len(m2))
wsc = off2va(m2[0].start())
print("SetWscScheme static", hex(wsc))

# runtime values from the log, last session
rt_sbs = 0xB94840
rt_wsc = 0xB93890
print("delta via SetBuiltinScheme", hex(rt_sbs - sbs), "via SetWscScheme", hex(rt_wsc - wsc))
delta = rt_sbs - sbs
for caller in (0xB7491A, 0xB415EC, 0xB4157E, 0xBA89D0):
    st = caller - delta
    o2 = va2off(st - 5)
    b = data[o2:o2 + 5]
    tgt = None
    if b[0] == 0xE8:
        tgt = st + struct.unpack_from("<i", b, 1)[0]
    print("runtime caller", hex(caller), "-> static", hex(st), "bytes", b.hex(), "call target", hex(tgt) if tgt else None,
          "== SetBuiltinScheme" if tgt == sbs else ("== SetWscScheme" if tgt == wsc else ""))

# every call site of SetBuiltinScheme in the exe
sites = []
txt = [s for s in secs if s[0] == ".text"][0]
tstart = txt[3]
tend = tstart + txt[4]
for i in range(tstart, tend - 5):
    if data[i] == 0xE8:
        va = off2va(i)
        tgt = va + 5 + struct.unpack_from("<i", data, i + 1)[0]
        if tgt == sbs:
            sites.append(va + 5)
print("SetBuiltinScheme return addresses (static):", [hex(x) for x in sites])
