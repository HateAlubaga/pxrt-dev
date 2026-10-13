p = r'C:\Users\Admin\pxrt_dev\harness\bench.lua'
s = open(p, encoding='utf-8').read()
old = "  local f = rawget(_G, name)\n  if f then\n    local tr = traceFn[name]"
assert old in s
s = s.replace(old, "  local f = rawget(_G, name)\n  if f and not SCEN.nohook then\n    local tr = traceFn[name]", 1)
old = 'local msgPerFrame = SCEN.msgs or { 2 }'
assert old in s
s = s.replace(old, 'if SCEN.nohook then debug.sethook() end\n' + old, 1)
open(p, 'w', encoding='utf-8').write(s)
p = r'C:\Users\Admin\pxrt_dev\harness\bench.py'
s = open(p, encoding='utf-8').read()
old = "    if os.environ.get('HOSTSITE'):"
assert old in s
s = s.replace(old, "    if os.environ.get('NOHOOK'):\n        lua.execute('SCEN.nohook = true')\n" + old, 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
