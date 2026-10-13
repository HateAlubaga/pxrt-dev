# pkg_wosc_lib

Based on my audit of the wosc_lib package, I've identified the PX features it needs and checked against the runtime implementation. Here are my findings:

## Findings

- `pxrt_e_classes.lua:253` - high - CTurnGame::SetCurrentTeam is stubbed (returns 0 immediately) - wosc_lib overrides it in 3 scripts (invisibilityturns, AutoFireWeapon, restoreweapons) to run per-turn logic, but the override will never execute because super() calls a no-op - implement SetCurrentTeam hooks or the per-turn weapon manager features silently fail
- `px_pipeline/testout/lua/@lib/wosc_lib/wosc_lib.lua:339` - med - transpiler incorrectly tests Stores Count/Delay for null with isnull() - in PX line 334 `Count[i+2] != 0` means "ammo is nonzero", but transpiled Lua `not isnull(K.GS.Info.Stores[...].Count[...])` means "value exists" - Count always returns a number (0 if none), never nil, so isnull() always returns false and the condition breaks - compare `K.GS.Info.Stores[...].Count[...] ~= 0`
- `px_pipeline/testout/lua/@lib/wosc_lib/wosc_lib.lua:339` - med - transpiler incorrectly tests Delay for zero with isnull() - PX line 334 `Delay[i+2] == 0` becomes `isnull(K.GS.Info.Stores[...].Delay[...])` - Delay returns a number, isnull(0) is true in pxrt but the logic inverts the test (should be `== 0` not `isnull()`) - RemoveWeapons sets wrong delays
- `px_pipeline/testout/lua/@lib/wosc_lib/wosc_lib.lua:277` - med - AutoFireWeapon string array incorrectly tested with isnull() - PX line 294 `AutoFireWeapon[i] != 0` (string empty check) becomes Lua `not isnull(__G__.AutoFireWeapon[ti(i)])` - string arrays are initialized as `__R__.arr({71}, "")` (empty strings), isnull("") is false, so the condition `not isnull("")` is true and fires weapons on empty slots - compare `~= "" and ~= 0`
- `px_pipeline/testout/lua/@lib/wosc_lib/wosc_lib.lua:201` - low - transpiler emits `self.vol =` for non-local variable - PX line 218 `vol = CalculateSoundVolume(PosX,PosY)` (missing `local`) becomes `self.vol =` polluting worm object state - compare PX line 259 where `local vol` correctly transpiles to `local vol` - minor: vol/pan leak into worm fields instead of being temporaries
- `pxrt_e_funcs.lua:113` - low - IsMultiplayer stubbed (always returns 0) - wosc_lib personalinvisibility uses it to decide whether to hide invisible worms from other players (lines 163, 198) - invisibility always renders as if single-player, showing black-tinted worms to all - implement or document multiplayer rendering is unsupported
- `pxrt_e_game.lua:220` - low - GG.machColors stubbed (always returns 0xFF) - wosc_lib checks `(GG->machColors[GetLocalMachine()] & (1 << c)) != 0` to see if local machine controls a color (lines 166, 201) - stub returns 0xFF so all colors appear local-controlled, invisibility tint applies when it shouldn't in network play - acceptable if multiplayer unsupported

## Notes

- GetWeaponByIndex, CheckName, GetWeaponIndex: implemented correctly in pxrt_e_classes.lua
- CShootDesc: implemented in pxrt_e_structs.lua with full field set
- GetTeamNumber: implemented in utils.lua (shared library), correctly used
- CalculateSoundVolume, CalculateSoundPan: stubbed (return 1.0 and calculated pan), acceptable
- FireFinal: implemented as hook in pxrt_e_classes.lua
- Stores Count/Delay: implemented as proxies in pxrt_e_classes.lua lines 324-353, return numbers correctly
- GetWeaponByName: implemented in pxrt_e_funcs.lua:143
- The utility_hangglider comparison was not performed as the task description indicated the hand-written port is NOT run by pxrt, and no comparison request was made for non-pxrt code
