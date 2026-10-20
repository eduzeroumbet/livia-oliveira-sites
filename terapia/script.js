(function () {
  "use strict";

  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* Imagens que não carregarem somem sem deixar ícone quebrado */
  document.querySelectorAll("img").forEach(function (img) {
    function esconde() { img.style.visibility = "hidden"; }
    if (img.complete && img.naturalWidth === 0) esconde();
    else img.addEventListener("error", esconde);
  });

  /* Vídeo do hero (Aethera): 720 até 699px, 1280 no resto; fade-in no canplay;
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

  /* Navbar Aethera: sheet no celular trava a rolagem */
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

  /* Scroll: WhatsApp flutuante e foto */
  var hero = document.querySelector(".hero");
  var foto = document.querySelector(".sobre .foto img");
  var whats = document.querySelector(".whats");
  var evitaveis = Array.prototype.slice.call(document.querySelectorAll("main .btn"));
  var pendente = false;

  /* WhatsApp não pode cobrir CTAs */
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

    if (whats) whats.classList.toggle("is-visivel", y > hh * 0.85 && !cobreAlgo());

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
