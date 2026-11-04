# -*- coding: utf-8 -*-
"""Gerador de Treinos na nuvem: a MESMA tela do Mac (arquivos em gerador/, copiados por
publicar_nuvem.sh). Cada pedido /api/ da tela passa pela função gerador-api do Supabase e
vai para a fila `comandos`; o worker do Mac chama o gerador local e devolve a resposta.
Regras e dados ficam só no Mac: com ele desligado a tela avisa em vez de fazer."""
import datetime as dt, hashlib, json, os, re, secrets
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
import streamlit as st
import streamlit.components.v1 as components

G = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gerador")


@st.cache_resource(ttl=6 * 86400, show_spinner=False)
def _sessao():
    """Token da tela, criado só depois da senha do app. É o mesmo enquanto o cache durar:
    um rerun ou uma reconexão do Streamlit não recarrega a tela nem perde o que está nela."""
    import psycopg2
    token = secrets.token_urlsafe(32)
    con = psycopg2.connect(os.environ["DB_URL"], connect_timeout=15)
    try:
        with con, con.cursor() as c:
            c.execute("INSERT INTO gerador_sessoes(token_hash, expira) VALUES(%s, now() + interval '7 days')",
                      (hashlib.sha256(token.encode()).hexdigest(),))
    finally:
        con.close()
    return token


def _funcao():
    u = os.environ["DB_URL"]
    m = re.search(r"//postgres\.([a-z0-9]+):", u) or re.search(r"@db\.([a-z0-9]+)\.supabase\.co", u)
    return f"https://{m.group(1)}.supabase.co/functions/v1/gerador-api"


PONTE = r"""
window.__QS = __QS__;
(function () {
  const FN = __FN__, TOKEN = __TOKEN__, real = window.fetch.bind(window);
  const dorme = (ms) => new Promise((r) => setTimeout(r, ms));
  async function chamar(b) {
    let r;
    for (let t = 0; ; t++) {
      try {
        r = await real(FN, { method: "POST", headers: { "Content-Type": "application/json" },
                             body: JSON.stringify({ token: TOKEN, ...b }) });
        break;
      } catch (e) {
        if (t >= 3) throw new Error("Sem conexão com a nuvem. Confira a internet e tente de novo.");
        await dorme(800 * (t + 1));
      }
    }
    const j = await r.json().catch(() => ({}));
    if (r.status === 401) throw new Error("A sessão expirou. Recarregue a página.");
    if (!r.ok) throw new Error(j.erro || "Falha na passagem para o Mac.");
    return j;
  }
  const json = (corpo, status) => new Response(corpo, { status, headers: { "Content-Type": "application/json" } });
  window.fetch = async function (url, opts) {
    if (typeof url !== "string" || !url.startsWith("/api/")) return real(url, opts);
    opts = opts || {};
    const { id } = await chamar({ acao: "pedir", metodo: opts.method || "GET", caminho: url, corpo: opts.body || null });
    const ini = Date.now();
    let espera = 200;
    for (;;) {
      await dorme(espera);
      espera = Math.min(espera * 1.25, 1500);
      const v = await chamar({ acao: "ver", id });
      if (v.status === "ok") { const x = JSON.parse(v.resultado); return json(x.corpo, x.status); }
      if (v.status === "erro") return json(JSON.stringify({ erro: v.resultado }), 500);
      if (v.status === "pendente" && v.mac_s !== null && v.mac_s > 150 && Date.now() - ini > 6000) {
        await chamar({ acao: "cancelar", id }).catch(() => {});
        throw new Error("O Mac está desligado ou sem internet. Ligue o Mac e tente de novo.");
      }
      if (Date.now() - ini > 900000) throw new Error("O Mac não respondeu a tempo.");
    }
  };
  try {                     // a tela ocupa a página inteira, como no Mac
    const f = window.frameElement;
    if (f) f.style.cssText += ";position:fixed;inset:0;width:100%;height:100%;z-index:999990;border:0;background:#0a2026";
  } catch (e) {}
})();
"""


def _html():
    ler = lambda n: open(os.path.join(G, n), encoding="utf-8").read()
    qs = {k: st.query_params[k] for k in ("atleta", "passo", "gerar") if k in st.query_params}
    ponte = (PONTE.replace("__QS__", json.dumps("?" + urlencode(qs) if qs else ""))
                  .replace("__FN__", json.dumps(_funcao())).replace("__TOKEN__", json.dumps(_sessao())))
    hoje = dt.datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    ini = hoje + dt.timedelta(days=(7 - hoje.weekday()) % 7 or 7)
    js = lambda n: ler(n).replace("location.search", "(window.__QS||location.search)")
    h = ler("index.html")
    trocas = [
        ("{{ inicio_padrao }}", ini.isoformat()),
        ("{{ fim_padrao }}", (ini + dt.timedelta(days=27)).isoformat()),
        ('<link rel="stylesheet" href="/static/fonts/faces.css?v={{ v }}">',
         "<style>" + ler("faces.css").replace("/static/fonts/", "/app/static/fonts/") + "</style>"),
        ('<link rel="stylesheet" href="/static/style.css?v={{ v }}">', "<style>" + ler("style.css") + "</style>"),
        ('<script src="/static/app.js?v={{ v }}"></script>',
         "<script>" + ponte + "</script><script>" + js("app.js") + "</script>"),
        ('<script src="/static/shell.js?v={{ v }}"></script>', "<script>" + js("shell.js") + "</script>"),
        ('href="http://127.0.0.1:8520" target="_blank"', 'href="./" target="_parent"'),     # Painel do Lab
        ('<a class="lg" href="/"', '<a class="lg" href="./gerador" target="_parent"'),
    ]
    for a, b in trocas:
        if a not in h: raise RuntimeError(f"tela do gerador mudou, não achei: {a}")
        h = h.replace(a, b)
    return h


st.markdown("<style>header,footer,[data-testid='stSidebar'],[data-testid='stToolbar']{display:none!important}"
            ".block-container{padding:0!important;max-width:100%!important}</style>", unsafe_allow_html=True)
try:
    components.html(_html(), height=900, scrolling=True)
except Exception as e:
    st.error(f"Não consegui abrir o Gerador de Treinos: {e}")
