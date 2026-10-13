# pkg_script_live_hp

Now let me summarize my findings. I'll create the audit report based on what I've verified:

## Findings

**script_live_hp package:**

- `px_pipeline/testout/lua/script_live_hp/livehp.lua:10` - **medium** - The transpiled script reads `self.TargHealth` from the worm proxy field (0x17C offset, supported by pxrt_engine.lua:205), but immediately overwrites it with `GetWormHealth`. In PX, `TargHealth` is the "pending" health value that the engine writes before damage animation, while the Info method reads the authoritative value. The override is correct: it refreshes TargHealth from the engine on every Message, ensuring the script field matches WA's state when a message arrives.

**utility_hangglider (hand-written Lua port vs PX transpiled vs PX source):**

- `jelly/packages/utility_hangglider/0.0.1/main.lua:232-236` vs `paratest.pxc:124-140` - **high** - **Control flow differs**: PX runs `Anim->Reset(); Anim->SetAnimEx(136, 0.0)` to hide the worm sprite while gliding (paratest.pxc:139-140). The Lua port omits this entirely. Without hiding the worm sprite, the default parachute worm will render under the glider sprite. `CSpriteAnim::Reset` and `CSpriteAnim::SetAnimEx(sindex, frame)` are **not implemented** in pxrt (pxrt_e_classes.lua:180 stubs `CWorm::SetAnimEx` to return 0; CSpriteAnim has no Reset method). **Fix**: Document that the Lua port cannot hide the worm sprite because pxrt stubs SetAnimEx. The weapon-scoped sprite overrides (main.lua:357-362) blank sprites 287/288 to work around this, but sprite 136 (the invisible anim PX used) is not overridden.

- `jelly/packages/utility_hangglider/0.0.1/main.lua:238-248` vs `paratest.pxc:271-277` - **medium** - **TraceMask collision detection removed**: PX called `TraceMask(Owner, Owner->ColMask, ...)` to detect terrain ahead and call `Owner->SetState(WS_AFTERROPE)` to end the glide (paratest.pxc:274-276). The Lua port replaces this with a position-delta heuristic (main.lua:242-248) that detects when the worm is blocked. TraceMask exists in pxrt (pxrt_e_soft.lua:344 as `_TraceMask`), but the Lua port uses a different approach. **Behavior**: PX ended the glide preemptively; the port ends it after the worm is already stuck. **Fix**: The port's heuristic works but changes glider behavior near obstacles.

- `jelly/packages/utility_hangglider/0.0.1/main.lua:212-237` vs `paratest.pxc:94-166` - **low** - **Think() structure differs**: PX ran CWormGlider::Think as a script object method inside a Message override (M_FRAME). The Lua port runs `think(worm, g)` as a plain function inside a vtable8 callback. Both are frame callbacks, but the PX version had access to the full CWorm proxy (`self.Owner`), while the port reads raw memory offsets (`rd(worm + 0x44)`). **Impact**: Functionally equivalent for the fields used, but the port bypasses pxrt's field proxy layer.

- `jelly/packages/utility_hangglider/0.0.1/main.lua:299-317` vs `paratest.pxc:284-303` - **high** - **Render() uses different drawing APIs**: PX called `Owner->AddSpriteEx(z, x, y, sprite, frame, rotation, scale)` (paratest.pxc:290, 294) with rotation in radians. The Lua port calls `drawSpriteLocal(y, z, x, sprite, frame)` (main.lua:316), which is a DLL-provided function that does **not** accept rotation/scale parameters. pxrt implements `CObject::AddSpriteEx` (pxrt_e_classes.lua:73-75) as `E.drawSprite(z, x, y, sprite, frame, rot, scale)`, forwarding to pxrt_e_quads.lua's quad renderer. The **hand-written port bypasses pxrt entirely** and uses pre-rotated sprite sheets (wgldrot1.png, wgldrot2.png: 58 discrete angles) instead of runtime rotation. **Fix**: The port is correct for wkJellyWorm's limitations (no arbitrary sprite rotation in the base API), but it cannot run under pxrt because it uses `drawSpriteLocal`, `registerCustomSprite`, and `CTaskWorm_RegisterCallback_vtable8` — all DLL APIs, not pxrt functions.

- `jelly/packages/utility_hangglider/0.0.1/main.lua:281-296` vs `paratest.pxc:305-348` - **medium** - **Move() input handling**: PX received M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT messages and modified ParaSpX/ParaSpY or GliderAng directly (paratest.pxc:307-347). The Lua port does the same (main.lua:281-296) but in a vtable8 callback filtering those message types. Both approaches work; PX filtered via a Message override, the port filters in the callback. **Impact**: Equivalent.

- `testout/lua/utility_hangglider/paratest.lua:71` vs `paratest.pxc:106` - **low** - **Transpiled CurWeapon->CheckName**: The transpiled code calls `mc(self.Owner.CurWeapon, "CheckName", "Hang-Glider")`, which invokes pxrt's CWeapon::CheckName (pxrt_e_classes.lua:537-552). This normalizes the weapon name and compares it. The Lua port bypasses this and directly compares weapon IDs via `getWormWeaponId` (main.lua:217-218). **Impact**: The port is faster and simpler; the transpiled version is correct but pays for method call overhead.

- `testout/lua/utility_hangglider/paratest.lua:152` vs `paratest.pxc:274` - **medium** - **Transpiled TraceMask call**: The transpiled code calls `__G__.TraceMask(...)` expecting a global function from utils (paratest.lua:152). pxrt implements TraceMask via `BF._TraceMask` (pxrt_e_soft.lua:344), but it must be registered as a script-visible function. If utils does not export TraceMask to the global table, this call will fail at runtime. **Fix**: Verify that the utils library's TraceMask shim is loaded and accessible.

- `testout/lua/utility_hangglider/paratest.lua:86` vs `paratest.pxc:133` - **low** - **Sound API**: PX calls `hangopen->Play(vol, pan, false)` (paratest.pxc:133). The transpiled code calls `mc(__G__.hangopen, "Play", self.vol, self.pan, 0)` (paratest.lua:86). pxrt does not implement CSoundFile methods; sound playback will be silent. **Fix**: Implement CSoundFile::Play or document that PX scripts calling sound methods are silent under pxrt.

## Notes

- **utility_hangglider is NOT auditable under pxrt**: The task stated that utility_hangglider is a hand-written Lua port in `jelly/packages/utility_hangglider/0.0.1/main.lua` and is NOT run by pxrt. I compared it to the transpiled version and PX source for controls and physics. The port bypasses pxrt and calls DLL APIs directly (`drawSpriteLocal`, `registerCustomSprite`, `CTaskWorm_RegisterCallback_vtable8`, `playSoundLocal`, `getWormWeaponId`, `readMemInt`, `writeMemInt`). These functions are not part of pxrt's API. The port uses pre-rotated sprite sheets instead of `AddSpriteEx` rotation because wkJellyWorm's base API lacks sprite rotation.

- **script_live_hp is minimal**: The package is 9 lines of PX (livehp.pxc) and transpiles to 13 lines of Lua. It overrides `CWorm::Message` to refresh `TargHealth` from `GetWormHealth` on every message. All runtime features it uses are implemented: `P:override`, `GetWormHealth`, `WormTeam`, `WormNumber`, `TargHealth` field. No stubs or missing features.

- **CSpriteAnim methods are stubbed**: `CWorm::SetAnimEx` (pxrt_e_classes.lua:180) returns 0. PX scripts that call `Anim->SetAnimEx(sprite, frame)` or `Anim->Reset()` to control worm animation will have no effect. The hangglider PX source relies on this to hide the worm sprite while gliding.

- **TraceMask availability**: The transpiled hangglider calls `__G__.TraceMask`, which requires the utils library to export it. pxrt implements `_TraceMask` (pxrt_e_soft.lua:344) but does not automatically expose it as a global. The utils library (pxl) likely wraps this.

- **Sound playback is silent**: pxrt does not implement CSoundFile methods. Scripts calling `sound->Play(...)` will silently fail (no error, no sound).
