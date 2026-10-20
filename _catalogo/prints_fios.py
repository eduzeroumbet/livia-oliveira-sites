"""Prints só do hero da versão B do curso (fios) em 0,3 s, 2,5 s e 7 s, em _catalogo/prints/fios-*.png.
Também confere que o canvas tem pixels desenhados e que o console não tem erros.

Uso: /Users/educloud/orquestra/.venv/bin/python _catalogo/prints_fios.py
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_catalogo" / "prints"
PAGINA = ROOT / "curso" / "versao-b" / "index.html"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}
MOMENTOS = [("0s3", 300), ("2s5", 2500), ("7s", 7000)]

# fração de pixels do canvas com alfa > 0 (amostrando uma grade)
PIXELS = """() => {
  const c = document.querySelector('.hero__fios');
  const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  let cheios = 0, total = 0;
  for (let i = 3; i < d.length; i += 4 * 37) { total++; if (d[i] > 0) cheios++; }
  return { w: c.width, h: c.height, fracao: cheios / total };
}"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    falhas = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vp_name, vp in VIEWPORTS.items():
            for reduz in (False, True):
                ctx = browser.new_context(
                    viewport=vp,
                    device_scale_factor=2 if vp_name == "mobile" else 1,
                    is_mobile=vp_name == "mobile",
                    has_touch=vp_name == "mobile",
                    reduced_motion="reduce" if reduz else "no-preference",
                )
                page = ctx.new_page()
                erros = []
                page.on("console", lambda m: m.type == "error" and erros.append(m.text))
                page.on("pageerror", lambda e: erros.append(str(e)))
                page.goto(PAGINA.as_uri(), wait_until="load")
                inicio = page.evaluate("performance.now()")
                momentos = MOMENTOS if not reduz else [("reduz", 300)]
                for nome, ms in momentos:
                    falta = ms - (page.evaluate("performance.now()") - inicio)
                    if falta > 0:
                        page.wait_for_timeout(falta)
                    destino = OUT / f"fios-{vp_name}-{nome}.png"
                    page.screenshot(path=str(destino), clip={"x": 0, "y": 0, **vp})
                    px = page.evaluate(PIXELS)
                    print(f"{destino.relative_to(ROOT)}  canvas {px['w']}x{px['h']}  pixels desenhados {px['fracao']:.1%}")
                    if px["fracao"] < 0.005:
                        falhas.append(f"{vp_name} {nome}: canvas quase vazio")
                largura = page.evaluate("document.documentElement.scrollWidth")
                if largura > vp["width"]:
                    falhas.append(f"{vp_name}: rolagem horizontal ({largura}px)")
                if erros:
                    falhas.append(f"{vp_name}{' reduz' if reduz else ''}: erros no console: {erros}")
                ctx.close()
        browser.close()
    if falhas:
        print("FALHOU:")
        for f in falhas:
            print(" -", f)
        sys.exit(1)
    print("OK: canvas desenhado, sem erros no console e sem rolagem horizontal.")


if __name__ == "__main__":
    main()
