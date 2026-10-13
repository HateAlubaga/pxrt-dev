# pkg_weapon_grenade_electro

Now I have sufficient information. Let me compile the audit report.

## Findings

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:13** - high - `CAnimationParams` is not a builtin class in pxrt - When package creates `__R__.new("CAnimationParams")` at FirstFrame, it falls through to unknown class handler and creates an empty table with no initialized fields - Add `R.builtinClasses.CAnimationParams` constructor in pxrt that initializes all fields (sprite, speed, duration, ZPlane, turns, scale, color, blend_type, etc.) matching p_animation.pxc:11-28

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:37** - high - `CAnimation` class is not implemented in pxrt - When package tries `__R__.new("CAnimation", K.Root, x, y, nil, __G__.ElectricGrenadeParams)`, it creates a stub object with no rendering logic - Implement CAnimation as a pseudo-object (CObject-rooted) in pxrt with Message handler and Render method, or stub it silently if animations are not supported

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:38** - high - `CTazerShot` class exists in weapon_tazer package but may not be loaded - Package requires weapon_tazer (line 4) but CTazerShot is only available if weapon_tazer package was loaded and registered - Verify weapon_tazer is in the load order before weapon_grenade_electro, or log missing class error

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:38** - med - `call(self, "GetObject", 25, 0)` uses wrong calling convention - PX source line 45 calls `GetObject(25, 0)` as a free function, transpiler emitted `call(self, "GetObject", 25, 0)` which routes to method lookup instead of F.GetObject or the CHashStore method - Check transpiler: free function calls in override context should use `F.GetObject` or check if this is CHashStore.GetObject on the implicit Store

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:39** - high - `AddToIgnoreList` method exists on CTazerShot but returns immediately if list is full - Method at tazer.lua:301-308 adds obj to global ignore list, returns 0 if full (63 entries) - No fix needed in this package, but note that silently failing to ignore EG_now means the tazer may target the firing worm

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:27,34,36** - low - Transpiled fields on CMissile (`im_electric`, `not_too_much_particles`, `imCheckMis`) rely on dynamic field storage - These fields are set directly on the proxy object; pxrt supports them via rawset but they are lost when the proxy is dropped - No action needed if proxies are pinned during missile lifetime (pxrt_e_hooks.lua does pin missiles on construction)

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:50** - med - `do_zip_trail_effects` method is defined in utils_pyroman but not in pxrt natives - Method exists in transpiled Lua (utils_pyroman.lua:1465) as a P:method registration; it uses PxParticle which may or may not work - Verify PxParticle class is implemented; if not, the method runs but creates no visual effect

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:61** - med - `CheckParticlesNumber` method is defined in utils_pyroman but iterates all objects - Method at utils_pyroman.lua:1356-1387 loops `K.Env.Objs.Count`, casts each to CMissile, counts them, sets `not_too_much_particles` flag - Ensure K.Env.Objs proxy returns live engine objects (pxrt_e_game.lua should provide this)

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_grenade_anim.lua:20,28** - high - `CWormAnimParams` is not a builtin class in pxrt - Package creates `__R__.new("CWormAnimParams")` but class is not registered; falls through to unknown handler - Add `R.builtinClasses.CWormAnimParams` in pxrt matching p_sprite_builder.pxc:60-86 (hand_radius, weap_rotation, hand_type, hand_scale, objStates, etc.)

- **px_pipeline\testout\lua\weapon_grenade_anim.lua:28** - high - `WormSprite` class is not implemented in pxrt - Package instantiates `__R__.new("WormSprite", weapName, sprite, Params)` but class is defined only in p_sprite_builder transpiled library, not as engine builtin - WormSprite is a CObject pseudo-class (p_sprite_builder.lua:5,88); if p_sprite_builder is loaded it should work, otherwise stub it or log missing class

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_grenade_anim.lua:41-42** - high - `WeapSpriteParams` and `WeapSprite` classes are not implemented in pxrt - Package creates `__R__.new("WeapSpriteParams")` and `__R__.new("WeapSprite", self, sprite, Params)` but classes are not registered as builtins - Add builtinClasses entries or ensure p_sprite_builder library is loaded before this package runs

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_grenade_anim.lua:43** - med - Field write `self.weap.launch.anim.spriteIndex = 0` assumes nested struct chain exists - CMissile.weap -> CWeapon, .launch -> CWeaponLaunch (memory-backed struct), .anim -> ? (not documented in runtime) - Verify CWeaponLaunch has anim field at correct offset, or this write silently fails on a table without error

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:59** - med - `__G__.GetCurrentWorm()` is a script-declared function, not a builtin - Transpiler should emit `F.GetCurrentWorm()` or this resolves to a package-defined global function; PX source line 68 calls the utils builtin - Check if utils package provides GetCurrentWorm as a P:func; pxrt has BF.GetCurrentWorm (pxrt_e_funcs.lua:370) but it is not in F table by default

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_nade_script.lua:36** - low - `blend_type = 4` is assigned to CAnimationParams but blend_type handling is not verified in runtime - PX p_animation.pxc:24 defaults blend_type to 2; value 4 may be unsupported or interpreted differently - Check pxrt_e_quads.lua or rendering layer for blend mode 4 support (likely additive or multiplicative)

- **px_pipeline\testout\lua\weapon_grenade_electro\electric_grenade_anim.lua:17** - low - Global variable `gframe` is accessed but not verified to exist in runtime - Line 17 checks `if (__G__.gframe == 1)` to run initialization once; gframe must be set by the engine layer or another package - Verify pxrt_engine or a core package sets gframe each frame (likely in the M_FRAME dispatch)

## Notes

- Could not access PX source files directly (blocked by permission); compared transpiled Lua against known PX patterns and p_animation/p_sprite_builder library sources
- Did not verify if p_sprite_builder, p_animation, weapon_tazer are in the package load order before weapon_grenade_electro
- PxParticle class implementation not checked (used by do_zip_trail_effects)
- K.Env.Objs proxy implementation exists in pxrt_e_game.lua but not read in detail
- gframe global not searched exhaustively; assumed to be set by frame dispatch hook
- NullObj constant not found in K table; PX source uses `NullObj` but transpiler emits `nil` (line 37: `new CAnimation(..., NullObj, ...)` becomes `nil`)
