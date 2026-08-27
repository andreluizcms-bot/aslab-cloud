# -*- coding: utf-8 -*-
"""AS Endurance LAB · Cloud — visualizador na nuvem (lê o Supabase).

Deploy: Streamlit Community Cloud. Secrets necessários (Settings → Secrets):
  DB_URL = "postgresql://postgres:...@db.xxxx.supabase.co:5432/postgres"
  APP_PASSWORD = "escolha-uma-senha-forte"
"""
import os, string, datetime as dt
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="AS Endurance LAB", page_icon="🏃", layout="wide")

# ---------- tema (identidade do painel local) ----------
DARK=dict(
  bg=("radial-gradient(1000px 620px at 88% -12%, rgba(238,108,77,.13), transparent 62%),"
      "radial-gradient(900px 560px at -6% 108%, rgba(63,142,160,.16), transparent 60%),"
      "linear-gradient(180deg,#0a2026,#07171d)"),
  text="#eaf3f4", mut="#8fa6ad", line="#1a4450",
  hero="linear-gradient(150deg, rgba(255,255,255,.075), rgba(255,255,255,.02))",
  metric="linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.018))",
  card="linear-gradient(160deg, rgba(255,255,255,.045), rgba(255,255,255,.012))",
  gbrd="rgba(255,255,255,.09)", hovbg="rgba(255,255,255,.05)",
  inbg="rgba(14,44,52,.85)", th="rgba(16,50,59,.92)", talt="rgba(255,255,255,.028)",
  chiptx="#f2a541", ax="#8fa6ad", grid="#123037", val="#c9d6d9", shc="4,19,26")
P=DARK
_CSS=string.Template('''
#MainMenu,[data-testid="stToolbarActions"],[data-testid="stAppDeployButton"],[data-testid="stDecoration"],footer{display:none!important}
header[data-testid="stHeader"]{display:none!important}
[data-testid="stSidebar"]{display:none!important}
.stApp{background:$bg;background-attachment:fixed}
.stApp,.stMarkdown,.stMarkdown *,h1,h2,h3,p,label,[data-testid="stMetricValue"],[data-testid="stMetricLabel"] *{
  color:$text;font-family:"Avenir Next","Segoe UI",system-ui,sans-serif}
.block-container{padding-top:1rem;max-width:1280px}
[data-testid="stWidgetLabel"] p{color:$text!important}
[data-baseweb="select"]>div{background:$inbg!important;border-color:$gbrd!important;border-radius:13px!important}
[data-baseweb="select"] div,[data-baseweb="select"] span{color:$text!important}
[data-baseweb="popover"] [role="listbox"]{background:$inbg!important}
[data-baseweb="popover"] li,[data-baseweb="popover"] li *{background:transparent!important;color:$text!important}
.stTextInput input{background:$inbg!important;color:$text!important;border-color:$gbrd!important;border-radius:13px!important}
.hero{background:$hero;border:1px solid $gbrd;border-radius:22px;padding:18px 24px;margin:0 0 16px;
  box-shadow:0 16px 40px rgba($shc,.28);backdrop-filter:blur(16px)}
.hero .kick{display:inline-block;color:#e0952a;font-weight:800;letter-spacing:2px;font-size:.66rem;
  text-transform:uppercase;padding:3px 11px;border-radius:20px;background:rgba(242,165,65,.12);
  border:1px solid rgba(242,165,65,.32);margin-bottom:6px}
.hero h1{margin:0;font-size:1.7rem;letter-spacing:-.6px}
.hero .sub{color:$mut;font-size:.9rem;margin-top:4px}
[data-testid="stMetric"]{background:$metric;border:1px solid $gbrd;border-radius:18px;padding:14px 16px 11px;
  box-shadow:0 10px 24px rgba($shc,.2);backdrop-filter:blur(12px);position:relative;overflow:hidden}
[data-testid="stMetric"]:before{content:"";position:absolute;left:0;top:0;height:3px;width:100%;
  background:linear-gradient(90deg,#ee6c4d,#f2a541)}
[data-testid="stMetricLabel"] p{color:$mut!important;font-size:.62rem;font-weight:800;text-transform:uppercase}
[data-testid="stMetricValue"]{font-weight:800;font-size:1.35rem;font-variant-numeric:tabular-nums}
[role="radiogroup"] label{padding:7px 12px;border-radius:12px;border:1px solid transparent}
[role="radiogroup"] label>div:first-child{display:none}
[role="radiogroup"] label p{font-weight:600;font-size:.9rem}
[role="radiogroup"] label:has(input:checked){background:rgba(242,165,65,.16);border-color:rgba(242,165,65,.42)}
.sect{font-weight:800;font-size:1rem;margin:.4rem 0 .5rem;display:flex;align-items:center;gap:9px}
.sect:before{content:"";width:8px;height:8px;border-radius:3px;background:linear-gradient(135deg,#ee6c4d,#f2a541)}
.tblwrap{max-height:460px;overflow:auto;border:1px solid $gbrd;border-radius:14px}
table.tbl{width:100%;border-collapse:separate;border-spacing:0;font-size:.84rem}
table.tbl th{position:sticky;top:0;background:$th;color:$mut;text-align:left;padding:9px 11px;font-weight:800;
  font-size:.66rem;text-transform:uppercase;border-bottom:1px solid $gbrd;z-index:1}
table.tbl td{padding:7px 11px;border-bottom:1px solid $line;white-space:nowrap;font-variant-numeric:tabular-nums}
table.tbl tr:nth-child(even) td{background:$talt}
table.tbl td.num,table.tbl th.num{text-align:right}
.tick{font-family:ui-monospace,Menlo,monospace;font-size:.68rem;letter-spacing:.06em;color:$mut;
  text-transform:uppercase;display:flex;gap:12px;flex-wrap:wrap;align-items:center;padding:7px 14px;
  border:1px solid $gbrd;border-radius:12px;background:$card;margin:2px 0 12px;font-variant-numeric:tabular-nums}
.tick b{color:$chiptx;font-weight:600}
.logo svg{display:block}
''')
st.markdown("<style>"+_CSS.substitute(P)+"</style>", unsafe_allow_html=True)

def hero(t, sub="", kick=""):
    k=f'<div class="kick">{kick}</div>' if kick else ""
    s=f'<div class="sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="hero">{k}<h1>{t}</h1>{s}</div>', unsafe_allow_html=True)

def sect(t): st.markdown(f'<div class="sect">{t}</div>', unsafe_allow_html=True)

def html_table(df, num=()):
    import html as _h
    num=set(num)
    head="".join(f'<th class="{"num" if c in num else ""}">{_h.escape(str(c))}</th>' for c in df.columns)
    rows=""
    for _,r in df.iterrows():
        tds="".join(f'<td class="{"num" if c in num else ""}">'
                    f'{"" if pd.isna(r[c]) else _h.escape(str(r[c]))}</td>' for c in df.columns)
        rows+=f"<tr>{tds}</tr>"
    st.markdown(f'<div class="tblwrap"><table class="tbl"><thead><tr>{head}</tr></thead>'
                f'<tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)

LOGO=('<svg viewBox="0 0 250 60" width="180" xmlns="http://www.w3.org/2000/svg" '
      'font-family="Avenir Next,Helvetica,Arial,sans-serif">'
      '<text x="0" y="45" font-size="39" font-weight="800" fill="#eaf3f4" letter-spacing="-2">AS</text>'
      '<rect x="64" y="12" width="3.4" height="39" rx="1.7" fill="#ee6c4d"/>'
      '<text x="80" y="31" font-size="12.5" font-weight="700" fill="#eaf3f4" letter-spacing="4">ENDURANCE</text>'
      '<text x="80" y="49" font-size="12.5" font-weight="800" fill="#d98a1f" letter-spacing="4">LAB</text></svg>')

# ---------- PWA: instalável na tela inicial (ícone, tela cheia, splash) ----------
def _instala_pwa():
    try:
        from pwa_assets import ICON_180, MANIFEST_B64
    except Exception:
        return
    import streamlit.components.v1 as _c
    _c.html(f"""<script>
(function() {{
  try {{
    var W = window.top || window.parent;
    var d = W.document;
    if (d.getElementById('aslab-pwa')) return;
    var mark = d.createElement('meta'); mark.id='aslab-pwa'; d.head.appendChild(mark);
    function meta(n, c, prop) {{
      var m = d.createElement('meta');
      m.setAttribute(prop ? 'property' : 'name', n); m.setAttribute('content', c);
      d.head.appendChild(m);
    }}
    function link(rel, href, extra) {{
      var l = d.createElement('link'); l.rel = rel; l.href = href;
      if (extra) Object.keys(extra).forEach(function(k) {{ l.setAttribute(k, extra[k]); }});
      d.head.appendChild(l);
    }}
    // remove as tags padrão do Streamlit (o navegador usa a PRIMEIRA de cada tipo)
    ['link[rel="manifest"]','meta[name="theme-color"]','link[rel="apple-touch-icon"]']
      .forEach(function(sel) {{ d.querySelectorAll(sel).forEach(function(el) {{ el.remove(); }}); }});
    link('manifest', 'data:application/json;base64,{MANIFEST_B64}');
    link('apple-touch-icon', 'data:image/png;base64,{ICON_180}', {{sizes: '180x180'}});
    meta('apple-mobile-web-app-capable', 'yes');
    meta('mobile-web-app-capable', 'yes');
    meta('apple-mobile-web-app-status-bar-style', 'black-translucent');
    meta('apple-mobile-web-app-title', 'AS Endurance LAB');
    meta('theme-color', '#0a2026');
    d.title = 'AS Endurance LAB';
    // guarda o evento de instalação (Android/desktop) p/ o botão "Instalar"
    W.addEventListener('beforeinstallprompt', function(e) {{
      e.preventDefault(); W.__aslabInstall = e;
    }});
  }} catch (e) {{}}
}})();
</script>""", height=0)

_instala_pwa()

# ---------- senha ----------
def _sec(k):
    try: return st.secrets.get(k)
    except Exception: return None

def _tok(pw):
    import hashlib
    return hashlib.sha256(("aslab|"+pw).encode()).hexdigest()[:20]

def _gate():
    pw=_sec("APP_PASSWORD") or os.environ.get("APP_PASSWORD")
    if not pw: return True
    tok=_tok(pw)
    if st.query_params.get("k")==tok:
        st.session_state["auth_ok"]=True
        return True
    if st.session_state.get("auth_ok"):
        st.query_params["k"]=tok
        return True
    st.markdown(f'<div class="logo" style="margin:8vh auto 20px;width:180px">{LOGO}</div>', unsafe_allow_html=True)
    c=st.columns([1,1.2,1])[1]
    with c:
        p=st.text_input("Senha", type="password", label_visibility="collapsed", placeholder="Senha do painel")
        if st.button("Entrar", type="primary", use_container_width=True):
            if p==pw:
                st.session_state["auth_ok"]=True
                st.query_params["k"]=_tok(pw)
                st.rerun()
            else: st.error("Senha incorreta.")
    return False
if not _gate(): st.stop()

# ---------- dados ----------
@st.cache_resource
def _conn():
    import psycopg2
    url=_sec("DB_URL") or os.environ.get("DB_URL")
    if not url:
        st.error("⚙️ Falta configurar os Secrets do app (DB_URL e APP_PASSWORD) em share.streamlit.io → Settings → Secrets.")
        st.stop()
    return psycopg2.connect(url)

@st.cache_data(ttl=300, show_spinner=False)
def q(sql, params=()):
    con=_conn()
    try:
        return pd.read_sql(sql, con, params=params)
    except Exception:
        con.rollback(); raise

MESES=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
       "setembro","outubro","novembro","dezembro"]
MA=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
WD=["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
SPORT_PT={"Run":"Corrida","Walk":"Caminhada","Bike":"Bike","MtnBike":"MTB","Swim":"Natação","Strength":"Força"}

def _ax():
    return alt.Axis(labelColor=P["ax"], domainColor=P["line"], tickColor=P["line"], labelAngle=0, title=None)
def _ay():
    return alt.Axis(labelColor=P["ax"], gridColor=P["grid"], domainOpacity=0, tickOpacity=0)

# ---------- header ----------
hd=st.columns([1.5,4.5], vertical_alignment="center")
hd[0].markdown(f'<div class="logo">{LOGO}</div>', unsafe_allow_html=True)
page=hd[1].radio("Seção", ["👥 Equipe","🧑‍💼 Atleta","🏆 Liga","🧭 Periodização","🎯 Provas","🚨 Perdidos"],
                 horizontal=True, label_visibility="collapsed")

try:
    _ls=q("SELECT v FROM sync_meta WHERE k='last_sync'")
    _last=_ls.iloc[0,0] if len(_ls) else "—"
except Exception:
    _last="—"
hoje=dt.date.today()
_sb=q("""SELECT COUNT(DISTINCT t.atleta_id) n, COALESCE(SUM(CASE WHEN t.kind='run' THEN t.dist_km END),0) km
         FROM treinos t JOIN atletas a ON a.id=t.atleta_id AND a.ativo=1
         WHERE t.date=%s AND t.type='completed'""",(hoje.isoformat(),))
_n,_km=int(_sb.iloc[0,0] or 0), float(_sb.iloc[0,1] or 0)
_ref="hoje"
if _n==0:
    _sb=q("""SELECT COUNT(DISTINCT t.atleta_id) n, COALESCE(SUM(CASE WHEN t.kind='run' THEN t.dist_km END),0) km
             FROM treinos t JOIN atletas a ON a.id=t.atleta_id AND a.ativo=1
             WHERE t.date=%s AND t.type='completed'""",((hoje-dt.timedelta(days=1)).isoformat(),))
    _n,_km,_ref=int(_sb.iloc[0,0] or 0), float(_sb.iloc[0,1] or 0), "ontem"
st.markdown(f'<div class="tick"><span>●</span><span>{_ref}: <b>{_n}</b> treinaram · <b>{_km:.0f} km</b></span>'
            f'<span>/</span><span>sincronizado: <b>{_last}</b></span></div>', unsafe_allow_html=True)

meses=q("SELECT DISTINCT mes FROM treinos ORDER BY mes DESC")["mes"].tolist()
if not meses: st.info("Sem dados ainda — rode a sincronização no Mac."); st.stop()
mlabel=lambda m: f'{MESES[int(m[5:7])-1].capitalize()} {m[:4]}'
mes=st.selectbox("Mês", meses, format_func=mlabel)

# ---------- páginas ----------

# ---------- Liga AS (mesma fórmula do painel local, sobre Postgres) ----------
PESOS={"disciplina":.35,"constancia":.25,"evolucao":.25,"ritmo":.15}
PESOS_CORRIDA={"disciplina":.30,"constancia":.25,"evolucao":.20,"volume":.25}
PESOS_FORCA={"disciplina":.50,"constancia":.50}

def _clamp(v, lo=0.0, hi=100.0): return max(lo, min(hi, v))

@st.cache_data(ttl=600, show_spinner=False)
def liga_cloud(ini_iso, fim_iso, modo, mensal, prev_ini, prev_fim):
    """Ranking do período. mensal=True usa semanas como referência; False = semana única."""
    tr=q("""SELECT t.atleta_id, a.nome, t.date, t.type, t.kind, t.dist_km, t.dur_h, t.was_planned
            FROM treinos t JOIN atletas a ON a.id=t.atleta_id AND a.ativo=1
            WHERE t.date>=%s AND t.date<=%s""",(ini_iso, fim_iso))
    if not len(tr): return []
    pv=q("""SELECT atleta_id, SUM(dist_km) km, SUM(dur_h) h FROM treinos
            WHERE date>=%s AND date<%s AND type='completed' AND kind='run'
              AND dist_km>=3 AND dur_h>0 GROUP BY atleta_id""",(prev_ini, prev_fim))
    prev={r["atleta_id"]:(r["km"], r["h"]) for _,r in pv.iterrows()} if len(pv) else {}
    ini=dt.date.fromisoformat(ini_iso); fim=dt.date.fromisoformat(fim_iso)
    n_sem=len({(ini+dt.timedelta(days=i)-dt.timedelta(days=(ini+dt.timedelta(days=i)).weekday())).isoformat()
               for i in range((fim-ini).days+1)}) if mensal else None
    alvo={"corrida":"run","forca":"strength"}.get(modo)
    min_sess=(6 if modo=="geral" else 4) if mensal else (3 if modo=="geral" else 2)
    min_plan=4 if (mensal and modo=="geral") else 2
    rows=[]
    for aid, g in tr.groupby("atleta_id"):
        nome=g["nome"].iloc[0]
        comp=g[(g["type"]=="completed") & ((g["kind"]==alvo) if alvo else True)]
        if not len(comp): continue
        plan=g[(g["type"]=="planned") & ((g["kind"]==alvo) if alvo else True)]
        done_pl=int(comp["was_planned"].fillna(0).sum())
        tot_plan=len(plan)+done_pl
        disciplina=(done_pl/tot_plan*100) if tot_plan>=min_plan else None
        dts=[dt.date.fromisoformat(str(x)[:10]) for x in comp["date"]]
        if mensal:
            por={}
            for d0 in dts:
                k=(d0-dt.timedelta(days=d0.weekday())).isoformat(); por[k]=por.get(k,0)+1
            mn=2 if modo=="forca" else 3
            constancia=sum(1 for v in por.values() if v>=mn)/n_sem*100
            grupos=len(por)
        else:
            dias=len(set(dts)); alvo_d=3 if modo=="forca" else 5
            constancia=_clamp(dias/alvo_d*100); grupos=dias
        runs=comp[comp["kind"]=="run"]
        km_run=float(runs["dist_km"].fillna(0).sum())
        val=runs[(runs["dist_km"]>=3) & (runs["dur_h"]>0)]
        pace=(float(val["dur_h"].sum())*60/float(val["dist_km"].sum())) if len(val) and val["dist_km"].sum()>0 else None
        evol=None
        if pace and aid in prev:
            pk, ph = prev[aid]
            if pk and pk>(20 if mensal else 10) and ph:
                pp=float(ph)*60/float(pk)
                evol=_clamp(50+(pp-pace)/pp*100*25)
        rows.append({"id":aid,"name":nome,"sess":len(comp),"km":round(km_run),
                     "km_sem":round(km_run/n_sem,1) if mensal else round(km_run,1),
                     "pace":pace,"disciplina":disciplina,"constancia":constancia,
                     "evolucao":evol,"ritmo":None,"volume":None,
                     "qualificado":len(comp)>=min_sess and (grupos>=2 if mensal else True)})
    pesos={"forca":PESOS_FORCA,"corrida":PESOS_CORRIDA}.get(modo, PESOS)
    if modo=="corrida":
        cv=sorted([r for r in rows if (r["km_sem"] or 0)>0], key=lambda r:-r["km_sem"])
        for i,r in enumerate(cv): r["volume"]=_clamp((1-i/max(len(cv)-1,1))*100)
    elif modo!="forca":
        cp=sorted([r for r in rows if r["pace"]], key=lambda r:r["pace"])
        for i,r in enumerate(cp): r["ritmo"]=_clamp((1-i/max(len(cp)-1,1))*100)
    for r in rows:
        num=den=0.0
        for k,w in pesos.items():
            if r.get(k) is not None: num+=r[k]*w; den+=w
        r["total"]=round(num/den,1) if den else 0.0
    rows.sort(key=lambda r:(-int(r["qualificado"]), -r["total"], -r["sess"], r["name"].lower()))
    return rows

def page_liga_cloud(mes):
    hero("Liga AS", "Competição de comprometimento — disciplina vale mais que velocidade", "🏆 Ranking")
    c0=st.columns([1.6,2.2,2.2])
    per=c0[0].radio("Período",["🗓️ Semanal","📆 Mensal"],horizontal=True,label_visibility="collapsed",key="lg_per")
    mod=c0[2].radio("Modalidade",["🏅 Geral","🏃 Corrida","🏋️ Força"],horizontal=True,
                    label_visibility="collapsed",key="lg_mod")
    modo={"🏅 Geral":"geral","🏃 Corrida":"corrida","🏋️ Força":"forca"}[mod]
    mon=hoje-dt.timedelta(days=hoje.weekday())
    if per.startswith("🗓️"):
        wops=[mon-dt.timedelta(days=7*i) for i in range(8)]
        wl=lambda w:f'{w.strftime("%d/%m")} – {(w+dt.timedelta(days=6)).strftime("%d/%m")}'+(" · atual" if w==mon else "")
        wk=c0[1].selectbox("Semana",wops,format_func=wl,key="lg_wk",label_visibility="collapsed")
        ini=wk; fim=min(wk+dt.timedelta(days=6),hoje); mensal=False
        prev=((ini-dt.timedelta(days=28)).isoformat(), ini.isoformat())
        rot=f"Semana {wl(wk)}"; cnome="📅 Presença"
    else:
        y,m=map(int,mes.split("-"))
        import calendar as _cal
        ini=dt.date(y,m,1); fim=min(dt.date(y,m,_cal.monthrange(y,m)[1]),hoje); mensal=True
        p0=(ini-dt.timedelta(days=62)).replace(day=1)
        prev=(p0.isoformat(), ini.isoformat())
        rot=mlabel(mes); cnome="📅 Constância"
    if fim<ini: st.info("Período ainda não começou."); return
    rows=liga_cloud(ini.isoformat(), fim.isoformat(), modo, mensal, prev[0], prev[1])
    if not rows: st.info("Sem treinos neste período ainda."); return
    qf=[r for r in rows if r["qualificado"]]; nq=[r for r in rows if not r["qualificado"]]
    if len(qf)>=3:
        med=["🥇","🥈","🥉"]; pc=st.columns(3)
        for pos,col in zip([0,1,2],[pc[1],pc[0],pc[2]]):
            r=qf[pos]
            extra=(f'{r["km_sem"]} km/sem' if modo=="corrida" else f'{r["km"]} km')
            col.markdown(f'''<div style="text-align:center;padding:{"24px" if pos==0 else "16px"} 10px;
              background:{P["metric"]};border:1px solid {"rgba(242,165,65,.5)" if pos==0 else P["gbrd"]};
              border-radius:18px;{"box-shadow:0 0 22px rgba(242,165,65,.15);" if pos==0 else ""}">
              <div style="font-size:{"2.2rem" if pos==0 else "1.6rem"}">{med[pos]}</div>
              <div style="font-weight:800;font-size:{"1.05rem" if pos==0 else ".95rem"}">{r["name"]}</div>
              <div style="font-size:{"1.9rem" if pos==0 else "1.4rem"};font-weight:800;color:#f2a541">{r["total"]:.1f}</div>
              <div style="font-size:.66rem;color:{P["mut"]};text-transform:uppercase">{r["sess"]} treinos · {extra}</div>
              </div>''', unsafe_allow_html=True)
    def _lead(k,emoji,nome_p):
        cand=[r for r in qf if r.get(k) is not None]
        if not cand: return f"{emoji} {nome_p}: –"
        b=max(cand,key=lambda r:r[k])
        return f'{emoji} **{nome_p}**: {b["name"].split()[0]} ({b[k]:.0f})'
    leads=[_lead("disciplina","🎯","Disciplina"), _lead("constancia","",cnome)]
    if modo=="corrida": leads+=[_lead("evolucao","📈","Evolução"), _lead("volume","📏","Volume")]
    elif modo!="forca": leads+=[_lead("evolucao","📈","Evolução"), _lead("ritmo","⚡","Ritmo")]
    st.markdown(" &nbsp;·&nbsp; ".join(leads))
    st.divider()
    sect(f"Classificação · {rot} · {len(qf)} qualificados")
    _f=lambda v: f"{v:.0f}" if v is not None else "–"
    def _pace(v):
        if not v: return "–"
        mi=int(v); se=int(round((v-mi)*60))
        if se==60: mi+=1; se=0
        return f"{mi}:{se:02d}"
    if modo=="forca":
        df=pd.DataFrame([{"#":i+1,"Atleta":r["name"],"Total":f'{r["total"]:.1f}',
            "🎯 Disc.":_f(r["disciplina"]),cnome:_f(r["constancia"]),"Sessões":r["sess"]} for i,r in enumerate(qf)])
        html_table(df, num={"#","Total","🎯 Disc.",cnome,"Sessões"})
    elif modo=="corrida":
        kl="Km/sem" if mensal else "Km"
        df=pd.DataFrame([{"#":i+1,"Atleta":r["name"],"Total":f'{r["total"]:.1f}',
            "🎯 Disc.":_f(r["disciplina"]),cnome:_f(r["constancia"]),"📈 Evol.":_f(r["evolucao"]),
            "📏 Volume":_f(r["volume"]),kl:f'{r["km_sem"]:.1f}',"Treinos":r["sess"],
            "Pace":_pace(r["pace"])} for i,r in enumerate(qf)])
        html_table(df, num={"#","Total","🎯 Disc.",cnome,"📈 Evol.","📏 Volume",kl,"Treinos","Pace"})
    else:
        df=pd.DataFrame([{"#":i+1,"Atleta":r["name"],"Total":f'{r["total"]:.1f}',
            "🎯 Disc.":_f(r["disciplina"]),cnome:_f(r["constancia"]),"📈 Evol.":_f(r["evolucao"]),
            "⚡ Ritmo":_f(r["ritmo"]),"Treinos":r["sess"],"Km":r["km"],
            "Pace":_pace(r["pace"])} for i,r in enumerate(qf)])
        html_table(df, num={"#","Total","🎯 Disc.",cnome,"📈 Evol.","⚡ Ritmo","Treinos","Km","Pace"})
    if nq:
        with st.expander(f"Ainda não qualificados ({len(nq)})"):
            html_table(pd.DataFrame([{"Atleta":r["name"],"Treinos":r["sess"],"Km":r["km"],
                                      "Total parcial":f'{r["total"]:.1f}'} for r in nq]),
                       num={"Treinos","Km","Total parcial"})
    if modo=="corrida":
        st.caption("**Corrida:** Disciplina 30% · "+cnome.replace("📅 ","")+" 25% · Evolução 20% · **Volume 25% "
                   "(percentil de km por semana)**.")
    elif modo=="forca":
        st.caption("**Força:** Disciplina 50% · "+cnome.replace("📅 ","")+" 50%.")
    else:
        st.caption("**Geral:** Disciplina 35% · "+cnome.replace("📅 ","")+" 25% · Evolução 25% · Ritmo 15%.")

if page.startswith("👥"):
    hero("Visão da Equipe", f"{mlabel(mes)} · dados da última sincronização", "Equipe")
    df=q("""SELECT a.nome "Atleta",
              ROUND(SUM(CASE WHEN t.kind='run' AND t.type='completed' THEN t.dist_km ELSE 0 END)) "Km",
              ROUND(SUM(CASE WHEN t.kind='bike' AND t.type='completed' THEN t.dist_km ELSE 0 END)) "Bike km",
              SUM(CASE WHEN t.kind='strength' AND t.type='completed' THEN 1 ELSE 0 END) "Força",
              SUM(CASE WHEN t.type='completed' THEN 1 ELSE 0 END) "Sessões",
              ROUND(AVG(CASE WHEN t.kind='run' AND t.type='completed' THEN t.hr END)) "FC média"
            FROM treinos t JOIN atletas a ON a.id=t.atleta_id AND a.ativo=1
            WHERE t.mes=%s GROUP BY a.nome HAVING SUM(CASE WHEN t.type='completed' THEN 1 ELSE 0 END)>0
            ORDER BY 2 DESC""",(mes,))
    c=st.columns(4)
    c[0].metric("Atletas", len(df))
    c[1].metric("Km totais", f'{df["Km"].sum():,.0f}'.replace(",","."))
    c[2].metric("Sessões", int(df["Sessões"].sum()))
    c[3].metric("Km bike", f'{df["Bike km"].sum():,.0f}'.replace(",","."))
    busca=st.text_input("Buscar atleta","")
    if busca: df=df[df["Atleta"].str.contains(busca, case=False, na=False)]
    html_table(df, num={"Km","Bike km","Força","Sessões","FC média"})

elif page.startswith("🧑"):
    ath=q("""SELECT DISTINCT a.id, a.nome FROM atletas a
             JOIN treinos t ON t.atleta_id=a.id AND t.mes=%s
             WHERE a.ativo=1 ORDER BY a.nome""",(mes,))
    sel=st.selectbox("Atleta", ath["nome"].tolist())
    aid=ath[ath["nome"]==sel]["id"].iloc[0]
    hero(sel, mlabel(mes), "Atleta")
    r=q("""SELECT ROUND(SUM(CASE WHEN kind='run' AND type='completed' THEN dist_km ELSE 0 END)) km,
                  SUM(CASE WHEN type='completed' THEN 1 ELSE 0 END) sess,
                  ROUND(SUM(CASE WHEN type='completed' THEN dur_h ELSE 0 END)::numeric,1) hrs,
                  ROUND(AVG(CASE WHEN kind='run' AND type='completed' THEN hr END)) fc,
                  ROUND(AVG(CASE WHEN kind='run' AND type='completed' THEN cad END)) cad
           FROM treinos WHERE atleta_id=%s AND mes=%s""",(aid,mes)).iloc[0]
    c=st.columns(5)
    c[0].metric("Corrida", f'{r["km"] or 0:.0f} km'); c[1].metric("Sessões", int(r["sess"] or 0))
    c[2].metric("Horas", f'{r["hrs"] or 0}'); c[3].metric("FC média", f'{r["fc"] or 0:.0f}')
    c[4].metric("Cadência", f'{r["cad"] or 0:.0f}')
    # PMC
    fit=q("""SELECT date, ctl, atl, tsb FROM fitness_diario WHERE atleta_id=%s
             AND date>=%s ORDER BY date""",(aid,(hoje-dt.timedelta(days=90)).isoformat()))
    if len(fit):
        sect("Condição física · 90 dias")
        fit["date"]=pd.to_datetime(fit["date"])
        base=alt.Chart(fit).encode(x=alt.X("date:T", axis=alt.Axis(format="%d/%m", labelColor=P["ax"], grid=False, title=None)))
        a1=base.mark_area(color="rgba(63,142,160,.25)", line={"color":"#3f8ea0","strokeWidth":2}).encode(
            y=alt.Y("ctl:Q", axis=_ay(), title=None))
        a2=base.mark_line(color="#ee6c4d", strokeWidth=1.5).encode(y="atl:Q")
        a3=base.mark_line(color="#37b87f", strokeWidth=1.4, strokeDash=[4,3]).encode(
            y=alt.Y("tsb:Q", axis=alt.Axis(labelColor="#37b87f", grid=False, title=None)))
        st.altair_chart(alt.layer(a1+a2, a3).resolve_scale(y="independent")
                        .properties(height=240, background="rgba(0,0,0,0)").configure_view(strokeWidth=0),
                        use_container_width=True)
    # evolução
    evo=q("""SELECT substr(date,1,7) mo,
               SUM(CASE WHEN kind='run' AND type='completed' THEN dist_km ELSE 0 END) km
             FROM treinos WHERE atleta_id=%s AND date>=%s GROUP BY 1 ORDER BY 1""",
          (aid,(hoje-dt.timedelta(days=365)).isoformat()))
    if len(evo):
        sect("Evolução · km por mês")
        evo["Mês"]=evo["mo"].map(lambda m: f'{MA[int(m[5:7])-1]}/{m[2:4]}')
        ch=(alt.Chart(evo).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=26, color="#ee6c4d")
            .encode(x=alt.X("Mês:N", sort=None, axis=_ax()), y=alt.Y("km:Q", axis=_ay(), title=None),
                    tooltip=["Mês", alt.Tooltip("km:Q", format=".0f")])
            .properties(height=200, background="rgba(0,0,0,0)").configure_view(strokeWidth=0))
        st.altair_chart(ch, use_container_width=True)
    # recuperação · tendências (VFC / sono / FC repouso)
    _win=st.radio("Janela", [30,60,90], index=1, horizontal=True, format_func=lambda x:f"{x} dias",
                  key="rec_win", label_visibility="collapsed")
    ms=q("""SELECT date, hrv, sono_h, fc_rep FROM metricas_diarias
            WHERE atleta_id=%s AND date>=%s ORDER BY date""",
         (aid,(hoje-dt.timedelta(days=_win)).isoformat()))
    if len(ms) and (ms["hrv"].notna().sum() or ms["sono_h"].notna().sum()):
        sect("🫀 Recuperação · tendências")
        ms["date"]=pd.to_datetime(ms["date"])
        for c in ("hrv","sono_h","fc_rep"):
            ms[c+"_m7"]=ms[c].rolling(7, min_periods=3).mean()
        def _trend(df, col, cor, ref=None, banda=None, fmt=".0f", h=210):
            d=df.dropna(subset=[col])
            if d.empty: return None
            xax=alt.X("date:T", title=None, axis=alt.Axis(format="%d/%m", labelColor=P["ax"], grid=False,
                      tickColor=P["line"], domainColor=P["line"], labelAngle=0, labelFontSize=10))
            yax=alt.Y(f"{col}:Q", title=None, scale=alt.Scale(zero=False), axis=_ay())
            base=alt.Chart(d).encode(x=xax); layers=[]
            if banda:
                layers.append(alt.Chart(pd.DataFrame({"lo":[banda[0]],"hi":[banda[1]]}))
                              .mark_rect(color=cor, opacity=0.08).encode(y="lo:Q", y2="hi:Q"))
            layers.append(base.mark_circle(size=32, color=cor, opacity=0.45).encode(
                y=yax, tooltip=[alt.Tooltip("date:T",title="Dia",format="%d/%m"),
                                alt.Tooltip(f"{col}:Q",format=fmt)]))
            layers.append(base.mark_line(color=cor, strokeWidth=2.6).encode(
                y=alt.Y(f"{col}_m7:Q", scale=alt.Scale(zero=False))))
            if ref is not None:
                layers.append(alt.Chart(pd.DataFrame({"y":[ref]})).mark_rule(
                    color=P["mut"], strokeDash=[4,4], strokeWidth=1.2).encode(y="y:Q"))
            return alt.layer(*layers).properties(height=h, background="rgba(0,0,0,0)").configure_view(strokeWidth=0)
        _hrv=ms["hrv"].dropna(); _sono=ms["sono_h"].dropna()
        _hrv7=ms["hrv_m7"].dropna(); _sono7=ms["sono_h_m7"].dropna()
        kk=st.columns(4)
        if len(_hrv):
            _hb=_hrv.mean(); _hn=_hrv7.iloc[-1] if len(_hrv7) else _hrv.iloc[-1]
            kk[0].metric("VFC · média 7d", f"{_hn:.0f} ms", f"{(_hn-_hb):+.0f} vs sua média ({_hb:.0f})")
            kk[1].metric("VFC · dias", f"{len(_hrv)}")
        if len(_sono):
            _sb=_sono.mean(); _sn=_sono7.iloc[-1] if len(_sono7) else _sono.iloc[-1]
            kk[2].metric("Sono · média 7d", f"{_sn:.1f} h", f"{(_sn-_sb):+.1f} vs sua média ({_sb:.1f})")
            kk[3].metric("Noites < 7h", f"{int((_sono<7).sum())} de {len(_sono)}")
        g=st.columns(2)
        with g[0]:
            st.caption("**VFC (HRV)** — pontos = dia · linha = média 7d · tracejado = sua média · faixa = zona normal")
            if len(_hrv):
                _sd=_hrv.std() if len(_hrv)>3 else 0
                ch=_trend(ms,"hrv","#37b87f", ref=_hrv.mean(), banda=(_hrv.mean()-_sd,_hrv.mean()+_sd))
                if ch is not None: st.altair_chart(ch, use_container_width=True)
        with g[1]:
            st.caption("**Sono** — pontos = noite · linha = média 7d · tracejado = 7h")
            if len(_sono):
                ch=_trend(ms,"sono_h","#3f8ea0", ref=7.0, fmt=".1f")
                if ch is not None: st.altair_chart(ch, use_container_width=True)
        if ms["fc_rep"].notna().sum()>=3:
            st.caption("**FC de repouso** — subir junto com VFC caindo = sinal de fadiga/estresse")
            ch=_trend(ms,"fc_rep","#ee6c4d", ref=ms["fc_rep"].mean(), h=160)
            if ch is not None: st.altair_chart(ch, use_container_width=True)
    # treinos do mês
    tt=q("""SELECT date "Data", title "Treino", kind, dist_km, dur_h, hr, cad, tss
            FROM treinos WHERE atleta_id=%s AND mes=%s AND type='completed'
            ORDER BY date DESC""",(aid,mes))
    if len(tt):
        sect("Treinos do mês")
        tt["Tipo"]=tt["kind"].map({"run":"Corrida","bike":"Bike","strength":"Força","walk":"Caminhada","swim":"Natação"}).fillna("Outro")
        tt["Dist."]=tt["dist_km"].map(lambda v: f"{v:.1f}" if v and v>0 else "–")
        tt["Pace"]=[(f"{int(d*60/k)}:{int((d*60/k-int(d*60/k))*60):02d}" if k and k>0 and d else "–")
                    for d,k in zip(tt["dur_h"], tt["dist_km"])]
        tt["Cad."]=tt["cad"].map(lambda v: f"{v:.0f}" if pd.notna(v) else "–")
        tt["FC"]=tt["hr"].map(lambda v: f"{v:.0f}" if pd.notna(v) else "–")
        tt["TSS"]=tt["tss"].map(lambda v: f"{v:.0f}" if v else "–")
        html_table(tt[["Data","Treino","Tipo","Dist.","Pace","Cad.","FC","TSS"]],
                   num={"Dist.","Pace","Cad.","FC","TSS"})

elif page.startswith("🏆"):
    page_liga_cloud(mes)

elif page.startswith("🧭"):
    hero("Periodização", "Planejado × realizado — edição no painel do Mac", "ATP do Lab")
    pl=q("""SELECT p.id, a.nome||' · '||p.nome||' · prova '||p.prova_data lab, p.atleta_id, p.inicio, p.prova_data
            FROM periodizacao p JOIN atletas a ON a.id=p.atleta_id ORDER BY p.prova_data DESC""")
    if not len(pl): st.info("Nenhum ciclo criado ainda."); st.stop()
    sel=st.selectbox("Ciclo", pl["lab"].tolist())
    row=pl[pl["lab"]==sel].iloc[0]
    sem=q("SELECT idx, inicio, fase, km, horas FROM periodizacao_semanas WHERE plano_id=%s ORDER BY idx",(int(row["id"]),))
    real=q("""SELECT date, dist_km FROM treinos WHERE atleta_id=%s AND type='completed'
              AND kind='run' AND date>=%s AND date<=%s""",(row["atleta_id"], row["inicio"], row["prova_data"]))
    rk={}
    for _,x in real.iterrows():
        d0=dt.date.fromisoformat(x["date"]); wk=(d0-dt.timedelta(days=d0.weekday())).isoformat()
        rk[wk]=rk.get(wk,0)+(x["dist_km"] or 0)
    sem["Semana"]=sem["inicio"].map(lambda s: dt.date.fromisoformat(s).strftime("%d/%m"))
    sem["Realizado"]=sem["inicio"].map(lambda s: rk.get(s))
    CORES={"Base":"#3f8ea0","Específico":"#f2a541","Polimento":"#37b87f","Prova":"#ee6c4d","Recuperação":"#8fa6ad"}
    bars=(alt.Chart(sem).mark_bar(size=20, opacity=.85, cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
          .encode(x=alt.X("Semana:N", sort=None, axis=_ax()), y=alt.Y("km:Q", axis=_ay(), title=None),
                  color=alt.Color("fase:N", scale=alt.Scale(domain=list(CORES), range=list(CORES.values())),
                                  legend=alt.Legend(title=None, orient="top", labelColor=P["text"])),
                  tooltip=["Semana","fase","km","Realizado"]))
    line=(alt.Chart(sem.dropna(subset=["Realizado"])).mark_line(point=True, color="#eaf3f4", strokeWidth=2)
          .encode(x=alt.X("Semana:N", sort=None), y="Realizado:Q"))
    st.altair_chart((bars+line).properties(height=260, background="rgba(0,0,0,0)").configure_view(strokeWidth=0),
                    use_container_width=True)
    sem2=sem[["idx","Semana","fase","km","horas","Realizado"]].rename(
        columns={"idx":"Sem","fase":"Fase","km":"Km","horas":"Horas"})
    html_table(sem2, num={"Sem","Km","Horas","Realizado"})

elif page.startswith("🎯"):
    hero("Provas dos Alunos", "Próxima prova de cada atleta (do banco)", "Competições")
    pv=q("""SELECT a.nome "Atleta", p.nome "Prova", p.date d FROM provas p
            JOIN atletas a ON a.id=p.atleta_id AND a.ativo=1
            WHERE p.date>=%s ORDER BY p.date""",(hoje.isoformat(),))
    if len(pv):
        pv["Data"]=pv["d"].map(lambda s: dt.date.fromisoformat(s).strftime("%d/%m/%y"))
        pv["Faltam"]=pv["d"].map(lambda s: f"{(dt.date.fromisoformat(s)-hoje).days}d")
        html_table(pv[["Atleta","Prova","Data","Faltam"]], num={"Faltam"})
    else:
        st.info("Nenhuma prova futura registrada.")

else:
    hero("Treinos Perdidos", "Planejado e não realizado", "Acompanhamento")
    dias=[hoje-dt.timedelta(days=i) for i in range(1,15)]
    dsel=st.selectbox("Dia", dias, format_func=lambda x: f'{WD[x.weekday()]} {x.strftime("%d/%m")}')
    d=dsel.isoformat()
    f=q("""SELECT a.nome "Atleta", string_agg(t.title, ', ') "Treino planejado"
           FROM treinos t JOIN atletas a ON a.id=t.atleta_id AND a.ativo=1
           WHERE t.date=%s AND t.type='planned'
             AND t.atleta_id NOT IN (SELECT atleta_id FROM treinos WHERE date=%s AND type='completed')
           GROUP BY a.nome ORDER BY a.nome""",(d,d))
    st.metric("Faltas no dia", len(f))
    if len(f): html_table(f)
    else: st.success("Ninguém faltou nesse dia. ✅")

import streamlit.components.v1 as _cc
_cc.html('''<div style="text-align:right;font-family:Avenir Next,system-ui;padding:6px 0">
  <button id="ib" style="display:none;background:linear-gradient(135deg,#f07a5a,#e5613f);color:#fff;
    border:0;border-radius:12px;padding:8px 14px;font-weight:700;font-size:13px;cursor:pointer">
    📲 Instalar app</button></div>
<script>
 var b=document.getElementById('ib');
 var ev=(window.top||window.parent).__aslabInstall;
 if (ev) {{ b.style.display='inline-block'; b.onclick=function(){{ ev.prompt(); }}; }}
</script>''', height=44)

st.markdown('<div style="margin-top:2.5rem;padding-top:14px;border-top:1px solid rgba(255,255,255,.09);'
            'color:#8fa6ad;font-size:.76rem;display:flex;justify-content:space-between">'
            '<span><b style="color:#eaf3f4">AS</b> ENDURANCE <span style="color:#d98a1f">LAB</span> · Cloud</span>'
            '<span>somente leitura · edição e coleta no painel do Mac</span></div>', unsafe_allow_html=True)
