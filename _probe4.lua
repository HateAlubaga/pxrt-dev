return function(R, E, H, L)
  local o
  for _, x in ipairs(E.pseudoList) do if rawget(x, "__cls") == "CHelibody" then o = x end end
  if not o then L("no helibody") return end
  for i = 1, 120 do
    local ok, e = pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 2, 0, 0)
    if not ok then L("frame %d FAILED %s", i, tostring(e)) break end
    if i % 10 == 0 or i < 8 then
      L("f%d pos=(%.3f,%.3f) sp=(%.4f,%.4f) ticker=%s stopped=%s", i, rawget(o, "PosX"), rawget(o, "PosY"), rawget(o, "SpX"), rawget(o, "SpY"),
        tostring(rawget(o, "animTicker")), tostring(rawget(o, "Stopped")))
    end
  end
end
