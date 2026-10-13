# pkg_utility_parkour

## Findings

**utility_parkour:**

- `px_pipeline/testout/lua/utility_parkour/p_parkour_script.lua:86,89` - **high** - TraceLine is called but the runtime has no TraceLine implementation (only _TraceMask in pxrt_e_soft.lua). The utils library wraps TraceLine as TraceMask(..., MASK_PIXEL, ...) but utility_parkour calls it directly as __G__.TraceLine, bypassing the wrapper. **Scenario:** WallJump() calls TraceLine to detect walls; will error "attempt to call a nil value (__G__.TraceLine)". **Fix:** Runtime must expose __G__.TraceLine as a wrapper to _TraceMask, or the transpiler must resolve library functions to their qualified names.

- `p_parkour_script.lua:70` - **med** - Transpilation error: PXC line 79 checks `if(BhopDelay == 0)` but Lua line 70 checks `if isnull(self.BhopDelay)`. The ctor initializes BhopDelay=0 (line 22), so isnull() will always be false and bhop never triggers. **Scenario:** Player presses backspace while parkour mode on; bhop should trigger when delay==0 but never does. **Fix:** Change line 70 to `if (self.BhopDelay == 0)`.

- `p_parkour_script.lua:31-33` - **low** - CalculateSoundVolume and CalculateSoundPan are stubs (return 1.0 and a simple pan formula). PX computed spatial audio volume/pan from worm position vs camera; pxrt ignores volume and uses a minimal pan. **Scenario:** Parkour sound plays at full volume regardless of distance. **Fix:** Document as known limitation; full spatial audio needs camera tracking.

- `p_parkour_script.lua:34` - **low** - ShowMessage exists (pxrt_e_funcs.lua:127) but is a stub that calls showChatMessage. The runtime implements it so no error, but behavior may differ slightly from PX. **Scenario:** Messages appear in chat; functionally correct. **Fix:** None needed.

**utility_hangglider (transpiled vs hand-written port):**

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:152` - **high** - Same TraceLine/TraceMask issue: the transpiled version calls __G__.TraceMask (which doesn't exist as a global function, only as _TraceMask). The PXC source (line 274) calls TraceMask from the utils library. The hand-written port (main.lua:241-247) works around this by directly checking if the worm was blocked, avoiding the TraceMask call entirely. **Scenario:** Glider collision detection fails; worm flies through terrain. **Fix:** Runtime must expose TraceMask or the transpiler must resolve it to the utils library wrapper.

- `main.lua:241-247 vs paratest.lua:150-153` - **med** - Physics behavior differs: the hand-written port detects terrain blocking by comparing actual movement distance vs expected velocity (lines 243-247), while the transpiled PX version calls TraceMask ahead 1.1× velocity (line 152). The hand-written version is a workaround for the missing TraceMask. **Scenario:** Collision detection timing/behavior differs between ports. **Fix:** Once TraceMask is implemented, the PX version is more accurate (predictive vs reactive).

- `main.lua:186-189 vs paratest.pxc:307-347` - **med** - Control input handling differs: the hand-written port reads M_PLEFT/M_PRIGHT (30/31) and M_PUP/M_PDOWN (32/33) and applies acceleration/rotation. The transpiled version (paratest.lua:185-189, 161-183) does the same but the runtime constants K.M_PLEFT etc. match (pxrt_e_consts.lua:10). Functionally equivalent but different code paths. **Scenario:** Both should work identically if the runtime delivers M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT messages. **Fix:** None if messages are delivered; verify wkJellyWorm sends movement messages during parachute state.

- `main.lua:166-168 vs paratest.lua:24` - **low** - Sprite registration differs: hand-written uses registerCustomSprite() directly, transpiled uses F.LoadSprite() which wraps registerCustomSprite (pxrt_e_funcs.lua:245). Both should work. **Scenario:** Sprites load. **Fix:** None.

- `paratest.lua:83-89 vs main.lua:232-236` - **low** - Deployment detection: transpiled checks `self.Deployed == 0`, hand-written checks `not g.Deployed`. Transpiled uses numeric 0/1, hand-written uses boolean. The PXC (line 60) declares `Deployed = false`. The transpiler converts `false` to `0`. Functionally equivalent. **Scenario:** Both work. **Fix:** None.

## Notes

- Could not verify: whether wkJellyWorm delivers M_PUP/M_PDOWN/M_PLEFT/M_PRIGHT during WS_PARACHUTE state. If these messages are not sent, both glider implementations will not respond to controls.
- Could not verify: the pxrt_e_soft.lua collision system's accuracy against PX's TraceLine/TraceMask behavior under all flags and masks.
- The runtime loads pxrt_e_soft.lua which implements _TraceMask but does not expose TraceLine or TraceMask as global functions; utils library wrappers are only available if the script requires utils and the transpiler resolves the call correctly.
