# rt_pxrt_e_pseudo

Based on my analysis of `pxrt_e_pseudo.lua`, here is my audit report:

## Findings

- `pxrt_e_pseudo.lua:218` - medium - Silent failure on recursion depth limit - When `depth > 8`, `dispatchPseudo` returns silently without logging, which could cause engine messages to be dropped without any indication. Scripts expecting frame messages won't receive them and features will silently break. - Add `log("pxrt: dispatchPseudo depth limit hit")` before the return.

- `pxrt_e_pseudo.lua:205` - medium - Silent failure on recursion depth limit - Same issue in `forwardToKids`: depth > 8 returns silently without logging, potentially dropping child messages. - Add logging before return.

- `pxrt_e_pseudo.lua:198` - low - pcall with `once()` suppresses repeated errors - Using `once()` means after the first Message() error for a specific class+mtype combination, all subsequent errors are suppressed. If a Message handler has intermittent bugs (e.g., fails only for certain objects or states), only the first failure is logged. - Consider using regular `log()` with the repeat suppression it already provides, or track per-object-class-mtype instead of just class-mtype.

- `pxrt_e_pseudo.lua:220-221` - medium - Per-frame allocation in hot path - `dispatchPseudo` creates a new copy array every call. If called per frame (likely for M_FRAME messages), this allocates repeatedly. The copy is needed for safety (roots can change during iteration), but the allocation overhead accumulates. - Reuse a preallocated buffer if roots size hasn't changed, or document why the allocation is acceptable.

- `pxrt_e_pseudo.lua:207-208` - medium - Per-message allocation in hot path - `forwardToKids` creates a copy array on every call. For objects with many children or frequent messages, this adds allocation overhead. - Consider reusing a buffer or using a different iteration strategy.

- `pxrt_e_pseudo.lua:231` - low - Allocation in enumeration function - `pseudoOfClass` creates a new array every call. If scripts enumerate objects frequently (e.g., collision checks), this adds allocation overhead. - Document if this is called frequently, consider caching results if the class filter doesn't change often.

- `pxrt_e_pseudo.lua:95` - high - Inefficient removal using `table.remove` - `removeFrom` uses `table.remove(list, i)` which shifts all subsequent elements. Called from `unregister` (line 157, 162, 163), this is O(n) per removal. For plist with many objects, unregistering becomes expensive. - Use swap-with-last removal like the manual implementation does elsewhere in the code.

- `pxrt_e_pseudo.lua:113` - medium - Inconsistent count tracking - `register` adds to plist using `plist[#plist + 1]` and increments count separately. But `count` is supposed to equal `#plist`. If these get out of sync (e.g., due to a bug), count won't match the actual list size. - Either use count consistently or rely on #plist. The code at line 115 suggests count should match #plist.

- `pxrt_e_pseudo.lua:157` - high - Wrong removal implementation - `unregister` calls `removeFrom(plist, obj)` which uses slow `table.remove`, but count is decremented separately at line 159. This creates inconsistency: plist has a hole filled by table.remove's shift, but count is decremented assuming swap-removal. If count and #plist diverge, iteration breaks. - Use swap-with-last: `plist[idx] = plist[count]; plist[count] = nil; count = count - 1`.

- `pxrt_e_pseudo.lua:46` - low - Removing null entries during Compact - Line 46 removes `nil` or `0` entries from the list. In PX semantics (line 50-52 of pxrt_core.lua), `isnull(v)` treats `nil`, `0`, and `false` as null, but this only removes `nil` or `0`, not `false`. If consistency with PX null semantics is intended, false should also be removed. - Add `or o == false` to the condition, or clarify if false objects are valid in lists.

- `pxrt_e_pseudo.lua:50` - medium - Closure recreated in Clear metamethod - The Clear function at line 50 creates a new closure for every access to the Clear method. If accessed in a loop or hot path, this allocates repeatedly. - Cache the closure or define it outside __index.

- `pxrt_e_pseudo.lua:39-47` - medium - Multiple closures in Remove and Compact - Lines 39-47 create closures for Remove and Compact methods on every __index access. If these methods are called frequently, the allocation overhead adds up. - Cache these closures or define them outside the metatable.

## Notes

- Could not verify if `dispatchPseudo` is actually called per-frame or less frequently. If called rarely (e.g., only for certain game events), the allocation concerns are less critical.
- Could not verify the intended behavior of the depth limit (lines 218, 205). The limit prevents infinite recursion but the threshold of 8 seems arbitrary and may be too low for deeply nested object hierarchies.
- The `pseudoCtor` functions are generated dynamically (lines 142-143), which is fine for initialization but the closures remain allocated. This is probably acceptable since there's one per root class, not per object.
- Did not analyze soft physics integration (`softCtor`, `softStep`) as those are in external modules, but the pcall wrapper at line 136-137 properly logs errors.
- The `register` function correctly handles parent-child relationships and maintains the roots list for top-level objects.
