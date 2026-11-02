import sys
from PIL import Image, ImageDraw, ImageOps
F = "/Users/educloud/orquestra/projetos/livia-oliveira/demandas/a8cda9e8/brutos/web1600/"
nomes = sys.argv[2:]
W = 300
sheet = Image.new("RGB", (W * len(nomes), 480), "white")
d = ImageDraw.Draw(sheet)
for i, n in enumerate(nomes):
    im = ImageOps.exif_transpose(Image.open(F + f"2L2A{n}.jpg")).convert("RGB")
    s = W / im.width
    im = im.resize((W, int(im.height * s)))
    dd = ImageDraw.Draw(im)
    for y in range(0, 1600, 200):
        dd.line([(0, y * s), (W, y * s)], fill=(0, 255, 0))
        dd.text((2, y * s), str(y), fill=(0, 255, 0))
    for x in range(0, 1067, 200):
        dd.line([(x * s, 0), (x * s, im.height)], fill=(255, 0, 255))
        dd.text((x * s + 2, 10), str(x), fill=(255, 0, 255))
    sheet.paste(im, (i * W, 30))
    d.text((i * W + 5, 5), n, fill="black")
sheet.save(sys.argv[1])
