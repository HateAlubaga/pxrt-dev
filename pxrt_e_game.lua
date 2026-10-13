-- pxrt_e_game: game-state proxies (Root, GS, Env, GameInfo), worm/object enumeration, turn helpers
return function(R, E)
  local rd, wr, rdf, wrf, rdU = E.rd, E.wr, E.rdf, E.wrf, E.rdU
  local okAddr = E.okAddr
  local ti, tf, isnull = R.ti, R.tf, R.isnull
  local floor = math.floor
  local log, once = R.log, R.once

  E.tick = 0

  ---------------------------------------------------------------------
  -- worm / team lookup (hash store, 1-based team and worm numbers)
  ---------------------------------------------------------------------
  function E.wormAddr(team, worm)
    return E.hashObject(2, (ti(team) << 4) + ti(worm))
  end
  function E.worm(team, worm)
    local a = E.wormAddr(team, worm)
    if a == 0 then return nil end
    return E.proxyAt(a, "CWorm")
  end
  function E.teamAddr(team) return E.hashObject(0x15, ti(team)) end
  function E.curWormAddr()
    local tg = E.turnGameAddr()
    if tg == 0 then return 0 end
    local team, w = rd(tg + 0x12C), rd(tg + 0x130)
    if team <= 0 or w <= 0 then return 0 end
    return E.hashGet(tg, 2, (team << 4) + w)
  end
  function E.curWorm()
    local a = E.curWormAddr()
    if a == 0 then return nil end
    return E.proxyAt(a, "CWorm")
  end
  -- every worm in the match
  function E.allWorms()
    local out = {}
    local tg = E.turnGameAddr()
    if tg == 0 then return out end
    for t = 1, 6 do
      for w = 1, 8 do
        local a = E.hashGet(tg, 2, (t << 4) + w)
        if a ~= 0 then out[#out + 1] = E.proxyAt(a, "CWorm") end
      end
    end
    return out
  end

  ---------------------------------------------------------------------
  -- CEnv: object lists
  ---------------------------------------------------------------------
  -- all-task list array {cap +0, dirty +4, count +8, data +0xC} at env+0x18
  local objsList = setmetatable({}, {
    __index = function(t, k)
      local env = E.envAddr()
      if env == 0 then return k == "Count" and 0 or nil end
      if k == "Count" then return rd(env + 0x18 + 8) end
      if k == "Objs" then return t.__arr end
      return nil
    end,
  })
  objsList.__arr = setmetatable({}, {
    __index = function(_, i)
      local env = E.envAddr()
      if env == 0 or type(i) ~= "number" then return nil end
      i = ti(i)
      if i < 0 or i >= rd(env + 0x18 + 8) then return nil end
      local data = rdU(env + 0x18 + 0xC)
      if not okAddr(data) then return nil end
      local a = rdU(data + 4 * i)
      if not okAddr(a) then return nil end
      return E.proxyAt(a)
    end,
  })
  E.objsList = objsList

  local envSpecial = {
    Objs = function() return objsList end,
    Water = function()
      return E.waterLevel and E.waterLevel() or 0
    end,
  }
  setmetatable(E.envProxy, {
    __index = function(t, k)
      local f = envSpecial[k]
      if f then return f() end
      local spec = E.fieldSpec("CEnv", k)
      local a = rawget(t, "__a")
      if spec and a and a ~= 0 then
        if spec[2] == "f" then return rd(a + spec[1]) / 65536.0 end
        return rd(a + spec[1])
      end
      local mf = R.buildChain("CEnv", k)
      if #mf > 0 then return R.methodClosure("CEnv", k) end
      return 0
    end,
    __newindex = function(t, k, v)
      local a = rawget(t, "__a")
      local spec = E.fieldSpec("CEnv", k)
      if spec and a and a ~= 0 then
        if spec[2] == "f" then wrf(a + spec[1], v) else wr(a + spec[1], ti(v)) end
        return
      end
      if k == "Water" and E.setWaterLevel then E.setWaterLevel(v) return end
      rawset(t, k, v)
    end,
  })
  E.envProxy.__cls = "CEnv"

  ---------------------------------------------------------------------
  -- GameInfo (K.GS.Info)
  ---------------------------------------------------------------------
  local function wormHealthAddr(team, worm)
    local dd = E.ddGame()
    if dd == 0 then return 0 end
    return dd + 0x40EC + ti(team) * 0x51C + ti(worm) * 0x9C
  end
  E.wormHealthAddr = wormHealthAddr
  -- NWorms walks 8 hash slots; scripts read it in nested per-worm-per-frame loops (random_zombies: ~45% of all
  -- script time in-game), so the count is kept for the current frame tick
  local nwTick, nwCount = -1, {}
  local function teamWormCount(team)
    if nwTick ~= E.tick then nwTick = E.tick; nwCount = {} end
    local n = nwCount[team]
    if n then return n end
    n = 0
    for w = 1, 8 do
      if E.wormAddr(team, w) ~= 0 then n = n + 1 end
    end
    nwCount[team] = n
    return n
  end
  -- Teams[i] / Worms[j] views hold no state of their own (every field reads or writes game memory, other writes
  -- are dropped), so one view per team / worm is built once and reused instead of new tables on every access
  local readOnly = function() end
  local function wormView(team, worm)
    return setmetatable({}, {
      __index = function(_, f)
        if f == "Health" then return rd(wormHealthAddr(team, worm)) end
        if f == "State" then
          local a = E.wormAddr(team, worm)
          if a == 0 then return 135 end       -- free slot
          return rd(a + 0x44)
        end
        return 0
      end,
      __newindex = function(_, f, v)
        if f == "Health" then wr(wormHealthAddr(team, worm), ti(v)) end
      end,
    })
  end
  local function teamView(team)
    local worms = setmetatable({}, {
      __index = function(t, wi0)
        local worm = ti(wi0) + 1
        local wv = rawget(t, worm - 1)
        if wv == nil then
          wv = wormView(team, worm)
          rawset(t, worm - 1, wv)
        end
        return wv
      end,
      __newindex = readOnly,
    })
    return setmetatable({}, {
      __index = function(_, f)
        if f == "Worms" then return worms end
        if f == "NWorms" then return teamWormCount(team) end
        if f == "Active" then local ta = E.teamAddr(team); return ta ~= 0 and rd(ta + 0x3C) or 0 end
        return 0
      end,
      __newindex = readOnly,
    })
  end
  local teamViews = {}
  local teamsView = setmetatable({}, {
    __index = function(_, ti0)
      local team = ti(ti0) + 1
      local tv = teamViews[team]
      if tv == nil then
        tv = teamView(team)
        teamViews[team] = tv
      end
      return tv
    end,
  })
  E.infoProxy.__cls = "CGameInfo"
  E.infoProxy.Teams = teamsView

  -- K.GS.Disp: display object. Drawing calls are no-ops (the engine draws via sprite overrides); sizes are plausible.
  local dispNoop = function() return 0 end
  local dispFns = {
    DrawText = true, DrawTextEx = true, DrawLine = true, DrawRect = true, FillRect = true, Rect = true, HLine = true,
    VLine = true, DrawBitmap = true, Draw = true, SetClip = true, ResetClip = true, SetColor = true, Flush = true,
    DrawSprite = true, DrawCircle = true, Fill = true, SetPixel = true,
  }
  local dispVals = { xRes = 1280, yRes = 720, halfX = 640, halfY = 360, ViewX = 0, ViewY = 0, ViewSX = 1280, ViewSY = 720, nSurfaces = 0 }
  E.dispProxy = setmetatable({ __cls = "CDisplay" }, {
    __index = function(t, k)
      if dispFns[k] then return dispNoop end
      local v = dispVals[k]
      if v ~= nil then return v end
      return 0
    end,
    __newindex = function() end,
  })

  -- GameState proxy: Tick, level size, selection, Info, env
  local gsFields = {
    Disp = function() return E.dispProxy end,
    Tick = function() return E.tick end,
    Info = function() return E.infoProxy end,
    env = function() E.envProxy.__a = E.envAddr() return E.envProxy end,
    Env = function() E.envProxy.__a = E.envAddr() return E.envProxy end,
    LevelSX = function() local w = E.levelSize and E.levelSize() return w or 4096 end,
    LevelSY = function() local h; if E.levelSize then local _; _, h = E.levelSize() end return h or 2048 end,
    landSelectX = function()
      local w = E.curWorm()
      return w and (rd(w.__a + 0x2E0) / 65536.0) or 32768
    end,
    landSelectY = function()
      local w = E.curWorm()
      return w and (rd(w.__a + 0x2E4) / 65536.0) or 32768
    end,
    ActCameraX = function() return E.cameraX and E.cameraX() or 0 end,
    ActCameraY = function() return E.cameraY and E.cameraY() or 0 end,
  }
  setmetatable(E.gsProxy, {
    __index = function(t, k)
      local f = gsFields[k]
      if f then return f() end
      local mf = R.buildChain("CGameState", k)
      if #mf > 0 then return R.methodClosure("CGameState", k) end
      return 0
    end,
    __newindex = function(t, k, v)
      if k == "landSelectX" or k == "landSelectY" then
        local w = E.curWorm()
        if w then wr(w.__a + (k == "landSelectX" and 0x2E0 or 0x2E4), ti(v)) end
        return
      end
      rawset(t, k, v)
    end,
  })

  -- GG (global game object): only a few members are ever used
  E.ggProxy = setmetatable({ __cls = "CGame" }, {
    __index = function(t, k)
      if k == "land" then return E.landProxy end
      if k == "machColors" then return setmetatable({}, { __index = function() return 0xFF end }) end
      if k == "curFont" then return 0 end
      if k == "queue2" then return E.queue2 or 0 end   -- command queue (M_PXMESSAGE), see pxrt_e_hooks
      local mf = R.buildChain("CGame", k)
      if #mf > 0 then return R.methodClosure("CGame", k) end
      return 0
    end,
  })
  E.landProxy = setmetatable({ __cls = "CLandscape" }, {
    __index = function(t, k)
      if k == "BitMask" then return E.bitMaskProxy end
      local mf = R.buildChain("CLandscape", k)
      if #mf > 0 then return R.methodClosure("CLandscape", k) end
      return 0
    end,
  })
  E.bitMaskProxy = setmetatable({ __cls = "CBitmask" }, {
    __index = function(t, k)
      local mf = R.buildChain("CBitmask", k)
      if #mf > 0 then return R.methodClosure("CBitmask", k) end
      return 0
    end,
  })

  ---------------------------------------------------------------------
  -- DDGame random numbers
  ---------------------------------------------------------------------
  function E.random(n)
    n = ti(n)
    if n <= 0 then return 0 end
    local ok, v = pcall(jellyRandomInt, 0, n - 1)
    if ok and type(v) == "number" then return ti(v) end
    return math.random(0, n - 1)
  end
end
