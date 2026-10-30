/* Lívia Oliveira: JS compartilhado (sem dependências) */

/*
 * IDs de rastreamento. Cada script só é carregado se o ID estiver preenchido (vazio = desligado).
 *   gtmId:       vazio (sem Google Tag Manager; o GA4 vai direto)
 *   metaPixelId: "1197036460960933"  (Pixel da Meta da conta de anúncios da Lívia: PageView em toda página)
 *   ga4Id:       "G-XH74VZSNZ2"  (GA4 direto, propriedade 559914633: config com page_view em toda página)
 * As páginas do curso dizem qual versão são no atributo data-pagina da tag <script> (pgA = curso/,
 * pgB = curso/b/, pgC = curso/versao-b/); o valor vai no pg do link da pré-página de inscrição (e dali no sck
 * da Hotmart) e no content_category dos eventos. Calculadora (pgCalc), quiz (pgQuiz) e materiais gratuitos (pgMat)
 * usam o data-pagina no pagina e no sck do contato enviado à Lambda (window.siteContato).
 * Páginas com data-sem-rastreamento na tag <script> (as de terapia: conteúdo de saúde) não carregam GTM, GA4
 * nem Pixel; o resto (UTMs, máscara, validação e envio dos formulários) funciona igual.
 */
const CONFIG = { gtmId: "", metaPixelId: "1197036460960933", ga4Id: "G-XH74VZSNZ2" };

window.dataLayer = window.dataLayer || [];

(function () {
  "use strict";

  /* Versão da página do curso (pgA, pgB, pgC); vazio nas outras páginas */
  var script = document.currentScript;
  var pagina = (script && script.getAttribute("data-pagina")) || "";
  var rastreia = !(script && script.hasAttribute("data-sem-rastreamento"));

  /* ---------- Carregamento condicional de GTM, GA4 e Pixel ---------- */
  function loadScript(src) {
    var s = document.createElement("script");
    s.async = true;
    s.src = src;
    document.head.appendChild(s);
  }

  if (rastreia && CONFIG.gtmId) {
    window.dataLayer.push({ "gtm.start": Date.now(), event: "gtm.js" });
    loadScript("https://www.googletagmanager.com/gtm.js?id=" + encodeURIComponent(CONFIG.gtmId));
  }

  if (rastreia && CONFIG.ga4Id) {
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", CONFIG.ga4Id);
    loadScript("https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(CONFIG.ga4Id));
  }

  if (rastreia && CONFIG.metaPixelId) {
    /* Snippet oficial do Pixel da Meta, reescrito sem minificação */
    var fbq = function () {
      fbq.callMethod ? fbq.callMethod.apply(fbq, arguments) : fbq.queue.push(arguments);
    };
    if (!window._fbq) window._fbq = fbq;
    fbq.push = fbq;
    fbq.loaded = true;
    fbq.version = "2.0";
    fbq.queue = [];
    window.fbq = fbq;
    loadScript("https://connect.facebook.net/en_US/fbevents.js");
    window.fbq("init", CONFIG.metaPixelId);
    window.fbq("track", "PageView");
  }

  var PIXEL_EVENTS = { begin_checkout: "InitiateCheckout", generate_lead: "Lead", view_offer: "ViewContent", material_view: "ViewContent" };
  /* Eventos personalizados do Pixel (trackCustom) */
  var PIXEL_CUSTOM = {
    clique_comprar: "CliqueComprar", cadastro_checkout: "CadastroCheckout", escolha_pagamento: "EscolhaPagamento",
    quiz_inicio: "QuizInicio", quiz_completo: "QuizCompleto", contato_calculadora: "ContatoCalculadora",
    material_copiar: "MaterialCopiar", material_pdf: "MaterialPDF"
  };

  function track(event, params) {
    var data = Object.assign({ event: event }, params || {});
    window.dataLayer.push(data);
    if (rastreia && CONFIG.ga4Id && window.gtag) window.gtag("event", event, params || {});
    if (rastreia && CONFIG.metaPixelId && window.fbq && (PIXEL_EVENTS[event] || PIXEL_CUSTOM[event])) {
      var p = {};
      if (params && params.value) { p.value = params.value; p.currency = params.currency || "BRL"; }
      if (params && params.form) p.content_name = params.form;
      if (params && params.content_name) p.content_name = params.content_name;
      if (params && params.content_category) p.content_category = params.content_category;
      if (params && params.payment_type) p.payment_type = params.payment_type;
      if (params && params.pontos !== undefined) p.pontos = params.pontos;
      if (params && params.faixa) p.faixa = params.faixa;
      if (params && params.material) p.material = params.material;
      if (PIXEL_EVENTS[event]) window.fbq("track", PIXEL_EVENTS[event], p);
      else window.fbq("trackCustom", PIXEL_CUSTOM[event], p);
    }
  }
  window.siteTrack = track;

  /* Advanced matching do Pixel: reinicia o Pixel com os dados da pessoa (o Pixel faz o hash).
   * Só no Pixel; nada de dados pessoais no GA4 nem no dataLayer. */
  window.siteIdentify = function (dados) {
    if (rastreia && CONFIG.metaPixelId && window.fbq) window.fbq("init", CONFIG.metaPixelId, dados);
  };

  /* ---------- UTMs: repassa a query string da visita para links internos ---------- */
  var visit = new URLSearchParams(location.search);

  function mergeParams(url) {
    visit.forEach(function (v, k) {
      if (!url.searchParams.has(k)) url.searchParams.set(k, v);
    });
    return url;
  }

  if (visit.toString()) {
    document.querySelectorAll("a[href]").forEach(function (a) {
      var raw = a.getAttribute("href");
      if (!raw || raw.charAt(0) === "#" || /^(https?:|mailto:|tel:|javascript:)/i.test(raw)) return;
      var url = new URL(raw, location.href);
      if (url.origin !== location.origin && url.protocol !== "file:") return;
      a.href = mergeParams(url).toString();
    });
  }

  /* ---------- Botões de compra do curso (a.checkout) ----------
   * Levam à pré-página de inscrição (curso/inscricao/) com pg=pgX da página e a query da visita (bloco acima).
   * É a pré-página que monta o link da Hotmart com src/sck. O clique dispara clique_comprar (CliqueComprar no
   * Pixel); o begin_checkout (InitiateCheckout) sai só no envio do formulário da pré-página.
   */
  var offerParams = { value: 860, currency: "BRL" };
  if (pagina) { offerParams.content_name = "Carreira com Sentido"; offerParams.content_category = pagina; }

  document.querySelectorAll("a.checkout").forEach(function (a) {
    if (pagina) {
      var url = new URL(a.href);
      if (!url.searchParams.has("pg")) {
        url.searchParams.set("pg", pagina);
        a.href = url.toString();
      }
    }
    a.addEventListener("click", function () {
      track("clique_comprar", { content_category: pagina });
    });
  });

  /* Oferta vista: quando o topo de #oferta passa da metade da tela (a área observada é só a metade de cima,
   * então vale para seção de qualquer altura). Uma vez por carregamento. */
  var offer = document.getElementById("oferta");
  if (offer && "IntersectionObserver" in window) {
    var offerSeen = false;
    var offerIO = new IntersectionObserver(function (entries) {
      if (!offerSeen && entries.some(function (e) { return e.isIntersecting; })) {
        offerSeen = true;
        offerIO.disconnect();
        track("view_offer", offerParams);
      }
    }, { rootMargin: "0px 0px -50% 0px", threshold: 0 });
    offerIO.observe(offer);
  }

  /* ---------- Barra fixa no celular ----------
   * Aparece depois que o botão principal do hero sai da tela e some enquanto a
   * oferta ou o formulário ([data-hide-sticky]) estão visíveis. Com a barra visível,
   * o body ganha padding-bottom igual à altura dela (e o botão do WhatsApp sobe junto).
   */
  var bar = document.querySelector(".sticky-bar");
  var hero = document.querySelector(".hero");
  if (bar && hero && "IntersectionObserver" in window) {
    var heroCta = hero.querySelector(".btn") || hero;
    var hideOn = document.querySelectorAll("[data-hide-sticky]");
    var pastHero = false;
    var hidden = 0;
    var update = function () {
      var show = pastHero && hidden === 0;
      bar.classList.toggle("on", show);
      document.body.classList.toggle("has-sticky", show);
      document.body.style.setProperty("--sticky-h", bar.offsetHeight + "px");
    };
    new IntersectionObserver(function (entries) {
      pastHero = !entries[0].isIntersecting && entries[0].boundingClientRect.top < 0;
      update();
    }).observe(heroCta);
    hideOn.forEach(function (el) {
      var visible = false;
      new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting !== visible) {
          visible = entries[0].isIntersecting;
          hidden += visible ? 1 : -1;
          update();
        }
      }).observe(el);
    });
    window.addEventListener("resize", update);
  }

  /* ---------- Máscara de WhatsApp: (51) 99999-9999 ---------- */
  function maskPhone(value) {
    var d = value.replace(/\D/g, "").slice(0, 11);
    if (d.length === 0) return "";
    if (d.length < 3) return "(" + d;
    var ddd = d.slice(0, 2), rest = d.slice(2);
    if (rest.length <= 4) return "(" + ddd + ") " + rest;
    var split = rest.length === 9 ? 5 : 4;
    return "(" + ddd + ") " + rest.slice(0, split) + "-" + rest.slice(split);
  }
  document.querySelectorAll('input[data-mask="phone"]').forEach(function (input) {
    input.addEventListener("input", function () { input.value = maskPhone(input.value); });
  });

  /* ---------- Contato do quiz e da calculadora (Lambda livia-leads) ----------
   * Mesma Lambda, validação e campos da pré-página de inscrição (curso/inscricao/script.js), mais o consentimento
   * obrigatório (checkbox name="consentimento"). src = utm_source|utm_medium|utm_campaign|utm_content; sck = o mesmo
   * + |pgX da página (data-pagina; sem UTM: direto|pgX). O envio nunca trava a página: espera no máximo 1,5 s.
   *   siteContato.prepara(form)          limpa o erro do campo ao digitar
   *   siteContato.valida(form)           true se nome, e-mail, WhatsApp e consentimento estão certos
   *   siteContato.dados(form, extras)    JSON do cadastro (extras: ferramenta, resultado, respostas, pontos)
   *   siteContato.envia(dados)           Promise que resolve com a resposta ou em 1,5 s, o que vier antes
   */
  var CADASTRO_URL = "https://nwmxltflulqvcxu7bdplodmyjm0yweuc.lambda-url.sa-east-1.on.aws/";
  var CADASTRO_ESPERA_MS = 1500;

  function cookie(nome) {
    var m = document.cookie.match(new RegExp("(?:^|; )" + nome + "=([^;]*)"));
    return m ? decodeURIComponent(m[1]) : "";
  }

  window.siteContato = {
    prepara: function (form) {
      ["nome", "email", "whatsapp", "consentimento"].forEach(function (n) {
        var el = form.elements[n];
        if (!el) return;
        el.addEventListener(el.type === "checkbox" ? "change" : "input", function () {
          if (el.getAttribute("aria-invalid")) setError(form, n, "");
        });
      });
    },
    valida: function (form) {
      var firstInvalid = null;
      function fail(name, message) {
        setError(form, name, message);
        if (!firstInvalid) firstInvalid = form.elements[name];
      }
      ["nome", "email", "whatsapp", "consentimento"].forEach(function (n) { setError(form, n, ""); });
      var letras = form.elements.nome.value.match(/[A-Za-zÀ-ÖØ-öø-ÿ]/g) || [];
      if (letras.length < 2) fail("nome", "Escreva o seu nome.");
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.elements.email.value.trim())) fail("email", "Confira o e-mail.");
      var d = form.elements.whatsapp.value.replace(/\D/g, "");
      if (d.length < 10 || d.length > 11) fail("whatsapp", "Informe o WhatsApp com DDD, por exemplo (51) 99999-9999.");
      if (!form.elements.consentimento.checked) fail("consentimento", "Marque esta opção para continuar.");
      if (firstInvalid) firstInvalid.focus();
      return !firstInvalid;
    },
    dados: function (form, extras) {
      var src = visit.get("src") || ["utm_source", "utm_medium", "utm_campaign", "utm_content"]
        .map(function (k) { return visit.get(k); })
        .filter(Boolean)
        .join("|");
      var dados = {
        nome: form.elements.nome.value.trim().replace(/\s+/g, " "),
        email: form.elements.email.value.trim().toLowerCase(),
        whatsapp: form.elements.whatsapp.value.replace(/\D/g, ""),
        pagina: pagina,
        src: src,
        sck: visit.get("sck") || (src || "direto") + "|" + pagina,
        utm_source: visit.get("utm_source") || "",
        utm_medium: visit.get("utm_medium") || "",
        utm_campaign: visit.get("utm_campaign") || "",
        utm_content: visit.get("utm_content") || "",
        utm_term: visit.get("utm_term") || "",
        url: location.href,
        consentimento: "sim",
        fbp: cookie("_fbp"),
        fbc: cookie("_fbc"),
        empresa: form.elements.empresa ? form.elements.empresa.value : ""
      };
      return Object.assign(dados, extras || {});
    },
    envia: function (dados) {
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
      /* a página não muda de endereço (fetch com keepalive): espera no máximo 0,8 s pela Lambda */
      var espera = new Promise(function (resolve) { setTimeout(resolve, 800); });
      return Promise.race([envio, espera]);
    }
  };

  /* ---------- Formulários enviados ao Google Forms ---------- */
  var WHATSAPP = "5551992597638";
  function waLink(text) { return "https://wa.me/" + WHATSAPP + "?text=" + encodeURIComponent(text); }

  function setError(form, name, message) {
    var out = form.querySelector('[data-error-for="' + name + '"]');
    if (out) out.textContent = message || "";
    form.querySelectorAll('[name="' + name + '"]').forEach(function (el) {
      if (message) el.setAttribute("aria-invalid", "true");
      else el.removeAttribute("aria-invalid");
    });
  }

  function validate(form) {
    var firstInvalid = null;
    function fail(name, message) {
      setError(form, name, message);
      if (!firstInvalid) firstInvalid = form.querySelector('[name="' + name + '"]');
    }
    form.querySelectorAll("[data-error-for]").forEach(function (o) { setError(form, o.getAttribute("data-error-for"), ""); });

    var nome = form.elements.nome;
    if (nome && nome.value.trim().length < 3) fail("nome", "Escreva o seu nome.");

    var whats = form.elements.whatsapp;
    if (whats) {
      var digits = whats.value.replace(/\D/g, "");
      if (digits.length < 10 || digits.length > 11) fail("whatsapp", "Informe o WhatsApp com DDD, por exemplo (51) 99999-9999.");
    }

    var email = form.elements.email;
    if (email && (email.required || email.value.trim())) {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.value.trim())) fail("email", "Confira o e-mail.");
    }

    form.querySelectorAll("fieldset[data-min]").forEach(function (fs) {
      var name = fs.getAttribute("data-name");
      if (fs.querySelectorAll("input:checked").length < Number(fs.getAttribute("data-min"))) {
        fail(name, fs.getAttribute("data-message") || "Escolha pelo menos uma opção.");
      }
    });

    form.querySelectorAll("input[type=checkbox][required]").forEach(function (c) {
      if (!c.checked) fail(c.name, c.getAttribute("data-message") || "Marque esta opção para continuar.");
    });

    if (firstInvalid) firstInvalid.focus();
    return !firstInvalid;
  }

  function buildPayload(form) {
    var fd = new FormData();
    form.querySelectorAll("[data-entry]").forEach(function (el) {
      if ((el.type === "checkbox" || el.type === "radio") && !el.checked) return;
      fd.append(el.getAttribute("data-entry"), el.value.trim());
    });
    return fd;
  }

  function leadMessage(form) {
    var type = form.getAttribute("data-lead");
    var nome = form.elements.nome ? form.elements.nome.value.trim() : "";
    if (type === "consultoria") {
      var tema = form.elements.tema ? form.elements.tema.value.trim() : "";
      return "Oi, Thaís! Sou " + nome + " e acabei de me inscrever na Consultoria Carreira com Sentido. " +
        (tema ? "Quero levar para a consultoria: " + tema : "Gostaria de marcar o meu horário.");
    }
    return "Oi, Thaís! Sou " + nome + " e gostaria de entrar na lista de interesse para terapia com a Lívia.";
  }

  document.querySelectorAll("form[data-gform]").forEach(function (form) {
    form.querySelectorAll("input, textarea").forEach(function (el) {
      el.addEventListener("change", function () { if (el.getAttribute("aria-invalid")) setError(form, el.name, ""); });
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (!validate(form)) return;

      var button = form.querySelector('button[type="submit"]');
      var status = form.querySelector(".form-status");
      var label = button.textContent;
      button.disabled = true;
      button.textContent = "Enviando...";
      if (status) status.textContent = "";

      fetch(form.getAttribute("data-gform"), { method: "POST", mode: "no-cors", body: buildPayload(form) })
        .then(function () {
          track("generate_lead", { form: form.getAttribute("data-lead") });
          var success = document.getElementById(form.getAttribute("data-success"));
          var wa = success && success.querySelector('[data-wa="lead"]');
          if (wa) wa.href = waLink(leadMessage(form));
          form.hidden = true;
          if (success) {
            success.hidden = false;
            success.focus();
          }
        })
        .catch(function () {
          button.disabled = false;
          button.textContent = label;
          if (status) {
            status.innerHTML = "";
            var p = document.createElement("p");
            p.className = "error";
            p.textContent = "Não conseguimos enviar agora (verifique a sua conexão). Você pode tentar de novo ou falar direto com a Thaís:";
            var a = document.createElement("a");
            a.className = "btn btn-wa";
            a.style.marginTop = "12px";
            a.href = waLink(leadMessage(form));
            a.target = "_blank";
            a.rel = "noopener";
            a.textContent = "Falar com a Thaís no WhatsApp";
            status.appendChild(p);
            status.appendChild(a);
          }
        });
    });
  });
})();
