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
)
# favicons e manifest usam caminho absoluto (site na raiz do domínio)
REL_ABSOLUTO = {"icon", "apple-touch-icon", "manifest"}
MANIFEST = "site.webmanifest"

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
                       "12x de R$ 71,67 sem juros", "R$ 860 à vista", "https://wa.me/5551992597638?text="):
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
                       "og-curso.jpg", "12x de R$ 71,67 sem juros ou R$ 860 à vista", "7 dias de garantia", 'aria-live="polite"'):
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
        if "og-curso.jpg" not in html:
            erros.append(f"{rel}: sem og:image")
    if rel == MATERIAIS_HUB:
        for m in MATERIAIS:
            if f'href="{m}/"' not in html:
                erros.append(f"{rel}: sem o card de {m}/")
    if rel in MATERIAIS_PAGINAS:
        slug = rel.split("/")[1]
        if f'data-material="{slug}"' not in html:
            erros.append(f"{rel}: sem data-material=\"{slug}\" no <main>")
        if not re.search(r'<script src="\.\./material\.js(\?v=\d+)?"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../material.js\"> (bloqueio, cadastro, copiar e PDF)")
        for trecho in ('localStorage.getItem("livia_mat_ok")', 'id="mat-trava"', 'id="contato"', 'name="consentimento"', 'name="empresa"',
                       'tabindex="-1"', 'data-mask="phone"', 'href="../../privacidade/"', "Libere o material completo, grátis",
                       "Salvar em PDF", "Cada pílula é um pedaço do", "12x de R$ 71,67 sem juros ou R$ 860 à vista",
                       f"../../curso/b/?utm_source=material&amp;utm_medium=site&amp;utm_campaign=ccs_material&amp;utm_content=mat_{slug}",
                       "https://wa.me/5551992597638?text=", "Outros materiais"):
            if trecho not in html:
                erros.append(f"{rel}: sem {trecho}")
        for outro in MATERIAIS:
            if outro != slug and f'href="../{outro}/"' not in html:
                erros.append(f"{rel}: \"Outros materiais\" sem o link ../{outro}/")
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


def main():
    for rel in PAGES:
        check_page(rel)
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
