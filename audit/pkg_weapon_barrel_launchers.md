# pkg_weapon_barrel_launchers

Based on my comprehensive audit of the weapon_barrel_launchers package and utility_hangglider comparison, here are the findings:

## Findings

- **icybarrel_logic_bl.pxc:8 / icybarrel_logic_bl.lua:7** - high - Missing DistBetweenObjs implementation - IceDrum::Freeze calls DistBetweenObjs(this, sel_worm) which is a utility function from utils.pxc library, but runtime has no implementation - Implement DistBetweenObjs as sqrt(dx*dx + dy*dy) in pxrt_e_funcs.lua or flag it as missing library function

- **bl_script.pxc:22-25 / bl_script.lua:20-24** - high - keySync object and AddKey method not implemented - FirstFrame calls keySync->AddKey(49..53) for barrel selection keys 1-5, but runtime has no keySync global or AddKey method - Scripts will fail at initialization - Implement keySync as a stub object with AddKey method or document as unsupported input feature

- **bl_script.pxc:525 / bl_script.lua:454** - high - ClearIgnoreList method missing - CTazerShot constructor calls self:ClearIgnoreList() but runtime has no implementation for this collision list method - Tazer shots may collide incorrectly - Implement ClearIgnoreList stub in runtime or document as missing collision feature

- **bl_script.pxc:550-551 / bl_script.lua:470-471** - high - ClearPoints and AddPoint methods missing - CTazerShot constructor calls ClearPoints() and AddPoint(x,y) for beam rendering, but runtime has no implementation - Tazer beam graphics will not render - Implement point list stubs or document as missing render feature

- **icybarrel_logic_bl.pxc:77 / icybarrel_logic_bl.lua:65** - med - CWorm field extension swimsuit not initialized properly - Override constructor adds swimsuit=false field but transpiled code initializes it to 0 (integer) instead of boolean false - Field type mismatch may cause logic errors - Transpiler should emit swimsuit=0 or runtime should normalize boolean fields

- **bl_script.pxc:496 / bl_script.lua:424** - low - barrelselector type inconsistency - PXC checks barrelselector==true but transpiled Lua checks __G__.barrelselector==1 - Type coercion works but inconsistent with source - Document that PX bool becomes Lua 0/1 integer

- **paratest.pxc:104,124 / paratest.lua:70,81** - med - WS_PARACHUTE state check implemented but state transitions not writable - Transpiled code reads Owner.ObjState==K.WS_PARACHUTE correctly (constant 0x7D defined in pxrt_e_consts.lua) but PX code also writes worm velocity/state which runtime may not support - Glider physics cannot override parachute behavior - Check if worm state/velocity writes are stubbed

- **paratest.pxc:139-140 / paratest.lua:89** - high - SetAnimEx call on worm animator stubbed - Code calls Owner->Anim->Reset() and Owner->Anim->SetAnimEx(136,0.0) to hide worm sprite, but pxrt_e_classes.lua:180 shows CW.SetAnimEx returns 0 (no-op) - Glider sprite replacement will not work, worm visible during glide - Document that custom animation overrides are unsupported or implement SetAnimEx hook

- **paratest.pxc:131-133,153-155** - med - CalculateSoundVolume returns fixed 1.0, CalculateSoundPan uses camera X - PX calculates volume/pan from distance to camera, runtime pxrt_e_funcs.lua:119-125 returns fixed volume=1.0 and simple pan based on cameraX - Glider sounds play at wrong volume/pan - Acceptable approximation but flag as simplified implementation

- **paratest.pxc:173 / paratest.lua:106** - med - TurnSide field read but worm facing direction may not update correctly - Code reads Owner->TurnSide to determine glider angle direction (left vs right facing) - Runtime defines TurnSide at offset 0x1A8 in pxrt_engine.lua:205 as readable - Verify TurnSide updates during gameplay or glider will face wrong direction

- **utility_hangglider hand-written port vs transpiled** - med - Hand-written main.lua (lines 162-563) documents that worm state detection, velocity write-back, TraceMask raycasting, and CSpriteAnim::SetAnimEx override have no wkJellyWorm equivalent and are stubbed with TODO(port) comments - Transpiled paratest.lua calls these features directly expecting full PX behavior - Glider physics/rendering incomplete in both versions but hand-written port is more honest about limitations - Prefer documenting unsupported features rather than silently stubbing

## Notes

- Did not verify asset loading (sprites/sounds) as files exist but runtime resolution may differ
- Did not check CTazerShot::Message and CTazerShot::Think methods for additional missing features
- Runtime implements WS_FROZEN constant (0x86) correctly so IceDrum freeze logic should work if DistBetweenObjs is added
- FireFinal override chain is implemented in runtime (pxrt_e_hooks.lua) so weapon interception works
- GetWeaponByName and CheckName are implemented so weapon detection works
- MakeHole terrain modification is implemented (pxrt_e_terrain.lua:145)
- TraceMask is implemented in pxrt_e_soft.lua:344 but may not be wired to all call sites
