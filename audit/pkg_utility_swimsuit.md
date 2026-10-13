# pkg_utility_swimsuit

I'll now create a comprehensive audit report by analyzing the findings from the code I've read.

## Findings

- `px_pipeline/testout/lua/utility_swimsuit/swimsuit_SCRIPT.lua:12` - high - **keySync global missing** - Script calls `mc(__G__.keySync, "AddKey", 16)` but `keySync` is never initialized in the runtime's global table. The runtime has no keySync implementation. - Add a keySync stub object with AddKey, KeyPressed, KeyPressedNow methods and kRStates array to the runtime's global initialization.

- `px_pipeline/testout/lua/utility_swimsuit/swim_suit_diving_s.lua:14` - high - **TraceLine builtin missing** - Script calls `__G__.TraceLine(self, self.PosX, self.PosY, ...)` but TraceLine is not implemented in pxrt_e_funcs.lua (only _TraceMask exists in pxrt_e_soft.lua). All terrain collision checks will fail with "missing builtin" log. - Implement BF.TraceLine or alias it to the existing terrain probe logic in pxrt_e_terrain.lua.

- `px_pipeline/testout/lua/utility_swimsuit/swimsuit_SCRIPT.lua:403` - med - **PlaySoundBank override ignored** - Script overrides `CWorm::PlaySoundBank` but this method is not in the CWorm natives table in pxrt_e_classes.lua. The override will register but never fire. Sound suppression for sound 58 (drowning splash) won't work. - Add CW.PlaySoundBank native stub to pxrt_e_classes.lua.

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:152` - high - **TraceMask builtin missing from global** - Script calls `__G__.TraceMask(...)` but TraceMask is only defined as `BF._TraceMask` (builtin function, not global). The collision check before landing will fail. - Add `__G__.TraceMask = BF._TraceMask` to runtime global initialization or change transpiler to emit `call(nil, "_TraceMask", ...)`.

- `C:\Users\Admin\pxrt_dev\pxrt_e_funcs.lua:370` - low - **GetCurrentWorm is BF not global** - Transpiled code calls `__G__.GetCurrentWorm()` but it's defined as `BF.GetCurrentWorm`. This works only if the transpiler emits `call(nil, "GetCurrentWorm", ...)` which routes to BF; direct `__G__.GetCurrentWorm()` would fail. - Verify transpiler emits correct form or add `__G__.GetCurrentWorm = BF.GetCurrentWorm`.

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:84` - low - **CalculateSoundVolume/Pan called as globals** - Script calls `__G__.CalculateSoundVolume(...)` and `__G__.CalculateSoundPan(...)` but these are defined as `F.CalculateSoundVolume` and `F.CalculateSoundPan` in pxrt_e_funcs.lua. - Add globals `__G__.CalculateSoundVolume = F.CalculateSoundVolume` and `__G__.CalculateSoundPan = F.CalculateSoundPan` or fix transpiler.

- `C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\utility_hangglider\0.0.1\main.lua:224` - high - **Hand-written port uses AddSpriteEx with rotation** - The Lua port calls `mc(w, "AddSpriteEx", 6, w.PosX, w.PosY, spriteId, frame, -angle, 1.0)` with rotation, but pxrt_e_classes.lua:73 `CO.AddSpriteEx` logs "rotation/scale not supported by the DLL" once then draws unrotated. Glider will not tilt. - The hand-written port compensates by using pre-rotated sprite sheets (wgldrot1/2.png with 58 angle frames), while transpiled version expects real rotation. pxrt needs E.drawSpriteRot implemented in the DLL.

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:224` - high - **Transpiled hangglider expects sprite rotation** - Transpiled code calls `mc(w, "AddSpriteEx", 6, w.PosX, w.PosY, __G__.wormGliderSprite.Index, w.Glider.GliderAnimCycle, (-w.Glider.GliderAng), 1.0)` with rotation angle, but runtime only logs "sprite rotation/scale not supported" and draws unrotated. Glider sprite won't tilt with angle. - Either implement E.drawSpriteRot in wkJellyWorm DLL or transpile utility_hangglider to use the hand-written port's pre-rotated sheet approach.

- `px_pipeline/testout/lua/utility_swimsuit/swimsuit_SCRIPT.lua:291` - med - **RenderWorm override draws without rotation** - Override draws `SwimAnim` and `SwimCircle` sprites via AddSpriteEx with rotation=0 and scale=1, which works. However, if the sprites needed rotation (like hangglider), they would render incorrectly. - No fix needed for swimsuit (rotation=0), but note the limitation for future packages.

- `px_pipeline/testout/lua/utility_swimsuit/swimsuit_SCRIPT.lua:49` - low - **antisink_fail field never read** - Field `self.antisink_fail` is set to 0 or 1 five times but never read. Likely dead code from incomplete transpilation or debugging. - Review PX source to confirm if this field has effects in real PX or can be removed.

## Notes

- Could not read PX source files (.pxc) in `C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\` due to working directory restrictions. Compared transpiled Lua with itself and with hand-written port where available.
- Did not verify asset files (wswim.png, swimround.png, wfloat.png, wgldlnk.png, wgldbak.png, *.wav) exist or are correctly registered.
- Did not check if utility_inverse and utils libraries used by swimsuit_SCRIPT.pxc are loaded and compatible with pxrt.
- The hand-written utility_hangglider port (main.lua) is more complete than the transpiled version: uses pre-rotated sprite sheets (58 angles) to work around missing rotation, has SetWeaponSpriteOverride to blank parachute sprites 287/288, and includes velocity-based physics not in the transpiled stub.
