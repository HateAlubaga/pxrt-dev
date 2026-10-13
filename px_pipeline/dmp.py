import sys, struct, os
from minidump.minidumpfile import MinidumpFile
m = MinidumpFile.parse(sys.argv[1])
e = m.exception.exception_records[0]
er = e.ExceptionRecord
addr = er.ExceptionAddress
print('code', er.ExceptionCode, 'addr', hex(addr), 'info', [hex(x) for x in er.ExceptionInformation[:er.NumberParameters]])
mods = [(md.baseaddress, md.size, os.path.basename(md.name)) for md in m.modules.modules]
def where(v):
    for b, s, n in mods:
        if b <= v < b + s:
            return '%s+%x' % (n, v - b)
    return None
print('fault in', where(addr))
for b, s, n in mods:
    if n.lower() in ('wa.exe', 'wkjellyworm.dll'):
        print(n, hex(b), hex(s))
r = m.get_reader()
for t in m.threads.threads:
    if t.ThreadId == e.ThreadId:
        ctx = t.ContextObject
        regs = {k: getattr(ctx, k) for k in ['Eax', 'Ebx', 'Ecx', 'Edx', 'Esi', 'Edi', 'Ebp', 'Esp', 'Eip']}
        print({k: hex(v) for k, v in regs.items()})
        esp = ctx.Esp
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 0x400
        try:
            data = r.read(esp, n)
        except Exception as ex:
            print('stack read fail', ex); data = b''
        for i in range(0, len(data) - 3, 4):
            v = struct.unpack_from('<I', data, i)[0]
            w = where(v)
            if w:
                print(hex(esp + i), hex(v), w)
        try:
            code = r.read(addr - 32, 64)
            print('code bytes', code.hex())
        except Exception as ex:
            print('code read fail', ex)
