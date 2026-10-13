# pkg_weapon_gravler_sb

Now I have enough information to compile the audit report. Let me create a comprehensive findings list:

## Findings

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_script.lua:47` - high - WormSprite class not implemented - Script creates `__R__.new("WormSprite", weapName, sprite, Params)` but runtime has no WormSprite builtin class - Package will fail at line 47 with "unknown class WormSprite"

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_script.lua:35` - high - CWormAnimParams class not implemented - Script creates `__R__.new("CWormAnimParams")` but runtime has no CWormAnimParams builtin class - Package will fail at line 35 with "unknown class CWormAnimParams"

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_script.lua:72` - high - WormSprite class not implemented (duplicate site) - Same as line 47, second instance in the duplicate override for "Gravler FD" weapon - Package will fail with same error

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_script.lua:88` - high - WeapSprite class not implemented - Script creates `__R__.new("WeapSprite", self, sprite, Params)` but runtime has no WeapSprite builtin class - Missile animation will fail with "unknown class WeapSprite"

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_script.lua:85` - high - WeapSpriteParams class not implemented - Script creates `__R__.new("WeapSpriteParams")` but runtime has no WeapSpriteParams builtin class - Package will fail at line 85

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_dig.lua:26` - med - MakeHole implemented but different signature - Script calls `mc(K.GG.land, "MakeHole", 8, __G__.dmis_gravler.PosX, (__G__.dmis_gravler.PosY - 0.0))` which is 4 args (self, radius, x, y), runtime pxrt_e_terrain.lua:145 expects `MakeHole = function(self, super, radius, x, y)` with super arg - Runtime will call E.makeHole(radius, x, y) correctly but the extra super parameter position suggests transpiler may have mistranslated the call

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_script.lua:89` - low - Sprite animation field assignment to zero instead of nil - Script sets `self.weap.launch.anim.spriteIndex = 0` which should work but PX convention for clearing sprite index is typically nil - Minor style inconsistency, functionally equivalent

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:240-257` - high - Hang-glider rendering depends on worm state introspection not exposed - Hand-written port at out/deploy/packages/utility_hangglider_render/0.0.1/main.lua:289-291 documents that wkJellyWorm wormcallback does not expose ObjState or CurWeapon, so glider activation logic cannot be ported faithfully - Both isParachuting and hangGliderEquipped are stubbed to false, so glider never activates

- `px_pipeline/testout/lua/utility_hangglider_render/paratest.lua:252-253` - high - CSpriteAnim override accesses worm.Anim which may not be available in all contexts - Script checks `__R__.eq(w.Anim, self)` in CSpriteAnim::SetAnimEx override; runtime supports w.Anim field (pxrt_engine.lua:211 maps Anim to offset 0x368 with kind "anim") but CSpriteAnim proxy creation (pxrt_engine.lua:349-355) is only triggered when a valid animator address exists - If SetAnimEx fires before worm.Anim is initialized, w.Anim may return 0 or nil instead of CSpriteAnim proxy

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:69-88` - med - Glider physics uses custom Glider.Enabled/Deployed fields on CWorm - Transpiled script extends CWorm with `self.Glider` object having Enabled/Deployed/ang/targetAng fields; runtime supports arbitrary script fields on proxies but these are not persisted or synchronized - If a worm proxy is recreated (address changes, proxy cache evicted), custom fields are lost

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:154-170` - med - Glider input handling overrides M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT - Runtime has these message constants (pxrt_e_consts.lua:11: M_PLEFT=30, M_PRIGHT=31, M_PUP=32, M_PDOWN=33) but transpiled script calls `mc(self.Glider, "Move", Type)` which invokes a method on a script-owned Glider object, not an engine class - This will work if Glider.Move is defined, but hand-written port shows this logic cannot work without ObjState check

- `out/deploy/packages/utility_hangglider_render/0.0.1/main.lua:281-291` - high - Hand-written port stubs critical glider activation conditions - Port documents that wkJellyWorm does not expose worm ObjState (WS_PARACHUTE check) or CurWeapon (CheckName for "Hang-Glider"), so glider never actually activates in the hand-written port - Transpiled version has the same issue but does not document it

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_dig.lua:19-22` - low - Global variable gravler used as state flag with confusing semantics - Line 19 checks `__G__.gravler ~= 0`, line 22 sets it to `1`, but line 34 in FireFinal also sets it to `1` - This creates a race where gravler is set twice (once in FireFinal, once in Message) which may be intentional but is unclear

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_script.lua:27-50` - med - Duplicate CTurnGame::Message overrides for M_FRAME with identical logic - Lines 27-50 and 52-75 both override CTurnGame::Message, check M_FRAME, check gframe==1, and create WormSprite for weapon aiming; only difference is weapon name ("Gravler" vs "Gravler FD") - Runtime will chain both overrides but creating two WormSprite objects per frame (if both weapons exist) may not be intended; PX may have deduplicated these at compile time

- `px_pipeline/testout/lua/weapon_gravler_sb/gravler_dig.lua:25` - low - Terrain damage loop uses dmis_gravler.Sdigging as flag but never clears it - Line 21 sets Sdigging=1, line 25 checks it every M_FRAME to call MakeHole - This will call MakeHole every frame until missile is destroyed, creating continuous terrain damage - May be intended behavior (drilling effect) but no mechanism stops it

## Notes

- Cannot verify PX source files (.pxc) directly as they are outside working directory; compared transpiled Lua with runtime implementation only
- WormSprite, WeapSprite, CWormAnimParams, WeapSpriteParams are sprite animation builder classes from PX that have no runtime equivalent; these are critical for weapon_gravler_sb visual behavior
- utility_hangglider_render hand-written port explicitly documents limitations (worm state introspection unavailable) but transpiled utility_hangglider does not; both versions cannot work correctly in pxrt
- Did not verify SetSpriteOverride, LoadSprite, GetAttachment implementations in detail but all three exist in runtime (pxrt_e_funcs.lua:242-282)
- Custom missile/worm fields (gravlera_anim, Sdigging, Glider.*) work in pxrt but are not persisted across proxy recreation
