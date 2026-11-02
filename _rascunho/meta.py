import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://liviaoliveira.me/assets/img/"
CURSO = ("og-curso-v2.jpg", "Lívia Oliveira com a mão no queixo e o título Carreira com Sentido, curso para psicólogas clínicas",
         "Carreira com Sentido, com Lívia Oliveira")
PAGINAS = {
    "index.html": ("og-home.jpg", "Lívia Oliveira sorrindo para a câmera, com o texto Lívia Oliveira, psicóloga clínica, CRP 07/18713", None),
    "curso/index.html": CURSO,
    "curso/b/index.html": CURSO,
    "curso/versao-b/index.html": CURSO,
    "curso/inscricao/index.html": CURSO,
    "materiais/index.html": ("og-materiais.jpg", "Lívia Oliveira sorrindo à mesa do consultório e o título Materiais gratuitos para a sua clínica", None),
    "materiais/mensagens/index.html": ("og-mat-mensagens.jpg", "Lívia Oliveira sorrindo ao notebook e o título 8 mensagens prontas para o WhatsApp",
                                       "8 mensagens prontas para o WhatsApp da clínica"),
    "materiais/faltas/index.html": ("og-mat-faltas.jpg", "Lívia Oliveira sorrindo à mesa e o título Política de faltas e pagamentos",
                                    "Política de faltas e pagamentos: modelo para copiar"),
    "materiais/etica/index.html": ("og-mat-etica.jpg", "Lívia Oliveira sorrindo para a câmera e o título Posso postar isso? Checklist ético para o Instagram da psicóloga",
                                   "Posso postar isso? Checklist ético para psicólogas"),
    "materiais/reajuste/index.html": ("og-mat-reajuste.jpg", "Lívia Oliveira sorrindo para a câmera e o título Como reajustar o valor da sessão",
                                      "Como reajustar o valor da sessão sem culpa"),
    "materiais/posts/index.html": ("og-mat-posts.jpg", "Lívia Oliveira sorrindo para a câmera e o título 30 ideias de posts",
                                   "30 ideias de posts que aproximam pacientes"),
    "materiais/indicacoes/index.html": ("og-mat-indicacoes.jpg", "Lívia Oliveira sorrindo para a câmera e o título Mensagens para médicos e colegas",
                                        "Mensagens para apresentar seu trabalho a médicos e colegas"),
    "quiz/index.html": ("og-quiz.jpg", "Lívia Oliveira na poltrona, com a mão no queixo, e a pergunta Você está pronta para viver da clínica? Teste de 1 minuto",
                        "Você está pronta para viver da clínica? Teste de 1 minuto"),
    "calculadora/index.html": ("og-calculadora.jpg", "Lívia Oliveira sorrindo e a pergunta Quanto deveria custar a sua sessão? Calculadora para psicólogas", None),
}

for rel, (img, alt, titulo) in PAGINAS.items():
    p = ROOT / rel
    linhas = p.read_text(encoding="utf-8").split("\n")
    ind = re.match(r"\s*", next(l for l in linhas if 'property="og:url"' in l)).group(0)
    linhas = [l for l in linhas if not re.search(r'property="og:image|name="twitter:image', l)]
    url = BASE + img
    novo = []
    for l in linhas:
        if 'property="og:title"' in l:
            if not any('property="og:site_name"' in x for x in linhas):
                novo.append(f'{ind}<meta property="og:site_name" content="Lívia Oliveira">')
            if titulo:
                l = re.sub(r'content="[^"]*"', f'content="{titulo}"', l)
        novo.append(l)
        if 'property="og:url"' in l:
            novo += [
                f'{ind}<meta property="og:image" content="{url}">',
                f'{ind}<meta property="og:image:secure_url" content="{url}">',
                f'{ind}<meta property="og:image:type" content="image/jpeg">',
                f'{ind}<meta property="og:image:width" content="1200">',
                f'{ind}<meta property="og:image:height" content="630">',
                f'{ind}<meta property="og:image:alt" content="{alt}">',
            ]
        if 'name="twitter:card"' in l:
            novo.append(f'{ind}<meta name="twitter:image" content="{url}">')
    p.write_text("\n".join(novo), encoding="utf-8")
    print(rel)
