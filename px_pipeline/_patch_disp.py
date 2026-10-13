p = r'C:\Users\Admin\pxrt_dev\pxrt_e_game.lua'
s = open(p, encoding='utf-8', newline='').read()
assert '\r\n' not in s
old = """  -- GameState proxy: Tick, level size, selection, Info, env
  local gsFields = {
"""
new = """  -- K.GS.Disp: display object. Drawing calls are no-ops (the engine draws via sprite overrides); sizes are plausible.
  local dispNoop = function() return 0 end
  local dispFns = {
    DrawText = true, DrawTextEx = true, DrawLine = true, DrawRect = true, FillRect = true, Rect = true, HLine = true,
    VLine = true, DrawBitmap = true, Draw = true, SetClip = true, ResetClip = true, SetColor = true, Flush = true,
    DrawSprite = true, DrawCircle = true, Fill = true, SetPixel = true,
  }
  local dispVals = { xRes = 1280, yRes = 720, halfX = 640, halfY = 360, ViewX = 0, ViewY = 0, ViewSX = 1280, ViewSY = 720, nSurfaces = 0 }
  E.dispProxy = setmetatable({ __cls = "CDisplay" }, {
    __index = function(t, k)
      if dispFns[k] then return dispNoop end
      local v = dispVals[k]
      if v ~= nil then return v end
      return 0
    end,
    __newindex = function() end,
  })

  -- GameState proxy: Tick, level size, selection, Info, env
  local gsFields = {
    Disp = function() return E.dispProxy end,
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)

p = r'C:\Users\Admin\pxrt_dev\pxrt_e_funcs.lua'
s = open(p, encoding='utf-8', newline='').read()
old = """  BC.CQuad = inert("CQuad")
"""
new = """  BC.CQuad = inert("CQuad")
  -- HUD text widget: drawn by nothing (no Lua text API for per-widget text); keeps scripts running
  BC.CGUIText = inert("CGUIText")
  R.natives.CGUIText = {
    SetText = function() return 0 end, Draw = function() return 0 end, Render = function() return 0 end,
    SetColor = function() return 0 end, SetPos = function() return 0 end, SetAlign = function() return 0 end,
    SetVisible = function() return 0 end, Show = function() return 0 end, Hide = function() return 0 end,
    SetFont = function() return 0 end, SetAlpha = function() return 0 end, SetScale = function() return 0 end,
  }
  BC.CFireDesc = inert("CFireDesc")
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
