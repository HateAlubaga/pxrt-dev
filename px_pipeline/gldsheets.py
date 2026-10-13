import sys, math, os
from PIL import Image
A = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages\utility_hangglider\0.0.1\assets"
OUT = sys.argv[1] if len(sys.argv) > 1 else A
src = Image.open(os.path.join(A, "wgldlnk.png")).convert("RGBA")
W, FH = 128, 128
frames = [src.crop((0, i*FH, W, (i+1)*FH)) for i in range(10)]
S = 140   # rotated frame box; open glider radius ~68px from centre

def rot(fr, a):
    big = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    big.paste(fr, ((S-W)//2, (S-FH)//2))
    # positive glider angle = nose down; nose points left, so counter-clockwise on screen
    r = big.rotate(math.degrees(a), resample=Image.NEAREST, center=(S/2, S/2))
    px = r.load()
    for y in range(S):
        for x in range(S):
            p = px[x, y]
            px[x, y] = (0, 0, 0, 0) if p[3] < 128 else (p[0], p[1], p[2], 255)
    return r

def sheet(imgs, name):
    sh = Image.new("RGBA", (S, S*len(imgs)), (0, 0, 0, 0))
    for i, im in enumerate(imgs):
        sh.paste(im, (0, i*S))
    sh.save(os.path.join(OUT, name))
    print(name, sh.size, len(imgs))

N = 58
angs = [-1.5 + 3.0*i/(N-1) for i in range(N)]
sheet([rot(frames[9], a) for a in angs[:29]], "wgldrot1.png")
sheet([rot(frames[9], a) for a in angs[29:]], "wgldrot2.png")
UA = [0.0, 0.5, 1.0]
sheet([rot(frames[f], a) for f in range(9) for a in UA], "wgldunf.png")
Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(os.path.join(OUT, "wgldnone.png"))
print("wgldnone.png")

if len(sys.argv) > 1:
    r1 = Image.open(os.path.join(OUT, "wgldrot1.png"))
    r2 = Image.open(os.path.join(OUT, "wgldrot2.png"))
    pv = Image.new("RGBA", (S*6, S), (200, 200, 255, 255))
    for k, (sh, i) in enumerate([(r1, 0), (r1, 14), (r1, 28), (r2, 0), (r2, 14), (r2, 28)]):
        fr = sh.crop((0, i*S, S, (i+1)*S))
        pv.paste(fr, (k*S, 0), fr)
    pv.save(os.path.join(OUT, "preview.png"))
