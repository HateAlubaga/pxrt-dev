import re


def patch(path, old, new, count=1):
    s = open(path, encoding='utf-8', newline='').read()
    assert s.count(old) == count, (path, old[:60], s.count(old))
    s = s.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='').write(s)


D = r'C:\Users\Admin\pxrt_dev'

# 1. core: engine classes never referenced before (CGas, ...) are creatable by `new`
patch(D + r'\pxrt_core.lua',
      "  local c = classes[clsName]\n  if not c then\n    once(\"newcls:\"",
      "  local c = classes[clsName] or (ENGINE_BASE[clsName] and getClass(clsName))\n  if not c then\n    once(\"newcls:\"")

# 2. funcs: method call whose name is shadowed by an instance field of the same name (PxParticle.GravityFactor)
patch(D + r'\pxrt_e_funcs.lua',
      """      local f = o[name]
      if type(f) == "function" then return f(o, ...) end
      return missingMethod(o, name)
    end
    if o == nil or o == 0 then""",
      """      local f = o[name]
      if type(f) == "function" then return f(o, ...) end
      local cls = rawget(o, "__cls")
      if cls and #R.buildChain(cls, name) > 0 then return R.methodClosure(cls, name)(o, ...) end
      return missingMethod(o, name)
    end
    if o == nil or o == 0 then""")

# 3. classes: per-team weapon Delay array
patch(D + r'\pxrt_e_classes.lua',
      """        __newindex = function(_, j, v) setAmmo(team, ti(j) - 2, v) end,
      }) }""",
      """        __newindex = function(_, j, v) setAmmo(team, ti(j) - 2, v) end,
      }), Delay = setmetatable({}, {
        __index = function(_, j)
          local t = teamUD(team)
          if t and getTeamWeaponDelay then
            local ok, v = pcall(getTeamWeaponDelay, t, ti(j) + 2)
            if ok and type(v) == "number" then return v end
          end
          return 0
        end,
        __newindex = function(_, j, v)
          local t = teamUD(team)
          if t and setTeamWeaponDelay then pc(setTeamWeaponDelay, t, ti(j) + 2, ti(v)) end
        end,
      }) }""")

# 4. engine module list + harness runtime list
patch(D + r'\pxrt_engine.lua', '"pxrt_e_soft", "pxrt_e_hooks" }', '"pxrt_e_soft", "pxrt_e_extra", "pxrt_e_hooks" }')
patch(D + r'\harness\harness.py', "'pxrt_e_soft.lua', 'pxrt_e_hooks.lua']", "'pxrt_e_soft.lua', 'pxrt_e_extra.lua', 'pxrt_e_hooks.lua']")

# 5. pxgen: `x:name(...)` -> mc(x, "name", ...) for names that are both a method and an instance field of the chunk
patch(D + r'\pxgen.py',
      """def read_chunks(d):""",
      '''def fix_shadowed(src):
    """A PX class may have a field and a method of the same name (AF_Shield, GravityFactor). Lua `obj:name()` would
    find the field first, so route those calls through mc()."""
    meth = set(re.findall(r'__P__:(?:method|override)\\("\\w+", "(\\w+)"', src))
    if not meth:
        return src
    fields = set(re.findall(r'\\b\\w+\\.(\\w+)\\s*=[^=]', src))
    for n in sorted(meth & fields):
        src = re.sub(r'\\b([A-Za-z_][\\w\\.]*):' + n + r'\\(\\s*\\)', r'mc(\\1, "' + n + '")', src)
        src = re.sub(r'\\b([A-Za-z_][\\w\\.]*):' + n + r'\\(', r'mc(\\1, "' + n + '", ', src)
    return src


def read_chunks(d):''')
patch(D + r'\pxgen.py', "import os, json, sys\n", "import os, json, sys, re\n")
patch(D + r'\pxgen.py',
      "            out.append((c, open(fp, encoding='utf-8', errors='replace').read()))",
      "            out.append((c, fix_shadowed(open(fp, encoding='utf-8', errors='replace').read())))")
print('ok')
