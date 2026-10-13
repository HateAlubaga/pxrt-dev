# pkg_utility_trampoline_destruct

Based on my analysis of the transpiled Lua and runtime files, I can now provide a comprehensive audit report. Let me compile the findings:

## Findings

**utility_trampoline_destruct:**

- `trampolineDestr.lua:17` - high - **GetAttachment stubbed**: F.GetAttachment returns a stub asset function that logs missing builtin. The package loads "bananaimpact.wav" and "wormspring.wav" but these will not resolve to actual sound files in pxrt.

- `trampolineDestr.lua:18-20` - medium - **CSoundFile constructor not implemented**: CSoundFile class constructor is defined in pxrt_e_funcs.lua:313 but the implementation creates an inert object with no actual sound loading or playback capability. Calls to Play/PlayLocalSound will be no-ops.

- `trampolineDestr.lua:24` - high - **CSprite creation not fully implemented**: F.GetAttachment returns stub for sprite loading. The sprite creation at line 24-28 (TrampSpriteDestr, TJumpSpriteDestr) will create placeholder objects without actual sprite data from "tramp.png" or "trampjump.png".

- `trampolineDestr.lua:130-232` - high - **CTrampolineDestr::Message(M_FRAME) physics depends on non-existent collision detection**: Lines 169-189 check collision via `FindInMask` which IS implemented in pxrt_e_soft.lua:311-323, but the collision detection logic stores global state (tramxDestr, tramyDestr, objxDestr, objyDestr, lastobjDestr) that is then used by the CTurnGame::Message override. **This is a PX design pattern that pxrt supports correctly.**

- `trampolineDestr.lua:252-312` - low - **CTurnGame::Message override processes collision aftermath**: The override at lines 252-312 manipulates worm/object positions based on collision state stored in globals. This pattern works in pxrt since CTurnGame overrides are dispatched correctly (pxrt_e_hooks.lua handles this).

- `trampolineDestr.lua:60-65` - medium - **Sprite rendering via override CRenderContext::DrawSprite not verified**: The DrawSprite override renders the trampoline sprite. pxrt_e_hooks.lua should have DrawSprite support but needs verification that sprite index substitution works correctly for script-created sprites.

- `trampolineDestr.lua:118-119` - low - **Layer assignment to -1**: The script sets `p.Layer = -1` for CTrampolineDestr objects. The soft physics worldObjs uses Layer for filtering (pxrt_e_soft.lua:331) but -1 is a valid layer value.

**utility_hangglider (comparison task):**

Since I cannot access the hand-written Lua port in `jelly\packages\utility_hangglider\0.0.1\main.lua` (blocked by directory permissions), I can only analyze the transpiled version:

- `paratest.lua:18-68` - N/A - **Cannot compare hand-written port**: The hand-written port at "C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\utility_hangglider\0.0.1\main.lua" is inaccessible due to working directory restrictions. Cannot verify control/physics differences between hand-written port and transpiled/PX source.

- `paratest.lua:195-234` - low - **CWorm::FireWeapon override complexity**: The transpiled hangglider uses complex weapon firing logic with sound playback (hangopen, hangclose). Sound files loaded via GetAttachment will be stubbed like in trampoline_destruct.

- `paratest.lua:235-260` - medium - **CRenderContext::DrawSprite override for sprite swapping**: Similar to trampoline, hangglider overrides DrawSprite to swap worm sprites (289-291) with glider sprites. This requires pxrt_e_hooks sprite override support.

**General transpilation issues:**

- `trampolineDestr.lua:3-6` - low - **Package metadata correct**: The package correctly declares dependency on "utils" library and defines CTrampolineDestr extending CGObject. No transpilation errors in class/package structure.

- `trampolineDestr.lua:216` - low - **RandomInt from utils library**: Line 216 calls __G__.RandomInt which should be provided by the "utils" library dependency. Verified that utils.pxc (px_pipeline/pxl/utils.pxc lines 96-99) defines RandomInt.

## Notes

- Cannot access PX source files in `C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\` due to working directory restrictions, so line-by-line PX-to-Lua comparison for important functions was not possible.
- Cannot access hand-written utility_hangglider Lua port to compare controls/physics with transpiled version.
- GetObjectsInArea and AddTimer are NOT used by utility_trampoline_destruct (grepped entire package, no matches found).
- The collision detection pattern (FindInMask storing to globals, then CTurnGame::Message reading those globals) is a valid PX pattern that pxrt supports.
- Sprite and sound asset loading via F.GetAttachment is stubbed in pxrt (returns placeholder), so visual/audio features will not work but logic will execute.
- CSprite and CSoundFile constructors exist but are inert (no actual rendering/playback).
