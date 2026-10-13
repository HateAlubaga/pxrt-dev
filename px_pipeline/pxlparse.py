"""Proper PXL parser: 02 01 <u16> 00 <u32 count> then entries <u8 type> <u32 namelen> name <u32 len> body.
Writes script entries (type 4) concatenated to pxl/<lib>.pxc (overwrites heuristic output)."""
import os, struct, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))


def parse(b):
    assert b[0] == 2, b[:8]
    cnt = struct.unpack_from("<I", b, 5)[0]
    p = 9
    ents = []
    while p < len(b) and len(ents) < 10000:
        t = b[p]
        nl = struct.unpack_from("<I", b, p + 1)[0]
        if nl > 4096:
            break
        name = b[p + 5:p + 5 + nl].decode("latin-1")
        ln = struct.unpack_from("<I", b, p + 5 + nl)[0]
        body = b[p + 9 + nl:p + 9 + nl + ln]
        ents.append((t, name, body))
        p = p + 9 + nl + ln
    return cnt, ents, p


if __name__ == "__main__":
    for fn in sys.argv[1:] or glob.glob(os.path.join(HERE, "pxl", "*.pxl")):
        b = open(fn, "rb").read()
        cnt, ents, p = parse(b)
        nm = os.path.splitext(os.path.basename(fn))[0]
        print(nm, "count", cnt, "parsed", len(ents), "end", p, "/", len(b), [(t, n, len(x)) for t, n, x in ents])
        with open(os.path.join(HERE, "pxl", nm + ".pxc"), "w", encoding="utf-8", newline="\n") as f:
            for t, n, body in ents:
                if t == 4:
                    f.write("//==== script %s ====\n" % n)
                    f.write(body.decode("latin-1").replace("\r\n", "\n"))
                    f.write("\n")
