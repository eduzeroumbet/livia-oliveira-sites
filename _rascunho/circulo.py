import sys
from PIL import Image, ImageDraw
im = Image.open(sys.argv[1]).convert("RGB")
w, h = im.size
fundo = Image.new("RGB", (w, h), (236, 229, 221))
m = Image.new("L", (w, h), 0)
ImageDraw.Draw(m).ellipse((0, 0, w - 1, h - 1), fill=255)
fundo.paste(im, (0, 0), m)
pequeno = fundo.resize((96, 96), Image.LANCZOS)
folha = Image.new("RGB", (w + 140, h), "white")
folha.paste(fundo, (0, 0))
folha.paste(pequeno, (w + 20, 20))
folha.save(sys.argv[2])
