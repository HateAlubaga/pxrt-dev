-- pxrt_engine.lua -- engine layer of the ProjectX script runtime.
-- Memory-backed proxies of WA objects, K constants, F builtins, builtin classes and
-- the hooks that feed WA events into the script object model of pxrt_core.
-- Loaded once from pxrt_core (require "pxrt_engine"); R = _G.__pxrt.
local R = _G.__pxrt
if not R or R.E then return R end
local E = {}
R.E = E

local floor = math.floor
local type, tostring, tonumber, pairs, ipairs, select = type, tostring, tonumber, pairs, ipairs, select
local rawget, rawset, setmetatable, getmetatable = rawget, rawset, setmetatable, getmetatable
local pcall = pcall
local mtype = math.type
local log, once = R.log, R.once
local T, ti, tf, isnull = R.T, R.ti, R.tf, R.isnull

---------------------------------------------------------------------------
-- raw memory helpers
---------------------------------------------------------------------------
local FIX = 65536.0
local rd = readMemInt
-- per-dispatch cache of the current worm (script-visible GetCurrentWorm). Valid only inside one engine message dispatch
-- (E.tgHold > 0) and dropped by every engine write, engine call and the hook exit: see BF.GetCurrentWorm in pxrt_e_funcs.
local CW = { have = false, val = nil }
E.CW = CW
local function wr(a, v)
  CW.have = false
  if v ~= v then v = 0 end
  if mtype(v) ~= "integer" then v = floor(v + 0.5) end
  if v > 2147483647 then v = 2147483647 elseif v < -2147483648 then v = -2147483648 end
  writeMemInt(a, v)
end
local function rdf(a) return rd(a) / FIX end
local function wrf(a, v) wr(a, tf(v) * FIX) end
local function rdU(a) return readMemU32(a) end
E.rd, E.wr, E.rdf, E.wrf, E.rdU = rd, wr, rdf, wrf, rdU
local function okAddr(a) return type(a) == "number" and a > 0x10000 and a < 0x7FFF0000 end
E.okAddr = okAddr

---------------------------------------------------------------------------
-- engine addresses (WA 3.8.1)
---------------------------------------------------------------------------
-- CTurnGame address: the host call is repeated hundreds of times per frame by scripts. Inside one engine message
-- dispatch (E.tgHold > 0) the address cannot change, so it is cached for that dispatch only.
local tgCache
E.tgHold = 0
local function turnGameAddr()
  local c = tgCache
  if c then return c end
  local ok, a = pcall(getTurnGameAddr)
  if ok and type(a) == "number" and a ~= 0 then
    if E.tgHold > 0 then tgCache = a end
    return a
  end
  return 0
end
function E.tgRelease() tgCache = nil; CW.have = false; CW.val = nil end
E.turnGameAddr = turnGameAddr
local function ddGame()
  local tg = turnGameAddr()
  if tg == 0 then return 0 end
  return rdU(tg + 0x2C)
end
E.ddGame = ddGame
local function envAddr()
  local dd = ddGame()
  if dd == 0 then return 0 end
  return rdU(dd + 0x528)
end
E.envAddr = envAddr
local function gameInfoAddr()
  local dd = ddGame()
  if dd == 0 then return 0 end
  return rdU(dd + 0x24)
end
E.gameInfoAddr = gameInfoAddr

---------------------------------------------------------------------------
-- WA.exe code addresses
---------------------------------------------------------------------------
-- WA 3.8.1 is linked at 0x400000 but marked DYNAMIC_BASE, so Windows maps it at another base on every boot
-- (0x680000 and 0x8F0000 were seen in crash dumps). Engine functions are written with their linked address and go
-- through E.waFn: it rebases the address and compares the function's own bytes before anything may call it.
local WA_LINKED, WA_IMAGE_SIZE, WA_TIMESTAMP = 0x400000, 0x584000, 0x5FA8504C
local function isWaImage(b)
  if readMemU16(b) ~= 0x5A4D then return false end   -- "MZ"
  local pe = readMemU32(b + 0x3C)
  if pe < 0x40 or pe > 0x400 then return false end
  local h = b + pe
  return readMemU32(h) == 0x4550 and readMemU32(h + 8) == WA_TIMESTAMP and readMemU32(h + 0x50) == WA_IMAGE_SIZE
end
local waBase   -- nil: not searched yet, false: not found
local function waImageBase()
  if waBase ~= nil then return waBase end
  local b
  -- CTurnGame's vtable lies inside the image: only ~90 candidates below it
  local tg = turnGameAddr()
  local vt = tg ~= 0 and rdU(tg) or 0
  if okAddr(vt) then
    local top = vt - vt % 0x10000
    for c = top, math.max(0x10000, top - WA_IMAGE_SIZE), -0x10000 do
      if isWaImage(c) then b = c break end
    end
  end
  if not b then
    for c = 0x10000, 0x7FFF0000, 0x10000 do
      if isWaImage(c) then b = c break end
    end
  end
  waBase = b or false
  if b then log("pxrt: WA.exe image at %X (linked at %X)", b, WA_LINKED)
  else log("pxrt: WA.exe image not found: engine function calls disabled") end
  return waBase
end
E.waImageBase = waImageBase
-- E.waFn(linked, sig): live address of the WA function linked at `linked`, or 0 (never call a 0).
-- sig = the function's bytes 8..23 as linked (no relocations there). Bytes 0..7 are not compared: a hook of the
-- host or another module may have patched a jmp over them, and calling through that hook is what WA itself does.
local waFns = {}
function E.waFn(linked, sig)
  local a = waFns[linked]
  if a then return a end
  a = 0
  local b = waImageBase()
  if b then
    local live = linked - WA_LINKED + b
    local got = readMemBytes(live + 8, #sig)
    if got == sig then
      a = live
    else
      local hex = type(got) == "string" and got:gsub(".", function(c) return string.format("%02X", c:byte()) end) or tostring(got)
      log("pxrt: WA function %X (live %X) has unexpected code %s: not called", linked, live, hex)
    end
  end
  waFns[linked] = a
  return a
end
-- the engine functions pxrt calls
E.WA_FIREWEAPON = function() return E.waFn(0x51EE60, "\x00\x00\x00\x00\x8B\x50\x30\x83\xC2\xFF\x83\xFA\x03\x57\x0F\x87") end
E.WA_RENDERWORM = function() return E.waFn(0x50FCD0, "\x24\x08\x50\x8D\x4C\x24\x14\x51\x8D\x54\x24\x14\x52\x8D\x44\x24") end
E.WA_SETANIM = function() return E.waFn(0x4F5BD0, "\x5E\x1C\x83\xC3\x01\x81\xE3\x0F\x00\x00\x80\x79\x05\x4B\x83\xCB") end
E.WA_WORMANIMSTATE = function() return E.waFn(0x512E80, "\x54\x24\x0C\x53\x8B\x5C\x24\x14\x55\x8B\x6C\x24\x10\x57\x8B\xF8") end
E.WA_EXPLOSION = function() return E.waFn(0x548080, "\x08\x04\x00\x00\x8B\x55\x08\x89\x4C\x24\x08\x8B\x4D\x10\x89\x54") end
E.WA_WATERLEVEL = function() return E.waFn(0x540190, "\xA4\x77\x00\x00\x05\xA0\x00\x00\x00\xC1\xE0\x10\x81\xC2\x00\x00") end
E.WA_HITTEST = function() return E.waFn(0x4FB9D0, "\x8B\x83\x40\x02\x00\x00\x8B\x40\x24\x05\x24\xD9\x00\x00\x80\x78") end

-- hash store: [task+0x24] -> table of 256 buckets; node {next,type,index,object}
local function hashGet(anyTask, htype, hindex)
  if not (anyTask > 0x10000 and anyTask < 0x7FFF0000) then return 0 end   -- okAddr, inlined (numbers only)
  local tbl = rdU(anyTask + 0x24)
  if not (tbl > 0x10000 and tbl < 0x7FFF0000) then return 0 end
  local node = rdU(tbl + 4 * ((hindex * 17 + htype) & 0xFF))
  local guard = 0
  while node > 0x10000 and node < 0x7FFF0000 and guard < 64 do
    if rd(node + 4) == htype and rd(node + 8) == hindex then return rdU(node + 0xC) end
    node = rdU(node)
    guard = guard + 1
  end
  return 0
end
E.hashGet = hashGet
function E.hashObject(htype, hindex)
  local tg = turnGameAddr()
  if tg == 0 then return 0 end
  return hashGet(tg, htype, hindex)
end

---------------------------------------------------------------------------
-- class ids ([task+0x20]) -> script class names
---------------------------------------------------------------------------
local CLASS_BY_ID = {
  [6] = "CTurnGame", [7] = "CFilter", [8] = "CMine", [9] = "CCanister", [10] = "CTeam", [11] = "CMissile",
  [12] = "CArrow", [15] = "CCrate", [16] = "CFlame", [17] = "CAirStrike", [18] = "CWorm", [19] = "COldWorm",
  [21] = "CCross", [22] = "CSmoke", [23] = "CCloud", [24] = "CFire", [25] = "CGas", [28] = "CLandscape",
  [30] = "COilDrum",
}
E.CLASS_BY_ID = CLASS_BY_ID
local OC_BY_NAME = { OC_Worm = 18, OC_Mine = 8, OC_Missile = 11, OC_Crate = 15, OC_OilDrum = 30, OC_Landscape = 28,
  OC_Cross = 21, OC_AirStrike = 17, OC_Team = 10, OC_Fire = 24, OC_Flame = 16, OC_Arrow = 12, OC_Smoke = 22,
  OC_SeaBubble = 27, OC_Gas = 25, OC_DragonBall = 26, OC_OldWorm = 19, OC_Filter = 7, OC_GameTask = 2,
  OC_Canister = 9, OC_Task = 1, OC_Collideable = 3 }
E.OC_BY_NAME = OC_BY_NAME

---------------------------------------------------------------------------
-- field tables: name -> {offset, kind}.  kinds: i int, f fixed16.16 <-> float, u8, p pointer->proxy,
-- gs DDGame proxy, w weapon struct proxy
---------------------------------------------------------------------------
local FIELDS = {}
E.FIELDS = FIELDS
FIELDS.CObject = {
  Parent = { 0x04, "p" }, StoreIndex = { 0x18, "i" }, StoreType = { 0x1C, "i" }, ClType = { 0x20, "i" },
  Store = { 0x24, "p" }, GS = { 0x2C, "gs" },
}
FIELDS.CGObject = {
  ObjState = { 0x44, "i" }, IsMaterial = { 0x3C, "i" }, DumpingC = { 0x4C, "f" }, SinkSpeedFactor = { 0x54, "f" },
  SpeedDivider = { 0x58, "f" }, WindFactor = { 0x5C, "f" }, GravityFactor = { 0x60, "f" }, DumpingA = { 0x6C, "f" },
  DumpingB = { 0x70, "f" }, SpeedDividerB = { 0x78, "f" }, PosX = { 0x84, "f" }, PosY = { 0x88, "f" },
  SpX = { 0x90, "f" }, SpY = { 0x94, "f" }, SkimFactor = { 0xA8, "i" }, Stopped = { 0xAC, "i" },
  Sinking = { 0xB0, "i" }, InMidAir = { 0xB8, "i" },
}
FIELDS.CWorm = {
  WormTeam = { 0xFC, "i" }, WormNumber = { 0x100, "i" }, SomeControlBased = { 0x104, "i" }, LabelColor = { 0x10C, "i" },
  KnockedOut = { 0x140, "i" }, WeaponN = { 0x170, "i" }, WeaponAmmo = { 0x174, "i" }, DispHealth = { 0x178, "i" },
  TargHealth = { 0x17C, "i" }, ShowHealthChgLbl = { 0x184, "i" }, GotDamage = { 0x188, "i" }, TurnSide = { 0x1A8, "i" },
  PressedUp = { 0x1D4, "i" }, PressedDown = { 0x1D8, "i" }, PressedLeft = { 0x1DC, "i" }, PressedRight = { 0x1E0, "i" },
  JetFuel = { 0x220, "i" }, FirePower = { 0x248, "f" }, FireAngle = { 0x24C, "f" }, FireAngleSmoothed = { 0x270, "f" },
  nTotalShoots = { 0x284, "i" }, nAvalShoots = { 0x288, "i" }, CanFire = { 0x28C, "i" }, nShooted = { 0x290, "i" },
  nShoots = { 0x294, "i" }, TimeToFire = { 0x298, "i" }, WeapLatency = { 0x2A4, "i" }, WeaponFuse = { 0x2BC, "i" },
  WeaponBounce = { 0x2C0, "i" }, WeaponCount = { 0x2C4, "i" }, SelectX = { 0x2E0, "i" }, SelectY = { 0x2E4, "i" },
  AnimHelper = { 0x368, "p" }, Anim = { 0x368, "anim" }, CurWeapon = { 0x36C, "w" },
}
FIELDS.CTurnGame = {
  num_teams = { 0xE8, "i" }, NextColor = { 0xEC, "ia" }, CurTeam = { 0x12C, "i" }, CurWorm = { 0x130, "i" },
  CurTeamB = { 0x134, "i" }, TimerDisabled = { 0x164, "i" }, RetreatTimer = { 0x178, "i" }, RoundTimer = { 0x184, "i" },
  TurnTimerDisplay = { 0x188, "i" }, TurnTimer = { 0x18C, "i" }, Timer = { 0x18C, "i" },
}
FIELDS.CTeam = { Active = { 0x3C, "i" }, CurWorm = { 0x48, "i" }, TeamIdx = { 0x38, "i" } }
FIELDS.CMissile = {
  Timer = { 0x37C, "i" }, ActionType = { 0x330, "i" }, IsFlying = { 0x394, "i" },
}
-- DDGame (K.GS) and CEnv
FIELDS.CGameState = {}
FIELDS.CEnv = { Gravity = { 0x22C, "f" }, Wind = { 0x230, "f" } }

local INHERIT = {
  CWorm = "CGObject", CMissile = "CGObject", CMine = "CGObject", CCrate = "CGObject", COilDrum = "CGObject",
  CGas = "CGObject", CArrow = "CGObject", CCanister = "CGObject", CCross = "CGObject", CFire = "CGObject",
  CFlame = "CGObject", CAirStrike = "CGObject", CSmoke = "CGObject", CCloud = "CGObject", COldWorm = "CGObject",
  CGObject = "CObject", CTurnGame = "CObject", CTeam = "CObject", CFilter = "CObject", CLandscape = "CObject",
}
local specCache = {}   -- cls -> name -> spec | false (FIELDS/INHERIT are static after load)
local function fieldSpec(cls, name)
  local sc = specCache[cls]
  if not sc then sc = {}; specCache[cls] = sc end
  local hit = sc[name]
  if hit ~= nil then return hit or nil end
  local c = cls
  while c do
    local ft = FIELDS[c]
    if ft then
      local s = ft[name]
      if s then sc[name] = s; return s end
    end
    c = INHERIT[c]
  end
  sc[name] = false
  return nil
end
E.fieldSpec = fieldSpec

---------------------------------------------------------------------------
-- proxies
---------------------------------------------------------------------------
local proxies = setmetatable({}, { __mode = "v" })
E.proxies = proxies
local proxyMT = {}
local classMT = {}
-- fixed-size int array living in engine memory (e.g. CTurnGame.NextColor[6])
local intArrays = setmetatable({}, { __mode = "v" })
function E.intArrayAt(addr, n)
  local v = intArrays[addr]
  if v then return v end
  v = setmetatable({}, {
    __index = function(_, i)
      if type(i) ~= "number" then return nil end
      i = R.ti(i)
      if i < 0 or i >= n then return 0 end
      return rd(addr + 4 * i)
    end,
    __newindex = function(_, i, x)
      if type(i) ~= "number" then return end
      i = R.ti(i)
      if i < 0 or i >= n then return end
      wr(addr + 4 * i, R.ti(x))
    end,
  })
  intArrays[addr] = v
  return v
end
local function getMT(cls)
  local mt = classMT[cls]
  if mt then return mt end
  local scriptIndex = R.scriptMTFor(cls).__index
  mt = {}
  mt.__index = function(t, k)
    if type(k) ~= "string" then return nil end
    local a = rawget(t, "__a")
    local spec = fieldSpec(cls, k)
    if spec then
      local off, kind = spec[1], spec[2]
      if kind == "i" then return rd(a + off)
      elseif kind == "f" then return rd(a + off) / FIX
      elseif kind == "p" then return E.proxyAt(rdU(a + off))
      elseif kind == "w" then return E.weaponAt(rdU(a + off), a)
      elseif kind == "anim" then return E.animAt(rdU(a + off))
      elseif kind == "gs" then return E.gs()
      elseif kind == "ia" then return E.intArrayAt(a + off, 6)
      end
    end
    local sp = E.special[cls]
    if sp then
      local f = sp[k]
      if f then return f(t, a) end
    end
    return scriptIndex(t, k)
  end
  mt.__newindex = function(t, k, v)
    local a = rawget(t, "__a")
    local spec = type(k) == "string" and fieldSpec(cls, k)
    if spec then
      local off, kind = spec[1], spec[2]
      if kind == "f" then wrf(a + off, v)
      elseif kind == "p" or kind == "w" or kind == "gs" then wr(a + off, ti(v))
      else wr(a + off, ti(v)) end
      return
    end
    local sp = E.specialSet[cls]
    if sp and sp[k] then sp[k](t, a, v) return end
    rawset(t, k, v)
  end
  mt.__tostring = function(t) return string.format("%s@%X", cls, rawget(t, "__a") or 0) end
  classMT[cls] = mt
  return mt
end
E.special, E.specialSet = {}, {}

local function classAt(a)
  local id = rd(a + 0x20)
  local c = CLASS_BY_ID[id]
  if c then return c end
  return "CGObject"
end

function E.proxyAt(a, cls)
  if not okAddr(a) then return nil end
  local p = proxies[a]
  if p then return p end
  -- a miss may be the first sight of a newly born object: the host's birth log must be read first, else a birth
  -- read later would retire the object constructed here
  if E.syncBirths then E.syncBirths() end
  cls = cls or classAt(a)
  p = setmetatable({ __a = a, __cls = cls }, getMT(cls))
  proxies[a] = p
  if E.onFirstSight then E.onFirstSight(p, a, cls) end
  return p
end
E.classAt = classAt
-- worm animators (CSpriteAnim, WA vtable 0x6640CC) are not tasks: plain proxies outside the task proxy table
local animProxies = setmetatable({}, { __mode = "v" })
function E.animAt(a)
  if not okAddr(a) then return nil end
  local p = animProxies[a]
  if not p then
    p = setmetatable({ __a = a, __cls = "CSpriteAnim" }, getMT("CSpriteAnim"))
    animProxies[a] = p
  end
  return p
end
-- cast: reinterpret as a class (used by __R__.cast)
function E.castTo(cls, v)
  if type(v) ~= "table" then return v end
  local a = rawget(v, "__a")
  if not a then return v end
  if rawget(v, "__cls") == cls then return v end
  return E.proxyAt(a)
end

-- DDGame / gameinfo / env proxies (singletons, always re-read)
local gsProxy = setmetatable({ __a = 0, __cls = "CGameState" }, {})
local envProxy = setmetatable({ __a = 0, __cls = "CEnv" }, {})
local infoProxy = setmetatable({ __a = 0, __cls = "CGameInfo" }, {})
E.gsProxy, E.envProxy, E.infoProxy = gsProxy, envProxy, infoProxy
function E.gs() gsProxy.__a = ddGame() return gsProxy end

-- weapon structs: proxy carries the id (for CheckName etc.)
local weaponProxies = setmetatable({}, { __mode = "v" })
function E.weaponAt(wsAddr, wormAddr)
  if not okAddr(wsAddr) then return nil end
  local w = weaponProxies[wsAddr]
  if not w then
    w = setmetatable({ __a = wsAddr, __cls = "CWeapon" }, E.weaponMT)
    weaponProxies[wsAddr] = w
  end
  if wormAddr then rawset(w, "__worm", wormAddr) end
  return w
end
E.weaponMT = {}

---------------------------------------------------------------------------
-- load the remaining engine modules (each one is a function(R, E))
---------------------------------------------------------------------------
local MODULES = { "pxrt_e_consts", "pxrt_e_game", "pxrt_e_funcs", "pxrt_e_structs", "pxrt_e_classes", "pxrt_e_terrain", "pxrt_e_pseudo", "pxrt_e_soft", "pxrt_e_extra", "pxrt_e_quads", "pxrt_e_hooks" }
for _, m in ipairs(MODULES) do
  local ok, mod = pcall(require, m)
  if ok and type(mod) == "function" then
    local ok2, err = pcall(mod, R, E)
    if not ok2 then log("pxrt: engine module %s failed: %s", m, tostring(err)) end
  elseif not ok then
    log("pxrt: engine module %s not loaded: %s", m, tostring(mod))
  end
end
-- optional extensions: pxrt_x_<name>.lua listed in E.extensions (appended by generated bundles)
for _, m in ipairs(E.extensions or {}) do
  local ok, mod = pcall(require, m)
  if ok and type(mod) == "function" then
    local ok2, err = pcall(mod, R, E)
    if not ok2 then log("pxrt: extension %s failed: %s", m, tostring(err)) end
  end
end
return R
