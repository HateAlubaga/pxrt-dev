"""Test a structured layout hypothesis for the ProjectX weapon .bin trailer."""
import os, glob, struct, collections

root = r'C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages'


class R:
    def __init__(s, d, p):
        s.d, s.p = d, p

    def u32(s):
        v = struct.unpack_from('<I', s.d, s.p)[0]
        s.p += 4
        return v

    def u8(s):
        v = s.d[s.p]
        s.p += 1
        return v

    def str(s):
        n = s.u32()
        if n > 512:
            raise ValueError('len %d' % n)
        v = s.d[s.p:s.p + n]
        s.p += n
        return v.decode('latin1')


ok = bad = 0
tails = collections.Counter()
mids = collections.Counter()
for f in sorted(glob.glob(os.path.join(root, '*', '*', 'weapons_raw', '*.bin'))):
    d = open(f, 'rb').read()
    r = R(d, 0x1E0)
    try:
        head = r.u32()
        names = [r.str() for _ in range(3)]
        gfx = r.str()
        spr = [r.str() for _ in range(3)]
        mid = (r.u32(), r.u32(), r.u8(), r.u32(), r.u32())
        anims = [r.str() for _ in range(9)]
        rest = d[r.p:]
    except Exception as e:
        bad += 1
        print('FAIL', os.path.relpath(f, root), e)
        continue
    if len(rest) == 4:
        ok += 1
        tails[rest.hex()] += 1
        mids[str(mid)] += 1
    else:
        bad += 1
        print('LEN', os.path.relpath(f, root), len(rest), rest[:40])
print('ok', ok, 'bad', bad)
print(tails.most_common(10))
print(mids.most_common(10))
