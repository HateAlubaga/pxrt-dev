-- pxboot.lua -- start-up glue between a converted package's main.lua and the pxrt runtime.
--
-- A converted package runs its REAL ProjectX scripts through pxrt (jelly/lualibs/pxrt*.lua, pxl_*.lua, pxp_<pkg>.lua)
-- instead of the old px2jelly draft code. main.lua calls:
--     require("pxboot").claim("pkg")  at load time   -> true: pxrt will run this package, the draft code is skipped
--     require("pxboot").boot("pkg")   inside initialize() (the package directory is the active one, which is what
--                                     registerCustomSprite/LoadSound resolve asset files against)
-- If anything is missing or switched off, claim() returns false and the package keeps its old behaviour.
--
-- Kill switch: jelly\pxrt_disable.txt  ("*" = every package, otherwise one package name per line, "#" comments).
-- Log: jelly\pxboot.log (pxrt itself logs to jelly\pxrt.log).
--
-- wkJellyWorm's require() reloads the file on every call, so the state lives in _G.__pxboot.
if _G.__pxboot then return _G.__pxboot end

local B = { version = "1.0" }
_G.__pxboot = B

local claimed = {}    -- pkg -> true/false (decision made)
local defs = {}       -- pkg -> package table (libs + chunks)
local booted = {}     -- pkg -> true
local cycle           -- host callback generation the state above belongs to

local LOG_PATH = "jelly\\pxboot.log"
local logOpened = false
local function log(fmt, ...)
  local msg = (select("#", ...) > 0) and string.format(fmt, ...) or tostring(fmt)
  if _G.__pxrt_logsink then _G.__pxrt_logsink("pxboot: " .. msg) end
  if io and io.open and not _G.__pxrt_logsink then
    local f = io.open(LOG_PATH, logOpened and "a" or "w")
    if f then logOpened = true; f:write(msg, "\n"); f:close() end
  end
end
B.log = log

local function disabledBy(pkg)
  if not (io and io.open) then return false end
  local f = io.open("jelly\\pxrt_disable.txt", "r")
  if not f then return false end
  local off = false
  for line in f:lines() do
    line = line:gsub("#.*", ""):gsub("^%s+", ""):gsub("%s+$", "")
    if line == "*" or line == pkg then off = true break end
  end
  f:close()
  return off
end

-- The host clears every callback (and re-runs every package's main.lua) on a config reset / package reload and bumps
-- getCallbackGeneration(). All pxrt state then belongs to a dead cycle: drop it so the runtime is rebuilt from scratch.
local function checkCycle()
  local gen = getCallbackGeneration and getCallbackGeneration() or 0
  if cycle == gen then return end
  if cycle ~= nil then log("host callback generation %s -> %s: pxrt state reset", tostring(cycle), tostring(gen)) end
  cycle = gen
  claimed, defs, booted = {}, {}, {}
  _G.__pxrt = nil
  if package and package.loaded then
    for k in pairs(package.loaded) do
      if type(k) == "string" and k:match("^px[rpl][t_]") then package.loaded[k] = nil end
    end
  end
end

function B.claim(pkg)
  checkCycle()
  local c = claimed[pkg]
  if c ~= nil then
    -- main.lua of an already booted package ran again (package re-enabled): its initialize() will run again too
    if c and booted[pkg] and _G.__pxrt and _G.__pxrt.rearmEntries then
      pcall(_G.__pxrt.rearmEntries, "InitGraphic", pkg)
    end
    return c
  end
  local ok, why = false, nil
  if disabledBy(pkg) then
    why = "disabled by jelly\\pxrt_disable.txt"
  else
    local o1, R = pcall(require, "pxrt")
    if not o1 or type(R) ~= "table" or not R.E then
      why = "pxrt runtime not available: " .. tostring(R)
    else
      local o2, def = pcall(require, "pxp_" .. pkg)
      if not o2 or type(def) ~= "table" then
        why = "package table pxp_" .. pkg .. " not available: " .. tostring(def)
      else
        defs[pkg] = def
        ok = true
      end
    end
  end
  claimed[pkg] = ok
  if ok then log("%s: claimed (ProjectX scripts run through pxrt)", pkg)
  else log("%s: NOT claimed, old behaviour kept: %s", pkg, tostring(why)) end
  return ok
end

function B.claimed(pkg) return claimed[pkg] == true end

function B.boot(pkg)
  if claimed[pkg] ~= true then return 0 end
  local R = _G.__pxrt
  if not R then log("%s: boot without runtime", pkg) return 0 end
  if not booted[pkg] then
    booted[pkg] = true
    local ok, err = pcall(R.loadPackage, pkg, defs[pkg])
    if not ok then log("%s: loadPackage failed: %s", pkg, tostring(err)) end
    defs[pkg] = nil
  end
  -- callbacks are cleared when the host bumps its callback generation; install() re-registers only then
  local ok, err = pcall(R.E.install)
  if not ok then log("%s: install failed: %s", pkg, tostring(err)) end
  -- sprites and sounds of this package: registered now, while this package's directory is the active one
  local ok2, err2 = pcall(R.runEntries, "InitGraphic", pkg)
  if not ok2 then log("%s: InitGraphic failed: %s", pkg, tostring(err2)) end
  return 0
end

return B
