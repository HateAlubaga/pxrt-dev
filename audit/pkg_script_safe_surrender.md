# pkg_script_safe_surrender

Now I have enough information to compile my audit report. Let me create the final findings:

## Findings

- `px_pipeline/testout/lua/script_safe_surrender/script_safesurrender.lua:7` - high - Script calls `mc(__G__.keySync, "AddKey", 17)` but `keySync` global is not initialized by pxrt - Script requires utils library (line 4) which defines keySync in sync_script::Init (utils.pxc:424-428), but pxrt does not automatically load shared PX libraries when a package requires them - Either pre-load utils library in pxrt or stub the CKeySync class with AddKey/KeyPressed methods in pxrt_e_pseudo.lua

- `px_pipeline/testout/lua/script_safe_surrender/script_safesurrender.lua:11` - high - Script calls `mc(__G__.keySync, "KeyPressed", 17)` which depends on the missing keySync global - KeyPressed method reads synchronized keyboard state from the kRStates array that gets updated through M_PXMESSAGE commands - Same root cause as AddKey: utils library provides CKeySync but runtime doesn't load it

- `px_pipeline/testout/lua/script_safe_surrender/script_safesurrender.lua:11,14` - med - CheckName method exists (pxrt_e_classes.lua:537) but depends on weapon name normalization that may not cover "Surrender" - CheckName normalizes weapon names and compares them; "Surrender" is in pxrt_e_classes.lua:392 and pxrt_wnames.lua:382, so this should work - Verify that weaponIdByName lookup works for "Surrender" in practice

- `px_pipeline/testout/lua/script_safe_surrender/script_safesurrender.lua:14` - low - ShowMessage is implemented (pxrt_e_funcs.lua:127-130) but uses showChatMessage with hardcoded font parameter 6 - Implementation wraps showChatMessage in pcall and passes R.str(s) for string conversion - Should work correctly; no issue unless showChatMessage is unavailable

- `px_pipeline/testout/lua/script_safe_surrender/script_safesurrender.lua:10-18` - med - FireFinal override chain mechanism is implemented (pxrt_e_hooks.lua:548, 572, 585) and should work - The override runs through onFire hook which checks hasScriptChain("CWorm", "FireFinal") and invokes the chain - super() calls fireNative which triggers WA's original FireWeapon - Verify that the chain execution order matches PX behavior (script first, then native via super)

- `px_pipeline/testout/lua/script_safe_surrender/script_safesurrender.lua:12,17` - med - super(Weap, Desc) calls fireNative which expects valid weapon struct and shoot desc addresses - fireNative validates args (line 528-530) and logs error if invalid, returning 0 instead of firing - If Weap or Desc proxies lack __a field or E.weaponStructAddr/E.sdAddr fail, shot is silently dropped

## Notes

- Cannot access original PX source files at `C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\script_safe_surrender\0.0.1\scripts_px\*.pxc` due to security restrictions; audit based on transpiled Lua only
- Cannot compare utility_hangglider hand-written port as the file at `jelly\packages\utility_hangglider\0.0.1\main.lua` is not in the accessible directory
- The runtime's require mechanism (pxrt_core.lua:661, 781-808) expects `require("pxl_utils")` to load utils library, but pxl_utils.lua is not found in pxrt_dev root - library files appear to be in out/deploy/lualibs/ subdirectory
- RegisterPXMessage is implemented (pxrt_e_funcs.lua:293-297) and returns unique message IDs starting from 0x2000, which CKeySync needs for its constructor
- The core issue is that script dependencies declared via `__P__:require({"utils"})` are not automatically loaded by pxrt - packages must explicitly call loadLib or the runtime must pre-load common libraries like utils
