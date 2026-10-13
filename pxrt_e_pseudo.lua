-- pxrt_e_pseudo: script-only objects (classes whose engine root is CObject / CGObject).
-- They live in a registry, receive the messages WA delivers to the turn game, and are
-- freed on delete.  CGObject-rooted ones also get soft physics (pxrt_e_soft).
return function(R, E)
  local ti, tf, once, log = R.ti, R.tf, R.once, R.log
  local N = R.natives
  local rawget, rawset, type, pcall, pairs, ipairs = rawget, rawset, type, pcall, pairs, ipairs
  local function nat(cls) N[cls] = N[cls] or {} return N[cls] end

  local roots = {}        -- top-level pseudo objects (parent not pseudo)
  local registry = {}     -- obj -> true
  local plist = {}        -- every live pseudo object in creation order (deterministic iteration)
  local count = 0
  local depth = 0
  E.pseudoRegistry = registry
  E.pseudoList = plist
  E.pseudoVersion = 0

  ---------------------------------------------------------------------
  -- CObjList (script-owned list) and the Childs view of pseudo objects
  ---------------------------------------------------------------------
  local function listView(getList)
    local objsArr = setmetatable({}, {
      __index = function(_, i)
        if type(i) ~= "number" then return nil end
        return getList()[ti(i) + 1]
      end,
      __newindex = function(_, i, v) getList()[ti(i) + 1] = v end,
    })
    local v = setmetatable({ __cls = "CObjList" }, {
      __index = function(t, k)
        if k == "Count" then return #getList() end
        if k == "Objs" then return objsArr end
        if k == "GetObject" then return function(_, i) return getList()[ti(i) + 1] end end
        if k == "Add" then return function(_, o) local l = getList(); l[#l + 1] = o; return #l end end
        if k == "Remove" then
          return function(_, o)
            local l = getList()
            for i = #l, 1, -1 do if l[i] == o then table.remove(l, i) end end
            return 0
          end
        end
        if k == "Compact" then
          return function()
            local l = getList()
            for i = #l, 1, -1 do local o = l[i]; if o == nil or o == 0 then table.remove(l, i) end end
            return 0
          end
        end
        if k == "Clear" then return function() local l = getList(); for i = #l, 1, -1 do l[i] = nil end return 0 end end
        return 0
      end,
    })
    return v
  end
  R.builtinClasses.CObjList = function()
    local list = {}
    return listView(function() return list end)
  end
  local noKids = {}
  function R.childsOf(obj)
    local v = rawget(obj, "__childsView")
    if not v then
      v = listView(function() return rawget(obj, "__kids") or noKids end)
      rawset(obj, "__childsView", v)
    end
    return v
  end

  -- engine root class name of a script class
  local function engineRoot(clsName)
    local c = R.getClass(clsName)
    local guard = 0
    while c and not c.engine and guard < 32 do
      c = c.base and R.getClass(c.base) or nil
      guard = guard + 1
    end
    return c and c.name or nil
  end
  E.engineRoot = engineRoot

  -- engine roots that script subclasses live on without a WA task behind them (soft objects, see pxrt_e_soft)
  local SOFT_ROOTS = {
    CGObject = true, CMine = true, COilDrum = true, CCrate = true, CGas = true, CFire = true, CArrow = true,
    CCanister = true, CCross = true, CMissile = true, CFlame = true, CSmoke = true, CCloud = true,
  }
  E.softRoots = SOFT_ROOTS
  local function isPseudoRoot(name) return name == "CObject" or SOFT_ROOTS[name] == true end

  local function addTo(list, o)
    list[#list + 1] = o
  end
  local function removeFrom(list, o)
    for i = #list, 1, -1 do
      if list[i] == o then table.remove(list, i) return end
    end
  end

  function E.hasPseudo() return count > 0 end
  function E.resetPseudo()
    roots = {}
    registry = {}
    plist = {}
    E.pseudoRegistry = registry
    E.pseudoList = plist
    E.pseudoVersion = E.pseudoVersion + 1
    count = 0
  end

  local function register(obj, clsName)
    if registry[obj] then return end
    registry[obj] = true
    plist[#plist + 1] = obj
    E.pseudoVersion = E.pseudoVersion + 1
    count = count + 1
    local parent = rawget(obj, "Parent")
    if type(parent) == "table" and registry[parent] then
      local k = rawget(parent, "__kids")
      if not k then k = {}; rawset(parent, "__kids", k) end
      addTo(k, obj)
    else
      addTo(roots, obj)
    end
  end

  -- engine ctor for script subclasses of the roots above: runs when the script ctor calls super(...), i.e. before
  -- the rest of the script ctor, so script assignments win over the soft defaults.  Registers the object at once
  -- (children created inside the ctor can link to it).
  local function pseudoCtor(root)
    return function(obj, parent, ...)
      -- engine-object proxies (CWorm::CWorm script ctor chain) already live in WA: nothing to create
      if rawget(obj, "__a") then return 0 end
      rawset(obj, "Parent", type(parent) == "table" and parent or nil)
      register(obj, rawget(obj, "__cls"))
      if root ~= "CObject" and E.softCtor then
        local ok, err = pcall(E.softCtor, obj, root, parent, ...)
        if not ok then log("pxrt: softCtor %s failed: %s", tostring(root), tostring(err)) end
      end
      return 0
    end
  end
  R.engineCtor.CObject = pseudoCtor("CObject")
  for name in pairs(SOFT_ROOTS) do R.engineCtor[name] = pseudoCtor(name) end

  local prevNew = R.onNewObject
  R.onNewObject = function(obj, clsName)
    if prevNew then prevNew(obj, clsName) end
    local root = engineRoot(clsName)
    if root and isPseudoRoot(root) and not rawget(obj, "__a") then
      register(obj, clsName)
    end
  end

  local function unregister(obj)
    if not registry[obj] then return end
    registry[obj] = nil
    removeFrom(plist, obj)
    E.pseudoVersion = E.pseudoVersion + 1
    count = count - 1
    local parent = rawget(obj, "Parent")
    local k = type(parent) == "table" and rawget(parent, "__kids")
    if k then removeFrom(k, obj) end
    removeFrom(roots, obj)
    -- children are freed with their parent
    local mine = rawget(obj, "__kids")
    if mine then
      for i = #mine, 1, -1 do
        local c = mine[i]
        if c then R.delete(c) end
      end
    end
  end
  function E.freePseudo(obj) unregister(obj) end

  R.onDelete = function(o)
    if type(o) ~= "table" then return end
    if rawget(o, "__a") then
      local f = o.Free
      if type(f) == "function" then pcall(f, o, 1) end
      return
    end
    local cls = rawget(o, "__cls")
    if cls then
      local ok, err = pcall(R.invoke, o, cls, "Free", 1)
      if not ok then log("pxrt: Free chain failed for %s: %s", tostring(cls), tostring(err)) end
    end
    unregister(o)
  end

  local function sendTo(o, sender, mtype, size, mdata)
    local cls = rawget(o, "__cls")
    if not cls then return end
    -- soft objects: the native physics step runs once per M_FRAME, at the script's `super` call if it makes one,
    -- else right after the script handler (PX scripts such as the helicopter never call super yet still get physics)
    local soft = mtype == 2 and rawget(o, "__soft") and E.softStep
    if soft then rawset(o, "__stepped", false) end
    local ok, err = pcall(R.invoke, o, cls, "Message", sender, mtype, size, mdata)
    if not ok then once("pmsg:" .. cls .. ":" .. tostring(mtype), "pxrt: %s::Message(%s) failed: %s", cls, tostring(mtype), tostring(err)) end
    if soft and registry[o] and not rawget(o, "__stepped") then E.softStepSafe(o) end
  end

  function E.forwardToKids(self, sender, mtype, size, mdata)
    local k = rawget(self, "__kids")
    if not k then return end
    if depth > 8 then return end
    depth = depth + 1
    local copy = {}
    for i = 1, #k do copy[i] = k[i] end
    for i = 1, #copy do
      local c = copy[i]
      if registry[c] then sendTo(c, sender, mtype, size, mdata) end
    end
    depth = depth - 1
  end

  -- engine message delivered to the turn game -> every top-level pseudo object
  function E.dispatchPseudo(sender, mtype, size, mdata)
    if depth > 8 then return end
    depth = depth + 1
    local copy = {}
    for i = 1, #roots do copy[i] = roots[i] end
    for i = 1, #copy do
      local o = copy[i]
      if registry[o] then sendTo(o, sender, mtype, size, mdata) end
    end
    depth = depth - 1
  end

  -- list of live pseudo objects of a class (for scripts that enumerate objects)
  function E.pseudoOfClass(name)
    local out = {}
    for _, o in ipairs(plist) do
      if R.isa(rawget(o, "__cls"), name) then out[#out + 1] = o end
    end
    return out
  end
end
