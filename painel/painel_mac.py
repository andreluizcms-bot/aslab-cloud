# -*- coding: utf-8 -*-
"""Funções do painel que só rodam no Mac: TrainingPeaks ao vivo e PDFs.

O painel local chama direto. O painel da nuvem chama pelo worker (nuvem.py manda o
pedido para a fila `comandos`, o worker roda a função aqui e devolve o resultado e
os arquivos gerados). Sem Streamlit aqui dentro.
"""
import os, sys, json, asyncio, subprocess, datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
PYBIN = sys.executable

from report import excluded_ids, active_ids
from render_all import titlecase
from render_all_modern import slug, MESES

ESCRITOS = []      # arquivos gravados fora do retorno (o worker manda junto para a nuvem)


# ---------- TrainingPeaks ----------
async def _user_data():
    from tp_mcp.client import TPClient
    async with TPClient() as c:
        return await c._get_user_data()

async def _atleta(aid):
    ud = await _user_data()
    a = next((x for x in (ud or {}).get("athletes", []) if str(x["athleteId"]) == str(aid)), None)
    if a is None: raise RuntimeError("Atleta não encontrado na conta de treinador.")
    return a

async def _refresh_async(month, aid):
    import collect
    start, end = collect.month_range(month); pstart, pend = collect.prev_month_range(month)
    a = await _atleta(aid)
    return await collect.collect_one(a, start, end, pstart, pend, month)

def refresh_athlete(month, aid):
    """Puxa do TrainingPeaks os treinos atuais do atleta (inclui os de hoje) e regrava o JSON."""
    rec = asyncio.run(_refresh_async(month, aid))
    p = os.path.join(BASE, "data", month, f"{aid}.json")
    json.dump(rec, open(p, "w"), ensure_ascii=False)
    ESCRITOS.append(p)
    return rec

def _date_chunks(start, end, size=90):
    cur = start
    while cur <= end:
        e = min(cur + dt.timedelta(days=size - 1), end)
        yield cur, e
        cur = e + dt.timedelta(days=1)

async def _history_async(aid, start, end):
    from tp_mcp.tools.workouts import tp_get_workouts, tp_get_workout
    from tp_mcp.client.context import athlete_override
    out = {}
    tok = athlete_override.set(str(aid))
    try:
        for s, e in _date_chunks(start, end):                      # 1) lista (rápido)
            wl = await tp_get_workouts(s.isoformat(), e.isoformat(), "completed")
            if wl.get("isError"): continue
            for w in wl.get("workouts", []):
                out[w["id"]] = w
        sem = asyncio.Semaphore(8)                                  # 2) detalhe (FC + cadência) em paralelo
        async def _hr(wid):
            async with sem:
                try:
                    d = await tp_get_workout(str(wid))
                    m = d.get("metrics", {}) if not d.get("isError") else {}
                    return wid, m.get("avg_hr"), m.get("avg_cadence")
                except Exception:
                    return wid, None, None
        for wid, hr, cad in await asyncio.gather(*[_hr(w) for w in out]):
            out[wid]["_hr"] = hr; out[wid]["_cad"] = cad
    finally:
        athlete_override.reset(tok)
    return list(out.values())

def history(aid, start, end):
    """Treinos realizados do atleta entre start e end (datas), com FC e cadência do detalhe."""
    return asyncio.run(_history_async(aid, start, end))

RUN_PRS = [("1 km", "speed1K", 1000.0), ("5 km", "speed5K", 5000.0), ("10 km", "speed10K", 10000.0),
           ("Meia", "speedHalfMarathon", 21097.5), ("Maratona", "speedMarathon", 42195.0)]

async def _records_async(aid):
    from tp_mcp.tools.peaks import tp_get_peaks
    from tp_mcp.client.context import athlete_override
    tok = athlete_override.set(str(aid)); out = {}
    try:
        sem = asyncio.Semaphore(6)
        async def one(label, prt, meters):
            async with sem:
                try:
                    r = await tp_get_peaks("Run", prt, 3650)
                    recs = r.get("records") or []
                    if r.get("isError") or not recs: return label, None
                    b = recs[0]; v = b.get("value")                 # value = velocidade (m/s)
                    if not v: return label, None
                    return label, {"pace": 1000.0 / (v * 60), "secs": meters / v, "date": b.get("date")}
                except Exception:
                    return label, None
        for label, rec in await asyncio.gather(*[one(l, p, m) for l, p, m in RUN_PRS]):
            out[label] = rec
    finally:
        athlete_override.reset(tok)
    return out

def records(aid):
    return asyncio.run(_records_async(aid))

async def _weekly_async(aid, wk_start):
    import collect
    ws, we = wk_start, wk_start + dt.timedelta(days=6)
    ps, pe = wk_start - dt.timedelta(days=7), wk_start - dt.timedelta(days=1)
    a = await _atleta(aid)
    return await collect.collect_one(a, ws.isoformat(), we.isoformat(),
                                     ps.isoformat(), pe.isoformat(), wk_start.strftime("%Y-%m"))

def semana(aid, wk_iso):
    """Semana ao vivo do TP (planejado + realizado) para o espelho do calendário."""
    return asyncio.run(_weekly_async(aid, dt.date.fromisoformat(wk_iso)))

async def _events_batch_async(roster, start, end, conc=12):
    """Busca eventos de todos os atletas no período (blocos de 85 dias)."""
    import collect
    from tp_mcp.client import TPClient
    from tp_mcp.tools.events import tp_get_events
    from tp_mcp.client.context import athlete_override
    async with TPClient() as c:
        pass   # garante token
    sem = asyncio.Semaphore(conc); out = []
    async def one(a):
        async with sem:
            tok = athlete_override.set(str(a["id"]))
            try:
                for cs, ce in collect._chunks(start, end):
                    r = await tp_get_events(cs, ce)
                    if not r.get("isError"):
                        for e in (r.get("events") or []):
                            if e.get("eventDate"):
                                out.append({"id": a["id"], "atleta": a["name"],
                                            "prova": e.get("name") or "—",
                                            "date": e["eventDate"][:10],
                                            "tipo": e.get("eventType") or ""})
            except Exception:
                pass
            finally:
                athlete_override.reset(tok)
    await asyncio.gather(*(one(a) for a in roster))
    return out

def eventos(horizon_days, day_iso):
    """Todas as provas de todos os alunos nos próximos N dias."""
    start = dt.date.fromisoformat(day_iso); end = start + dt.timedelta(days=horizon_days)
    return asyncio.run(_events_batch_async(atletas(), start.isoformat(), end.isoformat()))

async def _detail_async(aid, wid):
    from tp_mcp.client import TPClient
    from tp_mcp.tools.workouts import tp_get_workout
    from tp_mcp.client.context import athlete_override
    async with TPClient() as c:
        pass
    tok = athlete_override.set(str(aid))
    try:
        return await tp_get_workout(str(wid))
    finally:
        athlete_override.reset(tok)

def detalhe(aid, wid):
    """Todos os dados de um treino (detalhe completo do TP)."""
    return asyncio.run(_detail_async(aid, wid))

def atletas():
    """Atletas dos GRUPOS do TP (roster) — usado no lote semanal e no envio por e-mail."""
    ud = asyncio.run(_user_data())
    _exc = excluded_ids(); _act = active_ids()      # _act = ids dos 4 grupos (None se sem roster)
    ath = [{"id": str(a["athleteId"]),
            "name": titlecase(f'{a.get("firstName","")} {a.get("lastName","")}'.strip()),
            "email": (a.get("email") or "").strip().lower()}
           for a in (ud or {}).get("athletes", [])
           if str(a["athleteId"]) not in _exc and (_act is None or str(a["athleteId"]) in _act)]
    return sorted(ath, key=lambda x: x["name"].lower())

def drifts(aid, start_iso, end_iso):
    """Desacoplamento cardíaco dos longos (baixa os arquivos do relógio)."""
    import drift
    return asyncio.run(drift.athlete_drifts(aid, start_iso, end_iso))


# ---------- PDFs ----------
def pdf_path(month, name):
    y, m = map(int, month.split("-"))
    return os.path.join(BASE, "saida", month, f'{slug(name)}_{MESES[m-1]}_{y}.pdf')

def pdf_path_week(name, wk_start):
    return os.path.join(BASE, "saida", "semanal", f'{slug(name)}_semana_{wk_start.strftime("%Y-%m-%d")}.pdf')

def pdf_path_period(name, n, end):
    return os.path.join(BASE, "saida", "periodos", f'{slug(name)}_{n}meses_{end.strftime("%Y-%m-%d")}.pdf')

def _months_back(d, n):
    """Primeiro dia do mês, n meses antes de d."""
    y, m = d.year, d.month - n
    while m <= 0: m += 12; y -= 1
    return dt.date(y, m, 1)

def generate_athlete_pdf(d, month):
    """Gera o PDF de um único atleta (in-process). Retorna o caminho."""
    from report import coach_message as _coach_msg
    from report_modern import render_modern as _render_modern
    p = pdf_path(month, d["name"]); dd = dict(d)
    if not dd.get("coach_msg"): dd["coach_msg"] = _coach_msg(dd)   # fallback por regras
    os.makedirs(os.path.dirname(p), exist_ok=True)
    _render_modern(dd, p)
    return p

async def _period_async(aid, n_meses):
    import collect
    end = dt.date.today()
    start = _months_back(end, n_meses - 1)                      # inclui o mês atual (parcial)
    pend = start - dt.timedelta(days=1); pstart = _months_back(start, n_meses)
    a = await _atleta(aid)
    rec = await collect.collect_range(a, start.isoformat(), end.isoformat(),
                                      pstart.isoformat(), pend.isoformat())
    return rec, start, end

def generate_period_pdf(aid, name, n_meses):
    """Puxa N meses do TP (em blocos de 85 dias) e gera o PDF de período (quebra por mês)."""
    from report import compute, build_refs, coach_message_periodo
    from report_modern import render_modern
    rec, start, end = asyncio.run(_period_async(aid, n_meses))
    if rec.get("error"): raise RuntimeError(rec["error"])
    period = f'{start.strftime("%d/%m/%Y")} – {end.strftime("%d/%m/%Y")}'
    W_ = [{**w, "date": dt.date.fromisoformat(w["date"][:10])} for w in rec.get("workouts", [])]
    refs = build_refs(rec.get("settings", {}))
    data = compute(name, period, f"{n_meses}m anteriores", start, end, W_, rec.get("prev"),
                   rec.get("fitness"), rec.get("event"), rec.get("photo"), refs, bucket="month")
    data["id"] = str(aid); data["metrics"] = rec.get("metrics")
    data["periodo_tipo"] = "multi"; data["periodo_label"] = f"Últimos {n_meses} meses"
    data["coach_msg"] = coach_message_periodo(data, n_meses)
    p = pdf_path_period(name, n_meses, end)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    render_modern(data, p)
    return p

def _weekly_pdf_from_rec(aid, name, wk_start, rec):
    """Monta o PDF semanal a partir do rec já coletado. Retorna o caminho."""
    from report import compute, build_refs, coach_message_semana
    from report_modern import render_modern
    ws, we = wk_start, wk_start + dt.timedelta(days=6)
    period = f'{ws.strftime("%d/%m/%Y")} – {we.strftime("%d/%m/%Y")}'
    W_ = [{**w, "date": dt.date.fromisoformat(w["date"][:10])} for w in rec.get("workouts", [])]
    refs = build_refs(rec.get("settings", {}))
    data = compute(name, period, "sem. anterior", ws, we, W_, rec.get("prev"),
                   rec.get("fitness"), rec.get("event"), rec.get("photo"), refs, bucket="day")
    data["id"] = str(aid); data["metrics"] = rec.get("metrics"); data["periodo_tipo"] = "semanal"
    data["coach_msg"] = coach_message_semana(data)
    p = pdf_path_week(name, wk_start)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    render_modern(data, p)
    return p

def generate_weekly_pdf(aid, name, wk_start):
    """Puxa a semana do TP ao vivo e gera o PDF semanal (quebra por dia). Retorna (caminho, rec)."""
    rec = asyncio.run(_weekly_async(aid, wk_start))
    return _weekly_pdf_from_rec(aid, name, wk_start, rec), rec

async def _weekly_batch_async(aids, wk_start, conc=5):
    """Coleta a semana de vários atletas em paralelo. Retorna {aid: rec|None}."""
    import collect
    ws, we = wk_start, wk_start + dt.timedelta(days=6)
    ps, pe = wk_start - dt.timedelta(days=7), wk_start - dt.timedelta(days=1)
    ud = await _user_data()
    amap = {str(x["athleteId"]): x for x in (ud or {}).get("athletes", [])}
    sem = asyncio.Semaphore(conc); out = {}
    async def one(aid):
        a = amap.get(str(aid))
        if a is None: out[str(aid)] = None; return
        async with sem:
            try:
                out[str(aid)] = await collect.collect_one(a, ws.isoformat(), we.isoformat(),
                                                          ps.isoformat(), pe.isoformat(),
                                                          wk_start.strftime("%Y-%m"))
            except Exception:
                out[str(aid)] = None
    await asyncio.gather(*(one(a) for a in aids))
    return out

def semanais_lote(pares, wk_start):
    """PDFs semanais de vários atletas [(aid, nome)]. Retorna (caminhos_ok, nomes_que_falharam)."""
    recs = asyncio.run(_weekly_batch_async([a for a, _ in pares], wk_start))
    ok, fail = [], []
    for aid, nm in pares:
        rec = recs.get(str(aid))
        if not rec or rec.get("error"):
            fail.append(nm); continue
        try: ok.append(_weekly_pdf_from_rec(aid, nm, wk_start, rec))
        except Exception: fail.append(nm)
    return ok, fail

def pdf_periodizacao(dados, rel):
    """PDF do ciclo estruturado; `rel` é o caminho relativo à pasta do painel."""
    from report_periodizacao import render_periodizacao
    p = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    render_periodizacao(dados, p)
    return p

def preview_png(pdf):
    """Primeira página do PDF em PNG (sips no Mac; pypdfium2 onde não houver sips)."""
    out = pdf.replace(".pdf", "_preview.png")
    if sys.platform == "darwin":
        subprocess.run(["sips", "-s", "format", "png", pdf, "--out", out],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sips", "-Z", "1400", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            import pypdfium2 as pdfium
            pg = pdfium.PdfDocument(pdf)[0]
            img = pg.render(scale=1400 / max(pg.get_size())).to_pil()
            img.save(out)
        except Exception:
            return None
    return out if os.path.exists(out) else None


# ---------- LTHR: sugestão para quem está sinalizado ----------
LTHR_CACHE = os.path.join(BASE, "data", "lthr_sugestao.json")

def regra_lthr(lthr, p20, p60, p1):
    """Sugestão de LTHR pelos picos de FC de corrida (sem gravar nada no TP).
    Friel: numa prova/teste de ~1 h a FC média fica no limiar; num esforço de 20 min, ~5% acima.
    Teto de 93% da maior FC de 1 min, para não seguir leitura errada do sensor."""
    cands = []
    if p60: cands.append((p60, "melhor média de 60 min"))
    if p20: cands.append((p20 * 0.95, "95% da melhor média de 20 min"))
    if not cands: return None
    val, base = max(cands, key=lambda x: x[0])
    if p1 and val > p1 * 0.93: val, base = p1 * 0.93, "93% da FC máxima de 1 min"
    return int(round(val)), base

async def _picos_fc(aid):
    from tp_mcp.tools.peaks import tp_get_peaks
    from tp_mcp.client.context import athlete_override
    tok = athlete_override.set(str(aid)); out = {}
    try:
        for t, dias in (("hR20min", 90), ("hR60min", 90), ("hR1min", 365)):
            try:
                r = await tp_get_peaks("Run", t, dias)
                rr = [] if r.get("isError") else (r.get("records") or [])
                out[t] = (rr[0]["value"], rr[0].get("date", "")[:10]) if rr else None
            except Exception:
                out[t] = None
    finally:
        athlete_override.reset(tok)
    return out

def ler_sugestoes_lthr():
    try: return json.load(open(LTHR_CACHE))
    except Exception: return {}

def sugestao_lthr(itens):
    """itens = [(aid, lthr_atual)]. Calcula, grava no cache e devolve {aid: sugestão}."""
    async def todos():
        sem = asyncio.Semaphore(6)
        async def um(aid):
            async with sem: return await _picos_fc(aid)
        return await asyncio.gather(*[um(a) for a, _ in itens])
    picos = asyncio.run(todos()) if itens else []
    cache = ler_sugestoes_lthr(); hoje = dt.date.today().isoformat(); out = {}
    for (aid, atual), pk in zip(itens, picos):
        p20, p60, p1 = (pk.get(k) for k in ("hR20min", "hR60min", "hR1min"))
        r = regra_lthr(atual, p20 and p20[0], p60 and p60[0], p1 and p1[0])
        item = {"atual": atual, "calc": hoje,
                "p20": p20, "p60": p60, "p1": p1,
                "sugerido": r[0] if r else None, "base": r[1] if r else None}
        if r and r[1].startswith("melhor média de 60") and p60: item["data"] = p60[1]
        elif r and r[1].startswith("95%") and p20: item["data"] = p20[1]
        elif r and p1: item["data"] = p1[1]
        cache[str(aid)] = out[str(aid)] = item
    os.makedirs(os.path.dirname(LTHR_CACHE), exist_ok=True)
    json.dump(cache, open(LTHR_CACHE, "w"), ensure_ascii=False, indent=1)
    ESCRITOS.append(LTHR_CACHE)
    return out


# ---------- outros ----------
def arquivo(rel):
    """Caminho de um arquivo já gerado no Mac (a nuvem recebe o arquivo junto)."""
    p = os.path.normpath(os.path.join(BASE, rel))
    return p if p.startswith(BASE + os.sep) and os.path.isfile(p) else None

def retest():
    """Testes de limiar feitos nas últimas 12 semanas (retest_limiar.py --json)."""
    r = subprocess.run([PYBIN, "retest_limiar.py", "--json"], cwd=BASE, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError((r.stderr or "falhou")[-400:])
    try: return json.loads((r.stdout or "").strip().splitlines()[-1]) if r.stdout.strip() else []
    except Exception: return []

def email_configurado():
    import send_reports as sr
    return bool(sr.load_cfg())

def enviar_emails(alvos, periodo):
    """alvos = [(nome, email, caminho_pdf)]. Retorna (enviados, falhas)."""
    import time, send_reports as sr
    cfg = sr.load_cfg()
    if not cfg: raise RuntimeError("email_config.json não configurado no Mac")
    smtp = sr.open_smtp(cfg); ok = 0; fails = []
    try:
        for nm, em, pth in alvos:
            good, err = sr.send_report(cfg, em, nm, periodo, pth, smtp=smtp)
            if good: ok += 1
            else: fails.append(f"{nm} ({err[:40]})")
            time.sleep(1.0)   # gentileza com o Gmail
    finally:
        try: smtp.quit()
        except Exception: pass
    return ok, fails
