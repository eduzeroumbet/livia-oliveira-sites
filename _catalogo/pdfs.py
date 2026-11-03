"""Gera os PDFs estáticos dos 6 materiais em materiais/pdf/<slug>.pdf (o "Salvar em PDF" no celular e no navegador
do Instagram/Facebook abre esses arquivos, porque lá o window.print() não funciona).

Cada material abre liberado (localStorage livia_mat_ok=1) num http.server local e sai pela mesma folha de impressão
do site (@media print de materiais/style.css), em A4. Pixel, GA4, GTM, Clarity e a Lambda de cadastro são
bloqueados: gerar os PDFs não conta visita nem cadastro. Depois confere o texto de cada PDF (se o pymupdf estiver
instalado): linha da Lívia com o CRP, curso e WhatsApp da Lia no fim, e sem o aviso de material bloqueado.

Rode de novo sempre que o texto de um material mudar e commite os PDFs junto.
Uso: /Users/educloud/orquestra/.venv/bin/python _catalogo/pdfs.py [slug ...]   (sem slug, os 6)
Requer: playwright + chromium (python -m playwright install chromium); pymupdf para a conferência.
"""
import functools
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "materiais" / "pdf"
SLUGS = ["mensagens", "faltas", "etica", "reajuste", "posts", "indicacoes"]
LIBERA = "localStorage.setItem('livia_mat_ok', '1')"
BLOQUEIA = ("facebook", "google-analytics", "googletagmanager", "clarity", "lambda-url", "execute-api")
DEVE_TER = ("CRP 07/18713", "liviaoliveira.me/curso/b/", "(11) 91060-7651")
NAO_PODE = ("Este é só o começo",)


class Silencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def bloqueia(route):
    if any(b in route.request.url for b in BLOQUEIA):
        route.abort()
    else:
        route.continue_()


def confere(destino):
    try:
        import fitz
    except ImportError:
        print("  (pymupdf não instalado: texto do PDF não conferido)")
        return True
    with fitz.open(destino) as doc:
        texto = " ".join(" ".join(p.get_text().split()) for p in doc)
    faltando = [t for t in DEVE_TER if t not in texto]
    sobrando = [t for t in NAO_PODE if t in texto]
    for t in faltando:
        print(f"  ERRO: sem \"{t}\"")
    for t in sobrando:
        print(f"  ERRO: contém \"{t}\"")
    return not faltando and not sobrando


def enxuga(destino):
    """O avatar da assinatura (480x480) vai inteiro para o PDF e passa de 400 KB; reduz para 150 dpi em JPEG."""
    try:
        import fitz
    except ImportError:
        return
    doc = fitz.open(destino)
    doc.rewrite_images(dpi_threshold=160, dpi_target=150, quality=82)
    doc.save(str(destino) + ".tmp", garbage=4, deflate=True)
    doc.close()
    Path(str(destino) + ".tmp").replace(destino)


def main():
    slugs = [s for s in SLUGS if not sys.argv[1:] or s in sys.argv[1:]]
    OUT.mkdir(parents=True, exist_ok=True)
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencioso, directory=str(ROOT)))
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_address[1]}"
    certo = True
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            ctx = browser.new_context()
            ctx.add_init_script(LIBERA)
            ctx.route("**/*", bloqueia)
            page = ctx.new_page()
            for slug in slugs:
                page.goto(f"{base}/materiais/{slug}/", wait_until="networkidle")
                # avatar da assinatura é lazy: carrega antes de imprimir
                page.evaluate("document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager')")
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(800)
                destino = OUT / f"{slug}.pdf"
                # page.pdf já usa a mídia de impressão (@media print); não emular "screen" aqui
                page.pdf(path=str(destino), format="A4", prefer_css_page_size=True, print_background=False)
                enxuga(destino)
                kb = destino.stat().st_size / 1024
                print(f"{destino.relative_to(ROOT)}  {kb:.0f} KB" + ("  (ATENÇÃO: passou de 1 MB)" if kb > 1024 else ""))
                certo = confere(destino) and certo
            browser.close()
    finally:
        servidor.shutdown()
    if not certo:
        sys.exit(1)


if __name__ == "__main__":
    main()
