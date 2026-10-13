return function(R, E, H, L)
  local n = 0
  for _, o in ipairs(E.pseudoList) do
    n = n + 1
    L("pseudo[%d] %s soft=%s pos=(%s,%s) sp=(%s,%s) mat=%s stopped=%s", n, tostring(rawget(o, "__cls")), tostring(rawget(o, "__soft")),
      tostring(rawget(o, "PosX")), tostring(rawget(o, "PosY")), tostring(rawget(o, "SpX")), tostring(rawget(o, "SpY")),
      tostring(rawget(o, "IsMaterial")), tostring(rawget(o, "Stopped")))
  end
  L("pseudo total %d; calls tally:", n)
  for i, c in ipairs(H.calls) do
    if i > 12 then break end
    L("  call %s", tostring(c[1]))
  end
end
