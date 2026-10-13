p = r'C:\Users\Admin\pxrt_dev\harness\bench.lua'
s = open(p, encoding='utf-8').read()
old = """      hostCalls[name] = (hostCalls[name] or 0) + 1
      hostTotal = hostTotal + 1
      if tr then traceEv(name, ...) end"""
new = """      hostCalls[name] = (hostCalls[name] or 0) + 1
      hostTotal = hostTotal + 1
      if SCEN.hostsite then
        local k = name
        for lv = 2, 7 do
          local inf = debug.getinfo(lv, "Sl")
          if not inf then break end
          k = k .. " <- " .. inf.short_src:match("[^\\/]*$") .. ":" .. inf.currentline
        end
        siteCalls[k] = (siteCalls[k] or 0) + 1
      end
      if tr then traceEv(name, ...) end"""
assert old in s
s = s.replace(old, new, 1)
old = "local hostCalls, hostTotal = {}, 0\n"
assert old in s
s = s.replace(old, old + "local siteCalls = {}\n", 1)
old = "    for k in pairs(hostCalls) do hostCalls[k] = 0 end\n    hostTotal = 0\n    c0 = os.clock()"
assert old in s
s = s.replace(old, "    for k in pairs(hostCalls) do hostCalls[k] = 0 end\n    siteCalls = {}\n    hostTotal = 0\n    c0 = os.clock()", 1)
old = "local top = {}\nfor k, v in pairs(samples)"
new = """if SCEN.hostsite then
  local sc = {}
  for k, v in pairs(siteCalls) do sc[#sc + 1] = { k, v } end
  table.sort(sc, function(a, b) return a[2] > b[2] end)
  P("host call sites (per frame):")
  for i = 1, math.min(30, #sc) do P("   %6.1f  %s", sc[i][2] / frames, sc[i][1]) end
end
""" + old
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(s)

p = r'C:\Users\Admin\pxrt_dev\harness\bench.py'
s = open(p, encoding='utf-8').read()
print(s.count("callprof"))
