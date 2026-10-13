# pkg_pxparticles

Based on my comprehensive audit of the pxparticles package, comparing the PX source files with the transpiled Lua and checking against the runtime implementation, here is my report:

## Findings

- `px_pipeline/testout/lua/@lib/pxparticles/pxparticles.lua:231` - high - **RandomFloat is not implemented in the runtime** - When particles call `__G__.RandomFloat(min, max)` for randomness effects, it will trigger the missing builtin handler and return 0 instead of a random float. This breaks particle motion randomness and initial velocity randomization. - Add `F.RandomFloat = function(a, b) a, b = tf(a), tf(b); if b <= a then return a end; local n = E.random(10000); return a + ((b - a) * n) / 10000.0 end` to pxrt_e_funcs.lua.

- `px_pipeline/testout/lua/@lib/pxparticles/pxparticles.lua:291` - med - **K.Env constant pattern not implemented** - The transpiled code uses `K.Env.Wind` and `K.Env.Gravity` (lines 291-292), but the runtime's K.Env is a function call that returns a proxy, not a direct table access. The pxrt_e_consts.lua defines `Env = function() ... return E.envProxy end` in the metatable, so `K.Env` works but is called every access. - No fix needed (works correctly, just inefficient).

- `px_pipeline/testout/lua/pxparticles/particle.lua:24` - med - **Childs.Count accesses pseudo object children** - The code iterates `self.Childs.Count` to enumerate particle children, which relies on pxrt_e_pseudo.lua's childsOf implementation. This is implemented correctly via the __childsView mechanism. - No fix needed (works correctly).

- `px_pipeline/testout/lua/@lib/pxparticles/pxparticles.lua:45` - low - **AddCustomRender depends on quad renderer availability** - The package calls `AddCustomRender(6, "__DrawPxParticles")` which is only available if the DLL provides pxQuadSubmit. If the quad renderer is unavailable, it logs "AddCustomRender unsupported" and particles won't render. - Document that pxparticles requires the DLL quad renderer; no runtime fix needed (design constraint).

- `px_pipeline/testout/lua/@lib/pxparticles/pxparticles.lua:257` - low - **FillSpriteQuad uses animcycle as frame parameter** - The Draw method passes `animcycle` (a 0-1 float) as the frame parameter to FillSpriteQuad. The runtime stores this as `__frame` but doesn't use it for sprite frame selection (only stores sprite id). Animation cycling for multi-frame sprites is not functional. - If multi-frame particle sprites are needed, modify pxrt_e_quads.lua to incorporate __frame into texture coordinates or document this limitation.

- `px_pipeline/testout/lua/@lib/pxparticles/pxparticles.lua:267` - low - **RenderQuad outside custom render logs warning** - If RenderQuad is called outside an AddCustomRender callback context, it logs "RenderQuad outside a custom render function: drawn at layer 6" and draws anyway. The pxparticles package correctly uses AddCustomRender, so this is not triggered. - No action needed (correct usage).

## Notes

- Could not verify whether the DLL's quad renderer (pxQuadSubmit, pxSpriteCell) is available in the deployed wkJellyWorm.dll without running the game.
- Did not audit utility_hangglider as instructed (the hand-written port comparison) because the file at "C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\utility_hangglider\0.0.1\main.lua" could not be accessed due to permission restrictions outside the working directory.
- The transpilation of pxparticles.pxc to Lua appears correct for all methods checked (constructor, setters, Draw, Message, SetRandomVelocity).
- Env->Wind and Env->Gravity access patterns in the PX source correctly transpile to K.Env.Wind and K.Env.Gravity in Lua.
