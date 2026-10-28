# livia-oliveira-sites
Landing pages da psicóloga Lívia Oliveira: curso Carreira com Sentido, consultoria e atendimento psicológico

Site estático (HTML, CSS e JS puros, sem build) publicado pelo GitHub Pages em
https://liviaoliveira.me/ (domínio próprio, definido no arquivo `CNAME`). O endereço antigo do GitHub Pages
redireciona automaticamente para o domínio. `robots.txt` aponta para o `sitemap.xml`.

## Páginas

| Arquivo | Para quem | O que faz |
|---|---|---|
| `index.html` | Bio do Instagram | Página de links: curso, consultoria, terapia, WhatsApp da Thaís e Instagram |
| `curso/index.html` | Psicólogas (anúncios) | Versão A (`pgA`) da página de vendas do Carreira com Sentido (checkout Hotmart), com o vídeo da árvore. Página de destino dos anúncios da Meta e a página indexada (sitemap) |
| `curso/b/index.html` | Psicólogas (bio, links internos e anúncios) | Versão B (`pgB`): página do curso para a bio, os links internos do site e também anúncios (https://liviaoliveira.me/curso/b/). `noindex`, canonical para `/curso/` e fora do sitemap |
| `curso/versao-b/index.html` | Psicólogas (anúncios, teste A/B/C) | Versão C (`pgC`), hero "Fios que se organizam" (canvas em `curso/versao-b/hero-fios.js` e `hero-fios.css`). Usada nos anúncios do teste A/B/C; nenhuma página do site aponta para ela e o "Curso" do rodapé dela leva para `curso/b/`. `noindex`, canonical para `/curso/` e fora do sitemap |
| `consultoria/index.html` | Psicólogas | Inscrição na Consultoria 1:1 (formulário que envia ao Google Forms) |
| `terapia/index.html` | Pacientes adultos | Psicoterapia com agenda completa: lista de interesse (formulário que envia ao Google Forms, o mesmo de `terapia/b/`) e indicação de profissionais pelo WhatsApp da Thaís. Não há conversa inicial |
| `calculadora/index.html` | Psicólogas (anúncios) | Calculadora do valor da sessão (`pgCalc`), isca dos anúncios: custos, imposto, faltas e meta dão o custo por sessão, o valor mínimo e o ideal (conta em `calculadora/script.js`). No resultado, o convite para o curso (`curso/b/`, com as UTMs) e o WhatsApp. No sitemap |
| `privacidade/index.html` | Todos (app da Meta e anúncios) | Política de Privacidade (LGPD), linkada no rodapé de todas as páginas. Carrega o `site.js` normalmente (com rastreamento) |
| `termos/index.html` | Todos | Termos de Uso (curso, consultoria, lista da terapia, uso do site), linkados no rodapé de todas as páginas ao lado da Política de privacidade. Carrega o `site.js` normalmente (com rastreamento) |

## Como editar

- Textos: direto no HTML de cada página. Não use travessão; prefira vírgula, ponto ou dois-pontos.
- Links e imagens: sempre com caminho relativo (`assets/...` na raiz, `../assets/...` nas subpastas). Nunca comece com `/`.
- Links para o curso: a bio (`index.html`) e os links internos do site (consultoria, terapia, rodapés) apontam para `curso/b/`. Não crie links para `curso/versao-b/` (só o próprio rodapé dela, que leva para `curso/b/`). A versão A (`curso/`) fica só para os anúncios (tráfego pago): use `https://liviaoliveira.me/curso/` nos anúncios da Meta e não crie links internos para ela.
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
const CONFIG = { gtmId: "", metaPixelId: "1197036460960933", ga4Id: "G-XH74VZSNZ2" };
```

Cada script só é carregado se o ID estiver preenchido (Pixel da Meta da conta de anúncios da Lívia e GA4 da propriedade
559914633; sem GTM). Os eventos vão para o `dataLayer` (`begin_checkout`, `view_offer`, `generate_lead`), para o GA4 e,
no Pixel, viram `InitiateCheckout`, `ViewContent` e `Lead`.

As 3 versões do curso carregam o `site.js` com `data-pagina` na tag `<script>`, que diz qual versão vendeu:

| Sufixo | Página | Versão |
|---|---|---|
| `pgA` | `curso/` | A (anúncios) |
| `pgB` | `curso/b/` | B (bio, links internos e anúncios) |
| `pgC` | `curso/versao-b/` | C (anúncios, teste A/B/C) |
| `pgCalc` | `calculadora/` | Calculadora do valor da sessão (sem checkout) |

Nos links da Hotmart, `src` = `utm_source|utm_medium|utm_campaign|utm_content` e `sck` = o mesmo + `|pgX`, com o
sufixo da versão no fim (ex.: `sck=meta|paid|ccs_frio_criativos|V01|pgA`; sem UTM: `sck=direto|pgX`). Assim o relatório
da Hotmart mostra o anúncio e a versão da página de cada venda. Os eventos do curso levam `content_name` "Carreira com
Sentido" e `content_category` `pgX`. `view_offer`/`ViewContent` sai uma vez por carregamento, quando o topo da seção
`#oferta` passa da metade da tela.

As páginas de terapia (`terapia/` e `terapia/b/`) carregam o `site.js` com `data-sem-rastreamento`: sem Pixel, GA4 nem
GTM (conteúdo de saúde pode fazer a Meta restringir o Pixel); formulário, máscara e validação funcionam igual. O
`tests/check.py` confere isso. Ao mudar o `site.js`, suba o `?v=` dele em todas as páginas.

A calculadora (`calculadora/`) não tem link da Hotmart nem `#oferta`, então não dispara `InitiateCheckout` nem o
`ViewContent` automático. O `calculadora/script.js` chama o `window.siteTrack`: `generate_lead` (`Lead`) com
`content_name` "calculadora_sessao" e `content_category` "calc" quando o resultado aparece pela primeira vez no
carregamento, e `view_offer` (`ViewContent`) com `content_name` "calculadora_para_curso" no clique em "Conhecer o curso".

## Verificar

```sh
/Users/educloud/orquestra/.venv/bin/python _catalogo/preparar_assets.py   # gera imagens e copia vídeos
/Users/educloud/orquestra/.venv/bin/python tests/check.py                  # verificações
/Users/educloud/orquestra/.venv/bin/python tests/lista_terapia.py          # formulário da lista (terapia/) no Chromium, sem enviar ao Google
/Users/educloud/orquestra/.venv/bin/python tests/rastreamento_curso.py     # Pixel, GA4, src/sck e eventos nas 3 versões do curso, no Chromium
/Users/educloud/orquestra/.venv/bin/python tests/calculadora.py            # conta, erros, Lead, UTMs e 390px da calculadora, no Chromium
/Users/educloud/orquestra/.venv/bin/python _catalogo/prints.py             # prints em _catalogo/prints/
```

Para ver localmente: `python3 -m http.server` na raiz e abra http://localhost:8000/.

`tests/` e `_catalogo/` ficam fora do site publicado (`_config.yml`).
