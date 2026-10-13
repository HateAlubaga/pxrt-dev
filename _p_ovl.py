D = r'C:\Users\Admin\pxrt_dev'


def patch(path, old, new, count=1):
    s = open(path, encoding='utf-8', newline='').read()
    assert s.count(old) == count, (path, old[:60], s.count(old))
    s = s.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='').write(s)


OV_LUA = r'''-- PX overloads: same name, different parameter lists. Pick by argument count, then by value type
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
  local info = { fn = fn, np = gi(fn, "u").nparams, sig = sig, unit = unit }
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
'''

patch(D + r'\pxrt_core.lua', "local function makeP(unit)\n  local P = {}\n", OV_LUA)

patch(D + r'\pxrt_core.lua',
      """    if R.builtinClasses[cls] and not getClass(cls).engine then return end
    getClass(cls).methods[name] = fn
    invalidate()""",
      """    local sig = pendingSig; pendingSig = nil
    if R.builtinClasses[cls] and not getClass(cls).engine then return end
    local ms = getClass(cls).methods
    ms[name] = ovRegister(ms[name], fn, sig, unit, true)
    invalidate()""")

patch(D + r'\pxrt_core.lua',
      """  function P:func(name, fn)
    local bf = R.builtinFuncs and R.builtinFuncs[name]
    if bf then
      unit.G[name] = bf
      return
    end
    unit.G[name] = fn""",
      """  function P:func(name, fn)
    local sig = pendingSig; pendingSig = nil
    local bf = R.builtinFuncs and R.builtinFuncs[name]
    if bf then
      unit.G[name] = bf
      return
    end
    unit.G[name] = ovRegister(rawget(unit.G, name), fn, sig, unit, false)""")

TAG_PY = '''def tag_overloads(src):
    """Same-named P:func / P:method definitions are PX overloads; give each a signature (i/f/s per parameter) so the
    runtime can pick by argument types when the arity is the same."""
    head = re.compile(r'^__P__:(func|method)\\((?:"(\\w+)", )?"(\\w+)", function\\(([^)]*)\\)[ \\t]*$', re.M)
    ms = list(head.finditer(src))
    seen = {}
    for m in ms:
        k = (m.group(1), m.group(2), m.group(3))
        seen[k] = seen.get(k, 0) + 1
    out, last = [], 0
    for m in ms:
        key = (m.group(1), m.group(2), m.group(3))
        if seen[key] < 2:
            continue
        params = [p.strip() for p in m.group(4).split(',') if p.strip()]
        if m.group(1) == 'method':
            params = params[2:]
        body = src[m.end():m.end() + 600]
        sig = ''
        for p in params:
            if re.search(r'^\\s*' + re.escape(p) + r' = ti\\(' + re.escape(p) + r'\\)', body, re.M):
                sig += 'i'
            elif re.search(r'^\\s*' + re.escape(p) + r' = tf\\(' + re.escape(p) + r'\\)', body, re.M):
                sig += 'f'
            else:
                sig += 's'
        out.append(src[last:m.start()])
        out.append('__P__:sig("%s")\\n' % sig)
        last = m.start()
    out.append(src[last:])
    return ''.join(out)


def read_chunks(d):'''

patch(D + r'\pxgen.py', "def read_chunks(d):", TAG_PY)
patch(D + r'\pxgen.py',
      "fix_shadowed(open(fp, encoding='utf-8', errors='replace').read())",
      "tag_overloads(fix_shadowed(open(fp, encoding='utf-8', errors='replace').read()))")
print('ok')
