-- HARNESS_PROBE: force darkness2016's darkness on and run its custom render a few times (quad path + cost)
return function(R, E, H, L)
  local u = R.loadedPackages and R.loadedPackages["darkness2016"]
  if not u then L("probe: darkness2016 not loaded") return end
  local dc = u.G.darkControl
  if type(dc) ~= "table" then L("probe: no darkControl") return end
  dc.enabled = 1
  L("probe: initialized=%s nBlX=%s nBlY=%s bSize=%s", tostring(dc.initialized), tostring(dc.nBlX), tostring(dc.nBlY), tostring(dc.bSize))
  local before = H.quadN or 0
  local t0 = os.clock()
  for _ = 1, 5 do
    local ok, err = pcall(R.mc, dc, "Queue")
    if not ok then L("probe: Queue failed: %s", tostring(err)) break end
  end
  L("probe: darkness quads %d in 5 frames, %.2f ms/frame", (H.quadN or 0) - before, (os.clock() - t0) * 200)
end
