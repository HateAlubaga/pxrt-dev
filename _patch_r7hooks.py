import re
DEV = r'C:\Users\Admin\pxrt_dev'

def patch(path, pairs):
    s = open(path, encoding='utf-8').read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:60])
        s = s.replace(old, new)
    open(path, 'w', encoding='utf-8', newline='\n').write(s)

# ---------------------------------------------------------------- engine: CWorm.Anim + animator proxies
patch(DEV + r'\pxrt_engine.lua', [
('''  AnimHelper = { 0x368, "p" }, CurWeapon = { 0x36C, "w" },
}''',
'''  AnimHelper = { 0x368, "p" }, Anim = { 0x368, "anim" }, CurWeapon = { 0x36C, "w" },
}'''),
('''      elseif kind == "w" then return E.weaponAt(rdU(a + off), a)''',
'''      elseif kind == "w" then return E.weaponAt(rdU(a + off), a)
      elseif kind == "anim" then return E.animAt(rdU(a + off))'''),
('''E.classAt = classAt''',
'''E.classAt = classAt
-- worm animators (CSpriteAnim, WA vtable 0x6640CC) are not tasks: plain proxies outside the task proxy table
local animProxies = setmetatable({}, { __mode = "v" })
function E.animAt(a)
  if not okAddr(a) then return nil end
  local p = animProxies[a]
  if not p then
    p = setmetatable({ __a = a, __cls = "CSpriteAnim" }, getMT("CSpriteAnim"))
    animProxies[a] = p
  end
  return p
end'''),
('''E.WA_WORMANIMSTATE = function()''',
'''E.WA_RENDERWORM = function() return E.waFn(0x50FCD0, "\\x24\\x08\\x50\\x8D\\x4C\\x24\\x14\\x51\\x8D\\x54\\x24\\x14\\x52\\x8D\\x44\\x24") end
E.WA_SETANIM = function() return E.waFn(0x4F5BD0, "\\x5E\\x1C\\x83\\xC3\\x01\\x81\\xE3\\x0F\\x00\\x00\\x80\\x79\\x05\\x4B\\x83\\xCB") end
E.WA_WORMANIMSTATE = function()'''),
])

# ---------------------------------------------------------------- hooks
H = DEV + r'\pxrt_e_hooks.lua'
patch(H, [
# foreign vtable8 callbacks run first, as if registered before pxrt
('''    local function hook(This, sender, mtype, size, data)
      local h0 = E.tgHold''',
'''    local function hook(This, sender, mtype, size, data)
      local fret = 0
      local fl = foreignVt8[cls]
      if fl then fret = runForeign(fl, cls, This, sender, mtype, size, data) end
      local h0 = E.tgHold'''),
('''      if ok then return r end
      once("vt8err:" .. cls, "pxrt: %s vtable8 hook error: %s", cls, tostring(r))
      return 0
    end''',
'''      if ok then
        if fret ~= 0 then return 1 end
        return r
      end
      once("vt8err:" .. cls, "pxrt: %s vtable8 hook error: %s", cls, tostring(r))
      return fret
    end'''),
('''  local function makeVt8(cls)''',
'''  -- vtable8 callbacks of other (non-pxrt) packages registered after pxrt hooked the class. The host runs callbacks
  -- in registration order and pxrt's runs WA's handler itself, so a later callback would see every message only
  -- after WA handled it (the hang-glider's M_FRAME velocity was overwritten by the parachute physics). They are kept
  -- here and run at the start of pxrt's callback: the order they had before pxrt.
  local foreignVt8 = {}
  local function runForeign(fl, cls, This, sender, mtype, size, data)
    local fret = 0
    for i = 1, #fl do
      local ok, r = pcall(fl[i], This, sender, mtype, size, data)
      if not ok then
        once("vt8foreign:" .. cls .. ":" .. i, "pxrt: %s vtable8 callback of another package failed: %s", cls, tostring(r))
      elseif r and r ~= 0 then
        fret = 1
      end
    end
    return fret
  end

  local function makeVt8(cls)'''),
('''  local hookedCls = {}
  local hookedGen
  function E.hookClasses()
    local gen = getCallbackGeneration and getCallbackGeneration() or 0
    if hookedGen ~= gen then hookedGen = gen; hookedCls = {} end
    for cls, ct in pairs(CT) do
      if not hookedCls[cls] and (cls == "CTurnGame" or R.hasScriptChain(cls, "Message")) then
        local reg = _G[ct .. "_RegisterCallback_vtable8"]''',
'''  local hookedCls = {}
  local hookedGen
  -- CTaskX_RegisterCallback_vtable8 globals are wrapped: once pxrt hooked class X, later registrations go to
  -- foreignVt8. __pxrtVt8Real maps each wrapper to the host function (survives a runtime reload).
  local wrapReal = rawget(_G, "__pxrtVt8Real") or setmetatable({}, { __mode = "k" })
  rawset(_G, "__pxrtVt8Real", wrapReal)
  local wrapped = {}   -- CTaskX -> wrapper installed by this runtime instance
  local function regOf(cls, ct)
    local name = ct .. "_RegisterCallback_vtable8"
    local cur = rawget(_G, name)
    if type(cur) ~= "function" then return nil end
    local real = wrapReal[cur] or cur
    if cur ~= wrapped[ct] then
      local w = function(cb)
        if hookedCls[cls] and type(cb) == "function" then
          local fl = foreignVt8[cls] or {}
          foreignVt8[cls] = fl
          fl[#fl + 1] = cb
          return 0
        end
        return real(cb)
      end
      wrapReal[w] = real
      wrapped[ct] = w
      rawset(_G, name, w)
    end
    return real
  end
  function E.hookClasses()
    local gen = getCallbackGeneration and getCallbackGeneration() or 0
    if hookedGen ~= gen then hookedGen = gen; hookedCls = {}; foreignVt8 = {} end
    for cls, ct in pairs(CT) do
      if not hookedCls[cls] and (cls == "CTurnGame" or R.hasScriptChain(cls, "Message")) then
        local reg = regOf(cls, ct)'''),
# engine function hooks, installed with the class hooks
('''  function E.install()
    local gen = getCallbackGeneration and getCallbackGeneration() or 0
    if E.installedGen == gen then
      E.hookClasses()   -- a package loaded since the last call may override Message of a class not hooked yet
      return
    end
    E.installedGen = gen
    E.hookClasses()''',
'''  ---------------------------------------------------------------------
  -- engine function hooks (host hookFunction): CWorm::RenderWorm, CSpriteAnim::SetAnimEx
  ---------------------------------------------------------------------
  -- RenderWorm = WA 0x50FCD0 (eax = worm): draws the worm body sprite inside the worm's draw message.
  -- SetAnimEx = WA 0x4F5BD0, the animator's SetAnim (vtable 0x6640CC +0x18): thiscall (sprite, phase), ret 8.
  -- Hooked only once some loaded script overrides them; without an override the hook calls the original at once.
  local hookIds = {}   -- per runtime instance: hookFunction with a known name replaces the callback
  local hasChain = R.hasScriptChain
  local function u32(v) v = ti(v) return v & 0xFFFFFFFF end
  local function s32(v) if v >= 0x80000000 then return v - 0x100000000 end return v end
  nat("CWorm").RenderWorm = function(self)
    local a, id = rawget(self, "__a"), hookIds.render
    if a and id then callHookOriginal(id, a) end
    return 0
  end
  nat("CSpriteAnim").SetAnimEx = function(self, super, sindex, frame)
    local a, id = rawget(self, "__a"), hookIds.anim
    if a and id then callHookOriginal(id, a, u32(sindex), u32(math.floor(tf(frame) * 65536 + 0.5))) end
    return 0
  end
  R.invalidate()
  local function onRenderWorm(worm)
    local id = hookIds.render
    if not hasChain("CWorm", "RenderWorm") then callHookOriginal(id, worm) return end
    local o = E.objectFor(worm, "CWorm")
    if not o then callHookOriginal(id, worm) return end
    local ok, err = pcall(R.invoke, o, "CWorm", "RenderWorm")
    if not ok then once("renderworm", "pxrt: RenderWorm chain failed: %s", tostring(err)) end
  end
  local function onSetAnim(anim, sprite, phase)
    local id = hookIds.anim
    if not hasChain("CSpriteAnim", "SetAnimEx") then return callHookOriginal(id, anim, sprite, phase) end
    local o = E.animAt(anim)
    if not o then return callHookOriginal(id, anim, sprite, phase) end
    local ok, err = pcall(R.invoke, o, "CSpriteAnim", "SetAnimEx", s32(sprite), s32(phase) / 65536.0)
    if not ok then once("setanim", "pxrt: SetAnimEx chain failed: %s", tostring(err)) end
  end
  local function fnHook(key, name, cls, m, addrFn, spec, cb)
    if hookIds[key] or not hasChain(cls, m) then return end
    if type(hookFunction) ~= "function" or type(callHookOriginal) ~= "function" then
      once("nohookfn", "pxrt: the DLL has no hookFunction: %s::%s overrides stay inert", cls, m)
      return
    end
    local fn = addrFn()
    if fn == 0 then return end
    local ok, id = pcall(hookFunction, name, fn, spec, cb)
    if ok and type(id) == "number" then
      hookIds[key] = id
      log("pxrt: %s::%s hooked at %X", cls, m, fn)
    else
      once("hookfn:" .. name, "pxrt: hooking %s::%s failed: %s", cls, m, tostring(id))
    end
  end
  function E.installFnHooks()
    fnHook("render", "pxrt_RenderWorm", "CWorm", "RenderWorm", E.WA_RENDERWORM, { regs = { "eax" } }, onRenderWorm)
    fnHook("anim", "pxrt_SetAnimEx", "CSpriteAnim", "SetAnimEx", E.WA_SETANIM, { regs = { "ecx" }, nstack = 2 }, onSetAnim)
  end

  function E.install()
    local gen = getCallbackGeneration and getCallbackGeneration() or 0
    if E.installedGen == gen then
      E.hookClasses()   -- a package loaded since the last call may override Message of a class not hooked yet
      E.installFnHooks()
      return
    end
    E.installedGen = gen
    E.hookClasses()
    E.installFnHooks()'''),
])
print('ok')
