"""Testa no Chromium headless a calculadora do valor da sessão (calculadora/index.html).

Os scripts do Pixel e do GA4 são bloqueados (nada é enviado de verdade): os comandos ficam na fila do fbq e no
dataLayer, e é isso que o teste confere. Em 390px e 1440px, com e sem UTMs na URL:
- sem rolagem horizontal; sem travessão no texto;
- conta com os valores padrão (R$ 33 por sessão, mínimo R$ 40, ideal R$ 145) e com "Quanto você cobra hoje?";
- erros amigáveis com 0 sessões por semana e imposto de 100%;
- Lead (Pixel) e generate_lead (GA4) com content_name calculadora_sessao e content_category calc, uma vez só
  mesmo calculando de novo; nenhum InitiateCheckout / begin_checkout;
- "Conhecer o curso" leva para curso/b/ com os utm_*; o clique dispara ViewContent / view_offer com
  content_name calculadora_para_curso.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/calculadora.py
Requer: playwright + chromium (python -m playwright install chromium).
"""
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = (ROOT / "calculadora" / "index.html").as_uri()
UTMS = "utm_source=meta&utm_medium=paid&utm_campaign=ccs_calc&utm_content=V01&fbclid=abc123"
falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


ESTADO = """() => ({
  fbq: window.fbq ? window.fbq.queue.map(a => Array.from(a)) : [],
  dl: (window.dataLayer || []).map(x => (x && typeof x.length === "number" && !Array.isArray(x)) ? Array.from(x) : x),
})"""


def eventos_fbq(estado, nome):
    return [c for c in estado["fbq"] if c[:2] == ["track", nome]]


def eventos_gtag(estado, nome):
    return [c for c in estado["dl"] if isinstance(c, list) and c[:2] == ["event", nome]]


def saida(page, nome):
    return page.inner_text(f'[data-out="{nome}"]').strip()


with sync_playwright() as p:
    b = p.chromium.launch()
    for vp in ({"width": 390, "height": 844}, {"width": 1440, "height": 900}):
        for com_utm in (True, False):
            page = b.new_page(viewport=vp)
            page.route("**/*", lambda r: r.continue_() if r.request.url.startswith("file:") else r.abort())
            erros_js = []
            page.on("pageerror", lambda e: erros_js.append(str(e)))
            page.goto(URL + ("?" + UTMS if com_utm else ""), wait_until="load")
            print(f"--- calculadora {vp['width']}px, {'com' if com_utm else 'sem'} UTM")

            ok("—" not in page.inner_text("body"), "sem travessão no texto")
            ok(page.is_hidden("#resultado"), "resultado escondido antes da conta")
            for campo in ("aluguel", "imposto", "sessoes", "atual"):
                ok(page.get_attribute(f"#{campo}", "inputmode") == "decimal", f"#{campo} com inputmode=decimal")

            # erros: 0 sessões e imposto de 100%
            page.fill("#sessoes", "0")
            page.click("button[type=submit]")
            ok(page.is_hidden("#resultado") and page.inner_text('[data-error-for="sessoes"]') != "", "erro com 0 sessões por semana")
            page.fill("#sessoes", "20")
            page.fill("#imposto", "100")
            page.click("button[type=submit]")
            ok(page.is_hidden("#resultado") and "menor que 100%" in page.inner_text('[data-error-for="imposto"]'), "erro com imposto de 100%")
            page.fill("#imposto", "15")

            # valores padrão: 20 x 46 / 12 x 0,9 = 69 sessões; custos 2.250
            page.click("button[type=submit]")
            page.wait_for_timeout(900)
            ok(page.is_visible("#resultado"), "resultado aparece")
            ok(saida(page, "custo") == "R$ 33", f"custo por sessão R$ 33 ({saida(page, 'custo')})")
            ok(saida(page, "minimo") == "R$ 40", f"mínimo R$ 40 ({saida(page, 'minimo')})")
            ok(saida(page, "ideal") == "R$ 145", f"ideal R$ 145 ({saida(page, 'ideal')})")
            ok(page.evaluate("document.getElementById('resultado').getBoundingClientRect().top") < 200, "rolou até o resultado")

            page.fill("#atual", "120")
            texto = saida(page, "atual")
            ok("R$ 4.788" in texto and "Faltam R$ 1.212" in texto, f"valor atual de R$ 120 ({texto})")

            page.click("button[type=submit]")  # segunda conta: não repete o Lead
            estado = page.evaluate(ESTADO)
            lead = {"content_name": "calculadora_sessao", "content_category": "calc"}
            ok(eventos_fbq(estado, "Lead") == [["track", "Lead", lead]], "Lead no Pixel, uma vez")
            ok(eventos_gtag(estado, "generate_lead") == [["event", "generate_lead", lead]], "generate_lead no GA4, uma vez")

            href = page.get_attribute("#conhecer-curso", "href")
            partes = urlsplit(href)
            q = parse_qs(partes.query)
            ok(partes.path.endswith("/curso/b/") or partes.path.endswith("/curso/b/index.html"), f"Conhecer o curso vai para curso/b/ ({href})")
            if com_utm:
                ok(q.get("utm_source") == ["meta"] and q.get("utm_campaign") == ["ccs_calc"] and q.get("utm_content") == ["V01"]
                   and all(len(v) == 1 for v in q.values()), "utm_* preservados no link do curso, sem duplicar")
            else:
                ok(not partes.query, "sem UTM, link do curso sem query")

            page.evaluate("document.addEventListener('click', e => e.preventDefault())")
            page.click("#conhecer-curso")
            estado = page.evaluate(ESTADO)
            oferta = {"content_name": "calculadora_para_curso"}
            ok(eventos_fbq(estado, "ViewContent") == [["track", "ViewContent", oferta]], "ViewContent no clique do curso")
            ok(eventos_gtag(estado, "view_offer") == [["event", "view_offer", oferta]], "view_offer no GA4")
            ok(not eventos_fbq(estado, "InitiateCheckout") and not eventos_gtag(estado, "begin_checkout"), "sem InitiateCheckout")

            larg = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
            ok(larg[0] <= larg[1], f"sem rolagem horizontal ({larg[0]} <= {larg[1]})")
            ok(not erros_js, f"sem erros de JS {erros_js}")
            page.close()
    b.close()

print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
