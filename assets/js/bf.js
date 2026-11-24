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
 * Teste: ?bf_agora=<data ISO> simula a hora do aparelho, só em localhost/127.0.0.1 (no site publicado é ignorado).
 * Para encerrar antes ou estender, mude BF.fim (e suba o ?v= do bf.js nas páginas).
 */
window.BF = { fim: "2026-11-30T23:59:59-03:00", oferta: "qu4x7j2d", preco: "499,99", parcela: "41,67", de: "860" };
/* valor numérico para os eventos (499.99) */
window.BF.valor = Number(window.BF.preco.replace(/\./g, "").replace(",", "."));

(function () {
  "use strict";

  var fim = new Date(window.BF.fim).getTime();
  var desvio = 0;
  if (/^(localhost|127\.0\.0\.1)$/.test(location.hostname)) {
    var teste = new URLSearchParams(location.search).get("bf_agora");
    var simulado = teste ? new Date(teste).getTime() : NaN;
    if (!isNaN(simulado)) desvio = simulado - Date.now();
  }
  function agora() { return Date.now() + desvio; }

  window.bfAtiva = function () { return agora() <= fim; };

  var raiz = document.documentElement;
  function encerra() {
    if (raiz.classList.contains("bf-fim")) return;
    raiz.classList.add("bf-fim");
    try { document.dispatchEvent(new Event("bf:fim")); } catch (e) {}
  }
  if (!window.bfAtiva()) {
    raiz.classList.add("bf-fim");
    return;
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

  function inicia() {
    if (!atualiza()) return;
    var relogio = setInterval(function () { if (!atualiza()) clearInterval(relogio); }, 1000);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", inicia);
  else inicia();
})();
