# pkg_weapon_drilling_crew

I have completed the audit of weapon_drilling_crew and utility_hangglider. Let me compile my findings:

## Findings

- `drilling_crew_script.lua:40` - high - WormSprite class not implemented - The script creates `new WormSprite(weapName, sprite, Params)` to register worm animation parameters for the "Drilling Crew" weapon, but pxrt has no WormSprite class or registration mechanism. Without this, the weapon will not show the custom driller sprite on the worm's hand during aiming. - Implement WormSprite registration in pxrt_e_classes.lua, storing params indexed by weapon name, and apply them in the worm rendering path.

- `drilling_crew_script.lua:24` - med - CWormAnimParams struct not implemented - The script creates `new CWormAnimParams` and sets fields (hand_type, hand_scale, hand_radius, weap_rotation, animate, etc.), but pxrt has no CWormAnimParams struct definition. The struct is created but never validated or used. - Add CWormAnimParams to pxrt_e_structs.lua with the fields shown in the PX source (hand_type, hand_scale, hand_radius, hand_rotation, hand_radial_rotation, weap_radial_rotation, weap_rotation, weap_radius, animate, anim_speed, dont_rotate_with_angle, hand_ang_if_static, ang_if_static).

- `drilling_crew_script.lua:56-58` - med - Logic error in driller flag initialization - PX line 56-58: `if (driller) { dmis_driller = this; dmis_driller->Sdigging = true; driller = true; }` checks if driller is already true before setting it. Lua line 55-59 has identical logic. But driller is set to 1 at line 70 in FireFinal, so the check `if (__G__.driller ~= 0)` at line 55 will be true on the second missile onward, not the first. The first missile will have driller=0 initially (ginit line 7), so it won't dig. - The PX logic appears wrong: driller should be checked for non-zero, then set to true AFTER capturing the missile. The condition at line 56 should be `if (!driller)` or the flag should start as true.

- `drilling_crew_script.lua:62` - low - MakeHole called every frame without rate limiting - Line 62 calls `MakeHole(7, ...)` every M_FRAME while Sdigging is true. At 50 fps, this creates 50 holes/sec. PX likely had the same behavior, but it may cause performance issues. The runtime implements MakeHole via callThiscall to WA's terrain vtable, which should work. - Consider adding a frame counter to drill every N frames if performance is an issue.

- `utility_hangglider/paratest.lua:240-256` - high - Glider not functional in pxrt - The transpiled Lua overrides CObject::AddSprite to swap parachute sprites (289-291) for the glider backup sprite when a worm has Glider.Enabled. But the hand-written port in main.lua uses a completely different approach: it hooks onPlayerMessage for controls, modifies worm velocity directly via writeMemInt, and uses onPreRender to draw pre-rotated glider sprites via drawSpriteLocal. The transpiled version expects worm.Glider.Enabled (a custom field added in the override CWorm::CWorm at line 33), which pxrt doesn't initialize. The port doesn't run under pxrt; it's a standalone jelly package. - pxrt cannot run utility_hangglider as transpiled. The port demonstrates the correct approach for wkJellyWorm (direct memory manipulation + jelly hooks), but differs significantly from the PX control flow (physics, rotation, sprite selection).

- `drilling_crew_script.lua:21` - low - gframe not documented - Line 21 checks `if (__G__.gframe == 1)` but gframe is not found in any runtime grep. It's likely a global frame counter from utils or the engine, but its absence means the WormSprite registration at gframe==1 may never run. - Verify gframe is exported by pxrt or a loaded library; if missing, use K.GS.Tick or another frame counter.

No findings for transpilation mistakes in drilling_crew_script.lua — the Lua matches the PX source line-by-line for all functions (InitGraphic, CTurnGame::Message, CMissile::CMissile, CMissile::Message, CWorm::FireFinal). Field access, method calls, and control flow are correct.

## Notes

- Could not verify gframe global — not found in runtime files, likely from utils library which wasn't examined.
- Could not test runtime behavior — only static code analysis performed.
- MakeHole, CheckName, LoadSprite, GetAttachment are all implemented in the runtime and should work.
- The driller logic (lines 55-59, 69-71) appears to have a subtle initialization bug inherited from the original PX source.
- utility_hangglider's hand-written port uses a fundamentally different architecture (jelly hooks + direct memory writes) incompatible with pxrt's object-model approach. The transpiled version would need worm.Glider custom field support and AddSprite override dispatch, neither of which exist.
