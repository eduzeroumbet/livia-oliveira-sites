/* Lívia Oliveira: calculadora do valor da sessão (calculadora/). Depende do site.js (window.siteTrack) */
(function () {
  "use strict";

  var form = document.getElementById("calc");
  var resultado = document.getElementById("resultado");
  var atual = document.getElementById("atual");
  var conhecer = document.getElementById("conhecer-curso");
  if (!form || !resultado) return;

  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var CUSTOS = ["aluguel", "supervisao", "terapia", "cursos", "plataforma", "outros"];
  var ultima = null;      // última conta válida (para o "Quanto você cobra hoje?")
  var leadEnviado = false; // generate_lead uma vez por carregamento

  function track(event, params) {
    if (window.siteTrack) window.siteTrack(event, params);
  }

  /* Aceita "1.200,50", "1200,5", "1200.5" e "R$ 800". Vazio = null; texto inválido = NaN */
  function numero(texto) {
    var t = String(texto || "").replace(/[R$\s%]/g, "");
    if (!t) return null;
    if (t.indexOf(",") >= 0) t = t.replace(/\./g, "").replace(",", ".");
    else if (/^\d{1,3}(\.\d{3})+$/.test(t)) t = t.replace(/\./g, "");
    return /^-?\d*\.?\d+$/.test(t) ? parseFloat(t) : NaN;
  }

  function reais(v) {
    return "R$ " + Math.round(v).toLocaleString("pt-BR");
  }

  function arredonda5(v) {
    return Math.ceil(v / 5) * 5;
  }

  function setError(name, message) {
    var out = form.querySelector('[data-error-for="' + name + '"]');
    if (out) out.textContent = message || "";
    var el = form.elements[name];
    if (message) el.setAttribute("aria-invalid", "true");
    else el.removeAttribute("aria-invalid");
  }

  function calcula() {
    var erros = [];
    function fail(name, message) { erros.push(name); setError(name, message); }
    function campo(name, padraoVazio) {
      setError(name, "");
      var v = numero(form.elements[name].value);
      if (v === null) {
        if (padraoVazio !== undefined) return padraoVazio;
        fail(name, "Preencha este campo.");
        return 0;
      }
      if (isNaN(v)) { fail(name, "Use só números, por exemplo 800 ou 1.200,50."); return 0; }
      if (v < 0) { fail(name, "O valor não pode ser negativo."); return 0; }
      return v;
    }

    var custos = CUSTOS.reduce(function (soma, name) { return soma + campo(name, 0); }, 0);
    var imposto = campo("imposto");
    var meta = campo("meta", 0);
    var sessoes = campo("sessoes");
    var semanas = campo("semanas");
    var faltas = campo("faltas", 0);

    if (erros.indexOf("imposto") < 0 && imposto >= 100) fail("imposto", "O imposto precisa ser menor que 100%.");
    if (erros.indexOf("semanas") < 0 && semanas > 52) fail("semanas", "O ano tem 52 semanas. Coloque quantas você trabalha de fato.");
    if (erros.indexOf("faltas") < 0 && faltas >= 100) fail("faltas", "As faltas precisam ser menores que 100%.");

    var sessoesMes = sessoes * semanas / 12 * (1 - faltas / 100);
    if (!erros.length && !(sessoesMes > 0)) {
      if (!(sessoes > 0)) fail("sessoes", "Coloque quantas sessões você atende por semana.");
      else fail("semanas", "Coloque quantas semanas você trabalha no ano.");
    }

    if (erros.length) {
      form.elements[erros[0]].focus();
      return null;
    }

    var liquido = 1 - imposto / 100;
    return {
      custos: custos,
      meta: meta,
      liquido: liquido,
      sessoesMes: sessoesMes,
      custo: custos / sessoesMes,
      minimo: arredonda5(custos / sessoesMes / liquido),
      ideal: arredonda5((custos + meta) / sessoesMes / liquido)
    };
  }

  function mostraAtual() {
    var out = resultado.querySelector('[data-out="atual"]');
    var preco = numero(atual.value);
    if (!ultima || preco === null) { out.textContent = ""; return; }
    if (isNaN(preco) || preco <= 0) { out.textContent = "Coloque o valor da sua sessão, por exemplo 120."; return; }
    var ganho = preco * ultima.sessoesMes * ultima.liquido - ultima.custos;
    var dif = ganho - ultima.meta;
    var texto = ganho >= 0
      ? "Cobrando " + reais(preco) + " por sessão, você ganharia cerca de " + reais(ganho) + " por mês, líquido. "
      : "Cobrando " + reais(preco) + " por sessão, você teria um prejuízo de cerca de " + reais(-ganho) + " por mês. ";
    if (Math.round(dif) === 0) texto += "É exatamente a sua meta.";
    else if (dif < 0) texto += "Faltam " + reais(-dif) + " por mês para a sua meta.";
    else texto += "São " + reais(dif) + " por mês acima da sua meta.";
    out.textContent = texto;
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var r = calcula();
    if (!r) return;
    ultima = r;
    resultado.querySelector('[data-out="custo"]').textContent = reais(Math.ceil(r.custo));
    resultado.querySelector('[data-out="minimo"]').textContent = reais(r.minimo);
    resultado.querySelector('[data-out="ideal"]').textContent = reais(r.ideal);
    mostraAtual();
    resultado.hidden = false;
    resultado.scrollIntoView({ behavior: reduz ? "auto" : "smooth", block: "start" });
    resultado.focus({ preventScroll: true });
    if (!leadEnviado) {
      leadEnviado = true;
      track("generate_lead", { content_name: "calculadora_sessao", content_category: "calc" });
    }
  });

  form.querySelectorAll("input").forEach(function (el) {
    el.addEventListener("input", function () { if (el.getAttribute("aria-invalid")) setError(el.name, ""); });
  });
  atual.addEventListener("input", mostraAtual);

  /* "Conhecer o curso": leva as UTMs da visita para curso/b/ (o site.js já repassa a query string; aqui
     garante os utm_* mesmo assim) e registra view_offer / ViewContent */
  /* Contato opcional depois do resultado: vai para a Lambda livia-leads pelo site.js (pagina pgCalc, ferramenta
   * calculadora, resultado com mínimo, ideal e custo da última conta). Dispara contato_calculadora
   * (ContatoCalculadora), não outro Lead. Erro ou demora da Lambda também mostram o sucesso (espera no máximo 1,5 s). */
  var contatoForm = document.getElementById("contato");
  var contato = window.siteContato;
  if (contatoForm && contato) {
    var contatoBotao = contatoForm.querySelector('button[type="submit"]');
    var contatoEnviado = false;
    contato.prepara(contatoForm);
    contatoForm.addEventListener("submit", function (e) {
      e.preventDefault();
      if (contatoEnviado || !ultima || !contato.valida(contatoForm)) return;
      contatoEnviado = true;
      contatoBotao.disabled = true;
      contatoBotao.textContent = "Enviando...";
      var dados = contato.dados(contatoForm, {
        ferramenta: "calculadora",
        resultado: "minimo=" + Math.round(ultima.minimo) + ";ideal=" + Math.round(ultima.ideal) + ";custo=" + Math.ceil(ultima.custo)
      });
      if (window.siteIdentify) window.siteIdentify({ em: dados.email, ph: "55" + dados.whatsapp, fn: dados.nome.split(" ")[0].toLowerCase() });
      track("contato_calculadora", { content_name: "calculadora_sessao", content_category: "calc" });
      contato.envia(dados).then(function () {
        var okMsg = document.getElementById("contato-ok");
        contatoForm.hidden = true;
        okMsg.hidden = false;
        okMsg.focus();
      });
    });
  }

  if (conhecer) {
    var visita = new URLSearchParams(location.search);
    var url = new URL(conhecer.href);
    visita.forEach(function (v, k) {
      if (/^utm_/.test(k) && !url.searchParams.has(k)) url.searchParams.set(k, v);
    });
    conhecer.href = url.toString();
    conhecer.addEventListener("click", function () {
      track("view_offer", { content_name: "calculadora_para_curso" });
    });
  }
})();
