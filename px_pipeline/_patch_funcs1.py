p = r'C:\Users\Admin\pxrt_dev\pxrt_e_funcs.lua'
s = open(p, encoding='utf-8', newline='').read()
assert '\r\n' not in s
old = """  F.SetLayerOverride = function() return 0 end
"""
new = """  F.SetLayerOverride = function() return 0 end
  -- custom (script-to-script) message ids: unique, above the engine range
  E.nextPXMessage = E.nextPXMessage or 0x2000
  F.RegisterPXMessage = function()
    local m = E.nextPXMessage
    E.nextPXMessage = m + 1
    return m
  end
  -- PRegister/PUnregister: engine keeps the referenced object pointer valid; the runtime GC does that already
  F.PRegister = function() return 0 end
  F.PUnregister = function() return 0 end
  F.SetPitch = function() return 0 end
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
