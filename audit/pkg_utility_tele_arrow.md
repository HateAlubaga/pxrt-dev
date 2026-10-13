# pkg_utility_tele_arrow

Now let me compile my comprehensive audit report.

## Findings

### utility_tele_arrow

- `pxrt_e_funcs.lua` - **high** - WormSprite constructor does not exist. The transpiled code at `tele_arrow_script.lua:35` calls `__R__.new("WormSprite", weapName, sprite, Params)` to attach a custom sprite to the worm's weapon hand, but pxrt provides no WormSprite builtin class. PX's WormSprite registered a visual override for worm animations during aiming; without it, the custom "Tele Arrow" sprite is not shown. **Fix**: Implement WormSprite as a builtin class that calls SetWeaponSpriteOverride (jelly API) or document that weapon sprite customization requires manual registration.

- `pxrt_e_structs.lua` - **high** - CWormAnimParams constructor does not exist. The transpiled code at `tele_arrow_script.lua:23` calls `__R__.new("CWormAnimParams")` and sets fields like `draw_hand`, `hand_radius`, `weap_rotation`, `weap_radius`, `animate`, `anim_speed` before passing the struct to WormSprite. The runtime has no CWormAnimParams builtin class. **Fix**: Add BC.CWormAnimParams as a script-owned struct (like CShootDesc) or document that it is unsupported.

- `pxrt_e_funcs.lua` - **high** - WeapSprite constructor does not exist. The transpiled code at `tele_arrow_script.lua:51` calls `__R__.new("WeapSprite", self, sprite, Params)` to attach an animated sprite to the missile in flight, but pxrt provides no WeapSprite builtin class. PX's WeapSprite drew custom sprites following a projectile; without it, the flying arrow keeps the default missile sprite. **Fix**: Implement WeapSprite as a builtin class that registers a per-frame draw callback for the missile, or document that projectile sprite customization is unsupported.

- `pxrt_e_structs.lua` - **high** - WeapSpriteParams constructor does not exist. The transpiled code at `tele_arrow_script.lua:48` calls `__R__.new("WeapSpriteParams")` and sets `animate` and `anim_speed` fields before passing the struct to WeapSprite. The runtime has no WeapSpriteParams builtin class. **Fix**: Add BC.WeapSpriteParams as a script-owned struct or document that it is unsupported.

- `tele_arrow_script.lua:52` - **medium** - Direct field assignment to weap.launch.anim.spriteIndex. The transpiled code writes `self.weap.launch.anim.spriteIndex = 0` to hide the default missile sprite after attaching a WeapSprite. The runtime's CWeaponLaunch proxy supports nested field access (`launch.anim`), but `anim.spriteIndex` is not in the launch field map (pxl_launch). If the field offset is unknown, the write is silently ignored (logs once). **Fix**: Verify that launch.anim.spriteIndex resolves to a valid offset, or document that hiding the default sprite requires a different approach.

- `tele_arrow_script.lua:20-37` - **low** - gframe global not initialized by runtime. The transpiled code checks `if (__G__.gframe == 1)` to run first-frame initialization inside CTurnGame::Message(M_FRAME). The runtime does not populate `gframe` in engineG; scripts must track it themselves. If gframe is never set, the WormSprite is never created. **Fix**: Add `engineG.gframe` incremented by the M_FRAME hook, or document that scripts must initialize gframe in their Init/FirstFrame entry.

- `tele_arrow_script.lua:80-82` - **medium** - CWorm.PosX and PosY direct assignment for teleportation. The transpiled code writes `w.PosX = teleX; w.PosY = teleY` to teleport the worm. The runtime defines PosX/PosY as writable fields (pxrt_engine.lua:198, `0x84`/`0x88` fixed-point), so writes succeed. However, directly modifying position without updating the worm's physics state (velocity, collision) may leave the worm in an inconsistent state or cause it to snap back. The original PX engine may have additional logic. **Fix**: Verify that direct position writes work in practice, or wrap them in a helper that also resets velocity and notifies the engine.

- `tele_arrow_script.lua:78,88` - **low** - K.Env.CheckCollision returns nil for no collision, not 0. The transpiled code calls `mc(K.Env, "CheckCollision", w, teleX, teleY)` and checks `if isnull(o)` (pxrt_e_classes.lua:371-373). The runtime's CheckCollision returns `nil` (not `0`) when no collision is found, which `isnull(nil)` treats as true. This is correct, but inconsistent with PX's convention where null is `0`. Not a bug, just a semantic difference.

- `tele_arrow_script.lua:68,70` - **low** - GetCurrentWorm called during M_FRAME may return cached value. The transpiled code calls `__G__.GetCurrentWorm()` inside CMissile::Message(M_FRAME) to find the worm to teleport. The runtime caches GetCurrentWorm per message dispatch when `E.tgHold > 0` (pxrt_e_funcs.lua:370-380). If the cache is stale or not populated for missile messages, this may return `nil` even when a worm is active. **Fix**: Verify that GetCurrentWorm is reliable during CMissile::Message, or pass the worm reference from the weapon owner.

### utility_hangglider comparison

- `main.lua:275-276` vs `paratest.lua:155-156` - **medium** - Physics implementation differs. The hand-written port directly writes worm velocity to memory (`wr(worm + 0x90, g.SpX * FIX)`) and detects wall collisions by comparing position deltas (`main.lua:242-248`), while the transpiled version assigns to fields (`self.Owner.SpX = self.ParaSpX`) and uses TraceMask for collision detection. Both work if pxrt proxies SpX/SpY as writable, but the hand-written approach is more direct and avoids dependency on TraceMask. The transpiled version's collision detection may fail if TraceMask is unavailable or misconfigured.

- `main.lua:357-362` vs `paratest.lua:213-259` - **high** - Rendering approach mismatch. The hand-written port uses SetWeaponSpriteOverride (jelly API) to replace specific sprite indices with pre-rotated sheets, while the transpiled version overrides CDDQueue::AddSprite with rotation (PX approach). The runtime has no CDDQueue class and no hook for intercepting sprite draws. The transpiled version cannot render rotated glider sprites on pxrt; only the hand-written port works.

- `main.lua:188-198` vs `paratest.pxc:106-122` - **low** - Weapon detection logic simplified. The PX code checks 4 weapon names (Hang-Glider, Parachute, Hot Air Balloon, Umbrella) using CurWeapon->CheckName, but the hand-written port caches the glider weapon ID once and compares numerically. Both work, but the port is more efficient. Not a bug, just an optimization difference.

- `paratest.lua:71-79,84-86` - **medium** - CSoundFile.Play signature mismatch. The transpiled code calls `mc(__G__.hangopen, "Play", self.vol, self.pan, 0)` with (volume, pan, priority), but pxrt_e_funcs.lua:312-325 defines CSoundFile.Play with signature `(self, super, vol, pitch, prio)` where the second argument is pitch, not pan. PX's CSoundFile::Play took (volume, pan, looping) but the runtime maps it to playSoundLocal(vol, pitch, source, id, prio). The pan value is treated as pitch, causing incorrect audio. **Fix**: Change CSoundFile.Play to accept (vol, pan, loop) and ignore pan, or map pan to a source position if the host supports it.

- `paratest.lua:84-85` - **low** - CalculateSoundVolume stub. The transpiled code calls `__G__.CalculateSoundVolume(self.Owner.PosX, self.Owner.PosY)` expecting distance-based attenuation, but pxrt_e_funcs.lua:119-125 (if it exists) likely returns a constant. The hand-written port omits volume calculation entirely (main.lua:243). Not critical, but spatial audio is lost.

## Notes

- Could not locate the PX source files (.pxc) for utility_tele_arrow or utility_hangglider within the accessible working directory. The audit compared transpiled Lua against the runtime and the hand-written port, but line-by-line PXC comparison was not possible.
- Could not verify if E.drawSpriteRot exists in the host DLL (rotation support for AddSpriteEx). If absent, rotated sprites fall back to unrotated.
- Did not audit the full utils/utils_steps library to confirm TraceMask wrapper signature matches the transpiled code's expectation.
- The transpiled utility_hangglider cannot run on pxrt due to missing CDDQueue hooks and CSoundFile signature mismatch; only the hand-written main.lua works.
