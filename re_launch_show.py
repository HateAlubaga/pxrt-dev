import json, sys, io
if __name__ == '__main__':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
mem = {int(k): v for k, v in json.load(open(r"C:/Users/Admin/pxrt_dev/re_launch_wtab.json")).items()}
S = 0x1d0
names = "None|Bazooka|HomingMissile|Mortar|HomingPigeon|SheepLauncher|Grenade|ClusterBomb|BananaBomb|BattleAxe|Earthquake|Shotgun|Handgun|Uzi|Minigun|Longbow|FirePunch|DragonBall|Kamikaze|SuicideBomber|Prod|Dynamite|Mine|Sheep|SuperSheep|MoleBomb|AirStrike|NapalmStrike|MailStrike|MineStrike|Molotov|BlowTorch|Drill|Girder|BaseballBat|GirderPack|NinjaRope|Bungee|Parachute|Teleport|Scales|SuperBanana|HolyGrenade|FlameThrower|SalvationArmy|MadCow|OldWoman|Donkey|NukeTest|Armageddon|SkipGo|Surrender|SelectWorm|Freeze|MagicBullet|JetPack|Wk|Wl|Wm|Wn|Wo|Wp|Wq|Wr|Ws|Wt".split("|")
def fmt(v):
    if v is None: return "?"
    if v >= 0x80000000: v -= 1 << 32
    return str(v) if abs(v) < 0x100000 else hex(v)
def show(ids, lo=0x3c, hi=0x1d0):
    print("entry  L+off " + " ".join("%8s" % (names[i][:8] if i < len(names) else str(i)) for i in ids))
    for f in range(lo, hi, 4):
        row = [mem.get(w * S + f, None) for w in ids]
        raw = [(w * S + f) in mem for w in ids]
        if any(raw):
            print("+%03x  L+%03x %s" % (f, f - 0x3c, " ".join("%8s" % (fmt(mem[w * S + f]) if (w*S+f) in mem else ".") for w in ids)))
if __name__ == "__main__":
    ids = [int(x) for x in sys.argv[1].split(",")]
    lo = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x3c
    hi = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x1d0
    show(ids, lo, hi)
