-- pxrt_e_extra: small PX builtin classes / methods that scripts use but WA has no counterpart for (inert) or that are
-- trivial to answer from script state.
return function(R, E)
  local ti, tf = R.ti, R.tf
  local N, BC = R.natives, R.builtinClasses
  local rawset, setmetatable = rawset, setmetatable
  local function nat(cls) N[cls] = N[cls] or {} return N[cls] end

  -- PX-only structs: plain field bags (unknown fields read 0, writes are kept)
  local function bag(cls)
    BC[cls] = function() return setmetatable({ __cls = cls }, R.scriptMTFor(cls)) end
  end
  for _, c in ipairs({ "CLightSource", "CRespawnState", "CRespawnTeam" }) do bag(c) end

  -- CWormParams (new-worm descriptor): kept in the struct, spawning real worms is not supported
  nat("CWormParams").SetName = function(self, super, name) rawset(self, "Name", name) return 0 end
  -- PX: SetPosition(health, x, y, flag) (utils.pxc SpawnWorm, sheep scripts)
  nat("CWormParams").SetPosition = function(self, super, health, x, y, flag)
    rawset(self, "Health", ti(health)); rawset(self, "PosX", tf(x)); rawset(self, "PosY", tf(y))
    return 0
  end

  -- CGObject::IsInBox(left, top, right, bottom): is the object position inside the box
  nat("CGObject").IsInBox = function(self, super, l, t, r, b)
    local x, y = tf(self.PosX), tf(self.PosY)
    return (x >= tf(l) and x <= tf(r) and y >= tf(t) and y <= tf(b)) and 1 or 0
  end
end
