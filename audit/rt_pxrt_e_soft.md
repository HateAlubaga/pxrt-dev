# rt_pxrt_e_soft

Now I have enough information to compile my audit report. Let me analyze the findings:

## Findings

- `pxrt_e_soft.lua:485-489` - **medium** - pcall silently discards gravityFactor/windFactor read errors. If the property getter throws (malformed launch data), the object gets default factors (GravityFactor=1.0, WindFactor=0.0) with no warning. Missiles with incorrect physics fall through unnoticed. **Fix**: Check `ok` and log failures with `once()`, or validate the launch block structure before reading.

- `pxrt_e_soft.lua:530-531` - **low** - pcall swallows script callback errors in `callScript()`, logs once per class+method, but returns `true` even when the callback failed. Caller at line 564 (`OnSink`) and 617 (`Collide`) cannot distinguish success from pcall-caught failure. **Fix**: Return `ok` from `callScript` so callers know the callback ran successfully.

- `pxrt_e_soft.lua:544` - **high** - bitwise AND on potentially nil value. If `rawget(o, "ColGroup")` returns nil, `ti(nil)` returns 0, but the fallback `ALL_GROUPS` (0xFFFFFF) is only used when the entire expression is nil. The expression `ti(rawget(o, "ColGroup") or ALL_GROUPS) & 2` evaluates as `ti(nil or 0xFFFFFF) & 2`, which is correct. However, if ColGroup is explicitly 0 (valid in PX), the condition becomes `0 & 2 == 0`, disabling terrain collision incorrectly. **Fix**: Change to `ti(rawget(o, "ColGroup") or ALL_GROUPS)` so 0 is preserved and only nil gets the fallback.

- `pxrt_e_soft.lua:567` - **medium** - incorrect float semantics for SinkSpeedFactor. `fld(o, "SinkSpeedFactor") ~= 0 and fld(o, "SinkSpeedFactor") or 1.0` calls `fld()` twice when non-zero, and incorrectly returns the factor itself instead of using it as a boolean flag. PX SinkSpeedFactor is a multiplier; 0.0 means "don't sink" but this treats it as "use 1.0". **Fix**: `local ssf = fld(o, "SinkSpeedFactor"); (ssf ~= 0 and ssf or 1.0)` or just `fld(o, "SinkSpeedFactor")` if 0 already means no sinking.

- `pxrt_e_soft.lua:232` - **medium** - per-frame allocation in `worldObjs()`. Every call that misses the cache (tick/version/n/life change) allocates a new `list = {}` table. Called by `candidates()` (lines 289, 329) which is invoked by every `FindInMask`, `CheckMaskAt`, and `_TraceMask` call. High object count + multiple collision queries per frame = dozens of allocations. **Fix**: Reuse the cache table by clearing it (`for i = #list, 1, -1 do list[i] = nil end`) instead of allocating fresh.

- `pxrt_e_soft.lua:288` - **medium** - per-query allocation in `candidates()`. Allocates `out = {}` for every collision query. `FindInMask` / `CheckMaskAt` / `_TraceMask` are called from scripts potentially dozens of times per frame. **Fix**: Cache and reuse a candidates table, cleared before each use.

- `pxrt_e_soft.lua:93` - **low** - per-call allocation in `outlineOf()`. Allocates `ol = {}` every time the outline is not cached. First call per mask is unavoidable, but if `__outline` is cleared (line 36, 73), the next access re-allocates. Bitmap mutation is rare after construction, so low impact. **Fix**: None needed unless profiling shows this as hot.

- `pxrt_e_soft.lua:531` - **low** - per-failure string concatenation in hot path. `"soft:" .. cls .. name` allocates 3 strings (2 intermediate + 1 final) every time a script callback fails. Repeated failures (e.g., broken `OnSink`) concatenate every frame until `once()` suppresses. **Fix**: Pre-format the key or use `string.format` which is slightly cheaper for multi-part keys.

- `pxrt_e_soft.lua:211` - **low** - `__index` metamethod returns 0 for all missing terrainObj fields. Scripts reading undefined fields get 0 instead of nil, masking typos (e.g., `terrainObj.PoX` returns 0, not error). **Fix**: Explicitly list known terrain fields (PosX, PosY, SpX, SpY, Layer, etc.) and return 0 only for those; return nil otherwise.

- `pxrt_e_soft.lua:402` - **low** - Bresenham condition inconsistency. Line 394 uses `if err < 0` (strict), line 402 uses `if err <= 0` (non-strict). PX CLineTracer uses `<= 0` for vertical-major (dir==1) and `< 0` for horizontal-major (dir==0). Verify this matches ProjectX; if not, pixel-precise traces diverge. **Fix**: Confirm against PX source or test cases; adjust if wrong.

- `pxrt_e_soft.lua:567` - **low** - redundant terrain collision disable. `collideTerrain = false` inside the water block means objects in water never bounce off underwater terrain. If PX allows underwater terrain collision (e.g., mines resting on the seabed), this is wrong. **Fix**: Verify PX behavior; remove the line if PX does collide underwater.

- `pxrt_e_soft.lua:475` - **low** - allocates CMineParams default every time a CMine is constructed without InitParams. Construction is rare (once per mine spawn), but the allocation is avoidable. **Fix**: Cache a shared default CMineParams instance and clone it, or construct it once outside the loop.

- `pxrt_e_soft.lua:79, 164` - **low** - stub methods return 0 but should they? `CBitmap1.DrawText`, `CColMask.SetPixel` etc. are marked as stubs (no-ops). If scripts expect these to modify state and check the result, silent no-ops break features (e.g., dynamic mask editing). **Fix**: Log once when called so unsupported features are visible, not silent.

- `pxrt_e_soft.lua:603` - **medium** - floor contact threshold `cny < -0.6` allows 53° slopes to stop objects. PX may use a different threshold (e.g., -0.7 = 45°). Missiles/mines stopping on walls instead of floors changes gameplay. **Fix**: Verify threshold against PX behavior or documents.

- `pxrt_e_soft.lua:622` - **low** - world bounds check uses magic numbers (-600, W+600, -4000). If these don't match PX exactly, objects despawn early/late. **Fix**: Verify bounds against PX or make them configurable.

## Notes

- Could not verify fixed-point semantics: no fixed-point conversions found (everything uses `ti`/`tf` for int/float).
- Could not verify return value semantics without reading calling code in transpiled scripts.
- Did not check `E.landProbe()`, `E.proxyAt()`, `E.envAddr()`, `R.scriptMTFor()` - assumed correct if defined elsewhere.
- Did not verify DumpingA/B/C default values against PX specs.
