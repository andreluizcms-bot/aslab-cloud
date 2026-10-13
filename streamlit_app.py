# -*- coding: utf-8 -*-
"""AS Endurance LAB · Cloud — o painel do Mac rodando na nuvem.

O painel (pasta painel/) é o mesmo do Mac. Os dados chegam pelo Supabase
(pacote que o Mac publica a cada sincronização); o que precisa do TrainingPeaks
ou gera PDF vai para o Mac pela fila `comandos`.

Secrets (share.streamlit.io → Settings → Secrets):
  DB_URL = "postgresql://..."
  APP_PASSWORD = "..."
"""
import os, sys, hashlib
import streamlit as st

AQUI = os.path.dirname(os.path.abspath(__file__))
PAINEL = os.path.join(AQUI, "painel")
sys.path.insert(0, PAINEL)

def _sec(k):
    try: return st.secrets.get(k)
    except Exception: return None

if _sec("DB_URL"): os.environ["DB_URL"] = _sec("DB_URL")
os.environ["ASLAB_NUVEM"] = "1"
os.environ.setdefault("TP_MCP_SRC", os.path.join(AQUI, "_sem_tp"))

st.set_page_config(page_title="AS Endurance LAB", page_icon=os.path.join(PAINEL, "assets", "png", "icon.png"),
                   layout="wide", initial_sidebar_state="auto")

# ---------- senha (mesmo cookie do app antigo: quem já entrou não digita de novo) ----------
def _tok(pw):
    return hashlib.sha256(("aslab|" + pw).encode()).hexdigest()[:20]

def _lembrar(tok):
    import streamlit.components.v1 as _c
    _c.html(f"""<script>
      try {{
        var W=window.top||window.parent;
        var sec=(W.location.protocol==='https:')?'; Secure':'';
        W.document.cookie='aslab_k={tok}; max-age=31536000; path=/; SameSite=Lax'+sec;
      }} catch(e) {{}}
    </script>""", height=0)

def _gate():
    pw = _sec("APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    if not pw: return True
    tok = _tok(pw)
    try: cookie_ok = st.context.cookies.get("aslab_k") == tok
    except Exception: cookie_ok = False
    if cookie_ok or st.query_params.get("k") == tok or st.session_state.get("auth_ok"):
        if not st.session_state.get("auth_ok"): _lembrar(tok)
        st.session_state["auth_ok"] = True
        return True
    st.markdown("""<style>
      .stApp{background:linear-gradient(180deg,#0a2026,#07171d)}
      header,[data-testid="stSidebar"],footer{display:none!important}
      .gate{margin:14vh auto 18px;text-align:center;color:#eaf3f4;font-family:Inter,system-ui,sans-serif}
      .gate b{font-size:2.2rem;letter-spacing:.02em} .gate span{color:#ee6c4d;letter-spacing:.3em;font-size:.8rem}
    </style><div class="gate"><b>AS</b> ENDURANCE <span>LAB</span></div>""", unsafe_allow_html=True)
    c = st.columns([1, 1.2, 1])[1]
    with c:
        p = st.text_input("Senha", type="password", label_visibility="collapsed", placeholder="Senha do painel")
        if st.button("Entrar", type="primary", use_container_width=True):
            if p == pw:
                st.session_state["auth_ok"] = True
                _lembrar(tok); st.rerun()
            else:
                st.error("Senha incorreta.")
    return False

if not _gate(): st.stop()

# ---------- dados: pacote mais novo do Mac ----------
import nuvem

@st.cache_data(ttl=60, show_spinner=False)
def _sincroniza(_minuto):
    try: nuvem.sincronizar()
    except Exception: pass          # sem rede com o Supabase: segue com o pacote que já tem
    return True

@st.cache_resource
def _lido():
    return {"v": None}

if not nuvem.versao_local():
    with st.spinner("Baixando os dados do Lab…"):
        try: nuvem.sincronizar()
        except Exception as e:
            st.error(f"Não consegui baixar os dados do Lab: {e}"); st.stop()
else:
    import time
    _sincroniza(int(time.time() // 60))
_e = _lido()
if _e["v"] != nuvem.versao_local():
    st.cache_data.clear()              # pacote novo: o painel relê tudo
    _e["v"] = nuvem.versao_local()

pg = st.navigation([st.Page(os.path.join(PAINEL, "app.py"), title="Painel", default=True),
                    st.Page("montar.py", title="Montar treino", url_path="montar")],
                   position="hidden")
pg.run()
