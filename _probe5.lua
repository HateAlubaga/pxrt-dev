return function(R, E, H, L)
  local G = R.libs.utils.G
  local hx, hy = 0, 0
  local rx = R.ref(function() return hx end, function(v) hx = v end)
  local ry = R.ref(function() return hy end, function(v) hy = v end)
  local o
  for _, x in ipairs(E.pseudoList) do if rawget(x, "__cls") == "CHelibody" then o = x end end
  L("MASK_PIXEL=%s", tostring(G.MASK_PIXEL))
  local hit = G.TraceLine(o, 340, 460, 340, 2053, -1, rx, ry)
  L("TraceLine hit=%s cls=%s hx=%s hy=%s", tostring(hit), tostring(type(hit) == "table" and rawget(hit, "__cls")), tostring(hx), tostring(hy))
  L("worldObjs=%d", #E.worldObjs())
  for i, w in ipairs(E.worldObjs()) do
    L("  w[%d] cls=%s pos=(%s,%s) ClType=%s Layer=%s mask=%s", i, tostring(rawget(w, "__cls")), tostring(w.PosX), tostring(w.PosY), tostring(w.ClType), tostring(w.Layer), tostring(type(w.ColMask)))
  end
  L("land(340,1600)=%s land(340,1000)=%s", tostring(E.landSolid(340, 1600)), tostring(E.landSolid(340, 1000)))
end
