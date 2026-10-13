# pkg_weapon_explosives

Based on my audit of the weapon_explosives package, I've identified the missing runtime support. Let me compile my findings:

## Findings

- **explosives_script.lua:37,42,47** - high - `do_sprite_trail_effects` method not implemented in runtime - Particle trail effects for TNT, GunPowder Bomb, and Firecracker will not render during flight - Implement CMissile::do_sprite_trail_effects stub that logs once and returns 0, or import utils_pyroman library which defines it

- **tnt_anim.lua:20,gunpowder_bomb_anim.lua:20,firecracker_anim.lua:21** - high - `CWormAnimParams` class not defined in runtime - `new("CWormAnimParams")` will fail with missing builtin class error - Define CWormAnimParams as empty struct in pxrt_e_structs.lua or stub builtinClass that returns empty table

- **tnt_anim.lua:32,gunpowder_bomb_anim.lua:32,firecracker_anim.lua:32** - high - `WormSprite` class not defined in runtime - Worm aiming animations for all three weapons will not display - Define WormSprite as pseudo-object class or stub builtinClass; sprite-builder feature from p_sprite_builder.pxc is not implemented

- **tnt_anim.lua:45,gunpowder_bomb_anim.lua:45** - high - `WeapSpriteParams` class not defined in runtime - `new("WeapSpriteParams")` will fail with missing builtin class error - Define WeapSpriteParams as empty struct in pxrt_e_structs.lua or stub builtinClass

- **tnt_anim.lua:46,gunpowder_bomb_anim.lua:46** - high - `WeapSprite` class not defined in runtime - Missile sprite customization will not work - Define WeapSprite as pseudo-object class or stub builtinClass; sprite-builder feature from p_sprite_builder.pxc is not implemented

- **tnt_anim.lua:48,gunpowder_bomb_anim.lua:48** - high - `self.weap.launch.anim.spriteIndex` nested field access will fail - Runtime's CWeaponLaunch struct does not expose anim substructure or spriteIndex field - Add anim substructure to pxrt_e_structs.lua CWeaponLaunch field map, or make field writes no-ops with logging

- **explosives_script.lua:11-14** - med - `self:DoExplosion` called on CMissile instead of K.Root - GunPowder Bomb explosion may fail if CMissile does not inherit DoExplosion from CObject - Verify CMissile inherits from CObject; if not, add CMissile.DoExplosion = CObject.DoExplosion alias

- **explosives_script.lua:36,40,45** - med - `self.not_too_much_particles` field checked but never initialized - Scripts assume field exists to throttle particle generation; always-nil means trails always suppressed - Transpiler or utils library should initialize this flag; runtime could stub it as always-truthy

- **tnt_anim.lua:43,57,gunpowder_bomb_anim.lua:43,57** - low - Custom fields `tnt_anim2` and `gunpowder_bomb_anim2` on CMissile instances - Fields used as one-shot flags to apply WeapSprite once; harmless but non-standard pattern - No fix needed; Lua tables allow arbitrary fields

- **explosives_script.lua:56-57,60-61** - low - Global variables `ClWT` and `ClWN` used to pass team/worm context to ExplodeAt - Firecracker and GunPowder Bomb store current team/worm in globals for explosion attribution - Pattern works but is not thread-safe; acceptable for single-threaded game loop

## Notes

- Could not access PX source files at "C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\weapon_explosives\0.0.1\scripts_px\" due to working directory restrictions; relied on transpiled Lua in px_pipeline\testout\lua\weapon_explosives\*.lua
- Runtime implements DoExplosion in pxrt_e_classes.lua:94 for CObject; verified it calls WA engine explosion function
- Runtime implements CheckName in pxrt_e_classes.lua:537 for CWeapon; weapon name matching works correctly
- Runtime implements ExplodeAt as stubbed (not found in grep results); CMissile::ExplodeAt override will call super which may be unimplemented
- PxParticle class (used by do_sprite_trail_effects from utils_pyroman) is not defined in runtime; particle effects entirely unsupported
- The sprite-builder system (WormSprite, WeapSprite, CWormAnimParams, WeapSpriteParams from p_sprite_builder.pxc) is a complete subsystem not yet ported to pxrt
