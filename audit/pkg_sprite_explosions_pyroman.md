# pkg_sprite_explosions_pyroman

I have completed my audit of the sprite_explosions_pyroman package and utility_hangglider. Here are my findings:

## Findings

**sprite_explosions_pyroman package:**

- `explosions_change.lua:8-52` - low - All sprite loading and override calls transpile correctly and use supported runtime features. GetAttachment, LoadSprite, and SetSpriteOverride are properly implemented in pxrt_e_funcs.lua:242-282. No issues found.

**utility_hangglider package (transpiled vs hand-written port comparison):**

- `paratest.lua:27-30` - high - Transpiled code loads CSoundFile from .wav files but CSoundFile is implemented (pxrt_e_funcs.lua:313-335). However, the transpiled version uses `__G__.hangopen`/`__G__.hangclose` global CSoundFile objects while the hand-written port in main.lua uses registerCustomSound() directly and stores IDs. The hand-written approach is more efficient and matches wkJellyWorm's API better.

- `paratest.lua:71-79` - high - Transpiled code checks weapon names with `mc(self.Owner.CurWeapon, "CheckName", "Hang-Glider")` which relies on CWeapon::CheckName method (pxrt_e_classes.lua:537-552). The hand-written port (main.lua:217-218) uses `getWormWeaponId()` and compares weapon IDs directly - more reliable since it avoids the null weapon pointer issue mentioned in known logs ("method CheckName called on null").

- `paratest.lua:84-86,95-97` - medium - Transpiled code calls `CalculateSoundVolume` and `CalculateSoundPan` from utils library globals (`__G__.CalculateSoundVolume`). These functions exist as stubs (pxrt_e_funcs.lua:119-125) but CalculateSoundVolume always returns 1.0. The hand-written port plays sounds at fixed volume 1.0 directly - simpler and equivalent.

- `paratest.lua:134,145` - medium - Transpiled code calls `__G__.NormalizeAngle` and `__G__.LerpAngle` from utils library. These functions are defined in utils.pxc:304-316 but must be transpiled and available as globals. The hand-written port (main.lua:178-186) implements these locally as Lua functions - safer since it doesn't depend on the utils library being loaded.

- `paratest.lua:152-154` - high - Transpiled code calls `__G__.TraceMask()` to detect terrain collisions. TraceMask is implemented as `BF._TraceMask` in pxrt_e_soft.lua:344-409 but requires the utils library. The hand-written port (main.lua:242-247) detects blocked motion by comparing actual vs expected displacement - simpler workaround that doesn't need TraceMask.

- `paratest.lua:196` - high - Transpiled code adds `self.Glider = __R__.new("CWormGlider", self)` field to every CWorm instance via constructor override. The runtime has no native support for a CWorm.Glider field - this only works because pxrt allows arbitrary script fields on proxied objects. The hand-written port (main.lua:173,324) uses a separate `gliders = {}` table keyed by worm address - more explicit and doesn't pollute CWorm instances.

- `paratest.lua:221,242` - high - Transpiled code accesses `__G__.GetCurrentWorm()` which is implemented as `BF.GetCurrentWorm` (pxrt_e_funcs.lua:370-382). The hand-written port (main.lua:319-324) receives worm pointer directly via `CTaskWorm_RegisterCallback_vtable8` callback - avoids the expensive per-frame GetCurrentWorm lookup.

- `paratest.lua:224,228,236` - medium - Transpiled code calls `mc(w, "AddSpriteEx", ...)` to draw rotated glider sprites with rotation parameter. AddSpriteEx is implemented (pxrt_e_classes.lua:73-75) and supports rotation if `E.drawSpriteRot` exists, otherwise logs "sprite rotation/scale not supported" and draws unrotated. The hand-written port (main.lua:302-316) selects pre-rotated frames from sprite sheets and uses `drawSpriteLocal` directly - necessary workaround since wkJellyWorm has no sprite rotation.

- `paratest.lua:50,67` - low - Transpiled code calls `F.PRegister` and `F.PUnregister` for the Owner reference. These are no-op stubs (pxrt_e_funcs.lua:298-300) since Lua GC handles references automatically. The hand-written port doesn't use these - correct for Lua runtime.

No findings for sprite_explosions_pyroman - it uses only basic sprite loading/override features that are fully supported.

## Notes

- Did not verify whether utils library (NormalizeAngle, LerpAngle, TraceMask, CalculateSoundVolume, CalculateSoundPan) is actually transpiled and loaded as globals for the utility_hangglider transpiled version. If these are missing, paratest.lua would fail at runtime.
- Did not verify weapon name normalization logic in CWeapon::CheckName - the hand-written port's weapon ID comparison may behave differently if weapon names don't match exactly.
- The hand-written port in main.lua is not actually run by pxrt (as noted in the task) - it's a direct wkJellyWorm Lua implementation. The comparison shows the transpiled version relies heavily on PX runtime features (GetCurrentWorm, TraceMask, utils globals, CWorm.Glider field) that work in pxrt but are implemented differently or worked around in the hand-written port.
