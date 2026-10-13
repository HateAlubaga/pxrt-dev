-- lifecycle_probe.lua (HARNESS_PROBE): engine-object constructor chains through the host birth log, address reuse,
-- objects created inside FireWeapon, GG.queue2 -> M_PXMESSAGE, CMine::Explosion. Needs a package that loads utils.
return function(R, E, H, L)
  local fails = 0
  local function check(c, what)
    if c then L("ok   %s", what) else fails = fails + 1; L("FAIL %s", what) end
  end
  local K = R.K
  local function frame() H.sendMessage("CTaskTurnGame", H.TG, nil, K.M_FRAME, 0, 0) end
  L("birth log %s, CTaskMine hooks %d, ctor overrides: CMine %d, CMissile %d", tostring(type(taskBirthSeq) == "function"),
    #H.vt.CTaskMine.vtable8, #R.getClass("CMine").ctorOv, #R.getClass("CMissile").ctorOv)

  -- 1. a mine WA creates on its own: its script constructor runs when Lua first sees it
  local c0 = E.lifeStats.ctors
  local m = H.newTask(8, H.worms[1])
  writeMemInt(m + 0x84, 500 * 65536); writeMemInt(m + 0x88, 600 * 65536)
  frame()
  for _ = 1, 3 do H.sendMessage("CTaskMine", m, H.TG, K.M_FRAME, 0, 0) end
  local mp = E.pins[m]
  local mo = mp and mp.o
  check(mo ~= nil, "mine pinned")
  check(mo and mo.autoDestroyTimer == -1, "mine ctor ran (autoDestroyTimer " .. tostring(mo and mo.autoDestroyTimer) .. ")")
  check(E.lifeStats.ctors - c0 == 1, "one ctor run (" .. (E.lifeStats.ctors - c0) .. ")")
  if not mo then L("lifecycle probe: %d failed", fails) return end

  -- 2. CMine::Explosion: autoDestroyTimer reaching 0 blows the mine up through WA's explosion
  local fnExp = E.WA_EXPLOSION()
  local n0 = #H.calls
  mo.autoDestroyTimer = 1
  H.sendMessage("CTaskMine", m, H.TG, K.M_FRAME, 0, 0)
  H.sendMessage("CTaskMine", m, H.TG, K.M_FRAME, 0, 0)
  local exploded = false
  for i = n0 + 1, #H.calls do
    if H.calls[i][1] == "callRegs" and H.calls[i][2] == fnExp then exploded = true end
  end
  check(exploded, "timed mine explodes")

  -- 3. WA reuses the mine's memory for a missile: the dead mine's script state must not leak into it
  mo.sentinel = 4242
  H.freeTask(m)
  local m2 = H.newTask(11, H.worms[1], m)
  frame()
  local p2 = E.proxyAt(m2)
  check(rawget(p2, "__cls") == "CMissile", "reborn address has the new class (" .. tostring(rawget(p2, "__cls")) .. ")")
  check(rawget(p2, "sentinel") == nil, "dead object's script fields are gone")

  -- 4. FireWeapon: the missile WA creates runs its ctor chain while u_lweap is set (utils: weap = u_lweap)
  local fw = E.WA_FIREWEAPON()
  local fired = {}
  local cr = callRegs
  callRegs = function(addr, regs, ...)
    if addr == fw then
      local a = H.newTask(11, H.worms[1])
      memCopy(a + 0x2C8, regs.eax + 0x3C, 0x178)
      fired[#fired + 1] = a
    end
    return cr(addr, regs, ...)
  end
  local w = H.worms[1]
  H.setWormWeapon(w, 0)
  local sd = memAlloc(0x30)
  writeMemInt(sd + 0, 1); writeMemInt(sd + 4, 1)
  local okf, ef = pcall(H.fire, w, H.WTAB, sd)
  callRegs = cr
  check(okf, "fire ran (" .. tostring(ef) .. ")")
  check(#fired == 1, "FireWeapon reached WA (" .. #fired .. " missiles)")
  local fp = fired[1] and E.pins[fired[1]]
  check(fp ~= nil, "fired missile constructed")
  local weap = fp and rawget(fp.o, "weap")
  check(type(weap) == "table", "missile.weap is the fired weapon (" .. type(weap) .. ")")

  -- 5. GG.queue2: AddPXMessage reaches CTurnGame::Message as M_PXMESSAGE on the next frame, once
  local seen = {}
  local tg = R.getClass("CTurnGame")
  tg.overrides.Message = tg.overrides.Message or {}
  table.insert(tg.overrides.Message, function(self, super, sender, Type, MSize, MData)
    if R.ti(Type) == K.M_PXMESSAGE then seen[#seen + 1] = { MData.params[0], MData.params[1], MData.params[2] } end
    return super(sender, Type, MSize, MData)
  end)
  R.invalidate()
  local q = E.ggProxy.queue2
  q.AddPXMessage(q, 77, 5, 1)
  check(#seen == 0, "not delivered before the frame")
  frame()
  check(#seen == 1 and seen[1][1] == 77 and seen[1][2] == 5 and seen[1][3] == 1,
    "M_PXMESSAGE delivered (" .. #seen .. (seen[1] and (": " .. table.concat(seen[1], ",")) or "") .. ")")
  frame()
  check(#seen == 1, "delivered once")
  table.remove(tg.overrides.Message)
  R.invalidate()

  L("lifecycle probe: %d failed", fails)
end
