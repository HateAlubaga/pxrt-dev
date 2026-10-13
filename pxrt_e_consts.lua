-- pxrt_e_consts: K table (PX named constants + dynamic engine globals)
return function(R, E)
  local K = {}
  R.K = K
  E.K = K

  -- message ids: WA TaskMessage values (Constants.h), PX name -> id
  local M = {
    M_FRAME = 2, M_DRAWQUEUE = 3, M_INPUT = 4, M_UPDATENONCRITICAL = 5, M_CRATECOLLECTED = 7, M_WORMDROWNED = 11,
    M_QUITGAME = 13, M_CHAT = 15, M_CAMERAAUTO = 16, M_CURSORMOVED = 17, M_STRIKECHANGED = 19, M_TEAMVICTORY = 20,
    M_GAMEOVER = 21, M_THINKINGSHOW = 26, M_EXPLOSION = 28, M_PLEFT = 30, M_PRIGHT = 31, M_PUP = 32, M_PDOWN = 33,
    M_FACELEFT = 34, M_FACERIGHT = 35, M_ENTER = 36, M_BACKSPACE = 37, M_SPACE = 38, M_SPACERLS = 39,
    M_SKIPTURN = 40, M_SURRENDER = 43, M_DETONATEWEAPON = 44, M_MOVEWEAPONLEFT = 45, M_MOVEWEAPONRIGHT = 46,
    M_SETDELAY = 47, M_SETDELAYB = 48, M_SETBOUNCE = 49, M_SETTARGET = 50, M_SETWEAPON = 51, M_TURNBEGIN = 52,
    M_AFTERRETREAT = 53, M_TURNEND = 55, M_TURNFINISHED = 57, M_APPLYPOISON = 62, M_SETWORM = 63, M_KILLWORM = 64,
    M_SETTEAM = 67, M_SHOWDAMAGE = 68, M_ENABLEWEAPONS = 69, M_DISABLEWEAPONS = 70, M_WORMMOVED = 71,
    M_WORMDAMAGED = 72, M_AFTERSHOOT = 73, M_WEAPONRELEASED = 73, M_WEAPONFINISHED = 74, M_GUNEXP = 75,
    M_WEAPONCREATED = 76, M_WEAPONHOMING = 77, M_WEAPONDESTROYED = 78, M_WEAPONCLAIMCONTROL = 79,
    M_WEAPONRELEASECONTROL = 80, M_POISON = 81, M_UPDATEWIND = 84, M_SHOWMESSAGE = 85, M_CREATEANIMATION = 86,
    M_WATERRISE = 89, M_ARMAGEDDON = 91, M_PAUSETIMER = 96, M_RESUMETIMER = 97,
  }
  -- script-only messages (never produced by WA)
  local custom = {
    "M_PRETURNSTART", "M_PXMESSAGE", "M_PXMESSAGECUSTOM", "M_DISABLECONTROL", "M_REBUILDWPANEL",
    "M_CHANGEWEAPONPANEL", "M_TOUCHSENSOR", "M_TOUCHSENSOR_COLLIDE", "M_MOVESPECIAL", "M_GIVECRATES",
    "M_STATEWRONGCHECKSUM", "M_STATEWRONGINITCHECKSUM", "M_WORMMOVED2", "M_RESUMETURN", "M_THINKINGHIDE",
  }
  for i, n in ipairs(custom) do M[n] = 0x7100 + i end
  E.M = M
  for k, v in pairs(M) do K[k] = v end

  local WS = {
    WS_IDLE = 0x65, WS_WALKING = 0x66, WS_AIMING = 0x67, WS_SETPOWER = 0x68, WS_FIRED = 0x69, WS_FIRECONT = 0x6A,
    WS_REPEATFIRE = 0x6B, WS_FIREPUNCH = 0x6C, WS_DRILLING = 0x6E, WS_TELEPORTING = 0x6F, WS_SHOOTINGROPE = 0x70,
    WS_BLOWTORCH = 0x71, WS_AFTERROPE = 0x73, WS_CONTROL_WEAPON = 0x74, WS_SUICIDEBOMBER = 0x75, WS_POING = 0x76,
    WS_JUMPPREPARE = 0x77, WS_JETPACK = 0x78, WS_JUMP = 0x79, WS_ROPING = 0x7B, WS_BUNGEE = 0x7C,
    WS_PARACHUTE = 0x7D, WS_SLIDING = 0x7F, WS_FLYING2 = 0x80, WS_FLYING = 0x81, WS_DEATH = 0x82,
    WS_SINKING = 0x85, WS_FROZEN = 0x86, WS_DEAD = 0x87, WS_POWERFLY = 0x89,
  }
  E.WS = WS
  for k, v in pairs(WS) do K[k] = v end
  for k, v in pairs(E.OC_BY_NAME) do K[k] = v end
  K.EObjectClass = E.OC_BY_NAME

  -- crate / weapon enums used by scripts (values from the PX wiki order)
  local misc = {
    CT_WEAPON = 0, CT_UTILITY = 1, CT_HEALTH = 2, CT_MWEAPON = 3, CT_TIMED = 4,
    WCT_RANDOM = 0, WCT_DEFINED = 1, WCT_UNKNOWN = 2,
    DT_NONE = 0, DT_TELEPORT = 1, DT_CHUTE = 2,
    CM_CLEAR = 0, CM_SOIL = 1,
    TI_FireStore = 0x1B, TI_Team = 0x15,
    WAction_None = 0, WAction_Homing = 1, WAction_Bounce = 2, WAction_Roam = 3, WAction_Dig = 4,
    WExplode_Nothing = 0, WExplode_Clustlets = 1, WExplode_Fire = 2,
    WAT_TrackSpeed = 0, WAT_Rotation = 1, WAT_TrackMovement = 2, WAT_HSpeed = 3, WAT_Slow = 4, WAT_Medium = 5,
    WAT_Fast = 6, WT_Gun = 0, WT_Flamer = 1, WT_Bow = 2, WT_Launcher = 3, AT_Strike = 0, AT_Crosshair = 1,
    Kazi = 0,
  }
  for k, v in pairs(misc) do K[k] = v end

  -- dynamic engine globals
  local dyn = {
    Root = function() return E.proxyAt(E.turnGameAddr(), "CTurnGame") end,
    GS = function() return E.gs() end,
    Env = function()
      E.envProxy.__a = E.envAddr()
      return E.envProxy
    end,
    GG = function() return E.ggProxy end,
  }
  setmetatable(K, {
    __index = function(t, k)
      local f = dyn[k]
      if f then return f() end
      R.once("K:" .. tostring(k), "pxrt: unknown constant K.%s", tostring(k))
      return 0
    end,
  })
  R.engineG.GS = nil
end
