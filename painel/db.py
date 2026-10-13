# -*- coding: utf-8 -*-
"""Base de dados do AS Endurance LAB (SQLite).

Arquivo único em data/aslab.db. A coleta grava aqui além dos JSONs
(gravação dupla durante a transição). Esquema pensado para migrar
fácil para Postgres/Supabase no futuro (SQL padrão, sem extensões).
"""
import json, os, sqlite3, datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "aslab.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS atletas(
  id TEXT PRIMARY KEY,
  nome TEXT NOT NULL,
  email TEXT,
  foto TEXT,
  ativo INTEGER NOT NULL DEFAULT 1,
  atualizado TEXT
);
CREATE TABLE IF NOT EXISTS treinos(
  atleta_id TEXT NOT NULL,
  mes TEXT NOT NULL,              -- YYYY-MM (partição lógica: coleta substitui o mês inteiro)
  date TEXT NOT NULL,             -- YYYY-MM-DD
  type TEXT NOT NULL,             -- completed | planned
  title TEXT,
  kind TEXT,                      -- run | bike | strength | swim | walk | other
  sport TEXT,
  wt INTEGER,
  wid TEXT,                       -- id do treino no TP (quando disponível)
  dist_km REAL, dur_h REAL, tss REAL,
  hr REAL, cad REAL, if_ REAL, elev REAL, cal REAL,
  was_planned INTEGER
);
CREATE INDEX IF NOT EXISTS ix_treinos_atleta_data ON treinos(atleta_id, date);
CREATE INDEX IF NOT EXISTS ix_treinos_mes ON treinos(mes);
CREATE TABLE IF NOT EXISTS fitness_diario(
  atleta_id TEXT NOT NULL, date TEXT NOT NULL,
  ctl REAL, atl REAL, tsb REAL, tss REAL,
  PRIMARY KEY(atleta_id, date)
);
CREATE TABLE IF NOT EXISTS metricas_diarias(
  atleta_id TEXT NOT NULL, date TEXT NOT NULL,
  fc_rep REAL, hrv REAL, sono_h REAL,
  PRIMARY KEY(atleta_id, date)
);
CREATE TABLE IF NOT EXISTS provas(
  atleta_id TEXT NOT NULL, date TEXT NOT NULL, nome TEXT NOT NULL, tipo TEXT,
  PRIMARY KEY(atleta_id, date, nome)
);
CREATE TABLE IF NOT EXISTS recados(
  atleta_id TEXT NOT NULL, mes TEXT NOT NULL, texto TEXT,
  PRIMARY KEY(atleta_id, mes)
);
CREATE TABLE IF NOT EXISTS periodizacao(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  atleta_id TEXT NOT NULL,
  nome TEXT NOT NULL,
  prova_data TEXT NOT NULL,
  inicio TEXT NOT NULL,          -- segunda-feira da 1ª semana
  criado TEXT,
  obs TEXT
);
CREATE TABLE IF NOT EXISTS periodizacao_semanas(
  plano_id INTEGER NOT NULL,
  idx INTEGER NOT NULL,          -- 1..N
  inicio TEXT NOT NULL,          -- segunda da semana
  fase TEXT,
  km REAL, horas REAL, obs TEXT,
  longo_km REAL,                 -- distância do longo da semana
  PRIMARY KEY(plano_id, idx)
);
CREATE TABLE IF NOT EXISTS periodizacao_provas(
  plano_id INTEGER NOT NULL,
  date TEXT NOT NULL,            -- YYYY-MM-DD
  nome TEXT NOT NULL,
  prio TEXT NOT NULL DEFAULT 'A',  -- A | B | C
  PRIMARY KEY(plano_id, date, nome)
);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""

def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if os.environ.get("ASLAB_NUVEM"):
        import nuvem                  # na nuvem as gravações também vão para o banco do Mac
        con = sqlite3.connect(DB_PATH, timeout=30, factory=nuvem.ConexaoNuvem)
    else:
        con = sqlite3.connect(DB_PATH, timeout=30)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con

def init_db(con=None):
    own = con is None
    con = con or get_conn()
    con.executescript(SCHEMA)
    _migrate(con)
    con.commit()
    if own: con.close()

def _migrate(con):
    """Migrações leves para bancos criados antes das colunas novas."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(periodizacao_semanas)")}
    if "longo_km" not in cols:
        con.execute("ALTER TABLE periodizacao_semanas ADD COLUMN longo_km REAL")
    # ciclos antigos: a prova única vira prova A na tabela nova
    con.execute("""INSERT OR IGNORE INTO periodizacao_provas(plano_id, date, nome, prio)
                   SELECT p.id, p.prova_data, p.nome, 'A' FROM periodizacao p
                   WHERE NOT EXISTS (SELECT 1 FROM periodizacao_provas pp
                                     WHERE pp.plano_id = p.id)""")

def upsert_rec(rec, month, con=None, ativo=1):
    """Grava o registro de UM atleta em UM mês (substitui os treinos do mês)."""
    if rec.get("error"): return False
    own = con is None
    con = con or get_conn()
    init_db(con)
    aid = str(rec["id"])
    con.execute("""INSERT INTO atletas(id, nome, foto, ativo, atualizado)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     nome=excluded.nome, foto=COALESCE(excluded.foto, atletas.foto),
                     ativo=excluded.ativo, atualizado=excluded.atualizado""",
                (aid, rec.get("name") or "?", rec.get("photo"), ativo, dt.date.today().isoformat()))
    con.execute("DELETE FROM treinos WHERE atleta_id=? AND mes=?", (aid, month))
    rows = []
    for w in rec.get("workouts", []):
        rows.append((aid, month, (w.get("date") or "")[:10], w.get("type") or "",
                     w.get("title"), w.get("kind"), w.get("sport"), w.get("wt"),
                     str(w.get("wid")) if w.get("wid") is not None else None,
                     w.get("dist_km"), w.get("dur_h"), w.get("tss"), w.get("hr"),
                     w.get("cad"), w.get("if_"), w.get("elev"), w.get("cal"),
                     1 if w.get("was_planned") else 0))
    con.executemany("""INSERT INTO treinos(atleta_id,mes,date,type,title,kind,sport,wt,wid,
                        dist_km,dur_h,tss,hr,cad,if_,elev,cal,was_planned)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    for x in ((rec.get("fitness") or {}).get("daily") or []):
        d = (x.get("date") or "")[:10]
        if not d: continue
        con.execute("""INSERT INTO fitness_diario(atleta_id,date,ctl,atl,tsb,tss)
                       VALUES(?,?,?,?,?,?)
                       ON CONFLICT(atleta_id,date) DO UPDATE SET
                         ctl=excluded.ctl, atl=excluded.atl, tsb=excluded.tsb, tss=excluded.tss""",
                    (aid, d, x.get("ctl"), x.get("atl"), x.get("tsb"), x.get("tss")))
    for x in (rec.get("metrics_daily") or []):
        d = (x.get("date") or "")[:10]
        if not d: continue
        con.execute("""INSERT INTO metricas_diarias(atleta_id,date,fc_rep,hrv,sono_h)
                       VALUES(?,?,?,?,?)
                       ON CONFLICT(atleta_id,date) DO UPDATE SET
                         fc_rep=COALESCE(excluded.fc_rep,metricas_diarias.fc_rep),
                         hrv=COALESCE(excluded.hrv,metricas_diarias.hrv),
                         sono_h=COALESCE(excluded.sono_h,metricas_diarias.sono_h)""",
                    (aid, d, x.get("fc_rep"), x.get("hrv"), x.get("sono_h")))
    ev = rec.get("event")
    if ev and ev.get("date"):
        con.execute("""INSERT OR REPLACE INTO provas(atleta_id,date,nome,tipo)
                       VALUES(?,?,?,?)""",
                    (aid, ev["date"][:10], ev.get("name") or "?", str(ev.get("type") or "")))
    con.commit()
    if own: con.close()
    return True

def sync_roster(ids, con=None):
    """Marca ativo=1 para os ids do roster (grupos) e 0 para o resto."""
    own = con is None
    con = con or get_conn()
    init_db(con)
    ids = [str(x) for x in ids]
    con.execute("UPDATE atletas SET ativo=0")
    con.executemany("UPDATE atletas SET ativo=1 WHERE id=?", [(i,) for i in ids])
    con.commit()
    if own: con.close()

def upsert_recados(month, msgs, con=None):
    own = con is None
    con = con or get_conn()
    init_db(con)
    con.executemany("INSERT OR REPLACE INTO recados(atleta_id,mes,texto) VALUES(?,?,?)",
                    [(str(k), month, v) for k, v in (msgs or {}).items()])
    con.commit()
    if own: con.close()

def stats():
    con = get_conn(); init_db(con)
    out = {}
    for t in ("atletas", "treinos", "fitness_diario", "metricas_diarias", "provas", "recados"):
        out[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    out["ativos"] = con.execute("SELECT COUNT(*) FROM atletas WHERE ativo=1").fetchone()[0]
    con.close()
    return out
