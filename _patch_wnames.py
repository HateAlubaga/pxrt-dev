p = r'C:\Users\Admin\pxrt_dev\pxrt_e_classes.lua'
s = open(p, encoding='utf-8').read()
old = '''  local function idByName(name)
    local id = -1
    if weaponIdByName then
      local ok, v = pcall(weaponIdByName, name)
      if ok and type(v) == "number" then id = v end
    end
    if id < 0 then id = vanilla[normName(name)] or -1 end
    return id
  end'''
new = '''  -- px2jelly registered weapons under names made from the .bin file name ("Balloon W"); scripts test ProjectX's own
  -- names ("Hot Air Balloon"). pxrt_wnames (pxwnames.py) maps registered -> ProjectX name; scripts see the latter.
  local okW, WN = pcall(require, "pxrt_wnames")
  if not okW or type(WN) ~= "table" then WN = {} end
  local pxFromReg, regFromPx = {}, {}
  do
    local keys = {}
    for k in pairs(WN) do keys[#keys + 1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do
      local px = WN[k]
      pxFromReg[k] = px
      local n = normName(px)
      if not regFromPx[n] then regFromPx[n] = k end
    end
  end
  local function hostId(name)
    if not weaponIdByName then return -1 end
    local ok, v = pcall(weaponIdByName, name)
    if ok and type(v) == "number" then return v end
    return -1
  end
  local function idByName(name)
    local id = hostId(name)
    if id < 0 then
      local reg = regFromPx[normName(name)]
      if reg then id = hostId(reg) end
    end
    if id < 0 then id = vanilla[normName(name)] or -1 end
    return id
  end'''
assert s.count(old) == 1
s = s.replace(old, new)
old2 = '''    local ok, s = pcall(readMemString, p, 64)
    return ok and s or nil
  end'''
new2 = '''    local ok, s = pcall(readMemString, p, 64)
    if not ok or not s then return nil end
    return pxFromReg[s] or s
  end'''
assert s.count(old2) == 1
s = s.replace(old2, new2)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
