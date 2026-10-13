# -*- coding: utf-8 -*-
"""Painel de risco (via banco): carga alta, fadiga, queda de engajamento e
tendências ruins de recuperação — lendo de data/aslab.db.

Uso (CLI, p/ mensagem diária):  python risk.py
"""
import argparse, datetime as dt, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db

def _avg(v):
    v = [x for x in v if x is not None]
    return sum(v)/len(v) if v else None

def risk_flags(month=None, today=None):
    """[{name, acwr, tsb, adh14, flags:[...]}] ordenado por gravidade. (month é ignorado — banco)"""
    today = today or dt.date.today()
    lo14 = (today - dt.timedelta(days=14)).isoformat()
    lo21 = (today - dt.timedelta(days=21)).isoformat()
    lo7  = (today - dt.timedelta(days=7)).isoformat()
    hoje = today.isoformat()
    con = db.get_conn(); db.init_db(con)
    rows = []
    for aid, nome in con.execute("SELECT id, nome FROM atletas WHERE ativo=1 ORDER BY nome"):
        flags = []
        # 1) carga (ACWR ~ ATL/CTL) e fadiga (TSB) — último dia de fitness disponível
        cur = con.execute("""SELECT ctl, atl, tsb FROM fitness_diario
                             WHERE atleta_id=? AND date<=? ORDER BY date DESC LIMIT 1""",
                          (aid, hoje)).fetchone()
        ctl, atl, tsb = cur if cur else (None, None, None)
        acwr = (atl/ctl) if (ctl and atl is not None and ctl >= 25) else None
        if acwr is not None and acwr >= 1.5: flags.append("🔺 carga alta (ACWR %.1f)" % acwr)
        if tsb is not None and tsb <= -25:   flags.append("🟠 fadiga acumulada (TSB %.0f)" % tsb)

        # 2) engajamento: aderência nos últimos 14 dias
        pl, dn = con.execute("""SELECT
              SUM(CASE WHEN type='planned' THEN 1 ELSE 0 END),
              SUM(CASE WHEN type='completed' AND was_planned=1 THEN 1 ELSE 0 END)
            FROM treinos WHERE atleta_id=? AND date>=? AND date<?""",
            (aid, lo14, hoje)).fetchone()
        pl = pl or 0; dn = dn or 0
        tot = pl + dn
        adh14 = (dn/tot*100) if tot else None
        if tot >= 4 and adh14 is not None and adh14 < 50:
            flags.append("📉 engajamento (%.0f%% em 14d)" % adh14)

        # 3) recuperação: HRV caindo / FC repouso subindo (séries do banco)
        serie = con.execute("""SELECT date, fc_rep, hrv FROM metricas_diarias
                               WHERE atleta_id=? AND date>=? AND date<=? ORDER BY date""",
                            (aid, lo21, hoje)).fetchall()
        hrv  = [x[2] for x in serie]
        fcr  = [x[1] for x in serie]
        hrv7 = _avg([x[2] for x in serie if x[0] >= lo7]); hrv21 = _avg(hrv)
        fc7  = _avg([x[1] for x in serie if x[0] >= lo7]); fc21  = _avg(fcr)
        if hrv7 and hrv21 and len([x for x in hrv if x]) >= 10 and hrv7 < hrv21*0.90:
            flags.append("💗 HRV em queda (%.0f→%.0f)" % (hrv21, hrv7))
        if fc7 and fc21 and len([x for x in fcr if x]) >= 10 and fc7 > fc21 + 4:
            flags.append("❤️ FC repouso subindo (%.0f→%.0f)" % (fc21, fc7))

        if flags:
            rows.append({"name": nome, "acwr": acwr, "tsb": tsb, "adh14": adh14, "flags": flags})
    con.close()
    rows.sort(key=lambda x: (-len(x["flags"]), x["name"].lower()))
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=None)   # compat; ignorado
    a = ap.parse_args()
    rows = risk_flags(a.month)
    if not rows:
        print("Nenhum atleta sinalizado — tudo sob controle. ✅"); return
    print(f"⚠️ {len(rows)} atleta(s) merecem atenção:")
    for r in rows:
        print(f'- {r["name"]}: ' + " · ".join(r["flags"]))

if __name__ == "__main__":
    main()
