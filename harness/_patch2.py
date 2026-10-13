p = r'C:\Users\Admin\pxrt_dev\harness\bench.lua'
s = open(p, encoding='utf-8').read()
old = '  local t = src and chunkLines[src]\n'
new = '''  local t = src and chunkLines[src]
  if src and not t then
    for nm, lines in pairs(chunkLines) do
      if nm:sub(-#src - 1) == "/" .. src then t = lines break end
    end
  end
'''
assert old in s
open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))
print('ok')
