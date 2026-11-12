/* Lívia Oliveira: páginas de materiais gratuitos (materiais/<slug>/). Depende do site.js (window.siteTrack,
 * window.siteIdentify e window.siteContato). O slug vem do data-material do <main>.
 *
 * Os itens de .mat-trava ficam borrados (CSS) e inertes até o cadastro. O cadastro vale para os 6 materiais:
 * grava localStorage "livia_mat_ok" = "1" e o script do <head> já abre a página liberada (html.mat-ok) nas
 * próximas visitas. O envio vai para a Lambda livia-leads (pagina pgMat, ferramenta material, resultado = slug)
 * e espera no máximo 0,8 s: o material abre mesmo com erro ou demora.
 * Liberação por link: com ?acesso=wa na URL (link que a Lia manda pelo WhatsApp para quem já se cadastrou e abre
 * em outro navegador), o script do <head> já aplica html.mat-ok e tenta gravar o localStorage; aqui grava de novo
 * e dispara material_liberado_link ({material}, só GA4/dataLayer).
 * Eventos: material_view (ViewContent, content_name "material_<slug>") ao carregar; generate_lead (Lead, com
 * advanced matching) só no envio; material_copiar (MaterialCopiar, {material}) a cada cópia; no "Baixar PDF",
 * material_pdf (MaterialPDF, {material, modo: "download"}) com o material liberado (no navegador embutido, a cada
 * opção do painel: modo "whatsapp" | "externo" | "ver") ou material_pdf_bloqueado ({material}) quando ainda falta o
 * cadastro; view_offer (ViewContent, content_name
 * "material_para_curso") no clique em "Conhecer o curso". Sem InitiateCheckout.
 */
(function () {
  "use strict";

  var CHAVE = "livia_mat_ok";
  var main = document.querySelector("[data-material]");
  if (!main) return;
  var slug = main.getAttribute("data-material");
  var raiz = document.documentElement;
  var trava = document.getElementById("mat-trava");
  var form = document.getElementById("contato");
  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var enviado = false;

  function track(event, params) {
    if (window.siteTrack) window.siteTrack(event, params);
  }

  function lido() {
    try { return localStorage.getItem(CHAVE) === "1"; } catch (e) { return false; }
  }

  function grava() {
    try { localStorage.setItem(CHAVE, "1"); } catch (e) { /* modo privado: libera só nesta visita */ }
  }

  /* Liberado: tira o borrado (CSS) e o inert; bloqueado: nada do trecho fechado recebe foco ou clique */
  function aplica(ok) {
    raiz.classList.toggle("mat-ok", ok);
    if (trava) {
      trava.inert = !ok;
      if (ok) trava.removeAttribute("aria-hidden");
      else trava.setAttribute("aria-hidden", "true");
    }
    if (form) form.hidden = ok;
  }

  /* ?acesso=wa (ou &acesso=wa): libera como o cadastro, mesmo sem localStorage (modo privado, navegador do Instagram) */
  var porLink = /[?&]acesso=wa(&|$)/.test(location.search);
  if (porLink) grava();

  aplica(porLink || raiz.classList.contains("mat-ok") || lido());
  track("material_view", { content_name: "material_" + slug });
  if (porLink) track("material_liberado_link", { material: slug });

  /* ---------- Cadastro ---------- */
  if (form && window.siteContato) {
    var contato = window.siteContato;
    var button = form.querySelector('button[type="submit"]');
    contato.prepara(form);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (enviado || !contato.valida(form)) return;
      enviado = true;
      button.disabled = true;
      button.textContent = "Enviando...";

      var dados = contato.dados(form, { ferramenta: "material", resultado: slug });
      /* advanced matching só no Pixel (o Pixel faz o hash); GA4 e dataLayer sem dados pessoais */
      if (window.siteIdentify) window.siteIdentify({ em: dados.email, ph: "55" + dados.whatsapp, fn: dados.nome.split(" ")[0].toLowerCase() });
      track("generate_lead", { content_name: "material_" + slug });
      contato.envia(dados).then(libera, libera);
    });
  }

  function libera() {
    grava();
    aplica(true);
    if (!trava) return;
    var primeiro = trava.firstElementChild;
    if (primeiro) {
      primeiro.setAttribute("tabindex", "-1");
      primeiro.scrollIntoView({ behavior: reduz ? "auto" : "smooth", block: "start" });
      primeiro.focus({ preventScroll: true });
    }
  }

  /* ---------- Copiar: texto puro da mensagem, com os [campos] ---------- */
  function copia(texto) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(texto).catch(function () { return copiaAntigo(texto); });
    }
    return copiaAntigo(texto);
  }

  function copiaAntigo(texto) {
    var area = document.createElement("textarea");
    area.value = texto;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-9999px";
    document.body.appendChild(area);
    area.select();
    try { document.execCommand("copy"); } catch (e) { /* sem cópia: o texto continua na tela */ }
    document.body.removeChild(area);
    return Promise.resolve();
  }

  document.querySelectorAll(".mat-copiar").forEach(function (b) {
    var timer = 0;
    b.addEventListener("click", function () {
      var alvo = b.closest(".mat-msg").querySelector(".mat-msg__texto");
      var texto = alvo.textContent.replace(/\s+/g, " ").trim();
      copia(texto).then(function () {
        b.textContent = "Copiado";
        b.classList.add("is-copiado");
        clearTimeout(timer);
        timer = setTimeout(function () {
          b.textContent = "Copiar";
          b.classList.remove("is-copiado");
        }, 2000);
      });
      track("material_copiar", { material: slug });
    });
  });

  /* ---------- Checklist ético: os 10 marcados mostram a frase final ---------- */
  var pode = document.getElementById("mat-pode");
  var caixas = document.querySelectorAll('.mat-check input[type="checkbox"]');
  if (pode && caixas.length) {
    var confere = function () {
      var marcadas = Array.prototype.filter.call(caixas, function (c) { return c.checked; }).length;
      pode.hidden = marcadas !== caixas.length;
    };
    caixas.forEach(function (c) { c.addEventListener("change", confere); });
    confere();
  }

  /* ---------- Baixar PDF ----------
   * Bloqueado: leva ao cadastro com o aviso de que o PDF completo vem depois dele.
   * Liberado: baixa o PDF pronto de materiais/pdf/ (_catalogo/pdfs.py) como Livia-Oliveira-<slug>.pdf, no computador
   * e no celular (inclusive no navegador do WhatsApp). No navegador do Instagram/Facebook (e outros embutidos) não dá
   * para salvar arquivo: abre um painel abaixo do botão com WhatsApp da Lia, abrir no navegador do celular, ver o PDF
   * ali e copiar o link. A folha de impressão (@media print) continua para quem usa Ctrl+P. */
  var EMBUTIDO = /FBAN|FBAV|FB_IAB|FBIOS|Instagram|; wv\)|Line\//i;
  var URL_PDF = "https://liviaoliveira.me/materiais/pdf/" + slug + ".pdf";
  var TITULOS = {
    mensagens: "8 mensagens prontas para o WhatsApp da clínica",
    faltas: "Política de faltas e pagamentos",
    etica: "Checklist ético para o Instagram",
    reajuste: "Como reajustar o valor da sessão",
    posts: "30 ideias de posts",
    indicacoes: "Mensagens para apresentar o trabalho a médicos e colegas"
  };

  function baixa() {
    var a = document.createElement("a");
    a.href = "../pdf/" + slug + ".pdf";
    a.download = "Livia-Oliveira-" + slug + ".pdf";
    a.hidden = true;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  /* Android: intent do Chrome (sem Chrome, cai no fallback); iPhone/iPad: esquema do Safari; outros: o PDF numa aba nova */
  function linkExterno() {
    var ua = navigator.userAgent;
    var caminho = "liviaoliveira.me/materiais/pdf/" + slug + ".pdf";
    if (/Android/i.test(ua)) {
      return "intent://" + caminho + "#Intent;scheme=https;package=com.android.chrome;S.browser_fallback_url=" + encodeURIComponent(URL_PDF) + ";end";
    }
    if (/iPhone|iPad|iPod/i.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return "x-safari-https://" + caminho;
    return URL_PDF;
  }

  var painel = null;

  function montaPainel(botao) {
    painel = document.createElement("div");
    painel.className = "mat-pdf-painel";
    painel.id = "mat-pdf-painel";
    painel.setAttribute("role", "region");
    painel.setAttribute("aria-labelledby", "mat-pdf-painel-titulo");
    painel.tabIndex = -1;
    painel.innerHTML =
      '<button type="button" class="mat-pdf-painel__fechar" aria-label="Fechar">&times;</button>' +
      '<h2 class="mat-pdf-painel__titulo" id="mat-pdf-painel-titulo">O navegador do Instagram não deixa salvar arquivos</h2>' +
      '<a class="mat-pdf-op mat-pdf-op--wa" data-modo="whatsapp" target="_blank" rel="noopener">Receber o PDF no WhatsApp</a>' +
      '<a class="mat-pdf-op" data-modo="externo">Abrir no navegador do celular</a>' +
      '<p class="mat-pdf-painel__dica">Se não abrir, toque nos três pontinhos no canto da tela e escolha Abrir no navegador.</p>' +
      '<a class="mat-pdf-op" data-modo="ver">Ver o PDF aqui</a>' +
      '<button type="button" class="mat-pdf-op mat-pdf-op--copiar">Copiar link do PDF</button>' +
      '<p class="mat-pdf-painel__copiado" role="status" aria-live="polite"></p>';

    var titulo = TITULOS[slug] || document.querySelector("h1").textContent.replace(/\s+/g, " ").trim();
    painel.querySelector('[data-modo="whatsapp"]').href = "https://wa.me/5511910607651?text=" + encodeURIComponent("Oi! Quero o PDF do material " + titulo);
    var externo = painel.querySelector('[data-modo="externo"]');
    var destino = linkExterno();
    externo.href = destino;
    if (destino === URL_PDF) { externo.target = "_blank"; externo.rel = "noopener"; }
    painel.querySelector('[data-modo="ver"]').href = "../pdf/" + slug + ".pdf";

    painel.addEventListener("click", function (e) {
      var op = e.target.closest("[data-modo]");
      if (op) track("material_pdf", { material: slug, modo: op.getAttribute("data-modo") });
    });
    painel.addEventListener("keydown", function (e) {
      if (e.key === "Escape") fechaPainel(botao);
    });
    painel.querySelector(".mat-pdf-painel__fechar").addEventListener("click", function () { fechaPainel(botao); });

    var aviso = painel.querySelector(".mat-pdf-painel__copiado");
    painel.querySelector(".mat-pdf-op--copiar").addEventListener("click", function () {
      copia(URL_PDF).then(function () {
        aviso.textContent = "Link copiado. Cole no Safari ou no Chrome.";
      });
    });

    botao.setAttribute("aria-controls", painel.id);
    botao.parentNode.insertBefore(painel, botao.nextSibling);
  }

  function abrePainel(botao) {
    if (!painel) montaPainel(botao);
    painel.hidden = false;
    botao.setAttribute("aria-expanded", "true");
    painel.focus({ preventScroll: true });
    painel.scrollIntoView({ behavior: reduz ? "auto" : "smooth", block: "nearest" });
  }

  function fechaPainel(botao) {
    painel.hidden = true;
    botao.setAttribute("aria-expanded", "false");
    botao.focus();
  }

  function pedeCadastro() {
    if (!form) return;
    var aviso = form.querySelector(".mat-libera__pdf");
    if (!aviso) {
      aviso = document.createElement("p");
      aviso.className = "mat-libera__pdf";
      var envio = form.querySelector('button[type="submit"]');
      envio.parentNode.insertBefore(aviso, envio);
    }
    aviso.textContent = "Cadastre-se grátis para baixar o material completo em PDF.";
    form.scrollIntoView({ behavior: reduz ? "auto" : "smooth", block: "start" });
    var campo = form.querySelector("input");
    if (campo) campo.focus({ preventScroll: true });
  }

  var pdf = document.getElementById("mat-pdf");
  if (pdf) {
    pdf.addEventListener("click", function () {
      if (!raiz.classList.contains("mat-ok")) {
        track("material_pdf_bloqueado", { material: slug });
        pedeCadastro();
        return;
      }
      if (EMBUTIDO.test(navigator.userAgent)) {
        if (painel && !painel.hidden) fechaPainel(pdf);
        else abrePainel(pdf);
        return;
      }
      track("material_pdf", { material: slug, modo: "download" });
      baixa();
    });
  }

  /* ---------- Curso ---------- */
  var curso = document.getElementById("mat-curso");
  if (curso) {
    curso.addEventListener("click", function () {
      track("view_offer", { content_name: "material_para_curso" });
    });
  }
})();
