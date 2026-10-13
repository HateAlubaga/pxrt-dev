import re

# --- run.lua: optional trace hash of every world-changing host call (HARNESS_TRACE=1)
p = r'C:\Users\Admin\pxrt_dev\harness\run.lua'
s = open(p, encoding='utf-8').read()
old = 'H.build({ weapons = SCEN.weapons or {}, teams = 2, perTeam = 2 })\n'
new = old + '''
-- HARNESS_TRACE=1: hash every host call that changes the world, so two runtime versions can be compared package by package
local traceH, traceN = 5381, 0
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
    for i = 1, #line do traceH = (traceH * 33 + line:byte(i)) % 4294967296 end
  end
  for name in pairs(traced) do
    local f = rawget(_G, name)
    if f then _G[name] = function(...) ev(name, ...) return f(...) end end
  end
end
'''
assert old in s
s = s.replace(old, new, 1)
old = 'L("origCalls=%d", #H.origCalls)\n'
new = old + 'if os.getenv("HARNESS_TRACE") then L("trace events=%d hash=%08x", traceN, traceH) end\n'
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)

# --- harness.py: HARNESS_BASE=dir overrides the runtime files after the sync
p = r'C:\Users\Admin\pxrt_dev\harness\harness.py'
s = open(p, encoding='utf-8').read()
old = "    pxgen.write_libs(out)\n    return out\n"
new = """    pxgen.write_libs(out)
    base = os.environ.get('HARNESS_BASE')
    if base:
        import glob
        for f in glob.glob(os.path.join(base, 'pxrt*.lua')) + [os.path.join(base, 'pxboot.lua')]:
            shutil.copyfile(f, os.path.join(out, os.path.basename(f)))
    return out
"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)

# --- harness_all.py: HARNESS_OUT names the jsonl; trace lines are not issues
p = r'C:\Users\Admin\pxrt_dev\harness\harness_all.py'
s = open(p, encoding='utf-8').read()
old = "OUTJ = os.path.join(DEV, 'out', 'harness_res.jsonl')"
new = "OUTJ = os.environ.get('HARNESS_OUT') or os.path.join(DEV, 'out', 'harness_res.jsonl')"
assert old in s
s = s.replace(old, new, 1)
old = "l.startswith('H: calls')"
new = "l.startswith('H: trace') or l.startswith('H: calls')"
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
