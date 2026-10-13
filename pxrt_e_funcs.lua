-- pxrt_e_funcs: PX free builtin functions (F.*), builtin classes, R.F / R.call / R.mc
return function(R, E)
  local rd, wr, rdf, wrf, rdU = E.rd, E.wr, E.rdf, E.wrf, E.rdU
  local ti, tf, T, isnull = R.ti, R.tf, R.T, R.isnull
  local log, once = R.log, R.once
  local floor, sqrt, abs = math.floor, math.sqrt, math.abs
  local mtype = math.type
  local type, tostring, tonumber, pairs, setmetatable, rawget, rawset = type, tostring, tonumber, pairs, setmetatable, rawget, rawset

  local F = {}
  local BF = {}          -- overrides for script-declared functions (P:func)
  R.F, R.builtinFuncs = F, BF
  E.F = F
  setmetatable(F, {
    __index = function(t, k)
      once("F:" .. tostring(k), "pxrt: missing builtin F.%s", tostring(k))
      local f = function() return 0 end
      rawset(t, k, f)
      return f
    end,
  })

  local function pc(f, ...)
    if type(f) ~= "function" then return nil end
    local ok, a, b = pcall(f, ...)
    if ok then return a, b end
    once("pc:" .. tostring(a), "pxrt: native call failed: %s", tostring(a))
    return nil
  end
  E.pc = pc

  ---------------------------------------------------------------------
  -- math / strings
  ---------------------------------------------------------------------
  F.sin = function(x) return math.sin(tf(x)) end
  F.cos = function(x) return math.cos(tf(x)) end
  F.tan = function(x) return math.tan(tf(x)) end
  F.asin = function(x) return math.asin(tf(x)) end
  F.acos = function(x) return math.acos(tf(x)) end
  F.sqrt = function(x) x = tf(x); if x < 0 then return 0.0 end return sqrt(x) end
  F.abs = function(x) if mtype(x) == "integer" then return x < 0 and -x or x end return abs(tf(x)) end
  F.atan2 = function(y, x) return (math.atan2 or math.atan)(tf(y), tf(x)) end
  F.atan = function(x) return math.atan(tf(x)) end
  F.exp = function(x) return math.exp(tf(x)) end
  F.log = function(x) x = tf(x); if x <= 0 then return 0.0 end return math.log(x) end
  F.pow = function(a, b) return tf(a) ^ tf(b) end
  F.floor = function(x) return floor(tf(x)) + 0.0 end
  F.random = function(n) return E.random(n) end
  F.RandomInt = function(a, b) a, b = ti(a), ti(b); if b < a then return a end return a + E.random(b - a + 1) end
  F.StrCon = function(a, b) return R.str(a) .. R.str(b) end
  F.ItoA = function(v) return tostring(ti(v)) end
  F.ftoa = function(v) return R.str(tf(v)) end
  F.atoi = function(s) return ti(tonumber(s) or 0) end
  F.StrLen = function(s) return #R.str(s) end
  F.StrCmp = function(a, b)
    a, b = R.str(a), R.str(b)
    if a == b then return 0 end
    return a < b and -1 or 1
  end
  F.StrLeft = function(s, n) return R.str(s):sub(1, ti(n)) end
  F.StrRight = function(s, n) n = ti(n); if n <= 0 then return "" end return R.str(s):sub(-n) end
  F.StrChr = function(s, c)
    s = R.str(s)
    if type(c) == "number" then c = string.char(ti(c) & 255) end
    local i = s:find(R.str(c), 1, true)
    return i and (i - 1) or -1
  end
  F.StrSave = function(s) return R.str(s) end
  F.MakeNumberString = function(l, n, r) return R.str(l) .. tostring(ti(n)) .. R.str(r) end
  F.WriteToLog = function(s) log("px: %s", R.str(s)) end
  F.PrintMessage = function(i) if i ~= nil then log("px msg: %s", R.str(i)) end end
  F.zero = function(x)
    if type(x) ~= "table" then return 0 end
    local target = x
    if R.isref(x) then
      local inner = x.v
      if type(inner) ~= "table" then x.v = 0; return 0 end
      target = inner
    end
    if rawget(target, "__a") then return 0 end
    local keep = rawget(target, "__cls")
    for k in pairs(target) do
      if k ~= "__cls" then rawset(target, k, nil) end
    end
    if keep then rawset(target, "__cls", keep) end
    return 0
  end

  ---------------------------------------------------------------------
  -- colours
  ---------------------------------------------------------------------
  F.RGB = function(r, g, b) return ((ti(r) & 255) << 16) | ((ti(g) & 255) << 8) | (ti(b) & 255) end
  F.ARGB = function(a, r, g, b) return ((ti(a) & 255) << 24) | ((ti(r) & 255) << 16) | ((ti(g) & 255) << 8) | (ti(b) & 255) end
  E.colorMod = { color = nil, blend = 0 }
  F.SetColorMod = function(c, b) E.colorMod.color = ti(c); E.colorMod.blend = ti(b) end
  F.ClearColorMod = function() E.colorMod.color = nil; E.colorMod.blend = 0 end

  ---------------------------------------------------------------------
  -- engine info
  ---------------------------------------------------------------------
  function F.GetTeamColor(team)
    team = ti(team)
    if team < 1 then return 0 end
    local dd = E.ddGame()
    if dd ~= 0 then
      local a = rd(dd + 17964 + 1308 * (team - 1))
      if a >= 0 and a < 6 then return a end
    end
    return team - 1
  end
  F.GetLocalMachine = function() return 0 end
  F.IsReplay = function() local ok, v = pcall(isReplayPlayback); return (ok and v) and 1 or 0 end
  F.IsMultiplayer = function() return 0 end
  F.GetTeamName = function(team) return "Team " .. tostring(ti(team)) end
  F.GetName = function(o) return "" end
  F.SetName = function(o, n) return 0 end
  F.EMType = function(v) return ti(v) end
  F.EObjState = function(v) return ti(v) end
  F.CalculateSoundVolume = function() return 1.0 end
  F.CalculateSoundPan = function(x, y)
    local dx = tf(x) - (E.cameraX and E.cameraX() or 0)
    local p = dx * 0.0001
    if p < -1 then p = -1 elseif p > 1 then p = 1 end
    return p
  end

  function F.ShowMessage(s)
    s = R.str(s)
    pc(showChatMessage, s, 6)
  end
  function F.ShowTeamMessage(kind, s, team)
    pc(showChatMessage, R.str(s), 6)
  end

  local keyMap = { [16] = 0x10, [17] = 0x11, [13] = 0x0D }
  function F.IsKeyPressed(vk)
    local ok, v = pcall(isKeyDown, ti(vk))
    return (ok and v) and 1 or 0
  end
  F.IsKeyPressedB = F.IsKeyPressed

  -- weapon lookup: returns a weapon proxy (id based)
  function F.GetWeaponByName(name)
    name = R.str(name)
    local id = -1
    if weaponIdByName then
      local ok, v = pcall(weaponIdByName, name)
      if ok and type(v) == "number" then id = v end
    end
    return E.weaponById(id, name)
  end

  ---------------------------------------------------------------------
  -- sprites / images / sounds
  ---------------------------------------------------------------------
  -- Asset files. ProjectX finds an attachment in the package of the script that asks for it: a library's art sits in
  -- the library's own package (jelly\packages\<lib>\<ver>\assets), some in packages the script requires. The host
  -- only searches the package whose initialize() is running (and none at match start), so library art stayed a blank
  -- template. Names are therefore resolved here to a path the host takes as is; a name found nowhere stays bare and
  -- keeps the host's own lookup (active package, fuzzy spelling).
  E.PACKAGES_DIR = E.PACKAGES_DIR or "jelly\\packages\\"
  local VERSIONS = { "0.0.1", "1.0.0", "2.0.0", "0.0.2", "0.1.0", "1.0.1" }
  local function fileExists(p)
    local f = io and io.open and io.open(p, "rb")
    if f then f:close() return true end
    return false
  end
  local pkgDirs = {}
  local function pkgDir(pkg)
    local d = pkgDirs[pkg]
    if d ~= nil then return d end
    d = false
    for _, v in ipairs(VERSIONS) do
      local c = E.PACKAGES_DIR .. pkg .. "\\" .. v .. "\\"
      if fileExists(c .. "manifest.json") or fileExists(c .. "main.lua") then d = c break end
    end
    pkgDirs[pkg] = d
    return d
  end
  -- px2jelly saved attachments with every byte outside [A-Za-z0-9._-] replaced by "_"
  local function findIn(pkg, name)
    local d = pkgDir(pkg)
    if not d then return nil end
    local rel = name:gsub("/", "\\")
    local base = rel:match("[^\\]+$") or rel
    local cands = { d .. rel, d .. "assets\\" .. rel, d .. "assets\\" .. base, d .. "assets\\" .. base:gsub("[^%w%._%-]", "_") }
    for _, c in ipairs(cands) do
      if fileExists(c) then return c end
    end
    return nil
  end
  local function searchOrder(unit)
    local order, seen = {}, {}
    local function add(p) if type(p) == "string" and p ~= "" and not seen[p] then seen[p] = true; order[#order + 1] = p end end
    -- the unit's own package, then what it requires, breadth first
    local queue, qi = { unit }, 1
    while queue[qi] do
      local u = queue[qi]
      qi = qi + 1
      add(u.pkg)
      for _, list in ipairs({ u.requires or {}, u.deps or {} }) do
        for _, n in ipairs(list) do
          if not seen[n] then
            add(n)
            local dep = R.libs[n] or R.loadedPackages[n]
            if dep then queue[#queue + 1] = dep end
          end
        end
      end
    end
    -- then every other loaded unit
    for n in pairs(R.libs) do add(n) end
    for n in pairs(R.loadedPackages) do add(n) end
    return order
  end
  local assetCache = {}
  function E.resolveAsset(name, unit)
    if type(name) ~= "string" or name == "" then return name end
    local head = name:sub(1, 6):lower()
    if name:find(":", 1, true) or head == "jelly\\" or head == "jelly/" then return name end   -- already a path
    unit = unit or R.unitAt()
    if not unit then return name end
    local key = unit.name .. "|" .. name
    local hit = assetCache[key]
    if hit then return hit end
    local found, from
    for _, pkg in ipairs(searchOrder(unit)) do
      found = findIn(pkg, name)
      if found then from = pkg break end
    end
    if not found then
      log("pxrt: asset '%s' of %s not found in its packages: left to the host", name, tostring(unit.name))
      found = name
    elseif from ~= unit.pkg then
      log("pxrt: asset '%s' of %s taken from package %s", name, tostring(unit.name), from)
    end
    assetCache[key] = found
    return found
  end
  local function asset(file) return E.resolveAsset(R.str(file)) end

  function F.GetAttachment(name) return asset(name) end
  E.spriteFrames = {}
  local spriteMT = { __tostring = function(t) return "CSprite#" .. tostring(rawget(t, "Index")) end }
  function F.LoadSprite(file, frames, flags)
    file = asset(file)
    local id = 0
    if registerCustomSprite then
      local ok, v = pcall(registerCustomSprite, file, ti(frames))
      if ok and type(v) == "number" then id = v end
    end
    if id > 0 then E.spriteFrames[id] = ti(frames) end
    return setmetatable({ __cls = "CSprite", Index = id, File = file, Frames = ti(frames) }, spriteMT)
  end
  local function spriteId(s)
    if type(s) == "table" then return rawget(s, "Index") or 0 end
    return ti(s)
  end
  E.spriteId = spriteId
  -- LoadImage / MakeBitmap give bitmaps; per-pixel drawing is not supported: keep inert
  function F.LoadImage(file)
    return R.builtinClasses.CBitmap(R.str(file))
  end
  function F.MakeBitmap(w, h)
    return R.builtinClasses.CBitmap(nil, ti(w), ti(h))
  end
  local function overrideSrc(src, a, b)
    if type(src) == "table" then
      local id = rawget(src, "Index") or 0
      if id > 0 then return id end
      return rawget(src, "File"), rawget(src, "Frames"), a
    end
    if type(src) == "string" then return asset(src), a, b end
    return src, a, b
  end
  function F.SetSpriteOverride(target, src, a, b)
    if SetSpriteOverride then
      local s, x, y = overrideSrc(src, a, b)
      pc(SetSpriteOverride, ti(target), s, x, y)
    end
    return 0
  end
  function F.SetWeaponSpriteOverride(w, target, src, a, b)
    if SetWeaponSpriteOverride then
      local s, x, y = overrideSrc(src, a, b)
      pc(SetWeaponSpriteOverride, w, ti(target), s, x, y)
    end
    return 0
  end
  F.SetLayerOverride = function() return 0 end
  -- custom (script-to-script) message ids: unique, above the engine range
  E.nextPXMessage = E.nextPXMessage or 0x2000
  F.RegisterPXMessage = function()
    local m = E.nextPXMessage
    E.nextPXMessage = m + 1
    return m
  end
  -- PRegister/PUnregister: engine keeps the referenced object pointer valid; the runtime GC does that already
  F.PRegister = function() return 0 end
  F.PUnregister = function() return 0 end
  F.SetPitch = function() return 0 end

  ---------------------------------------------------------------------
  -- builtin classes
  ---------------------------------------------------------------------
  local BC = R.builtinClasses
  local function inert(cls)
    return function(...)
      return setmetatable({ __cls = cls }, R.scriptMTFor(cls))
    end
  end
  -- CSoundFile(file): registers the sound at construction; Play(volume, pan, loop)
  BC.CSoundFile = function(file)
    local o = setmetatable({ __cls = "CSoundFile" }, R.scriptMTFor("CSoundFile"))
    local id = 0
    if file and registerCustomSound then
      local ok, v = pcall(registerCustomSound, asset(file))
      if ok and type(v) == "number" then id = v end
    end
    rawset(o, "Index", id)
    rawset(o, "File", file)
    return o
  end
  R.natives.CSoundFile = {
    -- PX passes CalculateSoundPan() (about -0.1..0.1) as pan; it used to land in the host's pitch slot and played
    -- those sounds nearly silent. The host has no pan, so play at normal pitch.
    Play = function(self, super, vol, pan, loop)
      local id = rawget(self, "Index") or 0
      if id > 0 and playSoundLocal then pc(playSoundLocal, tf(vol), 1.0, E.soundSource(), id, 0) end
      return 0
    end,
    Stop = function() return 0 end,
    SetPitch = function() return 0 end,
    SetVolume = function() return 0 end,
  }
  E.soundSource = function() return nil end

  BC.CBitmap = function(file, w, h)
    local o = setmetatable({ __cls = "CBitmap" }, R.scriptMTFor("CBitmap"))
    rawset(o, "W", w or 0); rawset(o, "H", h or 0); rawset(o, "File", file)
    return o
  end
  R.natives.CBitmap = {
    Rect = function() return 0 end, HLine = function() return 0 end, VLine = function() return 0 end,
    SetPixel = function() return 0 end, GetPixel = function() return 0 end, Clear = function() return 0 end,
    DrawText = function() return 0 end, Draw = function() return 0 end, Copy = function() return 0 end,
    Compact = function() return 0 end, Update = function() return 0 end, Fill = function() return 0 end,
  }
  BC.CBitmap1 = BC.CBitmap
  R.natives.CBitmap1 = R.natives.CBitmap
  BC.CQuad = inert("CQuad")
  -- HUD text widget: drawn by nothing (no Lua text API for per-widget text); keeps scripts running
  BC.CGUIText = inert("CGUIText")
  R.natives.CGUIText = {
    SetText = function() return 0 end, Draw = function() return 0 end, Render = function() return 0 end,
    SetColor = function() return 0 end, SetPos = function() return 0 end, SetAlign = function() return 0 end,
    SetVisible = function() return 0 end, Show = function() return 0 end, Hide = function() return 0 end,
    SetFont = function() return 0 end, SetAlpha = function() return 0 end, SetScale = function() return 0 end,
  }
  BC.CFireDesc = inert("CFireDesc")
  -- CFilter(parent, type): message filter node. Children keep receiving everything (pseudo dispatch), so it is inert.
  BC.CFilter = inert("CFilter")
  R.natives.CFilter = {
    Allow = function() return 0 end, Forbid = function() return 0 end,
    AllowAll = function() return 0 end, ForbidAll = function() return 0 end,
  }
  -- PX utils::GetCurrentWorm(): called once per script override per message (hundreds of times per frame), so it is a
  -- direct native with the same result: nil unless 1<=CurWorm<=8 and 1<=CurTeam<=6, else the worm object at (CurWorm + 16*CurTeam)
  local CW = E.CW
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
  end
  -- utils_hack type-punning (PCMessageData_intP & co.): the pointer is an absolute WA address, view it in place
  BF.PCMessageData_intP = function(addr)
    local o = E.msgDataAt(ti(addr))
    return o or 0
  end
  R.natives.CQuad = {
    SetPoint = function() return 0 end, Set = function() return 0 end, Rect = function() return 0 end,
    SetColor = function() return 0 end, SetAlpha = function() return 0 end,
  }
  BC.CColMask = function(w, h)
    local o = setmetatable({ __cls = "CColMask" }, R.scriptMTFor("CColMask"))
    rawset(o, "W", ti(w or 0)); rawset(o, "H", ti(h or 0))
    return o
  end
  R.natives.CColMask = {
    SetPixel = function() return 0 end, GetPixel = function() return 0 end, Rect = function() return 0 end,
    HLine = function() return 0 end, VLine = function() return 0 end, Clear = function() return 0 end,
    Check = function() return 0 end,
  }
  BC.CMessageData = function()
    return setmetatable({ __cls = "CMessageData" }, R.scriptMTFor("CMessageData"))
  end
  R.natives.CMessageData = {
    GetParameter = function(self, super, i)
      local a = rawget(self, "__a")
      if a then return rd(a + 4 * ti(i)) end
      local p = rawget(self, "__p")
      return p and p[ti(i)] or 0
    end,
  }
  -- helpers for engine message plumbing
  function E.msgDataAt(addr)
    if not E.okAddr(addr) then return nil end
    return setmetatable({ __a = addr, __cls = "CMessageData" }, R.scriptMTFor("CMessageData"))
  end

  ---------------------------------------------------------------------
  -- R.call / R.mc: method dispatch used by transpiled chunks
  ---------------------------------------------------------------------
  local function missingMethod(o, name)
    local c = type(o) == "table" and rawget(o, "__cls") or type(o)
    once("mc:" .. tostring(c) .. ":" .. tostring(name), "pxrt: missing method %s::%s", tostring(c), tostring(name))
    return 0
  end
  local function mc(o, name, ...)
    local t = type(o)
    if t == "table" then
      local f = o[name]
      if type(f) == "function" then return f(o, ...) end
      local cls = rawget(o, "__cls")
      if cls and #R.buildChain(cls, name) > 0 then return R.methodClosure(cls, name)(o, ...) end
      return missingMethod(o, name)
    end
    if o == nil or o == 0 then
      once("mcnull:" .. tostring(name), "pxrt: method %s called on null", tostring(name))
      return 0
    end
    return missingMethod(o, name)
  end
  local function call(self, name, ...)
    if type(self) == "table" then
      local f = self[name]
      if type(f) == "function" then return f(self, ...) end
    end
    local bf = rawget(F, name)
    if bf then return bf(...) end
    local f = F[name]
    if f then return f(...) end
    return 0
  end
  R.mc, R.call = mc, call
  E.mc = mc
end
