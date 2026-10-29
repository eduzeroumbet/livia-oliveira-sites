/* Lívia Oliveira: quiz "Você está pronta para viver da clínica?" (quiz/). Depende do site.js (window.siteTrack e
 * window.siteContato).
 *
 * Uma pergunta por vez (Sim/Não avança sozinho; Voltar refaz a anterior). Na 5ª resposta mostra o resultado na hora
 * (faixa base 0 a 1 sim, meio 2 a 3, pronta 4 a 5) e o formulário de contato. O envio vai para a Lambda livia-leads
 * (pagina pgQuiz, ferramenta quiz, pontos, resultado = faixa, respostas = "S,N,...") e espera no máximo 1,5 s:
 * o plano aparece mesmo com erro. Eventos: quiz_inicio (QuizInicio), quiz_completo (QuizCompleto, com pontos e
 * faixa), generate_lead (Lead, content_name "quiz"; o único Lead da página) e view_offer (ViewContent,
 * content_name "quiz_para_curso") no clique em "Conhecer o curso". Sem InitiateCheckout.
 */
(function () {
  "use strict";

  var PERGUNTAS = [
    {
      texto: "Você sabe quanto custa cada sessão que você atende, somando custos fixos, impostos e faltas?",
      fazer: ["Defina o valor da sessão pela conta, não no chute. Comece pela ", { link: "../calculadora/", texto: "calculadora do valor da sessão" }, "."],
      curso: "Módulo 2, A base que sustenta o consultório.",
      forte: "Ponto forte: você já conhece os seus números."
    },
    {
      texto: "Você usa contrato terapêutico e tem uma regra de faltas que explica já na primeira sessão?",
      fazer: ["Contrato, recibo e regra de faltas protegem você e o paciente, e fazem o paciente entender o processo desde o início."],
      curso: "Módulos 2 e 3, gestão e comunicação assertiva.",
      forte: "Ponto forte: a sua clínica já tem regras claras."
    },
    {
      texto: "Você consegue falar o valor da sessão, e reajustar, sem se sentir culpada?",
      fazer: ["Falar de valor é uma habilidade, não um dom. Dá para aprender a comunicar valor, faltas e reajuste com segurança."],
      curso: "Módulo 3, Comunicação assertiva.",
      forte: "Ponto forte: você comunica o seu valor com segurança."
    },
    {
      texto: "Seus pacientes chegam por mais de um caminho: indicação, rede de colegas e internet?",
      fazer: ["Depender de um só canal deixa a agenda instável. Networking e indicação também enchem a agenda."],
      curso: "Módulos 6 e 9, Digital como vitrine e Captação offline.",
      forte: "Ponto forte: a sua agenda não depende de um só canal."
    },
    {
      texto: "Você sabe o que postar no Instagram, com ética e sem virar uma personagem?",
      fazer: ["O Instagram é vitrine, não palco. Dá para mostrar o seu trabalho do seu jeito, dentro do Código de Ética."],
      curso: "Módulos 4, 5, 7 e 8, branding, marketing ético, Instagram e conteúdo.",
      forte: "Ponto forte: você já usa o digital a seu favor."
    }
  ];
  var FAIXAS = {
    base: { titulo: "Hora de construir a base.", texto: "Você já tem a formação e o cuidado com o paciente. O que falta é estrutura, e é por ela que tudo começa." },
    meio: { titulo: "Você já começou. Falta organizar.", texto: "Parte da estrutura já existe. Organizar o que falta é o que transforma atendimentos em carreira." },
    pronta: { titulo: "Você está pronta. Agora é crescer com estratégia.", texto: "A base está de pé. O próximo passo é posicionamento e presença para atrair os pacientes certos." }
  };
  var WHATSAPP = "5551992597638";

  var capa = document.getElementById("capa");
  var perguntas = document.getElementById("perguntas");
  var resultado = document.getElementById("resultado");
  var form = document.getElementById("contato");
  var plano = document.getElementById("plano");
  if (!capa || !perguntas || !resultado || !form || !plano) return;

  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var visita = new URLSearchParams(location.search);
  var respostas = [];   // true = Sim, false = Não, na ordem das perguntas
  var atual = 0;
  var iniciou = false;  // quiz_inicio uma vez por carregamento
  var completou = false;
  var enviado = false;
  var pontos = 0;
  var faixa = "";

  function track(event, params) {
    if (window.siteTrack) window.siteTrack(event, params);
  }

  function rola(el) {
    el.scrollIntoView({ behavior: reduz ? "auto" : "smooth", block: "start" });
  }

  /* Link interno com a query da visita (como o site.js faz nos links do HTML) */
  function comVisita(href) {
    var url = new URL(href, location.href);
    visita.forEach(function (v, k) {
      if (!url.searchParams.has(k)) url.searchParams.set(k, v);
    });
    return url.toString();
  }

  /* Curso com as UTMs da visita e utm_content + "_quiz_<faixa>"; sem UTM: site / quiz / ccs_quiz / quiz_<faixa> */
  function linkCurso() {
    var url = new URL(comVisita("../curso/b/"));
    var temUtm = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"].some(function (k) { return visita.get(k); });
    if (!temUtm) {
      url.searchParams.set("utm_source", "site");
      url.searchParams.set("utm_medium", "quiz");
      url.searchParams.set("utm_campaign", "ccs_quiz");
    }
    var conteudo = visita.get("utm_content");
    url.searchParams.set("utm_content", (conteudo ? conteudo + "_" : "") + "quiz_" + faixa);
    return url.toString();
  }

  /* ---------- Perguntas ---------- */
  var passo = document.getElementById("quiz-passo");
  var barra = perguntas.querySelector(".quiz-barra");
  var titulo = document.getElementById("quiz-pergunta");
  var botoes = perguntas.querySelectorAll(".quiz-op");

  function mostraPergunta(i, foca) {
    atual = i;
    passo.textContent = "Pergunta " + (i + 1) + " de " + PERGUNTAS.length;
    barra.setAttribute("aria-valuenow", String(i + 1));
    barra.firstElementChild.style.width = ((i + 1) / PERGUNTAS.length * 100) + "%";
    titulo.textContent = PERGUNTAS[i].texto;
    botoes.forEach(function (b) {
      var escolhida = respostas[i] !== undefined && (b.getAttribute("data-resposta") === "S") === respostas[i];
      b.classList.toggle("is-escolhida", escolhida);
    });
    if (foca) titulo.focus({ preventScroll: true });
  }

  document.getElementById("comecar").addEventListener("click", function () {
    if (!iniciou) {
      iniciou = true;
      track("quiz_inicio", { content_name: "quiz" });
    }
    capa.hidden = true;
    perguntas.hidden = false;
    mostraPergunta(0, true);
    window.scrollTo(0, 0);
  });

  botoes.forEach(function (b) {
    b.addEventListener("click", function () {
      respostas[atual] = b.getAttribute("data-resposta") === "S";
      if (atual < PERGUNTAS.length - 1) mostraPergunta(atual + 1, true);
      else mostraResultado();
    });
  });

  document.getElementById("quiz-voltar").addEventListener("click", function () {
    if (atual > 0) {
      mostraPergunta(atual - 1, true);
      return;
    }
    perguntas.hidden = true;
    capa.hidden = false;
    document.getElementById("comecar").focus();
  });

  /* ---------- Resultado ---------- */
  function mostraResultado() {
    pontos = respostas.filter(Boolean).length;
    faixa = pontos <= 1 ? "base" : pontos <= 3 ? "meio" : "pronta";
    document.getElementById("quiz-pontos").textContent = "Você respondeu sim para " + pontos + " de " + PERGUNTAS.length;
    document.querySelectorAll("#quiz-bolinhas i").forEach(function (b, i) { b.classList.toggle("on", i < pontos); });
    document.getElementById("resultado-titulo").textContent = FAIXAS[faixa].titulo;
    document.getElementById("resultado-texto").textContent = FAIXAS[faixa].texto;
    resultado.setAttribute("data-faixa", faixa);
    document.getElementById("curso-direto").href = linkCurso();

    perguntas.hidden = true;
    resultado.hidden = false;
    window.scrollTo(0, 0);
    resultado.focus({ preventScroll: true });
    if (!completou) {
      completou = true;
      track("quiz_completo", { content_name: "quiz", pontos: pontos, faixa: faixa });
    }
  }

  /* ---------- Plano: um card por pergunta, os "Não" primeiro ---------- */
  function item(i) {
    var p = PERGUNTAS[i];
    var sim = respostas[i];
    var li = document.createElement("li");
    li.className = "quiz-item" + (sim ? " quiz-item--forte" : "");
    function linha(classe, conteudo) {
      var el = document.createElement("p");
      el.className = classe;
      conteudo.forEach(function (c) {
        if (typeof c === "string") { el.appendChild(document.createTextNode(c)); return; }
        var a = document.createElement("a");
        a.href = comVisita(c.link);
        a.textContent = c.texto;
        el.appendChild(a);
      });
      li.appendChild(el);
    }
    linha("quiz-item__tipo", [sim ? "Ponto forte" : "O que fazer"]);
    linha("quiz-item__pergunta", [p.texto]);
    if (sim) {
      linha("quiz-item__texto", [p.forte]);
    } else {
      linha("quiz-item__texto", p.fazer);
      linha("quiz-item__curso", ["No curso: " + p.curso]);
    }
    return li;
  }

  function mostraPlano() {
    var lista = document.getElementById("plano-itens");
    lista.textContent = "";
    var ordem = PERGUNTAS.map(function (_, i) { return i; });
    ordem.filter(function (i) { return !respostas[i]; })
      .concat(ordem.filter(function (i) { return respostas[i]; }))
      .forEach(function (i) { lista.appendChild(item(i)); });

    var conhecer = document.getElementById("conhecer-curso");
    conhecer.href = linkCurso();
    document.getElementById("quiz-wa").href = "https://wa.me/" + WHATSAPP + "?text=" + encodeURIComponent(
      "Oi! Fiz o quiz da Lívia e respondi sim para " + pontos + " de 5. Quero saber mais sobre o Carreira com Sentido.");

    form.hidden = true;
    document.getElementById("quiz-direto").hidden = true;
    plano.hidden = false;
    rola(plano);
    plano.focus({ preventScroll: true });
  }

  document.getElementById("conhecer-curso").addEventListener("click", function () {
    track("view_offer", { content_name: "quiz_para_curso" });
  });

  /* ---------- Contato ---------- */
  var contato = window.siteContato;
  var button = form.querySelector('button[type="submit"]');
  contato.prepara(form);

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (enviado || !contato.valida(form)) return;
    enviado = true;
    button.disabled = true;
    button.textContent = "Enviando...";

    var dados = contato.dados(form, {
      ferramenta: "quiz",
      pontos: String(pontos),
      resultado: faixa,
      respostas: respostas.map(function (r) { return r ? "S" : "N"; }).join(",")
    });
    /* advanced matching só no Pixel (o Pixel faz o hash); GA4 e dataLayer sem dados pessoais */
    if (window.siteIdentify) window.siteIdentify({ em: dados.email, ph: "55" + dados.whatsapp, fn: dados.nome.split(" ")[0].toLowerCase() });
    track("generate_lead", { content_name: "quiz", content_category: faixa });
    contato.envia(dados).then(mostraPlano);
  });
})();
