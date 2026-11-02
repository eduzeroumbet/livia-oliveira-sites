"""Gera as imagens Open Graph com título (prévia do link no WhatsApp) e a foto de perfil do WhatsApp.

Cada imagem tem 1200x630, JPEG, menos de 200 KB: fundo da cor do tema (vinho ou petróleo, como as capas das
páginas de captação; creme na página inicial), foto do ensaio em arco e título em Noto Serif Display extra
condensada (a mesma do site, carregada do Google Fonts). Foto e título ficam no quadrado central de 630x630,
porque o WhatsApp às vezes recorta a prévia para quadrado ou mostra em miniatura.

Também gera _catalogo/whatsapp-perfil-640.jpg (640x640, sem texto), recortado para a foto redonda do WhatsApp.

Uso: /Users/educloud/orquestra/.venv/bin/python _catalogo/og.py [arquivo ...]
     (sem nome, todas; ex.: og.py og-quiz.jpg)
Requer: playwright + chromium (python -m playwright install chromium) e internet (fonte do Google Fonts).
Depois de gerar, abra cada imagem e confira: rosto inteiro, título sem cortar e acentos certos.
"""
import base64
import io
import sys
from pathlib import Path
from string import Template

from PIL import Image, ImageOps
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FOTOS = Path("/Users/educloud/orquestra/projetos/livia-oliveira/demandas/a8cda9e8/brutos/web1600")
IMG = ROOT / "assets" / "img"
PERFIL = ROOT / "_catalogo" / "whatsapp-perfil-640.jpg"

LIMITE = 200 * 1024  # menos de 200 KB por imagem

# Arco da foto: 260x290 na imagem (o recorte na foto de 1600px tem a mesma proporção, do alto da cabeça aos ombros).
ARCO = (260, 290)

# (arquivo, tema, foto, recorte (esq, topo, dir, base) na foto de 1600px, título, trecho em itálico, linha de apoio)
# O trecho em itálico vai numa linha própria, como no <em> dos títulos do site. Sem travessão nos textos.
OG = [
    ("og-home.jpg", "creme", "2L2A1204", (100, 100, 1000, 1104),
     "Lívia Oliveira", "", "Psicóloga clínica · CRP 07/18713"),
    ("og-curso-v2.jpg", "vinho", "2L2A0688", (150, 60, 850, 841),
     "Carreira", "com Sentido", "Curso para psicólogas clínicas, com Lívia Oliveira"),
    ("og-materiais.jpg", "vinho", "2L2A0709", (270, 300, 830, 925),
     "Materiais gratuitos", "para a sua clínica", "Para psicólogas, com Lívia Oliveira"),
    ("og-quiz.jpg", "vinho", "2L2A0906", (180, 360, 820, 1074),
     "Você está pronta", "para viver da clínica?", "Teste de 1 minuto"),
    ("og-calculadora.jpg", "petroleo", "2L2A0686", (230, 160, 870, 874),
     "Quanto deveria custar", "a sua sessão?", "Calculadora para psicólogas"),
    ("og-mat-mensagens.jpg", "vinho", "2L2A0730", (214, 120, 854, 834),
     "8 mensagens prontas", "para o WhatsApp", "Material gratuito para psicólogas"),
    ("og-mat-faltas.jpg", "petroleo", "2L2A0760", (337, 450, 837, 1008),
     "Política de faltas", "e pagamentos", "Material gratuito para psicólogas"),
    ("og-mat-etica.jpg", "vinho", "2L2A0745", (234, 420, 834, 1089),
     "Posso postar isso?", "", "Checklist ético para o Instagram da psicóloga"),
    ("og-mat-reajuste.jpg", "petroleo", "2L2A1340", (307, 150, 867, 775),
     "Como reajustar", "o valor da sessão", "Material gratuito para psicólogas"),
    ("og-mat-posts.jpg", "vinho", "2L2A1301", (218, 320, 778, 945),
     "30 ideias de posts", "", "Material gratuito para psicólogas"),
    ("og-mat-indicacoes.jpg", "petroleo", "2L2A0692", (214, 80, 854, 794),
     "Mensagens para", "médicos e colegas", "Material gratuito para psicólogas"),
]

# Foto de perfil do WhatsApp (recorte em círculo): 1204, com folga acima do cabelo e o rosto no meio do círculo.
# Começa em x=90 para tirar do círculo o equipamento escuro desfocado da borda esquerda.
PERFIL_FOTO = ("2L2A1204", (90, 70, 1067, 1047))

# Cores e gradientes das variáveis de assets/css/site.css (--wine, --rose, --cream, --grad-wine, --grad-petrol).
HTML = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+Display:ital,wdth,wght@0,62.5,400..700;1,62.5,400..700&display=block" rel="stylesheet">
<style>
:root { --wine: #6E172C; --petrol: #264056; --rose: #DBA8AD; --cream: #FCFAF6; --muted: #605151; }
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { width: 1200px; height: 630px; overflow: hidden; }
body { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 0;
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif; letter-spacing: -.015em; text-align: center;
  color: var(--cream); position: relative; }
body.vinho { background: linear-gradient(135deg, oklch(32% .12 10), oklch(40% .13 18)); }
body.petroleo { background: linear-gradient(135deg, oklch(32% .05 245), oklch(40% .06 240)); }
body.creme { background: var(--cream); color: var(--wine); }
/* brilho suave atrás da foto e arcos finos nas laterais (só enfeite, fora do quadrado central) */
.brilho { position: absolute; left: 50%; top: 40px; width: 560px; height: 560px; margin-left: -280px;
  border-radius: 50%; background: radial-gradient(closest-side, rgba(219, 168, 173, .22), rgba(219, 168, 173, 0)); }
.creme .brilho { background: radial-gradient(closest-side, rgba(219, 168, 173, .35), rgba(219, 168, 173, 0)); }
.lado { position: absolute; top: 70px; width: 300px; height: 620px; border: 2px solid rgba(219, 168, 173, .28);
  border-radius: 150px 150px 0 0; }
.lado.e { left: -110px; } .lado.d { right: -110px; }
.creme .lado { border-color: rgba(110, 23, 44, .14); }
.arco { position: relative; width: ${aw}px; height: ${ah}px; border-radius: ${r}px ${r}px 10px 10px;
  overflow: hidden; outline: 3px solid var(--rose); outline-offset: 7px; flex: none; }
.arco img { display: block; width: 100%; height: 100%; }
h1 { position: relative; margin-top: 34px; font-family: "Noto Serif Display", serif; font-stretch: 62.5%;
  font-weight: 500; line-height: 1.02; letter-spacing: -.045em; word-spacing: .08em; }
h1 span { display: block; white-space: nowrap; }
h1 em { display: block; white-space: nowrap; color: var(--rose); }
.creme h1 { color: var(--wine); } .creme h1 em { color: var(--petrol); }
p { position: relative; margin-top: 16px; white-space: nowrap; font-weight: 500; opacity: .92; }
.creme p { color: var(--muted); opacity: 1; }
</style></head>
<body class="${tema}">
<div class="brilho"></div><div class="lado e"></div><div class="lado d"></div>
<figure class="arco"><img src="data:image/jpeg;base64,${foto}" alt=""></figure>
<h1><span>${titulo}</span>${em}</h1>
<p>${apoio}</p>
<script>
// encaixa o título e a linha de apoio na largura do quadrado central (cada linha numa linha só)
function encaixa(el, max, de, ate) {
  for (let t = de; t >= ate; t--) {
    el.style.fontSize = t + "px";
    const larg = Math.max(...[...el.children, el].map(c => c.scrollWidth));
    if (larg <= max) return t;
  }
  return -1;
}
window.tamTitulo = encaixa(document.querySelector("h1"), 590, document.querySelector("h1 em") ? 84 : 96, 56);
window.tamApoio = encaixa(document.querySelector("p"), 590, 32, 22);
</script>
</body></html>"""


def abrir(nome):
    img = Image.open(FOTOS / f"{nome}.jpg")
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def recortar(img, box):
    """Recorta sem sair dos limites da foto (evita bordas pretas se a foto tiver outro tamanho)."""
    w, h = img.size
    l, t, r, b = box
    return img.crop((max(0, l), max(0, t), min(w, r), min(h, b)))


def foto_base64(foto, box):
    # 2x o tamanho do arco, para a redução do navegador ficar nítida
    img = recortar(abrir(foto), box).resize((ARCO[0] * 2, ARCO[1] * 2), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def salvar_jpeg(img, destino):
    # 4:4:4 (sem subamostragem de cor) para o texto rosé e vinho não borrar
    for q in (90, 86, 82, 78, 74, 70):
        img.save(destino, "JPEG", quality=q, optimize=True, progressive=True, subsampling=0)
        if destino.stat().st_size <= LIMITE:
            return q
    return q


def gerar_og(page, item):
    saida, tema, foto, box, titulo, em, apoio = item
    for texto in (titulo, em, apoio):
        assert "—" not in texto and "–" not in texto, f"{saida}: sem travessão"
    html = Template(HTML).substitute(
        aw=ARCO[0], ah=ARCO[1], r=ARCO[0] // 2, tema=tema, foto=foto_base64(foto, box),
        titulo=titulo, em=f"<em>{em}</em>" if em else "", apoio=apoio,
    )
    page.set_content(html, wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    if not page.evaluate("document.fonts.check('500 80px \"Noto Serif Display\"')"):
        raise SystemExit("A fonte Noto Serif Display não carregou (precisa de internet).")
    # roda o encaixe de novo, agora com a fonte carregada
    page.evaluate("""() => {
      window.tamTitulo = encaixa(document.querySelector("h1"), 590, document.querySelector("h1 em") ? 84 : 96, 56);
      window.tamApoio = encaixa(document.querySelector("p"), 590, 32, 22);
    }""")
    tam_titulo, tam_apoio = page.evaluate("[window.tamTitulo, window.tamApoio]")
    if tam_titulo < 0 or tam_apoio < 0:
        raise SystemExit(f"{saida}: texto não coube no quadrado central; encurte o título ou a linha de apoio")
    # tudo dentro da imagem (nada cortado embaixo)
    base = page.evaluate("document.querySelector('p').getBoundingClientRect().bottom")
    if base > 610:
        raise SystemExit(f"{saida}: texto passou da borda de baixo ({base:.0f}px)")
    png = page.screenshot(clip={"x": 0, "y": 0, "width": 1200, "height": 630})
    img = Image.open(io.BytesIO(png)).convert("RGB")
    destino = IMG / saida
    q = salvar_jpeg(img, destino)
    kb = destino.stat().st_size / 1024
    print(f"{saida:24} 1200x630  q{q}  {kb:6.1f} KB  {foto}  título {tam_titulo}px, apoio {tam_apoio}px")
    return destino.stat().st_size <= LIMITE


def gerar_perfil():
    foto, box = PERFIL_FOTO
    img = recortar(abrir(foto), box).resize((640, 640), Image.LANCZOS)
    q = salvar_jpeg(img, PERFIL)
    kb = PERFIL.stat().st_size / 1024
    print(f"{PERFIL.name:24} 640x640   q{q}  {kb:6.1f} KB  {foto}")
    return PERFIL.stat().st_size <= LIMITE


def main():
    nomes = sys.argv[1:]
    itens = [i for i in OG if not nomes or i[0] in nomes]
    ok = True
    if itens:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
            for item in itens:
                ok &= gerar_og(page, item)
            browser.close()
    if not nomes or PERFIL.name in nomes:
        ok &= gerar_perfil()
    if not ok:
        print("Atenção: alguma imagem passou de 200 KB.")
        sys.exit(1)


if __name__ == "__main__":
    main()
