"""Prepara os arquivos binários do site.

1. Copia os vídeos comprimidos (assets/video/) da pasta principal do repositório, se faltarem aqui.
2. Gera as fotos WebP otimizadas em assets/img/ a partir do ensaio em 1600px.
3. Gera as imagens Open Graph (1200x630, JPEG).

Uso: /Users/educloud/orquestra/.venv/bin/python _catalogo/preparar_assets.py
"""
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
FOTOS = Path("/Users/educloud/orquestra/projetos/livia-oliveira/demandas/a8cda9e8/brutos/web1600")
VIDEOS_ORIGEM = Path("/Users/educloud/orquestra/repos/livia-oliveira-sites/assets/video")
IMG = ROOT / "assets" / "img"
VIDEO = ROOT / "assets" / "video"

LIMITE = 180 * 1024  # alvo: menos de 180 KB por WebP

# (arquivo de saída, foto, recorte (esq, topo, dir, base) na foto de 1600px, tamanho final)
# As fotos verticais têm 1067x1600; a 0823 é horizontal (1600x1067).
# Os tamanhos finais batem com os width/height usados no HTML.
WEBP = [
    ("avatar-1204.webp", "2L2A1204", (185, 300, 945, 1060), (480, 480)),
    ("curso-hero-0688.webp", "2L2A0688", (0, 100, 1067, 1434), (960, 1200)),
    ("curso-frentes-0709.webp", "2L2A0709", (0, 180, 1067, 1514), (800, 1000)),
    ("curso-sobre-1204.webp", "2L2A1204", (0, 150, 1067, 1484), (800, 1000)),
    ("curso-cta-1102-2.webp", "2L2A1102-2", (0, 0, 1067, 1334), (800, 1000)),
    ("consultoria-hero-0730.webp", "2L2A0730", (0, 180, 1067, 1514), (960, 1200)),
    ("consultoria-conversa-0718.webp", "2L2A0718", (0, 266, 1067, 1600), (800, 1000)),
    # 0823: corta o softbox do canto superior direito (fica acima de y=290 e à direita de x=1090)
    ("consultoria-mesa-0823.webp", "2L2A0823", (115, 291, 1085, 1067), (800, 640)),
    ("consultoria-sobre-1340.webp", "2L2A1340", (0, 100, 1067, 1434), (800, 1000)),
    ("terapia-hero-0973.webp", "2L2A0973", (0, 150, 1067, 1484), (960, 1200)),
    ("terapia-sessoes-1289.webp", "2L2A1289", (0, 180, 1067, 1514), (800, 1000)),
    ("terapia-sobre-0858.webp", "2L2A0858", (0, 200, 1067, 1534), (800, 1000)),
]

# Open Graph 1200x630 (proporção 1,905): faixa de 1067x560 na foto vertical, sem texto.
OG = [
    ("og-curso.jpg", "2L2A0688", (0, 170, 1067, 730)),
    ("og-consultoria.jpg", "2L2A0730", (0, 200, 1067, 760)),
    ("og-terapia.jpg", "2L2A0973", (0, 400, 1067, 960)),
]


def abrir(nome):
    img = Image.open(FOTOS / f"{nome}.jpg")
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def recortar(img, box):
    """Recorta sem sair dos limites da foto (evita bordas pretas se a foto tiver outro tamanho)."""
    w, h = img.size
    l, t, r, b = box
    return img.crop((max(0, l), max(0, t), min(w, r), min(h, b)))


def copiar_videos():
    VIDEO.mkdir(parents=True, exist_ok=True)
    if not VIDEOS_ORIGEM.exists():
        print("Pasta de vídeos de origem não encontrada; mantendo o que já existe em assets/video/")
        return
    for f in sorted(VIDEOS_ORIGEM.iterdir()):
        destino = VIDEO / f.name
        if f.is_file() and not destino.exists():
            shutil.copy2(f, destino)
            print(f"vídeo copiado: {f.name}")


def salvar_webp(img, destino):
    for q in (78, 74, 70, 66, 62, 58):
        img.save(destino, "WEBP", quality=q, method=6)
        if destino.stat().st_size <= LIMITE:
            return q
    return q


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    copiar_videos()
    ok = True
    for saida, foto, box, tamanho in WEBP:
        img = recortar(abrir(foto), box).resize(tamanho, Image.LANCZOS)
        destino = IMG / saida
        q = salvar_webp(img, destino)
        kb = destino.stat().st_size / 1024
        print(f"{saida:34} {tamanho[0]}x{tamanho[1]}  q{q}  {kb:6.1f} KB")
        ok &= kb * 1024 <= LIMITE
    for saida, foto, box in OG:
        img = recortar(abrir(foto), box).resize((1200, 630), Image.LANCZOS)
        destino = IMG / saida
        img.save(destino, "JPEG", quality=82, optimize=True, progressive=True)
        print(f"{saida:34} 1200x630  {destino.stat().st_size / 1024:6.1f} KB")
    if not ok:
        print("Atenção: alguma imagem passou de 180 KB.")
        sys.exit(1)


if __name__ == "__main__":
    main()
