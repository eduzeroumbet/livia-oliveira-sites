# livia-oliveira-sites
Landing pages da psicóloga Lívia Oliveira: curso Carreira com Sentido, consultoria e atendimento psicológico

Site estático (HTML, CSS e JS puros, sem build) publicado pelo GitHub Pages em
https://liviaoliveira.me/ (domínio próprio, definido no arquivo `CNAME`). O endereço antigo do GitHub Pages
redireciona automaticamente para o domínio. `robots.txt` aponta para o `sitemap.xml`.

## Páginas

| Arquivo | Para quem | O que faz |
|---|---|---|
| `index.html` | Bio do Instagram | Página de links: curso, consultoria, terapia, WhatsApp da Thaís e Instagram |
| `curso/index.html` | Psicólogas | Página de vendas do Carreira com Sentido (checkout Hotmart) |
| `consultoria/index.html` | Psicólogas | Inscrição na Consultoria 1:1 (formulário que envia ao Google Forms) |
| `terapia/index.html` | Pacientes adultos | Atendimento psicológico, lista de interesse (Google Forms) e indicação pelo WhatsApp |

## Como editar

- Textos: direto no HTML de cada página. Não use travessão; prefira vírgula, ponto ou dois-pontos.
- Links e imagens: sempre com caminho relativo (`assets/...` na raiz, `../assets/...` nas subpastas). Nunca comece com `/`.
- Visual: `assets/css/site.css` (cores da marca nas variáveis do topo).
- Comportamento: `assets/js/site.js` (UTMs, checkout, barra fixa, máscara de WhatsApp e formulários).
- Formulários: cada campo enviado ao Google Forms tem `data-entry="entry.XXXX"`; campos sem `data-entry` não são enviados.
- Imagens: `_catalogo/preparar_assets.py` gera os WebP e as imagens Open Graph a partir do ensaio (recortes e tamanhos no topo do arquivo) e copia os vídeos.
- Página de terapia: siga o Código de Ética e a resolução do CFP sobre publicidade (sem preço, sem promessa de resultado, sem depoimento de paciente).

## Rastreamento (GTM, Pixel da Meta, GA4)

No topo de `assets/js/site.js`:

```js
const CONFIG = { gtmId: "", metaPixelId: "", ga4Id: "" };
```

Preencha os IDs quando existirem; cada script só é carregado se o ID estiver preenchido. Os eventos vão para o `dataLayer`
(`begin_checkout`, `view_offer`, `generate_lead`) e, com o Pixel ativo, viram `InitiateCheckout`, `ViewContent` e `Lead`.

## Verificar

```sh
/Users/educloud/orquestra/.venv/bin/python _catalogo/preparar_assets.py   # gera imagens e copia vídeos
/Users/educloud/orquestra/.venv/bin/python tests/check.py                  # verificações
/Users/educloud/orquestra/.venv/bin/python _catalogo/prints.py             # prints em _catalogo/prints/
```

Para ver localmente: `python3 -m http.server` na raiz e abra http://localhost:8000/.

`tests/` e `_catalogo/` ficam fora do site publicado (`_config.yml`).
