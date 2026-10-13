# -*- coding: utf-8 -*-
"""Drift cardíaco (desacoplamento aeróbico Pa:Hr) em treinos contínuos.

Método (Friel/Coyle): baixa o arquivo FIT do treino, remove pausas e os
primeiros 10 min (aquecimento + atraso da FC), confere se o treino é
contínuo (CV da velocidade em janelas de 1 min ≤ 14%), divide o restante
em duas metades e compara a eficiência EF = velocidade média / FC média:

    drift % = (EF1 − EF2) / EF1 × 100

Referências: <5% base aeróbica sólida · 5–8% razoável · >8% fraca (ou
calor/desidratação). Negativo = melhorou na 2ª metade (excelente).
"""
import asyncio, gzip, io, json, os, statistics as stats, sys

TP_SRC = os.environ.get("TP_MCP_SRC", "/Users/andresantos/trainingpeaks-mcp/src")
sys.path.insert(0, TP_SRC)
try:                       # na nuvem só o classify é usado; o resto roda no Mac
    from tp_mcp.client import TPClient
    from tp_mcp.client.context import athlete_override
    from tp_mcp.tools.workouts import tp_get_workouts, tp_get_workout
    from tp_mcp.tools.workout_files import tp_download_workout_file
    import fitdecode
except ImportError:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(BASE, "data", "drift_cache.json")
TMP = os.path.join(BASE, "data", "_fit_tmp")

def _cache_load():
    try: return json.load(open(CACHE_PATH))
    except Exception: return {}

def _cache_save(c):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    json.dump(c, open(CACHE_PATH, "w"), ensure_ascii=False)

def parse_fit(path):
    """Série (t_seg, fc, vel_m_s) dos records do FIT (aceita .fit e .fit.gz)."""
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b": raw = gzip.decompress(raw)
    rows = []
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with fitdecode.FitReader(io.BytesIO(raw)) as f:
            for fr in f:
                if isinstance(fr, fitdecode.FitDataMessage) and fr.name == "record":
                    d = {x.name: x.value for x in fr.fields}
                    ts = d.get("timestamp"); hr = d.get("heart_rate")
                    sp = d.get("enhanced_speed", d.get("speed"))
                    if ts is not None and hr and sp is not None:
                        rows.append((ts, float(hr), float(sp)))
    if not rows: return []
    t0 = rows[0][0]
    return [((r[0]-t0).total_seconds(), r[1], r[2]) for r in rows]

def compute_drift(series, trim_min=10, min_total_min=35, cv_max=14.0):
    """Retorna (resultado|None, motivo_da_recusa|None)."""
    if not series: return None, "sem série de FC/velocidade"
    mov = [r for r in series if r[2] > 0.83]          # remove pausas (<3 km/h)
    if not mov: return None, "sem movimento"
    dur_min = (mov[-1][0]-mov[0][0])/60
    if dur_min < min_total_min: return None, f"curto ({dur_min:.0f} min)"
    core = [r for r in mov if r[0] >= mov[0][0] + trim_min*60]
    if len(core) < 600: return None, "poucos dados após aquecimento"
    win = {}
    for t, hr, sp in core: win.setdefault(int(t//60), []).append(sp)
    mins = [stats.mean(v) for v in win.values() if len(v) >= 20]
    cv = (stats.pstdev(mins)/stats.mean(mins)*100) if len(mins) >= 10 and stats.mean(mins) > 0 else 99.0
    if cv > cv_max: return None, f"não contínuo (variação {cv:.0f}%)"
    meio = core[len(core)//2][0]
    h1 = [r for r in core if r[0] < meio]; h2 = [r for r in core if r[0] >= meio]
    ef1 = stats.mean(r[2] for r in h1)/stats.mean(r[1] for r in h1)
    ef2 = stats.mean(r[2] for r in h2)/stats.mean(r[1] for r in h2)
    return {"dec": round((ef1-ef2)/ef1*100, 1), "cv": round(cv, 1), "dur_min": round(dur_min),
            "fc1": round(stats.mean(r[1] for r in h1)), "fc2": round(stats.mean(r[1] for r in h2)),
            "pace1": 1000/(60*stats.mean(r[2] for r in h1)),
            "pace2": 1000/(60*stats.mean(r[2] for r in h2))}, None

def classify(dec):
    if dec is None: return ""
    if dec < 0:  return "🟣 excelente (negativo)"
    if dec < 5:  return "🟢 sólido (<5%)"
    if dec <= 8: return "🟡 razoável (5–8%)"
    return "🔴 alto (>8%)"

async def athlete_drifts(aid, start, end, max_runs=8, min_dur_h=0.62, progress=None):
    """Corridas contínuas candidatas do período → drift por treino (com cache em disco)."""
    cache = _cache_load()
    os.makedirs(TMP, exist_ok=True)
    async with TPClient() as c:
        pass
    tok = athlete_override.set(str(aid))
    out = []
    try:
        wl = await tp_get_workouts(start, end, "completed")
        runs = [w for w in (wl.get("workouts") or [])
                if w.get("sport") == "Run" and (w.get("duration_actual") or 0) >= min_dur_h]
        runs.sort(key=lambda w: w.get("date") or "", reverse=True)
        runs = runs[:max_runs]
        for i, w in enumerate(runs):
            wid = str(w["id"])
            if progress: progress(i, len(runs), w.get("title") or "")
            if wid in cache:
                out.append({**cache[wid], "date": (w.get("date") or "")[:10],
                            "title": w.get("title") or "Corrida"}); continue
            entry = {"ok": False, "motivo": "sem arquivo do relógio"}
            try:
                det = await tp_get_workout(wid)
                files = det.get("device_files") or []
                if files:
                    fid = str(files[0].get("file_id"))
                    r = await tp_download_workout_file(wid, fid, TMP)
                    path = r.get("saved_path") or r.get("path") or r.get("file_path") or r.get("saved_to")
                    if not path and not r.get("isError"):
                        for k, v in r.items():
                            if isinstance(v, str) and v.endswith((".fit", ".gz")): path = v; break
                    if path and os.path.exists(path):
                        res, err = compute_drift(parse_fit(path))
                        entry = ({"ok": True, **res} if res else {"ok": False, "motivo": err})
                        try: os.remove(path)
                        except OSError: pass
                    elif r.get("isError"):
                        entry = {"ok": False, "motivo": str(r.get("message"))[:40]}
            except Exception as e:
                entry = {"ok": False, "motivo": str(e)[:40]}
            cache[wid] = entry
            out.append({**entry, "date": (w.get("date") or "")[:10], "title": w.get("title") or "Corrida"})
        _cache_save(cache)
        return out
    finally:
        athlete_override.reset(tok)
