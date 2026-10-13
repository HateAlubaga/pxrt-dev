-- pxrt_e_classes: natives of engine classes (CObject, CGObject, CWorm, CTurnGame, CGameState, CGameInfo, CWeapon...)
return function(R, E)
  local rd, wr, rdf, wrf, rdU = E.rd, E.wr, E.rdf, E.wrf, E.rdU
  local okAddr = E.okAddr
  local ti, tf, T, isnull = R.ti, R.tf, R.T, R.isnull
  local log, once = R.log, R.once
  local floor = math.floor
  local type, tostring, rawget, rawset, setmetatable, pairs = type, tostring, rawget, rawset, setmetatable, pairs
  local N = R.natives
  local pc = E.pc
  local function nat(cls) N[cls] = N[cls] or {} return N[cls] end

  local function addrOf(o) return type(o) == "table" and rawget(o, "__a") or 0 end
  E.addrOf = addrOf

  local function vtSlot(addr, off) return rdU(rdU(addr) + off) end
  E.vtSlot = vtSlot

  ---------------------------------------------------------------------
  -- calling WA code
  ---------------------------------------------------------------------
  -- thiscall: callThiscall(fn, this, args...)
  function E.callThis(fn, this, ...)
    E.CW.have = false
    if not callThiscall or not okAddr(fn) then return 0 end
    local ok, r = pcall(callThiscall, fn, this, ...)
    if not ok then once("ct:" .. tostring(r), "pxrt: callThiscall failed: %s", tostring(r)) return 0 end
    return r
  end

  -- Message(sender, type, size, data) through the live vtable (hooks fire)
  function E.sendMessage(target, senderAddr, msg, size, dataAddr)
    if not okAddr(target) then return 0 end
    return E.callThis(vtSlot(target, 8), target, senderAddr or 0, ti(msg), ti(size or 0), dataAddr or 0)
  end

  -- message data blocks for script-originated messages
  local scratchMsg
  local function scratch()
    if not scratchMsg then
      local ok, a = pcall(memAlloc, 1040)
      scratchMsg = (ok and a) or 0
    end
    return scratchMsg
  end

  ---------------------------------------------------------------------
  -- drawing
  ---------------------------------------------------------------------
  function E.drawSprite(z, x, y, sprite, frame, rot, scale)
    local id = E.spriteId(sprite)
    if id <= 0 then return 0 end
    if (rot and tf(rot) ~= 0) or (scale and tf(scale) ~= 1) then
      if E.drawSpriteRot then
        local ok = pcall(E.drawSpriteRot, tf(z), tf(x), tf(y), id, tf(frame), tf(rot or 0), tf(scale or 1))
        if ok then return 0 end
      else
        once("norot", "pxrt: sprite rotation/scale not supported by the DLL: drawn unrotated")
      end
    end
    if drawSpriteLocal then
      local ok, err = pcall(drawSpriteLocal, tf(y), tf(z), tf(x), id, tf(frame))
      if not ok then once("dsl:" .. tostring(err), "pxrt: drawSpriteLocal failed: %s", tostring(err)) end
    end
    return 0
  end

  ---------------------------------------------------------------------
  -- CObject
  ---------------------------------------------------------------------
  local CO = nat("CObject")
  CO.AddSprite = function(self, super, z, x, y, unk, sprite, frame) return E.drawSprite(z, x, y, sprite, frame) end
  CO.AddSpriteEx = function(self, super, z, x, y, sprite, frame, rot, scale)
    return E.drawSprite(z, x, y, sprite, frame, rot, scale)
  end
  CO.AddSpriteQ = function() once("addspriteq", "pxrt: AddSpriteQ (quad render) unsupported") return 0 end
  CO.AddBitmap = function() once("addbitmap", "pxrt: AddBitmap unsupported") return 0 end
  CO.AddInterfaceBitmap = function() once("addifbitmap", "pxrt: AddInterfaceBitmap unsupported") return 0 end
  CO.AddCustomRender = function() once("addcustomrender", "pxrt: AddCustomRender unsupported") return 0 end
  CO.SetActiveLevel = function() return 0 end

  local function selfAddrForSound(self)
    local a = addrOf(self)
    if a ~= 0 then return a end
    return nil
  end
  CO.PlaySound = function(self, super, idx, unk, unkb, unkc, pan)
    idx = E.spriteId and ti(type(idx) == "table" and (rawget(idx, "Index") or 0) or idx) or ti(idx)
    if idx > 0 and playSoundLocal then pc(playSoundLocal, 1.0, 1.0, selfAddrForSound(self), idx, 0) end
    return 0
  end
  CO.PlayLocalSound = CO.PlaySound

  CO.DoExplosion = function(self, super, x, y, push, damage, unkb, team)
    local sender = addrOf(self)
    if sender == 0 then sender = E.turnGameAddr() end
    if sender == 0 then return 0 end
    local px, py = floor(tf(x) * 65536.0 + 0.5), floor(tf(y) * 65536.0 + 0.5)
    local fn = E.WA_EXPLOSION()
    if callRegs and fn ~= 0 then
      local ok, err = pcall(callRegs, fn, { eax = px, ecx = py, esi = sender }, ti(push), ti(damage), ti(unkb), ti(team))
      if not ok then once("dx:" .. tostring(err), "pxrt: DoExplosion failed: %s", tostring(err)) end
    end
    return 0
  end

  CO.Free = function(self, super, flag)
    local a = addrOf(self)
    if a ~= 0 then
      -- engine objects: destroy through the vtable without releasing memory
      E.callThis(vtSlot(a, 4), a, 0)
      if E.forget then E.forget(a) end
      return 0
    end
    if E.freePseudo then E.freePseudo(self) end
    return 0
  end

  -- GetObject(type, index): hash store lookup
  CO.GetObject = function(self, super, t, i)
    local a = E.hashObject(ti(t), ti(i))
    if a == 0 then return nil end
    return E.proxyAt(a)
  end

  -- Message(sender, type, size, data): live vtable dispatch (script chain runs through hooks)
  CO.Message = function(self, super, sender, mtype, size, data)
    local a = addrOf(self)
    if a == 0 then return 0 end
    local da = addrOf(data)
    if da == 0 then da = scratch() end
    return E.sendMessage(a, addrOf(sender), mtype, size and ti(size) or 1032, da)
  end

  ---------------------------------------------------------------------
  -- CGObject
  ---------------------------------------------------------------------
  local CG = nat("CGObject")
  CG.SetState = function(self, super, s)
    local a = addrOf(self)
    if a == 0 then return 0 end
    s = ti(s)
    if rd(a + 0x20) == 18 and wormSetState then
      pc(wormSetState, a, s)
    else
      E.callThis(vtSlot(a, 0x38), a, s)
    end
    return 0
  end
  CG.Collide = function() return 0 end
  CG.OnSink = function() return 0 end
  CG.Reflect = function() return 0 end

  -- CMine::Explosion: the mine blows up where it lies (callers free it afterwards)
  nat("CMine").Explosion = function(self, super)
    local a = addrOf(self)
    if a == 0 then return 0 end
    return CO.DoExplosion(self, nil, rd(a + 0x84) / 65536.0, rd(a + 0x88) / 65536.0, 50, 50, 0, 0)
  end

  -- CMissile::launchdata: the missile's copy of its weapon launch block (weapon entry +0x3C, sprite +0x24 -> +0x2EC)
  E.special.CMissile = E.special.CMissile or {}
  E.special.CMissile.launchdata = function(t, a) return E.launchAt(a + 0x2C8) end

  ---------------------------------------------------------------------
  -- CWorm natives (original = base)
  ---------------------------------------------------------------------
  local CW = nat("CWorm")
  CW.RenderWorm = function() return 0 end
  CW.RenderCrosshair = function() return 0 end
  CW.RenderRope = function() return 0 end
  CW.RenderRopeShot = function() return 0 end
  CW.IsMoving = function(self)
    local a = addrOf(self)
    if a == 0 then return 0 end
    return (rd(a + 0x90) ~= 0 or rd(a + 0x94) ~= 0) and 1 or 0
  end
  CW.ResetWeapon = function() return 0 end
  CW.SelectWeapon = function() return 0 end
  CW.SetAnimEx = function() return 0 end
  CW.GetName = function(self)
    local a = addrOf(self)
    if a == 0 then return "" end
    return E.F.GetTeamName(rd(a + 0xFC))
  end
  CW.SetName = function() return 0 end
  -- GetWormAnimState(&x, &y, &sprite, &frame): what RenderWorm would draw (WA's GetWormDrawParams 0x512E80)
  local function setRef(r, v) if type(r) == "table" and R.isref(r) then r.v = v end end
  CW.GetWormAnimState = function(self, super, x, y, sprite, frame)
    local a = addrOf(self)
    if a == 0 then return 0 end
    local px, py, spr, ph = rd(a + 0x84) / 65536.0, rd(a + 0x88) / 65536.0, 0, 0
    local fn = E.WA_WORMANIMSTATE()
    if callRegs and E.acquireBuf and fn ~= 0 then
      local b = E.acquireBuf(16)
      if b ~= 0 then
        local ok = pcall(callRegs, fn, { eax = b, esi = a }, b + 4, b + 8, b + 12)
        if ok then
          px, py = rd(b + 4) / 65536.0, rd(b + 8) / 65536.0
          spr, ph = rd(b), rd(b + 12)
        end
        E.releaseBuf(16, b)
      end
    end
    setRef(x, px); setRef(y, py); setRef(sprite, spr); setRef(frame, ph)
    return 0
  end
  CW.TakeDamage = function(self, super, dmg)
    local a = addrOf(self)
    if a == 0 then return 0 end
    local team, worm = rd(a + 0xFC), rd(a + 0x100)
    local h = E.wormHealthAddr(team, worm)
    if h ~= 0 then wr(h, math.max(0, rd(h) - ti(dmg))) end
    return 0
  end
  CW.Heal = function(self, super, n)
    local a = addrOf(self)
    if a == 0 then return 0 end
    local h = E.wormHealthAddr(rd(a + 0xFC), rd(a + 0x100))
    if h ~= 0 then wr(h, rd(h) + ti(n)) end
    return 0
  end
  CW.isAlive = function(self)
    local a = addrOf(self)
    if a == 0 then return 0 end
    local h = E.wormHealthAddr(rd(a + 0xFC), rd(a + 0x100))
    return (h ~= 0 and rd(h) > 0) and 1 or 0
  end
  -- FireFinal(weapon, desc): the native element means "let WA fire normally"; the hook
  -- layer decides what that means (see pxrt_e_hooks)
  CW.FireFinal = function(self, super, weapon, desc)
    E.fireFinalNative = true
    return 0
  end

  ---------------------------------------------------------------------
  -- CTurnGame / CTeam
  ---------------------------------------------------------------------
  local CT = nat("CTurnGame")
  CT.GetCurColor = function(self)
    local tg = E.turnGameAddr()
    if tg == 0 then return 0 end
    return E.F.GetTeamColor(rd(tg + 0x12C))
  end
  CT.IsTimerActive = function(self)
    local tg = E.turnGameAddr()
    if tg == 0 then return 0 end
    return (rd(tg + 0x164) == 0) and 1 or 0
  end
  CT.FinishTurn = function() once("finishturn", "pxrt: CTurnGame::FinishTurn unsupported") return 0 end
  CT.ShowTeamMessage = function(self, super, kind, s, team) return E.F.ShowTeamMessage(kind, s, team) end
  CT.GetNextTeam = function() return 0 end
  CT.SetCurrentTeam = function() return 0 end
  nat("CTeam").GetNextWorm = function() return 0 end
  nat("CTeam").SetCurrentWorm = function() return 0 end

  ---------------------------------------------------------------------
  -- CGameState (K.GS)
  ---------------------------------------------------------------------
  local GS = nat("CGameState")
  GS.GetRandom = function() return E.random(0x7FFFFFFF) end
  GS.GetWeaponByName = function(self, super, name) return E.F.GetWeaponByName(name) end
  GS.GetWeaponByIndex = function(self, super, page, idx) return E.weaponById(ti(idx), nil) end
  GS.GetWeaponIcon = function() return 0 end
  GS.SetWeaponIcon = function() return 0 end

  ---------------------------------------------------------------------
  -- CGameInfo (K.GS.Info)
  ---------------------------------------------------------------------
  local function teamUD(team)
    local ta = E.teamAddr(team)
    if ta == 0 or not getTeams or not ptrToInt then return nil end
    local ok, list = pcall(getTeams)
    if not ok or type(list) ~= "table" then return nil end
    for _, t in pairs(list) do
      local ok2, a = pcall(ptrToInt, t)
      if ok2 and a == ta then return t end
    end
    return nil
  end
  E.teamUD = teamUD
  local GI = nat("CGameInfo")
  GI.GetWormHealth = function(self, super, team, worm)
    local h = E.wormHealthAddr(ti(team), ti(worm))
    return h ~= 0 and rd(h) or 0
  end
  GI.SetWormHealth = function(self, super, team, worm, hp)
    local h = E.wormHealthAddr(ti(team), ti(worm))
    if h ~= 0 then wr(h, ti(hp)) end
    return 0
  end
  local function setAmmo(team, widx, ammo)
    local t = teamUD(team)
    if t and setTeamWeaponAmmo then pc(setTeamWeaponAmmo, t, ti(widx) + 2, ti(ammo)) end
    return 0
  end
  GI.SetWeaponEx = function(self, super, team, widx, page, ammo) return setAmmo(team, widx, ammo) end
  GI.AddWeaponEx = function(self, super, team, widx, page, n)
    local t = teamUD(team)
    if t and getTeamWeaponAmmo and setTeamWeaponAmmo then
      local ok, cur = pcall(getTeamWeaponAmmo, t, ti(widx) + 2)
      cur = (ok and type(cur) == "number") and cur or 0
      if cur >= 0 then pc(setTeamWeaponAmmo, t, ti(widx) + 2, cur + ti(n)) end
    end
    return 0
  end
  GI.AddWeapon = function(self, super, team, w, n)
    local id = type(w) == "table" and E.weaponId(w) or ti(w)
    return GI.AddWeaponEx(self, super, team, id - 2, 0, n == nil and 1 or n)
  end
  GI.SetWeaponDelay = function(self, super, team, widx, page, delay)
    local t = teamUD(team)
    if t and setTeamWeaponDelay then pc(setTeamWeaponDelay, t, ti(widx) + 2, ti(delay)) end
    return 0
  end
  setmetatable(E.infoProxy, {
    __index = function(t, k)
      if k == "Stores" then return E.storesView end
      local mf = R.buildChain("CGameInfo", k)
      if #mf > 0 then return R.methodClosure("CGameInfo", k) end
      return 0
    end,
  })
  E.storesView = setmetatable({}, {
    __index = function(_, ti0)
      local team = ti(ti0) + 1
      return { Count = setmetatable({}, {
        __index = function(_, j)
          local t = teamUD(team)
          if t and getTeamWeaponAmmo then
            local ok, v = pcall(getTeamWeaponAmmo, t, ti(j) + 2)
            if ok and type(v) == "number" then return v end
          end
          return 0
        end,
        -- Count[j] is host weapon j + 2 (setAmmo adds the 2), like the getter and Delay
        __newindex = function(_, j, v) setAmmo(team, ti(j), v) end,
      }), Delay = setmetatable({}, {
        __index = function(_, j)
          local t = teamUD(team)
          if t and getTeamWeaponDelay then
            local ok, v = pcall(getTeamWeaponDelay, t, ti(j) + 2)
            if ok and type(v) == "number" then return v end
          end
          return 0
        end,
        __newindex = function(_, j, v)
          local t = teamUD(team)
          if t and setTeamWeaponDelay then pc(setTeamWeaponDelay, t, ti(j) + 2, ti(v)) end
        end,
      }) }
    end,
  })

  ---------------------------------------------------------------------
  -- CGame (K.GG)
  ---------------------------------------------------------------------
  nat("CGame").WriteToChat = function(self, super, font, msg) E.F.ShowMessage(msg) return 0 end
  local LAND = nat("CLandscape")
  for _, m in ipairs({ "Draw", "MakeHole", "ApplyMask", "ApplyCustomMask" }) do
    LAND[m] = function() once("land:" .. m, "pxrt: landscape %s not implemented yet", m) return 0 end
  end
  local BM = nat("CBitmask")
  BM.Rect = function() return 0 end
  BM.GetPixel = function() return 0 end

  ---------------------------------------------------------------------
  -- CEnv
  ---------------------------------------------------------------------
  local EN = nat("CEnv")
  EN.CheckCollision = function(self, super, obj, x, y)
    if E.checkCollision then return E.checkCollision(obj, tf(x), tf(y), nil, 0) end
    return nil
  end
  EN.CheckCollisionEx = function(self, super, obj, x, y, mask, flags)
    if E.checkCollision then return E.checkCollision(obj, tf(x), tf(y), mask, ti(flags)) end
    return nil
  end

  ---------------------------------------------------------------------
  -- weapons
  ---------------------------------------------------------------------
  local vanilla = {}
  do
    local names = { "Bazooka", "Homing Missile", "Mortar", "Homing Pigeon", "Sheep Launcher", "Grenade", "Cluster Bomb",
      "Banana Bomb", "Battle Axe", "Earthquake", "Shotgun", "Handgun", "Uzi", "Minigun", "Longbow", "Fire Punch",
      "Dragon Ball", "Kamikaze", "Suicide Bomber", "Prod", "Dynamite", "Mine", "Sheep", "Super Sheep", "Aqua Sheep",
      "Mole Bomb", "Air Strike", "Napalm Strike", "Mail Strike", "Mine Strike", "Mole Squadron", "Blow Torch",
      "Pneumatic Drill", "Girder", "Baseball Bat", "Girder Starter Pack", "Ninja Rope", "Bungee", "Parachute", "Teleport",
      "Scales of Justice", "Super Banana Bomb", "Holy Hand Grenade", "Flame Thrower", "Salvation Army", "MB Bomb",
      "Petrol Bomb", "Skunk", "Ming Vase", "Sheep Strike", "Carpet Bomb", "Mad Cow", "Old Woman", "Donkey",
      "Nuclear Test", "Armageddon", "Skip Go", "Surrender", "Select Worm", "Freeze", "Magic Bullet", "Jet Pack",
      "Low Gravity", "Fast Walk", "Laser Sight", "Invisibility", "Damage x2", "Crate Spy", "Double Turn Time", "Crate Shower" }
    for i, n in ipairs(names) do vanilla[n:lower():gsub("[^%w]", "")] = i end
    vanilla.girderpack = 36; vanilla.superbanana = 42; vanilla.holygrenade = 43; vanilla.jetpack = 61
    vanilla.damagex2 = 67; vanilla.doubledamage = 67; vanilla.earthquake = 10; vanilla.flamethrower = 44
  end
  local function normName(s) return (tostring(s or ""):lower():gsub("[^%w]", "")) end
  -- px2jelly registered weapons under names made from the .bin file name ("Balloon W"); scripts test ProjectX's own
  -- names ("Hot Air Balloon"). pxrt_wnames (pxwnames.py) maps registered -> ProjectX name; scripts see the latter.
  local okW, WN = pcall(require, "pxrt_wnames")
  if not okW or type(WN) ~= "table" then WN = {} end
  local pxFromReg, regFromPx = {}, {}
  do
    local keys = {}
    for k in pairs(WN) do keys[#keys + 1] = k end
    table.sort(keys)
    for _, k in ipairs(keys) do
      local px = WN[k]
      pxFromReg[k] = px
      local n = normName(px)
      if not regFromPx[n] then regFromPx[n] = k end
    end
  end
  local function hostId(name)
    if not weaponIdByName then return -1 end
    local ok, v = pcall(weaponIdByName, name)
    if ok and type(v) == "number" then return v end
    return -1
  end
  local function idByName(name)
    local id = hostId(name)
    if id < 0 then
      local reg = regFromPx[normName(name)]
      if reg then id = hostId(reg) end
    end
    if id < 0 then id = vanilla[normName(name)] or -1 end
    return id
  end
  E.idByName = idByName

  local wproxyById = {}
  function E.weaponById(id, name)
    local w = wproxyById[id]
    if id < 0 then
      w = setmetatable({ __cls = "CWeapon", __id = -1, __name = name }, E.weaponMT)
      return w
    end
    if not w then
      w = setmetatable({ __cls = "CWeapon", __id = id, __name = name }, E.weaponMT)
      wproxyById[id] = w
    end
    return w
  end
  -- weapon entry (WeaponStruct in WA): name1 +0, name2 +4, PX CWeapon fields follow, launch block at +0x3C
  E.FIELDS.CWeapon = {
    Row = { 0x08, "i" }, Remember = { 0x0C, "i" }, UseInCavern = { 0x10, "i" }, NShoots = { 0x14, "i" },
    EndsTurn = { 0x18, "i" }, RetreatTime = { 0x1C, "i" }, Probablity = { 0x20, "i" }, Count = { 0x24, "i" },
    Anim = { 0x28, "i" }, ActivationType = { 0x2C, "i" },
  }
  local function structName(w, off)
    local sa = rawget(w, "__a")
    if not sa or not okAddr(sa) then return nil end
    local p = rdU(sa + off)
    if not okAddr(p) then return nil end
    local ok, s = pcall(readMemString, p, 64)
    if not ok or not s then return nil end
    return pxFromReg[s] or s
  end
  local function widOf(w)
    local id = rawget(w, "__id")
    if id then return id end
    local n = structName(w, 0)
    if n then
      local v = idByName(n)
      if v >= 0 then return v end
    end
    local wa = rawget(w, "__worm")
    if wa then
      if getWormWeaponId then
        local ok, v = pcall(getWormWeaponId, wa)
        if ok and type(v) == "number" and v >= 0 then return v end
      end
      return rd(wa + 0x170)
    end
    return -1
  end
  function E.weaponId(w) return type(w) == "table" and widOf(w) or ti(w) end
  -- address of the engine weapon entry: explicit (__a) or looked up from the id
  local function saOf(t)
    local sa = rawget(t, "__a")
    if sa then return sa end
    local id = rawget(t, "__id")
    if id and id >= 0 then
      local a = E.weaponStructAddr(id)
      if a ~= 0 then return a end
    end
    return nil
  end
  E.weaponMT.__index = function(t, k)
    if type(k) ~= "string" then return nil end
    local sa = saOf(t)
    if sa and okAddr(sa) then
      local spec = E.FIELDS.CWeapon[k]
      if spec then return rd(sa + spec[1]) end
      if k == "NameA" or k == "NameB" then return structName(t, k == "NameA" and 0 or 4) or "" end
      if k == "launch" then return E.launchAt(sa + 0x3C) end
    end
    local mf = R.buildChain("CWeapon", k)
    if #mf > 0 then return R.methodClosure("CWeapon", k) end
    return 0
  end
  E.weaponMT.__newindex = function(t, k, v)
    local sa = saOf(t)
    local spec = sa and okAddr(sa) and E.FIELDS.CWeapon[k]
    if spec then wr(sa + spec[1], ti(v)) return end
    rawset(t, k, v)
  end
  E.weaponMT.__tostring = function(t) return "CWeapon#" .. tostring(rawget(t, "__id") or structName(t, 0) or "?") end
  E.weaponMT.__eq = function(a, b)
    local x, y = rawget(a, "__a"), rawget(b, "__a")
    if x and y then return x == y end
    return widOf(a) == widOf(b)
  end
  local function normW(s) return (tostring(s or ""):lower():gsub("[^%w]", "")) end
  -- CheckName runs every frame for every sprite-builder object: normalised names are cached per weapon entry and
  -- reused while the entry's two name pointers stay the same; normalised wanted names are cached too
  local normCache = {}
  local nameCache = {}   -- sa -> { p1, p2, norm1, norm2 }
  local function normWanted(s)
    local v = normCache[s]
    if not v then v = normW(s); normCache[s] = v end
    return v
  end
  local function normNames(self)
    local sa = rawget(self, "__a")
    if not sa or not okAddr(sa) then return nil end
    local p1, p2 = rdU(sa), rdU(sa + 4)
    local c = nameCache[sa]
    if c and c[1] == p1 and c[2] == p2 then return c[3], c[4] end
    local n1, n2 = structName(self, 0), structName(self, 4)
    c = { p1, p2, n1 and normW(n1) or false, n2 and normW(n2) or false }
    nameCache[sa] = c
    return c[3], c[4]
  end
  local CWP = nat("CWeapon")
  CWP.CheckName = function(self, super, name)
    local want = R.str(name)
    local n1, n2 = normNames(self)
    if n1 then
      local w = normWanted(want)
      if n1 == w then return 1 end
      if n2 and n2 == w then return 1 end
      return 0
    end
    local id = rawget(self, "__id")
    if id then
      local v = idByName(want)
      return (v >= 0 and v == id) and 1 or 0
    end
    return 0
  end
  CWP.GetWeaponIndex = function(self)
    local id = widOf(self)
    return id >= 2 and id - 2 or id
  end
  CWP.GetPageIndex = function(self) return 0 end
  CWP.Check = CWP.CheckName

  -- script-owned CWeapon struct (a global of a PX script): a private 0x1D0 buffer with the launch block at +0x3C.
  -- Never registered as an engine weapon; only its launch view is handed to the engine (new CMissile(..., launch, ...)).
  local OWN_SIZE = 0x1D0
  local OWN_FIELDS = {
    NameA = { 0x00, "i" }, NameB = { 0x04, "i" }, Row = { 0x08, "i" }, Remember = { 0x0C, "i" },
    UseInCavern = { 0x10, "i" }, NShoots = { 0x14, "i" }, EndsTurn = { 0x18, "i" }, RetreatTime = { 0x1C, "i" },
    Probablity = { 0x20, "i" }, Count = { 0x24, "i" }, Graphic = { 0x28, "i" }, ActivationType = { 0x2C, "i" },
    IsWeaponCrate = { 0x30, "i" }, GlobalIndex = { 0x34, "i" }, WeaponType = { 0x38, "i" },
  }
  local ownBase = R.scriptMTFor("CWeapon")
  local ownMT = {}
  local function ownBuf(t)
    local a = rawget(t, "__buf")
    if not a then
      a = E.acquireBuf(OWN_SIZE)
      rawset(t, "__buf", a)
      rawset(t, "__a", a)
    end
    return a
  end
  ownMT.__index = function(t, k)
    local s = OWN_FIELDS[k]
    if s then return rd(ownBuf(t) + s[1]) end
    if k == "launch" then return E.launchAt(ownBuf(t) + 0x3C) or 0 end
    if k == "__addr" then return ownBuf(t) end
    return ownBase.__index(t, k)
  end
  ownMT.__newindex = function(t, k, v)
    local s = OWN_FIELDS[k]
    if s then wr(ownBuf(t) + s[1], ti(v)) return end
    if k == "launch" then
      if type(v) == "table" then E.copyLaunch(E.launchAt(ownBuf(t) + 0x3C), v) end
      return
    end
    rawset(t, k, v)
  end
  ownMT.__gc = function(t)
    local a = rawget(t, "__buf")
    if a then E.releaseBuf(OWN_SIZE, a) end
  end
  R.builtinClasses.CWeapon = function() return setmetatable({ __cls = "CWeapon", __own = true }, ownMT) end

  -- Store.GetObject
  E.special.CObject = E.special.CObject or {}
  E.special.CObject.Store = function(t, a)
    return setmetatable({ __a = a, __cls = "CHashStore" }, R.scriptMTFor("CHashStore"))
  end
  nat("CHashStore").GetObject = CO.GetObject
end
