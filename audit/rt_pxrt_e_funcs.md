# rt_pxrt_e_funcs

Now let me systematically analyze the code. I'll document my findings as I go through the file:

## Findings

- `pxrt_e_funcs.lua:23-29` - high - `pc` function silently swallows all errors with `pcall` and logs once, then returns `nil` on failure. This means native call failures (registerCustomSprite, playSoundLocal, etc.) silently disable features without propagating errors. When a native function fails, scripts get `nil` instead of a valid object/result. Suggested fix: return a sentinel value (0 or empty object) that matches PX semantics instead of `nil`, or propagate the error to the caller.

- `pxrt_e_funcs.lua:112` - med - `F.IsReplay` uses `pcall` to catch errors from `isReplayPlayback()`, but if the function doesn't exist or throws, it returns 0 (false). This is correct for safety, but the error is not logged, making it hard to diagnose why replay detection fails. Suggested fix: add `once()` logging when pcall fails.

- `pxrt_e_funcs.lua:137-138` - med - `F.IsKeyPressed` uses `pcall` to catch errors from `isKeyDown()`, but if the function doesn't exist or throws, it silently returns 0. Same issue as IsReplay - no logging. Suggested fix: add `once()` logging when pcall fails.

- `pxrt_e_funcs.lua:147-148` - med - `F.GetWeaponByName` uses `pcall` to call `weaponIdByName`, but if it fails, `id` stays -1 and the function still calls `E.weaponById(-1, name)`. This may or may not be the correct behavior, but the error is not logged. Suggested fix: add `once()` logging when pcall fails.

- `pxrt_e_funcs.lua:216-239` - low - `assetCache` table grows unbounded. Every unique `unit.name|asset_name` combination is cached forever. In long-running games with many scripts loading different assets, this could slowly leak memory. Suggested fix: use a weak-keyed cache or add a cache size limit with LRU eviction.

- `pxrt_e_funcs.lua:249-250` - med - `F.LoadSprite` uses `pcall` to call `registerCustomSprite`, and if it fails, `id` stays 0, creating a sprite object with Index=0. Scripts can't distinguish between a failed load and a valid sprite. The error is not logged. Suggested fix: add `once()` logging when pcall fails, and optionally return a sentinel value.

- `pxrt_e_funcs.lua:317-318` - med - `BC.CSoundFile` constructor uses `pcall` to call `registerCustomSound`, and if it fails, `id` stays 0. The sound object is created but won't play. The error is not logged. Suggested fix: add `once()` logging when pcall fails.

- `pxrt_e_funcs.lua:327-330` - low - `CSoundFile:Play` creates a closure for every sound file object. If scripts create many sound objects (e.g., one per sound effect), this allocates a new closure per object. Suggested fix: use a shared function that reads `self.Index` instead of capturing `self` in each closure - but this is likely premature optimization since sound objects are probably not created in hot paths.

- `pxrt_e_funcs.lua:340` - low - `BC.CBitmap` uses `w or 0` and `h or 0` which converts `false` to 0. If a script passes `false` for width/height, it gets 0 instead of an error. This is defensive but may hide bugs. Suggested fix: use explicit nil checks: `w ~= nil and w or 0`.

- `pxrt_e_funcs.lua:370-382` - med - `BF.GetCurrentWorm` creates a new closure on every call (captures `CW`). According to the comment, this is "called once per script override per message (hundreds of times per frame)", making it a hot path. The closure allocation is per-frame CPU waste. Suggested fix: make it a direct function that accesses `E.CW` instead of capturing `CW` in the closure - but checking the code, `CW` is already `E.CW`, so the closure is unnecessary. Define `BF.GetCurrentWorm` as a named function instead of an anonymous one.

- `pxrt_e_funcs.lua:384-387` - low - `BF.PCMessageData_intP` calls `ti(addr)` then `E.msgDataAt(...)` which may return nil. If nil, the function returns 0. This is correct PX null semantics, but there's no logging to indicate when a bad address is passed. Consider adding a `once()` log when `E.msgDataAt` returns nil due to bad address.

- `pxrt_e_funcs.lua:427-440` - high - `mc` function (method call dispatcher) checks `if o == nil or o == 0` at line 436, but the check comes AFTER attempting to read `o[name]` at line 430 and `rawget(o, "__cls")` at line 432. If `o` is nil, lines 430-434 will cause a nil-index error ("attempt to index a nil value"). The nil check should come first. Suggested fix: move the `if o == nil or o == 0` check before `if t == "table"`.

- `pxrt_e_funcs.lua:442-452` - med - `call` function checks `if type(self) == "table"` and accesses `self[name]`, but if `self` is nil, the type check passes (returns "nil"), then `rawget(F, name)` is called. This is safe, but the logic is unclear. If `self` is nil, should it still try to call a builtin? Consider documenting this behavior or making it explicit. Suggested fix: add a comment explaining that nil/non-table objects fall through to builtin lookup.

- `pxrt_e_funcs.lua:14-21` - med - `F` metatable `__index` creates a stub function on every missing builtin access, logs once with `once()`, then caches the stub. The stub always returns 0. This is correct for missing functions, but the stub is a fresh closure allocation per missing function. If many missing functions are called, this allocates many closures. Suggested fix: use a single shared stub function instead of creating a new one per missing key.

- `pxrt_e_funcs.lua:192-214` - low - `searchOrder` function allocates three tables (`order`, `seen`, `queue`) on every call. This is called by `E.resolveAsset` which is called by `asset()` which is called by `F.GetAttachment`, `F.LoadSprite`, etc. If assets are loaded in a hot path (unlikely, but possible), this is allocation waste. Suggested fix: cache the search order per unit, since unit dependencies don't change at runtime.

- `pxrt_e_funcs.lua:267-275` - low - `overrideSrc` function is called by `F.SetSpriteOverride` and `F.SetWeaponSpriteOverride`. It returns multiple values `(s, x, y)`. If `src` is a table with `Index > 0`, it returns `(id)` (one value), not three. The callers at lines 278-279 and 285-286 unpack three values, so `x` and `y` will be nil when `Index > 0`. This may or may not be correct depending on what the native functions expect. Verify that `SetSpriteOverride(target, id, nil, nil)` is correct when `src` is a sprite object. Suggested fix: explicitly return `(id, nil, nil)` for clarity.

## Notes

- Could not verify if `pcall` failures in native calls are expected to be silent or should propagate errors - depends on PX behavior when a feature is unavailable.
- Could not verify if the `mc` nil-index issue at line 430-434 is actually triggered in practice - depends on whether transpiled code ever calls `mc(nil, ...)`.
- Could not check the ProjectX sources to confirm fixed-point usage - only saw fixed-point conversion in `rdf`/`wrf` (engine layer), not in this file.
- Could not verify if asset loading happens in hot paths - the code assumes it's initialization-time only.
