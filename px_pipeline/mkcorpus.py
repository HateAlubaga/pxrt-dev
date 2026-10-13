"""Cache all package pxc sources + pxl libs into one JSON: corpus.json = {"pkg/file.pxc": text}."""
import os, json, time
PK = r"C:\Program Files (x86)\by Decepticon\Worms Armageddon\jelly\packages"
HERE = os.path.dirname(os.path.abspath(__file__))
t0 = time.time()
out = {}
pkgs = sorted(os.listdir(PK))
for i, p in enumerate(pkgs):
    d = os.path.join(PK, p, "0.0.1", "scripts_px")
    if not os.path.isdir(d):
        continue
    for fn in os.listdir(d):
        if fn.lower().endswith(".pxc"):
            with open(os.path.join(d, fn), "rb") as f:
                out[p + "/" + fn] = f.read().decode("latin-1").replace("\r\n", "\n")
    if i % 100 == 0:
        print(i, len(out), round(time.time() - t0, 1), flush=True)
for fn in os.listdir(os.path.join(HERE, "pxl")):
    if fn.endswith(".pxc"):
        out["@lib/" + fn] = open(os.path.join(HERE, "pxl", fn), encoding="utf-8").read()
json.dump(out, open(os.path.join(HERE, "corpus.json"), "w", encoding="utf-8"))
print("files", len(out), "chars", sum(map(len, out.values())), "sec", round(time.time() - t0, 1))
