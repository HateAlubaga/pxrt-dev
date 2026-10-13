-- mock_dll.lua: fake wkJellyWorm Lua API + WA memory for running pxrt outside the game
local H = {}
_G.H = H

---------------------------------------------------------------------------
-- memory (byte-level sparse table)
---------------------------------------------------------------------------
local mem = {}
H.mem = mem
-- virtual land bitmap (rows >= groundY solid, 1 bit per pixel, 4096x2048): no need to fill 1 MB of sparse memory
H.LAND_DATA, H.LAND_STRIDE, H.LAND_H, H.groundY = 0x3000000, 512, 2048, 1500
local function rb(a)
  local v = mem[a]
  if v then return v end
  local d = a - H.LAND_DATA
  if d >= 0 and d < H.LAND_STRIDE * H.LAND_H then
    return (d // H.LAND_STRIDE) >= H.groundY and 0xFF or 0
  end
  return 0
end
local function wb(a, v) mem[a] = v & 0xFF end
function readMemU8(a) return rb(a) end
function readMemS8(a) local v = rb(a); return v >= 128 and v - 256 or v end
function readMemU16(a) return rb(a) | (rb(a + 1) << 8) end
function readMemS16(a) local v = readMemU16(a); return v >= 32768 and v - 65536 or v end
function readMemU32(a) return rb(a) | (rb(a + 1) << 8) | (rb(a + 2) << 16) | (rb(a + 3) << 24) end
function readMemInt(a) local v = readMemU32(a); return v >= 0x80000000 and v - 0x100000000 or v end
function readMemFloat(a) return (string.unpack("<f", string.pack("<I4", readMemU32(a)))) end
function readMemDouble(a) return (string.unpack("<d", string.char(rb(a), rb(a+1), rb(a+2), rb(a+3), rb(a+4), rb(a+5), rb(a+6), rb(a+7)))) end
function writeMemU8(a, v) wb(a, v) end
function writeMemS8(a, v) wb(a, v) end
function writeMemU16(a, v) wb(a, v); wb(a + 1, v >> 8) end
function writeMemU32(a, v) v = v & 0xFFFFFFFF; wb(a, v); wb(a + 1, v >> 8); wb(a + 2, v >> 16); wb(a + 3, v >> 24) end
function writeMemInt(a, v) writeMemU32(a, v) end
function writeMemFloat(a, v) writeMemU32(a, (string.unpack("<I4", string.pack("<f", v)))) end
function readMemString(a, n)
  local t = {}
  n = n or 256
  for i = 0, n - 1 do
    local c = rb(a + i)
    if c == 0 then break end
    t[#t + 1] = string.char(c)
  end
  return table.concat(t)
end
function writeMemString(a, s) for i = 1, #s do wb(a + i - 1, s:byte(i)) end wb(a + #s, 0) end
-- host semantics: byte strings
function readMemBytes(a, n) local t = {} for i = 0, n - 1 do t[#t + 1] = string.char(rb(a + i)) end return table.concat(t) end
function writeMemBytes(a, s) for i = 1, #s do wb(a + i - 1, s:byte(i)) end return true end
function isMemReadable() return true end

local heap = 0x08000000
function memAlloc(n) local a = heap; heap = heap + ((n + 15) & ~15) + 16; for i = 0, n - 1 do mem[a + i] = 0 end return a end
function memFree() end
function memFill(a, b, n) for i = 0, n - 1 do mem[a + i] = b & 0xFF end end
function memCopy(d, s, n) for i = 0, n - 1 do mem[d + i] = rb(s + i) end end
function ptrToInt(o)
  if type(o) == "number" then return o end
  if type(o) == "table" and o.__addr then return o.__addr end
  return 0
end
function intToPtr(a) return a end

---------------------------------------------------------------------------
-- calls log
---------------------------------------------------------------------------
H.calls = {}
local function logcall(name, ...)
  H.calls[#H.calls + 1] = { name, ... }
  H.callCount = (H.callCount or 0) + 1
  local c = H.callTally or {}
  H.callTally = c
  c[name] = (c[name] or 0) + 1
end
-- WA.exe is mapped away from its linked base (0x400000) like in the game (ASLR): a call to a linked-base address is
-- a bug, the host would refuse it ("bad target address") or jump into whatever is mapped there.
H.WA_BASE = 0xA50000
local function checkTarget(name, addr)
  if type(addr) ~= "number" or (addr >= 0x400000 and addr < 0x984000) then
    error(name .. ": bad target address", 2)
  end
end
function callRegs(addr, regs, ...) checkTarget("callRegs", addr) logcall("callRegs", addr, regs, ...) return 0 end
function callThiscall(addr, this, ...) checkTarget("callThiscall", addr) logcall("callThiscall", addr, this, ...) return 0 end
function callStdcall(addr, ...) checkTarget("callStdcall", addr) logcall("callStdcall", addr, ...) return 0 end
function callFastcall(addr, ...) checkTarget("callFastcall", addr) logcall("callFastcall", addr, ...) return 0 end
function showChatMessage(s, c) logcall("showChatMessage", s) end
function drawSpriteLocal(...) logcall("drawSpriteLocal", ...) return 0 end
function drawSpriteGlobal(...) logcall("drawSpriteGlobal", ...) return 0 end
function drawTextLocal(...) logcall("drawTextLocal", ...) return 0 end
function drawRectLocal(...) logcall("drawRectLocal", ...) return 0 end
function playSoundLocal(...) logcall("playSoundLocal", ...) return 0 end
function setSpriteOverride(...) logcall("setSpriteOverride", ...) return 0 end
function SetSpriteOverride(...) logcall("SetSpriteOverride", ...) return 0 end
function SetWeaponSpriteOverride(...) logcall("SetWeaponSpriteOverride", ...) return 0 end
function wormSetState(...) logcall("wormSetState", ...) return 0 end
function isKeyDown() return false end
function isGameKeyDown() return false end
function isReplayPlayback() return false end
function isHost() return true end
function getTickCount() return 0 end
function jellyRandom() return 0.5 end
function jellyRandomInt(a, b) return a end
function createExplosion(...) logcall("createExplosion", ...) return 0 end
function createWeaponProjectile(...) logcall("createWeaponProjectile", ...) return 0 end
function sendSyncChat() end
function jellySchedule() return 0 end
function jellyCancel() end

-- task birth log (the host's CTask constructor hook): HARNESS_OLDDLL=1 hides it, as with a DLL built before it
H.birthSeq, H.births = 0, {}
function H.birth(a) H.births[H.birthSeq % 4096] = a; H.birthSeq = H.birthSeq + 1 end
if not os.getenv("HARNESS_OLDDLL") then
  function taskBirthSeq() return H.birthSeq end
  function taskBirthsSince(from)
    local now = H.birthSeq
    local lost = now - from > 4096
    if lost then from = now - 4096 end
    local list = {}
    for q = from, now - 1 do list[#list + 1] = H.births[q % 4096] end
    return list, now, lost
  end
end

local nextSprite, nextSound = 851, 1
function registerCustomSprite(file, frames) local id = nextSprite; nextSprite = nextSprite + 1; return id end
function registerCustomSound(file) local id = nextSound; nextSound = nextSound + 1; return id end
H.callbackGen = 1
function getCallbackGeneration() return H.callbackGen end

---------------------------------------------------------------------------
-- callbacks
---------------------------------------------------------------------------
H.cb = {}
for _, n in ipairs({ "fireWeapon", "gameGlobalInit", "onFrame", "onTurnStart", "weaponRelease", "wormStartFiringWeapon",
  "createWeaponProjectile", "handleCreateExplosion", "handleSpecialImpact", "handleCGameTaskPhysics",
  "writeLandMaskID", "writeLandRaw" }) do
  H.cb[n] = {}
  _G["registerCallback_" .. n] = function(f) table.insert(H.cb[n], f) end
end
H.vt = {}      -- H.vt[ctask][slot] = { callbacks }
H.origCalls = {}
local CTASKS = { "CTaskWorm", "CTaskMissile", "CTaskMine", "CTaskCrate", "CTaskOildrum", "CTaskArrow", "CTaskCanister",
  "CTaskCross", "CTaskOldWorm", "CTaskTurnGame", "CTaskTeam", "CTaskFire", "CTaskFlame", "CTaskAirStrike", "CTaskCloud",
  "CTaskFilter", "CTaskLand", "CTask", "CGameTask" }
for _, c in ipairs(CTASKS) do
  H.vt[c] = {}
  for _, slot in ipairs({ "vtable0", "vtable4", "vtable8", "vtableC", "vtable10", "vtable14", "vtable18", "vtable1C",
    "vtable20", "vtable24", "vtable28", "vtable2C", "vtable30", "vtable34", "vtable38", "vtable3C", "vtable40", "vtable44",
    "vtable48" }) do
    H.vt[c][slot] = {}
    _G[c .. "_RegisterCallback_" .. slot] = function(f) table.insert(H.vt[c][slot], f) end
    _G[c .. "_CallOriginal_" .. slot] = function(this, ...)
      H.origCalls[#H.origCalls + 1] = { c, slot, ... }
      return 0
    end
  end
end

-- userdata stand-in for CTask*
function H.task(addr)
  return setmetatable({ __addr = addr }, { __index = { getAddr = function(self) return self.__addr end } })
end

---------------------------------------------------------------------------
-- WA world layout
---------------------------------------------------------------------------
H.TG, H.STORE, H.GG, H.LAND, H.INFO, H.WTAB, H.ENV = 0x1000000, 0x1010000, 0x1100000, 0x1200000, 0x1300000, 0x1400000, 0x1500000
local nodeHeap = 0x1020000
local function putHash(htype, hindex, obj)
  local b = H.STORE + 4 * ((hindex * 17 + htype) & 0xFF)
  local node = nodeHeap; nodeHeap = nodeHeap + 16
  writeMemU32(node, readMemU32(b)); writeMemU32(node + 4, htype); writeMemU32(node + 8, hindex); writeMemU32(node + 12, obj)
  writeMemU32(b, node)
end
H.putHash = putHash
function getTurnGameAddr() return H.TG end

local strHeap = 0x1600000
local function cstr(s) local a = strHeap; writeMemString(a, s); strHeap = strHeap + #s + 4; return a end
H.cstr = cstr

local VANILLA = { "Bazooka", "Homing Missile", "Mortar", "Homing Pigeon", "Sheep Launcher", "Grenade", "Cluster Bomb", "Banana Bomb",
  "Battle Axe", "Earthquake", "Shotgun", "Handgun", "Uzi", "Minigun", "Longbow", "Fire Punch", "Dragon Ball", "Kamikaze",
  "Suicide Bomber", "Prod", "Dynamite", "Mine", "Sheep", "Super Sheep", "Mole Bomb", "Air Strike", "Napalm Strike",
  "Mail Strike", "Mine Strike", "Molotov Cocktail", "Flame Thrower", "Blow Torch", "Pneumatic Drill", "Girder", "Baseball Bat",
  "Ninja Rope", "Bungee", "Parachute", "Teleport", "Scales of Justice", "Super Banana Bomb", "Holy Hand Grenade", "Freeze",
  "Magic Bullet", "Jet Pack", "Low Gravity", "Laser Sight", "Fast Walk", "Invisibility", "Damage x2", "Crate Spy", "Skip Go",
  "Surrender", "Select Worm", "Nuclear Test", "Armageddon" }
H.weaponNames = {}
local function setWeapon(id, name)
  local e = H.WTAB + id * 0x1D0
  writeMemU32(e, cstr(name)); writeMemU32(e + 4, cstr(name))
  H.weaponNames[id] = name
end
H.setWeapon = setWeapon
function weaponIdByName(n)
  for id, nm in pairs(H.weaponNames) do if nm:lower() == tostring(n):lower() then return id end end
  return -1
end
function getWormWeaponId(wa) return readMemInt(wa + 0x170) end

-- generic function hooks (LuaNative.cpp hookFunction): H.fireHook(name, ...) plays WA calling the hooked function
H.hooks = {}
function hookFunction(name, addr, spec, fn)
  for id, h in ipairs(H.hooks) do
    if h.name == name then h.fn = fn return id end
  end
  H.hooks[#H.hooks + 1] = { name = name, addr = addr, spec = spec, fn = fn }
  return #H.hooks
end
function callHookOriginal(id, ...)
  local h = H.hooks[id]
  logcall("hookOrig", h and h.name or "?", ...)
  return 0
end
function H.fireHook(name, ...)
  for _, h in ipairs(H.hooks) do
    if h.name == name then return h.fn(...) end
  end
  return nil
end

function H.initWorld()
  mem = {}; H.mem = mem
  -- (functions above close over the old `mem`; rebind by clearing in place instead)
end

-- WA.exe image: PE header + the first 24 bytes of the engine functions pxrt calls (from WA.exe 3.8.1)
local WA_FUNCS = {
  [0x51EE60] = "568b742408c7463c000000008b503083c2ff83fa03570f87",
  [0x512E80] = "518b8e880000008b54240c538b5c2414558b6c2410578bf8",
  [0x548080] = "558bec83e4f881ec080400008b5508894c24088b4d108954",
  [0x540190] = "8b81e00500008b91a477000005a0000000c1e01081c20000",
  [0x4FB9D0] = "83ec10538b5c24188b83400200008b40240524d900008078",
  [0x50FCD0] = "83ec10568bf08d442408508d4c2414518d542414528d4424",
  [0x4F5BD0] = "83ec0853568bf18b5e1c83c30181e30f00008079054b83cb",
}
function H.buildWaImage()
  local b = H.WA_BASE
  writeMemU16(b, 0x5A4D); writeMemU32(b + 0x3C, 0x110)
  writeMemU32(b + 0x110, 0x4550); writeMemU32(b + 0x118, 0x5FA8504C); writeMemU32(b + 0x160, 0x584000)
  writeMemU32(b + 0x144, b)
  for linked, hex in pairs(WA_FUNCS) do
    local a = linked - 0x400000 + b
    for i = 1, #hex, 2 do wb(a + (i - 1) // 2, tonumber(hex:sub(i, i + 1), 16)) end
  end
end

function H.build(opts)
  opts = opts or {}
  for k in pairs(mem) do mem[k] = nil end
  H.buildWaImage()
  H.calls = {}
  nodeHeap = 0x1020000; strHeap = 0x1600000
  H.weaponNames = {}
  -- turn game
  writeMemU32(H.TG + 0x20, 6); writeMemU32(H.TG + 0x24, H.STORE); writeMemU32(H.TG + 0x2C, H.GG)
  writeMemInt(H.TG + 0x12C, 1); writeMemInt(H.TG + 0x130, 1); writeMemInt(H.TG + 0xE8, opts.teams or 2)
  putHash(0x14, 0, H.TG)
  do -- environment filter node (hash 25/0)
    local fa = 0x2900000
    writeMemU32(fa, 0x7000000 + 0x300); writeMemU32(fa + 0x20, 7); writeMemU32(fa + 0x24, H.STORE); writeMemU32(fa + 0x2C, H.GG)
    putHash(25, 0, fa)
  end
  -- DDGame
  writeMemU32(H.GG + 0x20, H.LAND); writeMemU32(H.GG + 0x24, H.INFO); writeMemU32(H.GG + 0x510, H.WTAB)
  writeMemU32(H.GG + 0x528, H.ENV); writeMemInt(H.GG + 0x77C0, 4096); writeMemInt(H.GG + 0x77C4, 2048)
  writeMemInt(H.GG + 0x5E4, 2048 + 40)
  writeMemInt(H.ENV + 0x228, 2048 * 65536 // 65536 * 1)
  writeMemInt(H.ENV + 0x22C, 0x147B); writeMemInt(H.ENV + 0x230, 0)     -- gravity ~0.08, no wind
  do -- land bitmap (virtual rows, see rb)
    local bm = 0x1210000
    writeMemU32(H.LAND + 0x914, bm)
    writeMemU32(bm + 8, H.LAND_DATA); writeMemInt(bm + 0x10, H.LAND_STRIDE)
    writeMemInt(bm + 0x14, 4096); writeMemInt(bm + 0x18, 2048)
    writeMemInt(bm + 0x1C, 0); writeMemInt(bm + 0x20, 0); writeMemInt(bm + 0x24, 4096); writeMemInt(bm + 0x28, 2048)
  end
  -- weapons
  for i, n in ipairs(VANILLA) do setWeapon(i - 1 + 0, n) end
  local nextId = #VANILLA
  H.customIds = {}
  for _, n in ipairs(opts.weapons or {}) do
    if weaponIdByName(n) < 0 then setWeapon(nextId, n); H.customIds[n] = nextId; nextId = nextId + 1 end
  end
  -- worms
  H.worms = {}
  local teams = opts.teams or 2
  local per = opts.perTeam or 2
  local k = 0
  for t = 1, teams do
    local ta = 0x2800000 + t * 0x1000
    writeMemU32(ta, 0x7000000 + 0x200); writeMemU32(ta + 0x20, 10); writeMemU32(ta + 0x24, H.STORE); writeMemU32(ta + 0x2C, H.GG)
    writeMemInt(ta + 0x38, t); writeMemInt(ta + 0x3C, 1); writeMemInt(ta + 0x48, 1)
    putHash(0x15, t, ta)
    for w = 1, per do
      local a = 0x2000000 + k * 0x1000
      k = k + 1
      writeMemU32(a + 0x20, 18); writeMemU32(a + 0x24, H.STORE); writeMemU32(a + 0x2C, H.GG)
      writeMemU32(a, 0x7000000 + 0x100) -- vtable
      writeMemInt(a + 0xFC, t); writeMemInt(a + 0x100, w)
      writeMemInt(a + 0x44, 0x65)
      writeMemInt(a + 0x84, (300 + 40 * k) * 65536); writeMemInt(a + 0x88, 500 * 65536)
      writeMemInt(a + 0x178, 100); writeMemInt(a + 0x17C, 100)
      writeMemU32(a + 0x36C, H.WTAB + 0 * 0x1D0)
      writeMemInt(a + 0x170, 0)
      putHash(2, (t << 4) + w, a)
      H.worms[#H.worms + 1] = a
    end
  end
  -- env object list (all tasks)
  local objs = 0x1700000
  writeMemInt(H.ENV + 0x18, 64); writeMemInt(H.ENV + 0x18 + 8, #H.worms); writeMemU32(H.ENV + 0x18 + 0xC, objs)
  for i, a in ipairs(H.worms) do writeMemU32(objs + 4 * (i - 1), a) end
end

-- a task as WA's CTask constructor leaves it (class id, parent, vtable): logged in the birth log, added to the env list.
-- `at` reuses a freed task's memory, as WA's allocator does for the next task of the same size.
function H.newTask(cid, parent, at)
  local a = at or memAlloc(0x400)
  memFill(a, 0, 0x400)
  writeMemU32(a, 0x7000000 + 0x400 + cid * 0x10)
  writeMemU32(a + 4, parent or H.TG)
  writeMemU32(a + 0x20, cid); writeMemU32(a + 0x24, H.STORE); writeMemU32(a + 0x2C, H.GG)
  H.birth(a)
  local n = readMemInt(H.ENV + 0x18 + 8)
  writeMemU32(0x1700000 + 4 * n, a); writeMemInt(H.ENV + 0x18 + 8, n + 1)
  return a
end
function H.freeTask(a)
  local n = readMemInt(H.ENV + 0x18 + 8)
  for i = 0, n - 1 do
    if readMemU32(0x1700000 + 4 * i) == a then
      writeMemU32(0x1700000 + 4 * i, readMemU32(0x1700000 + 4 * (n - 1)))
      writeMemInt(H.ENV + 0x18 + 8, n - 1)
      break
    end
  end
end

function H.setWormWeapon(wa, id)
  writeMemInt(wa + 0x170, id)
  writeMemU32(wa + 0x36C, H.WTAB + id * 0x1D0)
end

-- fire all callbacks of a vtable8 slot; returns true when some callback returned nonzero
function H.sendMessage(ctask, addr, sender, mtype, size, data)
  local ret = 0
  for _, f in ipairs(H.vt[ctask].vtable8) do
    local r = f(H.task(addr), sender and H.task(sender) or nil, mtype, size, data)
    if r and r ~= 0 then ret = 1 end
  end
  return ret
end

function H.fire(wormAddr, wsAddr, sdAddr)
  local ret = 0
  for _, f in ipairs(H.cb.fireWeapon) do
    local r = f(H.task(wormAddr), H.task(wsAddr), H.task(sdAddr))
    if r and r ~= 0 then ret = r end
  end
  return ret
end

-- quad renderer (QuadRender.cpp): validates the flat batch layout
H.quadN = 0
function pxQuadSubmit(layer, data, n)
  if type(layer) ~= "number" or type(data) ~= "table" or math.type(n) ~= "integer" then error("pxQuadSubmit: bad arguments", 2) end
  for k = 1, n * 24 do
    local x = data[k]
    if x ~= nil and type(x) ~= "number" then error("pxQuadSubmit: field " .. k .. " is a " .. type(x), 2) end
  end
  H.quadN = H.quadN + n
  logcall("pxQuadSubmit", layer, n)
  return n
end
function pxSpriteCell(id) return 32, 24 end
function pxQuadStats() return 0, 0, 0, 0, 0 end
return H
