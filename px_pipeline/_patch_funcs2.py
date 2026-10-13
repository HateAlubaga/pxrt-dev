p = r'C:\Users\Admin\pxrt_dev\pxrt_e_funcs.lua'
s = open(p, encoding='utf-8', newline='').read()
assert '\r\n' not in s
old = """  BC.CFireDesc = inert("CFireDesc")
"""
new = """  BC.CFireDesc = inert("CFireDesc")
  -- CFilter(parent, type): message filter node. Children keep receiving everything (pseudo dispatch), so it is inert.
  BC.CFilter = inert("CFilter")
  R.natives.CFilter = {
    Allow = function() return 0 end, Forbid = function() return 0 end,
    AllowAll = function() return 0 end, ForbidAll = function() return 0 end,
  }
  -- utils_hack type-punning (PCMessageData_intP & co.): the pointer is an absolute WA address, view it in place
  BF.PCMessageData_intP = function(addr)
    local o = E.msgDataAt(ti(addr))
    return o or 0
  end
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
