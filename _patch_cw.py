def sub(path, old, new, count=1):
    s = open(path, encoding='utf-8', newline='').read()
    assert old in s, (path, old[:60])
    s = s.replace(old, new, count)
    open(path, 'w', encoding='utf-8', newline='').write(s)


eng = r'C:\Users\Admin\pxrt_dev\pxrt_engine.lua'
# CW cache table + invalidation in wr
sub(eng, '''local FIX = 65536.0
local rd = readMemInt
local function wr(a, v)
  if v ~= v then v = 0 end''', '''local FIX = 65536.0
local rd = readMemInt
-- per-dispatch cache of the current worm (script-visible GetCurrentWorm). Valid only inside one engine message dispatch
-- (E.tgHold > 0) and dropped by every engine write, engine call and the hook exit: see BF.GetCurrentWorm in pxrt_e_funcs.
local CW = { have = false, val = nil }
E.CW = CW
local function wr(a, v)
  CW.have = false
  if v ~= v then v = 0 end''')
sub(eng, 'function E.tgRelease() tgCache = nil end', 'function E.tgRelease() tgCache = nil; CW.have = false; CW.val = nil end')

funcs = r'C:\Users\Admin\pxrt_dev\pxrt_e_funcs.lua'
sub(funcs, '''  BF.GetCurrentWorm = function()
    local tg = E.turnGameAddr()
    if tg == 0 then return nil end
    local w, t = rd(tg + 0x130), rd(tg + 0x12C)
    if w <= 0 or w > 8 or t <= 0 or t > 6 then return nil end
    local a = E.hashGet(tg, 2, w + 16 * t)
    if a == 0 then return nil end
    return E.proxyAt(a)
  end''', '''  local CW = E.CW
  BF.GetCurrentWorm = function()
    if CW.have then return CW.val end
    local tg = E.turnGameAddr()
    if tg == 0 then return nil end
    local res
    local w, t = rd(tg + 0x130), rd(tg + 0x12C)
    if w > 0 and w <= 8 and t > 0 and t <= 6 then
      local a = E.hashGet(tg, 2, w + 16 * t)
      if a ~= 0 then res = E.proxyAt(a) end
    end
    if E.tgHold > 0 then CW.have = true; CW.val = res end
    return res
  end''')

cls = r'C:\Users\Admin\pxrt_dev\pxrt_e_classes.lua'
sub(cls, '''  function E.callThis(fn, this, ...)
    if not callThiscall or not okAddr(fn) then return 0 end''', '''  function E.callThis(fn, this, ...)
    E.CW.have = false
    if not callThiscall or not okAddr(fn) then return 0 end''')

hk = r'C:\Users\Admin\pxrt_dev\pxrt_e_hooks.lua'
sub(hk, '''    if top and top.addr == a then
      top.called = true
      local f = callOrig[top.cls]
      if f then
        local ok, r = pcall(f, top.This, senderUD(top, sender), mtype, size, E.msgAddr(mdata))''', '''    if top and top.addr == a then
      top.called = true
      local f = callOrig[top.cls]
      if f then
        E.CW.have = false
        local ok, r = pcall(f, top.This, senderUD(top, sender), mtype, size, E.msgAddr(mdata))
        E.CW.have = false''')
sub(hk, '''    fireGuard = true
    local ok, err = pcall(callRegs, FIREWEAPON, { eax = ws, ecx = sd }, worm)
    fireGuard = false''', '''    fireGuard = true
    E.CW.have = false
    local ok, err = pcall(callRegs, FIREWEAPON, { eax = ws, ecx = sd }, worm)
    E.CW.have = false
    fireGuard = false''')
print('patched')
