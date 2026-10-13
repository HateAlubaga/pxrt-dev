-- pxrt_e_quads: ProjectX quad rendering (CQuad, FillSpriteQuad, TransformQuad, RenderQuad, AddSpriteQ,
-- AddCustomRender) and rotated / scaled AddSpriteEx, on top of the DLL's quad renderer (QuadRender.cpp):
--   pxQuadSubmit(layer, data, n)  data = flat array, 24 numbers per quad:
--                                 sprite, frame, blend, flags, then 4 x (x, y, tx, ty, ARGB colour), world pixels
--   pxSpriteCell(id) -> w, h      sprite cell size
--   pxQuadStats()                 batches, quads, rejected, faults, draw ms since the last call
-- Each submit becomes one item of WA's draw queue at that layer. A custom render function (AddCustomRender) is run
-- right away (M_DRAWQUEUE is inside WA's queue window) and every RenderQuad it makes goes into one batch.
return function(R, E)
  local ti, tf = R.ti, R.tf
  local log, once = R.log, R.once
  local N, BC, F = R.natives, R.builtinClasses, R.F
  local rawget, rawset, setmetatable, type, pcall, tostring = rawget, rawset, setmetatable, type, pcall, tostring
  local cos, sin = math.cos, math.sin
  local submit, cellOf, stats = pxQuadSubmit, pxSpriteCell, pxQuadStats
  if type(submit) ~= "function" or type(cellOf) ~= "function" then
    log("pxrt: the DLL has no quad renderer (pxQuadSubmit): RenderQuad / AddSpriteQ / AddCustomRender stay inert")
    return
  end
  local isref, spriteId = R.isref, E.spriteId
  local CO = N.CObject or {}
  N.CObject = CO

  ---------------------------------------------------------------------
  -- CQuad { v[4] = {x, y, z, tx, ty, color}, tex, blend }
  ---------------------------------------------------------------------
  -- q.v.color (array used as a pointer in PX) is v[0].color
  local vMT = {
    __index = function(t, k) if type(k) == "string" then return rawget(t, 0)[k] end end,
    __newindex = function(t, k, x)
      if type(k) == "string" then rawget(t, 0)[k] = x else rawset(t, k, x) end
    end,
  }
  local function newVerts()
    local v = {}
    for i = 0, 3 do v[i] = { x = 0, y = 0, z = 0, tx = 0, ty = 0, color = 0 } end
    return setmetatable(v, vMT)
  end
  BC.CQuad = function()
    local q = setmetatable({ __cls = "CQuad" }, R.scriptMTFor("CQuad"))
    rawset(q, "v", newVerts()); rawset(q, "tex", 0); rawset(q, "blend", 0)
    return q
  end
  local function quadOf(q)
    if isref(q) then q = q.v end
    if type(q) ~= "table" then return nil end
    local v = rawget(q, "v")
    if type(v) ~= "table" then
      v = newVerts()
      rawset(q, "v", v)
    end
    return q, v
  end

  local function cellSize(id)
    if id <= 0 then return 0, 0 end
    local ok, w, h = pcall(cellOf, id)
    if not ok then return 0, 0 end
    return w or 0, h or 0
  end

  F.FillSpriteQuad = function(q, sprite, frame, flags)
    local v
    q, v = quadOf(q)
    if not q then return 0 end
    local id = spriteId(sprite)
    local w, h = cellSize(id)
    local hw, hh = w / 2, h / 2
    local p = v[0]; p.x, p.y, p.tx, p.ty, p.color = -hw, -hh, 0, 0, 0xFFFFFFFF
    p = v[1]; p.x, p.y, p.tx, p.ty, p.color = hw, -hh, 1, 0, 0xFFFFFFFF
    p = v[2]; p.x, p.y, p.tx, p.ty, p.color = hw, hh, 1, 1, 0xFFFFFFFF
    p = v[3]; p.x, p.y, p.tx, p.ty, p.color = -hw, hh, 0, 1, 0xFFFFFFFF
    -- sprite id bit 0x40000 (Index + 262144) = mirrored horizontally, as in WA's sprite draw
    if math.type(id) == "integer" and id & 0x40000 ~= 0 then
      v[0].tx, v[1].tx, v[2].tx, v[3].tx = 1, 0, 0, 1
    end
    rawset(q, "tex", id)
    rawset(q, "__frame", tf(frame or 0))
    return 0
  end

  -- scale by (sx, sy), rotate by rot radians, move to (x, y)
  F.TransformQuad = function(q, rot, sx, sy, x, y)
    local v
    q, v = quadOf(q)
    if not q then return 0 end
    rot, sx, sy, x, y = tf(rot or 0), tf(sx or 1), tf(sy or 1), tf(x or 0), tf(y or 0)
    local c, s = cos(rot), sin(rot)
    for i = 0, 3 do
      local p = v[i]
      local px, py = tf(p.x or 0) * sx, tf(p.y or 0) * sy
      p.x = px * c - py * s + x
      p.y = px * s + py * c + y
    end
    return 0
  end

  ---------------------------------------------------------------------
  -- batching
  ---------------------------------------------------------------------
  local function put(b, n, q, v, sprite, frame)
    local o = n * 24
    b[o + 1] = sprite; b[o + 2] = frame; b[o + 3] = rawget(q, "blend") or 0; b[o + 4] = 0
    for i = 0, 3 do
      local p = v[i]
      local k = o + 5 + i * 5
      b[k] = p.x; b[k + 1] = p.y; b[k + 2] = p.tx; b[k + 3] = p.ty; b[k + 4] = p.color
    end
    return n + 1
  end
  local function send(layer, b, n)
    if n <= 0 then return end
    local ok, err = pcall(submit, layer, b, n)
    if not ok then once("qsub:" .. tostring(err), "pxrt: pxQuadSubmit failed: %s", tostring(err)) end
  end

  local cbuf, cn, collecting = {}, 0, false   -- the AddCustomRender batch being collected
  local sbuf = {}                             -- one-shot batches (AddSpriteQ, rotated sprites)

  F.RenderQuad = function(q, flags)
    local v
    q, v = quadOf(q)
    if not q then return 0 end
    local tex = spriteId(rawget(q, "tex") or 0)
    if collecting then
      cn = put(cbuf, cn, q, v, tex, rawget(q, "__frame") or 0)
    else
      once("rq-outside", "pxrt: RenderQuad outside a custom render function: drawn at layer 6")
      send(6, sbuf, put(sbuf, 0, q, v, tex, rawget(q, "__frame") or 0))
    end
    return 0
  end

  CO.AddSpriteQ = function(self, super, z, q, sprite, frame, flags)
    local v
    q, v = quadOf(q)
    if not q then return 0 end
    local id = spriteId(sprite)
    if id == 0 then id = spriteId(rawget(q, "tex") or 0) end
    send(tf(z), sbuf, put(sbuf, 0, q, v, id, tf(frame or 0)))
    return 0
  end

  -- custom render functions are looked up by name in the calling unit (several packages define the same name)
  local fnCache = setmetatable({}, { __mode = "k" })
  local function findRender(name)
    local u = R.unitAt()
    if not u then return nil end
    local c = fnCache[u]
    if not c then c = {}; fnCache[u] = c end
    local fn = c[name]
    if fn == nil then
      fn = u.G[name]
      if fn == nil then fn = false end
      c[name] = fn
    end
    return fn or nil
  end
  CO.AddCustomRender = function(self, super, z, name)
    name = R.str(name)
    local fn = findRender(name)
    if not fn then
      once("acr:" .. name, "pxrt: AddCustomRender: render function %s not found", name)
      return 0
    end
    if collecting then   -- nested: its quads join the outer batch
      local ok, err = pcall(fn)
      if not ok then once("acr-err:" .. name, "pxrt: custom render %s failed: %s", name, tostring(err)) end
      return 0
    end
    collecting, cn = true, 0
    local ok, err = pcall(fn)
    collecting = false
    if not ok then once("acr-err:" .. name, "pxrt: custom render %s failed: %s", name, tostring(err)) end
    send(tf(z), cbuf, cn)
    cn = 0
    return 0
  end

  ---------------------------------------------------------------------
  -- AddSpriteEx with rotation (radians) / scale: one textured quad
  ---------------------------------------------------------------------
  local rq = BC.CQuad()
  local rv = rawget(rq, "v")
  function E.drawSpriteRot(z, x, y, id, frame, rot, scale)
    if scale == 0 then scale = 1 end
    F.FillSpriteQuad(rq, id, frame, 0)
    F.TransformQuad(rq, rot, scale, scale, x, y)
    rawset(rq, "blend", 0)
    send(z, sbuf, put(sbuf, 0, rq, rv, id, frame))
    return 0
  end

  function E.quadStats()
    if type(stats) ~= "function" then return nil end
    local ok, b, q, rej, faults, ms = pcall(stats)
    if not ok then return nil end
    return b, q, rej, faults, ms
  end
  log("pxrt: quad renderer ready (RenderQuad, AddSpriteQ, AddCustomRender, rotated sprites)")
end
