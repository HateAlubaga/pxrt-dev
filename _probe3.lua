return function(R, E, H, L)
  local o
  for _, x in ipairs(E.pseudoList) do if rawget(x, "__cls") == "CHelibody" then o = x end end
  if not o then L("no helibody") return end
  local function st(tag)
    L("%s pos=(%.3f,%.3f) sp=(%.4f,%.4f) mat=%s col=%s stopped=%s ticker=%s landed=%s ctrl=%s stepped=%s", tag,
      rawget(o, "PosX"), rawget(o, "PosY"), rawget(o, "SpX"), rawget(o, "SpY"), tostring(rawget(o, "IsMaterial")),
      tostring(rawget(o, "ColGroup")), tostring(rawget(o, "Stopped")), tostring(rawget(o, "animTicker")),
      tostring(rawget(o, "landed")), tostring(rawget(o, "ctrlmode")), tostring(rawget(o, "__stepped")))
  end
  st("before")
  for i = 1, 5 do
    local ok, e = pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 2, 0, 0)
    L("frame %d ok=%s %s", i, tostring(ok), tostring(e))
    st("after")
  end
  local ok, e = pcall(E.softStep, o)
  L("manual softStep ok=%s %s", tostring(ok), tostring(e))
  st("manual")
end
