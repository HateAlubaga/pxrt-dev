p = r'C:\Users\Admin\pxrt_dev\harness\run.lua'
s = open(p, encoding='utf-8', newline='').read()
old = """debug.sethook(function() budget = budget + 1; if budget > 60 then error("TIMEOUT (instruction budget)", 0) end end, "", 1000000)"""
new = """debug.sethook(function()
  budget = budget + 1
  if budget > 60 then
    if os.getenv("HARNESS_TB") and _G.__pxrt_logsink then
      local tb = debug.traceback("TIMEOUT-TB", 2)
      local n = 0
      for line in tb:gmatch("[^\n]+") do n = n + 1; if n <= 14 then _G.__pxrt_logsink("TB " .. line) end end
    end
    error("TIMEOUT (instruction budget)", 0)
  end
end, "", 1000000)"""
assert old in s
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
