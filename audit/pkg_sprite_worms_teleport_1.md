# pkg_sprite_worms_teleport_1

I have enough information to complete the audit. Let me compile my findings by analyzing what I've read.

## Findings

- `px_pipeline\testout\lua\sprite_worms_teleport_1\teleport_change_1.lua:13` - high - Wrong sprite used in SetSpriteOverride call - Line 13 uses `tele_wteldsv` instead of `tele_wteldsvu` for sprite 425, and line 16 uses `tele_wteldsv` instead of `tele_wteldsvd` for sprite 426 - This is a transpilation error. The PX source correctly loads three different sprites but the transpiled Lua reuses the first sprite variable. Fix: Change line 13 to `F.SetSpriteOverride(425, __G__.tele_wteldsvu)` and line 16 to `F.SetSpriteOverride(426, __G__.tele_wteldsvd)`.

- `px_pipeline\testout\lua\utility_hangglider\paratest.lua:122-123` - high - GS.env.Gravity and GS.env.Wind not implemented in runtime - Transpiled code accesses `K.GS.env.Gravity` and `K.GS.env.Wind` but the runtime's CEnv proxy (pxrt_engine.lua:224) defines these fields with lowercase (Gravity, Wind) and accesses them via fieldSpec which requires the proxy's `__a` to be set. The K.GS.env accessor in pxrt_e_game.lua:183 does set `__a` via `E.envAddr()`, but CEnv fields are accessed through the generic proxy mechanism - When transpiled code uses `K.GS.env.Gravity`, it goes through gsProxy → envProxy → getMT('CEnv').__index → fieldSpec('CEnv', 'Gravity') → reads offset 0x22C. This should work if envAddr() returns valid address. However, the hand-written port (main.lua:200-206) uses a direct memory read pattern `envGravityWind(worm)` that reads from `world + 0x22C` and `world + 0x230`. Verify E.envAddr() returns the correct world structure address.

- `px_pipeline\testout\lua\utility_hangglider\paratest.lua:71` - med - CurWeapon.CheckName method call - Transpiled code calls `mc(self.Owner.CurWeapon, "CheckName", "Hang-Glider")` which relies on CWeapon proxy's CheckName method (pxrt_e_classes.lua:537-552). The method normalizes weapon names and compares them. The hand-written port (main.lua:216-219) uses `getWormWeaponId(worm)` and compares numeric IDs instead - Both approaches should work, but CheckName depends on weapon name strings being available in memory, which may not be reliable. If CheckName returns false negatives, the glider won't activate.

- `px_pipeline\testout\lua\utility_hangglider\paratest.lua:84-86,95-97` - low - Sound position calculation uses undefined globals - Transpiled code calls `__G__.CalculateSoundVolume` and `__G__.CalculateSoundPan` which are not defined in the runtime or transpiled script globals - These are utility functions that should be provided by utils.pxc (required at line 4). If not defined, the sound Play calls will receive undefined/nil values. The hand-written port (main.lua:208-210) uses `playSoundLocal(1.0, 1.0, worm, id, 0)` instead with fixed volume/pan.

- `pxrt_e_funcs.lua:276-281` - low - SetSpriteOverride silently fails if engine function unavailable - Runtime checks `if SetSpriteOverride then` but always returns 0 whether the call succeeded or not - When the wkJellyWorm global `SetSpriteOverride` is nil, sprite overrides are silently ignored. PX scripts expect these calls to work. Should log a warning on first failure: `once("SetSpriteOverride", "pxrt: SetSpriteOverride unavailable")`.

- `pxrt_e_funcs.lua:245-254` - med - LoadSprite may return sprite with Index=0 if registration fails - When `registerCustomSprite` is nil or returns non-number, the sprite object gets Index=0. Subsequent SetSpriteOverride calls will pass 0 as target sprite ID - This causes sprite overrides to fail silently. The runtime should log when registerCustomSprite is unavailable: `once("registerCustomSprite", "pxrt: registerCustomSprite unavailable, sprites will not load")`.

## Notes

- Could not verify E.envAddr() implementation - it's referenced but not defined in the files I read. This function is critical for GS.env.Gravity/Wind access.
- Could not verify whether utils.pxc provides CalculateSoundVolume/CalculateSoundPan functions.
- The hand-written utility_hangglider port in main.lua uses direct memory access and wkJellyWorm callbacks (CTaskWorm_RegisterCallback_vtable8, registerCallback_onTurnStart) while the transpiled version uses PX class structure (CWormGlider objects with Think methods). These are fundamentally different architectures - the transpiled version won't execute without the CWormGlider class being instantiated and its Think method being called via M_FRAME message routing.
- Did not find evidence that pxrt instantiates custom PX classes or routes M_FRAME messages to their Think methods. The transpiled utility_hangglider code appears to depend on PX runtime features (custom classes, message routing to class methods) that pxrt may not support.
