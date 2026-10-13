-- HARNESS_PROBE: darkness2016 custom render cost split (script vs RenderQuad batching)
return function(R, E, H, L)
  local u = R.loadedPackages and R.loadedPackages["darkness2016"]
  local dc = u and u.G.darkControl
  if type(dc) ~= "table" then L("probe: no darkControl") return end
  dc.enabled = 1
  pcall(R.mc, dc, "Queue")
  local function run(tag)
    local t0 = os.clock()
    for _ = 1, 5 do pcall(R.mc, dc, "Queue") end
    L("probe: %s %.2f ms/frame", tag, (os.clock() - t0) * 200)
  end
  run("full")
  local rq = R.F.RenderQuad
  R.F.RenderQuad = function() return 0 end
  run("RenderQuad no-op")
  R.F.RenderQuad = rq
end
