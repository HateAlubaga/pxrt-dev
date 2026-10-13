# pkg_utility_platform

Now I'll compile my findings based on the audit.

## Findings

**utility_platform (ray_platform.lua):**

- `ray_platform.lua:22` - high - `SetLayerOverride(LAYER_OILDRUM)` calls stub function. Runtime has two implementations: `pxrt_e_funcs.lua:290` returns 0 (no-op), while `pxrt_e_soft.lua:496` sets `E.layerOverride`. The soft version may not be active, leaving platforms unable to set their render layer. Platform sprites may render at wrong depth or collide incorrectly with the layer system. Verify which implementation is loaded and ensure pxrt_e_soft is active.

- `ray_platform.lua:13-16` - low - `LoadSprite` loads sprites successfully but depends on `registerCustomSprite` being available at runtime. If `registerCustomSprite` is nil, sprite Index will be 0 and sprites won't render. Check initialization order ensures registerCustomSprite is available before InitGraphic runs.

- `ray_platform.lua:82-106` - med - `GetTeamColor` and `SetColorMod/ClearColorMod` are implemented in runtime (pxrt_e_funcs.lua:95-96, 101), but color modulation storage `E.colorMod` must be checked by the sprite drawing code. If `E.drawSprite` doesn't read `E.colorMod`, team colors won't apply. Platforms may all render as red or with wrong team colors.

- `ray_platform.lua:165-189` - med - `K.Env.Objs.Count` and `K.Env.Objs.Objs[i]` iterate the object list to find nearby platforms for ZPlane adjustment. Implementation exists in pxrt_e_game.lua:52-73, but relies on `E.envAddr()` and `rdU` memory reads. If the environment address is invalid (returns 0), the loop never finds matches and ZPlane resets to 13 every 200 frames. Stacked platforms may flicker or render at wrong depth.

- `ray_platform.lua:174` - low - ClType check `obj.ClType == ti(72)` assumes CPlatform has ClType 72. Runtime assigns ClType from `E.OC_BY_NAME` constants, but no constant named "CPlatform" or OC value 72 is defined in pxrt_e_consts.lua. Custom script classes like CPlatform default to ClType 0 unless explicitly set. The ZPlane collision detection won't find other platforms.

- `ray_platform.lua:204` - low - `worm.WormTeam` field exists in runtime (pxrt_engine.lua:203 offset 0xFC), but reading it returns memory value only if worm address is valid. For script-created pseudo-worms or if worm proxy is stale, returns 0. Platform owningTeam will always be 0 for invalid worm references.

- `ray_platform.lua:202` - med - `call(self, "GetObject", 25, 0)` looks up object type 25 (likely OC_Landscape) from the hash store. Runtime implementation (pxrt_e_classes.lua:120) calls `E.hashObject(ti(t), ti(i))`. If the hash store is empty or type 25 has no entry at index 0, returns 0/nil. Platforms will be parented to null instead of the landscape, breaking their attachment.

**utility_hangglider (paratest.lua transpiled vs hand-written port):**

- `paratest.lua:26-29` - high - Transpiled code creates `CSoundFile` objects for hangopen/hangclose sounds. Runtime implementation exists (pxrt_e_funcs.lua:313-333) and calls `registerCustomSound`. Hand-written port (main.lua:192-193) uses `registerCustomSound` directly, storing IDs. Transpiled version wraps in CSoundFile with Play method; hand-written calls `playSoundLocal` directly. Both should work, but CSoundFile.Play internally calls `playSoundLocal` with same signature. No functional difference if both paths are available.

- `paratest.lua:70-78` - high - Transpiled glider checks `mc(self.Owner.CurWeapon, "CheckName", "Hang-Glider")`. Runtime: `CurWeapon` field exists (pxrt_engine.lua:211 offset 0x36C), returns weapon proxy. `CheckName` implementation (pxrt_e_classes.lua:536) uses cached weapon names. Hand-written port (main.lua:291) stubs this as always false with TODO comment: "wkJellyWorm's wormcallback only exposes posX/posY/speedX/speedY... no equipped-weapon introspection available." **Critical mismatch**: transpiled code depends on CurWeapon.CheckName to enable glider, but hand-written port says this is impossible in wkJellyWorm API. Glider will never activate.

- `paratest.lua:69,80` - high - Transpiled code checks `self.Owner.ObjState == K.WS_PARACHUTE` (0x7D). Runtime: ObjState field exists (pxrt_engine.lua:196 offset 0x44), constant defined (pxrt_e_consts.lua:37). Hand-written port (main.lua:290) stubs as always false with TODO: "Owner->ObjState == WS_PARACHUTE... wkJellyWorm's wormcallback only exposes posX/posY/speedX/speedY on `This`; there is no worm-state... introspection available." **Critical mismatch**: transpiled relies on ObjState reads from memory-backed worm proxy; hand-written says wormcallback doesn't expose this. If pxrt runs via wormcallback (not memory hooks), ObjState won't be readable.

- `paratest.lua:83-85, 94-96` - med - Transpiled code calls `CalculateSoundVolume` and `CalculateSoundPan` utility functions. Runtime stubs exist (pxrt_e_funcs.lua:119-125): CalculateSoundVolume returns fixed 1.0, CalculateSoundPan computes basic pan from camera X. Hand-written port (main.lua:243-245) also stubs with fixed values and TODO comment. Both stub implementations match - no issue here.

- `paratest.lua:100-156` - med - Transpiled glider physics uses `K.GS.env.Gravity` and `K.GS.env.Wind`. Runtime `K.GS` returns game state proxy (pxrt_e_consts.lua:63), env reads from memory offsets. Hand-written port (main.lua:362-366) stubs with TODO: "GS->env->Gravity / GS->env->Wind... with no wkJellyWorm equivalent exposed. Using fixed placeholder for gravity and no wind." Physics will work but with wrong gravity/wind values if memory backend is unavailable.

- `paratest.lua:205-210` - high - Transpiled override on `CWorm::Message` intercepts M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT messages. Constants exist (pxrt_e_consts.lua:11), message dispatch happens via engine hooks (pxrt_e_hooks.lua). Hand-written port (main.lua:454-458) has move() method with TODO: "M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT key-hold events are not among the documented wormcallback messagetypes... Without a key-input message the runtime has no way to invoke this method." **Critical mismatch**: transpiled expects CWorm::Message override to receive keyboard input; hand-written says wormcallback doesn't deliver these messages. Glider steering won't work.

- `paratest.lua:213-260` - high - Transpiled override `CDDQueue::AddSprite` replaces worm sprite (287-291) with glider sprite using `AddSpriteEx` with rotation. Runtime: CDDQueue class not found in any pxrt file - no natives, no proxy, not in class hierarchy. Override will fail to register or won't be called. Hand-written port (main.lua:315-318, 434-441) has TODO comments acknowledging sprite replacement and SetAnimEx override are impossible. Glider sprite won't replace parachute animation - default parachute sprite will show.

- `paratest.lua:224,228` - med - Transpiled calls `AddSpriteEx(z, x, y, sprite, frame, angle, scale)`. Runtime `CO.AddSpriteEx` exists (pxrt_e_classes.lua:72-73) and forwards to `E.drawSprite` with rotation and scale parameters. `E.drawSprite` (pxrt_e_classes.lua:49-65) checks for `E.drawSpriteRot` function and warns "sprite rotation/scale not supported by the DLL: drawn unrotated" if unavailable. Falls back to `drawSpriteLocal` which has no rotation. Hand-written port (main.lua:437-440) acknowledges this with TODO: "drawSpriteLocal... has no angle, scale, layer, or mirroring parameters." Glider sprite draws at correct position but unrotated.

## Notes

- Could not read original .pxc source files (outside working directory permission). Audit based on transpiled Lua and hand-written port comparison.
- LAYER_OILDRUM constant not found in runtime - may be defined in package code or missing entirely.
- ClType 72 for CPlatform: script classes don't auto-register object type constants. Platform's ZPlane neighbor detection will fail unless ClType is explicitly set.
- CDDQueue override mechanism: class not present in runtime class hierarchy. Sprite override system may require different hook approach than CWorm::Message pattern.
- Utility_hangglider hand-written port documents extensive limitations of wkJellyWorm callback API vs. full PX memory access - most critical glider features (state detection, weapon checking, keyboard input, sprite replacement) are marked impossible in the port's TODOs but present in transpiled code.
