# pkg_sprite_phone

Based on my comprehensive audit of the sprite_phone package and the utility_hangglider comparison, I can now compile the findings. Let me create the report:

## Findings

**sprite_phone package (phone_change.lua):**

- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\sprite_phone\phone_change.lua:8` - **low** - GetAttachment returns resolved asset path but PX source not available to verify correctness - If phone.png is in wrong directory, runtime logs warning but continues with unresolved name - Verify phone.png exists in sprite_phone package assets directory

- `C:\Users\Admin\pxrt_dev\pxrt_e_funcs.lua:248-253` - **medium** - LoadSprite calls registerCustomSprite conditionally; if registerCustomSprite is nil or fails, sprite ID remains 0 - Scripts using sprite ID 0 will render nothing or crash SetSpriteOverride - Runtime should fail loudly when registerCustomSprite is unavailable rather than silently creating invalid sprite

- `C:\Users\Admin\pxrt_dev\pxrt_e_funcs.lua:277-281` - **medium** - SetSpriteOverride is a silent no-op when host function SetSpriteOverride is nil - sprite_phone's phone sprite override never applies, package has no visual effect - Runtime should log once when SetSpriteOverride is unavailable so package authors know the feature is stubbed

**utility_hangglider comparison:**

- `C:\Users\Admin\pxrt_dev\out\deploy\packages\utility_hangglider_render\0.0.1\main.lua:289-291` - **high** - Hand-written port stubs worm state check (isParachuting always false) and weapon check (hangGliderEquipped always false) because wkJellyWorm wormcallback exposes no ObjState or CurWeapon - Glider never activates in hand-written port; feature is non-functional - pxrt exposes Owner.ObjState and Owner.CurWeapon (pxrt_engine.lua:196,211); hand-written port should use pxrt object model instead of raw wormcallback

- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_hangglider\paratest.lua:152` - **high** - Transpiled code calls __G__.TraceMask but runtime only exports BF._TraceMask (pxrt_e_soft.lua:344), not TraceMask to script globals - Script crashes at runtime with "attempt to call nil value (field 'TraceMask')" when obstacle check runs - Runtime should export TraceMask wrapper in engineG or utils library

- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_hangglider\paratest.lua:86,96` - **medium** - Transpiled code calls __G__.CalculateSoundVolume and __G__.CalculateSoundPan which are not implemented in runtime - Sound effects play with incorrect volume/pan or crash - Runtime should stub these functions or transpiler should detect they're unimplemented

- `C:\Users\Admin\pxrt_dev\out\deploy\packages\utility_hangglider_render\0.0.1\main.lua:424-425` - **medium** - Hand-written port writes This.speedX/speedY (wkJellyWorm wormcallback fields) which are documented as read-only - Velocity changes have no effect; glider cannot steer - pxrt exposes writable Owner.SpX/Owner.SpY (pxrt_engine.lua:199,313); hand-written port should write those instead

- `C:\Users\Admin\pxrt_dev\out\deploy\packages\utility_hangglider_render\0.0.1\main.lua:441` - **medium** - Hand-written port calls drawSpriteLocal with no rotation/scale; comment says "angle, scale, layer, or mirroring parameters" unavailable - Glider drawn without rotation, breaks visual feedback of steering angle - pxrt supports CO.AddSpriteEx with rotation/scale (pxrt_e_classes.lua:73, pxrt_e_quads.lua:181); transpiled code should use that

- `C:\Users\Admin\pxrt_dev\out\deploy\packages\utility_hangglider_render\0.0.1\main.lua:454-458` - **high** - Hand-written port says M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT messages are unavailable so Glider:move never called - Player cannot steer the glider; it only drifts passively - pxrt defines K.M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT (pxrt_e_consts.lua:11) and CWorm::Message receives them; transpiled code hooks CWorm::Message (paratest.lua:199) to dispatch control inputs

- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_hangglider\paratest.lua:153` - **medium** - Transpiled code calls mc(self.Owner, "SetState", K.WS_AFTERROPE) which maps to CG.SetState (pxrt_e_classes.lua:139-148); that function conditionally calls wormSetState or vtable slot 0x38 - If wormSetState host function is unavailable, falls back to vtable call which may not be hooked correctly - Should verify wormSetState availability or ensure vtable fallback is correct

- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_hangglider\paratest.lua:71-79` - **low** - Transpiled code checks weapon name via mc(self.Owner.CurWeapon, "CheckName", "Hang-Glider") which normalizes names (pxrt_e_classes.lua:537-542) - If weapon registration used different capitalization or hyphens, CheckName may fail - Verify registered weapon name exactly matches "Hang-Glider"

- `C:\Users\Admin\pxrt_dev\out\deploy\packages\utility_hangglider_render\0.0.1\main.lua:502-506` - **medium** - Hand-written port comment says CSpriteAnim::SetAnimEx override unavailable to swap glider landing animation sprite - wormGliderBakSpriteId registered but unused; landing animation shows wrong sprite - pxrt hooks CSpriteAnim::SetAnimEx (pxrt_e_hooks.lua:691,707); transpiled code overrides it (paratest.lua:222-260) to swap sprites

- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_hangglider\paratest.lua:155-156` - **low** - Transpiled code writes self.Owner.SpX and self.Owner.SpY which map to wrf() calls (pxrt_engine.lua:313) that write fixed-point to memory offsets 0x90/0x94 - If memory layout differs from WA 3.8.1 or write protection is active, velocity writes silently fail - Runtime should validate memory writes succeed or log failures

## Notes

- Cannot verify sprite_phone PX source (.pxc) correctness because source files are outside allowed directories; only compared transpiled Lua with runtime implementation
- Cannot verify utility_hangglider_render PX source (paratest.pxc) line-by-line because source is outside allowed directories; comparison based on hand-written port comments describing missing features
- Did not audit sound loading (hangopen/hangclose) or weapon registration (WEAPON_GLIDER flag) in detail
- Did not check if NormalizeAngle, LerpAngle helper functions in hand-written port match pxrt implementations
