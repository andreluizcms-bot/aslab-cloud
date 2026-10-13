# -*- coding: utf-8 -*-
"""Relatório diário de faltas: alunos com treino PLANEJADO ontem que não realizaram nada.

Uso:
    python daily_absent.py                    # ontem
    python daily_absent.py --date 2026-07-10  # data específica
    python daily_absent.py --notify           # + notificação do macOS
Saída: imprime no terminal e salva em logs/faltas/faltas_<data>.md
"""
import json, glob, os, argparse, subprocess, datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))

def _excluded():
    try: return set(str(x) for x in json.load(open(os.path.join(BASE,"excluded.json"))).get("ids",[]))
    except Exception: return set()

def _roster():
    try: return set(str(x) for x in json.load(open(os.path.join(BASE,"data","roster.json"))).get("ids",[]))
    except Exception: return None
DIAS = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

def titlecase(s):
    return " ".join(w.capitalize() if len(w) > 2 else w.lower() for w in (s or "").split())

def report(day):
    """Faltas do dia — via banco (data/aslab.db)."""
    import db as _db
    con = _db.get_conn(); _db.init_db(con)
    d = day.isoformat()
    tem_mes = con.execute("SELECT 1 FROM treinos WHERE mes=? LIMIT 1",
                          (day.strftime("%Y-%m"),)).fetchone()
    if not tem_mes:
        con.close(); return None
    faltas, fez_outro, treinaram = [], [], 0
    for aid, nome_raw in con.execute("SELECT id, nome FROM atletas WHERE ativo=1"):
        ws = con.execute("""SELECT type, title FROM treinos
                            WHERE atleta_id=? AND date=?""", (aid, d)).fetchall()
        planned = [{"title": t} for ty, t in ws if ty == "planned"]
        done    = [1 for ty, _ in ws if ty == "completed"]
        if done: treinaram += 1
        if planned:
            nome = titlecase(nome_raw)
            titulos = ", ".join((w.get("title") or "Treino") for w in planned)
            if done: fez_outro.append((nome, titulos))
            else:    faltas.append((nome, titulos))
    con.close()
    faltas.sort(key=lambda x: x[0].lower()); fez_outro.sort(key=lambda x: x[0].lower())
    return {"faltas": faltas, "fez_outro": fez_outro, "treinaram": treinaram}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: ontem)")
    ap.add_argument("--notify", action="store_true", help="notificação do macOS")
    a = ap.parse_args()
    day = dt.date.fromisoformat(a.date) if a.date else dt.date.today() - dt.timedelta(days=1)

    rep = report(day)
    if rep is None:
        print(f"Sem dados coletados para {day.strftime('%Y-%m')}."); return

    titulo = f"Faltas de {DIAS[day.weekday()]}, {day.strftime('%d/%m/%Y')}"
    lines = [f"# {titulo}", ""]
    lines.append(f"**{len(rep['faltas'])} aluno(s) com treino planejado e NÃO realizado** · "
                 f"{len(rep['fez_outro'])} fizeram outro treino no lugar · "
                 f"{rep['treinaram']} treinaram no dia.")
    lines.append("")
    if rep["faltas"]:
        lines.append("## ❌ Não treinaram (tinham plano)")
        for nome, t in rep["faltas"]:
            lines.append(f"- **{nome}** — planejado: {t}")
    else:
        lines.append("## ✅ Ninguém faltou — todos que tinham plano treinaram!")
    if rep["fez_outro"]:
        lines.append("")
        lines.append("## 🔁 Pularam o planejado, mas fizeram outro treino")
        for nome, t in rep["fez_outro"]:
            lines.append(f"- {nome} — planejado era: {t}")
    md = "\n".join(lines)

    outdir = os.path.join(BASE, "logs", "faltas"); os.makedirs(outdir, exist_ok=True)
    outp = os.path.join(outdir, f"faltas_{day.isoformat()}.md")
    open(outp, "w").write(md + "\n")
    print(md)
    print(f"\n-> salvo em {outp}")

    if a.notify:
        n = len(rep["faltas"])
        msg = (f"{n} aluno(s) não treinaram ontem" if n else "Ninguém faltou ontem 🎉")
        subprocess.run(["osascript", "-e",
                        f'display notification "{msg} — veja no painel" with title "AS Endurance LAB"'],
                       capture_output=True)

if __name__ == "__main__":
    main()
