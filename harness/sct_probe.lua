-- SetCurrentTeam probe: switch CurTeam on the mock turn game and check the script chain runs once per change
return function(R, E, H, L)
  local n = 0
  local inv = R.invoke
  R.invoke = function(o, cls, m, ...)
    if m == "SetCurrentTeam" then n = n + 1 end
    return inv(o, cls, m, ...)
  end
  for _, team in ipairs({ 1, 1, 2, 2, 1 }) do
    writeMemInt(H.TG + 0x12C, team)
    H.sendMessage("CTaskTurnGame", H.TG, nil, 2, 0, 0)
  end
  R.invoke = inv
  L("SetCurrentTeam calls=%d (want 3 when a script overrides it)", n)
end
