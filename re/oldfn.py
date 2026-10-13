"""For return addresses in OLD dll: show section, the call instruction before it, and
try to match the enclosing function (found by scanning back to int3 padding) in NEW dll.
Usage: py -3.10 re/oldfn.py OLD.dll NEW.dll NEW.map off..."""
import bisect, re, sys
import pefile, capstone
sys.path.insert(0, __import__('os').path.dirname(__file__))
from symxlate import load, load_map, sym_at
old_path, new_path, map_path = sys.argv[1:4]
pe = pefile.PE(old_path, fast_load=True)
raw = pe.get_memory_mapped_image()
old, _, _ = load(old_path)
new, t0, t1 = load(new_path)
syms = load_map(map_path); keys = [s[0] for s in syms]
text = new[t0:t1]
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
def sec(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            return s.Name.rstrip(b'\0').decode()
    return '?'
for a in sys.argv[4:]:
    off = int(a, 16)
    line = '0x%x [%s]' % (off, sec(off))
    if sec(off) == '.text':
        for back in (5, 6, 2, 3, 7):
            ins = list(md.disasm(raw[off - back:off], 0x10000000 + off - back))
            if ins and ins[-1].address + ins[-1].size == 0x10000000 + off and ins[-1].mnemonic == 'call':
                i = ins[-1]
                line += '  after: %s %s' % (i.mnemonic, i.op_str)
                if i.op_str.startswith('0x'):
                    tgt = int(i.op_str, 16) - 0x10000000
                    pat = old[tgt:tgt + 24]
                    hits = [m.start() for m in re.finditer(re.escape(pat), text)]
                    if len(hits) == 1:
                        line += ' -> ' + sym_at(syms, keys, t0 + hits[0])
                    else:
                        line += ' -> (%d hits)' % len(hits)
                break
        # enclosing function start: scan back for CC CC padding
        st = off
        while st > 0 and not (raw[st - 1] == 0xCC and raw[st - 2] == 0xCC):
            st -= 1
        for n in (40, 32, 24, 16):
            pat = old[st:st + n]
            hits = [m.start() for m in re.finditer(re.escape(pat), text)]
            if len(hits) == 1:
                line += '  | fn@0x%x ~ %s (+0x%x)' % (st, sym_at(syms, keys, t0 + hits[0]), off - st)
                break
        else:
            line += '  | fn@0x%x unmatched' % st
    print(line)
