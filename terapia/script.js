(function () {
  "use strict";

  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* Imagens que não carregarem somem sem deixar ícone quebrado */
  document.querySelectorAll("img").forEach(function (img) {
    function esconde() { img.style.visibility = "hidden"; }
    if (img.complete && img.naturalWidth === 0) esconde();
    else img.addEventListener("error", esconde);
  });

  /* Título: palavras com blur-in escalonado */
  var titulo = document.querySelector("[data-palavras]");
  if (titulo && !reduz) {
    var i = 0;
    var quebra = function (no) {
      Array.prototype.slice.call(no.childNodes).forEach(function (filho) {
        if (filho.nodeType === 3) {
          var frag = document.createDocumentFragment();
          filho.textContent.split(/(\s+)/).forEach(function (parte) {
            if (!parte) return;
            if (/^\s+$/.test(parte)) { frag.appendChild(document.createTextNode(parte)); return; }
            var s = document.createElement("span");
            s.className = "palavra";
            s.style.setProperty("--i", i++);
            s.textContent = parte;
            frag.appendChild(s);
          });
          no.replaceChild(frag, filho);
        } else if (filho.nodeType === 1) {
          quebra(filho);
        }
      });
    };
    quebra(titulo);
  }

  /* Reveal das seções: o que está acima da dobra já começa revelado;
     rede de segurança revela o resto depois de 2,5 s ou ao chegar no fim da página */
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
    setTimeout(revelaTudo, 2500);
  }
  function noFim() {
    return window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4;
  }

  /* Scroll: WhatsApp flutuante, parallax do hero, véu dourado que levanta, foto e linha dos passos */
  var hero = document.querySelector(".hero");
  var heroMedia = document.querySelector(".hero-media");
  var veu = document.querySelector(".hero-veu");
  var foto = document.querySelector(".sobre .foto img");
  var passos = document.querySelector(".passos");
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

    if (y < hh) {
      var p = y / hh;
      heroMedia.style.transform = "translate3d(0," + (y * 0.25).toFixed(1) + "px,0) scale(" + (1 + p * 0.05).toFixed(4) + ")";
      veu.style.transform = "translateX(-50%) translate3d(0," + (-p * 35).toFixed(1) + "%,0)";
      veu.style.opacity = Math.max(0, 1 - p * 1.4).toFixed(3);
    }

    if (foto) {
      var r = foto.parentNode.getBoundingClientRect();
      if (r.bottom > 0 && r.top < vh) {
        var c = (r.top + r.height / 2 - vh / 2) / vh;
        foto.style.transform = "translate3d(0," + (c * -36).toFixed(1) + "px,0)";
      }
    }

    if (passos) {
      var q = passos.getBoundingClientRect();
      var prog = Math.min(Math.max((vh * 0.85 - q.top) / (vh * 0.5), 0), 1);
      passos.style.setProperty("--p", prog.toFixed(4));
    }
  }

  function agenda() {
    if (!pendente) { pendente = true; requestAnimationFrame(atualiza); }
  }
  window.addEventListener("scroll", agenda, { passive: true });
  window.addEventListener("resize", agenda);
  atualiza();
})();
