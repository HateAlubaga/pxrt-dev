p = r'C:\Users\Admin\pxrt_dev\pxrt_core.lua'
s = open(p, encoding='utf-8').read()
old = """local function loadLib(name)
  local lib = libs[name]
  if lib then return lib end
"""
new = """local loadedPackages = {}
local function loadLib(name)
  local lib = libs[name] or loadedPackages[name]
  if lib then return lib end
"""
assert old in s
s = s.replace(old, new)
old = """local loadedPackages = {}
-- R.loadPackage"""
new = """-- R.loadPackage"""
assert old in s
s = s.replace(old, new)
old = """  if loadedPackages[name] then return loadedPackages[name] end
  local parents = {}"""
new = """  if loadedPackages[name] then return loadedPackages[name] end
  if libs[name] then return libs[name] end
  local parents = {}"""
assert old in s
s = s.replace(old, new)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
