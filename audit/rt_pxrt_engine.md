# rt_pxrt_engine

Based on my audit of `pxrt_engine.lua`, here are my findings:

## Findings

- `pxrt_engine.lua:22` - **high** - `readMemInt` is accessed without validation. If the global `readMemInt` function doesn't exist, `rd` will be nil and all memory read operations will fail with "attempt to call a nil value". Concrete scenario: wkJellyWorm API not loaded → all `rd(addr)` calls crash. Suggested fix: Add `if not readMemInt then log("pxrt: readMemInt not available"); return R end` after line 22.

- `pxrt_engine.lua:32` - **high** - `writeMemInt` is called without prior validation. If the global `writeMemInt` doesn't exist, all write operations fail. Concrete scenario: restricted Lua environment → `wr(addr, val)` crashes. Suggested fix: Check `writeMemInt` exists, similar to `readMemInt`.

- `pxrt_engine.lua:36` - **high** - `readMemU32` is called without validation in `rdU`. Concrete scenario: API incomplete → `rdU(addr)` crashes. Suggested fix: Validate global exists.

- `pxrt_engine.lua:29` - **med** - NaN check `if v ~= v` converts NaN to 0, but the subsequent integer conversion at line 30 happens unconditionally. For infinity values, `floor(inf + 0.5)` produces infinity, then line 31 clamps to int32 range. This is correct, but the NaN check should use `math.type` or be removed since line 31 handles all edge cases. Suggested fix: Remove line 29 or move clamping before NaN check.

- `pxrt_engine.lua:314` - **low** - In `__newindex` metamethod, line 314 does `wr(a + off, ti(v))` but `ti` is not defined in local scope (should be `R.ti`). Actually, checking line 16, `ti` is not imported but `R.ti` exists. Concrete scenario: writing to pointer field → undefined global `ti`. Suggested fix: Change to `R.ti(v)`.

- `pxrt_engine.lua:51` - **med** - `pcall(getTurnGameAddr)` assumes global `getTurnGameAddr` exists. If it doesn't exist or returns invalid values repeatedly, `turnGameAddr()` returns 0, silently disabling all game state access. Concrete scenario: wkJellyWorm older version without this API → all engine proxies return nil/0. Suggested fix: Check once at module load and log a clear error if missing.

- `pxrt_engine.lua:128` - **low** - `readMemBytes` called without validation. Concrete scenario: API missing → waFn verification crashes. Suggested fix: Validate global exists.

- `pxrt_engine.lua:132` - **low** - String concatenation with `gsub` in error path (line 132) creates closure per call. This is in the cold path (WA function signature mismatch), so performance is acceptable, but the hex conversion could be pre-compiled. Suggested fix: None needed (cold path).

- `pxrt_engine.lua:286-307` - **med** - The `__index` metamethod for engine proxies (lines 286-307) does string concatenation and multiple table lookups per field access. If proxies are accessed in hot loops (per-frame for multiple worms/objects), this could add up. Line 294: `rdU(a + off)` followed by `E.proxyAt()` creates nested proxies on every pointer field access. Concrete scenario: script reads `worm.Parent.Parent.PosX` 8 times per frame for 8 worms → 64 proxy creations. Suggested fix: Cache proxy references or use a flyweight pattern.

- `pxrt_engine.lua:397-398` - **high** - Module loading failure is caught by pcall and only logged. If critical modules like `pxrt_e_funcs` or `pxrt_e_hooks` fail to load, the runtime continues in a broken state with missing functions. Concrete scenario: syntax error in `pxrt_e_funcs.lua` → scripts run but all builtin functions return nil → cascade of nil-index errors. Suggested fix: For core MODULES (not extensions), error on load failure: `if not ok2 then error(string.format("pxrt: critical module %s failed: %s", m, tostring(err))) end`.

- `pxrt_engine.lua:341` - **med** - `E.syncBirths()` is called conditionally at line 341, but the function is defined in `pxrt_e_hooks.lua` which loads later. If a proxy is created before hooks module loads, this will crash. Concrete scenario: extension module creates proxy before hooks loaded → nil function call. Suggested fix: Add `if E.syncBirths then E.syncBirths() end`.

- `pxrt_engine.lua:345` - **low** - `E.onFirstSight` callback is called if it exists, but no nil check. Actually, line 345 does `if E.onFirstSight then`, so this is safe. No issue.

- `pxrt_engine.lua:261-280` - **low** - `E.intArrayAt` creates a new metatable with closures for each array instance (lines 264-277). If many int arrays are created per frame, this allocates closures. Checking line 262, there's a weak-value cache `intArrays[addr]`, so arrays at the same address are reused. Likely safe unless many distinct addresses are accessed. Suggested fix: Reuse a single metatable if possible (would require storing `addr` and `n` in the array table itself).

## Notes

- Could not verify: Whether `E.syncBirths` timing issue (finding #11) actually occurs depends on module load order.
- Could not verify: Actual per-frame CPU cost of proxy creation (finding #9) without profiling real scripts.
- Could not verify: Whether `ti` undefined issue (finding #5) exists - need to check if line 16 imports it or if there's a global fallback.
- The file references many functions from other modules (`pxrt_e_*`) that define `E.weaponMT`, `E.special`, etc. - could not verify their correctness without reading those files.
