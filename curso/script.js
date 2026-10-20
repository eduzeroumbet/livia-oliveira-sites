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

  /* Reveal das seções */
  var revelaveis = document.querySelectorAll(".reveal");
  if (reduz || !("IntersectionObserver" in window)) {
    revelaveis.forEach(function (el) { el.classList.add("is-visivel"); });
  } else {
    var io = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-visivel"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    revelaveis.forEach(function (el) { io.observe(el); });
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

  /* Marquee: duplica os cards para o loop; pausa no toque */
  var marquee = document.querySelector(".marquee");
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

  /* Scroll: header, parallax do hero, véu, retrato, linha dos módulos, barra mobile */
  var header = document.querySelector(".header");
  var hero = document.querySelector(".hero");
  var heroMedia = document.querySelector(".hero-media");
  var veu = document.querySelector(".hero-veu");
  var retrato = document.querySelector(".guia-foto img");
  var modulos = document.querySelector(".modulos");
  var linha = document.querySelector(".modulos-linha span");
  var itensModulo = document.querySelectorAll(".modulo");
  var barra = document.querySelector(".barra-mobile");
  var oferta = document.getElementById("oferta");
  var pendente = false;

  function atualiza() {
    pendente = false;
    var y = window.scrollY;
    var vh = window.innerHeight;
    var hh = hero ? hero.offsetHeight : vh;

    if (header) header.classList.toggle("is-solid", y > hh * 0.6);

    var depoisHero = y > hh * 0.85;
    var ofertaRect = oferta ? oferta.getBoundingClientRect() : null;
    var naOferta = ofertaRect && ofertaRect.top < vh && ofertaRect.bottom > 0;
    if (barra) {
      var mostra = depoisHero && !naOferta;
      barra.classList.toggle("is-visivel", mostra);
      document.body.classList.toggle("tem-barra", mostra && window.innerWidth < 900);
    }

    if (reduz) return;

    if (y < hh) {
      var p = y / hh;
      if (heroMedia) heroMedia.style.transform = "translate3d(0," + (y * 0.28).toFixed(1) + "px,0) scale(" + (1 + p * 0.06).toFixed(4) + ")";
      if (veu) {
        veu.style.transform = "translate3d(0," + (-p * 60).toFixed(1) + "%,0)";
        veu.style.opacity = Math.max(0, 1 - p * 1.6).toFixed(3);
      }
    }

    if (retrato) {
      var r = retrato.parentNode.getBoundingClientRect();
      if (r.bottom > 0 && r.top < vh) {
        var c = (r.top + r.height / 2 - vh / 2) / vh;
        retrato.style.transform = "translate3d(0," + (c * -40).toFixed(1) + "px,0)";
      }
    }

    if (modulos && linha) {
      var m = modulos.getBoundingClientRect();
      var ref = vh * 0.6;
      var prog = Math.min(Math.max((ref - m.top) / m.height, 0), 1);
      linha.parentNode.style.setProperty("--p", prog.toFixed(4));
      itensModulo.forEach(function (it) {
        it.classList.toggle("is-ativo", it.getBoundingClientRect().top + 10 < ref);
      });
    }
  }

  function agenda() {
    if (!pendente) { pendente = true; requestAnimationFrame(atualiza); }
  }
  window.addEventListener("scroll", agenda, { passive: true });
  window.addEventListener("resize", agenda);
  atualiza();

  doc.classList.add("js");
})();
