"""Testa no Chromium headless o formulário da lista de interesse de terapia/index.html.

A requisição ao Google Forms é interceptada (nada é enviado de verdade). Confere a validação com campos vazios,
a máscara do WhatsApp e o POST para o formResponse com os entries e valores exatos, em 390px e 1440px.

Uso: /Users/educloud/orquestra/.venv/bin/python tests/lista_terapia.py
Requer: playwright + chromium (python -m playwright install chromium).
"""
import sys
from pathlib import Path
from urllib.parse import parse_qs

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
URL = (ROOT / "terapia" / "index.html").as_uri()
GFORM = "https://docs.google.com/forms/d/e/1FAIpQLSfBmYNmVucSkEQvBLERoWCcRs_zaT0MN2P944cHZapHvCwfUA/formResponse"
falhas = []


def ok(cond, msg):
    print(("OK   " if cond else "FALHA ") + msg)
    if not cond:
        falhas.append(msg)


def parse_multipart(body: bytes, ctype: str):
    boundary = ctype.split("boundary=")[1].encode()
    campos = []
    for parte in body.split(b"--" + boundary):
        if b'name="' not in parte:
            continue
        cab, _, val = parte.partition(b"\r\n\r\n")
        nome = cab.split(b'name="')[1].split(b'"')[0].decode()
        campos.append((nome, val.rstrip(b"\r\n").decode("utf-8")))
    return campos


with sync_playwright() as p:
    b = p.chromium.launch()
    for vp in ({"width": 390, "height": 844}, {"width": 1440, "height": 900}):
        page = b.new_page(viewport=vp)
        capturadas = []
        externas = []

        def rota(route):
            req = route.request
            if req.url.startswith("https://docs.google.com/"):
                capturadas.append((req.method, req.url, req.post_data_buffer, req.headers.get("content-type", "")))
                route.fulfill(status=200, body="ok")
            elif req.url.startswith("file:") or "fonts.g" in req.url:
                route.continue_()
            else:
                externas.append(req.url)
                route.abort()

        page.route("**/*", rota)
        erros_js = []
        page.on("pageerror", lambda e: erros_js.append(str(e)))
        page.goto(URL, wait_until="load")
        print(f"--- viewport {vp['width']}")

        # 1) envio vazio: a validação bloqueia
        page.click("#lista-form button[type=submit]")
        page.wait_for_timeout(300)
        ok(len(capturadas) == 0, "envio vazio não dispara requisição")
        for campo in ("nome", "email", "whatsapp", "dias", "turnos", "aceite"):
            txt = page.text_content(f'#lista-form [data-error-for="{campo}"]').strip()
            ok(bool(txt), f"erro visível em {campo}: {txt!r}")
        ok(page.evaluate("document.activeElement.name") == "nome", "foco vai para o primeiro campo inválido")

        # 2) máscara do telefone
        page.fill("#l-whats", "51999998888")
        page.dispatch_event("#l-whats", "input")
        ok(page.input_value("#l-whats") == "(51) 99999-8888", f"máscara: {page.input_value('#l-whats')!r}")

        # 3) envio parcial (sem aceite) também é bloqueado
        page.fill("#l-nome", "Teste Automatizado")
        page.fill("#l-email", "teste@example.com")
        page.check("#l-dia-seg")
        page.check("#l-dia-qua")
        page.check("#l-turno-manha")
        page.check("#l-turno-tarde")
        page.click("#lista-form button[type=submit]")
        page.wait_for_timeout(300)
        ok(len(capturadas) == 0, "sem o aceite não envia")

        # 4) envio completo: POST interceptado
        page.check("#l-aceite")
        page.click("#lista-form button[type=submit]")
        page.wait_for_selector("#lista-ok:not([hidden])", timeout=5000)
        ok(len(capturadas) == 1, f"uma requisição ao Google ({len(capturadas)})")
        if capturadas:
            metodo, url, body, ctype = capturadas[0]
            ok(metodo == "POST", f"método {metodo}")
            ok(url == GFORM, f"url {url}")
            campos = parse_multipart(body, ctype)
            print("     campos:", campos)
            esperado = [
                ("entry.1886022350", "Teste Automatizado"),
                ("entry.1192162037", "teste@example.com"),
                ("entry.1202505729", "(51) 99999-8888"),
                ("entry.1222954892", "Segunda-feira"),
                ("entry.1222954892", "Quarta-feira"),
                ("entry.1892587682", "Manhã (10h e 11h)"),
                ("entry.1892587682", "Tarde (13h  - 17h)"),
            ]
            ok(campos == esperado, "entries e valores exatos do Google Form")
        ok(page.is_hidden("#lista-form"), "formulário some após o envio")
        ok(page.evaluate("document.activeElement.id") == "lista-ok", "foco na mensagem de sucesso")
        ok(page.url.startswith(URL), "continua na mesma página")
        ok(page.evaluate("document.documentElement.scrollWidth") <= vp["width"], "sem rolagem horizontal")
        ok(not erros_js, f"sem erros de JS {erros_js}")
        page.close()
    b.close()

print("RESULTADO:", "OK" if not falhas else f"{len(falhas)} falha(s)")
sys.exit(1 if falhas else 0)
