p = r'C:\Users\Admin\pxrt_dev\pxrt_core.lua'
s = open(p, encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)


# 1. super closures cached per (chain, level, self) instead of one new closure per level per call
rep('''local function noSuper() return nil end
local function runChain(L, i, self, ...)
  local f = L[i]
  if not f then return nil end
  local n = i + 1
  if L[n] then
    return f(self, function(...) return runChain(L, n, self, ...) end, ...)
  end
  return f(self, noSuper, ...)
end''',
'''local function noSuper() return nil end
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
end''')

# 2. global lookups: cache the table that owns a name (per G); any new global anywhere bumps gver and drops caches
rep('''local gvarOwner = {}

local function newG(parentList)
  local G = {}
  setmetatable(G, {
    __index = function(t, k)
      for i = 1, #parentList do
        local v = rawget(parentList[i], k)
        if v == nil then v = parentList[i][k] end
        if v ~= nil then return v end
      end
      return engineG[k]
    end,
    __newindex = function(t, k, v)
      local owner = gvarOwner[k]
      if owner and owner ~= t then
        rawset(owner, k, v)
        return
      end
      rawset(t, k, v)
    end,
  })
  return G
end''',
'''local gvarOwner = {}

-- G[k] misses walk the required libs (depth first, each lib ending at engineG) on every access. The table that
-- answered is cached per G and re-checked with rawget; a name that appears in some G later (only through
-- __newindex or gvars) bumps gver, which drops every cache, so the lookup order stays exactly the walk's.
local gParents = setmetatable({}, { __mode = "k" })
local ownerCache = setmetatable({}, { __mode = "k" })   -- G -> { [k] = owner table }
local function bumpG() ownerCache = setmetatable({}, { __mode = "k" }) end
R.bumpG = bumpG
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
  gParents[G] = parentList
  setmetatable(G, {
    __index = function(t, k)
      local c = ownerCache[t]
      if c then
        local o = c[k]
        if o then
          local v = rawget(o, k)
          if v ~= nil then return v end
        end
      else
        c = {}
        ownerCache[t] = c
      end
      local v, o = resolveG(parentList, k)
      if o then c[k] = o end
      return v
    end,
    __newindex = function(t, k, v)
      bumpG()
      local owner = gvarOwner[k]
      if owner and owner ~= t then
        rawset(owner, k, v)
        return
      end
      rawset(t, k, v)
    end,
  })
  return G
end''')

rep('''      gvarOwner[n] = unit.G
      if rawget(unit.G, n) == nil then rawset(unit.G, n, 0) end''',
'''      gvarOwner[n] = unit.G
      if rawget(unit.G, n) == nil then rawset(unit.G, n, 0); bumpG() end''')
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
