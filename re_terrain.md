# WA 3.8.1 terrain queries - reverse engineering notes

Binary: `WA.exe` 3.8.1, x86, ImageBase 0x400000 (VAs below are absolute). Read-only static analysis, game never launched.
Confidence tags: [H] verified in disassembly, [M] strong inference, [L] guess / unverified.

## 0. Object chain (what Lua holds)

| name | how to get | notes |
|---|---|---|
| T = turn game task | `getTurnGameAddr()` | |
| G = "DDGame" (inner game object) | `readMemInt(T+0x2C)` | what every task keeps at `[task+0x2C]`. `E.ddGame()` in pxrt_engine.lua = G [H] |
| W = Jelly `addrDDGame` wrapper | vtable 0x66A30C, `W+0x488 = G` | DLL's `W+0x4CC` (PC_Landscape) is the same pointer as `[G+0x20]` [H] |
| P = PC_Landscape | `readMemInt(G+0x20)` (== `W+0x4CC`, == `[[CEnv+0x240]+0x20]`) | vtable 0x66B208, ctor 0x57ACB0, `[P+4] = G` [H] |
| CEnv | `readMemInt(G+0x528)` | `[CEnv+0x240] = G` [H] |
| gameinfo | `readMemInt(G+0x24)` | `+0xD778` = game-version number (gates 0x1F, 0x6B, 0x72, 0x11F, 0x17A) |

All world coordinates inside objects are 16.16 fixed point. Terrain methods of P take PLAIN PIXEL INTEGERS, so `px = x >> 16` (arithmetic shift = floor) before probing [H].

## 1. Landscape layers (PC_Landscape P)

Common bitmap object layout (all BitmapImage classes) [H]:

| off | meaning |
|---|---|
| +0x00 | vtable (base 0x6640EC; 1-bpp class 0x664118; 8-bpp class 0x664144) |
| +0x08 | data pointer (top row first, y grows down) |
| +0x10 | row stride in bytes |
| +0x14 | width (px) |
| +0x18 | height (px) |
| +0x1C / +0x20 / +0x24 / +0x28 | clip rect left, top, right (excl), bottom (excl); default (0,0,w,h). Reads outside return 0 |

| P field | type | role |
|---|---|---|
| +0x914 | 1-bpp | **collision / land bitmap** (1 = land). Source of truth for physics [H] |
| +0x910 | 8-bpp | visual land colour map (palette index per pixel) [H] |
| +0x908 | 1-bpp | third level image (loader image #3); snapshot/undo-copied with the others, never read by physics probes. Role unknown [L] |
| +0x90C | 8-bpp | extra layer used by the renderer [L] |
| +0x918 | bitmap | consulted by 0x57CC90 only when `[gameinfo+0xD9B0] != 0` [M] |
| +0x91C / +0x920 | display buffers | redraw targets [M] |
| +0x88 + id*4 | brush/mask table | entry m: `[m+0]` shape bitmap (1-bpp), `[m+4]` secondary bitmap, `[m+8]` w, `[m+0xC]` h, `[m+0x10]` hotspot x, `[m+0x14]` hotspot y [H] |
| +0xB3C | int | non-zero = **land frozen**: crater/mask writes are skipped. Setter = P vtable +0x04 (0x57BD10, thiscall `(P, flag)`, ret 4). Best candidate for the "Indestructible Land" cheat [M] |

Level size (pixels) is copied by the P ctor from the visual bitmap (0x57AD6E-0x57AD95): `[G+0x77C0]=width`, `[G+0x77C4]=height`, `[G+0x77C8]=w*h` [H].

### Bit encoding of the 1-bpp collision bitmap [H]
Leaf 0x4F5D70 (reached through the clip-check wrapper 0x4F9020):

    byte  = [data + stride*y + (x>>3)]
    solid = (byte >> (x & 7)) & 1        -- LSB-first within the byte

There is NO per-pixel "indestructible" value. The collision bitmap only distinguishes land / not land (see section 5).

8-bpp visual map (0x4F9140): `[data + stride*y + x]`, 0 outside clip.

## 2. P vtable (0x66B208) - every slot, verified

| slot | VA | convention | role |
|---|---|---|---|
| +0x00 | 0x57B540 | thiscall | dtor |
| +0x04 | 0x57BD10 | thiscall (P, flag) ret 4 | set `[P+0xB3C]` (freeze) |
| **+0x08** | **0x57C820** | thiscall (P, radius, x, y) ret 0xC | **carve circular crater**. PIXEL ints. radius clamped to [0,200] (0x64 if gameinfo+0xD778 < 6). No-op if `[P+0xB3C]!=0` |
| **+0x0C** | **0x57CCF0** | thiscall (P, maskId, x, y) ret 0xC | **apply brush mask** `[P+maskId*4+0x88]` at (x,y), centred by its hotspot. PIXEL ints. Writes layer 0 from `[m+0]`, layer 1 from `[m+4]` if non-nil. No-op if frozen |
| +0x10 | 0x57CD90 | thiscall (P, maskId, x, y) ret 0xC | **mask-vs-land overlap test**: 1 if any set pixel of brush `[m+0]` (placed like +0x0C) lies on a land pixel of `[P+0x914]`, else 0 |
| +0x14 | 0x57CE30 | thiscall | draws a bitmap into land (0x4F6910) |
| +0x18 | 0x57D7F0 | thiscall | not needed |
| +0x1C | 0x57CC90 | thiscall (P, x, y) ret 8 | 0 if `[P+0x914]` bit clear, else the colour byte of `[P+0x910]` (via 0x4F9140) |
| +0x20 | 0x57CF60 | thiscall (P, y) ret 4 | erase one pixel row y from 0x910/0x914 (rising-water task calls it per row) |
| +0x24 | 0x57D240 | thiscall (P, x16.16, y16.16, dx16.16, dy16.16, n) ret 0x14 | **line trace**: n steps adding (dx,dy), probing the collision bitmap at (x>>16,y>>16); returns index of first land step or -1 [H structure, M exact off-by-one] |
| **+0x28** | **0x57D230** | thiscall (P, x, y) ret 8 | **point probe** = `[P+0x914]->vt[+0x10](x,y)` -> 0 or 1. Used by the physics tick [H] |
| +0x2C | 0x57BD00 | thiscall | returns `[P+0xC8]` |

Your brief quoted slot VAs 0x57C1C0 / 0x57C690 for +8/+0xC. In this build those addresses sit inside other functions (0x57C1C0 is in a brush-table builder). The DLL reads the vtable dynamically, so it is unaffected; real values are 0x57C820 / 0x57CCF0.

### Carve-hole argument conventions (item 5)
- `Landscape::callWriteLandRadius` / MakeHole: `callThiscall(vt[+0x08], P, radius, x, y)`. **radius, x, y are PIXELS (plain ints), not 16.16.** Stack order: radius, x, y [H].
- `writeLandMaskID`: `callThiscall(vt[+0x0C], P, maskId, x, y)`. maskId indexes `[P+0x88+id*4]`; x, y pixels [H].
- Both skip when `[P+0xB3C] != 0`.

## 3. How WA tests object vs terrain (physics tick chain)

All VAs [H]. CEnv list iteration drives per-object ticks.

| VA | convention | what |
|---|---|---|
| 0x4FD230 | per-tick driver | loops calling 0x4FCDF0 per object (call at 0x4FD2CC) |
| 0x4FCDF0 | stdcall `(CEnv, obj, index)` ret 0xC | one object physics tick. Water sink check at 0x4FD104-0x4FD139: `movsx edx, word [obj+0x8A]; cmp edx,[G+0x5E4]` |
| 0x4FD640 | internal airborne path | builds a sub-step list in **globals at 0x7739C4..** (28 B/entry, count `[0x7739D0]`; `[obj+0xD0]` = steps, `[obj+0xE4]` = per-step records) then **point-probes terrain** at each step: `P=[[CEnv+0x240]+0x20]; P->vt[+0x28](x>>16, y>>16)` (0x4FD986-0x4FD9A5). Non-zero jumps to terrain-hit handler 0x4FDB19. Then object-vs-object via 0x4FB9D0 (call at 0x4FDA1A) |
| 0x4FD4C0 | stdcall `(CEnv, obj)` ret 8 | "path clear" re-test, also `P->vt[+0x28]` per step; AL=1 if clear. Uses the same 0x7739xx globals, NOT safely callable standalone |
| 0x4FB9D0 | stdcall `(CEnv, obj, x16.16, y16.16, size=[obj+0xDC], mask=[obj+0x34])` ret 0x18 | **object-vs-object** collision-group search (32 lists). Returns colliding object or 0. Terrain not involved |
| 0x4FB9A0 | register wrapper (obj in eax, stack x,y) | variant of the above |
| 0x4FBDC0 | esi=obj, stack `(CEnv, int* collType, int* fraction)` ret 0xC | returns the other object hit (via 0x4FB9D0) |
| 0x4FC6D0 | | ground walk speed/friction math (reads `[gameinfo+0xD9B0/D9C5/D9C8]`), no terrain probe |
| 0x4FF490 | | bounce response (called from 0x4FF69B), no terrain probe |

Take-aways for Lua:
1. The only terrain primitives physics uses are the **point probe** `P->vt[+0x28](px,py)` and (for projectiles) the line trace `+0x24`. Airborne objects are tested as a *point* (the sub-step position) against `[P+0x914]`; no object radius is tested against land on this path [M-H].
2. Worm ground collision uses its own probes in worm code (not traced in this pass) [L].
3. The tick functions share globals (0x7739C4 table). Do NOT call 0x4FD640 / 0x4FD4C0 / 0x4FCDF0 from Lua. Use the P vtable methods.

## 4. Water

There are no water pixels. Water is a Y threshold in pixels [H].

| field | meaning |
|---|---|
| `[G+0x5E0]` | water surface Y in pixels. Init (0x527A33): `(100 - [G+0x7780]) * [G+0x77C4] / 100` (`[G+0x7780]` = water % from level/scheme) |
| `[CEnv+0x228]` | copy of `[G+0x5E0]` (assigned at 0x550F6C-0x550F89 and 0x5537BA). PX `K.Env.Water` = this field [M]. Plain pixel int, NOT 16.16, although the PX wiki types it `fixed` |
| `[G+0x5E4]` | **sink threshold**: objects whose pixel Y `[obj+0x8A]` exceeds it drown. `(short)hi16([G+0x77A8]) + 0x28`; `[G+0x77A8] = max((water+0xA0)<<16, [G+0x77A4]+0x3000000)`, recomputed by 0x540190 (thiscall, ecx=G, no args, plain ret) |
| `[CEnv+0x22C]` | gravity (`= [gameinfo+0xD9A8]`); `[CEnv+0x230]` wind (earlier notes) |

Rising-water task (0x553760-0x5537DB), per pixel step: `[G+0x5E0] -= 1; P->vt[+0x20]([G+0x5E0])` (erase land row). At the end: `[CEnv+0x228]=[G+0x5E0]; call 0x540190(G); [G+0x5E4] = (short)[G+0x77AA] + 0x28`.

## 5. Solid vs indestructible vs empty

- Solid land: bit set in `[P+0x914]` [H].
- Empty: bit clear, or outside clip rect = outside the level (sides/top are not solid) [H].
- Water: `y >= [CEnv+0x228]` (pixel Y) [M]; objects die only once `y > [G+0x5E4]`.
- Indestructible: no per-pixel encoding found. Game only has (a) the global freeze flag `[P+0xB3C]` (carving writes skipped) and (b) the scheme cheat "Indestructible Land" plus mission keys `IndestructableLandscape/IndestructableBorder`, which almost certainly drive (a) [M]. A per-pixel indestructible mask, if any, would be `[P+0x908]` or the colour byte of `[P+0x910]` (via vt+0x1C): unverified [L]. For scripts treat indestructible as the global `readMemInt(P+0xB3C) ~= 0`.

## 6. Lua snippets (DLL natives only: readMemInt/readMemU8/readMemS16/writeMemU32/callThiscall/callStdcall)

```lua
-- helpers --------------------------------------------------------------
local function U(a) return readMemInt(a) % 4294967296 end     -- unsigned pointer read
local function floorDiv(a, b) return math.floor(a / b) end

local function G()                      -- inner game object ("DDGame")
  local t = getTurnGameAddr()
  if not t or t == 0 then return 0 end
  return U(t + 0x2C)
end
local function P()                      -- PC_Landscape
  local g = G(); if g == 0 then return 0 end
  return U(g + 0x20)                    -- == W+0x4CC
end
local function CEnv()
  local g = G(); if g == 0 then return 0 end
  return U(g + 0x528)
end

-- (2) level size in pixels --------------------------------------------
function levelSize()
  local g = G(); if g == 0 then return 4096, 2048 end
  local w, h = readMemInt(g + 0x77C0), readMemInt(g + 0x77C4)
  if w <= 0 or h <= 0 then              -- fallback: collision bitmap
    local p = P(); local bm = (p ~= 0) and U(p + 0x914) or 0
    if bm ~= 0 then w, h = readMemInt(bm + 0x14), readMemInt(bm + 0x18) end
  end
  return w, h
end

-- (2) water level (pixel Y of the surface) -----------------------------
function waterLevel()
  local e = CEnv(); if e == 0 then return 0 end
  return readMemInt(e + 0x228)          -- plain pixel int
end
function waterSinkY()                   -- objects below this die
  local g = G(); if g == 0 then return 0 end
  return readMemInt(g + 0x5E4)
end
function setWaterLevel(y)               -- keeps WA's derived fields consistent
  local g, e = G(), CEnv(); if g == 0 or e == 0 then return end
  y = math.floor(y)
  writeMemU32(g + 0x5E0, y % 4294967296)
  writeMemU32(e + 0x228, y % 4294967296)
  callThiscall(0x540190, g)             -- recompute [G+0x77A8]
  writeMemU32(g + 0x5E4, (readMemS16(g + 0x77AA) + 0x28) % 4294967296)
end

-- (1) is pixel (x,y) land?  direct read of the 1-bpp collision bitmap ---
function getPixelSolid(x, y)
  x, y = math.floor(x), math.floor(y)
  local p = P(); if p == 0 then return false end
  local bm = U(p + 0x914); if bm == 0 then return false end
  if x < readMemInt(bm + 0x1C) or x >= readMemInt(bm + 0x24)
     or y < readMemInt(bm + 0x20) or y >= readMemInt(bm + 0x28) then
    return false
  end
  local data, stride = U(bm + 8), readMemInt(bm + 0x10)
  local b = readMemU8(data + y * stride + floorDiv(x, 8))
  return (floorDiv(b, 2 ^ (x % 8)) % 2) == 1
end

-- same query through WA's own method (vtable +0x28 = 0x57D230) ----------
function getPixelSolidWA(x, y)
  local p = P(); if p == 0 then return false end
  local fn = U(U(p) + 0x28)
  return callThiscall(fn, p, math.floor(x), math.floor(y)) % 256 ~= 0
end

-- palette index of the land pixel, 0 if no land (vtable +0x1C = 0x57CC90)
function getLandColor(x, y)
  local p = P(); if p == 0 then return 0 end
  return callThiscall(U(U(p) + 0x1C), p, math.floor(x), math.floor(y)) % 256
end

-- classification: "out", "water", "land", "air" -------------------------
function terrainClass(x, y)
  local w, h = levelSize()
  if y >= waterLevel() then return "water" end
  if x < 0 or x >= w or y < 0 or y >= h then return "out" end
  return getPixelSolid(x, y) and "land" or "air"
end
function landIndestructible()           -- global flag only (section 5)
  local p = P(); return p ~= 0 and readMemInt(p + 0xB3C) ~= 0
end

-- (3) collision of an object at (x,y) with land --------------------------
-- WA physics = point probe of the object position (16.16 >> 16) per sub-step.
local function px16(v) return math.floor(v / 65536) end       -- 16.16 -> px (floor)
function collides(objAddr, x, y)
  -- x,y in PIXELS; nil = use object position (+0x84 x, +0x88 y, 16.16) [M]
  if x == nil then x = px16(readMemInt(objAddr + 0x84)) end
  if y == nil then y = px16(readMemInt(objAddr + 0x88)) end
  return getPixelSolid(x, y)
end
-- optional ring test, radius r in pixels (approximation; WA itself uses only the centre)
function collidesCircle(x, y, r)
  if getPixelSolid(x, y) then return true end
  local d = r * 0.7071
  local pts = {{r,0},{-r,0},{0,r},{0,-r},{d,d},{-d,d},{d,-d},{-d,-d}}
  for _, q in ipairs(pts) do
    if getPixelSolid(x + q[1], y + q[2]) then return true end
  end
  return false
end
-- brush mask vs land through WA (vtable +0x10 = 0x57CD90)
function maskHitsLand(maskId, x, y)
  local p = P(); if p == 0 then return false end
  return callThiscall(U(U(p) + 0x10), p, maskId, math.floor(x), math.floor(y)) % 256 ~= 0
end
-- ray march: index of first land step along (dx,dy) 16.16 each, n steps, or -1
function traceLand(x16, y16, dx16, dy16, n)
  local p = P(); if p == 0 then return -1 end
  local r = callThiscall(U(U(p) + 0x24), p, x16, y16, dx16, dy16, n)
  if r >= 2147483648 then r = r - 4294967296 end
  return r
end
-- object vs object (collision groups), NOT terrain: 0x4FB9D0 stdcall
function objectHitsObject(objAddr, x16, y16)
  return callStdcall(0x4FB9D0, CEnv(), objAddr, x16, y16,
                     readMemInt(objAddr + 0xDC), readMemInt(objAddr + 0x34))
end

-- carve (PIXELS) ----------------------------------------------------------
function makeHole(radius, x, y)
  local p = P(); if p == 0 then return end
  callThiscall(U(U(p) + 0x08), p, math.floor(radius), math.floor(x), math.floor(y))
end
function applyMask(maskId, x, y)
  local p = P(); if p == 0 then return end
  callThiscall(U(U(p) + 0x0C), p, maskId, math.floor(x), math.floor(y))
end
```

Hook-in to existing runtime: set `E.levelSize = levelSize` (returns w,h), `E.waterLevel = waterLevel`, `E.setWaterLevel = setWaterLevel` (consumed in `pxrt_e_game.lua` around lines 94, 104, 148). `K.GS.LevelSX/LevelSY` = `levelSize()`.

## 7. Confidence summary

| item | conf |
|---|---|
| G / P / CEnv chain, P = `[G+0x20]` = `W+0x4CC` | H |
| level size at `G+0x77C0/0x77C4` (and bitmap `+0x14/+0x18`) | H |
| collision bitmap `[P+0x914]`, 1 bpp, LSB-first, stride `[bm+0x10]`, clip rect `+0x1C..0x28` | H |
| point probe `P->vt[+0x28]` convention (x,y px ints, thiscall, ret 8) | H |
| crater/mask conventions (pixels; radius,x,y / maskId,x,y) | H |
| mask-overlap test vt+0x10 | H |
| line trace vt+0x24 exact index semantics | M |
| `K.Env.Water` = `[CEnv+0x228]`, pixel Y | M |
| sink threshold `[G+0x5E4]` and `setWaterLevel` recipe | H (mirrors 0x5537BA-0x5537D5) |
| airborne physics = centre point-probe ray march (no radius) | M-H |
| worm-on-ground probes | L (not traced) |
| indestructible = global flag `[P+0xB3C]` (setter vt+4) | M for cheat mapping; per-pixel indestructible not found (L if it exists in `[P+0x908]`) |
| `[obj+0x84]/[obj+0x88]` = 16.16 x/y (physics reads `word [obj+0x8A]` = hi16 of y at +0x88) | M |
