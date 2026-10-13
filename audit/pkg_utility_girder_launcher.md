# pkg_utility_girder_launcher

Now I'll compile the comprehensive audit report based on my analysis of the utility_girder_launcher package.

## Findings

- `pxrt_e_classes.lua:359-361` - **high** - `CLandscape::Draw` is stubbed and logs "landscape Draw not implemented yet". The girder launcher calls `mc(K.GG.land, "Draw", bmp, x, y)` at line 203 to draw the girder bitmap onto terrain after impact. This is the core feature - girders should stick to landscape at impact angle. The runtime logs the call once but does nothing, so girders never appear on terrain. Fix: implement CLandscape::Draw to apply bitmap to WA terrain via DLL terrain manipulation functions.

- `pxrt_e_funcs.lua:312-336` - **high** - `CSoundFile` constructor and `Play` method exist but `playSoundLocal` host function may be nil. Line 19 creates `mgirderimpactsnd = new("CSoundFile", f)` and line 132 calls `Play(1.0, 0.0, 0)`. If `playSoundLocal` is unavailable, Play silently fails (pc() catches errors). No impact sound plays on girder collision. Fix: verify DLL exports playSoundLocal or log missing sound capability.

- `pxrt_e_classes.lua:76` - **medium** - `AddSpriteQ` (quad rendering) logs "unsupported" unless pxrt_e_quads.lua loads successfully. Utility_laser_pointer (required dependency) calls `AddSpriteQ` for laser sight at line 68 and 84 of laserray.lua. The girder launcher uses laser sight during aiming (line 85, M_DRAWQUEUE handler). Without quad support, the aiming laser is invisible. pxrt_e_quads.lua checks for `pxQuadSubmit` at line 15-18; if missing, AddSpriteQ stays inert. Fix: ensure DLL exports pxQuadSubmit or document that laser aiming visual is unavailable.

- `girder_launcher_script.lua:42-43` - **medium** - Creates `WormSprite` and `WeapSprite` objects (lines 42, 58) but runtime has no builtin class for these. They're from p_sprite_builder.pxc library (pxchunks.json line 23). Grep found no `BC.WormSprite` or `BC.WeapSprite` in runtime. These classes likely control weapon sprite animation on worms. Without them, `new("WormSprite", ...)` returns an inert table via missing class fallback. Weapon sprite doesn't animate during aiming. Fix: implement WormSprite/WeapSprite/WormAnimParams/WeapSpriteParams as inert classes or stub their registration logic.

- `girder_launcher_script.lua:85` - **medium** - Calls `__G__.MakeLaserRay(self, x, y, 2, ang, LaserLen)` from utility_laser_pointer dependency. MakeLaserRay generates quad-based laser beam. If AddSpriteQ is inert (finding #3), laser renders nothing. Secondary impact: aiming feedback is completely missing. Fix: tied to quad renderer availability.

- `girder_launcher_script.lua:94` - **low** - `__G__.Trace(parent, __G__.lasermask, x, y, ang, 5, alen, -1, ref(len))` traces laser collision. Trace is from utils.pxc library. If Trace is missing or collision detection unavailable, laser length calculation fails and `__G__.len` stays 0. MakeLaserRayF renders a zero-length laser (nothing visible). Not verified if Trace exists in runtime. Check: grep runtime for Trace implementation.

- `girder_launcher_script.lua:144-152` - **medium** - GirderDamage constructs `CMessageData`, sets params[0..6], and sends M_GUNEXP message (line 152). CMessageData is implemented (pxrt_e_structs.lua:102-107) with memory backing. M_GUNEXP constant exists (pxrt_e_consts.lua:17). Message dispatch via `mc(target, "Message", ...)` routes through live vtable at pxrt_e_classes.lua:127-133. This should work, but M_GUNEXP handler in WA engine may not recognize script-originated messages or may require different params layout. Damage/knockback may not apply. Verify: test if M_GUNEXP from scripts actually damages worms.

- `girder_launcher_script.lua:52` - **low** - `mc(self.weap, "CheckName", "Girder Launcher")` checks weapon name. CheckName is implemented at pxrt_e_classes.lua:537-552 with normalization and caching. Should work correctly if weapon registered with correct name. Potential issue: weapon registration uses display name vs internal name mismatch. Verify weapon name mapping in pxrt_wnames.

- `girder_launcher_script.lua:10-14` - **low** - LoadImage creates inert CBitmap (pxrt_e_funcs.lua:261-263). At line 201-202, code sets `bmp.top` and `bmp.bottom` fields on the bitmap. CBitmap MT at line 338-350 of pxrt_e_funcs.lua allows field writes via __newindex but drawing with CLandscape::Draw is stubbed (finding #1). The bitmap angle calculation (lines 161-199) is complex but correct transpilation of rotation logic. No issue with bitmap manipulation itself, only with Draw being stubbed.

- `girder_launcher_script.lua:30-43` - **low** - WormAnimParams fields (draw_hand, hand_radius, etc.) are set but class may be inert. If WormAnimParams doesn't exist, `new("WormAnimParams")` returns empty table and field sets do nothing. Animation parameters never reach engine. Not a crash but sprite animation won't work. Related to finding #4.

- `girder_launcher_script.lua:101` - **low** - `__R__.cast("CGObject", K.Env.Objs.Objs[i])` casts array element. Cast is implemented in pxrt_core (not verified but standard). Loop iterates `K.Env.Objs.Count` objects checking ClType for collision. Env.Objs should be populated by engine. Potential issue: if K.Env or K.Env.Objs is not properly initialized, loop may skip. Check K.Env setup in pxrt_e_game.lua.

- `girder_launcher_script.lua:59` - **low** - Sets `self.weap.launch.anim.spriteIndex = 0` assuming launch.anim exists. Launch block is implemented at pxrt_e_structs.lua (CWeaponLaunch) with anim substructure. Access should work. Line accesses nested fields; if any intermediate is nil, runtime logs "method called on null" (pxrt_core.lua:437). Likely safe but depends on missile initialization.

## Notes

- Cannot access PX source files at "C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\utility_girder_launcher\0.0.1\scripts_px\*.pxc" - directory blocked. Line-by-line PX vs transpiled Lua comparison not possible. Transpilation looks structurally correct based on Lua patterns.
- sprite_curtis_259 dependency listed in pxchunks.json but not used in this script - may be used by p_sprite_builder library.
- utility_hangglider comparison task requires accessing hand-written port at "jelly\packages\utility_hangglider\0.0.1\main.lua" (blocked directory). Transpiled version at px_pipeline/testout/lua/utility_hangglider/paratest.lua exists but PX source comparison not done.
- Did not verify all utility functions (Trace, MakeRectMask) - assumed available from utils library based on other package usage patterns.
- M_DRAWQUEUE constant exists (pxrt_e_consts.lua:9) - drawing hooks should fire correctly.
