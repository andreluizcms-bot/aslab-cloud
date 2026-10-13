# -*- coding: utf-8 -*-
"""Revisão semanal (segunda-feira): para cada atleta ativo, lê a semana que fechou
(aderência, km feito x planejado, HRV, forma/TSB, prova) e propõe o que fazer na
semana que começa: progredir, manter, aliviar ou recuperar. Nada é gravado sem o
treinador aprovar (o painel aplica as escolhidas na periodização do atleta).
Uso: python revisao_semanal.py [--data YYYY-MM-DD] [--resumo]"""
import argparse, datetime as dt, json, os, sqlite3, statistics, sys
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import db

REGRAS = ("Progredir = aderência ≥ 80% nas 2 últimas semanas, HRV sem alerta e forma acima de -20. "
          "Manter = aderência entre 60 e 80%, ou forma entre -20 e -25. "
          "Aliviar = HRV em alerta (2+ dias abaixo do limiar na semana ou média 7d abaixo), forma ≤ -25 "
          "ou aderência abaixo de 60% com sinais de fadiga. Recuperar = prova nos últimos 7 dias.")


def _semana(ref):
    seg = ref - dt.timedelta(days=ref.weekday())          # segunda da semana atual
    return seg - dt.timedelta(days=7), seg - dt.timedelta(days=1), seg   # ini, fim (dom), próxima segunda


def _aderencia(con, aid, ini, fim):
    rows = con.execute("""SELECT date, type, kind, dist_km, dur_h, tss FROM treinos
                          WHERE atleta_id=? AND date>=? AND date<=?""",
                       (aid, ini.isoformat(), fim.isoformat())).fetchall()
    plan_dias = {r[0] for r in rows if r[1] == "planned"}
    done = [r for r in rows if r[1] == "completed" and ((r[3] or 0) > 0 or (r[4] or 0) > 0 or (r[5] or 0) > 0)]
    done_dias = {r[0] for r in done}
    plan = len(plan_dias)
    feitos = min(plan, len(done_dias))          # feito em outro dia da semana também conta
    km = round(sum((r[3] or 0) for r in done if r[2] == "run"), 1)
    ader = (feitos / plan * 100) if plan else None
    return {"plan": plan, "feitos": feitos, "sessoes": len(done_dias), "km": km, "ader": ader}


def _hrv(con, aid, fim):
    lo = (fim - dt.timedelta(days=29)).isoformat()
    rows = con.execute("""SELECT date, hrv FROM metricas_diarias WHERE atleta_id=? AND date>=? AND date<=?
                          AND hrv IS NOT NULL ORDER BY date""", (aid, lo, fim.isoformat())).fetchall()
    if len(rows) < 5: return None
    vals = [r[1] for r in rows]
    base = statistics.mean(vals); sd = statistics.pstdev(vals) if len(vals) > 2 else 0
    limiar = max(0, base - sd)
    ult7 = [r for r in rows if (fim - dt.date.fromisoformat(r[0])).days < 7]
    abaixo7 = sum(1 for _, v in ult7 if v < limiar)
    m7 = statistics.mean(v for _, v in ult7) if ult7 else None
    alerta = abaixo7 >= 2 or (m7 is not None and m7 < limiar)
    return {"base": round(base, 1), "limiar": round(limiar, 1), "abaixo7": abaixo7,
            "m7": round(m7, 1) if m7 is not None else None, "alerta": alerta, "n7": len(ult7)}


def _forma(con, aid, fim):
    r = con.execute("""SELECT date, ctl, atl, tsb FROM fitness_diario WHERE atleta_id=? AND date<=?
                       ORDER BY date DESC LIMIT 1""", (aid, fim.isoformat())).fetchone()
    return {"date": r[0], "ctl": r[1], "tsb": r[3]} if r else None


def _prova_recente(con, aid, ini, fim):
    r = con.execute("""SELECT date, nome FROM provas WHERE atleta_id=? AND date>=? AND date<=?
                       AND COALESCE(tipo,'')<>'OtherOther' ORDER BY date DESC LIMIT 1""",
                    (aid, ini.isoformat(), fim.isoformat())).fetchone()
    return {"date": r[0], "nome": r[1]} if r else None


def _plano_semanas(con, aid, seg_passada, seg_prox):
    """Semana do plano que fechou e a próxima (se o atleta tem ciclo cobrindo essas datas)."""
    r = con.execute("""SELECT p.id, s.plano_id, s.idx, s.inicio, s.fase, s.km, s.obs
                       FROM periodizacao_semanas s JOIN periodizacao p ON p.id=s.plano_id
                       WHERE p.atleta_id=? AND s.inicio IN (?,?) ORDER BY p.prova_data DESC, s.inicio""",
                    (aid, seg_passada.isoformat(), seg_prox.isoformat())).fetchall()
    out = {}
    for pid, _, idx, ini, fase, km, obs in r:
        if ini not in out: out[ini] = {"plano_id": pid, "idx": idx, "fase": fase, "km": km, "obs": obs or ""}
    return out.get(seg_passada.isoformat()), out.get(seg_prox.isoformat())


def revisar(ref=None):
    ref = ref or dt.date.today()
    ini, fim, seg_prox = _semana(ref)
    ini2 = ini - dt.timedelta(days=7)
    con = db.get_conn(); db.init_db(con)
    ath = con.execute("SELECT id, nome FROM atletas WHERE ativo=1 ORDER BY nome COLLATE NOCASE").fetchall()
    out = []
    for aid, nome in ath:
        a1 = _aderencia(con, aid, ini, fim)
        a2 = _aderencia(con, aid, ini2, ini - dt.timedelta(days=1))
        hrv = _hrv(con, aid, fim); forma = _forma(con, aid, fim); prova = _prova_recente(con, aid, ini, fim)
        sem_passada, sem_prox = _plano_semanas(con, aid, ini, seg_prox)
        tsb = forma["tsb"] if forma else None
        motivos = []
        if not a1["plan"] and not a1["sessoes"]:
            rec = "sem dados"; motivos.append("nada planejado nem realizado na semana")
        elif prova:
            rec = "recuperar"; motivos.append(f"prova {prova['nome']} em {prova['date'][8:10]}/{prova['date'][5:7]}")
        elif (hrv and hrv["alerta"]) or (tsb is not None and tsb <= -25) or \
             (a1["ader"] is not None and a1["ader"] < 60 and tsb is not None and tsb <= -15):
            rec = "aliviar"
            if hrv and hrv["alerta"]: motivos.append(f"HRV em alerta ({hrv['abaixo7']} dias abaixo do limiar {hrv['limiar']} ms)")
            if tsb is not None and tsb <= -25: motivos.append(f"forma {tsb:+.0f}")
            if a1["ader"] is not None and a1["ader"] < 60: motivos.append(f"aderência {a1['ader']:.0f}%")
        elif a1["ader"] is not None and a1["ader"] < 60:
            rec = "manter"; motivos.append(f"aderência {a1['ader']:.0f}% ({a1['feitos']} de {a1['plan']})")
        elif (a1["ader"] is not None and a1["ader"] < 80) or (tsb is not None and tsb <= -20):
            rec = "manter"
            if a1["ader"] is not None and a1["ader"] < 80: motivos.append(f"aderência {a1['ader']:.0f}%")
            if tsb is not None and tsb <= -20: motivos.append(f"forma {tsb:+.0f}")
        elif a1["ader"] is None:
            rec = "manter"; motivos.append(f"sem plano na semana: {a1['sessoes']} treinos e {a1['km']:.0f} km feitos")
        else:
            boas2 = (a2["ader"] is None) or a2["ader"] >= 80
            rec = "progredir" if boas2 else "manter"
            motivos.append(f"aderência {a1['ader']:.0f}%" + (f" e {a2['ader']:.0f}% na anterior" if a2["ader"] is not None else ""))
            if hrv and not hrv["alerta"]: motivos.append("HRV estável")
            if tsb is not None: motivos.append(f"forma {tsb:+.0f}")
        # proposta concreta para a próxima semana do plano (se houver)
        proposta = None
        if sem_prox and sem_prox["km"]:
            km_plan = float(sem_prox["km"]); km_feito = a1["km"]
            if rec == "aliviar": novo = round(km_plan * 0.70)
            elif rec == "recuperar": novo = round(km_plan * 0.50)
            elif rec == "manter": novo = round(min(km_plan, max(km_feito, km_plan * 0.85)))
            else: novo = round(km_plan)
            if novo != round(km_plan):
                proposta = {"plano_id": sem_prox["plano_id"], "inicio": seg_prox.isoformat(), "idx": sem_prox["idx"],
                            "km_atual": round(km_plan), "km_novo": novo,
                            "obs": f"revisão {ref:%d/%m}: {rec} ({'; '.join(motivos)})"}
        out.append({"id": aid, "nome": nome, "semana": f"{ini:%d/%m}–{fim:%d/%m}", "rec": rec, "motivos": motivos,
                    "ader": a1["ader"], "plan": a1["plan"], "feitos": a1["feitos"], "km": a1["km"],
                    "km_plano": (sem_passada or {}).get("km"), "hrv": hrv, "tsb": tsb, "prova": prova,
                    "prox": sem_prox, "proposta": proposta})
    con.close()
    return {"ref": ref.isoformat(), "semana_ini": ini.isoformat(), "semana_fim": fim.isoformat(),
            "proxima": seg_prox.isoformat(), "itens": out}


def aplicar(plano_id, inicio, km_novo, obs_extra):
    """Grava o km revisado na semana do plano e anota o motivo na observação."""
    con = db.get_conn()
    r = con.execute("SELECT obs FROM periodizacao_semanas WHERE plano_id=? AND inicio=?", (int(plano_id), inicio)).fetchone()
    if not r: con.close(); raise ValueError("semana não encontrada no plano")
    obs = (r[0] or "").strip()
    obs = (obs + " · " + obs_extra) if obs else obs_extra
    con.execute("UPDATE periodizacao_semanas SET km=?, obs=? WHERE plano_id=? AND inicio=?",
                (float(km_novo), obs, int(plano_id), inicio))
    con.commit(); con.close()
    return True


ORDEM = {"aliviar": 0, "recuperar": 1, "manter": 2, "progredir": 3, "sem dados": 4}

def resumo_texto(rev, max_itens=12):
    it = sorted(rev["itens"], key=lambda x: (ORDEM.get(x["rec"], 9), x["nome"].lower()))
    cont = {}
    for x in it: cont[x["rec"]] = cont.get(x["rec"], 0) + 1
    linhas = [f"Revisão semanal ({rev['semana_ini'][8:10]}/{rev['semana_ini'][5:7]} a {rev['semana_fim'][8:10]}/{rev['semana_fim'][5:7]}): "
              + ", ".join(f"{v} {k}" for k, v in cont.items())]
    for x in [x for x in it if x["rec"] in ("aliviar", "recuperar")][:max_itens]:
        linhas.append(f"- {x['nome']}: {x['rec']}. {'; '.join(x['motivos'])}" +
                      (f". Plano: {x['proposta']['km_atual']} → {x['proposta']['km_novo']} km" if x["proposta"] else ""))
    n_prog = cont.get("progredir", 0); n_man = cont.get("manter", 0)
    linhas.append(f"Progredir: {n_prog}. Manter: {n_man}. Detalhe e aprovação na aba Revisão do painel.")
    return "\n".join(linhas)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--data"); ap.add_argument("--resumo", action="store_true"); ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    rev = revisar(dt.date.fromisoformat(a.data) if a.data else None)
    if a.json: print(json.dumps(rev, ensure_ascii=False, default=str)); sys.exit()
    if a.resumo: print(resumo_texto(rev)); sys.exit()
    for x in sorted(rev["itens"], key=lambda x: (ORDEM.get(x["rec"], 9), x["nome"].lower())):
        ad = f"{x['ader']:.0f}%" if x["ader"] is not None else "—"
        print(f"{x['rec']:<10} {x['nome'][:26]:<26} ader {ad:>4} · {x['km']:>5.1f} km · {'; '.join(x['motivos'])}"
              + (f" · plano {x['proposta']['km_atual']}→{x['proposta']['km_novo']}" if x["proposta"] else ""))
