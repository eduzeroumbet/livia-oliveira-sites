# livia-oliveira-sites
Landing pages da psicóloga Lívia Oliveira: curso Carreira com Sentido, consultoria e atendimento psicológico

Site estático (HTML, CSS e JS puros, sem build) publicado pelo GitHub Pages em
https://liviaoliveira.me/ (domínio próprio, definido no arquivo `CNAME`). O endereço antigo do GitHub Pages
redireciona automaticamente para o domínio. `robots.txt` aponta para o `sitemap.xml`.

## Páginas

| Arquivo | Para quem | O que faz |
|---|---|---|
| `index.html` | Bio do Instagram | Página de links: curso, quiz, calculadora, consultoria, terapia, WhatsApp da Thaís e Instagram |
| `curso/index.html` | Psicólogas (anúncios) | Versão A (`pgA`) da página de vendas do Carreira com Sentido (checkout Hotmart), com o vídeo da árvore. Página de destino dos anúncios da Meta e a página indexada (sitemap) |
| `curso/b/index.html` | Psicólogas (bio, links internos e anúncios) | Versão B (`pgB`): página do curso para a bio, os links internos do site e também anúncios (https://liviaoliveira.me/curso/b/). `noindex`, canonical para `/curso/` e fora do sitemap |
| `curso/versao-b/index.html` | Psicólogas (anúncios, teste A/B/C) | Versão C (`pgC`), hero "Fios que se organizam" (canvas em `curso/versao-b/hero-fios.js` e `hero-fios.css`). Usada nos anúncios do teste A/B/C; nenhuma página do site aponta para ela e o "Curso" do rodapé dela leva para `curso/b/`. `noindex`, canonical para `/curso/` e fora do sitemap |
| `curso/inscricao/index.html` | Psicólogas (vindas das 3 versões do curso) | Pré-página de inscrição (https://liviaoliveira.me/curso/inscricao/): pede só nome, e-mail e WhatsApp, guarda o contato e manda para o checkout da Hotmart com nome, e-mail e celular já preenchidos (sobra só CPF e pagamento). Comportamento em `curso/inscricao/script.js`. Sem menu, sem barra fixa e sem links de saída além do WhatsApp e do rodapé legal. `noindex`, canonical para `/curso/` e fora do sitemap |
| `consultoria/index.html` | Psicólogas | Inscrição na Consultoria 1:1 (formulário que envia ao Google Forms) |
| `terapia/index.html` | Pacientes adultos | Psicoterapia com agenda completa: lista de interesse (formulário que envia ao Google Forms, o mesmo de `terapia/b/`) e indicação de profissionais pelo WhatsApp da Thaís. Não há conversa inicial |
| `calculadora/index.html` | Psicólogas (anúncios) | Calculadora do valor da sessão (`pgCalc`), isca dos anúncios: custos, imposto, faltas e meta dão o custo por sessão, o valor mínimo e o ideal (conta em `calculadora/script.js`). No resultado, o contato opcional ("Quer ajuda para colocar esse valor em prática?", enviado à Lambda `livia-leads`), o convite para o curso (`curso/b/`, com as UTMs), o WhatsApp e o link para o quiz. No sitemap |
| `quiz/index.html` | Psicólogas (anúncios de Lead) | Quiz "Você está pronta para viver da clínica?" (`pgQuiz`): 5 perguntas de sim ou não, resultado na hora (faixa `base` com 0 ou 1 sim, `meio` com 2 ou 3, `pronta` com 4 ou 5), contato (nome, e-mail, WhatsApp e consentimento, enviado à Lambda `livia-leads`) e, depois do envio, o plano por pergunta e o convite para o curso (`curso/b/`) e o WhatsApp. Perguntas, textos e envio em `quiz/script.js`. No sitemap |
| `privacidade/index.html` | Todos (app da Meta e anúncios) | Política de Privacidade (LGPD), linkada no rodapé de todas as páginas. Carrega o `site.js` normalmente (com rastreamento) |
| `termos/index.html` | Todos | Termos de Uso (curso, consultoria, lista da terapia, uso do site), linkados no rodapé de todas as páginas ao lado da Política de privacidade. Carrega o `site.js` normalmente (com rastreamento) |

## Como editar

- Textos: direto no HTML de cada página. Não use travessão; prefira vírgula, ponto ou dois-pontos.
- Links e imagens: sempre com caminho relativo (`assets/...` na raiz, `../assets/...` nas subpastas). Nunca comece com `/`.
- Links para o curso: a bio (`index.html`) e os links internos do site (consultoria, terapia, rodapés) apontam para `curso/b/`. Não crie links para `curso/versao-b/` (só o próprio rodapé dela, que leva para `curso/b/`). A versão A (`curso/`) fica só para os anúncios (tráfego pago): use `https://liviaoliveira.me/curso/` nos anúncios da Meta e não crie links internos para ela.
- Visual: `assets/css/site.css`, `curso/style.css` e `terapia/style.css` (cores da marca nas variáveis do topo; veja a seção Visual).
- Comportamento: `assets/js/site.js` (UTMs, botões de compra, barra fixa, máscara de WhatsApp e formulários).
- Botões de compra do curso: têm a classe `checkout` e apontam para a pré-página com o `pg` da versão
  (`inscricao/?pg=pgA` em `curso/`, `../inscricao/?pg=pgB` em `curso/b/`, `../inscricao/?pg=pgC` em
  `curso/versao-b/`). Não crie links para `pay.hotmart.com` nas páginas do curso: só a pré-página monta o link.
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
no Pixel, viram `InitiateCheckout`, `ViewContent` e `Lead`. Os eventos `clique_comprar`, `cadastro_checkout`,
`escolha_pagamento`, `quiz_inicio`, `quiz_completo` e `contato_calculadora` viram os eventos personalizados
(`trackCustom`) `CliqueComprar`, `CadastroCheckout`, `EscolhaPagamento`, `QuizInicio`, `QuizCompleto` e
`ContatoCalculadora`.

As 3 versões do curso carregam o `site.js` com `data-pagina` na tag `<script>`, que diz qual versão vendeu:

| Sufixo | Página | Versão |
|---|---|---|
| `pgA` | `curso/` | A (anúncios) |
| `pgB` | `curso/b/` | B (bio, links internos e anúncios) |
| `pgC` | `curso/versao-b/` | C (anúncios, teste A/B/C) |
| `pgCalc` | `calculadora/` | Calculadora do valor da sessão (sem checkout) |
| `pgQuiz` | `quiz/` | Quiz "Você está pronta para viver da clínica?" (sem checkout) |
| `pgInsc` | `curso/inscricao/` | Pré-página de inscrição. Só identifica a página: não é sufixo de `sck` |

### Funil do curso: página do curso, inscrição, Hotmart preenchida

1. Página do curso (A, B ou C): o botão "Quero minha vaga"/"Quero me inscrever" (`a.checkout`) leva para
   `curso/inscricao/` com `pg=pgX` e a query da visita (`utm_*`, `fbclid`). O clique dispara `clique_comprar`
   (GA4/`dataLayer`) e `CliqueComprar` (Pixel, `trackCustom`, com `content_category` `pgX`). Não dispara mais
   `InitiateCheckout`.
2. Pré-página `curso/inscricao/`: nome, e-mail e WhatsApp (mais o honeypot `empresa`, fora da tela). No envio,
   `curso/inscricao/script.js`:
   - dispara o advanced matching do Pixel (`fbq('init', pixel, {em, ph, fn})`, o Pixel faz o hash; nada de dados
     pessoais no GA4 nem no `dataLayer`), `begin_checkout` (`InitiateCheckout`, 860 BRL, `content_name` "Carreira com
     Sentido", `content_category` `pgX`; é o único `InitiateCheckout` do funil do curso) e `cadastro_checkout`
     (`CadastroCheckout` no Pixel). Não dispara `Lead` (reservado à calculadora e ao quiz);
   - manda o cadastro por `fetch` POST JSON (`keepalive`) para a constante `CADASTRO_URL` no topo do script: Lambda
     `livia-leads` (Function URL, tabela DynamoDB `livia-leads`, região `sa-east-1`, CORS para
     https://liviaoliveira.me e localhost:8000). Campos: `nome`, `email`, `whatsapp` (só dígitos), `pagina` (`pgX`),
     `src`, `sck`, `utm_source`, `utm_medium`, `utm_campaign`, `utm_content`, `utm_term`, `url`, `consentimento`,
     `fbp`, `fbc` e `empresa` (honeypot; a Lambda ignora o cadastro se vier preenchido);
   - espera no máximo 1,5 s pelo cadastro e vai para a Hotmart de qualquer jeito (erro ou demora da Lambda nunca
     bloqueiam a compra).
3. Hotmart: `https://pay.hotmart.com/M100028858P?off=n2h6k72h&checkoutMode=10` + `src`, `sck`, os `utm_*` e o `fbclid`
   da visita + `name`, `email`, `phoneac` (DDD) e `phonenumber` (resto do número). A Hotmart preenche nome, e-mail,
   confirmação de e-mail e celular; sobra só CPF e pagamento.

No link da Hotmart, `src` = `utm_source|utm_medium|utm_campaign|utm_content` e `sck` = o mesmo + `|pgX`, com o
sufixo da versão da página de origem no fim (ex.: `sck=meta|paid|ccs_frio_criativos|V01|pgA`; sem UTM: `sck=direto|pgX`;
sem `pg` na URL da pré-página vale `pgB`; um `sck` já pronto na URL é usado como veio). Assim o relatório da Hotmart
mostra o anúncio e a versão da página de cada venda. Os eventos do curso levam `content_name` "Carreira com
Sentido" e `content_category` `pgX`. `view_offer`/`ViewContent` sai uma vez por carregamento, quando o topo da seção
`#oferta` passa da metade da tela. Na pré-página só sai o `PageView` padrão.

As páginas de terapia (`terapia/` e `terapia/b/`) carregam o `site.js` com `data-sem-rastreamento`: sem Pixel, GA4 nem
GTM (conteúdo de saúde pode fazer a Meta restringir o Pixel); formulário, máscara e validação funcionam igual. O
`tests/check.py` confere isso. Ao mudar o `site.js`, suba o `?v=` dele em todas as páginas.

A calculadora (`calculadora/`) não tem link da Hotmart nem `#oferta`, então não dispara `InitiateCheckout` nem o
`ViewContent` automático. O `calculadora/script.js` chama o `window.siteTrack`: `generate_lead` (`Lead`) com
`content_name` "calculadora_sessao" e `content_category` "calc" quando o resultado aparece pela primeira vez no
carregamento, e `view_offer` (`ViewContent`) com `content_name` "calculadora_para_curso" no clique em "Conhecer o curso".
O contato opcional depois do resultado dispara `contato_calculadora` (`ContatoCalculadora` no Pixel, `trackCustom`),
não outro `Lead`, e mostra "Pronto! A equipe da Lívia vai te chamar no WhatsApp." mesmo se a Lambda falhar.

### Quiz e contato da calculadora: Lambda livia-leads

O quiz (`quiz/`) não tem link da Hotmart nem `#oferta`. O `quiz/script.js` chama o `window.siteTrack`:

| Momento | GA4 / `dataLayer` | Pixel |
|---|---|---|
| Toque em "Começar o quiz" (uma vez por carregamento) | `quiz_inicio` | `QuizInicio` (`trackCustom`) |
| 5ª resposta (com `pontos` e `faixa`) | `quiz_completo` | `QuizCompleto` (`trackCustom`) |
| Envio do contato válido (`content_name` "quiz", `content_category` a faixa) | `generate_lead` | `Lead` (o único `Lead` da página; é o evento das campanhas de Lead do quiz) |
| Clique em "Conhecer o curso" (`content_name` "quiz_para_curso") | `view_offer` | `ViewContent` |

O quiz não dispara `InitiateCheckout`. O "Conhecer o curso" e o "Prefiro ver o curso agora" levam para `curso/b/` com os
`utm_*` da visita e `utm_content` acrescido de `_quiz_<faixa>` (sem UTM: `utm_source=site&utm_medium=quiz&
utm_campaign=ccs_quiz&utm_content=quiz_<faixa>`).

O contato do quiz e da calculadora usa o `window.siteContato` do `site.js` (constante `CADASTRO_URL` no `site.js`, a mesma
Lambda da pré-página): mesma validação e máscara da pré-página, consentimento obrigatório (checkbox com link para a
Política de privacidade), honeypot `empresa`, advanced matching do Pixel e espera de no máximo 1,5 s (erro ou demora
da Lambda nunca travam a página). Campos enviados: os mesmos da pré-página (`nome`, `email`, `whatsapp`, `pagina`,
`src`, `sck` com `|pgQuiz` ou `|pgCalc`, `utm_*`, `url`, `consentimento`, `fbp`, `fbc`, `empresa`; sem `forma`) mais:

| Campo | Quiz | Calculadora |
|---|---|---|
| `ferramenta` | `quiz` | `calculadora` |
| `resultado` | faixa: `base`, `meio` ou `pronta` | `minimo=<valor mínimo>;ideal=<valor ideal>;custo=<custo por sessão>` (reais arredondados, como na tela) |
| `respostas` | `S` ou `N` por pergunta, na ordem (ex.: `S,N,S,N,S`) | não vai |
| `pontos` | número de "sim", como texto (`"0"` a `"5"`) | não vai |

## Verificar

```sh
/Users/educloud/orquestra/.venv/bin/python _catalogo/preparar_assets.py   # gera imagens e copia vídeos
/Users/educloud/orquestra/.venv/bin/python tests/check.py                  # verificações
/Users/educloud/orquestra/.venv/bin/python tests/lista_terapia.py          # formulário da lista (terapia/) no Chromium, sem enviar ao Google
/Users/educloud/orquestra/.venv/bin/python tests/rastreamento_curso.py     # Pixel, GA4, links para a pré-página e CliqueComprar nas 3 versões do curso, no Chromium
/Users/educloud/orquestra/.venv/bin/python tests/inscricao.py              # pré-página: erros, cadastro (Lambda interceptada), link da Hotmart e eventos, no Chromium
/Users/educloud/orquestra/.venv/bin/python tests/calculadora.py            # conta, erros, Lead, contato, UTMs e 390px da calculadora, no Chromium
/Users/educloud/orquestra/.venv/bin/python tests/quiz.py                   # quiz: perguntas, Voltar, faixas, contato (Lambda interceptada), plano, eventos e prints, no Chromium
/Users/educloud/orquestra/.venv/bin/python _catalogo/prints.py             # prints em _catalogo/prints/
```

Para ver localmente: `python3 -m http.server` na raiz e abra http://localhost:8000/.

`tests/` e `_catalogo/` ficam fora do site publicado (`_config.yml`).
