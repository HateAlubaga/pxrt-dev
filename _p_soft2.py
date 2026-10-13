p = r'C:\Users\Admin\pxrt_dev\harness\mock_dll.lua'
s = open(p, encoding='utf-8', newline='').read()

old = "local function rb(a) return mem[a] or 0 end\n"
new = """-- virtual land bitmap (rows >= groundY solid, 1 bit per pixel, 4096x2048): no need to fill 1 MB of sparse memory
H.LAND_DATA, H.LAND_STRIDE, H.LAND_H, H.groundY = 0x3000000, 512, 2048, 1500
local function rb(a)
  local v = mem[a]
  if v then return v end
  local d = a - H.LAND_DATA
  if d >= 0 and d < H.LAND_STRIDE * H.LAND_H then
    return (d // H.LAND_STRIDE) >= H.groundY and 0xFF or 0
  end
  return 0
end
"""
assert s.count(old) == 1
s = s.replace(old, new, 1)

old = "  writeMemInt(H.ENV + 0x228, 2048 * 65536 // 65536 * 1)\n"
new = """  writeMemInt(H.ENV + 0x228, 2048 * 65536 // 65536 * 1)
  writeMemInt(H.ENV + 0x22C, 0x147B); writeMemInt(H.ENV + 0x230, 0)     -- gravity ~0.08, no wind
  do -- land bitmap (virtual rows, see rb)
    local bm = 0x1210000
    writeMemU32(H.LAND + 0x914, bm)
    writeMemU32(bm + 8, H.LAND_DATA); writeMemInt(bm + 0x10, H.LAND_STRIDE)
    writeMemInt(bm + 0x14, 4096); writeMemInt(bm + 0x18, 2048)
    writeMemInt(bm + 0x1C, 0); writeMemInt(bm + 0x20, 0); writeMemInt(bm + 0x24, 4096); writeMemInt(bm + 0x28, 2048)
  end
"""
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)

p = r'C:\Users\Admin\pxrt_dev\pxrt_e_soft.lua'
s = open(p, encoding='utf-8', newline='').read()
old = '  local BM = nat("CBitmap1")\n'
new = '  N.CBitmap1 = {}      -- own table: R.natives.CBitmap1 aliases the inert GUI CBitmap natives\n  local BM = N.CBitmap1\n'
assert s.count(old) == 1
s = s.replace(old, new, 1)
open(p, 'w', encoding='utf-8', newline='').write(s)
print('ok')
