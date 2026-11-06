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


def fator_semana_prova_b(km):
    """Corte do km da semana da prova B (mini-polimento): 15% até 10 km, 20% até a
    meia, 30% acima. Convenção do treinador; não há estudo sobre prova secundária."""
    km = float(km or 0)
    return 0.85 if km <= 10.5 else 0.8 if km <= 21.5 else 0.7


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
              longo_pico=None, fases_ciclo=None, ini_auto=False, min_km=None,
              dias_semana=None, semana_min=None, longo_min=None, prova_km=None, provas=None):
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
        decide); sem ele, o longo de pico sai da fração do km de pico.
    fases_ciclo: ciclo SEM prova, do início até `fim` (o fim do período):
        "base" = todas as semanas de Base; "especifico" = todas de Específico;
        "base_especifico" = Base e depois Específico. Sem polimento, sem semana de prova; a última semana é o
        pico (km e longo pedidos).
    ini_auto: o km inicial NÃO foi digitado pelo treinador (veio do histórico).
        Então o ciclo sai do pico pedido: começa no mínimo em
        pico / (1 + aumento)^(semanas de carga - 1), e o longo inicial acompanha
        na mesma proporção do longo de pico. Km inicial digitado é respeitado.
    min_km / dias_semana: nenhuma semana fica abaixo do longo dela mais os
        outros dias de treino com o mínimo por treino (e o longo fica acima
        do mínimo por treino).
    semana_min: menor semana pedida. Nenhuma semana de Base/Específico (a leve
        também) fica abaixo dela, e o ciclo começa nela ou acima; polimento,
        prova e pós-prova ficam de fora.
    longo_min: menor longo pedido. Nenhum longo de Base/Específico (o da semana
        leve também) fica abaixo dele, e a rampa do longo começa nele ou acima;
        polimento, prova e pós-prova ficam de fora. A semana sobe junto quando
        não comporta o longo.
    prova_km: distância da prova A quando não é 5, 10, 21 ou 42 km (o objetivo
        é a estrutura mais próxima; a semana da prova conta essa distância).
    provas: [{date, name, prio, km}] - provas B e C do ciclo (a A é prova_data).
        A semana da B tem mini-polimento (fator_semana_prova_b) e, depois de uma
        B de 15 km ou mais, a semana seguinte alivia; B ou C de 15 km ou mais é o
        longo da semana. Polimento, prova, pós-prova e semana leve não mudam."""
    m = MACROS.get(objetivo or PADRAO, MACROS[PADRAO])
    ini = dt.date.fromisoformat(inicio) if isinstance(inicio, str) else inicio
    seg = ini - dt.timedelta(days=ini.weekday())
    if fases_ciclo:
        f = fim or prova_data
        f = dt.date.fromisoformat(f) if isinstance(f, str) else f
        fim_seg = f - dt.timedelta(days=f.weekday())
        n = max(int((fim_seg - seg).days / 7) + 1, 1)
        ip = n                                                  # nenhuma semana de prova
        taper = 0
        build = n
        n_base = (n if fases_ciclo == "base" else 0 if fases_ciclo == "especifico"
                  else max(1, round(build * m["fases"]["Base"])))
    else:
        prova = dt.date.fromisoformat(prova_data) if isinstance(prova_data, str) else prova_data
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
    # menor longo: o maior longo digitado manda nele; sem maior longo, o pico sobe até o piso
    lmn = float(longo_min) if longo_min else 0.0
    if longo_pedido: lmn = min(lmn, longo_pedido)
    elif lmn: longo_pico = max(longo_pico, lmn)
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
    # ponto de partida calculado pelo pico pedido (quando o treinador não digitou
    # o km inicial): o histórico não pode levar o ciclo a semanas de 4 km com o
    # pico em 35
    if ini_auto and km_pico > 0:
        p_auto = float(progressao_max_pct) / 100.0 if progressao_max_pct else 0.10
        km_ini = max(km_ini, km_pico / (1 + p_auto) ** max(n_carga - 1, 0))
        if longo_pico:
            longo_ini = max(longo_ini, longo_pico * km_ini / km_pico)
    if min_km:
        longo_ini = max(longo_ini, float(min_km) + 0.5)
    km_ini = min(km_ini, km_pico)
    sm = min(float(semana_min), km_pico) if semana_min else 0.0
    km_ini = max(km_ini, sm)
    longo_ini = max(longo_ini, lmn)
    if longo_pico:
        longo_ini = min(longo_ini, longo_pico)
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
            dist = float(prova_km) if prova_km else {"5k": 5, "10k": 10, "21k": 21.1, "42k": 42.2}.get(objetivo or PADRAO, 10)
            aquec = 1.0 if dist > 30 else 2.0
            resto = km_pico * (0.30 if dist <= 10 else 0.25)
            fase, km = "Prova", max(km_pico * 0.40, dist + aquec + resto)
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
            km = max(km, sm)
        km = round(km)
        if longo is not None:
            longo = min(longo, km * teto_frac if km else longo)
            if lmn and fase in ("Base", "Específico"):
                longo = max(longo, lmn)                 # menor longo pedido
                km = max(km, int(-(-longo // 1)))       # a semana comporta o longo
            longo = round(longo * 2) / 2
            obs = f"{obs} · longo {longo:g} km"
        rows.append({"idx": i + 1, "inicio": wseg.isoformat(), "fase": fase,
                     "km": km, "longo": longo, "obs": obs})
    _encaixar_provas_bc(rows, provas, sm, dist_a=float(prova_km) if prova_km else
                        {"5k": 5, "10k": 10, "21k": 21.1, "42k": 42.2}.get(objetivo or PADRAO, 10))
    # piso da semana: o longo dela + os outros dias com o mínimo por treino
    if min_km:
        import re as _re
        outros = max(int(dias_semana) - 1, 1) if dias_semana else 1
        for r in rows:
            if r["longo"] is None or r["fase"] == "Prova":
                continue
            L = max(r["longo"], float(min_km) + 0.5)
            L = round(L * 2) / 2
            piso_sem = int(-(-(L + outros * float(min_km)) // 1))       # arredonda para cima
            if L != r["longo"]:
                r["obs"] = _re.sub(r"longo [\d.,]+ km", f"longo {L:g} km", r["obs"])
                r["longo"] = L
            if r["km"] < piso_sem:
                r["km"] = piso_sem
    return rows


def _encaixar_provas_bc(rows, provas, semana_min=0.0, dist_a=10.0):
    """Marca as provas B e C nas semanas do ciclo e ajusta o km pela regra da B
    (ver gerar_atp). Mexe só em semanas de Base e Específico que não são leves."""
    import re as _re
    if not provas:
        return
    por_seg = {r["inicio"]: i for i, r in enumerate(rows)}
    for p in sorted(provas, key=lambda x: str(x.get("date"))):
        pr = (p.get("prio") or "").upper()
        if pr not in ("B", "C"):
            continue
        try:
            d0 = dt.date.fromisoformat(str(p.get("date"))[:10])
        except ValueError:
            continue
        i = por_seg.get((d0 - dt.timedelta(days=d0.weekday())).isoformat())
        if i is None:
            continue
        r = rows[i]
        try:
            k = float(p.get("km") or 0) or None
        except (TypeError, ValueError):
            k = None
        kk = k or dist_a
        nome = (p.get("name") or p.get("nome") or "prova").strip()
        tag = f"prova {pr}: {nome} {d0:%d/%m}" + (f" ({k:g} km)" if k else "")
        r["obs"] = f'{r["obs"]} · {tag}' if r["obs"] else tag
        treino = r["fase"] in ("Base", "Específico")
        carga = treino and "leve" not in r["obs"]
        if treino and kk >= 15 and r["longo"] is not None:
            r["longo"] = None                                  # a prova é o longo da semana
            r["obs"] = _re.sub(r" · longo [\d.,]+ km", "", r["obs"]) + " · longo = a prova"
        if treino:                                             # a semana comporta a prova
            r["km"] = max(r["km"], int(-(-(kk + 4) // 1)))
        if pr != "B":
            continue
        if carga:
            r["km"] = max(round(r["km"] * fator_semana_prova_b(kk)), int(-(-(kk + 4) // 1)), round(semana_min or 0))
        if kk >= 15 and i + 1 < len(rows):
            n = rows[i + 1]
            if n["fase"] in ("Base", "Específico") and "leve" not in n["obs"]:
                n["km"] = max(round(n["km"] * (0.85 if kk <= 21.5 else 0.6)), round(semana_min or 0))
                n["obs"] = f'{n["obs"]} · pós-prova B' if n["obs"] else "pós-prova B"

