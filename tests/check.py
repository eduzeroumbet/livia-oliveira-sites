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
PAGES = ["index.html", "curso/index.html", "curso/b/index.html", "curso/versao-b/index.html", "consultoria/index.html", "terapia/index.html", "terapia/b/index.html", "privacidade/index.html"]
# política de privacidade (URL do app da Meta e dos anúncios): link no rodapé de todas as páginas e no sitemap
PRIVACIDADE = "privacidade/index.html"
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
}
CHECKOUT = "https://pay.hotmart.com/M100028858P?checkoutMode=10"
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
)
# favicons e manifest usam caminho absoluto (site na raiz do domínio)
REL_ABSOLUTO = {"icon", "apple-touch-icon", "manifest"}
MANIFEST = "site.webmanifest"

erros = []


class Refs(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.checkouts = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        # data-src-720 / data-src-1280: fontes do vídeo do hero que o JS escolhe pela largura
        for attr in ("src", "href", "poster", "data-src-720", "data-src-1280"):
            if a.get(attr):
                self.refs.append((tag, attr, a[attr], a.get("rel") or ""))
        if tag == "a" and "checkout" in (a.get("class") or "").split() and a.get("href") == CHECKOUT:
            self.checkouts += 1


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

    # link "Política de privacidade" dentro do <footer> (na bio, no rodapé .bio-footer)
    rodape = re.search(r"<footer\b.*?</footer>|<p class=\"bio-footer\">.*?</p>", html, re.S)
    links_rodape = Refs()
    links_rodape.feed(rodape.group(0) if rodape else "")
    if not any(
        t == "a" and a == "href" and not v.startswith(EXTERNAL)
        and (path.parent / unquote(urlsplit(v).path)).resolve() == (ROOT / "privacidade").resolve()
        for t, a, v, _ in links_rodape.refs
    ):
        erros.append(f"{rel}: rodapé sem o link \"Política de privacidade\" para {PRIVACIDADE}")

    if rel == PRIVACIDADE:
        if '<link rel="canonical" href="https://liviaoliveira.me/privacidade/">' not in html:
            erros.append(f"{rel}: canonical deve apontar para https://{DOMINIO}/privacidade/")
        if not re.search(r'<script src="\.\./assets/js/site\.js(\?v=\d+)?"></script>', html):
            erros.append(f"{rel}: sem <script src=\"../assets/js/site.js\"> (carrega o rastreamento normalmente)")
        for trecho in ("CRP 07/18713", "Lívia Carvalho de Oliveira", "(51) 99259-7638", "@liviaoliveira.psicologa", "20 de outubro de 2026"):
            if trecho not in html:
                erros.append(f"{rel}: sem \"{trecho}\"")
        if "https://liviaoliveira.me/privacidade/" not in (ROOT / "sitemap.xml").read_text(encoding="utf-8"):
            erros.append(f"{rel}: não está no sitemap.xml")

    for entry in ENTRIES.get(rel, []):
        if f'data-entry="{entry}"' not in html:
            erros.append(f"{rel}: campo {entry} do Google Form ausente")

    if rel == "curso/b/index.html" and parser.checkouts == 0:
        erros.append(f"{rel}: nenhum botão class=\"checkout\" apontando para o Hotmart")

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

    if rel in ("curso/index.html", "curso/versao-b/index.html") and CHECKOUT not in html:
        erros.append(f"{rel}: sem link para o checkout Hotmart")
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
