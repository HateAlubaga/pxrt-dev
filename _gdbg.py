p = r'C:\Users\Admin\pxrt_dev\base_B\pxrt.lua'
s = open(p, encoding='utf-8').read()
old = """      local v, o = resolveG(parentList, k)
"""
new = """      local v, o = resolveG(parentList, k)
      local w
      for i = 1, #parentList do
        w = rawget(parentList[i], k)
        if w == nil then w = parentList[i][k] end
        if w ~= nil then break end
      end
      if w == nil then w = engineG[k] end
      if w ~= v then __gs.bad = (__gs.bad or "") .. tostring(k) .. ":" .. tostring(v) .. "/" .. tostring(w) .. " " end
"""
assert s.count(old) == 1
s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
