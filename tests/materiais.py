"""Testa no Chromium headless os materiais gratuitos (materiais/ e materiais/<slug>/), servidos por http.server local.

Nada sai para a internet: a chamada à Lambda de cadastro é interceptada com page.route (e, por garantia, o host da
Lambda é mapeado para um endereço inexistente no Chromium); Pixel e GA4 são bloqueados (os comandos ficam na fila do
fbq e no dataLayer, e é isso que o teste confere). Em 375px e 1440px:
- hub: 6 cards (etiqueta, título, linha de apoio, "Abrir material"), nota do cadastro único, links com as UTMs da
  visita, sem travessão, sem rolagem horizontal;
- mensagens/ sem cadastro: Mensagens 1 e 2 abertas, o resto borrado, inerte e não selecionável, cartão "Libere o
  material completo, grátis"; PageView e ViewContent (material_mensagens), nenhum Lead;
- contato: erros nos 4 campos, honeypot fora da tela; envio: JSON da Lambda (pagina pgMat, ferramenta material,
  resultado mensagens, src, sck, utm_*...), material aberto em <= 2 s, localStorage livia_mat_ok=1, Lead (Pixel) e
  generate_lead (GA4) uma vez com content_name material_mensagens, advanced matching (em, ph, fn), nenhum dado
  pessoal no dataLayer;
- Copiar: texto puro com os [campos] na área de transferência, "Copiado", MaterialCopiar {material};
- Salvar em PDF: window.print e MaterialPDF; CTA do curso com as utm de material e ViewContent material_para_curso;
  WhatsApp com o título do material; "Outros materiais" com os outros 5; nenhum InitiateCheckout;
- faltas/ no mesmo navegador abre já liberada, sem formulário;
- prints em _catalogo/prints/materiais-{hub,mensagens-bloqueada,mensagens-liberada}-{mobile,desktop}.png.
Em 375px: etica/ (liberada) mostra a frase final só com os 10 itens marcados; Lambda com erro 500 e sem resposta:
o material abre mesmo assim, em <= 2 s; sem UTM: sck=direto|pgMat; páginas sem rolagem horizontal.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/materiais.py
Requer: playwright + chromium (python -m playwright install chromium).
"""
import functools
import json
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PIXEL_ID = "1197036460960933"
LAMBDA_HOST = "nwmxltflulqvcxu7bdplodmyjm0yweuc.lambda-url.sa-east-1.on.aws"
QUERY = "utm_source=meta&utm_medium=paid&utm_campaign=ccs_material&utm_content=MAT-mensagens&fbclid=abc123"
SRC = "meta|paid|ccs_material|MAT-mensagens"
NOME, EMAIL, WHATS = "Maria Teste", "maria.teste@exemplo.com", "(51) 99999-8888"
SLUGS = ["mensagens", "faltas", "etica", "reajuste", "posts", "indicacoes"]
MSG1 = ("Oi, [nome]! Aqui é a [seu nome], psicóloga. Obrigada por me procurar. Eu atendo [online / presencialmente em cidade], "
        "com sessões semanais de [50] minutos. O valor da sessão é R$ [valor]. Tenho horários [dias e turnos]. Se fizer sentido "
        "para você, me conta qual horário fica melhor que eu já reservo.")
PODE = "Pode postar. Ética não é freio, é o que faz a paciente confiar em você."
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
TRAVA = """() => { const t = document.getElementById('mat-trava'); const s = getComputedStyle(t);
  return {inert: t.inert, filtro: s.filter, selecao: s.userSelect || s.webkitUserSelect, ok: document.documentElement.classList.contains('mat-ok')}; }"""


def eventos_fbq(estado, nome, tipo="track"):
    return [c for c in estado["fbq"] if c[:2] == [tipo, nome]]


def eventos_gtag(estado, nome):
    return [c for c in estado["dl"] if isinstance(c, list) and c[:2] == ["event", nome]]


def nova_aba(ctx_b, vp=None, lambda_modo="ok"):
    """Página com as rotas: site local, Lambda (ok, erro ou sem resposta); o resto é bloqueado."""
    page = ctx_b.new_page()
    if vp:
        page.set_viewport_size(vp)
    ctx = {"lambda": [], "pendentes": [], "erros_js": []}

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
        else:
            route.abort()

    page.route("**/*", rota)
    page.on("pageerror", lambda e: ctx["erros_js"].append(str(e)))
    return page, ctx


def contexto(b, vp):
    c = b.new_context(viewport=vp)
    c.grant_permissions(["clipboard-read", "clipboard-write"], origin=BASE)
    return c


def preenche(page, nome=NOME, email=EMAIL, whats=WHATS, aceita=True):
    page.fill("#nome", nome)
    page.fill("#email", email)
    page.fill("#whatsapp", whats)
    page.set_checked("#consentimento", aceita)


def envia(page):
    """Envia o contato e devolve o tempo até o material abrir (None se não abrir em 3 s)."""
    t0 = time.monotonic()
    page.click("#contato button[type=submit]")
    try:
        page.wait_for_function("document.documentElement.classList.contains('mat-ok')", timeout=3000)
    except Exception:
        return None
    return time.monotonic() - t0


def sem_rolagem(page, onde):
    larg = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
    ok(larg[0] <= larg[1], f"{onde} sem rolagem horizontal ({larg[0]} <= {larg[1]})")


def fecha(page, ctx):
    for r in ctx["pendentes"]:
        try:
            r.abort()
        except Exception:
            pass
    page.close()


with sync_playwright() as p:
    b = p.chromium.launch(args=[f"--host-resolver-rules=MAP {LAMBDA_HOST} ~NOTFOUND"])

    for vp in ({"width": 375, "height": 812}, {"width": 1440, "height": 900}):
        tela = "mobile" if vp["width"] < 900 else "desktop"
        cb = contexto(b, vp)

        # ---------- hub ----------
        print(f"--- materiais/ {vp['width']}px, com UTM")
        page, ctx = nova_aba(cb)
        page.goto(f"{BASE}/materiais/?{QUERY}", wait_until="load")
        ok("—" not in page.inner_text("body"), "hub sem travessão")
        ok(page.inner_text("h1") == "Materiais gratuitos para a sua clínica", f"título do hub ({page.inner_text('h1')})")
        ok(page.inner_text(".mat-topo .sub") == "Seis pílulas prontas para usar, tiradas do Carreira com Sentido. Copie, adapte e use ainda hoje.", "subtítulo do hub")
        cards = page.evaluate("""[...document.querySelectorAll('.mat-grade--hub .mat-card')].map(c => ({
          etiqueta: c.querySelector('.eyebrow').textContent, titulo: c.querySelector('h2').textContent,
          apoio: c.querySelector('p').textContent, botao: c.querySelector('a').textContent, href: c.querySelector('a').href}))""")
        ok(len(cards) == 6, f"hub com 6 cards ({len(cards)})")
        ok([urlsplit(c["href"]).path for c in cards] == [f"/materiais/{s}/" for s in SLUGS], "cards na ordem das pílulas")
        ok(all(c["etiqueta"].startswith(f"Pílula {i + 1} · Módulo") and c["titulo"] and c["apoio"] and c["botao"] == "Abrir material"
               for i, c in enumerate(cards)), "cada card com etiqueta, título, linha de apoio e \"Abrir material\"")
        ok(all(parse_qs(urlsplit(c["href"]).query).get("utm_content") == ["MAT-mensagens"] for c in cards), "links dos cards mantêm a query da visita")
        ok(page.inner_text(".mat-hub__nota") == "Os materiais são gratuitos. Você deixa nome, e-mail e WhatsApp uma vez e libera todos.", "nota do cadastro único")
        estado = page.evaluate(ESTADO)
        ok([c[1] for c in estado["fbq"] if c[0] in ("track", "trackCustom")] == ["PageView"], "hub: só o PageView")
        sem_rolagem(page, "hub")
        page.wait_for_timeout(300)
        page.screenshot(path=str(PRINTS / f"materiais-hub-{tela}.png"), full_page=True)
        ok(not ctx["erros_js"], f"hub sem erros de JS {ctx['erros_js']}")
        page.close()

        # ---------- mensagens/ bloqueada ----------
        print(f"--- materiais/mensagens/ {vp['width']}px, com UTM, sem cadastro")
        page, ctx = nova_aba(cb, lambda_modo="ok")
        page.goto(f"{BASE}/materiais/mensagens/?{QUERY}", wait_until="load")
        ok("—" not in page.inner_text("body"), "sem travessão")
        ok(page.title() == "8 mensagens prontas para o WhatsApp da clínica | Materiais gratuitos da Lívia Oliveira", f"title ({page.title()})")
        ok(page.inner_text(".mat-topo .eyebrow").upper() == "PÍLULA 1 · MÓDULO 3, COMUNICAÇÃO ASSERTIVA", "etiqueta")
        visiveis = page.evaluate("[...document.querySelectorAll('.mat-itens .mat-item__num')].map(e => e.textContent)")
        ok(visiveis == ["Mensagem 1.", "Mensagem 2."], f"Mensagens 1 e 2 abertas ({visiveis})")
        trancadas = page.evaluate("document.querySelectorAll('#mat-trava .mat-item').length")
        ok(trancadas == 6, f"6 mensagens no trecho bloqueado ({trancadas})")
        t = page.evaluate(TRAVA)
        ok(t["inert"] and "blur" in t["filtro"] and t["selecao"] == "none" and not t["ok"], f"trecho bloqueado: inerte, borrado e não selecionável ({t})")
        ok(page.is_visible("#contato") and page.inner_text("#contato h2") == "Libere o material completo, grátis", "cartão do cadastro visível")
        ok(page.evaluate("document.querySelectorAll('.mat-itens mark.mat-campo').length") >= 5, "[campos] destacados")
        estado = page.evaluate(ESTADO)
        ok(["init", PIXEL_ID] in estado["fbq"], "Pixel iniciado")
        tracks = [c[1] for c in estado["fbq"] if c[0] in ("track", "trackCustom")]
        ok(tracks == ["PageView", "ViewContent"], f"ao carregar: PageView e ViewContent ({tracks})")
        vista = {"content_name": "material_mensagens"}
        ok(eventos_fbq(estado, "ViewContent") == [["track", "ViewContent", vista]], "ViewContent com content_name material_mensagens")
        ok(eventos_gtag(estado, "material_view") == [["event", "material_view", vista]], "material_view no GA4")
        ok(not eventos_fbq(estado, "Lead") and not eventos_gtag(estado, "generate_lead"), "nenhum Lead antes do envio")
        sem_rolagem(page, "material bloqueado")

        # Copiar (mensagem aberta)
        page.click(".mat-itens .mat-copiar >> nth=0")
        page.wait_for_timeout(150)
        ok(page.evaluate("navigator.clipboard.readText()") == MSG1, "Copiar põe o texto puro, com os [campos], na área de transferência")
        ok(page.inner_text(".mat-itens .mat-copiar >> nth=0") == "Copiado", "botão mostra \"Copiado\"")
        caixa = page.evaluate("(() => { const r = document.querySelector('.mat-copiar').getBoundingClientRect(); return [r.width, r.height]; })()")
        ok(caixa[1] >= 48 and caixa[0] >= 120, f"botão Copiar grande ({[round(x) for x in caixa]})")
        estado = page.evaluate(ESTADO)
        copiar = {"material": "mensagens"}
        ok(eventos_fbq(estado, "MaterialCopiar", "trackCustom") == [["trackCustom", "MaterialCopiar", copiar]], "MaterialCopiar no Pixel")
        ok(eventos_gtag(estado, "material_copiar") == [["event", "material_copiar", copiar]], "material_copiar no GA4")
        page.wait_for_timeout(2200)
        ok(page.inner_text(".mat-itens .mat-copiar >> nth=0") == "Copiar", "botão volta para \"Copiar\"")
        page.wait_for_timeout(200)
        page.screenshot(path=str(PRINTS / f"materiais-mensagens-bloqueada-{tela}.png"), full_page=True)

        # validação
        hp = page.evaluate("""() => { const e = document.getElementById('empresa'); const r = e.getBoundingClientRect();
          return {valor: e.value, tab: e.getAttribute('tabindex'), auto: e.getAttribute('autocomplete'), fora: r.right <= 0 || r.width <= 1}; }""")
        ok(hp == {"valor": "", "tab": "-1", "auto": "off", "fora": True}, f"honeypot vazio, fora da tela ({hp})")
        ok(page.get_attribute('#contato a[href*="privacidade/"]', "href") is not None, "link para a Política de privacidade no consentimento")
        page.click("#contato button[type=submit]")
        page.wait_for_timeout(200)
        erros = {n: page.inner_text(f'#contato [data-error-for="{n}"]') for n in ("nome", "email", "whatsapp", "consentimento")}
        ok(all(erros.values()), f"erros nos 4 campos ({erros})")
        ok(not ctx["lambda"] and page.evaluate(TRAVA)["inert"], "envio inválido não cadastra nem libera")

        # envio certo
        preenche(page)
        tempo = envia(page)
        ok(tempo is not None and tempo <= 2, f"material abre em {tempo if tempo is None else round(tempo, 2)}s")
        ok(len(ctx["lambda"]) == 1, f"uma chamada à Lambda ({len(ctx['lambda'])})")
        if ctx["lambda"]:
            req = ctx["lambda"][0]
            ok(req.method == "POST" and "application/json" in (req.headers.get("content-type") or ""), "POST application/json")
            esperado = {
                "nome": NOME, "email": EMAIL, "whatsapp": "51999998888", "pagina": "pgMat", "src": SRC, "sck": f"{SRC}|pgMat",
                "utm_source": "meta", "utm_medium": "paid", "utm_campaign": "ccs_material", "utm_content": "MAT-mensagens", "utm_term": "",
                "url": f"{BASE}/materiais/mensagens/?{QUERY}", "consentimento": "sim", "fbp": "", "fbc": "", "empresa": "",
                "ferramenta": "material", "resultado": "mensagens",
            }
            dados = req.post_data_json
            ok(dados == esperado, f"JSON do cadastro {dados}")
        t = page.evaluate(TRAVA)
        ok(not t["inert"] and t["filtro"] == "none" and t["ok"], f"material liberado: sem borrado e sem inert ({t})")
        ok(page.is_hidden("#contato"), "formulário some depois do envio")
        ok(page.evaluate("localStorage.getItem('livia_mat_ok')") == "1", "localStorage livia_mat_ok = 1")
        estado = page.evaluate(ESTADO)
        lead = {"content_name": "material_mensagens"}
        ok(eventos_fbq(estado, "Lead") == [["track", "Lead", lead]], "Lead no Pixel, uma vez")
        ok(eventos_gtag(estado, "generate_lead") == [["event", "generate_lead", lead]], "generate_lead no GA4, uma vez")
        ok(["init", PIXEL_ID, {"em": EMAIL, "ph": "5551999998888", "fn": "maria"}] in estado["fbq"], "advanced matching (em, ph, fn) no Pixel")
        texto_dl = json.dumps(estado["dl"], ensure_ascii=False, default=str).lower()
        ok(not any(x in texto_dl for x in ("maria", "exemplo.com", "99999")), "nenhum dado pessoal no dataLayer/GA4")

        # copiar uma mensagem que estava bloqueada
        page.click("#mat-trava .mat-copiar >> nth=0")
        page.wait_for_timeout(150)
        ok(page.evaluate("navigator.clipboard.readText()").startswith("Oi, [nome]! Confirmando nossa primeira sessão: [dia]"),
           "Copiar funciona na mensagem liberada")
        sem_rolagem(page, "material liberado")

        # PDF, CTA, WhatsApp, outros materiais
        page.evaluate("() => { window.print = () => { window.__imprimiu = (window.__imprimiu || 0) + 1; }; }")
        page.click("#mat-pdf")
        n_imp = page.evaluate("window.__imprimiu"); ok(n_imp == 1, f"Salvar em PDF chama window.print ({n_imp})")
        estado = page.evaluate(ESTADO)
        ok(len(eventos_fbq(estado, "MaterialPDF", "trackCustom")) == 1 and len(eventos_gtag(estado, "material_pdf")) == 1, "MaterialPDF no Pixel e material_pdf no GA4")
        page.emulate_media(media="print")
        impresso = page.evaluate("""() => ['.site-header', '.site-footer', '#contato', '.mat-outros', '#mat-pdf']
          .map(s => getComputedStyle(document.querySelector(s)).display)""")
        ok(all(d == "none" for d in impresso), f"impressão sem cabeçalho, rodapé, formulário, outros materiais e botão ({impresso})")
        ok(page.evaluate("getComputedStyle(document.getElementById('mat-trava')).display") != "none", "impressão liberada: material todo aberto")
        page.emulate_media(media="screen")

        curso = page.get_attribute("#mat-curso", "href")
        partes, q = urlsplit(curso), parse_qs(urlsplit(curso).query)
        ok(partes.path == "/curso/b/" and q.get("utm_source") == ["material"] and q.get("utm_medium") == ["site"]
           and q.get("utm_campaign") == ["ccs_material"] and q.get("utm_content") == ["mat_mensagens"] and all(len(v) == 1 for v in q.values()),
           f"Conhecer o curso com as utm de material ({q})")
        wa = page.get_attribute("#mat-wa", "href")
        ok(wa.startswith("https://wa.me/5551992597638?text=")
           and unquote(wa.split("text=", 1)[1]) == "Oi! Baixei o material 8 mensagens prontas para o WhatsApp da clínica e quero saber mais sobre o Carreira com Sentido.",
           f"WhatsApp da equipe com o título do material ({unquote(wa)})")
        outros = page.evaluate("[...document.querySelectorAll('.mat-outros .mat-outro')].map(a => new URL(a.href).pathname)")
        ok(outros == [f"/materiais/{s}/" for s in SLUGS if s != "mensagens"], f"Outros materiais com os outros 5 ({outros})")
        page.wait_for_timeout(600)
        page.screenshot(path=str(PRINTS / f"materiais-mensagens-liberada-{tela}.png"), full_page=True)

        page.evaluate("document.addEventListener('click', e => e.preventDefault())")
        page.click("#mat-curso")
        estado = page.evaluate(ESTADO)
        oferta = {"content_name": "material_para_curso"}
        ok(eventos_fbq(estado, "ViewContent")[-1:] == [["track", "ViewContent", oferta]], "ViewContent material_para_curso no clique do curso")
        ok(eventos_gtag(estado, "view_offer") == [["event", "view_offer", oferta]], "view_offer no GA4")
        ok(not eventos_fbq(estado, "InitiateCheckout") and not eventos_gtag(estado, "begin_checkout"), "nenhum InitiateCheckout / begin_checkout")
        ok(len(eventos_fbq(estado, "Lead")) == 1, "continua um Lead só")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        fecha(page, ctx)

        # ---------- outra página já liberada ----------
        print(f"--- materiais/faltas/ {vp['width']}px, depois do cadastro")
        page, ctx = nova_aba(cb)
        page.goto(f"{BASE}/materiais/faltas/", wait_until="load")
        t = page.evaluate(TRAVA)
        ok(t["ok"] and not t["inert"] and t["filtro"] == "none", f"faltas/ abre já liberada ({t})")
        ok(page.is_hidden("#contato"), "faltas/ sem formulário")
        estado = page.evaluate(ESTADO)
        ok(eventos_fbq(estado, "ViewContent") == [["track", "ViewContent", {"content_name": "material_faltas"}]], "ViewContent material_faltas")
        ok(not eventos_fbq(estado, "Lead"), "nenhum Lead sem novo envio")
        ok(not ctx["lambda"], "nenhuma chamada à Lambda")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        page.close()
        cb.close()

    # ---------- checklist ético, outras páginas e Lambda com falha (375px) ----------
    vp = {"width": 375, "height": 812}
    print("--- materiais/etica/ 375px, liberada")
    cb = contexto(b, vp)
    cb.add_init_script("localStorage.setItem('livia_mat_ok', '1')")
    page, ctx = nova_aba(cb)
    page.goto(f"{BASE}/materiais/etica/", wait_until="load")
    caixas = page.query_selector_all(".mat-check input[type=checkbox]")
    ok(len(caixas) == 10, f"10 checkboxes ({len(caixas)})")
    ok(page.is_hidden("#mat-pode"), "frase escondida antes de marcar")
    for c in caixas[:9]:
        c.check()
    ok(page.is_hidden("#mat-pode"), "frase escondida com 9 marcados")
    caixas[9].check()
    ok(page.is_visible("#mat-pode") and page.inner_text("#mat-pode") == PODE, "com os 10 marcados aparece a frase final")
    caixas[3].uncheck()
    ok(page.is_hidden("#mat-pode"), "desmarcar um esconde a frase")
    ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
    page.close()

    for slug in SLUGS:
        page, ctx = nova_aba(cb)
        page.goto(f"{BASE}/materiais/{slug}/", wait_until="load")
        ok("—" not in page.inner_text("body"), f"{slug}: sem travessão")
        sem_rolagem(page, f"{slug} (375px)")
        n = page.evaluate("document.querySelectorAll('.mat-copiar').length")
        esperado = {"mensagens": 8, "faltas": 9, "etica": 0, "reajuste": 1, "posts": 0, "indicacoes": 3}[slug]
        ok(n == esperado, f"{slug}: {esperado} botões Copiar ({n})")
        ok(not ctx["erros_js"], f"{slug}: sem erros de JS {ctx['erros_js']}")
        page.close()
    cb.close()

    print("--- etica/ bloqueada: só os itens 1 e 2 marcáveis")
    cb = contexto(b, vp)
    page, ctx = nova_aba(cb)
    page.goto(f"{BASE}/materiais/etica/", wait_until="load")
    abertos = page.evaluate("[...document.querySelectorAll('.mat-check input')].filter(c => !c.closest('[inert]')).length")
    ok(abertos == 2, f"2 itens abertos sem cadastro ({abertos})")
    page.close()
    cb.close()

    for modo in ("erro", "timeout"):
        print(f"--- materiais/reajuste/ 375px, sem UTM, Lambda {modo}")
        cb = contexto(b, vp)
        page, ctx = nova_aba(cb, lambda_modo=modo)
        page.goto(f"{BASE}/materiais/reajuste/", wait_until="load")
        preenche(page)
        tempo = envia(page)
        ok(tempo is not None and tempo <= 2, f"material abre em {tempo if tempo is None else round(tempo, 2)}s com a Lambda em {modo}")
        ok(len(ctx["lambda"]) == 1, "tentou o cadastro")
        dados = ctx["lambda"][0].post_data_json if ctx["lambda"] else {}
        ok(dados.get("pagina") == "pgMat" and dados.get("sck") == "direto|pgMat" and dados.get("src") == ""
           and dados.get("ferramenta") == "material" and dados.get("resultado") == "reajuste",
           f"sem UTM: sck=direto|pgMat, resultado reajuste ({dados.get('sck')}, {dados.get('resultado')})")
        ok(page.evaluate("localStorage.getItem('livia_mat_ok')") == "1", "localStorage gravado mesmo com falha")
        estado = page.evaluate(ESTADO)
        ok(len(eventos_fbq(estado, "Lead")) == 1, "Lead uma vez")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        fecha(page, ctx)
        cb.close()

    b.close()
servidor.shutdown()

print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
