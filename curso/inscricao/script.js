/* Pré-página de inscrição do curso (curso/inscricao/): forma de pagamento, nome, e-mail e WhatsApp antes da Hotmart.
 *
 * A pessoa escolhe primeiro a forma de pagamento (cartão, Pix ou boleto; escolha_pagamento/EscolhaPagamento pelo
 * site.js); só então abrem os campos. Os métodos do checkout da Hotmart dependem da escolha (HOTMART_ESCONDE).
 *
 * No envio: valida; guarda o contato na Lambda livia-leads (tabela DynamoDB livia-leads, sa-east-1) sem
 * bloquear a compra (espera no máximo 1,5 s); dispara begin_checkout (InitiateCheckout, o único do funil do
 * curso) e cadastro_checkout (CadastroCheckout) pelo site.js; e vai para a Hotmart com nome, e-mail e celular
 * já preenchidos. src/sck no mesmo formato das páginas do curso: src = utm_source|utm_medium|utm_campaign|
 * utm_content; sck = o mesmo + |pgX da página de origem (pg na URL; padrão pgB; sem UTM: sck=direto|pgX).
 */
var CADASTRO_URL = "https://nwmxltflulqvcxu7bdplodmyjm0yweuc.lambda-url.sa-east-1.on.aws/";
var CHECKOUT_URL = "https://pay.hotmart.com/M100028858P?off=n2h6k72h&checkoutMode=10";
var CADASTRO_ESPERA_MS = 1500;
/* Métodos escondidos no checkout da Hotmart (hide<Metodo>=1). A Hotmart sempre abre com um método marcado, não
 * aceita pré-selecionar o Pix e bloqueia de propósito o hideCreditCard: o cartão nunca some. Então a escolha é
 * feita aqui e o link esconde todo o resto: cartão = só a aba do cartão (some também o "usar dois cartões");
 * pix = cartão + Pix; boleto = cartão + boleto. */
var HOTMART_ESCONDE = ["hidePix", "hidePixAutomatic", "hideBillet", "hideNupay", "hideMultipleCards", "hidePaypal",
  "hideApplePay", "hideGooglePay", "hideVirtualCard", "hideMercadoPago", "hideHybrid", "hideDirectDebit",
  "hideHotmartInstallments"];
var HOTMART_MOSTRA = { cartao: "", pix: "hidePix", boleto: "hideBillet" };
var FORMAS = {
  cartao: {
    botao: "Continuar para o pagamento no cartão",
    dica: "Na próxima tela, a Hotmart já mostra só o cartão. Seus dados já vão preenchidos: falta o CPF e os dados do cartão."
  },
  pix: {
    botao: "Continuar para o pagamento com Pix",
    dica: "Na próxima tela, toque em Pix para gerar o código. Seus dados já vão preenchidos: falta só o CPF."
  },
  boleto: {
    botao: "Continuar para o pagamento com boleto",
    dica: "Na próxima tela, toque em Boleto para gerar o boleto. Seus dados já vão preenchidos: falta só o CPF."
  }
};

(function () {
  "use strict";

  var form = document.getElementById("inscricao");
  if (!form) return;

  /* ---------- Origem da visita: utm_*, fbclid, src, sck e pg vindos da página do curso ---------- */
  var visit = new URLSearchParams(location.search);
  var PAGINAS = ["pgA", "pgB", "pgC"];
  var sckPronto = visit.get("sck") || "";
  var pg = visit.get("pg");
  if (PAGINAS.indexOf(pg) < 0) {
    var doSck = sckPronto.match(/\|(pg[ABC])$/);
    pg = doSck ? doSck[1] : "pgB";
  }
  var src = visit.get("src") || ["utm_source", "utm_medium", "utm_campaign", "utm_content"]
    .map(function (k) { return visit.get(k); })
    .filter(Boolean)
    .join("|");
  var sck = sckPronto || (src || "direto") + "|" + pg;

  /* ---------- Forma de pagamento: os campos só abrem depois da escolha ---------- */
  var grupo = form.querySelector(".insc-formas");
  var dadosBloco = document.getElementById("insc-dados");
  var dica = document.getElementById("insc-dica");
  var button = form.querySelector('button[type="submit"]');
  var label = button.textContent;
  var porToque = false;

  function forma() {
    var marcada = form.querySelector('input[name="forma"]:checked');
    return marcada ? marcada.value : "";
  }

  function setErroForma(message) {
    form.querySelector('[data-error-for="forma"]').textContent = message || "";
    if (message) grupo.setAttribute("aria-invalid", "true");
    else grupo.removeAttribute("aria-invalid");
  }

  /* só move o foco para o nome quando a escolha é por toque/clique: pelas setas do teclado a pessoa ainda está
   * navegando entre as opções */
  grupo.addEventListener("pointerdown", function () { porToque = true; });
  grupo.addEventListener("keydown", function () { porToque = false; });

  /* mostra os campos e ajusta o botão e a dica; devolve true se os campos estavam fechados */
  function mostraForma(f) {
    setErroForma("");
    label = FORMAS[f].botao;
    if (!button.disabled) button.textContent = label;
    dica.textContent = FORMAS[f].dica;
    var abriu = dadosBloco.hidden;
    dadosBloco.hidden = false;
    return abriu;
  }

  grupo.addEventListener("change", function () {
    var f = forma();
    if (!FORMAS[f]) return;
    if (mostraForma(f) && porToque) {
      form.elements.nome.focus({ preventScroll: true });
      var suave = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      dadosBloco.scrollIntoView({ behavior: suave ? "smooth" : "auto", block: "nearest" });
    }
    porToque = false;
    if (window.siteTrack) window.siteTrack("escolha_pagamento", { content_category: pg, payment_type: f });
  });

  /* navegador que restaura o formulário ao voltar (opção já marcada): abre os campos sem novo evento */
  if (FORMAS[forma()]) mostraForma(forma());

  /* ---------- Validação (mesma marcação e mensagens do site.js) ---------- */
  function setError(name, message) {
    var out = form.querySelector('[data-error-for="' + name + '"]');
    if (out) out.textContent = message || "";
    var el = form.elements[name];
    if (message) el.setAttribute("aria-invalid", "true");
    else el.removeAttribute("aria-invalid");
  }

  function digitos(v) { return v.replace(/\D/g, ""); }

  function validate() {
    var firstInvalid = null;
    function fail(name, message) {
      setError(name, message);
      if (!firstInvalid) firstInvalid = form.elements[name];
    }
    ["nome", "email", "whatsapp"].forEach(function (n) { setError(n, ""); });

    var letras = form.elements.nome.value.match(/[A-Za-zÀ-ÖØ-öø-ÿ]/g) || [];
    if (letras.length < 2) fail("nome", "Escreva o seu nome.");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.elements.email.value.trim())) fail("email", "Confira o e-mail.");
    var d = digitos(form.elements.whatsapp.value);
    if (d.length < 10 || d.length > 11) fail("whatsapp", "Informe o WhatsApp com DDD, por exemplo (51) 99999-9999.");

    if (firstInvalid) firstInvalid.focus();
    return !firstInvalid;
  }

  ["nome", "email", "whatsapp"].forEach(function (n) {
    form.elements[n].addEventListener("input", function () {
      if (form.elements[n].getAttribute("aria-invalid")) setError(n, "");
    });
  });

  function cookie(nome) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + nome + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  /* ---------- Link final da Hotmart ---------- */
  function linkHotmart(nome, email, whats, f) {
    var url = new URL(CHECKOUT_URL);
    if (src) url.searchParams.set("src", src);
    url.searchParams.set("sck", sck);
    visit.forEach(function (v, k) {
      if (/^utm_/.test(k) || k === "fbclid") url.searchParams.set(k, v);
    });
    url.searchParams.set("name", nome);
    url.searchParams.set("email", email);
    url.searchParams.set("phoneac", whats.slice(0, 2));
    url.searchParams.set("phonenumber", whats.slice(2));
    HOTMART_ESCONDE.forEach(function (k) {
      if (k !== HOTMART_MOSTRA[f]) url.searchParams.set(k, "1");
    });
    /* espaço como %20 (o URLSearchParams usa "+"; um "+" digitado já sai como %2B) */
    return url.toString().replace(/\+/g, "%20");
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (button.disabled) return;
    var f = forma();
    if (!FORMAS[f]) {
      /* não deve acontecer (o botão só aparece depois da escolha), mas por segurança */
      setErroForma("Escolha a forma de pagamento.");
      form.querySelector('input[name="forma"]').focus();
      return;
    }
    if (!validate()) return;
    button.disabled = true;
    button.textContent = "Abrindo o pagamento...";

    var nome = form.elements.nome.value.trim().replace(/\s+/g, " ");
    var email = form.elements.email.value.trim().toLowerCase();
    var whats = digitos(form.elements.whatsapp.value);
    var destino = linkHotmart(nome, email, whats, f);

    /* Rastreamento: advanced matching só no Pixel; GA4 e dataLayer sem dados pessoais. Sem Lead aqui
     * (Lead é da calculadora, que tem campanha própria otimizando Lead). */
    if (window.siteIdentify) window.siteIdentify({ em: email, ph: "55" + whats, fn: nome.split(" ")[0].toLowerCase() });
    if (window.siteTrack) {
      window.siteTrack("begin_checkout", { value: 860, currency: "BRL", content_name: "Carreira com Sentido", content_category: pg, payment_type: f });
      window.siteTrack("cadastro_checkout", { content_category: pg, payment_type: f });
    }

    var dados = {
      nome: nome,
      email: email,
      whatsapp: whats,
      pagina: pg,
      forma: f,
      src: src,
      sck: sck,
      utm_source: visit.get("utm_source") || "",
      utm_medium: visit.get("utm_medium") || "",
      utm_campaign: visit.get("utm_campaign") || "",
      utm_content: visit.get("utm_content") || "",
      utm_term: visit.get("utm_term") || "",
      url: location.href,
      consentimento: "sim",
      fbp: cookie("_fbp"),
      fbc: cookie("_fbc"),
      empresa: form.elements.empresa.value
    };

    /* O cadastro nunca bloqueia a compra: no máximo 1,5 s de espera e vai para a Hotmart mesmo com erro */
    var envio;
    try {
      envio = fetch(CADASTRO_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(dados),
        keepalive: true
      }).catch(function () {});
    } catch (err) {
      envio = Promise.resolve();
    }
    var espera = new Promise(function (resolve) { setTimeout(resolve, CADASTRO_ESPERA_MS); });
    Promise.race([envio, espera]).then(function () { location.href = destino; });
  });

  /* Voltar da Hotmart pelo botão do navegador (página restaurada do cache): botão ativo de novo */
  window.addEventListener("pageshow", function (e) {
    if (e.persisted) {
      button.disabled = false;
      button.textContent = label;
    }
  });
})();
