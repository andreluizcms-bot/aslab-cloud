const $ = (s) => document.querySelector(s);
const DIAS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"];
const TIPOS = [
  ["", "— folga —"], ["teste_limiar", "Teste de limiar 30'"], ["limiar", "Limiar (sem pré-fadiga)"],
  ["limiar_prefadiga", "Limiar c/ pré-fadiga"],
  ["escada_limiar", "Escada de limiar"],
  ["segundo_limiar", "Segundo limiar"],
  ["limiar_vo2", "Limiar + VO2"],
  ["vo2max", "VO2max"],
  ["ritmo_prova", "Ritmo de prova"],
  ["over_under", "Over/Under"],
  ["piramide", "Pirâmide"],
  ["fartlek", "Fartlek"],
  ["longo", "Longo"], ["longo_continuo", "Longo continuo"],
  ["longo_trocas", "Longo com trocas"], ["longo_bloco", "Longo em bloco"],
  ["longo_progressivo", "Longo progressivo"],
  ["longo_alternado", "Longo alternado"],
  ["longo_surges", "Longo c/ surges"],
  ["progressivo", "Progressivo"],
  ["rodagem", "Rodagem (varia strides)"],
  ["rodagem_strides", "Rodagem c/ strides"],
  ["rodagem_leve", "Rodagem sem strides"],
  ["corre_anda", "Corre e anda"],
  ["bike_rodagem", "Bike giro Z2"],
  ["bike_intervalado", "Bike intervalado"],
  ["bike_longa", "Bike longa"],
  ["cic_endurance", "Endurance (zona 2)"], ["cic_leve", "Pedal leve"], ["cic_longao", "Longão"],
  ["cic_tempo", "Tempo em blocos"], ["cic_sweet", "Sweet spot (sem estudo)"], ["cic_limiar", "Limiar"],
  ["cic_over_under", "Over/under (sem estudo)"], ["cic_vo2", "VO2máx"], ["cic_3015", "Intervalado 30/15"],
  ["cic_sprint", "Sprints 30\""], ["cic_torque", "Torque em subida"], ["cic_xco", "Simulação XCO (sem estudo)"],
  ["cic_tecnica", "Técnica de MTB"], ["cic_teste_ftp", "Teste de FTP 20'"],
  ["forca", "Força (academia)"],
  ["forca_inferior", "Força · membros inferiores"],
  ["forca_superior", "Força · membros superiores"],
  ["forca_empurrar", "Força · empurrar"],
  ["forca_puxar", "Força · puxar"],
  ["forca_core", "Força · core"],
  ["forca_pliometria", "Força · pliometria"],
  ["forca_estab_core", "Força · estabilidade de core"],
  ["forca_ativ_gluteo", "Força · ativação de glúteo"],
  ["forca_ativ_superiores", "Força · ativação de membros superiores"],
];

let ATLETAS = [], DADOS = null, PREVIA = null;
let FORCA_BIB = null;   // treinos das bibliotecas de força do treinador

// objetivo (5k/10k/21k/42k) a partir da distância da prova no calendário
function objetivoPorKm(km) {
  if (!km) return "";
  if (km >= 40) return "42k";
  if (km >= 19) return "21k";
  if (km >= 9) return "10k";
  if (km >= 4) return "5k";
  return "";
}
function fmtBR(iso) { return iso.split("-").reverse().join("/"); }

function pintarProvasCal() {
  const sel = $("#prova-cal");
  const provas = (DADOS && DADOS.provas) || [];
  if (!provas.length) {
    sel.innerHTML = `<option value="">— nenhuma prova no calendário —</option>`; return;
  }
  sel.innerHTML = `<option value="">— escolher da lista —</option>` +
    provas.map((p, i) => {
      const k = kmDaProva(p);
      const km = k ? ` · ${+(+k).toFixed(1)} km` : "";
      const prio = p.prio ? ` [${p.prio}]` : "";
      return `<option value="${i}">${fmtBR(p.date)} — ${p.name}${km}${prio}</option>`;
    }).join("");
}

// ---- objetivo: 5, 10, 21, 42 km ou outra distância digitada ----
const KM_OBJ = { "5k": 5, "10k": 10, "21k": 21.1, "42k": 42.2 };
// estrutura de ciclo que o motor usa (a distância digitada cai na mais próxima)
function objetivoMotor() {
  const v = $("#prova").value;
  if (v !== "outra") return v;
  const km = parseFloat($("#prova-km").value);
  return objetivoPorKm(km) || (km > 0 ? "5k" : "");
}
// distância da prova A: a digitada em "Outra distância" ou a da prova do Dia na lista
function kmObjetivo() {
  if ($("#prova").value === "outra") return parseFloat($("#prova-km").value) || null;
  const c = ((DADOS && DADOS.provas) || []).find((x) => x.date === $("#prova-data").value);
  return c && kmDaProva(c) ? +kmDaProva(c) : null;
}
function rotuloObjetivo() {
  if ($("#prova").value !== "outra") return $("#prova").value;
  const km = parseFloat($("#prova-km").value);
  return km > 0 ? `${+km.toFixed(1)} km` : "";
}
function mostrarKmObjetivo() {
  const outra = $("#prova").value === "outra";
  $("#lbl-prova-km").classList.toggle("oculto", !outra);
  const km = parseFloat($("#prova-km").value), obj = objetivoMotor();
  const dica = $("#prova-km-dica");
  dica.classList.toggle("oculto", !(outra && km > 0));
  if (outra && km > 0) dica.textContent = `${+km.toFixed(1)} km: as fases e o polimento seguem o ciclo de ` +
    `${obj.replace("k", " km")}; o ritmo de prova e a sessão do dia usam os ${+km.toFixed(1)} km.`;
}
// escolhe o objetivo pela distância da prova: 5, 10, 21 ou 42 km quando bate, senão "Outra"
function definirObjetivo(km) {
  km = parseFloat(km);
  if (!(km > 0)) return false;
  const padrao = Object.entries(KM_OBJ).find(([, k]) => Math.abs(k - km) <= (k > 30 ? 0.8 : k > 15 ? 0.6 : 0.3));
  if (padrao) { $("#prova").value = padrao[0]; $("#prova-km").value = ""; }
  else { $("#prova").value = "outra"; $("#prova-km").value = +km.toFixed(1); }
  mostrarKmObjetivo();
  return true;
}

// ---- lista de provas do atleta: TP + digitadas à mão, cada uma A, B, C ou ignorar ----
// A prova A é a do campo "Dia". A lista fica salva por atleta no Lab e as B e C vão
// para o plano do ciclo; trocar a A não tira a anterior da lista (ela vira B).
let PROVAS_PRIO = {};          // {date: "B"|"C"|"fora"} escolhido pelo treinador nesta tela
let PROVAS_KM = {};            // {date: km} digitado pelo treinador: vale mais que o do TP
const kmDaProva = (p) => (PROVAS_KM[p.date] != null ? PROVAS_KM[p.date]
  : p.km_salvo != null ? p.km_salvo : p.km);
function prioDe(p) {
  if (p.date === $("#prova-data").value) return "A";
  const e = PROVAS_PRIO[p.date] || p.escolha;
  if (e === "A") return "B";                     // era a A e outra prova virou a A
  if (e) return e;
  return (p.prio || "").toUpperCase() === "C" ? "C" : "B";
}
function provasDoBloco() {
  if (modalidade() === "forca") return [];     // bloco só de força não olha prova
  const ini = $("#inicio").value, fim = $("#fim").value, a = $("#prova-data").value;
  const out = [];
  if (a) out.push({ date: a, name: $("#prova-nome").value || "Prova", prio: "A", km: kmObjetivo() });
  ((DADOS && DADOS.provas) || []).forEach((p) => {
    if (p.date === a || !ini || !fim || p.date < ini || p.date > fim) return;
    const prio = prioDe(p);
    if (prio !== "fora") out.push({ date: p.date, name: p.name, prio, km: kmDaProva(p) });
  });
  return out;
}
// provas B e C de toda a lista (o ciclo do Lab pode ir além do bloco)
function provasParaCiclo() {
  return ((DADOS && DADOS.provas) || []).filter((p) => p.date !== $("#prova-data").value)
    .map((p) => ({ date: p.date, name: p.name, prio: prioDe(p), km: kmDaProva(p) || null }))
    .filter((p) => p.prio === "B" || p.prio === "C");
}
// a prova do Dia sempre está na lista; digitada à mão entra como prova manual
function garantirProvaDoDia() {
  const a = $("#prova-data").value;
  if (!a || !DADOS) return;
  DADOS.provas = DADOS.provas || [];
  let p = DADOS.provas.find((x) => x.date === a);
  if (!p) {
    p = { date: a, name: $("#prova-nome").value || "Prova", km: kmObjetivo(), prio: "", origem: "manual",
          escolha: "A", auto: true };
    DADOS.provas.push(p);
    DADOS.provas.sort((x, y) => x.date.localeCompare(y.date));
  } else if (p.origem === "manual") {
    if ($("#prova-nome").value) p.name = $("#prova-nome").value;
    if ($("#prova").value === "outra" && kmObjetivo()) p.km = kmObjetivo();
  }
}
// a prova do Dia mudou: a anterior continua na lista como B (a criada só pelo Dia sai)
let DIA_ANTERIOR = "";
function provaDoDiaMudou() {
  const ant = DIA_ANTERIOR, a = $("#prova-data").value;
  if (ant && ant !== a && DADOS && DADOS.provas) {
    const p = DADOS.provas.find((x) => x.date === ant);
    if (p && p.auto) DADOS.provas = DADOS.provas.filter((x) => x !== p);
    else if (p) PROVAS_PRIO[ant] = "B";
  }
  DIA_ANTERIOR = a;
  garantirProvaDoDia();
  pintarProvasCal();
  pintarProvasBloco();
  salvarProvasDepois();
}
function pintarProvasBloco() {
  const box = $("#provas-bloco"); if (!box) return;
  if (!DADOS) { box.classList.add("oculto"); box.innerHTML = ""; return; }
  const ini = $("#inicio").value, fim = $("#fim").value;
  const hoje = new Date().toISOString().slice(0, 10);
  const lista = (DADOS.provas || []).filter((p) => p.date >= hoje || (ini && p.date >= ini));
  box.classList.remove("oculto");
  const linhas = lista.map((p) => {
    const prio = prioDe(p);
    const km = kmDaProva(p);
    const fora = !(ini && fim && p.date >= ini && p.date <= fim);
    const origem = p.origem === "manual" ? "digitada" : p.prio ? "TP: " + p.prio : "TP";
    return `<div class="pv${prio === "A" ? " eh-a" : ""}${fora ? " fora-bloco" : ""}${prio === "fora" ? " ignorada" : ""}">
      <b>${fmtBR(p.date)}</b> ${p.name}<small>${origem}${fora ? " · fora do bloco" : ""}</small>
      <label class="pv-km${PROVAS_KM[p.date] != null ? " manual" : ""}" title="Distância da prova. Vem do TP ou do que foi digitado; digite para corrigir">
        <input type="number" class="km-prova" data-date="${p.date}" min="1" max="250" step="0.1"
          value="${km ? +(+km).toFixed(1) : ""}" placeholder="?"> km</label>
      <select class="prio-sel" data-date="${p.date}">${["A", "B", "C", "fora"].map((o) =>
        `<option value="${o}" ${o === prio ? "selected" : ""}>${o === "fora" ? "ignorar" : "Prova " + o}</option>`).join("")}</select>
      ${p.origem === "manual" && prio !== "A" ? `<button type="button" class="pv-del ghost" data-date="${p.date}" title="Tirar da lista">×</button>` : ""}</div>`;
  }).join("");
  box.innerHTML = `<span class="rotulo">Provas do atleta · A manda no ciclo · B tem mini-polimento e dias leves depois, pela distância · C entra sem polimento</span>` +
    (linhas || `<p class="dica" style="margin:2px 0 6px">Nenhuma prova no TP. Digite abaixo para incluir.</p>`) +
    `<div class="pv pv-novo">
      <input type="date" id="pv-n-data" title="Dia da prova">
      <input type="text" id="pv-n-nome" placeholder="nome da prova">
      <label class="pv-km"><input type="number" id="pv-n-km" min="1" max="250" step="0.1" placeholder="km"> km</label>
      <select id="pv-n-prio"><option value="B">Prova B</option><option value="C">Prova C</option><option value="A">Prova A</option></select>
      <button type="button" class="secundario" id="pv-n-add">Adicionar prova</button></div>` +
    avisoCicloProvas();
}
// o ciclo do Lab já tem o km das semanas com essas provas? Senão, oferece refazer
function avisoCicloProvas() {
  const pl = DADOS && DADOS.periodizacao;
  if (!pl || !pl.semanas || !pl.semanas.length) return "";
  const ini = pl.semanas[0].inicio;
  const fimPl = new Date(pl.semanas[pl.semanas.length - 1].inicio + "T12:00"); fimPl.setDate(fimPl.getDate() + 6);
  const fimIso = fimPl.toISOString().slice(0, 10);
  const faltam = provasParaCiclo().filter((p) => {
    if (p.date < ini || p.date > fimIso) return false;
    const seg = segundaDe(new Date(p.date + "T12:00")).toISOString().slice(0, 10);
    const w = pl.semanas.find((s) => s.inicio === seg);
    return w && !(w.obs || "").includes(`prova ${p.prio}: `);
  });
  if (!faltam.length) return "";
  return `<p class="dica pv-aviso">O ciclo do Lab foi montado sem ${faltam.length > 1 ? "as provas" : "a prova"} ` +
    `${faltam.map((p) => `${p.prio} de ${fmtBR(p.date).slice(0, 5)}`).join(", ")}. ` +
    `<button type="button" class="secundario" id="pv-encaixar" title="Refaz as semanas do ciclo com a progressão guardada e com as provas: a semana da B ganha o mini-polimento. O que foi mudado à mão na tabela do ciclo volta ao cálculo">Encaixar no ciclo</button></p>`;
}
let _salvarProvasT = null;
function salvarProvasDepois() {
  clearTimeout(_salvarProvasT);
  _salvarProvasT = setTimeout(salvarProvas, 500);
}
async function salvarProvas() {
  if (!DADOS || !DADOS.athlete_id) return;
  const a = $("#prova-data").value;
  // do TP só vai o que o treinador escolheu; as digitadas vão sempre
  const provas = (DADOS.provas || []).filter((p) => p.origem === "manual" || p.date === a
      || PROVAS_PRIO[p.date] || PROVAS_KM[p.date] != null || p.escolha || p.km_salvo != null)
    .map((p) => ({ date: p.date, name: p.name, km: kmDaProva(p) || null, prio: prioDe(p),
                   origem: p.origem === "manual" ? "manual" : "tp" }));
  try {
    const r = await api("/api/provas/salvar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: DADOS.athlete_id, provas }),
    });
    if (r.periodizacao) { DADOS.periodizacao = r.periodizacao; pintarProvasBloco(); }
  } catch (e) { console.warn("provas não salvas:", e.message); }
}
function mudouProvas() {
  pintarProvasCal();
  pintarProvasBloco();
  salvarProvasDepois();
  document.dispatchEvent(new CustomEvent("fases-mudou"));
}
// vira a prova A do bloco: Dia, Nome e Objetivo vêm dela
function tornarA(p) {
  $("#prova-data").value = p.date; $("#prova-nome").value = p.name;
  definirObjetivo(kmDaProva(p));
  delete PROVAS_PRIO[p.date];
  $("#btn-ciclo-prova").disabled = false;
  provaDoDiaMudou();
  setAuto("#semana-max", ""); sugerirBloco();
}
$("#provas-bloco") && $("#provas-bloco").addEventListener("change", (e) => {
  const ik = e.target.closest(".km-prova");
  if (ik) {                                        // km digitado: fica como o treinador pôs
    const v = parseFloat(ik.value);
    if (v > 0) PROVAS_KM[ik.dataset.date] = v; else delete PROVAS_KM[ik.dataset.date];
    if (ik.dataset.date === $("#prova-data").value && v > 0) definirObjetivo(v);
    mudouProvas();
    return;
  }
  const sel = e.target.closest(".prio-sel"); if (!sel) return;
  const p = (DADOS.provas || []).find((x) => x.date === sel.dataset.date);
  if (!p) return;
  if (sel.value === "A") { tornarA(p); return; }
  PROVAS_PRIO[p.date] = sel.value;
  if (p.date === $("#prova-data").value) {          // a A deixou de ser A: o bloco fica sem prova A
    $("#prova-data").value = ""; $("#prova-nome").value = "";
    $("#btn-ciclo-prova").disabled = true;
    DIA_ANTERIOR = "";
  }
  mudouProvas();
});
$("#provas-bloco") && $("#provas-bloco").addEventListener("click", async (e) => {
  const del = e.target.closest(".pv-del");
  if (del) {
    DADOS.provas = (DADOS.provas || []).filter((x) => x.date !== del.dataset.date);
    delete PROVAS_PRIO[del.dataset.date]; delete PROVAS_KM[del.dataset.date];
    mudouProvas();
    return;
  }
  if (e.target.closest("#pv-n-add")) {
    const data = $("#pv-n-data").value, nome = $("#pv-n-nome").value.trim();
    const km = parseFloat($("#pv-n-km").value) || null, prio = $("#pv-n-prio").value;
    if (!data) { alert("Coloque o dia da prova."); return; }
    DADOS.provas = DADOS.provas || [];
    let p = DADOS.provas.find((x) => x.date === data);
    if (p) { alert(`Já tem prova em ${fmtBR(data)} na lista (${p.name}).`); return; }
    p = { date: data, name: nome || "Prova", km, prio: "", origem: "manual", escolha: prio === "A" ? null : prio };
    DADOS.provas.push(p);
    DADOS.provas.sort((x, y) => x.date.localeCompare(y.date));
    if (prio === "A") { tornarA(p); return; }
    PROVAS_PRIO[data] = prio;
    mudouProvas();
    return;
  }
  if (e.target.closest("#pv-encaixar")) {
    const pl = DADOS.periodizacao;
    carregando("encaixando as provas no ciclo...");
    try {
      const r = await api("/api/periodizacao/refazer", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: DADOS.athlete_id, plano_id: pl.id,
          objetivo: objetivoMotor() || null, prova_km: kmObjetivo(), provas: provasParaCiclo(),
          ...progressaoPedido(), min_km: parseFloat($("#min-km").value) || null,
          max_km: parseFloat($("#max-km").value) || null }),
      });
      DADOS.periodizacao = r.periodizacao;
      pintarPlano();
      pintarProvasBloco();
      sugerirBloco();
      statusProgressao("Provas encaixadas no ciclo: a semana de cada prova B ganhou o mini-polimento." + (r.aviso ? " " + r.aviso : ""));
    } catch (err) { alert("Não deu para encaixar as provas: " + err.message); } finally { pronto(); }
  }
});
["#inicio", "#fim"].forEach((k) => $(k).addEventListener("change", pintarProvasBloco));
$("#prova-data").addEventListener("change", provaDoDiaMudou);
$("#prova-nome").addEventListener("change", () => { garantirProvaDoDia(); pintarProvasBloco(); salvarProvasDepois(); });
$("#prova-km").addEventListener("input", () => {
  mostrarKmObjetivo();
  const a = (DADOS && DADOS.provas || []).find((x) => x.date === $("#prova-data").value);
  if (a && parseFloat($("#prova-km").value) > 0) { PROVAS_KM[a.date] = parseFloat($("#prova-km").value); }
});
$("#prova-km").addEventListener("change", () => {
  if (!DADOS) return;
  garantirProvaDoDia(); mudouProvas();
  setAuto("#semana-max", ""); sugerirBloco();
});

$("#prova-cal").onchange = () => {
  const p = (DADOS && DADOS.provas || [])[+$("#prova-cal").value];
  if (!p) return;
  tornarA(p);
};
// restaura a prova A salva para o atleta (a que estava no Dia da última vez)
function restaurarProvaA() {
  if (!DADOS || $("#prova-data").value) return;
  const hoje = new Date().toISOString().slice(0, 10);
  const a = (DADOS.provas || []).find((p) => p.escolha === "A" && p.date >= hoje);
  if (!a) return;
  $("#prova-data").value = a.date; $("#prova-nome").value = a.name;
  definirObjetivo(kmDaProva(a));
  $("#btn-ciclo-prova").disabled = false;
  DIA_ANTERIOR = a.date;
}

// ---- orientações do treinador em texto livre: o servidor lê com o Claude e devolve regras ----
let ORIENT = null;             // {texto, regras, nao_entendi, hash} da última leitura
const ORIENT_LIDO = () => ORIENT && (ORIENT.texto || "").trim() === $("#orientacoes").value.trim();
function pintarOrientacoes() {
  const box = $("#orientacoes-lidas"), st = $("#orientacoes-status");
  const texto = $("#orientacoes").value.trim();
  if (!texto) { box.classList.add("oculto"); box.innerHTML = ""; st.textContent = ""; return; }
  if (!ORIENT_LIDO()) {
    st.textContent = "Texto ainda não lido. Clique em Ler orientações ou gere a prévia, que lê sozinha.";
    box.classList.add("oculto");
    return;
  }
  const regras = ORIENT.regras || [], nao = ORIENT.nao_entendi || [];
  st.textContent = regras.length ? `${regras.length} regra${regras.length > 1 ? "s" : ""} para a prévia.` : "Nenhuma regra que o gerador consiga aplicar.";
  const esc = (t) => String(t || "").replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" })[c]);
  box.innerHTML = (regras.length ? `<span class="rotulo">O gerador entendeu</span><ul>${regras.map((r) =>
      `<li>${esc(r.explicacao || r.acao)}${r.periodo ? ` <small>(${fmtBR(r.periodo.ini).slice(0, 5)} a ${fmtBR(r.periodo.fim).slice(0, 5)})</small>` : ""}</li>`).join("")}</ul>` : "") +
    (nao.length ? `<span class="rotulo">Não dá para aplicar</span><ul class="nao">${nao.map((x) =>
      `<li>${x.trecho ? `"${esc(x.trecho)}": ` : ""}${esc(x.motivo)}</li>`).join("")}</ul>` : "");
  box.classList.toggle("oculto", !(regras.length || nao.length));
}
function gradeSemana1() {
  const g = {};
  document.querySelectorAll('#dias select[data-dia][data-semana="1"]').forEach((s) => { if (s.value) g[s.dataset.dia] = s.value; });
  return { 1: g };
}
function orientacoesPedido() {
  const texto = $("#orientacoes").value.trim();
  if (!texto) return null;
  return ORIENT_LIDO() ? { texto, regras: ORIENT.regras || [], hash: ORIENT.hash } : { texto };
}
$("#btn-orientacoes").onclick = async () => {
  if (!DADOS) return;
  const texto = $("#orientacoes").value.trim();
  carregando(texto ? "lendo as orientações (leva uns 30 segundos)..." : "limpando as orientações...");
  try {
    ORIENT = await api("/api/orientacoes/interpretar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: DADOS.athlete_id, texto, inicio: $("#inicio").value, fim: $("#fim").value,
        modalidade: modalidade(), prova: objetivoMotor() || null, prova_data: $("#prova-data").value || null,
        semanas_tipos: gradeSemana1() }),
    });
    pintarOrientacoes();
  } catch (e) { alert("Não deu para ler as orientações: " + e.message); } finally { pronto(); }
};
$("#orientacoes").addEventListener("input", pintarOrientacoes);
function restaurarOrientacoes() {
  ORIENT = (DADOS && DADOS.orientacoes) || null;
  $("#orientacoes").value = ORIENT ? ORIENT.texto || "" : "";
  pintarOrientacoes();
}

async function anexarForcaBib(ed) {
  const sel = ed.querySelector('#ed-campos [data-k="template"]');
  if (!sel || sel.dataset.bibOk) return;
  sel.dataset.bibOk = "1";
  try {
    if (!FORCA_BIB) FORCA_BIB = (await api("/api/forca/biblioteca")).itens;
  } catch (e) { return; }   // sem rede: ficam só os templates embutidos
  const grupos = {};
  FORCA_BIB.forEach((it) => (grupos[it.biblioteca] ??= []).push(it));
  for (const [lib, itens] of Object.entries(grupos)) {
    const og = document.createElement("optgroup");
    og.label = `Biblioteca ${lib}`;
    itens.forEach((it) => {
      const o = document.createElement("option");
      o.value = it.chave; o.textContent = it.titulo;
      og.appendChild(o);
    });
    sel.appendChild(og);
  }
}
let NOTAS = {};   // {semana: {dia: texto}} - comentario do treinador por sessao
let FIXOS = {};   // {semana: {dia: {params}}} - estrutura definida na grade

// -- tema ------------------------------------------------------------------
if (localStorage.tema === "claro") document.body.classList.add("claro");
$("#tema").onclick = () => {
  document.body.classList.toggle("claro");
  localStorage.tema = document.body.classList.contains("claro") ? "claro" : "escuro";
};

// -- util ------------------------------------------------------------------
function carregando(txt) {
  $("#carregando-txt").textContent = txt || "carregando...";
  $("#carregando").classList.remove("oculto");
}
function pronto() { $("#carregando").classList.add("oculto"); }

async function api(url, opts) {
  const r = await fetch(url, opts);
  const j = await r.json();
  if (!r.ok || j.erro) throw new Error(j.erro || "erro na requisicao");
  return j;
}
function aviso(el, texto, classe) {
  el.className = "aviso " + (classe || "");
  el.textContent = texto;
  el.classList.remove("oculto");
}

// -- 1. atletas ------------------------------------------------------------
// lista = atletas dos grupos do TP (Corrida, Corrida e Força, Força, Millenium, BV TechSport,
// Manakai Run, Compartilhado, My Athletes); "fora dos grupos" traz o resto da conta
async function carregarAtletas(todos) {
  const j = await api("/api/atletas" + (todos ? "?todos=1" : ""));
  ATLETAS = j.atletas;
  filtrarAtletas();
}
(async () => {
  try {
    await carregarAtletas(false);
    // link direto (do painel ou de um favorito): abre já com o atleta carregado
    const qs = new URLSearchParams(location.search);
    const alvo = qs.get("atleta");
    if (alvo && !ATLETAS.some((a) => a.id === alvo)) {
      $("#fora-grupos").checked = true;
      await carregarAtletas(true);
    }
    if (alvo && [...$("#atleta").options].some((o) => o.value === alvo)) {
      $("#atleta").value = alvo;
      $("#carregar").click();
    }
  } catch (e) {
    $("#atleta").innerHTML = `<option>erro: ${e.message}</option>`;
  }
})();

function pintarAtletas(lista) {
  const grupos = [];
  for (const a of lista) {
    const g = a.grupo || "";
    if (!grupos.length || grupos[grupos.length - 1].nome !== g) grupos.push({ nome: g, itens: [] });
    grupos[grupos.length - 1].itens.push(a);
  }
  const op = (a) => `<option value="${a.id}">${a.nome}</option>`;
  $("#atleta").innerHTML = grupos
    .map((g) => g.nome ? `<optgroup label="${g.nome} (${g.itens.length})">${g.itens.map(op).join("")}</optgroup>`
                       : g.itens.map(op).join(""))
    .join("");
}
function filtrarAtletas() {
  const q = $("#busca").value.toLowerCase();
  pintarAtletas(ATLETAS.filter((a) => a.nome.toLowerCase().includes(q)));
}
$("#busca").oninput = filtrarAtletas;
$("#fora-grupos").onchange = async (e) => {
  const atual = $("#atleta").value;
  try { await carregarAtletas(e.target.checked); }
  catch (err) { $("#atleta").innerHTML = `<option>erro: ${err.message}</option>`; return; }
  if ([...$("#atleta").options].some((o) => o.value === atual)) $("#atleta").value = atual;
};

// valores iniciais do bloco (os da página), para zerar quando trocar de atleta
const PADRAO_BLOCO = {
  inicio: $("#inicio").value, fim: $("#fim").value,
  progressao: $("#progressao").value, recupCada: $("#recup-cada").value, recupCorte: $("#recup-corte").value,
};

// tudo que era do atleta anterior sai da tela: prévia, resultado da publicação,
// grade, fases, notas, estruturas fixadas, prova, pisos e datas
function limparEstadoAtleta() {
  PREVIA = null; NOTAS = {}; FIXOS = {}; FASES = {}; PROVAS_PRIO = {}; PROVAS_KM = {}; MANUAIS = {}; DIA_ANTERIOR = "";
  CIC_MANUAL = {}; CIC_PLANO = null;
  CAMPOS_MANUAIS.clear();
  $("#lista-treinos").innerHTML = "";
  $("#conflitos").classList.add("oculto"); $("#conflitos").innerHTML = "";
  $("#resumo-semanas").classList.add("oculto"); $("#resumo-semanas").innerHTML = "";
  $("#resultado").classList.add("oculto"); $("#resultado").innerHTML = "";
  $("#sec-previa").classList.add("oculto");
  $("#publicar").disabled = true;
  $("#substituir").checked = true;
  ["#prova-data", "#prova-nome", "#prova-km", "#min-km", "#max-km", "#semana-max", "#semana-min", "#longo-min"].forEach((k) => { $(k).value = ""; });
  $("#prova").value = "";
  mostrarKmObjetivo();
  $("#btn-ciclo-prova").disabled = true;
  $("#inicio").value = PADRAO_BLOCO.inicio; $("#fim").value = PADRAO_BLOCO.fim;
  $("#progressao").value = PADRAO_BLOCO.progressao;
  $("#recup-cada").value = PADRAO_BLOCO.recupCada;
  $("#recup-corte").value = PADRAO_BLOCO.recupCorte;
  $("#sem-recup").checked = false; $("#recup-cada").disabled = false; $("#recup-corte").disabled = false;
  document.querySelectorAll(".editor").forEach((el) => el.remove());
}

$("#carregar").onclick = async () => {
  const id = $("#atleta").value;
  if (!id) return;
  carregando("lendo o historico do atleta no TrainingPeaks...");
  try {
    const trocou = !DADOS || String(DADOS.athlete_id) !== String(id);
    DADOS = await api(`/api/atleta/${id}`);
    if (trocou) limparEstadoAtleta();
    DADOS.athlete_id = id;
    restaurarProvaA();
    restaurarOrientacoes();
    pintarProvasCal();
    NOTAS = {};
    FIXOS = {};
    pintarPerfil();
    pintarProvasBloco();
    $("#perfil").classList.remove("oculto");
    $("#sec-bloco").classList.remove("oculto");
    montarDias();
    if (trocou) document.dispatchEvent(new CustomEvent("atleta-trocado"));
  } catch (e) {
    alert("Erro: " + e.message);
  } finally { pronto(); }
};

function pintarPerfil() {
  const h = DADOS.historico;
  $("#i-volume").textContent = h.km_semana != null ? `${h.km_semana} km` : "—";
  $("#i-longo").textContent = h.maior_longo ? `${h.maior_longo} km` : "—";
  $("#i-facil").textContent = h.pace_facil ? `${h.pace_facil}/km` : "—";
  $("#i-corridas").textContent = h.corridas;
  const dt = h.dias_treino || [];
  $("#i-dias").textContent = dt.length ? dt.map((d) => d.nome).join(" · ") : "—";
  $("#i-dias-n").textContent = dt.length
    ? `${dt.length} dia${dt.length > 1 ? "s" : ""}/semana pela rotina recente`
    : "sem corridas no periodo";
  pintarChipsDias(dt.map((d) => d.dia));

  // forma vinda do banco do AS Endurance Lab (quando o atleta esta na coleta)
  const fit = DADOS.lab && DADOS.lab.fitness;
  $("#c-ctl").classList.toggle("oculto", !fit);
  $("#c-tsb").classList.toggle("oculto", !fit);
  if (fit) {
    $("#i-ctl").textContent = fit.ctl;
    $("#i-ctl-data").textContent = `Lab · ${fit.date.split("-").reverse().slice(0, 2).join("/")}`;
    $("#i-tsb").textContent = (fit.tsb > 0 ? "+" : "") + fit.tsb;
    $("#i-tsb").style.color = fit.tsb >= 5 ? "var(--verde)" :
      fit.tsb <= -15 ? "var(--vermelho)" : "";
  }

  // periodizacao do atleta (ATP do Lab) - quadro editavel; a caixa Progressão
  // mostra com que progressão o plano foi montado
  progressaoDoPlano(DADOS.periodizacao);
  pintarPlano();

  // bloco do gerador que cobre a data de hoje
  const ba = DADOS.bloco_ativo;
  const boxBa = $("#bloco-ativo");
  if (ba) {
    const f = (iso) => iso.split("-").reverse().slice(0, 2).join("/");
    const semAtual = Math.min(
      Math.floor((Date.now() - new Date(ba.inicio + "T12:00")) / 6048e5) + 1,
      ba.semanas || 1);
    aviso(boxBa, `Este atleta já tem um bloco do gerador em andamento: ` +
      `${f(ba.inicio)} → ${f(ba.fim)} · semana ${semAtual} de ${ba.semanas} · ` +
      `${ba.sessoes} treinos, ${ba.km_total} km. Gerar outro por cima vai duplicar.`);
  } else boxBa.classList.add("oculto");

  const est = DADOS.threshold_estimado, cad = DADOS.threshold_cadastrado;
  const boxLimiar = document.querySelector(".limiar-box");
  if (DADOS.zonas_tp) {
    // zonas reais do TP mandam: esconde a escolha de limiar
    boxLimiar.querySelector("h2").textContent =
      `Zonas do TrainingPeaks (10 zonas · ancora ${DADOS.ancora_pace}/km)`;
    boxLimiar.querySelector(".opcoes-limiar").classList.add("oculto");
    $("#aviso-limiar").classList.add("oculto");
  } else {
    boxLimiar.querySelector("h2").textContent =
      "Pace de limiar — sem zonas no TP, base de todas as zonas";
    boxLimiar.querySelector(".opcoes-limiar").classList.remove("oculto");
    $("#l-est").textContent = est.pace ? `${est.pace}/km` : "sem dados";
    $("#l-est-fonte").textContent = est.fonte || "sem base para estimar";
    $("#l-cad").textContent = cad.pace ? `${cad.pace}/km` : "nao cadastrado";
    if (!est.ms) document.querySelector('input[value="cadastrado"]').checked = true;

    // alerta quando os dois discordam muito
    const box = $("#aviso-limiar");
    if (est.ms && cad.ms) {
      const dif = Math.abs(1000 / est.ms - 1000 / cad.ms);
      if (dif > 25) {
        aviso(box, `O limiar cadastrado (${cad.pace}/km) e o estimado pelo historico ` +
          `(${est.pace}/km) diferem em ${Math.round(dif)} seg/km. O cadastrado costuma vir ` +
          `de calculo automatico antigo — confira antes de gerar o bloco.`);
      } else box.classList.add("oculto");
    } else box.classList.add("oculto");
  }

  const b = DADOS.base_sugerida;
  $("#b-longo").value = b.longo_km;
  $("#b-limiar").value = b.limiar_min;
  $("#b-vo2").value = b.vo2_seg;
  $("#b-rodagem").value = b.rodagem_min;
  // sugestao para o maior longo do periodo, editavel
  setAuto("#longo-max", Math.max(Math.round((b.longo_km * 1.35) * 2) / 2, b.longo_km + 1.5));
  sugerirBloco();
  cicPadroes();
  if (modalidade() === "ciclismo") agendarPlanoCiclismo();

  pintarZonas();
}

document.addEventListener("change", (e) => {
  if (e.target.name === "limiar" || e.target.id === "l-manual") pintarZonas();
});

function thresholdEscolhido() {
  // com zonas do TP, a ancora e o threshold cadastrado - os alvos vem das zonas
  if (DADOS.zonas_tp) return DADOS.threshold_cadastrado.ms;
  const op = document.querySelector('input[name="limiar"]:checked').value;
  if (op === "cadastrado") return DADOS.threshold_cadastrado.ms;
  if (op === "manual") {
    const v = $("#l-manual").value.trim();
    const m = v.match(/^(\d+)[:.](\d{1,2})$/);
    if (!m) return null;
    return 1000 / (parseInt(m[1]) * 60 + parseInt(m[2]));
  }
  return DADOS.threshold_estimado.ms;
}

function pintarZonas() {
  const t = $("#tabela-zonas");
  if (DADOS.zonas_tp) {
    // as 10 zonas reais do atleta, com as usadas nos treinos destacadas
    const usadas = {};
    (DADOS.zonas_intents || []).forEach((z) => {
      const n = parseInt(z.zona.slice(1));
      (usadas[n] = usadas[n] || []).push(z.nome);
    });
    t.innerHTML = DADOS.zonas_tp.map((z) => {
      const uso = usadas[z.num];
      return `<tr class="${uso ? "" : "gray"}"><td>${z.label}</td>` +
        `<td>${z.pace}</td><td>${uso ? "→ " + [...new Set(uso)].join(", ") : ""}</td></tr>`;
    }).join("");
    return;
  }
  const th = thresholdEscolhido();
  if (!th) { t.innerHTML = "<tr><td>defina um pace de limiar valido</td></tr>"; return; }
  const op = document.querySelector('input[name="limiar"]:checked').value;
  const tabela = op === "cadastrado" ? DADOS.zonas_cadastrado
    : op === "estimado" ? DADOS.zonas_estimado : null;
  if (tabela) {
    t.innerHTML = tabela.map((z) =>
      `<tr><td>${z.nome}</td><td>${z.pct}</td><td>${z.pace}</td></tr>`).join("");
  } else {
    // manual: calcula no proprio navegador
    const Z = [["rodagem",65,72],["aquecimento",72,78],["aerobico leve",80,86],
               ["aerobico forte",88,92],["limiar",95,100],["VO2max",105,110]];
    const p = (pct) => { const s = 1000 / (th * pct / 100);
      return `${Math.floor(s/60)}:${String(Math.round(s%60)).padStart(2,"0")}`; };
    t.innerHTML = Z.map(([n,lo,hi]) =>
      `<tr><td>${n}</td><td>${lo}-${hi}%</td><td>${p(hi)}-${p(lo)}/km</td></tr>`).join("");
  }
}

// ---- periodizacao: quadro editavel + criacao -------------------------------
const FASES_PLANO = ["Base", "Específico", "Polimento", "Prova"];
const FASES_FORCA = ["Adaptação", "Base", "Força máxima", "Acumulação", "Pré-competitivo", "Competitivo", "Descarga",
  "Hipertrofia", "Potência", "Resistência"];
// o objetivo é o padrão das semanas em automática (espelho de forca.FASE_DO_OBJETIVO)
const FASE_DO_OBJETIVO = { hipertrofia: "Hipertrofia", forca_maxima: "Força máxima", potencia: "Potência", resistencia: "Resistência" };
// fase escolhida à mão por semana: { [semana]: { corrida: "Base"|..., forca: "Adaptação"|... } }
// (vazio = automático, pela periodização/posição no bloco)
let FASES = {};
// dias da grade que o treinador mexeu à mão: { [semana]: { [dia]: true } }. Nenhuma
// sugestão nem regra muda esses dias (a tela pula, e o motor recebe a lista)
let MANUAIS = {};
const eManual = (w, d) => !!(MANUAIS[w] && MANUAIS[w][d]);
function marcarManual(w, d, sim = true) {
  if (sim) (MANUAIS[w] ??= {})[d] = true;
  else if (MANUAIS[w]) { delete MANUAIS[w][d]; if (!Object.keys(MANUAIS[w]).length) delete MANUAIS[w]; }
  const el = document.querySelector(`#dias select[data-semana="${w}"][data-dia="${d}"]`);
  if (el) { el.classList.toggle("manual", sim); el.title = sim ? "Marcado à mão: o gerador não muda" : ""; }
}
function manuaisPayload() {
  const out = {};
  for (const [w, ds] of Object.entries(MANUAIS)) out[w] = Object.keys(ds).map(Number);
  return out;
}
// campos do período que o treinador digitou: o gerador não sobrescreve
const CAMPOS_MANUAIS = new Set();
function setAuto(sel, v) {
  if (CAMPOS_MANUAIS.has(sel)) return;
  // o maior longo automático nunca fica abaixo do menor longo digitado
  const mn = +$("#longo-min").value;
  if (sel === "#longo-max" && v !== "" && mn > +v) v = mn;
  $(sel).value = v;
}
document.addEventListener("input", (e) => {
  if (["semana-max", "semana-min", "longo-max", "longo-min", "min-km"].includes(e.target.id)
      || e.target.classList.contains("cic-campo"))
    CAMPOS_MANUAIS.add("#" + e.target.id);
});
// menor longo acima do maior longo: o automático sobe junto; os dois digitados, vale o maior
document.addEventListener("change", (e) => {
  if (e.target.id !== "longo-min") return;
  const mn = +e.target.value, mx = +$("#longo-max").value;
  if (!mn || !mx || mn <= mx) return;
  if (CAMPOS_MANUAIS.has("#longo-max")) {
    statusProgressao(`Menor longo (${mn} km) acima do maior longo (${mx} km): vale o maior longo.`, true);
    return;
  }
  setAuto("#longo-max", mn);
  _longoEditado = true;                // a periodização refeita leva o novo maior longo
}, true);

function pintarPlano() {
  const box = $("#plano-box");
  if (!DADOS) { box.classList.add("oculto"); return; }
  box.classList.remove("oculto");
  const p = DADOS.periodizacao;
  box.innerHTML = p ? htmlPlanoEditor(p) : htmlPlanoCriar();
  if (p) renumeraPlano();
}

function htmlPlanoEditor(p) {
  const fmt = (iso) => iso.split("-").reverse().slice(0, 2).join("/");
  const linhas = p.semanas.map((s) => `
    <tr data-horas="${s.horas ?? ""}">
      <td class="p-idx">—</td><td class="p-data">—</td>
      <td><select class="p-fase">${FASES_PLANO.map((f) =>
        `<option ${f === s.fase ? "selected" : ""}>${f}</option>`).join("")}</select></td>
      <td><input class="p-km" type="number" step="1" min="0" value="${s.km ?? ""}"> km</td>
      <td><input class="p-obs" value="${(s.obs || "").replace(/"/g, "&quot;")}" placeholder="obs"></td>
      <td><button class="ghost mini plano-del">×</button></td>
    </tr>`).join("");
  return `
    <h2>Periodização do atleta (ATP do Lab)</h2>
    <div class="linha" style="margin-bottom:10px">
      <label>Ciclo <input id="plano-nome" value="${p.nome.replace(/"/g, "&quot;")}"></label>
      <label>${p.sem_prova ? "Fim do ciclo (sem prova)" : "Prova"} <input id="plano-prova" type="date" value="${p.prova_data}"></label>
      <span class="dica" style="margin:0">início ${fmt(p.inicio)} · edite e salve — vale aqui e no painel</span>
    </div>
    <table class="zonas plano-edit" data-inicio="${p.inicio}" data-id="${p.id}">
      <tr><td>sem</td><td>início</td><td>fase</td><td>km na semana</td><td></td><td></td></tr>
      ${linhas}
    </table>
    <div class="linha" style="margin-top:10px">
      <button class="ghost mini" id="plano-add">+ semana</button>
      <button class="primario" id="plano-salvar">Salvar periodização</button>
      <span id="plano-status" class="dica" style="margin:0"></span>
    </div>
    <div class="linha" style="margin-top:12px">
      <label class="check"><input type="checkbox" id="seguir-plano" checked>
        Seguir a periodização — o volume de cada semana segue o plano</label>
      <button class="ghost" id="usar-datas">Usar as datas do plano</button>
    </div>`;
}

function htmlPlanoCriar() {
  const hoje = new Date();
  const seg = new Date(hoje); seg.setDate(seg.getDate() + ((8 - seg.getDay()) % 7 || 7));
  const prova = new Date(hoje); prova.setDate(prova.getDate() + 84);
  const d = (x) => x.toISOString().slice(0, 10);
  // próxima prova real do calendário (a mais distante ≥ 6 semanas, senão a próxima)
  const cal = (DADOS && DADOS.provas) || [];
  const alvo = cal.find((p) => (new Date(p.date) - hoje) / 864e5 >= 42) || cal[0];
  const provaIso = alvo ? alvo.date : d(prova);
  const nomeCiclo = alvo ? alvo.name : "Ciclo de prova";
  const obj = objetivoMotor() || objetivoPorKm(alvo && kmDaProva(alvo)) || "10k";
  setTimeout(sugerirCiclo, 0);        // preenche km inicial/pico pelo histórico
  return `
    <h2>Periodização do atleta (ATP do Lab)</h2>
    <div class="dica">Este atleta ainda não tem ciclo. Crie aqui — aparece igual na página Periodização do painel.</div>
    <div class="linha">
      <label>Ciclo <input id="cr-nome" value="${nomeCiclo.replace(/"/g, "&quot;")}"></label>
      <label>Objetivo <select id="cr-obj">${["5k","10k","21k","42k"].map((o) =>
        `<option value="${o}" ${o === obj ? "selected" : ""}>${o.replace("k", " km")}</option>`).join("")}</select></label>
      <label>Prova <input id="cr-prova" type="date" value="${provaIso}"></label>
      <label>Início <input id="cr-inicio" type="date" value="${d(seg)}"></label>
      <label>Km/sem inicial <input id="cr-km-ini" type="number" value="20" step="1" min="5"></label>
      <label>Km/sem no pico <input id="cr-km-pico" type="number" value="40" step="1" min="10"></label>
      <button class="primario" id="plano-criar">Criar ciclo</button>
    </div>
    <p class="dica" id="cr-dica" style="margin:8px 0 0">calculando o ponto de partida pelo histórico…</p>`;
}

// Bloco: maior semana / maior longo pelo histórico e pelo objetivo (com travas)
// semanas do plano do Lab que caem dentro do bloco (datas da tela)
function planoNoBloco() {
  const p = DADOS && DADOS.periodizacao;
  if (!p || !p.semanas || !($("#seguir-plano") && $("#seguir-plano").checked)) return [];
  const ini = $("#inicio").value, fim = $("#fim").value;
  if (!ini || !fim) return [];
  const seg0 = segundaDe(new Date(ini + "T12:00")).toISOString().slice(0, 10);
  return p.semanas.filter((s) => s.inicio >= seg0 && s.inicio <= fim && (s.km || s.horas));
}

function picosDoCiclo() {
  const p = DADOS && DADOS.periodizacao;
  if (!p) return { km: 0, longo: 0 };
  const carga = p.semanas.filter((s) => s.km && ["Base", "Específico"].includes(s.fase));
  const base = carga.length ? carga : p.semanas.filter((s) => s.km);
  return { km: Math.max(...base.map((s) => +s.km), 0),
           longo: Math.max(...p.semanas.map((s) => +s.longo || 0), 0) };
}

async function sugerirBloco() {
  if (!DADOS) return;
  // seguindo o plano do Lab: a maior semana e o teto do longo saem do PLANO, não do histórico
  const doPlano = planoNoBloco().filter((s) => s.km);
  if (doPlano.length) {
    // os dois campos são o pico do CICLO inteiro (o que o treinador pede para a
    // periodização); o bloco na tela segue o km e o longo de cada semana do plano
    const ciclo = picosDoCiclo();
    const tetoObj = { "5k": 14, "10k": 18, "21k": 20, "42k": 34 }[objetivoMotor()] || 20;
    setAuto("#semana-max", ciclo.km);
    setAuto("#longo-max", ciclo.longo > 0 ? ciclo.longo
      : Math.min(tetoObj, Math.round(ciclo.km * 0.35 * 2) / 2));
    const kmsB = doPlano.map((s) => +s.km);
    const longoB = Math.max(...doPlano.map((s) => +s.longo || 0));
    const el = $("#dica-partida");
    if (el) el.textContent = `Seguindo a periodização do Lab. Pico do ciclo: ${ciclo.km} km na semana e ` +
      `longo de ${$("#longo-max").value} km (mude aqui e o plano inteiro é refeito). Neste bloco: ` +
      `${Math.min(...kmsB)} a ${Math.max(...kmsB)} km${longoB ? `, longo até ${longoB} km` : ""}.`;
    document.dispatchEvent(new CustomEvent("fases-mudou"));
    return;
  }
  try {
    const r = await api("/api/periodizacao/sugestao", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objetivo: objetivoMotor() || null, inicio: $("#inicio").value,
        prova_data: $("#prova-data").value || null, historico: historicoCompacto(),
        prova_km: kmObjetivo(), provas: provasParaCiclo() }),
    });
    if (!$("#semana-max").value) setAuto("#semana-max", r.km_pico);
    const longoTeto = Math.min(r.longo_max, Math.round(r.km_pico * 0.3 * 2) / 2);
    setAuto("#longo-max", Math.min(+$("#longo-max").value || longoTeto, longoTeto));
    const el = $("#dica-partida");
    if (el) el.textContent = `Ponto de partida pelo histórico: ${r.motivo}. Semana inicial ${r.km_ini} km, ` +
      `maior semana sugerida ${r.km_pico} km, longo até ${longoTeto} km (${r.objetivo}).`;
  } catch (e) { /* silencioso */ }
}
$("#prova").addEventListener("change", () => {
  mostrarKmObjetivo();
  if ($("#prova").value === "outra" && !$("#prova-km").value) $("#prova-km").focus();
  if (DADOS) { garantirProvaDoDia(); mudouProvas(); setAuto("#semana-max", ""); sugerirBloco(); }
});
document.addEventListener("change", (e) => {
  if (!DADOS) return;
  if (e.target.id === "seguir-plano" || ((e.target.id === "inicio" || e.target.id === "fim") && planoNoBloco().length)) {
    if (e.target.id === "seguir-plano" && !e.target.checked) setAuto("#semana-max", "");
    sugerirBloco();
  }
});

// histórico compacto que vai para o motor decidir o ponto de partida
function historicoCompacto() {
  const h = (DADOS && DADOS.historico) || {};
  return { km_semana: h.km_semana, km_2sem: h.km_2sem, km_8sem: h.km_8sem, maior_longo: h.maior_longo };
}

// sugestão de km inicial / pico / longo para o formulário de criar ciclo
async function sugerirCiclo() {
  if (!DADOS || !$("#cr-obj")) return;
  try {
    const r = await api("/api/periodizacao/sugestao", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objetivo: $("#cr-obj").value, inicio: $("#cr-inicio").value,
        prova_data: $("#cr-prova").value, historico: historicoCompacto() }),
    });
    if (!$("#cr-km-ini")) return;
    $("#cr-km-ini").value = r.km_ini; $("#cr-km-pico").value = r.km_pico;
    const n = r.semanas.length;
    const ideal = r.semanas_ideal;
    const aviso = n && n < ideal - 2 ? ` Ciclo curto para ${$("#cr-obj").value}: o ideal seria ${ideal} semanas.` : "";
    $("#cr-dica").textContent = `Ponto de partida: ${r.motivo}. Início ${r.km_ini} km, pico ${r.km_pico} km, ` +
      `longo de ${r.longo_ini} até ${Math.min(r.longo_max, Math.round(r.km_pico * 0.3))} km · ${n} semanas.${aviso}`;
  } catch (e) { if ($("#cr-dica")) $("#cr-dica").textContent = "não consegui calcular a sugestão: " + e.message; }
}

function renumeraPlano() {
  const tab = document.querySelector(".plano-edit");
  if (!tab) return;
  const anc = new Date(tab.dataset.inicio + "T12:00");
  anc.setDate(anc.getDate() - ((anc.getDay() + 6) % 7));      // segunda-feira
  [...tab.querySelectorAll("tr")].slice(1).forEach((tr, i) => {
    const d = new Date(anc); d.setDate(d.getDate() + 7 * i);
    tr.querySelector(".p-idx").textContent = i + 1;
    tr.querySelector(".p-data").textContent =
      `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
  });
}

function usarDatasDoPlano() {
  const plano = DADOS && DADOS.periodizacao;
  if (!plano) return;
  const hoje = new Date().toISOString().slice(0, 10);
  const futuras = plano.semanas.filter((s) => {
    const fim = new Date(s.inicio + "T12:00");
    fim.setDate(fim.getDate() + 6);
    return fim.toISOString().slice(0, 10) >= hoje;
  });
  if (!futuras.length) { alert("O plano já terminou — todas as semanas ficaram para trás."); return; }
  const ini = futuras[0].inicio >= hoje ? futuras[0].inicio : hoje;
  const ult = new Date(futuras[futuras.length - 1].inicio + "T12:00");
  ult.setDate(ult.getDate() + 6);
  $("#inicio").value = ini;
  $("#fim").value = ult.toISOString().slice(0, 10);
  montarDias(true);
  sugerirBloco();                 // maior semana e longo do novo período
}

async function ajustarPlanoAteProva() {
  const tab = document.querySelector(".plano-edit");
  const prova = $("#plano-prova") && $("#plano-prova").value;
  if (!tab || !prova) return;
  const ini = segundaDe(new Date(tab.dataset.inicio + "T12:00"));
  const alvo = Math.round((segundaDe(new Date(prova + "T12:00")) - ini) / 6048e5) + 1;
  if (alvo < 2) { alert("A prova é anterior ao início do ciclo."); return; }
  // macrociclo do objetivo: fases, km, longo e sessões-chave por semana
  const cal = (DADOS && DADOS.provas || []).find((p) => p.date === prova);
  const objetivo = objetivoMotor() || objetivoPorKm(cal && kmDaProva(cal)) || "";
  const linhasAtuais = [...tab.querySelectorAll("tr")].slice(1);
  const kmIni = +(linhasAtuais[0] && linhasAtuais[0].querySelector(".p-km").value) || null;
  try {
    const r = await api("/api/periodizacao/sugestao", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objetivo: objetivo || null, inicio: tab.dataset.inicio, prova_data: prova,
        km_ini: kmIni, historico: historicoCompacto() }),
    });
    if (r.semanas && r.semanas.length) {
      let linhas = [...tab.querySelectorAll("tr")].slice(1);
      while (linhas.length > r.semanas.length) { linhas.pop().remove(); }
      while (linhas.length < r.semanas.length) {
        const nova = linhas[linhas.length - 1].cloneNode(true);
        tab.appendChild(nova); linhas.push(nova);
      }
      linhas.forEach((tr, i) => {
        const w = r.semanas[i];
        tr.querySelector(".p-fase").value = w.fase === "Recuperação" ? "Base" : w.fase;
        tr.querySelector(".p-km").value = w.km;
        tr.querySelector(".p-obs").value = w.obs || "";
      });
      renumeraPlano();
      $("#plano-status") && ($("#plano-status").textContent =
        `${r.semanas.length} semanas até ${fmtBR(prova)} · ${r.objetivo} · ${r.km_ini}→${r.km_pico} km · confira e salve`);
      return;
    }
  } catch (e) { /* sem motor: cai no ajuste simples abaixo */ }
  let linhas = [...tab.querySelectorAll("tr")].slice(1);
  while (linhas.length > alvo) { linhas.pop().remove(); }
  while (linhas.length < alvo) {
    const nova = linhas[linhas.length - 1].cloneNode(true);
    nova.querySelector(".p-obs").value = "";
    tab.appendChild(nova); linhas.push(nova);
  }
  // cauda do ciclo: 1-2 semanas de polimento e a semana da prova
  const taper = alvo >= 9 ? 2 : 1;
  const pico = Math.max(...linhas.map((tr) => +tr.querySelector(".p-km").value || 0));
  linhas.forEach((tr, i) => {
    const sel = tr.querySelector(".p-fase"), km = tr.querySelector(".p-km");
    if (i === alvo - 1) { sel.value = "Prova"; km.value = Math.round(pico * 0.40); }
    else if (i >= alvo - 1 - taper) {
      sel.value = "Polimento";
      km.value = Math.round(pico * (i === alvo - 1 - taper ? 0.70 : 0.55));
    } else if (sel.value === "Prova" || sel.value === "Polimento") {
      sel.value = "Específico";               // linha antiga que deixou de ser cauda
    }
  });
  renumeraPlano();
  $("#plano-status") && ($("#plano-status").textContent =
    `${alvo} semanas até ${fmtBR(prova)} — confira e salve`);
}
$("#plano-box").addEventListener("change", (e) => {
  if (e.target.id === "plano-prova") ajustarPlanoAteProva();
  if (["cr-obj", "cr-prova", "cr-inicio"].includes(e.target.id)) sugerirCiclo();
});

$("#plano-box").addEventListener("click", async (e) => {
  const t = e.target;
  if (t.id === "usar-datas") return usarDatasDoPlano();
  if (t.id === "plano-add") {
    const tab = document.querySelector(".plano-edit");
    const modelo = tab.querySelector("tr:last-child");
    const nova = modelo.cloneNode(true);
    nova.querySelector(".p-obs").value = "";
    tab.appendChild(nova);
    return renumeraPlano();
  }
  if (t.classList.contains("plano-del")) {
    const tab = document.querySelector(".plano-edit");
    if (tab.querySelectorAll("tr").length <= 2) { alert("O plano precisa de pelo menos uma semana."); return; }
    t.closest("tr").remove();
    return renumeraPlano();
  }
  if (t.id === "plano-salvar") await salvarPlanoDaTela();
  if (t.id === "plano-criar") {
    carregando("criando o ciclo...");
    try {
      const r = await api("/api/periodizacao/criar", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          athlete_id: DADOS.athlete_id,
          nome: $("#cr-nome").value, prova_data: $("#cr-prova").value,
          inicio: $("#cr-inicio").value, objetivo: $("#cr-obj").value,
          km_ini: $("#cr-km-ini").value, km_pico: $("#cr-km-pico").value,
          historico: historicoCompacto(),
          ...progressaoPedido(),
        }),
      });
      DADOS.periodizacao = r.periodizacao;
      pintarPlano();
      statusProgressao("Ciclo criado com essa progressão." + (r.aviso ? " " + r.aviso : ""));
      usarDatasDoPlano();
      montarDias();          // reproduz a periodizacao nos dias/tipos
    } catch (err) { alert("Erro ao criar: " + err.message); } finally { pronto(); }
  }
});

// -- 2. dias (uma linha por semana do ciclo) --------------------------------
function segundaDe(d) {           // segunda-feira da semana de uma Date
  const x = new Date(d); x.setDate(x.getDate() - ((x.getDay() + 6) % 7)); return x;
}
function nSemanasPeriodo() {
  const i = new Date($("#inicio").value + "T12:00");
  const f = new Date($("#fim").value + "T12:00");
  if (isNaN(i) || isNaN(f) || f < i) return 4;
  // semanas de segunda a segunda: mesma contagem das linhas da periodização
  const n = Math.round((segundaDe(f) - segundaDe(i)) / 6048e5) + 1;
  return Math.min(Math.max(n, 1), 30);
}

function fmtHoras(min) {
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return `${h}:${String(m).padStart(2, "0")} h`;
}

// chips editaveis com os dias de treino do atleta (detectados, ajustaveis)
const ABREV_D = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"];

function pintarChipsDias(marcados) {
  $("#chips-dias").innerHTML = ABREV_D.map((a, d) =>
    `<label class="chip-dia"><input type="checkbox" data-dia="${d}"
      ${marcados.includes(d) ? "checked" : ""}><span>${a}</span></label>`).join("");
}

function diasEscolhidos() {
  const marcados = [...document.querySelectorAll("#chips-dias input:checked")]
    .map((c) => +c.dataset.dia);
  if (marcados.length) return marcados;
  return ((DADOS && DADOS.historico && DADOS.historico.dias_treino) || [])
    .map((d) => d.dia);
}

// enfase de qualidade por objetivo, com rotacao semana a semana:
// 5k/10k = limiar + VO2 curtos; 21k = limiar dominante e POUCO VO2 (a cada 3
// semanas); 42k = limiar + ritmo pos-fadiga (pre-fadiga/ritmo de prova)
// ---- sugestão de semanas: fase da periodização + objetivo, sem repetir ----
// Pools de qualidade por fase e objetivo. A rotação usa (semana + semente do
// atleta), então semanas vizinhas nunca saem iguais e atletas diferentes
// recebem sequências diferentes.
// Regra de organização do ciclo (André, 01/11/2026):
// - Base: menos intensidade e mais rodagem (UMA qualidade na semana).
// - 5 e 10 km: muita intensidade e volume menor (VO2, pirâmide, ritmo de prova).
// - Meia e maratona: limiar, durabilidade e ritmo de prova, sem VO2; os longos do
//   Específico são de durabilidade (parte forte no fim, progressivo, alternado).
const POOL_QUAL = {
  Base: {
    "5k":  ["fartlek", "limiar", "progressivo", "segundo_limiar"],
    "10k": ["limiar", "fartlek", "progressivo", "segundo_limiar"],
    "21k": ["limiar", "progressivo", "segundo_limiar", "escada_limiar"],
    "42k": ["limiar", "progressivo", "segundo_limiar", "escada_limiar"],
    padrao: ["limiar", "fartlek", "escada_limiar", "progressivo", "limiar_prefadiga", "segundo_limiar"],
  },
  "Específico": {
    "5k":  ["vo2max", "piramide", "limiar_vo2", "ritmo_prova", "over_under", "limiar"],
    "10k": ["vo2max", "limiar_vo2", "ritmo_prova", "piramide", "over_under", "escada_limiar"],
    "21k": ["limiar", "ritmo_prova", "segundo_limiar", "escada_limiar", "over_under"],
    "42k": ["ritmo_prova", "limiar", "limiar_prefadiga", "segundo_limiar", "escada_limiar", "progressivo"],
    padrao: ["limiar", "vo2max", "ritmo_prova", "escada_limiar", "fartlek", "limiar_vo2"],
  },
  Polimento: {
    "42k": ["ritmo_prova", "limiar"], "21k": ["ritmo_prova", "limiar"],
    padrao: ["ritmo_prova", "vo2max", "limiar"],
  },
  Prova: { padrao: ["limiar"] },
};
// longos do Específico (na Base o longo é contínuo)
const POOL_LONGO = {
  "42k": ["longo_bloco", "longo_alternado", "longo_progressivo", "longo_bloco"],
  "21k": ["longo_bloco", "longo_progressivo", "longo_alternado", "longo_trocas"],
  padrao: ["longo", "longo_surges", "longo", "longo_progressivo"],
};

function sementeAtleta() {
  const id = String((DADOS && DADOS.athlete_id) || 0);
  return [...id].reduce((a, c) => a + c.charCodeAt(0), 0) % 7;
}

// fase e "semana leve" da semana w da grade, pela periodização do atleta
// (casando a segunda-feira) ou pela posição no bloco quando não há plano
// bloco sem semana de recuperação (opção do passo Bloco)
function semRecup() { const c = document.getElementById("sem-recup"); return !!(c && c.checked); }

// -- progressão do ciclo: manda na periodização do atleta -------------------
function progressaoPedido() {
  return {
    progressao_pct: $("#progressao").value === "" ? null : +$("#progressao").value,
    recup_cada: $("#recup-cada").value === "" ? 4 : +$("#recup-cada").value,
    recup_corte_pct: $("#recup-corte").value === "" ? 25 : +$("#recup-corte").value,
    sem_recuperacao: semRecup(),
    // dias de treino da semana: o plano não põe semana abaixo do longo + os
    // outros dias com o mínimo por treino
    dias_semana: (typeof diasEscolhidos === "function" && diasEscolhidos().length) || null,
    // menor semana do Período: nenhuma semana de carga abaixo dela (vazio = 0, sem piso)
    semana_min: $("#semana-min").value === "" ? 0 : +$("#semana-min").value,
    // menor longo do Período: nenhum longo de Base/Específico abaixo dele (vazio = 0, sem piso)
    longo_min: $("#longo-min").value === "" ? 0 : +$("#longo-min").value,
  };
}
function statusProgressao(txt, alerta) {
  const el = $("#progressao-status");
  if (!el) return;
  el.innerHTML = txt;
  el.style.color = alerta ? "var(--vermelho)" : "";
}
// ao carregar o atleta, a caixa mostra a progressão com que o plano foi montado
function progressaoDoPlano(p) {
  const pr = p && p.params;
  if (!pr) {
    statusProgressao(p ? "Plano criado fora do gerador: mudar a progressão refaz o plano inteiro."
                       : "Vale para a periodização do atleta: mudou aqui, o plano inteiro é refeito.");
    return;
  }
  const sem = !pr.recup_cada;
  $("#sem-recup").checked = sem;
  if (!sem) $("#recup-cada").value = pr.recup_cada;
  if (pr.recup_corte != null) $("#recup-corte").value = pr.recup_corte;
  if (pr.progressao != null) $("#progressao").value = pr.progressao;
  if (pr.min_km != null) setAuto("#min-km", pr.min_km);
  if (pr.max_km != null) setAuto("#max-km", pr.max_km);
  if (pr.semana_min) setAuto("#semana-min", pr.semana_min);
  if (pr.longo_min) setAuto("#longo-min", pr.longo_min);
  if (["base", "especifico", "base_especifico", "completo"].includes(pr.modo)) $("#fases-ciclo").value = pr.modo;
  ["#recup-cada", "#recup-corte"].forEach((k) => { $(k).disabled = sem; });
  statusProgressao("Progressão da periodização do atleta: mudou aqui, o plano inteiro é refeito.");
  if (DADOS) DADOS._inputsProg = inputsProgressao();
}

let _refazerTimer = null, _desfazerPlano = null;
let _picoEditado = false, _longoEditado = false;
// com a periodização ligada, "Maior semana" e "Maior longo" são o pico do ciclo inteiro
function picosPedidos() {
  const out = {};
  if (!(DADOS && DADOS.periodizacao)) return out;
  if (_picoEditado && $("#semana-max").value) out.km_pico = +$("#semana-max").value;
  if (_longoEditado && $("#longo-max").value) out.longo_pico = +$("#longo-max").value;
  return out;
}
function inputsProgressao() {
  return { progressao: $("#progressao").value, recupCada: $("#recup-cada").value,
           recupCorte: $("#recup-corte").value, semRecup: semRecup() };
}
async function refazerPlano() {
  const p = DADOS && DADOS.periodizacao;
  if (!p) return;
  statusProgressao("Refazendo a periodização do atleta…");
  const enviado = { sem: $("#semana-max").value, longo: $("#longo-max").value };
  // os picos editados vão neste pedido; uma edição feita enquanto ele está no
  // ar marca de novo e entra no pedido seguinte
  const picos = picosPedidos();
  const mexeuPico = _picoEditado || _longoEditado;
  _picoEditado = _longoEditado = false;
  try {
    const r = await api("/api/periodizacao/refazer", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: DADOS.athlete_id, plano_id: p.id,
        objetivo: objetivoMotor() || null, ...progressaoPedido(), ...picos,
        min_km: parseFloat($("#min-km").value) || null, max_km: parseFloat($("#max-km").value) || null }),
    });
    DADOS.periodizacao = r.periodizacao;
    // o treinador mexeu de novo enquanto este pedido ia e voltava: só o plano
    // é atualizado; os campos ficam com o valor novo, que já está na fila
    if (_refazerTimer || $("#semana-max").value !== enviado.sem || $("#longo-max").value !== enviado.longo) {
      pintarPlano();
      return;
    }
    pintarPlano();
    montarDias(true);
    reaplicarSugestaoGrade();
    sugerirBloco();
    const leve = semRecup() ? "sem semana leve" :
      `semana leve a cada ${$("#recup-cada").value} (corte de ${$("#recup-corte").value}%)`;
    const pq = mexeuPico ? `maior semana ${$("#semana-max").value} km e longo até ${$("#longo-max").value} km, ` : "";
    statusProgressao(`Plano refeito: ${pq}${leve}.${r.aviso ? " " + r.aviso : ""} ` +
      `<a href="#" id="desfazer-plano">desfazer</a>`);
  } catch (err) {
    if (picos.km_pico) _picoEditado = true;
    if (picos.longo_pico) _longoEditado = true;
    statusProgressao("Não deu para refazer o plano: " + err.message, true);
  } finally { pronto(); }
}
// progressão: refaz enquanto digita (com espera); maior semana/longo: só quando
// o valor é confirmado (change), para não refazer o plano com um número pela metade
document.addEventListener("input", (e) => {
  if (["progressao", "recup-cada", "recup-corte", "sem-recup"].includes(e.target.id)) agendarRefazer(e);
});
document.addEventListener("change", (e) => {
  if (["semana-max", "semana-min", "longo-max", "longo-min", "min-km"].includes(e.target.id)) agendarRefazer(e);
});
function agendarRefazer(e) {
  if (!DADOS || !DADOS.periodizacao) return;
  if (["semana-max", "semana-min", "longo-max", "longo-min", "min-km"].includes(e.target.id)) {
    // fora da periodização (caixa "Seguir a periodização" desmarcada) os
    // campos valem só para o bloco; menor semana e menor longo apagados também refazem (tiram o piso)
    if (!($("#seguir-plano") && $("#seguir-plano").checked)) return;
    if (!e.target.value && !["semana-min", "longo-min"].includes(e.target.id)) return;
    if (e.target.id === "semana-max") _picoEditado = true;
    else if (e.target.id === "longo-max") _longoEditado = true;
  }
  // guarda o plano de antes da primeira mudança de uma sequência, para o desfazer
  if (!_refazerTimer) {
    _desfazerPlano = { semanas: DADOS.periodizacao.semanas.map((s) => ({ ...s })),
                       nome: DADOS.periodizacao.nome, prova_data: DADOS.periodizacao.prova_data,
                       params: DADOS.periodizacao.params, inputs: DADOS._inputsProg || inputsProgressao() };
  }
  clearTimeout(_refazerTimer);
  _refazerTimer = setTimeout(async () => {
    _refazerTimer = null;
    await refazerPlano();
    DADOS._inputsProg = inputsProgressao();
  }, 600);
}
document.addEventListener("click", async (e) => {
  if (e.target.id !== "desfazer-plano") return;
  e.preventDefault();
  const u = _desfazerPlano;
  if (!u || !DADOS || !DADOS.periodizacao) return;
  carregando("voltando o plano anterior...");
  try {
    const r = await api("/api/periodizacao/salvar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: DADOS.athlete_id, plano_id: DADOS.periodizacao.id,
        nome: u.nome, prova_data: u.prova_data, semanas: u.semanas, params: u.params }),
    });
    $("#progressao").value = u.inputs.progressao; $("#recup-cada").value = u.inputs.recupCada;
    $("#recup-corte").value = u.inputs.recupCorte; $("#sem-recup").checked = u.inputs.semRecup;
    ["#recup-cada", "#recup-corte"].forEach((k) => { $(k).disabled = u.inputs.semRecup; });
    DADOS.periodizacao = r.periodizacao;
    DADOS._inputsProg = inputsProgressao();
    _desfazerPlano = null;
    pintarPlano(); montarDias(true); reaplicarSugestaoGrade(); sugerirBloco();
    statusProgressao("Plano anterior de volta.");
  } catch (err) { alert("Erro ao desfazer: " + err.message); } finally { pronto(); }
});
// a grade segue as semanas leves do plano: reaplica a sugestão nos dias marcados
function reaplicarSugestaoGrade() {
  if (typeof montarDias !== "function" || !document.querySelector("#dias select[data-dia]")) return;
  document.querySelectorAll("#dias select[data-dia]").forEach((sel) => {
    const w = +sel.dataset.semana, sug = sugestaoGrade(w) || {};
    if (eManual(w, +sel.dataset.dia)) return;
    if (sel.value && sug[+sel.dataset.dia] && !sel.value.startsWith("forca")) sel.value = sug[+sel.dataset.dia];
  });
  document.dispatchEvent(new CustomEvent("fases-mudou"));
}
document.addEventListener("change", (e) => {
  if (e.target.id !== "sem-recup") return;
  ["#recup-cada", "#recup-corte"].forEach((k) => { $(k).disabled = e.target.checked; });
  // as semanas leves somem da sugestão: redesenha a grade mantendo o que já foi marcado
  if (typeof montarDias === "function" && document.querySelector("#dias select[data-dia]")) {
    document.querySelectorAll("#dias select[data-dia]").forEach((sel) => {
      const w = +sel.dataset.semana, sug = sugestaoGrade(w) || {};
      if (eManual(w, +sel.dataset.dia)) return;
      if (sel.value && sug[+sel.dataset.dia] && !sel.value.startsWith("forca")) sel.value = sug[+sel.dataset.dia];
    });
  }
  document.dispatchEvent(new CustomEvent("fases-mudou"));
});

function faseDaSemana(w) {
  const auto = faseAutomatica(w);
  const manual = FASES[w] && FASES[w].corrida;
  return manual ? { ...auto, fase: manual, manual: true, auto: auto.fase } : { ...auto, auto: auto.fase };
}
function faseAutomatica(w) {
  const n = nSemanasPeriodo();
  const ini = segundaDe(new Date($("#inicio").value + "T12:00"));
  const seg = new Date(ini); seg.setDate(seg.getDate() + 7 * (w - 1));
  const segIso = seg.toISOString().slice(0, 10);
  const plano = DADOS && DADOS.periodizacao;
  if (plano) {
    const k = plano.semanas.findIndex((x) => x.inicio === segIso);
    const sem = k >= 0 ? plano.semanas[k] : null;
    if (sem) {
      // semana leve = queda de 13% ou mais no km em relação à anterior (fora de Polimento/Prova)
      const ant = k > 0 ? plano.semanas[k - 1] : null;
      const caiu = ant && ant.km && sem.km && +sem.km < +ant.km * 0.87;
      return { fase: sem.fase, leve: !semRecup() && !!caiu && !["Polimento", "Prova"].includes(sem.fase) };
    }
  }
  const provaData = $("#prova-data").value;
  const fim = new Date(seg); fim.setDate(fim.getDate() + 6);
  if (provaData && provaData >= segIso && provaData <= fim.toISOString().slice(0, 10))
    return { fase: "Prova", leve: false };
  const recup = semRecup() ? 0 : (+$("#recup-cada").value || 0);
  const leve = recup > 0 && w % recup === 0 && w < n;
  const frac = w / Math.max(n, 1);
  const fase = n <= 3 ? "Específico" : frac <= 0.45 ? "Base" : frac <= 0.85 ? "Específico" : "Polimento";
  return { fase, leve };
}

// só força: fase de cada semana (espelho de forca.fase_da_semana + a descarga do Bloco)
function faseForcaAuto(w) {
  const n = nSemanasPeriodo(), cada = +$("#forca-descarga").value || 0;
  if (cada > 0 && w % cada === 0 && w < n) return "Descarga";
  if (FASE_DO_OBJETIVO[forcaObjetivo()]) return FASE_DO_OBJETIVO[forcaObjetivo()];
  if (n <= 1) return "Base";
  if (n <= 3) return ["Base", "Força máxima", "Competitivo"][Math.min(w, n) - 1];
  if (n === 5) return ["Adaptação", "Força máxima", "Acumulação", "Pré-competitivo", "Competitivo"][Math.min(w, 5) - 1];
  if (n === 4) return ["Base", "Força máxima", "Acumulação", "Competitivo"][Math.min(w, 4) - 1];
  const fases = FASES_FORCA.slice(0, 6);
  const qt = [0.15, 0.15, 0.20, 0.20, 0.15, 0.15].map((p) => Math.max(1, Math.round(n * p)));
  while (qt.reduce((a, b) => a + b) > n) qt[qt.indexOf(Math.max(...qt))]--;
  while (qt.reduce((a, b) => a + b) < n) qt[2]++;
  let acc = 0;
  for (let i = 0; i < 6; i++) { acc += qt[i]; if (w <= acc) return fases[i]; }
  return "Competitivo";
}
const faseForcaDaSemana = (w) => (FASES[w] && FASES[w].forca) || faseForcaAuto(w);
// espelho de forca.RECEITA_FASE, só para mostrar no quadro
const RECEITA_FASE = { "Adaptação": "3 séries de 10", "Base": "3 séries de 8", "Força máxima": "3 séries de 5",
  "Acumulação": "3 séries de 6", "Pré-competitivo": "3 séries de 5", "Competitivo": "3 séries de 6", "Descarga": "2 séries de 8",
  "Hipertrofia": "4 séries de 10 a 12", "Potência": "3 séries de 5, velocidade máxima", "Resistência": "3 séries de 15" };
function pintarPlanoForca() {
  const box = $("#plano-forca");
  if (!box || modalidade() !== "forca" || !$("#inicio").value) return;
  const n = nSemanasPeriodo();
  const ini = segundaDe(new Date($("#inicio").value + "T12:00"));
  let linhas = "";
  for (let w = 1; w <= n; w++) {
    const seg = new Date(ini); seg.setDate(seg.getDate() + 7 * (w - 1));
    const fase = faseForcaDaSemana(w), manual = FASES[w] && FASES[w].forca;
    const receita = RECEITA_FASE[fase];
    linhas += `<tr><td class="p-idx">${w}</td><td class="p-data">${seg.toISOString().slice(0, 10).split("-").reverse().slice(0, 2).join("/")}</td>
      <td><select class="plano-forca-sel${manual ? " manual" : ""}" data-semana="${w}"><option value="">automática · ${faseForcaAuto(w)}</option>` +
      FASES_FORCA.map((f) => `<option value="${f}" ${manual === f ? "selected" : ""}>${f}</option>`).join("") +
      `</select></td><td>${receita}</td></tr>`;
  }
  box.innerHTML = `<div class="grade-wrap"><table class="zonas plano-edit"><tr><td>sem</td><td>início</td><td>fase</td><td>exercícios principais</td></tr>${linhas}</table></div>`;
}
$("#plano-forca").addEventListener("change", (e) => {
  if (!e.target.classList.contains("plano-forca-sel")) return;
  const w = +e.target.dataset.semana;
  FASES[w] = { ...(FASES[w] || {}) };
  if (e.target.value) FASES[w].forca = e.target.value; else delete FASES[w].forca;
  if (!Object.keys(FASES[w]).length) delete FASES[w];
  const g = document.querySelector(`#dias .forca-sel[data-semana="${w}"]`);
  if (g) g.value = e.target.value;
  document.dispatchEvent(new CustomEvent("fases-mudou"));
});
document.addEventListener("fases-mudou", pintarPlanoForca);
document.addEventListener("change", (e) => {
  if (["inicio", "fim"].includes(e.target.id)) agendarPlanoCiclismo();
  if (["inicio", "fim", "forca-descarga"].includes(e.target.id) || e.target.name === "forca-objetivo") {
    pintarPlanoForca();
    document.dispatchEvent(new CustomEvent("fases-mudou"));
  }
});

function sugestaoGrade(w) {
  let dias = diasEscolhidos();
  w = w || 1;
  if (modalidade() === "ciclismo") return sugestaoCiclismo(w, dias);
  if (modalidade() === "forca") {           // só força: 2 a 4 dias de força, alternando o foco
    if (!dias.length) dias = [1, 3, 5];     // sem dias marcados: ter/qui/sáb
    const focos = ["forca", "forca_inferior", "forca_superior", "forca_core"];
    const mapa = {};
    dias.slice(0, 4).forEach((d, k) => { mapa[d] = focos[(k + w - 1) % focos.length]; });
    return mapa;
  }
  if (!dias.length) return null;
  const obj = objetivoMotor();
  const { fase, leve } = faseDaSemana(w);
  const sem = sementeAtleta();

  // o longo vai para sabado/domingo se ele treina neles; senao o ultimo dia
  const fimSemana = dias.filter((d) => d >= 5);
  const diaLongo = dias.length >= 2
    ? (fimSemana.length ? Math.max(...fimSemana) : Math.max(...dias))
    : null;
  const restantes = dias.filter((d) => d !== diaLongo);
  const mapa = {};

  if (leve) {                                   // semana leve: só rodagem
    restantes.forEach((d) => { mapa[d] = "rodagem_leve"; });
    if (diaLongo != null) mapa[diaLongo] = "longo_continuo";
    return mapa;
  }

  const pool = (POOL_QUAL[fase] || POOL_QUAL.Base);
  const quals = pool[obj] || pool.padrao;
  const longa = obj === "21k" || obj === "42k";
  // Base: 1 qualidade e o resto rodagem. Específico: 5/10 km até 3 qualidades
  // (intensidade), meia/maratona 2 (limiar + ritmo de prova; o longo é o 3º estímulo)
  let nQual = Math.min(restantes.length, restantes.length >= 4 && !longa ? 3 : 2);
  if (fase === "Base") nQual = Math.min(restantes.length, 1);
  if (fase === "Polimento") nQual = Math.min(nQual, 2);
  if (fase === "Prova") nQual = 1;

  // qualidades da semana: janela deslizante no pool, deslocada por semana+atleta
  const off = (w - 1 + sem) % quals.length;
  const escolhidas = [];
  for (let i = 0; escolhidas.length < nQual && i < quals.length; i++) {
    const t = quals[(off + i * 2) % quals.length];      // passo 2 evita vizinhas iguais
    if (!escolhidas.includes(t)) escolhidas.push(t);
  }
  // dia mais distante do longo recebe a qualidade mais forte; nunca dois fortes
  // em dias seguidos (a semana é cíclica: domingo e segunda são vizinhos)
  const distC = (a, b) => { const x = Math.abs(a - b); return Math.min(x, 7 - x); };
  const fortes = diaLongo != null ? [diaLongo] : [];
  const vizinhoForte = (d) => fortes.some((f) => distC(d, f) === 1);
  const ordem = [...restantes].sort((a, b) =>
    (diaLongo == null ? b - a : distC(b, diaLongo) - distC(a, diaLongo)));
  let qi = 0;
  ordem.forEach((d) => {
    if (qi < nQual && !vizinhoForte(d)) { mapa[d] = escolhidas[qi++]; fortes.push(d); }
  });
  ordem.forEach((d, i) => {
    if (!mapa[d]) mapa[d] = ((i + w + sem) % 2) ? "rodagem_strides" : "rodagem_leve";
  });
  if (diaLongo != null) {
    if (fase === "Prova") mapa[diaLongo] = "rodagem_leve";      // a prova entra sozinha
    else {
      const pl = POOL_LONGO[obj] || POOL_LONGO.padrao;
      mapa[diaLongo] = fase === "Base" ? "longo_continuo"
                     : fase === "Polimento" ? "longo"
                     : pl[(w - 1 + sem) % pl.length];
    }
  }
  return mapa;
}

function aplicarSugestao() {
  if (!diasEscolhidos().length) {
    alert("Marque pelo menos um dia de treino."); return;
  }
  document.querySelectorAll("#dias select[data-dia]").forEach((s) => {
    if (eManual(+s.dataset.semana, +s.dataset.dia)) return;
    const mapa = sugestaoGrade(+s.dataset.semana) || {};
    s.value = mapa[s.dataset.dia] || "";
    s.classList.toggle("ativo", !!s.value);
  });
}

function montarDias(preservar) {
  const n = nSemanasPeriodo();
  const abrev = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"];

  // ao redesenhar (mudanca de datas), mantem o que ja foi configurado
  const prev = { tipos: {}, max: {} };
  let prevMaxW = 0;
  if (preservar) {
    document.querySelectorAll("#dias select[data-dia]").forEach((s) => {
      (prev.tipos[s.dataset.semana] ??= {})[s.dataset.dia] = s.value;
      prevMaxW = Math.max(prevMaxW, +s.dataset.semana);
    });
    document.querySelectorAll(".dia-max").forEach((el) => {
      prev.max[el.dataset.dia] = el.value;
    });
  }
  // força no mesmo dia da corrida (segunda sessão): estado guardado à parte
  const prevF2 = {};
  document.querySelectorAll("#dias select.forca2").forEach((s2) => {
    (prevF2[s2.dataset.semana2] ??= {})[s2.dataset.dia2] = s2.value;
  });
  const comForca2 = ["mista", "ciclismo"].includes(modalidade());
  const soForca = modalidade() === "forca";
  const cicl = modalidade() === "ciclismo";
  const rotForca = (v) => ((TIPOS.find(([x]) => x === v) || [])[1] || v).replace("Força · ", "").replace(" (academia)", "");
  const forca2Html = (w, i) => {
    if (!comForca2) return "";
    const v2 = (prevF2[w] || {})[i] || "";
    return `<select class="forca2 ${v2 ? "ativo" : ""}" data-semana2="${w}" data-dia2="${i}" title="Força no mesmo dia da corrida (segunda sessão)">` +
      `<option value="">+ força</option>` +
      FORCA_TIPOS.map((t) => `<option value="${t}" ${v2 === t ? "selected" : ""}>+ ${rotForca(t)}</option>`).join("") + `</select>`;
  };
  const permitidos = new Set(tiposVisiveis().map(([v]) => v));
  const valorDe = (w, i) => {
    if (preservar && prevMaxW) {
      const linha = prev.tipos[Math.min(w, prevMaxW)] || {};
      const v = linha[i] ?? "";
      return permitidos.has(v) ? v : "";
    }
    const padrao = sugestaoGrade(w) || { 1: "limiar", 3: "vo2max", 5: "longo" };
    return padrao[i] || "";
  };

  let html = `<div class="sem-cfg cab"><span></span>` +
    abrev.map((a) => `<span>${a}</span>`).join("") + `<span></span></div>`;
  for (let w = 1; w <= n; w++) {
    const fw = FASES[w] || {};
    const cm = (CIC_MANUAL[w] || {}).fase || "";
    html += `<div class="sem-cfg"><div class="sem-fase">` +
      (soForca ? "" : cicl ? `<label title="Fase do ciclo de ciclismo nesta semana: muda a sugestão de treinos e a dose">Fase ` +
      `<select class="cic-fase-sel" data-semana="${w}"><option value="">automática</option>` +
      FASES_CIC.map((f) => `<option value="${f}" ${cm === f ? "selected" : ""}>${f}</option>`).join("") + `</select></label>`
      : `<label title="Fase do ciclo de corrida nesta semana — muda a sugestão de treinos e o volume">Fase ` +
      `<select class="fase-sel" data-semana="${w}"><option value="">automática</option>` +
      FASES_PLANO.map((f) => `<option value="${f}" ${fw.corrida === f ? "selected" : ""}>${f}</option>`).join("") +
      `</select></label>`) +
      (cicl ? "" : `<label title="Fase da periodização de força nesta semana — define as séries e repetições">${soForca ? "Fase" : "Força"} ` +
      `<select class="forca-sel" data-semana="${w}"><option value="">automática</option>` +
      FASES_FORCA.map((f) => `<option value="${f}" ${fw.forca === f ? "selected" : ""}>${f}</option>`).join("") +
      `</select></label>`) + `${soForca ? "" : `<span class="sem-km"></span>`}</div><label>Sem ${w}</label>` +
      abrev.map((_, i) => {
        const v = valorDe(w, i);
        const nota = (NOTAS[w] || {})[i];
        const fixo = (FIXOS[w] || {})[i];
        const man = eManual(w, i);
        return `<span class="cel-tipo"><select data-semana="${w}" data-dia="${i}" class="${v ? "ativo" : ""}${man ? " manual" : ""}"` +
          `${man ? ` title="Marcado à mão: o gerador não muda"` : ""}>` +
          tiposVisiveis().map(([tv, t]) =>
            `<option value="${tv}" ${v === tv ? "selected" : ""}>${t}</option>`).join("") +
          `</select><button type="button" class="nota-btn ${nota ? "tem-nota" : ""}" ` +
          `data-semana="${w}" data-dia="${i}" title="${nota ? nota.replace(/"/g, "&quot;") : "Comentário para esta sessão"}"><svg><use href="#ic-nota"/></svg></button>` +
          `<button type="button" class="param-btn ${fixo ? "tem-nota" : ""}" ` +
          `data-semana="${w}" data-dia="${i}" title="${fixo ? "Estrutura definida — clique para editar" : "Estruturar esta sessão antes de gerar"}"><svg><use href="#ic-estrutura"/></svg></button>${forca2Html(w, i)}</span>`;
      }).join("") +
      `<span class="sem-acoes">` +
      (w > 1 ? `<button class="ghost copiar" data-w="${w}" title="Copiar a semana anterior inteira">⧉</button>` : "") +
      (w < n && !soForca ? `<button class="ghost copiar-forca" data-w="${w}" title="Copiar só a força desta semana para a semana ${w + 1}">F↓</button>` : "") +
      `</span></div>`;
  }
  // linha de tempo maximo por dia da semana (vale para todas as semanas)
  html += `<div class="sem-cfg tempo-max"><label title="Duração máxima do treino nesse dia">Máx min</label>` +
    abrev.map((_, i) =>
      `<input type="number" class="dia-max" data-dia="${i}" min="15" step="5" ` +
      `value="${preservar ? (prev.max[i] || "") : ""}" placeholder="—" ` +
      `title="tempo máximo (minutos) de treino na ${DIAS[i]}">`).join("") +
    `<span></span></div>`;
  $("#dias").innerHTML = html;
  $("#dias").onchange = (e) => {
    if (e.target.classList.contains("cic-fase-sel")) {      // fase do ciclismo: vale no quadro do Bloco também
      cicManual(+e.target.dataset.semana, "fase", e.target.value);
      return;
    }
    if (e.target.classList.contains("fase-sel") || e.target.classList.contains("forca-sel")) {
      const w = +e.target.dataset.semana, chave = e.target.classList.contains("fase-sel") ? "corrida" : "forca";
      FASES[w] = { ...(FASES[w] || {}) };
      if (e.target.value) FASES[w][chave] = e.target.value; else delete FASES[w][chave];
      if (!Object.keys(FASES[w]).length) delete FASES[w];
      document.dispatchEvent(new CustomEvent("fases-mudou"));   // shell repinta faixa e ciclo
      if (chave === "corrida") {
        // a fase muda o cardápio: resugere só os dias que já estão marcados nesta semana
        const sug = sugestaoGrade(w) || {};
        document.querySelectorAll(`#dias select[data-semana="${w}"][data-dia]`).forEach((s) => {
          if (!s.value || eManual(w, +s.dataset.dia)) return;
          const novo = sug[+s.dataset.dia];
          if (novo && novo !== s.value) {
            s.value = novo;
            if (FIXOS[w] && FIXOS[w][+s.dataset.dia] !== undefined) {
              delete FIXOS[w][+s.dataset.dia];
              s.closest(".cel-tipo")?.querySelector(".param-btn")?.classList.remove("tem-nota");
            }
          }
        });
      }
      return;
    }
    if (e.target.tagName === "SELECT") {
      e.target.classList.toggle("ativo", !!e.target.value);
      const w = +e.target.dataset.semana, di = +e.target.dataset.dia;
      // o código nunca dispara "change" na grade: todo change aqui é do treinador
      if (e.target.dataset.dia !== undefined) marcarManual(w, di);
      if (FIXOS[w] && FIXOS[w][di] !== undefined) {
        delete FIXOS[w][di];       // params eram do tipo anterior
        e.target.closest(".cel-tipo")?.querySelector(".param-btn")
          ?.classList.remove("tem-nota");
      }
    }
    if (e.target.classList.contains("dia-max"))
      e.target.classList.toggle("ativo", !!e.target.value);
  };
  $("#dias").onclick = (e) => {
    const pb = e.target.closest(".param-btn");
    if (pb) return abrirParams(pb);
    const nb = e.target.closest(".nota-btn");
    if (nb) return abrirNota(nb);
    const bf = e.target.closest(".copiar-forca");
    if (bf) return copiarForcaGrade(+bf.dataset.w);
    const b = e.target.closest(".copiar");
    if (!b) return;
    const w = +b.dataset.w;
    document.querySelectorAll(`select[data-semana="${w}"][data-dia]`).forEach((s) => {
      const origem = document.querySelector(
        `select[data-semana="${w - 1}"][data-dia="${s.dataset.dia}"]`);
      if (!origem) return;
      s.value = origem.value;
      s.classList.toggle("ativo", !!s.value);
      marcarManual(w, +s.dataset.dia);
    });
    document.querySelectorAll(`select.forca2[data-semana2="${w}"]`).forEach((s2) => {
      const origem = document.querySelector(`select.forca2[data-semana2="${w - 1}"][data-dia2="${s2.dataset.dia2}"]`);
      if (!origem) return;
      s2.value = origem.value; s2.classList.toggle("ativo", !!s2.value);
    });
  };
}

// copia SÓ a força da semana w para a w+1. A corrida da semana seguinte não muda:
// força que caía em dia de corrida vai para o "+ força" do mesmo dia (modalidade mista).
function copiarForcaGrade(w) {
  const ehForca = (v) => !!v && v.startsWith("forca");
  const sel = (sem, d) => document.querySelector(`#dias select[data-semana="${sem}"][data-dia="${d}"]`);
  const sel2 = (sem, d) => document.querySelector(`#dias select.forca2[data-semana2="${sem}"][data-dia2="${d}"]`);
  const marcar = (el, v) => { if (!el) return; el.value = v; el.classList.toggle("ativo", !!v); };
  const sobrou = [];
  for (let d = 0; d < 7; d++) {
    const origem = sel(w, d), origem2 = sel2(w, d), alvo = sel(w + 1, d), alvo2 = sel2(w + 1, d);
    if (!alvo) continue;
    // limpa a força que já existia na semana seguinte
    if (ehForca(alvo.value)) marcar(alvo, "");
    if (alvo2) marcar(alvo2, "");
    const forcas = [origem && ehForca(origem.value) ? origem.value : "", origem2 ? origem2.value : ""].filter(Boolean);
    for (const f of forcas) {
      if (!alvo.value) marcar(alvo, f);                 // dia livre: força no treino principal
      else if (alvo2 && !alvo2.value) marcar(alvo2, f); // dia com corrida: força no mesmo dia
      else sobrou.push(`${DIAS[d]}: ${f}`);
    }
    // estrutura fixada (sessão escolhida) acompanha a força copiada no treino principal
    if (origem && ehForca(origem.value) && alvo.value === origem.value && (FIXOS[w] || {})[d] !== undefined) {
      (FIXOS[w + 1] ??= {})[d] = FIXOS[w][d];
      alvo.closest(".cel-tipo")?.querySelector(".param-btn")?.classList.add("tem-nota");
    }
  }
  document.dispatchEvent(new CustomEvent("fases-mudou"));
  if (sobrou.length) alert("Não coube na semana " + (w + 1) + " (o dia já tinha corrida e força):\n" + sobrou.join("\n"));
}

function abrirParams(btn) {
  document.querySelector(".nota-pop")?.remove();
  const w = +btn.dataset.semana, d = +btn.dataset.dia;
  const sel = document.querySelector(`select[data-semana="${w}"][data-dia="${d}"]`);
  const tipo = sel?.value;
  if (!tipo) { alert("Escolha primeiro o tipo de treino desse dia."); return; }
  if (!CAMPOS[tipo] || !CAMPOS[tipo].length) {
    alert("Esse tipo não tem parâmetros para fixar — o motor monta sozinho.");
    return;
  }
  const rotulo = (TIPOS.find(([v]) => v === tipo) || [])[1] || tipo;
  const abrev = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"];

  const pop = document.createElement("div");
  pop.className = "nota-pop param-pop";
  pop.innerHTML = `
    <label>Estrutura — ${rotulo} · ${abrev[d]}, semana ${w}
      <small>(o motor usa exatamente isso; progressão e teto de tempo não mexem)</small></label>
    <div class="param-campos">${camposHtml(tipo, null)}</div>
    <div class="editor-acoes">
      <button class="primario mini pp-salvar">Fixar estrutura</button>
      <button class="ghost mini pp-remover">Voltar ao automático</button>
      <button class="ghost mini pp-fechar">Fechar</button>
    </div>`;
  document.body.appendChild(pop);
  const r = btn.getBoundingClientRect();
  pop.style.top = `${r.bottom + window.scrollY + 6}px`;
  pop.style.left = `${Math.min(r.left + window.scrollX, window.innerWidth - 400)}px`;

  // preenche com o que ja estava fixado
  const salvo = (FIXOS[w] || {})[d] || {};
  pop.querySelectorAll("[data-k]").forEach((el) => {
    const v = salvo[el.dataset.k];
    if (v === undefined) return;
    if (el.type === "checkbox") el.checked = !!v;
    else el.value = v;
  });

  const fecha = () => pop.remove();
  pop.querySelector(".pp-fechar").onclick = fecha;
  pop.querySelector(".pp-salvar").onclick = () => {
    const params = {};
    pop.querySelectorAll("[data-k]").forEach((el) => {
      params[el.dataset.k] = el.type === "checkbox" ? el.checked : el.value;
    });
    (FIXOS[w] ??= {})[d] = params;
    btn.classList.add("tem-nota");
    btn.title = "Estrutura definida — clique para editar";
    fecha();
  };
  pop.querySelector(".pp-remover").onclick = () => {
    if (FIXOS[w]) delete FIXOS[w][d];
    btn.classList.remove("tem-nota");
    btn.title = "Estruturar esta sessão antes de gerar";
    fecha();
  };
}

function abrirNota(btn) {
  document.querySelector(".nota-pop")?.remove();
  const w = +btn.dataset.semana, d = +btn.dataset.dia;
  const abrev = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"];
  const pop = document.createElement("div");
  pop.className = "nota-pop";
  pop.innerHTML = `
    <label>Comentário — ${abrev[d]}, semana ${w} <small>(vai na descrição do treino)</small></label>
    <textarea rows="3" placeholder="ex.: fazer na pista; focar na cadência; correr com a turma...">${(NOTAS[w] || {})[d] || ""}</textarea>
    <div class="editor-acoes">
      <button class="primario mini np-salvar">Salvar</button>
      <button class="ghost mini np-remover">Remover</button>
      <button class="ghost mini np-fechar">Fechar</button>
    </div>`;
  document.body.appendChild(pop);
  const r = btn.getBoundingClientRect();
  pop.style.top = `${r.bottom + window.scrollY + 6}px`;
  pop.style.left = `${Math.min(r.left + window.scrollX, window.innerWidth - 340)}px`;
  pop.querySelector("textarea").focus();

  const fecha = () => pop.remove();
  pop.querySelector(".np-fechar").onclick = fecha;
  pop.querySelector(".np-salvar").onclick = () => {
    const t = pop.querySelector("textarea").value.trim();
    if (t) (NOTAS[w] ??= {})[d] = t;
    else if (NOTAS[w]) delete NOTAS[w][d];
    btn.classList.toggle("tem-nota", !!t);
    btn.title = t || "Comentário para esta sessão";
    fecha();
  };
  pop.querySelector(".np-remover").onclick = () => {
    if (NOTAS[w]) delete NOTAS[w][d];
    btn.classList.remove("tem-nota");
    btn.title = "Comentário para esta sessão";
    fecha();
  };
}

$("#inicio").onchange = () => montarDias(true);
$("#fim").onchange = () => montarDias(true);
// botão "Abrir ciclo até a prova": cria o ciclo na periodização do atleta
// (ATP do Lab) quando ainda não existe um para essa prova, mostra o plano para
// revisão e só então monta as semanas até o dia da prova
$("#prova-data").oninput = () => {
  $("#btn-ciclo-prova").disabled = !$("#prova-data").value;
};
$("#btn-ciclo-prova").onclick = async () => {
  const p = $("#prova-data").value;
  if (!p) return;
  if ($("#inicio").value && $("#inicio").value > p) {
    alert("O dia da prova é anterior ao início do bloco."); return;
  }
  const plano = DADOS && DADOS.periodizacao;
  const jaTem = plano && !plano.sem_prova && (plano.prova_data || "").slice(0, 10) === p;
  let criado = false;
  if (!jaTem) {
    const cal = ((DADOS && DADOS.provas) || []).find((x) => x.date === p);
    const nome = $("#prova-nome").value || (cal && cal.name)
      || (rotuloObjetivo() ? `Ciclo ${rotuloObjetivo().replace(/k$/, " km")}` : "Ciclo de prova");
    const seg = segundaDe(new Date());
    if (seg.toISOString().slice(0, 10) < new Date().toISOString().slice(0, 10)) seg.setDate(seg.getDate() + 7);
    carregando("criando o ciclo na periodização do atleta...");
    try {
      const r = await api("/api/periodizacao/criar", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          athlete_id: DADOS.athlete_id,
          nome, prova_data: p,
          inicio: $("#inicio").value || seg.toISOString().slice(0, 10),
          objetivo: objetivoMotor() || objetivoPorKm(cal && kmDaProva(cal)) || null,
          prova_km: kmObjetivo(), prova_nome: $("#prova-nome").value || (cal && cal.name) || null,
          provas: provasParaCiclo(),
          historico: historicoCompacto(),
          ...progressaoPedido(),
        }),
      });
      DADOS.periodizacao = r.periodizacao;
      pintarPlano();
      statusProgressao("Ciclo criado com essa progressão." + (r.aviso ? " " + r.aviso : ""));
      criado = true;
    } catch (err) {
      alert("Não deu para criar o ciclo na periodização: " + err.message); return;
    } finally { pronto(); }
  }
  $("#fim").value = p;
  if (!$("#inicio").value && DADOS.periodizacao) $("#inicio").value = DADOS.periodizacao.inicio;
  montarDias(true);
  sugerirBloco();
  $("#btn-ciclo-prova").textContent = criado
    ? `Ciclo criado na periodização ✓` : `Ciclo aberto até ${p.split("-").reverse().join("/")} ✓`;
  setTimeout(() => { $("#btn-ciclo-prova").textContent = "Abrir ciclo até a prova →"; }, 3500);
  // revisar o plano antes de descer para as semanas
  $("#plano-box").scrollIntoView({ behavior: "smooth", block: "start" });
};

// -- ciclismo: plano do ciclo em horas, sugestão da grade e envio ao motor ----
const FASES_CIC = ["Base", "Construção", "Específico", "Polimento", "Prova", "Recuperação"];
let CIC_PLANO = null;       // semanas do plano de ciclismo (vêm do servidor)
let CIC_MANUAL = {};        // {semana: {fase, horas, longao_h}} mexido à mão: vence o cálculo
let _cicTimer = null;
const numCampo = (id) => ($(id).value === "" ? null : +$(id).value);
function paramsCiclismo() { return { metrica: $("#cic-metrica").value, disciplina: $("#cic-disciplina").value }; }
function cicPedido() {
  const rc = numCampo("#cic-recup-cada");
  return { ...paramsCiclismo(), horas_ini: numCampo("#cic-horas-ini"), horas_pico: numCampo("#cic-horas-pico"),
    semana_min_h: numCampo("#cic-semana-min"), longao_ini_h: numCampo("#cic-longao-ini"),
    longao_pico_h: numCampo("#cic-longao-pico"), longao_min_h: numCampo("#cic-longao-min"),
    prova_data: $("#cic-prova-data").value || null, prova_nome: $("#cic-prova-nome").value || null,
    prova_h: numCampo("#cic-prova-h"), aumento: numCampo("#cic-aumento"), recup_cada: rc, sem_recup: rc === 0,
    recup_corte: numCampo("#cic-recup-corte"), manual: CIC_MANUAL };
}
// ponto de partida pelo histórico de pedal do atleta (só preenche o que não foi digitado)
function cicPadroes() {
  if (!DADOS) return;
  const b = (DADOS.historico && DADOS.historico.bike) || {};
  const mtb = $("#cic-disciplina").value === "mtb";
  const h0 = b.horas_semana ? Math.max(2, Math.round(b.horas_semana * 2) / 2) : 5;
  setAuto("#cic-horas-ini", h0);
  setAuto("#cic-horas-pico", Math.max(h0, Math.round(h0 * 1.4 * 2) / 2));
  const l0 = b.maior_pedal_h ? Math.max(1, Math.round(b.maior_pedal_h * 4) / 4) : 2;
  setAuto("#cic-longao-ini", l0);
  setAuto("#cic-longao-pico", Math.max(l0, mtb ? 3 : 4));
  // potência quando há FTP; senão FC de limiar; sem nenhum dos dois, percepção de esforço (Borg)
  if (!CAMPOS_MANUAIS.has("#cic-metrica")) $("#cic-metrica").value = DADOS.ftp ? "ftp" : DADOS.threshold_hr ? "fc" : "rpe";
  const t = [DADOS.ftp ? `FTP ${DADOS.ftp} W` : "sem FTP no TP", DADOS.threshold_hr ? `FC de limiar ${DADOS.threshold_hr} bpm` : "sem FC de limiar no TP"];
  $("#cic-limiares").textContent = t.join(" · ") + (b.horas_semana ? ` · pedalou ${String(b.horas_semana).replace(".", ",")} h/semana nas últimas 4 semanas` : "");
}
function faseCiclismoDaSemana(w) {
  const r = (CIC_PLANO || []).find((x) => x.semana === w);
  return r || { semana: w, fase: "Base", horas: null, longao_h: null, leve: false };
}
async function pintarPlanoCiclismo() {
  const box = $("#plano-ciclismo");
  if (!box || modalidade() !== "ciclismo" || !DADOS || !$("#inicio").value || !$("#fim").value) return;
  try {
    const r = await api("/api/ciclismo/plano", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ inicio: $("#inicio").value, fim: $("#fim").value, ciclismo: cicPedido() }) });
    CIC_PLANO = r.semanas;
  } catch (e) { $("#cic-status").textContent = "Não deu para montar o plano: " + e.message; return; }
  const fmt = (iso) => iso.split("-").reverse().slice(0, 2).join("/");
  const num = (v) => (v == null ? "" : v);
  box.innerHTML = `<div class="grade-wrap"><table class="zonas plano-edit"><tr><td>sem</td><td>início</td><td>fase</td><td>horas</td><td>longão</td><td></td></tr>` +
    CIC_PLANO.map((x) => {
      const m = CIC_MANUAL[x.semana] || {};
      return `<tr class="${x.manual ? "manual" : ""}"><td class="p-idx">${x.semana}</td><td class="p-data">${fmt(x.inicio)}</td>
        <td><select class="cic-plano${m.fase ? " manual" : ""}" data-k="fase" data-w="${x.semana}">${FASES_CIC.map((f) =>
          `<option ${f === x.fase ? "selected" : ""}>${f}</option>`).join("")}</select></td>
        <td><input class="cic-plano${m.horas ? " manual" : ""}" data-k="horas" data-w="${x.semana}" type="number" step="0.25" min="0" value="${num(x.horas)}"> h</td>
        <td><input class="cic-plano${m.longao_h != null ? " manual" : ""}" data-k="longao_h" data-w="${x.semana}" type="number" step="0.25" min="0" value="${num(x.longao_h)}" placeholder="—"> h</td>
        <td><small>${x.leve ? "leve" : ""}</small></td></tr>`;
    }).join("") + `</table></div>` +
    (Object.keys(CIC_MANUAL).length ? `<button type="button" class="ghost mini" id="cic-soltar">voltar tudo ao automático</button>` : "");
  document.dispatchEvent(new CustomEvent("fases-mudou"));
}
function agendarPlanoCiclismo() {
  if (modalidade() !== "ciclismo") return;
  clearTimeout(_cicTimer);
  _cicTimer = setTimeout(async () => {
    _cicTimer = null;
    await pintarPlanoCiclismo();
    reaplicarSugestaoCiclismo();
  }, 450);
}
function cicManual(w, k, v) {
  CIC_MANUAL[w] = { ...(CIC_MANUAL[w] || {}) };
  if (v === "" || v == null) delete CIC_MANUAL[w][k]; else CIC_MANUAL[w][k] = k === "fase" ? v : +v;
  if (!Object.keys(CIC_MANUAL[w]).length) delete CIC_MANUAL[w];
  agendarPlanoCiclismo();
}
// a fase mudou: os dias que o treinador não mexeu seguem a sugestão da nova fase
function reaplicarSugestaoCiclismo() {
  document.querySelectorAll("#dias select[data-dia]").forEach((sel) => {
    const w = +sel.dataset.semana, d = +sel.dataset.dia;
    if (eManual(w, d) || !sel.value) return;
    const novo = (sugestaoCiclismo(w, diasEscolhidos()) || {})[d];
    if (novo && novo !== sel.value) { sel.value = novo; sel.classList.toggle("ativo", true); }
  });
  document.dispatchEvent(new CustomEvent("fases-mudou"));
}
$("#plano-ciclismo").addEventListener("change", (e) => {
  const el = e.target.closest(".cic-plano"); if (!el) return;
  cicManual(+el.dataset.w, el.dataset.k, el.value);
});
$("#plano-ciclismo").addEventListener("click", (e) => {
  if (e.target.id !== "cic-soltar") return;
  CIC_MANUAL = {}; agendarPlanoCiclismo();
});
document.addEventListener("input", (e) => { if (e.target.classList.contains("cic-campo")) agendarPlanoCiclismo(); });
document.addEventListener("change", (e) => {
  if (e.target.classList.contains("cic-campo")) agendarPlanoCiclismo();
  if (e.target.id === "cic-metrica") CAMPOS_MANUAIS.add("#cic-metrica");
  if (e.target.id === "cic-disciplina") { cicPadroes(); agendarPlanoCiclismo(); }
});
// sessões de qualidade por fase e disciplina (a grade é só o ponto de partida)
// só tipos com ensaio em ciclistas entram sozinhos (sweet spot, over/under e XCO ficam para a escolha
// do treinador); estrada puxa limiar longo e longão, MTB puxa 30/15, sprint e torque em subida
const POOL_CIC = {
  estrada: { Base: ["cic_tempo", "cic_limiar"], "Construção": ["cic_vo2", "cic_limiar", "cic_3015"],
             "Específico": ["cic_limiar", "cic_vo2", "cic_tempo", "cic_3015"], Polimento: ["cic_vo2", "cic_3015"] },
  mtb: { Base: ["cic_tempo", "cic_torque"], "Construção": ["cic_vo2", "cic_3015", "cic_sprint", "cic_limiar"],
         "Específico": ["cic_3015", "cic_sprint", "cic_vo2", "cic_torque"], Polimento: ["cic_3015", "cic_vo2"] },
};
function sugestaoCiclismo(w, dias) {
  dias = (dias && dias.length ? dias : [1, 3, 5, 6]).slice().sort((a, b) => a - b);
  const p = faseCiclismoDaSemana(w), disc = $("#cic-disciplina").value === "mtb" ? "mtb" : "estrada";
  const mapa = {};
  const fimSemana = dias.filter((d) => d >= 5);
  const diaLongo = dias.length >= 2 ? (fimSemana.length ? Math.max(...fimSemana) : Math.max(...dias)) : null;
  const semLongao = ["Prova", "Recuperação"].includes(p.fase);
  if (diaLongo != null) mapa[diaLongo] = semLongao ? "cic_endurance" : "cic_longao";
  const restantes = dias.filter((d) => d !== diaLongo);
  let nQual = p.leve || semLongao ? 0 : ["Base", "Polimento"].includes(p.fase) ? 1 : 2;
  nQual = Math.min(nQual, Math.max(restantes.length - 1, restantes.length >= 2 ? 1 : 0));
  const pool = (POOL_CIC[disc][p.fase] || POOL_CIC[disc]["Construção"]);
  const off = (w - 1 + sementeAtleta()) % pool.length;
  const quals = [];
  for (let i = 0; quals.length < nQual && i < pool.length; i++) {
    const t = pool[(off + i) % pool.length];
    if (!quals.includes(t)) quals.push(t);
  }
  const distC = (a, b) => { const x = Math.abs(a - b); return Math.min(x, 7 - x); };
  const fortes = diaLongo != null && !semLongao ? [diaLongo] : [];
  const ordem = [...restantes].sort((a, b) => (diaLongo == null ? a - b : distC(b, diaLongo) - distC(a, diaLongo)));
  let qi = 0;
  ordem.forEach((d) => { if (qi < quals.length && !fortes.some((f) => distC(d, f) === 1)) { mapa[d] = quals[qi++]; fortes.push(d); } });
  let tec = disc === "mtb" && ["Base", "Construção"].includes(p.fase) && !p.leve;
  ordem.forEach((d) => {
    if (mapa[d]) return;
    if (tec) { mapa[d] = "cic_tecnica"; tec = false; }
    else mapa[d] = p.leve || p.fase === "Recuperação" ? "cic_leve" : "cic_endurance";
  });
  return mapa;
}
// bloco de ciclismo: nada de prova de corrida, km, teste de limiar ou plano de corrida no motor
function payloadCiclismo() {
  return { modalidade: "ciclismo", ciclismo: cicPedido(), so_forca: false, prova: null, prova_data: null,
    prova_nome: null, prova_km: null, provas: [], taper_ctl: false, teste_limiar: "nenhum", min_km_treino: null, max_km_treino: null,
    semana_max_km: null, semana_min: null, longo_max_km: null, longo_min_km: null, seguir_periodizacao: false };
}

// -- 3. previa -------------------------------------------------------------
let PREVIA_SEM_ROLAR = false;
$("#gerar").onclick = () => gerarPrevia();
async function gerarPrevia() {
  const th = thresholdEscolhido();
  const soForca = modalidade() === "forca";
  const soCiclismo = modalidade() === "ciclismo";
  if (!th && !soForca && !soCiclismo) { alert("Defina um pace de limiar valido (ex: 6:13)."); return; }

  const semanas_tipos = {};
  document.querySelectorAll("#dias select[data-dia]").forEach((s) => {
    semanas_tipos[s.dataset.semana] ??= {};
    if (s.value) semanas_tipos[s.dataset.semana][s.dataset.dia] = s.value;
  });
  const tempo_max = {};
  document.querySelectorAll(".dia-max").forEach((el) => {
    if (el.value) tempo_max[el.dataset.dia] = parseFloat(el.value);
  });
  const semanas_forca = {};
  document.querySelectorAll("#dias select.forca2").forEach((s2) => {
    if (s2.value) (semanas_forca[s2.dataset.semana2] ??= {})[s2.dataset.dia2] = s2.value;
  });

  const orientacoes = orientacoesPedido();
  carregando(orientacoes && !orientacoes.regras ? "lendo as orientações e montando o bloco..." : "montando o bloco...");
  try {
    PREVIA = await api("/api/previa", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        athlete_id: DADOS.athlete_id, threshold_ms: th,
        inicio: $("#inicio").value, fim: $("#fim").value,
        semanas_tipos,
        semanas_forca,
        orientacoes,
        forca_objetivo: forcaObjetivo(),
        tempo_max,
        notas: NOTAS,
        fixos: FIXOS,
        fases: FASES,
        manuais: manuaisPayload(),
        prova: objetivoMotor() || null,
        prova_data: $("#prova-data").value || null,
        prova_nome: $("#prova-nome").value || null,
        prova_km: kmObjetivo(),
        provas: provasDoBloco(),
        taper_ctl: $("#taper-ctl") ? $("#taper-ctl").checked : true,
        teste_limiar: $("#teste-limiar") ? $("#teste-limiar").value : "auto",
        min_km_treino: $("#min-km").value ? parseFloat($("#min-km").value) : null,
        max_km_treino: $("#max-km").value ? parseFloat($("#max-km").value) : null,
        semana_max_km: $("#semana-max").value ? parseFloat($("#semana-max").value) : null,
        longo_max_km: $("#longo-max").value ? parseFloat($("#longo-max").value) : null,
        longo_min_km: $("#longo-min").value ? parseFloat($("#longo-min").value) : null,
        base: {
          longo_km: parseFloat($("#b-longo").value),
          limiar_min: parseFloat($("#b-limiar").value),
          vo2_seg: parseFloat($("#b-vo2").value),
          rodagem_min: parseFloat($("#b-rodagem").value),
        },
        ...progressaoPedido(),               // campo vazio vai com o padrão (10%, a cada 4, 25%)
        progressao_pct: $("#progressao").value === "" ? 10 : +$("#progressao").value,
        seguir_periodizacao: !!(DADOS.periodizacao &&
          $("#seguir-plano") && $("#seguir-plano").checked),
        ...(soForca ? payloadSoForca() : {}),
        ...(soCiclismo ? payloadCiclismo() : {}),
      }),
    });
    if (PREVIA.orientacoes) { ORIENT = PREVIA.orientacoes; pintarOrientacoes(); }
    pintarPrevia();
    $("#publicar").disabled = !(PREVIA.sessoes && PREVIA.sessoes.length);   // apontamentos não bloqueiam
    $("#sec-previa").classList.remove("oculto");
    if (!PREVIA_SEM_ROLAR) $("#sec-previa").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    alert("Erro ao gerar: " + e.message);
  } finally { pronto(); }
};

// bloco só de força: nada de prova, volume, teste de limiar ou plano de corrida no motor
function payloadSoForca() {
  const fases = {};
  for (let w = 1; w <= nSemanasPeriodo(); w++) fases[w] = { forca: faseForcaDaSemana(w) };
  return { so_forca: true, fases, prova: null, prova_data: null, prova_nome: null, prova_km: null, provas: [],
    taper_ctl: false, teste_limiar: "nenhum", min_km_treino: null, max_km_treino: null, semana_max_km: null, semana_min_km: null,
    longo_max_km: null, longo_min_km: null, semana_min: null, longo_min: null, sem_recuperacao: true, seguir_periodizacao: false, semanas_forca: {} };
}

// planejado que este bloco substitui: mesmo dia e mesmo tipo de treino. Vale depois de
// mover, trocar ou excluir na prévia: força nunca apaga a corrida que já está no plano
function conflitosValidos() {
  return (PREVIA.conflitos || []).filter((c) =>
    PREVIA.sessoes.some((s) => s.data === c.data &&
      (c.esporte ? esporteDe(s) === c.esporte : !!s.forca === !!c.forca)));
}
function esporteDe(s) { return s.forca ? "forca" : s.bike ? "bike" : "corrida"; }

function pintarPrevia() {
  $("#resumo-semanas").classList.add("oculto");
  const av = $("#avisos-seq");
  if (av) {
    // orientações do treinador ficam à vista; os ajustes de montagem, recolhidos
    const ori = (PREVIA.avisos || []).filter((x) => x.startsWith("Orientação: "));
    const lista = (PREVIA.avisos || []).filter((x) => !x.startsWith("Orientação: "));
    av.classList.toggle("oculto", !lista.length && !ori.length);
    av.innerHTML = (ori.length ? `<div class="orientacoes-aplicadas"><b>Orientações aplicadas</b><ul>${ori.map((x) =>
        `<li>${x.slice(12)}</li>`).join("")}</ul></div>` : "") +
      (lista.length ? `<details><summary>${lista.length} ajuste${lista.length > 1 ? "s" : ""} na sequência dos dias (regras de montagem)</summary><ul>${lista.map((x) => `<li>${x}</li>`).join("")}</ul></details>` : "");
  }
  const pm = $("#pmc-linha");
  if (pm) {
    const p = PREVIA.pmc;
    pm.classList.toggle("oculto", !p);
    if (p) pm.innerHTML = `<svg><use href="#ic-bandeira"/></svg> ${p.resumo}` +
      (p.data_ref ? ` <small>· CTL/ATL do Lab em ${p.data_ref.slice(8, 10)}/${p.data_ref.slice(5, 7)}</small>` : "");
  }

  const c = $("#conflitos");
  const validos = conflitosValidos();
  if (validos.length) {
    const n = validos.length;
    c.className = "aviso conflitos";
    c.innerHTML = `<details><summary>${n} treino${n > 1 ? "s" : ""} já planejado${n > 1 ? "s" : ""} nessas datas — as células marcadas em âmbar serão substituídas se "apagar os planejados" ficar marcado</summary>` +
      `<ul>${validos.map((x) => `<li>${x.data.split("-").reverse().join("/")} · ${x.titulo}</li>`).join("")}</ul></details>`;
    c.classList.remove("oculto");
  } else c.classList.add("oculto");

  const abrev = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"];
  const fmt = (iso) => iso.split("-").reverse().slice(0, 2).join("/");
  const infoSem = Object.fromEntries((PREVIA.semanas || []).map((w) => [w.semana, w]));

  const porSem = {};
  PREVIA.sessoes.forEach((s, i) => (porSem[s.semana] ??= []).push([s, i]));

  $("#lista-treinos").innerHTML = Object.keys(porSem)
    .sort((a, b) => a - b).map((w) => {
      const sess = porSem[w];
      const info = infoSem[w] || { km: 0, minutos: 0 };
      const porDia = {};
      sess.forEach(([s, i]) => {
        (porDia[(new Date(s.data + "T12:00").getDay() + 6) % 7] ??= []).push([s, i]);
      });
      // segunda-feira desta semana, para datar as celulas vazias
      const d0 = new Date(sess[0][0].data + "T12:00");
      d0.setDate(d0.getDate() - ((d0.getDay() + 6) % 7));
      const celulas = abrev.map((a, d) => {
        if (!porDia[d]) {
          const dt = new Date(d0); dt.setDate(dt.getDate() + d);
          const iso = dt.toISOString().slice(0, 10);
          return `<div class="tcell vazio add" data-data="${iso}" data-semana="${w}"
            data-recup="${info.recuperacao ? 1 : 0}" data-fase="${info.fase || ""}"
            title="Adicionar treino em ${a} ${iso.slice(8, 10)}/${iso.slice(5, 7)}">
            <span>${a} ${iso.slice(8, 10)}/${iso.slice(5, 7)}</span><em aria-hidden="true"></em></div>`;
        }
        const cartoes = porDia[d].map(([s, i]) => {
        const lim = s.tempo_max
          ? ` <span class="${s.minutos > s.tempo_max ? "estourou" : "no-limite"}">· lim ${s.tempo_max}'</span>`
          : "";
        const exs = (s.forca && s.forca.lista && s.forca.lista.length)
          ? `<div class="exs">${s.forca.lista.map((b, bi) => `<div class="bl"><small>${b.bloco}</small>` +
              b.exercicios.map((e, ei) => `<span class="ex-card" data-i="${i}" data-b="${bi}" data-e="${ei}" title="Trocar na biblioteca do TrainingPeaks">${e.nome} <i>${e.series}</i></span>`).join("") + `</div>`).join("")}</div>` +
            `<button type="button" class="ghost mini ver-exs" data-i="${i}">todos os exercícios</button>`
          : `<div class="grafico gforca"><svg><use href="#ic-forca"/></svg></div>`;
        const corpo = s.forca
          ? `<div class="num">${s.forca.exercicios} exercícios · ${s.forca.series} séries · ${s.minutos} min</div>${exs}`
          : `<div class="num">${s.bike ? "" : s.km + " km · "}${s.minutos} min${s.tss ? ` · TSS ${s.tss}` : ""}${lim}</div>${svg(s.desenho)}`;
        return `<div class="treino compacta ${s.recuperacao ? "recup" : ""}" data-i="${i}" draggable="true" title="Arraste para outro dia">
          <small class="tdia">${a} ${s.data.slice(8, 10)}/${s.data.slice(5, 7)}</small>
          <b>${s.titulo}${s.fixado ? ' <span class="tag-edit">definido</span>' : ""}${s.editado ? ' <span class="tag-edit">editado</span>' : s.ajustado ? ' <span class="tag-edit">ajustado</span>' : ""}${s.movido ? ' <span class="tag-edit">movido</span>' : ""}${s.teste ? ' <span class="tag-edit teste">teste</span>' : ""}</b>
          ${s.nota ? `<div class="nota-prev" title="${s.nota.replace(/"/g, "&quot;")}"><svg><use href="#ic-nota"/></svg> ${s.nota.length > 46 ? s.nota.slice(0, 46) + "…" : s.nota}</div>` : ""}
          ${s.forca ? corpo : `<div class="num">${s.bike ? "" : s.km + " km · "}${s.minutos} min${s.tss ? ` · TSS ${s.tss}` : ""}${lim}</div>${svg(s.desenho)}`}
          <div class="card-acoes"><button class="ghost trocar" data-i="${i}" title="${s.forca ? "Editar os exercícios deste dia" : "Trocar ou editar este treino"}"><svg><use href="#ic-editar"/></svg>${s.forca ? "exercícios" : "editar"}</button><button class="ghost excluir" data-i="${i}" title="Excluir este treino da prévia" aria-label="Excluir este treino">×</button></div>
        </div>`;
        }).join("");
        const dataDia = porDia[d][0][0].data;
        const conflito = validos.some((x) => x.data === dataDia);
        return `<div class="tcell ${conflito ? "conflito" : ""} ${porDia[d].length > 1 ? "duplo" : ""}" data-data="${dataDia}" data-semana="${w}"
          data-recup="${info.recuperacao ? 1 : 0}" data-fase="${info.fase || ""}">${cartoes}
          <button type="button" class="ghost mini add-mais" title="Adicionar outro treino neste dia">+ treino</button></div>`;
      }).join("");

      const v = info.variacao;
      const vtxt = v == null ? "" :
        `<span class="var ${v >= 0 ? "sobe" : "desce"}">${v > 0 ? "+" : ""}${v}%</span>`;
      const rot = info.fase || (info.recuperacao ? "recuperação" : "");
      return `<div class="sem-linha ${info.recuperacao ? "recup" : ""}">
        <div class="sem-cab">
          <b>Semana ${w}</b>
          <span>${fmt(sess[0][0].data)} – ${fmt(sess[sess.length - 1][0].data)}</span>
          ${rot ? `<span class="fase">${rot}</span>` : ""}
          <span class="tot">${modalidade() === "ciclismo"
            ? `bike ${fmtHoras(info.min_bike || 0)}${info.horas_plano ? ` de ${String(info.horas_plano).replace(".", ",")} h no plano` : ""} · TSS ${info.tss || 0}`
            : `${info.km ? `${info.km} km · ` : ""}${fmtHoras(info.minutos)}`}</span>
          ${(() => {
            const runs = sess.map(([x]) => x).filter(ehCorridaDoTeto);
            const lgs = runs.filter((x) => /^longo/.test(x.tipo || "") || /^(Longo|Rodagem longa)/.test(x.titulo || ""));
            if (!lgs.length) return "";
            const lg = lgs.reduce((a, b) => (b.km > a.km ? b : a));
            return runs.some((x) => x !== lg && x.km >= lg.km)
              ? `<span class="teto estourou" title="Algum treino da semana tem mais km que o longo">longo não é o maior</span>` : "";
          })()}
          ${info.teto != null ? `<span class="teto ${info.km_corrida > info.teto + 0.05 ? "estourou" : ""}" title="Corrida da semana (sem contar a prova) e o volume proposto">corrida ${info.km_corrida ?? 0} / ${info.teto} km</span>` : ""}
          ${vtxt}
          ${sess.some(([x]) => x.forca) && porSem[+w + 1] ? `<button type="button" class="ghost mini copiar-forca-prev" data-w="${w}" title="Copiar as sessões de força desta semana para a semana ${+w + 1}">copiar força para a semana ${+w + 1}</button>` : ""}
        </div>
        <div class="sem-grid7">${celulas}</div>
      </div>`;
    }).join("");
}

const TIPOS_PROVA = ["prova", "prova_b", "prova_c", "pre_prova"];
function ehCorridaDoTeto(s) { return !s.forca && !s.bike && (s.km || 0) > 0 && !TIPOS_PROVA.includes(s.tipo); }
function recalcSemanas() {
  const tetos = PREVIA.tetos || {};
  const por = {};
  PREVIA.sessoes.forEach((s) => {
    const w = (por[s.semana] ??= { semana: s.semana, km: 0, minutos: 0, km_corrida: 0,
      recuperacao: s.recuperacao, sessoes: 0, teto: tetos[s.semana] ?? null });
    w.km += s.km; w.minutos += s.minutos; w.sessoes++;
    w.tss = (w.tss || 0) + (s.tss || 0);
    if (s.bike) w.min_bike = (w.min_bike || 0) + s.minutos;
    const pc = (PREVIA.plano_ciclismo || []).find((r) => r.semana === s.semana);
    if (pc) { w.horas_plano = pc.horas; w.recuperacao = !!pc.leve; }
    if (ehCorridaDoTeto(s)) w.km_corrida += s.km;
    if (s.fase && (!w.fase || (w.faseForca && !s.forca))) { w.fase = s.fase; w.faseForca = !!s.forca; }
  });
  const arr = Object.values(por).sort((a, b) => a.semana - b.semana);
  let ant = null;
  arr.forEach((w) => {
    w.km = Math.round(w.km * 10) / 10;
    w.km_corrida = Math.round(w.km_corrida * 10) / 10;
    w.variacao = (ant == null || ant === 0 || w.km === 0)
      ? null : Math.round((w.km / ant - 1) * 100);
    ant = w.km;
  });
  PREVIA.semanas = arr;
  PREVIA.total_km = Math.round(PREVIA.sessoes.reduce((t, x) => t + (x.km || 0), 0) * 10) / 10;
}

// -- editor de sessao --------------------------------------------------------
// campos por tipo: [chave, rotulo, {def | sel: [[valor, rotulo]] | chk}]
const ESCADA_OPTS = [[0,"2k + 3x1k"],[1,"4k + 2k + 1k"],[2,"4k + 4x1k"],[3,"4x1k + 4k"],
  [4,"3k + 2x1,5k + 3x750m"],[5,"2x2k"],[6,"3x2k"],[7,"2x3k"]];
const LV_OPTS = [[0,"5x1k + 6x200m"],[1,"2x2k + 7x400m"],[2,"2x2k + 6x800m"],
  [3,"8x200m + 2x1600m (invertido)"],[4,"4x1k + 5x400m"],[5,"6x300m + 3x1k (invertido)"]];
const PIR_OPTS = [[0,"1'-2'-3'-2'-1'"],[1,"1'-2'-3'-3'-2'-1'"],[2,"2'-3'-4'-3'-2'"],
  [3,"1'-2'-3'-4'-3'-2'-1'"]];

const CAMPOS = {
  limiar: [["series","séries",3],["minutos","min/bloco",6],["por_distancia","por distância",{chk:0}]],
  limiar_prefadiga: [["series","séries",3],["minutos","min/bloco",6],
    ["pre_reps","estímulos",4],["pre_valor","estímulo",200],
    ["pre_unidade","unid.",{sel:[["m","metros"],["s","segundos"]]}],
    ["por_distancia","limiar por distância",{chk:1}]],
  vo2max: [["tiros","tiros",6],["segundos","seg/tiro",60],["por_distancia","por distância",{chk:0}]],
  longo_continuo: [["km","km",8]],
  longo_trocas: [["km","km",9],["blocos","trocas",4],["forte_m","forte (m)",800],["leve_m","leve (m)",600]],
  longo_bloco: [["km","km",10],["final_forte","final forte",{chk:0}]],
  longo_progressivo: [["km","km",12]],
  longo_alternado: [["km","km",14],["mod_m","moderado (m)",1000],["leve_m","leve (m)",1000]],
  longo_surges: [["km","km",12],["surges","surges (0=auto)",0]],
  bike_rodagem: [["minutos","minutos",60]],
  bike_intervalado: [["sets","sets",5],["forte_min","forte (min)",4],["leve_min","leve (min)",3]],
  bike_longa: [["minutos","minutos",120],["bloco_moderado","bloco moderado",{chk:1}]],
  rodagem: [["minutos","minutos",40],["strides","strides",4],["por_distancia","por distância",{chk:0}]],
  rodagem_strides: [["minutos","minutos",40],["strides","strides",4],["por_distancia","por distância",{chk:0}]],
  rodagem_leve: [["minutos","minutos",40],["por_distancia","por distância",{chk:0}]],
  fartlek: [["blocos","blocos",6],["forte_s","forte (seg)",120],["leve_s","leve (seg)",120],["por_distancia","por distância",{chk:0}]],
  progressivo: [["km","km",7]],
  escada_limiar: [["variante","escada",{sel:ESCADA_OPTS}]],
  segundo_limiar: [["series","séries",5],["minutos","min/bloco",3],["por_distancia","por distância",{chk:0}]],
  limiar_vo2: [["variante","combinação",{sel:LV_OPTS}]],
  teste_limiar: [],
  ritmo_prova: [["reps","blocos",4],["metros","metros/bloco",1000]],
  piramide: [["variante","pirâmide",{sel:PIR_OPTS}]],
  corre_anda: [["blocos","blocos",8],["corre_min","corre (min)",4],["anda_min","anda (min)",1]],
  over_under: [["sets","sets",4],["over_s","over (seg)",300],["under_s","under (seg)",300]],
  forca: [["template","sessão",{sel:[["forca_a","Força A — base geral"],
    ["forca_b","Força B — unilateral"],["forca_c","Força C — potência"],
    ["adapt_a","Adaptação A — geral"],["adapt_b","Adaptação B — unilateral"],
    ["max_a","Força máxima A"],["max_b","Força máxima B"],
    ["pot_a","Potência A — saltos"],["pot_b","Potência B — mista"],
    ["forca_corrida","Força para corrida"],["forca_hiper","Hipertrofia"],
    ["forca_bruta","Força bruta"],["forca_precomp","Pré-competitivo"],
    ["inferior_a","Força · membros inferiores A"],["inferior_b","Força · membros inferiores B"],
    ["superior_a","Força · membros superiores A"],["superior_b","Força · membros superiores B"],
    ["empurrar_a","Força · empurrar A"],["empurrar_b","Força · empurrar B"],
    ["puxar_a","Força · puxar A"],["puxar_b","Força · puxar B"],
    ["core_a","Core A · anti-extensão e anti-rotação"],["core_b","Core B · estabilidade e quadril"],
    ["plio_a","Força · pliometria A"],["plio_b","Força · pliometria B"],
    ["estab_a","Força · estabilidade de core A"],["estab_b","Força · estabilidade de core B"],
    ["gluteo_a","Força · ativação de glúteo A"],["gluteo_b","Força · ativação de glúteo B"],
    ["ativ_sup_a","Força · ativação de membros superiores A"],["ativ_sup_b","Força · ativação de membros superiores B"],
    ["descarga","Descarga — leve"]]}]],
};
Object.assign(CAMPOS, {
  cic_endurance: [["minutos","minutos",90]], cic_leve: [["minutos","minutos",45]],
  cic_longao: [["minutos","minutos",180],["final_min","bloco final (min)",0]],
  cic_tempo: [["blocos","blocos",5],["minutos","min/bloco",12]], cic_sweet: [["blocos","blocos",3],["minutos","min/bloco",12]],
  cic_limiar: [["blocos","blocos",2],["minutos","min/bloco",20]],
  cic_over_under: [["sets","séries",3],["ciclos","ciclos",3],["over_min","acima (min)",1],["under_min","abaixo (min)",2]],
  cic_vo2: [["reps","tiros",4],["minutos","min/tiro",8]], cic_3015: [["series","séries",3],["reps","repetições",13]],
  cic_sprint: [["reps","sprints",6],["segundos","segundos",30]], cic_torque: [["reps","blocos",6],["minutos","min/bloco",5]],
  cic_xco: [["series","séries",3],["reps","esforços",6],["forte_s","forte (s)",40],["firme_s","firme (s)",80]],
  cic_tecnica: [["minutos","minutos",75]], cic_teste_ftp: [],
});
const FORCA_TIPOS = ["forca","forca_inferior","forca_superior","forca_empurrar","forca_puxar","forca_core",
  "forca_pliometria","forca_estab_core","forca_ativ_gluteo","forca_ativ_superiores"];
FORCA_TIPOS.forEach((t) => { CAMPOS[t] = CAMPOS.forca; });
// modalidade do bloco (Bloco): corrida | mista | forca — filtra os treinos da grade e da sugestão
function modalidade() { return (document.querySelector('input[name="modalidade"]:checked') || {}).value || "mista"; }
// objetivo do treino de força do bloco: performance esportiva | hipertrofia
function forcaObjetivo() { return (document.querySelector('input[name="forca-objetivo"]:checked') || {}).value || "performance"; }
// trocou a fase de uma semana ou o objetivo com a prévia aberta: refaz a prévia com as
// séries novas. Prévia com treino editado à mão não é refeita por cima: fica o aviso
let _previaForcaT = null;
document.addEventListener("change", (e) => {
  if (!e.target.matches('.plano-forca-sel, .forca-sel, input[name="forca-objetivo"]')) return;
  if (!PREVIA || !PREVIA.sessoes || !PREVIA.sessoes.some((s) => s.forca)) return;
  clearTimeout(_previaForcaT);
  _previaForcaT = setTimeout(async () => {
    const st = $("#forca-status");
    if (PREVIA.sessoes.some((s) => s.editado)) {
      if (st) { st.textContent = "A prévia tem treino editado à mão: gere de novo para levar as séries novas."; st.classList.remove("oculto"); }
      return;
    }
    if (st) st.classList.add("oculto");
    PREVIA_SEM_ROLAR = true;
    try { await gerarPrevia(); } finally { PREVIA_SEM_ROLAR = false; }
  }, 500);
});
document.addEventListener("change", (e) => {
  if (e.target.name === "modalidade") {
    const g = document.getElementById("grupo-forca-obj");
    if (g) g.classList.toggle("oculto", modalidade() === "corrida");
  }
});
function tiposVisiveis() {
  const m = modalidade();
  const cic = (v) => v.startsWith("cic_");
  return TIPOS.filter(([v]) => !v || (m === "ciclismo" ? cic(v) || FORCA_TIPOS.includes(v)
    : !cic(v) && (m === "mista" || (m === "forca") === FORCA_TIPOS.includes(v))));
}

function tipoConcreto(s) {
  if (s.forca) return "forca";
  // 'longo' generico vira o modelo concreto que foi usado, pelo titulo
  if (s.tipo !== "longo") return CAMPOS[s.tipo] ? s.tipo : "limiar";
  if (/final forte/.test(s.titulo) || /em bloco/.test(s.titulo)) return "longo_bloco";
  if (/fortes/.test(s.titulo)) return "longo_trocas";
  return "longo_continuo";
}

function camposHtml(tipo, sessao) {
  return (CAMPOS[tipo] || []).map(([k, rot, spec]) => {
    const obj = typeof spec === "object" && spec !== null;
    if (obj && spec.sel) {
      return `<label>${rot} <select data-k="${k}">` +
        spec.sel.map(([v, t]) => `<option value="${v}">${t}</option>`).join("") +
        `</select></label>`;
    }
    if (obj && "chk" in spec) {
      const on = spec.chk || (sessao && /final forte/.test(sessao.titulo) && k === "final_forte");
      return `<label class="check">${rot} <input type="checkbox" data-k="${k}" ${on ? "checked" : ""}></label>`;
    }
    let def = spec;
    if (sessao && (k === "km")) def = sessao.km;
    return `<label>${rot} <input type="number" data-k="${k}" value="${def}" step="any"></label>`;
  }).join("");
}

// classes de passo, com rotulo em PT
const CLASSES = [["warmUp", "aquecimento"], ["active", "trabalho"],
                 ["rest", "recuperação"], ["coolDown", "desaquecimento"]];
let BIB_PASTAS = null;      // cache das pastas da biblioteca do TP

function blocosDaSessao(s) {
  // estrutura nativa -> blocos editaveis (espelho do _blocos_de_native)
  return (s.structured_workout.structure || []).map((b) => ({
    rep: b.length?.unit === "repetition" ? b.length.value : 1,
    passos: (b.steps || []).map((p) => {
      const t = (p.targets || [{}])[0];
      let lo = t.minValue || 0, hi = t.maxValue || 0;
      const classe = p.intensityClass || "active";
      if (hi <= 1) [lo, hi] = classe === "rest" || classe === "coolDown" ? [40, 60] : [72, 80];
      if (lo <= 1) lo = Math.max(hi - 10, 40);
      // exibe na unidade mais legivel: min/km quando o valor e redondo
      let valor = p.length?.value ?? 60;
      let unidade = p.length?.unit === "meter" ? "m" : "s";
      if (unidade === "s" && valor >= 60 && valor % 60 === 0) {
        unidade = "min"; valor = valor / 60;
      } else if (unidade === "m" && valor >= 1000 && valor % 100 === 0) {
        unidade = "km"; valor = valor / 1000;
      }
      return { nome: p.name || "Passo", valor, unidade, lo, hi, classe };
    }),
  }));
}

// zonas do aluno para a lista do editor: [{rot, lo, hi}] (TP: as 10 zonas; sem TP: as intenções)
function zonaOpcoes() {
  if (!DADOS) return [];
  if (DADOS.zonas_tp && DADOS.zonas_tp.length && DADOS.zonas_tp[0].pct_lo != null) {
    const usos = {};
    (DADOS.zonas_intents || []).forEach((z) => {
      const n = parseInt(z.zona.slice(1)); (usos[n] = usos[n] || []).push(z.nome);
    });
    return DADOS.zonas_tp.map((z) => ({
      rot: `Z${z.num} ${z.label}${usos[z.num] ? " · " + [...new Set(usos[z.num])].join("/") : ""} · ${z.pace}`,
      lo: z.pct_lo, hi: z.pct_hi,
    }));
  }
  const op = (document.querySelector('input[name="limiar"]:checked') || {}).value;
  const tabela = op === "estimado" ? DADOS.zonas_estimado : DADOS.zonas_cadastrado;
  return (tabela || []).map((z) => {
    const m = /([\d.]+)-([\d.]+)%/.exec(z.pct || "");
    return m ? { rot: `${z.nome} · ${z.pace}`, lo: +m[1], hi: +m[2] } : null;
  }).filter(Boolean);
}
function zonaSelectHtml(lo, hi) {
  const ops = zonaOpcoes();
  const igual = (a, b) => Math.abs(a - b) < 0.6;
  const atual = ops.findIndex((o) => igual(o.lo, lo) && igual(o.hi, hi));
  return `<select class="p-zona" title="zona do aluno (preenche a faixa; dá para ajustar à mão)">` +
    `<option value="">manual</option>` +
    ops.map((o, k) => `<option value="${k}" ${k === atual ? "selected" : ""}>${o.rot}</option>`).join("") +
    `</select>`;
}

function passosHtml(blocos) {
  return blocos.map((b, bi) => `
    <div class="ed-bloco" data-b="${bi}">
      <div class="ed-bloco-cab">
        <label>Repete <input type="number" class="ed-rep" value="${b.rep}" min="1" step="1"> vez(es)</label>
        <button class="ghost mini ed-add-passo" title="Adicionar passo neste bloco">+ passo</button>
        <button class="ghost mini ed-del-bloco" title="Remover bloco">× bloco</button>
      </div>
      ${b.passos.map((p, pi) => `
      <div class="ed-passo" data-p="${pi}">
        <input class="p-nome" value="${p.nome.replace(/"/g, "&quot;")}" title="nome do passo">
        <input class="p-valor" type="number" value="${p.valor}" step="any" min="1">
        <select class="p-unidade">
          <option value="s" ${p.unidade === "s" ? "selected" : ""}>seg</option>
          <option value="min" ${p.unidade === "min" ? "selected" : ""}>min</option>
          <option value="m" ${p.unidade === "m" ? "selected" : ""}>metros</option>
          <option value="km" ${p.unidade === "km" ? "selected" : ""}>km</option>
        </select>
        ${zonaSelectHtml(p.lo, p.hi)}
        <span class="p-faixa"><input class="p-lo" type="number" value="${p.lo}" step="any"> –
          <input class="p-hi" type="number" value="${p.hi}" step="any"> %</span>
        <select class="p-classe">
          ${CLASSES.map(([v, t]) => `<option value="${v}" ${p.classe === v ? "selected" : ""}>${t}</option>`).join("")}
        </select>
        <button class="ghost mini ed-del-passo" title="Remover passo">×</button>
      </div>`).join("")}
    </div>`).join("") +
    `<button class="ghost mini" id="ed-add-bloco">+ bloco</button>`;
}

function lerBlocosDoDom(cont) {
  return [...cont.querySelectorAll(".ed-bloco")].map((bl) => ({
    rep: +bl.querySelector(".ed-rep").value || 1,
    passos: [...bl.querySelectorAll(".ed-passo")].map((p) => ({
      nome: p.querySelector(".p-nome").value || "Passo",
      valor: +p.querySelector(".p-valor").value || 60,
      unidade: p.querySelector(".p-unidade").value,
      lo: +p.querySelector(".p-lo").value || 60,
      hi: +p.querySelector(".p-hi").value || 70,
      classe: p.querySelector(".p-classe").value,
    })),
  })).filter((b) => b.passos.length);
}

// ---- exercícios da sessão de força: troca, ajusta, inclui e tira, dia a dia, na prévia ----
const TIPOS_BLOCO = [["WarmUp", "Aquecimento / ativação"], ["Superset", "Superset"], ["Circuit", "Circuito"],
  ["SingleExercise", "Exercício único"], ["CoolDown", "Desaquecimento"]];
const UNIDADES_EX = [["Reps", "reps"], ["RepsPerSide", "reps/lado"], ["Duration", "seg"], ["DistanceMeters", "metros"]];
let BIB_EX = null;          // espelho da biblioteca de exercícios do TP
const DET_EX = {};          // vídeo, instruções e colunas de cada exercício já aberto
const MUSCULOS_PT = { Abs: "Abdômen", Biceps: "Bíceps", Calves: "Panturrilha", Chest: "Peito", Forearms: "Antebraço",
  Glute: "Glúteo", Hamstrings: "Posterior de coxa", LowerBack: "Lombar", Quads: "Quadríceps", Shoulders: "Ombro",
  Triceps: "Tríceps", UpperBack: "Costas" };
const semAcento = (t) => String(t || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const html = (t) => String(t ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const rotMusculo = (m) => MUSCULOS_PT[String(m).replace(/\s/g, "")] || m;
async function carregarBibEx() {
  if (BIB_EX) return BIB_EX;
  const r = await api("/api/forca/exercicios");
  r.exercicios.forEach((e) => {
    e.busca = semAcento([e.nome, ...e.alt, ...e.prim, ...e.sec, ...[...e.prim, ...e.sec].map(rotMusculo)].join(" "));
    e.chave = semAcento(e.nome);
  });
  r.exercicios.sort((a, b) => (a.chave < b.chave ? -1 : 1));
  BIB_EX = r;
  return r;
}
async function detalheEx(id) {
  if (!DET_EX[id]) DET_EX[id] = await api(`/api/forca/exercicio/${id}`);
  return DET_EX[id];
}
// A biblioteca do TrainingPeaks espelhada: abre ao clicar em qualquer exercício.
// aoEscolher(exercicio) recebe {id, nome, parametros}
function abrirBibliotecaEx(atual, aoEscolher) {
  document.querySelector(".bibex-fundo")?.remove();
  const voltaFoco = document.activeElement;
  const f = document.createElement("div");
  f.className = "bibex-fundo";
  f.innerHTML = `<div class="bibex" role="dialog" aria-modal="true" aria-label="Biblioteca de exercícios do TrainingPeaks">
    <div class="bibex-cab">
      <div><h2>Biblioteca do TrainingPeaks</h2><small>${atual ? `Trocando ${html(atual)}` : "Novo exercício"}</small></div>
      <button type="button" class="ghost bibex-fecha" aria-label="Fechar">×</button>
    </div>
    <input class="bibex-busca" type="search" placeholder="Buscar por nome, apelido ou músculo" aria-label="Buscar exercício" autocomplete="off">
    <div class="bibex-filtros">
      <div class="bibex-origem" role="group" aria-label="Origem">
        <button type="button" class="ativo" data-o="">Todos</button><button type="button" data-o="meu">Meus exercícios</button><button type="button" data-o="tp">Do TrainingPeaks</button>
      </div>
      <select class="bibex-musculo" aria-label="Grupo muscular"><option value="">Todos os músculos</option></select>
      <span class="bibex-n" aria-live="polite"></span>
    </div>
    <div class="bibex-lista"><p class="dica">carregando a biblioteca…</p></div>
  </div>`;
  document.body.appendChild(f);
  const lista = f.querySelector(".bibex-lista"), busca = f.querySelector(".bibex-busca"), selM = f.querySelector(".bibex-musculo");
  let origem = "", filtrados = [];
  const fechar = () => { f.remove(); document.removeEventListener("keydown", tecla); voltaFoco?.focus?.(); };
  const tecla = (e) => { if (e.key === "Escape") { e.stopPropagation(); fechar(); } };
  document.addEventListener("keydown", tecla);
  f.addEventListener("mousedown", (e) => { if (e.target === f) fechar(); });
  f.querySelector(".bibex-fecha").onclick = fechar;
  const usar = async (e, botao) => {
    if (botao) { botao.disabled = true; botao.textContent = "abrindo…"; }
    let parametros = null;
    try { parametros = (await detalheEx(e.id)).parametros; } catch (err) { console.warn("detalhe do exercício:", err); }
    fechar();
    aoEscolher({ id: e.id, nome: e.nome, parametros });
  };
  const pintar = () => {
    const q = semAcento(busca.value).split(/\s+/).filter(Boolean), m = selM.value;
    filtrados = BIB_EX.exercicios.filter((e) =>
      (!origem || (origem === "meu") === e.meu) &&
      (!m || e.prim.concat(e.sec).some((x) => x.replace(/\s/g, "") === m)) &&
      q.every((t) => e.busca.includes(t)));
    if (q.length) {         // começa com o que foi digitado, depois palavra inteira, depois o resto
      const frase = q.join(" ");
      const nota = (e) => { if (e.chave.startsWith(frase)) return 0;
        const pal = e.busca.split(/\s+/);
        return q.every((t) => pal.includes(t)) ? 1 : q.every((t) => pal.some((w) => w.startsWith(t))) ? 2 : 3; };
      filtrados = filtrados.map((e) => [nota(e), e]).sort((x, y) => x[0] - y[0]).map((x) => x[1]);
    }
    f.querySelector(".bibex-n").textContent = `${filtrados.length} exercício${filtrados.length === 1 ? "" : "s"}`;
    lista.innerHTML = filtrados.length ? filtrados.map((e, k) => {
      const ms = [...new Set(e.prim.concat(e.sec))].map(rotMusculo).join(" · ");
      return `<div class="bibex-item${e.nome === atual ? " atual" : ""}" data-k="${k}">
        <button type="button" class="bibex-nome"><b>${html(e.nome)}</b>${ms ? `<small>${html(ms)}</small>` : ""}</button>
        ${e.meu ? `<span class="bibex-tag">meu</span>` : ""}${e.nome === atual ? `<span class="bibex-tag atual">atual</span>` : ""}
        <button type="button" class="ghost mini bibex-ver" aria-expanded="false">detalhes</button>
      </div>`;
    }).join("") : `<p class="dica">Nenhum exercício com esse filtro.</p>`;
  };
  lista.onclick = async (ev) => {
    const item = ev.target.closest(".bibex-item"); if (!item) return;
    const e = filtrados[+item.dataset.k];
    if (ev.target.closest(".bibex-nome") || ev.target.closest(".bibex-usar")) return usar(e, ev.target.closest(".bibex-usar"));
    const ver = ev.target.closest(".bibex-ver"); if (!ver) return;
    const aberto = item.querySelector(".bibex-det");
    if (aberto) { aberto.remove(); ver.setAttribute("aria-expanded", "false"); return; }
    ver.setAttribute("aria-expanded", "true");
    const d = document.createElement("div");
    d.className = "bibex-det"; d.textContent = "carregando…";
    item.appendChild(d);
    try {
      const x = await detalheEx(e.id);
      d.innerHTML = `${x.instrucoes ? `<p>${html(x.instrucoes).replace(/\n/g, "<br>")}</p>` : `<p class="dica">Sem instruções na biblioteca.</p>`}
        <div class="bibex-det-acoes"><button type="button" class="primario bibex-usar">Usar este exercício</button>
        ${/^https:\/\//.test(x.video || "") ? `<a href="${attr(x.video)}" target="_blank" rel="noopener noreferrer">Ver vídeo</a>` : ""}</div>`;
    } catch (err) { d.textContent = "Não consegui abrir os detalhes: " + err.message; }
  };
  busca.oninput = () => BIB_EX && pintar();
  busca.onkeydown = (e) => { if (e.key === "Enter" && filtrados[0] && BIB_EX) { e.preventDefault(); usar(filtrados[0]); } };
  selM.onchange = pintar;
  f.querySelector(".bibex-origem").onclick = (ev) => {
    const b = ev.target.closest("button"); if (!b) return;
    origem = b.dataset.o;
    f.querySelectorAll(".bibex-origem button").forEach((x) => x.classList.toggle("ativo", x === b));
    if (BIB_EX) pintar();
  };
  busca.focus();
  carregarBibEx().then((b) => {
    if (!f.isConnected) return;
    selM.insertAdjacentHTML("beforeend", b.musculos.map((m) => `<option value="${attr(m)}">${html(rotMusculo(m))}</option>`).join(""));
    pintar();
    lista.querySelector(".bibex-item.atual")?.scrollIntoView({ block: "center" });
  }).catch((err) => { lista.innerHTML = `<p class="dica">Não consegui abrir a biblioteca: ${html(err.message)}</p>`; });
}
const attr = (v) => String(v ?? "").replace(/"/g, "&quot;");
// parâmetro principal da série: o primeiro com valor, senão o primeiro que existir
function unidadeDoEx(ex) {
  const sr = ex.series[0] || {};
  const com = UNIDADES_EX.find(([p]) => sr[p] != null && sr[p] !== "");
  return (com || UNIDADES_EX.find(([p]) => p in sr) || UNIDADES_EX[0])[0];
}
function valoresDoEx(ex, un) {
  const vals = ex.series.map((sr) => sr[un] ?? "");
  return new Set(vals.map(String)).size === 1 ? String(vals[0]) : vals.join(",");
}
function exerciciosHtml(blocos) {
  return blocos.map((b, bi) => `
    <div class="ed-bloco ed-ex-bloco" data-b="${bi}">
      <div class="ed-bloco-cab">
        <select class="bl-tipo" aria-label="Tipo do bloco">${TIPOS_BLOCO.map(([v, t]) =>
          `<option value="${v}" ${b.tipo === v ? "selected" : ""}>${t}</option>`).join("")}</select>
        <input class="bl-titulo" value="${attr(b.titulo)}" placeholder="nome do bloco" aria-label="Nome do bloco">
        <button class="ghost mini bl-mover" data-d="-1" title="Subir o bloco">↑</button>
        <button class="ghost mini bl-mover" data-d="1" title="Descer o bloco">↓</button>
        <button class="ghost mini bl-del" title="Tirar o bloco">× bloco</button>
      </div>
      ${b.exercicios.map((e, ei) => { const un = unidadeDoEx(e); return `
      <div class="ed-ex" data-e="${ei}">
        <button type="button" class="ex-nome" title="Abrir a biblioteca do TrainingPeaks">${html(e.nome) || "Escolher na biblioteca"}</button>
        <label>séries <input class="ex-series" type="number" min="1" max="20" step="1" value="${e.series.length}"></label>
        <input class="ex-valor" value="${attr(valoresDoEx(e, un))}" placeholder="8 ou 12,10,8" aria-label="Repetições ou tempo">
        <select class="ex-unidade" aria-label="Unidade">${UNIDADES_EX.map(([v, t]) =>
          `<option value="${v}" ${un === v ? "selected" : ""}>${t}</option>`).join("")}</select>
        <input class="ex-nota" value="${attr(e.notas)}" placeholder="observação" aria-label="Observação do exercício">
        <button class="ghost mini ex-mover" data-d="-1" title="Subir">↑</button>
        <button class="ghost mini ex-mover" data-d="1" title="Descer">↓</button>
        <button class="ghost mini ex-del" title="Tirar o exercício">×</button>
      </div>`; }).join("")}
      <button class="ghost mini ex-add">+ exercício</button>
    </div>`).join("") + `<button class="ghost mini" id="ed-add-bloco-ex">+ bloco</button>`;
}
// exercício escolhido na biblioteca: as colunas padrão dele valem, como no TP, com carga
// em kg. Séries e repetições ficam; exercício que aceita tempo (prancha, isometria) vai
// por segundos, e a unidade só muda nos outros se ele não aceitar a atual
function exercicioEscolhido(escolha, antes) {
  const base = antes && antes.series.length ? antes.series : [{ Reps: 8 }, { Reps: 8 }, { Reps: 8 }];
  const ps = escolha.parametros;
  const un0 = unidadeDoEx({ series: base });
  const unidades = UNIDADES_EX.map(([p]) => p);
  const un = !ps ? un0 : ps.includes("Duration") ? "Duration"
    : ps.includes(un0) ? un0 : (ps.find((p) => unidades.includes(p)) || un0);
  const extras = ps ? ps.filter((p) => !unidades.includes(p)).map((p) => p.replace("Lb", "Kg")) : null;
  const padrao = un === "Duration" ? 30 : un === "DistanceMeters" ? 100 : 8;
  return { nome: escolha.nome, id: escolha.id, notas: antes ? antes.notas : null, formatos: {},
    series: base.map((sr) => {
      const linha = { [un]: un === un0 ? sr[un0] : padrao };
      if (extras) extras.forEach((p) => { linha[p] = null; });
      else Object.keys(sr).filter((p) => !unidades.includes(p)).forEach((p) => { linha[p] = sr[p]; });
      return linha;
    }) };
}
// DOM -> blocos. Carga e formato de cada série ficam: só muda o que aparece nos campos
function lerExercicios(cont, blocos) {
  return [...cont.querySelectorAll(".ed-ex-bloco")].map((bl) => {
    const orig = blocos[+bl.dataset.b];
    return {
      tipo: bl.querySelector(".bl-tipo").value, titulo: bl.querySelector(".bl-titulo").value,
      notas: orig.notas,
      exercicios: [...bl.querySelectorAll(".ed-ex")].map((l) => {
        const ex = orig.exercicios[+l.dataset.e];
        const un = l.querySelector(".ex-unidade").value;
        const n = Math.max(+l.querySelector(".ex-series").value || 1, 1);
        const vals = l.querySelector(".ex-valor").value.split(/[,;\s]+/).filter(Boolean);
        const base = ex.series.length ? ex.series : [{}];
        const series = Array.from({ length: n }, (_, k) => {
          const extras = { ...base[Math.min(k, base.length - 1)] };
          UNIDADES_EX.forEach(([p]) => delete extras[p]);
          return { [un]: vals.length ? vals[Math.min(k, vals.length - 1)] : null, ...extras };
        });
        return { nome: ex.nome, id: ex.id, notas: l.querySelector(".ex-nota").value, series, formatos: ex.formatos };
      }),
    };
  });
}
function montarEditorExercicios(ed, s, i) {
  const cont = ed.querySelector("#ed-exercicios");
  let blocos = JSON.parse(JSON.stringify(s.forca.blocos || []));
  const pintar = () => { cont.innerHTML = exerciciosHtml(blocos); };
  pintar();
  carregarBibEx().catch((e) => console.warn("biblioteca de exercícios:", e));
  const mover = (arr, k, d) => { const j = k + d; if (j >= 0 && j < arr.length) [arr[k], arr[j]] = [arr[j], arr[k]]; };
  cont.onclick = (ev) => {
    const t = ev.target;
    const acao = ["ex-nome", "ex-del", "ex-add", "ex-mover", "bl-del", "bl-mover"].find((c) => t.classList.contains(c));
    if (!acao && t.id !== "ed-add-bloco-ex") return;
    ev.preventDefault();
    blocos = lerExercicios(cont, blocos);
    if (t.id === "ed-add-bloco-ex") {
      return abrirBibliotecaEx("", (esc) => {
        blocos.push({ tipo: "SingleExercise", titulo: "", exercicios: [exercicioEscolhido(esc, null)] });
        pintar();
      });
    }
    const bi = +t.closest(".ed-ex-bloco").dataset.b, b = blocos[bi];
    const ei = t.closest(".ed-ex") ? +t.closest(".ed-ex").dataset.e : -1;
    if (acao === "ex-nome") {
      return abrirBibliotecaEx(b.exercicios[ei].nome, (esc) => {
        b.exercicios[ei] = exercicioEscolhido(esc, b.exercicios[ei]);
        pintar();
      });
    }
    if (acao === "ex-add") {
      return abrirBibliotecaEx("", (esc) => {
        b.exercicios.push(exercicioEscolhido(esc, b.exercicios[b.exercicios.length - 1]));
        if (b.tipo === "SingleExercise") b.tipo = "Superset";
        pintar();
      });
    }
    if (acao === "ex-del") b.exercicios.splice(ei, 1);
    if (acao === "ex-mover") mover(b.exercicios, ei, +t.dataset.d);
    if (acao === "bl-del") blocos.splice(bi, 1);
    if (acao === "bl-mover") mover(blocos, bi, +t.dataset.d);
    pintar();
  };
  // Superset e Circuito pedem o mesmo número de séries em todos os exercícios do bloco
  cont.onchange = (ev) => {
    if (!ev.target.classList.contains("ex-series")) return;
    const bl = ev.target.closest(".ed-ex-bloco");
    if (["Superset", "Circuit"].includes(bl.querySelector(".bl-tipo").value))
      bl.querySelectorAll(".ex-series").forEach((x) => { x.value = ev.target.value; });
  };
  ed.querySelector(".ed-aplicar-exs").onclick = async () => {
    blocos = lerExercicios(cont, blocos);
    carregando("montando a sessão...");
    try {
      const r = await api("/api/forca/sessao_editada", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ titulo: ed.querySelector("#ed-nome-ex").value, descricao: s.descricao,
          minutos: +ed.querySelector("#ed-min-ex").value || s.minutos, blocos,
          template: s.forca.template, objetivo: s.forca.objetivo, tss: s.forca.tss }),
      });
      aplicarSessao(i, { ...r.sessao, tipo: s.tipo, nota: s.nota, tempo_max: s.tempo_max, segundo: s.segundo, manual: s.manual });
    } catch (err) { alert("Erro: " + err.message); pintar(); } finally { pronto(); }
  };
}

// salva a tabela do ciclo e leva o km de cada semana para as semanas e para a prévia
async function salvarPlanoDaTela() {
  clearTimeout(_salvarPlanoT);
  const tab = document.querySelector(".plano-edit");
  if (!tab || !DADOS) return;
  const semanas = [...tab.querySelectorAll("tr")].slice(1).map((tr) => ({
    fase: tr.querySelector(".p-fase").value,
    km: tr.querySelector(".p-km").value,
    horas: tr.dataset.horas || null,
    obs: tr.querySelector(".p-obs").value,
  }));
  carregando("salvando a periodização...");
  try {
    const r = await api("/api/periodizacao/salvar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        athlete_id: DADOS.athlete_id, plano_id: +tab.dataset.id,
        nome: $("#plano-nome").value, prova_data: $("#plano-prova").value,
        semanas,
      }),
    });
    DADOS.periodizacao = r.periodizacao;
    pintarPlano();
    $("#plano-status") && ($("#plano-status").textContent = "salvo ✓");
  } catch (err) { alert("Erro ao salvar: " + err.message); return; } finally { pronto(); }
  await levarPlanoParaSemanas();
}
// o km salvo no ciclo vale nas semanas: a grade segue o plano e a prévia é refeita.
// Prévia com treino editado à mão não é refeita por cima: fica o aviso
async function levarPlanoParaSemanas() {
  if ($("#seguir-plano")) $("#seguir-plano").checked = true;
  montarDias(true); reaplicarSugestaoGrade(); sugerirBloco();
  document.dispatchEvent(new CustomEvent("fases-mudou"));
  const st = $("#plano-status");
  if (!PREVIA || !PREVIA.sessoes) {
    if (st) st.textContent = "salvo ✓ · o km de cada semana vale na prévia";
    return;
  }
  if (PREVIA.sessoes.some((s) => s.editado)) {
    if (st) st.textContent = "salvo ✓ · a prévia tem treino editado à mão: gere de novo para levar o km";
    return;
  }
  PREVIA_SEM_ROLAR = true;
  try { await gerarPrevia(); } finally { PREVIA_SEM_ROLAR = false; }
  if (st) st.textContent = "salvo ✓ · prévia refeita com o km de cada semana";
}
// mudou o km (ou a fase) de uma semana na tabela do ciclo: salva sozinho quando o
// cursor sai da tabela (redesenhar no meio da digitação apagaria a semana seguinte)
let _salvarPlanoT = null;
function agendarSalvarPlano() {
  clearTimeout(_salvarPlanoT);
  _salvarPlanoT = setTimeout(() => {
    const foco = document.activeElement;
    if (foco && foco.closest && foco.closest(".plano-edit")) return agendarSalvarPlano();
    salvarPlanoDaTela();
  }, 900);
}
document.addEventListener("change", (e) => {
  if (!e.target.closest(".plano-edit") || !e.target.matches(".p-km, .p-fase")) return;
  agendarSalvarPlano();
});

// REGRA OBRIGATÓRIA: depois de qualquer edição manual, o longo continua sendo o maior
// treino de corrida da semana (o servidor ajusta os outros, sem passar do teto)
async function garantirLongo(semanas) {
  if (!PREVIA || !DADOS) return;
  const ws = [...new Set(semanas.filter((w) => w != null).map(Number))];
  if (!ws.length) return;
  const idx = PREVIA.sessoes.map((s, i) => [s, i]).filter(([s]) => ws.includes(s.semana));
  if (!idx.some(([s]) => /^longo/.test(s.tipo || "") || /^(Longo|Rodagem longa)/.test(s.titulo || ""))) return;
  try {
    const r = await api("/api/longo_maior", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: DADOS.athlete_id, threshold_ms: thresholdEscolhido(),
        semanas: ws, tetos: PREVIA.tetos || {},
        longo_max_km: $("#longo-max").value ? parseFloat($("#longo-max").value) : null,
        longo_min_km: $("#longo-min").value ? parseFloat($("#longo-min").value) : null,
        min_km: parseFloat($("#min-km").value) || null, prova: objetivoMotor() || null,
        sessoes: idx.map(([s]) => s) }),
    });
    r.sessoes.forEach((s, k) => {
      const i = idx[k][1], antes = PREVIA.sessoes[i];
      // mexido pela regra, não pelo treinador: não trava como edição manual
      if (JSON.stringify(antes.structured_workout) !== JSON.stringify(s.structured_workout)) s.ajustado = true;
      PREVIA.sessoes[i] = s;
    });
    if (r.avisos && r.avisos.length) PREVIA.avisos = [...(PREVIA.avisos || []), ...r.avisos];
    recalcSemanas();
    pintarPrevia();
  } catch (e) { console.warn("longo maior:", e); }
}

function aplicarSessao(i, sessaoNova) {
  const s = PREVIA.sessoes[i];
  PREVIA.sessoes[i] = { ...sessaoNova, data: s.data, dia: s.dia,
    semana: s.semana, recuperacao: s.recuperacao, editado: true, fase: sessaoNova.fase ?? s.fase };
  recalcSemanas();
  pintarPrevia();
  $("#publicar").disabled = false;
  garantirLongo([s.semana]);
}

$("#lista-treinos").onclick = (e) => {
  const vazio = e.target.closest(".tcell.vazio.add");
  if (vazio) return abrirEditorNovo(vazio);
  const ex = e.target.closest(".excluir");
  if (ex) return excluirSessao(+ex.dataset.i);
  const cfp = e.target.closest(".copiar-forca-prev");
  if (cfp) return copiarForcaPrevia(+cfp.dataset.w);
  const mais = e.target.closest(".add-mais");
  if (mais) return abrirEditorNovo(mais.closest(".tcell"));
  const exc = e.target.closest(".ex-card");
  if (exc) {                                  // clique no exercício: abre o editor do dia e a biblioteca
    if (!document.querySelector(`.editor[data-e="${exc.dataset.i}"]`))
      document.querySelector(`.treino[data-i="${exc.dataset.i}"] .trocar`).click();
    document.querySelector(`.editor[data-e="${exc.dataset.i}"] .ed-ex-bloco[data-b="${exc.dataset.b}"] .ed-ex[data-e="${exc.dataset.e}"] .ex-nome`)?.click();
    return;
  }
  const ve = e.target.closest(".ver-exs");
  if (ve) {                                   // abre/fecha a lista completa de exercícios
    const card = ve.closest(".treino"); const aberto = card.classList.toggle("exs-aberto");
    ve.textContent = aberto ? "menos" : "todos os exercícios"; return;
  }
  const btn = e.target.closest(".trocar");
  if (!btn) return;
  const i = +btn.dataset.i;
  const card = document.querySelector(`.treino[data-i="${i}"]`);
  const jaAberto = !!document.querySelector(`.editor[data-e="${i}"]`);
  document.querySelectorAll(".editor").forEach((el) => el.remove());
  if (jaAberto) return;

  const s = PREVIA.sessoes[i];
  const tipo0 = tipoConcreto(s);
  const temPassos = !!s.structured_workout && !s.bike;
  const temExs = !!s.forca;
  const ed = document.createElement("div");
  ed.className = "editor";
  ed.innerHTML = `
    <div class="ed-abas">
      ${temPassos ? '<button class="aba ativa" data-aba="passos">Editar passos</button>' : ""}
      ${temExs ? '<button class="aba ativa" data-aba="exercicios">Exercícios</button>' : ""}
      <button class="aba ${temPassos || temExs ? "" : "ativa"}" data-aba="modelo">Trocar modelo</button>
      <button class="aba" data-aba="bib">Biblioteca do TP</button>
    </div>

    ${temPassos ? `<div data-painel="passos">
      <label class="ed-titulo">Título <input id="ed-nome" value="${s.titulo.replace(/"/g, "&quot;")}"></label>
      <div id="ed-passos">${passosHtml(blocosDaSessao(s))}</div>
      <div class="editor-acoes">
        <button class="primario ed-aplicar-passos">Aplicar neste dia</button>
        <button class="ghost ed-cancelar">Cancelar</button>
      </div>
    </div>` : ""}

    ${temExs ? `<div data-painel="exercicios">
      <div class="editor-linha ed-titulo-ex">
        <label>Título <input id="ed-nome-ex" value="${attr(s.titulo)}"></label>
        <label>Duração <input id="ed-min-ex" type="number" min="5" step="5" value="${s.minutos}"> min</label>
      </div>
      <div id="ed-exercicios"></div>
      <div class="editor-acoes">
        <button class="primario ed-aplicar-exs">Aplicar neste dia</button>
        <button class="ghost ed-cancelar">Cancelar</button>
      </div>
    </div>` : ""}

    <div data-painel="modelo" class="${temPassos || temExs ? "oculto" : ""}">
      <div class="editor-linha">
        <label>Tipo <select id="ed-tipo">
          ${tiposVisiveis().filter(([v]) => v && v !== "longo").map(([v, t]) =>
            `<option value="${v}" ${v === (s.forca && FORCA_TIPOS.includes(s.tipo) ? s.tipo : tipo0) ? "selected" : ""}>${t}</option>`).join("")}
        </select></label>
        <span id="ed-campos">${camposHtml(tipo0, s)}</span>
      </div>
      <div class="editor-acoes">
        <button class="primario ed-aplicar-modelo">Aplicar neste dia</button>
        <button class="ghost ed-cancelar">Cancelar</button>
      </div>
    </div>

    <div data-painel="bib" class="oculto">
      <div class="editor-linha">
        <label>Pasta <select id="ed-pasta"><option value="">carregando...</option></select></label>
        <label>Treino <select id="ed-item"><option value="">—</option></select></label>
      </div>
      <div class="editor-acoes">
        <button class="primario ed-aplicar-bib" disabled>Aplicar neste dia</button>
        <button class="ghost ed-cancelar">Cancelar</button>
      </div>
    </div>`;
  ed.dataset.e = i;
  (card.closest(".sem-linha") || card).appendChild(ed);

  // ---- navegacao entre abas
  ed.querySelector(".ed-abas").onclick = (ev) => {
    const aba = ev.target.closest(".aba");
    if (!aba) return;
    ed.querySelectorAll(".aba").forEach((a) => a.classList.toggle("ativa", a === aba));
    ed.querySelectorAll("[data-painel]").forEach((p) =>
      p.classList.toggle("oculto", p.dataset.painel !== aba.dataset.aba));
    if (aba.dataset.aba === "bib" && !BIB_PASTAS) carregarPastas(ed);
  };
  ed.querySelectorAll(".ed-cancelar").forEach((b) => (b.onclick = () => ed.remove()));
  if (temExs) montarEditorExercicios(ed, s, i);

  // ---- aba passos: adicionar/remover
  const contPassos = ed.querySelector("#ed-passos");
  if (contPassos) contPassos.onclick = (ev) => {
    const blocos = lerBlocosDoDom(contPassos);
    if (ev.target.id === "ed-add-bloco") {
      blocos.push({ rep: 1, passos: [{ nome: "Novo passo", valor: 5, unidade: "min", lo: 74, hi: 82, classe: "active" }] });
    } else if (ev.target.classList.contains("ed-add-passo")) {
      const bi = +ev.target.closest(".ed-bloco").dataset.b;
      blocos[bi]?.passos.push({ nome: "Novo passo", valor: 60, unidade: "s", lo: 74, hi: 82, classe: "rest" });
    } else if (ev.target.classList.contains("ed-del-passo")) {
      const bi = +ev.target.closest(".ed-bloco").dataset.b;
      const pi = +ev.target.closest(".ed-passo").dataset.p;
      blocos[bi]?.passos.splice(pi, 1);
      if (blocos[bi] && !blocos[bi].passos.length) blocos.splice(bi, 1);
    } else if (ev.target.classList.contains("ed-del-bloco")) {
      blocos.splice(+ev.target.closest(".ed-bloco").dataset.b, 1);
    } else return;
    contPassos.innerHTML = passosHtml(blocos);
  };

  if (contPassos) {
    contPassos.onchange = (ev) => {
      if (!ev.target.classList.contains("p-zona") || ev.target.value === "") return;
      const o = zonaOpcoes()[+ev.target.value]; if (!o) return;
      const linha = ev.target.closest(".ed-passo");
      linha.querySelector(".p-lo").value = o.lo;
      linha.querySelector(".p-hi").value = o.hi;
    };
    contPassos.oninput = (ev) => {
      if (!ev.target.classList.contains("p-lo") && !ev.target.classList.contains("p-hi")) return;
      const linha = ev.target.closest(".ed-passo");
      const lo = +linha.querySelector(".p-lo").value, hi = +linha.querySelector(".p-hi").value;
      const k = zonaOpcoes().findIndex((o) => Math.abs(o.lo - lo) < 0.6 && Math.abs(o.hi - hi) < 0.6);
      linha.querySelector(".p-zona").value = k >= 0 ? String(k) : "";
    };
  }

  const btnPassos = ed.querySelector(".ed-aplicar-passos");
  if (btnPassos) btnPassos.onclick = async () => {
    const blocos = lerBlocosDoDom(contPassos);
    if (!blocos.length) { alert("O treino precisa de pelo menos um passo."); return; }
    carregando("remontando o treino...");
    try {
      const r = await api("/api/sessao_passos", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          athlete_id: DADOS.athlete_id, threshold_ms: thresholdEscolhido(),
          // título intocado -> vazio: o servidor nomeia pelos passos editados
          titulo: (ed.querySelector("#ed-nome").value === s.titulo)
                    ? "" : ed.querySelector("#ed-nome").value,
          descricao: s.descricao, tipo: s.tipo, blocos,
        }),
      });
      aplicarSessao(i, r.sessao);
    } catch (err) { alert("Erro: " + err.message); } finally { pronto(); }
  };

  // ---- aba modelo
  ed.querySelector("#ed-tipo").onchange = (ev) => {
    ed.querySelector("#ed-campos").innerHTML = camposHtml(ev.target.value, null);
    if (FORCA_TIPOS.includes(ev.target.value)) anexarForcaBib(ed);
  };
  if (FORCA_TIPOS.includes(tipo0)) anexarForcaBib(ed);
  ed.querySelector(".ed-aplicar-modelo").onclick = async () => {
    const tipo = ed.querySelector("#ed-tipo").value;
    const params = {};
    ed.querySelectorAll("#ed-campos [data-k]").forEach((el) => {
      params[el.dataset.k] = el.type === "checkbox" ? el.checked : el.value;
    });
    if (FORCA_TIPOS.includes(tipo)) params.objetivo = forcaObjetivo();
    if (modalidade() === "forca") params.fase = s.fase;
    if (tipo.startsWith("cic_")) Object.assign(params, paramsCiclismo());
    carregando("gerando o treino novo...");
    try {
      const r = await api("/api/sessao", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: DADOS.athlete_id,
          threshold_ms: thresholdEscolhido(), tipo, params }),
      });
      aplicarSessao(i, r.sessao);
    } catch (err) { alert("Erro: " + err.message); } finally { pronto(); }
  };

  // ---- aba biblioteca
  const selPasta = ed.querySelector("#ed-pasta");
  const selItem = ed.querySelector("#ed-item");
  const btnBib = ed.querySelector(".ed-aplicar-bib");
  if (BIB_PASTAS) pintarPastas(ed);

  selPasta.onchange = async () => {
    selItem.innerHTML = "<option value=''>carregando...</option>";
    btnBib.disabled = true;
    if (!selPasta.value) return;
    try {
      const r = await api(`/api/biblioteca/${selPasta.value}`);
      selItem.innerHTML = "<option value=''>— escolha —</option>" +
        r.itens.map((it) => `<option value="${it.id}">${it.nome}</option>`).join("");
    } catch (err) {
      selItem.innerHTML = `<option value=''>erro: ${err.message}</option>`;
    }
  };
  selItem.onchange = () => { btnBib.disabled = !selItem.value; };
  btnBib.onclick = async () => {
    carregando("trazendo o treino da biblioteca...");
    try {
      const r = await api("/api/biblioteca/aplicar", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: DADOS.athlete_id,
          threshold_ms: thresholdEscolhido(),
          library_id: selPasta.value, item_id: selItem.value }),
      });
      aplicarSessao(i, r.sessao);
    } catch (err) { alert("Erro: " + err.message); } finally { pronto(); }
  };
};

// ---- mover treino de dia arrastando (como no calendário do TrainingPeaks) ----
let ARRASTANDO = null;
function semanaDaData(iso) {
  const ini = segundaDe(new Date($("#inicio").value + "T12:00"));
  const d = new Date(iso + "T12:00");
  return Math.floor((d - ini) / 6048e5) + 1;
}
function excluirSessao(i) {
  const s = PREVIA.sessoes[i];
  if (!s) return;
  const dm = s.data.slice(8, 10) + "/" + s.data.slice(5, 7);
  if (!confirm(`Excluir "${s.titulo}" de ${dm} da prévia?`)) return;
  document.querySelectorAll(".editor").forEach((el) => el.remove());
  PREVIA.sessoes.splice(i, 1);
  recalcSemanas();
  pintarPrevia();
  $("#publicar").disabled = !PREVIA.sessoes.length;
  garantirLongo([s.semana]);
}

// prévia: as sessões de força da semana w substituem as da semana w+1, mesmos dias da
// semana e mesmos exercícios. A corrida da semana seguinte fica como está.
function copiarForcaPrevia(w) {
  const mais7 = (iso) => { const d = new Date(iso + "T12:00"); d.setDate(d.getDate() + 7); return d.toISOString().slice(0, 10); };
  const fontes = PREVIA.sessoes.filter((x) => x.semana === w && x.forca);
  if (!fontes.length) return;
  const n = PREVIA.sessoes.filter((x) => x.semana === w + 1 && x.forca).length;
  PREVIA.sessoes = PREVIA.sessoes.filter((x) => !(x.semana === w + 1 && x.forca));
  const recupProx = PREVIA.sessoes.some((x) => x.semana === w + 1 && x.recuperacao);
  fontes.forEach((x) => {
    const c = JSON.parse(JSON.stringify(x));
    c.data = mais7(x.data); c.semana = w + 1; c.recuperacao = recupProx;
    c.editado = true; delete c.movido;
    PREVIA.sessoes.push(c);
  });
  PREVIA.sessoes.sort((a, b) => (a.data < b.data ? -1 : a.data > b.data ? 1 : (a.forca ? 1 : 0) - (b.forca ? 1 : 0)));
  recalcSemanas();
  pintarPrevia();
  $("#publicar").disabled = false;
}

function moverSessao(i, isoAlvo) {
  const s = PREVIA.sessoes[i];
  if (!s || s.data === isoAlvo) return;
  // dia ocupado por treino do MESMO tipo (corrida x corrida, força x força): troca os dois;
  // tipos diferentes convivem no mesmo dia
  const j = PREVIA.sessoes.findIndex((x, k) => k !== i && x.data === isoAlvo && !!x.forca === !!s.forca);
  const wd = (iso) => (new Date(iso + "T12:00").getDay() + 6) % 7;
  const origem = s.data;
  if (j >= 0) {                                   // dia ocupado: troca os dois de lugar
    const o = PREVIA.sessoes[j];
    o.data = origem; o.dia = DIAS[wd(origem)]; o.semana = semanaDaData(origem); o.movido = true;
  }
  const semOrigem = s.semana;
  s.data = isoAlvo; s.dia = DIAS[wd(isoAlvo)]; s.semana = semanaDaData(isoAlvo); s.movido = true;
  PREVIA.sessoes.sort((a, b) => (a.data < b.data ? -1 : 1));
  recalcSemanas();
  pintarPrevia();
  $("#publicar").disabled = false;
  garantirLongo([semOrigem, s.semana]);
}
$("#lista-treinos").addEventListener("dragstart", (e) => {
  const card = e.target.closest(".treino[data-i]");
  if (!card) return;
  ARRASTANDO = +card.dataset.i;
  e.dataTransfer.effectAllowed = "move";
  e.dataTransfer.setData("text/plain", String(ARRASTANDO));
  card.classList.add("arrastando");
});
$("#lista-treinos").addEventListener("dragend", () => {
  ARRASTANDO = null;
  document.querySelectorAll(".tcell.solta").forEach((c) => c.classList.remove("solta"));
  document.querySelectorAll(".treino.arrastando").forEach((c) => c.classList.remove("arrastando"));
});
$("#lista-treinos").addEventListener("dragover", (e) => {
  const cel = e.target.closest(".tcell[data-data]");
  if (!cel || ARRASTANDO == null) return;
  e.preventDefault(); e.dataTransfer.dropEffect = "move";
  cel.classList.add("solta");
});
$("#lista-treinos").addEventListener("dragleave", (e) => {
  const cel = e.target.closest(".tcell[data-data]");
  if (cel && !cel.contains(e.relatedTarget)) cel.classList.remove("solta");
});
$("#lista-treinos").addEventListener("drop", (e) => {
  const cel = e.target.closest(".tcell[data-data]");
  if (!cel || ARRASTANDO == null) return;
  e.preventDefault();
  const i = ARRASTANDO; ARRASTANDO = null;
  moverSessao(i, cel.dataset.data);
});

function inserirSessao(cel, sessao) {
  const iso = cel.dataset.data;
  const wd = (new Date(iso + "T12:00").getDay() + 6) % 7;
  PREVIA.sessoes.push({
    ...sessao,
    data: iso, dia: DIAS[wd],
    semana: +cel.dataset.semana,
    recuperacao: cel.dataset.recup === "1",
    fase: cel.dataset.fase || undefined,
    editado: true,
  });
  PREVIA.sessoes.sort((a, b) => (a.data < b.data ? -1 : 1));
  recalcSemanas();
  pintarPrevia();
  $("#publicar").disabled = false;
  garantirLongo([+cel.dataset.semana]);
}

function abrirEditorNovo(cel) {
  document.querySelectorAll(".editor").forEach((el) => el.remove());
  const linha = cel.closest(".sem-linha");
  const rot = cel.dataset.data.split("-").reverse().slice(0, 2).join("/");

  const tipoNovo = tiposVisiveis().filter(([v]) => v && v !== "longo")[0][0];
  const ed = document.createElement("div");
  ed.className = "editor";
  ed.dataset.e = "novo";
  ed.innerHTML = `
    <div class="ed-abas">
      <button class="aba ativa" data-aba="modelo">Novo treino em ${rot}</button>
      <button class="aba" data-aba="bib">Biblioteca do TP</button>
    </div>
    <div data-painel="modelo">
      <div class="editor-linha">
        <label>Tipo <select id="ed-tipo">
          ${tiposVisiveis().filter(([v]) => v && v !== "longo").map(([v, t]) =>
            `<option value="${v}">${t}</option>`).join("")}
        </select></label>
        <span id="ed-campos">${camposHtml(tipoNovo, null)}</span>
      </div>
      <div class="editor-acoes">
        <button class="primario ed-add-modelo">Adicionar neste dia</button>
        <button class="ghost ed-cancelar">Cancelar</button>
      </div>
    </div>
    <div data-painel="bib" class="oculto">
      <div class="editor-linha">
        <label>Pasta <select id="ed-pasta"><option value="">carregando...</option></select></label>
        <label>Treino <select id="ed-item"><option value="">—</option></select></label>
      </div>
      <div class="editor-acoes">
        <button class="primario ed-add-bib" disabled>Adicionar neste dia</button>
        <button class="ghost ed-cancelar">Cancelar</button>
      </div>
    </div>`;
  linha.appendChild(ed);

  ed.querySelector(".ed-abas").onclick = (ev) => {
    const aba = ev.target.closest(".aba");
    if (!aba) return;
    ed.querySelectorAll(".aba").forEach((a) => a.classList.toggle("ativa", a === aba));
    ed.querySelectorAll("[data-painel]").forEach((p) =>
      p.classList.toggle("oculto", p.dataset.painel !== aba.dataset.aba));
    if (aba.dataset.aba === "bib") {
      if (BIB_PASTAS) pintarPastas(ed); else carregarPastas(ed);
    }
  };
  ed.querySelectorAll(".ed-cancelar").forEach((b) => (b.onclick = () => ed.remove()));

  ed.querySelector("#ed-tipo").onchange = (ev) => {
    ed.querySelector("#ed-campos").innerHTML = camposHtml(ev.target.value, null);
    if (FORCA_TIPOS.includes(ev.target.value)) anexarForcaBib(ed);
  };
  if (FORCA_TIPOS.includes(tipoNovo)) anexarForcaBib(ed);
  ed.querySelector(".ed-add-modelo").onclick = async () => {
    const tipo = ed.querySelector("#ed-tipo").value;
    const params = {};
    ed.querySelectorAll("#ed-campos [data-k]").forEach((el) => {
      params[el.dataset.k] = el.type === "checkbox" ? el.checked : el.value;
    });
    if (FORCA_TIPOS.includes(tipo)) params.objetivo = forcaObjetivo();
    if (modalidade() === "forca") params.fase = cel.dataset.fase;
    if (tipo.startsWith("cic_")) Object.assign(params, paramsCiclismo());
    carregando("gerando o treino novo...");
    try {
      const r = await api("/api/sessao", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: DADOS.athlete_id,
          threshold_ms: thresholdEscolhido(), tipo, params }),
      });
      inserirSessao(cel, r.sessao);
    } catch (err) { alert("Erro: " + err.message); } finally { pronto(); }
  };

  const selPasta = ed.querySelector("#ed-pasta");
  const selItem = ed.querySelector("#ed-item");
  const btnBib = ed.querySelector(".ed-add-bib");
  selPasta.onchange = async () => {
    selItem.innerHTML = "<option value=''>carregando...</option>";
    btnBib.disabled = true;
    if (!selPasta.value) return;
    try {
      const r = await api(`/api/biblioteca/${selPasta.value}`);
      selItem.innerHTML = "<option value=''>— escolha —</option>" +
        r.itens.map((it) => `<option value="${it.id}">${it.nome}</option>`).join("");
    } catch (err) {
      selItem.innerHTML = `<option value=''>erro: ${err.message}</option>`;
    }
  };
  selItem.onchange = () => { btnBib.disabled = !selItem.value; };
  btnBib.onclick = async () => {
    carregando("trazendo o treino da biblioteca...");
    try {
      const r = await api("/api/biblioteca/aplicar", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ athlete_id: DADOS.athlete_id,
          threshold_ms: thresholdEscolhido(),
          library_id: selPasta.value, item_id: selItem.value }),
      });
      inserirSessao(cel, r.sessao);
    } catch (err) { alert("Erro: " + err.message); } finally { pronto(); }
  };
}

async function carregarPastas(ed) {
  try {
    const r = await api("/api/biblioteca");
    BIB_PASTAS = r.pastas;
    pintarPastas(ed);
  } catch (err) {
    ed.querySelector("#ed-pasta").innerHTML = `<option value=''>erro: ${err.message}</option>`;
  }
}

function pintarPastas(ed) {
  // pastas do proprio treinador primeiro, depois as compartilhadas
  const minhas = BIB_PASTAS.filter((p) => p.dona === "Andre Santos");
  const outras = BIB_PASTAS.filter((p) => p.dona !== "Andre Santos");
  const opt = (p) => `<option value="${p.id}">${p.nome}</option>`;
  ed.querySelector("#ed-pasta").innerHTML =
    "<option value=''>— escolha a pasta —</option>" +
    `<optgroup label="Minhas pastas">${minhas.map(opt).join("")}</optgroup>` +
    `<optgroup label="Compartilhadas">${outras.map(opt).join("")}</optgroup>`;
}

function svg(barras) {
  const r = barras.map((b) => {
    const cls = b.h > 0.93 ? "alta" : b.h < 0.75 ? "baixa" : "";
    return `<rect class="${cls}" x="${(b.x * 100).toFixed(2)}%" width="${Math.max(b.w * 100, 0.4).toFixed(2)}%"
      y="${((1 - b.h) * 100).toFixed(1)}%" height="${(b.h * 100).toFixed(1)}%" rx="1"></rect>`;
  }).join("");
  return `<svg class="grafico" preserveAspectRatio="none">${r}</svg>`;
}

// -- 4. publicar -----------------------------------------------------------
$("#publicar").onclick = async () => {
  if (!PREVIA) return;
  const apagar = $("#substituir").checked ? conflitosValidos().map((c) => c.id) : [];
  const n = PREVIA.sessoes.length;
  if (!n) return;
  const nAp = (PREVIA.avisos || []).length;
  if (!confirm(`Publicar ${n} treinos no TrainingPeaks de ${DADOS.nome}` +
    (apagar.length ? `, apagando ${apagar.length} planejados existentes` : "") +
    (nAp ? ` (há ${nAp} apontamento${nAp > 1 ? "s" : ""} na prévia; publica assim mesmo)` : "") + "?")) return;

  carregando(`publicando ${n} treinos...`);
  try {
    const r = await api("/api/publicar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        athlete_id: DADOS.athlete_id, atleta_nome: DADOS.nome,
        sessoes: PREVIA.sessoes, apagar_ids: apagar,
      }),
    });
    const el = $("#resultado");
    el.classList.remove("oculto");
    const houve = r.erros.length;
    aviso(el, `${r.criados.length} treinos criados` +
      (r.apagados.length ? `, ${r.apagados.length} apagados` : "") +
      (r.lab_registrado ? ", bloco registrado no Lab" : "") +
      (houve ? `. Falhas: ${r.erros.join(" | ")}` : ". Tudo certo."),
      houve ? "erro" : "ok");
    if (!houve) $("#publicar").disabled = true;
  } catch (e) {
    alert("Erro ao publicar: " + e.message);
  } finally { pronto(); }
};

// -- bindings da sugestao (dias de treino + objetivo de prova) ---------------
$("#sugerir").onclick = aplicarSugestao;
$("#modalidade").addEventListener("change", () => {
  const m = modalidade();
  $("#so-forca").classList.toggle("oculto", m !== "mista");
  document.body.classList.toggle("modo-forca", m === "forca");
  document.body.classList.toggle("modo-ciclismo", m === "ciclismo");
  // a grade é refeita do zero; a prévia da modalidade anterior não vale mais
  MANUAIS = {}; FIXOS = {};
  PREVIA = null;
  $("#lista-treinos").innerHTML = "";
  $("#conflitos").classList.add("oculto"); $("#avisos-seq").classList.add("oculto"); $("#pmc-linha").classList.add("oculto");
  $("#resultado").classList.add("oculto");
  $("#sec-previa").classList.add("oculto");
  $("#publicar").disabled = true;
  pintarPlanoForca();
  if (m === "ciclismo" && DADOS) {
    cicPadroes();
    pintarPlanoCiclismo().then(() => { montarDias(); document.dispatchEvent(new CustomEvent("fases-mudou")); });
    return;
  }
  if (DADOS) { montarDias(); document.dispatchEvent(new CustomEvent("fases-mudou")); }
});
$("#so-forca").onclick = () => {
  const dias = diasEscolhidos();
  if (!dias.length) { alert("Marque pelo menos um dia de treino."); return; }
  const diasForca = dias.slice(0, 3);          // forca 2-3x/semana
  document.querySelectorAll("#dias select[data-dia]").forEach((s) => {
    s.value = diasForca.includes(+s.dataset.dia) ? "forca" : "";
    s.classList.toggle("ativo", !!s.value);
  });
};
$("#chips-dias").addEventListener("change", aplicarSugestao);
$("#soltar-manuais").onclick = () => {
  if (!Object.keys(MANUAIS).length) return;
  if (!confirm("Os dias que você mexeu à mão voltam a seguir a sugestão. Continuar?")) return;
  MANUAIS = {};
  document.querySelectorAll("#dias select.manual").forEach((el) => { el.classList.remove("manual"); el.title = ""; });
  aplicarSugestao();
};

// "Abrir ciclo no período": periodização do Início ao Fim, com a maior semana, o
// maior longo e o mínimo por treino do Período. Base e Base + Específico não têm
// prova nem polimento; Completo tem Base, Específico, Polimento e a prova (no Dia
// da caixa Prova, se cair no período; senão no Fim)
$("#btn-ciclo-periodo").onclick = async () => {
  if (!DADOS) return;
  const ini = $("#inicio").value, fim = $("#fim").value;
  if (!ini || !fim || fim < ini) { alert("Defina o início e o fim do período."); return; }
  const km = parseFloat($("#semana-max").value);
  if (!km) { alert("Coloque a maior semana (km) do período."); return; }
  const fases = $("#fases-ciclo").value;
  const completo = fases === "completo";
  const fmt = (iso) => iso.split("-").reverse().slice(0, 2).join("/");
  const pd = $("#prova-data").value;
  const provaDia = completo ? (pd && pd > ini && pd <= fim ? pd : fim) : null;
  const cal = provaDia && ((DADOS.provas) || []).find((x) => x.date === provaDia);
  const objetivo = objetivoMotor() || (cal ? objetivoPorKm(kmDaProva(cal)) : "") || null;
  if (completo && !objetivo) {
    alert("Escolha o Objetivo (5, 10, 21, 42 km ou outra distância) na caixa Prova: ele define o polimento e a semana da prova.");
    return;
  }
  const nomeProva = completo ? ((provaDia === pd && $("#prova-nome").value) || (cal && cal.name.trim()) || "") : "";
  const nome = completo
    ? (nomeProva ? `Ciclo ${nomeProva}` : `Ciclo ${objetivo.replace("k", " km")} ${fmt(ini)} a ${fmt(provaDia)}`)
    : ({ base: "Base", especifico: "Específico" }[fases] || "Base + Específico") + ` ${fmt(ini)} a ${fmt(fim)}`;
  carregando("criando a periodização do período...");
  try {
    // mesmo período de um ciclo do Período que já existe: refaz em vez de duplicar
    const atual = DADOS.periodizacao;
    const seg = (iso) => segundaDe(new Date(iso + "T12:00")).toISOString().slice(0, 10);
    const ult = atual && atual.semanas && atual.semanas.length ? atual.semanas[atual.semanas.length - 1].inicio : "";
    const doPeriodo = atual && ["base", "especifico", "base_especifico", "completo"].includes(((atual.params || {}).modo)
      || (atual.sem_prova ? "base" : ""));
    const mesmo = doPeriodo && seg(atual.inicio) === seg(ini) && ult === seg(fim);
    const r = mesmo ? await api("/api/periodizacao/refazer", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ athlete_id: DADOS.athlete_id, plano_id: atual.id, fases_ciclo: fases,
        objetivo, km_pico: km, prova_data: provaDia, fim,
        prova_km: completo && provaDia === pd ? kmObjetivo() : null, provas: provasParaCiclo(),
        longo_pico: parseFloat($("#longo-max").value) || null,
        min_km: parseFloat($("#min-km").value) || null, max_km: parseFloat($("#max-km").value) || null,
        ini_auto: true, ...progressaoPedido() }),
    }) : await api("/api/periodizacao/criar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        athlete_id: DADOS.athlete_id, nome, inicio: ini, fim, fases_ciclo: fases,
        prova_data: provaDia,
        objetivo,
        prova_km: completo && provaDia === pd ? kmObjetivo() : null, prova_nome: nomeProva || null,
        provas: provasParaCiclo(),
        km_pico: km,
        longo_pico: parseFloat($("#longo-max").value) || null,
        min_km: parseFloat($("#min-km").value) || null,
        max_km: parseFloat($("#max-km").value) || null,
        historico: historicoCompacto(),
        ...progressaoPedido(),
      }),
    });
    DADOS.periodizacao = r.periodizacao;
    const tinhaProva = !!pd;
    if (completo) {
      // a prova do ciclo vira a prova do bloco: o gerador monta o polimento até ela
      $("#prova-data").value = provaDia;
      $("#prova-nome").value = nomeProva;
      if (!$("#prova").value) $("#prova").value = objetivo;
      $("#btn-ciclo-prova").disabled = false;
    } else {
      // ciclo sem prova: a prova marcada na tela sairia do período pedido
      $("#prova-data").value = ""; $("#prova-nome").value = "";
      $("#btn-ciclo-prova").disabled = true;
    }
    pintarPlano();
    pintarProvasBloco();
    if ($("#seguir-plano")) $("#seguir-plano").checked = true;
    montarDias(true);
    reaplicarSugestaoGrade();
    sugerirBloco();
    statusProgressao((completo ? `Ciclo completo criado até a prova de ${fmt(provaDia)} (${objetivo.replace("k", " km")})`
                               : `Ciclo sem prova criado: ${nome.toLowerCase()}`) + `, maior semana ${km} km` +
      ($("#longo-max").value ? `, longo até ${$("#longo-max").value} km` : "") +
      ($("#longo-min").value ? `, longo nunca abaixo de ${$("#longo-min").value} km` : "") +
      ($("#min-km").value ? `, mínimo de ${$("#min-km").value} km por treino` : "") +
      ($("#max-km").value ? `, máximo de ${$("#max-km").value} km por treino (fora o longo)` : "") + "." +
      (!completo && tinhaProva ? " A data de prova da tela foi limpa (o ciclo não tem prova)." : "") +
      (completo && pd && pd !== provaDia ? ` O Dia da caixa Prova estava fora do período; a prova ficou no Fim (${fmt(provaDia)}).` : "") +
      (r.aviso ? " " + r.aviso : ""));
    $("#plano-box").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) { alert("Não deu para criar o ciclo: " + err.message); } finally { pronto(); }
};
$("#prova").addEventListener("change", () => {
  if (DADOS) aplicarSugestao();
});
