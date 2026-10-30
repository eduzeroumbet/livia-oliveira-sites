"""Tira prints das páginas (desktop 1440 e mobile 390) em _catalogo/prints/.

Uso: /Users/educloud/orquestra/.venv/bin/python _catalogo/prints.py [nome ...]
     (sem nome, todas as páginas; ex.: prints.py curso-inscricao, ou só as de captação:
      prints.py materiais-hub materiais-mensagens-bloqueada materiais-mensagens-liberada materiais-faltas
      materiais-etica materiais-posts quiz-capa quiz-pergunta quiz-resultado calculadora calculadora-resultado)
Requer: playwright + chromium (python -m playwright install chromium).
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "_catalogo" / "prints"
PAGES = {
    "bio": "index.html",
    "curso-b": "curso/b/index.html",
    "curso-a": "curso/index.html",
    "curso-versao-b": "curso/versao-b/index.html",
    "curso-inscricao": "curso/inscricao/index.html",
    "consultoria": "consultoria/index.html",
    "terapia": "terapia/index.html",
    "terapia-b": "terapia/b/index.html",
    # páginas de captação (temas): (arquivo, JS rodado depois de carregar para chegar ao estado do print)
    "materiais-hub": "materiais/index.html",
    "materiais-mensagens-bloqueada": "materiais/mensagens/index.html",
    "materiais-mensagens-liberada": ("materiais/mensagens/index.html", "LIBERA"),
    "materiais-faltas": "materiais/faltas/index.html",
    "materiais-etica": "materiais/etica/index.html",
    "materiais-posts": "materiais/posts/index.html",
    "quiz-capa": "quiz/index.html",
    "quiz-pergunta": ("quiz/index.html", "document.getElementById('comecar').click()"),
    "quiz-resultado": ("quiz/index.html", "document.getElementById('comecar').click();"
                       " for (const r of 'SNSNS') document.querySelector('.quiz-op[data-resposta=' + r + ']').click()"),
    "calculadora": "calculadora/index.html",
    "calculadora-resultado": ("calculadora/index.html", "document.querySelector('#calc button[type=submit]').click()"),
}
# liberado: o mesmo localStorage do cadastro; recarrega para o script do <head> abrir a página liberada
LIBERA = "localStorage.setItem('livia_mat_ok', '1')"
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844},
}


def main():
    pages = {k: v for k, v in PAGES.items() if not sys.argv[1:] or k in sys.argv[1:]}
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
            for name, alvo in pages.items():
                rel, acao = alvo if isinstance(alvo, tuple) else (alvo, None)
                page.goto((ROOT / rel).as_uri(), wait_until="networkidle")
                if acao == "LIBERA":
                    page.evaluate(LIBERA)
                    page.reload(wait_until="networkidle")
                elif acao:
                    page.evaluate(acao)
                # força o carregamento das imagens lazy antes do print de página inteira
                page.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager')")
                # passa do fallback de 1,5 s do reveal e do fade-in do vídeo do hero
                page.wait_for_timeout(2200)
                largura = page.evaluate("document.documentElement.scrollWidth")
                if largura > vp["width"]:
                    print(f"ATENÇÃO {name} {vp_name}: rolagem horizontal ({largura}px > {vp['width']}px)")
                destino = OUT / f"{name}-{vp_name}.png"
                page.screenshot(path=str(destino), full_page=True)
                print(destino.relative_to(ROOT))
                # a próxima página começa sem cadastro (materiais bloqueados)
                page.evaluate("localStorage.removeItem('livia_mat_ok')")
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
