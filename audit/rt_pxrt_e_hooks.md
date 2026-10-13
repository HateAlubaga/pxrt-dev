# rt_pxrt_e_hooks

Now I have enough context. Let me analyze the code systematically for the requested issues.

## Findings

- `pxrt_e_hooks.lua:204` - high - CallOriginal failure returns 0 but WA expects 1 for "handled" - When a script override exists but CallOriginal crashes (e.g., bad native function pointer), returns 0 which tells WA "not handled", causing WA to potentially invoke another handler or ignore the message entirely - Return 1 to indicate the message was consumed

- `pxrt_e_hooks.lua:213` - high - sendMessage failure returns 0, silently dropping script-initiated messages - When a script sends a message to an engine object and E.sendMessage crashes, the message is lost and scripts continue unaware - Should propagate the error or at minimum log it without `once()` suppression

- `pxrt_e_hooks.lua:388-391` - med - M_PXMESSAGE dispatch failures swallowed with once() per-session logging - First M_PXMESSAGE dispatch error is logged, subsequent failures are silent for the entire session - Commands queued by scripts (keys, camera) silently stop working after first error - Remove `once()` or add a counter

- `pxrt_e_hooks.lua:446` - high - onFrame callback failures suppressed with once() - After the first onFrame error, all subsequent per-frame callback failures are silent - Scripts relying on frame callbacks silently break - Use regular `log()` instead of `once()`

- `pxrt_e_hooks.lua:486-487` - low - CallOriginal for SCRIPT_MSG_MIN messages ignores return value and pcall result - When mtype >= SCRIPT_MSG_MIN, the code calls `pcall(callOrig[cls], ...)` but discards both ok and return value - Inconsistent with line 204 where CallOriginal failures are checked - Check pcall result

- `pxrt_e_hooks.lua:494` - med - Message chain failure falls back to CallOriginal but without checking if it's safe - When a script Message override crashes, the code tries to call the native handler as fallback, but this may not be appropriate for SCRIPT_MSG_MIN messages (>= 0x2000) which WA never produced - Add `if mtype < SCRIPT_MSG_MIN` guard

- `pxrt_e_hooks.lua:526-528` - high - FireWeapon failure continues to constructFired, creating objects without proper weapon initialization - When WA's FireWeapon crashes, the code proceeds to construct fired objects anyway - Objects created without FireWeapon side effects (velocities, positions) will be in invalid state - Return early on FireWeapon failure

- `pxrt_e_hooks.lua:567-568` - med - Inconsistent error handling: traceback only with PXRT_TB env var - xpcall error handler conditionally returns debug.traceback or just tostring(e) - Without PXRT_TB, stack traces are lost making bugs hard to diagnose - Always return traceback, or make it opt-out not opt-in

- `pxrt_e_hooks.lua:596,601,603` - med - Init/InitGraphic failures logged but match continues in potentially broken state - matchReset, InitGraphic, and Init entry failures are logged but execution continues - Scripts may depend on Init-time setup (variables, assets) that never happened - Consider failing the match or at minimum warning user visibly

- `pxrt_e_hooks.lua:612` - low - FirstFrame entries run without pcall - R.runEntries("FirstFrame") at line 612 is called without pcall wrapping - If FirstFrame entry crashes, the entire onFrame callback fails and game may crash - Wrap in pcall like Init/InitGraphic

- `pxrt_e_hooks.lua:255,261,270,319` - low - String concatenation and format in perfReport hot path during per-frame accounting - Multiple string.format calls per class per frame and table.concat in perfReport - While perfReport runs infrequently (every PERF_FRAMES), it allocates many strings each time - Pre-allocate buffers or reduce format calls

- `pxrt_e_hooks.lua:365` - med - pxQueue allocation on every AddPXMessage call - Each AddPXMessage allocates a new table `{ ti(mtype), ti(p1), ti(p2) }` - In scripts that send many commands per frame, this allocates hundreds of tables - Pre-allocate queue entries or use a ring buffer

- `pxrt_e_hooks.lua:474,477` - low - Message dispatch creates new ctxStack entry and closure captures for every message - Line 474: `local top = { This = ..., sender = ..., ... }` allocates a table per message - For high-message-rate objects (flames, clouds) this is hundreds of allocations per frame - Consider reusing a single top object

- `pxrt_e_hooks.lua:616` - med - Pin validation reads memory (rd/rdU) for every pinned object every SWEEP frames - Every 30 frames, iterates all pins and calls rd(a+0x20) and rdU(a) for validation - For games with 100+ pinned objects, this is 200+ memory reads - Cache validation results or increase SWEEP interval

- `pxrt_e_hooks.lua:703,711` - med - RenderWorm/SetAnimEx failures suppressed with once() - After first rendering error, all subsequent rendering failures are silent - Rendering issues could affect multiple worms/animations but only first is reported - Use regular log() with msgSeen deduplication instead

## Notes

- Could not verify fixed-point arithmetic correctness without reading transpiled scripts and understanding exact PX fixed-point format
- Could not verify all null object semantics without seeing CWorm/CTurnGame proxy implementations in pxrt_engine.lua
- The `once()` pattern is used correctly for non-repeating issues (missing DLL functions, wrong SDK version) but incorrectly for per-frame/per-message failures that should be logged each time
