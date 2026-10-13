# -*- coding: utf-8 -*-
"""Gera um PDF por atleta (com corrida no mês) a partir dos JSON coletados.

Uso:
    python render_all.py --month 2026-06
    python render_all.py --month 2026-06 --only robson   # filtra por nome
"""
import json, glob, os, datetime as dt, re, unicodedata, argparse, calendar, zipfile
from report import compute, render, build_refs, coach_message

BASE = os.path.dirname(os.path.abspath(__file__))
MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
         "setembro","outubro","novembro","dezembro"]

def slug(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+","_",s).strip("_") or "atleta"

def titlecase(name):
    small={"de","da","do","dos","das","e"}
    return " ".join(w if w.lower() in small else w.capitalize() for w in name.split())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True); ap.add_argument("--only", default=None)
    args = ap.parse_args()
    y, m = map(int, args.month.split("-"))
    last = calendar.monthrange(y, m)[1]
    START, END = dt.date(y,m,1), dt.date(y,m,last)
    PERIOD = f"01/{m:02d}/{y} – {last}/{m:02d}/{y}"
    PREV_LABEL = MESES[(m-2) % 12][:3]
    DATA = os.path.join(BASE, "data", args.month)
    OUT  = os.path.join(BASE, "saida", args.month); os.makedirs(OUT, exist_ok=True)
    only = args.only.lower() if args.only else None
    # recados escritos por IA (id -> texto). Fallback: gerador por regras.
    msgs_path = os.path.join(DATA, "_messages.json")
    MSGS = json.load(open(msgs_path)) if os.path.exists(msgs_path) else {}
    made=[]; skipped=[]; unconf=[]
    for f in sorted(glob.glob(os.path.join(DATA,"*.json"))):
        if os.path.basename(f).startswith("_"): continue  # arquivos auxiliares (_messages, _summaries, _msg_batch_*)
        r=json.load(open(f)); name=titlecase(r["name"])
        if only and only not in name.lower(): continue
        if not r.get("has_run"): skipped.append(name); continue
        W=[{**w,"date":dt.date.fromisoformat(w["date"][:10])} for w in r["workouts"]]
        refs=build_refs(r.get("settings",{}))
        data=compute(name,PERIOD,PREV_LABEL,START,END,W,r.get("prev"),r.get("fitness"),
                     r.get("event"),r.get("photo"),refs)
        data["id"]=r["id"]
        if data["total_completed"]==0 or data["run_km"]<=0: skipped.append(name); continue
        data["coach_msg"]=MSGS.get(str(r["id"])) or coach_message(data)
        out=os.path.join(OUT,f'{slug(name)}_{MESES[m-1]}_{y}.pdf')
        try:
            render(data,out); made.append(name)
            if refs["unconfigured"]: unconf.append(name)
        except Exception as e:
            skipped.append(f"{name} (ERRO: {e})")
    # zip
    zip_path=os.path.join(BASE, f'Relatorios_{MESES[m-1]}_{y}.zip')
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
        for p in sorted(glob.glob(os.path.join(OUT,"*.pdf"))): z.write(p, os.path.basename(p))
    print(f"Gerados: {len(made)}  |  Sem corrida/pulados: {len(skipped)}")
    if unconf: print("Zonas de FC nao configuradas no TP (LTHR~=FCmax):", ", ".join(unconf))
    print("PULADOS:", ", ".join(skipped) if skipped else "nenhum")
    print("ZIP:", zip_path)
    print("PASTA:", OUT)

if __name__=="__main__":
    main()
