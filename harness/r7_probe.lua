-- r7_probe.lua (HARNESS_PROBE, package utility_balloon): ProjectX weapon names, CWorm::RenderWorm and
-- CSpriteAnim::SetAnimEx hooks, order of vtable8 callbacks other packages register after pxrt hooked the class.
return function(R, E, H, L)
  local fails = 0
  local function check(c, what)
    if c then L("ok   %s", what) else fails = fails + 1; L("FAIL %s", what) end
  end
  local K = R.K
  local worm = H.worms[1]
  local function frame() H.sendMessage("CTaskTurnGame", H.TG, nil, K.M_FRAME, 0, 0) end
  local function callsOf(name, from)
    local out = {}
    for i = from + 1, #H.calls do
      if H.calls[i][1] == name then out[#out + 1] = H.calls[i] end
    end
    return out
  end

  -- 1. registered "Balloon W" answers to the ProjectX name
  -- the mock registers the names scripts test; rename to the name px2jelly gave it in the game
  local id = -1
  for wid, nm in pairs(H.weaponNames) do if nm == "Hot Air Balloon" then id = wid end end
  if id >= 0 then H.setWeapon(id, "Balloon W") end
  check(id >= 0, "balloon weapon registered (id " .. id .. ")")
  local w = E.weaponAt(H.WTAB + id * 0x1D0, worm)
  check(w and w:CheckName("Hot Air Balloon") == 1, "CheckName(\"Hot Air Balloon\")")
  check(w and w:CheckName("Umbrella") == 0, "CheckName(\"Umbrella\") is false")
  check(E.idByName("Hot Air Balloon") == id, "idByName(ProjectX name)")
  check(w and w.NameA == "Hot Air Balloon", "NameA = " .. tostring(w and w.NameA))

  -- 2. hooks installed
  local names = {}
  for _, h in ipairs(H.hooks) do names[h.name] = h end
  check(names.pxrt_RenderWorm ~= nil, "RenderWorm hooked")
  check(names.pxrt_SetAnimEx ~= nil, "SetAnimEx hooked")

  -- 3. no balloon: RenderWorm runs WA's original
  frame()
  local o = E.objectFor(worm, "CWorm")
  local n0 = #H.calls
  H.fireHook("pxrt_RenderWorm", worm)
  check(#callsOf("hookOrig", n0) == 1, "inactive balloon: original worm drawn")

  -- 4. balloon fired: FireFinal sets balloon_active, RenderWorm draws the balloon instead of the worm
  H.setWormWeapon(worm, id)
  R.invoke(o, "CWorm", "FireFinal", w, nil)
  check(o.balloon_active == true or o.balloon_active == 1, "FireFinal: balloon_active = " .. tostring(o.balloon_active))
  n0 = #H.calls
  H.fireHook("pxrt_RenderWorm", worm)
  check(#callsOf("hookOrig", n0) == 0, "active balloon: original worm not drawn")

  -- 5. SetAnimEx: parachute sprites swapped while the balloon is up
  local anim = 0x3A00000
  writeMemU32(worm + 0x368, anim)
  check(R.eq(o.Anim, E.animAt(anim)), "CWorm.Anim is the animator")
  n0 = #H.calls
  H.fireHook("pxrt_SetAnimEx", anim, 287, 0x8000)
  local c = callsOf("hookOrig", n0)
  check(#c == 1 and c[1][3] == anim and c[1][4] == 278 and c[1][5] == 0x8000,
    "SetAnimEx(287) -> original(278, 0x8000): " .. (c[1] and table.concat({ tostring(c[1][4]), tostring(c[1][5]) }, ",") or "none"))
  n0 = #H.calls
  H.fireHook("pxrt_SetAnimEx", anim, 100, 0)
  c = callsOf("hookOrig", n0)
  check(#c == 1 and c[1][4] == 100, "SetAnimEx(100) unchanged")
  -- another object's animator: straight to the original, no sprite swap
  n0 = #H.calls
  H.fireHook("pxrt_SetAnimEx", 0x3B00000, 287, 0x8000)
  c = callsOf("hookOrig", n0)
  check(#c == 1 and c[1][3] == 0x3B00000 and c[1][4] == 287, "SetAnimEx(287) on another animator unchanged")

  -- 6. a vtable8 callback registered after pxrt hooked CWorm runs before WA's handler
  local seen = {}
  CTaskWorm_RegisterCallback_vtable8(function(This, sender, mtype)
    seen[#seen + 1] = { mtype = mtype, origBefore = #H.origCalls }
    return 0
  end)
  local hostCount = #H.vt.CTaskWorm.vtable8
  local o0 = #H.origCalls
  H.sendMessage("CTaskWorm", worm, H.TG, K.M_FRAME, 0, 0)
  check(#seen == 1, "late callback ran (" .. #seen .. ")")
  check(seen[1] and seen[1].origBefore == o0, "late callback ran before WA's handler")
  check(#H.vt.CTaskWorm.vtable8 == hostCount, "late callback not registered with the host")
  L("r7 probe: %d failed", fails)
end
