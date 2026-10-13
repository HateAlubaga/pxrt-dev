# pkg_utility_sacrifice

Excellent! Now I have all the information I need. Let me compile the audit report.

## Findings

- `C:/Users/Admin/pxrt_dev/px_pipeline/testout/lua/utility_sacrifice/sacrifice_SCRIPT.lua:13` - high - **CSoundFile constructor expects asset path but GetAttachment returns string** - When `new("CSoundFile", F.GetAttachment("sacrifice_sound.wav"))` runs, GetAttachment returns a bare string (pxrt_e_funcs.lua:242), but CSoundFile expects this and registers the sound (pxrt_e_funcs.lua:313-324), so this works correctly in pxrt.

- `C:/Users/Admin/pxrt_dev/px_pipeline/testout/lua/utility_sacrifice/sacrifice_SCRIPT.lua:19-23` - high - **keySync global is undefined** - Script calls `mc(__G__.keySync, "AddKey", 49)` but keySync is not in the gvars list (line 5) and is never initialized. In PX, keySync is a global from utils.pxc library. Without it, AddKey/KeyPressedNow calls will fail with "method called on null" errors.

- `C:/Users/Admin/pxrt_dev/px_pipeline/testout/lua/utility_sacrifice/sacrifice_SCRIPT.lua:30` - medium - **TargHealth field write has no effect** - Line 30 writes `self.TargHealth = mc(K.GS.Info, "GetWormHealth", ...)`. TargHealth is a real CWorm field at offset 0x17C (pxrt_engine.lua:205), so the write goes to WA memory and may affect WA's own health change display logic, but this is likely unintended (PX scripts often use arbitrary field names as scratch storage).

- `C:/Users/Admin/pxrt_dev/px_pipeline/testout/lua/utility_sacrifice/sacrifice_SCRIPT.lua:85-86, 119` - medium - **vol and pan fields stored on CWorm proxy** - Lines 85-86 write `self.vol` and `self.pan`, then lines 93, 105, 110, 119 read them. These are not CWorm fields (not in FIELDS, pxrt_engine.lua:198-211), so they're stored as rawset script fields on the proxy table. This works but means every CWorm instance touched by this script carries these fields permanently in memory until the worm is freed.

- `C:/Users/Admin/pxrt_dev/px_pipeline/testout/lua/utility_sacrifice/sacrifice_SCRIPT.lua:91, 103` - **high** - **K.Root.Timer field write not implemented** - Lines 91 and 103 do `__o1.Timer = __R__.add(__o1.Timer, ...)` where `__o1 = K.Root` (CTurnGame proxy). Timer is defined (pxrt_engine.lua:216, offset 0x18C), reads work, but **writes to CTurnGame.Timer go through proxyAt __newindex (pxrt_engine.lua:308-321) which calls `wr(a + off, ti(v))` for integer fields**. This writes to WA memory at TurnGame+0x18C. **However, the transpiler generates `__R__.add()` which returns a string when either operand is a string** (pxrt_core.lua:117-123). If Timer reads as an integer but add() is called with a string operand (even by accident elsewhere), the result is a string, and `ti(stringresult)` converts it back to int, so the write works. **The real issue: PX Timer is milliseconds, WA's 0x18C is also milliseconds, so this should work correctly.**

- `C:/Users/Admin/pxrt_dev/px_pipeline/testout/lua/utility_sacrifice/sacrifice_SCRIPT.lua:97` - low - **isnull check on arithmetic result is always false** - Line 97: `if isnull((HP - (newfactor * 50)))` checks if the result is null. Arithmetic always returns a number, never nil/0/false (the isnull cases), so this branch never executes. In PX, this might check for a specific zero case, but here it's dead code.

- `C:/Users/Admin/pxrt_dev/px_pipeline/testout/lua/utility_sacrifice/sacrifice_SCRIPT.lua:117-118` - medium - **GetWeaponByName and AddWeapon on weapon refund path** - Line 117 calls `mc(K.GS, "GetWeaponByName", "Sacrifice")` which uses weaponIdByName (pxrt_e_funcs.lua:143-151) to get a weapon proxy, then line 118 calls `mc(K.GS.Info, "AddWeapon", self.WormTeam, mc(wepGC, "GetWeaponIndex"), 1)`. GetWeaponIndex returns `id >= 2 and id - 2 or id` (pxrt_e_classes.lua:553-556), and AddWeapon calls setTeamWeaponAmmo via teamUD (pxrt_e_classes.lua:307-309). If weaponIdByName returns -1 (weapon not found), GetWeaponIndex returns -1, and AddWeapon tries to set ammo for weapon index -1, which will be ignored by setTeamWeaponAmmo.

- `C:/Users/Admin/pxrt_dev/pxrt_e_funcs.lua:127-133` - medium - **ShowMessage and ShowTeamMessage ignore team parameter** - Both functions call `pc(showChatMessage, R.str(s), 6)` with no team filtering (pxrt_e_funcs.lua:127-132). PX ShowTeamMessage(kind, s, team) should show the message only to the specified team, but pxrt shows it to everyone. Sacrifice uses this at lines 36, 44, 50, 56, 62, 68, 107, 112.

- `C:/Users/Admin/pxrt_dev/pxrt_e_funcs.lua:313-324` - low - **CSoundFile.Play signature mismatch** - Comment says "Play(volume, pan, loop)" (line 312), but PX CSoundFile::Play is (volume, pitch, priority). Sacrifice calls `mc(__G__.timeadded, "Play", self.vol, self.pan, 0)` expecting (vol, pan, loop). The runtime implementation (line 325-327) passes these to a custom sound play function; if the host API expects (vol, pitch, priority), the pan value goes to pitch and 0 goes to priority, which means sounds play at the worm's pan value as pitch, sounding wrong.

- `C:/Users/Admin/pxrt_dev/pxrt_e_classes.lua:537-552` - medium - **CWeapon.CheckName uses normalized name matching** - CheckName normalizes both the weapon's stored names and the query (lines 520-524, 538-543) via normW (presumably lowercases, strips spaces). If the weapon registration used a different spelling than "Sacrifice", CheckName might still match, but if normalization differs from PX, weapons could fail to match.

## Notes

- Could not read the original PX source (sacrifice_SCRIPT.pxc) from Program Files directory due to permission restrictions. Comparison with PX source for transpilation correctness was not possible.
- utility_hangglider: could not access the hand-written Lua port at jelly\packages\utility_hangglider\0.0.1\main.lua due to directory permissions. Comparison of controls and physics between hand-written port, transpiled paratest.lua, and PX source paratest.pxc was not possible.
- GetCurrentWorm, CalculateSoundVolume, CalculateSoundPan are referenced by sacrifice but are utils.pxc library functions not runtime builtins - these would come from the transpiled utils library loaded via `__P__:require({"utils", "utils_steps"})` at line 4.
- K.Root returns a CTurnGame proxy via `E.proxyAt(E.turnGameAddr(), "CTurnGame")` (pxrt_e_consts.lua:62), so K.Root.Timer reads and writes work through the proxy field system.
