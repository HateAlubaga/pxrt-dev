return function(R, E, H, L)
  local function dump(tag)
    local n = 0
    for _, o in ipairs(E.pseudoList or {}) do
      n = n + 1
      local cls = rawget(o, "__cls")
      if rawget(o, "__soft") then
        L("%s pseudo[%d] %s pos=(%.2f,%.2f) sp=(%.3f,%.3f) stopped=%s mid=%s gf=%s layer=%s",
          tag, n, tostring(cls), tonumber(rawget(o, "PosX")) or -1, tonumber(rawget(o, "PosY")) or -1,
          tonumber(rawget(o, "SpX")) or 0, tonumber(rawget(o, "SpY")) or 0, tostring(rawget(o, "Stopped")),
          tostring(rawget(o, "InMidAir")), tostring(rawget(o, "GravityFactor")), tostring(rawget(o, "Layer")))
      end
    end
    L("%s pseudo total=%d world=%d", tag, n, #E.worldObjs())
  end
  dump("f0")
  for f = 1, 100 do pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 2, 0, 0) end
  dump("f100")
  for f = 1, 600 do pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 2, 0, 0) end
  dump("f700")
end
