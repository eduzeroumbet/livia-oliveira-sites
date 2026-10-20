/* Curso versão B | hero "Fios que se organizam".
   Fios finos começam emaranhados (soma de senos) e, em uns 5 s, se desembaraçam em feixes paralelos
   que fluem da esquerda para a direita com uma ondulação leve que nunca para. A rolagem adianta a
   organização. Concentrados à direita e embaixo no desktop, embaixo no celular (o texto fica do outro lado).
   Pausa fora da tela e com a aba oculta; com prefers-reduced-motion desenha um quadro só, já organizado */
(function () {
  "use strict";

  var hero = document.querySelector(".hero--fios");
  var canvas = hero && hero.querySelector(".hero__fios");
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  if (!ctx) return;

  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var TAU = Math.PI * 2;
  var DURACAO = 5;    // segundos até tudo organizado
  var INICIO = 0.4;   // os fios ficam emaranhados um instante antes de começar

  /* Sorteio com semente: os mesmos fios a cada carregamento e a cada redimensionamento */
  var semente = 20261020;
  function sorteia() {
    semente = (semente + 0x6D2B79F5) | 0;
    var t = Math.imul(semente ^ (semente >>> 15), 1 | semente);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  function entre(a, b) { return a + (b - a) * sorteia(); }

  /* Rosé na maioria, creme e um azul petróleo mais claro que #264056 para aparecer no vinho */
  var CORES = [
    { rgb: "219, 168, 173", peso: 0.64 },
    { rgb: "252, 250, 246", peso: 0.22 },
    { rgb: "128, 162, 189", peso: 0.14 }
  ];
  function cor() {
    var r = sorteia(), soma = 0;
    for (var i = 0; i < CORES.length; i++) {
      soma += CORES[i].peso;
      if (r < soma) return CORES[i].rgb;
    }
    return CORES[0].rgb;
  }

  /* Feixes organizados, em frações da altura: y0 na borda esquerda, y1 na direita.
     Desktop: sobem do fundo à esquerda para a metade direita. Celular: faixa na parte de baixo */
  var FEIXES = {
    desktop: [
      { y0: 0.95, y1: 0.30, abre: 0.050, amp: 0.034, k: 1.10, fase: 0.0 },
      { y0: 0.99, y1: 0.50, abre: 0.060, amp: 0.042, k: 0.80, fase: 1.7 },
      { y0: 1.03, y1: 0.70, abre: 0.045, amp: 0.030, k: 1.35, fase: 3.1 },
      { y0: 0.90, y1: 0.90, abre: 0.035, amp: 0.022, k: 1.00, fase: 4.4 }
    ],
    celular: [
      { y0: 0.74, y1: 0.66, abre: 0.030, amp: 0.020, k: 0.90, fase: 0.0 },
      { y0: 0.84, y1: 0.78, abre: 0.035, amp: 0.024, k: 0.70, fase: 1.7 },
      { y0: 0.92, y1: 0.89, abre: 0.028, amp: 0.018, k: 1.10, fase: 3.1 },
      { y0: 0.99, y1: 0.97, abre: 0.022, amp: 0.014, k: 0.85, fase: 4.4 }
    ]
  };

  var MAX_FIOS = 64;
  var FIOS_CELULAR = 40;
  var fios = [];
  for (var i = 0; i < MAX_FIOS; i++) {
    fios.push({
      cor: cor(),
      alfa: entre(0.25, 0.6),
      largura: entre(1, 1.5),
      feixe: i % 4,
      lugar: entre(-1, 1),              // posição dentro do feixe
      atraso: entre(0, 0.25),           // cada fio se organiza num tempo um pouco diferente
      tremor: entre(0, TAU),
      // emaranhado: centro e três senos com frequências, velocidades e fases próprias
      centro: sorteia(),
      a: [entre(0.06, 0.12), entre(0.04, 0.08), entre(0.02, 0.04)],
      f: [entre(0.6, 1.6), entre(1.8, 3.2), entre(3.5, 6)],
      v: [entre(-0.5, 0.5), entre(-0.7, 0.7), entre(-0.9, 0.9)],
      p: [entre(0, TAU), entre(0, TAU), entre(0, TAU)],
      dobra: entre(3.5, 6),             // ondulação em x que cria pequenas laçadas
      dobraAmp: entre(0.03, 0.06),
      dobraV: entre(-0.4, 0.4),
      dobraP: entre(0, TAU)
    });
  }

  var largura = 0, altura = 0, celular = false, feixes = FEIXES.desktop, quantos = MAX_FIOS, pontos = 60;
  var tempo = 0, organiza = 0, rolagem = 0;

  function suave(x) { return x <= 0 ? 0 : x >= 1 ? 1 : x * x * (3 - 2 * x); }
  function emDentro(x) { return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; }

  function mede() {
    var w = hero.clientWidth, h = hero.clientHeight;
    if (!w || !h) return false;
    var dpr = Math.min(2, window.devicePixelRatio || 1);
    largura = w; altura = h;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    celular = w < 700;
    feixes = celular ? FEIXES.celular : FEIXES.desktop;
    quantos = celular ? FIOS_CELULAR : MAX_FIOS;
    pontos = Math.max(36, Math.min(110, Math.round(w / 16)));
    return true;
  }

  /* No emaranhado os fios ficam na mesma região dos feixes, só que embaralhados */
  function centroEmaranhado(fio, u) {
    if (celular) return 0.7 + fio.centro * 0.28;
    var topo = 0.88 - 0.5 * suave(u);
    return topo + fio.centro * (1 - topo) * 0.95;
  }

  function desenha() {
    ctx.clearRect(0, 0, largura, altura);
    var t = tempo;
    var g = Math.min(1, organiza + rolagem);
    var px = new Array(pontos + 1), py = new Array(pontos + 1);
    // no celular o texto ocupa quase toda a altura: emaranhado mais baixo para não subir atrás dele
    var escala = celular ? 0.55 : 1;

    for (var n = 0; n < quantos; n++) {
      var fio = fios[n];
      var fx = feixes[fio.feixe];
      for (var j = 0; j <= pontos; j++) {
        var u = -0.08 + (j / pontos) * 1.16;

        // organizado: centro do feixe + onda que viaja para a direita + abertura que respira
        var centro = fx.y0 + (fx.y1 - fx.y0) * suave((u - 0.1) / 0.8);
        var onda = fx.amp * Math.sin(TAU * fx.k * u - 0.55 * t + fx.fase) +
                   fx.amp * 0.4 * Math.sin(TAU * fx.k * 1.7 * u - 0.32 * t + fx.fase * 1.3);
        var abre = fx.abre * (0.75 + 0.25 * Math.sin(TAU * 0.9 * u + 0.3 * t + fx.fase));
        var yo = centro + onda + fio.lugar * abre + 0.003 * Math.sin(14 * u + 0.8 * t + fio.tremor);
        var xo = u;

        // emaranhado: soma de senos em y e uma dobra em x
        var ye = centroEmaranhado(fio, u);
        for (var k = 0; k < 3; k++) ye += escala * fio.a[k] * Math.sin(TAU * fio.f[k] * u + fio.v[k] * t + fio.p[k]);
        var xe = u + fio.dobraAmp * Math.sin(TAU * fio.dobra * u + fio.dobraV * t + fio.dobraP);

        // a organização corre da esquerda para a direita, como um pente
        var q = emDentro(Math.max(0, Math.min(1, g * 1.55 - fio.atraso - u * 0.3)));
        px[j] = (xe + (xo - xe) * q) * largura;
        py[j] = (ye + (yo - ye) * q) * altura;
      }

      ctx.beginPath();
      ctx.moveTo(px[0], py[0]);
      for (var m = 1; m < pontos; m++) {
        ctx.quadraticCurveTo(px[m], py[m], (px[m] + px[m + 1]) / 2, (py[m] + py[m + 1]) / 2);
      }
      ctx.lineTo(px[pontos], py[pontos]);
      ctx.strokeStyle = "rgba(" + fio.cor + ", " + fio.alfa + ")";
      ctx.lineWidth = fio.largura;
      ctx.stroke();
    }
  }

  /* Rolagem: quanto mais desce dentro do hero, mais alinhados */
  function leRolagem() {
    var h = hero.offsetHeight || window.innerHeight;
    rolagem = Math.max(0, Math.min(1, window.scrollY / (h * 0.6)));
  }

  if (reduz) {
    organiza = 1;
    var estatico = function () { if (mede()) desenha(); };
    estatico();
    if ("ResizeObserver" in window) new ResizeObserver(estatico).observe(hero);
    else window.addEventListener("resize", estatico);
    return;
  }

  var raf = 0, ultimo = 0, naTela = true;
  function quadro(agora) {
    raf = 0;
    var dt = ultimo ? Math.min(0.05, (agora - ultimo) / 1000) : 0;
    ultimo = agora;
    tempo += dt;
    organiza = Math.max(0, Math.min(1, (tempo - INICIO) / DURACAO));
    desenha();
    liga();
  }
  function liga() {
    if (!raf && naTela && !document.hidden && largura) raf = requestAnimationFrame(quadro);
  }
  function desliga() {
    if (raf) cancelAnimationFrame(raf);
    raf = 0; ultimo = 0;
  }

  function redimensiona() {
    if (mede()) { desenha(); liga(); }
  }
  redimensiona();
  if ("ResizeObserver" in window) new ResizeObserver(redimensiona).observe(hero);
  else window.addEventListener("resize", redimensiona);

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entradas) {
      naTela = entradas[0].isIntersecting;
      if (naTela) liga(); else desliga();
    }, { threshold: 0 }).observe(hero);
  }
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) desliga(); else liga();
  });

  leRolagem();
  window.addEventListener("scroll", leRolagem, { passive: true });
})();
