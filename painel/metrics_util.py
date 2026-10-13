# -*- coding: utf-8 -*-
"""Agrega as métricas diárias (recuperação) de um atleta num resumo compacto."""

# type -> chave no resumo
MTYPES = {5:"fc_rep", 60:"hrv", 6:"sono_h", 64:"body_batt", 62:"stress", 9:"peso",
          46:"sono_prof", 47:"sono_rem", 48:"sono_leve"}   # sono detalhado (horas)

def daily_series(metrics_list, keys=("fc_rep","hrv","sono_h")):
    """Série diária compacta (p/ tendências de risco): [{date, fc_rep, hrv, sono_h}...]"""
    out=[]
    for day in metrics_list or []:
        if not isinstance(day, dict): continue
        d=(day.get("date") or day.get("dateTime") or day.get("timeStamp") or "")[:10]
        row={}
        for x in (day.get("details") or []):
            t=MTYPES.get(x.get("type")); v=x.get("value")
            if t not in keys: continue
            if isinstance(v,(list,tuple)):
                nums=[float(i) for i in v if isinstance(i,(int,float))]
                if nums: row[t]=sum(nums)/len(nums)
            elif isinstance(v,(int,float)):
                row[t]=float(v)
        if d and row: out.append({"date":d, **row})
    return sorted(out, key=lambda r: r["date"])

def aggregate_metrics(metrics_list):
    """Recebe a lista `metrics` do tp_get_metrics e devolve médias mensais compactas."""
    acc = {k: [] for k in MTYPES.values()}
    days = 0
    for day in metrics_list or []:
        det = day.get("details") if isinstance(day, dict) else None
        if not det: continue
        got = False
        for d in det:
            t = d.get("type"); v = d.get("value")
            if t in MTYPES and isinstance(v, (int, float)):
                acc[MTYPES[t]].append(float(v)); got = True
        if got: days += 1
    def avg(vals):
        return (sum(vals)/len(vals)) if vals else None
    out = {k: avg(v) for k, v in acc.items()}
    out["days"] = days
    # nada útil? devolve None
    if not any(out[k] is not None for k in MTYPES.values()):
        return None
    return out
