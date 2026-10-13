# pkg_utility_jump

Based on my audit of the utility_jump package, here are my findings:

## Findings

- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_jump\jumpscript.lua:45` - high - `GetObject` call returns raw object instead of cast result - When retrieving the CTeam object via `GetObject(21, self.WormTeam)`, the code immediately casts it, but the runtime's `GetObject` implementation (pxrt_e_pseudo.lua:34) returns from a list without proper type wrapping for task objects - Replace `GetObject` pseudo implementation to return properly typed proxies or verify cast behavior handles raw task pointers
- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_jump\jumpscript.lua:46-47` - high - `AllowSelectDelay` and `AllowSelectBounce` fields missing from CTeam - The script sets `Team.AllowSelectDelay = 0` and `Team.AllowSelectBounce = 0` but these fields are not defined in FIELDS.CTeam (pxrt_engine.lua:218) which only has Active, CurWorm, and TeamIdx - Add AllowSelectDelay and AllowSelectBounce field definitions to FIELDS.CTeam with correct offsets
- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_jump\jumpscript.lua:51-52` - high - `CSpriteAnim.Reset` method missing - The code calls `mc(self.Anim, "Reset")` but CSpriteAnim has no Reset method defined in the runtime - Implement CSpriteAnim.Reset native method in pxrt_e_classes.lua or stub it
- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_jump\jumpscript.lua:52` - medium - `SetAnimEx` on CSpriteAnim may not work - The script calls `mc(self.Anim, "SetAnimEx", 269, self.FirePower)` but while CSpriteAnim.SetAnimEx exists (pxrt_e_hooks.lua:707), it's only hooked when scripts override it, and CWorm.SetAnimEx is a stub (pxrt_e_classes.lua:180) - Verify CSpriteAnim.SetAnimEx native implementation actually calls WA's SetAnim when not overridden
- `C:\Users\Admin\pxrt_dev\px_pipeline\testout\lua\utility_jump\jumpscript.lua:28-33` - low - Constructor override adds custom field without class registration - The CWorm constructor override adds `self.SettingJump = 0` which is not a WA memory field, creating a runtime-only Lua table field that won't persist across proxy recreations - Document that SettingJump is Lua-only state or use a weak table keyed by worm address

## Notes

- Could not access PX source files at "C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\utility_jump\0.0.1\scripts_px\*.pxc" (outside working directory) to compare transpilation line-by-line
- Could not verify correct memory offsets for AllowSelectDelay and AllowSelectBounce without WA executable analysis
- Did not audit utility_hangglider comparison as hand-written port location ("jelly\packages\utility_hangglider\0.0.1\main.lua") is also outside working directory
