# rt_pxrt_e_structs

Now let me analyze the full code. I have enough information to complete the audit. Let me compile my findings:

## Findings

- `pxrt_e_structs.lua:27` - high - `memFill` failure on buffer acquisition is silently ignored via unguarded `pcall` - if `memFill` fails (invalid address, protection fault), the buffer returns with uninitialized garbage that the engine will read - wrap in `pcall` with error check: `local ok = pcall(memFill, a, 0, size); if not ok then once("memfill", "pxrt: memFill(%d, 0, %d) failed", a, size); return 0 end`

- `pxrt_e_structs.lua:48-49` - med - `setKind` writes fixed-point without proper rounding - `tf(v) * FIX` can produce non-integer results (e.g., `1.1 * 65536.0 = 72089.6`), but `wr` expects integers and will floor them in `pxrt_engine.lua:30`, causing precision loss vs ProjectX which rounds - change to `wr(a, floor(tf(v) * FIX + 0.5))`

- `pxrt_e_structs.lua:110` - high - `GetParameter` bypasses array bounds check - reads raw memory at `bufOf(self) + 4 * ti(i)` without checking `i < 0 or i >= 256`, but `__index` metamethod at lines 59-64 enforces this - inconsistent behavior; out-of-bounds `GetParameter(msg, 300)` reads invalid memory instead of returning 0 - add bounds check: `i = ti(i); if i < 0 or i >= 256 then return 0 end; return rd(bufOf(self) + 4 * i)`

- `pxrt_e_structs.lua:180-182` - low - `loadLaunchFields` pcall failure silently falls back to empty table - if `require("pxl_launch")` fails for reasons other than missing file (syntax error, runtime error during load), the error is swallowed and all launch fields become "unknown", disabling weapon launch customization - log the failure: `if ok and type(v) == "table" then t = v elseif not ok then once("pxl_launch", "pxrt: require pxl_launch failed: %s", tostring(v)) end`

- `pxrt_e_structs.lua:232-235` - high - cached sub-object in `__subs` holds stale buffer address after object moves - if a CWeaponLaunch object's `__buf` changes (e.g., via `__addr` access triggering `lBuf`), the cached sub-object at line 235 still references the old `__b = lBuf(t)` captured at creation time, causing reads/writes to wrong memory - store `__parent` instead and compute address dynamically: in `subMT.__index` (line 201): `local spec = rawget(t, "__f")[k]; if spec then return getKind(rawget(t, "__parent").__addr + spec.off, spec.kind) end`

- `pxrt_e_structs.lua:235` - med - per-frame allocation of sub-object tables creates GC pressure - every access to `launch.Phys` or similar sub-struct after cache miss allocates a new table with metatable; in tight loops (per-projectile updates) this creates hundreds of tables per frame - for read-only sub-objects, consider interning or reusing a single proxy per parent object

- `pxrt_e_structs.lua:276` - med - `copyLaunch` pcall failure is silent - if `memCopy` fails (bad address, protection fault), the operation silently does nothing, leaving destination with stale/uninitialized data that the engine reads - check result: `local ok = pcall(memCopy, d, s, LAUNCH_SIZE); if not ok then once("copyl", "pxrt: memCopy launch failed") end`

- `pxrt_e_structs.lua:293` - med - `F.zero` override uses `pcall` for `memFill` without checking result - if `memFill` fails, `F.zero` returns 0 as if it succeeded, but the struct memory is not zeroed, causing unpredictable engine behavior - check pcall result: `local ok = pcall(memFill, a, 0, sz); if not ok then once("zero", "pxrt: memFill zero failed") end`

- `pxrt_e_structs.lua:91-93` - low - `params` and `fparams` views are cached in the object table, persisting across pool reuse - when a CMessageData object is GC'd, its buffer returns to the pool, but the cached `params` table at rawset line 91 stays in the object; if the object is resurrected or the table accessed after release, reads hit freed memory - clear cached views in `__gc`: `rawset(t, "params", nil); rawset(t, "fparams", nil)`

- `pxrt_e_structs.lua:257` - low - weak-valued `launchViews` cache can cause view object churn - the cache uses `__mode = "v"`, so if no script holds a reference to the view, it's GC'd and the next `E.launchAt(addr)` allocates a new one, even for frequently-accessed addresses (e.g., current weapon launch) - not a bug but inefficient; consider strong cache with size limit or per-frame clear

- `pxrt_e_structs.lua:292` - low - `F.zero` reads `target.__addr` as fallback without checking if it returns 0 - line 292 tries `rawget(target, "__a")`, `rawget(target, "__buf")`, then falls back to `target.__addr` which may trigger `__index` metamethod; if that returns 0 (buffer not allocated yet), `memFill(0, 0, sz)` is called - the `if a and a ~= 0` guard on line 293 prevents the call, but the metamethod invocation allocates the buffer unnecessarily - check `a` existence before fallback: `if not a then local addr = target.__addr; if addr ~= 0 then a = addr end end`

## Notes

- Could not verify if `readMemInt`, `writeMemInt`, `readMemU32`, `memAlloc`, `memFill`, `memCopy` (native functions from wkJellyWorm) handle invalid addresses gracefully or crash; assumed they may fail and pcall is appropriate.
- Could not verify if ProjectX uses banker's rounding, round-half-up, or truncation for fixed-point writes; assumed round-half-up based on common fixed-point convention.
- Did not audit `pxl_launch.lua` field definitions for correctness (out of scope); assumed offsets and kinds are correct if present.
- Sub-object caching issue (finding #5) is the most severe: stale buffer addresses cause memory corruption if objects are pool-recycled or moved.
