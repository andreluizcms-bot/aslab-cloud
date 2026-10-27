# -*- coding: utf-8 -*-
"""Macrociclo por objetivo e ponto de partida pelo histórico.

- MACROS: para 5k, 10k, 21k e 42k, o tamanho ideal do ciclo, as fatias de cada
  fase, o teto do longo e as sessões-chave de cada fase.
- ponto_de_partida(): km inicial e km de pico a partir do que o atleta já vem
  fazendo (últimas 4 semanas, últimas 2, maior longo), com travas de segurança.
- gerar_atp(): as semanas do ciclo (fase, km, longo, sessões-chave, semana leve).
"""
import datetime as dt

MACROS = {
    "5k":  {"semanas": 8,  "longo_max": 14, "teto_semana": 55, "taper": 1, "frac_longo": 0.30,
            "fases": {"Base": 0.40, "Específico": 0.60},
            "chave": {"Base": "limiar + rodagem c/ strides + longo contínuo",
                      "Específico": "VO2max + ritmo de prova + longo contínuo",
                      "Polimento": "ritmo de prova curto + strides"}},
    "10k": {"semanas": 10, "longo_max": 18, "teto_semana": 65, "taper": 1, "frac_longo": 0.30,
            "fases": {"Base": 0.45, "Específico": 0.55},
            "chave": {"Base": "limiar + rodagem c/ strides + longo contínuo",
                      "Específico": "limiar + VO2/ritmo de prova + longo com trocas",
                      "Polimento": "ritmo de prova curto + rodagem"}},
    "21k": {"semanas": 12, "longo_max": 20, "teto_semana": 75, "taper": 2, "frac_longo": 0.32,
            "fases": {"Base": 0.45, "Específico": 0.55},
            "chave": {"Base": "limiar + rodagem + longo contínuo",
                      "Específico": "ritmo de prova + limiar + longo em bloco",
                      "Polimento": "ritmo de prova curto + rodagem"}},
    "42k": {"semanas": 16, "longo_max": 34, "teto_semana": 95, "taper": 3, "frac_longo": 0.42,
            "fases": {"Base": 0.40, "Específico": 0.60},
            "chave": {"Base": "limiar + rodagem + longo contínuo progressivo",
                      "Específico": "ritmo de prova + longo em bloco/progressivo",
                      "Polimento": "ritmo de prova curto + rodagem"}},
}
PADRAO = "10k"


def aumento_semanal_max(rows):
    """Maior aumento (%) entre duas semanas de carga seguidas do plano."""
    ks = [r["km"] for r in rows if r.get("fase") in ("Base", "Específico")
          and r.get("km") and "leve" not in (r.get("obs") or "")]
    return max(((b / a - 1) * 100 for a, b in zip(ks, ks[1:]) if a), default=0.0)


def objetivo_por_km(km):
    if not km: return None
    if km >= 40: return "42k"
    if km >= 19: return "21k"
    if km >= 9: return "10k"
    if km >= 4: return "5k"
    return None


def ponto_de_partida(hist, objetivo=None, semanas_build=None):
    """km_ini / km_pico / longo_ini a partir do histórico, com travas.

    hist: {km_semana (média 4 sem), km_2sem (média 2 últimas), km_8sem (média 8 sem),
           maior_longo, dias_treino:[...]}  (tudo opcional)
    Regras: início = média das 4 semanas (60% se as 2 últimas caíram pela metade:
    pausa/lesão); pico = progressão de ~8%/semana de construção, limitada a 1,8× o
    início, ao teto do objetivo e, em ciclos curtos, a 25% acima do início;
    longo inicial ≥ o que ele já faz, ≤ 30% da semana e ≤ teto do objetivo."""
    m = MACROS.get(objetivo or PADRAO, MACROS[PADRAO])
    km4 = float(hist.get("km_semana") or 0)
    km2 = hist.get("km_2sem")
    km8 = float(hist.get("km_8sem") or 0)
    longo_atual = float(hist.get("maior_longo") or 0)
    motivo = []
    if km4 <= 0:
        km_ini = 15.0; motivo.append("sem corridas recentes: início conservador de 15 km")
    else:
        km_ini = km4; motivo.append(f"média das últimas 4 semanas: {km4:.0f} km")
        if km2 is not None and km2 < km4 * 0.5:
            km_ini = max(10.0, km4 * 0.6); motivo.append(f"2 últimas semanas caíram para {km2:.0f} km: começa em 60%")
        elif km8 and km8 < km4 * 0.75:
            km_ini = (km4 + km8) / 2; motivo.append(f"volume subiu rápido (8 sem: {km8:.0f} km): início na média")
    km_ini = round(km_ini)
    build = semanas_build if semanas_build is not None else max(m["semanas"] - m["taper"] - 1, 3)
    pico = km_ini * (1 + 0.08 * build)
    pico = min(pico, km_ini * 1.6, m["teto_semana"])
    if build <= 3: pico = min(pico, km_ini * 1.25)
    km_pico = max(round(pico), km_ini)
    if km_pico >= m["teto_semana"]: motivo.append(f"pico travado no teto do objetivo ({m['teto_semana']} km)")
    # longo inicial: não abaixo do que ele já faz (até 40% da semana), nem acima do teto
    longo_ini = max(min(longo_atual, km_ini * 0.45, m["longo_max"]), min(km_ini * 0.25, m["longo_max"]))
    longo_ini = round(longo_ini * 2) / 2
    return {"km_ini": km_ini, "km_pico": km_pico, "longo_ini": longo_ini,
            "longo_max": m["longo_max"], "semanas_ideal": m["semanas"], "motivo": "; ".join(motivo)}


def gerar_atp(objetivo, inicio, prova_data, km_ini, km_pico, longo_ini=None, fim=None,
              recup_cada=4, recup_corte_pct=25.0, progressao_max_pct=None,
              longo_pico=None):
    """Semanas do ciclo até a prova (e depois dela, se fim > prova):
    [{idx, inicio, fase, km, longo, obs}]. obs traz sessões-chave e "semana leve".

    recup_cada: semana leve a cada N semanas na Base/Específico (0 = nenhuma).
    recup_corte_pct: quanto a semana leve corta do km e do longo da rampa.
    progressao_max_pct: teto do aumento de km entre duas semanas de carga
        seguidas. A rampa vai do km inicial ao pico só pelas semanas de carga
        (a leve não conta). Km inicial e pico são sempre os pedidos; o teto
        só muda a forma da subida (ver aumento_semanal_max para o aviso).
    longo_pico: maior longo do ciclo pedido pelo treinador. Vale acima da
        fração padrão do objetivo e do teto de longo do macro (o treinador
        decide); sem ele, o longo de pico sai da fração do km de pico."""
    m = MACROS.get(objetivo or PADRAO, MACROS[PADRAO])
    ini = dt.date.fromisoformat(inicio) if isinstance(inicio, str) else inicio
    prova = dt.date.fromisoformat(prova_data) if isinstance(prova_data, str) else prova_data
    seg = ini - dt.timedelta(days=ini.weekday())
    prova_seg = prova - dt.timedelta(days=prova.weekday())
    fim_seg = prova_seg if fim is None else max(prova_seg, (fim if not isinstance(fim, str) else dt.date.fromisoformat(fim)))
    n = max(int((fim_seg - seg).days / 7) + 1, 3)
    ip = min(int((prova_seg - seg).days / 7), n - 1)          # semana da prova
    taper = min(m["taper"], max(1, ip - 3))                     # ciclo curto: taper menor
    build = ip - taper
    n_base = round(build * m["fases"]["Base"])
    km_ini = float(km_ini); km_pico = float(km_pico)
    longo_pedido = float(longo_pico) if longo_pico else None
    longo_max = max(m["longo_max"], longo_pedido or 0)
    longo_ini = float(longo_ini) if longo_ini else min(km_ini * 0.3, longo_max)
    frac = m.get("frac_longo", 0.30)
    longo_pico = longo_pedido if longo_pedido else min(km_pico * frac, longo_max)
    # proporção máxima longo/semana: a padrão, ou a do pedido (com folga) quando
    # o treinador pediu um longo maior que a fração do objetivo
    teto_frac = max(frac + 0.05, (longo_pico / km_pico + 0.02) if km_pico else 0)
    recup_cada = int(recup_cada or 0)
    corte = 1.0 - float(recup_corte_pct if recup_corte_pct is not None else 25.0) / 100.0

    def e_leve(i):
        return recup_cada > 0 and (i + 1) % recup_cada == 0 and i < build - 1

    # rampa só pelas semanas de carga do build: a semana leve não conta degrau
    carga = [i for i in range(build) if not e_leve(i)]
    n_carga = len(carga)
    km_carga, longo_carga = {}, {}
    # o km inicial e o pico pedidos são exatos: a rampa sai de um e chega no
    # outro. O teto de aumento só escolhe a forma da subida (linear quando o 1º
    # salto, o maior em %, cabe nele; senão % igual em todas as semanas, a
    # forma mais suave entre os dois números) e nunca move as pontas
    p = float(progressao_max_pct) / 100.0 if progressao_max_pct else None
    passos = max(n_carga - 1, 1)
    linear_cabe = (not p or km_ini <= 0 or
                   (km_ini + (km_pico - km_ini) / passos) / km_ini <= 1 + p + 1e-9)
    razao = (km_pico / km_ini) ** (1 / passos) if km_ini > 0 else 1.0
    for k, i in enumerate(carga):
        t = k / passos
        km_carga[i] = (km_ini + (km_pico - km_ini) * t if linear_cabe
                       else km_ini * razao ** k)
        longo_carga[i] = longo_ini + (longo_pico - longo_ini) * t
    # pico da rampa: polimento, prova e pós-prova partem dele
    if km_carga:
        km_pico = max(km_carga.values())
        longo_pico = min(longo_carga[max(km_carga, key=km_carga.get)], longo_max)

    rows = []
    for i in range(n):
        wseg = seg + dt.timedelta(days=7 * i)
        obs = ""; longo = None
        if i > ip:
            fase, km = "Recuperação", km_pico * 0.35
            obs = "pós-prova: só rodagem leve"
        elif i == ip:
            # a semana da prova conta a própria prova (com aquecimento) e um
            # volume leve nos outros dias; 40% do pico não cabia nem a prova
            prova_km = {"5k": 5, "10k": 10, "21k": 21.1, "42k": 42.2}.get(objetivo or PADRAO, 10)
            aquec = 1.0 if prova_km > 30 else 2.0
            resto = km_pico * (0.30 if prova_km <= 10 else 0.25)
            fase, km = "Prova", max(km_pico * 0.40, prova_km + aquec + resto)
            obs = "semana da prova: ativação na véspera"
        elif i >= ip - taper:
            k = i - (ip - taper)                                  # 0,1,2 dentro do taper
            fator = [0.70, 0.55, 0.45][k] if taper == 3 else ([0.70, 0.55][k] if taper == 2 else [0.65][k])
            fase, km = "Polimento", km_pico * fator
            longo = min(longo_pico * (0.65 if k == 0 else 0.5), longo_max)
            obs = m["chave"]["Polimento"]
        else:
            fase = "Base" if i < n_base else "Específico"
            obs = m["chave"][fase]
            if i in km_carga:
                km, longo = km_carga[i], longo_carga[i]
            else:
                # semana leve: corta a partir da última semana de carga
                prev = max((j for j in km_carga if j < i), default=None)
                km = (km_carga[prev] if prev is not None else km_ini) * corte
                longo = (longo_carga[prev] if prev is not None else longo_ini) * corte
                obs = "semana leve: só rodagem"
        km = round(km)
        if longo is not None:
            longo = min(longo, km * teto_frac if km else longo)
            longo = round(longo * 2) / 2
            obs = f"{obs} · longo {longo:g} km"
        rows.append({"idx": i + 1, "inicio": wseg.isoformat(), "fase": fase,
                     "km": km, "longo": longo, "obs": obs})
    return rows
