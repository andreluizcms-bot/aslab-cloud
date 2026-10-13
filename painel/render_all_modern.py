# -*- coding: utf-8 -*-
"""Gera um PDF por atleta (com corrida) no layout MODERNO. Monta o ZIP.
Uso: python render_all_modern.py --month 2026-06
"""
import json, glob, os, datetime as dt, re, unicodedata, argparse, calendar, zipfile
from report import compute, build_refs, coach_message, has_sport, excluded_ids, is_active
try:
    from report_modern import render_modern
except Exception:              # nuvem: sem a fonte do macOS, os PDFs saem do Mac
    render_modern = None
import render_all as ra

BASE=os.path.dirname(os.path.abspath(__file__))
EXC_IDS=excluded_ids()
MESES=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
       "setembro","outubro","novembro","dezembro"]

def slug(s):
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+","_",s).strip("_") or "atleta"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--month",required=True); ap.add_argument("--only",default=None)
    a=ap.parse_args()
    y,m=map(int,a.month.split("-")); last=calendar.monthrange(y,m)[1]
    START,END=dt.date(y,m,1),dt.date(y,m,last)
    PERIOD=f"01/{m:02d}/{y} – {last}/{m:02d}/{y}"; PREV=MESES[(m-2)%12][:3]
    DATA=os.path.join(BASE,"data",a.month)
    OUT=os.path.join(BASE,"saida",a.month); os.makedirs(OUT,exist_ok=True)
    only=a.only.lower() if a.only else None
    msgs_path=os.path.join(DATA,"_messages.json")
    MSGS=json.load(open(msgs_path)) if os.path.exists(msgs_path) else {}
    made=[]; made_paths=[]; skipped=[]
    for f in sorted(glob.glob(os.path.join(DATA,"*.json"))):
        if os.path.basename(f).startswith("_"): continue
        if os.path.basename(f).replace(".json","") in EXC_IDS: continue
        if not is_active(os.path.basename(f).replace(".json","")): continue
        r=json.load(open(f)); name=ra.titlecase(r["name"])
        if only and only not in name.lower(): continue
        if not has_sport(r): skipped.append(name); continue
        W=[{**w,"date":dt.date.fromisoformat(w["date"][:10])} for w in r["workouts"]]
        refs=build_refs(r.get("settings",{}))
        data=compute(name,PERIOD,PREV,START,END,W,r.get("prev"),r.get("fitness"),r.get("event"),r.get("photo"),refs)
        data["id"]=r["id"]; data["metrics"]=r.get("metrics")
        if data["total_completed"]==0 or (data["run_km"]<=0 and data.get("bike_km",0)<=0 and data.get("str_n",0)==0 and sum(data.get(k,0) or 0 for k in ("run_n","bike_n","walk_n","swim_n","other_n"))==0): skipped.append(name); continue
        data["coach_msg"]=MSGS.get(str(r["id"])) or coach_message(data)
        out=os.path.join(OUT,f'{slug(name)}_{MESES[m-1]}_{y}.pdf')
        try:
            render_modern(data,out); made.append(name); made_paths.append(out)
        except Exception as e:
            skipped.append(f"{name} (ERRO: {e})")
    # ---- higiene: a pasta e o ZIP devem conter SÓ alunos dos grupos ativos ----
    import shutil as _sh
    _slugs_ok=set()
    try:
        import sqlite3 as _sq
        _c=_sq.connect(os.path.join(BASE,"data","aslab.db"))
        _slugs_ok={slug(ra.titlecase(x[0])) for x in _c.execute("SELECT nome FROM atletas WHERE ativo=1")}
        _c.close()
    except Exception as e:
        print(f"(aviso: não consegui checar o roster p/ limpeza: {e})")
    fora=0
    if _slugs_ok:
        _arq=os.path.join(BASE,"saida","_fora_dos_grupos",a.month); os.makedirs(_arq, exist_ok=True)
        for _p in glob.glob(os.path.join(OUT,"*")):
            _b=os.path.basename(_p)
            if not (_b.endswith(".pdf") or _b.endswith("_preview.png")): continue
            _base=_b.replace("_preview.png","").replace(".pdf","")
            if "_".join(_base.split("_")[:-2]) not in _slugs_ok:
                _sh.move(_p, os.path.join(_arq,_b)); fora+=1
        if fora: print(f"({fora} arquivo(s) de fora dos grupos movidos p/ saida/_fora_dos_grupos/{a.month})")
    zip_path=os.path.join(BASE,f'Relatorios_{MESES[m-1]}_{y}.zip')
    _todos=sorted(glob.glob(os.path.join(OUT,"*.pdf")))     # só alunos dos grupos (pós-limpeza)
    with zipfile.ZipFile(zip_path,"w",zipfile.ZIP_DEFLATED) as z:
        for p in _todos: z.write(p,os.path.basename(p))
    print(f"Gerados: {len(made)}  |  Sem corrida/pulados: {len(skipped)}  |  ZIP: {len(_todos)} PDFs")
    errs=[s for s in skipped if "ERRO" in s]
    if errs: print("ERROS:", " | ".join(errs))
    print("ZIP:", zip_path); print("PASTA:", OUT)

if __name__=="__main__":
    main()
