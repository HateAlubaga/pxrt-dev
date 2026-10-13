p = r'C:\Users\Admin\pxrt_dev\harness\run.lua'
s = open(p, encoding='utf-8').read()
old = 'local H = dofile(DEV .. "\\harness\\mock_dll.lua")\n'
assert old in s, 'anchor'
s = s.replace(old, old + 'if os.getenv("HARNESS_TRACE") then math.randomseed(20261007) end   -- deterministic runs for version diffing\n', 1)
open(p, 'w', encoding='utf-8').write(s)
print('ok')
