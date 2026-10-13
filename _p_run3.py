p = r'C:\Users\Admin\pxrt_dev\harness\run.lua'
s = open(p, encoding='utf-8', newline='').read()
old = "frames(30)\n"
new = "frames(30)\nif os.getenv(\"HARNESS_PROBE\") then local okp, e = pcall(function() dofile(os.getenv(\"HARNESS_PROBE\"))(R, E, H, L) end); if not okp then L(\"probe failed: %s\", tostring(e)) end end\n"
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
