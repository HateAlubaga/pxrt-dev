import sys
from PIL import Image, ImageDraw
# usage: sheet.py in.png out.png frameW frameH cols [scale]
src, dst, fw, fh, cols = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
scale = int(sys.argv[6]) if len(sys.argv) > 6 else 2
im = Image.open(src).convert("RGBA")
n = im.height // fh
rows = (n + cols - 1) // cols
out = Image.new("RGBA", (cols * fw * scale, rows * fh * scale), (60, 60, 90, 255))
d = ImageDraw.Draw(out)
for i in range(n):
    f = im.crop((0, i * fh, fw, (i + 1) * fh)).resize((fw * scale, fh * scale), Image.NEAREST)
    x, y = (i % cols) * fw * scale, (i // cols) * fh * scale
    out.paste(f, (x, y), f)
    d.text((x + 2, y + 2), str(i), fill=(255, 255, 0, 255))
out.save(dst)
print(n, "frames")
