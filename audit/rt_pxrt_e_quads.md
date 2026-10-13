# rt_pxrt_e_quads

Perfect. Now I have all the context I need. Let me compile my audit findings:

## Findings

**pxrt_e_quads.lua:102** - high - Index calculation uses 1-based Lua convention but should be 0-based for flat array packing. The formula `o = n * 24` assumes `n` starts at 0, but when `n=0`, `o=0`, and the first element is stored at `b[1]` (line 103), which is correct. However, the offset calculation `o + 1`, `o + 2`, etc. means for `n=0`: indices 1-24, for `n=1`: indices 25-48. This is correct for Lua 1-based arrays, but the comment on line 3 says "flat array, 24 numbers per quad" suggesting 0-based packing might be expected by the C++ side. Need to verify pxQuadSubmit expects 1-based or 0-based. - If C++ expects 0-based, change to `b[o] = sprite; b[o + 1] = frame` etc.

**pxrt_e_quads.lua:57** - low - pcall error on cellOf is silently converted to 0,0 dimensions. If the native pxSpriteCell fails unexpectedly (not just for invalid IDs), quads will render with zero size, making debugging difficult. The known log "beam_glow.png not found" suggests sprite loading failures do occur. - Add once() logging when pcall fails: `if not ok then once("cellOf:" .. tostring(id), "pxrt: pxSpriteCell(%d) failed: %s", id, tostring(w)) end`

**pxrt_e_quads.lua:74-75** - med - Horizontal mirroring check uses bitwise AND on potentially non-integer sprite IDs. Line 74 checks `math.type(id) == "integer"` which is correct, but if `id` is a float due to upstream bug, the mirroring won't apply and sprites render wrong. ProjectX uses integer sprite IDs, so receiving a float indicates a type coercion error that should be caught. - Add warning when ID is numeric but not integer: `elseif type(id) == "number" then once("sprite-float:" .. tostring(id), "pxrt: sprite ID %.2f is not an integer, mirroring disabled", id)`

**pxrt_e_quads.lua:87** - low - tf() conversions are called per-vertex in the transform loop (line 91: `tf(p.x or 0)`, `tf(p.y or 0)`). These are hot-path allocations since tf() is called 8 times per quad (4 vertices × 2 coordinates). The vertex coordinates should already be numbers from FillSpriteQuad, so tf() is defensive but wasteful. - Pre-convert once before the loop: `rot, sx, sy, x, y = tf(rot or 0), tf(sx or 1), tf(sy or 1), tf(x or 0), tf(y or 0)` is good, but also pre-check vertices are numbers and skip tf() in loop: `local px, py = p.x * sx, p.y * sy`

**pxrt_e_quads.lua:103** - med - Blend mode retrieval uses `rawget(q, "blend") or 0`. If blend is explicitly set to `false` (truthy but not a number), it will pass through as a non-numeric value to the native pxQuadSubmit, potentially causing a fault. ProjectX expects blend to be an integer enum. - Change to `(rawget(q, "blend") or 0) + 0` to force numeric, or better: `ti(rawget(q, "blend") or 0)` for integer semantics.

**pxrt_e_quads.lua:126** - low - RenderQuad inside a custom render function accumulates quads into cbuf with cn as the count. If two nested custom renders both call RenderQuad, cn increments across both, which is correct per line 166 comment "nested: its quads join the outer batch". However, if cn overflows (many quads), put() will write beyond allocated buffer bounds. No bounds check exists. - Add warning when cn exceeds a threshold: `if cn > 1000 then once("cbuf-large", "pxrt: custom render batch has %d quads, possible memory issue", cn) end`

**pxrt_e_quads.lua:138-139** - med - spriteId() is called twice for AddSpriteQ: once at line 138 for the explicit sprite param, and again implicitly if id==0 at line 139. The second call at line 139 calls spriteId on `rawget(q, "tex")` which is already an ID (stored as integer by FillSpriteQuad line 77), so the spriteId call is redundant. Not a bug but wasteful. - Remove redundant call: `if id == 0 then id = rawget(q, "tex") or 0 end`

**pxrt_e_quads.lua:145-158** - med - Custom render function cache uses weak-keyed table (line 145: `__mode = "k"`), so fnCache entries are garbage collected when the unit object is collected. However, line 150 creates a new cache `c = {}` for each unit, and this cache is stored with the unit as key. If the unit is a temporary object that gets collected frequently, the cache rebuilds often, defeating its purpose. Need to verify units are long-lived. - If units are transient, change to weak-value cache or use unit ID as key instead of unit object.

**pxrt_e_quads.lua:153** - low - Function lookup stores `false` sentinel (line 154) to cache negative results, but returns `nil` (line 157: `return fn or nil`). This is correct, but the `or nil` is redundant since `false or nil` is already `nil`. - Simplify to `return fn or nil` → `return fn or nil` is fine, or just `return fn ~= false and fn or nil` for clarity.

**pxrt_e_quads.lua:167-168** - low - Nested custom render function failure is logged with once(), but the error is not propagated. If the nested function fails, the outer function continues, potentially with incomplete rendering. The known log "method CheckName called on null" suggests null reference errors do occur. - Consider re-throwing after logging if the error is critical: check error message for "null" and propagate.

**pxrt_e_quads.lua:185** - low - Scale parameter default (line 185: `if scale == 0 then scale = 1 end`) only handles exact zero, not nil. If caller passes nil, scale becomes nil, then line 187's TransformQuad receives nil, which tf() converts to 1.0 (line 87). This works but is inconsistent with the check. - Change to `if not scale or scale == 0 then scale = 1 end` for explicit nil handling, or remove the check since tf() handles it.

**pxrt_e_quads.lua:195-197** - low - quadStats() wraps stats() in pcall and returns nil on failure. If the DLL stats function fails transiently (e.g., during teardown), the caller gets nil with no logging. Stats are diagnostic, so silent failure is acceptable, but unexpected failures should be logged once. - Add once() logging: `if not ok then once("qstats", "pxrt: pxQuadStats failed: %s", tostring(b)); return nil end`

## Notes

- Could not verify whether pxQuadSubmit expects 0-based or 1-based array indices. The Lua code uses 1-based (b[1], b[2], ...), which is Lua-idiomatic, but the C++ side needs confirmation.
- Did not analyze sbuf/cbuf buffer reuse patterns across frames. If these buffers grow unbounded and are never cleared, they could leak memory, but the code reuses sbuf for one-shot batches (resets index to 0) and cbuf for custom renders (cn resets to 0 after send), so this appears safe.
- The `collecting` flag (line 117) is a module-level global, so concurrent custom renders would interfere. However, ProjectX scripts are single-threaded per the runtime model, so this is not an issue.
- Did not trace whether vertex color values (0xFFFFFFFF) are correct ARGB format vs RGBA. The comment on line 3 says "ARGB colour", so line 69-72 default colors are correct.
- The transform math (line 88-93) uses standard 2D rotation matrix, which matches ProjectX semantics for rot in radians.
