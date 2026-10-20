"""Verificações simples do site estático.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/check.py
"""
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
EXTRAS = (
    "assets/css/site.css",
    "assets/js/site.js",
    "curso/style.css",
    "curso/script.js",
    "terapia/style.css",
    "terapia/script.js",
)

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
                self.refs.append((tag, attr, a[attr]))
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

    parser = Refs()
    parser.feed(html)
    for tag, attr, value in parser.refs:
        if value.startswith("/"):
            erros.append(f"{rel}: <{tag} {attr}=\"{value}\"> começa com \"/\" (use caminho relativo)")
            continue
        if value.startswith(EXTERNAL):
            continue
        local = unquote(urlsplit(value).path)
        if not local:
            continue
        target = (path.parent / local).resolve()
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

    if erros:
        print("FALHOU:")
        for e in erros:
            print(" -", e)
        sys.exit(1)
    print(f"OK: {len(PAGES)} páginas verificadas, sem problemas.")


if __name__ == "__main__":
    main()
