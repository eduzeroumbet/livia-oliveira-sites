(function () {
  "use strict";

  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var doc = document.documentElement;

  /* Imagens que não carregarem somem sem deixar ícone quebrado. Lazy ainda não pedida também tem
     naturalWidth 0, então só a eager entra na checagem imediata; o resto depende do evento error */
  document.querySelectorAll("img").forEach(function (img) {
    function esconde() { img.style.visibility = "hidden"; }
    img.addEventListener("error", esconde);
    img.addEventListener("load", function () { img.style.visibility = ""; });
    if (img.loading !== "lazy" && img.complete && img.naturalWidth === 0) esconde();
  });

  /* Preserva UTMs e fbclid nos links da Hotmart */
  var qs = window.location.search.replace(/^\?/, "");
  if (qs) {
    document.querySelectorAll('a[href*="pay.hotmart.com"]').forEach(function (a) {
      var url = new URL(a.href);
      new URLSearchParams(qs).forEach(function (valor, chave) {
        if (!url.searchParams.has(chave)) url.searchParams.append(chave, valor);
      });
      a.href = url.toString();
    });
  }

  /* Vídeo do hero (Arbor): 720 até 699px, 1280 no resto; fade-in no canplay;
     pausado com prefers-reduced-motion; se falhar, fica o poster.
     No celular o poster é o LCP: o vídeo (preload="none") só começa a baixar e tocar depois do load */
  var video = document.querySelector(".hero__video");
  if (video) {
    var celular = window.innerWidth <= 699;
    var pronto = function () { video.classList.add("is-ready"); };
    var inicia = function () {
      var src = celular ? video.getAttribute("data-src-720") : video.getAttribute("data-src-1280");
      var fonte = video.querySelector("source");
      if (src && fonte && fonte.getAttribute("src") !== src) {
        fonte.setAttribute("src", src);
        video.load();
      }
      video.muted = true;
      var toca = video.play();
      if (toca && toca.catch) toca.catch(function () {});
    };
    video.addEventListener("canplay", pronto);
    video.addEventListener("error", pronto, true);
    if (video.readyState >= 3) pronto();
    if (reduz) {
      pronto();
    } else if (celular && document.readyState !== "complete") {
      window.addEventListener("load", inicia);
    } else {
      inicia();
    }
  }

  /* Navbar Arbor: papel com blur depois de 16px; sheet no celular trava a rolagem */
  var nav = document.querySelector(".nav");
  var toggle = document.querySelector(".nav__toggle");
  var sheet = document.getElementById("nav-sheet");
  function marcaNav() { if (nav) nav.classList.toggle("is-scrolled", window.scrollY > 16); }
  marcaNav();
  window.addEventListener("scroll", marcaNav, { passive: true });
  function abreMenu(aberto) {
    if (!toggle || !sheet) return;
    toggle.setAttribute("aria-expanded", aberto ? "true" : "false");
    toggle.setAttribute("aria-label", aberto ? "Fechar menu" : "Abrir menu");
    sheet.hidden = !aberto;
    document.body.style.overflow = aberto ? "hidden" : "";
  }
  if (toggle && sheet) {
    toggle.addEventListener("click", function () { abreMenu(sheet.hidden); });
    sheet.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { abreMenu(false); }); });
    window.addEventListener("resize", function () { if (window.innerWidth > 880 && !sheet.hidden) abreMenu(false); });
  }

  /* Reveal das seções: o que está acima da dobra já começa revelado;
     rede de segurança força o estado final (sem transição, opacity 1) depois de 1,5 s,
     no evento load e ao chegar no fim da página, para nenhum card ficar a meio caminho */
  var revelaveis = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  var io = null;
  var revelado = false;
  function revelaTudo() {
    if (revelado) return;
    revelado = true;
    revelaveis.forEach(function (el) {
      if (el.classList.contains("is-visivel")) return;
      el.style.transition = "none";
      el.classList.add("is-visivel");
    });
    doc.offsetHeight;
    revelaveis.forEach(function (el) { el.style.transition = ""; });
    if (io) io.disconnect();
  }
  if (reduz || !("IntersectionObserver" in window)) {
    revelaTudo();
  } else {
    io = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-visivel"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0 });
    revelaveis.forEach(function (el) {
      if (el.getBoundingClientRect().top < window.innerHeight) {
        el.style.transition = "none";
        el.classList.add("is-visivel");
        el.offsetHeight;
        el.style.transition = "";
      } else {
        io.observe(el);
      }
    });
    setTimeout(revelaTudo, 1500);
    if (document.readyState === "complete") revelaTudo();
    else window.addEventListener("load", revelaTudo);
  }
  function noFim() {
    return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
  }

  /* Contadores */
  function formata(n, casasMil) {
    return casasMil ? n.toLocaleString("pt-BR") : String(n);
  }
  var contadores = document.querySelectorAll("[data-conta]");
  function conta(el) {
    var alvo = parseInt(el.getAttribute("data-conta"), 10);
    var prefixo = el.getAttribute("data-prefixo") || "";
    var sufixo = el.getAttribute("data-sufixo") || "";
    var desde = parseInt(el.getAttribute("data-de") || "0", 10);
    if (reduz) { el.textContent = prefixo + alvo + sufixo; return; }
    var dur = 1600, t0 = null;
    function passo(t) {
      if (!t0) t0 = t;
      var p = Math.min((t - t0) / dur, 1);
      var e = 1 - Math.pow(1 - p, 3);
      el.textContent = prefixo + formata(Math.round(desde + (alvo - desde) * e)) + sufixo;
      if (p < 1) requestAnimationFrame(passo);
    }
    requestAnimationFrame(passo);
  }
  if ("IntersectionObserver" in window && !reduz) {
    var ioc = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (e.isIntersecting) { conta(e.target); ioc.unobserve(e.target); }
      });
    }, { threshold: 0.6 });
    contadores.forEach(function (el) { ioc.observe(el); });
  }

  /* Vídeo da história: com JS, poster limpo e botão de play central; o clique esconde o botão,
     liga os controles e toca com som. Sem JS o botão fica hidden e valem os controles nativos */
  var historia = document.querySelector(".video-tela video");
  var play = document.querySelector(".video-play");
  if (historia && play) {
    historia.controls = false;
    play.hidden = false;
    var assiste = function () {
      play.hidden = true;
      historia.controls = true;
    };
    play.addEventListener("click", function () {
      assiste();
      historia.muted = false;
      var toca = historia.play();
      if (toca && toca.catch) toca.catch(function () {});
      historia.focus();
    });
    historia.addEventListener("play", assiste);
  }

  /* FAQ: abre e fecha com altura suave */
  document.querySelectorAll(".faq details").forEach(function (d) {
    var sumario = d.querySelector("summary");
    var corpo = d.querySelector(".faq-resposta");
    sumario.addEventListener("click", function (ev) {
      if (reduz || !corpo.animate) return;
      ev.preventDefault();
      if (d.open) {
        var a = corpo.animate([{ height: corpo.offsetHeight + "px", opacity: 1 }, { height: "0px", opacity: 0 }], { duration: 280, easing: "ease" });
        a.onfinish = function () { d.open = false; };
      } else {
        d.open = true;
        var h = corpo.offsetHeight;
        corpo.animate([{ height: "0px", opacity: 0 }, { height: h + "px", opacity: 1 }], { duration: 320, easing: "ease" });
      }
    });
  });

  /* Scroll: retrato, barra mobile e WhatsApp */
  var hero = document.querySelector(".hero");
  var retrato = document.querySelector(".guia-foto img");
  var barra = document.querySelector(".barra-mobile");
  var oferta = document.getElementById("oferta");
  var whats = document.querySelector(".whats");
  var evitaveis = Array.prototype.slice.call(document.querySelectorAll("main .btn, .step"));
  var pendente = false;

  /* WhatsApp não pode cobrir CTAs nem os passos */
  function cobreAlgo() {
    var w = whats.getBoundingClientRect();
    return evitaveis.some(function (el) {
      var r = el.getBoundingClientRect();
      return r.width > 0 && r.left < w.right + 8 && r.right > w.left - 8 && r.top < w.bottom + 8 && r.bottom > w.top - 8;
    });
  }

  function atualiza() {
    pendente = false;
    var y = window.scrollY;
    var vh = window.innerHeight;
    var hh = hero ? hero.offsetHeight : vh;

    var depoisHero = y > hh * 0.85;
    var ofertaRect = oferta ? oferta.getBoundingClientRect() : null;
    var naOferta = ofertaRect && ofertaRect.top < vh && ofertaRect.bottom > 0;
    if (barra) {
      var mostra = depoisHero && !naOferta;
      barra.classList.toggle("is-visivel", mostra);
      doc.style.setProperty("--barra-h", barra.offsetHeight + "px");
      document.body.classList.toggle("tem-barra", mostra && window.innerWidth < 900);
    }
    if (whats) whats.classList.toggle("is-visivel", depoisHero && !cobreAlgo());

    if (noFim()) revelaTudo();

    if (reduz) return;

    if (retrato) {
      var r = retrato.parentNode.getBoundingClientRect();
      if (r.bottom > 0 && r.top < vh) {
        var c = (r.top + r.height / 2 - vh / 2) / vh;
        retrato.style.transform = "translate3d(0," + (c * -40).toFixed(1) + "px,0)";
      }
    }
  }

  function agenda() {
    if (!pendente) { pendente = true; requestAnimationFrame(atualiza); }
  }
  window.addEventListener("scroll", agenda, { passive: true });
  window.addEventListener("resize", agenda);
  atualiza();
})();
