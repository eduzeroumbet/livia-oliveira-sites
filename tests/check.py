"""Verificações simples do site estático.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/check.py
"""
import json
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["index.html", "curso/index.html", "curso/b/index.html", "consultoria/index.html", "terapia/index.html", "terapia/b/index.html"]
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
CHECKOUT = "https://pay.hotmart.com/M100028858P?checkoutMode=10"
HOTLINK = "r2" + ".dev"  # storage do Scrolltide; montado em partes para o próprio check não conter o literal
DOMINIO = "liviaoliveira.me"
URL_ANTIGA = "github.io" + "/livia-oliveira-sites"  # endereço antigo; em partes pelo mesmo motivo
EXTRAS = (
    "assets/css/site.css",
    "assets/js/site.js",
    "curso/style.css",
    "curso/script.js",
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

    for entry in ENTRIES.get(rel, []):
        if f'data-entry="{entry}"' not in html:
            erros.append(f"{rel}: campo {entry} do Google Form ausente")

    if rel == "curso/b/index.html" and parser.checkouts == 0:
        erros.append(f"{rel}: nenhum botão class=\"checkout\" apontando para o Hotmart")

    if rel == "curso/index.html" and CHECKOUT not in html:
        erros.append(f"{rel}: sem link para o checkout Hotmart")
    if rel.startswith("terapia/") and "R$" in html:
        erros.append(f"{rel}: contém preço (R$)")
    if rel == "terapia/b/index.html":
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
