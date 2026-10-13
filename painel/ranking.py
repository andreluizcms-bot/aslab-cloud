# -*- coding: utf-8 -*-
"""Liga AS — ranking de comprometimento (via banco), mensal e semanal,
nas modalidades: geral, corrida e força.

Pilares (geral/corrida): Disciplina 35% · Constância/Presença 25% · Evolução 25% · Ritmo 15%.
Força: Disciplina 50% · Constância/Presença 50% (sem pace).
CLI:  python ranking.py [YYYY-MM]              # liga mensal geral
      python ranking.py --podio-semana         # pódios da última semana fechada (p/ mensagem de segunda)
"""
import argparse, calendar, datetime as dt, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

PESOS = {"disciplina": .35, "constancia": .25, "evolucao": .25, "ritmo": .15}
PESOS_CORRIDA = {"disciplina": .30, "constancia": .25, "evolucao": .20, "volume": .25}
PESOS_FORCA = {"disciplina": .50, "constancia": .50}

def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))

def _monta(rows, modo):
    """Ritmo/Volume (percentil) + total ponderado + ordenação."""
    pesos = {"forca": PESOS_FORCA, "corrida": PESOS_CORRIDA}.get(modo, PESOS)
    if modo == "corrida":
        # Volume = percentil de km por SEMANA (o que o treinador prescreve)
        com_vol = sorted([r for r in rows if (r.get("km_sem") or 0) > 0],
                         key=lambda r: -r["km_sem"])
        n = len(com_vol)
        for i, r in enumerate(com_vol):
            r["volume"] = _clamp((1 - i / max(n - 1, 1)) * 100)
    elif modo != "forca":
        com_pace = sorted([r for r in rows if r.get("pace")], key=lambda r: r["pace"])
        n = len(com_pace)
        for i, r in enumerate(com_pace):
            r["ritmo"] = _clamp((1 - i / max(n - 1, 1)) * 100)
    for r in rows:
        r.setdefault("ritmo", None); r.setdefault("volume", None)
        num = den = 0.0
        for k, w in pesos.items():
            if r.get(k) is not None:
                num += r[k] * w; den += w
        r["total"] = round(num / den, 1) if den else 0.0
    rows.sort(key=lambda r: (-int(r["qualificado"]), -r["total"], -r["sess"], r["name"].lower()))
    return rows

def _pilares(con, aid, tr, ini, fim, modo, n_ref, prev_range, min_plan):
    """Calcula pilares de um atleta numa janela. n_ref = semanas (mês) ou None (semana)."""
    comp_all = [t for t in tr if t[1] == "completed"]
    kind_alvo = {"corrida": "run", "forca": "strength"}.get(modo)
    comp = [t for t in comp_all if (t[2] == kind_alvo)] if kind_alvo else comp_all
    if not comp: return None
    # disciplina (planejados do tipo)
    pl_rows = [t for t in tr if t[1] == "planned" and (not kind_alvo or t[2] == kind_alvo)]
    done_pl = sum(1 for t in comp if t[5])
    tot_plan = len(pl_rows) + done_pl
    disciplina = (done_pl / tot_plan * 100) if tot_plan >= min_plan else None
    # constância / presença
    if n_ref:                                        # mensal: semanas com X+ sessões
        por_sem = {}
        for t in comp:
            d0 = dt.date.fromisoformat(t[0])
            k = (d0 - dt.timedelta(days=d0.weekday())).isoformat()
            por_sem[k] = por_sem.get(k, 0) + 1
        minimo = 2 if modo == "forca" else 3
        constancia = sum(1 for v in por_sem.values() if v >= minimo) / n_ref * 100
        n_grupos = len(por_sem)
    else:                                            # semanal: dias com treino
        dias = len({t[0] for t in comp})
        alvo = 3 if modo == "forca" else 5
        constancia = _clamp(dias / alvo * 100)
        n_grupos = dias
    km_run = sum(t[3] or 0 for t in comp if t[2] == "run")
    out = {"sess": len(comp), "disciplina": disciplina, "constancia": constancia,
           "grupos": n_grupos, "pace": None, "evolucao": None,
           "km": round(km_run),
           "km_sem": round(km_run / n_ref, 1) if n_ref else round(km_run, 1)}
    if modo != "forca":
        runs = [(t[3], t[4]) for t in comp if t[2] == "run" and (t[3] or 0) >= 3 and (t[4] or 0) > 0]
        km = sum(r[0] for r in runs); hrs = sum(r[1] for r in runs)
        out["pace"] = (hrs * 60 / km) if km > 0 else None
        if out["pace"] and prev_range:
            prev = con.execute("""SELECT SUM(dist_km), SUM(dur_h) FROM treinos
                                  WHERE atleta_id=? AND date>=? AND date<? AND type='completed'
                                  AND kind='run' AND dist_km>=3 AND dur_h>0""",
                               (aid, prev_range[0], prev_range[1])).fetchone()
            if prev and prev[0] and prev[0] > (10 if n_ref is None else 20) and prev[1]:
                pace_prev = prev[1] * 60 / prev[0]
                out["evolucao"] = _clamp(50 + (pace_prev - out["pace"]) / pace_prev * 100 * 25)
    return out

def liga(month, today=None, modo="geral"):
    today = today or dt.date.today()
    y, m = map(int, month.split("-"))
    ini = dt.date(y, m, 1)
    fim = min(dt.date(y, m, calendar.monthrange(y, m)[1]), today)
    if fim < ini: return []
    semanas = set(); d = ini
    while d <= fim:
        semanas.add((d - dt.timedelta(days=d.weekday())).isoformat()); d += dt.timedelta(days=1)
    prev = ((ini.replace(day=1) - dt.timedelta(days=62)).replace(day=1).isoformat(), ini.isoformat())
    min_sess = 4 if modo == "forca" else (4 if modo == "corrida" else 6)
    con = db.get_conn(); db.init_db(con)
    rows = []
    for aid, nome in con.execute("SELECT id, nome FROM atletas WHERE ativo=1"):
        tr = con.execute("""SELECT date, type, kind, dist_km, dur_h, was_planned FROM treinos
                            WHERE atleta_id=? AND mes=? AND date<=?""",
                         (aid, month, fim.isoformat())).fetchall()
        p = _pilares(con, aid, tr, ini, fim, modo, len(semanas), prev, min_plan=4 if modo == "geral" else 2)
        if not p: continue
        rows.append({"id": aid, "name": nome, **p,
                     "qualificado": p["sess"] >= min_sess and p["grupos"] >= 2})
    con.close()
    return _monta(rows, modo)

def liga_semana(wk_start, today=None, modo="geral"):
    today = today or dt.date.today()
    ini = wk_start - dt.timedelta(days=wk_start.weekday())
    fim = min(ini + dt.timedelta(days=6), today)
    if fim < ini: return []
    prev = ((ini - dt.timedelta(days=28)).isoformat(), ini.isoformat())
    min_sess = 2 if modo in ("forca", "corrida") else 3
    con = db.get_conn(); db.init_db(con)
    rows = []
    for aid, nome in con.execute("SELECT id, nome FROM atletas WHERE ativo=1"):
        tr = con.execute("""SELECT date, type, kind, dist_km, dur_h, was_planned FROM treinos
                            WHERE atleta_id=? AND date>=? AND date<=?""",
                         (aid, ini.isoformat(), fim.isoformat())).fetchall()
        p = _pilares(con, aid, tr, ini, fim, modo, None, prev, min_plan=2)
        if not p: continue
        rows.append({"id": aid, "name": nome, **p, "qualificado": p["sess"] >= min_sess})
    con.close()
    return _monta(rows, modo)

def podio_semana_texto(wk_start=None, today=None):
    """Texto pronto (p/ mensagem de segunda) com os 3 pódios da semana."""
    today = today or dt.date.today()
    if wk_start is None:
        seg_atual = today - dt.timedelta(days=today.weekday())
        wk_start = seg_atual - dt.timedelta(days=7)      # última semana FECHADA
    fim = wk_start + dt.timedelta(days=6)
    med = ["🥇", "🥈", "🥉"]
    linhas = [f"🏆 PÓDIO DA SEMANA ({wk_start.strftime('%d/%m')}–{fim.strftime('%d/%m')})"]
    for modo, rot in (("geral", "🏅 Geral"), ("corrida", "🏃 Corrida"), ("forca", "🏋️ Força")):
        q = [r for r in liga_semana(wk_start, today, modo) if r["qualificado"]][:3]
        if q:
            linhas.append(f'{rot}: ' + " · ".join(
                f'{med[i]} {r["name"].split()[0].title()} ({r["total"]:.0f})' for i, r in enumerate(q)))
        else:
            linhas.append(f"{rot}: sem qualificados")
    return "\n".join(linhas)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mes", nargs="?", default=None)
    ap.add_argument("--podio-semana", action="store_true")
    ap.add_argument("--modo", default="geral", choices=["geral", "corrida", "forca"])
    a = ap.parse_args()
    if a.podio_semana:
        print(podio_semana_texto()); sys.exit(0)
    mes = a.mes or dt.date.today().strftime("%Y-%m")
    for i, r in enumerate(liga(mes, modo=a.modo)[:15], 1):
        q = "" if r["qualificado"] else " (não qualif.)"
        print(f'{i:2}. {r["name"][:26]:26} {r["total"]:5.1f} sess:{r["sess"]:2}{q}')
