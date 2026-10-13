# rt_pxrt_e_terrain

Based on my audit of `pxrt_e_terrain.lua`, here is my report:

## Findings

- `pxrt_e_terrain.lua:49` - low - pcall failure on `WA_WATERLEVEL()` is silently swallowed in `setWaterLevel` - if the thiscall fails, water level is set in memory but WA's internal update doesn't run, potentially causing visual desync - log the error with `once()` similar to `makeHole`

- `pxrt_e_terrain.lua:85` - low - pcall failure on `landColor` vtable call is silently swallowed - if callThiscall fails, returns 0 with no indication that the operation failed vs legitimate color 0 - add `once()` logging on failure

- `pxrt_e_terrain.lua:109-110` - low - pcall failure on `maskHitsLand` vtable call is silently swallowed - returns false on both legitimate "no hit" and on call failure, making debugging impossible - add `once()` logging to distinguish call failure from no-hit result

- `pxrt_e_terrain.lua:115-116` - low - pcall failure on `traceLand` vtable call is silently swallowed - returns -1 on failure with no logging, same return value as some legitimate results - add `once()` logging on pcall failure

- `pxrt_e_terrain.lua:69-80` - medium - `landProbe()` allocates a new closure on every call - used in hot paths like `pxrt_e_soft.lua:543` (per-frame physics) and `pxrt_e_soft.lua:133` (collision loops), allocating closures repeatedly - cache the probe at module level or pass bitmap pointers through a reusable structure

- `pxrt_e_terrain.lua:131-133` - medium - `checkCollision` calls `solid(x, y)` up to 5 times per collision check - each `solid()` call does `floor(x)`, `floor(y)`, `P()`, memory reads, bounds checks - called from `CEnv.CheckCollision` which may be invoked frequently - cache `P()` and bitmap pointers, or use `landProbe()` pattern

- `pxrt_e_terrain.lua:137-139` - low - pcall failure on WA hittest (stdcall) is silently swallowed in `checkCollision` - if the hittest call fails, returns nil (same as "no collision"), making it impossible to distinguish call failure from legitimate no-hit - add `once()` logging on pcall failure

- `pxrt_e_terrain.lua:123` - medium - `TERRAIN` marker object allocated at module load with setmetatable - the metatable's `__index` function allocates a closure - every access to undefined keys on TERRAIN will invoke this closure returning 0 - use a table with explicit zero values or `{__index = {}}` pattern to avoid closure allocation per access

## Notes

- Line 34: `waterLevel()` returns `rd(e + 0x228) + 0.0` which reads an integer pixel value, not fixed-point - verified against `harness\mock_dll.lua:270` and `pxrt_engine.lua:21,34-35` where fixed-point uses `FIX=65536.0` and `rdf()` - the comment "float, PX fixed" is confusing but the implementation appears correct
- Did not verify vtable offsets (0x1C, 0x08, 0x0C, 0x10, 0x24) against actual WA 3.8.1 memory layout
- Did not verify whether `mask` and `flags` parameters in `checkCollision` are actually used (they're read from the object but not passed to terrain checks)
