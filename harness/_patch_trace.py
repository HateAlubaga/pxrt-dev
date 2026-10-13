p = r'C:\Users\Admin\pxrt_dev\harness\bench.lua'
s = open(p, encoding='utf-8').read()

# 1. trace of all host calls that change the world
old = '''local skip = { jellyRandom = true }
for _, name in ipairs({'''
new = '''local skip = { jellyRandom = true }
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
  if traceOut then traceOut:write(line, "\\n") end
  for i = 1, #line do traceH = (traceH * 33 + line:byte(i)) % 4294967296 end
end
for _, name in ipairs({'''
assert old in s
s = s.replace(old, new, 1)

old = '''    _G[name] = function(...)
      hostCalls[name] = (hostCalls[name] or 0) + 1
      hostTotal = hostTotal + 1
      return f(...)
    end'''
new = '''    local tr = traceFn[name]
    _G[name] = function(...)
      hostCalls[name] = (hostCalls[name] or 0) + 1
      hostTotal = hostTotal + 1
      if tr then traceEv(name, ...) end
      return f(...)
    end'''
assert old in s
s = s.replace(old, new, 1)

old = 'H.build({ weapons'
new = 'if SCEN.trace then traceOut = io.open(SCEN.trace, "w") end\nH.build({ weapons'
# only the first occurrence after chunkLines block (H.build appears once)
assert old in s
s = s.replace(old, new, 1)

old = 'P("VM instructions per frame: %.0f", instr / frames)'
new = 'P("VM instructions per frame: %.0f", instr / frames)\nP("TRACE events=%d hash=%08x", traceN, traceH)\nif traceOut then traceOut:close() end'
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)

p = r'C:\Users\Admin\pxrt_dev\harness\bench.py'
s = open(p, encoding='utf-8').read()
old = "        elif args[i] == '--incl':"
new = """        elif args[i] == '--trace':
            trace = args[i + 1]; i += 2
        elif args[i] == '--base':
            base = args[i + 1]; i += 2
        elif args[i] == '--incl':"""
assert old in s
s = s.replace(old, new, 1)
s = s.replace("    msgs = '2'\n", "    msgs = '2'\n    trace = ''\n    base = ''\n", 1)
old = "    out = harness.sync_runtime()\n"
new = """    out = harness.sync_runtime()
    if base:
        import glob, shutil
        for f in glob.glob(os.path.join(base, 'pxrt*.lua')) + [os.path.join(base, 'pxboot.lua')]:
            shutil.copyfile(f, os.path.join(out, os.path.basename(f)))
"""
assert old in s
s = s.replace(old, new, 1)
old = "'true' if incl else 'false', warm, msgs))"
new = "'true' if incl else 'false', warm, msgs))\n    if trace:\n        lua.execute('SCEN.trace = %s' % harness.lua_str(trace.replace(chr(92), '/')))"
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
