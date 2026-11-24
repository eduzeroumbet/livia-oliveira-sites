/* Black Friday do Carreira com Sentido (2026): configuração única, fim automático e contagem regressiva.
 *
 * Carregado SEM defer no <head> das páginas com Black Friday (antes do site.js), para decidir o estado antes de
 * pintar a página. O HTML já vem com o conteúdo da Black Friday; depois de BF.fim (hora do aparelho) este script
 * põe a classe bf-fim no <html> e o assets/css/bf.css esconde o que é da Black Friday ([data-bf="on"]) e mostra
 * o texto normal ([data-bf="off"]). Sem novo deploy e sem "piscar" de preço.
 *
 *   window.BF          configuração (fim, oferta da Hotmart, preço, parcela e preço "de")
 *   window.bfAtiva()   true até BF.fim
 *   document "bf:fim"  evento disparado se o prazo acabar com a página aberta (a classe bf-fim entra na hora)
 *
 * Contagem regressiva: [data-bf-contagem] recebe o texto curto ("2d 04h 12min 09s"); [data-bf-dias],
 * [data-bf-horas], [data-bf-min] e [data-bf-seg] recebem os números com 2 dígitos.
 *
 * Hora do servidor: logo ao carregar, um HEAD (sem cache) na própria página lê o cabeçalho Date. O estado inicial é
 * decidido pelo relógio do aparelho (sem "piscar" de preço) e só muda se o servidor disser que o aparelho está mais de
 * 60s adiantado ou atrasado; aí a contagem e o estado (ativa/encerrada) passam a usar a hora do servidor. Se o HEAD
 * falhar, fica o relógio do aparelho. Se o servidor disser que ainda vale, a classe bf-fim sai e vem o evento "bf:ativa".
 *
 * Teste: ?bf_agora=<data ISO> simula a hora do aparelho, só em localhost/127.0.0.1 (no site publicado é ignorado), e
 * tem prioridade sobre a hora do servidor.
 * Para encerrar antes ou estender, mude BF.fim (e suba o ?v= do bf.js nas páginas).
 *
 * Páginas black-friday/ (body.page-bf), no celular: o botão flutuante do WhatsApp (.wa-float) ganha a classe bf-wa-on
 * quando o hero sai da tela (o assets/css/bf.css esconde o botão enquanto o hero aparece; html.bf-io indica suporte
 * a IntersectionObserver, sem ele nada muda).
 */
window.BF = { fim: "2026-11-30T23:59:59-03:00", oferta: "qu4x7j2d", preco: "499,99", parcela: "41,67", de: "860" };
/* valor numérico para os eventos (499.99) */
window.BF.valor = Number(window.BF.preco.replace(/\./g, "").replace(",", "."));

(function () {
  "use strict";

  var fim = new Date(window.BF.fim).getTime();
  var desvio = 0;
  var teste = false;
  if (/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) {
    var simulacao = new URLSearchParams(location.search).get("bf_agora");
    var simulado = simulacao ? new Date(simulacao).getTime() : NaN;
    if (!isNaN(simulado)) {
      desvio = simulado - Date.now();
      teste = true;
    }
  }
  function agora() { return Date.now() + desvio; }

  window.bfAtiva = function () { return agora() <= fim; };

  var raiz = document.documentElement;
  function encerra() {
    if (raiz.classList.contains("bf-fim")) return;
    raiz.classList.add("bf-fim");
    try { document.dispatchEvent(new Event("bf:fim")); } catch (e) {}
  }
  function quandoPronto(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  function dois(n) { return (n < 10 ? "0" : "") + n; }

  function atualiza() {
    var resta = Math.max(0, Math.floor((fim - agora()) / 1000));
    var d = Math.floor(resta / 86400), h = Math.floor(resta % 86400 / 3600);
    var m = Math.floor(resta % 3600 / 60), s = resta % 60;
    var curto = (d ? d + "d " : "") + dois(h) + "h " + dois(m) + "min " + dois(s) + "s";
    document.querySelectorAll("[data-bf-contagem]").forEach(function (el) { el.textContent = curto; });
    [["data-bf-dias", d], ["data-bf-horas", h], ["data-bf-min", m], ["data-bf-seg", s]].forEach(function (par) {
      document.querySelectorAll("[" + par[0] + "]").forEach(function (el) { el.textContent = dois(par[1]); });
    });
    if (!window.bfAtiva()) {
      encerra();
      return false;
    }
    return true;
  }

  var relogio = null;
  function inicia() {
    if (relogio || !atualiza()) return;
    relogio = setInterval(function () {
      if (!atualiza()) {
        clearInterval(relogio);
        relogio = null;
      }
    }, 1000);
  }
  if (window.bfAtiva()) quandoPronto(inicia);
  else raiz.classList.add("bf-fim");

  /* hora do servidor (fora do modo de teste): só corrige o relógio se a diferença passar de 60s */
  if (!teste && window.fetch) {
    var enviado = Date.now();
    fetch(location.pathname, { method: "HEAD", cache: "no-store" }).then(function (r) {
      var data = r.headers.get("Date");
      var servidor = data ? new Date(data).getTime() : NaN;
      if (isNaN(servidor)) return;
      var diferenca = servidor - (enviado + Date.now()) / 2;
      if (Math.abs(diferenca) <= 60000) return;
      desvio = diferenca;
      if (window.bfAtiva()) {
        if (raiz.classList.contains("bf-fim")) {
          raiz.classList.remove("bf-fim");
          try { document.dispatchEvent(new Event("bf:ativa")); } catch (e) {}
        }
        quandoPronto(inicia);
      } else {
        quandoPronto(atualiza);
      }
    }).catch(function () {});
  }

  /* black-friday/ no celular: WhatsApp flutuante só depois que o hero sai da tela */
  if ("IntersectionObserver" in window) {
    raiz.classList.add("bf-io");
    quandoPronto(function () {
      var wa = document.querySelector(".page-bf .wa-float");
      if (!wa) return;
      var hero = document.querySelector(".page-bf .hero");
      if (!hero) {
        wa.classList.add("bf-wa-on");
        return;
      }
      new IntersectionObserver(function (entries) {
        wa.classList.toggle("bf-wa-on", !entries[entries.length - 1].isIntersecting);
      }).observe(hero);
    });
  }
})();
