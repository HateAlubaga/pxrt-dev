# WA 3.8.1 CTaskWorm: render, aim, collision, sink, state-to-animation (static RE)

Binary: `C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe`, 32-bit, image base 0x400000. All addresses are VAs. The game was never launched; everything is from disassembly. Helper to re-check any address: `cd /c/Users/Admin && py -3.10 pxrt_dev/wr/wl.py <hexaddr> f|l [N]|b [N]|u [N]` (f = function with jump tables, l = linear N insns, b = bytes, u = dwords).

Units: 16.16 fixed point. Aim angle: 0 = straight down, 0x8000 = level, 0x10000 = straight up (a half circle spans 0..0x10000). Confidence tags: [H] read in the code, [M] strong inference, [L] guess.

## 0. Headline findings

1. There is NO RenderWorm / RenderCrosshair vtable slot. Drawing is done by direct calls inside `HandleMessage` message 3: RenderWorm = `0x50FCD0`, RenderCrosshair = `0x51D680`. Hook them with `hookFunction`, not with vtable callbacks. [H]
2. OnSink is vtable offset `+0x30` (slot 12), not `+0x2C`. The DLL name `vtable2C_OnSink` is a misnomer: `+0x2C` is the earthquake/knock impulse `(dvx, dvy)`. [H]
3. Message 3 = physics + draw enqueue. Message 2 = per-frame game logic (`0x515650`, which also drives the aim easing; the animator Advance is called from the same function). [H]
4. The body sprite is not stored on the worm. The worm owns an animator object (`[worm+0x368]`) holding the current sprite id and phase; RenderWorm reads it each frame through `GetWormDrawParams (0x512E80)` and queues one sprite. Everything PX does in `RenderWorm` can be done by hooking `0x512E80` and rewriting its outputs. [H]

---

## 1. CTaskWorm vtable at 0x6644C8 (20 slots)

DLL naming: `CTaskWorm_RegisterCallback_vtableXX(fn)` and `CTaskWorm_CallOriginal_vtableXX(this, ...)`, XX = byte offset in hex. Callbacks are `fn(this, a2, a3...)`. Any callback returning nonzero suppresses the original, and the hook then returns 0 to the engine.

| off | addr | meaning | args (thiscall, ecx=this) | notes |
|---|---|---|---|---|
| +0x00 | 0x50CAA0 | destructor | flag | |
| +0x04 | 0x50C7E0 | Free | | |
| +0x08 | 0x510B40 | HandleMessage | (sender, msg, size, data), ret 0x10 | switch idx=msg-1, byte table 0x512D54, jump table 0x512C7C |
| +0x0C | 0x516780 | unknown | | |
| +0x10 | 0x5613D0 | base | | |
| +0x14 | 0x562FA0 | base | | |
| +0x18 | 0x563000 | base | | |
| +0x1C | 0x50D5D0 | Reflect(other, type) | 2 stack, ret 8 | worm override of base 0x4FF720 (momentum exchange). Called on the OTHER object by Collide. PX `Reflect`. |
| +0x20 | 0x50D9A0 | Collide(obj, type) | 2 stack, ret 8, returns AL | worm override of base 0x4FFED0. PX `Collide`. Called from the physics tick at 0x4FD0AE. |
| +0x24 | 0x50D810 | OnHitObject(arg) | 1 stack, ret 4 | tail-jumps to 0x516990. Called at 0x4FCF3A with the object returned by 0x4FD640. [M] role |
| +0x28 | 0x50D820 | unknown | 1 stack, ret 4 | tail-calls 0x516A90 with edx=arg. [L] |
| +0x2C | 0x50D570 | ApplyImpulse(dvx, dvy) | 2 stack, ret 8 | earthquake/knock. Worm: if state is not a flying-class state it calls SetState(0x7F) first, then adds to speed (+0x90/+0x94). Base 0x5000E0 only adds. DLL calls this "vt2C". |
| +0x30 | 0x500380 | OnSink() | none | NOT overridden by worms. Plays Splash (sound 0x39) with volume from (|vx|+|vy|)/5+0x8000 via 0x4FDFE0. |
| +0x34 | 0x50D3B0 | OnSkim() | none | worm override. Plays Splish (0x3A), then SetState(0x81 or 0x89) (0x89 when game version >= 0x4D) unless config byte `cfg+0xD967` is set. |
| +0x38 | 0x50E850 | SetState(newState) | 1 stack, ret 4 | the worm state machine. PX `SetState`. |
| +0x3C | 0x516900 | ReleaseRope | | if `[+0xBC]` set then SetState(0x73). [M] |
| +0x40 | 0x516920 | unknown | | |
| +0x44 | 0x500090 | ApplyForce(dx, dy, dz) | 3 stack, ret 0xC | speed += arg * `[+0x4C]` (weight); `[+0x98] += dz`; returns 0 when `[+0x48]` is nonzero. [M] |
| +0x48 | 0x5168F0 | unknown | | called by 0x4FB9D0 (landscape probe) to fetch a team index |
| +0x4C | 0x4AA060 | unknown | | |

---

## 2. Rendering (item 1)

### 2.1 Call order inside HandleMessage msg 3 (handler 0x511B9B, block 0x511C60..0x511D57)  [H]

`ebx` = worm, `esi` = worm right before the calls. Gate: state 0x64 (not placed) skips the whole block; `[+0x140]` and the team flags at `game+team*0x51C+0x4618/0x4628` also decide whether it is skipped (0x511C84..0x511CB8).

```
0x511CF0 call 0x513A90   jetpack flame sprites 0xAB/0xAC (state 0x78 only)
0x511CF5 call 0x50FB50   HUD text (DrawTextbox)
0x511CFC call 0x50FCD0   RenderWorm       (eax = worm)   <== body sprite
0x511D01 call 0x510260   HUD text
0x511D08 call 0x5197D0   overlay sprite (rope / parachute class)   [M]
0x511D20 call 0x50F900   label text / marker (stack: worm; only when [+0x208]==0)
0x511D25 call 0x50FDC0   text
0x511D2A call 0x51D680   RenderCrosshair  (esi = worm)   <== crosshair, power bar, laser line
0x511D31 call 0x50F810   target cursor sprite (ecx = worm)   [M]
0x511D48 call 0x500720   base-class helper (stack: worm, ...)   [L]
0x511D4F call 0x5103A0   overlay sprite 0x88 when [+0x1C4] != 0 (eax = worm)   [M]
```

### 2.2 RenderWorm = 0x50FCD0  [H]

Calling convention: `eax = worm`, no stack args, plain `ret`. It pushes and restores esi and clobbers ecx/edx. Only caller: 0x511CFC.

```
GetWormDrawParams(eax=&sprite; stack &x,&y,&phase)             // 0x512E80
if (team flags byte [game + team*0x51C + 0x4628] & 8)  sprite |= 0x200000   [M meaning]
if (worm[+0x148])                                     sprite |= 0x400000   [M meaning]
idx  = worm[+0x158]
base = idx >= 0 ? game[+0x2600 + idx*4]
                : (game[+0x3608] > 0x100 ? game[+0x3608] : game[+0x3604])
layer = base*4 + (layerTab[state-0x68] == 0 ? 0xC0000 : 0xD0000)
QueueSprite(ecx=game[+0x524], eax=y, stack: layer, x, sprite, phase)       // 0x542060
```
Layer table: bytes at 0x50FD9C indexed by `state-0x68` (35 entries), jump table 0x50FD94 {0:0x50FD5F -> `base*4+0xC0000`, 1:0x50FD68 -> `base*4+0xD0000`}. Value 0 for states 0x68..0x72, 0x74, 0x75, 0x8A; value 1 for 0x73 and 0x76..0x89. States outside 0x68..0x8A (idle 0x65, walk 0x66, aim 0x67) use 0xD0000. Whether a higher layer draws in front of a lower one was not checked. [H table, L semantics]

### 2.3 GetWormDrawParams = 0x512E80  [H]

Convention: `eax = &outSprite`, `esi = worm` (implicit register), stack `(int* outX, int* outY, int* outPhase)` (pushed phase, y, x so `[esp+4]` is `&x`), `ret 0xC`. Only caller: RenderWorm.

1. `*x = worm[+0x84]`, `*y = worm[+0x88]` (16.16 world position).
2. Calls animator vtable `+0x0C` (Get) to fill `*sprite` and `*phase`.
3. Special cases applied to the animator values:
   - state 0x78 (jetpack): if `[+0x224] >= 0` then `sprite ^= 0x40000`; returns at once (no generic facing flip).
   - state 0x66 with sprite 0x89 (walk) and `[+0x1A8] != [+0x334]`: x/y bob from `[+0x1F0]`, `[+0x1F4]`.
   - state 0x71 with sprite 0x8C (blowtorch): y offset `[+0x1F4]`. [M]
   - sprite 0x1A8: `phase = 2*[+0x18C]` if `[+0x18C] < 0x8000` else `2*(0x10000-[+0x18C])`.
   - sprites 0x204, 0x228, 0x22B (limited-arc weapons): phase clamped to [0x4000, 0xC000] then `2*phase - 0x8000`.
   - sprite 0x8C: sprite id +1 or +2 chosen from the aim bucket `((aim*8+0x8000)>>16)` mapped to 3..5 (`==5` +1, `==3` +2). [M]
   - turn-around variants: sprite ids come in triples (base, base+1, base+2). For "class 0" bases (tables at 0x51326C for ids 0x89..0x187, 0x513374 for 0x18D..0x24F, 0x513444 for 0x800130..) the code adds `+1` if `[+0x1AC] < 0` and `+2` if `[+0x1AC] > 0` (0x513100). `[+0x1AC]` is the turn-around phase sign. [M]
   - sprite 0x95 (flying): variant `0x95 + f((x+y)>>16)` so the tumble frame depends on position, not time. [M]
   - **`if worm[+0x1A8] > 0: sprite ^= 0x40000`** (mirror flag). The native art faces left (-1); facing right sets 0x40000. [H]
   - per-state phase override (byte table 0x51351C, index = state-0x73, jump table 0x51350C): state 0x73 and 0x80 -> phase from rotation `[+0x8C]` plus spin; 0x7B (roping) -> `phase = ((-[+0x8C]*facing)&0xFFFF) - 0xBE00`; 0x7C (bungee) -> another function of `[+0x8C]`. All return via `ret 0xC`.

### 2.4 QueueSprite = 0x542060  [H]

`ecx = [game+0x524]` (draw queue: record count at `+0x10004`, record pointer array at `+0x10008`, capacity 0x800, 0x18 byte records), `eax = y`, stack `(layer, x, spriteId, phase)`, `ret 0x10`. Writes record `{type=5, layer, x&0xFFFF0000, y&0xFFFF0000, sprite, phase}`. The sibling at 0x542000 writes type 4 (fixed frame instead of phase). The consumer is the loop at 0x542380 with jump table 0x542AC8; type 5 subtracts the camera (0x542B10) and calls the display object's vtable `+0x4C` with (sprite, phase). The phase-to-frame step inside that method was NOT traced. [H producer, M consumer]

Sprite id flag bits seen: `0x40000` mirror, `0x800000` reverse playback (animator), `0x200000` / `0x400000` set by RenderWorm, `0x2000000` set by RenderCrosshair.

### 2.5 Lua recipes (render)

Tweak what is drawn but keep WA's own draw (covers most PX uses). Hook GetWormDrawParams and edit its outputs after the original ran:
```lua
local G
G = hookFunction("wormdraw", 0x512E80, {regs = {"eax", "esi"}, nstack = 3},
  function(pSprite, worm, pX, pY, pPhase)
    callHookOriginal(G)                      -- fills *pSprite, *pX, *pY, *pPhase
    if readMemU32(worm + 0x44) == MY_STATE then
      local flip = readMemU32(pSprite) & 0x40000          -- keep facing mirror
      writeMemU32(pSprite, MY_SPRITE | flip)
      writeMemU32(pPhase, 0x8000)
      writeMemU32(pY, readMemU32(pY) - 0x100000)          -- 16 px up (u32 wrap is fine)
    end
    return nil                               -- nil after callHookOriginal passes original EAX through
  end)
```
Args arrive as `regs` first (eax, esi), then the 3 stack args. `cleanup` defaults to nstack*4 = 12, matching `ret 0xC`.

Replace the body draw completely (PX `RenderWorm` override). A Lua hook that returns WITHOUT calling `callHookOriginal` suppresses the original (see `luaHookDispatch` in LuaNative.cpp; the original only runs when the callback errors):
```lua
hookFunction("wormrender", 0x50FCD0, {regs = {"eax"}}, function(worm)
  local game = readMemU32(worm + 0x2C)
  local q    = readMemU32(game + 0x524)
  local sprite = MY_SPRITE
  if readMemU32(worm + 0x1A8) == 1 then sprite = sprite | 0x40000 end
  local layer = readMemU32(game + 0x3604) * 4 + 0xD0000      -- default layer when worm[+0x158] < 0 (also see 2.2)
  callRegs(0x542060, {ecx = q, eax = readMemU32(worm + 0x88)},
           layer, readMemU32(worm + 0x84), sprite, MY_PHASE)
  return 0
end)
```
To add something around the original, call `callHookOriginal(id)` first. Use `hookCurrentRegs()` once to confirm eax = worm.

---

## 3. Aim angle, crosshair, weapon-hold pose (item 2)

### 3.1 Worm fields  [H unless noted]

| off | meaning |
|---|---|
| +0x1A8 | facing (-1 left, +1 right, 0 transient). Right => sprite mirror flag 0x40000. |
| +0x24C | aim TARGET angle, 0..0x10000, init 0x8000. Input handler 0x51D100: down key `-= 0x200`, up key `+= 0x200` per frame (swapped by byte `+0x338`). |
| +0x270 | live smoothed aim angle used by the crosshair: `new = 0.8*old + 0.2*[+0x24C]` (0xCCCC/0x3333), at 0x51D0C7 and 0x51D7B0. |
| +0x26C | crosshair fade-in factor, 0 -> 0x10000 with the same filter. |
| +0x268 | aim-pose mode. 0 = weapon has no aim-driven pose; 1 = Set(sprite, 0x8000) at equip; 2 = quantized variant. 0x51CFC0 and RenderCrosshair both bail when 0. Written by 0x517100. |
| +0x248 | firing power 0..0x10000 (charge state 0x68 adds 0x369 per frame). |
| +0x170 / +0x174 | selected weapon index (0 = none) / ammo. |
| +0x36C | weapon struct pointer = `[game+0x510] + idx*0x1D0`: `+0x30` category (1..4), `+0x34` sub-id, `+0x38`, `+0x60`. |
| +0x338 / +0x339 | up/down swap byte / power oscillation direction byte. |
| +0x3D0..+0x3E0 | crosshair interpolation cache used by 0x51D680. |
| +0x10C | crosshair sprite base, added to `0x2000002` when drawing the crosshair. [M] |
| +0x368 | animator object pointer (section 4.1). |

### 3.2 Angle to frame  [H angle side, M renderer side]

`0x51CFC0` runs every frame (call at 0x515837 inside 0x515650, `esi = worm`, no stack args, plain `ret`):

```
Get(animator) -> (sprite, phase)
if worm[+0x268] == 0 or worm[+0x170] == 0: return
target = worm[+0x24C]
if phase != target and sprite == WormAimSprite(worm[+0x36C], worm):        // 0x51C060
    next = (|phase-target| >= 0x16C) ? (0x4CCC*target + 0xB333*phase) >> 16 : target   // 0.3/0.7 easing
    if worm[+0x170] != 0x12: animator.SetPhase(next)                        // vtable +0x10
(then updates the +0x26C / +0x270 smoothing and the +0x3D0.. cache)
```
So for a static aim-pose sprite the animator phase IS the aim angle: phase 0 = down, 0x8000 = level, 0x10000 = up; the frame strip is indexed by phase (the exact `phase*frames` rounding is inside the display method, not traced). `SetPhase` (0x4F53F0) only applies when the animator speed field `[anim+0x10]` is 0, i.e. for non-animating pose sprites. The DLL aim-pose fix (`CustomWeapons.cpp`: `hookAimUpdateCall`, `aimPoseBefore/After`, pattern site `0x51582D+10`) replicates exactly this easing. Facing left is done by the mirror flag; the crosshair geometry additionally mirrors the angle (`0x20000 - a`) when `[+0x1A8] < 0`.

`WormAimSprite = 0x51C060`: `eax = weapon struct`, stack `(worm)`, `ret 4`; returns a sprite id, 0 when none (an invisible worm if used raw; the DLL has a fallback). Callers: 0x517127, 0x517879, 0x518212, 0x51ACF2, 0x51D00D. Dispatch on `[wep+0x30]-1` (jump table 0x51C240, only 0..3 reachable) [H]:

| `[wep+0x30]` | selector | result |
|---|---|---|
| 1 | `[wep+0x34]-1` (table 0x51C250) | sub-id 1: 0x234, 3: 0x20D, 4: 0x23A, 5: 0x21F, 6: 0x22E, 7: 0x213, 8: 0x216, 9: 0x210, 10: 0x204, 11: 0x2AD, 12: 0x2B0; sub-id 2: by `[wep+0x60]-0x32` (table 0x51C280) 0x32: 0x240, 0x33: 0x246, 0x35: 0x243, 0x37: 0x249, 0x38: 0x24C (others 0) |
| 2 | `[wep+0x38]` | 1: 0x184; 2: by weapon id `[wep+0x60]&0xFFFF` in 0x4A.. (byte table 0x51C2C0, jump 0x51C29C): 0x151, 0x14E, 0x157, 0x15A, 0x163, 0x154, 0x160, 0x15D (first one is id 0x4A, the rest at the table positions); anything else 0 |
| 3 | none | 0x19C |
| 4 (utility) | `[wep+0x34]-1` (table 0x51C324) | 0: 0x199, 1: 0x207, 2: 0x199, 3: 0x199, 4: 0x148, 5: 0x219, 6: 0, 7: 0x166, 8: 0x16A, 9: 0x1A2, 10: 0x8F, 11: 0, 12: 0xF2, 13: 0x107, 14: 0x10A, 15: 0x136, 16: 0x133, 17: 0x18D, 18: 0x148, 19: 0x1D5, 20..23: 0x148 |

Names of the weapon categories were not resolved; use the table, not guesses about meaning. [H tables]

Equip pose set-up `0x517100` (`edi = state`, `esi = worm`; entered from SetState state 0x67 at 0x50F247): zeroes `+0x248`, `Reset()` the animator, `sprite = WormAimSprite(...)`, clears `+0x26C`, per-sprite arc clamps on `+0x24C` (0x1EE: [0x4000, 0xC000]; 0x1AE: [0x8000, 0xD999]; 0x1E2: depends on a game flag), quantizes `+0x24C` to 1/512 steps, then `Set(sprite, 0x8000)` when `+0x268 == 1`, otherwise `SetSprite(sprite)`. [H]

Holster table at `0x6A9218`: 63 rows of 12 bytes `{currentSprite, replacementSprite, flags}`, terminator key 0. Used by `0x516CA0` (`edi = worm`, stack `(currentSprite)`, `ret 4`) when entering idle states 0x65/0x88/0x8B (SetState 0x50F0E9): if the animator shows a "weapon ready" sprite it plays the replacement (flag 0x800000 = reverse playback, i.e. the weapon is put away) via `Reset()` + `SetSprite(repl)`. Rows with flags bit 0 are skipped, rows with flags 2 need `game.version >= 0x5F`. Also zeroes `+0x23C, +0x150, +0x240, +0x244, +0x15C`. [H]

### 3.3 RenderCrosshair = 0x51D680  [H]

Convention: `esi = worm`, no stack args, plain `ret`; preserves ebx/ebp/edi and does not modify esi. Only caller: 0x511D2A.

1. Return at once if `[+0x170] == 0` or `[+0x268] == 0`, or if state != 0x67 and `[game + team*0x51C + worm*0x9C + 0x4128] == 0`.
2. `ebp = [+0x26C]`, `edi = [+0x270]`; re-smooth with 0xCCCC/0x3333 (and handle a facing flip using the `+0x3D0..+0x3E0` cache).
3. `0x51CA90(worm, &a, &b, &c, &d)` (stack 5 args, esi-free) computes the crosshair offset: sin/cos tables `0x6A1860` / `0x6A1C60`, radius 14 px (also the weapon fire origin), angle mirrored with `0x20000 - a` when `[+0x1A8] < 0`.
4. State 0x68 (charging): `0x51CEF0(worm, power=[+0x248], ...)` draws the power indicator.
5. Team flag bit 4 (laser sight) plus conditions: `0x51FD90` and `0x51D9F0` draw the dotted aim line.
6. Final draw: `QueueSprite(ecx=game[+0x524], eax=y, layer=0x10000, x, sprite = [+0x10C] + 0x2000002 + (0x40000 or 0 by facing xor mirror), phase = (2*(angle + 2*(0x10000 - fade))) & 0xFFFF)`; x/y = worm position + offset + 0x8000. The crosshair strip is a full circle, so phase = 2 x angle. [H arithmetic]

Recipes:
```lua
-- hide / replace the crosshair (PX RenderCrosshair override)
local C
C = hookFunction("crosshair", 0x51D680, {regs = {"esi"}}, function(worm)
  if hideIt(worm) then return 0 end        -- original suppressed
  callHookOriginal(C)
  return 0
end)
-- free aim (e.g. MouseAim): write the target every frame; WA's easing then moves phase and crosshair
writeMemU32(worm + 0x24C, angle)           -- 0..0x10000
```
The input handler and 0x517100 clamp `+0x24C` to [0, 0x10000] (plus per-weapon arcs). Full 360 degrees is achieved by flipping `+0x1A8` and mirroring the angle, not by larger values. The DLL already patches the rope clamp (`CustomWeapons.cpp` ~1742). [M]

---

## 4. Animation and per-state sprites (items 1 and 5)

### 4.1 Animator object (`[worm+0x368]`, vtable 0x6640CC)  [H]

Fields: `+0x04` owner/bank pointer, `+0x08` current sprite id, `+0x0C` current phase, `+0x10` phase speed per tick (0 for static pose sprites), `+0x14` loop flag, `+0x18` divisor, `+0x1C` queue write index, `+0x20` queue read index, ring of 16 queued animations at `+0x24` with stride 0x14 `{phase, sprite, speed, loop, divisor}`.

| vt off | addr | method |
|---|---|---|
| +0x00 | 0x4F5700 | serializer |
| +0x04 | 0x4F5440 | destructor |
| +0x08 | 0x4F5AE0 | **Advance(ticks)** stack 1, ret 4. `phase += speed*ticks/divisor`; pops the queue when a non-looping clip ends. Called from the worm per-frame logic around 0x5159EC. |
| +0x0C | 0x4F5400 | **Get(int* sprite, int* phase)** ret 8 |
| +0x10 | 0x4F53F0 | **SetPhase(phase)** ret 4, only when `[anim+0x10] == 0` |
| +0x14 | 0x4F5420 | **Reset()** zeroes +0x08..+0x20 |
| +0x18 | 0x4F5BD0 | **Set(sprite, phase)** ret 8: enqueue. If nothing is playing (`[anim+0x08] & 0xFFFF == 0`) the head becomes current immediately. Speed/loop/divisor come from the sprite info via owner vtable `+0x18`. Sprite 0x8001D5 forces speed 8; 0x80012D multiplies the divisor by 4. |
| +0x1C | 0x4F5BB0 | **SetSprite(sprite)** = Set(sprite, 0) |

The idiom everywhere is `Reset()` then `SetSprite(id)` (= replace the animation). From Lua: `local vt = readMemU32(anim); callThiscall(readMemU32(vt+0x14), anim); callThiscall(readMemU32(vt+0x1C), anim, spriteId)`.

### 4.2 Where each state picks its sprite

All state-to-sprite assignment is in `SetState = 0x50E850` (vtable `+0x38`): entry jump table `[(state-0x64)*4 + 0x50F484]`, common tail at 0x50F308 mirrors the state to `GS.Info.Teams[].Worms[].State`, resets `+0x78 = 0xFEB8`, `+0x80 = 0x3AE1`, `+0x58 = 0x10000` (0x50ECB8) and resets the `game[+0x5DC]` counter (except for state 0x74). Per-frame logic per state is `0x515650` (jump `[(state-0x65)*4 + 0x516674]` at 0x515D9B; settle table 0x51671C). `0x515650` is stdcall with one stack arg (worm), returns in EAX (tested by the msg-2 handler at 0x511ED6). [H]

| state | PX name | SetState entry | animator set-up (always `Reset()` first) |
|---|---|---|---|
| 0x64 | not placed | tail only | none, worm not drawn |
| 0x65, 0x88, 0x8B | IDLE | 0x50F0D7 | holster table via `0x516CA0(oldSprite)` |
| 0x66 | WALKING | 0x50F0FB | SetSprite(0x89) wwalk |
| 0x67 | AIMING | 0x50F241 | `0x517100`: weapon aim sprite (0x51C060) |
| 0x68 | SETPOWER | 0x50F256 | keeps the aim pose |
| 0x69, 0x8A | FIRED | 0x50F26E | `0x517850`: weapon fire pose (0x19F, 0x17A, 0x118, 0x173, 0x177/0x16D, 0x1A5, 0x14B, 0x222...) |
| 0x6A | FIRECONT | 0x50F284 | `0x517F00` |
| 0x6B / 0x6C | repeat fire / punch | 0x50F296 / 0x50F2AD | `0x5181D0` / `0x518340` |
| 0x6D | kamikaze | 0x50F2B8 | `0x518A50` |
| 0x6E | drill | 0x50F2D5 | `0x5186A0` (0x169) |
| 0x6F | TELEPORTING | 0x50F2E0 | `0x5196D0` |
| 0x70 | SHOOTINGROPE | 0x50F2C1 | `0x519D80` (rope aim 0x21C) |
| 0x71 | blowtorch | 0x50EDE0 | `0x51A7B0` (0x8C) |
| 0x72 | battle axe | 0x50F2E9 | SetSprite(0x190) waxelk2 |
| 0x73, 0x80 | AFTERROPE / FLYING2 | 0x50EE34 | SetSprite(0x94) wroll; clears `[+0x8C]` |
| 0x74 | control weapon (L) | 0x50F2CC | `0x51A750` |
| 0x75 | suicide bomber (M) | 0x50EDEC | SetSprite(0x177) |
| 0x76 | poing (M) | 0x50F021 | SetSprite(0x124) wtwang; `0x53F320` crosshair sprite 3 |
| 0x77 | JUMPPREPARE | 0x50EEA6 | SetSprite(0x10D) wjump |
| 0x78 | JETPACK | 0x50EEE8 | `0x513980` init; flames 0xAB/0xAC drawn by 0x513A90; per-frame 0x513C50 |
| 0x79 | JUMP | 0x50EEF4 | 0x117 wbackflp if `[+0x2A0] != 0`, else 0x1FC wflyup |
| 0x7A | landing | 0x50EF98 | 0x121 (after parachute), 0x181, 0x110 wland1 / 0x113 wland2 by vy |
| 0x7B | ROPING | 0x50EDC6 | `0x519E50` (0x93 wbatrope) |
| 0x7C | BUNGEE | 0x50EDB8 | `0x51A3B0` (0x92) |
| 0x7D | PARACHUTE | 0x50EDD2 | `0x51A710` |
| 0x7E | falling | 0x50EE82 | SetSprite(0x1FE) wfall |
| 0x7F | SLIDING | 0x50EE5E | SetSprite(0x201) wslide |
| 0x81, 0x89 | FLYING / POWERFLY | 0x50EE10 | SetSprite(0x95) wfly1 |
| 0x82 | DEATH | 0x50F1D6 | SetSprite(0x1FA) wdie; speed zeroed; `[+0x48] = 1` |
| 0x83 | (unnamed) | 0x50F219 | SetSprite(0x280); `[+0x34] = 2` |
| 0x84, 0x87 | DEAD | tail only | none |
| 0x85 | SINKING | 0x50F11F | SetSprite(0x273 if old state 0x86 else 0x280); `[+0x34] = 0x400000` |
| 0x86 | FROZEN | 0x50F0C4 | `0x516B40` |

Full numeric table and evidence in `worm_states.md` (ROPING is 0x7B in this binary, 0x7C is the bungee spring).

### 4.3 Overriding animation from Lua

- Persistent per-state sprite: use the GetWormDrawParams hook of section 2.5 and rewrite sprite/phase for the wanted `[worm+0x44]`. No animator state is touched, so nothing leaks when the state ends.
- One-shot at state entry: SetState is `thiscall(ecx=worm, stack newState)`, `ret 4`.
  ```lua
  local S
  S = hookFunction("setstate", 0x50E850, {regs = {"ecx"}, nstack = 1}, function(worm, st)
    callHookOriginal(S)                                    -- engine picks its sprite
    if st == MY_STATE then
      local an = readMemU32(worm + 0x368); local vt = readMemU32(an)
      callThiscall(readMemU32(vt + 0x14), an)              -- Reset
      callThiscall(readMemU32(vt + 0x1C), an, MY_SPRITE)   -- SetSprite
    end
    return nil
  end)
  ```
  The DLL vtable callback `CTaskWorm_RegisterCallback_vtable38` runs BEFORE the original, so use it only for pre-hooks or to block a state change.

---

## 5. Collision, ground check, hovering (item 3)

### 5.1 Physics tick 0x4FCDF0  [H]

Per object per frame, called from msg 3 (before the draw block). Stdcall, stack args `(world/physics context, object, frameOffset)`, `ret 0xC` (inside the function ebp = world, ebx = object; `world[+0x240]` = game pointer). Skips the object when `[+0x3C] == 0` (not IsMaterial) or `[+0x48] != 0`.

1. `0x4FBC30` (esi=this, edi=world): pre-step.
2. Clear `[+0xB0]` (Sinking), `[+0xB4]`, `[+0xB8]` (InMidAir); old `[+0xB0]` kept in edi.
3. **Water test `0x4FDE20`** (esi = this, stack `(world, flag)`, `ret 8`). Needs `[+0x34] & 0x400000` and `(short)[+0x8A] > [world+0x228]` (pixel Y below the water surface). Then either skim (calls vtable `+0x34` OnSkim when `|vx|*[+0xA8] > 3|vy|`, `|vy| < 8px`, `|vx| > 6px` and no terrain at the surface point via `0x4FB9A0`) or sink: `vx,vy *= [+0x54]`, `vy += 0x4CCC`, `[+0xB0] = 1`. Returns nonzero only when the object was handled as sinking.
4. If 0x4FDE20 returned 0: **gravity `0x4FC280`** (ecx = this, eax = world): `if [+0xBC] { vy += [world+0x22C] * [+0x60] >> 16; [+0xB8] = 1 }` (only when the added amount is nonzero).
5. **OnSink edge-detect** at 0x4FCEAC: `if ([+0xB0] != oldB0) vtable+0x30()`. It fires on entering water and also when the flag drops back to 0.
6. If `[+0xBC]`: `0x4FD360`, `0x4FD4C0` (-> vtable `+0x3C` when it returns true), `speed *= [+0x78]`, then up to 10 sub-steps `0x4FD640(this, &t, 0)` (-> vtable `+0x24(obj)` on a hit).
7. **Terrain / object collision loop** (0x4FD081..0x4FD0C1, 2 iterations): `0x4FBDC0` (esi = this, stack `(world, &t, &rem)`) sweeps the position along the speed vector against the landscape/objects and returns the thing hit (eax) with the collision type in a stack local; then `vtable+0x20(obj, type)` = **Collide**. Base Collide `0x4FFED0` calls `obj->vtable+0x1C` (**Reflect**, on the OTHER object) and, if not consumed, bounces through `0x4FF490` (types 1/3 floor/ceiling use `+0x70` and `+0x74`; types 2/4 walls use `+0x6C` and `+0x74`).
8. `0x4FCD60` spin update then `[+0x8C] += [+0x98]`.
9. Version >= 0xE0: if `[+0x34] & 0x400000`, not sinking, and pixel Y >= `[game+0x5E4]`: `[+0xB0] = 1`, Y snapped to that line, **vtable `+0x30` OnSink** (0x4FD12B).

Worm Collide `0x50D9A0` (vtable `+0x20`): when config `[cfg+0xD9B4] == 0` (normal) it tail-calls `0x50DC00` (`eax = worm`, stack `(obj, type)`, `ret 8`). `0x50DC00` is the worm ground/wall response: calls base Collide (0x4FFED0) at 0x50DC60 and 0x50E3CC, sets SetState(0x7A) landing when the old state is 0x79/0x7D/0x7E (0x50DD69), SetState(0x80/0x76 ...) in other branches, and handles flying states 0x7F/0x81/0x89 (0x50E3D4). When `[cfg+0xD9B4] != 0` it forces `+0x6C = +0x70 = cfg value`, handles states 0x79/0x7D/0x6E/0x6C separately and logs the hit in a table at 0x774320 (stride 0xC `{this, obj, frameNo}`). [H flow, M the many-branch semantics of 0x50DC00]

### 5.2 Physics fields  [H unless noted]

| off | meaning |
|---|---|
| +0x34 | flags; 0x400000 = water-interacting |
| +0x3C | IsMaterial (0 => skipped by the tick) |
| +0x44 | state (worm) |
| +0x48 | dead/disabled; nonzero => skipped |
| +0x4C | weight (0x4FF720 exchange, 0x500090 force) |
| +0x54 | sink speed factor |
| +0x58 | per-frame speed multiplier (1.0) |
| +0x60 | GravityFactor (multiplies `world+0x22C`) |
| +0x6C / +0x70 / +0x74 | wall / floor-ceiling restitution / tangential friction (worm: 0.6 / 0 / -) |
| +0x78 | damping per frame (0xFEB8), applied only while `+0xBC` is set |
| +0x84 / +0x88 | PosX / PosY (16.16; `(short)[+0x8A]` = pixel Y) |
| +0x8C / +0x98 | rotation / spin |
| +0x90 / +0x94 | SpeedX / SpeedY |
| +0xA8 | skim factor (worm 0x20000) |
| +0xAC | stopped counter |
| +0xB0 / +0xB8 | Sinking / InMidAir (cleared at the start of each tick) |
| +0xBC | gravity+damping active flag (0 => no gravity, no damping, no sub-steps) |

### 5.3 Hover recipes (untested)

1. Cancel gravity: `writeMemU32(worm + 0x60, 0)` each frame (GravityFactor). The SetState tail only resets `+0x78/+0x80/+0x58`, so `+0x60` should persist [M]. Alternatively hook `0x4FC280` (`eax = world`, `ecx = this`, plain `ret`) and skip the original for hover worms.
2. Counter gravity instead: add `hoverForce` to `[+0x94]` from a per-frame hook.
3. Do not collide: `CTaskWorm_RegisterCallback_vtable20(function(worm, obj, ctype) if hovering(worm) then return 1 end return 0 end)`. A nonzero return suppresses 0x50D9A0 and returns 0 to the tick. The loop is bounded by 2 iterations, and the position was already advanced by the sweep. Or equivalently:
   ```lua
   local K
   K = hookFunction("wormcollide", 0x50D9A0, {regs = {"ecx"}, nstack = 2}, function(worm, obj, ctype)
     if hovering(worm) then return 0 end
     return callHookOriginal(K)
   end)
   ```
4. Keep the state in a flying class (0x81 or 0x78) while hovering so 0x50DC00 never reaches the 0x7A landing branch.

Ground-check primitive: `0x4FB9A0` (eax = this, stack `(world, x16.16, y16.16)`, `ret 0xC`) forwards to the landscape probe `0x4FB9D0` and tells whether the point is blocked. [M] A cheap "supported" test after the tick is `readMemU32(worm + 0xB8) == 0` (InMidAir not set, because gravity writes it each tick). [M]

---

## 6. OnSink and the water hook (item 4)

- `OnSink` = vtable `+0x30` = `0x500380`. Thiscall, `ecx = this`, no args, plain `ret`, base implementation shared by worm, mine, oildrum, crate. It only plays the Splash sound (id 0x39 = 57) at volume `(|vx|+|vy|)/5 + 0x8000`. It does not change state. Drowning comes from the Sinking flag `[+0xB0]` that the water test sets (0x4FDF30 writes `[+0xB0] = 1`) and from SetState 0x85 (SINKING), which bumps `game[+0x7374]`.
- Callers: tick edge-detect `0x4FCEAC`, map-bottom path `0x4FD12B`, and `0x50ADDF` (another task type). All use the object's vtable, so a per-class vtable hook sees every one.
- Cleanest "worm touched water" hook:
  ```lua
  CTaskWorm_RegisterCallback_vtable30(function(worm)
    if readMemU32(worm + 0xB0) ~= 0 then        -- 1 = entering water (0 = leaving)
      -- custom effect here
    end
    return 0                                     -- 0 keeps the splash sound; nonzero silences it
  end)
  ```
  At callback time the engine has already damped the speed and set the Sinking flag, and Y is at or below the waterline.
- Raw function variant for all classes: `hookFunction("onsink", 0x500380, {regs = {"ecx"}}, function(this) ... callHookOriginal(H) end)`; filter worms with `readMemU32(this + 0x20) == 0x12`.
- OnSkim (vtable `+0x34`, worm 0x50D3B0) is the "skipped over the surface" event: Splish sound and SetState(0x81/0x89).
- Water data: `[world+0x228]` = surface pixel Y used by the tick; `[game+0x5E4]` = bottom line used by the version >= 0xE0 path. `[game+0x24]` is the config block: `+0xD778` version, `+0xD9B1` scheme byte, `+0xD9B4` bounce flag. [M] on the relation between the two Y levels (`[ebp+0x240]` in the tick equals the game pointer).

---

## 7. Worm struct offsets (CTaskWorm)

Common: `+0x00` vtable, `+0x20` type byte (0x12 worm, 8 mine, 0x1E oildrum), `+0x2C` game ptr (`[game+0x24]` = config, `[game+0x510]` = weapon table, `[game+0x524]` = draw queue), `+0x44` state, `+0x84/+0x88` pos, `+0x90/+0x94` speed (rest in 5.2).

Worm: `+0xFC` team idx, `+0x100` worm idx (per-worm game data at `game + team*0x51C + worm*0x9C`, health `+0x40EC`, visible/active word `+0x4128`), `+0x104` turn-active flag, `+0x108` flag, `+0x140` knocked-out latch, `+0x148` draw flag, `+0x158` draw-layer slot, `+0x164` idle timer, `+0x170/+0x174` weapon/ammo, `+0x178..+0x188` health-display animation and damage accumulator, `+0x1A8` facing, `+0x1AC` turn-around sign, `+0x1D4/+0x1D8/+0x1DC/+0x1E0` held up/down/left/right (cleared every frame), `+0x1F0/+0x1F4` walk bob, `+0x220..+0x238` jetpack fuel/thrust, `+0x248` power, `+0x24C` aim target, `+0x268` aim mode, `+0x26C` crosshair fade, `+0x270` smoothed aim, `+0x284/+0x288/+0x28C` shot counters/active, `+0x290..+0x2D4` fire/burst state, `+0x2BC/+0x2C0/+0x2C4` weapon options, `+0x2E0..+0x2EC` target click, `+0x330` pending jump, `+0x338/+0x339` aim swap / power oscillation, `+0x368` animator, `+0x36C` weapon struct, `+0x3D0..+0x3E0` crosshair cache. More in `worm_misc.md` and `worm_input.md`.

---

## 8. PX method to WA hook map

| PX | WA target | hook with |
|---|---|---|
| RenderWorm | 0x50FCD0 (eax=worm) or 0x512E80 (draw params) | `hookFunction` (2.5) |
| RenderCrosshair | 0x51D680 (esi=worm) | `hookFunction` (3.3) |
| Collide(obj,type) | vtable `+0x20` | `CTaskWorm_RegisterCallback_vtable20` |
| Reflect(obj,type) | vtable `+0x1C` | `..._vtable1C` |
| OnSink | vtable `+0x30` (not 0x2C) | `..._vtable30` |
| SetState | vtable `+0x38` | `..._vtable38` (pre) or `hookFunction` on 0x50E850 (post) |
| TakeDamage | no single slot. Explosion/damage message handler 0x511F8C (msgs 28/118) and damage accumulation into `+0x188` at 0x50E08D, 0x50E0DB, 0x50F5B8, ... | hook HandleMessage `+0x08` or the sites (not analysed here) |
| FireFinal | candidate 0x51C390 (per-shot fire, called by 0x51B520 and the burst manager 0x51F1C0) | `hookFunction`; [L] not verified |

## 9. Confidence summary

- [H] Addresses, calling conventions and call order of RenderWorm, GetWormDrawParams, QueueSprite, RenderCrosshair; animator interface; vtable offsets; physics-tick order; OnSink edge detection; per-state SetState entry sprites.
- [M] Meaning of render flags 0x200000/0x400000 and worm `+0x148`; roles of vtable `+0x24/+0x28/+0x3C/+0x40/+0x44`; sprite-id triple rule (`+0x1AC`); relation between `[world+0x228]` and `[game+0x5E4]`; 0x50DC00 branch details.
- [L] Layer ordering semantics; names for states 0x74-0x76 and 0x83; FireFinal address.
- Not traced: the display object's draw method (phase to frame rounding), HUD functions 0x50FB50/0x510260/0x50F900/0x50FDC0, rope overlay 0x5197D0, TakeDamage internals.
- Hover and all Lua recipes are untested (game never run). Before relying on implicit-register arguments (0x512E80 and 0x51D680 use esi, 0x50FCD0 uses eax) print `hookCurrentRegs()` once inside the callback.
- WormAimSprite rows in 3.2 were transcribed from the jump tables ([H] for the dispatch, [M] for any single row because the byte-indexed sub-tables were only partly expanded).
