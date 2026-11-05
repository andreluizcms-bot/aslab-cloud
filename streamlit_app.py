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
import streamlit.components.v1 as _componentes

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

def _icone_aba(pasta_png):
    """Logo do Lab na aba do navegador. O page_icon do Streamlit vira arquivo de mídia da
    sessão e some (erro 500) quando a sessão é renovada com a aba aberta; aqui o ícone vai
    embutido na página (data URI) e um vigia recoloca se alguém trocar."""
    import base64, json as _json
    import streamlit.components.v1 as _c
    try:
        ico=base64.b64encode(open(os.path.join(pasta_png,"favicon.png"),"rb").read()).decode()
        app=base64.b64encode(open(os.path.join(pasta_png,"icon.png"),"rb").read()).decode()
    except Exception:
        return
    js=("(function(){var I='data:image/png;base64,%s',A='data:image/png;base64,%s',d=document;"
        "function f(){var ls=d.querySelectorAll('link[rel~=\"icon\"]');"
        "if(!ls.length){var l=d.createElement('link');l.rel='icon';d.head.appendChild(l);ls=[l];}"
        "ls.forEach(function(l){if(l.href!==I){l.type='image/png';l.href=I;}});"
        "d.querySelectorAll('link[rel=\"apple-touch-icon\"]').forEach(function(l){if(l.href!==A)l.href=A;});}"
        "f();new MutationObserver(f).observe(d.head,{childList:true,subtree:true,attributes:true,attributeFilter:['href']});})();"
        % (ico, app))
    # o script entra no documento do app (e no de fora, na nuvem) para seguir vivo entre reruns
    _c.html("<script>(function(){var c=%s;[window.parent,window.top].forEach(function(W){try{"
            "var d=W.document;if(d.getElementById('lab-icone'))return;var s=d.createElement('script');"
            "s.id='lab-icone';s.textContent=c;d.head.appendChild(s);}catch(e){}});})();</script>"
            % _json.dumps(js), height=0)
_icone_aba(os.path.join(PAINEL, "assets", "png"))

# ---------- senha (mesmo cookie do app antigo: quem já entrou não digita de novo) ----------
def _tok(pw):
    return hashlib.sha256(("aslab|" + pw).encode()).hexdigest()[:20]

def _lembrar(tok):
    _componentes.html(f"""<script>
      try {{
        var W=window.top||window.parent;
        var sec=(W.location.protocol==='https:')?'; Secure':'';
        W.document.cookie='aslab_k={tok}; max-age=31536000; path=/; SameSite=Lax'+sec;
      }} catch(e) {{}}
    </script>""", height=0)

_cookie_navegador = _componentes.declare_component("lab_cookie", path=os.path.join(AQUI, "cookie_comp"))

# SONDA TEMPORÁRIA: mostra só o tamanho do cookie lido no navegador
if st.query_params.get("diag") == "componente":
    _v = _cookie_navegador(default=None, key="lab_cookie_diag")
    st.write("LIDO", "sem resposta" if _v is None else len(_v))
    st.stop()

def _gate():
    pw = _sec("APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    if not pw: return True
    tok = _tok(pw)
    ss = st.session_state
    if not ss.get("auth_ok"):
        if _cookie_navegador(default=None, key="lab_cookie") == tok:
            ss["auth_ok"] = True
        elif st.query_params.get("k") == tok:
            ss["auth_ok"] = ss["gravar_cookie"] = True
    if ss.get("auth_ok"):
        # grava aqui, numa execução que vai até o fim: logo antes de um st.rerun() o iframe
        # some sem rodar, o cookie não fica e o próximo carregamento de página pede a senha
        if ss.get("gravar_cookie"): _lembrar(tok)
        return True
    st.markdown("""<style>
      .stApp{background:linear-gradient(180deg,#0a2026,#07171d)}
      header,[data-testid="stSidebar"],footer{display:none!important}
      .gate{margin:14vh auto 18px;text-align:center;color:#eaf3f4;font-family:Inter,system-ui,sans-serif}
      .gate b{font-size:2.2rem;letter-spacing:.02em} .gate span{color:#ee6c4d;letter-spacing:.3em;font-size:.8rem}
      /* quem já tem o cookie entra direto: o campo só aparece se o componente não reconhecer */
      .stTextInput,.stButton{animation:lab-ap .15s 1.2s both}
      @keyframes lab-ap{from{opacity:0}to{opacity:1}}
    </style><div class="gate"><b>AS</b> ENDURANCE <span>LAB</span></div>""", unsafe_allow_html=True)
    c = st.columns([1, 1.2, 1])[1]
    with c:
        p = st.text_input("Senha", type="password", label_visibility="collapsed", placeholder="Senha do painel")
        if st.button("Entrar", type="primary", use_container_width=True):
            if p == pw:
                ss["auth_ok"] = ss["gravar_cookie"] = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
    return False

# antes da senha: o Streamlit só guarda a página pedida na URL se a navegação já existir;
# sem isso, quem abre /gerador e digita a senha cai no painel
pg = st.navigation([st.Page(os.path.join(PAINEL, "app.py"), title="Painel", default=True),
                    st.Page("gerador.py", title="Gerador de Treinos", url_path="gerador"),
                    st.Page("montar.py", title="Montar treino", url_path="montar")],
                   position="hidden")

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

pg.run()
