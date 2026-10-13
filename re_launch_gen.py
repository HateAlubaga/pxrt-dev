import json
B = 0x3c
F = {}


def add(name, off, kind, conf, note, extra=False):
    d = {"off": off, "entryOff": off + B, "kind": kind, "conf": conf, "note": note}
    if extra:
        d["extra"] = True
    F[name] = d


add("spriteSize", 0x00, "int", "high", "Launch copy +0 (outside the DB copy). Passed as the 4th arg (collision mask / radius index) of ConstructCGameTask in the CTaskMissile ctor. Bazooka/grenade 2; PX clustlet reset uses 2.")
add("launchSpeed", 0x04, "int", "high", "Fixed shot power in percent; 0 = use player charge. Vanilla: Mortar 100, Pigeon 33, Sheep Launcher 50, all others 0. PX clustlet script sets 0.")
add("runAway", 0x08, "bool", "high", "Worm 'run away' shout 800 ms before the blast (missile +0x164 compared/set in the frame handler). 1 for Grenade/Cluster/Banana, 0 for Bazooka. PX clustlet script sets true.")
add("explosion.flags", 0x0c, "int", "high", "Bitfield; DB+0 (missile +0x2d4). OR-ed into object collision flags and tested in the collide function (0x508c90). 137342 for Bazooka/clustlets, 0 for Grenade, 0x400000 = skim only, 1 in pyro scripts. Treat as int.")
add("explosion.bias", 0x10, "int", "high", "DB+4 (+0x2d8). 4th arg of CreateExplosion/DoExplosion ('unkB'). 0 in every vanilla weapon checked; PX scripts set 0. Argument order fixed by the explosion call at 0x509b05..0x509b38.")
add("explosion.pushPower", 0x14, "int", "high", "DB+8 (+0x2dc). Percent. 100 in Bazooka/clustlets; PX script 100.")
add("explosion.damage", 0x18, "int", "high", "DB+0xC (+0x2e0). Bazooka 50, Grenade 50, Mortar 30, Cluster/Banana clustlets 30/75; PX scripts override (20/60). Read at 0x509aee/0x509b12 together with dmgVar (damage-variance function 0x547cb0).")
add("explosion.dmgVar", 0x1c, "int", "high", "DB+0x10 (+0x2e4). Damage variance percent; consumed by 0x547cb0 at 0x509ae8. 0 in the vanilla weapons checked; PX airplane script 0.")
add("unk", 0x20, "int", "med", "DB+0x14 (+0x2e8). Divisor in the ctor: spriteIndex += (ShootDesc+0x20 - 1) % unk, i.e. number of sprite variants cycled across clustlets. 1 in vanilla clustlet blocks, 0 in plain block A. Keep name 'unk'.")
add("anim.spriteIndex", 0x24, "int", "high", "DB+0x18 (+0x2ec). Sprite id. Bazooka 48, Mortar 52, Banana clustlet 51, Cluster clustlet 54 (matches PX clustlet reset 54). Used by the missile render (0x5091a0).")
add("anim.type", 0x28, "enum", "high", "Offset certain (render switch at 0x5094ba, frame handler at 0x50b6aa, vanilla clustlet = 1 = WAT_Rotation). Raw values: 0 fuse-progress frame (frame = 1 - timer/countdown); 1 spin/rotation ([obj+0x8c] angle, [obj+0x98] spin; grenades, clusters, banana, homing); 2 face direction of travel (bazooka, mortar, sheep launcher); 3 speed-dependent frame offset with horizontal flip (pigeon, min(|vx|/2,3)); 4/5/6 frame advance each tick by [obj+0x128]/100, /50, /25 (slow/medium/fast; sheep family = 6). Name mapping: Rotation=1 (high), TrackMovement=2 (med-high), HSpeed=3 (med), Slow=4 / Medium=5 / Fast=6 (med-high), TrackSpeed=0 only by elimination (low). The existing pxrt_e_consts.lua WAT values (TrackMovement=0, Fast=1, TrackSpeed=2, Slow=3, Medium=4, Rotation=5, HSpeed=6) contradict the code.")
add("anim.trailIndex", 0x2c, "int", "high", "DB+0x20 (+0x2f4). Trail sprite id, 131 in vanilla and PX scripts. Base of the trail block read via edi=&+0x2f4 at 0x50ba79.")
add("anim.trailPower", 0x30, "int", "high", "DB+0x24 (+0x2f8). Trail puff spawn rate (accumulated each frame into [+0x114]). Bazooka 50, clustlets 20 (PX reset 20), banana clustlet 0.")
add("anim.trailSpeed", 0x34, "int", "high", "DB+0x28 (+0x2fc). Puff speed/scale argument (x 0x147a / 100). 100 everywhere vanilla; PX script 100.")
add("anim.unk", 0x38, "int", "med", "DB+0x2C (+0x300). Rate of underwater bubble puffs: used by the branch at 0x50bb8a taken when missile Y >= water level (spawns via 0x5472c0). 50 in all vanilla weapons except weapon 25 (200). PX script 50.")
add("speedMultipler", 0x3c, "int", "high", "DB+0x30 (+0x304). Percent speed scale, 100 default; read in init at 0x50817c.")
add("windFactor", 0x40, "int", "high", "DB+0x34 (+0x308), copied to CGObject +0x5c (WindFactor). Bazooka 100, Grenade/clustlets 0.")
add("gravityFactor", 0x48, "int", "high", "DB+0x3C (+0x310), copied to CGObject +0x60 (GravityFactor). 100 default, PX airplane 0.")
add("countdownFrom", 0x4c, "int", "high", "DB+0x40 (+0x314), ms. Fuse start for fused projectiles (Grenade/Cluster/Banana 5000), 0 for rocket types. Compared in the render at 0x509269 (fuse label).")
add("timeBeforeExplosion", 0x50, "int", "high", "DB+0x44 (+0x318), ms; entry +0x8C. Max lifetime (Bazooka 9000, Homing 10000, clustlets 9000, PX reset 10000); overwritten from ShootDesc+0x28 at ctor 0x507f1c when nonzero. Also the divisor of the anim.type 0 frame.")
add("sound.soundIndex", 0x54, "int", "high", "DB+0x48 (+0x31c). Looped in-flight sound started in the ctor (0x508ab1 -> 0x546c20, handle in +0x3e4). 66 in PX nuke/oil-drum scripts, 0 in vanilla clustlets.")
add("sound.useExpSound", 0x58, "bool", "med", "DB+0x4C (+0x320). Gate for the delayed explosion sound: when set, the countdown at 0x50b868 only runs while the object is NOT moving (0x4fb580 false). Holy Hand Grenade = 1.")
add("sound.expSoundIndex", 0x5c, "int", "high", "DB+0x50 (+0x324). Sound played by PlaySoundLocal at 0x50b8a8 when the delay counter [+0x380] expires. Holy Hand Grenade 104.")
add("sound.expSoundDelay", 0x60, "int", "high", "DB+0x54 (+0x328), ms. Copied into the counter [+0x380] at ctor 0x507fb8; counter drops 20 per frame. Holy Hand Grenade 1800.")
add("explodeOnSpace", 0x64, "bool", "med", "DB+0x58 (+0x32c). Nonzero = missile reacts to the 'fire again' message 0x2c (HandleMessage 0x50b4e0 -> 0x50b557): value 1 detonates (SetState 1, or SetState 2 if explodeInto==3), value 2 re-arms (clears +0x314/+0x32c, random +0x37c). Vanilla 1 on sheep family and Sheep Launcher. Not exercised at runtime.")
add("action", 0x68, "enum", "med", "DB+0x5C (+0x330) = CMissile.ActionType. Offset certain. Raw values from the ctor/frame/water/collision switches: 0 none (valid, no special handling), 1 homing (Homing Missile, Pigeon), 2 ballistic with bounce% (Bazooka, Mortar, Grenade, clusters, banana, clustlets), 3 walker/sheep (turns at walls, crate pickup, sheep family), 4 jump-and-animate walker (unused in the vanilla table; 3-sprite cycle), 5 Sheep Launcher (ballistic like 2 plus launcher logic). PX name mapping is NOT verifiable from the exe: best guess None=0, Homing=1, Bounce=2, Roam=3 (med), Dig=4 (low). pxrt_e_consts.lua (Bounce=1, Homing=2, Dig=3) is almost certainly wrong.")
add("explodeInto", 0xb4, "enum", "high", "Launch copy +0xB4 (outside DB; +0x210). Explode-time switch at 0x509b43: 0 nothing, 1 clustlets (0x5096a0, first explosion only), 2 fire/napalm (0x509d70), 3 clustlet variant (same path as 1; also forces SetState 2 on fire-again). Matches WExplode_Nothing=0, Clustlets=1, Fire=2.")
add("wav", 0xb8, "int", "low", "UNRESOLVED. No script in the corpus reads or writes a launch 'wav'. Only candidate: launch copy +0xB8, a sound id played once at missile creation (PlaySoundGlobal at 0x507eab, block-A path only; Pigeon 51, Sheep Launcher 50). Do not rely on it.")

# extras (not requested)
add("movementRandomness", 0x44, "int", "med", "DB+0x38 (+0x30c). Random jitter applied to velocity in the frame handler (0x50b72f..0x50b75e).", True)
add("collisionFlags", 0x6c, "int", "med", "DB+0x60 (+0x334). OR-ed with explosion.flags into CGObject +0x34 at ctor (0x508273/0x508284); bit 0x40000000 tested at 0x50b24c. 0x400000 Bazooka/Mortar, 0x42187e sheep family.", True)
add("bounce", 0x70, "int", "med", "+0x338. Bounciness percent for action 2/5, copied to CGObject +0x70 (DumpingB) as value/100. 0 = use the player-set bounce (ShootDesc+0x24, M_SETBOUNCE). Banana 60, Pigeon 58, Mortar 1.", True)
add("friction", 0x74, "int", "med", "+0x33c. Percent scaled by the game friction setting (game+0xd780/0xd784), stored to CGObject +0x74. Grenade/Cluster/Banana 100.", True)
add("launchSound", 0xb8, "int", "med", "Same slot as the unresolved 'wav' candidate: sound id played once at creation.", True)
add("childCount", 0xbc, "int", "med", "Launch copy +0xBC (+0x218). Number of clustlets / fire particles spawned on explosion (loop at 0x509735). Mortar/Cluster/Banana 5, Napalm-type 40.", True)
add("childSpeed", 0xc0, "int", "low", "+0x21c. Base clustlet speed percent (30 vanilla).", True)
add("childSpeedVar", 0xc4, "int", "low", "+0x220. Multiplies childSpeed; random variation percent (30 vanilla).", True)
add("childSpread", 0xcc, "int", "low", "+0x228. Random angle spread in degrees (45 vanilla), used as (rand-0.5)*value*256/360.", True)

json.dump(F, open(r"C:/Users/Admin/pxrt_dev/launch_fields.json", "w"), indent=1)
print(len(F), "fields")
