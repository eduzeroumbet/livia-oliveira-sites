(function () {
  "use strict";

  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var doc = document.documentElement;

  /* Imagens que não carregarem somem sem deixar ícone quebrado */
  document.querySelectorAll("img").forEach(function (img) {
    function esconde() { img.style.visibility = "hidden"; }
    if (img.complete && img.naturalWidth === 0) esconde();
    else img.addEventListener("error", esconde);
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
     pausado com prefers-reduced-motion; se falhar, fica o poster */
  var video = document.querySelector(".hero__video");
  if (video) {
    var pronto = function () { video.classList.add("is-ready"); };
    var src = window.innerWidth <= 699 ? video.getAttribute("data-src-720") : video.getAttribute("data-src-1280");
    var fonte = video.querySelector("source");
    if (src && fonte && fonte.getAttribute("src") !== src) {
      fonte.setAttribute("src", src);
      video.load();
    }
    video.addEventListener("canplay", pronto);
    video.addEventListener("error", pronto, true);
    if (video.readyState >= 3) pronto();
    var toca = video.play();
    if (toca && toca.catch) toca.catch(function () {});
    if (reduz) { video.pause(); pronto(); }
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
     rede de segurança revela o resto depois de 1,5 s ou ao chegar no fim da página */
  var revelaveis = Array.prototype.slice.call(document.querySelectorAll(".reveal"));
  var io = null;
  function revelaTudo() {
    revelaveis.forEach(function (el) { el.classList.add("is-visivel"); });
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

  /* Marquee: duplica os cards para o loop; pausa no toque.
     No celular vira carrossel com swipe (CSS) e pontinhos indicadores. */
  var marquee = document.querySelector(".marquee");
  if (marquee) {
    var originais = Array.prototype.slice.call(marquee.querySelectorAll(".depo"));
    var pontos = document.createElement("div");
    pontos.className = "depo-pontos";
    originais.forEach(function (card, n) {
      var b = document.createElement("button");
      b.type = "button";
      b.setAttribute("aria-label", "Depoimento " + (n + 1) + " de " + originais.length);
      if (n === 0) b.setAttribute("aria-current", "true");
      b.addEventListener("click", function () {
        marquee.scrollTo({ left: card.offsetLeft - originais[0].offsetLeft, behavior: reduz ? "auto" : "smooth" });
      });
      pontos.appendChild(b);
    });
    marquee.parentNode.insertBefore(pontos, marquee.nextSibling);
    var botoesPontos = pontos.querySelectorAll("button");
    marquee.addEventListener("scroll", function () {
      var passo = originais.length > 1 ? originais[1].offsetLeft - originais[0].offsetLeft : 1;
      var atual = Math.min(originais.length - 1, Math.max(0, Math.round(marquee.scrollLeft / passo)));
      botoesPontos.forEach(function (b, n) {
        if (n === atual) b.setAttribute("aria-current", "true");
        else b.removeAttribute("aria-current");
      });
    }, { passive: true });
  }
  if (marquee && !reduz) {
    var trilha = marquee.querySelector(".marquee-trilha");
    Array.prototype.slice.call(trilha.children).forEach(function (card) {
      var clone = card.cloneNode(true);
      clone.setAttribute("aria-hidden", "true");
      trilha.appendChild(clone);
    });
    marquee.addEventListener("touchstart", function () { marquee.classList.add("is-pausado"); }, { passive: true });
    marquee.addEventListener("touchend", function () { marquee.classList.remove("is-pausado"); }, { passive: true });
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
