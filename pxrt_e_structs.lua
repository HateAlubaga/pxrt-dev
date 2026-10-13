-- pxrt_e_structs: memory-backed value structs (CMessageData, CShootDesc, CWeaponLaunch)
-- Message / launch data must live in real memory: the engine reads and writes them.
return function(R, E)
  local rd, wr, rdU = E.rd, E.wr, E.rdU
  local ti, tf, once, log = R.ti, R.tf, R.once, R.log
  local BC, N = R.builtinClasses, R.natives
  local F = R.F
  local FIX = 65536.0
  local type, rawget, rawset, setmetatable, pairs = type, rawget, rawset, setmetatable, pairs

  ---------------------------------------------------------------------
  -- buffer pool (zeroed on acquire, returned to the pool on __gc)
  ---------------------------------------------------------------------
  local pools = {}
  local function acquire(size)
    local p = pools[size]
    if not p then p = {}; pools[size] = p end
    local a = table.remove(p)
    if not a then
      local ok, v = pcall(memAlloc, size)
      if not ok or type(v) ~= "number" or v == 0 then
        once("memalloc", "pxrt: memAlloc(%d) failed", size)
        return 0
      end
      a = v
    end
    pcall(memFill, a, 0, size)
    return a
  end
  local function release(size, a)
    if a and a ~= 0 then
      local p = pools[size]
      if not p then p = {}; pools[size] = p end
      p[#p + 1] = a
    end
  end
  E.acquireBuf, E.releaseBuf = acquire, release

  ---------------------------------------------------------------------
  -- generic field readers/writers
  ---------------------------------------------------------------------
  local function getKind(a, kind)
    if kind == "fixed" or kind == "f" then return rd(a) / FIX end
    if kind == "ptr" then return rdU(a) end
    return rd(a)
  end
  local function setKind(a, kind, v)
    if kind == "fixed" or kind == "f" then wr(a, tf(v) * FIX)
    else wr(a, ti(v)) end
  end
  E.getKind, E.setKind = getKind, setKind

  ---------------------------------------------------------------------
  -- CMessageData: params[i] (int) and fparams[i] (fixed) view the same dwords
  ---------------------------------------------------------------------
  local MSG_SIZE = 1056
  local function viewMT(kind)
    return {
      __index = function(t, i)
        local base = rawget(t, "__b")
        if type(i) ~= "number" or not base or base == 0 then return 0 end
        i = ti(i)
        if i < 0 or i >= 256 then return 0 end
        return getKind(base + 4 * i, kind)
      end,
      __newindex = function(t, i, v)
        local base = rawget(t, "__b")
        if type(i) ~= "number" or not base or base == 0 then return end
        i = ti(i)
        if i < 0 or i >= 256 then return end
        setKind(base + 4 * i, kind, v)
      end,
    }
  end
  local paramsMT, fparamsMT = viewMT("i"), viewMT("fixed")
  local msgBase = R.scriptMTFor("CMessageData")
  local msgMT = {}
  local function bufOf(t)
    local a = rawget(t, "__a")
    if a then return a end
    a = rawget(t, "__buf")
    if not a then
      a = acquire(MSG_SIZE)
      rawset(t, "__buf", a)
      rawset(t, "__own", true)
    end
    return a
  end
  msgMT.__index = function(t, k)
    if k == "params" then
      local v = setmetatable({ __b = bufOf(t) }, paramsMT); rawset(t, "params", v); return v
    elseif k == "fparams" then
      local v = setmetatable({ __b = bufOf(t) }, fparamsMT); rawset(t, "fparams", v); return v
    elseif k == "__addr" then
      return bufOf(t)
    end
    return msgBase.__index(t, k)
  end
  msgMT.__gc = function(t)
    if rawget(t, "__own") then release(MSG_SIZE, rawget(t, "__buf")) end
  end
  BC.CMessageData = function()
    return setmetatable({ __cls = "CMessageData" }, msgMT)
  end
  function E.msgDataAt(addr)
    if not E.okAddr(addr) then return nil end
    return setmetatable({ __a = addr, __cls = "CMessageData" }, msgMT)
  end
  N.CMessageData = {
    GetParameter = function(self, super, i) return rd(bufOf(self) + 4 * ti(i)) end,
  }
  -- address of a message-data object (for passing to the engine); non-object -> 0
  function E.msgAddr(m)
    if type(m) ~= "table" then return 0 end
    local a = rawget(m, "__a")
    if a then return a end
    if rawget(m, "__cls") == "CMessageData" then return bufOf(m) end
    return 0
  end

  ---------------------------------------------------------------------
  -- CShootDesc (0x2C bytes)
  ---------------------------------------------------------------------
  local SD_SIZE = 0x30
  local SD_FIELDS = {
    Team = { 0x00, "i" }, Worm = { 0x04, "i" }, X = { 0x08, "f" }, Y = { 0x0C, "f" },
    SpX = { 0x10, "f" }, SpY = { 0x14, "f" }, AddX = { 0x18, "f" }, AddY = { 0x1C, "f" },
    Child = { 0x20, "i" }, Extra1 = { 0x24, "i" }, Extra2 = { 0x28, "i" },
  }
  E.SD_FIELDS = SD_FIELDS
  local sdBase = R.scriptMTFor("CShootDesc")
  local sdMT = {}
  local function sdBuf(t)
    local a = rawget(t, "__a")
    if a then return a end
    a = rawget(t, "__buf")
    if not a then
      a = acquire(SD_SIZE)
      rawset(t, "__buf", a)
      rawset(t, "__own", true)
    end
    return a
  end
  sdMT.__index = function(t, k)
    local s = SD_FIELDS[k]
    if s then return getKind(sdBuf(t) + s[1], s[2]) end
    if k == "__addr" then return sdBuf(t) end
    return sdBase.__index(t, k)
  end
  sdMT.__newindex = function(t, k, v)
    local s = SD_FIELDS[k]
    if s then setKind(sdBuf(t) + s[1], s[2], v) return end
    rawset(t, k, v)
  end
  sdMT.__gc = function(t)
    if rawget(t, "__own") then release(SD_SIZE, rawget(t, "__buf")) end
  end
  BC.CShootDesc = function() return setmetatable({ __cls = "CShootDesc" }, sdMT) end
  function E.sdAt(addr)
    if not E.okAddr(addr) then return nil end
    return setmetatable({ __a = addr, __cls = "CShootDesc" }, sdMT)
  end
  function E.sdAddr(s)
    if type(s) ~= "table" then return 0 end
    local a = rawget(s, "__a")
    if a then return a end
    if rawget(s, "__cls") == "CShootDesc" then return sdBuf(s) end
    return 0
  end

  ---------------------------------------------------------------------
  -- CWeaponLaunch (0x178 bytes; lives at weapon entry +0x3C).
  -- Field map comes from lualib pxl_launch (generated from re_launch) or E.launchFields.
  -- spec = { off = <launch-relative offset>, kind = "int"|"fixed"|"bool"|"enum"|"ptr" }
  ---------------------------------------------------------------------
  local LAUNCH_SIZE = 0x178
  local function loadLaunchFields()
    if E.launchFields then return E.launchFields end
    local t
    local ok, v = pcall(require, "pxl_launch")
    if ok and type(v) == "table" then t = v end
    E.launchFields = t or {}
    return E.launchFields
  end
  local TOP, SUBS
  local function ensureMaps()
    if TOP then return end
    TOP, SUBS = {}, {}
    for name, spec in pairs(loadLaunchFields()) do
      local pre, rest = name:match("^([%w_]+)%.([%w_]+)$")
      if pre then
        SUBS[pre] = SUBS[pre] or {}
        SUBS[pre][rest] = spec
      else
        TOP[name] = spec
      end
    end
  end
  local launchBase = R.scriptMTFor("CWeaponLaunch")
  local subMT = {}
  subMT.__index = function(t, k)
    local spec = rawget(t, "__f")[k]
    if spec then return getKind(rawget(t, "__b") + spec.off, spec.kind) end
    if type(k) == "string" and not k:find("^__") then
      once("launchsub:" .. rawget(t, "__n") .. "." .. tostring(k), "pxrt: unknown launch field %s.%s", rawget(t, "__n"), tostring(k))
    end
    return 0
  end
  subMT.__newindex = function(t, k, v)
    local spec = rawget(t, "__f")[k]
    if spec then setKind(rawget(t, "__b") + spec.off, spec.kind, v) return end
    once("launchsubw:" .. rawget(t, "__n") .. "." .. tostring(k), "pxrt: unknown launch field write %s.%s", rawget(t, "__n"), tostring(k))
  end
  local launchMT = {}
  local function lBuf(t)
    local a = rawget(t, "__a")
    if a then return a end
    a = rawget(t, "__buf")
    if not a then
      a = acquire(LAUNCH_SIZE)
      rawset(t, "__buf", a)
      rawset(t, "__own", true)
    end
    return a
  end
  launchMT.__index = function(t, k)
    ensureMaps()
    local spec = TOP[k]
    if spec then return getKind(lBuf(t) + spec.off, spec.kind) end
    local sub = SUBS[k]
    if sub then
      local cache = rawget(t, "__subs")
      if not cache then cache = {}; rawset(t, "__subs", cache) end
      local v = cache[k]
      if not v then v = setmetatable({ __f = sub, __b = lBuf(t), __n = k }, subMT); cache[k] = v end
      return v
    end
    if k == "__addr" then return lBuf(t) end
    if type(k) == "string" and not k:find("^__") then
      local m = launchBase.__index(t, k)
      if type(m) == "function" then return m end
      once("launchf:" .. k, "pxrt: unknown launch field %s", k)
    end
    return 0
  end
  launchMT.__newindex = function(t, k, v)
    ensureMaps()
    local spec = TOP[k]
    if spec then setKind(lBuf(t) + spec.off, spec.kind, v) return end
    if SUBS[k] then once("launchsub:" .. k, "pxrt: cannot assign launch.%s", k) return end
    once("launchw:" .. tostring(k), "pxrt: unknown launch field write %s", tostring(k))
  end
  launchMT.__gc = function(t)
    if rawget(t, "__own") then release(LAUNCH_SIZE, rawget(t, "__buf")) end
  end
  BC.CWeaponLaunch = function() return setmetatable({ __cls = "CWeaponLaunch" }, launchMT) end
  local launchViews = setmetatable({}, { __mode = "v" })
  function E.launchAt(addr)
    if not E.okAddr(addr) then return nil end
    local v = launchViews[addr]
    if v then return v end
    v = setmetatable({ __a = addr, __cls = "CWeaponLaunch" }, launchMT)
    launchViews[addr] = v
    return v
  end
  function E.launchAddr(l)
    if type(l) ~= "table" then return 0 end
    local a = rawget(l, "__a")
    if a then return a end
    if rawget(l, "__cls") == "CWeaponLaunch" then return lBuf(l) end
    return 0
  end
  -- copy a launch block (script object or view) into another
  function E.copyLaunch(dst, src)
    local d, s = E.launchAddr(dst), E.launchAddr(src)
    if d ~= 0 and s ~= 0 then pcall(memCopy, d, s, LAUNCH_SIZE) end
  end

  ---------------------------------------------------------------------
  -- memory-aware F.zero
  ---------------------------------------------------------------------
  local oldZero = F.zero
  local SIZES = { CMessageData = MSG_SIZE, CShootDesc = SD_SIZE, CWeaponLaunch = LAUNCH_SIZE }
  F.zero = function(x)
    local target = x
    if type(x) == "table" and R.isref(x) then target = x.v end
    if type(target) == "table" then
      local c = rawget(target, "__cls")
      local sz = c and SIZES[c]
      if sz then
        local a = rawget(target, "__a") or rawget(target, "__buf")
        if not a then a = target.__addr end
        if a and a ~= 0 then pcall(memFill, a, 0, sz) end
        return 0
      end
    end
    return oldZero(x)
  end

  ---------------------------------------------------------------------
  -- weapon table
  ---------------------------------------------------------------------
  function E.weaponTableAddr()
    local g = E.ddGame()
    if g == 0 then return 0 end
    return rdU(g + 0x510)
  end
  function E.weaponStructAddr(id)
    local base = E.weaponTableAddr()
    if base == 0 then return 0 end
    return base + ti(id) * 0x1D0
  end
end
