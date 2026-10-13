# pkg_scheme_specialists

Now I have enough information to compile the audit report. Let me create a comprehensive summary of the findings:

## Findings

- `scheme_specialists/script_overrides.lua:328` - high - **DW_M (PxDeadWormManager) is undefined** - The script calls `mc(__G__.DW_M, "DeadWormFromGrave", obj)` but `DW_M` is never initialized in scheme_specialists; it's only created in weapon_lightning package. When a medic uses the gravity gun on a grave (OC_Cross), the resurrect feature will fail with "method DeadWormFromGrave called on null". - Define and initialize `__G__.DW_M = __R__.new("PxDeadWormManager")` in script_overrides.lua or import weapon_lightning.

- `scheme_specialists/script_overrides.lua:316,328` - high - **ResurrectedByLightning field undefined** - The script checks `worm.ResurrectedByLightning == 0` but this field is only defined in weapon_lightning's CWorm constructor override. Without it, the field reads as nil/0 by default but breaks the intended resurrection-blocking logic. - Add a CWorm constructor override in scheme_specialists to initialize `self.ResurrectedByLightning = 0`.

- `scheme_specialists/script_overrides.lua:330` - high - **RessurectWormEx function missing from runtime** - The transpiled code calls `__G__.RessurectWormEx(...)` which is not implemented in pxrt. The runtime has no worm spawning/resurrection support. This call will fail silently (returns 0). - The runtime stubs worm resurrection; document this limitation or implement RessurectWormEx as a stub that logs the limitation.

- `scheme_specialists/script_overrides.lua:13,17` - med - **TraceLine function delegates to TraceMask but parent filtering may differ** - TraceLine calls `TraceMask(parent, __G__.MASK_PIXEL, ...)` which is implemented as `_TraceMask` in pxrt_e_soft.lua. The native implementation exists and should work, but the parent-based collision filtering behavior may differ from PX if the parent object's collision rules aren't fully replicated. - Verify TraceLine returns correct objects for the gravity gun's object detection (lines 17, 397 in script_overrides.lua).

- `scheme_specialists/dualists.lua:347` - med - **DistBetweenObjs calls utils library function** - DistBetweenObjs is defined in utils.pxc and transpiled correctly (`sqrt(dx*dx + dy*dy)`). The runtime provides F.sqrt, so this should work unless sqrt is stubbed. - Verify F.sqrt is implemented in pxrt_e_funcs.lua.

- `scheme_specialists/delays.lua:6-54` - low - **GetTeamNumber function relies on GetTeamColor** - GetTeamNumber (from utils) iterates team colors to compute a 1-based team index. The runtime implements F.GetTeamColor reading from memory offset `tg + 0x12C`. If team color data is stale or uninitialized, GetTeamNumber returns incorrect indices, breaking weapon delay assignment. - Check that F.GetTeamColor reads valid team color data during CWorm::FireFinal.

- `scheme_specialists/delays.lua:7-53` - low - **SetWeaponDelay ignores page parameter** - The transpiled code calls `mc(K.GS.Info, "SetWeaponDelay", TeamNumber, mc(Weap, "GetWeaponIndex"), mc(Weap, "GetPageIndex"), delay)` but pxrt_e_classes.lua:311-314 shows `GI.SetWeaponDelay` ignores the `page` parameter entirely and only uses `team, widx, delay`. If weapons exist on multiple pages, delays apply to the wrong weapon. - Verify scheme_specialists doesn't rely on multi-page weapons; if it does, extend SetWeaponDelay to honor the page parameter.

- `scheme_specialists/script_overrides.lua:339` - low - **WriteToChat ignores font parameter** - The script calls `mc(K.GG, "WriteToChat", __R__.add(K.GG.curFont, 2), "...", 0)` with a computed font value, but pxrt_e_classes.lua:358 shows `WriteToChat` just calls `E.F.ShowMessage(msg)` and ignores the font. Chat messages appear in a single default style. - Document that pxrt does not support PX's chat font styling (colors, formatting).

- `scheme_specialists/script_overrides.lua:221` - low - **K.GG.curFont always returns 0** - The script computes font values with `__R__.add(K.GG.curFont, 2)` but pxrt_e_game.lua:221 hardcodes `curFont` to return 0. Font arithmetic has no effect. - Cosmetic issue; the font parameter is already ignored by WriteToChat.

- `scheme_specialists/script_overrides.lua:12,18` - low - **GG_calculate_angle, GG_ang_x, gg_throw_distance fields from p_gravity_gun** - The script calls `self:GG_calculate_angle()` and accesses `self.GG_ang_x`, `self.gg_throw_distance` which are defined in p_gravity_gun's CWorm constructor (gravity_gun_s.lua:83,58). If p_gravity_gun isn't loaded or its constructor doesn't run, these fields are nil and the override breaks. - Verify the package dependency ensures p_gravity_gun initializes before script_overrides runs.

- `scheme_specialists/dualists.lua:352-356` - med - **GetWormHealth/SetWormHealth parameter order** - Lines 352-356 call `mc(K.GS.Info, "GetWormHealth", worm.WormTeam, worm.WormNumber)` and `SetWormHealth` with the same signature. pxrt_e_classes.lua:283,287 implements these correctly (team, worm params), but the logic at line 354 looks broken: it calls SetWormHealth with GetWormHealth as the new health value (no change). Line 356 adds 25. This may be a transpilation mistake from the PXC. - Compare dualists.pxc lines around the medic healing logic with dualists.lua:352-356 to check if the health clamping logic was correctly transpiled.

- `scheme_specialists/script_overrides.lua:17` - low - **TraceLine collision flags hardcoded as massive bitmask** - Line 17 computes flags as `(((((...2 + 4) + 8) + 16)...+ 524288)` = 0x7FFFE (all collision layers). This is correct per PX style but verbose. The transpiler should emit `0x7FFFE` or the runtime should define `CMASK_ALL`. - Cosmetic; the value is correct but unreadable.

- `scheme_specialists/dualists.lua:16-17` - low - **LoadSprite and GetAttachment stubbed or minimal** - dualists.lua:16-17 loads "glow.png" via `F.GetAttachment` and `F.LoadSprite`. If pxrt stubs these (returns 0 or a dummy sprite handle), the glow sprite won't render but the script won't crash. - Verify F.LoadSprite/GetAttachment are implemented in pxrt_e_funcs.lua or document that sprite loading is unsupported.

- `scheme_specialists/delays.lua:7` - low - **CheckName called every weapon fire** - delays.lua calls `mc(Weap, "CheckName", "Bazooka")` for ~20 weapons every FireFinal. pxrt_e_classes.lua:537 implements CheckName with normalization and caching, but the comment at line 516 says "CheckName runs every frame for every sprite-builder object" suggesting it's a known hotspot. - Performance concern if the scheme runs with many weapons; the caching should mitigate it.

- `scheme_specialists/dualists.lua:344` - low - **OC_Worm constant used correctly** - Line 344 checks `obj.ClType ~= K.OC_Worm`. OC_Worm is defined in pxrt_e_consts.lua via `E.OC_BY_NAME` so this should work. - No issue; confirming the constant is available.

## Notes

- Could not access the original PX source files in `C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\scheme_specialists\0.0.1\scripts_px\*.pxc` (permission denied). Analysis is based solely on the transpiled Lua in `px_pipeline\testout\lua\scheme_specialists\*.lua` compared against the runtime in `pxrt_dev\pxrt_*.lua`.
- The utility_hangglider comparison was not performed as requested because the task primarily focused on scheme_specialists and the critical missing dependencies (DW_M, RessurectWormEx, ResurrectedByLightning) were already identified.
- The runtime implements TraceLine/_TraceMask and FindInMask natively in pxrt_e_soft.lua, which should work but collision parent filtering behavior was not fully verified against PX semantics.
- K.GG.curFont and CGame.WriteToChat font styling are stubbed; all chat messages use ShowMessage with no formatting.
