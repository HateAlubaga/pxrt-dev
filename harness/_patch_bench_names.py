p = r'C:\Users\Admin\pxrt_dev\harness\bench.lua'
s = open(p, encoding='utf-8').read()
old = 'H.build({ weapons'
new = '''local chunkLines = {}
do
  local oload = load
  _G.load = function(chunk, name, ...)
    if type(chunk) == "string" and type(name) == "string" and name:sub(1, 1) == "=" and #chunk > 200 then
      local t = {}
      for l in (chunk .. "\\n"):gmatch("(.-)\\n") do t[#t + 1] = l end
      chunkLines[name:sub(2)] = t
    end
    return oload(chunk, name, ...)
  end
end
local function nameOf(key)
  -- key "short_src:linedefined" -> PX function name taken from the comment line above the definition
  local src, ln = key:match("^(.*):(%d+)$")
  local t = src and chunkLines[src]
  if t then
    local c = t[tonumber(ln) - 1]
    if c and c:sub(1, 2) == "--" then return key .. "  " .. c:sub(4, 80) end
  end
  return key
end
H.build({ weapons'''
assert old in s and 'nameOf' not in s
s = s.replace(old, new, 1)
s = s.replace('cc[i][2] / frames, cc[i][1]) end', 'cc[i][2] / frames, nameOf(cc[i][1])) end')
s = s.replace('100 * ic[i][2] / math.max(1, nsamples), ic[i][1]) end', '100 * ic[i][2] / math.max(1, nsamples), nameOf(ic[i][1])) end')
s = s.replace('100 * sf[i][2] / math.max(1, nsamples), sf[i][1]) end', '100 * sf[i][2] / math.max(1, nsamples), nameOf(sf[i][1])) end')
s = s.replace('math.min(30, #cc)', 'math.min(45, #cc)').replace('math.min(45, #ic)', 'math.min(60, #ic)').replace('math.min(40, #sf)', 'math.min(50, #sf)')
open(p, 'w', encoding='utf-8').write(s)
print('ok', s.count('nameOf'))
