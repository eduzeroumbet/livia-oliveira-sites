"""Testa no Chromium headless a Black Friday 2026 (assets/js/bf.js, black-friday/, black/ e a faixa nas outras páginas),
com o site servido por http.server local.

A hora do aparelho é simulada com ?bf_agora=<ISO> (o bf.js só aceita em localhost/127.0.0.1), então o teste vale antes
e depois da campanha. Nada sai para a internet: Pixel, GA4 e fontes são bloqueados (os comandos ficam na fila do fbq e
no dataLayer); a Lambda de cadastro e a Hotmart são interceptadas.
- black-friday/ em 390px e 1366px: carrega sem rolagem horizontal, título, R$ 499,99, faixa do topo com a contagem;
- contagem regressiva certa (dias, horas, min, seg até 30/11 23h59min59s de Brasília) e andando;
- 3 ou mais botões de compra para curso/inscricao/?pg=pgBF com as UTMs da visita; CliqueComprar com pgBF;
  ViewContent com value 499.99 ao ver o bloco de preço; botão fixo do celular depois da primeira dobra;
- do botão à pré-página e dali ao link da Hotmart com off=qu4x7j2d e sck terminando em |pgBF;
- depois do prazo: "A Black Friday terminou", nenhum R$ 499,99 nem 41,67 na tela, botão para curso/b/; o prazo acabando
  com a página aberta troca tudo na hora;
- black/ redireciona para black-friday/ com a query;
- versões B (black-friday/b/) e C (black-friday/c/), e a A junto: BF.fim 2026-11-30T23:59:59-03:00, R$ 499,99 e 41,67,
  sem travessão, noindex só em B e C, botões com pg=pgBF&versao=bf_x, eventos com pagina_versao (bf_a, bf_b, bf_c),
  Hotmart com off=qu4x7j2d e sck terminando em |pgBF|bf_b ou |pgBF|bf_c (a A fica com |pgBF), e o "terminou" depois do prazo;
- nas 3 versões, só durante a Black Friday: chips do que o curso inclui junto do preço do hero, faixa de números do
  curso/b/ logo depois do hero e o vídeo de depoimento Trafego_17 (sem autoplay) na seção de alunas; depois do prazo
  nada disso aparece; o "terminou" (bf-terminou e bf-topo--fim) fica escondido por CSS mesmo sem JS; foto do "Prazer,
  sou Lívia Oliveira" (A e B) lazy, em 4/5 e com fundo neutro;
- faixa no curso (A, B, C), materiais, quiz, calculadora e home, com o link certo e sem cobrir o cabeçalho; preço de BF
  durante e o normal depois; terapia sem nada de Black Friday;
- fora de localhost (domínio liviaoliveira.me simulado) o ?bf_agora é ignorado.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/black_friday.py
Requer: playwright + chromium (python -m playwright install chromium).
"""
import functools
import json
import re
import sys
import threading
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
LAMBDA_HOST = "nwmxltflulqvcxu7bdplodmyjm0yweuc.lambda-url.sa-east-1.on.aws"
CORS = {"access-control-allow-origin": "*", "access-control-allow-methods": "POST, OPTIONS", "access-control-allow-headers": "content-type"}
FIM = datetime(2026, 12, 1, 2, 59, 59, tzinfo=timezone.utc)  # BF.fim = 2026-11-30T23:59:59-03:00
DURANTE_ISO = "2026-11-25T12:00:00-03:00"
DURANTE = "bf_agora=" + DURANTE_ISO
DEPOIS = "bf_agora=2026-12-01T03:00:01Z"
UTMS = "utm_source=ig&utm_medium=stories&utm_campaign=ccs_bf&utm_content=S01&fbclid=abc123"
LINHA_BF = "de R$ 860 por R$ 499,99 · 12x de R$ 41,67 sem juros (Black Friday até 30/11)"
LINHA = "12x de R$ 71,67 sem juros ou R$ 860 à vista"
# as 3 versões da página da Black Friday: caminho > (pagina_versao, sufixo do sck na Hotmart)
VERSOES = {"black-friday/": ("bf_a", "|pgBF"), "black-friday/b/": ("bf_b", "|pgBF|bf_b"), "black-friday/c/": ("bf_c", "|pgBF|bf_c")}
CHIPS = ["10 módulos", "60+ aulas", "12 meses de acesso", "Comunidade de alunas", "Certificado", "7 dias de garantia"]
NUMEROS = ["47 mil", "15+ anos", "100+"]
# páginas com a faixa e o destino do link (sem a query da visita)
FAIXA = {
    "curso/": "black-friday/", "curso/b/": "black-friday/", "curso/versao-b/": "black-friday/", "": "black-friday/",
    "materiais/": "black-friday/?utm_source=site&utm_medium=materiais&utm_campaign=ccs_bf",
    "materiais/mensagens/": "black-friday/?utm_source=site&utm_medium=materiais_mensagens&utm_campaign=ccs_bf",
    "materiais/faltas/": "black-friday/?utm_source=site&utm_medium=materiais_faltas&utm_campaign=ccs_bf",
    "quiz/": "black-friday/?utm_source=site&utm_medium=quiz&utm_campaign=ccs_bf",
    "calculadora/": "black-friday/?utm_source=site&utm_medium=calculadora&utm_campaign=ccs_bf",
}
falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


class Silencioso(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


servidor = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Silencioso, directory=str(ROOT)))
threading.Thread(target=servidor.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{servidor.server_address[1]}"

ESTADO = """() => ({
  fbq: window.fbq ? window.fbq.queue.map(a => Array.from(a)) : [],
  dl: (window.dataLayer || []).map(x => (x && typeof x.length === "number" && !Array.isArray(x)) ? Array.from(x) : x),
})"""
ROLAR_ATE = "el => window.scrollTo({top: el.getBoundingClientRect().top + window.scrollY, behavior: 'instant'})"
SEM_ROLAGEM = "() => [document.documentElement.scrollWidth, window.innerWidth]"
# registra no Python cada chamada do fbq e do dataLayer (a pré-página sai para a Hotmart logo depois do envio)
ESPIAO = """() => {
  const fbq = window.fbq;
  window.fbq = function () { window.registra("fbq", Array.from(arguments)); return fbq.apply(this, arguments); };
  Object.assign(window.fbq, fbq);
  const push = window.dataLayer.push.bind(window.dataLayer);
  window.dataLayer.push = function (x) {
    window.registra("dl", (x && typeof x.length === "number" && !Array.isArray(x)) ? Array.from(x) : x);
    return push(x);
  };
}"""


def abre(b, caminho, query="", vp=None, dominio=False):
    """Abre a página com as rotas: site local, Lambda e Hotmart interceptadas; o resto é bloqueado."""
    page = b.new_page(viewport=vp or {"width": 390, "height": 844})
    ctx = {"lambda": [], "hotmart": [], "fbq": [], "dl": [], "erros_js": []}

    def rota(route):
        req = route.request
        partes = urlsplit(req.url)
        if req.url.startswith(BASE):
            route.continue_()
        elif partes.hostname == "liviaoliveira.me" and dominio:
            # domínio de produção simulado com os arquivos locais
            local = ROOT / partes.path.lstrip("/")
            if partes.path.endswith("/"):
                local = local / "index.html"
            if local.is_file():
                tipo = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}.get(local.suffix, "application/octet-stream")
                route.fulfill(status=200, body=local.read_bytes(), content_type=tipo)
            else:
                route.fulfill(status=404, body="")
        elif partes.hostname == LAMBDA_HOST:
            if req.method == "OPTIONS":
                route.fulfill(status=204, headers=CORS)
                return
            ctx["lambda"].append(req)
            route.fulfill(status=200, headers=CORS, content_type="application/json", body=json.dumps({"ok": True}))
        elif partes.hostname == "pay.hotmart.com":
            ctx["hotmart"].append(req.url)
            route.fulfill(status=200, content_type="text/html", body="<!doctype html><title>Hotmart (teste)</title>")
        else:
            route.abort()

    page.route("**/*", rota)
    page.expose_function("registra", lambda tipo, item: ctx[tipo].append(item))
    page.on("pageerror", lambda e: ctx["erros_js"].append(str(e)))
    base = "https://liviaoliveira.me" if dominio else BASE
    page.goto(f"{base}/{caminho}" + ("?" + query if query else ""), wait_until="load")
    return page, ctx


def visivel(page, seletor):
    return page.eval_on_selector_all(seletor, "els => els.filter(e => e.offsetParent !== null || getComputedStyle(e).position === 'fixed' && getComputedStyle(e).display !== 'none').length")


def contagem(page):
    return page.evaluate("""() => ['dias', 'horas', 'min', 'seg'].map(k => Number(document.querySelector('[data-bf-' + k + ']').textContent))""")


with sync_playwright() as p:
    b = p.chromium.launch(args=[f"--host-resolver-rules=MAP {LAMBDA_HOST} ~NOTFOUND"])

    # ---------- página black-friday/ durante a campanha ----------
    for vp in ({"width": 390, "height": 844}, {"width": 1366, "height": 768}):
        print(f"--- black-friday/ {vp['width']}px, durante")
        page, ctx = abre(b, "black-friday/", UTMS + "&" + DURANTE, vp)
        largura = page.evaluate(SEM_ROLAGEM)
        ok(largura[0] <= largura[1], f"sem rolagem horizontal ({largura[0]} <= {largura[1]})")
        ok(page.title() == "Black Friday Carreira com Sentido: de R$ 860 por R$ 499,99", f"título ({page.title()})")
        texto = page.inner_text("body")
        ok("BLACK FRIDAY CARREIRA COM SENTIDO" in texto.upper(), "selo \"Black Friday Carreira com Sentido\"")
        for trecho in ("De R$ 860 por", "R$ 499,99", "12x de R$ 41,67", "Você economiza R$ 360,01",
                       "7 dias de garantia · acesso imediato · Pix, cartão ou boleto", "Aluna do Carreira com Sentido", "CRP 07/18713",
                       "Até quando vale?", "Já baixei os materiais gratuitos, o curso é diferente?"):
            ok(trecho in texto, f"mostra \"{trecho}\"")
        ok("—" not in texto, "sem travessão no texto")
        ok("terminou" not in texto.lower(), "não mostra \"terminou\"")
        topo = page.locator(".bf-topo").first
        caixa = topo.bounding_box()
        ok(topo.is_visible() and "BLACK FRIDAY · TERMINA EM" in topo.inner_text().upper() and caixa["y"] == 0, "faixa do topo com \"Black Friday · termina em\"")
        page.evaluate("window.scrollTo({top: 1500, behavior: 'instant'})")
        page.wait_for_timeout(100)
        ok(abs(topo.bounding_box()["y"]) < 1, "faixa do topo continua fixa ao rolar")
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")

        # contagem: de 25/11 12h até 30/11 23h59min59s = 5 dias, 11 h, 59 min, ~59 s
        d, h, m, s = contagem(page)
        ok((d, h, m) == (5, 11, 59) and s >= 55, f"contagem regressiva certa ({d}d {h}h {m}min {s}s)")
        page.wait_for_timeout(1300)
        ok(contagem(page)[3] != s, "contagem andando a cada segundo")

        # botões de compra
        hrefs = page.eval_on_selector_all("a.checkout", "els => els.map(a => a.href)")
        bons = []
        for h_ in hrefs:
            q = parse_qs(urlsplit(h_).query)
            if (urlsplit(h_).path == "/curso/inscricao/" and q.get("pg") == ["pgBF"] and q.get("versao") == ["bf_a"] and q.get("utm_source") == ["ig"]
                    and q.get("utm_campaign") == ["ccs_bf"] and q.get("utm_content") == ["S01"] and q.get("fbclid") == ["abc123"]):
                bons.append(h_)
        ok(len(bons) >= 3 and len(bons) == len(hrefs), f"{len(bons)} de {len(hrefs)} botões vão para curso/inscricao/?pg=pgBF com as UTMs")
        textos = page.eval_on_selector_all("main a.checkout", "els => els.map(a => a.textContent.trim())")
        ok(textos.count("Quero garantir o preço de Black Friday") >= 3, "botão \"Quero garantir o preço de Black Friday\" 3 vezes ao longo da página")
        wa = page.eval_on_selector_all('a[href*="wa.me/"]', "els => els.map(a => a.href)")
        ok(wa and all(u.startswith("https://wa.me/5511910607651?text=Oi!%20Tenho%20uma%20d%C3%BAvida%20sobre%20a%20Black%20Friday") for u in wa),
           "WhatsApp da Lia com a mensagem da Black Friday")
        ok(page.get_by_text("Falar com a equipe no WhatsApp").is_visible(), "link \"Falar com a equipe no WhatsApp\"")

        # ViewContent ao ver o bloco de preço (uma vez), value 499.99
        if vp["width"] == 390:
            ok(not page.eval_on_selector(".sticky-bar", "e => e.classList.contains('on')"), "botão fixo escondido na primeira dobra")
        page.eval_on_selector("#programa", ROLAR_ATE)
        page.wait_for_timeout(500)
        if vp["width"] == 390:
            ok(page.eval_on_selector(".sticky-bar", "e => e.classList.contains('on')"), "botão fixo do celular depois da primeira dobra")
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        page.wait_for_timeout(300)
        page.eval_on_selector("#oferta", "el => window.scrollTo({top: el.getBoundingClientRect().top + window.scrollY - 100, behavior: 'instant'})")
        page.wait_for_timeout(500)
        estado = page.evaluate(ESTADO)
        vc = [c for c in estado["fbq"] if c[:2] == ["track", "ViewContent"]]
        esperado = {"value": 499.99, "currency": "BRL", "content_name": "Carreira com Sentido", "content_category": "pgBF", "pagina_versao": "bf_a"}
        ok(vc == [["track", "ViewContent", esperado]], f"ViewContent com value 499.99, pgBF e bf_a ({vc})")
        ok(["event", "view_offer", esperado] in estado["dl"], "view_offer no GA4")
        # clique: CliqueComprar com pgBF e bf_a (navegação cancelada)
        page.evaluate("document.addEventListener('click', e => e.preventDefault())")
        page.eval_on_selector("a.checkout", "a => a.click()")
        estado = page.evaluate(ESTADO)
        clique = {"content_category": "pgBF", "pagina_versao": "bf_a"}
        ok(["trackCustom", "CliqueComprar", clique] in estado["fbq"], "CliqueComprar com content_category pgBF e pagina_versao bf_a")
        ok(["event", "clique_comprar", clique] in estado["dl"], "clique_comprar no GA4")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()

    # ---------- do botão à pré-página e à Hotmart ----------
    print("--- black-friday/ botão > pré-página > Hotmart")
    page, ctx = abre(b, "black-friday/", UTMS + "&" + DURANTE)
    page.click("#oferta a.checkout")
    page.wait_for_url(lambda u: "/curso/inscricao/" in u, timeout=5000)
    q = parse_qs(urlsplit(page.url).query)
    ok(q.get("pg") == ["pgBF"] and q.get("utm_source") == ["ig"], f"chega na pré-página com pg=pgBF e as UTMs ({page.url})")
    ok(page.locator(".insc-bf").is_visible(), "pré-página mostra o preço de Black Friday")
    page.click('label.insc-forma:has(input[value="pix"])')
    page.fill("#nome", "Maria Teste")
    page.fill("#email", "maria.teste@exemplo.com")
    page.fill("#whatsapp", "(51) 99999-8888")
    page.evaluate(ESPIAO)
    with page.expect_request(lambda r: "pay.hotmart.com" in r.url, timeout=5000):
        page.click("button[type=submit]")
    page.wait_for_timeout(200)
    hq = parse_qs(urlsplit(ctx["hotmart"][0]).query) if ctx["hotmart"] else {}
    ok(hq.get("off") == ["qu4x7j2d"], f"link da Hotmart com off=qu4x7j2d ({hq.get('off')})")
    ok((hq.get("sck") or [""])[0].endswith("|pgBF") and hq.get("sck") == ["ig|stories|ccs_bf|S01|pgBF"], f"sck terminando em |pgBF ({hq.get('sck')})")
    ok(hq.get("fbclid") == ["abc123"] and "bf_agora" not in hq, "fbclid vai, bf_agora não vai")
    ok(["track", "InitiateCheckout", {"value": 499.99, "currency": "BRL", "content_name": "Carreira com Sentido", "content_category": "pgBF",
                                      "pagina_versao": "bf_a", "payment_type": "pix"}] in ctx["fbq"],
       "InitiateCheckout com value 499.99 e pagina_versao bf_a")
    page.close()

    # ---------- as 3 versões: o que vale para todas ----------
    for caminho, (versao, sufixo) in VERSOES.items():
        print(f"--- {caminho} ({versao}): oferta, prazo e origem")
        page, ctx = abre(b, caminho, DURANTE)
        cfg = page.evaluate("[window.BF.fim, window.BF.oferta, window.BF.preco, window.BF.parcela, window.BF.de]")
        ok(cfg == ["2026-11-30T23:59:59-03:00", "qu4x7j2d", "499,99", "41,67", "860"], f"BF.fim 2026-11-30T23:59 -03:00, oferta e preço ({cfg})")
        html = page.content()
        texto = page.inner_text("body")
        ok("R$ 499,99" in texto and "41,67" in texto and "R$ 360,01" in texto and "R$ 860" in texto, "R$ 860, R$ 499,99, 12x de R$ 41,67 e economia de R$ 360,01")
        ok("—" not in html, "sem travessão (—) no HTML")
        ok("menor preço" not in html.lower(), "sem \"menor preço\"")
        robots = page.eval_on_selector_all('meta[name="robots"]', "els => els.map(e => e.content)")
        if versao == "bf_a":
            ok(robots == [], f"A indexável, sem noindex ({robots})")
        else:
            ok(robots == ["noindex"], f"noindex ({robots})")

        # chips no hero, junto do card de preço
        chips = page.eval_on_selector_all(".hero .chips li", "els => els.filter(e => e.offsetParent !== null).map(e => e.textContent.trim())")
        ok(chips == CHIPS, f"chips no hero ({chips})")
        perto = page.evaluate("""() => { const c = document.querySelector('.hero .chips').getBoundingClientRect(), p = document.querySelector('.hero .bf-preco').getBoundingClientRect();
          return Math.min(Math.abs(p.top - c.bottom), Math.abs(c.top - p.bottom)); }""")
        ok(perto <= 30, f"chips logo acima ou logo abaixo do card de preço ({perto:.0f}px)")
        # WhatsApp discreto logo abaixo do "7 dias de garantia · acesso imediato · ..." do card de preço do hero
        wa_card = page.evaluate("""() => { const t = [...document.querySelectorAll('.hero .bf-preco .trust')].find(p => p.textContent.startsWith('7 dias de garantia'));
          const p = t && t.nextElementSibling, a = p && p.querySelector('a');
          return a ? [a.textContent.trim(), a.href.startsWith('https://wa.me/5511910607651?text=Oi!%20Tenho%20uma%20d%C3%BAvida%20sobre%20a%20Black%20Friday'), a.offsetParent !== null] : null; }""")
        ok(wa_card == ["Ficou com dúvida? Fale com a equipe no WhatsApp", True, True], f"link do WhatsApp logo abaixo do trust do card ({wa_card})")
        # FAQ ampliado, com as respostas do curso/b/ e o boleto do dia 30/11
        perguntas = page.eval_on_selector_all("#faq summary", "els => els.map(e => e.textContent.trim())")
        ok(all(q_ in perguntas for q_ in ("Sou recém-formada. Esse curso serve pra mim?", "O conteúdo respeita o Código de Ética e as orientações do CFP?",
                                         "Não tenho tempo. Quanto preciso me dedicar por semana?", "Funciona mesmo que eu não tenha muitos seguidores?",
                                         "Gerei o boleto no dia 30/11. Ainda vale o preço?")), f"FAQ ampliado ({perguntas})")
        # faixa de números logo depois do hero
        barra = page.locator(".proofbar")
        numeros = [" ".join(t.split()) for t in barra.locator("b").all_inner_texts()] if barra.count() == 1 else []
        ok(barra.count() == 1 and barra.is_visible() and numeros == NUMEROS, f"faixa de números visível ({numeros})")
        ok("psicólogas acompanham a Lívia no Instagram" in texto and "alunas no Carreira com Sentido" in texto, "textos da faixa de números")
        ok(page.evaluate("document.querySelector('.proofbar').previousElementSibling.matches('section.hero')"), "faixa de números logo depois do hero")
        caixas = page.eval_on_selector_all(".proofbar li", "els => els.map(e => e.getBoundingClientRect().right)")
        ok(all(r <= 390 for r in caixas), f"faixa de números cabe em 390px ({caixas})")
        # vídeo de depoimento na seção de alunas, sem autoplay e com tamanho reservado
        video = page.eval_on_selector_all("#alunas video", """els => els.map(v => ({poster: v.getAttribute('poster'), src: v.querySelector('source').getAttribute('src'),
          controls: v.controls, playsinline: v.hasAttribute('playsinline'), preload: v.getAttribute('preload'), autoplay: v.hasAttribute('autoplay'),
          w: v.getAttribute('width'), h: v.getAttribute('height'), visivel: v.offsetParent !== null}))""")
        v = video[0] if len(video) == 1 else {}
        ok(len(video) == 1 and v["poster"].endswith("assets/video/Trafego_17-poster.jpg") and v["src"].endswith("assets/video/Trafego_17.mp4"),
           f"vídeo Trafego_17 com o poster na seção de alunas ({video})")
        ok(v.get("controls") and v.get("playsinline") and v.get("preload") == "none" and not v.get("autoplay") and (v.get("w"), v.get("h")) == ("360", "640") and v.get("visivel"),
           "vídeo com controls, playsinline, preload=none, sem autoplay, width/height e visível")
        ok("Mensagens das alunas, lidas pela Lívia" in page.inner_text("#alunas"), "legenda do vídeo")
        # "Prazer, sou Lívia Oliveira": foto lazy, espaço reservado em 4/5 e fundo neutro enquanto carrega
        if page.locator(".bf-sobre img").count():
            foto = page.eval_on_selector(".bf-sobre img", """i => { const c = getComputedStyle(i); const r = i.getBoundingClientRect();
              return [i.loading, c.aspectRatio, c.backgroundImage !== 'none', Math.abs(r.width / r.height - 0.8) < 0.01]; }""")
            ok(foto[0] == "lazy" and foto[1].replace(" ", "") == "4/5" and foto[2] and foto[3], f"foto do \"Prazer\" lazy, 4/5 e com fundo ({foto})")
        page.close()

        # depois do prazo: nada disso aparece
        page, ctx = abre(b, caminho, DEPOIS)
        vis = {sel: visivel(page, sel) for sel in (".hero .chips", ".proofbar", "#alunas video")}
        ok(not any(vis.values()), f"depois do prazo: sem chips, faixa de números e vídeo ({vis})")
        page.close()

        # o "terminou" começa escondido por CSS, antes de qualquer JS (e fora da árvore de acessibilidade)
        ctx_sem_js = b.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        page = ctx_sem_js.new_page()
        page.route("**/*", lambda r: r.continue_() if r.request.url.startswith(BASE) else r.abort())
        page.goto(f"{BASE}/{caminho}", wait_until="load")
        disp = page.eval_on_selector_all("section.bf-terminou, .bf-topo--fim", "els => els.map(e => getComputedStyle(e).display)")
        ok(disp == ["none", "none"], f"sem JS: bf-terminou e bf-topo--fim com display:none ({disp})")
        ok("terminou" not in page.inner_text("body").lower(), "sem JS: \"terminou\" fora do texto lido")
        ctx_sem_js.close()

    for caminho in ("black-friday/b/", "black-friday/c/"):
        versao, sufixo = VERSOES[caminho]
        for vp in ({"width": 390, "height": 844}, {"width": 1366, "height": 768}):
            print(f"--- {caminho} {vp['width']}px, durante")
            page, ctx = abre(b, caminho, UTMS + "&" + DURANTE, vp)
            largura = page.evaluate(SEM_ROLAGEM)
            ok(largura[0] <= largura[1], f"sem rolagem horizontal ({largura[0]} <= {largura[1]})")
            titulo = page.title()
            ok(titulo and titulo != "Black Friday Carreira com Sentido: de R$ 860 por R$ 499,99" and "499,99" in titulo, f"título próprio ({titulo})")
            texto = page.inner_text("body")
            ok("terminou" not in texto.lower(), "não mostra \"terminou\"")
            topo = page.locator(".bf-topo").first
            ok(topo.is_visible() and "BLACK FRIDAY · TERMINA EM" in topo.inner_text().upper() and topo.bounding_box()["y"] == 0,
               "faixa do topo igual à da A")
            d, h, m, s = contagem(page)
            ok((d, h, m) == (5, 11, 59) and s >= 55, f"contagem regressiva certa ({d}d {h}h {m}min {s}s)")
            hrefs = page.eval_on_selector_all("a.checkout", "els => els.map(a => a.href)")
            bons = [h_ for h_ in hrefs if urlsplit(h_).path == "/curso/inscricao/" and parse_qs(urlsplit(h_).query).get("pg") == ["pgBF"]
                    and parse_qs(urlsplit(h_).query).get("versao") == [versao] and parse_qs(urlsplit(h_).query).get("utm_source") == ["ig"]
                    and parse_qs(urlsplit(h_).query).get("fbclid") == ["abc123"]]
            ok(len(bons) >= 3 and len(bons) == len(hrefs), f"{len(bons)} de {len(hrefs)} botões vão para curso/inscricao/?pg=pgBF&versao={versao} com as UTMs")
            wa = page.eval_on_selector_all('a[href*="wa.me/"]', "els => els.map(a => a.href)")
            ok(wa and all(u.startswith("https://wa.me/5511910607651?text=Oi!%20Tenho%20uma%20d%C3%BAvida%20sobre%20a%20Black%20Friday") for u in wa),
               "WhatsApp da Lia com a mensagem da Black Friday")
            if caminho == "black-friday/b/":
                ok(page.locator("h1").inner_text().startswith("Quanto a sua sessão precisa custar para a clínica"), "topo com a pergunta da conta da clínica")
                ok(page.locator(".hero #oferta a.checkout").is_visible(), "oferta com botão logo abaixo da pergunta")
                ok(page.locator(".bf-dor").count() == 3 and all(t in texto for t in ("Módulo 02", "Módulo 03")), "3 dores ligadas aos módulos")
                ok(page.locator(".bf-preco-sec .bf-contagem").is_visible(), "bloco de preço com contagem regressiva")
            else:
                cta = page.get_by_role("link", name="Garantir por R$ 499,99").first
                caixa = cta.bounding_box()
                ok(cta.is_visible() and caixa["y"] + caixa["height"] <= vp["height"], f"botão \"Garantir por R$ 499,99\" na primeira dobra ({caixa})")
                ok(page.locator(".bf-contagem").count() == 0, "sem a caixa grande de contagem (a contagem fica na faixa do topo)")
                selo = page.locator(".hero .bf-selo")
                ok(selo.is_visible() and selo.inner_text().upper() == "ATÉ 30/11 ÀS 23H59", "pílula \"Até 30/11 às 23h59\" no hero")
                ok(page.locator(".bf-c-aprende h2").inner_text() == "O que você vai aprender." and page.locator(".bf-c-aprende .mod").count() == 5,
                   "\"O que você vai aprender.\" com 5 módulos")
                ok(page.locator("#faq details").count() == 9 and "Quanto custa e posso parcelar?" not in texto, "9 perguntas no FAQ, sem \"Quanto custa e posso parcelar?\"")
                ok(page.get_by_role("link", name="Tenho uma dúvida").first.is_visible(), "botão \"Tenho uma dúvida\" para a Lia")
            if vp["width"] == 390:
                ok(not page.eval_on_selector(".sticky-bar", "e => e.classList.contains('on')"), "botão fixo escondido na primeira dobra")
                page.eval_on_selector("#alunas", ROLAR_ATE)
                page.wait_for_timeout(500)
                barra = page.locator(".sticky-bar")
                ok(page.eval_on_selector(".sticky-bar", "e => e.classList.contains('on')") and "41,67" in barra.inner_text(),
                   f"botão fixo do celular com o preço depois da primeira dobra ({' '.join(barra.inner_text().split())})")
                page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
                page.wait_for_timeout(300)
            page.eval_on_selector("#oferta", "el => window.scrollTo({top: el.getBoundingClientRect().top + window.scrollY - 100, behavior: 'instant'})")
            page.wait_for_timeout(500)
            estado = page.evaluate(ESTADO)
            vc = [c for c in estado["fbq"] if c[:2] == ["track", "ViewContent"]]
            esperado = {"value": 499.99, "currency": "BRL", "content_name": "Carreira com Sentido", "content_category": "pgBF", "pagina_versao": versao}
            ok(vc == [["track", "ViewContent", esperado]], f"ViewContent com value 499.99 e pagina_versao {versao} ({vc})")
            ok(["event", "view_offer", esperado] in estado["dl"], "view_offer no GA4 com pagina_versao")
            page.evaluate("document.addEventListener('click', e => e.preventDefault())")
            page.eval_on_selector("a.checkout", "a => a.click()")
            estado = page.evaluate(ESTADO)
            clique = {"content_category": "pgBF", "pagina_versao": versao}
            ok(["trackCustom", "CliqueComprar", clique] in estado["fbq"], f"CliqueComprar com pagina_versao {versao}")
            ok(["event", "clique_comprar", clique] in estado["dl"], "clique_comprar no GA4 com pagina_versao")
            ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
            page.close()

        print(f"--- {caminho} botão > pré-página > Hotmart")
        page, ctx = abre(b, caminho, UTMS + "&" + DURANTE)
        page.click("#oferta a.checkout")
        page.wait_for_url(lambda u: "/curso/inscricao/" in u, timeout=5000)
        ok(page.locator(".insc-bf").is_visible(), "pré-página mostra o preço de Black Friday")
        page.click('label.insc-forma:has(input[value="cartao"])')
        page.fill("#nome", "Maria Teste")
        page.fill("#email", "maria.teste@exemplo.com")
        page.fill("#whatsapp", "(51) 99999-8888")
        page.evaluate(ESPIAO)
        with page.expect_request(lambda r: "pay.hotmart.com" in r.url, timeout=5000):
            page.click("button[type=submit]")
        page.wait_for_timeout(200)
        destino = ctx["hotmart"][0] if ctx["hotmart"] else ""
        hq = parse_qs(urlsplit(destino).query)
        ok(destino.startswith("https://pay.hotmart.com/M100028858P?") and hq.get("off") == ["qu4x7j2d"], f"link da Hotmart com off=qu4x7j2d ({hq.get('off')})")
        ok(hq.get("sck") == ["ig|stories|ccs_bf|S01" + sufixo], f"sck com a versão, terminando em {sufixo} ({hq.get('sck')})")
        ok("versao" not in hq and "pg" not in hq and "bf_agora" not in hq, "nem versao, nem pg, nem bf_agora no link da Hotmart")
        dados = ctx["lambda"][0].post_data_json if ctx["lambda"] else {}
        ok(dados.get("pagina") == "pgBF" and dados.get("sck") == "ig|stories|ccs_bf|S01" + sufixo, f"cadastro com pgBF e o sck da versão ({dados.get('sck')})")
        oferta = {"value": 499.99, "currency": "BRL", "content_name": "Carreira com Sentido", "content_category": "pgBF", "pagina_versao": versao, "payment_type": "cartao"}
        ok(["track", "InitiateCheckout", oferta] in ctx["fbq"], f"InitiateCheckout com value 499.99 e pagina_versao {versao}")
        ok(["event", "begin_checkout", oferta] in ctx["dl"], "begin_checkout no GA4 com pagina_versao")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()

        for vp in ({"width": 390, "height": 844}, {"width": 1366, "height": 768}):
            print(f"--- {caminho} {vp['width']}px, depois do prazo")
            page, ctx = abre(b, caminho, DEPOIS, vp)
            texto = page.inner_text("body")
            ok("A Black Friday terminou" in texto, "mostra \"A Black Friday terminou\"")
            ok("499,99" not in texto and "41,67" not in texto and "360,01" not in texto, "nenhum preço de Black Friday na tela")
            ok("499,99" not in page.title(), f"título sem o preço ({page.title()})")
            ok(visivel(page, "a.checkout") == 0, "nenhum botão de compra da Black Friday visível")
            destinos = page.eval_on_selector_all("main a.btn", "els => els.filter(e => e.offsetParent !== null && !e.href.includes('wa.me')).map(a => new URL(a.href).pathname)")
            ok(destinos and all(d_ == "/curso/b/" for d_ in destinos), f"botões levam para curso/b/ ({destinos})")
            largura = page.evaluate(SEM_ROLAGEM)
            ok(largura[0] <= largura[1], f"sem rolagem horizontal ({largura[0]} <= {largura[1]})")
            ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
            page.close()

    # ---------- depois do prazo ----------
    for vp in ({"width": 390, "height": 844}, {"width": 1366, "height": 768}):
        print(f"--- black-friday/ {vp['width']}px, depois do prazo")
        page, ctx = abre(b, "black-friday/", DEPOIS, vp)
        texto = page.inner_text("body")
        ok("A Black Friday terminou" in texto, "mostra \"A Black Friday terminou\"")
        ok("499,99" not in texto and "41,67" not in texto and "360,01" not in texto, "nenhum preço de Black Friday na tela")
        ok("499,99" not in page.title(), f"título sem o preço ({page.title()})")
        ok(visivel(page, "a.checkout") == 0, "nenhum botão de compra da Black Friday visível")
        destinos = page.eval_on_selector_all(".bf-terminou a.btn, #programa a.btn, .final a.btn",
                                             "els => els.filter(e => e.offsetParent !== null).map(a => new URL(a.href).pathname)")
        ok(destinos and all(d_ == "/curso/b/" for d_ in destinos), f"botões levam para curso/b/ ({destinos})")
        largura = page.evaluate(SEM_ROLAGEM)
        ok(largura[0] <= largura[1], f"sem rolagem horizontal ({largura[0]} <= {largura[1]})")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()

    print("--- black-friday/ prazo acabando com a página aberta")
    page, ctx = abre(b, "black-friday/", "bf_agora=2026-11-30T23:59:58-03:00")
    ok(page.locator(".hero").is_visible(), "ainda na Black Friday")
    page.wait_for_function("document.documentElement.classList.contains('bf-fim')", timeout=5000)
    texto = page.inner_text("body")
    ok("A Black Friday terminou" in texto and "499,99" not in texto, "troca para \"terminou\" na hora, sem recarregar")
    page.close()

    # ---------- atalho black/ ----------
    print("--- black/ redireciona com a query")
    page, ctx = abre(b, "black/", UTMS + "&" + DURANTE)
    page.wait_for_url(lambda u: "/black-friday/" in u, timeout=5000)
    partes = urlsplit(page.url)
    ok(partes.path == "/black-friday/" and partes.query == UTMS + "&" + DURANTE, f"black/ > black-friday/ com a query ({page.url})")
    page.close()

    # ---------- faixa nas outras páginas ----------
    for caminho, destino in FAIXA.items():
        print(f"--- /{caminho} faixa")
        query = "utm_source=meta&utm_medium=paid" if caminho == "curso/b/" else ""
        page, ctx = abre(b, caminho, "&".join(x for x in (query, DURANTE) if x))
        faixa = page.locator("a.bf-faixa")
        ok(faixa.is_visible(), "faixa de Black Friday visível")
        txt = " ".join(faixa.inner_text().split())
        ok(re.search(r"Black Friday: de R\$ 860 por R\$ 499,99, termina em 5d 11h 59min \d\ds", txt, re.I) is not None, f"texto e contagem ({txt})")
        href = urlsplit(faixa.evaluate("a => a.href"))
        q = parse_qs(href.query)
        esperado = parse_qs(urlsplit(destino).query)
        ok(href.path == "/black-friday/" and all(q.get(k) == v for k, v in esperado.items()), f"link para {destino} ({href.path}?{href.query})")
        if caminho == "curso/b/":
            ok(q.get("utm_source") == ["meta"] and q.get("utm_medium") == ["paid"], "link da faixa preserva a query da visita")
        cab = page.evaluate("""() => { const f = document.querySelector('.bf-faixa').getBoundingClientRect();
          const h = document.querySelector('.site-header, .nav'); return h ? [f.bottom, h.getBoundingClientRect().top] : null; }""")
        if cab:
            ok(abs(cab[0] - cab[1]) < 1.5, f"cabeçalho logo abaixo da faixa, sem sobrepor ({cab})")
        largura = page.evaluate(SEM_ROLAGEM)
        ok(largura[0] <= largura[1], f"sem rolagem horizontal em 390px ({largura[0]} <= {largura[1]})")
        texto = page.inner_text("body")
        if caminho.startswith("curso/") or caminho.startswith("materiais/") and caminho != "materiais/" or caminho in ("quiz/", "calculadora/"):
            # linhas de preço que valem agora (o bloco do quiz e o da calculadora só aparecem depois do resultado)
            linhas = page.eval_on_selector_all(".preco-linha", "els => els.filter(e => getComputedStyle(e).display !== 'none').map(e => e.textContent.trim())")
            ok(LINHA_BF in linhas and LINHA not in linhas, f"preço de Black Friday no bloco do curso ({linhas})")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()

        page, ctx = abre(b, caminho, DEPOIS)
        texto = page.inner_text("body")
        ok(not page.locator("a.bf-faixa").is_visible() and "499,99" not in texto and "Black Friday" not in texto,
           "depois do prazo: sem faixa e sem preço de BF")
        if caminho.startswith("curso/"):
            ok(LINHA in texto and "12x de R$ 71,67" in texto, "depois do prazo: preço normal")
        page.close()

    print("--- home: card do curso durante e depois")
    for query, durante in ((DURANTE, True), (DEPOIS, False)):
        page, ctx = abre(b, "", query)
        card = page.locator("a.link.primary")
        ok(urlsplit(card.evaluate("a => a.href")).path == "/curso/b/", "card do curso continua indo para curso/b/")
        titulo, sub = card.locator("b").inner_text(), card.locator("small").inner_text()
        selo = page.locator(".bf-card__selo")
        if durante:
            ok((titulo, sub) == ("Black Friday: Carreira com Sentido", "De R$ 860 por R$ 499,99, só até 30/11"), f"durante: card com a oferta ({titulo} / {sub})")
            ok(selo.is_visible() and selo.inner_text().upper() == "BLACK FRIDAY", "durante: selo \"Black Friday\" no card")
            tam = page.eval_on_selector(".bf-faixa", "e => getComputedStyle(e).fontSize")
            ok(tam == "15px", f"faixa da home com letra de 15px ({tam})")
            caixa = page.evaluate("""() => { const c = document.querySelector('a.link.primary').getBoundingClientRect(), s = document.querySelector('.bf-card__selo').getBoundingClientRect();
              return s.right <= c.right && s.left >= c.left && s.right <= window.innerWidth; }""")
            ok(caixa, "selo dentro da largura do card e da tela em 390px")
        else:
            ok((titulo, sub) == ("Curso Carreira com Sentido", "Para psicólogas que querem viver bem da clínica"), f"depois: card com o texto normal ({titulo} / {sub})")
            ok(not selo.is_visible(), "depois: sem selo")
        largura = page.evaluate(SEM_ROLAGEM)
        ok(largura[0] <= largura[1], f"sem rolagem horizontal ({largura[0]} <= {largura[1]})")
        page.close()

    print("--- curso/b/: etiqueta e botões durante e depois")
    for query, durante in ((DURANTE, True), (DEPOIS, False)):
        page, ctx = abre(b, "curso/b/", "utm_source=meta&utm_medium=paid&" + query)
        etiqueta = page.locator(".hero .eyebrow:visible").inner_text().upper()
        # texto de cada botão de compra: só os <span> que estão aparecendo (data-bf on/off)
        botoes = page.eval_on_selector_all("a.checkout", """els => els.map(a => [...a.children]
          .filter(c => c.tagName === 'SPAN' && getComputedStyle(c).display !== 'none').map(c => c.textContent.trim()).join(''))""")
        hrefs = page.eval_on_selector_all("a.checkout", "els => els.map(a => a.href)")
        ok(all(urlsplit(h_).path == "/curso/inscricao/" and parse_qs(urlsplit(h_).query).get("pg") == ["pgB"] for h_ in hrefs), "botões continuam em curso/inscricao/?pg=pgB")
        if durante:
            ok(etiqueta == "BLACK FRIDAY · SÓ ATÉ 30/11", f"durante: etiqueta acima do H1 ({etiqueta})")
            ok(botoes and all(t == "Quero por R$ 499,99" for t in botoes), f"durante: botões \"Quero por R$ 499,99\" ({botoes})")
        else:
            ok(etiqueta == "CURSO ONLINE PARA PSICÓLOGAS CLÍNICAS", f"depois: etiqueta normal ({etiqueta})")
            ok(botoes and all(t == "Quero me inscrever" for t in botoes), f"depois: botões \"Quero me inscrever\" ({botoes})")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()

    print("--- curso/ e curso/b/: preços durante e depois")
    for caminho in ("curso/", "curso/b/", "curso/versao-b/"):
        page, ctx = abre(b, caminho, DURANTE, {"width": 1366, "height": 768})
        texto = page.inner_text("body")
        ok("12x de R$ 41,67" in texto and "71,67" not in texto and "1.497" not in texto, f"{caminho}: só o preço de BF durante")
        page.eval_on_selector("#oferta", ROLAR_ATE)
        page.wait_for_timeout(600)
        vc = [c for c in page.evaluate(ESTADO)["fbq"] if c[:2] == ["track", "ViewContent"]]
        ok(vc and vc[0][2].get("value") == 499.99, f"{caminho}: ViewContent com value 499.99 ({vc})")
        page.close()
        page, ctx = abre(b, caminho, DEPOIS, {"width": 1366, "height": 768})
        page.eval_on_selector("#oferta", ROLAR_ATE)
        page.wait_for_timeout(600)
        vc = [c for c in page.evaluate(ESTADO)["fbq"] if c[:2] == ["track", "ViewContent"]]
        ok(vc and vc[0][2].get("value") == 860, f"{caminho}: depois do prazo, ViewContent com value 860 ({vc})")
        page.close()

    print("--- terapia sem Black Friday")
    for caminho in ("terapia/", "terapia/b/"):
        page, ctx = abre(b, caminho, DURANTE)
        ok("Black Friday" not in page.inner_text("body") and page.locator(".bf-faixa").count() == 0, f"{caminho}: sem nada de Black Friday")
        ok(page.evaluate("typeof window.bfAtiva") == "undefined", f"{caminho}: não carrega o bf.js")
        page.close()

    print("--- domínio de produção: ?bf_agora ignorado")
    page, ctx = abre(b, "black-friday/", DEPOIS, dominio=True)
    ativa = datetime.now(timezone.utc) <= FIM
    ok(page.evaluate("window.bfAtiva()") == ativa, f"fora de localhost vale a hora real (bfAtiva = {ativa})")
    page.close()

    b.close()
servidor.shutdown()

print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
