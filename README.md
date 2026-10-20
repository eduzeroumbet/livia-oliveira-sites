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
- Visual: `assets/css/site.css`, `curso/style.css` e `terapia/style.css` (cores da marca nas variáveis do topo; veja a seção Visual).
- Comportamento: `assets/js/site.js` (UTMs, checkout, barra fixa, máscara de WhatsApp e formulários).
- Formulários: cada campo enviado ao Google Forms tem `data-entry="entry.XXXX"`; campos sem `data-entry` não são enviados.
- Imagens: `_catalogo/preparar_assets.py` gera os WebP e as imagens Open Graph a partir do ensaio (recortes e tamanhos no topo do arquivo) e copia os vídeos.
- Página de terapia: siga o Código de Ética e a resolução do CFP sobre publicidade (sem preço, sem promessa de resultado, sem depoimento de paciente).

## Visual

Identidade do site da Lívia, https://carreiracomsentido.com.br/ (cores convertidas de oklch para hex):

| Cor | Hex | Uso |
|---|---|---|
| Vinho | `#6E172C` | Cor principal: títulos, botão principal, seções escuras |
| Rosé | `#DBA8AD` | Destaques e itálicos sobre fundo escuro; botão sobre fundo vinho (texto vinho) |
| Azul petróleo | `#264056` | Trecho itálico dos títulos no fundo claro; seções escuras alternativas |
| Creme | `#FCFAF6` | Fundo base e texto sobre fundo escuro |
| Texto | `#1E1212` | Texto corrido |
| Texto suave | `#605151` | Texto de apoio |
| Realce | `#F5ECEA` | Fundo de cards e seções de realce |
| Borda | `#E5D3D2` | Bordas e divisórias |

- Gradientes (com hex de reserva antes do oklch): vinho `oklch(32% .12 10)` a `oklch(40% .13 18)`, petróleo
  `oklch(32% .05 245)` a `oklch(40% .06 240)`, sempre a 135°.
- Seções alternam creme, vinho (texto creme, destaques em rosé) e petróleo (texto creme).
- Botões em pílula: principal vinho com texto creme; secundário com borda vinho a 30% e texto vinho; sobre fundo
  vinho ou petróleo, rosé com texto vinho (hover creme). Cards com raio de .5rem.
- Títulos (h1 a h3 e itálicos de destaque): Noto Serif Display extra condensada (`font-stretch: 62.5%`), peso 500,
  `line-height: 1.02`, carregada do Google Fonts. O trecho final do título vai em `<em>`: itálico numa linha
  própria, petróleo no fundo claro e rosé no escuro. O espaçamento entre letras fica na variável `--titulo-ls`.
- Texto: Helvetica Neue (fonte do sistema, sem download), com `letter-spacing: -.015em`.
- Favicon (`assets/img/favicon.svg`): vinho com o monograma em creme. Os PNG e o ICO não têm script de geração.

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
