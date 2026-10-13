-- pxrt.lua -- ProjectX script runtime for wkJellyWorm (built from pxrt_core + pxrt_engine).
-- Executes ProjectX scripts transpiled to Lua (pxc2lua.py) on top of the wkJellyWorm Lua API.
-- Loaded through require("pxrt"); the instance is cached in _G.__pxrt (require reloads the file).
if _G.__pxrt then return _G.__pxrt end

local R = {}
_G.__pxrt = R
R.version = "0.1"

local floor = math.floor
local type, tostring, tonumber, pairs, ipairs, select = type, tostring, tonumber, pairs, ipairs, select
local rawget, rawset, setmetatable, getmetatable = rawget, rawset, setmetatable, getmetatable
local mtype = math.type
local pcall, load = pcall, load

---------------------------------------------------------------------------
-- logging
---------------------------------------------------------------------------
local LOG_PATH = "jelly\\pxrt.log"
local logCount, logOpened = 0, false
local msgSeen = {}
local function log(fmt, ...)
  if logCount > 4000 then return end
  local msg = (select("#", ...) > 0) and string.format(fmt, ...) or tostring(fmt)
  -- the same line is logged at most 3 times (per-frame failures must not flood the log)
  local n = (msgSeen[msg] or 0) + 1
  msgSeen[msg] = n
  if n > 3 then
    if n == 4 then msg = msg .. "  [repeats suppressed]" else return end
  end
  logCount = logCount + 1
  if _G.__pxrt_logsink then _G.__pxrt_logsink(msg) return end
  if io and io.open then
    local f = io.open(LOG_PATH, logOpened and "a" or "w")
    if f then logOpened = true; f:write(msg, "\n"); f:close() end
  end
end
R.log = log
local seenOnce = {}
local function once(key, fmt, ...)
  if seenOnce[key] then return end
  seenOnce[key] = true
  log(fmt, ...)
end
R.once = once

---------------------------------------------------------------------------
-- value helpers (PX semantics)
---------------------------------------------------------------------------
local function isnull(v)
  return v == nil or v == 0 or v == false
end
local function T(v)
  if v == nil or v == false then return false end
  if type(v) == "number" then return v ~= 0 end
  return true
end
local function ti(v)
  if mtype(v) == "integer" then return v end
  local t = type(v)
  if t == "number" then
    if v ~= v then return 0 end
    if v >= 2147483647 then return 2147483647 end
    if v <= -2147483648 then return -2147483648 end
    return v >= 0 and floor(v) or -floor(-v)
  elseif t == "boolean" then return v and 1 or 0
  elseif t == "nil" then return 0
  elseif t == "string" then return ti(tonumber(v) or 0)
  elseif t == "table" then
    local a = rawget(v, "__a")
    if a then return a end
    return 1
  end
  return 0
end
local function tf(v)
  local t = type(v)
  if t == "number" then return v + 0.0
  elseif t == "boolean" then return v and 1.0 or 0.0
  elseif t == "nil" then return 0.0
  elseif t == "string" then return (tonumber(v) or 0) + 0.0 end
  return 0.0
end
local function div(a, b)
  if mtype(a) == "integer" and mtype(b) == "integer" then
    if b == 0 then return 0 end
    local q = a // b
    if q < 0 and q * b ~= a then q = q + 1 end
    return q
  end
  a, b = tf(a), tf(b)
  if b == 0 then return 0.0 end
  return a / b
end
local function mod(a, b)
  if mtype(a) == "integer" and mtype(b) == "integer" then
    if b == 0 then return 0 end
    return math.fmod(a, b)
  end
  a, b = tf(a), tf(b)
  if b == 0 then return 0.0 end
  return math.fmod(a, b)
end
local function fmtnum(v)
  if mtype(v) == "integer" then return tostring(v) end
  if v == floor(v) and v > -1e15 and v < 1e15 then return string.format("%d", v) end
  return string.format("%g", v)
end
local function str(v)
  local t = type(v)
  if t == "string" then return v end
  if t == "number" then return fmtnum(v) end
  if t == "nil" then return "" end
  return tostring(v)
end
local function cat(a, b) return str(a) .. str(b) end
local function add(a, b)
  local ta, tb = type(a), type(b)
  if ta == "string" or tb == "string" then return str(a) .. str(b) end
  if ta ~= "number" then a = ti(a) end
  if tb ~= "number" then b = ti(b) end
  return a + b
end
local function shr(a, b)
  a, b = ti(a), ti(b)
  if b <= 0 then return a end
  if b > 62 then return a < 0 and -1 or 0 end
  return a // (1 << b)
end
local function eq(a, b)
  if a == b then return true end
  if isnull(a) and isnull(b) then return true end
  if type(a) == "table" and type(b) == "table" then
    local x, y = rawget(a, "__a"), rawget(b, "__a")
    if x and y then return x == y end
  end
  return false
end
R.T, R.ti, R.tf, R.div, R.mod, R.isnull, R.eq, R.add, R.cat, R.str, R.shr = T, ti, tf, div, mod, isnull, eq, add, cat, str, shr

---------------------------------------------------------------------------
-- class registry
---------------------------------------------------------------------------
local ENGINE_BASE = {
  CWorm = "CGObject", CMissile = "CGObject", CMine = "CGObject", CCrate = "CGObject",
  COilDrum = "CGObject", CGas = "CGObject", CArrow = "CGObject", CCanister = "CGObject",
  CCross = "CGObject", CGObject = "CObject", CTurnGame = "CObject", CTeam = "CObject",
  CFilter = "CObject", CLand = "CObject", CGameState = "CObject", CEnv = "CObject",
  CFire = "CGObject", CAirStrike = "CGObject", CCloud = "CGObject", CSmoke = "CGObject",
  CWeapon = "CObject",
}
local classes = {}
local function getClass(name)
  local c = classes[name]
  if not c then
    c = { name = name, base = ENGINE_BASE[name], methods = {}, overrides = {}, ctor = nil, ctorOv = {},
          engine = ENGINE_BASE[name] ~= nil or name == "CObject" }
    classes[name] = c
  end
  return c
end
R.getClass = getClass
local function chainOf(name)
  local out, seen = {}, {}
  local c = classes[name] or getClass(name)
  while c and not seen[c.name] do
    out[#out + 1] = c
    seen[c.name] = true
    c = c.base and getClass(c.base) or nil
  end
  return out
end
local function isa(clsName, target)
  for _, c in ipairs(chainOf(clsName)) do
    if c.name == target then return true end
  end
  return false
end
R.isa = isa

---------------------------------------------------------------------------
-- method dispatch: [overrides (outermost first)..., script method, native]
---------------------------------------------------------------------------
local natives = {}      -- natives[className][method] = function(self, super, ...)
R.natives = natives
local chainCache = {}
local nativeSet = setmetatable({}, { __mode = "k" })
local function buildChain(clsName, m)
  local cc = chainCache[clsName]
  if not cc then cc = {}; chainCache[clsName] = cc end
  local L = cc[m]
  if L then return L end
  L = {}
  local ch = chainOf(clsName)
  for _, c in ipairs(ch) do
    local ov = c.overrides[m]
    if ov then
      for i = #ov, 1, -1 do L[#L + 1] = ov[i] end
    end
  end
  for _, c in ipairs(ch) do
    local f = c.methods[m]
    if f then L[#L + 1] = f; break end
  end
  for _, c in ipairs(ch) do
    local nt = natives[c.name]
    if nt and nt[m] then L[#L + 1] = nt[m]; nativeSet[nt[m]] = true; break end
  end
  cc[m] = L
  return L
end
local function noSuper() return nil end
-- super closures are cached per (chain, level, self): weak keys (ephemerons), so dead objects and chains rebuilt by
-- invalidate() are collected. Saves one closure allocation per chain level per call on the hot Message path.
local runChain
local superCache = setmetatable({}, { __mode = "k" })   -- L -> { [level] = { [self] = fn } }
local function superFor(L, n, self)
  local per = superCache[L]
  if not per then per = {}; superCache[L] = per end
  local t = per[n]
  if not t then t = setmetatable({}, { __mode = "k" }); per[n] = t end
  local f = t[self]
  if f then return f end
  f = function(...) return runChain(L, n, self, ...) end
  t[self] = f
  return f
end
runChain = function(L, i, self, ...)
  local f = L[i]
  if not f then return nil end
  local n = i + 1
  if L[n] then
    if type(self) == "table" then return f(self, superFor(L, n, self), ...) end
    return f(self, function(...) return runChain(L, n, self, ...) end, ...)
  end
  return f(self, noSuper, ...)
end
local function invoke(self, clsName, m, ...)
  local L = buildChain(clsName, m)
  if #L == 0 then return nil end
  return runChain(L, 1, self, ...)
end
-- true when at least one non-native (script) element exists in the chain
local function hasScriptChain(clsName, m)
  local L = buildChain(clsName, m)
  for i = 1, #L do
    if not nativeSet[L[i]] then return true end
  end
  return false
end
R.invoke, R.buildChain, R.runChain, R.hasScriptChain = invoke, buildChain, runChain, hasScriptChain

-- Message-type filters (pxc2lua/msgfilter.py): for an override with filter F, the transpiler proved that for any
-- message type not in F it only calls super once with unchanged arguments, so it is left out of that type's chain.
-- F items are integers or names of K constants (the override compares against K.<name>).
local ovFilter = setmetatable({}, { __mode = "k" })
local typedCache = {}
local function filterPasses(F, mtype)
  local K = R.K
  for i = 1, #F do
    local c = F[i]
    if type(c) == "string" then c = K and K[c] end
    if type(c) ~= "number" or c == mtype then return true end
  end
  return false
end
-- chain of clsName.m for messages of type mtype, plus whether it has a script element
local function typedChain(clsName, m, mtype)
  local tc = typedCache[clsName]
  if not tc then tc = {}; typedCache[clsName] = tc end
  local tm = tc[m]
  if not tm then tm = {}; tc[m] = tm end
  local e = tm[mtype]
  if e then return e[1], e[2] end
  local L = buildChain(clsName, m)
  local T, script = {}, false
  for i = 1, #L do
    local f = L[i]
    local F = ovFilter[f]
    if not F or filterPasses(F, mtype) then
      T[#T + 1] = f
      if not nativeSet[f] then script = true end
    end
  end
  tm[mtype] = { T, script }
  return T, script
end
local function invokeTyped(self, clsName, m, mtype, ...)
  local L = typedChain(clsName, m, mtype)
  if #L == 0 then return nil end
  return runChain(L, 1, self, ...)
end
-- true when clsName or any script class derived from it has a script element in its chain for mtype
local wantsAnyCache = {}
local function typedWantsAny(clsName, m, mtype)
  local wc = wantsAnyCache[clsName]
  if not wc then wc = {}; wantsAnyCache[clsName] = wc end
  local wm = wc[m]
  if not wm then wm = {}; wc[m] = wm end
  local v = wm[mtype]
  if v ~= nil then return v end
  local _, s = typedChain(clsName, m, mtype)
  v = s
  if not v then
    for name, c in pairs(classes) do
      if not c.engine and name ~= clsName then
        local derived = false
        for _, b in ipairs(chainOf(name)) do
          if b.name == clsName then derived = true; break end
        end
        if derived then
          local _, s2 = typedChain(name, m, mtype)
          if s2 then v = true; break end
        end
      end
    end
  end
  wm[mtype] = v
  return v
end
R.typedChain, R.invokeTyped, R.typedWantsAny, R.ovFilter = typedChain, invokeTyped, typedWantsAny, ovFilter

R.gen = 0
local function invalidate() chainCache = {}; typedCache = {}; wantsAnyCache = {}; R.gen = R.gen + 1 end
R.invalidate = invalidate

---------------------------------------------------------------------------
-- object model for script classes and generic structs
---------------------------------------------------------------------------
local methodClosureCache = {}
local function methodClosure(clsName, m)
  local ck = methodClosureCache[clsName]
  if not ck then ck = {}; methodClosureCache[clsName] = ck end
  local f = ck[m]
  if f == nil then
    f = function(self, ...) return invoke(self, clsName, m, ...) end
    ck[m] = f
  end
  return f
end
local scriptMT = {}
local function scriptMTFor(clsName)
  local mt = scriptMT[clsName]
  if mt then return mt end
  mt = {}
  mt.__index = function(t, k)
    if type(k) == "string" then
      if #buildChain(clsName, k) > 0 then return methodClosure(clsName, k) end
      if k == "Childs" and R.childsOf then return R.childsOf(t) end
    end
    return 0
  end
  scriptMT[clsName] = mt
  return mt
end
R.scriptMTFor = scriptMTFor
R.methodClosure = methodClosure
local function clsOfObj(o)
  if type(o) ~= "table" then return nil end
  return rawget(o, "__cls")
end
R.clsOfObj = clsOfObj

local builtinClasses = {}     -- builtinClasses[name] = function(...) -> object
R.builtinClasses = builtinClasses

-- constructor chain: per class, override ctors (latest outermost) wrap the class ctor,
-- whose `super` continues with the base class chain.
local function runCtor(clsName, obj, ...)
  local ch = chainOf(clsName)
  local function stage(i, ...)
    local c = ch[i]
    if not c then return end
    local ov = c.ctorOv
    local function overrideStage(j, ...)
      if j == 0 then
        if c.ctor then
          return c.ctor(obj, function(...) return stage(i + 1, ...) end, ...)
        end
        local ec = c.engine and R.engineCtor[c.name]
        if ec then return ec(obj, ...) end
        return stage(i + 1, ...)
      end
      return ov[j](obj, function(...) return overrideStage(j - 1, ...) end, ...)
    end
    return overrideStage(#ov, ...)
  end
  return stage(1, ...)
end
R.runCtor = runCtor
R.engineCtor = {}      -- engineCtor[className] = function(obj, ...) -- creates the native object for script subclasses

local BASIC_DEFAULT = { bool = 0, int = 0, fixed = 0.0, float = 0.0, string = "" }
-- struct arguments passed by reference to constructors (new CMissile(parent, &launch, ...)) arrive as ref wrappers
local function unrefArgs(...)
  local n = select("#", ...)
  local a = { ... }
  local changed = false
  for i = 1, n do
    local x = a[i]
    if type(x) == "table" and R.isref(x) then
      local v = x.v
      if type(v) == "table" then a[i] = v; changed = true end
    end
  end
  if changed then return table.unpack(a, 1, n) end
  return ...
end
local function newObject(clsName, ...)
  local bd = BASIC_DEFAULT[clsName]
  if bd ~= nil then return bd end
  local b = builtinClasses[clsName]
  if b then return b(...) end
  local c = classes[clsName] or (ENGINE_BASE[clsName] and getClass(clsName))
  if not c then
    once("newcls:" .. tostring(clsName), "pxrt: new of unknown class %s", tostring(clsName))
    return setmetatable({ __cls = clsName }, scriptMTFor(clsName))
  end
  local obj = setmetatable({ __cls = clsName }, scriptMTFor(clsName))
  local ok, err = pcall(runCtor, clsName, obj, unrefArgs(...))
  if not ok then log("pxrt: ctor %s failed: %s", clsName, tostring(err)) end
  if R.onNewObject then
    local ok2, err2 = pcall(R.onNewObject, obj, clsName)
    if not ok2 then log("pxrt: onNewObject %s failed: %s", clsName, tostring(err2)) end
  end
  return obj
end
local function newStruct(clsName)
  local b = builtinClasses[clsName]
  if b then
    local ok, o = pcall(b)
    if ok then return o end
  end
  return setmetatable({ __cls = clsName }, scriptMTFor(clsName))
end
local function cloneDefault(d)
  if type(d) ~= "table" then return d end
  local c = {}
  for k, v in pairs(d) do c[k] = cloneDefault(v) end
  return setmetatable(c, getmetatable(d))
end
local function arr(dims, default)
  local function build(level)
    local n = dims[level] or 0
    local t = {}
    if level < #dims then
      for i = 0, n - 1 do t[i] = build(level + 1) end
    else
      for i = 0, n - 1 do t[i] = cloneDefault(default) end
    end
    if type(default) ~= "table" then
      return setmetatable(t, { __index = function() return default end })
    end
    return t
  end
  return build(1)
end
local function newarr(clsName, n)
  local bd = BASIC_DEFAULT[clsName]
  if bd ~= nil then return arr({ ti(n) }, bd) end
  local t = {}
  for i = 0, ti(n) - 1 do t[i] = newObject(clsName) end
  return t
end
local refSet = setmetatable({}, { __mode = "k" })
local function ref(getter, setter)
  local r = setmetatable({}, {
    -- a ref to a struct/object behaves like the struct itself (PX passes structs by pointer): other keys go to the target
    __index = function(_, k)
      local v = getter()
      if k == "v" then return v end
      if type(v) == "table" then return v[k] end
    end,
    __newindex = function(_, k, x)
      if k == "v" then setter(x) return end
      local v = getter()
      if type(v) == "table" then v[k] = x end
    end,
  })
  refSet[r] = true
  return r
end
R.isref = function(x) return refSet[x] == true end
local function delete(o)
  if type(o) ~= "table" then return end
  if R.onDelete then
    local ok, err = pcall(R.onDelete, o)
    if not ok then log("pxrt: delete failed: %s", tostring(err)) end
    return
  end
  if not rawget(o, "__a") then
    local f = o.Free
    if type(f) == "function" then pcall(f, o, 1) end
  end
end
local function isOf(v, clsName)
  local c = clsOfObj(v)
  if not c then return false end
  return isa(c, clsName)
end
R.new, R.newStruct, R.arr, R.newarr, R.ref, R.delete, R.is, R.cast = newObject, newStruct, arr, newarr, ref, delete, isOf,
  function(clsName, v) return v end
local flags = {}
R.flag = function(n) return flags[n] and true or false end
R.setflag = function(n) flags[n] = true end
R.struct = newStruct

---------------------------------------------------------------------------
-- package / chunk loader
---------------------------------------------------------------------------
-- Every lib or package owns a G table. Reads fall through to the G of the libs it requires,
-- then to engine globals. Names declared with gvars() stay owned by the declaring unit.
local libs = {}
R.libs = libs
local engineG = {}
R.engineG = engineG
local gvarOwner = {}

-- G[k] misses walk the required libs (depth first, each lib ending at engineG) on every access. Each G caches, per
-- name, the table that answered (re-checked with rawget) or false when no table had it. A name only appears in a G
-- through __newindex or gvars, and both drop that name from every cache, so lookups stay exactly the walk's.
-- Negative entries are kept only for Gs whose whole parent tree is Gs (engineG has no metatable).
local gParents = setmetatable({}, { __mode = "k" })
local gPure = setmetatable({}, { __mode = "k" })
local ownerCache = setmetatable({}, { __mode = "k" })   -- G -> { [k] = owner table | false }
local function forgetG(k)
  for _, c in pairs(ownerCache) do c[k] = nil end
end
R.forgetG = forgetG
local function resolveG(pl, k)
  for i = 1, #pl do
    local p = pl[i]
    local v = rawget(p, k)
    if v ~= nil then return v, p end
    local pp = gParents[p]
    if pp then
      local o
      v, o = resolveG(pp, k)
      if v ~= nil then return v, o end
    else
      v = p[k]
      if v ~= nil then return v, nil end
    end
  end
  local v = engineG[k]
  if v ~= nil then return v, engineG end
  return nil
end
local function newG(parentList)
  local G = {}
  local c = {}
  gParents[G] = parentList
  ownerCache[G] = c
  local pure = true
  for i = 1, #parentList do
    if not gPure[parentList[i]] then pure = false end
  end
  gPure[G] = pure
  setmetatable(G, {
    __index = function(t, k)
      local o = c[k]
      if o then
        local v = rawget(o, k)
        if v ~= nil then return v end
      elseif o == false then
        return nil
      end
      local v, ow = resolveG(parentList, k)
      if ow then c[k] = ow
      elseif v == nil and pure then c[k] = false end
      return v
    end,
    __newindex = function(t, k, v)
      if v == nil then
        -- k is not raw in t; removing it from a gvar owner needs no cache update (owner entries are re-checked)
        local owner = gvarOwner[k]
        if owner and owner ~= t then rawset(owner, k, nil) end
        return
      end
      forgetG(k)
      local owner = gvarOwner[k]
      if owner and owner ~= t then
        rawset(owner, k, v)
        return
      end
      rawset(t, k, v)
    end,
  })
  return G
end

-- entries are kept for the whole session: InitGraphic runs once, Init/FirstFrame/InitSMap every match
local pendingEntries = { InitGraphic = {}, Init = {}, FirstFrame = {}, InitSMap = {} }
R.pendingEntries = pendingEntries
local allUnits = {}
local entryOv = {}    -- entryOv[cls..":"..stage] = { override fns (innermost first) }

local function ctorArity(fn)
  local gi = debug and debug.getinfo
  if not gi then return 0 end
  local info = gi(fn, "u")
  return (info and info.nparams or 2) - 2
end

-- PX overloads: same name, different parameter lists. Pick by argument count, then by value type
-- (signature letters i/f/s come from pxgen: `p = ti(p)` -> i, `p = tf(p)` -> f, else s).
local OVINFO = setmetatable({}, { __mode = "k" })
local OVSET = setmetatable({}, { __mode = "k" })
local function ovPick(list, n, ...)
  local best, bestS
  for i = #list, 1, -1 do
    local c = list[i]
    local s = -math.abs(c.np - n) * 100
    local sig = c.sig
    if sig then
      for j = 1, #sig do
        local v = (select(j, ...))
        local t, mt = sig:sub(j, j), math.type(v)
        if t == "i" then
          if mt == "integer" then s = s + 2 elseif mt == "float" then s = s + 1 end
        elseif t == "f" then
          if mt == "float" then s = s + 2 elseif mt == "integer" then s = s + 1 end
        elseif type(v) == "string" then s = s + 2
        elseif mt == nil then s = s + 1 end
      end
    end
    if not bestS or s > bestS then best, bestS = c, s end
  end
  return best.fn
end
local function ovRegister(prev, fn, sig, unit, isMethod)
  local info = { fn = fn, np = debug.getinfo(fn, "u").nparams, sig = sig, unit = unit }
  OVINFO[fn] = info
  if prev then
    local set = OVSET[prev]
    if set and set.unit == unit then
      set[#set + 1] = info
      return prev
    end
    local pi = OVINFO[prev]
    if pi and pi.unit == unit and pi.fn ~= fn then
      local list = { unit = unit, pi, info }
      local disp
      if isMethod then
        disp = function(self, super, ...) return ovPick(list, 2 + select("#", ...), ...)(self, super, ...) end
      else
        disp = function(...) return ovPick(list, select("#", ...), ...)(...) end
      end
      OVSET[disp] = list
      return disp
    end
  end
  return fn
end

local function makeP(unit)
  local P = {}
  local pendingSig
  function P:sig(s) pendingSig = s end
  function P:file(name) unit.file = name end
  function P:require(list) for _, n in ipairs(list) do unit.requires[#unit.requires + 1] = n end end
  function P:defflag(f) if flags[f] == nil then flags[f] = false end end
  function P:class(name, base)
    local c = getClass(name)
    c.base = (base ~= "" and base) or nil
    c.engine = false
    invalidate()
  end
  function P:gvars(names)
    for _, n in ipairs(names) do
      gvarOwner[n] = unit.G
      if rawget(unit.G, n) == nil then rawset(unit.G, n, 0); forgetG(n) end
    end
  end
  function P:ginit(fn)
    unit.ginit[#unit.ginit + 1] = fn
    unit.ginitAll = unit.ginitAll or {}
    unit.ginitAll[#unit.ginitAll + 1] = fn
  end
  function P:entry(cls, name, fn)
    local list = pendingEntries[name]
    if list then list[#list + 1] = { unit = unit, cls = cls, fn = fn, done = false } end
  end
  function P:ctor(cls, fn, isOverride)
    local c = getClass(cls)
    if R.builtinClasses[cls] and not c.engine then return end
    if isOverride then
      c.ctorOv[#c.ctorOv + 1] = fn
    elseif c.ctor and c.ctorUnit == unit then
      -- overloaded constructors: dispatch on argument count
      local set = c.ctorSet
      if not set then
        set = {}
        c.ctorSet = set
        set[ctorArity(c.ctor)] = c.ctor
      end
      set[ctorArity(fn)] = fn
      c.ctor = function(obj, super, ...)
        local n = select("#", ...)
        local f = set[n]
        if not f then
          local best, bestN
          for k, v in pairs(set) do
            if k <= n and (not bestN or k > bestN) then best, bestN = v, k end
          end
          if not best then
            for k, v in pairs(set) do
              if not bestN or k < bestN then best, bestN = v, k end
            end
          end
          f = best
        end
        return f(obj, super, ...)
      end
    else
      c.ctor = fn
      c.ctorUnit = unit
      c.ctorSet = nil
    end
    invalidate()
  end
  function P:override(cls, name, fn, filter)
    if filter then ovFilter[fn] = filter end
    if cls == nil then
      local prev = unit.G[name]
      unit.G[name] = function(...) return fn(nil, prev or noSuper, ...) end
      return
    end
    if pendingEntries[name] then
      local k = tostring(cls) .. ":" .. name
      local l = entryOv[k]
      if not l then l = {}; entryOv[k] = l end
      l[#l + 1] = fn
    end
    local c = getClass(cls)
    local list = c.overrides[name]
    if not list then list = {}; c.overrides[name] = list end
    list[#list + 1] = fn
    invalidate()
  end
  function P:method(cls, name, fn)
    local sig = pendingSig; pendingSig = nil
    if R.builtinClasses[cls] and not getClass(cls).engine then return end
    local ms = getClass(cls).methods
    ms[name] = ovRegister(ms[name], fn, sig, unit, true)
    invalidate()
  end
  function P:func(name, fn)
    local sig = pendingSig; pendingSig = nil
    local bf = R.builtinFuncs and R.builtinFuncs[name]
    if bf then
      unit.G[name] = bf
      return
    end
    unit.G[name] = ovRegister(rawget(unit.G, name), fn, sig, unit, false)
  end
  return P
end

local RT = setmetatable({}, { __index = R })   -- passed to chunks as __R__
R.RT = RT

local function loadChunk(unit, chunk)
  local cname = tostring(unit.name)
  if type(chunk) == "table" then
    cname = cname .. "/" .. tostring(chunk[1])
    chunk = chunk[2]
  end
  local fn = chunk
  if type(chunk) == "string" then
    local f, err = load(chunk, "=" .. cname, "t", {})
    if not f then log("pxrt: chunk compile error in %s: %s", cname, tostring(err)); return false end
    fn = f
  end
  local ok, err = pcall(fn, RT, unit.P, unit.G)
  if not ok then log("pxrt: chunk load error in %s: %s", cname, tostring(err)); return false end
  return true
end

local loadedPackages = {}
local function loadLib(name)
  local lib = libs[name] or loadedPackages[name]
  if lib then return lib end
  lib = { name = "@lib/" .. name, requires = {}, ginit = {}, G = newG({}), pkg = name, deps = {} }
  libs[name] = lib
  allUnits[#allUnits + 1] = lib
  local okm, mod = pcall(require, "pxl_" .. name)
  if not okm or type(mod) ~= "table" then
    log("pxrt: lib %s not available: %s", name, tostring(mod))
    lib.P = makeP(lib)
    return lib
  end
  local parents = {}
  for _, dep in ipairs(mod.requires or {}) do
    parents[#parents + 1] = loadLib(dep).G
  end
  lib.G = newG(parents)
  lib.P = makeP(lib)
  lib.pkg = name
  lib.deps = mod.requires or {}
  for _, chunk in ipairs(mod.chunks or {}) do loadChunk(lib, chunk) end
  for _, gi in ipairs(lib.ginit) do
    local ok, err = pcall(gi)
    if not ok then log("pxrt: lib %s ginit error: %s", name, tostring(err)) end
  end
  lib.ginit = {}
  return lib
end
R.loadLib = loadLib

-- R.loadPackage(name, {libs={...}, chunks={fn|string,...}})
function R.loadPackage(name, def)
  if loadedPackages[name] then return loadedPackages[name] end
  if libs[name] then return libs[name] end
  local parents = {}
  for _, ln in ipairs(def.libs or {}) do
    parents[#parents + 1] = loadLib(ln).G
  end
  local unit = { name = name, requires = {}, ginit = {}, G = newG(parents), pkg = name, deps = def.libs or {} }
  unit.P = makeP(unit)
  loadedPackages[name] = unit
  allUnits[#allUnits + 1] = unit
  for _, chunk in ipairs(def.chunks or {}) do loadChunk(unit, chunk) end
  for _, gi in ipairs(unit.ginit) do
    local ok, err = pcall(gi)
    if not ok then log("pxrt: package %s ginit error: %s", name, tostring(err)) end
  end
  unit.ginit = {}
  R.packagesChanged = true
  return unit
end
R.loadedPackages = loadedPackages

-- The unit (package or library) whose script code called into the runtime: chunk names are "=<unit name>/<file>"
-- (see loadChunk). Asset lookups need it, so it is only used at load/init time.
function R.unitAt()
  local gi = debug and debug.getinfo
  if not gi then return nil end
  for level = 2, 12 do
    local info = gi(level, "S")
    if not info then return nil end
    local src = info.source
    if type(src) == "string" and src:byte(1) == 61 then   -- "="
      local lib = src:match("^=@lib/([^/]+)/")
      local u
      if lib then u = libs[lib] else u = loadedPackages[src:match("^=([^/]+)/") or ""] end
      if u then return u end
    end
  end
  return nil
end

-- a package that is enabled again (main.lua re-run without a runtime reset) registers its sprites/sounds anew
function R.rearmEntries(stage, only)
  for _, e in ipairs(pendingEntries[stage] or {}) do
    local un = e.unit and e.unit.name
    if un == only or un == "@lib/" .. only then e.done = false end
  end
end

-- only (optional): run just the entries of that package / lib (sprite loading resolves files against the
-- package whose initialize() is running)
function R.runEntries(stage, only)
  local list = pendingEntries[stage]
  if not list then return end
  for _, e in ipairs(list) do
    local un = e.unit and e.unit.name
    if not e.done and (not only or un == only or un == "@lib/" .. only) then
      e.done = true
      local fn = e.fn
      local ovl = entryOv[tostring(e.cls) .. ":" .. stage]
      if ovl then
        for _, ov in ipairs(ovl) do
          local inner = fn
          fn = function(...) return ov(nil, inner, ...) end
        end
      end
      local ok, err = pcall(fn)
      if not ok then log("pxrt: entry %s::%s failed: %s", tostring(e.cls), stage, tostring(err)) end
    end
  end
end

-- new match: Init / FirstFrame / InitSMap entries run again, per-match globals are rebuilt
function R.matchReset()
  for _, stage in ipairs({ "Init", "FirstFrame", "InitSMap" }) do
    for _, e in ipairs(pendingEntries[stage]) do e.done = false end
  end
  for _, u in ipairs(allUnits) do
    for _, gi in ipairs(u.ginitAll or {}) do
      local ok, err = pcall(gi)
      if not ok then log("pxrt: %s ginit (match reset) error: %s", tostring(u.name), tostring(err)) end
    end
  end
end
R.classes = classes

-- engine half (memory proxies, builtins, hooks)
local okE, errE = pcall(require, "pxrt_engine")
if not okE then log("pxrt: engine layer failed to load: %s", tostring(errE)) end
return R
