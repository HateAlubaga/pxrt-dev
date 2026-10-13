# rt_pxrt_e_game

Based on my audit of `pxrt_e_game.lua`, here are my findings:

## Findings

- `pxrt_e_game.lua:209` - **high** - Wrong fixed-point write semantics for `landSelectX`/`landSelectY`. Uses `wr(addr, ti(v))` which writes raw integer, but reading at lines 189,193 uses `/65536.0` (fixed-point to float conversion). When a script sets `GS.landSelectX = 100.5`, this writes `100` instead of `6586368` (100.5 * 65536), causing position to be off by factor of 65536. Fix: change `wr(w.__a + (k == "landSelectX" and 0x2E0 or 0x2E4), ti(v))` to `wrf(w.__a + (k == "landSelectX" and 0x2E0 or 0x2E4), v)`.

- `pxrt_e_game.lua:252` - **medium** - Missing `ti()` wrapper on fallback random. Line 251 returns `ti(v)` from `jellyRandomInt`, but line 252 returns raw `math.random(0, n - 1)` without `ti()`. Type inconsistency: callers may expect integer but get Lua number. Fix: `return ti(math.random(0, n - 1))`.

- `pxrt_e_game.lua:250-252` - **medium** - Pcall silently swallows `jellyRandomInt` failures. If `jellyRandomInt` is unavailable or throws for any reason, code falls back to `math.random` with no warning. Scripts relying on DDGame random sequence get different results, breaking determinism. Fix: log once on failure: `if not ok then once("jellyRandomInt", "jellyRandomInt unavailable, using math.random fallback") end`.

- `pxrt_e_game.lua:134,143` - **medium** - No validation of `wormHealthAddr` return value. If `dd == 0`, `wormHealthAddr` returns 0, then `rd(0)` or `wr(0, v)` is called. While engine may handle this safely, semantically wrong. Scenario: accessing `Teams[0].Worms[0].Health` before game starts (ddGame() == 0) reads/writes address 0. Fix: check result in lines 134,143: `local addr = wormHealthAddr(team, worm); if addr == 0 then return 0 end; return rd(addr)` and similar for write.

- `pxrt_e_game.lua:189,193` - **low** - Inconsistent return types in `landSelectX`/`landSelectY`. Normal case returns float (`rd(...) / 65536.0`), fallback returns integer `32768`. While Lua coerces integers to floats, semantically inconsistent. Scenario: when `curWorm()` returns nil, caller gets integer 32768 instead of float. Fix: change `32768` to `32768.0`.

- `pxrt_e_game.lua:126-154` - **high** - Per-frame allocation in Teams proxy. Each access to `Teams[i]` creates new table + metatable + nested Worms table + nested metatable. If a script loops `for i=0,5 do local h = GS.Info.Teams[i].Worms[0].Health end`, creates 6 tables + 6 metatables + 6 Worms tables + 6 Worms metatables per frame. Fix: cache team proxies in a weak table keyed by team index, return cached proxy if exists.

- `pxrt_e_game.lua:220` - **medium** - Per-access allocation in `machColors`. Each read of `GG.machColors` creates new table + metatable. If accessed per-frame, allocates repeatedly. Scenario: script reads `GG.machColors[i]` in a per-frame loop. Fix: create `machColors` proxy once and cache in `E.machColorsProxy`.

- `pxrt_e_game.lua:36-45` - **low** - Repeated length computation in `allWorms`. Loop uses `out[#out + 1]` which recomputes length each iteration (Lua 5.3 optimizes this for pure arrays, but explicit tracking avoids any risk). Minor CPU cost, only if called per-frame. Fix: use local counter: `local n = 0; ... out[n+1] = proxy; n = n + 1`.

- `pxrt_e_game.lua:64-70` - **low** - Potential nil-index on invalid type. Line 69 calls `rdU(data + 4 * i)` where `data` comes from `rdU(env + 0x18 + 0xC)`. If `rdU` can return nil for invalid addresses (not just 0), line 68 `okAddr(data)` checks for valid range but `rdU` on line 69 might still fail on nil. Check if `rdU` ever returns nil; if so, add explicit nil check: `if not okAddr(data) or data == nil then return nil end`.

## Notes

- Did not verify semantic correctness of worm state value `135` at line 137 (marked as "free slot") - assumes comment is accurate
- Did not verify display resolution hardcoded values at line 167 (1280x720) - marked as "plausible" so may be intentional approximations
- Display drawing functions (lines 161-176) are intentional no-ops per comment - not a bug
- Could not verify if `rd`/`wr` engine functions handle address 0 safely - flagged as semantic issue regardless
- methodClosure allocations (lines 94, 203, 224, 232, 239) are cached per (class, method) and not per-call - verified in pxrt_core.lua:330-340
