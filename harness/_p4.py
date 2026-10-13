p = r'C:\Users\Admin\pxrt_dev\harness\run.lua'
s = open(p, encoding='utf-8').read()
old = '    for i = 1, #line do traceH = (traceH * 33 + line:byte(i)) % 4294967296 end\n'
new = '''    local lh = 5381
    for i = 1, #line do lh = (lh * 33 + line:byte(i)) % 4294967296 end
    traceH = (traceH + lh) % 4294967296     -- order-insensitive: pairs() order may differ between runs
'''
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
