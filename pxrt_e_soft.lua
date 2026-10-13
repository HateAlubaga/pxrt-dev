-- pxrt_e_soft: the "soft world" - collision masks, a unified object list (engine objects, script-owned objects,
-- terrain) and a light physics step for script-owned CGObject-family objects (they have no WA task behind them).
--
--   masks      CBitmap1 (1-bit rows) + CColMask(hotspotX, hotspotY, bitmap) + exact pixel overlap tests
--   world      E.worldObjs(): engine GObjects + soft objects that own a mask + the terrain pseudo-object
--   utils      native FindInMask / CheckMaskAt / _TraceMask (same results as the PX script versions, ~100x cheaper)
--   physics    E.softStep(obj): gravity, wind, terrain bounce (DumpingA walls / B floors / C friction), water, bounds
return function(R, E)
  local ti, tf, T = R.ti, R.tf, R.T
  local log, once = R.log, R.once
  local rd, rdU, okAddr = E.rd, E.rdU, E.okAddr
  local floor, abs, sqrt, max, min, ceil = math.floor, math.abs, math.sqrt, math.max, math.min, math.ceil
  local rawget, rawset, type, setmetatable, pairs, ipairs, pcall, tostring =
    rawget, rawset, type, setmetatable, pairs, ipairs, pcall, tostring
  local N, BC = R.natives, R.builtinClasses
  R.builtinFuncs = R.builtinFuncs or {}
  local BF = R.builtinFuncs
  local F = R.F
  local function nat(cls) N[cls] = N[cls] or {} return N[cls] end

  local OC = E.OC_BY_NAME
  local FRAME = 2

  ---------------------------------------------------------------------
  -- 1-bit bitmaps and collision masks
  ---------------------------------------------------------------------
  local function bset(o, x, y, c)
    if x < 0 or y < 0 or x >= o.SX or y >= o.SY then return end
    local rows = rawget(o, "__rows")
    local r = rows[y]
    if c ~= 0 then
      if not r then r = {}; rows[y] = r end
      r[x] = true
    elseif r then
      r[x] = nil
    end
    rawset(o, "__outline", nil)
  end

  local function newBitmap1(w, h)
    local o = setmetatable({ __cls = "CBitmap1" }, R.scriptMTFor("CBitmap1"))
    rawset(o, "SX", w); rawset(o, "SY", h); rawset(o, "W", w); rawset(o, "H", h)
    rawset(o, "__rows", {})
    return o
  end
  BC.CBitmap1 = function(w, h) return newBitmap1(max(0, ti(w or 0)), max(0, ti(h or 0))) end

  N.CBitmap1 = {}      -- own table: R.natives.CBitmap1 aliases the inert GUI CBitmap natives
  local BM = N.CBitmap1
  BM.SetPixel = function(self, super, x, y, c) bset(self, ti(x), ti(y), ti(c)); return 0 end
  BM.GetPixel = function(self, super, x, y)
    local r = rawget(self, "__rows")[ti(y)]
    return (r and r[ti(x)]) and 1 or 0
  end
  local function hline(self, x1, x2, y, c)
    if x1 > x2 then x1, x2 = x2, x1 end
    for x = max(0, x1), min(self.SX - 1, x2) do bset(self, x, y, c) end
  end
  BM.HLine = function(self, super, x1, x2, y, c) hline(self, ti(x1), ti(x2), ti(y), ti(c)); return 0 end
  BM.VLine = function(self, super, x, y1, y2, c)
    x, y1, y2, c = ti(x), ti(y1), ti(y2), ti(c)
    if y1 > y2 then y1, y2 = y2, y1 end
    for y = max(0, y1), min(self.SY - 1, y2) do bset(self, x, y, c) end
    return 0
  end
  BM.Rect = function(self, super, x1, y1, x2, y2, c)
    x1, y1, x2, y2, c = ti(x1), ti(y1), ti(x2), ti(y2), ti(c)
    if y1 > y2 then y1, y2 = y2, y1 end
    for y = max(0, y1), min(self.SY - 1, y2) do hline(self, x1, x2, y, c) end
    return 0
  end
  BM.Clear = function(self, super, c)
    rawset(self, "__rows", {}); rawset(self, "__outline", nil)
    if ti(c or 0) ~= 0 then
      for y = 0, self.SY - 1 do hline(self, 0, self.SX - 1, y, 1) end
    end
    return 0
  end
  for _, k in ipairs({ "DrawText", "Draw", "Copy", "Compact", "Update", "Fill" }) do BM[k] = function() return 0 end end

  -- GUI bitmaps (F.MakeBitmap): drawing is not supported but sizes are kept
  local mkBitmap = F.MakeBitmap
  F.MakeBitmap = function(w, h)
    local o = mkBitmap(w, h)
    if type(o) == "table" then rawset(o, "SX", ti(w)); rawset(o, "SY", ti(h)) end
    return o
  end

  -- outline of a mask bitmap: set pixels with an unset 4-neighbour (all that is needed to detect contact with solids)
  local function outlineOf(bm)
    local ol = rawget(bm, "__outline")
    if ol then return ol end
    ol = {}
    local rows = rawget(bm, "__rows")
    for y, row in pairs(rows) do
      local up, dn = rows[y - 1], rows[y + 1]
      for x in pairs(row) do
        if not (row[x - 1] and row[x + 1] and up and up[x] and dn and dn[x]) then
          ol[#ol + 1] = { x, y }
        end
      end
    end
    -- deterministic order (pairs() order is not)
    table.sort(ol, function(a, b) if a[2] ~= b[2] then return a[2] < b[2] end return a[1] < b[1] end)
    rawset(bm, "__outline", ol)
    return ol
  end

  BC.CColMask = function(hx, hy, bmp)
    local o = setmetatable({ __cls = "CColMask" }, R.scriptMTFor("CColMask"))
    hx, hy = ti(hx or 0), ti(hy or 0)
    if type(bmp) == "table" and rawget(bmp, "SX") == 1 and rawget(bmp, "SY") == 1 then hx, hy = 0, 0 end
    rawset(o, "HX", hx); rawset(o, "HY", hy); rawset(o, "Bmp", type(bmp) == "table" and bmp or nil)
    rawset(o, "W", type(bmp) == "table" and rawget(bmp, "SX") or 0)
    rawset(o, "H", type(bmp) == "table" and rawget(bmp, "SY") or 0)
    return o
  end
  -- the terrain behaves as one huge mask
  local TERRAIN_MASK = setmetatable({ __cls = "CColMask", __terrain = true, HX = 0, HY = 0, W = 0, H = 0 }, R.scriptMTFor("CColMask"))
  E.TERRAIN_MASK = TERRAIN_MASK

  -- pixel overlap of mask a (hotspot at ax,ay) and mask b (hotspot at bx,by); positions are floored to pixels.
  -- `probe` = E.landProbe() closure when the same land snapshot is reused for many tests.
  local function maskCheck(a, ax, ay, b, bx, by, probe)
    if type(a) ~= "table" or type(b) ~= "table" then return false end
    ax, ay, bx, by = floor(tf(ax)), floor(tf(ay)), floor(tf(bx)), floor(tf(by))
    if rawget(a, "__terrain") then a, b, ax, ay, bx, by = b, a, bx, by, ax, ay end
    if rawget(a, "__terrain") then return false end
    local ab = rawget(a, "Bmp")
    if not ab then return false end
    local aox, aoy = ax - rawget(a, "HX"), ay - rawget(a, "HY")
    if rawget(b, "__terrain") then
      probe = probe or E.landProbe()
      local ol = outlineOf(ab)
      for i = 1, #ol do
        local p = ol[i]
        if probe(aox + p[1], aoy + p[2]) then return true end
      end
      return false
    end
    local bb = rawget(b, "Bmp")
    if not bb then return false end
    local box, boy = bx - rawget(b, "HX"), by - rawget(b, "HY")
    local x0, x1 = max(aox, box), min(aox + ab.SX, box + bb.SX)
    local y0, y1 = max(aoy, boy), min(aoy + ab.SY, boy + bb.SY)
    if x0 >= x1 or y0 >= y1 then return false end
    local arows, brows = rawget(ab, "__rows"), rawget(bb, "__rows")
    for wy = y0, y1 - 1 do
      local ra, rb = arows[wy - aoy], brows[wy - boy]
      if ra and rb then
        for wx = x0, x1 - 1 do
          if ra[wx - aox] and rb[wx - box] then return true end
        end
      end
    end
    return false
  end
  E.maskCheck = maskCheck

  nat("CColMask").Check = function(self, super, x, y, other, ox, oy)
    return maskCheck(self, x, y, other, ox, oy) and 1 or 0
  end
  for _, k in ipairs({ "SetPixel", "GetPixel", "Rect", "HLine", "VLine", "Clear" }) do
    nat("CColMask")[k] = function() return 0 end
  end

  -- filled disc mask of radius r (cached)
  local circleCache = {}
  local function circleMask(r)
    r = max(1, floor(r + 0.5))
    local m = circleCache[r]
    if m then return m end
    local d = r * 2 + 1
    local bm = newBitmap1(d, d)
    for y = 0, d - 1 do
      for x = 0, d - 1 do
        local dx, dy = x - r, y - r
        if dx * dx + dy * dy <= r * r + r then bset(bm, x, y, 1) end
      end
    end
    m = BC.CColMask(r, r, bm)
    circleCache[r] = m
    return m
  end
  E.circleMask = circleMask

  ---------------------------------------------------------------------
  -- engine objects expose a ColMask / Layer too (disc from the object's size field)
  ---------------------------------------------------------------------
  local DEFAULT_R = { [8] = 4, [9] = 5, [11] = 3, [12] = 3, [15] = 8, [18] = 6, [21] = 6, [24] = 2, [25] = 3, [30] = 9 }
  local function engineMask(proxy)
    local a = rawget(proxy, "__a")
    if not a then return nil end
    local r = rd(a + 0xDC) / 65536.0
    if r < 1 or r > 64 then r = DEFAULT_R[rd(a + 0x20)] or 4 end
    return circleMask(r)
  end
  for _, cls in ipairs({ "CGObject", "CWorm", "CMine", "CCrate", "COilDrum", "CMissile", "CArrow", "CCanister", "CCross",
    "CGas", "CFire", "CFlame", "COldWorm" }) do
    E.special[cls] = E.special[cls] or {}
    local sp = E.special[cls]
    if not sp.ColMask then sp.ColMask = function(t) return engineMask(t) end end
    if not sp.Layer then sp.Layer = function(t, a) return 0 end end
  end

  ---------------------------------------------------------------------
  -- terrain pseudo-object (what PX sees as the OC_Landscape entry of Env.Objs)
  ---------------------------------------------------------------------
  E.terrainObj = setmetatable({ __cls = "CGObject", __terrain = true, ClType = OC.OC_Landscape, ColMask = TERRAIN_MASK,
    PosX = 0.0, PosY = 0.0, SpX = 0.0, SpY = 0.0, Layer = 1, ColGroup = 0, ObjState = 0, IsMaterial = 1 },
    { __index = function() return 0 end })

  ---------------------------------------------------------------------
  -- unified object list
  ---------------------------------------------------------------------
  local GOBJ_IDS = { [8] = true, [9] = true, [11] = true, [12] = true, [15] = true, [16] = true, [18] = true,
    [21] = true, [24] = true, [25] = true, [30] = true }
  local worldCache, worldTick, worldVer, worldN, worldLife = nil, -1, -1, -1, -1
  function E.worldObjs()
    local env = E.envAddr()
    local n = 0
    local data
    if env ~= 0 then
      n = rd(env + 0x18 + 8)
      data = rdU(env + 0x18 + 0xC)
    end
    if E.syncBirths then E.syncBirths() end
    local life = E.lifeVer or 0
    if worldCache and worldTick == E.tick and worldVer == E.pseudoVersion and worldN == n and worldLife == life then
      return worldCache
    end
    local list = {}
    if env ~= 0 and okAddr(data) then
      for i = 0, n - 1 do
        local a = rdU(data + 4 * i)
        if okAddr(a) and GOBJ_IDS[rd(a + 0x20)] then list[#list + 1] = E.proxyAt(a) end
      end
    end
    for _, o in ipairs(E.pseudoList or {}) do
      if type(rawget(o, "ColMask")) == "table" and rawget(o, "__soft") then list[#list + 1] = o end
    end
    list[#list + 1] = E.terrainObj
    worldCache, worldTick, worldVer, worldN, worldLife = list, E.tick, E.pseudoVersion, n, E.lifeVer or 0
    return list
  end

  -- Env.Objs as seen by scripts: the same unified list
  if E.objsList then
    local objsArr = setmetatable({}, {
      __index = function(_, i)
        if type(i) ~= "number" then return nil end
        return E.worldObjs()[ti(i) + 1]
      end,
    })
    getmetatable(E.objsList).__index = function(t, k)
      if k == "Count" then return #E.worldObjs() end
      if k == "Objs" then return objsArr end
      return nil
    end
  end

  -- mask of a world object + its position (nil mask = not collidable)
  local function maskOf(o)
    local m = o.ColMask
    if type(m) ~= "table" then return nil end
    return m
  end

  -- world-space bbox [x0,x1) x [y0,y1) of an object's mask (nil for the terrain)
  local function bboxOf(o, m)
    if rawget(m, "__terrain") then return nil end
    local b = rawget(m, "Bmp")
    if not b then return false end
    local x = floor(tf(o.PosX)) - rawget(m, "HX")
    local y = floor(tf(o.PosY)) - rawget(m, "HY")
    return x, y, x + b.SX, y + b.SY
  end

  local function groupMatch(obj, flags)
    local lib = R.libs and R.libs.utils
    local f = lib and lib.G.MatchCollisionGroup
    if type(f) == "function" then return T(f(obj, flags)) end
    return true
  end

  -- candidates for a mask moving over the rect [x0,x1) x [y0,y1): { {obj, mask, matches} ... }
  local function candidates(parent, flags, x0, y0, x1, y1)
    local out = {}
    for _, o in ipairs(E.worldObjs()) do
      if o ~= parent then
        local m = maskOf(o)
        if m then
          local bx0, by0, bx1, by1 = bboxOf(o, m)
          if bx0 == nil or (bx0 and bx0 < x1 and bx1 > x0 and by0 < y1 and by1 > y0) then
            if groupMatch(o, flags) then out[#out + 1] = { o, m } end
          end
        end
      end
    end
    return out
  end

  local function maskExtent(m)
    local b = type(m) == "table" and rawget(m, "Bmp")
    if not b then return 0, 0, 0, 0 end
    local hx, hy = rawget(m, "HX"), rawget(m, "HY")
    return hx, hy, b.SX - hx, b.SY - hy      -- left, up, right, down reach from the hotspot
  end

  -- FindInMask(parent, mask, x, y, flags)
  BF.FindInMask = function(parent, msk, x, y, flags)
    x, y, flags = ti(x), ti(y), ti(flags)
    if flags <= 0 and type(parent) == "table" then flags = ti(parent.ColGroup) end
    local l, u, r, d = maskExtent(msk)
    local cands = candidates(parent, flags, x - l, y - u, x + r + 1, y + d + 1)
    local probe
    for i = 1, #cands do
      local o, m = cands[i][1], cands[i][2]
      if rawget(m, "__terrain") then probe = probe or E.landProbe() end
      if maskCheck(msk, x, y, m, o.PosX, o.PosY, probe) then return o end
    end
    return nil
  end

  -- CheckMaskAt(obj, mask, x, y, flags): layer-filtered overlap test against every object
  BF.CheckMaskAt = function(obj, msk, x, y, flags)
    x, y, flags = tf(x), tf(y), ti(flags)
    local probe
    for _, o in ipairs(E.worldObjs()) do
      if o ~= obj then
        if not (flags >= 0 and flags ~= ti(o.Layer)) then
          local m = maskOf(o)
          if m then
            if rawget(m, "__terrain") then probe = probe or E.landProbe() end
            if maskCheck(msk, x, y, m, o.PosX, o.PosY, probe) then return o end
          end
        end
      end
    end
    return nil
  end

  -- _TraceMask(parent, mask, x1,y1,x2,y2, flags, &xr,&yr, &xl,&yl, &ssolid, &xls,&yls): same Bresenham walk as CLineTracer
  BF._TraceMask = function(parent, mask, x1, y1, x2, y2, flags, xr, yr, xl, yl, ssolid, xls, yls)
    x1, y1, x2, y2, flags = ti(x1), ti(y1), ti(x2), ti(y2), ti(flags)
    if flags <= 0 and type(parent) == "table" then flags = ti(parent.ColGroup) end
    local l, u, r, d = maskExtent(mask)
    local cands = candidates(parent, flags, min(x1, x2) - l, min(y1, y2) - u, max(x1, x2) + r + 1, max(y1, y2) + d + 1)
    local probe
    for i = 1, #cands do
      if rawget(cands[i][2], "__terrain") then probe = E.landProbe() break end
    end
    local function find(x, y)
      for i = 1, #cands do
        local o, m = cands[i][1], cands[i][2]
        if maskCheck(mask, x, y, m, o.PosX, o.PosY, probe) then return o end
      end
      return nil
    end
    -- CLineTracer::Start
    local dx, dy = x2 - x1, y2 - y1
    local sx, sy, adx, ady = 0, 0, 0, 0
    if dx > 0 then sx, adx = 1, dx elseif dx < 0 then sx, adx = -1, -dx end
    if dy > 0 then sy, ady = 1, dy elseif dy < 0 then sy, ady = -1, -dy end
    local dir, err
    if adx >= ady then err, dir = adx, 0 else err, dir = ady, 1 end
    adx, ady = adx * 2, ady * 2
    local first, insolid = true, false
    xl.v, yl.v, xls.v, yls.v, ssolid.v = x1, y1, x1, y1, 0
    local cx, cy = x1, y1
    local done = false
    while not done do
      local obj = find(cx, cy)
      if obj ~= nil then
        if first then
          ssolid.v = 1
          insolid = true
        elseif not insolid then
          xr.v, yr.v = cx, cy
          return obj
        end
      elseif insolid then
        insolid = false
        xls.v, yls.v = cx, cy
      end
      xl.v, yl.v = cx, cy
      -- CLineTracer::NextPoint
      if dir == 0 then
        cx = cx + sx
        if cx == x2 then
          done = true
        elseif sy ~= 0 then
          err = err - ady
          if err < 0 then cy = cy + sy; err = err + adx end
        end
      else
        cy = cy + sy
        if cy == y2 then
          done = true
        elseif sx ~= 0 then
          err = err - adx
          if err <= 0 then cx = cx + sx; err = err + ady end
        end
      end
      first = false
    end
    xr.v, yr.v = x2, y2
    return nil
  end

  ---------------------------------------------------------------------
  -- soft objects: defaults at construction (engine ctor stage) and the physics step
  ---------------------------------------------------------------------
  local DEF = {
    CGObject = { A = 0.6, B = 0.6, C = 1.0, cl = 0, r = 3 },
    CMine = { A = 0.6, B = 0.6, C = 1.0, cl = OC.OC_Mine, r = 4 },
    COilDrum = { A = 0.0, B = 0.5, C = 1.0, cl = OC.OC_OilDrum, r = 9 },
    CCrate = { A = 0.0, B = 0.5, C = 1.0, cl = OC.OC_Crate, r = 8 },
    CGas = { A = 0.0, B = 0.0, C = 1.0, cl = OC.OC_Gas, r = 3 },
    CFire = { A = 0.0, B = 0.0, C = 1.0, cl = OC.OC_Fire, r = 2 },
    CArrow = { A = 0.0, B = 0.0, C = 1.0, cl = OC.OC_Arrow, r = 3 },
    CCanister = { A = 0.6, B = 0.6, C = 1.0, cl = OC.OC_Canister, r = 5 },
    CCross = { A = 0.0, B = 0.0, C = 1.0, cl = OC.OC_Cross, r = 6 },
    CMissile = { A = 0.6, B = 0.6, C = 1.0, cl = OC.OC_Missile, r = 3 },
    CFlame = { A = 0.0, B = 0.0, C = 1.0, cl = OC.OC_Flame, r = 2 },
    CSmoke = { A = 0.0, B = 0.0, C = 1.0, cl = OC.OC_Smoke, r = 2 },
    CCloud = { A = 0.0, B = 0.0, C = 1.0, cl = 23, r = 2 },
  }
  local ALL_GROUPS = 0xFFFFFF

  function E.softCtor(obj, root, parent, a2, a3, a4, a5)
    local d = DEF[root] or DEF.CGObject
    rawset(obj, "__soft", true)
    rawset(obj, "PosX", 0.0); rawset(obj, "PosY", 0.0); rawset(obj, "SpX", 0.0); rawset(obj, "SpY", 0.0)
    rawset(obj, "GravityFactor", 1.0); rawset(obj, "WindFactor", 0.0)
    rawset(obj, "DumpingA", d.A); rawset(obj, "DumpingB", d.B); rawset(obj, "DumpingC", d.C)
    rawset(obj, "IsMaterial", 1); rawset(obj, "InMidAir", 1); rawset(obj, "Stopped", 0); rawset(obj, "Sinking", 0)
    rawset(obj, "ObjState", 0); rawset(obj, "ClType", d.cl)
    rawset(obj, "ColGroup", ALL_GROUPS); rawset(obj, "MaskIndex", 0)
    rawset(obj, "SinkSpeedFactor", 1.0); rawset(obj, "SkimFactor", 0)
    local layer = E.layerOverride
    E.layerOverride = nil
    local radius = d.r
    if root == "CGObject" then
      layer = layer or ti(a2 or 0)
      local mi = ti(a3 or 0)
      rawset(obj, "MaskIndex", mi)
      radius = (mi == 2 and 4) or (mi == 9 and 9) or d.r
    end
    rawset(obj, "Layer", layer or 0)
    rawset(obj, "ColMask", circleMask(radius))
    -- spawn descriptor (CShootDesc / CFireDesc): position and velocity
    for _, a in ipairs({ a2, a3, a4, a5 }) do
      if type(a) == "table" then
        local c = rawget(a, "__cls")
        if c == "CShootDesc" or c == "CFireDesc" then
          rawset(obj, "PosX", tf(a.X)); rawset(obj, "PosY", tf(a.Y))
          rawset(obj, "SpX", tf(a.SpX)); rawset(obj, "SpY", tf(a.SpY))
          rawset(obj, "ShootData", a)
          if root == "CMissile" then
            local sd = R.builtinClasses.CShootDesc()
            for fname in pairs(E.SD_FIELDS) do sd[fname] = a[fname] end
            rawset(obj, "initdesc", sd)
          end
          break
        end
      end
    end
    -- CMine(parent, InitParams, ...): mine descriptor (Radius = -1 / 0 / 1 mine kind used by scripts)
    if root == "CMine" then
      for _, a in ipairs({ a2, a3, a4, a5 }) do
        if type(a) == "table" and rawget(a, "__cls") == "CMineParams" then rawset(obj, "InitParams", a) break end
      end
      if rawget(obj, "InitParams") == nil then
        rawset(obj, "InitParams", setmetatable({ __cls = "CMineParams" }, R.scriptMTFor("CMineParams")))
      end
    end
    -- CMissile(parent, launch, shootdesc, ...): the object keeps its own copy of the launch block
    if root == "CMissile" then
      for _, a in ipairs({ a2, a3, a4, a5 }) do
        if type(a) == "table" and rawget(a, "__cls") == "CWeaponLaunch" then
          local l = R.builtinClasses.CWeaponLaunch()
          E.copyLaunch(l, a)
          rawset(obj, "launchdata", l)
          local ok, gf = pcall(function() return l.gravityFactor end)
          if ok and type(gf) == "number" then rawset(obj, "GravityFactor", gf / 100.0) end
          local ok2, wf = pcall(function() return l.windFactor end)
          if ok2 and type(wf) == "number" then rawset(obj, "WindFactor", wf / 100.0) end
          break
        end
      end
    end
    return 0
  end

  F.SetLayerOverride = function(layer) E.layerOverride = ti(layer); return 0 end

  local function fld(o, k)
    local v = rawget(o, k)
    if v == nil then return 0.0 end
    return tf(v)
  end

  -- contact normal of mask m at integer position (x,y): mean direction from the contact pixels to the hotspot.
  -- returns hits, nx, ny  (hits == 0 -> not blocked)
  local function contact(m, x, y, probe, wantNormal)
    local ab = rawget(m, "Bmp")
    if not ab then return 0, 0, 0 end
    local ol = outlineOf(ab)
    local hx, hy = rawget(m, "HX"), rawget(m, "HY")
    local ox, oy = x - hx, y - hy
    local hits, sx, sy = 0, 0, 0
    for i = 1, #ol do
      local p = ol[i]
      if probe(ox + p[1], oy + p[2]) then
        hits = hits + 1
        if not wantNormal then return 1, 0, 0 end
        sx, sy = sx + (p[1] - hx), sy + (p[2] - hy)
      end
    end
    if hits == 0 then return 0, 0, 0 end
    local len = sqrt(sx * sx + sy * sy)
    if len < 1e-6 then return hits, 0, 0 end
    return hits, -sx / len, -sy / len
  end

  local function callScript(o, name, ...)
    local cls = rawget(o, "__cls")
    if cls and R.hasScriptChain(cls, name) then
      local ok, err = pcall(R.invoke, o, cls, name, ...)
      if not ok then once("soft:" .. cls .. name, "pxrt: %s::%s failed: %s", cls, name, tostring(err)) end
      return true
    end
    return false
  end

  function E.softStep(o)
    local mat = rawget(o, "IsMaterial")
    if mat == 0 or mat == false then return end
    local px, py = fld(o, "PosX"), fld(o, "PosY")
    local sx, sy = fld(o, "SpX"), fld(o, "SpY")
    local mask = rawget(o, "ColMask")
    local probe = E.landProbe()
    local collideTerrain = (ti(rawget(o, "ColGroup") or ALL_GROUPS) & 2) ~= 0 and type(mask) == "table" and rawget(mask, "Bmp") ~= nil
    local stopped = ti(rawget(o, "Stopped") or 0) ~= 0

    if stopped then
      if sx == 0 and sy == 0 then
        -- resting: stay while something still supports the object
        if not collideTerrain or contact(mask, floor(px), floor(py) + 1, probe, false) > 0 then return end
      end
      rawset(o, "Stopped", 0)
    end

    local env = E.envProxy
    sy = sy + tf(env.Gravity) * fld(o, "GravityFactor")
    sx = sx + tf(env.Wind) * fld(o, "WindFactor")

    -- water
    local water = E.waterLevel and E.waterLevel() or 0
    if water > 0 and py > water then
      if ti(rawget(o, "Sinking") or 0) == 0 then
        rawset(o, "Sinking", 1)
        callScript(o, "OnSink")
      end
      sx = sx * 0.92
      sy = min(sy, 1.2 * (fld(o, "SinkSpeedFactor") ~= 0 and fld(o, "SinkSpeedFactor") or 1.0))
      collideTerrain = false
    end

    local contactFloor, hitTerrain = false, false
    if collideTerrain then
      -- embedded start (spawned inside the ground): lift out
      if contact(mask, floor(px), floor(py), probe, false) > 0 then
        for k = 1, 12 do
          if contact(mask, floor(px), floor(py) - k, probe, false) == 0 then py = py - k; break end
        end
      end
      local dist = max(abs(sx), abs(sy))
      local steps = min(64, max(1, ceil(dist)))
      local dx, dy = sx / steps, sy / steps
      for _ = 1, steps do
        local nx, ny = px + dx, py + dy
        local hits, cnx, cny = contact(mask, floor(nx), floor(ny), probe, true)
        if hits == 0 then
          px, py = nx, ny
        else
          hitTerrain = true
          if cnx == 0 and cny == 0 then
            local len = sqrt(sx * sx + sy * sy)
            if len > 0 then cnx, cny = -sx / len, -sy / len else cnx, cny = 0, -1 end
          end
          local vn = sx * cnx + sy * cny
          if vn < 0 then
            local tx, ty = -cny, cnx
            local vt = sx * tx + sy * ty
            local bounce = abs(cnx) * fld(o, "DumpingA") + abs(cny) * fld(o, "DumpingB")
            local newvn = -vn * bounce
            if newvn < 0.15 then newvn = 0 end
            vt = vt * (0.98 * fld(o, "DumpingC"))
            sx, sy = tx * vt + cnx * newvn, ty * vt + cny * newvn
            if cny < -0.5 then contactFloor = true end
            if newvn == 0 and abs(vt) < 0.12 and cny < -0.6 then sx, sy = 0.0, 0.0 end
          end
          break
        end
      end
    else
      px, py = px + sx, py + sy
    end

    rawset(o, "PosX", px); rawset(o, "PosY", py)
    rawset(o, "SpX", sx); rawset(o, "SpY", sy)
    rawset(o, "InMidAir", contactFloor and 0 or 1)
    if contactFloor and sx == 0 and sy == 0 then rawset(o, "Stopped", 1) end

    if hitTerrain then callScript(o, "Collide", E.terrainObj, 0) end

    -- out of the world: free
    local W = E.levelSize()
    local sink = E.waterSinkY and E.waterSinkY() or 0
    if px < -600 or px > W + 600 or py < -4000 or (sink > 0 and py > sink + 40) then
      R.delete(o)
    end
  end

  function E.softStepSafe(o)
    rawset(o, "__stepped", true)
    local ok, err = pcall(E.softStep, o)
    if not ok then
      once("softstep:" .. tostring(rawget(o, "__cls")), "pxrt: softStep(%s) failed: %s", tostring(rawget(o, "__cls")), tostring(err))
    end
  end

  -- CGObject.Message: engine objects keep the original handler (CObject terminal); soft objects integrate on M_FRAME
  local CG = nat("CGObject")
  CG.Message = function(self, super, sender, mtype, size, mdata)
    if rawget(self, "__a") then
      return N.CObject.Message(self, super, sender, mtype, size, mdata)
    end
    mtype = ti(mtype)
    if mtype == FRAME and rawget(self, "__soft") and not rawget(self, "__stepped") then
      E.softStepSafe(self)
    end
    if E.forwardToKids then E.forwardToKids(self, sender, mtype, size, mdata) end
    return 0
  end
end
