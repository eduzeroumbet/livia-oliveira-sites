"""Verificações simples do site estático.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/check.py
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "curso/index.html", "curso/b/index.html", "curso/versao-b/index.html", "curso/inscricao/index.html", "consultoria/index.html", "terapia/index.html", "terapia/b/index.html", "privacidade/index.html", "termos/index.html", "calculadora/index.html", "quiz/index.html"]
# materiais gratuitos (isca dos anúncios de Lead): hub + 6 páginas com site.js data-pagina="pgMat" e materiais/material.js
MATERIAIS = ["mensagens", "faltas", "etica", "reajuste", "posts", "indicacoes"]
MATERIAIS_HUB = "materiais/index.html"
MATERIAIS_PAGINAS = [f"materiais/{m}/index.html" for m in MATERIAIS]
PAGES += [MATERIAIS_HUB, *MATERIAIS_PAGINAS]
# Black Friday 2026 (assets/js/bf.js + assets/css/bf.css): página de venda black-friday/ (pgBF) e atalho black/
BLACK_FRIDAY = "black-friday/index.html"
BLACK_ATALHO = "black/index.html"
# versões novas da página da Black Friday (anúncios): B "conta da clínica" e C "direto ao ponto", com noindex e fora do sitemap;
# as três usam pgBF e se diferenciam pelo data-versao do site.js (bf_a, bf_b, bf_c)
BF_VERSOES = {"black-friday/b/index.html": ("bf_b", "bf_quad_valor.jpg"), "black-friday/c/index.html": ("bf_c", "bf_quad_oferta.jpg")}
PAGES += [BLACK_FRIDAY, *BF_VERSOES]
BF_CONFIG = 'window.BF = { fim: "2026-11-30T23:59:59-03:00", oferta: "qu4x7j2d", preco: "499,99", parcela: "41,67", de: "860" };'
# páginas com Black Friday: bf.js no <head> (sem defer) e bf.css; as com faixa no topo levam a black-friday/
BF_PAGINAS = ["index.html", "curso/index.html", "curso/b/index.html", "curso/versao-b/index.html", "curso/inscricao/index.html",
              "calculadora/index.html", "quiz/index.html", MATERIAIS_HUB, *MATERIAIS_PAGINAS, BLACK_FRIDAY, *BF_VERSOES]
BF_FAIXA = [p for p in BF_PAGINAS if p not in ("curso/inscricao/index.html", BLACK_FRIDAY, *BF_VERSOES)]
# links de materiais, quiz e calculadora para a página da Black Friday (utm_medium = página de origem)
BF_UTM = {MATERIAIS_HUB: "materiais", "quiz/index.html": "quiz", "calculadora/index.html": "calculadora",
          **{f"materiais/{m}/index.html": f"materiais_{m}" for m in MATERIAIS}}
# terapia: nada de Black Friday
SEM_BF = ["terapia/index.html", "terapia/b/index.html"]
# política de privacidade (URL do app da Meta e dos anúncios) e termos de uso: link no rodapé de todas as páginas e no sitemap
PRIVACIDADE = "privacidade/index.html"
TERMOS = "termos/index.html"
LEGAIS = {PRIVACIDADE: "Política de privacidade", TERMOS: "Termos de uso"}
# data de "Última atualização" de cada página legal
ATUALIZACAO = {PRIVACIDADE: "30 de outubro de 2026", TERMOS: "20 de outubro de 2026"}
EXTERNAL = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:", "#")

ENTRIES = {
    "consultoria/index.html": ["entry.488014542", "entry.2112078615"],
    "terapia/b/index.html": [
        "entry.1886022350",
        "entry.1192162037",
        "entry.1202505729",
        "entry.1222954892",
        "entry.1892587682",
    ],
}
ENTRIES["terapia/index.html"] = ENTRIES["terapia/b/index.html"]
GFORM_TERAPIA = "https://docs.google.com/forms/d/e/1FAIpQLSfBmYNmVucSkEQvBLERoWCcRs_zaT0MN2P944cHZapHvCwfUA/formResponse"
# links orgânicos para o curso: todos vão para curso/b/ (a versão A, curso/, fica só para os anúncios)
CURSO_ORGANICO = {
    "index.html": "curso/b/",
    "consultoria/index.html": "../curso/b/",
    "terapia/index.html": "../curso/b/",
    "privacidade/index.html": "../curso/b/",
    "termos/index.html": "../curso/b/",
    "calculadora/index.html": "../curso/b/",
    "quiz/index.html": "../curso/b/",
}
CHECKOUT = "https://pay.hotmart.com/M100028858P?off=n2h6k72h&checkoutMode=10"
# botões de compra (class="checkout") das 3 versões do curso: vão para a pré-página de inscrição com o pg da versão
INSCRICAO = "curso/inscricao/index.html"
CURSO_INSCRICAO = {
    "curso/index.html": "inscricao/?pg=pgA",
    "curso/b/index.html": "../inscricao/?pg=pgB",
    "curso/versao-b/index.html": "../inscricao/?pg=pgC",
    BLACK_FRIDAY: "../curso/inscricao/?pg=pgBF",
    **{rel: "../../curso/inscricao/?pg=pgBF" for rel in BF_VERSOES},
}
LAMBDA_CADASTRO = "https://nwmxltflulqvcxu7bdplodmyjm0yweuc.lambda-url.sa-east-1.on.aws/"
# as 3 versões do curso carregam o site.js (Pixel, GA4, src/sck) com o sufixo da página no data-pagina
CURSO_PAGINA = {
    "curso/index.html": ("../assets/js/site.js", "pgA"),
    "curso/b/index.html": ("../../assets/js/site.js", "pgB"),
    "curso/versao-b/index.html": ("../../assets/js/site.js", "pgC"),
}
PIXEL_ID = "1197036460960933"
GA4_ID = "G-XH74VZSNZ2"
# terapia (conteúdo de saúde): site.js com data-sem-rastreamento, sem Pixel, GA4 nem GTM
SEM_RASTREAMENTO = {
    "terapia/index.html": "../assets/js/site.js",
    "terapia/b/index.html": "../../assets/js/site.js",
}
# calculadora (isca dos anúncios): site.js com data-pagina="pgCalc", Lead ao mostrar o resultado, sem checkout
CALCULADORA = "calculadora/index.html"
# quiz (isca dos anúncios de Lead): site.js com data-pagina="pgQuiz", Lead só no envio do contato, sem checkout
QUIZ = "quiz/index.html"
TAGS_RASTREAMENTO = ("fbq(", "gtag(", "googletagmanager.com", "connect.facebook.net", PIXEL_ID, GA4_ID)
HOTLINK = "r2" + ".dev"  # storage do Scrolltide; montado em partes para o próprio check não conter o literal
DOMINIO = "liviaoliveira.me"
URL_ANTIGA = "github.io" + "/livia-oliveira-sites"  # endereço antigo; em partes pelo mesmo motivo
EXTRAS = (
    "assets/css/site.css",
    "assets/css/captacao.css",
    "assets/js/site.js",
    "curso/style.css",
    "curso/script.js",
    "curso/versao-b/hero-fios.css",
    "curso/versao-b/hero-fios.js",
    "terapia/style.css",
    "terapia/script.js",
    "calculadora/script.js",
    "curso/inscricao/script.js",
    "quiz/script.js",
    "materiais/style.css",
    "materiais/material.js",
    "assets/js/bf.js",
    "assets/css/bf.css",
)
# favicons e manifest usam caminho absoluto (site na raiz do domínio)
REL_ABSOLUTO = {"icon", "apple-touch-icon", "manifest"}
MANIFEST = "site.webmanifest"
# WhatsApp: a Lia (assistente da equipe) atende as psicólogas; o da Thaís só em links que dizem "Thaís", na home, na terapia e nas páginas legais
WHATSAPP_LIA = "5511910607651"
WHATSAPP_THAIS = "5551992597638"
WA_LIA = ("curso/", "calculadora/", "quiz/", "materiais/", "consultoria/", "black-friday/")
WA_THAIS = ("terapia/", "termos/", "privacidade/")

erros = []


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.checkouts = []  # href dos <a class="checkout">

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        # data-src-720 / data-src-1280: fontes do vídeo do hero que o JS escolhe pela largura
        for attr in ("src", "href", "poster", "data-src-720", "data-src-1280"):
            if a.get(attr):
                self.refs.append((tag, attr, a[attr], a.get("rel") or ""))
        if tag == "a" and "checkout" in (a.get("class") or "").split():
            self.checkouts.append(a.get("href"))


class WaLinks(HTMLParser):
    """Links wa.me de uma página, com o texto de cada um."""
    def __init__(self):
        super().__init__()
        self.links = []  # [href, texto]
        self.atual = None

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href") or ""
        if tag == "a" and "wa.me/" in href:
            self.atual = [href, ""]
            self.links.append(self.atual)

    def handle_endtag(self, tag):
        if tag == "a":
            self.atual = None

    def handle_data(self, data):
        if self.atual is not None:
            self.atual[1] += data


def check_whatsapp():
    for p in sorted(ROOT.glob("**/index.html")):
        if ".git" in p.parts:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel.startswith(WA_LIA):
            esperado, regra = WHATSAPP_LIA, "páginas de psicólogas vão para a Lia, exceto links que dizem Thaís"
        elif rel == "index.html" or rel.startswith(WA_THAIS):
            esperado, regra = WHATSAPP_THAIS, "home, terapia e páginas legais vão para a Thaís"
        else:
            continue
        parser = WaLinks()
        parser.feed(p.read_text(encoding="utf-8"))
        for href, texto in parser.links:
            texto = " ".join(texto.split())
            numero = re.match(r"https://wa\.me/(\d+)", href)
            numero = numero.group(1) if numero else href
            if esperado == WHATSAPP_LIA and "Thaís" in texto:
                if numero != WHATSAPP_THAIS:
                    erros.append(f"{rel}: link \"{texto}\" diz Thaís e deve ir para {WHATSAPP_THAIS} ({href})")
            elif numero != esperado:
                erros.append(f"{rel}: wa.me deve ir para {esperado} ({regra}): \"{texto}\" {href}")
    site = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
    for trecho in (f'WHATSAPP_LIA = "{WHATSAPP_LIA}"', f'WHATSAPP_THAIS = "{WHATSAPP_THAIS}"'):
        if trecho not in site:
            erros.append(f"assets/js/site.js: sem {trecho}")
    if f'WHATSAPP = "{WHATSAPP_LIA}"' not in (ROOT / "quiz/script.js").read_text(encoding="utf-8"):
        erros.append(f"quiz/script.js: WHATSAPP deve ser {WHATSAPP_LIA} (Lia)")


def check_page(rel):
    path = ROOT / rel
    if not path.exists():
        erros.append(f"{rel}: página não existe")
        return
    html = path.read_text(encoding="utf-8")

    if "—" in html:
        erros.append(f"{rel}: contém travessão (—)")
    if HOTLINK in html:
        erros.append(f"{rel}: referencia o storage do Scrolltide ({HOTLINK}); sirva o arquivo localmente")
    if URL_ANTIGA in html:
        erros.append(f"{rel}: usa o endereço antigo ({URL_ANTIGA}); use https://{DOMINIO}/")
    if 'location.protocol==="http:"' not in html:
        erros.append(f"{rel}: sem o script que força HTTPS no domínio próprio")

    parser = Refs()
    parser.feed(html)
    for tag, attr, value, link_rel in parser.refs:
        absoluto = tag == "link" and link_rel in REL_ABSOLUTO and value.startswith("/") and not value.startswith("//")
        if value.startswith("/") and not absoluto:
            erros.append(f"{rel}: <{tag} {attr}=\"{value}\"> começa com \"/\" (use caminho relativo)")
            continue
        if value.startswith(EXTERNAL):
            continue
        local = unquote(urlsplit(value).path)
        if not local:
            continue
        target = (ROOT / local.lstrip("/")).resolve() if absoluto else (path.parent / local).resolve()
        if local.endswith("/") or target.is_dir():
            target = target / "index.html"
        if not target.exists():
            erros.append(f"{rel}: <{tag} {attr}=\"{value}\"> aponta para arquivo inexistente")

    # links "Política de privacidade" e "Termos de uso" dentro do <footer> (na bio, no rodapé .bio-footer)
    rodape = re.search(r"<footer\b.*?</footer>|<p class=\"bio-footer\">.*?</p>", html, re.S)
    links_rodape = Refs()
    links_rodape.feed(rodape.group(0) if rodape else "")
    for legal, nome in LEGAIS.items():
        if not any(
            t == "a" and a == "href" and not v.startswith(EXTERNAL)
            and (path.parent / unquote(urlsplit(v).path)).resolve() == (ROOT / legal).parent.resolve()
            for t, a, v, _ in links_rodape.refs
        ):
            erros.append(f"{rel}: rodapé sem o link \"{nome}\" para {legal}")

    if rel in LEGAIS:
        pasta = rel.split("/")[0]
        if f'<link rel="canonical" href="https://liviaoliveira.me/{pasta}/">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/{pasta}/")
        if not re.search(r'<script src="\.\./assets/js/site\.js(\?v=\d+)?"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../assets/js/site.js\"> (carrega o rastreamento normalmente)")
        for trecho in ("CRP 07/18713", "Lívia Carvalho de Oliveira", "(51) 99259-7638", "@liviaoliveira.psicologa", ATUALIZACAO[rel]):
            if trecho not in html:
                erros.append(f"{rel}: sem \"{trecho}\"")
        if f"https://liviaoliveira.me/{pasta}/" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não está no sitemap.xml")
    if rel == PRIVACIDADE and 'href="../termos/"' not in html.split("<footer", 1)[0]:
        erros.append(f"{rel}: sem o link para os Termos de uso no texto da política")
    if rel == PRIVACIDADE:
        for trecho in ("Inscrição no curso Carreira com Sentido", "Amazon Web Services", "região São Paulo", "até 12 meses"):
            if trecho not in html:
                erros.append(f"{rel}: sem \"{trecho}\" (dados da pré-página de inscrição do curso)")
        if "materiais gratuitos" not in html:
            erros.append(f"{rel}: sem \"materiais gratuitos\" (ponto de coleta, junto do quiz e da calculadora)")

    for entry in ENTRIES.get(rel, []):
        if f'data-entry="{entry}"' not in html:
            erros.append(f"{rel}: campo {entry} do Google Form ausente")

    if rel in CURSO_INSCRICAO:
        destino = CURSO_INSCRICAO[rel]
        if not parser.checkouts:
            erros.append(f"{rel}: nenhum botão class=\"checkout\" (deve apontar para {destino})")
        for href in parser.checkouts:
            if href != destino:
                erros.append(f"{rel}: botão class=\"checkout\" com href=\"{href}\" (deve ser {destino})")
        if "pay.hotmart.com" in html:
            erros.append(f"{rel}: link para pay.hotmart.com; os botões vão para a pré-página ({destino})")
        # "Quero minha vaga" que só rola até a #oferta não é botão de compra
        compra = re.findall(r'<a\b[^>]*>(?:(?!</a>).)*Quero (?:minha vaga|me inscrever)', html, re.S)
        sem_classe = [a for a in compra if 'href="#' not in a.split(">", 1)[0]
                      and not re.search(r'class="[^"]*\bcheckout\b', a.split(">", 1)[0])]
        if sem_classe:
            erros.append(f"{rel}: {len(sem_classe)} botão(ões) de compra sem class=\"checkout\"")

    if rel == INSCRICAO:
        if '<meta name="robots" content="noindex">' not in html:
            erros.append(f"{rel}: sem <meta name=\"robots\" content=\"noindex\">")
        if '<link rel="canonical" href="https://liviaoliveira.me/curso/">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/curso/")
        if "inscricao" in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não deve estar no sitemap.xml")
        if not re.search(r'<script src="\.\./\.\./assets/js/site\.js(\?v=\d+)?" data-pagina="pgInsc"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../../assets/js/site.js\" data-pagina=\"pgInsc\">")
        if not re.search(r'<script src="script\.js(\?v=\d+)?"></script>', html):
            erros.append(f"{rel}: sem <script src=\"script.js\"> (envio do formulário)")
        for trecho in ('autocomplete="name"', 'type="email"', 'autocomplete="email"', 'inputmode="email"', 'type="tel"',
                       'data-mask="phone"', 'autocomplete="tel"', 'inputmode="tel"', 'placeholder="(51) 99999-9999"',
                       'name="empresa"', 'tabindex="-1"', "Continuar para o pagamento", 'href="../../privacidade/"',
                       "12x de R$ 71,67 sem juros", "R$ 860 à vista", "https://wa.me/5511910607651?text="):
            if trecho not in html:
                erros.append(f"{rel}: sem {trecho}")
        for proibido in ("pay.hotmart.com", "sticky-bar", "garantia", "depoimento", "<nav"):
            if proibido in html.lower():
                erros.append(f"{rel}: contém {proibido!r} (pré-página sem checkout fixo, barra, menu, garantia ou depoimentos)")
        script = (ROOT / "curso/inscricao/script.js").read_text(encoding="utf-8")
        for trecho in (f'CADASTRO_URL = "{LAMBDA_CADASTRO}"', f'CHECKOUT_URL = "{CHECKOUT}"', "keepalive: true",
                       '"begin_checkout"', '"cadastro_checkout"', "siteIdentify"):
            if trecho not in script:
                erros.append(f"curso/inscricao/script.js: sem {trecho}")
        if "generate_lead" in script or '"Lead"' in script or "'Lead'" in script:
            erros.append("curso/inscricao/script.js: não pode disparar Lead (reservado à calculadora)")

    if rel in CURSO_PAGINA:
        script, pagina = CURSO_PAGINA[rel]
        if not re.search(rf'<script src="{re.escape(script)}(\?v=\d+)?" data-pagina="{pagina}"', html):
            erros.append(f"{rel}: sem <script src=\"{script}\" data-pagina=\"{pagina}\"> (rastreamento do curso)")

    if rel in SEM_RASTREAMENTO:
        script = SEM_RASTREAMENTO[rel]
        if not re.search(rf'<script src="{re.escape(script)}(\?v=\d+)?" data-sem-rastreamento>', html):
            erros.append(f"{rel}: sem <script src=\"{script}\" data-sem-rastreamento> (terapia não carrega Pixel/GA4)")
        for tag in TAGS_RASTREAMENTO:
            if tag in html:
                erros.append(f"{rel}: contém {tag!r} (terapia não carrega Pixel/GA4/GTM)")
    elif "data-sem-rastreamento" in html:
        erros.append(f"{rel}: data-sem-rastreamento só nas páginas de terapia")

    if rel == CALCULADORA:
        if not re.search(r'<script src="\.\./assets/js/site\.js(\?v=\d+)?" data-pagina="pgCalc"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../assets/js/site.js\" data-pagina=\"pgCalc\">")
        if '<link rel="canonical" href="https://liviaoliveira.me/calculadora/">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/calculadora/")
        if "https://liviaoliveira.me/calculadora/" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não está no sitemap.xml")
        if "pay.hotmart.com" in html or 'id="oferta"' in html:
            erros.append(f"{rel}: sem checkout nem #oferta (nada de InitiateCheckout nem view_offer automático)")
        script = (ROOT / "calculadora/script.js").read_text(encoding="utf-8")
        for trecho in ('"generate_lead"', '"calculadora_sessao"', '"view_offer"', '"calculadora_para_curso"'):
            if trecho not in script:
                erros.append(f"calculadora/script.js: sem {trecho}")
        if "begin_checkout" in script:
            erros.append("calculadora/script.js: não pode disparar begin_checkout (InitiateCheckout)")
        if script.count('"generate_lead"') != 1 or '"contato_calculadora"' not in script:
            erros.append("calculadora/script.js: o contato dispara contato_calculadora; o único generate_lead é o do cálculo")
        for trecho in ('id="contato"', 'name="consentimento"', 'name="empresa"', 'data-mask="phone"', 'href="../quiz/"'):
            if trecho not in html:
                erros.append(f"{rel}: sem {trecho} (contato opcional e link do quiz)")
    if rel == QUIZ:
        if not re.search(r'<script src="\.\./assets/js/site\.js(\?v=\d+)?" data-pagina="pgQuiz"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../assets/js/site.js\" data-pagina=\"pgQuiz\">")
        if not re.search(r'<script src="script\.js(\?v=\d+)?"></script>', html):
            erros.append(f"{rel}: sem <script src=\"script.js\"> (perguntas, contato e plano)")
        if '<link rel="canonical" href="https://liviaoliveira.me/quiz/">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/quiz/")
        if "noindex" in html:
            erros.append(f"{rel}: o quiz é indexável (sem noindex)")
        if "https://liviaoliveira.me/quiz/" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não está no sitemap.xml")
        if "pay.hotmart.com" in html or 'id="oferta"' in html or "checkout" in html:
            erros.append(f"{rel}: sem checkout nem #oferta (nada de InitiateCheckout nem view_offer automático)")
        for trecho in ('name="consentimento"', 'name="empresa"', 'tabindex="-1"', 'data-mask="phone"', 'href="../privacidade/"',
                       "assets/img/og-quiz.jpg", "12x de R$ 71,67 sem juros ou R$ 860 à vista", "7 dias de garantia", 'aria-live="polite"'):
            if trecho not in html:
                erros.append(f"{rel}: sem {trecho}")
        script = (ROOT / "quiz/script.js").read_text(encoding="utf-8")
        for trecho in ('"quiz_inicio"', '"quiz_completo"', '"generate_lead"', '"view_offer"', '"quiz_para_curso"', 'ferramenta: "quiz"'):
            if trecho not in script:
                erros.append(f"quiz/script.js: sem {trecho}")
        if "begin_checkout" in script:
            erros.append("quiz/script.js: não pode disparar begin_checkout (InitiateCheckout)")
    if rel == MATERIAIS_HUB or rel in MATERIAIS_PAGINAS:
        pasta = rel.rsplit("/", 1)[0] + "/"
        site_js = "../" * pasta.count("/") + "assets/js/site.js"
        if not re.search(rf'<script src="{re.escape(site_js)}(\?v=\d+)?" data-pagina="pgMat"></script>', html):
            erros.append(f"{rel}: sem <script src=\"{site_js}\" data-pagina=\"pgMat\">")
        if f'<link rel="canonical" href="https://liviaoliveira.me/{pasta}">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/{pasta}")
        if f"https://liviaoliveira.me/{pasta}" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não está no sitemap.xml")
        if "noindex" in html:
            erros.append(f"{rel}: os materiais são indexáveis (sem noindex)")
        if "pay.hotmart.com" in html or 'id="oferta"' in html or "checkout" in html:
            erros.append(f"{rel}: sem checkout nem #oferta (nada de InitiateCheckout nem view_offer automático)")
        # og:image própria de cada página (prévia do link no WhatsApp), gerada por _catalogo/og.py
        og = "og-materiais.jpg" if rel == MATERIAIS_HUB else f"og-mat-{rel.split('/')[1]}.jpg"
        if f'<meta property="og:image" content="https://liviaoliveira.me/assets/img/{og}">' not in html:
            erros.append(f"{rel}: og:image deve ser https://{DOMINIO}/assets/img/{og}")
        if not (ROOT / "assets/img" / og).exists():
            erros.append(f"{rel}: falta assets/img/{og} (rode _catalogo/og.py)")
    if rel == MATERIAIS_HUB:
        for m in MATERIAIS:
            if f'href="{m}/"' not in html:
                erros.append(f"{rel}: sem o card de {m}/")
        # hub com ?acesso=wa: grava livia_mat_ok e repassa acesso=wa aos links dos 6 materiais (vale mesmo sem localStorage)
        if not ("acesso=wa" in html and 'localStorage.setItem("livia_mat_ok","1")' in html
                and all(f'a[href="{m}/"]' in html for m in MATERIAIS)):
            erros.append(f"{rel}: o hub não trata ?acesso=wa (localStorage livia_mat_ok + acesso=wa nos links dos 6 materiais)")
    if rel in MATERIAIS_PAGINAS:
        slug = rel.split("/")[1]
        if f'data-material="{slug}"' not in html:
            erros.append(f"{rel}: sem data-material=\"{slug}\" no <main>")
        if not re.search(r'<script src="\.\./material\.js(\?v=\d+)?"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../material.js\"> (bloqueio, cadastro, copiar e PDF)")
        for trecho in ('localStorage.getItem("livia_mat_ok")', 'id="mat-trava"', 'id="contato"', 'name="consentimento"', 'name="empresa"',
                       'tabindex="-1"', 'data-mask="phone"', 'href="../../privacidade/"', "Libere o material completo, grátis",
                       ">Baixar PDF</button>", "Cada pílula é um pedaço do", "12x de R$ 71,67 sem juros ou R$ 860 à vista",
                       f"../../curso/b/?utm_source=material&amp;utm_medium=site&amp;utm_campaign=ccs_material&amp;utm_content=mat_{slug}",
                       "https://wa.me/5511910607651?text=", "Outros materiais"):
            if trecho not in html:
                erros.append(f"{rel}: sem {trecho}")
        # liberação por link (?acesso=wa, mandado pela Lia no WhatsApp): o script do <head> aplica html.mat-ok
        # antes de pintar e grava livia_mat_ok, mesmo se o localStorage falhar
        cabeca = html.split("</head>", 1)[0]
        if not ("acesso=wa" in cabeca and 'localStorage.setItem("livia_mat_ok","1")' in cabeca):
            erros.append(f"{rel}: o script do <head> não libera com ?acesso=wa (html.mat-ok + localStorage livia_mat_ok)")
        for outro in MATERIAIS:
            if outro != slug and f'href="../{outro}/"' not in html:
                erros.append(f"{rel}: \"Outros materiais\" sem o link ../{outro}/")
        # impressão (Ctrl+P) e PDFs estáticos: blocos só de impressão (identificação no topo, aviso do bloqueio, curso e WhatsApp no fim)
        for classe in ("mat-print-topo", "mat-print-aviso", "mat-print-fim"):
            if not re.search(rf'class="so-print {classe}"', html):
                erros.append(f"{rel}: sem o bloco de impressão .so-print.{classe}")
        if "CRP 07/18713" not in (re.search(r'<p class="so-print mat-print-topo">(.*?)</p>', html) or [""])[0]:
            erros.append(f"{rel}: .mat-print-topo sem o CRP 07/18713")
        if f'href="https://liviaoliveira.me/materiais/{slug}/"' not in (re.search(r'<p class="so-print mat-print-aviso">(.*?)</p>', html) or [""])[0]:
            erros.append(f"{rel}: .mat-print-aviso sem o link https://liviaoliveira.me/materiais/{slug}/")
        fim = (re.search(r'<div class="so-print mat-print-fim">(.*?)</div>', html, re.S) or [""])[0]
        for trecho in ("liviaoliveira.me/curso/b/", f"utm_campaign={slug}", 'href="https://wa.me/5511910607651"', "liviaoliveira.me/materiais/"):
            if trecho not in fim:
                erros.append(f"{rel}: .mat-print-fim sem {trecho}")
        pdf = ROOT / "materiais" / "pdf" / f"{slug}.pdf"
        if not pdf.is_file() or pdf.stat().st_size == 0:
            erros.append(f"materiais/pdf/{slug}.pdf: não existe ou está vazio (rode _catalogo/pdfs.py)")
    if rel == "curso/versao-b/index.html":
        if '<meta name="robots" content="noindex, follow">' not in html:
            erros.append(f"{rel}: sem noindex (é variação de teste)")
        if '<link rel="canonical" href="https://liviaoliveira.me/curso/">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/curso/")
        if "versao-b" in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não deve estar no sitemap.xml")
        if not any(t == "a" and a == "href" and v == "../b/" for t, a, v, _ in parser.refs):
            erros.append(f"{rel}: o link \"Curso\" do rodapé deve apontar para ../b/")
    if rel == "curso/b/index.html":
        if '<meta name="robots" content="noindex">' not in html:
            erros.append(f"{rel}: sem <meta name=\"robots\" content=\"noindex\">")
        if '<link rel="canonical" href="https://liviaoliveira.me/curso/">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/curso/")
        if "curso/b/" in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não deve estar no sitemap.xml")
        for destino in ("../../", "../../consultoria/", "../../terapia/", "https://www.instagram.com/liviaoliveira.psicologa/"):
            if f'href="{destino}"' not in html:
                erros.append(f"{rel}: rodapé sem o link {destino}")
    if rel in CURSO_ORGANICO:
        if not any(t == "a" and a == "href" and v == CURSO_ORGANICO[rel] for t, a, v, _ in parser.refs):
            erros.append(f"{rel}: sem link para o curso em {CURSO_ORGANICO[rel]}")
    if not rel.startswith("curso/versao-b/"):
        for t, a, v, _ in parser.refs:
            if t == "a" and "versao-b" in v:
                erros.append(f"{rel}: link interno para curso/versao-b/ ({v}); use curso/b/")
    if rel.startswith("curso/") and re.search(r"total (de )?R\$ 860", html):
        erros.append(f"{rel}: diz que o total no cartão é R$ 860 (a Hotmart mostra R$ 860,04); use \"12x de R$ 71,67 sem juros ou R$ 860 à vista\"")
    if rel.startswith("terapia/") and "R$" in html:
        erros.append(f"{rel}: contém preço (R$)")
    if rel == "terapia/index.html":
        baixo = html.lower()
        for proibido in ("conversa inicial", "agendar uma conversa", "primeiro contato", "combinamos horário"):
            if proibido in baixo:
                erros.append(f"{rel}: contém \"{proibido}\" (a Lívia não faz conversa inicial; a página é lista de interesse)")
        if 'id="lista"' not in html:
            erros.append(f"{rel}: sem a seção id=\"lista\" da lista de interesse")
        if f'data-gform="{GFORM_TERAPIA}"' not in html:
            erros.append(f"{rel}: formulário da lista não envia ao Google Form da terapia")
        if "../assets/js/site.js" not in html:
            erros.append(f"{rel}: sem ../assets/js/site.js (validação e envio do formulário)")
    if rel in ("terapia/index.html", "terapia/b/index.html"):
        if 'value="Tarde (13h  - 17h)"' not in html:
            erros.append(f"{rel}: valor do turno da tarde difere do Google Form (\"Tarde (13h  - 17h)\")")
        if 'value="Manhã (10h e 11h)"' not in html:
            erros.append(f"{rel}: valor do turno da manhã difere do Google Form (\"Manhã (10h e 11h)\")")


class PrecoBF(HTMLParser):
    """Texto com o preço de Black Friday (499,99 ou 41,67) fora de um elemento data-bf="on" no <body>: apareceria
    depois do fim (o bf.css só esconde [data-bf="on"])."""
    VAZIOS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.pilha = []  # (tag, dentro de data-bf="on")
        self.no_body = False
        self.soltos = []

    def handle_starttag(self, tag, attrs):
        if tag == "body":
            self.no_body = True
        if tag in self.VAZIOS:
            return
        dentro = (bool(self.pilha) and self.pilha[-1][1]) or dict(attrs).get("data-bf") == "on"
        self.pilha.append((tag, dentro or tag == "script"))

    def handle_endtag(self, tag):
        for i in range(len(self.pilha) - 1, -1, -1):
            if self.pilha[i][0] == tag:
                del self.pilha[i:]
                break

    def handle_data(self, data):
        if self.no_body and re.search(r"499,99|41,67", data) and not (self.pilha and self.pilha[-1][1]):
            self.soltos.append(" ".join(data.split())[:80])


def check_black_friday():
    bf_js = (ROOT / "assets/js/bf.js").read_text(encoding="utf-8")
    for trecho in (BF_CONFIG, "window.bfAtiva = function", '"bf-fim"', '"bf:fim"', "data-bf-contagem", "bf_agora",
                   r"/^(localhost|127\.0\.0\.1)$/.test(location.hostname)"):
        if trecho not in bf_js:
            erros.append(f"assets/js/bf.js: sem {trecho}")
    bf_css = (ROOT / "assets/css/bf.css").read_text(encoding="utf-8")
    if 'html:not(.bf-fim) [data-bf="off"]' not in bf_css or 'html.bf-fim [data-bf="on"]' not in bf_css:
        erros.append('assets/css/bf.css: sem as regras que trocam [data-bf="on"] e [data-bf="off"] pela classe bf-fim')

    for rel in BF_PAGINAS:
        html = (ROOT / rel).read_text(encoding="utf-8")
        cabeca = html.split("</head>", 1)[0]
        pre = "../" * rel.count("/")
        if not re.search(rf'<script src="{re.escape(pre)}assets/js/bf\.js(\?v=\d+)?"></script>', cabeca):
            erros.append(f"{rel}: sem <script src=\"{pre}assets/js/bf.js\"> no <head> (sem defer: decide o preço antes de pintar)")
        if not re.search(rf'<link rel="stylesheet" href="{re.escape(pre)}assets/css/bf\.css(\?v=\d+)?">', cabeca):
            erros.append(f"{rel}: sem {pre}assets/css/bf.css")
        if "71,67" in html and "data-bf=\"off\"" not in html:
            erros.append(f"{rel}: preço normal sem a versão data-bf=\"off\"")
        soltos = PrecoBF()
        soltos.feed(html)
        for t in soltos.soltos:
            erros.append(f"{rel}: preço de Black Friday fora de data-bf=\"on\" (apareceria depois do fim): \"{t}\"")
        if rel in BF_FAIXA:
            faixa = re.search(r'<a class="bf-faixa" data-bf="on" href="([^"]+)">(.*?)</a>', html)
            if not faixa:
                erros.append(f"{rel}: sem a faixa de Black Friday (a.bf-faixa data-bf=\"on\")")
            else:
                destino = f"{pre}black-friday/"
                if rel in BF_UTM:
                    destino += f"?utm_source=site&amp;utm_medium={BF_UTM[rel]}&amp;utm_campaign=ccs_bf"
                if faixa.group(1) != destino:
                    erros.append(f"{rel}: a faixa de Black Friday deve levar para {destino} ({faixa.group(1)})")
                if "data-bf-contagem" not in faixa.group(2) or "de R$ 860 por R$ 499,99" not in faixa.group(2):
                    erros.append(f"{rel}: faixa sem \"de R$ 860 por R$ 499,99\" e a contagem (data-bf-contagem)")
        if rel in BF_UTM and rel != MATERIAIS_HUB:
            link = f'data-bf="on" href="{pre}black-friday/?utm_source=site&amp;utm_medium={BF_UTM[rel]}&amp;utm_campaign=ccs_bf"'
            if link not in html or "de R$ 860 por R$ 499,99 · 12x de R$ 41,67 sem juros (Black Friday até 30/11)" not in html:
                erros.append(f"{rel}: bloco do curso sem o preço de Black Friday e o link para black-friday/ ({BF_UTM[rel]})")
    for rel in ("curso/index.html", "curso/b/index.html", "curso/versao-b/index.html"):
        html = (ROOT / rel).read_text(encoding="utf-8")
        if html.count("de R$ 860 por R$ 499,99 · 12x de R$ 41,67 sem juros (Black Friday até 30/11)") < 1:
            erros.append(f"{rel}: sem a linha de preço de Black Friday")
    for rel in SEM_BF:
        html = (ROOT / rel).read_text(encoding="utf-8")
        for proibido in ("bf.js", "bf.css", "bf-faixa", "Black Friday", "data-bf"):
            if proibido in html:
                erros.append(f"{rel}: contém {proibido!r} (terapia fica sem Black Friday)")

    rel = BLACK_FRIDAY
    html = (ROOT / rel).read_text(encoding="utf-8")
    for trecho in ("<title>Black Friday Carreira com Sentido: de R$ 860 por R$ 499,99</title>", '<meta name="description"',
                   '<link rel="canonical" href="https://liviaoliveira.me/black-friday/">',
                   '<meta property="og:image" content="https://liviaoliveira.me/assets/img/og-black-friday.jpg">',
                   "Black Friday · termina em", "data-bf-dias", "data-bf-seg", "Black Friday Carreira com Sentido",
                   "De R$ 860 por <em>R$ 499,99.</em>", "Você economiza R$ 360,01", "Quero garantir o preço de Black Friday",
                   "7 dias de garantia · acesso imediato · Pix, cartão ou boleto", 'id="oferta"', "CRP 07/18713",
                   "A Black Friday terminou", 'data-bf="off" href="../curso/b/"', "Até quando vale?", "Posso parcelar?",
                   "Tem Pix e boleto?", "Quanto tempo tenho de acesso?", "E se eu não gostar?",
                   "Já baixei os materiais gratuitos, o curso é diferente?", "sticky-bar",
                   "https://wa.me/5511910607651?text=Oi!%20Tenho%20uma%20d%C3%BAvida%20sobre%20a%20Black%20Friday%20do%20Carreira%20com%20Sentido",
                   "Falar com a equipe no WhatsApp"):
        if trecho not in html:
            erros.append(f"{rel}: sem {trecho}")
    if not re.search(r'<script src="\.\./assets/js/site\.js(\?v=\d+)?" data-pagina="pgBF" data-versao="bf_a"></script>', html):
        erros.append(f"{rel}: sem <script src=\"../assets/js/site.js\" data-pagina=\"pgBF\" data-versao=\"bf_a\">")
    if html.count('class="btn btn-light btn-cta checkout"') + html.count('class="btn btn-cta checkout"') < 3:
        erros.append(f"{rel}: menos de 3 botões de compra ao longo da página")
    if html.count("<blockquote class=\"test\">") != 6:
        erros.append(f"{rel}: deve ter os 6 depoimentos do curso/b/")
    if html.count('<li class="mod">') != 10:
        erros.append(f"{rel}: deve ter os 10 módulos")
    if not (ROOT / "assets/img/og-black-friday.jpg").is_file():
        erros.append(f"{rel}: falta assets/img/og-black-friday.jpg (rode _catalogo/og.py og-black-friday.jpg)")
    if "https://liviaoliveira.me/black-friday/" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
        erros.append(f"{rel}: não está no sitemap.xml")

    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for rel, (versao, arte) in BF_VERSOES.items():
        html = (ROOT / rel).read_text(encoding="utf-8")
        pasta = rel.rsplit("/", 1)[0] + "/"
        for trecho in ('<meta name="robots" content="noindex">', '<link rel="canonical" href="https://liviaoliveira.me/black-friday/">',
                       f'<meta property="og:url" content="https://liviaoliveira.me/{pasta}">',
                       f'<meta property="og:image" content="https://liviaoliveira.me/assets/img/bf/{arte}">',
                       "Black Friday · termina em", "data-bf-dias", "data-bf-seg", "A Black Friday terminou",
                       'data-bf="off" href="../../curso/b/"', "Você economiza R$ 360,01", 'id="oferta"', "sticky-bar",
                       "https://wa.me/5511910607651?text=Oi!%20Tenho%20uma%20d%C3%BAvida%20sobre%20a%20Black%20Friday%20do%20Carreira%20com%20Sentido"):
            if trecho not in html:
                erros.append(f"{rel}: sem {trecho}")
        if html.count("<title>") != 1 or "<title>Black Friday Carreira com Sentido: de R$ 860 por R$ 499,99</title>" in html:
            erros.append(f"{rel}: precisa de um <title> próprio (diferente da black-friday/)")
        if '<meta name="description" content="' not in html or (ROOT / BLACK_FRIDAY).read_text(encoding="utf-8").split('<meta name="description"', 1)[1].split(">", 1)[0] in html:
            erros.append(f"{rel}: precisa de uma description própria")
        if not re.search(rf'<script src="\.\./\.\./assets/js/site\.js(\?v=\d+)?" data-pagina="pgBF" data-versao="{versao}"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../../assets/js/site.js\" data-pagina=\"pgBF\" data-versao=\"{versao}\">")
        if not (ROOT / "assets/img/bf" / arte).is_file():
            erros.append(f"{rel}: falta assets/img/bf/{arte}")
        if f"liviaoliveira.me/{pasta}" in sitemap:
            erros.append(f"{rel}: página de anúncio não vai no sitemap.xml")
        if "menor preço" in html.lower():
            erros.append(f"{rel}: contém \"menor preço\" (sem fonte)")
        if html.count('class="btn btn-light btn-cta checkout"') + html.count('class="btn btn-cta checkout"') < 2:
            erros.append(f"{rel}: menos de 2 botões de compra ao longo da página")
    b = (ROOT / "black-friday/b/index.html").read_text(encoding="utf-8")
    for trecho in ("Quanto a sua sessão precisa custar para a clínica <em>fechar a conta?</em>", "Módulo 02", "Módulo 03",
                   "Valor da sessão", "Faltas e agenda", "Contrato e impostos", "CRP 07/18713", "Garantia de 7 dias."):
        if trecho not in b:
            erros.append(f"black-friday/b/index.html: sem {trecho}")
    if b.count('<blockquote class="test">') != 6 or b.count('<div class="bf-dor">') != 3:
        erros.append("black-friday/b/index.html: deve ter 6 depoimentos e 3 dores")
    c = (ROOT / "black-friday/c/index.html").read_text(encoding="utf-8")
    for trecho in ("Black Friday <em>Carreira com Sentido</em>", "de <s>R$ 860</s>", ">Garantir por R$ 499,99</a>",
                   "ou 12x de R$ 41,67 sem juros", ">Garantir</a>", "Tenho uma dúvida", "Garantia de 7 dias."):
        if trecho not in c:
            erros.append(f"black-friday/c/index.html: sem {trecho}")
    if c.count("<li><svg") != 6 or c.count('<blockquote class="test">') != 6 or c.count("<details") != 4:
        erros.append("black-friday/c/index.html: deve ter 6 itens com ícone, 6 depoimentos e 4 perguntas")

    atalho = (ROOT / BLACK_ATALHO).read_text(encoding="utf-8")
    for trecho in ('location.replace("../black-friday/"+location.search', '<meta http-equiv="refresh" content="0; url=../black-friday/">',
                   '<meta name="robots" content="noindex">'):
        if trecho not in atalho:
            erros.append(f"{BLACK_ATALHO}: sem {trecho}")
    if "liviaoliveira.me/black/" in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
        erros.append(f"{BLACK_ATALHO}: o atalho não vai no sitemap.xml")

    script = (ROOT / "curso/inscricao/script.js").read_text(encoding="utf-8")
    for trecho in ('PAGINAS = ["pgA", "pgB", "pgC", "pgBF"]', r"\|(pg(?:[ABC]|BF))$", "window.BF.oferta", "window.BF.valor",
                   "value: valorCurso()"):
        if trecho not in script:
            erros.append(f"curso/inscricao/script.js: sem {trecho} (Black Friday)")
    if re.search(r"^function bfAtiva\b", script, re.M):
        erros.append("curso/inscricao/script.js: function bfAtiva global sobrescreve o window.bfAtiva do bf.js")
    for trecho in ('visit.get("versao")', "pagina_versao", '"|" + versao'):
        if trecho not in script:
            erros.append(f"curso/inscricao/script.js: sem {trecho} (versão da página da Black Friday no sck e nos eventos)")
    site_js = (ROOT / "assets/js/site.js").read_text(encoding="utf-8")
    if "valorOferta()" not in site_js:
        erros.append("assets/js/site.js: view_offer sem o valor da Black Friday (valorOferta)")
    for trecho in ('getAttribute("data-versao")', "p.pagina_versao = params.pagina_versao", 'searchParams.set("versao", versao)'):
        if trecho not in site_js:
            erros.append(f"assets/js/site.js: sem {trecho} (versão da página da Black Friday)")

    # ao mudar o site.js, o ?v= sobe em todas as páginas: todas com a mesma versão
    versoes = {}
    for p in ROOT.glob("**/index.html"):
        if ".git" in p.parts:
            continue
        for v in re.findall(r'assets/js/site\.js\?v=(\d+)', p.read_text(encoding="utf-8")):
            versoes.setdefault(v, []).append(p.relative_to(ROOT).as_posix())
    if len(versoes) > 1:
        erros.append(f"site.js com ?v= diferente entre as páginas: { {v: len(ps) for v, ps in versoes.items()} }")


def main():
    for rel in PAGES:
        check_page(rel)
    check_whatsapp()
    check_black_friday()
    for extra in EXTRAS:
        p = ROOT / extra
        if not p.exists():
            erros.append(f"{extra}: não existe")
            continue
        texto = p.read_text(encoding="utf-8")
        if "—" in texto:
            erros.append(f"{extra}: contém travessão (—)")
        if HOTLINK in texto:
            erros.append(f"{extra}: referencia o storage do Scrolltide ({HOTLINK})")
        if extra == "assets/js/site.js":
            if f'metaPixelId: "{PIXEL_ID}"' not in texto:
                erros.append(f"{extra}: CONFIG sem o Pixel da Meta {PIXEL_ID}")
            if f'ga4Id: "{GA4_ID}"' not in texto:
                erros.append(f"{extra}: CONFIG sem o GA4 {GA4_ID}")
            if 'hasAttribute("data-sem-rastreamento")' not in texto:
                erros.append(f"{extra}: não respeita data-sem-rastreamento (terapia sem Pixel/GA4)")
            if f'CADASTRO_URL = "{LAMBDA_CADASTRO}"' not in texto:
                erros.append(f"{extra}: sem CADASTRO_URL da Lambda livia-leads (contato do quiz e da calculadora)")
        if extra == "materiais/material.js":
            for trecho in ('"livia_mat_ok"', 'ferramenta: "material"', '"generate_lead"', '"material_view"', '"material_copiar"',
                           '"material_pdf"', '"view_offer"', '"material_para_curso"', "siteIdentify"):
                if trecho not in texto:
                    erros.append(f"{extra}: sem {trecho}")
            if "begin_checkout" in texto:
                erros.append(f"{extra}: não pode disparar begin_checkout (InitiateCheckout)")
            # Baixar PDF: bloqueado pede o cadastro; liberado baixa materiais/pdf/<slug>.pdf (no navegador embutido,
            # painel com WhatsApp, navegador externo, ver e copiar o link); nunca chama window.print()
            botao = texto.find('getElementById("mat-pdf")')
            checa = texto.find('classList.contains("mat-ok")', botao)
            baixa = texto.find("baixa()", botao)
            if botao < 0 or not 0 <= checa < baixa:
                erros.append(f"{extra}: o #mat-pdf só pode baixar o PDF depois de checar html.mat-ok")
            if "window.print()" in texto:
                erros.append(f"{extra}: o \"Baixar PDF\" não chama mais window.print() (a impressão fica só no Ctrl+P)")
            for trecho in ('"material_pdf_bloqueado"', '"../pdf/" + slug + ".pdf"', "mat-libera__pdf", "acesso=wa",
                           '"material_liberado_link"', 'a.download = "Livia-Oliveira-"', 'modo: "download"', "EMBUTIDO",
                           "https://wa.me/5511910607651?text=", '"intent://"', '"x-safari-https://"', "Copiar link do PDF"):
                if trecho not in texto:
                    erros.append(f"{extra}: sem {trecho}")
        if extra == "terapia/script.js":
            for tag in TAGS_RASTREAMENTO:
                if tag in texto:
                    erros.append(f"{extra}: contém {tag!r} (terapia não carrega Pixel/GA4/GTM)")

    cname = ROOT / "CNAME"
    if not cname.exists():
        erros.append("CNAME: não existe")
    elif cname.read_text(encoding="utf-8").strip() != DOMINIO:
        erros.append(f"CNAME: deve conter exatamente {DOMINIO}")
    if not (ROOT / "robots.txt").exists():
        erros.append("robots.txt: não existe")
    manifest = ROOT / MANIFEST
    if not manifest.exists():
        erros.append(f"{MANIFEST}: não existe")
    else:
        try:
            icones = json.loads(manifest.read_text(encoding="utf-8")).get("icons", [])
        except ValueError as e:
            erros.append(f"{MANIFEST}: JSON inválido ({e})")
            icones = []
        for icone in icones:
            if not (ROOT / icone.get("src", "").lstrip("/")).is_file():
                erros.append(f"{MANIFEST}: ícone {icone.get('src')} aponta para arquivo inexistente")
    for p in [ROOT / "sitemap.xml", *ROOT.glob("**/*.html")]:
        if ".git" in p.parts:
            continue
        rel = p.relative_to(ROOT).as_posix()
        if p.exists() and URL_ANTIGA in p.read_text(encoding="utf-8") and rel not in PAGES:
            erros.append(f"{rel}: usa o endereço antigo ({URL_ANTIGA}); use https://{DOMINIO}/")

    if erros:
        print("FALHOU:")
        for e in erros:
            print(" -", e)
        sys.exit(1)
    print(f"OK: {len(PAGES)} páginas verificadas, sem problemas.")


if __name__ == "__main__":
    main()
