"""Map stack dwords in WA's ERRORLOG.TXT to module+offset. Usage: py -3.10 errlog_stack.py [ERRORLOG.TXT] [max]"""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\ERRORLOG.TXT'
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 120
t = open(path, encoding='latin-1').read()
mods = []
for m in re.finditer(r'Module \d+\r?\n(.+?)\r?\nImage Base: 0x([0-9a-f]+)\s+Image Size: 0x([0-9a-f]+)', t):
    mods.append((int(m.group(2), 16), int(m.group(3), 16), m.group(1).strip()))


def find(a):
    for b, s, n in mods:
        if b <= a < b + s:
            return n.split('\\')[-1], a - b, b
    return None


print(t.split('\n\n')[0])
for b, s, n in mods:
    low = n.lower()
    if 'jelly' in low or 'lua' in low or low.endswith('wa.exe') or 'wk' in low.split('\\')[-1]:
        print('MOD', hex(b), hex(s), n)
n = 0
for addr, words in re.findall(r'^(0x[0-9a-f]+): ((?:[0-9a-f]{8} ){4})', t, re.M):
    base = int(addr, 16)
    for i, w in enumerate(words.split()):
        a = int(w, 16)
        r = find(a)
        if r and a > 0x10000:
            name, off, mb = r
            extra = ''
            if name.lower() == 'wa.exe':
                extra = ' static=' + hex(0x400000 + off)
            print(hex(base + 4 * i), w, name, hex(off) + extra)
            n += 1
            if n >= limit:
                sys.exit()
