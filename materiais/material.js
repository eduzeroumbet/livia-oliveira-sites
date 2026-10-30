/* Lívia Oliveira: páginas de materiais gratuitos (materiais/<slug>/). Depende do site.js (window.siteTrack,
 * window.siteIdentify e window.siteContato). O slug vem do data-material do <main>.
 *
 * Os itens de .mat-trava ficam borrados (CSS) e inertes até o cadastro. O cadastro vale para os 6 materiais:
 * grava localStorage "livia_mat_ok" = "1" e o script do <head> já abre a página liberada (html.mat-ok) nas
 * próximas visitas. O envio vai para a Lambda livia-leads (pagina pgMat, ferramenta material, resultado = slug)
 * e espera no máximo 0,8 s: o material abre mesmo com erro ou demora.
 * Eventos: material_view (ViewContent, content_name "material_<slug>") ao carregar; generate_lead (Lead, com
 * advanced matching) só no envio; material_copiar (MaterialCopiar, {material}) a cada cópia; material_pdf
 * (MaterialPDF) no "Salvar em PDF"; view_offer (ViewContent, content_name "material_para_curso") no clique em
 * "Conhecer o curso". Sem InitiateCheckout.
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

  aplica(raiz.classList.contains("mat-ok") || lido());
  track("material_view", { content_name: "material_" + slug });

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

  /* ---------- Salvar em PDF ---------- */
  var pdf = document.getElementById("mat-pdf");
  if (pdf) {
    pdf.addEventListener("click", function () {
      track("material_pdf", { material: slug });
      window.print();
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
