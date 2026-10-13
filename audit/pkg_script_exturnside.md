# pkg_script_exturnside

Now let me create the final report based on my analysis:

## Findings

- `px_pipeline/testout/lua/script_exturnside/exturnside.lua:18-19` - high - Script attempts to write `self.RopeReady` and `self.ActionReady` fields that don't exist in CWorm - The PXC source uses these as CWorm instance fields (`RopeReady = false`), but pxrt_engine.lua:202-212 shows CWorm only has documented fields (WormTeam, WormNumber, TurnSide, etc.); RopeReady/ActionReady are undefined - Add RopeReady and ActionReady to FIELDS.CWorm in pxrt_engine.lua (research their memory offsets) or use a side table keyed by worm address

- `px_pipeline/testout/lua/script_exturnside/exturnside.lua:7-10` - high - Script calls `mc(__G__.keySync, "AddKey", ...)` but keySync global is not initialized by pxrt - The PXC requires utils.pxc which creates keySync in utils::FirstFrame (px_pipeline/pxl/utils.pxc:428), but pxrt doesn't automatically load shared PX libraries - Either pre-load utils.pxl in pxrt_core or stub CKeySync class with AddKey/KeyPressedNow methods

- `px_pipeline/testout/lua/script_exturnside/exturnside.lua:27,30` - med - Script calls `mc(__G__.keySync, "KeyPressedNow", 90)` which requires CKeySync implementation - keySync.KeyPressedNow reads keyboard state and returns 1 if key was just pressed this frame - Implement CKeySync as a pseudo-class or stub KeyPressedNow to return 0 (disables the feature but prevents crash)

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:196` - high - Transpiled script writes `self.Glider` field in CWorm constructor override, but CWorm has no Glider field - PXC source (paratest.pxc:356) adds `Glider = new CWormGlider(this)` as a CWorm instance field; pxrt_engine.lua:202-212 doesn't define it - Add Glider to FIELDS.CWorm or allow dynamic per-worm fields via side table (worm.Glider would need runtime support for script-added fields)

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:203,207,222-256` - high - Script accesses `w.Glider.Think`, `w.Glider.Deployed`, `w.Glider.GliderAnimCycle` which depend on missing CWorm.Glider field - utility_hangglider transpiled code expects every CWorm to have a .Glider sub-object, created by the CWorm constructor override - This package cannot run on pxrt without CWorm.Glider support; only the hand-written jelly/packages/utility_hangglider/0.0.1/main.lua works (uses SetWeaponSpriteOverride instead)

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:213` - high - Script overrides `CDDQueue::AddSprite` but CDDQueue class is not implemented in pxrt - PXC source (paratest.pxc:333) overrides CDDQueue::AddSprite to replace parachute sprites with glider sprites during rendering; CDDQueue is WA's draw queue - pxrt has no CDDQueue class; grep shows no matches in pxrt_e_*.lua files. This override is critical for rendering the glider

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:205-209` - med - Script filters M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT messages but these may not be delivered during WS_PARACHUTE - PXC expects directional input messages to control the glider during parachute state - Could not verify whether wkJellyWorm sends these messages to CWorm during WS_PARACHUTE; if not sent, glider controls won't work

- `px_pipeline/testout/lua/script_exturnside/exturnside.lua:34` - low - Transpiled code has deeply nested OR chain instead of using Lua table for state checks - PXC line 26-34 has a long multi-line OR condition; transpiler produced 18 nested OR expressions instead of a set lookup - Not a bug, but inefficient. Consider transpiler optimization to generate `local states = {[K.WS_BLOWTORCH]=true, ...}; if states[AWorm.ObjState]` for >5 ORs

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:84-86,95-97` - med - Script calls sound methods `mc(__G__.hangopen, "Play", vol, pan, 0)` but hangopen/hangclose globals may not exist - PXC source loads sounds in paratest::FirstFrame (line 39-40); transpiled to lines 28-29 of paratest.lua using LoadSound - Need to verify pxrt supports LoadSound / CSoundFile.Play; grep shows playSoundLocal in pxrt_e_classes.lua but not LoadSound

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:152` - med - Script calls `__G__.TraceMask(self.Owner, ...)` which requires TraceMask implementation - TraceMask performs collision detection ahead of the worm to detect terrain hits - Need to verify pxrt implements TraceMask; if stubbed, glider won't detect collisions and may phase through terrain

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:71-78` - low - Script calls `mc(self.Owner.CurWeapon, "CheckName", "Hang-Glider")` to detect weapon type - CurWeapon.CheckName is used to determine if the current weapon is the glider vs parachute/balloon/umbrella - Need to verify pxrt's weapon proxy supports CheckName method; if missing, glider enable/disable logic fails

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:224,228` - med - Script calls `mc(w, "AddSpriteEx", 6, w.PosX, w.PosY, sprite, frame, angle, scale)` with rotation parameter - AddSpriteEx draws rotated glider sprites; pxrt_e_classes.lua:73-75 shows rotation support depends on E.drawSpriteRot existence - If drawSpriteRot is unavailable, pxrt logs "sprite rotation/scale not supported" and draws unrotated (glider would look wrong)

## Notes

- Could not verify memory offsets for RopeReady/ActionReady in CWorm structure (would need WA memory map or runtime inspection)
- The hand-written utility_hangglider port (jelly/packages/utility_hangglider/0.0.1/main.lua) works around these issues by using SetWeaponSpriteOverride instead of CDDQueue override and avoiding CWorm.Glider field
- M_DRAWQUEUE message exists in pxrt_e_consts.lua but no evidence that pxrt delivers it to script overrides (utility_hangglider_render expects it)
- CSpriteAnim::SetAnimEx override in paratest.pxc:389 was NOT transpiled to the utility_hangglider/paratest.lua output (transpiler only includes CWorm and CDDQueue overrides, not CSpriteAnim)
- GetCurrentWorm is implemented (pxrt_e_funcs.lua:370) and TurnSide field exists (pxrt_engine.lua:205), so the core exturnside logic should work if keySync and RopeReady/ActionReady are fixed
