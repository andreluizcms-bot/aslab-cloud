# -*- coding: utf-8 -*-
"""Ponte do painel com a nuvem.

No Mac o painel roda como sempre. Na nuvem (ASLAB_NUVEM=1) ele lê o pacote de dados
que o Mac publica no Supabase (snapshot_nuvem.py) e manda para o Mac, pela fila
`comandos`, só o que precisa de lá: TrainingPeaks ao vivo, PDFs, scripts de coleta
e as gravações no banco do Lab.
"""
import os, io, re, json, time, base64, sqlite3, tarfile, datetime as dt

NUVEM = bool(os.environ.get("ASLAB_NUVEM"))
BASE = os.path.dirname(os.path.abspath(__file__))

# funções de painel_mac.py que rodam no Mac quando o painel está na nuvem
REMOTOS = {"refresh_athlete", "records", "history", "semana", "eventos", "detalhe", "atletas",
           "drifts", "generate_athlete_pdf", "generate_period_pdf", "generate_weekly_pdf",
           "semanais_lote", "pdf_periodizacao", "retest", "email_configurado", "enviar_emails",
           "arquivo"}
SCRIPTS = {"collect.py", "gen_summaries.py", "render_all_modern.py", "refresh_metrics.py"}


# ---------- codificação (datas, caminhos e chaves não-texto atravessam o JSON) ----------
def codificar(o, base=BASE):
    if isinstance(o, dt.datetime): return {"__dt": o.isoformat()}
    if isinstance(o, dt.date): return {"__d": o.isoformat()}
    if isinstance(o, str):
        return {"__rel": os.path.relpath(o, base)} if o.startswith(base + os.sep) else o
    if isinstance(o, dict):
        if all(isinstance(k, str) for k in o):
            return {k: codificar(v, base) for k, v in o.items()}
        return {"__kv": [[codificar(k, base), codificar(v, base)] for k, v in o.items()]}
    if isinstance(o, (list, tuple, set)): return [codificar(x, base) for x in o]
    if hasattr(o, "item") and not isinstance(o, (int, float, bool)):
        try: return o.item()                     # escalares do numpy
        except Exception: pass
    return o

def decodificar(o, base=BASE):
    if isinstance(o, dict):
        if len(o) == 1:
            k, v = next(iter(o.items()))
            if k == "__d": return dt.date.fromisoformat(v)
            if k == "__dt": return dt.datetime.fromisoformat(v)
            if k == "__rel": return os.path.join(base, v)
            if k == "__kv":
                return {_chave(decodificar(a, base)): decodificar(b, base) for a, b in v}
        return {k: decodificar(v, base) for k, v in o.items()}
    if isinstance(o, list): return [decodificar(x, base) for x in o]
    return o

def _chave(k):
    return tuple(k) if isinstance(k, list) else k

def arquivos_do_resultado(o, base=BASE, achados=None):
    """Caminhos de arquivos existentes dentro da pasta do painel citados no resultado."""
    achados = set() if achados is None else achados
    if isinstance(o, str):
        if o.startswith(base + os.sep) and os.path.isfile(o): achados.add(o)
    elif isinstance(o, dict):
        for v in o.values(): arquivos_do_resultado(v, base, achados)
    elif isinstance(o, (list, tuple)):
        for v in o: arquivos_do_resultado(v, base, achados)
    return achados


# ---------- conexão com o Supabase ----------
def _db_url():
    url = os.environ.get("DB_URL")
    if url: return url
    cfg = os.path.join(BASE, "supabase_config.json")
    if os.path.exists(cfg): return json.load(open(cfg))["db_url"]
    raise RuntimeError("DB_URL não configurado")

def _pg():
    import psycopg2
    return psycopg2.connect(_db_url(), connect_timeout=15)

def mac_ligado():
    """O worker grava um sinal de vida a cada volta; ocupado com um comando também conta."""
    try:
        con = _pg()
        try:
            with con.cursor() as c:
                c.execute("SELECT to_regclass('public.worker_vivo')")
                if c.fetchone()[0]:
                    c.execute("SELECT extract(epoch FROM now()-visto) FROM worker_vivo WHERE k='mac'")
                    r = c.fetchone()
                    if r and r[0] is not None and r[0] < 150: return True
                c.execute("""SELECT 1 FROM comandos WHERE status='executando'
                             AND atualizado > now() - interval '2 hours' LIMIT 1""")
                return bool(c.fetchone())
        finally:
            con.close()
    except Exception:
        return False

def enfileirar(tipo, params):
    con = _pg()
    try:
        with con.cursor() as c:
            c.execute("INSERT INTO comandos(tipo, params) VALUES(%s, %s::jsonb) RETURNING id",
                      (tipo, json.dumps(params or {})))
            cid = c.fetchone()[0]
        con.commit(); return cid
    finally:
        con.close()

def esperar(cid, segundos=900, msg="Pedindo ao Mac…"):
    """Aguarda o worker devolver. Mostra uma barra discreta enquanto isso."""
    import streamlit as st
    barra = st.progress(0.0, text=msg)
    con = _pg()
    try:
        t0 = time.time()
        while time.time() - t0 < segundos:
            con.rollback()
            with con.cursor() as c:
                c.execute("SELECT status, resultado FROM comandos WHERE id=%s", (cid,))
                r = c.fetchone()
            stt, res = (r[0], r[1]) if r else ("sumiu", None)
            if stt in ("ok", "erro", "sumiu"):
                barra.empty(); return stt, res
            i = int(time.time() - t0)
            barra.progress(min(0.97, i / segundos),
                           text=f"{msg} ({i}s)" if stt == "executando" else f"Na fila do Mac… ({i}s)")
            time.sleep(1.5)
    finally:
        con.close()
    barra.empty()
    return "esperando", None


class MacDesligado(RuntimeError):
    pass

def _exige_mac():
    if not mac_ligado():
        raise MacDesligado("O Mac está desligado ou sem internet. Esta ação usa o TrainingPeaks "
                           "ou gera PDF no Mac; ligue o Mac e tente de novo.")

def chamar(fn, *args, msg=None, segundos=900):
    """Roda painel_mac.<fn>(*args) no Mac e traz o resultado e os arquivos gerados."""
    _exige_mac()
    cid = enfileirar("painel", {"fn": fn, "args": codificar(list(args))})
    stt, res = esperar(cid, segundos, msg or "Buscando no Mac…")
    if stt == "esperando": raise RuntimeError("O Mac não respondeu a tempo. Tente de novo em instantes.")
    if stt != "ok": raise RuntimeError(res or "falhou no Mac")
    j = json.loads(res)
    for rel, b64 in (j.get("files") or {}).items():
        p = os.path.normpath(os.path.join(BASE, rel))
        if not p.startswith(BASE + os.sep): continue
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh: fh.write(base64.b64decode(b64))
    return decodificar(j.get("r"))


class Remoto:
    """Mesmo jeito de usar que o módulo painel_mac; as funções do Mac vão pela fila."""
    def __init__(self, mod): self._mod = mod
    def __getattr__(self, nome):
        if nome in REMOTOS:
            return lambda *a, **k: chamar(nome, *a, **k)
        return getattr(self._mod, nome)


def rodar_script(cmd, ph):
    """Equivalente ao _run_stream do painel: roda o script no Mac e mostra o fim do log."""
    argv = [x for x in cmd[1:] if x != "-u"]
    if not argv or argv[0] not in SCRIPTS:
        ph.error("Esse comando não roda pela nuvem."); return 1
    try: _exige_mac()
    except MacDesligado as e:
        ph.error(str(e)); return 1
    ph.info(f"Rodando no Mac: {' '.join(argv)}")
    cid = enfileirar("script", {"argv": argv})
    stt, res = esperar(cid, 3600, f"Rodando {argv[0]} no Mac…")
    ph.code(res or stt)
    if stt == "ok":
        sincronizar(forcar=True)
        return 0
    return 1


# ---------- pacote de dados (snapshot) ----------
_MARCA = os.path.join(BASE, "data", ".snapshot_versao")

def versao_local():
    try: return open(_MARCA).read().strip()
    except Exception: return ""

def _membro_ok(m):
    n = os.path.normpath(m.name)
    return (m.isfile() or m.isdir()) and not n.startswith(("/", "..")) and ".." not in n.split(os.sep)

def sincronizar(forcar=False):
    """Baixa o pacote mais novo do Supabase se ele for diferente do que está aqui.
    Retorna a versão nova quando trocou, senão None."""
    con = _pg()
    try:
        with con.cursor() as c:
            c.execute("""SELECT versao FROM painel_snapshot GROUP BY versao, total
                         HAVING count(*)=total ORDER BY versao DESC LIMIT 1""")
            r = c.fetchone()
            if not r: return None
            v = r[0]
            if v == versao_local(): return None
            c.execute("SELECT dados FROM painel_snapshot WHERE versao=%s ORDER BY parte", (v,))
            blob = b"".join(bytes(x[0]) for x in c.fetchall())
    finally:
        con.close()
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        membros = [m for m in tar.getmembers() if _membro_ok(m)]
        db_tmp = None
        for m in membros:
            if m.name == "data/aslab.db":
                db_tmp = os.path.join(BASE, "data", ".aslab.db.novo")
                os.makedirs(os.path.dirname(db_tmp), exist_ok=True)
                with tar.extractfile(m) as src, open(db_tmp, "wb") as dst: dst.write(src.read())
            else:
                tar.extract(m, BASE)
    if db_tmp:
        for suf in ("-wal", "-shm"):
            try: os.remove(os.path.join(BASE, "data", "aslab.db" + suf))
            except FileNotFoundError: pass
        os.replace(db_tmp, os.path.join(BASE, "data", "aslab.db"))
    with open(_MARCA, "w") as fh: fh.write(v)
    return v

def pdfs_no_mac():
    """{caminho relativo: mtime} dos PDFs/ZIPs que existem no Mac (vem no pacote)."""
    p = os.path.join(BASE, "data", "_pdfs_mac.json")
    try: return json.load(open(p))
    except Exception: return {}


# ---------- banco do Lab: o que a nuvem grava vai também para o Mac ----------
_ESCRITA = re.compile(r"^\s*(INSERT|UPDATE|DELETE|REPLACE)\b", re.I)
_INSERT_SIMPLES = re.compile(r"^\s*INSERT\s+INTO\s+(\w+)\s*\(([^)]*)\)\s*VALUES\s*\(", re.I | re.S)

class _Cursor(sqlite3.Cursor):
    def execute(self, sql, params=()):
        r = super().execute(sql, params)
        self.connection._anota(sql, params, self.lastrowid, self.rowcount, False)
        return r
    def executemany(self, sql, seq):
        seq = [tuple(x) if isinstance(x, (list, tuple)) else x for x in seq]
        r = super().executemany(sql, seq)
        self.connection._anota(sql, seq, None, self.rowcount, True)
        return r

class ConexaoNuvem(sqlite3.Connection):
    """sqlite3 normal; as escritas confirmadas (commit) são repetidas no banco do Mac."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self._pend = []
    def cursor(self, factory=_Cursor):
        return super().cursor(factory)
    def execute(self, sql, params=()):
        return self.cursor().execute(sql, params)
    def executemany(self, sql, seq):
        return self.cursor().executemany(sql, seq)
    def _anota(self, sql, params, rowid, n, many):
        if not _ESCRITA.match(sql) or n == 0: return
        if not many and rowid and isinstance(params, (list, tuple)):
            m = _INSERT_SIMPLES.match(sql)
            if m and "rowid" not in m.group(2).lower():
                # mesmo id dos dois lados: as tabelas filhas apontam para ele
                sql = sql[:m.start(2)] + "rowid, " + sql[m.start(2):]
                sql = re.sub(r"VALUES\s*\(", "VALUES(?, ", sql, count=1, flags=re.I)
                params = [rowid] + list(params)
        self._pend.append({"sql": sql, "params": codificar(list(params) if not isinstance(params, dict) else params),
                           "many": many})
    def commit(self):
        super().commit()
        if self._pend:
            lote, self._pend = self._pend, []
            enfileirar("sql", {"stmts": lote})      # fica na fila se o Mac estiver desligado
