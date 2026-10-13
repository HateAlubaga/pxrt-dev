p = r'C:\Users\Admin\pxrt_dev\harness\mock_dll.lua'
s = open(p, encoding='utf-8').read()
old = '''  [0x4FB9D0] = "83ec10538b5c24188b83400200008b40240524d900008078",
}'''
new = '''  [0x4FB9D0] = "83ec10538b5c24188b83400200008b40240524d900008078",
  [0x50FCD0] = "83ec10568bf08d442408508d4c2414518d542414528d4424",
  [0x4F5BD0] = "83ec0853568bf18b5e1c83c30181e30f00008079054b83cb",
}'''
assert s.count(old) == 1
s = s.replace(old, new)
old2 = 'function getWormWeaponId(wa) return readMemInt(wa + 0x170) end'
new2 = old2 + '''

-- generic function hooks (LuaNative.cpp hookFunction): H.fireHook(name, ...) plays WA calling the hooked function
H.hooks = {}
function hookFunction(name, addr, spec, fn)
  for id, h in ipairs(H.hooks) do
    if h.name == name then h.fn = fn return id end
  end
  H.hooks[#H.hooks + 1] = { name = name, addr = addr, spec = spec, fn = fn }
  return #H.hooks
end
function callHookOriginal(id, ...)
  local h = H.hooks[id]
  logcall("hookOrig", h and h.name or "?", ...)
  return 0
end
function H.fireHook(name, ...)
  for _, h in ipairs(H.hooks) do
    if h.name == name then return h.fn(...) end
  end
  return nil
end'''
assert s.count(old2) == 1
s = s.replace(old2, new2)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
