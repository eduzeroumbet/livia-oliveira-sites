"""Tira prints das 4 páginas (desktop 1440 e mobile 390) em _catalogo/prints/.

Uso: /Users/educloud/orquestra/.venv/bin/python _catalogo/prints.py
Requer: playwright + chromium (python -m playwright install chromium).
"""
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_catalogo" / "prints"
PAGES = {
    "bio": "index.html",
    "curso": "curso/index.html",
    "consultoria": "consultoria/index.html",
    "terapia": "terapia/index.html",
}
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for vp_name, vp in VIEWPORTS.items():
            ctx = browser.new_context(
                viewport=vp,
                device_scale_factor=1,
                is_mobile=vp_name == "mobile",
                has_touch=vp_name == "mobile",
            )
            page = ctx.new_page()
            for name, rel in PAGES.items():
                page.goto((ROOT / rel).as_uri(), wait_until="networkidle")
                # força o carregamento das imagens lazy antes do print de página inteira
                page.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager')")
                page.wait_for_timeout(600)
                largura = page.evaluate("document.documentElement.scrollWidth")
                if largura > vp["width"]:
                    print(f"ATENÇÃO {name} {vp_name}: rolagem horizontal ({largura}px > {vp['width']}px)")
                destino = OUT / f"{name}-{vp_name}.png"
                page.screenshot(path=str(destino), full_page=True)
                print(destino.relative_to(ROOT))
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
