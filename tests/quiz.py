"""Testa no Chromium headless o quiz "Você está pronta para viver da clínica?" (quiz/), servido por http.server local.

Nada sai para a internet: a chamada à Lambda de cadastro é interceptada com page.route (e, por garantia, o host da
Lambda é mapeado para um endereço inexistente no Chromium); Pixel e GA4 são bloqueados (os comandos ficam na fila do
fbq e no dataLayer, e é isso que o teste confere). Em 390px e 1440px, com UTM:
- capa: título, sem travessão, sem rolagem horizontal, só o PageView ao carregar;
- Começar: QuizInicio (Pixel) e quiz_inicio (GA4) uma vez só; "Pergunta 1 de 5"; Sim e Não com área de toque >= 48px;
- Voltar: volta para a pergunta anterior com a resposta marcada; na 1ª pergunta volta para a capa;
- respostas S,N,S,N,S: "Você respondeu sim para 3 de 5", 3 bolinhas, faixa meio, QuizCompleto com pontos e faixa;
  formulário de contato visível e nenhum Lead antes do envio;
- contato: erros nos 4 campos (nome, e-mail, WhatsApp, consentimento), máscara do WhatsApp, honeypot fora da tela;
- envio: JSON da Lambda (pagina pgQuiz, ferramenta quiz, pontos, resultado, respostas, src, sck, utm_*...), plano
  em <= 2 s com os "Não" primeiro, Lead (Pixel) e generate_lead (GA4) com content_name quiz, uma vez; nenhum dado
  pessoal no dataLayer; links do curso com utm_content V01_quiz_meio; WhatsApp com "sim para 3 de 5"; clique em
  Conhecer o curso dispara ViewContent / view_offer com content_name quiz_para_curso; nenhum InitiateCheckout;
- prints em _catalogo/prints/quiz-{capa,pergunta,resultado,plano}-{mobile,desktop}.png.
Em 390px: as 3 faixas (0, 1, 4 e 5 sim), sem UTM (utm_source=site, utm_medium=quiz, utm_campaign=ccs_quiz,
utm_content=quiz_<faixa>; sck=direto|pgQuiz), link da calculadora no plano quando a 1ª resposta é Não, e Lambda com
erro 500 e sem resposta: o plano aparece mesmo assim, em <= 2 s.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/quiz.py
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
QUERY = "utm_source=meta&utm_medium=paid&utm_campaign=ccs_quiz_frio&utm_content=V01&fbclid=abc123"
SRC = "meta|paid|ccs_quiz_frio|V01"
NOME, EMAIL, WHATS = "Maria Teste", "maria.teste@exemplo.com", "(51) 99999-8888"
TITULOS = {
    "base": "Hora de construir a base.",
    "meio": "Você já começou. Falta organizar.",
    "pronta": "Você está pronta. Agora é crescer com estratégia.",
}
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


def eventos_fbq(estado, nome, tipo="track"):
    return [c for c in estado["fbq"] if c[:2] == [tipo, nome]]


def eventos_gtag(estado, nome):
    return [c for c in estado["dl"] if isinstance(c, list) and c[:2] == ["event", nome]]


def abre(b, vp, lambda_modo="ok", query=QUERY):
    """Abre o quiz com as rotas: site local, Lambda (ok, erro ou sem resposta); o resto é bloqueado."""
    page = b.new_page(viewport=vp)
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
    page.goto(f"{BASE}/quiz/" + ("?" + query if query else ""), wait_until="load")
    return page, ctx


def responde(page, respostas):
    """Começa (se ainda estiver na capa) e responde a sequência de "S"/"N"."""
    if page.is_visible("#comecar"):
        page.click("#comecar")
    for r in respostas:
        page.click(f'#perguntas button[data-resposta="{r}"]')


def preenche(page, nome=NOME, email=EMAIL, whats=WHATS, aceita=True):
    page.fill("#nome", nome)
    page.fill("#email", email)
    page.fill("#whatsapp", whats)
    page.set_checked("#consentimento", aceita)


def envia(page):
    """Envia o contato e devolve o tempo até o plano aparecer (None se não aparecer em 3 s)."""
    t0 = time.monotonic()
    page.click("#contato button[type=submit]")
    try:
        page.wait_for_selector("#plano", state="visible", timeout=3000)
    except Exception:
        return None
    return time.monotonic() - t0


def query_de(href):
    partes = urlsplit(href)
    return partes, parse_qs(partes.query)


def fecha(page, ctx):
    for r in ctx["pendentes"]:
        try:
            r.abort()
        except Exception:
            pass
    page.close()


with sync_playwright() as p:
    b = p.chromium.launch(args=[f"--host-resolver-rules=MAP {LAMBDA_HOST} ~NOTFOUND"])

    for vp in ({"width": 390, "height": 844}, {"width": 1440, "height": 900}):
        tela = "mobile" if vp["width"] < 900 else "desktop"
        print(f"--- quiz {vp['width']}px, com UTM, Lambda ok")
        page, ctx = abre(b, vp)

        # capa
        ok("—" not in page.inner_text("body"), "sem travessão no texto")
        ok(page.inner_text("h1") == "Você está pronta para viver da clínica?" and page.inner_text("h1 em") == "viver da clínica?",
           f"título com \"viver da clínica?\" em itálico ({page.inner_text('h1')})")
        ok(page.title() == "Você está pronta para viver da clínica? | Quiz da Lívia Oliveira", f"title ({page.title()})")
        ok(page.is_visible("#comecar") and page.is_hidden("#perguntas") and page.is_hidden("#resultado"), "capa visível, perguntas e resultado escondidos")
        estado = page.evaluate(ESTADO)
        ok(["init", PIXEL_ID] in estado["fbq"], "Pixel iniciado")
        tracks = [c[1] for c in estado["fbq"] if c[0] in ("track", "trackCustom")]
        ok(tracks == ["PageView"], f"ao carregar só o PageView ({tracks})")
        larg = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        ok(larg[0] <= larg[1], f"capa sem rolagem horizontal ({larg[0]} <= {larg[1]})")
        page.wait_for_timeout(300)
        page.screenshot(path=str(PRINTS / f"quiz-capa-{tela}.png"), full_page=True)

        # começar
        page.click("#comecar")
        ok(page.is_hidden("#capa") and page.is_visible("#perguntas"), "Começar mostra as perguntas")
        ok(page.inner_text("#quiz-passo") == "Pergunta 1 de 5", f"progresso ({page.inner_text('#quiz-passo')})")
        ok(page.evaluate("document.activeElement.id") == "quiz-pergunta", "foco na pergunta")
        caixas = page.evaluate("[...document.querySelectorAll('.quiz-op')].map(b => { const r = b.getBoundingClientRect(); return [r.width, r.height, r.bottom]; })")
        ok(len(caixas) == 2 and all(w >= 48 and h >= 48 for w, h, _ in caixas), f"Sim e Não com área de toque >= 48px ({[[round(w), round(h)] for w, h, _ in caixas]})")
        ok(all(bottom <= vp["height"] for _, _, bottom in caixas), "Sim e Não visíveis sem rolar")
        ok([page.inner_text(".quiz-op >> nth=0"), page.inner_text(".quiz-op >> nth=1")] == ["Sim", "Não"], "botões Sim e Não")
        voltar = page.evaluate("(() => { const r = document.getElementById('quiz-voltar').getBoundingClientRect(); return r.height; })()")
        ok(voltar >= 44, f"Voltar com área de toque ({voltar:.0f}px)")
        larg = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        ok(larg[0] <= larg[1], f"pergunta sem rolagem horizontal ({larg[0]} <= {larg[1]})")
        page.screenshot(path=str(PRINTS / f"quiz-pergunta-{tela}.png"), full_page=True)

        # Voltar
        page.click('#perguntas button[data-resposta="S"]')
        ok(page.inner_text("#quiz-passo") == "Pergunta 2 de 5" and "contrato terapêutico" in page.inner_text("#quiz-pergunta"),
           "Sim avança sozinho para a pergunta 2")
        page.click("#quiz-voltar")
        ok(page.inner_text("#quiz-passo") == "Pergunta 1 de 5" and "quanto custa cada sessão" in page.inner_text("#quiz-pergunta"),
           "Voltar leva à pergunta 1")
        ok(page.evaluate("document.querySelector('.quiz-op[data-resposta=S]').classList.contains('is-escolhida')"), "resposta anterior marcada")
        page.click("#quiz-voltar")
        ok(page.is_visible("#capa") and page.is_hidden("#perguntas"), "Voltar na 1ª pergunta leva à capa")
        page.click("#comecar")
        estado = page.evaluate(ESTADO)
        inicio = {"content_name": "quiz"}
        ok(eventos_fbq(estado, "QuizInicio", "trackCustom") == [["trackCustom", "QuizInicio", inicio]], "QuizInicio no Pixel, uma vez")
        ok(eventos_gtag(estado, "quiz_inicio") == [["event", "quiz_inicio", inicio]], "quiz_inicio no GA4, uma vez")

        # respostas mistas: S,N,S,N,S = 3 sim (meio)
        responde(page, "SNSNS")
        ok(page.is_hidden("#perguntas") and page.is_visible("#resultado"), "resultado aparece depois da 5ª resposta")
        ok(page.inner_text("#quiz-pontos") == "Você respondeu sim para 3 de 5", f"placar ({page.inner_text('#quiz-pontos')})")
        ok(page.evaluate("document.querySelectorAll('#quiz-bolinhas i.on').length") == 3, "3 bolinhas preenchidas")
        ok(page.inner_text("#resultado-titulo") == TITULOS["meio"], f"faixa meio ({page.inner_text('#resultado-titulo')})")
        ok(page.get_attribute("#resultado .wrap > div", "aria-live") == "polite", "resultado com aria-live")
        ok(page.is_visible("#contato") and page.is_hidden("#plano"), "formulário visível e plano escondido antes do envio")
        estado = page.evaluate(ESTADO)
        completo = {"content_name": "quiz", "pontos": 3, "faixa": "meio"}
        ok(eventos_fbq(estado, "QuizCompleto", "trackCustom") == [["trackCustom", "QuizCompleto", completo]], "QuizCompleto no Pixel com pontos e faixa")
        ok(eventos_gtag(estado, "quiz_completo") == [["event", "quiz_completo", completo]], "quiz_completo no GA4")
        ok(not eventos_fbq(estado, "Lead") and not eventos_gtag(estado, "generate_lead"), "nenhum Lead antes do envio")
        partes, q = query_de(page.get_attribute("#curso-direto", "href"))
        ok(partes.path == "/curso/b/" and q.get("utm_content") == ["V01_quiz_meio"] and q.get("utm_source") == ["meta"]
           and q.get("utm_campaign") == ["ccs_quiz_frio"] and all(len(v) == 1 for v in q.values()),
           f"\"Prefiro ver o curso agora\" com UTMs e utm_content V01_quiz_meio ({q})")
        page.wait_for_timeout(400)
        page.screenshot(path=str(PRINTS / f"quiz-resultado-{tela}.png"), full_page=True)

        # validação
        hp = page.evaluate("""() => { const e = document.getElementById('empresa'); const r = e.getBoundingClientRect();
          return {valor: e.value, tab: e.getAttribute('tabindex'), auto: e.getAttribute('autocomplete'), fora: r.right <= 0 || r.width <= 1}; }""")
        ok(hp == {"valor": "", "tab": "-1", "auto": "off", "fora": True}, f"honeypot vazio, fora da tela ({hp})")
        ok(page.get_attribute('#contato a[href*="privacidade/"]', "href") is not None, "link para a Política de privacidade no consentimento")
        page.click("#contato button[type=submit]")
        page.wait_for_timeout(200)
        erros = {n: page.inner_text(f'#contato [data-error-for="{n}"]') for n in ("nome", "email", "whatsapp", "consentimento")}
        ok(all(erros.values()), f"erros nos 4 campos ({erros})")
        ok(page.evaluate("document.activeElement.id") == "nome", "foco no primeiro campo com erro")
        preenche(page, "M", "maria@", "51 9999", aceita=False)
        page.click("#contato button[type=submit]")
        page.wait_for_timeout(200)
        ok(all(page.inner_text(f'#contato [data-error-for="{n}"]') for n in ("nome", "email", "whatsapp", "consentimento")),
           "erros com nome de 1 letra, e-mail incompleto, WhatsApp curto e sem consentimento")
        ok(page.input_value("#whatsapp") == "(51) 9999", f"máscara do WhatsApp ({page.input_value('#whatsapp')})")
        ok(not ctx["lambda"] and page.is_hidden("#plano"), "envio inválido não cadastra nem mostra o plano")
        preenche(page)
        ok(page.inner_text('#contato [data-error-for="consentimento"]') == "", "erro do consentimento some ao marcar")

        # envio certo
        tempo = envia(page)
        ok(tempo is not None and tempo <= 2, f"plano aparece em {tempo if tempo is None else round(tempo, 2)}s")
        ok(len(ctx["lambda"]) == 1, f"uma chamada à Lambda ({len(ctx['lambda'])})")
        if ctx["lambda"]:
            req = ctx["lambda"][0]
            ok(req.method == "POST" and "application/json" in (req.headers.get("content-type") or ""), "POST application/json")
            esperado = {
                "nome": NOME, "email": EMAIL, "whatsapp": "51999998888", "pagina": "pgQuiz", "src": SRC, "sck": f"{SRC}|pgQuiz",
                "utm_source": "meta", "utm_medium": "paid", "utm_campaign": "ccs_quiz_frio", "utm_content": "V01", "utm_term": "",
                "url": f"{BASE}/quiz/?{QUERY}", "consentimento": "sim", "fbp": "", "fbc": "", "empresa": "",
                "ferramenta": "quiz", "pontos": "3", "resultado": "meio", "respostas": "S,N,S,N,S",
            }
            dados = req.post_data_json
            ok(dados == esperado, f"JSON do cadastro {dados}")
        ok(page.is_hidden("#contato") and page.is_hidden("#quiz-direto"), "formulário some depois do envio")
        itens = page.evaluate("[...document.querySelectorAll('#plano-itens li')].map(li => [li.querySelector('.quiz-item__tipo').textContent, li.querySelector('.quiz-item__pergunta').textContent, li.querySelector('.quiz-item__texto').textContent])")
        tipos = [i[0] for i in itens]
        ok(tipos == ["O que fazer", "O que fazer", "Ponto forte", "Ponto forte", "Ponto forte"], f"plano com os \"Não\" primeiro ({tipos})")
        ok("contrato terapêutico" in itens[0][1] and "Contrato, recibo e regra de faltas" in itens[0][2], "1º card: pergunta 2 (Não)")
        ok("mais de um caminho" in itens[1][1] and "Depender de um só canal" in itens[1][2], "2º card: pergunta 4 (Não)")
        ok(itens[2][2] == "Ponto forte: você já conhece os seus números.", f"3º card: ponto forte da pergunta 1 ({itens[2][2]})")
        cursos = page.evaluate("[...document.querySelectorAll('#plano-itens .quiz-item__curso')].map(p => p.textContent)")
        ok(cursos == ["No curso: Módulos 2 e 3, gestão e comunicação assertiva.", "No curso: Módulos 6 e 9, Digital como vitrine e Captação offline."],
           f"\"No curso\" só nos cards de O que fazer ({cursos})")
        ok("12x de R$ 71,67 sem juros ou R$ 860 à vista" in page.inner_text("#plano") and "7 dias de garantia" in page.inner_text("#plano"), "preço e garantia no convite")

        estado = page.evaluate(ESTADO)
        lead = {"content_name": "quiz", "content_category": "meio"}
        ok(eventos_fbq(estado, "Lead") == [["track", "Lead", lead]], "Lead no Pixel, uma vez")
        ok(eventos_gtag(estado, "generate_lead") == [["event", "generate_lead", lead]], "generate_lead no GA4, uma vez")
        ok(["init", PIXEL_ID, {"em": EMAIL, "ph": "5551999998888", "fn": "maria"}] in estado["fbq"], "advanced matching (em, ph, fn) no Pixel")
        texto_dl = json.dumps(estado["dl"], ensure_ascii=False).lower()
        ok(not any(x in texto_dl for x in ("maria", "exemplo.com", "99999")), "nenhum dado pessoal no dataLayer/GA4")

        partes, q = query_de(page.get_attribute("#conhecer-curso", "href"))
        ok(partes.path == "/curso/b/", f"Conhecer o curso vai para curso/b/ ({partes.path})")
        ok(q.get("utm_source") == ["meta"] and q.get("utm_medium") == ["paid"] and q.get("utm_campaign") == ["ccs_quiz_frio"]
           and q.get("utm_content") == ["V01_quiz_meio"] and all(len(v) == 1 for v in q.values()),
           f"Conhecer o curso com utm_content V01_quiz_meio, sem duplicar ({q})")
        wa = page.get_attribute("#quiz-wa", "href")
        ok(wa.startswith("https://wa.me/5551992597638?text=")
           and unquote(wa.split("text=", 1)[1]) == "Oi! Fiz o quiz da Lívia e respondi sim para 3 de 5. Quero saber mais sobre o Carreira com Sentido.",
           f"WhatsApp da Thaís com a mensagem do quiz ({unquote(wa)})")
        larg = page.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        ok(larg[0] <= larg[1], f"plano sem rolagem horizontal ({larg[0]} <= {larg[1]})")
        page.wait_for_timeout(600)
        page.screenshot(path=str(PRINTS / f"quiz-plano-{tela}.png"), full_page=True)

        page.evaluate("document.addEventListener('click', e => e.preventDefault())")
        page.click("#conhecer-curso")
        estado = page.evaluate(ESTADO)
        oferta = {"content_name": "quiz_para_curso"}
        ok(eventos_fbq(estado, "ViewContent") == [["track", "ViewContent", oferta]], "ViewContent no clique do curso")
        ok(eventos_gtag(estado, "view_offer") == [["event", "view_offer", oferta]], "view_offer no GA4")
        ok(not eventos_fbq(estado, "InitiateCheckout") and not eventos_gtag(estado, "begin_checkout"), "nenhum InitiateCheckout / begin_checkout")
        ok(len(eventos_fbq(estado, "Lead")) == 1, "continua um Lead só")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        fecha(page, ctx)

    # as 3 faixas, sem UTM
    for respostas, pontos, faixa in (("NNNNN", 0, "base"), ("NNSNN", 1, "base"), ("SSSSN", 4, "pronta"), ("SSSSS", 5, "pronta")):
        print(f"--- quiz 390px, sem UTM, {respostas} ({pontos} sim)")
        page, ctx = abre(b, {"width": 390, "height": 844}, query="")
        responde(page, respostas)
        ok(page.inner_text("#quiz-pontos") == f"Você respondeu sim para {pontos} de 5", f"placar {pontos} de 5")
        ok(page.evaluate("document.querySelectorAll('#quiz-bolinhas i.on').length") == pontos, f"{pontos} bolinhas preenchidas")
        ok(page.inner_text("#resultado-titulo") == TITULOS[faixa], f"faixa {faixa} ({page.inner_text('#resultado-titulo')})")
        preenche(page)
        tempo = envia(page)
        ok(tempo is not None and tempo <= 2, "plano aparece")
        dados = ctx["lambda"][0].post_data_json if ctx["lambda"] else {}
        ok(dados.get("pontos") == str(pontos) and dados.get("resultado") == faixa and dados.get("respostas") == ",".join(respostas),
           f"cadastro com pontos, resultado e respostas ({dados.get('pontos')}, {dados.get('resultado')}, {dados.get('respostas')})")
        ok(dados.get("pagina") == "pgQuiz" and dados.get("sck") == "direto|pgQuiz" and dados.get("src") == "", f"sem UTM: sck=direto|pgQuiz ({dados.get('sck')})")
        _, q = query_de(page.get_attribute("#conhecer-curso", "href"))
        ok(q == {"utm_source": ["site"], "utm_medium": ["quiz"], "utm_campaign": ["ccs_quiz"], "utm_content": [f"quiz_{faixa}"]},
           f"sem UTM: link do curso com utm de site/quiz ({q})")
        tipos = page.evaluate("[...document.querySelectorAll('#plano-itens .quiz-item__tipo')].map(p => p.textContent)")
        ok(tipos == ["O que fazer"] * (5 - pontos) + ["Ponto forte"] * pontos, f"{5 - pontos} O que fazer e {pontos} Ponto forte")
        calc = page.query_selector('#plano-itens a[href*="/calculadora/"]')
        if respostas[0] == "N":
            ok(calc is not None and "calculadora do valor da sessão" in calc.inner_text(), "1ª resposta Não: link da calculadora no plano")
        else:
            ok(calc is None, "1ª resposta Sim: sem link da calculadora")
        estado = page.evaluate(ESTADO)
        ok(eventos_fbq(estado, "QuizCompleto", "trackCustom") == [["trackCustom", "QuizCompleto", {"content_name": "quiz", "pontos": pontos, "faixa": faixa}]],
           "QuizCompleto com pontos e faixa")
        ok(not eventos_fbq(estado, "InitiateCheckout"), "nenhum InitiateCheckout")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        fecha(page, ctx)

    # link da calculadora mantém as UTMs
    print("--- quiz 390px, com UTM, link da calculadora")
    page, ctx = abre(b, {"width": 390, "height": 844})
    responde(page, "NNNNN")
    preenche(page)
    envia(page)
    partes, q = query_de(page.get_attribute('#plano-itens a[href*="/calculadora/"]', "href"))
    ok(partes.path == "/calculadora/" and q.get("utm_source") == ["meta"] and q.get("utm_content") == ["V01"], f"calculadora com as UTMs da visita ({q})")
    fecha(page, ctx)

    # Lambda com erro ou sem resposta: o plano aparece mesmo assim
    for modo in ("erro", "timeout"):
        print(f"--- quiz 390px, Lambda {modo}")
        page, ctx = abre(b, {"width": 390, "height": 844}, lambda_modo=modo)
        responde(page, "SNSNS")
        preenche(page)
        tempo = envia(page)
        ok(tempo is not None and tempo <= 2, f"plano aparece em {tempo if tempo is None else round(tempo, 2)}s com a Lambda em {modo}")
        ok(len(ctx["lambda"]) == 1, "tentou o cadastro")
        estado = page.evaluate(ESTADO)
        ok(len(eventos_fbq(estado, "Lead")) == 1, "Lead uma vez")
        ok(not ctx["erros_js"], f"sem erros de JS {ctx['erros_js']}")
        fecha(page, ctx)

    b.close()
servidor.shutdown()

print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
