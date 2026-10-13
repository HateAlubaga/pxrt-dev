p = r'C:\Users\Admin\pxrt_dev\pxrt_core.lua'
s = open(p, encoding='utf-8').read()


def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)


i = s.index('-- G[k] misses walk the required libs')
j = s.index('local function newG(parentList)')
k = s.index('\nend\n', j) + 5
s = s[:i] + '''-- G[k] misses walk the required libs (depth first, each lib ending at engineG) on every access. Each G caches, per
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
''' + s[k:]
rep('if rawget(unit.G, n) == nil then rawset(unit.G, n, 0); bumpG() end',
    'if rawget(unit.G, n) == nil then rawset(unit.G, n, 0); forgetG(n) end')
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
