// Casca "Mesa do treinador": trilho de passos, resumo, linha do ciclo e
// atalhos. Não toca no motor (app.js): observa o DOM e lê o estado global.
(() => {
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const PASSOS = ["atleta", "bloco", "semanas", "previa"];
  const CAT = {
    qual: ["teste_limiar", "limiar", "limiar_prefadiga", "escada_limiar", "segundo_limiar", "limiar_vo2", "vo2max",
      "ritmo_prova", "over_under", "piramide", "fartlek", "progressivo", "corre_anda"],
    longo: ["longo", "longo_continuo", "longo_trocas", "longo_bloco", "longo_progressivo", "longo_alternado", "longo_surges"],
    rodagem: ["rodagem", "rodagem_strides", "rodagem_leve"],
    bike: ["bike_rodagem", "bike_intervalado", "bike_longa"],
    forca: ["forca", "forca_inferior", "forca_superior", "forca_empurrar", "forca_puxar", "forca_core",
      "forca_pliometria", "forca_estab_core", "forca_ativ_gluteo", "forca_ativ_superiores"],
  };
  const catDe = (v) => Object.keys(CAT).find((k) => CAT[k].includes(v)) || "";
  const dados = () => (typeof DADOS !== "undefined" ? DADOS : null);
  const previa = () => (typeof PREVIA !== "undefined" ? PREVIA : null);
  const soForca = () => typeof modalidade === "function" && modalidade() === "forca";

  // ---- passos --------------------------------------------------------------
  const secao = (p) => $(`.passo[data-passo="${p}"]`);
  const botao = (p) => $(`.passo-btn[data-passo="${p}"]`);
  const liberado = (p) => p === "atleta" ? true
    : p === "bloco" || p === "semanas" ? !$("#sec-bloco").classList.contains("oculto")
    : !$("#sec-previa").classList.contains("oculto");

  function irPara(p) {
    if (!liberado(p)) return;
    PASSOS.forEach((x) => {
      const s = secao(x); const b = botao(x);
      const ativo = x === p;
      // "oculto" é o cadeado do motor; "ativo" é a aba visível
      s.classList.toggle("ativo", ativo);
      s.style.display = ativo ? "" : "none";
      b.classList.toggle("ativo", ativo);
    });
    $("#ciclo").classList.toggle("oculto", p === "atleta" || !dados());
    window.scrollTo({ top: 0, behavior: "smooth" });
    pintarCiclo();
  }
  function atualizarTrilho() {
    PASSOS.forEach((p) => { botao(p).disabled = !liberado(p); });
    const temAtleta = !!dados();
    $("#carregar").classList.toggle("primario", !temAtleta);
    $("#carregar").classList.toggle("secundario", temAtleta);
    $("#tr-atleta").textContent = temAtleta ? dados().nome || "carregado" : "escolha na barra";
    $("#tr-bloco").textContent = soForca() ? "datas e fases" : "datas e prova";
    botao("atleta").classList.toggle("feito", temAtleta);
    botao("bloco").classList.toggle("feito", temAtleta && !!$("#inicio").value && !!$("#fim").value);
    const nSel = $$("#dias select[data-dia]").filter((s) => s.value).length;
    $("#tr-semanas").textContent = nSel ? `${nSel} treinos marcados` : "dias e tipos";
    botao("semanas").classList.toggle("feito", nSel > 0);
    const temPrevia = liberado("previa") && previa() && previa().sessoes;
    $("#tr-previa").textContent = temPrevia ? `${previa().sessoes.length} sessões` : "gere para ver";
    const pub = $("#publicar-trilho");
    pub.disabled = !temPrevia;
    $("#tr-publicar").textContent = temPrevia ? `${previa().sessoes.length} treinos · oculto` : "nada gerado";
  }
  $$(".passo-btn").forEach((b) => (b.onclick = () => irPara(b.dataset.passo)));
  $$("[data-ir]").forEach((b) => (b.onclick = () => irPara(b.dataset.ir)));
  $("#publicar-trilho").onclick = () => { irPara("previa"); $("#publicar").click(); };

  // cadeados do motor mudam -> destrava passos e avança sozinho
  new MutationObserver((muts) => {
    atualizarTrilho();
    for (const m of muts) {
      const el = m.target;
      // só avança quando o cadeado "oculto" ACABOU de abrir — não quando a
      // classe muda por outro motivo (ex.: o próprio irPara alternando "ativo",
      // que antes puxava o treinador de volta para a prévia)
      const destravou = /\boculto\b/.test(m.oldValue || "") && !el.classList.contains("oculto");
      if (!destravou) continue;
      if (el.id === "sec-bloco" && botao("atleta").classList.contains("ativo")) irPara("bloco");
      if (el.id === "sec-previa") irPara("previa");
    }
    pintarResumo();
  }).observe(document.body, { attributes: true, attributeFilter: ["class"], attributeOldValue: true, subtree: true });

  // ---- categorias nas células da grade --------------------------------------
  function tingirGrade() {
    $$("#dias select[data-dia]").forEach((s) => { s.dataset.cat = catDe(s.value); });
    // fase e km por linha (da periodização, casando a segunda-feira)
    if (typeof faseDaSemana !== "function") return;
    $$("#dias .sem-cfg").forEach((row) => {
      const sel = row.querySelector("select"); if (!sel) return;
      const w = +sel.dataset.semana;
      try {
        if (soForca()) {               // só força: a linha mostra a fase de força, sem km
          row.dataset.fase = faseForcaDaSemana(w); row.classList.remove("leve");
          row.classList.toggle("manual", !!(FASES[w] && FASES[w].forca));
          delete row.dataset.km;
          const fo = row.querySelector(".forca-sel"), t = `automática · ${faseForcaAuto(w)}`;
          if (fo && fo.options[0].textContent !== t) fo.options[0].textContent = t;
          return;
        }
        const f = faseDaSemana(w);
        row.dataset.fase = f.fase; row.classList.toggle("leve", !!f.leve);
        row.classList.toggle("manual", !!f.manual);
        const fs = row.querySelector(".fase-sel");
        if (fs) {                       // só grava se mudou: o observer de #dias reage a texto novo
          const t = `automática · ${f.auto}`;
          if (fs.options[0].textContent !== t) fs.options[0].textContent = t;
          if (fs.dataset.fase !== f.fase) fs.dataset.fase = f.fase;
        }
        const plano = dados().periodizacao;
        let km = "";
        if (plano) {
          const ini = segundaDe(new Date($("#inicio").value + "T12:00"));
          const seg = new Date(ini); seg.setDate(seg.getDate() + 7 * (w - 1));
          const sem = plano.semanas.find((x) => x.inicio === seg.toISOString().slice(0, 10));
          if (sem && sem.km) km = sem.km;
        }
        row.dataset.km = km || "—";
        const sk = row.querySelector(".sem-km");
        const tk = km ? `${km} km no plano` : "";
        if (sk && sk.textContent !== tk) sk.textContent = tk;
      } catch (e) { /* sem datas ainda */ }
    });
  }
  new MutationObserver(() => { tingirGrade(); atualizarTrilho(); pintarCiclo(); })
    .observe($("#dias"), { childList: true, subtree: true });
  $("#dias").addEventListener("change", () => { tingirGrade(); atualizarTrilho(); pintarResumo(); });
  document.addEventListener("fases-mudou", () => { tingirGrade(); pintarCiclo(); pintarResumo(); });
  // trocou de atleta: a prévia antiga já foi limpa pelo motor; volta ao passo Bloco
  document.addEventListener("atleta-trocado", () => { atualizarTrilho(); irPara("bloco"); pintarResumo(); });

  // ---- linha do ciclo -------------------------------------------------------
  // só força: sem km, a barra indica a carga de cada fase
  const ALTURA_FASE = { "Adaptação": 40, Base: 55, "Força máxima": 100, "Acumulação": 85,
    "Pré-competitivo": 70, "Competitivo": 50, Descarga: 25 };
  function pintarCiclo() {
    const faixa = $("#ciclo-faixa");
    if (!dados() || typeof nSemanasPeriodo !== "function" || !$("#inicio").value) { faixa.innerHTML = ""; return; }
    const n = nSemanasPeriodo();
    const f0 = soForca();
    const plano = f0 ? null : dados().periodizacao;
    const ini = segundaDe(new Date($("#inicio").value + "T12:00"));
    const prova = f0 ? "" : $("#prova-data").value;
    const semanas = [];
    for (let w = 1; w <= n; w++) {
      const seg = new Date(ini); seg.setDate(seg.getDate() + 7 * (w - 1));
      const iso = seg.toISOString().slice(0, 10);
      const fim = new Date(seg); fim.setDate(fim.getDate() + 6);
      const f = f0 ? { fase: faseForcaDaSemana(w), leve: false } : faseDaSemana(w);
      const sem = plano ? plano.semanas.find((x) => x.inicio === iso) : null;
      const fimIso = fim.toISOString().slice(0, 10);
      const pvs = (typeof provasDoBloco === "function" ? provasDoBloco() : []).filter((p) => p.date >= iso && p.date <= fimIso);
      semanas.push({ w, iso, fase: f.fase, leve: f.leve, km: sem ? +sem.km || 0 : 0,
        prova: prova && prova >= iso && prova <= fimIso,
        prio: pvs.some((p) => p.prio === "A") ? "A" : pvs.some((p) => p.prio === "B") ? "B" : pvs.some((p) => p.prio === "C") ? "C" : "",
        pnomes: pvs.map((p) => `${p.prio}: ${p.name}`).join(" · ") });
    }
    const max = Math.max(...semanas.map((s) => s.km), 1);
    const ativa = +(document.activeElement && document.activeElement.dataset && document.activeElement.dataset.semana) || 0;
    faixa.innerHTML = semanas.map((s) => {
      const h = f0 ? ALTURA_FASE[s.fase] || 60 : s.km ? Math.max(18, Math.round(s.km / max * 100)) : (s.leve ? 35 : 60);
      return `<button type="button" class="ciclo-sem ${s.leve ? "leve" : ""} ${s.w === ativa ? "atual" : ""}"
        data-fase="${s.fase}" data-w="${s.w}" title="Semana ${s.w} · ${s.fase}${s.leve ? " (leve)" : ""}${s.km ? " · " + s.km + " km" : ""}${s.pnomes ? " · " + s.pnomes : ""}">
        <small>${s.w}${s.km ? ` · ${s.km} km` : ""}</small>${s.prova || s.prio === "A" ? '<svg class="flag"><use href="#ic-bandeira"/></svg>' : s.prio ? `<small class="pflag ${s.prio.toLowerCase()}">${s.prio}</small>` : ""}<div class="barra" style="height:${h}%"></div></button>`;
    }).join("");
    const fases = [...new Set(semanas.map((s) => s.fase))];
    const cor = { Base: "var(--f-base)", "Específico": "var(--f-esp)", Polimento: "var(--f-pol)", Prova: "var(--f-prova)",
      "Adaptação": "var(--teal2)", "Força máxima": "var(--coral)", "Acumulação": "var(--ambar)",
      "Pré-competitivo": "var(--verde)", "Competitivo": "var(--verm)", "Descarga": "var(--f-leve)" };
    $("#ciclo-legenda").innerHTML = fases.map((f) => `<span><i style="background:${cor[f] || "var(--f-leve)"}"></i>${f}</span>`).join("")
      + (semanas.some((s) => s.leve) ? `<span><i style="background:var(--f-leve)"></i>leve</span>` : "");
  }
  $("#ciclo-faixa").addEventListener("click", (e) => {
    const b = e.target.closest(".ciclo-sem"); if (!b) return;
    const w = +b.dataset.w;
    irPara("semanas");
    const sel = $(`#dias select[data-semana="${w}"]`);
    if (sel) {
      sel.closest(".sem-cfg").scrollIntoView({ behavior: "smooth", block: "center" });
      $$(".ciclo-sem").forEach((x) => x.classList.toggle("atual", x === b));
    }
  });

  // ---- resumo ---------------------------------------------------------------
  const fmtBR2 = (iso) => iso ? iso.split("-").reverse().slice(0, 2).join("/") : "—";
  function pintarResumo() {
    const d = dados();
    $("#res-nome").textContent = d ? (d.nome || $("#atleta option:checked")?.textContent || "—") : "—";
    $("#res-sub").textContent = !d ? "nenhum atleta" : soForca() ? "periodização de força"
      : d.periodizacao ? `ciclo: ${d.periodizacao.nome}` : "sem periodização no Lab";
    $("#res-objetivo").textContent = d ? (forcaObjetivo() === "hipertrofia" ? "Hipertrofia" : "Performance") : "—";
    const n = (d && typeof nSemanasPeriodo === "function" && $("#inicio").value) ? nSemanasPeriodo() : null;
    $("#res-semanas").textContent = n ?? "—";
    $("#res-periodo").innerHTML = (d && $("#inicio").value) ? `${fmtBR2($("#inicio").value)}<small>até ${fmtBR2($("#fim").value)}</small>` : "—";
    const pd = $("#prova-data").value, po = $("#prova").value, pn = $("#prova-nome").value;
    $("#res-prova").innerHTML = pd ? `${fmtBR2(pd)}<small>${[po, pn].filter(Boolean).join(" · ") || "sem objetivo"}</small>` : (po || "—");
    $("#res-longo").innerHTML = $("#longo-max").value
      ? `${$("#longo-max").value} km${$("#longo-min").value ? `<small>menor ${$("#longo-min").value} km</small>` : ""}` : "—";
    $("#res-semana").textContent = $("#semana-max").value ? `${$("#semana-max").value} km` : "—";
    const dias = typeof diasEscolhidos === "function" ? diasEscolhidos() : [];
    $("#res-dias").textContent = dias.length ? `${dias.length}×` : "—";
    const forcaSem1 = $$('#dias select[data-semana="1"]').filter((s) => s.value.startsWith("forca")).length +
      $$('#dias select.forca2[data-semana2="1"]').filter((s) => s.value).length;
    $("#res-forca").textContent = d ? (forcaSem1 ? `${forcaSem1}×/sem` : "—") : "—";
    $("#res-zonas").innerHTML = d ? (d.zonas_tp ? "TP<small>10 zonas do atleta</small>" : "estimado<small>sem zonas no TP</small>") : "—";
    const P = previa(); const temPrevia = P && P.sessoes && !$("#sec-previa").classList.contains("oculto");
    $("#res-previa").classList.toggle("oculto", !temPrevia);
    if (temPrevia) {
      $("#res-p-km").textContent = P.total_km ?? Math.round(P.sessoes.reduce((a, s) => a + (s.km || 0), 0));
      $("#res-p-n").textContent = P.sessoes.length;
    }
  }
  document.addEventListener("input", () => { pintarResumo(); atualizarTrilho(); });
  document.addEventListener("change", () => { pintarResumo(); pintarCiclo(); atualizarTrilho(); });
  new MutationObserver(() => {
    $("#vazio-atleta").classList.toggle("oculto", !$("#perfil").classList.contains("oculto"));
    pintarResumo();
  }).observe($("#perfil"), { attributes: true, attributeFilter: ["class"] });
  new MutationObserver(() => { pintarResumo(); atualizarTrilho(); }).observe($("#lista-treinos"), { childList: true });

  // ---- status do TP (lista de atletas carregou?) ----------------------------
  new MutationObserver(() => {
    const ok = $("#atleta option") && !/erro|carregando/i.test($("#atleta").textContent);
    $("#status-tp").classList.toggle("off", !ok);
  }).observe($("#atleta"), { childList: true });

  // ---- teclado: 1-4 troca de passo, ⌘↵ gera prévia -------------------------
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, select, textarea")) return;
    const i = ["1", "2", "3", "4"].indexOf(e.key);
    if (i >= 0) irPara(PASSOS[i]);
  });
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && liberado("semanas")) $("#gerar").click();
  });

  // link direto: depois que o atleta carrega, vai ao passo pedido / gera a prévia
  const qs = new URLSearchParams(location.search);
  if (qs.get("passo") || qs.get("gerar")) {
    let feito = false;
    new MutationObserver(() => {
      if (feito || $("#sec-bloco").classList.contains("oculto")) return;
      feito = true;
      setTimeout(() => {
        if (qs.get("gerar")) $("#gerar").click();
        else if (qs.get("passo")) irPara(qs.get("passo"));
      }, 300);
    }).observe($("#sec-bloco"), { attributes: true, attributeFilter: ["class"] });
  }

  // estado inicial
  PASSOS.forEach((p) => { if (p !== "atleta") secao(p).style.display = "none"; });
  atualizarTrilho(); pintarResumo();
})();
