# rt_pxrt_core

Now I have enough context. Let me analyze the code for the specific issues requested. Based on my complete reading of pxrt_core.lua, I can now generate the audit report.

## Findings

- `pxrt_core.lua:314-323` - med - Per-frame closure allocation in hot path - When methods are accessed on objects, `methodClosure` creates and caches closures via `function(self, ...) return invoke(self, clsName, m, ...) end`, but the cache lookup and closure wrapper still executes on every method access through `__index` metamethod - Pre-allocate method closures during class registration rather than on first access to eliminate the cache lookup in the hot path.

- `pxrt_core.lua:330-336` - med - String concatenation in hot `__index` metamethod - The `scriptMTFor` metamethod performs `type(k) == "string"` check and `buildChain(clsName, k)` lookup on every field/method access, including in per-frame game loops - Cache the full method set per class during invalidation and use simple table lookup in `__index`.

- `pxrt_core.lua:116` - low - String concatenation allocates in hot path - `cat` function does `str(a) .. str(b)` which allocates new strings; transpiled code calls this for PX string concatenation which may occur in frame loops - Consider reusing a string buffer or document that hot string ops are unavoidable.

- `pxrt_core.lua:579` - med - Closure allocation in overload dispatcher - When overloaded methods exist, `ovRegister` creates dispatcher closures `function(self, super, ...) return ovPick(list, 2 + select("#", ...), ...)(self, super, ...) end` that allocate on every call - Acceptable if overloads are rare; document if this is a known cost.

- `pxrt_core.lua:566` - high - Missing nil check causes potential crash - `ovRegister` calls `debug.getinfo(fn, "u").nparams` without checking if `debug.getinfo` returns nil (it can fail for C functions or in restricted environments) - Add nil check: `local info = debug.getinfo(fn, "u"); if not info then return fn end`.

- `pxrt_core.lua:405` - high - Constructor failure is logged but object still returned - When `pcall(runCtor, ...)` fails with `ok == false`, the error is logged but the partially-constructed object is still returned to caller, potentially with missing fields or invalid state - Return a null sentinel or valid empty object on constructor failure instead of returning broken object.

- `pxrt_core.lua:706-710` - med - Chunk load failures return false but caller may not check - `loadChunk` returns `false` on compile/load errors, but callers at lines 735, 757 don't check return value in loops - Check `loadChunk` return value and skip ginit/registration when chunk fails to load.

- `pxrt_core.lua:825-826` - med - ginit error swallowed in matchReset - `matchReset` wraps ginit calls in pcall and only logs errors; if a ginit rebuilds critical per-match state and fails, the match continues with stale/missing globals - Consider propagating critical ginit failures or setting an error flag that halts match initialization.

- `pxrt_core.lua:509` - low - Double metamethod lookup inefficiency - `newG` metamethod `__index` does `local v = rawget(parentList[i], k); if v == nil then v = parentList[i][k] end` which first does rawget then falls through to the parent's metamethod - This is intentional to bypass parent metamethods only after checking raw value, but could clarify with comment.

- `pxrt_core.lua:87` - med - Integer division asymmetry vs C/C++ - `div` function for integer division uses `q = a // b; if q < 0 and q * b ~= a then q = q + 1` which rounds toward zero for consistency with C, but Lua's `//` rounds toward negative infinity - Verify this matches ProjectX's integer division semantics exactly; a test case with negative dividends is needed.

- `pxrt_core.lua:64` - low - Float-to-int truncation uses floor-based approach - `ti` function converts floats to integers using `v >= 0 and floor(v) or -floor(-v)` which truncates toward zero, but doesn't explicitly handle -0.0 edge case - Verify that negative zero is handled correctly in ProjectX semantics.

- `pxrt_core.lua:308` - low - Cache invalidation creates garbage - `invalidate()` discards entire `chainCache`, `typedCache`, and `wantsAnyCache` tables, potentially containing thousands of entries - This happens on class registration (rare), but the garbage spike might cause frame drops if classes are registered during gameplay.

- `pxrt_core.lua:834` - med - Engine load failure is logged but runtime continues - `pcall(require, "pxrt_engine")` failure only logs error; if engine layer is essential, the runtime returns in broken state - Consider returning nil or error object if engine layer is required for functionality.

- `pxrt_core.lua:477` - low - Delete falls back to Free method without checking callable - `delete` function does `local f = o.Free; if type(f) == "function" then pcall(f, o, 1)` where `o.Free` might hit the `__index` metamethod returning 0 (line 335), then `type(0) == "function"` correctly fails, but this is implicit - Current code is correct but could be clearer with comment explaining Free=0 default.

- `pxrt_core.lua:647` - low - Constructor overload fallback is underspecified - When no exact parameter count match exists for overloaded constructors, the code picks "best <= n else smallest", but doesn't document what happens if `set` table is empty - This case should be impossible (set is only created when multiple ctors exist), but lacks defensive check.

## Notes

- Could not verify fixed-point arithmetic semantics without access to original ProjectX fixed-point implementation; `tf` and floating operations appear standard but would need comparison testing.
- Message filter optimization (lines 242-250, 252-276) uses K constants that come from engine layer; could not verify filter correctness without reading pxrt_engine.lua.
- Several pcall wrappers swallow errors at lines 415, 471, 477, 737, 759, 812, 825 - verified these are appropriate for optional callbacks and initialization functions.
- `__a` field usage (lines 69, 134, 475) is undocumented in this file; appears to be engine-provided address/handle for native objects.
