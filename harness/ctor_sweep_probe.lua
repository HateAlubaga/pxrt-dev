-- ctor_sweep_probe.lua (HARNESS_PROBE, any package): WA-born objects of every class with script constructors, then
-- every weapon fired again with WA creating a missile inside FireWeapon. Failures surface as pxrt log lines
-- ("ctor chain failed", "Message(...) chain failed", ...), which harness_all aggregates.
return function(R, E, H, L)
  local K = R.K
  local CIDS = { 8, 15, 30, 12, 24, 9, 21, 25, 17, 23, 22, 11 }
  local CT = { [8] = "CTaskMine", [15] = "CTaskCrate", [30] = "CTaskOildrum", [12] = "CTaskArrow", [24] = "CTaskFire",
    [9] = "CTaskCanister", [21] = "CTaskCross", [17] = "CTaskAirStrike", [23] = "CTaskCloud", [11] = "CTaskMissile" }
  local made = {}
  local c0 = E.lifeStats and E.lifeStats.ctors or 0
  for _, cid in ipairs(CIDS) do
    local a = H.newTask(cid, H.worms[1])
    writeMemInt(a + 0x84, 700 * 65536); writeMemInt(a + 0x88, 900 * 65536)
    made[#made + 1] = { a, cid }
  end
  local function frame()
    H.sendMessage("CTaskTurnGame", H.TG, nil, K.M_FRAME, 0, 0)
    for _, m in ipairs(made) do
      local ct = CT[m[2]]
      if ct then H.sendMessage(ct, m[1], H.TG, K.M_FRAME, 0, 0) end
    end
  end
  for _ = 1, 3 do frame() end
  -- Env.Objs walk (what PX scripts do every turn): every object seen, constructed once
  for _ = 1, 2 do
    local n = K.Env.Objs.Count
    for i = 0, n - 1 do local _ = K.Env.Objs.Objs[i] end
  end

  local fw = E.WA_FIREWEAPON()
  local nf = 0
  local cr = callRegs
  callRegs = function(addr, regs, ...)
    if addr == fw then
      local a = H.newTask(11, H.worms[1])
      memCopy(a + 0x2C8, regs.eax + 0x3C, 0x178)
      writeMemInt(a + 0x84, 400 * 65536); writeMemInt(a + 0x88, 500 * 65536)
      made[#made + 1] = { a, 11 }
      nf = nf + 1
    end
    return cr(addr, regs, ...)
  end
  local sd = memAlloc(0x30)
  for _, name in ipairs(SCEN.weapons or {}) do
    local id = weaponIdByName(name)
    if id >= 0 then
      local w = H.worms[1]
      H.setWormWeapon(w, id)
      memFill(sd, 0, 0x30)
      writeMemInt(sd + 0, 1); writeMemInt(sd + 4, 1)
      writeMemInt(sd + 8, 300 * 65536); writeMemInt(sd + 0xC, 400 * 65536)
      local ok, e = pcall(H.fire, w, H.WTAB + id * 0x1D0, sd)
      if not ok then L("ctor sweep: fire %s: %s", name, tostring(e)) end
      frame()
    end
  end
  callRegs = cr
  for _ = 1, 3 do frame() end
  L("ctor sweep: %d objects, %d fired missiles, %d ctor chains run", #made, nf, (E.lifeStats and E.lifeStats.ctors or 0) - c0)
end
