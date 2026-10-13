# rt_pxrt_e_classes

Now I have enough context. Let me analyze the code systematically for the specific issues mentioned. Let me create a comprehensive audit report:

## Findings

- `pxrt_e_classes.lua:195` - high - Missing null check before buffer allocation - If `E.acquireBuf(16)` returns 0 (allocation failure), the code proceeds to use `b` as a valid address at line 196-199, leading to invalid memory access - Add `if b == 0 then E.releaseBuf(16, b) return 0 end` after line 195.

- `pxrt_e_classes.lua:573` - high - Missing null check before buffer allocation - If `E.acquireBuf(OWN_SIZE)` returns 0 (allocation failure), the buffer address is stored and later used without validation - Add `if a == 0 then return 0 end` after line 575 before storing in rawset.

- `pxrt_e_classes.lua:88` - med - Swallowed pcall failure in PlaySound - Line 88 calls `pc(playSoundLocal, ...)` but the return value is ignored. If playSoundLocal fails, scripts won't know sound didn't play, breaking audio-dependent logic - Check return value or use once() to log failures.

- `pxrt_e_classes.lua:143` - med - Swallowed pcall failure in SetState - Line 143 calls `pc(wormSetState, a, s)` but ignores return. If wormSetState fails (e.g., invalid state), the script continues assuming success, causing desync between script state and actual worm state - Check return value.

- `pxrt_e_classes.lua:294` - med - Swallowed pcall failure in setAmmo - Line 294 calls `pc(setTeamWeaponAmmo, ...)` but ignores return. If it fails, the function returns 0 (success) even though ammo wasn't set - Check return value before returning 0.

- `pxrt_e_classes.lua:303` - med - Swallowed pcall failure in AddWeaponEx - Line 303 calls `pc(setTeamWeaponAmmo, ...)` after reading current ammo, but ignores return. If it fails, ammo isn't added but function returns 0 (success) - Check return value.

- `pxrt_e_classes.lua:313` - med - Swallowed pcall failure in SetWeaponDelay - Line 313 calls `pc(setTeamWeaponDelay, ...)` but ignores return. Weapon delay won't be set on failure but script assumes success - Check return value.

- `pxrt_e_classes.lua:348` - med - Swallowed pcall failure in weapon delay setter - Line 348 calls `pc(setTeamWeaponDelay, ...)` in __newindex metamethod. Failures are silent, causing scripts to think they set delay when they didn't - Check return or log failures.

- `pxrt_e_classes.lua:517-523` - high - Per-frame allocations in CheckName hot path - CheckName is called every frame per sprite-builder object (line 1 comment confirms this). Lines 520-522 call `normWanted(s)` which creates cache entries, and 524-533 call `normNames(self)` which reads memory and potentially creates nameCache entries. While these use caches, cache misses allocate tables every frame - Pre-warm caches or use interned string table.

- `pxrt_e_classes.lua:537-550` - high - String normalization in CheckName hot path - CheckName (lines 536-551) calls `normWanted(want)` at line 540 which calls `normW(s)` (line 514). `normW` does `tostring():lower():gsub("[^%w]", "")` - three string operations per call on cache miss. With many sprite objects checking names every frame, this is expensive - Intern normalized weapon names at startup.

- `pxrt_e_classes.lua:336` - med - Off-by-two weapon index bug in Stores Count setter - Line 336: `__newindex = function(_, j, v) setAmmo(team, ti(j) - 2, v) end`. The getter at line 331 uses `ti(j) + 2`, but setter uses `ti(j) - 2`. This is inconsistent and causes wrong weapon slot to be set - Should be `setAmmo(team, ti(j), v)` (no adjustment needed, setAmmo handles it).

- `pxrt_e_classes.lua:97` - low - Fixed-point conversion loses sub-pixel precision - DoExplosion converts coordinates at line 97: `floor(tf(x) * 65536.0 + 0.5)`. The `+ 0.5` rounds to nearest, which is correct for fixed-point. However, if PX semantics use truncation instead of rounding, this causes explosions to detonate 0.5 pixels off - Verify PX uses rounding, not truncation, for float-to-fixed conversion.

- `pxrt_e_classes.lua:157` - low - Hardcoded explosion parameters in CMine::Explosion - Line 157 uses `DoExplosion(..., 50, 50, 0, 0)` with hardcoded push=50, damage=50. Real mines may have different values based on scheme settings or mine type - Read actual mine damage/push from game state or mine object fields.

- `pxrt_e_classes.lua:336` - high - Weapon index off-by-two causes wrong ammo slot write - Stores.Count setter at line 336 uses `setAmmo(team, ti(j) - 2, v)` but setAmmo at line 292 already adds 2 internally (line 294: `ti(widx) + 2`). This double-adjusts: writing to index j writes to slot j-2+2=j in engine, but getter reads j+2, causing mismatch - Remove the `- 2` from line 336.

## Notes

- Could not verify if `E.copyLaunch` at line 590 validates the table structure before copying, or if malformed launch tables cause memory corruption.
- Could not verify if `E.checkCollision` (lines 371, 375) handles null obj parameter correctly when called from scripts.
- Could not verify the exact ProjectX semantics for integer division and float-to-fixed conversions to confirm if runtime matches.
