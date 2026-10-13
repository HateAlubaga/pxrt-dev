"""Run a jelly package main.lua under lupa with stubbed wkJellyWorm APIs.

usage: py -3.10 luasim.py <package_dir> <scenario>
"""
import sys, os
from lupa import LuaRuntime

PKG = sys.argv[1]
SCEN = sys.argv[2] if len(sys.argv) > 2 else "glider"
LIBS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(PKG.rstrip("/\\")))), "lualibs")

lua = LuaRuntime(unpack_returned_tuples=True)
G = lua.globals()
mem = {}
log = []
callbacks = {"vt8": [], "turnstart": []}
next_id = {"sprite": 851, "sound": 451}
sprites = {}


def rd(a):
    return int(mem.get(int(a), 0))


def wr(a, v):
    v = int(v)
    if v >= 2**31: v -= 2**32
    mem[int(a)] = v


def reg_sprite(name, frames=None, flags=None):
    path = os.path.join(PKG, "assets", name)
    if not os.path.isfile(path):
        log.append(("MISSING_SPRITE", name))
        return 0
    i = next_id["sprite"]; next_id["sprite"] += 1
    sprites[i] = (name, frames)
    return i


def reg_sound(name):
    path = os.path.join(PKG, "assets", name)
    if not os.path.isfile(path):
        log.append(("MISSING_SOUND", name))
    i = next_id["sound"]; next_id["sound"] += 1
    return i


def draw(*a):
    log.append(("draw",) + tuple(a))


def play(*a):
    log.append(("sound",) + tuple(a))


def wso(*a):
    name = a[2]
    if isinstance(name, str) and not os.path.isfile(os.path.join(PKG, "assets", name)):
        log.append(("MISSING_OVERRIDE", name))
    log.append(("override",) + tuple(a))
    return True


G.readMemInt = rd
G.writeMemInt = wr
G.registerCustomSprite = reg_sprite
G.registerCustomSound = reg_sound
G.drawSpriteLocal = draw
G.playSoundLocal = play
G.SetWeaponSpriteOverride = wso
G.SetSpriteOverride = wso
G.registerCustomWeapon = lambda *a: 74
G.weaponIdByName = lambda n: 74 if n in ("Glider", "Hot Air Balloon", "Balloon") else -1
G.getWormWeaponId = lambda w: rd(int(w) + 0x170)
G.wormSetState = lambda w, s: wr(int(w) + 0x44, s)
lua.execute("""
package.path = ... .. '/?.lua;' .. package.path
""", LIBS.replace("\\", "/"))
reg = lua.eval("function(tbl) return function(f) table.insert(tbl, f) end end")
G.CTaskWorm_RegisterCallback_vtable8 = reg(lua.table())
lua.execute("__vt8 = {}; __ts = {}")
lua.execute("function CTaskWorm_RegisterCallback_vtable8(f) table.insert(__vt8, f) end")
lua.execute("function registerCallback_onTurnStart(f) table.insert(__ts, f) end")
lua.execute("""
local mt = {__index = function(t, k) return function(...) return 0 end end}
setmetatable(_G, {__index = function(t, k)
  if type(k) == 'string' and (k:match('^registerCallback_') or k:match('^CTask')) then
    return function(...) end
  end
  return nil
end})
""")

src = open(os.path.join(PKG, "main.lua"), encoding="utf-8", errors="replace").read()
lua.execute("__pkgdir = ...", PKG.replace("\\", "/"))
chunk = lua.eval("function(s) local f, e = load(s, 'main.lua'); if not f then error(e) end; return f end")(src)
chunk()
if G.initialize:
    G.initialize()

WORM = 0x1000000
FIX = 65536
DD, WORLD = 0x2000000, 0x3000000
wr(WORM + 0x2C, DD); wr(DD + 0x528, WORLD)
wr(WORLD + 0x22C, int(0.03 * FIX))  # gravity px/frame^2
wr(WORLD + 0x230, int(0.01 * FIX))
wr(WORM + 0x84, 500 * FIX); wr(WORM + 0x88, 300 * FIX)
wr(WORM + 0x1A8, -1)
wr(WORM + 0x170, 74)


class This:
    def getAddr(self):
        return WORM


this = This()


def send(m):
    r = 0
    for f in lua.globals().__vt8.values():
        r |= int(f(this, None, m, 0, None) or 0)
    return r


def frame(state, keys=()):
    wr(WORM + 0x44, state)
    for k in keys:
        send(k)
    send(2)
    # move worm by its speed like WA would
    wr(WORM + 0x84, rd(WORM + 0x84) + rd(WORM + 0x90))
    wr(WORM + 0x88, rd(WORM + 0x88) + rd(WORM + 0x94))
    send(3)


def scenario_glider():
    wr(WORM + 0x90, int(2 * FIX)); wr(WORM + 0x94, int(-1 * FIX))
    for _ in range(3):
        frame(0x65)
    for t in range(120):
        frame(0x7D, keys=(33,) if 40 <= t < 60 else ((32,) if 80 <= t < 90 else ()))
        if t % 10 == 0 or t in (1, 2, 3):
            print("t=%3d sp=(%.2f,%.2f) pos=(%.1f,%.1f) last=%s" % (
                t, rd(WORM + 0x90) / FIX, rd(WORM + 0x94) / FIX,
                rd(WORM + 0x84) / FIX, rd(WORM + 0x88) / FIX,
                [e for e in log if e[0] == "draw"][-1:]))
    # stall: worm stopped by WA (not moving)
    for t in range(3):
        wr(WORM + 0x44, 0x7D); send(2); send(3)
    print("stall sp=(%.2f,%.2f)" % (rd(WORM + 0x90) / FIX, rd(WORM + 0x94) / FIX))
    frame(0x65)
    wr(WORM + 0x1A8, 1)
    frame(0x7D); frame(0x7D)
    print("right-facing draw", [e for e in log if e[0] == "draw"][-1])
    frame(0x65)


globals()["scenario_" + SCEN]()
for e in log:
    if e[0] != "draw":
        print(e)
print("sprites", sprites)
