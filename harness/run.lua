-- run.lua: execute one package scenario in the mock WA world. Expects global SCEN = {pkg=, pkgtable=, weapons=, frames=}
local budget = 0
debug.sethook(function()
  budget = budget + 1
  if budget > (tonumber(os.getenv("HARNESS_BUDGET")) or 60) then
    if os.getenv("HARNESS_TB") and _G.__pxrt_logsink then
      local tb = debug.traceback("TIMEOUT-TB", 2)
      local n = 0
      for line in tb:gmatch("[^\r\n]+") do n = n + 1; if n <= 16 then _G.__pxrt_logsink("TB " .. line) end end
    end
    error("TIMEOUT (instruction budget)", 0)
  end
end, "", 1000000)
local H = dofile(DEV .. "\\harness\\mock_dll.lua")
if os.getenv("HARNESS_TRACE") then math.randomseed(20261007) end   -- deterministic runs for version diffing
-- HARNESS_NOGC=1: struct buffers return to their pool on __gc, so GC timing (which any runtime change shifts) moves
-- buffer addresses in the trace; stopping the collector keeps two runtime versions comparable
if os.getenv("HARNESS_NOGC") then collectgarbage("stop") end
local logs = {}
_G.__pxrt_logsink = function(m) logs[#logs + 1] = m end
local function L(fmt, ...) logs[#logs + 1] = "H: " .. string.format(fmt, ...) end

H.build({ weapons = SCEN.weapons or {}, teams = 2, perTeam = 2 })

-- HARNESS_TRACE=1: hash every host call that changes the world, so two runtime versions can be compared package by package
local traceH, traceN = 5381, 0
local traceDump = os.getenv("HARNESS_TRACE_DUMP") and io.open(os.getenv("HARNESS_TRACE_DUMP"), "w")
if os.getenv("HARNESS_TRACE") then
  local traced = { writeMemU8 = 1, writeMemS8 = 1, writeMemU16 = 1, writeMemU32 = 1, writeMemInt = 1, writeMemFloat = 1, writeMemString = 1,
    writeMemBytes = 1, memFill = 1, memCopy = 1, callRegs = 1, callThiscall = 1, callStdcall = 1, callFastcall = 1, drawSpriteLocal = 1,
    drawSpriteGlobal = 1, drawTextLocal = 1, drawRectLocal = 1, wormSetState = 1, setSpriteOverride = 1, SetSpriteOverride = 1,
    showChatMessage = 1, playSoundLocal = 1 }
  local fmt = string.format
  local function ev(name, ...)
    traceN = traceN + 1
    local parts = { name }
    for i = 1, select("#", ...) do
      local v = select(i, ...)
      local tv = type(v)
      if tv == "number" then parts[#parts + 1] = fmt("%.9g", v)
      elseif tv == "table" then
        local keys = {}
        for k, x in pairs(v) do keys[#keys + 1] = tostring(k) .. "=" .. tostring(x) end
        table.sort(keys)
        parts[#parts + 1] = "{" .. table.concat(keys, ",") .. "}"
      else parts[#parts + 1] = tostring(v) end
    end
    local line = table.concat(parts, " ")
    if traceDump then traceDump:write(line, "\n"); traceDump:flush() end
    local lh = 5381
    for i = 1, #line do lh = (lh * 33 + line:byte(i)) % 4294967296 end
    traceH = (traceH + lh) % 4294967296     -- order-insensitive: pairs() order may differ between runs
  end
  for name in pairs(traced) do
    local f = rawget(_G, name)
    if f then _G[name] = function(...) ev(name, ...) return f(...) end end
  end
end

local ok, R = pcall(require, "pxrt")
if not ok then logs[#logs + 1] = "H: require pxrt failed: " .. tostring(R); return logs, H end
local E = R.E
if not E then logs[#logs + 1] = "H: no engine layer"; return logs, H end
-- HARNESS_PKGDIR: resolve assets against a real packages tree (pxboot.claim rebuilds the runtime, so set it on the live one)
local function setPkgDir(RR)
  if os.getenv("HARNESS_PKGDIR") and RR and RR.E then RR.E.PACKAGES_DIR = os.getenv("HARNESS_PKGDIR") end
end
setPkgDir(R)

local okp, errp = pcall(function()
  if os.getenv("HARNESS_BOOT") then
    local B = require("pxboot")
    if not B.claim(SCEN.pkg) then error("pxboot did not claim " .. SCEN.pkg) end
    setPkgDir(_G.__pxrt)
    B.boot(SCEN.pkg)
  else
    local unit = R.loadPackage(SCEN.pkg, SCEN.pkgtable)
    E.install()
    R.runEntries("InitGraphic")
  end
end)
if not okp then L("package load crashed: %s", tostring(errp)) return logs, H end

-- match start
for _, f in ipairs(H.cb.gameGlobalInit) do local o, e = pcall(f); if not o then L("gameGlobalInit cb: %s", tostring(e)) end end

local function frames(n)
  for i = 1, n do
    -- engine order: the turn game gets M_FRAME first (our hook runs FirstFrame there), then it forwards to its children
    local o, e = pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 2, 0, 0)
    if not o then L("tg frame: %s", tostring(e)) return false end
    for _, w in ipairs(H.worms) do
      local o, e = pcall(H.sendMessage, "CTaskWorm", w, H.TG, 2, 0, 0)
      if not o then L("worm frame: %s", tostring(e)) return false end
    end
    for _, f in ipairs(H.cb.onFrame) do pcall(f) end
    -- HARNESS_DRAW=1: M_DRAWQUEUE after every frame (render path: sprites, quads, custom render functions)
    if os.getenv("HARNESS_DRAW") then
      local o, e = pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, 3, 0, 0)
      if not o then L("tg drawqueue: %s", tostring(e)) return false end
      for _, w in ipairs(H.worms) do
        local o2, e2 = pcall(H.sendMessage, "CTaskWorm", w, H.TG, 3, 0, 0)
        if not o2 then L("worm drawqueue: %s", tostring(e2)) return false end
      end
    end
  end
  return true
end

local fr = SCEN.frames or 20
frames(fr)

-- turn begin messages
for _, t in ipairs({ 52, 55 }) do
  pcall(H.sendMessage, "CTaskTurnGame", H.TG, nil, t, 0, 0)
  for _, w in ipairs(H.worms) do pcall(H.sendMessage, "CTaskWorm", w, H.TG, t, 0, 0) end
end

-- fire every weapon name
local sd = memAlloc(0x30)
for _, name in ipairs(SCEN.weapons or {}) do
  local id = weaponIdByName(name)
  if id >= 0 then
    local w = H.worms[1]
    H.setWormWeapon(w, id)
    memFill(sd, 0, 0x30)
    writeMemInt(sd + 0, 1); writeMemInt(sd + 4, 1)
    writeMemInt(sd + 8, 300 * 65536); writeMemInt(sd + 0xC, 400 * 65536)
    writeMemInt(sd + 0x10, 3 * 65536); writeMemInt(sd + 0x14, -2 * 65536)
    local before = H.callCount or 0
    local o, e = pcall(H.fire, w, H.WTAB + id * 0x1D0, sd)
    if not o then L("fire %s: %s", name, tostring(e)) end
    L("fire '%s' -> %d host calls", name, (H.callCount or 0) - before)
    frames(5)
  end
end
frames(30)
if os.getenv("HARNESS_PROBE") then local okp, e = pcall(function() local RR = _G.__pxrt or R; dofile(os.getenv("HARNESS_PROBE"))(RR, RR.E or E, H, L) end); if not okp then L("probe failed: %s", tostring(e)) end end

local tally = {}
for k, v in pairs(H.callTally or {}) do tally[#tally + 1] = k .. "=" .. v end
table.sort(tally)
L("calls: %s", table.concat(tally, " "))
L("origCalls=%d", #H.origCalls)
if os.getenv("HARNESS_DRAW") then L("quads submitted=%d", H.quadN or 0) end
if os.getenv("HARNESS_TRACE") then L("trace events=%d hash=%08x", traceN, traceH) end
if os.getenv("HARNESS_COUNT") then L("instructions %dM", budget); if rawget(_G, "__gs") then L("GS h=%d b=%d m=%d bad=%s", __gs.h, __gs.b, __gs.m, tostring(__gs.bad):sub(1,600)) end end
return logs, H
