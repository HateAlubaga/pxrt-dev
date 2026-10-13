-- bench.lua: load SEVERAL packages together (the user's enabled set) and measure what one match frame costs on the Lua side.
-- Expects global SCEN = {pkgs = {...}, frames = N, worms = N}. Returns a report table (strings).
local H = dofile(DEV .. "\\harness\\mock_dll.lua")
local out = {}
local function P(fmt, ...) out[#out + 1] = string.format(fmt, ...) end

-- count host API calls (wrap BEFORE pxrt is loaded so it caches the wrappers)
local hostCalls, hostTotal = {}, 0
local siteCalls = {}
local skip = { jellyRandom = true }
local traceFn = { writeMemU8 = 1, writeMemS8 = 1, writeMemU16 = 1, writeMemU32 = 1, writeMemInt = 1, writeMemFloat = 1, writeMemString = 1,
  writeMemBytes = 1, memFill = 1, memCopy = 1, callRegs = 1, callThiscall = 1, callStdcall = 1, callFastcall = 1, drawSpriteLocal = 1,
  drawSpriteGlobal = 1, drawTextLocal = 1, drawRectLocal = 1, wormSetState = 1, setSpriteOverride = 1, SetSpriteOverride = 1 }
local traceH, traceN, traceOut = 5381, 0, nil
local fmt = string.format
local function traceEv(name, ...)
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
  if traceOut then traceOut:write(line, "\n") end
  for i = 1, #line do traceH = (traceH * 33 + line:byte(i)) % 4294967296 end
end
for _, name in ipairs({ "readMemU8", "readMemS8", "readMemU16", "readMemS16", "readMemU32", "readMemInt", "readMemFloat", "readMemDouble",
  "writeMemU8", "writeMemS8", "writeMemU16", "writeMemU32", "writeMemInt", "writeMemFloat", "readMemString", "writeMemString",
  "readMemBytes", "writeMemBytes", "memAlloc", "memFree", "memFill", "memCopy", "ptrToInt", "intToPtr", "callRegs", "callThiscall",
  "callStdcall", "callFastcall", "drawSpriteLocal", "drawSpriteGlobal", "drawTextLocal", "drawRectLocal", "getTurnGameAddr",
  "getWormWeaponId", "isKeyDown", "isGameKeyDown", "wormSetState", "setSpriteOverride", "SetSpriteOverride" }) do
  local f = rawget(_G, name)
  if f and not SCEN.nohook then
    local tr = traceFn[name]
    _G[name] = function(...)
      hostCalls[name] = (hostCalls[name] or 0) + 1
      hostTotal = hostTotal + 1
      if SCEN.hostsite then
        local k = name
        for lv = 2, 7 do
          local inf = debug.getinfo(lv, "Sl")
          if not inf then break end
          k = k .. " <- " .. inf.short_src:match("[^/]*$") .. ":" .. inf.currentline
        end
        siteCalls[k] = (siteCalls[k] or 0) + 1
      end
      if tr then traceEv(name, ...) end
      return f(...)
    end
  end
end

local chunkLines = {}
do
  local oload = load
  _G.load = function(chunk, name, ...)
    if type(chunk) == "string" and type(name) == "string" and name:sub(1, 1) == "=" and #chunk > 200 then
      local t = {}
      for l in (chunk .. "\n"):gmatch("(.-)\n") do t[#t + 1] = l end
      chunkLines[name:sub(2)] = t
    end
    return oload(chunk, name, ...)
  end
end
local function nameOf(key)
  -- key "short_src:linedefined" -> PX function name taken from the comment line above the definition
  local src, ln = key:match("^(.*):(%d+)$")
  local t = src and chunkLines[src]
  if src and not t then
    for nm, lines in pairs(chunkLines) do
      if nm:sub(-#src - 1) == "/" .. src then t = lines break end
    end
  end
  if t then
    local c = t[tonumber(ln) - 1]
    if c and c:sub(1, 2) == "--" then return key .. "  " .. c:sub(4, 80) end
  end
  return key
end
if SCEN.trace then traceOut = io.open(SCEN.trace, "w") end
H.build({ weapons = SCEN.weapons or {}, teams = 2, perTeam = (SCEN.worms or 4) // 2 })
local logs = {}
_G.__pxrt_logsink = function(m) logs[#logs + 1] = m end

local ok, R = pcall(require, "pxrt")
if not ok then return { "require pxrt failed: " .. tostring(R) } end
local B = require("pxboot")
local t0 = os.clock()
for _, pkg in ipairs(SCEN.pkgs) do
  if B.claim(pkg) then B.boot(pkg) else P("NOT CLAIMED %s", pkg) end
end
P("load of %d packages: %.3fs", #SCEN.pkgs, os.clock() - t0)
for _, f in ipairs(H.cb.gameGlobalInit) do pcall(f) end

-- which vtable8 hooks got registered
local reg = {}
for c, slots in pairs(H.vt) do
  local n = #slots.vtable8
  if n > 0 then reg[#reg + 1] = c .. "=" .. n end
end
table.sort(reg)
P("vtable8 callbacks registered: %s", table.concat(reg, " "))

-- sampling profiler by VM instruction count
local samples, nsamples = {}, 0
local incl, selfFn = {}, {}
local instr = 0
local STEP = 100
debug.sethook(function()
  instr = instr + STEP
  local info = debug.getinfo(2, "Sl")
  if info then
    local k = (info.short_src or "?") .. ":" .. tostring(info.currentline)
    samples[k] = (samples[k] or 0) + 1
    nsamples = nsamples + 1
    local seen = {}
    if SCEN.incl then
    do
      local f2 = debug.getinfo(2, "S")
      local sk = (f2.short_src or "?"):gsub("^.*[/\\]", "") .. ":" .. tostring(f2.linedefined)
      selfFn[sk] = (selfFn[sk] or 0) + 1
    end
    for lv = 2, 40 do
      local fi = debug.getinfo(lv, "S")
      if not fi then break end
      local fk = (fi.short_src or "?"):gsub("^.*[/\\]", "") .. ":" .. tostring(fi.linedefined)
      if not seen[fk] then
        seen[fk] = true
        incl[fk] = (incl[fk] or 0) + 1
      end
    end
    end
  end
end, "", STEP)

if SCEN.nohook then debug.sethook() end
local msgPerFrame = SCEN.msgs or { 2 }
local nmsg, msgByClass = 0, {}
local function send(cls, addr, sender, mt)
  nmsg = nmsg + 1
  msgByClass[cls] = (msgByClass[cls] or 0) + 1
  return pcall(H.sendMessage, cls, addr, sender, mt, 0, 0)
end

local frames = SCEN.frames or 60
local callCount = {}
if SCEN.callprof then
  debug.sethook(function()
    local info = debug.getinfo(2, "S")
    if info then
      local k = (info.short_src or "?"):gsub("^.*[/\\]", "") .. ":" .. tostring(info.linedefined)
      callCount[k] = (callCount[k] or 0) + 1
    end
  end, "c")
end
for k in pairs(hostCalls) do hostCalls[k] = 0 end
hostTotal = 0
local c0 = os.clock()
local WARM = SCEN.warm or 40
for i = 1, frames + WARM do
  if i == WARM + 1 then
    -- one-time work (sprite building, first-frame entries) is over: measure the steady state only
    samples, nsamples, incl, selfFn, instr, callCount, nmsg, msgByClass = {}, 0, {}, {}, 0, {}, 0, {}
    for k in pairs(hostCalls) do hostCalls[k] = 0 end
    siteCalls = {}
    hostTotal = 0
    c0 = os.clock()
  end
  for _, mt in ipairs(msgPerFrame) do
    send("CTaskTurnGame", H.TG, nil, mt)
    for _, w in ipairs(H.worms) do send("CTaskWorm", w, H.TG, mt) end
    -- the engine also sends frames to clouds / fire / flames / land / filter / teams: model them as plain extra messages
    for c = 1, (SCEN.extra or 0) do
      for _, cls in ipairs({ "CTaskCloud", "CTaskFlame", "CTaskFire", "CTaskLand", "CTaskFilter" }) do send(cls, 0x2900000 + c * 0x100, H.TG, mt) end
    end
  end
  for _, f in ipairs(H.cb.onFrame) do pcall(f) end
end
local el = os.clock() - c0
debug.sethook()
if SCEN.callprof then
  local cc, tot = {}, 0
  for k, v in pairs(callCount) do cc[#cc + 1] = { k, v }; tot = tot + v end
  table.sort(cc, function(a, b) return a[2] > b[2] end)
  P("Lua function calls per frame: %.0f", tot / frames)
  for i = 1, math.min(45, #cc) do P("   %7.1f/frame  %s", cc[i][2] / frames, nameOf(cc[i][1])) end
end

P("frames=%d  messages=%d (%.1f/frame)  lua cpu(mock, incl. mock memory)=%.1f ms/frame", frames, nmsg, nmsg / frames, 1000 * el / frames)
P("VM instructions per frame: %.0f", instr / frames)
P("TRACE events=%d hash=%08x", traceN, traceH)
if traceOut then traceOut:close() end
P("host API calls per frame: %.0f", hostTotal / frames)
local hc = {}
for k, v in pairs(hostCalls) do hc[#hc + 1] = { k, v } end
table.sort(hc, function(a, b) return a[2] > b[2] end)
for i = 1, math.min(10, #hc) do P("   %-16s %.0f/frame", hc[i][1], hc[i][2] / frames) end

if SCEN.hostsite then
  local sc = {}
  for k, v in pairs(siteCalls) do sc[#sc + 1] = { k, v } end
  table.sort(sc, function(a, b) return a[2] > b[2] end)
  P("host call sites (per frame):")
  for i = 1, math.min(30, #sc) do P("   %6.1f  %s", sc[i][2] / frames, sc[i][1]) end
end
local top = {}
for k, v in pairs(samples) do top[#top + 1] = { k, v } end
table.sort(top, function(a, b) return a[2] > b[2] end)
P("hot lines (share of VM instructions):")
for i = 1, math.min(18, #top) do P("   %5.1f%%  %s", 100 * top[i][2] / math.max(1, nsamples), top[i][1]) end
local byFile = {}
for k, v in pairs(samples) do
  local f = k:gsub(":%d+$", "")
  byFile[f] = (byFile[f] or 0) + v
end
local bf = {}
for k, v in pairs(byFile) do bf[#bf + 1] = { k, v } end
table.sort(bf, function(a, b) return a[2] > b[2] end)
P("hot files:")
for i = 1, math.min(14, #bf) do P("   %5.1f%%  %s", 100 * bf[i][2] / math.max(1, nsamples), bf[i][1]) end
if SCEN.incl then
  local sf = {}
  for k, v in pairs(selfFn) do sf[#sf + 1] = { k, v } end
  table.sort(sf, function(a, b) return a[2] > b[2] end)
  P("self time by function:")
  for i = 1, math.min(50, #sf) do P("   %5.1f%%  %s", 100 * sf[i][2] / math.max(1, nsamples), nameOf(sf[i][1])) end
  local ic = {}
  for k, v in pairs(incl) do ic[#ic + 1] = { k, v } end
  table.sort(ic, function(a, b) return a[2] > b[2] end)
  P("inclusive (share of samples whose stack contains the function):")
  for i = 1, math.min(60, #ic) do P("   %5.1f%%  %s", 100 * ic[i][2] / math.max(1, nsamples), nameOf(ic[i][1])) end
end
local cl = {}
for k, v in pairs(msgByClass) do cl[#cl + 1] = k .. "=" .. v end
table.sort(cl)
P("messages by class: %s", table.concat(cl, " "))
for i = 1, math.min(12, #logs) do P("LOG %s", logs[i]) end
for i = 13, #logs do if logs[i]:find("perf", 1, true) or logs[i]:find("profile", 1, true) or logs[i]:find("fail", 1, true) then P("LOG %s", logs[i]) end end
return out
