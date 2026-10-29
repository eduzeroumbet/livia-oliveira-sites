"""Testa no Chromium headless o rastreamento das 3 versões da página do curso (A=curso/, B=curso/b/, C=curso/versao-b/).

Os scripts do Pixel e do GA4 são bloqueados (nada é enviado de verdade): os comandos ficam na fila do fbq e no
dataLayer, e é isso que o teste confere. Para cada página, com e sem UTMs na URL:
- Pixel 1197036460960933 iniciado com PageView e GA4 G-XH74VZSNZ2 configurado;
- nenhum link para pay.hotmart.com; os botões de compra (a.checkout) vão para a pré-página curso/inscricao/ com
  pg=pgA/pgB/pgC e a query da visita (UTMs e fbclid, sem duplicar); sem UTM, só pg;
- clique no botão de compra: CliqueComprar (Pixel, trackCustom) e clique_comprar (GA4) com content_category, e nenhum
  InitiateCheckout / begin_checkout (esse sai só no envio da pré-página, ver tests/inscricao.py);
- seção #oferta na tela: ViewContent e view_offer uma vez só.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/rastreamento_curso.py
Requer: playwright + chromium (python -m playwright install chromium).
"""
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeout, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PAGINAS = {"pgA": "curso/index.html", "pgB": "curso/b/index.html", "pgC": "curso/versao-b/index.html"}
PIXEL_ID = "1197036460960933"
GA4_ID = "G-XH74VZSNZ2"
UTMS = "utm_source=meta&utm_medium=paid&utm_campaign=ccs_frio_criativos&utm_content=V01&fbclid=abc123"
falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


# fila do fbq e dataLayer (os itens do gtag são objetos arguments; viram listas)
ESTADO = """() => ({
  fbq: window.fbq ? window.fbq.queue.map(a => Array.from(a)) : [],
  dl: (window.dataLayer || []).map(x => (x && typeof x.length === "number" && !Array.isArray(x)) ? Array.from(x) : x),
})"""
ROLAR_ATE = "el => window.scrollTo({top: el.getBoundingClientRect().top + window.scrollY, behavior: 'instant'})"
VIU_OFERTA = "() => window.fbq && window.fbq.queue.some(a => a[0] === 'track' && a[1] === 'ViewContent')"


def eventos_fbq(estado, nome, tipo="track"):
    return [c for c in estado["fbq"] if c[:2] == [tipo, nome]]


def eventos_gtag(estado, nome):
    return [c for c in estado["dl"] if isinstance(c, list) and c[:2] == ["event", nome]]


with sync_playwright() as p:
    b = p.chromium.launch()
    for pagina, rel in PAGINAS.items():
        for com_utm in (True, False):
            url = (ROOT / rel).as_uri() + ("?" + UTMS if com_utm else "")
            page = b.new_page(viewport={"width": 1440, "height": 900})
            externas = []

            def rota(route):
                if route.request.url.startswith("file:"):
                    route.continue_()
                else:
                    externas.append(route.request.url)
                    route.abort()

            page.route("**/*", rota)
            erros_js = []
            page.on("pageerror", lambda e: erros_js.append(str(e)))
            page.goto(url, wait_until="load")
            print(f"--- {rel} ({pagina}, {'com' if com_utm else 'sem'} UTM)")

            estado = page.evaluate(ESTADO)
            ok(["init", PIXEL_ID] in estado["fbq"], f"Pixel {PIXEL_ID} iniciado")
            ok(len(eventos_fbq(estado, "PageView")) == 1, "PageView no Pixel")
            ok(["config", GA4_ID] in estado["dl"], f"GA4 {GA4_ID} configurado")
            ok(any("connect.facebook.net/en_US/fbevents.js" in u for u in externas), "pede o fbevents.js")
            ok(any(f"googletagmanager.com/gtag/js?id={GA4_ID}" in u for u in externas), "pede o gtag.js")

            ok(page.eval_on_selector_all('a[href*="pay.hotmart.com"]', "els => els.length") == 0, "nenhum link para pay.hotmart.com")
            hrefs = page.eval_on_selector_all("a.checkout", "els => els.map(a => a.href)")
            ok(len(hrefs) > 0, f"{len(hrefs)} botões de compra (a.checkout)")
            # "Quero minha vaga" que só rola até a #oferta não é botão de compra
            textos = page.eval_on_selector_all("a", "els => els.filter(a => /Quero (minha vaga|me inscrever)/.test(a.textContent) && !a.getAttribute('href').startsWith('#')).map(a => a.classList.contains('checkout'))")
            ok(textos and all(textos), f"todos os {len(textos)} \"Quero minha vaga\"/\"Quero me inscrever\" com class=checkout")
            for h in hrefs:
                partes = urlsplit(h)
                q = parse_qs(partes.query)
                certo = partes.path.endswith("/curso/inscricao/") and q.get("pg") == [pagina] and all(len(v) == 1 for v in q.values())
                if com_utm:
                    certo = (certo and q.get("utm_source") == ["meta"] and q.get("utm_medium") == ["paid"]
                             and q.get("utm_campaign") == ["ccs_frio_criativos"] and q.get("utm_content") == ["V01"]
                             and q.get("fbclid") == ["abc123"])
                else:
                    certo = certo and set(q) == {"pg"}
                if not certo:
                    ok(False, f"botão de compra: {h}")
                    break
            else:
                ok(True, f"botões vão para curso/inscricao/ com pg={pagina}" + (" e as UTMs, sem duplicar" if com_utm else ""))

            # clique: o evento sai, a navegação é cancelada
            page.evaluate("document.addEventListener('click', e => e.preventDefault())")
            page.eval_on_selector("a.checkout", "a => a.click()")
            estado = page.evaluate(ESTADO)
            clique = {"content_category": pagina}
            ok(eventos_fbq(estado, "CliqueComprar", "trackCustom") == [["trackCustom", "CliqueComprar", clique]], "CliqueComprar no Pixel")
            ok(eventos_gtag(estado, "clique_comprar") == [["event", "clique_comprar", clique]], "clique_comprar no GA4")
            ok(not eventos_fbq(estado, "InitiateCheckout") and not eventos_gtag(estado, "begin_checkout"),
               "clique sem InitiateCheckout / begin_checkout")
            esperado = {"value": 860, "currency": "BRL", "content_name": "Carreira com Sentido", "content_category": pagina}

            # oferta na tela (duas vezes): um único ViewContent / view_offer.
            # Rolagem instantânea: as páginas usam scroll-behavior: smooth, e o scrollIntoView() animado era
            # interrompido pela volta ao topo antes de a oferta chegar na tela.
            for i in range(2):
                page.eval_on_selector("#oferta", ROLAR_ATE)
                if i == 0:
                    try:
                        page.wait_for_function(VIU_OFERTA, timeout=5000)
                    except PlaywrightTimeout:
                        pass  # a falha aparece na conferência abaixo
                page.wait_for_timeout(400)
                page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                page.wait_for_timeout(400)
            estado = page.evaluate(ESTADO)
            ok(eventos_fbq(estado, "ViewContent") == [["track", "ViewContent", esperado]], "ViewContent no Pixel, uma vez")
            ok(eventos_gtag(estado, "view_offer") == [["event", "view_offer", esperado]], "view_offer no GA4, uma vez")

            ok(not erros_js, f"sem erros de JS {erros_js}")
            page.close()
    b.close()

print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
