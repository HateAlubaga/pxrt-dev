-- pxrt_e_hooks: feeds WA events into the script object model.
--  * per-class task message hook (vtable slot 8): script `override X::Message` chains, original = terminal native
--  * FireWeapon hook: script `override CWorm::FireFinal` chain, original FireWeapon = terminal native
--  * match lifecycle (gameGlobalInit, per-frame tick), pseudo (script-only) objects
return function(R, E)
  local rd, wr, rdU = E.rd, E.wr, E.rdU
  local ti, tf, once, log = R.ti, R.tf, R.once, R.log
  local N = R.natives
  local K = R.K
  local type, rawget, rawset, pairs, ipairs, pcall, setmetatable = type, rawget, rawset, pairs, ipairs, pcall, setmetatable
  local function nat(cls) N[cls] = N[cls] or {} return N[cls] end

  E.pins = {}          -- addr -> { o = proxy, cid = class id } (strong refs: script fields survive GC)
  E.scriptObjs = {}    -- addr -> script-class object that wraps an engine object
  E.tick = 0
  local pins = E.pins

  local FRAME = (K and K.M_FRAME) or 2

  ---------------------------------------------------------------------
  -- engine object <-> script proxy
  ---------------------------------------------------------------------
  function E.objectFor(addr, cls)
    local so = E.scriptObjs[addr]
    if so then return so end
    local p = pins[addr]
    if p then return p.o end
    local o = E.proxyAt(addr, cls)
    if o and not pins[addr] then pins[addr] = { o = o, cid = rd(addr + 0x20), vt = rdU(addr) } end
    return o
  end
  function E.pinObject(o)
    local a = type(o) == "table" and rawget(o, "__a")
    if a and not pins[a] then pins[a] = { o = o, cid = rd(a + 0x20), vt = rdU(a), keep = true } end
  end

  -- first sight of a worm: pin it and run the script constructor chain (CWorm::CWorm overrides)
  function E.onNewWorm(p, a)
    pins[a] = { o = p, cid = rd(a + 0x20), vt = rdU(a), keep = true }
    local ch = R.getClass("CWorm")
    if #ch.ctorOv == 0 and not ch.ctor then return end
    local team, idx = rd(a + 0xFC), rd(a + 0x100)
    local ok, err = pcall(R.runCtor, "CWorm", p, nil, team, idx, nil)
    if not ok then log("pxrt: CWorm ctor chain failed: %s", tostring(err)) end
  end

  ---------------------------------------------------------------------
  -- engine object lifetime
  ---------------------------------------------------------------------
  -- PX runs the script constructor chain (`override CMissile::CMissile(...)`, CMine, CCrate, COilDrum, CArrow,
  -- CFire...) for every object the engine constructs. Here an engine object is constructed when Lua first sees its
  -- address (E.proxyAt miss); objects WA creates inside FireWeapon are constructed right after it returns, while the
  -- FireFinal chain still runs (utils: `weap = u_lweap`). WA reuses a freed task's memory for the next task, so the
  -- host logs every CTask construction (taskBirthSeq/taskBirthsSince): a birth at an address ends the object that
  -- lived there before, together with its pin, proxy and script fields.
  local hostBirths = type(taskBirthSeq) == "function" and type(taskBirthsSince) == "function"
  local birthSeq = hostBirths and taskBirthSeq() or 0
  local life = { births = 0, ctors = 0 }
  E.lifeStats = life
  E.lifeVer = 0   -- bumped whenever an address loses its object (cache key of Env.Objs)

  local function retire(a)
    if pins[a] or E.proxies[a] or E.scriptObjs[a] then
      pins[a] = nil
      E.scriptObjs[a] = nil
      E.proxies[a] = nil
      E.lifeVer = E.lifeVer + 1
    end
  end
  E.retire = retire

  -- read the host's birth log: every address born since the last call loses its previous object
  function E.syncBirths()
    if not hostBirths then return end
    local now = taskBirthSeq()
    if now == birthSeq then return end
    local list, n, lost = taskBirthsSince(birthSeq)
    birthSeq = n
    if lost then once("birthlost", "pxrt: task birth log overflowed: reused addresses may keep stale script state") end
    life.births = life.births + #list
    for i = 1, #list do retire(list[i]) end
  end

  -- script constructor arguments, rebuilt from the constructed object (PX signatures)
  local zeroMT = { __index = function() return 0 end, __newindex = function() end }
  local function zeroStruct() return setmetatable({}, zeroMT) end
  local function parentOf(a) return E.proxyAt(rdU(a + 0x04)) end
  local function shootDesc()
    local sd = E.fireSd or (E.curFire and E.curFire.sd)
    if sd and sd ~= 0 then return E.sdAt(sd) end
    return R.builtinClasses.CShootDesc()
  end
  local floor = math.floor
  local CTOR_ARGS = {
    CMissile = function(a) return parentOf(a), E.launchAt(a + 0x2C8), shootDesc() end,
    CMine = function(a) return parentOf(a), zeroStruct(), shootDesc(), 0, 0 end,
    CCrate = function(a) return parentOf(a), zeroStruct(), 0 end,
    COilDrum = function(a) return parentOf(a), floor(rd(a + 0x84) / 65536), floor(rd(a + 0x88) / 65536), 0 end,
    CArrow = function(a) return parentOf(a), 0, shootDesc() end,
    CFire = function(a) return parentOf(a), zeroStruct(), 0 end,
  }
  local CTOR_CLASSES = { CMissile = true, CMine = true, CCrate = true, COilDrum = true, CArrow = true, CFire = true,
    CCanister = true, CCross = true, CGas = true, CAirStrike = true, CCloud = true, CSmoke = true }

  local function runEngineCtor(p, a, cls)
    if #R.getClass(cls).ctorOv == 0 then return end
    pins[a] = { o = p, cid = rd(a + 0x20), vt = rdU(a) }
    life.ctors = life.ctors + 1
    local argf = CTOR_ARGS[cls]
    local ok, err
    if argf then
      ok, err = pcall(function() return R.runCtor(cls, p, argf(a)) end)
    else
      ok, err = pcall(R.runCtor, cls, p, parentOf(a))
    end
    if not ok then once("ctor:" .. cls, "pxrt: %s ctor chain failed: %s", cls, tostring(err)) end
  end

  -- first sight of an engine object (E.proxyAt created its proxy)
  function E.onFirstSight(p, a, cls)
    if cls == "CWorm" then return E.onNewWorm(p, a) end
    if CTOR_CLASSES[cls] then runEngineCtor(p, a, cls) end
  end

  -- objects WA created inside FireWeapon: construct them now, while the FireFinal chain still runs
  local function constructAt(a)
    if pins[a] or not E.okAddr(a) then return end
    local cls = E.CLASS_BY_ID[rd(a + 0x20)]
    if cls and (CTOR_CLASSES[cls] or cls == "CWorm") then E.proxyAt(a, cls) end
  end
  -- addresses in the env object list (no host birth log: fired objects are found by comparing two snapshots)
  local function envAddrs()
    local set = {}
    local env = E.envAddr and E.envAddr() or 0
    if env == 0 then return set end
    local n, data = rd(env + 0x18 + 8), rdU(env + 0x18 + 0xC)
    if n <= 0 or n > 65536 or not E.okAddr(data) then return set end
    for i = 0, n - 1 do
      local a = rdU(data + 4 * i)
      if a ~= 0 then set[a] = true end
    end
    return set
  end
  local function fireMark()
    if hostBirths then return taskBirthSeq(), nil end
    return nil, envAddrs()
  end
  local function constructFired(mark, before)
    if mark then
      E.syncBirths()
      local list = taskBirthsSince(mark)
      for i = 1, #list do constructAt(list[i]) end
    elseif before then
      for a in pairs(envAddrs()) do
        if not before[a] then retire(a); constructAt(a) end
      end
    end
  end

  ---------------------------------------------------------------------
  -- message hook: terminal native + ctx stack
  ---------------------------------------------------------------------
  local ctxStack = {}
  local directSend = nil   -- {addr=, mtype=} : engine-bound send initiated by script, skip the script chain once

  local CT = {
    CWorm = "CTaskWorm", CMissile = "CTaskMissile", CMine = "CTaskMine", CCrate = "CTaskCrate",
    COilDrum = "CTaskOildrum", CArrow = "CTaskArrow", CCanister = "CTaskCanister", CCross = "CTaskCross",
    COldWorm = "CTaskOldWorm", CTurnGame = "CTaskTurnGame", CTeam = "CTaskTeam", CFire = "CTaskFire",
    CFlame = "CTaskFlame", CAirStrike = "CTaskAirStrike", CCloud = "CTaskCloud", CFilter = "CTaskFilter",
    CLand = "CTaskLand",
  }
  E.CT = CT
  local callOrig = {}   -- class -> CTaskX_CallOriginal_vtable8

  local function senderUD(top, sender)
    if sender == nil or sender == 0 then return nil end
    if type(sender) == "table" and rawget(sender, "__a") == top.senderAddr then return top.sender end
    return nil
  end

  -- message ids from 0x2000 up are script-only (RegisterPXMessage ids, M_PXMESSAGE and the other custom M_ ids):
  -- WA never produced them and its handlers must never see them
  local SCRIPT_MSG_MIN = 0x2000

  -- terminal of every Message chain: run the original WA handler
  nat("CObject").Message = function(self, super, sender, mtype, size, mdata)
    local a = type(self) == "table" and rawget(self, "__a")
    mtype, size = ti(mtype), ti(size)
    if not a then
      -- pseudo object: forward to pseudo children
      if E.forwardToKids then E.forwardToKids(self, sender, mtype, size, mdata) end
      return 0
    end
    if mtype >= SCRIPT_MSG_MIN then return 0 end
    local top = ctxStack[#ctxStack]
    if top and top.addr == a then
      top.called = true
      local f = callOrig[top.cls]
      if f then
        E.CW.have = false
        local ok, r = pcall(f, top.This, senderUD(top, sender), mtype, size, E.msgAddr(mdata))
        E.CW.have = false
        if not ok then once("origmsg:" .. top.cls, "pxrt: CallOriginal %s failed: %s", top.cls, tostring(r)) return 0 end
        return r
      end
      return 0
    end
    -- script-initiated send to an engine object: engine handler only (script chain already ran in mc())
    directSend = { addr = a, mtype = mtype }
    local ok, r = pcall(E.sendMessage, a, sender, mtype, size, mdata)
    directSend = nil
    if not ok then once("sendmsg", "pxrt: sendMessage failed: %s", tostring(r)) return 0 end
    return r
  end

  local typedChain, invokeTyped, typedWantsAny = R.typedChain, R.invokeTyped, R.typedWantsAny
  local function classWants(cls)
    local gen = R.gen
    local e = E.wantCache[cls]
    if e and e.gen == gen then return e.v end
    local v = R.hasScriptChain(cls, "Message")
    E.wantCache[cls] = { gen = gen, v = v }
    return v
  end
  E.wantCache = {}

  -- cheap always-on accounting of time spent in the Lua message hooks. One line per ~PERF_FRAMES match frames in
  -- pxrt.log, at most PERF_LINES lines per session:
  --   period  = wall time between two turn-game M_FRAMEs (the whole game frame: WA logic, render, other hooks)
  --   hooks   = time inside the outermost hooks (includes WA's own handlers called from them)
  --   lua     = hooks minus the WA handlers called through CallOriginal (= time of pxrt + scripts)
  --   per class: lua time and message count, nested dispatches included
  local clock = os.clock
  local PERF_FRAMES, PERF_LINES = 500, 30
  local perfFrames, perfLines, perfHooks, perfPeriod, lastFrameT = 0, 0, 0, 0, nil
  local perfWindow = 150   -- first window is short, so a short match still logs one line
  -- engine function hooks (RenderWorm, SetAnimEx): calls and time spent in their Lua callbacks
  local fnN, fnT, fnFast = { render = 0, anim = 0 }, { render = 0, anim = 0 }, 0
  local perfLua, perfN, perfType = {}, {}, {}
  local natAcc = {}     -- natAcc[depth]: WA handler time called from the hook at that nesting depth
  local perfBirths, perfCtors = 0, 0
  local function perfOrig(orig)
    return function(...)
      local t = clock()
      local r = orig(...)
      local d = E.tgHold
      natAcc[d] = (natAcc[d] or 0) + (clock() - t)
      return r
    end
  end
  local function perfReport()
    if perfLines < PERF_LINES then
      perfLines = perfLines + 1
      local lua, parts, types = 0, {}, {}
      for c, t in pairs(perfLua) do
        lua = lua + t
        parts[#parts + 1] = string.format("%s %.2f/%d", c:gsub("^C", ""), 1000 * t / perfFrames, perfN[c] // perfFrames)
      end
      table.sort(parts)
      for m, t in pairs(perfType) do types[#types + 1] = { m, t } end
      table.sort(types, function(x, y) return x[2] > y[2] end)
      local tp = {}
      for i = 1, math.min(5, #types) do tp[i] = string.format("%d:%.2f", types[i][1], 1000 * types[i][2] / perfFrames) end
      local qs = ""
      if E.quadStats then
        local b, q, rej, faults, ms = E.quadStats()
        if b then
          qs = string.format("; quads %d/frame in %d batches, draw %.2f ms/frame, rejected %d, faults %d",
            q // perfFrames, b // perfFrames, ms / perfFrames, rej, faults)
        end
      end
      local fs = string.format("; fn hooks: RenderWorm %d/frame %.2f ms, SetAnimEx %d/frame %.2f ms (%d/frame skipped the chain)",
        fnN.render // perfFrames, 1000 * fnT.render / perfFrames, fnN.anim // perfFrames, 1000 * fnT.anim / perfFrames,
        fnFast // perfFrames)
      log("pxrt perf: %d frames, period %.2f ms, hooks %.2f ms, lua %.2f ms/frame (lua ms/msgs per class: %s; lua ms by msg type: %s); births %d, ctors %d%s%s",
        perfFrames, 1000 * perfPeriod / perfFrames, 1000 * perfHooks / perfFrames, 1000 * lua / perfFrames,
        table.concat(parts, ", "), table.concat(tp, " "), life.births - perfBirths, life.ctors - perfCtors, qs, fs)
    end
    perfFrames, perfHooks, perfPeriod = 0, 0, 0
    perfWindow = PERF_FRAMES
    fnN.render, fnN.anim, fnT.render, fnT.anim, fnFast = 0, 0, 0, 0, 0
    perfLua, perfN, perfType = {}, {}, {}
    perfBirths, perfCtors = life.births, life.ctors
  end
  -- d = nesting depth of this dispatch (1 = outermost), dt = its duration
  local function perfAdd(cls, mtype, d, dt)
    local lua = dt - (natAcc[d] or 0)
    natAcc[d] = 0
    perfLua[cls] = (perfLua[cls] or 0) + lua
    perfN[cls] = (perfN[cls] or 0) + 1
    perfType[mtype] = (perfType[mtype] or 0) + lua
    if d ~= 1 then return end
    perfHooks = perfHooks + dt
  end
  -- sampling profile of the Lua side over perf windows 2 and 5 (one count hook every PROF_STEP VM instructions):
  -- logs the functions and source files that run most, so in-game hot spots show up in pxrt.log
  local PROF_STEP, PROF_WINDOWS = 10000, { [1] = true, [4] = true }
  local profFn, profFile, profScript, profN, profOn = {}, {}, {}, 0, false
  local getinfo, sethook = debug and debug.getinfo, debug and debug.sethook
  local function shortSrc(s) return (s:gsub("^.*[/\\]", "")) end
  local function profSample()
    local i = getinfo(2, "S")
    if not i then return end
    local src = shortSrc(i.short_src)
    local k = src .. ":" .. i.linedefined
    profFn[k] = (profFn[k] or 0) + 1
    profFile[src] = (profFile[src] or 0) + 1
    profN = profN + 1
    -- the innermost package / lib function on the stack (runtime helpers charged to their script caller)
    for lv = 2, 40 do
      local j = getinfo(lv, "S")
      if not j then break end
      local s = j.short_src
      if j.what == "Lua" and not s:find("pxrt", 1, true) and not s:find("mock_dll", 1, true) then
        local sk = shortSrc(s) .. ":" .. j.linedefined
        profScript[sk] = (profScript[sk] or 0) + 1
        break
      end
    end
  end
  local function profTop(t, n)
    local a = {}
    for k, c in pairs(t) do a[#a + 1] = { k, c } end
    table.sort(a, function(x, y) return x[2] > y[2] end)
    local s = {}
    for i = 1, math.min(n, #a) do s[i] = string.format("%s %.1f%%", a[i][1], 100 * a[i][2] / profN) end
    return table.concat(s, ", ")
  end
  local function profStop()
    if not profOn then return end
    profOn = false
    sethook()
    if profN > 0 then
      log("pxrt profile: %d samples (1 per %d VM instructions = %.0f instr/frame); files: %s", profN, PROF_STEP,
        profN * PROF_STEP / PERF_FRAMES, profTop(profFile, 12))
      log("pxrt profile: functions: %s", profTop(profFn, 30))
      log("pxrt profile: script functions (incl. runtime calls they make): %s", profTop(profScript, 30))
    end
    profFn, profFile, profScript, profN = {}, {}, {}, 0
  end
  local function perfFrame()
    local t = clock()
    if lastFrameT then perfPeriod = perfPeriod + (t - lastFrameT) end
    lastFrameT = t
    perfFrames = perfFrames + 1
    if perfFrames >= perfWindow then
      profStop()
      perfReport()
      if sethook and getinfo and PROF_WINDOWS[perfLines] then
        profOn = true
        sethook(profSample, "", PROF_STEP)
      end
    end
  end

  ---------------------------------------------------------------------
  -- GG.queue2: M_PXMESSAGE commands
  ---------------------------------------------------------------------
  -- PX scripts post commands to WA's outgoing command queue (CKeySync: keys, CCamSync: camera and mouse); WA hands
  -- each queued command back to the turn game as M_PXMESSAGE on a later game frame (on every client of a network
  -- game). Here the queue is local: it is flushed into the turn game's Message chain at the start of the next
  -- M_FRAME, params[0..2] = (type, p1, p2).
  local PXMSG = (K and K.M_PXMESSAGE) or 0x7102
  local PXQ_MAX = 4096
  local pxQueue, pxQueueN = {}, 0
  local function addPX(self, mtype, p1, p2)
    if pxQueueN >= PXQ_MAX then
      once("pxqfull", "pxrt: M_PXMESSAGE queue full (no game frames?): commands dropped")
      return 0
    end
    pxQueueN = pxQueueN + 1
    pxQueue[pxQueueN] = { ti(mtype), ti(p1), ti(p2) }
    return 0
  end
  E.queue2 = setmetatable({ __cls = "CMessageQueue" }, {
    __index = function(t, k)
      if k == "AddPXMessage" then return addPX end
      return 0
    end,
  })
  local pxData
  local function flushPX(tgAddr)
    local q, n = pxQueue, pxQueueN
    pxQueue, pxQueueN = {}, 0
    local obj = E.objectFor(tgAddr, "CTurnGame")
    if not obj then return end
    if not pxData then pxData = R.builtinClasses.CMessageData() end
    local params = pxData.params
    local ccls = rawget(obj, "__cls") or "CTurnGame"
    local pseudo = E.hasPseudo and E.hasPseudo()
    for i = 1, n do
      local m = q[i]
      params[0], params[1], params[2] = m[1], m[2], m[3]
      local ok, err = pcall(R.invokeTyped, obj, ccls, "Message", PXMSG, nil, PXMSG, 12, pxData)
      if not ok then once("pxmsg", "pxrt: M_PXMESSAGE dispatch failed: %s", tostring(err)) end
      if pseudo then
        local ok2, err2 = pcall(E.dispatchPseudo, nil, PXMSG, 12, pxData)
        if not ok2 then once("pxmsgp", "pxrt: M_PXMESSAGE pseudo dispatch failed: %s", tostring(err2)) end
      end
    end
  end

  -- vtable8 callbacks of other (non-pxrt) packages registered after pxrt hooked the class. The host runs callbacks
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

  -- CTurnGame::SetCurrentTeam: WA switches teams internally, so script overrides (utils, wosc_lib and ~25 packages
  -- reset per-turn state there) never ran. The turn game's CurTeam (0x12C) is watched each M_FRAME instead and the
  -- chain runs once per change, after WA already switched (the native base is a no-op super).
  local lastTeam = 0
  local function checkTeamSwitch(tg)
    local team = rd(tg + 0x12C)
    if team == lastTeam then return end
    lastTeam = team
    if team <= 0 or not R.hasScriptChain("CTurnGame", "SetCurrentTeam") then return end
    local o = E.objectFor(tg, "CTurnGame")
    if not o then return end
    local ok, err = pcall(R.invoke, o, rawget(o, "__cls") or "CTurnGame", "SetCurrentTeam", team)
    if not ok then once("setcurteam", "pxrt: SetCurrentTeam chain failed: %s", tostring(err)) end
  end

  local function makeVt8(cls)
    local isTG = cls == "CTurnGame"
    local inner
    -- the CTurnGame address is cached for exactly one dispatch (see E.turnGameAddr)
    local function hook(This, sender, mtype, size, data)
      local fret = 0
      local fl = foreignVt8[cls]
      if fl then fret = runForeign(fl, cls, This, sender, mtype, size, data) end
      local h0 = E.tgHold
      E.tgHold = h0 + 1
      if isTG and mtype == FRAME and h0 == 0 then perfFrame() end
      natAcc[h0 + 1] = 0
      local t0 = clock()
      local ok, r = pcall(inner, This, sender, mtype, size, data)
      perfAdd(cls, mtype, h0 + 1, clock() - t0)
      local h = E.tgHold - 1
      E.tgHold = h
      if h <= 0 then
        E.tgHold = 0
        E.tgRelease()
      end
      if ok then
        if fret ~= 0 then return 1 end
        return r
      end
      once("vt8err:" .. cls, "pxrt: %s vtable8 hook error: %s", cls, tostring(r))
      return fret
    end
    inner = function(This, sender, mtype, size, data)
      if isTG and mtype == FRAME then
        E.syncBirths()   -- FirstFrame entries may already look objects up
        local ok, err = pcall(E.onFrame)
        if not ok then once("onframe", "pxrt: onFrame failed: %s", tostring(err)) end
        checkTeamSwitch(This:getAddr())
      end
      local pseudo = isTG and E.hasPseudo and E.hasPseudo()
      if not pseudo then
        if not classWants(cls) then return 0 end
        -- no override (of cls or a script class derived from it) acts on this message type: plain WA handler
        if mtype < SCRIPT_MSG_MIN and not typedWantsAny(cls, "Message", mtype) then return 0 end
      end
      local addr = This:getAddr()
      if directSend and directSend.addr == addr and directSend.mtype == mtype then
        directSend = nil
        return 0
      end
      local sa = 0
      if sender ~= nil then
        local ok, v = pcall(sender.getAddr, sender)
        if ok and type(v) == "number" then sa = v end
      end
      local daddr = 0
      if data ~= nil then
        local ok, v = pcall(ptrToInt, data)
        if ok and type(v) == "number" then daddr = v end
      end
      E.syncBirths()   -- before any pin lookup: a reborn address must not reach its dead owner's script state
      if isTG and mtype == FRAME and pxQueueN > 0 then flushPX(addr) end
      local obj = E.objectFor(addr, cls)
      if not obj then return 0 end
      local ccls = rawget(obj, "__cls") or cls
      local top = { This = This, sender = sender, senderAddr = sa, addr = addr, cls = cls, called = false }
      ctxStack[#ctxStack + 1] = top
      local mdata = (daddr ~= 0) and E.msgDataAt(daddr) or nil
      local snd = (sa ~= 0) and E.proxyAt(sa) or nil
      local ok, err
      if classWants(cls) and select(2, typedChain(ccls, "Message", mtype)) then
        ok, err = pcall(invokeTyped, obj, ccls, "Message", mtype, snd, mtype, size, mdata)
      else
        -- no script override: default behaviour = original handler
        ok = true
        if mtype < SCRIPT_MSG_MIN then
          E.CW.have = false
          pcall(callOrig[cls], This, sender, mtype, size, daddr)
          E.CW.have = false
        end
        top.called = true
      end
      ctxStack[#ctxStack] = nil
      if not ok then
        log("pxrt: %s::Message(%d) chain failed: %s", cls, mtype, tostring(err))
        if not top.called then pcall(callOrig[cls], This, sender, mtype, size, daddr) end
      end
      if pseudo then
        local ok2, err2 = pcall(E.dispatchPseudo, snd, mtype, size, mdata)
        if not ok2 then once("pseudo:" .. tostring(mtype), "pxrt: pseudo dispatch(%d) failed: %s", mtype, tostring(err2)) end
      end
      return 1
    end
    return hook
  end

  ---------------------------------------------------------------------
  -- FireWeapon hook
  ---------------------------------------------------------------------
  local fireGuard = false
  local function fireNative(self, super, weap, desc)
    local worm = rawget(self, "__a")
    if not worm then return 0 end
    local ws = type(weap) == "table" and (rawget(weap, "__a") or E.weaponStructAddr(E.weaponId(weap))) or 0
    local sd = E.sdAddr(desc)
    if ws == 0 or sd == 0 then once("firenative", "pxrt: FireFinal super with bad args") return 0 end
    -- WA's FireWeapon (the host's fireWeapon hook sits on it: onFire below lets it through while fireGuard is set)
    local fn = E.WA_FIREWEAPON()
    if fn == 0 then once("firenofn", "pxrt: FireWeapon not available: shot dropped") return 0 end
    local mark, before = fireMark()
    local prevSd = E.fireSd
    E.fireSd = sd   -- shoot desc of objects constructed during this shot
    fireGuard = true
    E.CW.have = false
    local ok, err = pcall(callRegs, fn, { eax = ws, ecx = sd }, worm)
    E.CW.have = false
    fireGuard = false
    if not ok then log("pxrt: FireWeapon original failed: %s", tostring(err)) end
    local ok2, err2 = pcall(constructFired, mark, before)
    if not ok2 then once("firector", "pxrt: constructing fired objects failed: %s", tostring(err2)) end
    E.fireSd = prevSd
    return 0
  end
  nat("CWorm").FireFinal = fireNative
  R.invalidate()

  -- pxcompat's registerCallback_fireWeapon shim hands callbacks the package's own Lua WeaponStruct (the one given to
  -- registerCustomWeapon: no names, placeholder sprite ids, raw converter data) in place of the entry WA fired. The
  -- original FireWeapon must get WA's live weapon-table entry, so anything outside the table is mapped back to the
  -- entry of the worm's current weapon.
  local WTAB_MAX = 0x400
  local function liveWeaponStruct(wsa, wa)
    local base = E.weaponTableAddr()
    if base == 0 or (wsa >= base and wsa < base + WTAB_MAX * 0x1D0 and (wsa - base) % 0x1D0 == 0) then return wsa end
    local id = -1
    if getWormWeaponId then
      local ok, v = pcall(getWormWeaponId, wa)
      if ok and type(v) == "number" then id = v end
    end
    if id < 0 then id = rd(wa + 0x170) end
    if id <= 0 or id >= WTAB_MAX then return wsa end
    local live = base + id * 0x1D0
    once("fireLive:" .. id, "pxrt: fired weapon struct 0x%X is not WA's table entry: using entry %d (0x%X)", wsa, id, live)
    return live
  end
  local function onFire(worm, ws, sd)
    if fireGuard then return 0 end
    if not R.hasScriptChain("CWorm", "FireFinal") then return 0 end
    local wa = ptrToInt(worm)
    local wsa, sda = ptrToInt(ws), ptrToInt(sd)
    wsa = liveWeaponStruct(wsa, wa)
    E.syncBirths()
    local o = E.objectFor(wa, "CWorm")
    if not o then return 0 end
    local weap = E.weaponAt(wsa, wa)
    local desc = E.sdAt(sda)
    E.curFire = { worm = wa, ws = wsa, sd = sda }
    local ok, err = xpcall(R.invoke, function(e)
      if os and os.getenv and os.getenv("PXRT_TB") then return debug.traceback(tostring(e), 2) end
      return e
    end, o, "CWorm", "FireFinal", weap, desc)
    E.curFire = nil
    if not ok then
      log("pxrt: FireFinal chain failed: %s", tostring(err))
      return 0
    end
    return 1
  end

  ---------------------------------------------------------------------
  -- lifecycle
  ---------------------------------------------------------------------
  local firstFrameDone = false
  function E.matchStart()
    E.tick = 0
    firstFrameDone = false
    for k in pairs(pins) do pins[k] = nil end
    for k in pairs(E.scriptObjs) do E.scriptObjs[k] = nil end
    for k in pairs(E.proxies) do E.proxies[k] = nil end
    if hostBirths then birthSeq = taskBirthSeq() end   -- every object is new to this match anyway
    E.lifeVer = E.lifeVer + 1
    pxQueue, pxQueueN = {}, 0
    ctxStack = {}
    directSend = nil
    if E.resetPseudo then E.resetPseudo() end
    if R.matchReset then
      local ok, err = pcall(R.matchReset)
      if not ok then log("pxrt: matchReset failed: %s", tostring(err)) end
    end
    -- InitGraphic normally ran inside each package's initialize() (asset paths resolve against the active package);
    -- units nobody initialized (libs whose package is not enabled) get it here
    local okg, errg = pcall(R.runEntries, "InitGraphic")
    if not okg then log("pxrt: InitGraphic entries failed: %s", tostring(errg)) end
    local ok, err = pcall(R.runEntries, "Init")
    if not ok then log("pxrt: Init entries failed: %s", tostring(err)) end
    pcall(E.hookClasses)
  end

  local SWEEP = 30
  function E.onFrame()
    E.tick = E.tick + 1
    if not firstFrameDone then
      firstFrameDone = true
      R.runEntries("FirstFrame")
    end
    if E.tick % SWEEP == 0 then
      for a, p in pairs(pins) do
        if not p.keep and (rd(a + 0x20) ~= p.cid or rdU(a) ~= p.vt) then pins[a] = nil end
      end
    end
  end

  ---------------------------------------------------------------------
  -- install (idempotent per callback generation)
  ---------------------------------------------------------------------
  -- A registered vtable8 callback makes the host call into Lua for EVERY Message of EVERY instance of that class (three
  -- userdata wrappers + a Lua call each, several times per frame per object: clouds, flames, fire, land, filter...).
  -- So a class is hooked only when some loaded script overrides Message for it (own or inherited). CTurnGame is always
  -- hooked: it carries the frame tick and the script-only (pseudo) objects. The host cannot unregister a callback, so
  -- the set only grows within one callback generation; it is re-evaluated after each package load.
  local hookedCls = {}
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
        local reg = regOf(cls, ct)
        local orig = _G[ct .. "_CallOriginal_vtable8"]
        if reg and orig then
          callOrig[cls] = perfOrig(orig)
          reg(makeVt8(cls))
          hookedCls[cls] = true
          E.hookedCount = (E.hookedCount or 0) + 1
        else
          once("novt8:" .. ct, "pxrt: no vtable8 hooks for %s", ct)
        end
      end
    end
  end

  ---------------------------------------------------------------------
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
    local t0 = clock()
    fnN.render = fnN.render + 1
    local id = hookIds.render
    local o = hasChain("CWorm", "RenderWorm") and E.objectFor(worm, "CWorm")
    if not o then
      callHookOriginal(id, worm)
    else
      local ok, err = pcall(R.invoke, o, "CWorm", "RenderWorm")
      if not ok then once("renderworm", "pxrt: RenderWorm chain failed: %s", tostring(err)) end
    end
    fnT.render = fnT.render + (clock() - t0)
  end
  -- the current worm's animator (GetCurrentWorm().Anim), 0 if there is no current worm
  local function curWormAnim()
    local tg = E.turnGameAddr()
    if tg == 0 then return 0 end
    local w, t = rd(tg + 0x130), rd(tg + 0x12C)
    if w <= 0 or w > 8 or t <= 0 or t > 6 then return 0 end
    local a = E.hashGet(tg, 2, w + 16 * t)
    if a == 0 then return 0 end
    return rdU(a + 0x368)
  end
  -- WA calls SetAnim for every animated object, many times per frame. Every PX SetAnimEx override (balloon, device,
  -- all_crates, hangglider, magnet) acts only when self is GetCurrentWorm().Anim and otherwise just calls super,
  -- so calls on any other animator go straight to the original without entering the script chain.
  local function onSetAnim(anim, sprite, phase)
    local t0 = clock()
    fnN.anim = fnN.anim + 1
    local id = hookIds.anim
    local o = hasChain("CSpriteAnim", "SetAnimEx") and u32(anim) == curWormAnim() and E.animAt(anim)
    if not o then
      fnFast = fnFast + 1
      local r = callHookOriginal(id, anim, sprite, phase)
      fnT.anim = fnT.anim + (clock() - t0)
      return r
    end
    local ok, err = pcall(R.invoke, o, "CSpriteAnim", "SetAnimEx", s32(sprite), s32(phase) / 65536.0)
    if not ok then once("setanim", "pxrt: SetAnimEx chain failed: %s", tostring(err)) end
    fnT.anim = fnT.anim + (clock() - t0)
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
    E.installFnHooks()
    if registerCallback_fireWeapon then registerCallback_fireWeapon(onFire) end
    if registerCallback_gameGlobalInit then
      registerCallback_gameGlobalInit(function()
        local ok, err = pcall(E.matchStart)
        if not ok then log("pxrt: matchStart failed: %s", tostring(err)) end
        return 0
      end)
    end
    if E.installExtra then E.installExtra() end
    log("pxrt: hooks installed (generation %s, task birth log %s)", tostring(gen), hostBirths and "yes" or "NO: old wkJellyWorm.dll")
  end
end
