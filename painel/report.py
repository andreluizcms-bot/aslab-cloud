# -*- coding: utf-8 -*-
"""Gerador de Relatório Mensal de Treino LIMIAR (2 páginas, layout neutro)."""
import os, math, io, datetime as dt, textwrap, urllib.request
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ---------- paleta (petróleo/teal + coral + âmbar) ----------
NAVY   = (0.063, 0.239, 0.306)
NAVY_BAR=(0.078, 0.345, 0.420)
LTBLUE = (0.435, 0.702, 0.753)
ORANGE = (0.933, 0.424, 0.302)
YELLOW = (0.949, 0.647, 0.255)
RED    = (0.757, 0.286, 0.353)
PINK   = (0.965, 0.851, 0.824)
GREEN  = (0.220, 0.620, 0.415)
GREY   = (0.353, 0.420, 0.482)
LGREY  = (0.933, 0.949, 0.965)
WHITE  = (1,1,1)

HX_PRIM  = "#103d4e"; HX_CORAL = "#ee6c4d"; HX_CORALD= "#c65535"
HX_TEAL  = "#3f8ea0"; HX_RED   = "#c1495a"; HX_AMBER = "#f2a541"
HX_PINK  = "#f6dcd6"; HX_GREYT = "#5a6b7b"; HX_GREYL = "#c9d3dc"; HX_GREEN = "#38a06a"

W, H = A4
SCRATCH = os.path.dirname(os.path.abspath(__file__))
AVDIR = os.path.join(SCRATCH, "data", "avatars"); os.makedirs(AVDIR, exist_ok=True)

# ---------- marca ----------
BRAND     = "LIMIAR"
TAGLINE   = "Performance & Endurance"
SIGNATURE = "André Santos"

def fmt_pace(mpk):
    if not mpk or mpk<=0 or math.isinf(mpk): return "–"
    m=int(mpk); s=int(round((mpk-m)*60))
    if s==60: m+=1; s=0
    return f"{m}:{s:02d}/km"

def monday(d): return d-dt.timedelta(days=d.weekday())

def mmss(mpk):
    if not mpk or mpk<=0: return "–"
    m=int(mpk); s=int(round((mpk-m)*60))
    if s==60: m+=1; s=0
    return f"{m}:{s:02d}"

def initials(name):
    parts=[p for p in name.split() if p]
    if not parts: return "?"
    if len(parts)==1: return parts[0][:2].upper()
    return (parts[0][0]+parts[-1][0]).upper()

def avatar_path(aid, url):
    """Baixa (e cacheia) a foto do atleta; retorna caminho local ou None."""
    if not url: return None
    p=os.path.join(AVDIR, f"{aid}.img")
    if os.path.exists(p) and os.path.getsize(p)>200: return p
    try:
        req=urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data=r.read()
        if len(data)<200: return None
        open(p,"wb").write(data); return p
    except Exception:
        return None

def days_to_event(event, ref):
    if not event or not event.get("date"): return None
    try: ed=dt.date.fromisoformat(event["date"])
    except Exception: return None
    return (ed-ref).days

def form_status(tsb):
    if tsb is None: return "–"
    if tsb>15: return "muito descansado"
    if tsb>5:  return "fresco / em forma"
    if tsb>=-10: return "equilíbrio"
    if tsb>=-30: return "carga produtiva"
    return "fadiga alta"

# cores p/ zonas
_GREEN=(0.357,0.686,0.490); _GOLD=(0.949,0.722,0.255); _ORG=(0.933,0.510,0.220)
_ORG2=(0.886,0.384,0.220); _RED=(0.796,0.259,0.243); _DRED=(0.588,0.114,0.153)
_BLUE=(0.435,0.702,0.753)

def build_refs(settings):
    hz=(settings.get("heartRateZones") or [{}])[0]
    sz=(settings.get("speedZones") or [{}])[0]
    lthr=hz.get("threshold") or 0
    fcmax=hz.get("maximumHeartRate") or 0
    thr=sz.get("threshold")
    pace_T=(1000/(thr*60)) if thr else None
    unconfigured = (not lthr) or (fcmax and lthr>=fcmax)
    hrspec=[("Z2",0.81,0.89,_GREEN,0.18),("Z3",0.90,0.93,_GOLD,0.12),
            ("Z4",0.94,0.99,_ORG,0.14),("Z5A",1.00,1.02,_ORG2,0.10),
            ("Z5B",1.03,1.06,_RED,0.08),("Z5C",1.07,1.15,_DRED,0.38)]
    hr_zones=[]
    for lab,lo,hi,col,fr in hrspec:
        if lthr:
            r=f"{round(lthr*lo)}–{round(lthr*hi)}" + (" bpm" if lab in("Z2","Z5C") else "")
        else: r="–"
        hr_zones.append((lab,fr,col,r))
    pspec=[("Z1",1.25,None,_BLUE),("Z2",1.16,1.25,_GREEN),("Z3",1.10,1.16,(0.42,0.72,0.52)),
           ("Z4",1.06,1.10,_GOLD),("Z5",1.00,1.06,(0.95,0.62,0.22)),("Z6",0.97,1.00,_ORG),
           ("Z7",0.93,0.97,_ORG2),("Z8",0.90,0.93,_RED),("Z9",0.87,0.90,(0.70,0.16,0.18)),
           ("Z10",None,0.87,_DRED)]
    pace_zones=[]
    for spec in pspec:
        lab=spec[0]; col=spec[-1]
        if not pace_T: rng="–"
        elif lab=="Z1": rng=f">{mmss(pace_T*spec[1])}"
        elif lab=="Z10": rng=f"<{mmss(pace_T*spec[2])}"
        else: rng=f"{mmss(pace_T*spec[2])}–{mmss(pace_T*spec[1])}"
        pace_zones.append((lab,rng,col))
    return {"lthr":round(lthr) if lthr else 0, "fcmax":round(fcmax) if fcmax else 0,
            "pace_lim":(mmss(pace_T)+"/km") if pace_T else "–",
            "pace_T":pace_T, "pace_pspec":pspec,
            "hr_zones":hr_zones,"pace_zones":pace_zones,"unconfigured":unconfigured}

# ================= COMPUTE =================
def excluded_ids():
    """IDs de atletas excluídos do app/relatórios (grupo 'Não é mais atleta' do TP).
    Editável em excluded.json na raiz do projeto."""
    import json as _json
    p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"excluded.json")
    try: return set(str(x) for x in _json.load(open(p)).get("ids",[]))
    except Exception: return set()

def active_ids():
    """IDs dos atletas atualmente na conta do TP (data/roster.json, gravado pela coleta).
    None se o arquivo não existe (sem filtro)."""
    import json as _json
    p=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","roster.json")
    try: return set(str(x) for x in _json.load(open(p)).get("ids",[]))
    except Exception: return None

def is_active(aid):
    r=active_ids()
    return True if r is None else str(aid) in r

def has_sport(rec):
    """Atleta conta no período se tem QUALQUER treino feito com tempo de
    treino — corrida, bike, força, natação, caminhada ou 'outros' (elíptico,
    cardio de academia...). Bike sem distância (indoor) e atividades sem km
    entram pela duração."""
    if rec.get("has_run"): return True
    for w in rec.get("workouts",[]):
        if w.get("type")!="completed": continue
        if (w.get("dur_h") or 0)>0 or (w.get("dist_km") or 0)>0 or (w.get("tss") or 0)>0:
            return True
    return False

_DIAS_ABR=["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
_MES_ABR=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

def compute(name, period_label, prev_label, start, end, workouts, prev, fitness, event, photo, refs, bucket="week"):
    lthr=refs["lthr"]
    _SPK={"Run":"run","Bike":"bike","MtnBike":"bike","Strength":"strength","Walk":"walk","Swim":"swim"}
    for w in workouts:                       # normaliza esportes em dados antigos (kind era "other")
        if w.get("wt")==2: w["kind"]="bike"
        elif w.get("wt")==8: w["kind"]="bike"          # 8 = Mountain Bike
        elif w.get("wt")==9: w["kind"]="strength"
        elif w.get("wt")==1: w["kind"]="swim"
        elif w.get("kind") in (None,"other") and w.get("sport") in _SPK:
            w["kind"]=_SPK[w["sport"]]
    completed=[w for w in workouts if w["type"]=="completed"]
    planned  =[w for w in workouts if w["type"]=="planned"]
    runs     =[w for w in completed if w["kind"]=="run"]
    bikes    =[w for w in completed if w["kind"]=="bike"]
    strengths=[w for w in completed if w["kind"]=="strength"]
    swims    =[w for w in completed if w["kind"]=="swim"]
    walks    =[w for w in completed if w["kind"]=="walk"]
    others   =[w for w in completed if w["kind"]=="other"]
    # ---- aderência por SEMANA: treino feito em outro dia da mesma semana conta ----
    # O TP só marca was_planned quando o feito cai no dia exato do plano. Aqui,
    # um planejado "perdido" é casado com um treino avulso do MESMO esporte na
    # MESMA semana (seg-dom): sai dos perdidos e entra na aderência.
    extras=[w for w in completed if not w.get("was_planned")]
    usados=set(); restantes=[]
    for pw in planned:
        sem_p=monday(pw["date"])
        cand=next((i for i,c in enumerate(extras)
                   if i not in usados and c.get("kind")==pw.get("kind")
                   and monday(c["date"])==sem_p), None)
        if cand is None:
            restantes.append(pw)
        else:
            usados.add(cand)
            extras[cand]["was_planned"]=True      # cumpriu o plano, só mudou o dia
            extras[cand]["fora_do_dia"]=True
            pw["feito_outro_dia"]=extras[cand]["date"]
    planned=restantes

    planned_done=[w for w in completed if w.get("was_planned")]
    total_plan=len(planned_done)+len(planned)
    adher=(len(planned_done)/total_plan*100) if total_plan else 0
    run_km=sum(w["dist_km"] for w in runs); peak_km=max([w["dist_km"] for w in runs],default=0)
    bike_km=sum(w["dist_km"] for w in bikes)
    str_h=sum(w["dur_h"] for w in strengths)

    # buckets: por semana (relatório mensal) ou por dia (relatório semanal)
    buckets={}; order=[]
    if bucket=="day":
        k=start
        while k<=end: buckets[k]=[]; order.append(k); k+=dt.timedelta(days=1)
        keyfn=lambda w: w["date"]
        labfn=lambda k: _DIAS_ABR[k.weekday()]
    elif bucket=="month":
        k=start.replace(day=1)
        while k<=end:
            buckets[k]=[]; order.append(k)
            k=(k+dt.timedelta(days=32)).replace(day=1)
        keyfn=lambda w: w["date"].replace(day=1)
        labfn=lambda k: _MES_ABR[k.month-1]
    else:
        k=monday(start)
        while k<=end: buckets[k]=[]; order.append(k); k+=dt.timedelta(days=7)
        keyfn=lambda w: monday(w["date"])
        labfn=lambda k: k.strftime("%d/%m")
    for w in completed:
        kk=keyfn(w)
        if kk in buckets: buckets[kk].append(w)
    active_weeks=sum(1 for k in order if buckets[k])
    weekly=[]
    for k in order:
        ws=buckets[k]
        rk=sum(x["dist_km"] for x in ws if x["kind"]=="run")
        bk=sum(x["dist_km"] for x in ws if x["kind"]=="bike")
        hrs=sum(x["dur_h"] for x in ws); tss=sum(x["tss"] for x in ws)
        hl=[x["hr"] for x in ws if x["kind"]=="run" and x.get("hr")]
        fc=round(sum(hl)/len(hl)) if hl else None
        weekly.append({"label":labfn(k),"km":rk,"bkm":bk,"hrs":hrs,"tss":tss,"sess":len(ws),"fc":fc})

    hr_all=[w["hr"] for w in runs if w.get("hr")]; fc_med=round(sum(hr_all)/len(hr_all)) if hr_all else None
    cad_all=[w["cad"] for w in runs if w.get("cad")]; cad_med=round(sum(cad_all)/len(cad_all)) if cad_all else None
    for w in runs: w["pace"]=(w["dur_h"]*60)/w["dist_km"] if w["dist_km"]>0 else None
    pace_all=[w["pace"] for w in runs if w.get("pace")]
    pace_med=sum(pace_all)/len(pace_all) if pace_all else None
    highlights=sorted(sorted(runs,key=lambda x:x["dist_km"],reverse=True)[:6],key=lambda x:x["date"])

    # distribuição de intensidade (proxy por %LTHR da FC média de cada corrida)
    easy=mod=hard=nohr=0
    for w in runs:
        hr=w.get("hr")
        if not hr or not lthr:
            if w["dist_km"]>0: nohr+=1
            continue
        r=hr/lthr
        if r<0.90: easy+=1
        elif r<1.00: mod+=1
        else: hard+=1
    tot_i=easy+mod+hard
    hard_share=hard/tot_i if tot_i else 0
    easy_share=easy/tot_i if tot_i else 0
    # FC média mensal >= LTHR + muita corrida "forte" => LTHR provavelmente baixo (config)
    lthr_suspect=bool(tot_i>=4 and lthr and fc_med and fc_med>=lthr*0.98 and hard_share>=0.5)
    if tot_i==0: note=None
    elif lthr_suspect: note=f"Maioria das corridas com FC ≥ LTHR ({lthr}). Se o esforço foi tranquilo, o LTHR pode estar baixo. Vale reavaliar."
    elif easy_share>=0.65: note=f"{easy_share*100:.0f}% em ritmo fácil, boa base aeróbia."
    elif hard_share>=0.4: note="Bom volume de treino forte; garanta os fáceis bem fáceis."
    else: note="Mix equilibrado de intensidades."
    intens={"easy":easy,"mod":mod,"hard":hard,"nohr":nohr,"note":note,"lthr_suspect":lthr_suspect}

    # destaques do mês
    runs_valid=[w for w in runs if w["dist_km"]>0]
    rec_dist=max(runs_valid,key=lambda x:x["dist_km"],default=None)
    pace_runs=[w for w in runs_valid if w["dist_km"]>=2 and w.get("pace")]
    rec_pace=min(pace_runs,key=lambda x:x["pace"]) if pace_runs else None
    rec_tss=max(runs_valid,key=lambda x:x["tss"],default=None)
    elev_total=sum((w.get("elev") or 0) for w in runs)

    return {"name":name,"period":period_label,"prev_label":prev_label,"photo":photo,
            "all_workouts":sorted(completed,key=lambda x:x["date"]),
            "sess_done":len(planned_done),"sess_plan":total_plan,
            "adher":adher,"total_completed":len(completed),"run_km":run_km,"peak_km":peak_km,
            "bike_km":bike_km,"bike_n":len(bikes),"str_n":len(strengths),"str_h":str_h,
            "run_n":len(runs),
            "swim_km":sum(w["dist_km"] for w in swims),"swim_n":len(swims),
            "walk_km":sum(w["dist_km"] for w in walks),"walk_n":len(walks),
            "other_n":len(others),"other_h":sum(w["dur_h"] for w in others),
            "missed":len(planned),"missed_pct":(len(planned)/total_plan*100) if total_plan else 0,
            "active_weeks":active_weeks,"n_weeks":len(order),"weekly":weekly,"highlights":highlights,
            "planned_missed":planned,"fc_med":fc_med,"cad_med":cad_med,"pace_med":pace_med,
            "prev":prev,"fitness":fitness,"event":event,"intens":intens,
            "rec_dist":rec_dist,"rec_pace":rec_pace,"rec_tss":rec_tss,"elev_total":elev_total,
            "start":start,"end":end,"refs":refs}

def coach_message(data):
    first=data["name"].split()[0].title()
    adh=data["adher"]; km=data["run_km"]; peak=data["peak_km"]; miss=data["missed"]
    done=data["total_completed"]; sess_done=data["sess_done"]; pl=data["prev_label"]
    prev=data["prev"]; it=data["intens"]; fit=data["fitness"]; ev=data["event"]
    fcs=[w["fc"] for w in data["weekly"] if w["fc"]]

    sem_km = km<=0 and done>0
    if sem_km:
        # mês sem km de corrida (indoor, elíptico, caminhada, força): fala de sessões e horas
        horas=sum((w.get("dur_h") or 0) for w in data.get("all_workouts",[]))
        partes=[]
        if data.get("bike_km",0)>0: partes.append(f'{data["bike_km"]:.0f} km de bike')
        elif data.get("bike_n",0): partes.append(f'{data["bike_n"]} pedal(is) indoor')
        if data.get("str_n",0)>0: partes.append(f'{data["str_n"]} sessões de força')
        if data.get("run_n",0): partes.append(f'{data["run_n"]} corrida(s) sem distância registrada')
        if data.get("walk_n",0): partes.append(f'{data["walk_n"]} caminhada(s)')
        if data.get("other_n",0): partes.append(f'{data["other_n"]} atividade(s) extra')
        corpo=" e ".join(partes) if partes else f"{done} sessões"
        s=[f"{first}, mês sem corrida com distância no registro, mas com trabalho feito: {corpo}, {_fmt_hm(horas)} no total."]
        if data.get("run_n",0): s.append("Se correu na esteira, vale ligar o relógio para a distância entrar no relatório.")
    elif adh>=85: s=[f"{first}, mês muito bem entregue: {sess_done} das sessões planejadas cumpridas e {km:.0f} km somados."]
    elif adh>=60: s=[f"{first}, mês de boa constância: {done} sessões realizadas e {km:.0f} km na perna."]
    else: s=[f"{first}, o mês teve altos e baixos, mas você somou {done} sessões e {km:.0f} km."]

    if prev and prev.get("run_km") and not sem_km:
        d=km-prev["run_km"]
        if abs(d)>=3:
            s.append(f"Foram {abs(d):.0f} km {'a mais' if d>0 else 'a menos'} que em {pl}.")
    if data.get("bike_km",0)>=10:
        s.append(f"No pedal, mais {data['bike_km']:.0f} km. Bom trabalho cruzado.")
    if data.get("swim_km",0)>=2:
        s.append(f"Na água, {data['swim_km']:.1f} km de natação.")
    if data.get("str_n",0)>=4:
        s.append(f"E {data['str_n']} sessões de força no mês, base que protege de lesão.")
    if peak>=15: s.append(f"O ponto alto foi o longo de {peak:.0f} km.")

    tot=it["easy"]+it["mod"]+it["hard"]
    if tot>=4:
        if it.get("lthr_suspect"):
            s.append(f"Boa parte das corridas ficou com FC no limiar ou acima. Se foram tranquilas, revise seu LTHR ({data['refs']['lthr']} bpm) para as zonas baterem certo.")
        elif it["easy"]/tot>=0.65: s.append("A base ficou bem aeróbia: maioria dos treinos em ritmo fácil, do jeito que sustenta evolução.")
        elif it["hard"]/tot>=0.4: s.append("Teve bastante treino forte no mês; garanta os fáceis bem fáceis para absorver a carga.")

    if len(fcs)>=2:
        if fcs[-1] < fcs[0]-3: s.append("A FC média foi caindo para o mesmo esforço. Bom sinal de adaptação aeróbia.")
        elif fcs[-1] > fcs[0]+3: s.append("A FC média subiu no fim do mês. Olhe sono e recuperação.")

    if fit and fit.get("current"):
        cur=fit["current"]; tsb=cur.get("tsb")
        if tsb is not None:
            if tsb< -15: s.append("Você fechou o mês com fadiga acumulada. Uma semana mais leve cai bem antes de puxar de novo.")
            elif tsb>10: s.append("Terminou o mês descansado e com forma em alta. Bom momento para um teste ou prova.")

    if miss>=3: s.append(f"Ficaram {miss} sessões pelo caminho; proteger os dias-chave rende ganho rápido no próximo ciclo.")
    elif miss>=1: s.append(f"Só {miss} sessão(ões) ficou(ram) para trás, quase plano cheio.")

    if ev:
        dtoev=days_to_event(ev, data["end"])
        if dtoev is not None and dtoev>0:
            s.append(f"Foco agora na {ev['name']} ({dt.date.fromisoformat(ev['date']).strftime('%d/%m')}), faltam {dtoev} dias.")

    s.append(f"Segue firme. {SIGNATURE}")
    return " ".join(s)

def coach_message_periodo(data, meses_n):
    """Recado para relatório de período (3/6/9 meses), visão de tendência."""
    first=data["name"].split()[0].title()
    km=data["run_km"]; sess=data["total_completed"]
    s=[f"{first}, balanço dos últimos {meses_n} meses: {km:.0f} km de corrida em {sess} treinos."]
    wk=[w for w in data["weekly"] if w["km"]>0]
    if len(wk)>=2:
        best=max(wk,key=lambda x:x["km"])
        s.append(f"Melhor mês: {best['label']}, com {best['km']:.0f} km.")
        if wk[-1]["km"]>wk[0]["km"]*1.15: s.append("Volume em tendência de alta, construção consistente.")
        elif wk[-1]["km"]<wk[0]["km"]*0.85: s.append("Volume caiu no fim do período. Vale entender o que atrapalhou.")
    if data.get("bike_km",0)>=20: s.append(f"No pedal, {data['bike_km']:.0f} km somados.")
    if data.get("str_n",0)>=6: s.append(f"{data['str_n']} sessões de força no período, constância que protege.")
    prev=data.get("prev")
    if prev and prev.get("run_km") and prev["run_km"]>=30:
        dd=km-prev["run_km"]
        if abs(dd)>=15:
            s.append(f"{'+' if dd>0 else '-'}{abs(dd):.0f} km vs os {meses_n} meses anteriores.")
    fcs=[w["fc"] for w in data["weekly"] if w["fc"]]
    if len(fcs)>=3:
        if fcs[-1]<fcs[0]-3: s.append("FC média caindo ao longo do período. Bom sinal de adaptação aeróbia.")
    ev=data.get("event")
    if ev:
        dtoev=days_to_event(ev, data["end"])
        if dtoev is not None and dtoev>0:
            s.append(f"Próximo alvo: {ev['name']}, em {dtoev} dias.")
    s.append(f"Segue firme. {SIGNATURE}")
    return " ".join(s)

def provas_do_atleta(aid, ini, fim):
    """Provas do atleta no banco (todas, não só a próxima) entre ini e fim (date)."""
    if not aid: return []
    try:
        import db as _db
        con=_db.get_conn()
        rows=con.execute("""SELECT date, nome, tipo FROM provas WHERE atleta_id=? AND date>=? AND date<=?
                            ORDER BY date""", (str(aid), ini.isoformat(), fim.isoformat())).fetchall()
        con.close()
    except Exception:
        return []
    out=[]
    for d,nome,tipo in rows:
        if (tipo or "")=="OtherOther": continue          # anotações (viagem etc.) não são prova
        try: out.append({"date":dt.date.fromisoformat(d), "name":(nome or "").strip(), "type":tipo})
        except Exception: pass
    return out

def _fmt_hm(h):
    m=int(round((h or 0)*60)); return f"{m//60}h{m%60:02d}" if m>=60 else f"{m} min"

def coach_message_semana(data, limite=480):
    """Recado da semana: números, contexto de prova (na semana, à frente ou recém-feita),
    leitura da carga e foco da próxima semana. Frases têm prioridade: quando não cabe
    no quadro do PDF, as de menor prioridade saem primeiro."""
    first=data["name"].split()[0].title()
    ws, we = data["start"], data["end"]
    km=data["run_km"]; sess=data["total_completed"]
    horas=sum((w.get("dur_h") or 0) for w in data.get("all_workouts",[]))
    plan=data.get("sess_plan") or 0; feitos=data.get("sess_done") or 0
    fr=[]   # (prioridade, frase) — 1 fica sempre, números maiores saem primeiro

    # ---- 1. o que foi feito ----
    if not sess:
        fr.append((1, f"{first}, semana sem treino registrado no TrainingPeaks."))
    else:
        partes=[]
        if km>=1: partes.append(f"{km:.0f} km de corrida")
        if data.get("bike_km",0)>=5: partes.append(f"{data['bike_km']:.0f} km de bike")
        elif data.get("bike_n",0): partes.append(f"{data['bike_n']} pedal(is)")
        if data.get("str_n",0): partes.append(f"{data['str_n']} de força")
        if data.get("swim_km",0)>=1: partes.append(f"{data['swim_km']:.1f} km de natação")
        if data.get("other_n",0): partes.append(f"{data['other_n']} atividade(s) extra")
        corpo=", ".join(partes) if partes else f"{sess} treino(s)"
        fr.append((1, f"{first}, sua semana fechou com {corpo}, {sess} treino(s) e {_fmt_hm(horas)} no total."))
        if plan: fr.append((3, f"Do planejado, {feitos} de {plan} sessões cumpridas."))
    prev=data.get("prev")
    if prev and prev.get("run_km") and prev["run_km"]>=5 and km>=1:
        d=km-prev["run_km"]
        if abs(d)>=2: fr.append((6, f"São {abs(d):.0f} km {'a mais' if d>0 else 'a menos'} que na semana anterior."))
    if data["peak_km"]>=8: fr.append((7, f"O treino mais longo foi de {data['peak_km']:.0f} km."))

    # ---- 2. provas ----
    provas=provas_do_atleta(data.get("id"), ws-dt.timedelta(days=14), we+dt.timedelta(days=70))
    na_semana=[p for p in provas if ws<=p["date"]<=we]
    futuras=[p for p in provas if p["date"]>we]
    recentes=[p for p in provas if p["date"]<ws]
    hoje=dt.date.today()
    fase=None; olhar_frente=True
    if na_semana:
        p=na_semana[0]
        do_dia=[w for w in data.get("all_workouts",[]) if w.get("date")==p["date"]]
        w=max(do_dia, key=lambda x:(x.get("dist_km") or 0), default=None)
        if w and (w.get("dist_km") or 0)>=1:
            res=f"{w['dist_km']:.1f} km em {_fmt_hm(w.get('dur_h'))}"
            if w.get("pace"): res+=f", pace {fmt_pace(w['pace'])}"
            if w.get("hr"): res+=f", FC média {w['hr']:.0f}"
            fr.append((1, f"Semana de prova: {p['name']} em {p['date']:%d/%m}, registrada com {res}. Parabéns pela entrega."))
            fr.append((2, "Agora é recuperação de verdade: rodagem leve, sono em dia e nada de treino forte antes do corpo pedir."))
            fase="pos"; olhar_frente=False
            # o longo da semana foi a prova: não repetir
            fr=[x for x in fr if not x[1].startswith("O treino mais longo")]
        elif p["date"]>hoje:
            fr.append((1, f"A {p['name']} é dia {p['date']:%d/%m}. Daqui até lá o trabalho é chegar descansado: volume baixo, um ou dois estímulos curtos no ritmo de prova, sono e alimentação em dia."))
            fase="prova"; olhar_frente=False
        else:
            fr.append((1, f"A {p['name']} estava marcada para {p['date']:%d/%m} e não apareceu como treino realizado. Se correu, sincronize o relógio para entrar no relatório."))
    if olhar_frente and futuras:
        p=futuras[0]; dias=(p["date"]-we).days
        outras=[x for x in futuras[1:3] if x["date"]!=p["date"]]
        extra=(" Depois vem "+" e ".join(f"{x['name']} em {x['date']:%d/%m}" for x in outras)+".") if outras else ""
        if dias<=7:
            fr.append((1, f"Semana que vem é a {p['name']}, dia {p['date']:%d/%m}. Agora é polimento: o volume cai, a intensidade fica curta só para manter o ritmo na perna, e o que decide a prova é chegar descansado. Nada de treino, tênis ou alimentação novos."))
            fase="polimento"
        elif dias<=21:
            fr.append((1, f"Faltam {dias} dias para a {p['name']} ({p['date']:%d/%m}). Reta final específica: treinos-chave no ritmo de prova e o longo com trechos no ritmo alvo. Depois o volume desce para chegar inteiro.{extra}"))
            fase="especifico"
        else:
            fr.append((1, f"Faltam {dias} dias ({round(dias/7)} semanas) para a {p['name']} ({p['date']:%d/%m}). Fase de construção: constância nos longos e nas qualidades vale mais que qualquer treino isolado.{extra}"))
            fase="base"
    elif olhar_frente and not na_semana and recentes:
        p=recentes[-1]
        fr.append((1, f"Semana pós-{p['name']} ({p['date']:%d/%m}). Recuperação faz parte do treino: rodagens leves, força leve e sono. O corpo absorve a prova agora."))
        fase="pos"

    # ---- 3. leitura da carga ----
    it=data["intens"]; tot=it["easy"]+it["mod"]+it["hard"]
    if tot and fase not in ("pos","prova"):
        if it.get("lthr_suspect"):
            fr.append((5, f"Boa parte das corridas ficou com FC no limiar ou acima. Se o esforço foi tranquilo, revise o LTHR ({data['refs']['lthr']} bpm)."))
        elif it["easy"]/tot>=0.6:
            fr.append((5, "Distribuição certa: a maior parte da semana em ritmo fácil, que é o que sustenta a evolução."))
        elif it["hard"]/tot>=0.4:
            fr.append((5, "Semana forte de intensidade. Os fáceis precisam ser fáceis de verdade para a carga ser absorvida."))
    fit=data.get("fitness") or {}
    cur=fit.get("current") if isinstance(fit,dict) else None
    tsb=cur.get("tsb") if cur else None
    if tsb is not None and fase!="prova":
        if tsb<=-20 and fase=="especifico":
            fr.append((5, f"Forma em {tsb:+.0f}, fadiga esperada nesta fase. O polimento converte isso em prova."))
        elif tsb<=-20 and fase=="polimento":
            fr.append((4, f"Forma em {tsb:+.0f}. O descanso desta semana precisa aparecer nesse número até a prova."))
        elif tsb<=-20: fr.append((4, f"Fadiga acumulada alta (forma {tsb:+.0f}). Uma semana mais leve cai bem antes de puxar de novo."))
        elif tsb>=15 and fase not in ("polimento","pos"): fr.append((5, f"Você está descansado (forma {tsb:+.0f}). Dá para puxar um pouco mais nas próximas semanas."))
    mt=data.get("metrics") or {}
    if mt.get("sono_h") and mt["sono_h"]<6.5:
        fr.append((5, f"Sono médio de {mt['sono_h']:.1f}h. Abaixo de 7h a recuperação fica devendo, e isso aparece no treino."))
    miss=data["missed"]
    if miss>=2 and fase not in ("pos","prova"):
        fr.append((4, f"{miss} sessões planejadas ficaram para trás. Se a agenda apertar, me avisa que eu reorganizo a semana."))

    # ---- 4. foco da próxima semana ----
    foco={"polimento":"Próxima semana: descansar bem, confiar no que foi feito e curtir a prova.",
          "especifico":"Próxima semana: ritmo de prova nos treinos-chave e o longo bem feito.",
          "base":"Próxima semana: manter a constância, sem pular o longo.",
          "pos":"Próxima semana: só rodagem leve e força leve. Voltamos ao plano quando o corpo responder.",
          "prova":"Depois da prova, os dois dias seguintes são de rodagem bem leve."}.get(fase,
          "Próxima semana: seguir o plano e proteger os treinos-chave.")
    fr.append((2, foco)); fr.append((2, SIGNATURE))

    # ---- cabe no quadro? tira as frases menos importantes primeiro ----
    def txt(lst): return " ".join(t for _,t in lst)
    while len(txt(fr))>limite and any(pr>2 for pr,_ in fr):
        pior=max(pr for pr,_ in fr)
        idx=max(i for i,(pr,_) in enumerate(fr) if pr==pior)
        fr.pop(idx)
    return txt(fr)

# ================= CHARTS =================
def _style(ax):
    for s in ["top","right"]: ax.spines[s].set_visible(False)
    ax.tick_params(length=0,labelsize=8,colors=HX_GREYT)
    for s in ["left","bottom"]: ax.spines[s].set_color(HX_GREYL)

def chart_volume(data,path):
    wk=data["weekly"]; labels=[w["label"] for w in wk]; km=[w["km"] for w in wk]
    mean=sum(km)/len(km) if km else 0
    fig,ax=plt.subplots(figsize=(4.6,2.3),dpi=150)
    ax.bar(range(len(km)),km,color=HX_PRIM,width=0.62,zorder=3)
    for i,v in enumerate(km): ax.text(i,v+1.2,f"{v:.0f}",ha="center",va="bottom",fontsize=8,fontweight="bold",color=HX_PRIM)
    ax.axhline(mean,ls="--",color=HX_CORAL,lw=1.6,zorder=2,label=f"Média {mean:.0f}km")
    _style(ax); ax.set_ylabel("km",fontsize=8,color=HX_GREYT)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels,rotation=45,ha="right")
    ax.set_ylim(0,max(km+[10])*1.25); ax.legend(loc="upper left",fontsize=7.5,frameon=False)
    fig.tight_layout(pad=0.3); fig.savefig(path,transparent=True); plt.close(fig)

def chart_hours(data,path):
    wk=data["weekly"]; labels=[w["label"] for w in wk]; hrs=[w["hrs"] for w in wk]
    mean=sum(hrs)/len(hrs) if hrs else 0
    fig,ax=plt.subplots(figsize=(4.6,2.3),dpi=150)
    ax.bar(range(len(hrs)),hrs,color=HX_CORAL,width=0.62,zorder=3)
    for i,v in enumerate(hrs): ax.text(i,v+0.08,f"{v:.1f}h",ha="center",va="bottom",fontsize=8,fontweight="bold",color=HX_CORALD)
    ax.axhline(mean,ls="--",color=HX_TEAL,lw=1.6,zorder=2,label=f"Média {mean:.1f}h/semana")
    _style(ax); ax.set_ylabel("Horas",fontsize=8,color=HX_GREYT)
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels,rotation=45,ha="right")
    ax.set_ylim(0,max(hrs+[1])*1.28); ax.legend(loc="upper left",fontsize=7.5,frameon=False)
    fig.tight_layout(pad=0.3); fig.savefig(path,transparent=True); plt.close(fig)

def chart_pmc(fitness,path):
    daily=fitness.get("daily",[]) if fitness else []
    xs=range(len(daily))
    ctl=[d["ctl"] for d in daily]; atl=[d["atl"] for d in daily]; tsb=[d["tsb"] for d in daily]
    labels=[d["date"][5:].replace("-","/") for d in daily]
    fig,ax=plt.subplots(figsize=(7.1,1.95),dpi=150)
    ax.fill_between(list(xs),ctl,color=HX_TEAL,alpha=0.22,zorder=1)
    ax.plot(list(xs),ctl,color=HX_PRIM,lw=2.1,zorder=4,label="Condição (CTL)")
    ax.plot(list(xs),atl,color=HX_CORAL,lw=1.5,zorder=3,label="Fadiga (ATL)")
    _style(ax); ax.set_ylabel("CTL / ATL",fontsize=8,color=HX_GREYT)
    ax.set_ylim(0,max(ctl+atl+[10])*1.15)
    step=max(1,len(daily)//8)
    ax.set_xticks(list(xs)[::step]); ax.set_xticklabels(labels[::step],fontsize=7)
    ax2=ax.twinx()
    ax2.axhline(0,color=HX_GREYL,lw=0.9,ls=":")
    ax2.plot(list(xs),tsb,color=HX_AMBER,lw=1.6,zorder=5,label="Forma (TSB)")
    ax2.set_ylabel("Forma (TSB)",fontsize=8,color=HX_GREYT)
    ax2.tick_params(length=0,labelsize=7,colors=HX_GREYT); ax2.spines["top"].set_visible(False)
    l1,la1=ax.get_legend_handles_labels(); l2,la2=ax2.get_legend_handles_labels()
    ax.legend(l1+l2,la1+la2,loc="upper left",fontsize=7,frameon=False,ncol=3)
    fig.tight_layout(pad=0.3); fig.savefig(path,transparent=True); plt.close(fig)

def chart_fc_if(data,path,lthr):
    hl=data["highlights"]; labels=[w["date"].strftime("%d/%m") for w in hl]
    fc=[w["hr"] for w in hl]; iff=[w["if_"] for w in hl]
    fcv=[v for v in fc if v]
    fig,ax=plt.subplots(figsize=(4.6,2.45),dpi=150); xs=range(len(hl))
    ax.bar(xs,[v or 0 for v in fc],color=HX_RED,width=0.5,zorder=3,alpha=0.9)
    for i,v in enumerate(fc):
        if v: ax.text(i,v-8,f"{v}",ha="center",va="top",fontsize=8,color="white",fontweight="bold")
    for i,w in enumerate(hl): ax.text(i,(fc[i] or 150)+3,f'{w["dist_km"]:.1f}km',ha="center",va="bottom",fontsize=6.5,color=HX_PRIM)
    ax.axhline(lthr,ls="--",color=HX_TEAL,lw=1.4,label=f"LTHR {lthr}")
    ax.set_ylim(120,max(fcv+[lthr])+20); _style(ax); ax.set_ylabel("FC (bpm)",fontsize=8,color=HX_GREYT)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels,fontsize=7)
    ax2=ax.twinx(); ax2.plot(list(xs),iff,color=HX_AMBER,marker="D",ms=5.5,lw=1.4,zorder=5)
    ax2.set_ylim(0.6,1.05); ax2.tick_params(length=0,labelsize=7,colors=HX_GREYT); ax2.spines["top"].set_visible(False)
    ax2.set_ylabel("IF",fontsize=8,color=HX_GREYT); ax.legend(loc="lower center",fontsize=7,frameon=False)
    fig.tight_layout(pad=0.3); fig.savefig(path,transparent=True); plt.close(fig)

def chart_fc_trend(data,path,lthr):
    wk=[w for w in data["weekly"] if w["fc"]]; labels=[w["label"] for w in wk]; fc=[w["fc"] for w in wk]
    if not fc: fc=[lthr]; labels=["–"]
    fig,ax=plt.subplots(figsize=(4.6,2.35),dpi=150); xs=range(len(fc))
    ymin=min(fc+[lthr])-15; ymax=max(fc+[lthr])+15
    ax.axhspan(lthr,ymax,color=HX_PINK,alpha=0.55,zorder=1)
    ax.plot(list(xs),fc,color=HX_PRIM,marker="o",ms=6.5,lw=2,zorder=4)
    for i,v in enumerate(fc): ax.text(i,v+3,f"{v}",ha="center",va="bottom",fontsize=8.5,fontweight="bold",color=HX_PRIM)
    ax.axhline(lthr,ls="--",color=HX_RED,lw=1.4,label=f"LTHR {lthr} bpm")
    ax.set_ylim(ymin,ymax); _style(ax); ax.set_ylabel("FC Média (bpm)",fontsize=8,color=HX_GREYT)
    ax.set_xticks(list(xs)); ax.set_xticklabels(labels,fontsize=7.5)
    ax.set_title("Tendência de FC Média por Semana",fontsize=10,color=HX_PRIM,fontweight="bold")
    ax.legend(loc="upper right",fontsize=7.5,frameon=False)
    fig.tight_layout(pad=0.3); fig.savefig(path,transparent=True); plt.close(fig)

# ================= PRIMITIVAS =================
def _sect(c,x,y,w,title):
    c.setFillColorRGB(*NAVY); c.setFont("Helvetica-Bold",10.5); c.drawString(x,y,title.upper())
    c.setStrokeColorRGB(*YELLOW); c.setLineWidth(2.2); c.line(x,y-4,x+w,y-4)

def _card(c,x,y,w,h,barcol,big,s1,s2,delta=None):
    c.setFillColorRGB(0.98,0.99,1.0); c.setStrokeColorRGB(0.85,0.89,0.93); c.setLineWidth(0.8)
    c.roundRect(x,y-h,w,h,4,fill=1,stroke=1)
    c.setFillColorRGB(*barcol); c.rect(x,y-h,4,h,fill=1,stroke=0)
    c.setFillColorRGB(*NAVY); c.setFont("Helvetica-Bold",19); c.drawString(x+12,y-22,big)
    c.setFillColorRGB(*GREY); c.setFont("Helvetica-Bold",7.5); c.drawString(x+12,y-33,s1.upper())
    c.setFillColorRGB(*GREY); c.setFont("Helvetica",7); c.drawString(x+12,y-43,s2)
    if delta:
        txt,col=delta
        c.setFillColorRGB(*col); c.setFont("Helvetica-Bold",6.6); c.drawString(x+12,y-53,txt)

def _delta_txt(cur, prev, better_up=True):
    if prev is None: return None
    if prev==0: return ("novo", GREY)
    pct=(cur-prev)/prev*100
    good=(pct>=0) if better_up else (pct<=0)
    col=GREEN if good else RED
    sign="+" if pct>=0 else "-"
    val = f"{sign}200%+" if abs(pct)>200 else f"{sign}{abs(pct):.0f}%"
    return (f"{val} vs mês ant.", col)

def _header(c, data, compact=False):
    if compact:
        hh=46
        c.setFillColorRGB(*NAVY); c.rect(0,H-hh,W,hh,fill=1,stroke=0)
        c.saveState(); _to=c.beginText(34,H-17); _to.setFont("Helvetica-Bold",8); _to.setFillColorRGB(*YELLOW)
        _to.setCharSpace(2.6); _to.textOut(BRAND); c.drawText(_to); c.restoreState()
        c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",13); c.drawString(34,H-34,data["name"])
        c.setFillColorRGB(0.72,0.82,0.85); c.setFont("Helvetica",8); c.drawRightString(W-34,H-30,f'{data["period"]}  ·  pág. 2')
        return
    hh=90; M=34
    c.setFillColorRGB(*NAVY); c.rect(0,H-hh,W,hh,fill=1,stroke=0)
    c.saveState(); _to=c.beginText(M,H-22); _to.setFont("Helvetica-Bold",9.5); _to.setFillColorRGB(*YELLOW)
    _to.setCharSpace(3.2); _to.textOut(BRAND); c.drawText(_to); c.restoreState()
    c.setFillColorRGB(0.55,0.66,0.70); c.setFont("Helvetica",6.5); c.drawString(M+52,H-22,TAGLINE.upper())
    c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",20); c.drawString(M,H-45,data["name"])
    c.setFillColorRGB(0.75,0.85,0.88); c.setFont("Helvetica-Bold",11.5); c.drawString(M,H-62,"Relatório Mensal de Treino")
    c.setFillColorRGB(0.75,0.85,0.88); c.setFont("Helvetica",9); c.drawString(M,H-77,data["period"])
    c.setFillColorRGB(0.72,0.82,0.85); c.setFont("Helvetica",7.5); c.drawRightString(W-M-52,H-84,"Relatório Mensal · Confidencial")
    # avatar (foto) ou monograma
    cx=W-M-22; cy=H-40; r=21
    drew=False
    ap=data.get("_avatar")
    if ap:
        try:
            c.saveState(); path=c.beginPath(); path.circle(cx,cy,r); c.clipPath(path,stroke=0,fill=0)
            c.drawImage(ImageReader(ap),cx-r,cy-r,2*r,2*r,mask="auto",preserveAspectRatio=True,anchor="c")
            c.restoreState()
            c.setStrokeColorRGB(*YELLOW); c.setLineWidth(1.6); c.circle(cx,cy,r,fill=0,stroke=1); drew=True
        except Exception: drew=False
    if not drew:
        c.setFillColorRGB(*YELLOW); c.circle(cx,cy,r,fill=1,stroke=0)
        c.setFillColorRGB(*NAVY); c.setFont("Helvetica-Bold",14); c.drawCentredString(cx,cy-5,initials(data["name"]))

def _footer(c, data):
    c.setFillColorRGB(*NAVY); c.rect(0,0,W,20,fill=1,stroke=0)
    c.setFillColorRGB(0.72,0.82,0.85); c.setFont("Helvetica",7)
    c.drawString(34,7,f"{BRAND} · Relatório Mensal de Treinamento · Confidencial")
    c.drawRightString(W-34,7,data["period"])

# ================= RENDER (página única) =================
def render(data,out_path):
    c=canvas.Canvas(out_path,pagesize=A4); refs=data["refs"]; lthr=refs["lthr"]
    M=34; colw=(W-2*M-16)/2; c2=M+colw+16; CH=86
    data["_avatar"]=avatar_path(data.get("id","x"), data.get("photo"))
    p_vol=os.path.join(SCRATCH,"_vol.png"); p_hrs=os.path.join(SCRATCH,"_hrs.png")
    p_fc=os.path.join(SCRATCH,"_fc.png");   p_tr=os.path.join(SCRATCH,"_tr.png")
    chart_volume(data,p_vol); chart_hours(data,p_hrs); chart_fc_if(data,p_fc,lthr); chart_fc_trend(data,p_tr,lthr)

    _header(c,data)
    y=H-90-6

    # banner de prova-alvo
    ev=data["event"]
    if ev:
        dtoev=days_to_event(ev, data["end"])
        bh=16; by=y-bh
        c.setFillColorRGB(0.93,0.96,0.97); c.setStrokeColorRGB(0.80,0.87,0.90); c.setLineWidth(0.7)
        c.roundRect(M,by,W-2*M,bh,3,fill=1,stroke=1)
        c.setFillColorRGB(*ORANGE); c.roundRect(M,by,3,bh,1,fill=1,stroke=0)
        c.setFillColorRGB(*NAVY); c.setFont("Helvetica-Bold",8); c.drawString(M+12,by+5,f'PRÓXIMA PROVA:  {ev["name"]}')
        try: edtxt=dt.date.fromisoformat(ev["date"]).strftime("%d/%m/%Y")
        except Exception: edtxt=ev["date"]
        cd = f'{edtxt}   ·   faltam {dtoev} dias' if (dtoev is not None and dtoev>0) else edtxt
        c.setFillColorRGB(*GREY); c.setFont("Helvetica-Bold",7.5); c.drawRightString(W-M-10,by+5,cd)
        y=by-9

    # resumo/cards com deltas
    _sect(c,M,y,W-2*M,"Resumo do Mês")
    cy=y-11; cw=(W-2*M-3*8)/4; ch=52
    prev=data["prev"]
    d_km = _delta_txt(data["run_km"], prev["run_km"]) if prev else None
    d_ss = _delta_txt(data["total_completed"], prev["sessions"]) if prev else None
    d_ad = _delta_txt(data["adher"], prev["adher"]) if prev else None
    d_ms = _delta_txt(data["missed"], prev["missed"], better_up=False) if prev else None
    _card(c,M,cy,cw,ch,NAVY,f'{data["sess_done"]}/{data["sess_plan"]}',"Sessões",f'aderência {data["adher"]:.0f}%',d_ss)
    _card(c,M+(cw+8),cy,cw,ch,NAVY,f'{data["run_km"]:.0f} km',"Distância",f'pico {data["peak_km"]:.0f}km',d_km)
    _card(c,M+2*(cw+8),cy,cw,ch,RED,f'{data["missed"]}',"Perdidas",f'{data["missed_pct"]:.0f}% do plano',d_ms)
    _card(c,M+3*(cw+8),cy,cw,ch,NAVY,f'{data["adher"]:.0f}%',"Aderência",f'{data["active_weeks"]}/{data["n_weeks"]} sem. ativas',d_ad)

    # volume + horas
    ry=cy-ch-11
    _sect(c,M,ry,colw,"Volume Semanal  —  km Corridos"); _sect(c,c2,ry,colw,"Horas Treinadas por Semana")
    imgy=ry-8-CH
    c.drawImage(ImageReader(p_vol),M,imgy,colw,CH,mask="auto"); c.drawImage(ImageReader(p_hrs),c2,imgy,colw,CH,mask="auto")

    # intensidade + destaques
    ry2=imgy-11
    _sect(c,M,ry2,colw,"Distribuição de Intensidade"); _sect(c,c2,ry2,colw,"Destaques do Mês")
    it=data["intens"]; tot=it["easy"]+it["mod"]+it["hard"]; iy=ry2-11
    if tot>0:
        bh=13; segs=[("Fácil",it["easy"],GREEN),("Moderado",it["mod"],YELLOW),("Forte",it["hard"],RED)]
        cxx=M
        for lab,n,col in segs:
            w=colw*(n/tot)
            if w>0:
                c.setFillColorRGB(*col); c.rect(cxx,iy-bh,w,bh,fill=1,stroke=0)
                if w>24: c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",7); c.drawCentredString(cxx+w/2,iy-bh+4,f"{n}")
                cxx+=w
        ly=iy-bh-10; lx=M
        for lab,n,col in segs:
            c.setFillColorRGB(*col); c.rect(lx,ly,7,7,fill=1,stroke=0)
            c.setFillColorRGB(*GREY); c.setFont("Helvetica",7); c.drawString(lx+10,ly+1,f"{lab} ({n})"); lx+=colw/3
        col=RED if it.get("lthr_suspect") else NAVY
        c.setFillColorRGB(*col); c.setFont("Helvetica-Oblique",7)
        for j,ln in enumerate(textwrap.wrap(it.get("note") or "",70)[:2]): c.drawString(M,ly-10-j*8.5,ln)
    else:
        c.setFillColorRGB(*GREY); c.setFont("Helvetica-Oblique",7.5); c.drawString(M,iy-10,"Sem FC registrada para classificar intensidade.")
    recs=[]
    if data["rec_dist"]: recs.append(("Maior distância",f'{data["rec_dist"]["dist_km"]:.1f} km',data["rec_dist"]["date"].strftime("%d/%m")))
    if data["rec_pace"]: recs.append(("Melhor pace",fmt_pace(data["rec_pace"]["pace"]),data["rec_pace"]["date"].strftime("%d/%m")))
    if data["rec_tss"]: recs.append(("Maior carga",f'{data["rec_tss"]["tss"]:.0f} TSS',data["rec_tss"]["date"].strftime("%d/%m")))
    recs.append(("Altimetria total",f'{data["elev_total"]:.0f} m',"acumulado"))
    rcw=(colw-8)/2; rch=24
    for i,(lab,val,sub) in enumerate(recs[:4]):
        rx=c2+(i%2)*(rcw+8); ryy=(ry2-11)-(i//2)*(rch+6)
        c.setFillColorRGB(0.98,0.99,1.0); c.setStrokeColorRGB(0.85,0.89,0.93); c.setLineWidth(0.7)
        c.roundRect(rx,ryy-rch,rcw,rch,3,fill=1,stroke=1)
        c.setFillColorRGB(*ORANGE); c.rect(rx,ryy-rch,3,rch,fill=1,stroke=0)
        c.setFillColorRGB(*NAVY); c.setFont("Helvetica-Bold",10.5); c.drawString(rx+8,ryy-13,val)
        c.setFillColorRGB(*GREY); c.setFont("Helvetica-Bold",5.8); c.drawString(rx+8,ryy-21,lab.upper())
        c.setFillColorRGB(*GREY); c.setFont("Helvetica",5.8); c.drawRightString(rx+rcw-6,ryy-21,sub)
    row2_bot = min(iy-41, (ry2-11)-2*(rch+6))

    # sessões em destaque + fc/if
    ry3=row2_bot-12
    _sect(c,M,ry3,colw,"Sessões em Destaque"); _sect(c,c2,ry3,colw,"FC Média · IF · Cadência")
    ty=ry3-11; rh=13
    cData=M+4; cSess=M+32; cBadge=M+colw-132; cDist=M+colw-52; cPace=M+colw-4
    c.setFillColorRGB(*NAVY); c.rect(M,ty-rh,colw,rh,fill=1,stroke=0)
    c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",7)
    c.drawString(cData,ty-rh+3.5,"Data"); c.drawString(cSess,ty-rh+3.5,"Sessão")
    c.drawString(cBadge,ty-rh+3.5,"Tipo"); c.drawRightString(cDist,ty-rh+3.5,"Dist."); c.drawRightString(cPace,ty-rh+3.5,"Pace")
    rr=ty-rh
    for i,w in enumerate(data["highlights"]):
        rr-=rh
        if i%2==0: c.setFillColorRGB(*LGREY); c.rect(M,rr,colw,rh,fill=1,stroke=0)
        c.setFillColorRGB(*GREY); c.setFont("Helvetica",6.8); c.drawString(cData,rr+3.5,w["date"].strftime("%d/%m"))
        c.setFillColorRGB(*NAVY); c.setFont("Helvetica-Bold",6.8); c.drawString(cSess,rr+3.5,(w["title"] or "Corrida")[:20])
        c.setFillColorRGB(*NAVY); c.roundRect(cBadge,rr+2.6,34,8,2,fill=1,stroke=0)
        c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",5,); c.drawCentredString(cBadge+17,rr+4.6,"CORRIDA")
        c.setFillColorRGB(*NAVY); c.setFont("Helvetica",6.8)
        c.drawRightString(cDist,rr+3.5,f'{w["dist_km"]:.1f} km'); c.drawRightString(cPace,rr+3.5,fmt_pace(w["pace"]))
    tbl_bot=rr
    c.drawImage(ImageReader(p_fc),c2,tbl_bot-2,colw,ty-tbl_bot+6,preserveAspectRatio=True,anchor="n",mask="auto")

    # planejadas + refs
    ry4=tbl_bot-11
    _sect(c,M,ry4,colw,"Planejadas Não Executadas"); _sect(c,c2,ry4,colw,"Referências Fisiológicas")
    py=ry4-12; col2x=M+colw/2; pm=data["planned_missed"][:8]
    for i,w in enumerate(pm):
        cx=M if i%2==0 else col2x; yy=py-(i//2)*10
        c.setFillColorRGB(*RED); c.circle(cx+3,yy+2.5,1.7,fill=1,stroke=0)
        c.setFillColorRGB(*GREY); c.setFont("Helvetica",6.8); c.drawString(cx+9,yy,w["date"].strftime("%d/%m")+"  "+(w["title"] or "Treino")[:22])
    if not pm:
        c.setFillColorRGB(*GREEN); c.setFont("Helvetica-Oblique",7.2); c.drawString(M,py,"Nenhuma — plano cumprido no mês.")
    planned_bot=py-((len(pm)+1)//2)*10 if pm else py-10
    chips=[("LTHR",f'{refs["lthr"]} bpm',RED),("Pace Limiar",refs["pace_lim"],ORANGE),
           ("FC Máxima",f'{refs["fcmax"]} bpm',RED),("FC Média",f'{data["fc_med"]} bpm' if data["fc_med"] else "–",NAVY),
           ("Pace Médio",fmt_pace(data["pace_med"]),ORANGE),("Cadência",f'{data["cad_med"]} spm' if data["cad_med"] else "–",NAVY)]
    chw=(colw-2*6)/3; chh=22
    for i,(lab,val,col) in enumerate(chips):
        cx=c2+(i%3)*(chw+6); cyy=py-(i//3)*(chh+5)
        c.setFillColorRGB(0.98,0.99,1.0); c.setStrokeColorRGB(0.85,0.89,0.93); c.setLineWidth(0.7)
        c.roundRect(cx,cyy-chh,chw,chh,3,fill=1,stroke=1)
        c.setFillColorRGB(*col); c.rect(cx,cyy-chh,3,chh,fill=1,stroke=0)
        c.setFillColorRGB(*NAVY); c.setFont("Helvetica-Bold",10); c.drawString(cx+7,cyy-13,val)
        c.setFillColorRGB(*GREY); c.setFont("Helvetica",6); c.drawString(cx+7,cyy-20,lab.upper())
    refs_bot=py-2*(chh+5)
    if refs["unconfigured"]:
        c.setFillColorRGB(*RED); c.setFont("Helvetica-Bold",6.2)
        c.drawString(c2,refs_bot+1,"! Zonas de FC não configuradas no TP — faixas estimadas."); refs_bot-=8

    # tendência + detalhe por semana
    ry5=min(planned_bot,refs_bot)-9
    _sect(c,M,ry5,colw,"Tendência de FC Média"); _sect(c,c2,ry5,colw,"Detalhe por Semana")
    c.drawImage(ImageReader(p_tr),M,ry5-8-CH,colw,CH,mask="auto")
    tx=c2; tyy=ry5-8; rh2=12
    c.setFillColorRGB(*NAVY); c.rect(tx,tyy-rh2,colw,rh2,fill=1,stroke=0)
    c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",6.6)
    for name_,px,al in [("Semana",tx+4,"l"),("km",tx+colw*0.42,"r"),("Hrs",tx+colw*0.58,"r"),
                        ("TSS",tx+colw*0.74,"r"),("Sess.",tx+colw*0.88,"r"),("FC",tx+colw-4,"r")]:
        (c.drawRightString if al=="r" else c.drawString)(px,tyy-rh2+3.5,name_)
    rr2=tyy-rh2
    for i,w in enumerate(data["weekly"]):
        rr2-=rh2
        if i%2==0: c.setFillColorRGB(*LGREY); c.rect(tx,rr2,colw,rh2,fill=1,stroke=0)
        c.setFillColorRGB(*GREY); c.setFont("Helvetica",6.5); c.drawString(tx+4,rr2+3.5,w["label"])
        c.setFillColorRGB(*NAVY)
        c.drawRightString(tx+colw*0.42,rr2+3.5,f'{w["km"]:.0f}' if w["km"] else "–")
        c.drawRightString(tx+colw*0.58,rr2+3.5,f'{w["hrs"]:.1f}' if w["hrs"] else "–")
        c.drawRightString(tx+colw*0.74,rr2+3.5,f'{w["tss"]:.0f}' if w["tss"] else "–")
        c.drawRightString(tx+colw*0.88,rr2+3.5,str(w["sess"]))
        if w["fc"]:
            c.setFillColorRGB(*RED); c.roundRect(tx+colw-28,rr2+2,25,8,2,fill=1,stroke=0)
            c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",6.2); c.drawCentredString(tx+colw-15.5,rr2+3.7,str(w["fc"]))
        else:
            c.setFillColorRGB(*GREY); c.drawRightString(tx+colw-4,rr2+3.5,"–")

    # zonas
    zy=min(ry5-8-CH,rr2)-11
    _sect(c,M,zy,W-2*M,f'Zonas de FC  —  LTHR {lthr} bpm')
    zb=refs["hr_zones"]; zw=W-2*M; zh=13; zyy=zy-11-zh; cx=M
    for lab,frac,col,rng in zb:
        bw=zw*frac; c.setFillColorRGB(*col); c.rect(cx,zyy,bw,zh,fill=1,stroke=0)
        c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",6.2); c.drawCentredString(cx+bw/2,zyy+4,lab)
        c.setFillColorRGB(*GREY); c.setFont("Helvetica",5.3); c.drawCentredString(cx+bw/2,zyy-6.5,rng); cx+=bw
    pzhy=zyy-17
    _sect(c,M,pzhy,W-2*M,f'Zonas de Pace  —  Limiar {refs["pace_lim"]}')
    pz=refs["pace_zones"]; pzh=15; pzy=pzhy-11-pzh; cx=M; pw=zw/len(pz)
    for lab,rng,col in pz:
        c.setFillColorRGB(*col); c.rect(cx,pzy,pw,pzh,fill=1,stroke=0)
        c.setFillColorRGB(*WHITE); c.setFont("Helvetica-Bold",6.4); c.drawCentredString(cx+pw/2,pzy+8,lab)
        c.setFont("Helvetica",5.1); c.drawCentredString(cx+pw/2,pzy+1.6,rng); cx+=pw

    # recado (encaixa acima do rodapé; corta linhas excedentes)
    rcy=pzy-12
    _sect(c,M,rcy,W-2*M,"Recado do Treinador")
    avail=rcy-8-24
    maxlines=max(2,int((avail-10)/9.2))
    lines=textwrap.wrap(data["coach_msg"],124)[:maxlines]
    bh=max(34,10+len(lines)*9.2); by=rcy-8-bh
    c.setFillColorRGB(0.98,0.99,1.0); c.setStrokeColorRGB(0.85,0.89,0.93); c.setLineWidth(0.8)
    c.roundRect(M,by,W-2*M,bh,4,fill=1,stroke=1)
    c.setFillColorRGB(*NAVY); c.rect(M,by,4,bh,fill=1,stroke=0)
    c.setFillColorRGB(0.2,0.28,0.35); c.setFont("Helvetica",7.6)
    tobj=c.beginText(M+14,by+bh-11); tobj.setLeading(9.2)
    for line in lines: tobj.textLine(line)
    c.drawText(tobj)

    _footer(c,data)
    c.showPage(); c.save()
    for p in (p_vol,p_hrs,p_fc,p_tr):
        try: os.remove(p)
        except OSError: pass
