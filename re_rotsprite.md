# WA 3.8.1 - rotated / scaled sprite draw: reverse-engineering notes

Binary: `C:\Program Files (x86)\by Decepticon\Worms Armageddon\WA.exe`, 32-bit, base 0x400000, static analysis only (never launched).
Everything marked UNVERIFIED was not confirmed by running the game.

## 1. Verdict

WA has NO native "draw sprite with arbitrary rotation / scale / alpha" call.
The render queue only knows these sprite-related capabilities:

* rotation = **pre-rotated frame banks** selected by a 16-bit phase (full circle = 0x10000). A sprite stores a set of frames; the draw call picks one by phase. With flag 0x1000000 the frame set only has to cover one quadrant and the engine adds 90-degree rotations/mirrors (orientation code in the high word of the DrawBitmapOnBitmap mode).
* 90-degree rotations and mirrors: flags 0x1000000 (phase to quadrant), 0x40000, 0x80000 (see section 6).
* scale: none for sprites. The only scale in the engine is perspective parallax of POSITIONS: `FixedDiv(0x1000000, z + 0x1000000)` inside the position transform 0x542BA0 (type 6 / type 3 items). The sprite bitmap size is never changed.
* alpha: none. Only (a) checkerboard stipple (flags 0x8000000 / 0x10000000) and (b) palette remap-table blends (flags 0x200000 / 0x4000000). Screen is 8bpp palette-indexed, colour key = index 0.

Feasible alternatives, best first:

* **A. Frame banks (recommended, works today in pure Lua)**: author the sprite with N pre-rotated frames (N = 32/64/128 ... or a quadrant with flag 0x1000000), call the existing `drawSpriteLocal(y, layer, x, sprite, phase)` with `phase = angle/2pi*65536`. Scale and alpha: also pre-baked banks (scale bank per frame set, remap/stipple flags for alpha).
* **D. DLL-rotated surface + native type-1/2 blit**: DLL software-rotates the source frame into its own 8bpp buffer each frame, then enqueues it with the native `0x542170` (global) / `0x542200` (local) "blit a rect of an arbitrary BitmapImage" function. Arbitrary angle, scale, stipple alpha. Needs a BitmapImage-compatible struct (section 8D). Moderate effort, UNVERIFIED.
* **B. Type-3 object callback**: the queue dispatcher supports a "call object->vtbl[2](bitmap,x,y,p,q)" item (type 3). WA never enqueues it itself (no enqueue function exists), but a DLL can write such an item by hand and rasterise anything straight into the screen bitmap. Needs C++ (Lua cannot make native callbacks). UNVERIFIED.

## 2. Key addresses

| Address | What | Convention |
|---|---|---|
| 0x541FE0 | enqueue sprite, GLOBAL (type 4) | usercall: ecx = Q (queue), eax = posy (16.16); stack: layer, posx, sprite, frame; `ret 0x10` |
| 0x542060 | enqueue sprite, LOCAL (type 5) | same as above (this is what `drawSpriteLocal` calls) |
| 0x542170 | enqueue bitmap-rect blit, GLOBAL (type 1) | ecx = Q, edx = y (16.16); stack: layer, x, srcBitmap*, y1, x2, y2, mode; `ret 0x1C` (item x1 forced to 0) |
| 0x542200 | enqueue bitmap-rect blit, LOCAL (type 2) | ecx = Q; 6 stack args (`ret 0x18`), item size 0x34, layout UNVERIFIED |
| 0x5420E0 | enqueue type 6 (perspective sprite) | item size 0x24 |
| 0x5422A0 | enqueue type 0xE | item size 0x24; ecx = Q, eax = y; 2 stack args (`ret 8`) |
| 0x541F40 / 0x541FBB | enqueue type 0 (filled rect) | item size 0x20 |
| 0x541E50 / 0x541ED0 / 0x541D60 / 0x541DD0 | enqueue types 9 / 0xB / 0xD / 8 | |
| 0x542350 | queue dispatcher (sort + draw) | eax = Q; stack: ddDisplay + 1 more arg, `ret 8`; qsort 0x5D7890 with comparator 0x542330 |
| 0x542330 | qsort comparator | `A.layer - B.layer` on item pointers (unstable: ties in arbitrary order) |
| 0x542BA0 | position transform with z | thiscall ecx = ddDisplay; (x, y, z, &sx, &sy, &scale), returns 0 if culled |
| 0x542B10 | 2D position transform (camera) | used by type 5 / 0xA |
| 0x56B080 | DDDisplay::DrawSprite (vtbl +0x4C) | thiscall ecx = ddDisplay; stack (x16.16, y16.16, spriteIdWithFlags, phase); `ret 0x10` |
| 0x56B660 | DDDisplay::DrawBitmapRect (vtbl +0x50) | thiscall; 8 stack args: x, y (16.16), srcBitmap*, x1, y1, x2, y2, mode; `ret 0x20`; blit is CENTRED on (x,y) |
| 0x56B7C0 | type-3 caller (vtbl +0x54) | thiscall; 5 stack args: sx, sy (16.16), obj*, p, q; `ret 0x14` |
| 0x5237C0 -> 0x4FAD30 | GetSpriteFrame (vtbl +0x84) | thiscall; (id16, phase, 7 out pointers), returns source BitmapImage* or 0 |
| 0x56A370 | screen prep (called before blits) | |
| 0x4F6910 | DrawBitmapOnBitmap | usercall esi = dest BitmapImage*, 9 stack args, `ret 0x24` |
| 0x5B3501 | FixedDiv | |
| 0x575730 | atan2 -> 16-bit phase | |
| 0x533DC0 | per-frame render function; queue reset at 0x533F85 (`[Q]=0x10000`, count=0), dispatch call at 0x5340AF | |
| 0x569C10 | DDDisplay constructor; vtable at 0x66A218 | |

## 3. Queue object Q

`Q = *(DWORD*)(G + 0x524)` where `G` = game global (`Game::getAddrGameGlobal()`), total size 0x12008.

```
+0x00000  DWORD  bytes_left     (reset to 0x10000 each frame)
+0x00004  ...    item arena, 0x10000 bytes, items are carved from the TOP downward
+0x10004  DWORD  count          (max 0x800)
+0x10008  DWORD  ptr[0x800]     item pointers (sorted in place by the dispatcher)
```

Allocator (identical in every enqueue function):
```
if (count >= 0x800) fail;
left = [Q] - size; if (left < 0) fail;
[Q] = left;
item = Q + left + 4;
[Q + 0x10008 + count*4] = item;  [Q + 0x10004] = count + 1;
```
The queue is reset at the start of the frame render (0x533F85) and drawn once at 0x5340AF. Items MUST be enqueued in that window (the DLL already does it from its render hook).

Dispatcher: qsort ascending by `item[4]` (layer), then iterates from the LAST index down to 0. So **highest layer is drawn first, lowest layer is drawn last = on top**. Equal layers: order undefined.

## 4. Item layouts (every item starts `[0]=type, [4]=layer`)

| type | size | layout / dispatch |
|---|---|---|
| 0 | 0x20 | filled rect: [8]=colour, [0xC],[0x10],[0x14],[0x18] corners, [0x1C] z; vtbl +0x48 |
| 1 | 0x28 | bitmap rect, global: [8]=x, [0xC]=y, [0x10]=BitmapImage*, [0x14]=x1 (0), [0x18]=y1, [0x1C]=x2, [0x20]=y2, [0x24]=mode; vtbl +0x50 |
| 2 | 0x34 | bitmap rect, local (camera transform + clip); vtbl +0x50 |
| 3 | 0x24 (needed) | object callback: [8]=x, [0xC]=y, [0x10]=z (16.16, world, camera-transformed by 0x542BA0), [0x14]=unused, [0x18]=object*, [0x1C]=p, [0x20]=q; calls `obj->vtbl[2](screenBitmap, xpx, ypx, p, q)` through vtbl +0x54. NO native enqueue exists. |
| 4 | 0x18 | sprite, GLOBAL: [8]=posx (&0xFFFF0000), [0xC]=posy (&0xFFFF0000), [0x10]=sprite id with flags, [0x14]=frame/phase; vtbl +0x4C (screen-centre-relative) |
| 5 | 0x18 | sprite, LOCAL: same fields; position goes through 0x542B10 (world minus camera), then vtbl +0x4C |
| 6 | 0x24 | perspective sprite (uses 0x542BA0 with z) |
| 7..14 | | lines/polylines/other; not needed here (type 9 = polyline used for rope, types 8/0xB/0xD/0xE various) |

Note: positions are stored with the low 16 bits cleared (`& 0xFFFF0000`), so sub-pixel positioning is impossible through these items.

## 5. DDDisplay vtable (0x66A218) - the relevant slots

```
+0x48 0x56B810  filled rect
+0x4C 0x56B080  DrawSprite(x, y, idFlags, phase)
+0x50 0x56B660  DrawBitmapRect(x, y, bmp, x1, y1, x2, y2, mode)
+0x54 0x56B7C0  DrawObject(sx, sy, obj, p, q)
+0x58 0x56C5A0  (type 0xE)
+0x84 0x5237C0  GetSpriteFrame(id16, phase, &W, &H, &x1, &y1, &x2, &y2, &?) -> BitmapImage*
```
Sprite table: `ddDisplay + 0x1008 + id*4` (second table +0x2008, third +0x3DD4); ids 1..0x3FF. Screen centre in pixels: `[dd+0x3560]`, `[dd+0x3564]`. Screen BitmapImage: `[dd+0x3d9c]`; clip rect in BitmapImage: +0x1C x1, +0x20 y1, +0x24 x2, +0x28 y2; data +8, bitdepth +0xC (8), stride +0x10.

GetSpriteFrame outputs (decoded from the caller 0x56B080): arg3 = cell width W, arg4 = cell height H, arg5/6/7/8 = x1/y1/x2/y2 of the non-empty rectangle inside the cell (blit width = x2-x1, height = y2-y1), arg9 = not decoded. Unmirrored placement:
```
dest_x = screenCentreX + (posx >> 16) - W/2 + x1
dest_y = screenCentreY + (posy >> 16) - H/2 + y1
```
(the sprite cell is centred on the position).

## 6. Sprite id flags (high 16 bits of the sprite argument) and phase

* low 16 bits = sprite id; `frame` argument = **phase** 0..0xFFFF = fraction of the whole frame set (NOT an index).
* 0x1000000: phase is a full-circle angle; `q = (phase*4 + 0x8000) >> 16 & 3` picks the quadrant, the remaining `(phase*4 + 0x8000) & 0xFFFF` is the phase within a quadrant frame set. Quadrant to DrawBitmapOnBitmap mode: q0 = 0x80001, q1 = 0xC0001, q2 = 0x00001 (default), q3 = 0x40001.
* 0x40000 / 0x80000: set bits 0x10000 / 0x20000 in the mode (mirror X / mirror Y).
* 0x800000: phase reversed (`0x10000 - phase`; for ids 0x1D5..0x1D7 also scaled by 8/9).
* 0x2000000: phase remap (x31/32 + 0x400, wrapped mod 0xF800).
* 0x200000 / 0x4000000: draw through a remap table (+0x4DF4 / +0x14DF4 in ddDisplay) = colour blend.
* 0x8000000 / 0x10000000: checkerboard stipple (the only "alpha"), parity 0 / 1.
* 0x400000: draw to secondary bitmap [dd+0x3DA4] first.
* In the existing DLL (`Sprites.cpp`): `toPhase`: value >= 256 = raw phase; non-integer = fraction*65536; integer < 256 = frame index (with the +0.25-bin offset).

Angle unit: 16-bit phase, full circle = 0x10000. `0x575730` is an atan2 returning that phase (existing callers feed it straight into the frame argument, e.g. aim dot 0x51CF9A, rope end 0x51999E).

## 7. Coordinates and layers

* positions: 16.16 fixed point. LOCAL (type 5) = world position minus camera, relative to screen centre; GLOBAL (type 4) = screen-centre-relative, no camera.
* layer: 16.16 too (`0x180000` = 24.0). DLL `toLayer` multiplies values < 256 by 65536. Lower layer = drawn later = in front.

## 8. Recipes

### 8A. Rotation with frame banks (Lua only, ready today)

```lua
-- angle in radians, any value. sprite must have a frame set that covers 360 degrees
-- (N pre-rotated frames), or 90 degrees if you OR in 0x1000000 (sprite | 0x1000000).
local TWO_PI = 2 * math.pi
function drawSpriteRot(x, y, layer, sprite, angleRad)
  local ph = math.floor((angleRad % TWO_PI) / TWO_PI * 65536) % 65536
  if ph < 256 then ph = 256 end        -- values < 256 are read as a frame INDEX by the DLL
  drawSpriteLocal(y, layer, x, sprite, ph)
end
-- quadrant-bank variant (frames only for 0..90 degrees, engine adds the 90-degree steps):
-- drawSpriteLocal(y, layer, x, sprite + 0x1000000, ph)   -- UNVERIFIED with the DLL's id range check
```
Pass `ph` as a raw integer. Scale = separate frame banks per scale level (sprite ids 851+ are free for custom sprites). Alpha = flags 0x8000000 / 0x10000000 (50% stipple) or a remap-table flag. This matches how the engine rotates everything (aim dot, rope end, projectiles).

### 8D. Arbitrary angle/scale via DLL-rotated surface + native type-1 blit (UNVERIFIED)

1. Per rotated sprite, the DLL software-rotates the frame rect (source: `GetSpriteFrame` vtbl +0x84, pixels at `src->data + y*stride + x`) into a DLL-owned 8bpp buffer `buf` (w*h bytes, index 0 stays transparent). Rotation = inverse mapping, nearest neighbour, scale folded into the same mapping.
2. Fake BitmapImage: only `+0x8 = data*`, `+0xC = 8` (bitdepth), `+0x10 = stride` were seen read from the SOURCE by 0x4F6910. Safest: allocate a real BitmapImage the same way WA does and fill its pixels. Keep the buffer alive until the frame has been dispatched.
3. Enqueue (centred on the position; mode 0 = colour-keyed, 0x8000000/0x10000000 = stipple, 0x200000 = remap):
```
callRegs(0x542170, {ecx = Q, edx = posy16},
         layer16, posx16, bufBitmap, 0 --[[y1]], w --[[x2]], h --[[y2]], mode)
```
Q = `readMem32(G + 0x524)`. The local (camera-relative) twin is 0x542200 (layout not decoded; alternatively subtract the camera yourself and use the global one).
Risk: the optional GL renderer hooks 0x4F6910 and may map bitmaps by pointer; use only with the software renderer or hook-aware code.

### 8B. Type-3 callback with a software rasteriser (C++, UNVERIFIED)

Item (0x24 bytes) written by hand, same allocator as section 3. WA calls `obj->vtbl[2]` thiscall, 4 stack args, callee cleans (`ret 0x10`). A C++ class with two dummy virtuals and then `Draw` as the third virtual compiles to exactly that on MSVC x86 (virtual members default to `__thiscall`).

```cpp
// sketch for a new DLL function drawSpriteRotLocal(posx,posy,layer,sprite,frame,angle,scale,alpha)
struct RotParams { int sprite; int frame; float angle; float scale; int alpha; };
struct RotDrawer {
    virtual void v0() {}
    virtual void v1() {}
    // WA: obj->vtbl[2](screenBitmap, xpx, ypx, p, q)   (xpx,ypx = pixel position, screen centre applied)
    virtual void Draw(Bitmap::BitmapImage* dst, int xpx, int ypx, RotParams* p, int /*q*/) {
        // 1. dst: data = *(BYTE**)((BYTE*)dst + 8), stride = *(int*)((BYTE*)dst + 0x10),
        //    clip = {+0x1C,+0x20,+0x24,+0x28} (x1,y1,x2,y2)
        // 2. source frame: GetSpriteFrame (ddDisplay vtbl +0x84) -> src bitmap + rect (section 5)
        // 3. for each dest pixel in the rotated bounding box: inverse-rotate/scale to the source,
        //    skip colour 0, apply alpha as checkerboard ((x+y)&1) or via remap table, write if inside clip
    }
};
static RotDrawer g_drawer;                         // vptr is its first dword

void drawSpriteRotLocal(int posx, int posy, int layer, int sprite, int frame,
                        float angle, float scale, int alpha) {
    DWORD G = Game::getAddrGameGlobal();
    BYTE* Q = *(BYTE**)(G + 0x524);
    int cnt = *(int*)(Q + 0x10004);
    if (cnt >= 0x800) return;
    int left = *(int*)Q - 0x24; if (left < 0) return;
    *(int*)Q = left;
    DWORD* it = (DWORD*)(Q + left + 4);
    *(DWORD**)(Q + 0x10008 + cnt * 4) = it;  *(int*)(Q + 0x10004) = cnt + 1;
    auto* prm = new RotParams{sprite, frame, angle, scale, alpha};   // free after the frame (ring buffer)
    it[0] = 3;  it[1] = toLayer(layer);
    it[2] = toFixed(posx) & 0xFFFF0000;  it[3] = toFixed(posy) & 0xFFFF0000;
    it[4] = 0;                                  // z = 0 -> scale 1.0 (perspective off)
    it[5] = 0;  it[6] = (DWORD)&g_drawer;  it[7] = (DWORD)prm;  it[8] = 0;
}
```
Checks needed in-game: (a) item [0x14] is really unused, (b) the pixel origin passed to Draw is the position (not top-left), (c) clipping fields, (d) GL renderer mode (writes to the 8bpp screen are bypassed when `EnableCustomRenderer` is on, so the callback output would not appear). Lua cannot do this because Lua cannot create a native vtable/callback.

### 8C. Hook of 0x56B080 (alternative, UNVERIFIED)

Hook DrawSprite (vtbl +0x4C, 0x56B080) and use a spare flag bit (candidates 0x20000000 / 0x40000000 / 0x80000000, not tested by 0x56B080) to look up a side table of {angle, scale, alpha} keyed by a token carried in the phase high bits. Heavier than 8B and the phase high bits may be consumed by GetSpriteFrame; not recommended.

## 9. Caveats

* Layer ties are unstable (qsort); use distinct layers for z-fighting-sensitive sprites.
* Items cap at 0x800 per frame and 0x10000 bytes of arena (about 2730 x 24-byte items).
* Position low 16 bits are cleared by every enqueue: whole-pixel positioning only.
* Sprite blits have no rotation anywhere in the 8bpp software path: 0x56AEA0 (remap), 0x56AEF0 (stipple), 0x56AFB0 / 0x56B000 (plain, via DrawBitmapOnBitmap).
* GL renderer (`EnableCustomRenderer`, default 0) hooks DrawBitmapOnBitmap; it has no rotation either.

## 10. Source files consulted

* `C:\Users\Admin\Projects\worms-modding-lab\sources\wkJellyWorm\src\Sprites.cpp` / `Sprites.h` (`callDrawSpriteLocal`, `toPhase`)
* `...\src\LuaNative.cpp` (callRegs, callThiscall, callStdcall, memAlloc, readMem/writeMem)
* `...\src\renderer\Bitmap.h` (BitmapImage layout), `Drawing.cpp`, `Renderer.cpp`
* disassembly scratch: `C:\Users\Admin\pxrt_dev\rs\` (lin.pkl, lin_*.asm, f_*.asm), tool scripts in `%LOCALAPPDATA%\Temp\d14.py`, `d21.py`
