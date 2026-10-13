-- pxrt_e_terrain: landscape / level size / water / collision (WA 3.8.1, see re_terrain.md)
return function(R, E)
  local rd, wr, rdU = E.rd, E.wr, E.rdU
  local ti, tf, once = R.ti, R.tf, R.once
  local floor = math.floor
  local N = R.natives
  local function nat(cls) N[cls] = N[cls] or {} return N[cls] end

  local function G() return E.ddGame() end
  local function P()
    local g = G()
    if g == 0 then return 0 end
    return rdU(g + 0x20)
  end
  local function CEnvA() return E.envAddr() end

  function E.levelSize()
    local g = G()
    if g == 0 then return 4096, 2048 end
    local w, h = rd(g + 0x77C0), rd(g + 0x77C4)
    if w <= 0 or h <= 0 then
      local p = P()
      local bm = p ~= 0 and rdU(p + 0x914) or 0
      if bm ~= 0 then w, h = rd(bm + 0x14), rd(bm + 0x18) end
    end
    if w <= 0 or h <= 0 then return 4096, 2048 end
    return w, h
  end

  -- pixel Y of the water surface (float, PX fixed)
  function E.waterLevel()
    local e = CEnvA()
    if e == 0 then return 0.0 end
    return rd(e + 0x228) + 0.0
  end
  function E.waterSinkY()
    local g = G()
    if g == 0 then return 0 end
    return rd(g + 0x5E4)
  end
  function E.setWaterLevel(v)
    local g, e = G(), CEnvA()
    if g == 0 or e == 0 then return end
    local y = floor(tf(v))
    writeMemU32(g + 0x5E0, y % 4294967296)
    writeMemU32(e + 0x228, y % 4294967296)
    local fn = E.WA_WATERLEVEL()
    if callThiscall and fn ~= 0 then
      pcall(callThiscall, fn, g)
      writeMemU32(g + 0x5E4, (readMemS16(g + 0x77AA) + 0x28) % 4294967296)
    end
  end

  -- 1-bpp collision bitmap probe, pixel coordinates
  local function solid(x, y)
    x, y = floor(x), floor(y)
    local p = P()
    if p == 0 then return false end
    local bm = rdU(p + 0x914)
    if bm == 0 then return false end
    if x < rd(bm + 0x1C) or x >= rd(bm + 0x24) or y < rd(bm + 0x20) or y >= rd(bm + 0x28) then return false end
    local data, stride = rdU(bm + 8), rd(bm + 0x10)
    local b = readMemU8(data + y * stride + (x >> 3))
    return ((b >> (x & 7)) & 1) == 1
  end
  E.landSolid = solid

  -- fast probe for many integer pixels in a row (caches the bitmap pointers once)
  function E.landProbe()
    local p = P()
    local bm = p ~= 0 and rdU(p + 0x914) or 0
    if bm == 0 then return function() return false end end
    local data, stride = rdU(bm + 8), rd(bm + 0x10)
    local x0, y0, x1, y1 = rd(bm + 0x1C), rd(bm + 0x20), rd(bm + 0x24), rd(bm + 0x28)
    return function(x, y)
      if x < x0 or x >= x1 or y < y0 or y >= y1 then return false end
      local b = readMemU8(data + y * stride + (x >> 3))
      return ((b >> (x & 7)) & 1) == 1
    end
  end

  function E.landColor(x, y)
    local p = P()
    if p == 0 or not callThiscall then return 0 end
    local ok, r = pcall(callThiscall, rdU(rdU(p) + 0x1C), p, floor(x), floor(y))
    return ok and (r % 256) or 0
  end

  function E.landIndestructible()
    local p = P()
    return p ~= 0 and rd(p + 0xB3C) ~= 0
  end

  function E.makeHole(radius, x, y)
    local p = P()
    if p == 0 or not callThiscall then return end
    local ok, err = pcall(callThiscall, rdU(rdU(p) + 0x08), p, floor(tf(radius)), floor(tf(x)), floor(tf(y)))
    if not ok then once("hole:" .. tostring(err), "pxrt: MakeHole failed: %s", tostring(err)) end
  end
  function E.applyMask(id, x, y)
    local p = P()
    if p == 0 or not callThiscall then return end
    local ok, err = pcall(callThiscall, rdU(rdU(p) + 0x0C), p, ti(id), floor(tf(x)), floor(tf(y)))
    if not ok then once("mask:" .. tostring(err), "pxrt: ApplyMask failed: %s", tostring(err)) end
  end
  function E.maskHitsLand(id, x, y)
    local p = P()
    if p == 0 or not callThiscall then return false end
    local ok, r = pcall(callThiscall, rdU(rdU(p) + 0x10), p, ti(id), floor(tf(x)), floor(tf(y)))
    return ok and (r % 256) ~= 0
  end
  function E.traceLand(x16, y16, dx16, dy16, n)
    local p = P()
    if p == 0 or not callThiscall then return -1 end
    local ok, r = pcall(callThiscall, rdU(rdU(p) + 0x24), p, x16, y16, dx16, dy16, n)
    if not ok then return -1 end
    if r >= 2147483648 then r = r - 4294967296 end
    return r
  end

  -- PX CEnv::CheckCollision(Ex): terrain probe at the (fixed) position, then object-vs-object.
  -- Returns the colliding object proxy, a non-zero terrain marker object (0 = none).
  local TERRAIN = setmetatable({ __cls = "CGObject", __terrain = true }, { __index = function() return 0 end })
  E.TERRAIN = TERRAIN
  function E.checkCollision(obj, x, y, mask, flags)
    x, y = tf(x), tf(y)
    -- circle probe: centre plus 4 points; radius from the object (+0xDC is 16.16 size)
    local r = 0
    local a = type(obj) == "table" and rawget(obj, "__a") or 0
    if a ~= 0 then r = rd(a + 0xDC) / 65536.0 end
    if solid(x, y) then return TERRAIN end
    if r > 1 then
      if solid(x + r, y) or solid(x - r, y) or solid(x, y + r) or solid(x, y - r) then return TERRAIN end
    end
    local fn = a ~= 0 and E.WA_HITTEST() or 0
    if fn ~= 0 and callStdcall and E.okAddr(CEnvA()) then
      local ok, hit = pcall(callStdcall, fn, CEnvA(), a, floor(x * 65536.0), floor(y * 65536.0),
        rd(a + 0xDC), rd(a + 0x34))
      if ok and hit ~= 0 and hit ~= a then return E.proxyAt(hit % 4294967296) end
    end
    return nil
  end

  local LAND = nat("CLandscape")
  LAND.MakeHole = function(self, super, radius, x, y) E.makeHole(radius, x, y) return 0 end
  LAND.ApplyMask = function(self, super, idx, x, y) E.applyMask(idx, x, y) return 0 end
  LAND.ApplyCustomMask = function() once("acm", "pxrt: ApplyCustomMask unsupported") return 0 end
  LAND.Draw = function() once("landdraw", "pxrt: CLandscape::Draw unsupported") return 0 end

  local BM = nat("CBitmask")
  BM.GetPixel = function(self, super, x, y) return solid(tf(x), tf(y)) and 1 or 0 end
  BM.CheckPoint = BM.GetPixel
  BM.SetPixel = function() once("bmset", "pxrt: land BitMask writes unsupported") return 0 end
end
