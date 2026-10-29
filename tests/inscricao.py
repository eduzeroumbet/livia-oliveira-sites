"""Testa no Chromium headless a pré-página de inscrição do curso (curso/inscricao/), servida por http.server local.

Nada sai para a internet: a chamada à Lambda de cadastro é interceptada com page.route (e, por garantia, o host da
Lambda é mapeado para um endereço inexistente no Chromium, então nada é gravado na Lambda real); a navegação para a
Hotmart é interceptada e respondida com uma página vazia; Pixel e GA4 são bloqueados (os comandos ficam no fbq e no
dataLayer, registrados pelo teste antes de a página sair). Em 390px e 1440px:
- ao abrir: nenhuma forma de pagamento marcada, campos ocultos (hidden, sem ocupar espaço), as 3 opções visíveis sem
  rolar a 390x844 e com área de toque >= 48px; sem rolagem horizontal; sem travessão; honeypot vazio e fora da tela;
- só o PageView ao carregar (sem ViewContent nem InitiateCheckout);
- cada opção (cartão, Pix, boleto) abre os campos, foco no nome, muda o texto do botão e a dica; EscolhaPagamento no
  Pixel e escolha_pagamento no GA4 com payment_type, sem InitiateCheckout; trocar de opção preserva o que foi digitado;
  setas do teclado trocam a opção;
- envio vazio: erros nos 3 campos, sem cadastro e sem ir à Hotmart;
- envio com Maria Teste / maria.teste@exemplo.com / (51) 99999-8888: JSON enviado à Lambda (com forma), link final da
  Hotmart (off, checkoutMode, name, email, phoneac, phonenumber, src, sck, utms e os hide* da forma escolhida),
  advanced matching, InitiateCheckout e CadastroCheckout no Pixel, begin_checkout e cadastro_checkout no GA4 (com
  payment_type), nenhum Lead e nenhum dado pessoal no dataLayer;
- link da Hotmart para cada forma: cartão com hidePix e hideBillet; Pix sem hidePix; boleto sem hideBillet;
- envio sem forma (forçado): erro "Escolha a forma de pagamento." e nada é enviado;
- prints com os campos abertos em _catalogo/prints/curso-inscricao-escolha-{mobile,desktop}.png;
- Lambda com erro 500 e Lambda que não responde: vai para a Hotmart mesmo assim, em até ~2 s;
- sem pg nem UTM na URL: sck=direto|pgB e sem src.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/inscricao.py
Requer: playwright + chromium (python -m playwright install chromium).
"""
import functools
import json
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PIXEL_ID = "1197036460960933"
LAMBDA_HOST = "nwmxltflulqvcxu7bdplodmyjm0yweuc.lambda-url.sa-east-1.on.aws"
QUERY = "utm_source=meta&utm_medium=paid&utm_campaign=ccs_teste&utm_content=V01&pg=pgA"
SRC = "meta|paid|ccs_teste|V01"
NOME, EMAIL, WHATS = "Maria Teste", "maria.teste@exemplo.com", "(51) 99999-8888"
# métodos escondidos na Hotmart conforme a forma (ver HOTMART_ESCONDE no script.js)
ESCONDE = ["hidePix", "hidePixAutomatic", "hideBillet", "hideNupay", "hideMultipleCards", "hidePaypal", "hideApplePay",
           "hideGooglePay", "hideVirtualCard", "hideMercadoPago", "hideHybrid", "hideDirectDebit", "hideHotmartInstallments"]
MOSTRA = {"cartao": None, "pix": "hidePix", "boleto": "hideBillet"}
BOTAO = {
    "cartao": "Continuar para o pagamento no cartão",
    "pix": "Continuar para o pagamento com Pix",
    "boleto": "Continuar para o pagamento com boleto",
}
DICA = {"cartao": "só o cartão", "pix": "toque em Pix", "boleto": "toque em Boleto"}
PRINTS = ROOT / "_catalogo" / "prints"
CORS = {"access-control-allow-origin": "*", "access-control-allow-methods": "POST, OPTIONS", "access-control-allow-headers": "content-type"}
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
# registra cada chamada do fbq e cada push do dataLayer no Python (a página sai para a Hotmart logo depois do envio)
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


def abre(b, vp, lambda_modo="ok", query=QUERY):
    """Abre a pré-página com as rotas: site local, Lambda (ok, erro ou sem resposta), Hotmart; o resto é bloqueado."""
    page = b.new_page(viewport=vp)
    ctx = {"lambda": [], "hotmart": [], "pendentes": [], "fbq": [], "dl": [], "erros_js": []}

    def rota(route):
        req = route.request
        host = urlsplit(req.url).hostname
        if req.url.startswith(BASE):
            route.continue_()
        elif host == LAMBDA_HOST:
            if req.method == "OPTIONS":
                route.fulfill(status=204, headers=CORS)
                return
            ctx["lambda"].append(req)
            if lambda_modo == "ok":
                route.fulfill(status=200, headers=CORS, content_type="application/json", body=json.dumps({"ok": True}))
            elif lambda_modo == "erro":
                route.fulfill(status=500, headers=CORS, content_type="application/json", body='{"ok":false}')
            else:
                ctx["pendentes"].append(route)  # sem resposta (timeout)
        elif host == "pay.hotmart.com":
            ctx["hotmart"].append(req.url)
            route.fulfill(status=200, content_type="text/html", body="<!doctype html><title>Hotmart (teste)</title>")
        else:
            route.abort()

    page.route("**/*", rota)
    page.expose_function("registra", lambda tipo, item: ctx[tipo].append(item))
    page.on("pageerror", lambda e: ctx["erros_js"].append(str(e)))
    page.goto(f"{BASE}/curso/inscricao/" + ("?" + query if query else ""), wait_until="load")
    return page, ctx


def hides(forma):
    """Parâmetros hide*=1 esperados no link da Hotmart para a forma."""
    return {k: ["1"] for k in ESCONDE if k != MOSTRA[forma]}


def escolhe(page, forma):
    page.click(f'label.insc-forma:has(input[value="{forma}"])')
    page.wait_for_timeout(50)


def envia(page, ctx, nome=NOME, email=EMAIL, whats=WHATS, forma="cartao"):
    """Escolhe a forma (se ainda não houver), preenche, envia e espera a ida à Hotmart. Devolve o tempo do clique até o pedido da Hotmart e o estado do
    botão logo depois do clique (None se a página já tiver saído)."""
    if not page.evaluate("!!document.querySelector('input[name=forma]:checked')"):
        escolhe(page, forma)
    page.fill("#nome", nome)
    page.fill("#email", email)
    page.fill("#whatsapp", whats)
    page.evaluate(ESPIAO)
    t0 = time.monotonic()
    botao = None
    with page.expect_request(lambda r: "pay.hotmart.com" in r.url, timeout=5000):
        page.click("button[type=submit]")
        try:
            botao = page.evaluate("(() => { const b = document.querySelector('button[type=submit]'); return [b.disabled, b.textContent]; })()")
        except Exception:
            pass
    tempo = time.monotonic() - t0
    page.wait_for_url(lambda u: "pay.hotmart.com" in u, timeout=5000)
    page.wait_for_timeout(100)
    return tempo, botao


with sync_playwright() as p:
    b = p.chromium.launch(args=[f"--host-resolver-rules=MAP {LAMBDA_HOST} ~NOTFOUND"])

    for vp in ({"width": 390, "height": 844}, {"width": 1440, "height": 900}):
        print(f"--- curso/inscricao/ {vp['width']}px, Lambda ok")
        page, ctx = abre(b, vp)

        ok("—" not in page.inner_text("body"), "sem travessão no texto")
        inicio = page.evaluate("""() => { const d = document.getElementById('insc-dados');
          return {marcadas: document.querySelectorAll('input[name=forma]:checked').length, hidden: d.hidden,
                  altura: d.getBoundingClientRect().height, botao: document.querySelector('button[type=submit]').offsetParent !== null,
                  grupo: document.querySelector('[role=radiogroup]') !== null, radios: document.querySelectorAll('input[type=radio][name=forma]').length}; }""")
        ok(inicio == {"marcadas": 0, "hidden": True, "altura": 0, "botao": False, "grupo": True, "radios": 3},
           f"ao abrir: nenhuma forma marcada, campos ocultos e sem espaço, radiogroup com 3 opções ({inicio})")
        caixas = page.evaluate("[...document.querySelectorAll('label.insc-forma')].map(l => { const r = l.getBoundingClientRect(); return [r.height, r.bottom]; })")
        ok(all(h >= 48 for h, _ in caixas), f"opções com área de toque >= 48px ({[round(h) for h, _ in caixas]})")
        ok(page.evaluate("window.scrollY") == 0 and caixas[-1][1] <= vp["height"], f"as 3 opções visíveis sem rolar ({caixas[-1][1]:.0f} <= {vp['height']})")
        larg = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        ok(larg[0] <= larg[1], f"sem rolagem horizontal ({larg[0]} <= {larg[1]})")
        hp = page.evaluate("""() => { const e = document.getElementById('empresa'); const r = e.getBoundingClientRect();
          return {valor: e.value, tab: e.getAttribute('tabindex'), auto: e.getAttribute('autocomplete'), fora: r.right <= 0 || r.width <= 1}; }""")
        ok(hp == {"valor": "", "tab": "-1", "auto": "off", "fora": True}, f"honeypot vazio, fora da tela, tabindex -1 e autocomplete off ({hp})")
        ok(page.get_attribute('a[href*="privacidade/"]', "href") is not None, "link para a Política de privacidade")

        estado = page.evaluate(ESTADO)
        ok(["init", PIXEL_ID] in estado["fbq"], "Pixel iniciado")
        tracks = [c[1] for c in estado["fbq"] if c[0] in ("track", "trackCustom")]
        ok(tracks == ["PageView"], f"ao carregar só o PageView ({tracks})")

        # escolha da forma: cada opção abre os campos e muda o botão e a dica; trocar preserva o que foi digitado
        for i, forma in enumerate(("cartao", "pix", "boleto")):
            escolhe(page, forma)
            st = page.evaluate("""() => ({hidden: document.getElementById('insc-dados').hidden,
              botao: document.querySelector('button[type=submit]').textContent, dica: document.getElementById('insc-dica').textContent,
              marcada: document.querySelector('input[name=forma]:checked').value, foco: document.activeElement.id})""")
            ok(not st["hidden"] and st["marcada"] == forma and st["botao"] == BOTAO[forma] and DICA[forma] in st["dica"],
               f"{forma}: campos abertos, botão \"{st['botao']}\" e dica")
            if i == 0:
                ok(st["foco"] == "nome", f"foco no nome ao abrir os campos ({st['foco']})")
                page.fill("#nome", "Ana Digitada")
                page.fill("#email", "ana@exemplo.com")
        ok(page.input_value("#nome") == "Ana Digitada" and page.input_value("#email") == "ana@exemplo.com",
           "trocar de opção preserva o que foi digitado")
        page.wait_for_timeout(400)
        page.screenshot(path=str(PRINTS / f"curso-inscricao-escolha-{'mobile' if vp['width'] < 900 else 'desktop'}.png"), full_page=True)
        page.focus('input[name=forma][value="boleto"]')
        page.keyboard.press("ArrowUp")
        ok(page.evaluate("document.querySelector('input[name=forma]:checked').value") == "pix"
           and page.evaluate("document.activeElement.value") == "pix", "seta do teclado troca a opção sem tirar o foco do grupo")
        estado = page.evaluate(ESTADO)
        escolhas = [c[2] for c in estado["fbq"] if c[:2] == ["trackCustom", "EscolhaPagamento"]]
        ok([e.get("payment_type") for e in escolhas] == ["cartao", "pix", "boleto", "pix"] and all(e.get("content_category") == "pgA" for e in escolhas),
           f"EscolhaPagamento no Pixel com payment_type ({escolhas})")
        ok(["event", "escolha_pagamento", {"content_category": "pgA", "payment_type": "cartao"}] in estado["dl"], "escolha_pagamento no GA4")
        ok(not any(c[1] in ("InitiateCheckout", "Lead") for c in estado["fbq"] if len(c) > 1), "escolher não dispara InitiateCheckout nem Lead")
        escolhe(page, "cartao")
        page.fill("#nome", "")
        page.fill("#email", "")

        # envio vazio
        page.click("button[type=submit]")
        page.wait_for_timeout(300)
        erros = {n: page.inner_text(f'[data-error-for="{n}"]') for n in ("nome", "email", "whatsapp")}
        ok(all(erros.values()), f"erros nos 3 campos ({erros})")
        ok(page.evaluate("document.activeElement.id") == "nome", "foco no primeiro campo com erro")
        ok(not ctx["lambda"] and not ctx["hotmart"], "envio vazio não cadastra nem vai à Hotmart")
        page.fill("#nome", "M")
        page.fill("#email", "maria@")
        page.fill("#whatsapp", "51 9999")
        page.click("button[type=submit]")
        page.wait_for_timeout(300)
        ok(all(page.inner_text(f'[data-error-for="{n}"]') for n in ("nome", "email", "whatsapp")), "erros com nome de 1 letra, e-mail incompleto e WhatsApp curto")
        ok(page.input_value("#whatsapp") == "(51) 9999", f"máscara do WhatsApp ({page.input_value('#whatsapp')})")

        # envio certo
        envia(page, ctx)
        page.wait_for_url(lambda u: "pay.hotmart.com" in u, timeout=5000)

        ok(len(ctx["lambda"]) == 1, f"uma chamada à Lambda ({len(ctx['lambda'])})")
        if ctx["lambda"]:
            req = ctx["lambda"][0]
            ok(req.method == "POST" and "application/json" in (req.headers.get("content-type") or ""), "POST application/json")
            dados = req.post_data_json
            esperado = {
                "nome": NOME, "email": EMAIL, "whatsapp": "51999998888", "pagina": "pgA", "forma": "cartao", "src": SRC, "sck": f"{SRC}|pgA",
                "utm_source": "meta", "utm_medium": "paid", "utm_campaign": "ccs_teste", "utm_content": "V01", "utm_term": "",
                "url": f"{BASE}/curso/inscricao/?{QUERY}", "consentimento": "sim", "fbp": "", "fbc": "", "empresa": "",
            }
            ok(dados == esperado, f"JSON do cadastro {dados}")

        ok(len(ctx["hotmart"]) == 1, "uma ida à Hotmart")
        if ctx["hotmart"]:
            url = ctx["hotmart"][0]
            partes = urlsplit(url)
            q = parse_qs(partes.query)
            esperado = {
                "off": ["n2h6k72h"], "checkoutMode": ["10"], "name": [NOME], "email": [EMAIL], "phoneac": ["51"],
                "phonenumber": ["999998888"], "src": [SRC], "sck": [f"{SRC}|pgA"], "utm_source": ["meta"],
                "utm_medium": ["paid"], "utm_campaign": ["ccs_teste"], "utm_content": ["V01"], **hides("cartao"),
            }
            ok(partes.netloc == "pay.hotmart.com" and partes.path == "/M100028858P", f"produto M100028858P ({partes.netloc}{partes.path})")
            ok(q == esperado, f"parâmetros da Hotmart {q}")
            ok("+" not in partes.query and "name=Maria%20Teste" in partes.query, "espaço do nome como %20")

        fbq = ctx["fbq"]
        oferta = {"value": 860, "currency": "BRL", "content_name": "Carreira com Sentido", "content_category": "pgA", "payment_type": "cartao"}
        ok(["init", PIXEL_ID, {"em": EMAIL, "ph": "5551999998888", "fn": "maria"}] in fbq, "advanced matching (em, ph, fn) no Pixel")
        ok(["track", "InitiateCheckout", oferta] in fbq, "InitiateCheckout no Pixel")
        ok(["trackCustom", "CadastroCheckout", {"content_category": "pgA", "payment_type": "cartao"}] in fbq, "CadastroCheckout no Pixel")
        ok(fbq.index(["init", PIXEL_ID, {"em": EMAIL, "ph": "5551999998888", "fn": "maria"}]) < fbq.index(["track", "InitiateCheckout", oferta]),
           "advanced matching antes do InitiateCheckout")
        ok(not any("Lead" in c for c in fbq), "nenhum Lead no Pixel")
        ok(["event", "begin_checkout", oferta] in ctx["dl"], "begin_checkout no GA4")
        ok(["event", "cadastro_checkout", {"content_category": "pgA", "payment_type": "cartao"}] in ctx["dl"], "cadastro_checkout no GA4")
        ok(not any(isinstance(c, list) and c[:2] == ["event", "generate_lead"] for c in ctx["dl"]), "nenhum generate_lead")
        texto_dl = json.dumps(ctx["dl"], ensure_ascii=False).lower()
        ok(not any(x in texto_dl for x in ("maria", "exemplo.com", "99999")), "nenhum dado pessoal no dataLayer/GA4")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()

    # link da Hotmart para cada forma: só os métodos da forma escolhida (o cartão a Hotmart não deixa esconder)
    for forma in ("cartao", "pix", "boleto"):
        print(f"--- curso/inscricao/ 390px, forma {forma}")
        page, ctx = abre(b, {"width": 390, "height": 844})
        envia(page, ctx, forma=forma)
        q = parse_qs(urlsplit(ctx["hotmart"][0]).query) if ctx["hotmart"] else {}
        base = {"name": [NOME], "email": [EMAIL], "phoneac": ["51"], "phonenumber": ["999998888"], "src": [SRC], "sck": [f"{SRC}|pgA"]}
        ok(all(q.get(k) == v for k, v in base.items()), f"{forma}: mantém name, email, phone, src e sck")
        ok({k: v for k, v in q.items() if k.startswith("hide")} == hides(forma), f"{forma}: hide* corretos ({sorted(k for k in q if k.startswith('hide'))})")
        if forma == "cartao":
            ok(q.get("hidePix") == ["1"] and q.get("hideBillet") == ["1"], "cartao: hidePix=1 e hideBillet=1")
        else:
            ok(MOSTRA[forma] not in q and q.get("hidePixAutomatic") == ["1"], f"{forma}: sem {MOSTRA[forma]} e com hidePixAutomatic=1")
        dados = ctx["lambda"][0].post_data_json if ctx["lambda"] else {}
        ok(dados.get("forma") == forma, f"{forma}: cadastro com forma={dados.get('forma')}")
        ok(["trackCustom", "CadastroCheckout", {"content_category": "pgA", "payment_type": forma}] in ctx["fbq"], f"{forma}: CadastroCheckout com payment_type")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()

    # envio sem forma (não deve acontecer pela interface): erro no grupo
    print("--- curso/inscricao/ envio sem forma")
    page, ctx = abre(b, {"width": 390, "height": 844})
    page.evaluate("document.getElementById('inscricao').requestSubmit()")
    page.wait_for_timeout(200)
    ok(page.inner_text('[data-error-for="forma"]') == "Escolha a forma de pagamento." and not ctx["lambda"] and not ctx["hotmart"],
       "sem forma: \"Escolha a forma de pagamento.\" e não envia")
    escolhe(page, "pix")
    ok(page.inner_text('[data-error-for="forma"]') == "", "erro some ao escolher")
    page.close()

    # Lambda com erro ou sem resposta: a compra não pode travar
    for modo in ("erro", "timeout"):
        print(f"--- curso/inscricao/ 390px, Lambda {modo}")
        page, ctx = abre(b, {"width": 390, "height": 844}, lambda_modo=modo)
        tempo, botao = envia(page, ctx)
        ok(len(ctx["hotmart"]) == 1 and tempo <= 2.3, f"vai para a Hotmart em {tempo:.2f}s com a Lambda em {modo}")
        if modo == "timeout":
            ok(botao == [True, "Abrindo o pagamento..."], f"botão desabilitado com \"Abrindo o pagamento...\" ({botao})")
        ok(len(ctx["lambda"]) == 1, "tentou o cadastro")
        for r in ctx["pendentes"]:
            try:
                r.abort()
            except Exception:
                pass
        page.close()

    # sem pg nem UTM: sck=direto|pgB, sem src
    print("--- curso/inscricao/ sem pg nem UTM")
    page, ctx = abre(b, {"width": 390, "height": 844}, query="")
    envia(page, ctx)
    q = parse_qs(urlsplit(ctx["hotmart"][0]).query) if ctx["hotmart"] else {}
    ok(q.get("sck") == ["direto|pgB"] and "src" not in q and not any(k.startswith("utm_") for k in q), f"sck=direto|pgB e sem src ({q.get('sck')})")
    dados = ctx["lambda"][0].post_data_json if ctx["lambda"] else {}
    ok(dados.get("pagina") == "pgB" and dados.get("sck") == "direto|pgB" and dados.get("src") == "", f"cadastro com pagina pgB ({dados.get('pagina')})")
    ok(["trackCustom", "CadastroCheckout", {"content_category": "pgB", "payment_type": "cartao"}] in ctx["fbq"], "CadastroCheckout com pgB")
    page.close()

    b.close()
servidor.shutdown()

print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
