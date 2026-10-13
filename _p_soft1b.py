import re
p = r'C:\Users\Admin\pxrt_dev\pxrt_e_terrain.lua'
s = open(p, encoding='utf-8', newline='').read()
old = "  E.landSolid = solid\n"
new = """  E.landSolid = solid

  -- fast probe for many integer pixels in a row (caches the bitmap pointers once)
  function E.landProbe()
    local p = P()
    local bm = p ~= 0 and rdU(p + 0x914) or 0
    if bm == 0 then return function() return false end end
    local data, stride = rdU(bm + 8), rd(bm + 0x10)
    local x0, y0, x1, y1 = rd(bm + 0x1C), rd(bm + 0x20), rd(bm + 0x24), rd(bm + 0x28)
    return function(x, y)
      if x < x0 or x >= x1 or y < y0 or y >= y1 then return false end
      local b = readMemU8(data + y * stride + (x >> 3))
      return ((b >> (x & 7)) & 1) == 1
    end
  end
"""
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)

p = r'C:\Users\Admin\pxrt_dev\pxrt_core.lua'
s = open(p, encoding='utf-8', newline='').read()
old = "local libs = {}\nlocal engineG = {}\n"
new = "local libs = {}\nR.libs = libs\nlocal engineG = {}\n"
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)

p = r'C:\Users\Admin\pxrt_dev\pxrt_engine.lua'
s = open(p, encoding='utf-8', newline='').read()
old = '"pxrt_e_terrain", "pxrt_e_pseudo", "pxrt_e_hooks" }'
new = '"pxrt_e_terrain", "pxrt_e_pseudo", "pxrt_e_soft", "pxrt_e_hooks" }'
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)

p = r'C:\Users\Admin\pxrt_dev\harness\harness.py'
s = open(p, encoding='utf-8', newline='').read()
old = "'pxrt_e_classes.lua', 'pxrt_e_terrain.lua', 'pxrt_e_pseudo.lua', 'pxrt_e_hooks.lua']"
new = "'pxrt_e_classes.lua', 'pxrt_e_terrain.lua', 'pxrt_e_pseudo.lua', 'pxrt_e_soft.lua', 'pxrt_e_hooks.lua']"
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
