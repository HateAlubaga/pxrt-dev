# pkg_weapon_bulldozer_yellow

Based on my analysis of the weapon_bulldozer_yellow package and utility_hangglider comparison, here is my audit report:

## Findings

- `px_pipeline/pxl/utils.pxc:1521` - high - MakeRectMask function not implemented in runtime - PushBldzr_yellow.pxc line 11 calls `MakeRectMask(20,20)` to create collision mask, runtime has no MakeRectMask builtin function - Add `F.MakeRectMask = function(w, h) local bm = BC.CBitmap1(ti(w), ti(h)); bm:Rect(0, 0, w, h, 1); return bm end` to pxrt_e_funcs.lua

- `weapon_bulldozer_yellow/bulldozer_spb.pxc:31` - high - WormSprite class not implemented in runtime - bulldozer_spb creates `new WormSprite(weapName, sprite, Params)` at gframe 1 to register weapon animation, runtime has no WormSprite class - Stub WormSprite constructor in pxrt_e_classes or implement p_sprite_builder library support

- `weapon_bulldozer_yellow/PushBldzr_yellow.lua:14` - med - CColMask constructor signature mismatch - PX source line 11 calls `new CColMask(10,10,MakeRectMask(20,20))` (3 args: hotspotX, hotspotY, bitmap), transpiled Lua passes all 3 args but pxrt_e_funcs.lua:392 BC.CColMask accepts only (w,h) and ignores bitmap - Change BC.CColMask in pxrt_e_funcs to call pxrt_e_soft's 3-arg version: `BC.CColMask = function(...) return require('pxrt_e_soft').softCColMask(...) end`

- `weapon_bulldozer_yellow/bulldozer_spb.pxc:8` - med - LoadSprite frames parameter may not create multi-frame sprite - PX line 8 `LoadSprite(f, 0, 0)` expects sprite Index usable for weapon animation, runtime pxrt_e_funcs.lua:245 registers custom sprite but frames=0 may not work correctly - Verify registerCustomSprite handles frames=0 case or change PX to frames=1

- `weapon_bulldozer_yellow/PushBldzr_yellow.pxc:34` - low - BType field initialized as bool but used as int - PX line 19 `BType = false`, line 34 `BType = true`, line 52 checked `if(BType == true)`, transpiler converts to 0/1 correctly but semantically inconsistent - No fix needed, transpilation handles it

- `weapon_bulldozer_yellow/PushBldzr_yellow.lua:49` - low - MakeHole third parameter precision - PX line 54 calls `MakeHole(10, dmis_bldzr->PosX, dmis_bldzr->PosY-8.7)`, runtime pxrt_e_terrain.lua:145 implementation exists and calls E.makeHole - Verify E.makeHole handles fixed-point y coordinate correctly

- `utility_hangglider/main.lua:138-145` - high - Hand-written port lacks CWormGlider class entirely - PX paratest.pxc defines CWormGlider class with Think/OnStartGliding/OnStopGliding methods and complex physics (lines 53-263), hand-written main.lua only has weapon registration and sprite override setup, missing all glider physics and controls - Port lacks core functionality; pxrt would need full CWormGlider implementation

- `utility_hangglider_render/paratest.pxc:139-140` - med - CSpriteAnim::SetAnimEx override not in pxrt - PX line 390-406 overrides CSpriteAnim::SetAnimEx to swap sprite 289 with glider sprite, runtime has no CSpriteAnim class or SetAnimEx method - Add CSpriteAnim proxy and SetAnimEx method stub to pxrt_e_classes

- `px_pipeline/testout/lua/utility_hangglider/paratest.lua:122` - med - GS.env.Gravity field access pattern - Transpiled line 122 `K.GS.env.Gravity`, PX accesses engine environment fields, runtime proxies may not expose env.Gravity correctly - Verify K.GS.env proxy in pxrt_e_game returns correct Gravity/Wind fields

- `utility_hangglider_render/paratest.pxc:65` - low - PRegister/PUnregister are stubs - PX lines 65,99 call PRegister/PUnregister to keep Owner reference, runtime pxrt_e_funcs.lua:299-300 stubs them as no-ops, Lua GC already prevents collection - Acceptable difference, no fix needed

- `weapon_bulldozer_yellow/PushBldzr_yellow.pxc:95` - med - M_GUNEXP message format undocumented - PX line 95-103 constructs CMessageData with specific params/fparams layout for M_GUNEXP (force application), runtime accepts struct but effect unclear - Document M_GUNEXP handling or verify explosion force is applied by engine

- `utility_hangglider_render/paratest.pxc:106-121` - med - CurWeapon field access during parachute state - PX lines 106-121 check `Owner->CurWeapon->CheckName("Hang-Glider")` etc., runtime CWorm proxy may not expose CurWeapon correctly during WS_PARACHUTE state - Verify CWorm.CurWeapon proxy field exists and CheckName works in all weapon states

## Notes

- Could not verify if registerCustomSprite (pxrt_e_funcs.lua:248) correctly handles sprite registration for weapon animations with frames=0
- Did not trace full E.makeHole terrain modification implementation to confirm fixed-point coordinate handling
- Cannot confirm if M_GUNEXP message handling applies forces to objects as ProjectX does without running in-game
- utility_hangglider hand-written port is fundamentally incomplete compared to PX version - missing ~300 lines of physics logic
