/* Pré-página de inscrição do curso (curso/inscricao/): nome, e-mail e WhatsApp antes da Hotmart.
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
  function linkHotmart(nome, email, whats) {
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
    /* espaço como %20 (o URLSearchParams usa "+"; um "+" digitado já sai como %2B) */
    return url.toString().replace(/\+/g, "%20");
  }

  var button = form.querySelector('button[type="submit"]');
  var label = button.textContent;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (button.disabled || !validate()) return;
    button.disabled = true;
    button.textContent = "Abrindo o pagamento...";

    var nome = form.elements.nome.value.trim().replace(/\s+/g, " ");
    var email = form.elements.email.value.trim().toLowerCase();
    var whats = digitos(form.elements.whatsapp.value);
    var destino = linkHotmart(nome, email, whats);

    /* Rastreamento: advanced matching só no Pixel; GA4 e dataLayer sem dados pessoais. Sem Lead aqui
     * (Lead é da calculadora, que tem campanha própria otimizando Lead). */
    if (window.siteIdentify) window.siteIdentify({ em: email, ph: "55" + whats, fn: nome.split(" ")[0].toLowerCase() });
    if (window.siteTrack) {
      window.siteTrack("begin_checkout", { value: 860, currency: "BRL", content_name: "Carreira com Sentido", content_category: pg });
      window.siteTrack("cadastro_checkout", { content_category: pg });
    }

    var dados = {
      nome: nome,
      email: email,
      whatsapp: whats,
      pagina: pg,
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
