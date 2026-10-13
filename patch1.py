import re
p = r'C:\Users\Admin\pxrt_dev\pxrt_core.lua'
s = open(p, encoding='utf-8').read()

# 1. entry override chain
old = """  function P:override(cls, name, fn)
    if cls == nil then
      local prev = unit.G[name]
      unit.G[name] = function(...) return fn(nil, prev or noSuper, ...) end
      return
    end
"""
new = """  function P:override(cls, name, fn)
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
"""
assert old in s
s = s.replace(old, new)

old = "local allUnits = {}\n"
new = "local allUnits = {}\nlocal entryOv = {}    -- entryOv[cls..\":\"..stage] = { override fns (innermost first) }\n"
assert old in s
s = s.replace(old, new, 1)

old = """      e.done = true
      local ok, err = pcall(e.fn)
"""
new = """      e.done = true
      local fn = e.fn
      local ovl = entryOv[tostring(e.cls) .. ":" .. stage]
      if ovl then
        for _, ov in ipairs(ovl) do
          local inner = fn
          fn = function(...) return ov(nil, inner, ...) end
        end
      end
      local ok, err = pcall(fn)
"""
assert old in s
s = s.replace(old, new)

# 2. ctor overloads by arity
old = """    if isOverride then c.ctorOv[#c.ctorOv + 1] = fn else c.ctor = fn end
    invalidate()
"""
new = """    if isOverride then
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
"""
assert old in s
s = s.replace(old, new)

old = "local function makeP(unit)\n"
new = """local function ctorArity(fn)
  local gi = debug and debug.getinfo
  if not gi then return 0 end
  local info = gi(fn, "u")
  return (info and info.nparams or 2) - 2
end

local function makeP(unit)
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok')
