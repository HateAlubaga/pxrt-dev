"""Survey ProjectX scripts in all packages: WormSprite / WeapSprite usage and params."""
import os, re, glob, json, collections

P = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
out = {}
stats = collections.Counter()
for pkg in sorted(os.listdir(P)):
    for ver in glob.glob(os.path.join(P, pkg, "*")):
        sdir = os.path.join(ver, "scripts_px")
        if not os.path.isdir(sdir):
            continue
        for f in glob.glob(os.path.join(sdir, "*.pxc")):
            src = open(f, encoding="latin1").read()
            src_nc = re.sub(r"//[^\n]*", "", src)
            src_nc = re.sub(r"/\*.*?\*/", "", src_nc, flags=re.S)
            n_worm = len(re.findall(r"new\s+WormSprite\s*\(", src_nc))
            n_weap = len(re.findall(r"new\s+WeapSprite\s*\(", src_nc))
            if n_worm: stats["files_wormsprite"] += 1
            if n_weap: stats["files_weapsprite"] += 1
            if n_worm or n_weap:
                out.setdefault(pkg, []).append((os.path.basename(f), n_worm, n_weap))
print(stats)
print(len(out), "packages")
for k in list(out)[:40]:
    print(k, out[k])
