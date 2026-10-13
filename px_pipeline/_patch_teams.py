p = r'C:\Users\Admin\pxrt_dev\pxrt_e_game.lua'
s = open(p, encoding='utf-8', newline='').read()
assert '\r\n' not in s
old = """  local teamsView = setmetatable({}, {
    __index = function(_, ti0)
      local team = ti(ti0) + 1
      local tv = { Worms = setmetatable({}, {
        __index = function(_, wi0)
          local worm = ti(wi0) + 1
          return setmetatable({}, {
            __index = function(_, f)
              if f == "Health" then return rd(wormHealthAddr(team, worm)) end
              return 0
            end,
            __newindex = function(_, f, v)
              if f == "Health" then wr(wormHealthAddr(team, worm), ti(v)) end
            end,
          })
        end,
      }) }
      return tv
    end,
  })
"""
new = """  local function teamWormCount(team)
    local n = 0
    for w = 1, 8 do
      if E.wormAddr(team, w) ~= 0 then n = n + 1 end
    end
    return n
  end
  local teamsView = setmetatable({}, {
    __index = function(_, ti0)
      local team = ti(ti0) + 1
      local tv = setmetatable({ Worms = setmetatable({}, {
        __index = function(_, wi0)
          local worm = ti(wi0) + 1
          return setmetatable({}, {
            __index = function(_, f)
              if f == "Health" then return rd(wormHealthAddr(team, worm)) end
              if f == "State" then
                local a = E.wormAddr(team, worm)
                if a == 0 then return 135 end       -- free slot
                return rd(a + 0x44)
              end
              return 0
            end,
            __newindex = function(_, f, v)
              if f == "Health" then wr(wormHealthAddr(team, worm), ti(v)) end
            end,
          })
        end,
      }) }, {
        __index = function(_, f)
          if f == "NWorms" then return teamWormCount(team) end
          if f == "Active" then local ta = E.teamAddr(team); return ta ~= 0 and rd(ta + 0x3C) or 0 end
          return 0
        end,
      })
      return tv
    end,
  })
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)

# log dedupe
p = r'C:\Users\Admin\pxrt_dev\pxrt_core.lua'
s = open(p, encoding='utf-8', newline='').read()
old = """local function log(fmt, ...)
  if logCount > 4000 then return end
  logCount = logCount + 1
  local msg = (select("#", ...) > 0) and string.format(fmt, ...) or tostring(fmt)
"""
new = """local msgSeen = {}
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
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
