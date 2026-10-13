p = r'C:\Users\Admin\pxrt_dev\pxrt_e_classes.lua'
s = open(p, encoding='utf-8', newline='').read()
assert '\r\n' not in s
old = """  CW.RenderWorm = function() return 0 end
  CW.RenderCrosshair = function() return 0 end
"""
new = """  CW.RenderWorm = function() return 0 end
  CW.RenderCrosshair = function() return 0 end
  CW.RenderRope = function() return 0 end
  CW.RenderRopeShot = function() return 0 end
  CW.IsMoving = function(self)
    local a = addrOf(self)
    if a == 0 then return 0 end
    return (rd(a + 0x90) ~= 0 or rd(a + 0x94) ~= 0) and 1 or 0
  end
  CW.ResetWeapon = function() return 0 end
  CW.SelectWeapon = function() return 0 end
  CW.SetAnimEx = function() return 0 end
  CW.GetName = function(self)
    local a = addrOf(self)
    if a == 0 then return "" end
    return E.F.GetTeamName(rd(a + 0xFC))
  end
  CW.SetName = function() return 0 end
  -- GetWormAnimState(&x, &y, &sprite, &frame): what RenderWorm would draw (WA's GetWormDrawParams 0x512E80)
  local function setRef(r, v) if type(r) == "table" and R.isref(r) then r.v = v end end
  CW.GetWormAnimState = function(self, super, x, y, sprite, frame)
    local a = addrOf(self)
    if a == 0 then return 0 end
    local px, py, spr, ph = rd(a + 0x84) / 65536.0, rd(a + 0x88) / 65536.0, 0, 0
    if callRegs and E.acquireBuf then
      local b = E.acquireBuf(16)
      if b ~= 0 then
        local ok = pcall(callRegs, 0x512E80, { eax = b, esi = a }, b + 4, b + 8, b + 12)
        if ok then
          px, py = rd(b + 4) / 65536.0, rd(b + 8) / 65536.0
          spr, ph = rd(b), rd(b + 12)
        end
        E.releaseBuf(16, b)
      end
    end
    setRef(x, px); setRef(y, py); setRef(sprite, spr); setRef(frame, ph)
    return 0
  end
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
