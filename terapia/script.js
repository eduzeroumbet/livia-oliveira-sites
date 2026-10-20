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

  /* Navbar: transparente no hero; fora dele ganha fundo papel (IntersectionObserver no hero) */
  var nav = document.querySelector(".nav");
  var heroNav = document.querySelector(".hero");
  if (nav && heroNav) {
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (entradas) {
        nav.classList.toggle("is-solida", !entradas[0].isIntersecting);
      }, { rootMargin: "-88px 0px 0px 0px", threshold: 0 }).observe(heroNav);
    } else {
      var marcaNav = function () { nav.classList.toggle("is-solida", window.scrollY > heroNav.offsetHeight - 88); };
      marcaNav();
      window.addEventListener("scroll", marcaNav, { passive: true });
    }
  }

  /* Sheet no celular trava a rolagem */
  var toggle = document.querySelector(".nav__toggle");
  var sheet = document.getElementById("nav-sheet");
  function abreMenu(aberto) {
    toggle.setAttribute("aria-expanded", aberto ? "true" : "false");
    toggle.setAttribute("aria-label", aberto ? "Fechar menu" : "Abrir menu");
    sheet.hidden = !aberto;
    document.body.style.overflow = aberto ? "hidden" : "";
  }
  if (toggle && sheet) {
    toggle.addEventListener("click", function () { abreMenu(sheet.hidden); });
    sheet.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { abreMenu(false); }); });
    window.addEventListener("resize", function () { if (window.innerWidth > 1040 && !sheet.hidden) abreMenu(false); });
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

  /* Scroll: WhatsApp flutuante e foto */
  var hero = document.querySelector(".hero");
  var foto = document.querySelector(".sobre .foto img");
  var whats = document.querySelector(".whats");
  var evitaveis = Array.prototype.slice.call(document.querySelectorAll("main .btn, .step, .faq summary, .nota"));
  var pendente = false;

  /* WhatsApp não pode cobrir CTAs, passos, perguntas do FAQ nem a nota da lista de espera */
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
    var hh = hero.offsetHeight;

    if (whats) whats.classList.toggle("is-visivel", y > hh - 88 && !cobreAlgo());

    if (noFim()) revelaTudo();

    if (reduz) return;

    if (foto) {
      var r = foto.parentNode.getBoundingClientRect();
      if (r.bottom > 0 && r.top < vh) {
        var c = (r.top + r.height / 2 - vh / 2) / vh;
        foto.style.transform = "translate3d(0," + (c * -36).toFixed(1) + "px,0)";
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
