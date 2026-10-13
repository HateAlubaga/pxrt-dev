"""Translate code offsets in an old wkJellyWorm.dll (no symbols) to function names
using a fresh build of nearly the same source that has a linker .map file.

Usage: py -3.10 re/symxlate.py OLD.dll NEW.dll NEW.map off1 off2 ...   (offsets = RVA hex, e.g. 0x2812bb)

For each offset it takes byte windows ending at the offset in OLD.dll (relocated absolute
addresses differ between builds, so several short windows are tried), finds a unique match
in NEW.dll, and prints the containing symbol from NEW.map.
"""
import bisect
import re
import sys

import pefile


def load(path):
    pe = pefile.PE(path, fast_load=True)
    img = pe.get_memory_mapped_image()
    text = next(s for s in pe.sections if s.Name.rstrip(b'\0') == b'.text')
    return img, text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize


def load_map(path):
    syms = []
    pref = None
    for line in open(path, encoding='latin-1'):
        m = re.match(r'\s*Preferred load address is ([0-9a-fA-F]+)', line)
        if m:
            pref = int(m.group(1), 16)
        m = re.match(r'\s*[0-9a-fA-F]{4}:[0-9a-fA-F]{8}\s+(\S+)\s+([0-9a-fA-F]{8})\s+[f ]?\s*(.*)', line)
        if m and pref is not None:
            va = int(m.group(2), 16)
            if va >= pref:
                syms.append((va - pref, m.group(1), m.group(3).strip()))
    syms.sort()
    return syms


def sym_at(syms, keys, rva):
    i = bisect.bisect_right(keys, rva) - 1
    if i < 0:
        return '?'
    r, name, obj = syms[i]
    return '%s+0x%x (%s)' % (name, rva - r, obj)


def main():
    old_path, new_path, map_path = sys.argv[1:4]
    offs = [int(x, 16) for x in sys.argv[4:]]
    old, _, _ = load(old_path)
    new, t0, t1 = load(new_path)
    syms = load_map(map_path)
    keys = [s[0] for s in syms]
    text = new[t0:t1]
    for off in offs:
        found = None
        for before, after in ((48, 16), (32, 8), (24, 8), (16, 8), (12, 4), (8, 8), (6, 10), (0, 16), (16, 0), (10, 0)):
            pat = old[off - before:off + after]
            hits = [m.start() for m in re.finditer(re.escape(pat), text)]
            if len(hits) == 1:
                found = t0 + hits[0] + before
                break
        if found is None:
            print('0x%x: no unique match' % off)
        else:
            print('0x%x -> new 0x%x  %s' % (off, found, sym_at(syms, keys, found)))


if __name__ == '__main__':
    main()
