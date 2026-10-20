/* Lívia Oliveira: JS compartilhado (sem dependências) */

/*
 * IDs de rastreamento. Cada script só é carregado se o ID estiver preenchido (vazio = desligado).
 *   gtmId:       vazio (sem Google Tag Manager; o GA4 vai direto)
 *   metaPixelId: "1197036460960933"  (Pixel da Meta da conta de anúncios da Lívia: PageView em toda página)
 *   ga4Id:       "G-XH74VZSNZ2"  (GA4 direto, propriedade 559914633: config com page_view em toda página)
 * As páginas do curso dizem qual versão são no atributo data-pagina da tag <script> (pgA = curso/,
 * pgB = curso/b/, pgC = curso/versao-b/); o valor vai no sck da Hotmart e no content_category dos eventos.
 */
const CONFIG = { gtmId: "", metaPixelId: "1197036460960933", ga4Id: "G-XH74VZSNZ2" };

window.dataLayer = window.dataLayer || [];

(function () {
  "use strict";

  /* Versão da página do curso (pgA, pgB, pgC); vazio nas outras páginas */
  var pagina = (document.currentScript && document.currentScript.getAttribute("data-pagina")) || "";

  /* ---------- Carregamento condicional de GTM, GA4 e Pixel ---------- */
  function loadScript(src) {
    var s = document.createElement("script");
    s.async = true;
    s.src = src;
    document.head.appendChild(s);
  }

  if (CONFIG.gtmId) {
    window.dataLayer.push({ "gtm.start": Date.now(), event: "gtm.js" });
    loadScript("https://www.googletagmanager.com/gtm.js?id=" + encodeURIComponent(CONFIG.gtmId));
  }

  if (CONFIG.ga4Id) {
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag("js", new Date());
    window.gtag("config", CONFIG.ga4Id);
    loadScript("https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(CONFIG.ga4Id));
  }

  if (CONFIG.metaPixelId) {
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

  var PIXEL_EVENTS = { begin_checkout: "InitiateCheckout", generate_lead: "Lead", view_offer: "ViewContent" };

  function track(event, params) {
    var data = Object.assign({ event: event }, params || {});
    window.dataLayer.push(data);
    if (CONFIG.ga4Id && window.gtag) window.gtag("event", event, params || {});
    if (CONFIG.metaPixelId && window.fbq && PIXEL_EVENTS[event]) {
      var p = {};
      if (params && params.value) { p.value = params.value; p.currency = params.currency || "BRL"; }
      if (params && params.form) p.content_name = params.form;
      if (params && params.content_name) p.content_name = params.content_name;
      if (params && params.content_category) p.content_category = params.content_category;
      window.fbq("track", PIXEL_EVENTS[event], p);
    }
  }
  window.siteTrack = track;

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

  /* ---------- Checkout Hotmart: UTMs em src/sck + eventos ----------
   * src = utm_source|utm_medium|utm_campaign|utm_content; sck = o mesmo + |pgX da página
   * (sem UTM: sem src e sck=direto|pgX). Ex.: sck=meta|paid|ccs_frio_criativos|V01|pgA
   */
  var src = ["utm_source", "utm_medium", "utm_campaign", "utm_content"]
    .map(function (k) { return visit.get(k); })
    .filter(Boolean)
    .join("|");
  var sck = pagina ? (src || "direto") + "|" + pagina : src;
  var offerParams = { value: 860, currency: "BRL" };
  if (pagina) { offerParams.content_name = "Carreira com Sentido"; offerParams.content_category = pagina; }

  document.querySelectorAll('a.checkout, a[href*="pay.hotmart.com"]').forEach(function (a) {
    var url = mergeParams(new URL(a.href));
    if (src) url.searchParams.set("src", src);
    if (sck) url.searchParams.set("sck", sck);
    a.href = url.toString();
    a.addEventListener("click", function () {
      track("begin_checkout", offerParams);
    });
  });

  var offer = document.getElementById("oferta");
  if (offer && "IntersectionObserver" in window) {
    var offerIO = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) {
        track("view_offer", offerParams);
        offerIO.disconnect();
      }
    }, { threshold: 0.3 });
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
