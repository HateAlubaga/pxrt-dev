# pkg_p_gravity_gun

Now I have enough information to compile my audit report. Let me create the final findings document.

## Findings

- `gravity_gun_s.lua:1076` - high - `self.WAP.Size` field access fails: CWorm has no WAP field - the runtime does not expose CWorm.WAP (worm animation parameters), but gravity_gun reads it in DrawDimmedGG() - add WAP to FIELDS.CWorm in pxrt_engine.lua or stub it as a default struct
- `gravity_gun_s.lua:713,741,768` - high - PxParticle constructor called but particle system disabled - __R__.new("PxParticle") creates particle objects, but pxrt logs "AddCustomRender unsupported" (pxrt_e_classes.lua:79), so particles never render - enable pxrt_e_quads.lua or stub PxParticle to no-op
- `gravity_gun_s.lua:400,493,556,848` - high - TraceLine not provided by runtime - gravity_gun calls __G__.TraceLine from utils, which wraps _TraceMask (pxrt_e_soft.lua:344) - runtime provides _TraceMask, so TraceLine works; verified this is NOT stubbed
- `gravity_gun_s.lua:448,460,697` - high - TeleportObject not provided by runtime - gravity_gun calls __G__.TeleportObject from utils (utils.lua:1667), which uses K.Env.CheckCollisionEx - runtime provides CheckCollisionEx (pxrt_e_classes.lua:375) via E.checkCollision host call, so TeleportObject works if checkCollision is available; if stub returns nil, object never teleports
- `gravity_gun_s.lua:519,871` - med - GetWeaponByName may return invalid weapon proxy - F.GetWeaponByName("Gravity Gun") returns E.weaponById(id, name) where id comes from weaponIdByName host call; if the weapon is not registered (custom weapon), id=-1 and subsequent GetWeaponIndex/GetPageIndex calls return 0, breaking AddWeaponEx ammo replenishment - verify "Gravity Gun" is registered in the host's weapon list
- `gravity_gun_animations.lua:42` - med - WormSprite constructor creates script object with no native support - __R__.new("WormSprite", ...) builds a script object (p_sprite_builder.lua:88) that stores weapon animation state; runtime has no native WormSprite, so it relies entirely on script logic and AddSpriteEx drawing - this works, but GG_WS.aimAng read at gravity_gun_s.lua:380,385 depends on WormSprite.Message being called every frame to update aimAng
- `gravity_gun_s.lua:1059` - low - math_exp called from utils_pyroman - __G__.math_exp(deg) is a script approximation of e^x (utils_pyroman.lua:1319), not a stub; it returns correct values within ~1% for small x - no runtime issue
- `gravity_gun_s.lua:424,645,685` - med - CheckMaskAt collision check - __G__.CheckMaskAt is provided by pxrt_e_soft.lua:326 and works correctly; no stub - verified working
- `gravity_gun_s.lua:17-25` - low - CSoundFile Play() ignores pan parameter - runtime CSoundFile.Play (pxrt_e_funcs.lua:327) receives (vol, pan, loop) but always plays at pitch 1.0, ignoring pan (PX's CalculateSoundPan ~-0.1..0.1 was misinterpreted as pitch in old code); sounds play at normal volume and pitch, no spatial audio - cosmetic, matches comment in runtime
- `gravity_gun_s.lua:813,817` - med - WormSprite.sprite2 field mutation depends on script execution - gravity_gun's GGOpenHolder sets __G__.GG_WS.sprite2 to different sprites based on gg_superworm; if WormSprite.Message doesn't run (no M_DRAWQUEUE), sprite changes don't propagate to rendering - ensure pxparticles and p_sprite_builder receive M_DRAWQUEUE
- `gravity_gun_animations.lua:28-44` - med - WormSprite created at gframe==1 only - __G__.GG_WS is created in CTurnGame override at gframe==1; if this message is missed (late script load), GG_WS stays nil and gravity_gun crashes at line 380 (GG_WS.aimAng) - add nil check or ensure InitGraphic runs before first M_FRAME
- `gravity_gun_s.lua:1080-1086` - low - PxLightningStrike override never called - override of PxLightningStrike.LightningHit sets gg_superworm=1; PxLightningStrike is a script class from another package (weapon_lightning required at line 4), not an engine class; if weapon_lightning is not loaded, this override is inert - superworm feature depends on lightning weapon package

## Notes

- Could not verify PX source files (blocked from reading C:\Program Files); compared transpiled Lua with runtime only
- AddCustomRender is logged as "unsupported" unless pxrt_e_quads is loaded; if the DLL lacks pxQuadSubmit, particles and custom rendering are inert
- checkCollision host function availability not verified; if absent, TeleportObject always fails (returns 0)
- weaponIdByName host function: if "Gravity Gun" not registered, weapon lookup returns invalid proxy
- WormSprite and PxParticle are pure script classes with no engine backing; they rely on M_DRAWQUEUE and AddSpriteEx/AddCustomRender hooks
- No transpilation errors found when comparing Lua structure to expected PX patterns
