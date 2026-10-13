return function(R, E, H, L)
  local K = R.K
  L("PROBE Objs.Count=%s Water=%s", tostring(K.Env.Objs.Count), tostring(K.Env.Water))
  local h = E.pseudoOfClass and E.pseudoOfClass("CHelibody")
  L("PROBE helibody=%s", tostring(h))
end
