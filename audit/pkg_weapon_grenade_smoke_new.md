# pkg_weapon_grenade_smoke_new

Now I have enough information to compile my audit report. Let me create the comprehensive findings document.

## Findings

- `frag_anim.pxc:19,23` / `toxic_anim.pxc:19,23` - **high** - CWormAnimParams constructor not implemented in runtime - Both frag_anim and toxic_anim create `new CWormAnimParams` at gframe==1 and set fields like hand_radius, hand_rotation, weap_rotation, hand_type, hand_scale before passing to WormSprite constructor, but runtime has no CWormAnimParams builtin class (searched pxrt*.lua, not found) - The p_sprite_builder library defines CWormAnimParams:ctor at line 59-85 but it is never loaded into pxrt's builtinClasses - Add BC.CWormAnimParams as a script-owned struct in pxrt_e_structs.lua or load p_sprite_builder library

- `frag_anim.pxc:31` / `toxic_anim.pxc:31` - **high** - WormSprite class not implemented in runtime - Both scripts call `new WormSprite(weapName, sprite, Params)` to register custom weapon hand animation for "Smoke Grenade"/"Toxic Grenade", but runtime has no WormSprite builtin class (grep found no matches in pxrt*.lua) - The p_sprite_builder library defines WormSprite class (px_pipeline/testout/lua/@lib/p_sprite_builder/p_sprite_builder.lua:5-855) but it requires loading utils, utils_pyroman, pxparticles, utils_r2 and is not integrated into pxrt - Stub WormSprite constructor as inert or integrate p_sprite_builder library support

- `frag_anim.pxc:42,45` / `toxic_anim.pxc:42,45` - **high** - WeapSpriteParams constructor not implemented in runtime - Both scripts create `new WeapSpriteParams` inside CMissile::Message to customize projectile sprite, but runtime has no WeapSpriteParams builtin class (searched pxrt*.lua, not found) - The p_sprite_builder library may define it but is not loaded - Add BC.WeapSpriteParams as a script-owned struct in pxrt_e_structs.lua

- `frag_anim.pxc:43,46` / `toxic_anim.pxc:43,46` - **high** - WeapSprite class not implemented in runtime - Both scripts call `new WeapSprite(this, sprite, Params)` to attach custom sprite to the missile in flight, but runtime has no WeapSprite builtin class (grep found no matches in pxrt*.lua) - The p_sprite_builder library defines WeapSprite class (px_pipeline/testout/lua/@lib/p_sprite_builder/p_sprite_builder.lua:7) but is not loaded into pxrt - Stub WeapSprite constructor as inert or integrate p_sprite_builder library

- `frag_anim.lua:18,32` / `toxic_anim.lua:18,32` - **medium** - gframe global not initialized by runtime - Transpiled code checks `if (__G__.gframe == 1)` to run first-frame initialization inside CTurnGame::Message(M_FRAME) override, but runtime does not define or increment gframe in engineG (searched pxrt*.lua for gframe, no hits) - WormSprite registration never runs because gframe is never 1 - Scripts must initialize gframe themselves in FirstFrame entry, or runtime should add engineG.gframe incremented by M_FRAME hook

- `frag_anim.lua:47` / `toxic_anim.lua:47` - **medium** - Direct field assignment to weap.launch.anim.spriteIndex - Transpiled code writes `self.weap.launch.anim.spriteIndex = 0` to hide default missile sprite after attaching WeapSprite, but runtime's CWeaponLaunch proxy field map may not include anim.spriteIndex (checked pxrt_e_structs.lua:100-250, launch struct has anim field but nested access unclear) - If field offset is unknown, write is silently ignored - Verify launch.anim.spriteIndex resolves to valid offset or document that hiding default sprite requires different approach

- `smoker_script.pxc:22,24` - **high** - parman global and ParticleBoom method not implemented - CSmoker::Message calls `parman->ParticleBoom(6, x, y, 6, parman->toxicdesc)` and `parman->ParticleBoom(8, x, y, 12, parman->smokedesc)` expecting a global CParticleMan instance with smokedesc/toxicdesc fields and ParticleBoom method (PX particles.pxc:37-93), but runtime has no CParticleMan/CParticleDesc builtin classes (searched pxrt*.lua, no matches) - Without particles library, smoke grenades create CSmoker objects but emit no visual particles - Stub CParticleMan/CParticleDesc as inert or integrate particles library (px_pipeline/testout/lua/@lib/particles/particles.lua)

- `smoker_script.pxc:7` - **low** - CSmoker constructor passes GS constant - CSmoker:ctor calls `super(parent, GS)` where GS is a dynamic global (K.GS in pxrt_e_consts.lua:63), but CObject constructor expects a memory address - Runtime handles this via K metatable (__index calls gs() function returning proxy), so it works, but semantically different from PX where GS was a static pointer

- `smoker_script.pxc:34-44` - **high** - CMissile::ExplodeAt override support unclear - smoker_script overrides CMissile::ExplodeAt to spawn CSmoker instead of normal explosion for "Smoke Grenade"/"Toxic Grenade", but runtime has no CMissile natives defining ExplodeAt (searched pxrt*.lua for ExplodeAt, no matches; searched for nat("CMissile"), found only in CTOR_CLASSES list pxrt_e_hooks.lua:102) - If ExplodeAt is not a native method, the override may not fire or may replace a method that never existed - Verify CMissile has ExplodeAt native or that scripts can add new methods to engine classes via override

- `frag_anim.pxc:50-52` / `toxic_anim.pxc:50-52` - **medium** - CMissile constructor override chaining - Both scripts override CMissile::CMissile to set FragAnim/ToxicAnim flag, then call super(parent, ldata, sdata) - Runtime supports constructor overrides via __P__:ctor (pxrt_core.lua:686-696), but if multiple packages override CMissile ctor, only the last-loaded override runs unless chaining is correct - Verify ctor override chaining allows multiple packages to augment CMissile construction

- `frag_anim.pxc:39,42` / `toxic_anim.pxc:39,42` - **low** - weap->CheckName called every M_FRAME - CMissile::Message override checks `weap->CheckName("Smoke Grenade")` on every frame to guard sprite attachment logic - Runtime implements CheckName with normalization caching (pxrt_e_classes.lua:516-558), so performance cost is low - Acceptable pattern

- `smoker_script.pxc:11-12` - **low** - turn field initialized to 4 with no turn decrement - CSmoker:ctor sets `turn = 4` and Message checks `if (turn < 0) return`, with `turn -= 1` on M_TURNEND (line 30-31) - Runtime defines M_TURNEND constant (pxrt_e_consts.lua:15), so smoke grenades emit particles for 4 turns then become inert - Correct behavior

- `frag_anim.pxc:7-8` / `toxic_anim.pxc:7-8` - **low** - GetAttachment returns asset path - Both scripts call `GetAttachment("fraggren.png")` / `GetAttachment("fragtoxic.png")` and pass result to LoadSprite - Runtime implements GetAttachment as `F.GetAttachment(name) return asset(name)` (pxrt_e_funcs.lua:242) where asset() resolves to package attachment path - Correct if registerCustomSprite accepts resolved paths

- `smoker_script.pxc:1` - **low** - requires utils and particles libraries - Script declares `require utils, particles` expecting shared libraries loaded, but runtime does not auto-load pxl libraries (px_pipeline/testout/lua/@lib/) - If particles library is missing, script fails at load time with undefined parman - Document that packages using particles must bundle or pre-load the library

- `smoker_script.lua:44,46` - **medium** - K.Root used as parent for CSmoker - Transpiled code passes `K.Root` (dynamic global returning CTurnGame proxy, pxrt_e_consts.lua:62) as parent to CSmoker constructor - CObject base constructor accepts parent address, K.Root.__a should resolve to turnGameAddr() - Works if K metatable resolves Root to proxy with __a, but semantically unusual (CSmoker should be child of Root, not a peer)

## Notes

- Could not verify if registerCustomSprite (pxrt_e_funcs.lua:248) correctly handles fraggren.png/fragtoxic.png sprite registration for weapon animations
- Did not trace full p_sprite_builder library to confirm WormSprite/WeapSprite rendering behavior matches PX expectations
- Cannot confirm if M_TURNEND message is reliably sent to script objects (CSmoker) or only to engine objects without running in-game
- The package cannot render weapon hand sprites or projectile sprites or particle effects on pxrt without p_sprite_builder and particles library integration
