import sys, struct
sys.path.insert(0, r"C:/Users/Admin/pxrt_dev/rs")
f = open(r"C:/Program Files (x86)/by Decepticon/Worms Armageddon/WA.exe","rb").read()
# PE: image base 0x400000; find section containing va
import struct
pe = struct.unpack_from("<I", f, 0x3c)[0]
nsec = struct.unpack_from("<H", f, pe+6)[0]
osz = struct.unpack_from("<H", f, pe+20)[0]
secs=[]
for i in range(nsec):
    o = pe+24+osz+40*i
    vs, va, rs, rp = struct.unpack_from("<IIII", f, o+8)
    secs.append((va, vs, rp, rs))
def rd(va, n):
    rva = va-0x400000
    for (a, vs, rp, rs) in secs:
        if a <= rva < a+max(vs, rs):
            return f[rp+rva-a: rp+rva-a+n]
for a in [int(x,16) for x in sys.argv[2:]]:
    n = int(sys.argv[1])
    d = rd(a, n*4)
    print(hex(a), [hex(x) for x in struct.unpack("<%dI"%n, d)])
