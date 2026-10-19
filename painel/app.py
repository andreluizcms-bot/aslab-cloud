# -*- coding: utf-8 -*-
"""Central de Relatórios — painel local (Streamlit) do gerador mensal.
Rodar:  /Users/andresantos/trainingpeaks-mcp/.venv/bin/streamlit run app.py
"""
import os, sys, glob, json, time, subprocess, calendar, asyncio, base64, string, html as _html, datetime as dt
from collections import defaultdict
import pandas as pd
import altair as alt
import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
PYBIN = sys.executable
from report import compute, build_refs, fmt_pace, days_to_event, initials, coach_message, has_sport, excluded_ids, is_active, active_ids
from render_all import titlecase
from render_all_modern import slug, MESES
import nuvem
import painel_mac as pm          # TrainingPeaks ao vivo e PDFs (no Mac)
NUVEM = nuvem.NUVEM
if NUVEM: pm = nuvem.Remoto(pm)  # na nuvem essas funções rodam no Mac, pela fila

_icon=os.path.join(BASE,"assets","png","icon.png")
st.set_page_config(page_title="AS Endurance LAB", page_icon=(_icon if os.path.exists(_icon) else "🏃"), layout="wide", initial_sidebar_state="auto")

# ---------- temas: estrutura do painel esportivo, paleta clássica do Lab ----------
DARK=dict(
  bg=("radial-gradient(1000px 620px at 88% -12%, rgba(238,108,77,.10), transparent 62%),"
      "radial-gradient(900px 560px at -6% 108%, rgba(63,142,160,.13), transparent 60%),"
      "linear-gradient(180deg,#0a2026,#07171d)"),
  text="#eaf3f4", mut="#8fa6ad", line="#163a44",
  hero="#0c262e", metric="#0d2931", side="#081c22", card="#0c262e",
  gbrd="#1c4450", hovbg="rgba(255,255,255,.05)", scrl="rgba(143,166,173,.35)",
  pill="#ee6c4d", pilltx="#ffffff",
  inbg="#0e2c34", th="#0b242c", talt="rgba(255,255,255,.025)", chiptx="#f2a541",
  ax="#8fa6ad", grid="#11333c", val="#c9d6d9", fcline="#e8f0f1", fcpt="#eaf3f4",
  ringtx="#eaf3f4")
LIGHT=dict(
  bg=("radial-gradient(1000px 620px at 88% -12%, rgba(238,108,77,.12), transparent 62%),"
      "radial-gradient(900px 560px at -6% 108%, rgba(63,142,160,.12), transparent 60%),"
      "linear-gradient(180deg,#f6fafb,#eaf1f3)"),
  text="#123039", mut="#5c6f77", line="#dde6e9",
  hero="#ffffff", metric="#ffffff", side="#f0f5f6", card="#ffffff",
  gbrd="#d3dfe2", hovbg="rgba(18,48,57,.05)", scrl="rgba(92,111,119,.35)",
  pill="#ee6c4d", pilltx="#ffffff",
  inbg="#ffffff", th="#eef4f5", talt="#f6fafa", chiptx="#b5760f",
  ax="#5c6f77", grid="#e6edee", val="#33505a", fcline="#2f5c8f", fcpt="#2f5c8f",
  ringtx="#123039")
P = DARK  # reatribuído no sidebar conforme o toggle

_CSS = string.Template('''
@font-face{font-family:'Barlow Condensed';font-style:italic;font-weight:700;font-display:swap;src:url('/app/static/fonts/barlow-700i.woff2') format('woff2');}
@font-face{font-family:'Barlow Condensed';font-style:normal;font-weight:600;font-display:swap;src:url('/app/static/fonts/barlow-600.woff2') format('woff2');}
@font-face{font-family:'Barlow Condensed';font-style:normal;font-weight:700;font-display:swap;src:url('/app/static/fonts/barlow-700.woff2') format('woff2');}
@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:500;font-display:swap;src:url('/app/static/fonts/mono-500.woff2') format('woff2');}
@font-face{font-family:'Inter';font-style:normal;font-weight:400 700;font-display:swap;src:url('/app/static/fonts/inter-var.woff2') format('woff2');}
:root{--mono:"JetBrains Mono",ui-monospace,Menlo,monospace; --display:"Barlow Condensed",Inter,sans-serif;}
#MainMenu, [data-testid="stMainMenu"], [data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stStatusWidget"], [data-testid="stDecoration"], footer {display:none !important;}
header[data-testid="stHeader"]{background:transparent !important; height:0 !important; min-height:0 !important; overflow:visible; pointer-events:none;}
header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"]{pointer-events:auto; position:fixed; top:10px; left:10px; z-index:1000;
  background:$card; border:1px solid $gbrd; border-radius:8px; padding:4px;}
header[data-testid="stHeader"] [data-testid="stExpandSidebarButton"] *{color:$mut !important;}
.stMain .block-container{padding-top:1rem;}
[data-testid="stSidebar"]{background:$side !important; border-right:1px solid $gbrd; min-width:236px !important; max-width:236px !important;}
[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding:1rem 0 1.2rem;}
[data-testid="stSidebar"] .block-container, [data-testid="stSidebar"] [data-testid="stSidebarUserContent"]{padding:0 14px 0 14px;}
[data-testid="stSidebar"] hr{margin:.7rem 0;}
[data-testid="stSidebarCollapseButton"] *, [data-testid="stExpandSidebarButton"] *{color:$mut !important;}
[data-testid="stSidebar"] .logo{margin:2px 0 12px 2px;}
[data-testid="stSidebar"] [role="radiogroup"]{flex-direction:column; gap:2px;}
[data-testid="stSidebar"] [role="radiogroup"] label{width:100%; padding:9px 12px; border-radius:8px;}
[data-testid="stSidebar"] [role="radiogroup"] label p{font-size:.9rem;}
[data-testid="stSidebar"] [role="radiogroup"][aria-label="Seção"] label::before{width:16px; height:16px; margin-right:10px;}
[data-testid="stSidebar"] [role="radiogroup"][aria-label="Seção"] label:nth-child(1){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='9' cy='8' r='3.5'/%3E%3Cpath d='M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6'/%3E%3Ccircle cx='17' cy='9' r='2.5'/%3E%3Cpath d='M15.5 14.4c3.3-.3 6 1.6 6 5.6'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(2){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='7' r='4'/%3E%3Cpath d='M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(3){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M2 12h4l2-5 3 10 3-8 2 3h6'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(4){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0z'/%3E%3Cpath d='M7 6H4v2a3 3 0 0 0 3 3M17 6h3v2a3 3 0 0 1-3 3'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(5){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 18l5-9 4 5 3-3 6 7'/%3E%3Cpath d='M3 6h18'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(6){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M9 4h6v3H9z'/%3E%3Cpath d='M15 5h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h3'/%3E%3Cpath d='M9 14l2 2 4-4'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(7){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M5 21V4'/%3E%3Cpath d='M5 4h13l-3 4 3 4H5'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(8){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 3l10 18H2z'/%3E%3Cpath d='M12 10v4M12 17.5v.5'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(9){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 3h8l4 4v14H6z'/%3E%3Cpath d='M14 3v4h4M9 12h6M9 16h6'/%3E%3C/svg%3E");}
[role="radiogroup"][aria-label="Seção"] label:nth-child(10){--ic:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23000' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='3'/%3E%3Cpath d='M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1'/%3E%3C/svg%3E");}
.stMarkdown a.link-app{display:flex; justify-content:center; width:100%;}
.hrvg{display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:12px; margin:4px 0 8px;}
.hrvc{background:$card; border:1px solid $gbrd; border-radius:14px; padding:14px 16px 12px; display:flex; flex-direction:column; gap:8px;}
.hrvc.alerta{border-color:rgba(207,74,90,.55);}
.hrvc .top{display:flex; align-items:center; gap:10px;}
.hrvc .top img,.hrvc .top .mono{width:34px; height:34px; border-radius:50%; object-fit:cover; flex:none; border:2px solid #f2a541;}
.hrvc .top .mono{display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#f2a541,#ee8c3d); color:#0e2a33; font-size:.85rem; font-weight:800;}
.hrvc .nm{font-family:var(--display); font-weight:700; font-size:1.35rem; line-height:1; letter-spacing:.02em; color:$text;}
.hrvc .upd{font:500 11px var(--mono); color:$mut; margin-top:3px;}
.hrvc .tag{margin-left:auto; font:500 11px var(--mono); padding:3px 8px; border-radius:999px; border:1px solid $gbrd; color:$mut; white-space:nowrap;}
.hrvc .tag.alerta{color:#cf4a5a; border-color:rgba(207,74,90,.5);}
.hrvc .tag.ok{color:#37b87f; border-color:rgba(55,184,127,.45);}
.hrvc .kp{display:grid; grid-template-columns:repeat(4,1fr); gap:6px;}
.hrvc .kp b{display:block; font-family:var(--display); font-weight:700; font-size:1.45rem; line-height:1; color:$text; font-variant-numeric:tabular-nums;}
.hrvc .kp small{display:block; font:500 11px var(--mono); color:$mut; margin-top:3px;}
.hrvc .lg{font:500 11px var(--mono); color:$mut; margin-top:2px;}
.hrvc svg.ch{width:100%;height:auto;display:block;overflow:visible}
.hrvc svg .tip{display:none;pointer-events:none}.hrvc svg .pt:hover .tip{display:block}
.hrvc svg .pt:hover circle:first-child{r:4}
.hrvc svg .tip rect{fill:$text;opacity:.96}.hrvc svg .tip text{font:500 8.5px var(--mono);fill:$card}
.hrvc svg text.ax{font:500 8px var(--mono)}
.hrvc svg .tip{display:none; pointer-events:none;} .hrvc svg .pt:hover .tip{display:block;}
.hrvc svg .pt:hover circle:first-child{r:4;}
.hrvc svg .tip rect{fill:$text; opacity:.96;} .hrvc svg .tip text{font:500 8.5px var(--mono); fill:$card;}
.hrvc svg text.ax{font:500 8px var(--mono);}
.hrvc .pr i{cursor:default;}
.hrvc .pr{display:flex; gap:3px;}
.hrvc .pr i{flex:1; height:12px; border-radius:3px; display:block;}
.hrvc .msg{font-size:.8rem; color:$text; line-height:1.35; margin-top:2px;}
.hrvc .msg b{font-weight:700;}
.hrvc .aux{font:500 11px var(--mono); color:$mut;}
@media (max-width:760px){.hrvg{grid-template-columns:1fr;}}
.sb-h{font:500 12px var(--mono) !important; color:$mut; margin:12px 2px 6px;}
html{scroll-behavior:smooth;}
::selection{background:rgba(242,165,65,.35);}
.stApp{background:$bg; background-attachment:fixed;}
table.tbl td, [data-testid="stMetricValue"], .rec .rv, .tpw .m{font-variant-numeric:tabular-nums;}
.stButton>button:focus-visible, .stDownloadButton>button:focus-visible, .stTextInput input:focus-visible{
  outline:2px solid rgba(242,165,65,.75) !important; outline-offset:2px;}
.stApp, .stMarkdown, .stMarkdown *, p, label{color:$text;}
.stApp, .stMarkdown, .stMarkdown *, p, label,
[data-testid="stMetricLabel"] *, [data-testid="stMetricDelta"] *,
.stButton button, .stDownloadButton button, input, textarea, [data-baseweb="select"] *{
  font-family:Inter,"Avenir Next",system-ui,-apple-system,sans-serif;}
.stApp{font-variant-numeric:tabular-nums;}
h1,h2,h3,h4{color:$text; font-family:var(--display);}
h2{font-weight:600; font-style:italic; text-transform:uppercase; letter-spacing:.02em;}
.block-container{padding-top:1rem; padding-bottom:1.2rem; max-width:1400px; animation:fadeup .3s ease;}
@keyframes fadeup{from{opacity:0; transform:translateY(6px);} to{opacity:1; transform:none;}}
::-webkit-scrollbar{width:9px; height:9px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:$scrl; border-radius:8px;}
::-webkit-scrollbar-thumb:hover{background:#f2a541;}
[data-testid="stWidgetLabel"] p, .stCheckbox label p{color:$mut !important; font:500 12px/1.3 var(--mono) !important;}
[data-baseweb="select"]>div{background:$inbg !important; border-color:$gbrd !important; border-radius:10px !important; transition:border-color .15s ease;}
[data-baseweb="select"]>div:hover{border-color:#f2a541 !important;}
[data-baseweb="select"] div, [data-baseweb="select"] span{color:$text !important;}
[data-baseweb="select"] svg{fill:$mut !important; color:$mut !important;}
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] ul{background:$inbg !important;}
[data-baseweb="popover"] li, [data-baseweb="popover"] li *{background:transparent !important; color:$text !important;}
[data-baseweb="popover"] li:hover, [data-baseweb="popover"] [aria-selected="true"]{background:$hovbg !important;}
.stTextInput input{background:$inbg !important; color:$text !important; border-color:$gbrd !important;}
[data-baseweb="input"], [data-baseweb="base-input"]{background:$inbg !important; border-color:$gbrd !important; border-radius:10px !important;}
[data-baseweb="checkbox"] > span:first-of-type{background:$inbg !important; border:1.5px solid $mut !important; border-radius:5px;}
[data-baseweb="checkbox"]:has(input:checked) > span:first-of-type{background:#ee6c4d !important; border-color:#ee6c4d !important;}
[data-testid="stAlert"]{background:$card !important; color:$text !important; border:1px solid $gbrd !important; border-left:4px solid #f2a541 !important; border-radius:12px;}
[data-testid="stAlert"] *{color:$text !important;}
.hero{background:$hero; border:1px solid $gbrd; border-radius:16px; padding:14px 20px 12px; margin:0 0 14px;}
.hero .kick{display:none;}
.hero h1{margin:0; font-size:2.3rem; line-height:1; letter-spacing:.02em; text-transform:uppercase;
  font-family:"Barlow Condensed",sans-serif; font-weight:700; font-style:italic; color:$text;}
.hero .sub{color:$mut; font-size:.86rem; margin-top:3px;}
[data-testid="stMetric"]{background:$metric; border:1px solid $gbrd; border-radius:14px;
  padding:12px 15px 9px; position:relative; overflow:hidden;}
[data-testid="stMetric"]:before{content:""; position:absolute; left:0; bottom:0; height:3px; width:100%;
  background:linear-gradient(90deg,#ee6c4d,#f2a541);}
[data-testid="stMetricLabel"]{overflow:visible !important;}
[data-testid="stMetricLabel"] p{color:$mut !important; font:500 12px/1.2 var(--mono) !important; white-space:normal;}
[data-testid="stMetricValue"]{color:$text; font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:2.1rem; line-height:1.05; overflow:visible !important;}
[data-testid="stMetricValue"] *{overflow:visible !important; text-overflow:clip !important; white-space:nowrap; color:$text;}
[data-testid="stMetricDelta"] *{overflow:visible !important; text-overflow:clip !important;}
.stButton>button, .stDownloadButton>button{border-radius:8px; font-weight:600; border:1px solid #ee6c4d; padding:.55rem 1.15rem;
  background:#ee6c4d; color:#0b1f24 !important;
  transition:transform .14s ease, filter .14s ease;}
.stButton>button *, .stDownloadButton>button *{color:#0b1f24 !important;}
.stButton>button:hover, .stDownloadButton>button:hover{filter:brightness(1.07); transform:translateY(-1px);}
.stButton>button:active, .stDownloadButton>button:active{transform:translateY(0) scale(.98);}
.stButton>button[kind="secondary"]{background:transparent; border:1px solid $gbrd; color:$text !important;}
.stButton>button[kind="secondary"] *{color:$text !important;}
.stButton>button[kind="secondary"], .stButton>button[kind="secondary"] *{color:$text !important;}
.stButton>button[kind="secondary"]:hover{border-color:#f2a541;}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:14px !important; border-color:$gbrd !important; background:$card;}
[role="radiogroup"]{gap:4px;}
[role="radiogroup"] label{padding:7px 13px; border-radius:8px; border:1px solid transparent; background:transparent;
  transition:background .15s ease, border-color .15s ease; margin:0; align-items:center;}
[role="radiogroup"] label:hover{background:$hovbg;}
[role="radiogroup"] label:has(input:checked){background:$card; border-color:$gbrd;}
[role="radiogroup"] label:has(input:checked) p{color:#ee6c4d !important; font-weight:700;}
[role="radiogroup"][aria-label="Seção"] label:has(input:checked)::before{opacity:1; background:#ee6c4d;}
[role="radiogroup"] label>div:first-child{display:none;}
[role="radiogroup"] label p{font-size:.88rem; font-weight:600; color:$mut;}
[role="radiogroup"][aria-label="Seção"] label::before{content:""; width:15px; height:15px; flex:none; display:inline-block; margin-right:7px;
  background:$mut; opacity:.85; -webkit-mask:var(--ic) center/contain no-repeat; mask:var(--ic) center/contain no-repeat;}
.stMarkdown a.link-app{display:inline-flex; align-items:center; gap:7px; text-decoration:none !important; font-size:.85rem; font-weight:600;
  padding:8px 14px; border-radius:8px; border:1px solid $gbrd; color:$text !important; transition:border-color .15s ease,color .15s ease;}
.link-app svg{width:15px; height:15px; fill:none; stroke:currentColor; stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round;}
.stMarkdown a.link-app:hover{border-color:#ee6c4d; color:#ee6c4d !important;}
.logo{margin:2px 0 0;} .logo svg{display:block; max-width:100%;}
hr{border-color:$gbrd; margin:1rem 0;}
.sect{font:500 12px var(--mono); color:$mut; margin:.6rem 0 .5rem; display:flex; align-items:center; gap:8px;}
.sect:before{content:""; width:14px; height:3px; background:#ee6c4d; display:inline-block;}
.ath{display:flex; gap:16px; align-items:center; background:$metric; border:1px solid $gbrd; border-radius:14px;
  padding:14px 18px; margin-bottom:4px;}
.ath img,.ath .mono{width:72px; height:72px; border-radius:50%; object-fit:cover; border:2.5px solid #f2a541; flex:none;}
.ath .mono{display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg,#f2a541,#ee8c3d); color:#0e2a33; font-size:1.7rem; font-weight:800;}
.ath .nm{font-size:1.9rem; font-weight:700; color:$text; line-height:1; letter-spacing:.02em;
  font-family:"Barlow Condensed",sans-serif; font-style:italic; text-transform:uppercase;}
.ath .meta{margin-top:7px;}
.chip{display:inline-block; background:rgba(242,165,65,.13); color:$chiptx; border:1px solid rgba(242,165,65,.36);
  padding:3px 11px; border-radius:20px; font-size:.78rem; font-weight:700; margin-right:6px;}
.recwrap{display:flex; flex-wrap:wrap; gap:10px; margin:.2rem 0 .4rem;}
.rec{flex:1 1 130px; background:$metric; border:1px solid $gbrd; border-radius:14px; padding:11px 14px 9px;
  position:relative; overflow:hidden;}
.rec:before{content:""; position:absolute; left:0; bottom:0; height:3px; width:100%;
  background:linear-gradient(90deg,#ee6c4d,#f2a541);}
.rec .rl{color:$mut; font:500 12px var(--mono);}
.rec .rv{color:$text; font-family:"Barlow Condensed",sans-serif; font-size:1.8rem; font-weight:700; margin-top:2px; line-height:1;}
.rec .rs{color:$mut; font-size:.72rem; margin-top:3px;}
.ringrow{display:flex; gap:14px; align-items:center; background:$card; border:1px solid $gbrd;
  border-radius:14px; padding:10px 14px;}
.ringlab{font:500 12px var(--mono); color:$mut;}
.ringval{font-family:"Barlow Condensed",sans-serif; font-weight:700; font-size:1.5rem; line-height:1.1;}
.tblwrap{max-height:470px; overflow:auto; border:1px solid $gbrd; border-radius:12px; background:$card;}
table.tbl{width:100%; border-collapse:separate; border-spacing:0; font-size:.85rem;}
table.tbl th{position:sticky; top:0; background:$th; color:$mut; text-align:left; padding:9px 12px;
  font:500 12px var(--mono); border-bottom:1px solid $gbrd; z-index:1;}
table.tbl td{padding:8px 12px; border-bottom:1px solid $line; color:$text; white-space:nowrap;}
table.tbl tr:nth-child(even) td{background:$talt;}
table.tbl tbody tr:hover td{background:$hovbg;}
table.tbl td.num, table.tbl th.num{text-align:right;}
[data-testid="stImage"] img{border-radius:12px; border:1px solid $gbrd;}
[data-testid="stExpander"]{background:$card; border:1px solid $gbrd !important; border-radius:12px !important;}
[data-testid="stToast"]{background:$hero !important; color:$text !important; border:1px solid $gbrd !important; border-radius:12px !important;}
.tpweek{display:grid; grid-template-columns:repeat(7,1fr); gap:8px; margin:.3rem 0 .6rem;}
.tpday{background:$card; border:1px solid $gbrd; border-radius:12px; padding:8px; min-height:96px;}
.tpday.today{border-color:rgba(242,165,65,.6);}
.tpdh{font:500 11px/1.3 var(--mono); color:$mut; margin-bottom:6px; text-align:center;}
.tpdh b{color:$text; font-size:.78rem;}
.tpw{border-radius:9px; padding:6px 8px; margin-bottom:6px; font-size:.72rem; line-height:1.3;
  background:$metric; border:1px solid $gbrd; border-left:3px solid #9aa7ad;}
.tpw .t{font-weight:700; color:$text; display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.tpw .m{color:$mut; font-size:.66rem; display:block;}
.tpw .st{font-size:.58rem; font-weight:800; letter-spacing:.5px; text-transform:uppercase; display:block;}
.tpw.done{border-left-color:#37b87f;} .tpw.done .st{color:#37b87f;}
.tpw.miss{border-left-color:#cf4a5a;} .tpw.miss .st{color:#cf4a5a;}
.tpw.plan{border-left-color:#f2a541;} .tpw.plan .st{color:#f2a541;}
.tpw.extra{border-left-color:#3f8ea0;} .tpw.extra .st{color:#3f8ea0;}
.tpempty{text-align:center; color:$mut; font-size:.68rem; padding-top:16px;}
.tick{font:500 12px var(--mono);
  color:$mut; display:flex; gap:14px; flex-wrap:wrap; align-items:center;
  padding:8px 16px; border:1px solid $gbrd; border-radius:10px; background:$card;
  margin:2px 0 12px; font-variant-numeric:tabular-nums;}
.tick, .tick *{font-family:var(--mono) !important;}
.tick b{color:$chiptx; font-weight:500;}
@media (max-width:640px){
  .stMain .block-container{padding-top:3.6rem;}
  .hero h1{font-size:1.9rem;}
  [data-testid="stMetricValue"]{font-size:1.8rem;}
}
.tick .sep{color:rgba(242,165,65,.45);}
.tick .live{width:7px; height:7px; border-radius:50%; background:#37b87f; flex:none;
  animation:tickpulse 2.4s ease-in-out infinite;}
@keyframes tickpulse{50%{opacity:.35;}}
@media (prefers-reduced-motion: reduce){.tick .live{animation:none;} .block-container{animation:none;}}
.nvbar{height:1.5px; background:linear-gradient(90deg,transparent,$line 10%,$line 90%,transparent); margin:.1rem 0 .7rem;}
.nvlogo{margin-top:4px;}
.foot{display:flex; justify-content:space-between; gap:12px; flex-wrap:wrap; margin-top:3.2rem;
  padding:16px 6px 4px; border-top:1px solid $gbrd; color:$mut; font-size:.78rem;}
.foot b{color:$text;}
.pmc-leg{font-size:.8rem;color:$text;margin:.1rem 0 .3rem}
.pmc-leg b{color:$text}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin:0 5px 0 14px;vertical-align:middle}
''')

def apply_theme(pal):
    st.markdown("<style>"+_CSS.substitute(pal)+"</style>", unsafe_allow_html=True)

def hero(title, subtitle="", kicker=""):
    k=f'<div class="kick">{kicker}</div>' if kicker else ""
    s=f'<div class="sub">{subtitle}</div>' if subtitle else ""
    st.markdown(f'<div class="hero">{k}<h1>{title}</h1>{s}</div>', unsafe_allow_html=True)

def sect(t):
    st.markdown(f'<div class="sect">{t}</div>', unsafe_allow_html=True)

def ring_svg(pct, cor, size=76):
    """Anel de progresso (assinatura do design esportivo). pct em 0..1."""
    pct=max(0.0, min(1.0, pct or 0)); r=30; c=2*3.14159*r; m=size/2
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 76 76">'
            f'<circle cx="38" cy="38" r="{r}" fill="none" stroke="{P["grid"]}" stroke-width="7"/>'
            f'<circle cx="38" cy="38" r="{r}" fill="none" stroke="{cor}" stroke-width="7" '
            f'stroke-linecap="round" stroke-dasharray="{c*pct:.1f} {c:.1f}" '
            f'transform="rotate(-90 38 38)"/>'
            f'<text x="38" y="44" text-anchor="middle" fill="{P["ringtx"]}" font-size="17" '
            f'font-weight="700" font-family="Barlow Condensed,sans-serif">{pct*100:.0f}%</text></svg>')

def ring(pct, cor, valor, rotulo, sub=""):
    sub=f'<div class="ringlab" style="text-transform:none;letter-spacing:0">{sub}</div>' if sub else ""
    st.markdown(f'<div class="ringrow">{ring_svg(pct, cor)}<div>'
                f'<div class="ringlab">{rotulo}</div>'
                f'<div class="ringval" style="color:{cor}">{valor}</div>{sub}</div></div>',
                unsafe_allow_html=True)

def cor_aderencia(pct):
    return "#37b87f" if pct>=80 else ("#f2a541" if pct>=50 else "#cf4a5a")

def logo_svg(pal, w=212):
    """Wordmark AS Endurance LAB (adapta a cor ao tema)."""
    tx=pal["text"]
    return (f'<svg viewBox="0 0 250 60" width="{w}" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="\'Avenir Next\',\'Helvetica Neue\',Arial,sans-serif">'
            f'<text x="0" y="45" font-size="39" font-weight="800" fill="{tx}" letter-spacing="-2">AS</text>'
            f'<rect x="64" y="12" width="3.4" height="39" rx="1.7" fill="#ee6c4d"/>'
            f'<text x="80" y="31" font-size="12.5" font-weight="700" fill="{tx}" letter-spacing="4">ENDURANCE</text>'
            f'<text x="80" y="49" font-size="12.5" font-weight="800" fill="#d98a1f" letter-spacing="4">LAB</text>'
            f'</svg>')

def html_table(df, num=()):
    num=set(num)
    def cell(v): return "" if (v is None or (isinstance(v,float) and pd.isna(v))) else _html.escape(str(v))
    head="".join(f'<th class="{ "num" if c in num else "" }">{_html.escape(str(c))}</th>' for c in df.columns)
    rows=""
    for _,r in df.iterrows():
        tds="".join(f'<td class="{ "num" if c in num else "" }">{cell(r[c])}</td>' for c in df.columns)
        rows+=f"<tr>{tds}</tr>"
    st.markdown(f'<div class="tblwrap"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)

# ---------- helpers de dados ----------
def list_months():
    ms=[os.path.basename(d) for d in glob.glob(os.path.join(BASE,"data","*")) if os.path.isdir(d)]
    return sorted([m for m in ms if len(m)==7 and m[4]=="-"], reverse=True)

def _month_bounds(month):
    y,m=map(int,month.split("-")); last=calendar.monthrange(y,m)[1]
    return dt.date(y,m,1), dt.date(y,m,last), y, m, last

@st.cache_data(show_spinner=False)
def load_records(month):
    recs=[]
    for f in sorted(glob.glob(os.path.join(BASE,"data",month,"*.json"))):
        if os.path.basename(f).startswith("_"): continue
        try: recs.append(json.load(open(f)))
        except Exception: pass
    return recs

@st.cache_data(show_spinner=False)
def load_json(month, name):
    p=os.path.join(BASE,"data",month,name)
    return json.load(open(p)) if os.path.exists(p) else {}

@st.cache_data(show_spinner=True, persist="disk")
def build_all(month):
    START,END,y,m,last=_month_bounds(month)
    PERIOD=f"01/{m:02d}/{y} – {last}/{m:02d}/{y}"; PREV=MESES[(m-2)%12][:3]
    msgs=load_json(month,"_messages.json")
    _exc=excluded_ids()
    out=[]
    for r in load_records(month):
        if str(r.get("id")) in _exc: continue      # ex-atletas (grupo "Não é mais atleta")
        if not is_active(r.get("id")): continue    # só quem está na conta do TP hoje
        if not has_sport(r): continue
        name=titlecase(r["name"])
        W=[{**w,"date":dt.date.fromisoformat(w["date"][:10])} for w in r["workouts"]]
        refs=build_refs(r.get("settings",{}))
        d=compute(name,PERIOD,PREV,START,END,W,r.get("prev"),r.get("fitness"),r.get("event"),r.get("photo"),refs)
        if d["total_completed"]==0 or (d["run_km"]<=0 and d.get("bike_km",0)<=0 and d.get("str_n",0)==0 and sum(d.get(k,0) or 0 for k in ("run_n","bike_n","walk_n","swim_n","other_n"))==0): continue
        d["id"]=str(r["id"]); d["metrics"]=r.get("metrics"); d["fitness_raw"]=r.get("fitness")
        # recado: usa a mensagem AI do mês (_messages.json) se existir; senão gera pela regra
        d["coach_msg"]=msgs.get(str(r["id"])) or coach_message(d)
        d["workouts_raw"]=W
        out.append(d)
    out.sort(key=lambda x:x["run_km"], reverse=True)
    return out

def refresh_athlete(month, aid):
    """Puxa do TrainingPeaks os treinos atuais do atleta (inclui os de hoje) e regrava o JSON."""
    return pm.refresh_athlete(month, aid)

def pmc_chart(daily):
    """Condição Física integrada ao tema: CTL em gradiente teal, ATL em coral,
    TSB como faixa verde/vermelha ao redor do zero (eixo direito) e TSS em pontos."""
    df=pd.DataFrame(daily); df["date"]=pd.to_datetime(df["date"])
    df["tsb_pos"]=df["tsb"].clip(lower=0); df["tsb_neg"]=df["tsb"].clip(upper=0)
    xax=alt.X("date:T", title=None, axis=alt.Axis(format="%d/%m", labelColor=P["ax"],
              tickColor=P["line"], domainColor=P["line"], grid=False, labelAngle=0, labelFontSize=10))
    yL=alt.Axis(title=None, labelColor=P["ax"], gridColor=P["grid"],
                domainOpacity=0, tickOpacity=0, labelFontSize=10)
    yR=alt.Axis(title=None, labelColor="#37b87f", grid=False,
                domainOpacity=0, tickOpacity=0, labelFontSize=10)
    base=alt.Chart(df).encode(x=xax)
    grad=alt.Gradient(gradient="linear",
        stops=[alt.GradientStop(color="rgba(63,142,160,.42)",offset=0),
               alt.GradientStop(color="rgba(63,142,160,.03)",offset=1)],
        x1=1,x2=1,y1=1,y2=0)
    tss   = base.mark_circle(size=20, color=P["mut"], opacity=0.35).encode(
                y=alt.Y("tss:Q", axis=yL),
                tooltip=[alt.Tooltip("date:T",title="Dia",format="%d/%m"),
                         alt.Tooltip("tss:Q",title="TSS",format=".0f")])
    ctlar = base.mark_area(color=grad, line={"color":"#3f8ea0","strokeWidth":2.4}).encode(
                y=alt.Y("ctl:Q", axis=yL),
                tooltip=[alt.Tooltip("date:T",title="Dia",format="%d/%m"),
                         alt.Tooltip("ctl:Q",title="Fitness (CTL)",format=".0f"),
                         alt.Tooltip("atl:Q",title="Fadiga (ATL)",format=".0f"),
                         alt.Tooltip("tsb:Q",title="Forma (TSB)",format=".0f")])
    atl   = base.mark_line(color="#ee6c4d", strokeWidth=1.6, opacity=.95).encode(
                y=alt.Y("atl:Q", axis=yL),
                tooltip=[alt.Tooltip("atl:Q",title="Fadiga (ATL)",format=".0f")])
    left  = alt.layer(tss, ctlar, atl)
    tsb_p = base.mark_area(color="#37b87f", opacity=0.20, clip=True).encode(
                y=alt.Y("tsb_pos:Q", axis=yR, title=None))
    tsb_n = base.mark_area(color="#cf4a5a", opacity=0.22, clip=True).encode(
                y=alt.Y("tsb_neg:Q", axis=yR, title=None))
    tsb_l = base.mark_line(color="#37b87f", strokeWidth=1.2, opacity=.75,
                strokeDash=[4,3]).encode(
                y=alt.Y("tsb:Q", axis=yR),
                tooltip=[alt.Tooltip("tsb:Q",title="Forma (TSB)",format=".0f")])
    right = alt.layer(tsb_p, tsb_n, tsb_l)
    return (alt.layer(left, right).resolve_scale(y="independent")
            .properties(height=300, background="rgba(0,0,0,0)",
                        padding={"left":8,"top":12,"right":8,"bottom":8})
            .configure_view(strokeWidth=0))

def _axis_x():
    return alt.Axis(labelColor=P["ax"], domainColor=P["line"], tickColor=P["line"], labelAngle=0,
                    labelFontSize=11, title=None)

def _axis_y():
    return alt.Axis(labelColor=P["ax"], gridColor=P["grid"], domainOpacity=0, tickOpacity=0, labelFontSize=10)

def bar_weekly(weekly, field, color, fmt=".0f", h=220):
    df=pd.DataFrame(weekly)
    base=alt.Chart(df).encode(x=alt.X("label:N", sort=None, axis=_axis_x()))
    bars=base.mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=30, color=color).encode(
        y=alt.Y(f"{field}:Q", title=None, axis=_axis_y()),
        tooltip=[alt.Tooltip("label:N",title="Semana"), alt.Tooltip(f"{field}:Q",title=field,format=fmt)])
    lab=base.mark_text(dy=-9, color=P["val"], fontWeight="bold", fontSize=11).encode(
        y=f"{field}:Q", text=alt.Text(f"{field}:Q", format=fmt))
    return (bars+lab).properties(height=h, background="rgba(0,0,0,0)").configure_view(strokeWidth=0)

def bar_weekly_bike(weekly, h=220):
    """Barras agrupadas: km de corrida + km de bike por semana."""
    df=pd.DataFrame(weekly)
    long=df.melt(id_vars=["label"], value_vars=["km","bkm"], var_name="esporte", value_name="dist")
    long["esporte"]=long["esporte"].map({"km":"Corrida","bkm":"Bike"})
    base=alt.Chart(long).encode(
        x=alt.X("label:N", sort=None, axis=_axis_x()),
        xOffset=alt.XOffset("esporte:N"),
        color=alt.Color("esporte:N", scale=alt.Scale(domain=["Corrida","Bike"], range=["#ee6c4d","#3f8ea0"]),
                        legend=alt.Legend(title=None, orient="top-left", labelColor=P["text"])))
    bars=base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=14).encode(
        y=alt.Y("dist:Q", title=None, axis=_axis_y()),
        tooltip=[alt.Tooltip("label:N",title="Semana"), alt.Tooltip("esporte:N",title="Esporte"),
                 alt.Tooltip("dist:Q",title="km",format=".0f")])
    return bars.properties(height=h, background="rgba(0,0,0,0)").configure_view(strokeWidth=0)

def fc_weekly(weekly, h=220):
    df=pd.DataFrame(weekly).dropna(subset=["fc"])
    if df.empty: return None
    grad=alt.Gradient(gradient="linear",
        stops=[alt.GradientStop(color="rgba(63,142,160,.38)",offset=0), alt.GradientStop(color="rgba(63,142,160,.02)",offset=1)],
        x1=1,x2=1,y1=1,y2=0)
    x=alt.X("label:N", sort=None, axis=_axis_x())
    y=alt.Y("fc:Q", title=None, scale=alt.Scale(zero=False), axis=_axis_y())
    area=alt.Chart(df).mark_area(line={"color":P["fcline"],"strokeWidth":2.4}, color=grad).encode(x=x, y=y)
    pts=alt.Chart(df).mark_circle(size=60, color=P["fcpt"]).encode(x=x, y=y,
        tooltip=[alt.Tooltip("label:N",title="Semana"), alt.Tooltip("fc:Q",title="FC",format=".0f")])
    lab=alt.Chart(df).mark_text(dy=-13, color=P["val"], fontWeight="bold", fontSize=11).encode(
        x=x, y=y, text=alt.Text("fc:Q", format=".0f"))
    return (area+pts+lab).properties(height=h, background="rgba(0,0,0,0)").configure_view(strokeWidth=0)

def _hm(h):
    if not h: return "–"
    m=round(h*60); return f"{m//60}:{m%60:02d}"

KIND_LABEL={"run":"Corrida","walk":"Caminhada","other":"Outro"}
SPORT_PT={"Run":"Corrida","Walk":"Caminhada","Bike":"Bike","MtnBike":"MTB","Swim":"Natação",
          "Strength":"Força","Brick":"Brick","Other":"Outro","Rowing":"Remo","XCSki":"Ski"}
WD=["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]

def _fmt_time(secs):
    s=int(round(secs)); h=s//3600; m=(s%3600)//60; ss=s%60
    return f"{h}:{m:02d}:{ss:02d}" if h else f"{m}:{ss:02d}"

@st.cache_data(show_spinner=False)
def athlete_records(aid, today_str):
    return pm.records(aid)

@st.cache_data(show_spinner=False)
def athlete_history(aid, months, today_str):
    """Histórico completo de treinos realizados (lista em janelas de 90 dias + FC do detalhe). Cacheado por dia."""
    end=dt.date.today(); start=end-dt.timedelta(days=int(months*30.5))
    raw=pm.history(aid, start, end)
    res=[]
    for w in raw:
        try: d=dt.date.fromisoformat(w["date"][:10])
        except Exception: continue
        dist=float(w.get("distance_actual_km") or 0); dur=float(w.get("duration_actual") or 0)
        res.append({"id":w.get("id"), "date":d, "title":(w.get("title") or "—"), "sport":w.get("sport") or "",
                    "dist":dist, "dur":dur, "tss":float(w.get("tss") or w.get("tss_actual") or 0),
                    "pace":(dur*60/dist) if dist>0 else None, "hr":w.get("_hr"),
                    "cad":w.get("_cad")})
    res.sort(key=lambda x:x["date"], reverse=True)
    return res

RUN_PRS=pm.RUN_PRS
pdf_path=pm.pdf_path; pdf_path_week=pm.pdf_path_week; pdf_path_period=pm.pdf_path_period
_months_back=pm._months_back

def generate_athlete_pdf(d, month):
    """Gera o PDF de um único atleta. Retorna o caminho."""
    return pm.generate_athlete_pdf(d, month)

def generate_period_pdf(aid, name, n_meses):
    """Puxa N meses do TP (em blocos de 85 dias) e gera o PDF de período (quebra por mês)."""
    return pm.generate_period_pdf(aid, name, n_meses)

def generate_weekly_pdf(aid, name, wk_start):
    """Puxa a semana do TP ao vivo e gera o PDF semanal (quebra por dia). Retorna (caminho, rec)."""
    return pm.generate_weekly_pdf(aid, name, wk_start)

def pdf_local(p):
    """Caminho do PDF para ler aqui, ou None. Na nuvem busca no Mac o que só existe lá."""
    if os.path.exists(p): return p
    if not NUVEM: return None
    rel=os.path.relpath(p, BASE)
    if rel not in nuvem.pdfs_no_mac(): return None
    try: return pm.arquivo(rel)
    except Exception: return None

@st.cache_data(show_spinner=False, ttl=600)
def week_mirror(aid, wk_iso):
    """Puxa a semana ao vivo do TP (planejado + realizado) para o espelho do calendário."""
    return pm.semana(aid, wk_iso)

def render_week_mirror(rec, wk_start):
    KEMOJI={"run":"🏃","bike":"🚴","strength":"🏋️","walk":"🚶"}
    days=[wk_start+dt.timedelta(days=i) for i in range(7)]
    today=dt.date.today()
    by={dd:[] for dd in days}
    for w in rec.get("workouts",[]):
        try: wd=dt.date.fromisoformat((w.get("date") or "")[:10])
        except Exception: continue
        if wd in by: by[wd].append(w)
    def _dur(h):
        m=int(round((h or 0)*60))
        return (f"{m//60}h{m%60:02d}" if m>=60 else f"{m}min") if m else ""
    def card(w, wd):
        kind=w.get("kind") or "other"
        if w.get("wt")==2: kind="bike"
        elif w.get("wt")==9: kind="strength"
        em=KEMOJI.get(kind,"📋")
        title=_html.escape((w.get("title") or "Treino")[:36])
        parts=[]
        if w.get("dist_km"): parts.append(f'{w["dist_km"]:.1f} km')
        if w.get("dur_h"): parts.append(_dur(w["dur_h"]))
        if w["type"]=="completed":
            cls,stt=("done","feito") if w.get("was_planned") else ("extra","extra")
            if kind=="run" and w.get("dist_km") and w.get("dur_h"):
                parts.append(fmt_pace((w["dur_h"]*60)/w["dist_km"]))
            if w.get("cad"): parts.append(f'{round(w["cad"])} ppm')
            if w.get("hr"): parts.append(f'{round(w["hr"])} bpm')
        else:
            cls,stt=("miss","não feito") if wd<today else ("plan","a fazer")
            if w.get("tss"): parts.append(f'{w["tss"]:.0f} TSS')
        met=" · ".join(p for p in parts if p) or "—"
        return f'<div class="tpw {cls}"><span class="st">{stt}</span><span class="t">{em} {title}</span><span class="m">{met}</span></div>'
    cells=[]
    for wd in days:
        hdr=f'<div class="tpdh">{WD[wd.weekday()]}<br><b>{wd.strftime("%d/%m")}</b></div>'
        ws=sorted(by[wd], key=lambda x: x["type"]=="completed")   # planejado primeiro
        cards="".join(card(w, wd) for w in ws) or '<div class="tpempty">—</div>'
        cells.append(f'<div class="tpday{" today" if wd==today else ""}">{hdr}{cards}</div>')
    return f'<div class="tpweek">{"".join(cells)}</div>'

@st.cache_data(show_spinner=False, ttl=600)
def evolution(aid, months, day_iso):
    """Km/pace/horas/sessões por mês — direto do banco (data/aslab.db)."""
    import db as _db
    start=_months_back(dt.date.fromisoformat(day_iso), months-1).isoformat()
    con=_db.get_conn()
    q="""SELECT substr(date,1,7) mo,
                SUM(CASE WHEN kind='run' THEN dist_km ELSE 0 END) km,
                SUM(CASE WHEN kind='run' THEN dur_h ELSE 0 END) runh,
                SUM(dur_h) hrs, COUNT(*) sess
         FROM treinos
         WHERE atleta_id=? AND type='completed' AND date>=?
         GROUP BY 1 ORDER BY 1"""
    MA=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    rows=[]
    for mo,km,runh,hrs,sess in con.execute(q,(str(aid), start)):
        y,m=mo.split("-")
        pace=(runh*60/km) if km and km>0 else None
        rows.append({"mes":f'{MA[int(m)-1]}/{y[2:]}',"km":km or 0,"pace":pace,
                     "hrs":hrs or 0,"sess":sess})
    con.close()
    return rows

@st.cache_data(show_spinner=False, ttl=3600)
def all_events(horizon_days, day_iso):
    """Todas as provas de todos os alunos nos próximos N dias (cache 1h)."""
    return pm.eventos(horizon_days, day_iso)

@st.cache_data(show_spinner=False, ttl=3600)
def workout_detail(aid, wid):
    """Todos os dados de um treino (detalhe completo do TP)."""
    return pm.detalhe(aid, wid)

@st.cache_data(show_spinner=False, ttl=600)
def scoreboard(day_iso):
    """Pulso do dia p/ o placar: treinos, km, faltas de ontem, próxima prova."""
    import db as _db
    con=_db.get_conn(); _db.init_db(con)
    hoje=dt.date.fromisoformat(day_iso); ontem=(hoje-dt.timedelta(days=1)).isoformat()
    def _dia(d):
        return con.execute("""SELECT COUNT(DISTINCT t.atleta_id),
                                     COALESCE(SUM(CASE WHEN t.kind='run' THEN t.dist_km END),0)
                              FROM treinos t JOIN atletas a ON a.id=t.atleta_id AND a.ativo=1
                              WHERE t.date=? AND t.type='completed'""",(d,)).fetchone()
    n_h,km_h=_dia(day_iso)
    if n_h: ref, n, km = "hoje", n_h, km_h
    else:
        n_o,km_o=_dia(ontem); ref, n, km = "ontem", n_o, km_o
    faltas=con.execute("""SELECT COUNT(DISTINCT t.atleta_id) FROM treinos t
                          JOIN atletas a ON a.id=t.atleta_id AND a.ativo=1
                          WHERE t.date=? AND t.type='planned'
                          AND t.atleta_id NOT IN(
                            SELECT atleta_id FROM treinos WHERE date=? AND type='completed')""",
                       (ontem,ontem)).fetchone()[0]
    prova=con.execute("""SELECT p.date, p.nome, COUNT(*) FROM provas p
                         JOIN atletas a ON a.id=p.atleta_id AND a.ativo=1
                         WHERE p.date>=? GROUP BY p.date ORDER BY p.date LIMIT 1""",
                      (day_iso,)).fetchone()
    con.close()
    out={"ref":ref,"n":n or 0,"km":km or 0,"faltas":faltas or 0}
    if prova:
        pd_=dt.date.fromisoformat(prova[0])
        out["prova"]={"em":(pd_-hoje).days,"nome":prova[1],"n":prova[2],"data":pd_.strftime("%d/%m")}
    return out

@st.cache_data(show_spinner=False, ttl=600)
def risk_cached(month, day_iso):
    from risk import risk_flags
    return risk_flags(month, dt.date.fromisoformat(day_iso))

@st.cache_data(show_spinner=False, ttl=600)
def absent_report(day_iso):
    """Faltas do dia (planejado e não realizado) — reusa o daily_absent.py."""
    from daily_absent import report as _rep
    return _rep(dt.date.fromisoformat(day_iso))

@st.cache_data(show_spinner=False, ttl=3600)
def all_athletes():
    """Atletas dos GRUPOS do TP (roster) — usado no lote semanal e no envio por e-mail."""
    return pm.atletas()

@st.cache_data(show_spinner=False)
def pdf_preview_png(pdf, mtime):
    return pm.preview_png(pdf)

def avatar_bytes(aid):
    p=os.path.join(BASE,"data","avatars",f"{aid}.img")
    if os.path.exists(p) and os.path.getsize(p)>200:
        return open(p,"rb").read()
    return None

def fmtnum(v,suf="",dec=0):
    if v is None: return "–"
    return (f"{v:.{dec}f}"+suf) if dec else (f"{round(v)}{suf}")

# ---------- cabeçalho estilo site ----------
_light = st.session_state.get("theme_light", False)   # lê o tema antes p/ colorir o logo
P = LIGHT if _light else DARK
apply_theme(P)

_collected=list_months()
_cur=dt.date.today().strftime("%Y-%m")                       # mês atual sempre selecionável
def _recent_months(cur, n=12):                               # cur, cur-1, ... (n meses atrás)
    y,m=map(int,cur.split("-")); out=[]
    for i in range(n+1):
        mm=m-i; yy=y
        while mm<=0: mm+=12; yy-=1
        out.append(f"{yy:04d}-{mm:02d}")
    return out
months=sorted(set(_collected)|set(_recent_months(_cur,12)), reverse=True)  # todos os meses
_idx=months.index(_collected[0]) if _collected else months.index(_cur)     # abre no mês mais recente com dados
def _mlabel(mm):
    lab=f'{MESES[int(mm[5:7])-1].capitalize()} {mm[:4]}'
    if mm==_cur: lab+=" (atual)"
    if mm not in _collected: lab+=" · vazio"
    return lab

def _goto_cb():
    v=st.session_state.get("goto_ath")
    if v:
        st.session_state["page_sel"]="Atleta"
        st.session_state["sel_atleta"]=v
        st.session_state["goto_ath"]=""

# barra lateral: logo + navegação + ferramentas
with st.sidebar:
    st.markdown(f'<div class="logo">{logo_svg(P, w=178)}</div>', unsafe_allow_html=True)
    page=st.radio("Seção", ["Visão da Equipe","Atleta","HRV","Liga","Periodização","Revisão","Provas","Treinos perdidos","Relatórios (PDF)","Pipeline"],
                  key="page_sel", label_visibility="collapsed")
    st.markdown('<div class="sb-h">Ferramentas</div>', unsafe_allow_html=True)
    month=st.selectbox("Mês", months, index=_idx, format_func=_mlabel)
    try:
        _srch_names=[""]+sorted((x["name"] for x in build_all(month)), key=str.lower)
    except Exception:
        _srch_names=[""]
    st.selectbox("Ir para atleta", _srch_names, key="goto_ath", on_change=_goto_cb)
    st.toggle("Tema claro", key="theme_light")
    st.markdown('<div style="margin-top:10px">'
                f'<a class="link-app" href="{"./montar" if NUVEM else "http://127.0.0.1:8640"}" target="{"_self" if NUVEM else "_blank"}">'
                '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 4h6v6M20 4l-9 9"/>'
                '<path d="M19 14v5a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/></svg>'
                'Gerador de Treinos</a></div>', unsafe_allow_html=True)
try:
    _sb=scoreboard(dt.date.today().isoformat())
    _p=_sb.get("prova")
    _pl="atleta" if _p and _p["n"]==1 else "atletas"
    _pv=(f'<span class="sep">/</span> próx. prova <b>{_p["data"]}</b> · {_html.escape(_p["nome"][:24])} · <b>{_p["n"]}</b> {_pl} · em <b>{_p["em"]}d</b>' if _p else '')
    st.markdown(f"""<div class="tick"><span class="live"></span>
      <span>{_sb["ref"]}: <b>{_sb["n"]}</b> treinaram · <b>{_sb["km"]:.0f} km</b> corridos</span>
      <span class="sep">/</span><span>faltas ontem: <b>{_sb["faltas"]}</b></span>
      {_pv}</div>""", unsafe_allow_html=True)
except Exception:
    pass

def _lan_ip():
    import socket
    try:
        s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("8.8.8.8",80))
        ip=s.getsockname()[0]; s.close(); return ip
    except Exception: return None
_ip=_lan_ip()

def site_footer():
    cel=''          # painel responde só neste Mac (127.0.0.1)
    st.markdown(f'''<div class="foot">
      <div><b>AS</b> <span style="letter-spacing:2px">ENDURANCE</span> <span style="color:#d98a1f;letter-spacing:2px">LAB</span>
      &nbsp;·&nbsp; Performance & Endurance</div>
      <div>{cel}André Santos · dados do TrainingPeaks</div>
    </div>''', unsafe_allow_html=True)

# ================= PÁGINAS =================
def lthr_sugestoes(data):
    """{aid: sugestão} de quem está com LTHR a revisar. Calcula no Mac quem falta
    (ou foi calculado há mais de 7 dias ou mudou de LTHR). Nunca grava no TP."""
    flag=[(d["id"], d["refs"]["lthr"]) for d in data if d["intens"].get("lthr_suspect")]
    cache=pm.ler_sugestoes_lthr()
    lim=(dt.date.today()-dt.timedelta(days=7)).isoformat()
    falta=[(a,l) for a,l in flag if a not in cache or cache[a].get("calc","")<lim or cache[a].get("atual")!=l]
    if falta and not st.session_state.get("_lthr_tentou"):
        st.session_state["_lthr_tentou"]=True
        try:
            with st.spinner(f"Calculando a sugestão de LTHR de {len(falta)} atleta(s) pelos picos de FC do TP…"):
                cache.update(pm.sugestao_lthr(falta))
        except Exception as e:
            st.caption(f"Sugestão de LTHR indisponível agora: {e}")
    return {a:cache.get(a) for a,_ in flag}

def lthr_txt(sg, curto=False):
    if not sg: return "sugestão ainda não calculada"
    if not sg.get("sugerido"): return "sem FC de corrida nos últimos 90 dias: fazer o Teste de limiar 30'"
    if sg["sugerido"]<=sg["atual"]+2:
        return "os picos de FC não sustentam subir: confira se os treinos leves estão fortes demais"
    dd=(f'{sg["data"][8:10]}/{sg["data"][5:7]}' if sg.get("data") else "")
    if curto: return f'{sg["atual"]} → {sg["sugerido"]}'
    return f'{sg["atual"]} → {sg["sugerido"]} bpm ({sg["base"]}{", "+dd if dd else ""})'

def page_equipe(month):
    hero("Visão da Equipe", f'{MESES[int(month[5:7])-1].capitalize()} {month[:4]} · panorama de todos os atletas', "Equipe")
    tp=st.columns([1.25,3])
    if tp[0].button("Atualizar todos", type="primary", key="refresh_all"):
        with st.status("Puxando todos os atletas do TrainingPeaks… pode levar alguns minutos.", expanded=True):
            rc=_run_stream([PYBIN,"collect.py","--month",month], st.empty())
        if rc==0:
            st.cache_data.clear(); st.toast("Todos atualizados!", icon="✅"); st.rerun()
        else:
            st.error("Falhou — veja o log acima.")
    tp[1].caption("Puxa os treinos do mês até hoje de TODOS os atletas (~alguns min). "
                  "Para atualizar os PDFs depois, use Pipeline → Renderizar.")
    data=build_all(month)
    if not data:
        st.info("Nenhum dado deste mês ainda. Clique em **Atualizar todos** acima para puxar os treinos do TrainingPeaks (até hoje)."); return
    # KPIs topo
    tot_km=sum(d["run_km"] for d in data); adh=sum(d["adher"] for d in data)/len(data)
    lthr_n=sum(1 for d in data if d["intens"].get("lthr_suspect"))
    metr_n=sum(1 for d in data if d.get("metrics"))
    prova_n=sum(1 for d in data if d.get("event"))
    c=st.columns([1.5,1,1,1,1], vertical_alignment="center")
    with c[0]:
        ring(adh/100, cor_aderencia(adh), f"{adh:.0f}%", "Aderência da equipe")
    c[1].metric("Atletas", len(data))
    c[2].metric("Km totais", f"{tot_km:,.0f}".replace(",","."))
    c[3].metric("LTHR baixo", lthr_n)
    c[4].metric("Com prova", prova_n)

    # ---- LTHR a revisar: sempre com a sugestão ----
    _sug=lthr_sugestoes(data) if lthr_n else {}
    if lthr_n:
        with st.expander(f"LTHR a revisar · {lthr_n} atleta(s) com sugestão", expanded=True):
            _ls=[]
            for d in sorted((x for x in data if x["intens"].get("lthr_suspect")), key=lambda x:x["name"].lower()):
                sg=_sug.get(d["id"]) or {}
                ok=bool(sg.get("sugerido")) and sg["sugerido"]>sg["atual"]+2
                _ls.append({"Atleta":d["name"], "LTHR atual":d["refs"]["lthr"],
                            "Sugerido":(sg["sugerido"] if ok else "–"),
                            "Diferença":(f'+{sg["sugerido"]-sg["atual"]}' if ok else "–"),
                            "FC média no mês":(str(round(d["fc_med"])) if d.get("fc_med") else "–"),
                            "Base da sugestão":(f'{sg["base"]}'+(f' em {sg["data"][8:10]}/{sg["data"][5:7]}' if sg.get("data") else "") if ok else lthr_txt(sg))})
            html_table(pd.DataFrame(_ls), num={"LTHR atual","Sugerido","Diferença","FC média no mês"})
            st.caption("Sugestão pelos picos de FC de corrida no TrainingPeaks (últimos 90 dias): a maior entre a melhor média de 60 min "
                       "e 95% da melhor média de 20 min, limitada a 93% da maior FC de 1 min. Se o pico veio de um treino leve, "
                       "ela é o mínimo provável. Nada é gravado no TP: confirme com o Teste de limiar 30' e ajuste você.")

    # ---- painel de risco ----
    _risk=risk_cached(month, dt.date.today().isoformat())
    if _risk:
        with st.expander(f"Atenção — {len(_risk)} atleta(s) sinalizados", expanded=len(_risk)<=8):
            html_table(pd.DataFrame([{
                "Atleta":r["name"],
                "Sinais":" · ".join(r["flags"]),
                "ACWR":f'{r["acwr"]:.2f}' if r.get("acwr") is not None else "–",
                "TSB":f'{r["tsb"]:.0f}' if r.get("tsb") is not None else "–",
                "Aderência 14d":f'{r["adh14"]:.0f}%' if r.get("adh14") is not None else "–",
            } for r in _risk]), num={"ACWR","TSB","Aderência 14d"})
            st.caption("🔺 ACWR ≥ 1.5 (carga aguda vs crônica) · 🟠 TSB ≤ -25 · 📉 aderência < 50% em 14d · "
                       "💗/❤️ tendência de HRV/FC repouso (chega com as próximas coletas diárias).")

    # filtros
    f=st.columns([2,1,1,1])
    q=f[0].text_input("Buscar atleta","")
    only_lthr=f[1].checkbox("Só LTHR a revisar")
    only_prova=f[2].checkbox("Só com prova")
    only_nomet=f[3].checkbox("Só sem métricas")

    dash="–"
    def si(v):  return str(round(v)) if v is not None else dash        # inteiro ou "–"
    def sf(v):  return f"{v:.1f}" if v is not None else dash            # 1 casa ou "–"
    def prova_dt(ev):
        if not ev or not ev.get("date"): return ""
        try: return dt.date.fromisoformat(ev["date"]).strftime("%d/%m/%y")
        except Exception: return ev.get("date","")
    rows=[]
    for d in data:
        mt=d.get("metrics") or {}
        ev=d.get("event")
        rows.append({
            "Atleta":d["name"],
            "Km":round(d["run_km"]),
            "Bike km":str(round(d["bike_km"])) if d.get("bike_km",0)>0 else "",
            "Força":str(d["str_n"]) if d.get("str_n",0)>0 else "",
            "Sessões":d["total_completed"],
            "Aderência %":round(d["adher"]),
            "FC média":si(d["fc_med"]),
            "HRV":si(mt.get("hrv")),
            "Sono h":sf(mt.get("sono_h")),
            "FC rep":si(mt.get("fc_rep")),
            "Prova":ev["name"] if ev else "",
            "Data prova":prova_dt(ev),
            "LTHR?":("⚠️ "+lthr_txt(_sug.get(d["id"]), curto=True)) if d["intens"].get("lthr_suspect") else "",
            "Métricas":"✓" if d.get("metrics") else "—",
        })
    df=pd.DataFrame(rows)
    if q: df=df[df["Atleta"].str.contains(q,case=False,na=False)]
    if only_lthr: df=df[df["LTHR?"].str.startswith("⚠️")]
    if only_prova: df=df[df["Prova"]!=""]
    if only_nomet: df=df[df["Métricas"]=="—"]
    df=df.sort_values("Km", ascending=False)
    html_table(df, num={"Km","Bike km","Força","Sessões","Aderência %","FC média","HRV","Sono h","FC rep"})
    st.caption(f"{len(df)} atletas · ordenado por km")

    sect("Km por atleta · top 20")
    top=df.head(20)
    ch=(alt.Chart(top).mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, height=15, color="#ee6c4d")
        .encode(y=alt.Y("Atleta:N", sort="-x", title=None, axis=alt.Axis(labelColor=P["text"], labelFontSize=11, domainOpacity=0, tickOpacity=0)),
                x=alt.X("Km:Q", title=None, axis=_axis_y()),
                tooltip=["Atleta","Km"])
        .properties(height=430, background="rgba(0,0,0,0)").configure_view(strokeWidth=0))
    st.altair_chart(ch, width="stretch", theme=None)

def page_atleta(month):
    data=build_all(month)
    if not data:
        st.info("Nenhum dado deste mês ainda. Vá em **Visão da Equipe** e clique em **Atualizar todos** para puxar do TrainingPeaks."); return
    names=sorted((d["name"] for d in data), key=str.lower)   # atletas em ordem alfabética
    if st.session_state.get("sel_atleta") not in names:
        st.session_state.pop("sel_atleta", None)             # mês mudou → valor pode não existir
    sel=st.selectbox("Atleta", names, key="sel_atleta")
    d=next(x for x in data if x["name"]==sel)
    mt=d.get("metrics") or {}
    ev=d.get("event")

    # card do atleta
    av=avatar_bytes(d["id"])
    if av:
        avhtml=f'<img src="data:image/jpeg;base64,{base64.b64encode(av).decode()}">'
    else:
        avhtml=f'<div class="mono">{initials(sel)}</div>'
    chips=[f'<span class="chip">{d["run_km"]:.0f} km corrida</span>',
           f'<span class="chip">{d["total_completed"]} treinos</span>']
    if d.get("bike_km",0)>0:
        chips.insert(1, f'<span class="chip">🚴 {d["bike_km"]:.0f} km bike</span>')
    if d.get("str_n",0)>0:
        chips.insert(2 if d.get("bike_km",0)>0 else 1,
                     f'<span class="chip">🏋️ {d["str_n"]} força</span>')
    if ev:
        dd=days_to_event(ev, dt.date.today())        # dias a partir de hoje
        try: _edt=dt.date.fromisoformat(ev["date"]).strftime("%d/%m/%Y")
        except Exception: _edt=ev.get("date","")
        _falta=(f" · faltam {dd}d" if dd and dd>0 else (" · hoje!" if dd==0 else ""))
        chips.append(f'<span class="chip">🎯 {ev["name"]} · {_edt}{_falta}</span>')
    _adh=d["adher"]
    st.markdown(f'<div class="ath">{avhtml}<div><div class="nm">{sel}</div>'
                f'<div class="meta">{"".join(chips)}</div></div>'
                f'<div style="margin-left:auto;text-align:center;flex:none">'
                f'{ring_svg(_adh/100, cor_aderencia(_adh), 68)}'
                f'<div class="ringlab">aderência</div></div></div>', unsafe_allow_html=True)

    # bloco ativo criado pelo Gerador de Treinos (tabela blocos_gerados do aslab.db)
    try:
        import sqlite3 as _sq3
        from db import DB_PATH as _DBP
        _con=_sq3.connect(f"file:{_DBP}?mode=ro", uri=True, timeout=3)
        _hj=dt.date.today().isoformat()
        _b=_con.execute("SELECT inicio,fim,semanas,sessoes,km_total FROM blocos_gerados "
                        "WHERE atleta_id=? AND inicio<=? AND fim>=? ORDER BY criado DESC LIMIT 1",
                        (str(d["id"]), _hj, _hj)).fetchone()
        _con.close()
        if _b:
            _ini,_fim,_sem,_n,_km=_b
            _w=min((dt.date.today()-dt.date.fromisoformat(_ini)).days//7+1, int(_sem or 1))
            _fmt=lambda s: dt.date.fromisoformat(s).strftime("%d/%m")
            st.markdown(f'<div class="tick"><b>Bloco ativo do Gerador</b>'
                        f'<span class="sep">/</span>{_fmt(_ini)} → {_fmt(_fim)}'
                        f'<span class="sep">/</span>semana <b>{_w}</b> de <b>{int(_sem or 1)}</b>'
                        f'<span class="sep">/</span><b>{int(_n or 0)}</b> treinos · <b>{(_km or 0):.0f} km</b></div>',
                        unsafe_allow_html=True)
    except Exception:
        pass
    if d["intens"].get("lthr_suspect"):
        _sg=lthr_sugestoes([d]).get(d["id"])
        st.warning(f'LTHR a revisar — FC média ≥ LTHR ({d["refs"]["lthr"]} bpm). Sugestão: {lthr_txt(_sg)}. '
                   'Nada foi alterado no TP; confirme com o Teste de limiar 30\'.')

    # atualização ao vivo (puxa do TP, inclui os treinos de hoje)
    u=st.columns([1.3,3])
    if u[0].button("Atualizar do TrainingPeaks", key="rf_"+d["id"], type="primary"):
        try:
            with st.spinner("Puxando os treinos atuais do atleta…"):
                rec=refresh_athlete(month, d["id"])
            nrun=sum(1 for w in rec.get("workouts",[]) if w["type"]=="completed" and w["kind"]=="run")
            st.cache_data.clear()
            st.toast(f'Atualizado — {nrun} corridas no mês.', icon="✅")
            st.rerun()
        except Exception as e:
            st.error(f"Não consegui atualizar: {e}")
    u[1].caption("Puxa os treinos do mês até hoje (inclui os de hoje). Pode clicar todo dia.")

    # ---- espelho da semana do TrainingPeaks (planejado × realizado) ----
    sect("Semana no TrainingPeaks · espelho")
    _today=dt.date.today(); _this_mon=_today-dt.timedelta(days=_today.weekday())
    _week_opts=[_this_mon-dt.timedelta(days=7*i) for i in range(8)]
    def _wlbl(m):
        e=m+dt.timedelta(days=6)
        return f'{m.strftime("%d/%m")} – {e.strftime("%d/%m/%Y")}' + (" · atual" if m==_this_mon else "")
    wk2=st.selectbox("Semana ", _week_opts, format_func=_wlbl, key="tpwk_"+d["id"])
    try:
        with st.spinner("Puxando a semana do TrainingPeaks…"):
            recw=week_mirror(d["id"], wk2.isoformat())
    except Exception as e:
        recw=None; st.error(f"Não consegui puxar a semana: {e}")
    if recw:
        if recw.get("error"):
            _msg=str(recw["error"])
            if "token" in _msg.lower() or "auth" in _msg.lower():
                st.warning("🔑 A sessão do TrainingPeaks expirou. Entre em app.trainingpeaks.com no Chrome "
                           "(conta andrelcmsantos@gmail.com) e me peça: **reautentica o TP**.")
            else:
                st.error(f'Erro do TrainingPeaks: {_msg}')
        else:
            st.markdown(render_week_mirror(recw, wk2), unsafe_allow_html=True)
            st.caption("🟢 feito como planejado · 🔴 planejado e não feito · 🟠 a fazer · 🔵 extra (não planejado). "
                       "Ao vivo do TP, cache de 10 min.")

    _hasbike=d.get("bike_km",0)>0
    mets=[("Corrida", f'{d["run_km"]:.0f} km', _delta(d,"run_km","prev","run_km"))]
    if _hasbike: mets.append(("Bike", f'{d["bike_km"]:.0f} km', None))
    if d.get("str_n",0)>0: mets.append(("Força", f'{d["str_n"]} sessões', None))
    mets+=[("Sessões", d["total_completed"], _delta(d,"total_completed","prev","sessions")),
           ("Aderência", f'{d["adher"]:.0f}%', _delta(d,"adher","prev","adher","%")),
           ("Pico longo", f'{d["peak_km"]:.0f} km', None)]
    if len(mets)<6: mets.append(("Altimetria", f'{d["elev_total"]:.0f} m', None))
    k=st.columns(len(mets))
    for _c,(_l,_v,_dl) in zip(k,mets): _c.metric(_l,_v,_dl)

    # gráficos de treino
    g=st.columns(2)
    with g[0]:
        sect("Volume semanal · km" + (" · corrida + bike" if _hasbike else ""))
        st.altair_chart(bar_weekly_bike(d["weekly"]) if _hasbike else bar_weekly(d["weekly"],"km","#ee6c4d"),
                        width="stretch", theme=None)
    with g[1]:
        sect("Horas treinadas")
        st.altair_chart(bar_weekly(d["weekly"],"hrs","#3f8ea0",fmt=".1f"), width="stretch", theme=None)
    sect("Tendência de FC média · semanal")
    fcc=fc_weekly(d["weekly"])
    if fcc is not None: st.altair_chart(fcc, width="stretch", theme=None)
    else: st.caption("Sem FC registrada.")

    # condição física — PMC estilo TrainingPeaks
    fr=d.get("fitness_raw") or {}
    daily=fr.get("daily") or []
    if daily:
        with st.container(border=True):
            st.markdown("**Condição Física — Performance Management Chart**")
            _cur_=fr.get("current") or (daily[-1] if daily else {})
            _chips=[]
            if _cur_.get("ctl") is not None: _chips.append(f'<span class="chip" style="border-color:rgba(63,142,160,.5);color:#3f8ea0;background:rgba(63,142,160,.12)">Fitness {_cur_["ctl"]:.0f}</span>')
            if _cur_.get("atl") is not None: _chips.append(f'<span class="chip" style="border-color:rgba(238,108,77,.5);color:#ee6c4d;background:rgba(238,108,77,.10)">Fadiga {_cur_["atl"]:.0f}</span>')
            if _cur_.get("tsb") is not None:
                _tv=_cur_["tsb"]; _tc="#37b87f" if _tv>=0 else "#cf4a5a"
                _chips.append(f'<span class="chip" style="border-color:{_tc}66;color:{_tc};background:{_tc}1a">Forma {_tv:+.0f}</span>')
            st.markdown('<div class="pmc-leg">'
                        '<span class="dot" style="background:#3f8ea0;margin-left:0"></span><b>Fitness (CTL)</b>'
                        '<span class="dot" style="background:#ee6c4d"></span><b>Fadiga (ATL)</b>'
                        '<span class="dot" style="background:#37b87f"></span><b>Forma (TSB · verde=descansado, vermelho=fadigado)</b>'
                        f'<span class="dot" style="background:{P["mut"]}"></span><b>TSS diário</b>'
                        + ("&nbsp;&nbsp;·&nbsp;&nbsp;"+" ".join(_chips) if _chips else "") + '</div>',
                        unsafe_allow_html=True)
            st.altair_chart(pmc_chart(daily), width="stretch", theme=None)

    # ---- tendências de recuperação (VFC e sono, do banco) ----
    st.divider()
    sect("🫀 Recuperação · tendências")
    _dias=st.radio("Janela", [30,60,90], index=1, horizontal=True, format_func=lambda x:f"{x} dias",
                   key="rec_win_"+d["id"], label_visibility="collapsed")
    _ms=metricas_serie(d["id"], _dias, dt.date.today().isoformat())
    if _ms.empty or (_ms["hrv"].notna().sum()==0 and _ms["sono_h"].notna().sum()==0):
        st.caption("Sem métricas de recuperação sincronizadas para este atleta (relógio/Garmin não conectado ao TP).")
    else:
        _hrv=_ms["hrv"].dropna(); _sono=_ms["sono_h"].dropna()
        _hrv7=_ms["hrv_m7"].dropna(); _sono7=_ms["sono_h_m7"].dropna()
        kk=st.columns(4)
        if len(_hrv):
            _hb=_hrv.mean(); _hn=_hrv7.iloc[-1] if len(_hrv7) else _hrv.iloc[-1]
            kk[0].metric("VFC · média 7d", f"{_hn:.0f} ms", f"{(_hn-_hb):+.0f} vs sua média ({_hb:.0f})",
                         delta_color="normal")
            kk[1].metric("VFC · dias registrados", f"{len(_hrv)}")
        if len(_sono):
            _sb=_sono.mean(); _sn=_sono7.iloc[-1] if len(_sono7) else _sono.iloc[-1]
            kk[2].metric("Sono · média 7d", f"{_sn:.1f} h", f"{(_sn-_sb):+.1f} vs sua média ({_sb:.1f})",
                         delta_color="normal")
            kk[3].metric("Noites < 7h", f'{int((_sono<7).sum())} de {len(_sono)}')
        g=st.columns(2)
        with g[0]:
            st.caption("**VFC (HRV)** — pontos = dia · linha = média 7d · tracejado = sua média · faixa = zona normal (±1 dp)")
            if len(_hrv):
                _sd=_hrv.std() if len(_hrv)>3 else 0
                ch=trend_chart(_ms,"hrv","#37b87f","VFC (ms)", ref=_hrv.mean(),
                               banda=(_hrv.mean()-_sd, _hrv.mean()+_sd))
                if ch is not None: st.altair_chart(ch, width="stretch", theme=None)
            else: st.caption("sem VFC")
        with g[1]:
            st.caption("**Sono** — pontos = noite · linha = média 7d · tracejado = 7h (referência)")
            if len(_sono):
                ch=trend_chart(_ms,"sono_h","#3f8ea0","Sono (h)", ref=7.0, fmt=".1f")
                if ch is not None: st.altair_chart(ch, width="stretch", theme=None)
            else: st.caption("sem sono")
        if _ms["fc_rep"].notna().sum()>=3:
            st.caption("**FC de repouso** — subir junto com VFC caindo = sinal clássico de fadiga/estresse")
            ch=trend_chart(_ms,"fc_rep","#ee6c4d","FC repouso (bpm)", ref=_ms["fc_rep"].mean(), h=170)
            if ch is not None: st.altair_chart(ch, width="stretch", theme=None)

    # drift cardíaco (desacoplamento Pa:Hr em treinos contínuos)
    st.divider()
    sect("🫀 Drift cardíaco · desacoplamento Pa:Hr")
    st.caption("Compara eficiência (velocidade/FC) da 1ª vs 2ª metade dos treinos **contínuos** ≥40 min "
               "(descarta aquecimento e pausas). <5% = base aeróbica sólida · 5–8% razoável · >8% alto · negativo = excelente.")
    if st.button("🫀 Calcular drift (últimos 60 dias)", key="drift_"+d["id"], type="secondary"):
        st.session_state["drift_on_"+d["id"]]=True
    if st.session_state.get("drift_on_"+d["id"]):
        import drift as _drift
        _pb=st.progress(0.0, text="Baixando arquivos dos treinos…")
        def _prog(i,n,t): _pb.progress((i+1)/max(n,1), text=f"{i+1}/{n} — {t[:36]}")
        _d0=dt.date.today()
        try:
            if NUVEM: _res=pm.drifts(d["id"], (_d0-dt.timedelta(days=60)).isoformat(), _d0.isoformat())
            else: _res=asyncio.run(_drift.athlete_drifts(d["id"], (_d0-dt.timedelta(days=60)).isoformat(),
                                                         _d0.isoformat(), progress=_prog))
        except Exception as e:
            _res=[]; st.error(f"Falhou: {e}")
        _pb.progress(1.0, text="Concluído")
        _oks=[r for r in _res if r.get("ok")]
        _skip=[r for r in _res if not r.get("ok")]
        if _oks:
            html_table(pd.DataFrame([{
                "Data":dt.date.fromisoformat(r["date"]).strftime("%d/%m") if r.get("date") else "–",
                "Treino":r["title"][:34], "Dur.":f'{r["dur_min"]}min',
                "Pace 1ª→2ª":f'{fmt_pace(r["pace1"]).replace("/km","")} → {fmt_pace(r["pace2"]).replace("/km","")}',
                "FC 1ª→2ª":f'{r["fc1"]} → {r["fc2"]}',
                "Drift":f'{r["dec"]:+.1f}%',
                "Avaliação":_drift.classify(r["dec"]),
            } for r in _oks]), num={"Dur.","Drift"})
            _med=sum(r["dec"] for r in _oks)/len(_oks)
            st.caption(f'Média do período: **{_med:+.1f}%** · {len(_oks)} treino(s) avaliados'
                       + (f' · {len(_skip)} não avaliados (intervalado/curto/sem arquivo)' if _skip else '')
                       + ' · calor e desidratação também elevam o drift.')
        else:
            st.info("Nenhum treino contínuo avaliável nos últimos 60 dias ("
                    + "; ".join(f'{r["title"][:18]}: {r.get("motivo","?")}' for r in _skip[:4]) + "…)")

    # recuperação
    if d.get("metrics"):
        sect("Recuperação · médias do mês")
        items=[]
        if mt.get("fc_rep") is not None:    items.append(("FC repouso", f'{round(mt["fc_rep"])} bpm'))
        if mt.get("hrv") is not None:       items.append(("HRV", f'{round(mt["hrv"])}'))
        if mt.get("sono_h") is not None:    items.append(("Sono", f'{mt["sono_h"]:.1f} h'))
        if mt.get("body_batt") is not None: items.append(("Body Battery", f'{round(mt["body_batt"])}'))
        if mt.get("stress") is not None:    items.append(("Estresse", f'{round(mt["stress"])}'))
        if mt.get("peso") is not None:      items.append(("Peso", f'{mt["peso"]:.1f} kg'))
        cols=st.columns(len(items) or 1)
        for i,(lab,val) in enumerate(items): cols[i].metric(lab, val)
        # sono detalhado (profundo/leve/REM)
        prof,leve,rem = mt.get("sono_prof"), mt.get("sono_leve"), mt.get("sono_rem")
        if any(v is not None for v in (prof,leve,rem)):
            sect("Sono detalhado · médias")
            s=st.columns(3)
            s[0].metric("Profundo", f'{prof:.1f} h' if prof is not None else "–")
            s[1].metric("Leve", f'{leve:.1f} h' if leve is not None else "–")
            s[2].metric("REM", f'{rem:.1f} h' if rem is not None else "–")
        st.caption(f'{mt.get("days",0)} dias monitorados')

    # destaques (do mês)
    sect("Destaques do mês")
    h=st.columns(3)
    if d["rec_dist"]: h[0].metric("Maior distância", f'{d["rec_dist"]["dist_km"]:.1f} km', d["rec_dist"]["date"].strftime("%d/%m"))
    if d["rec_pace"]: h[1].metric("Melhor pace", fmt_pace(d["rec_pace"]["pace"]))
    if d["rec_tss"]: h[2].metric("Maior carga", f'{d["rec_tss"]["tss"]:.0f} TSS')

    # recordes de corrida (melhores marcas por distância, todo o histórico)
    sect("🏅 Recordes de corrida · melhores marcas")
    with st.spinner("Buscando recordes do atleta…"):
        try: recs=athlete_records(d["id"], dt.date.today().isoformat())
        except Exception as e: recs={}; st.caption(f"Recordes indisponíveis agora: {e}")
    if any(recs.values()):
        cards=""
        for label,_,_ in RUN_PRS:
            rec=recs.get(label)
            if not rec: continue
            try: dtxt=dt.date.fromisoformat(rec["date"][:10]).strftime("%d/%m/%y")
            except Exception: dtxt=rec.get("date","") or ""
            cards+=(f'<div class="rec"><div class="rl">{label}</div>'
                    f'<div class="rv">{_fmt_time(rec["secs"])}</div>'
                    f'<div class="rs">{fmt_pace(rec["pace"])} · {dtxt}</div></div>')
        st.markdown(f'<div class="recwrap">{cards}</div>', unsafe_allow_html=True)
    else:
        st.caption("Sem recordes de corrida registrados no TrainingPeaks.")

    sect("Recado do treinador")
    st.info(d.get("coach_msg") or "_(recado de IA não gerado para este mês — usando fallback por regras no PDF)_")

    # ---- relatório individual (gera só este atleta, na hora) ----
    # ---- evolução de longo prazo ----
    st.divider()
    sect("Evolução · últimos 12 meses")
    if True:
        evo=evolution(d["id"], 12, dt.date.today().isoformat())
        if evo:
            edf=pd.DataFrame(evo)
            g2=st.columns(2)
            with g2[0]:
                st.caption("Km de corrida por mês")
                ch=(alt.Chart(edf).mark_bar(cornerRadiusTopLeft=6,cornerRadiusTopRight=6,size=26,color="#ee6c4d")
                    .encode(x=alt.X("mes:N",sort=None,axis=_axis_x()),
                            y=alt.Y("km:Q",title=None,axis=_axis_y()),
                            tooltip=["mes",alt.Tooltip("km:Q",format=".0f")])
                    .properties(height=230,background="rgba(0,0,0,0)").configure_view(strokeWidth=0))
                st.altair_chart(ch, width="stretch", theme=None)
            with g2[1]:
                st.caption("Pace médio por mês (min/km)")
                pdf2=edf.dropna(subset=["pace"])
                if len(pdf2):
                    ch2=(alt.Chart(pdf2).mark_line(point=True,color="#3f8ea0",strokeWidth=2.5)
                        .encode(x=alt.X("mes:N",sort=None,axis=_axis_x()),
                                y=alt.Y("pace:Q",title=None,scale=alt.Scale(reverse=True,zero=False),axis=_axis_y()),
                                tooltip=["mes",alt.Tooltip("pace:Q",format=".2f")])
                        .properties(height=230,background="rgba(0,0,0,0)").configure_view(strokeWidth=0))
                    st.altair_chart(ch2, width="stretch", theme=None)
                else:
                    st.caption("Sem corridas no período.")
            html_table(pd.DataFrame([{"Mês":r["mes"],"Km":f'{r["km"]:.0f}',
                                      "Pace":fmt_pace(r["pace"]) if r["pace"] else "–",
                                      "Horas":f'{r["hrs"]:.1f}',"Sessões":r["sess"]} for r in evo]),
                       num={"Km","Pace","Horas","Sessões"})
        else:
            st.caption("Nenhum treino encontrado nos últimos 12 meses.")

    st.divider()
    sect("Relatório individual")
    per=st.radio("Período do relatório", ["Mês selecionado","3 meses","6 meses","9 meses"],
                 horizontal=True, key="per_"+d["id"])
    if per=="Mês selecionado":
        p=pdf_path(month, sel)
        gc=st.columns([1.3,1.3,3])
        if gc[0].button("Gerar relatório", key="genpdf_"+d["id"], type="primary"):
            try:
                with st.spinner("Gerando o PDF deste atleta…"):
                    generate_athlete_pdf(d, month)
                st.toast("Relatório gerado!", icon="✅")
            except Exception as e:
                st.error(f"Falhou ao gerar: {e}")
        if pdf_local(p):
            with open(p,"rb") as fh:
                gc[1].download_button("Baixar PDF", fh.read(), file_name=os.path.basename(p), mime="application/pdf")
            png=pdf_preview_png(p, os.path.getmtime(p))
            if png: st.image(png, width="stretch")
        else:
            gc[1].caption("Ainda não gerado.")
    else:
        n=int(per.split()[0])
        pp=pdf_path_period(sel, n, dt.date.today())
        gc=st.columns([1.3,1.3,3])
        if gc[0].button(f"Gerar {per}", key=f"genper{n}_"+d["id"], type="primary"):
            try:
                with st.spinner(f"Puxando {n} meses do TrainingPeaks e gerando o PDF… (~1 min)"):
                    generate_period_pdf(d["id"], sel, n)
                st.toast(f"Relatório de {per} gerado!", icon="✅")
            except Exception as e:
                st.error(f"Falhou ao gerar: {e}")
        if pdf_local(pp):
            with open(pp,"rb") as fh:
                gc[1].download_button("Baixar PDF", fh.read(), file_name=os.path.basename(pp),
                                      mime="application/pdf", key=f"dlper{n}_"+d["id"])
            png=pdf_preview_png(pp, os.path.getmtime(pp))
            if png: st.image(png, width="stretch")
        else:
            gc[1].caption(f"Ainda não gerado hoje. Puxa os últimos {n} meses ao vivo do TP (quebra por mês).")

    # ---- relatório SEMANAL (puxa a semana escolhida do TP, na hora) ----
    st.divider()
    sect("Relatório semanal")
    wk=st.selectbox("Semana", _week_opts, format_func=_wlbl, key="wk_sel_"+d["id"])
    wc=st.columns([1.4,1.4,3])
    if wc[0].button("Gerar semanal", key="genwk_"+d["id"], type="primary"):
        try:
            with st.spinner("Puxando a semana do TrainingPeaks e gerando o PDF…"):
                generate_weekly_pdf(d["id"], sel, wk)
            st.toast("Relatório semanal gerado!", icon="✅")
        except Exception as e:
            st.error(f"Falhou ao gerar o semanal: {e}")
    wp=pdf_path_week(sel, wk)
    if pdf_local(wp):
        with open(wp,"rb") as fh:
            wc[1].download_button("Baixar semanal", fh.read(), file_name=os.path.basename(wp),
                                  mime="application/pdf", key="dlwk_"+d["id"])
        wpng=pdf_preview_png(wp, os.path.getmtime(wp))
        if wpng: st.image(wpng, width="stretch")
    else:
        wc[1].caption("Ainda não gerado para esta semana.")

    # ---- treinos por semana (HISTÓRICO COMPLETO, independe do mês) ----
    st.divider()
    sect("Treinos por semana · histórico completo")
    mb=st.radio("Período", [3,6,12,24], index=0, horizontal=True,
                format_func=lambda m:f"{m} meses", key="hist_meses")
    with st.spinner("Buscando o histórico de treinos (com FC)… pode levar alguns segundos na 1ª vez."):
        try: hist=athlete_history(d["id"], mb, dt.date.today().isoformat())
        except Exception as e:
            st.caption(f"Histórico indisponível agora: {e}"); return
    if not hist:
        st.caption("Nenhum treino realizado no período."); return

    # ---- detalhe completo de um treino (clique/selecione) ----
    def _wlab(h):
        return (f'{WD[h["date"].weekday()]} {h["date"].strftime("%d/%m/%y")} · '
                f'{SPORT_PT.get(h["sport"], h["sport"] or "—")} · {(h["title"] or "")[:30]}'
                + (f' · {h["dist"]:.1f}km' if h.get("dist") else ""))
    _opts={_wlab(h): h for h in hist if h.get("id")}
    _selw=st.selectbox("🔎 Ver todos os dados de um treino", [""]+list(_opts.keys()),
                       key="wdet_"+d["id"])
    if _selw:
        h=_opts[_selw]
        with st.spinner("Buscando o detalhe no TrainingPeaks…"):
            try: det=workout_detail(d["id"], h["id"])
            except Exception as e: det={"isError":True, "message":str(e)}
        if det.get("isError"):
            st.error(f'Não consegui: {det.get("message")}')
        else:
            m=det.get("metrics") or {}
            with st.container(border=True):
                st.markdown(f'**{det.get("title") or h["title"]}** · '
                            f'{h["date"].strftime("%d/%m/%Y")} · {SPORT_PT.get(det.get("sport"), det.get("sport") or "")}')
                _dur=m.get("duration_actual"); _dist=m.get("distance_actual_km")
                _pace=(_dur*60/_dist) if (_dur and _dist and _dist>0) else None
                c1=st.columns(6)
                c1[0].metric("Distância", f'{_dist:.2f} km' if _dist else "–")
                c1[1].metric("Tempo", _hm(_dur) if _dur else "–")
                c1[2].metric("Pace", fmt_pace(_pace) if _pace else "–")
                c1[3].metric("FC média", f'{round(m["avg_hr"])} bpm' if m.get("avg_hr") else "–")
                c1[4].metric("Cadência", f'{round(m["avg_cadence"])}' if m.get("avg_cadence") else "–")
                c1[5].metric("TSS", f'{m["tss_actual"]:.0f}' if m.get("tss_actual") else "–")
                c2=st.columns(6)
                c2[0].metric("IF", f'{m["if_actual"]:.2f}' if m.get("if_actual") else "–")
                c2[1].metric("Potência méd.", f'{round(m["avg_power"])} W' if m.get("avg_power") else "–")
                c2[2].metric("Elevação", f'{m["elevation_gain"]:.0f} m' if m.get("elevation_gain") is not None else "–")
                c2[3].metric("Calorias", f'{round(m["calories"])}' if m.get("calories") else "–")
                _rpe=det.get("rpe"); _feel=det.get("feeling")
                c2[4].metric("RPE", f'{_rpe}/10' if _rpe else "–")
                _fmap={1:"😫",2:"😕",3:"😐",4:"🙂",5:"😄"}
                c2[5].metric("Sensação", _fmap.get(_feel,"–") if _feel else "–")
                # planejado × realizado
                if m.get("duration_planned") or m.get("tss_planned") or m.get("distance_planned_km"):
                    _pl=[]
                    if m.get("distance_planned_km"): _pl.append(f'{m["distance_planned_km"]:.1f} km')
                    if m.get("duration_planned"): _pl.append(_hm(m["duration_planned"]))
                    if m.get("tss_planned"): _pl.append(f'{m["tss_planned"]:.0f} TSS')
                    st.caption("📋 Planejado: " + " · ".join(_pl))
                if det.get("description"):
                    st.markdown(f'<div class="chip" style="white-space:normal;display:block;margin-top:6px">📝 {_html.escape(det["description"])}</div>',
                                unsafe_allow_html=True)
                _cms=det.get("workout_comments") or []
                for cm in _cms[:5]:
                    _txt=cm.get("comment") or cm.get("text") or ""
                    _who=cm.get("firstName") or cm.get("commenterName") or ""
                    if _txt: st.caption(f'💬 {_who}: {_txt}')

    weeks=defaultdict(list)
    for w in hist:
        weeks[w["date"]-dt.timedelta(days=w["date"].weekday())].append(w)
    st.caption(f"{len(hist)} treinos em {len(weeks)} semanas.")
    for wkstart in sorted(weeks, reverse=True):
        ws=sorted(weeks[wkstart], key=lambda x:x["date"], reverse=True)
        km=sum(x["dist"] for x in ws if x["sport"]=="Run")
        hrs=sum(x["dur"] for x in ws); tss=sum(x["tss"] for x in ws)
        wkend=wkstart+dt.timedelta(days=6)
        sect(f'Semana {wkstart.strftime("%d/%m/%y")}–{wkend.strftime("%d/%m/%y")} · '
             f'{len(ws)} treinos · {km:.0f} km · {hrs:.1f}h · {tss:.0f} TSS')
        rows=[]
        for w in ws:
            rows.append({
                "Dia": f'{WD[w["date"].weekday()]} {w["date"].strftime("%d/%m/%y")}',
                "Treino": w["title"][:44],
                "Tipo": SPORT_PT.get(w["sport"], w["sport"] or "—"),
                "Dist.": f'{w["dist"]:.1f} km' if w["dist"] else "–",
                "Tempo": _hm(w["dur"]),
                "Pace": fmt_pace(w["pace"]) if w["pace"] else "–",
                "Cad.": str(round(w["cad"])) if w.get("cad") else "–",
                "FC": str(round(w["hr"])) if w.get("hr") else "–",
                "TSS": str(round(w["tss"])) if w["tss"] else "–",
            })
        html_table(pd.DataFrame(rows), num={"Dist.","Tempo","Pace","Cad.","FC","TSS"})

def _delta(d, curkey, prevblock, prevkey, suf=""):
    prev=d.get(prevblock)
    if not prev or prev.get(prevkey) in (None,0): return None
    cur=d[curkey]; base=prev[prevkey]
    pct=(cur-base)/base*100
    if abs(pct)<1: return None
    return f'{pct:+.0f}%'   # vs mês anterior (seta indica direção)

def page_pdfs(month):
    hero("Relatórios (PDF)", f'{MESES[int(month[5:7])-1].capitalize()} {month[:4]}', "Documentos")
    data=build_all(month)
    if not data:
        st.info("Nenhum atleta com dados neste mês. Colete em **Visão da Equipe → Atualizar todos**."); return
    outdir=os.path.join(BASE,"saida",month)
    pdfs=sorted(glob.glob(os.path.join(outdir,"*.pdf")))
    y,m=map(int,month.split("-")); zip_path=os.path.join(BASE,f'Relatorios_{MESES[m-1]}_{y}.zip')
    ga=st.columns([1.7,1.4,2])
    if ga[0].button("Gerar todos os PDFs", key="genall", type="primary"):
        with st.status("Gerando todos os relatórios do mês… (pode levar alguns minutos)", expanded=True):
            rc=_run_stream([PYBIN,"render_all_modern.py","--month",month], st.empty())
        if rc==0:
            st.cache_data.clear(); st.toast("Todos gerados + ZIP montado!", icon="✅"); st.rerun()
        else:
            st.error("Falhou — veja o log acima.")
    if pdf_local(zip_path):
        with open(zip_path,"rb") as fh:
            ga[1].download_button("Baixar ZIP", fh.read(), file_name=os.path.basename(zip_path), mime="application/zip")
    ga[2].caption(f"{len(pdfs)} de {len(data)} atletas com PDF · monta o ZIP com todos.")
    st.divider()

    names=sorted((x["name"] for x in data), key=str.lower)   # alfabético
    sel=st.selectbox("Atleta", names)
    d=next(x for x in data if x["name"]==sel)
    p=pdf_path(month, sel)
    gc=st.columns([1.5,1.5,3])
    lbl="Regerar PDF" if pdf_local(p) else "Gerar PDF"
    if gc[0].button(lbl, key="pdfgen_"+d["id"], type="primary"):
        try:
            with st.spinner("Gerando o relatório…"):
                generate_athlete_pdf(d, month)
            st.toast("Relatório gerado!", icon="✅")
        except Exception as e:
            st.error(f"Falhou: {e}")
    if pdf_local(p):
        with open(p,"rb") as fh:
            gc[1].download_button("Baixar", fh.read(), file_name=os.path.basename(p), mime="application/pdf")
        png=pdf_preview_png(p, os.path.getmtime(p))
        if png: st.image(png, width="stretch")
    else:
        gc[1].caption("Ainda não gerado.")

    # ---- relatórios SEMANAIS em lote ----
    st.divider()
    sect("Relatórios semanais em lote")
    _today=dt.date.today(); _mon=_today-dt.timedelta(days=_today.weekday())
    _wopts=[_mon-dt.timedelta(days=7*i) for i in range(8)]
    def _wlbl2(w):
        e=w+dt.timedelta(days=6)
        return f'{w.strftime("%d/%m")} – {e.strftime("%d/%m/%Y")}' + (" · atual" if w==_mon else "")
    wcol=st.columns([1.6,3])
    wk=wcol[0].selectbox("Semana", _wopts, format_func=_wlbl2, key="wkb_sel")
    with wcol[1]:
        st.write(""); st.write("")
        todos=st.checkbox("Todos os atletas dos grupos", key="wkb_all")
    # lista COMPLETA do TrainingPeaks (não só quem correu no mês)
    try:
        roster=all_athletes()
    except Exception:
        roster=[{"id":x["id"],"name":x["name"]} for x in data]
        st.caption("Não consegui listar do TP agora — mostrando só os atletas do mês.")
    id_by_name={}
    for a_ in roster:
        nm_=a_["name"]
        if nm_ in id_by_name: nm_=f'{a_["name"]} ({a_["id"][-4:]})'   # desambigua homônimos
        id_by_name[nm_]=a_["id"]
    all_names=list(id_by_name.keys())
    msel=st.multiselect(f"Atletas · {len(all_names)} nos grupos", all_names, key="wkb_names",
                        placeholder="Escolha um ou mais atletas…", disabled=todos)
    alvo=all_names if todos else msel
    bc=st.columns([1.8,1.8,2.4])
    if bc[0].button(f"Gerar semanais ({len(alvo)})", key="wkb_go", type="primary", disabled=not alvo):
        pb=st.progress(0.0, text="Coletando a semana no TrainingPeaks…")
        ok=[]; fail=[]
        pairs=[(id_by_name[n], n) for n in alvo]; CH=8
        for ci in range(0, len(pairs), CH):
            chunk=pairs[ci:ci+CH]
            try:
                oks,fs=pm.semanais_lote(chunk, wk); ok+=oks; fail+=fs
            except Exception as e:
                st.error(str(e)); fail+=[nm for _,nm in chunk]; break
            done=min(ci+CH, len(pairs))
            pb.progress(done/len(pairs), text=f"{done}/{len(pairs)} atletas — gerando PDFs…")
        if ok:
            import zipfile
            zp=os.path.join(BASE, f'Semanais_{wk.strftime("%Y-%m-%d")}.zip')
            with zipfile.ZipFile(zp,"w",zipfile.ZIP_DEFLATED) as z:
                for p_ in ok: z.write(p_, os.path.basename(p_))
        pb.progress(1.0, text=f"Concluído — {len(ok)} PDFs gerados.")
        if fail:
            st.warning(f'{len(ok)} gerados · falharam {len(fail)}: {", ".join(fail[:8])}{"…" if len(fail)>8 else ""}')
        else:
            st.toast(f"{len(ok)} relatórios semanais gerados!", icon="✅")
    zp=os.path.join(BASE, f'Semanais_{wk.strftime("%Y-%m-%d")}.zip')
    if pdf_local(zp):
        with open(zp,"rb") as fh:
            bc[1].download_button("Baixar ZIP da semana", fh.read(), file_name=os.path.basename(zp),
                                  mime="application/zip", key="wkb_zip")
    bc[2].caption("Puxa a semana ao vivo do TrainingPeaks e gera um PDF por atleta + ZIP.")

    # ---- envio por E-MAIL ----
    st.divider()
    sect("Enviar relatórios por e-mail")
    try: _cfg=pm.email_configurado()
    except Exception as e:
        _cfg=None; st.caption(f"Envio por e-mail indisponível agora: {e}")
    if _cfg is False:
        st.info("**Configuração necessária (1x):** crie uma *senha de app* do Google em "
                "[myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) "
                "(precisa ter verificação em 2 etapas), copie `email_config.example.json` para "
                "`email_config.json` e cole a senha lá. Depois é só recarregar esta página.")
    elif _cfg:
        _mails={x["name"]:x.get("email") for x in all_athletes()}
        y2,m2=map(int,month.split("-")); _per=f'{MESES[m2-1]} de {y2}'
        _no_mac=nuvem.pdfs_no_mac() if NUVEM else {}
        def _tem_pdf(pth): return os.path.exists(pth) or os.path.relpath(pth, BASE) in _no_mac
        _envio=[]
        for x in data:
            _p=pdf_path(month, x["name"])
            _e=_mails.get(x["name"])
            if _tem_pdf(_p) and _e: _envio.append((x["name"], _e, _p))
        _sem_mail=[x["name"] for x in data if _tem_pdf(pdf_path(month,x["name"])) and not _mails.get(x["name"])]
        st.caption(f'{len(_envio)} atletas com PDF **e** e-mail cadastrado no TP · '
                   f'{len(_sem_mail)} com PDF mas sem e-mail.')
        _esel=st.multiselect("Enviar para", [n for n,_,_ in _envio], key="mail_sel",
                             placeholder="Escolha os atletas (ou marque todos abaixo)…")
        _todos_m=st.checkbox(f"Enviar para TODOS os {len(_envio)}", key="mail_all")
        _alvo=[t for t in _envio if _todos_m or t[0] in _esel]
        _conf=st.checkbox(f"Confirmo o envio de {len(_alvo)} e-mail(s) com os PDFs de {_per}",
                          key="mail_conf", disabled=not _alvo)
        if st.button(f"Enviar {len(_alvo)} e-mail(s)", key="mail_go", type="primary",
                     disabled=not (_alvo and _conf)):
            try:
                with st.spinner(f"Enviando {len(_alvo)} e-mail(s) pelo Gmail…"):
                    ok,fails=pm.enviar_emails(_alvo, _per)
                if fails: st.warning(f'{ok} enviados · falharam: {", ".join(fails[:6])}')
                else: st.success(f"{ok} relatórios enviados por e-mail!")
            except Exception as e:
                st.error(f"Falha no envio: {e}")

def _run_stream(cmd, ph):
    if NUVEM: return nuvem.rodar_script(cmd, ph)
    if cmd and cmd[0]==PYBIN and "-u" not in cmd:
        cmd=[cmd[0],"-u"]+cmd[1:]        # sem buffer → log ao vivo
    proc=subprocess.Popen(cmd, cwd=BASE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    buf=[]
    for line in proc.stdout:
        buf.append(line.rstrip())
        ph.code("\n".join(buf[-25:]))
    proc.wait(); return proc.returncode

def page_pipeline(month):
    hero("Pipeline", "Coletar · resumos · renderizar", "Automação")
    m=month or dt.date.today().strftime("%Y-%m")
    tgt=st.text_input("Mês alvo (YYYY-MM)", m)
    recs=load_records(tgt) if os.path.isdir(os.path.join(BASE,"data",tgt)) else []
    nrun=sum(1 for r in recs if r.get("has_run"))
    has_sum=os.path.exists(os.path.join(BASE,"data",tgt,"_summaries.json"))
    has_msg=os.path.exists(os.path.join(BASE,"data",tgt,"_messages.json"))
    npdf=len(glob.glob(os.path.join(BASE,"saida",tgt,"*.pdf")))
    s=st.columns(4)
    s[0].metric("Atletas c/ corrida", nrun)
    s[1].metric("Resumos", "✓" if has_sum else "—")
    s[2].metric("Recados de IA", "✓" if has_msg else "—")
    s[3].metric("PDFs gerados", npdf)

    st.divider()
    st.markdown("##### 1 · Coletar dados do TrainingPeaks")
    st.caption("Puxa treinos, fitness, prova, foto e métricas de todos os atletas. Pode levar ~10 min.")
    if st.button("Coletar", type="primary"):
        with st.spinner("Coletando..."):
            rc=_run_stream([PYBIN,"collect.py","--month",tgt], st.empty())
        st.success("Coleta concluída.") if rc==0 else st.error("Falhou (ver log).")
        st.cache_data.clear()

    st.markdown("##### 2 · Gerar resumos por atleta")
    if st.button("Gerar resumos"):
        with st.spinner("Gerando..."):
            rc=_run_stream([PYBIN,"gen_summaries.py","--month",tgt], st.empty())
        st.success("Resumos gerados.") if rc==0 else st.error("Falhou.")
        st.cache_data.clear()

    st.markdown("##### 3 · Recados de IA")
    st.caption("Este passo é feito pelo Claude Code (subagentes). Peça no chat: "
               "\"Gere os recados de IA de %s a partir do _summaries.json\". "
               "Sem isso, o PDF usa o recado automático por regras." % tgt)
    st.info("Status: " + ("✓ _messages.json presente" if has_msg else "— ainda não gerado (usará fallback por regras)"))

    st.markdown("##### 4 · Renderizar os PDFs")
    if st.button("Renderizar PDFs", type="primary"):
        with st.spinner("Renderizando..."):
            rc=_run_stream([PYBIN,"render_all_modern.py","--month",tgt], st.empty())
        st.success("PDFs gerados e ZIP montado.") if rc==0 else st.error("Falhou.")
        st.cache_data.clear()

def page_provas(month):
    hero("Provas dos Alunos", "Calendário completo — todas as provas de cada aluno, direto do TrainingPeaks", "Competições")
    data=build_all(month)
    _hoje=dt.date.today()
    fev=st.columns([2.4,1.6,2.0])
    q_ev=fev[0].text_input("Buscar atleta ou prova", key="ev_q", placeholder="ex.: maratona, Caroline…")
    hor=fev[1].selectbox("Horizonte", [60,90,180,365],
                         format_func=lambda x:f"próximos {x} dias", key="ev_hor", index=1)
    with st.spinner(f"Buscando provas de todos os alunos ({hor} dias)… 1ª carga demora ~15s, depois fica em cache."):
        try: _evs=all_events(hor, _hoje.isoformat())
        except Exception as e:
            _evs=[]; st.error(f"Não consegui buscar as provas: {e}")
    if not _evs:
        st.info("Nenhuma prova encontrada no horizonte selecionado."); return

    _tsb_by={d0["name"]:((d0.get("fitness_raw") or {}).get("current") or {}).get("tsb") for d0 in data}
    _km_by={d0["name"]:round(d0["run_km"]) for d0 in data}
    MA=["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
    rows=[]
    for e in _evs:
        try: edt=dt.date.fromisoformat(e["date"])
        except Exception: continue
        dd=(edt-_hoje).days
        if dd<0: continue
        rows.append({"Atleta":e["atleta"], "Prova":e["prova"],
                     "Data":edt.strftime("%d/%m/%y"), "Faltam":f'{dd}d',
                     "_dd":dd, "_mes":f'{MA[edt.month-1]}/{str(edt.year)[2:]}',
                     "Tipo":str(e.get("tipo") or ""),
                     "Km no mês":_km_by.get(e["atleta"],""),
                     "TSB":f'{_tsb_by[e["atleta"]]:.0f}' if _tsb_by.get(e["atleta"]) is not None else "–"})
    if q_ev:
        _q=q_ev.lower()
        rows=[r for r in rows if _q in r["Atleta"].lower() or _q in r["Prova"].lower()]
    if not rows:
        st.info("Nenhuma prova bate com esse filtro."); return
    rows.sort(key=lambda x:x["_dd"])

    # KPIs
    prox=rows[0]
    c=st.columns(4)
    c[0].metric("Provas no horizonte", len(rows))
    c[1].metric("Atletas com prova", len({r["Atleta"] for r in rows}))
    c[2].metric("Nos próximos 30 dias", sum(1 for r in rows if r["_dd"]<=30))
    c[3].metric("Próxima prova", prox["Data"], f'{prox["Atleta"].split()[0]} · {prox["Prova"][:18]}', delta_color="off")

    # provas por mês
    _cnt={}
    for r in rows: _cnt[r["_mes"]]=_cnt.get(r["_mes"],0)+1
    _seen=[]; _=[_seen.append(r["_mes"]) for r in rows if r["_mes"] not in _seen]
    cdf=pd.DataFrame([{"Mês":m,"Provas":_cnt[m]} for m in _seen])
    sect("Provas por mês")
    ch=(alt.Chart(cdf).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, size=34, color="#f2a541")
        .encode(x=alt.X("Mês:N", sort=None, axis=_axis_x()),
                y=alt.Y("Provas:Q", title=None, axis=_axis_y()),
                tooltip=["Mês","Provas"])
        .properties(height=180, background="rgba(0,0,0,0)").configure_view(strokeWidth=0))
    st.altair_chart(ch, width="stretch", theme=None)

    # calendário agrupado por mês
    for m in _seen:
        grp=[r for r in rows if r["_mes"]==m]
        sect(f'{m} · {len(grp)} prova(s)')
        html_table(pd.DataFrame(grp).drop(columns=["_dd","_mes"]),
                   num={"Faltam","Km no mês","TSB"})
    st.caption("TSB positivo perto da prova = chegando descansado · cache de 1h · inclui TODAS as provas de cada aluno, não só a próxima.")

FASES_ATP=["Base","Específico","Polimento","Prova","Recuperação"]
CORES_FASE={"Base":"#3f8ea0","Específico":"#f2a541","Polimento":"#37b87f",
            "Prova":"#ee6c4d","Recuperação":"#8fa6ad"}

def _macro():
    import importlib, sys as _sys
    _g="/Users/andresantos/gerador-treinos"       # na nuvem vem uma cópia do macro.py junto
    if os.path.isdir(_g) and _g not in _sys.path:
        _sys.path.insert(0, _g)
    return importlib.import_module("macro")

def _historico_db(con, aid, ref=None):
    """km por semana (4, 2 e 8 semanas) e maior longo pelo banco, para o ponto de partida."""
    ref=ref or dt.date.today()
    lo=(ref-dt.timedelta(days=56)).isoformat()
    rows=con.execute("""SELECT date, dist_km FROM treinos WHERE atleta_id=? AND kind='run'
                        AND type='completed' AND date>=? AND date<=? AND dist_km>0""",
                     (aid, lo, ref.isoformat())).fetchall()
    def soma(d): return sum(km for x,km in rows if (ref-dt.date.fromisoformat(x)).days<=d)
    return {"km_semana": round(soma(28)/4.0,1), "km_2sem": round(soma(14)/2.0,1),
            "km_8sem": round(soma(56)/8.0,1),
            "maior_longo": round(max((km for _,km in rows), default=0),1)}

def _objetivo_por_nome(nome):
    n=(nome or "").lower()
    if any(k in n for k in ("42","marat")) and "meia" not in n and "half" not in n: return "42k"
    if any(k in n for k in ("21","meia","half")): return "21k"
    if "10" in n: return "10k"
    if "5k" in n or "5 k" in n: return "5k"
    return None

def _gerar_atp(inicio, prova, km_ini, km_pico, h_pico, fim=None, objetivo=None, longo_ini=None):
    """Semanas do ciclo pelo macrociclo do objetivo (o mesmo do Gerador de Treinos):
    Base → Específico (rampa 3:1 com semana leve) → Polimento → Prova, com longo e
    sessões-chave por semana. `fim` estende o ciclo se houver prova depois da A."""
    m=_macro()
    ratio=(h_pico/km_pico) if (km_pico and h_pico and h_pico>0) else None
    rows=[]
    for r in m.gerar_atp(objetivo, inicio, prova, km_ini, km_pico, longo_ini, fim=fim):
        rows.append({"idx":r["idx"], "inicio":dt.date.fromisoformat(r["inicio"]), "fase":r["fase"],
                     "km":r["km"], "horas":(round(r["km"]*ratio,1) if ratio else None),
                     "obs":r["obs"], "longo":r["longo"]})
    return rows

def page_periodizacao(month):
    hero("Periodização", "Ciclo de prova por km e horas semanais — estilo ATP, planejado × realizado", "ATP do Lab")
    import db as _db
    con=_db.get_conn(); _db.init_db(con)
    ath=con.execute("SELECT id,nome FROM atletas WHERE ativo=1 ORDER BY nome COLLATE NOCASE").fetchall()
    if not ath: st.info("Sem atletas no banco ainda."); con.close(); return
    id_by={n:i for i,n in ath}
    sel=st.selectbox("Atleta", list(id_by.keys()), key="atp_ath")
    aid=id_by[sel]

    planos=con.execute("""SELECT id,nome,prova_data,inicio FROM periodizacao
                          WHERE atleta_id=? ORDER BY prova_data DESC""",(aid,)).fetchall()
    def _plabel(p):
        return f'{p[1]} · prova {dt.date.fromisoformat(p[2]).strftime("%d/%m/%y")}'
    _labels=["➕ Criar novo ciclo"]+[_plabel(p) for p in planos]
    # plano recém-criado/excluído: ajusta a seleção ANTES de instanciar o widget
    _novo=st.session_state.pop("_atp_novo", None)
    _idx=1 if planos else 0                      # abre no ciclo mais recente do atleta
    if _novo is not None:
        st.session_state.pop("atp_plano", None)
        _idx=0
        for i,p in enumerate(planos):
            if p[0]==_novo: _idx=i+1; break
    if st.session_state.get("atp_plano") not in _labels:
        st.session_state.pop("atp_plano", None)
    escolha=st.selectbox("Plano", _labels, index=_idx, key="atp_plano")

    # ---------- criar novo ----------
    if escolha=="➕ Criar novo ciclo":
        evs=con.execute("SELECT date,nome FROM provas WHERE atleta_id=? AND date>=? ORDER BY date",
                        (aid, dt.date.today().isoformat())).fetchall()
        c=st.columns([2.6,1.4])
        nome=c[0].text_input("Nome do ciclo", value=(evs[0][1] if evs else "Ciclo de prova"), key="atp_nome")
        ini=c[1].date_input("Início do ciclo", value=dt.date.today(), format="DD/MM/YYYY", key="atp_ini")
        sect("Provas do ciclo · a prova A define o fim da periodização (B e C entram como marcos)")
        _pdf0=pd.DataFrame([{"Data":dt.date.fromisoformat(e[0]),"Nome":e[1],
                             "Prioridade":("A" if j==0 else "B")} for j,e in enumerate(evs)] or
                           [{"Data":dt.date.today()+dt.timedelta(days=84),"Nome":"Prova alvo","Prioridade":"A"}])
        pedit=st.data_editor(_pdf0, hide_index=True, num_rows="dynamic", width="stretch", key="atp_provas_new",
            column_config={
                "Data": st.column_config.DateColumn(format="DD/MM/YYYY", required=True),
                "Nome": st.column_config.TextColumn(required=True),
                "Prioridade": st.column_config.SelectboxColumn(options=["A","B","C"], required=True),
            })
        provas=[(pd.Timestamp(r["Data"]).date(), str(r["Nome"] or "Prova").strip() or "Prova",
                 (str(r["Prioridade"]) if str(r["Prioridade"]) in ("A","B","C") else "C"))
                for _,r in pedit.iterrows() if pd.notna(r["Data"])]
        pa=[p for p in provas if p[2]=="A"]
        # ponto de partida pelo histórico do banco + macrociclo do objetivo (mesmo do gerador)
        _m=_macro(); _hist=_historico_db(con, aid)
        _obj_padrao=(_objetivo_por_nome(pa[0][1]) if pa else None) or "10k"
        _objs=["5k","10k","21k","42k"]
        cobj=st.columns([1.2,4.8])
        objetivo=cobj[0].selectbox("Objetivo", _objs, index=_objs.index(_obj_padrao),
                                   format_func=lambda o:o.replace("k"," km"), key="atp_obj")
        _build=None
        if pa:
            _pd=max(p[0] for p in pa)
            _nn=int(((_pd-dt.timedelta(days=_pd.weekday()))-(ini-dt.timedelta(days=ini.weekday()))).days/7)+1
            _build=max(_nn-_m.MACROS[objetivo]["taper"]-1,1)
        _pp=_m.ponto_de_partida(_hist, objetivo, _build)
        if st.session_state.get("atp_pp_key")!=(aid, objetivo, _build):
            st.session_state["atp_pp_key"]=(aid, objetivo, _build)
            st.session_state["atp_ki"]=int(_pp["km_ini"]); st.session_state["atp_kp"]=int(_pp["km_pico"])
        cobj[1].caption(f"Ponto de partida pelo histórico: {_pp['motivo']}. Longo de {_pp['longo_ini']:g} até "
                        f"{min(_pp['longo_max'], round(_pp['km_pico']*_m.MACROS[objetivo]['frac_longo']))} km · "
                        f"ciclo ideal de {_pp['semanas_ideal']} semanas para {objetivo.replace('k',' km')}.")
        c2=st.columns([1.2,1.2,1.2,2.4])
        km_ini=c2[0].number_input("Km/sem inicial", 5, 200, step=1, key="atp_ki")
        km_pico=c2[1].number_input("Km/sem no pico", 10, 250, step=1, key="atp_kp")
        h_pico=c2[2].number_input("Horas/sem no pico (opcional)", 0.0, 25.0, 0.0, 0.5, key="atp_hp",
                                  help="Deixe 0 para planejar só por quilômetros.")
        if not pa:
            c2[3].caption("Marque pelo menos uma prova como **A** para gerar o ciclo.")
        else:
            pdata=max(p[0] for p in pa); fim=max(p[0] for p in provas)
            _n=max(int(((fim-dt.timedelta(days=fim.weekday()))-(ini-dt.timedelta(days=ini.weekday()))).days/7)+1,3)
            _ip=int(((pdata-dt.timedelta(days=pdata.weekday()))-(ini-dt.timedelta(days=ini.weekday()))).days/7)
            _tp=min(_m.MACROS[objetivo]["taper"], max(1,_ip-3))
            _aviso=(f" Curto para {objetivo.replace('k',' km')}: o ideal seria {_m.MACROS[objetivo]['semanas']} semanas."
                    if _ip+1 < _m.MACROS[objetivo]["semanas"]-2 else "")
            c2[3].caption(f"→ {_n} semanas até {pdata.strftime('%d/%m')} (prova A) · semana leve a cada 4 · "
                          f"polimento de {_tp} semana(s) · sessões-chave e longo por semana na observação.{_aviso}")
        if st.button("Gerar ciclo", type="primary", key="atp_gera", disabled=not pa):
            rows=_gerar_atp(ini, pdata, km_ini, km_pico, h_pico, fim=fim, objetivo=objetivo,
                            longo_ini=_pp["longo_ini"])
            _by_seg={r["inicio"].isoformat(): r for r in rows}
            for d0,nm,pr in provas:            # marca cada prova na semana em que cai
                wseg=(d0-dt.timedelta(days=d0.weekday())).isoformat()
                r=_by_seg.get(wseg)
                if r is None: continue
                tag=f'🏁 {pr} · {nm} {d0.strftime("%d/%m")}'
                r["obs"]=(r["obs"]+" · "+tag).strip(" ·") if r["obs"] else tag
            cur=con.execute("""INSERT INTO periodizacao(atleta_id,nome,prova_data,inicio,criado)
                               VALUES(?,?,?,?,?)""",
                            (aid, nome.strip() or "Ciclo", pdata.isoformat(),
                             rows[0]["inicio"].isoformat(), dt.date.today().isoformat()))
            pid=cur.lastrowid
            con.executemany("""INSERT INTO periodizacao_semanas(plano_id,idx,inicio,fase,km,horas,obs,longo_km)
                               VALUES(?,?,?,?,?,?,?,?)""",
                            [(pid,r["idx"],r["inicio"].isoformat(),r["fase"],r["km"],r["horas"],r["obs"],r["longo"]) for r in rows])
            con.executemany("""INSERT OR IGNORE INTO periodizacao_provas(plano_id,date,nome,prio)
                               VALUES(?,?,?,?)""",
                            [(pid,d0.isoformat(),nm,pr) for d0,nm,pr in provas])
            con.commit(); con.close()
            st.session_state["_atp_novo"]=pid
            st.toast("Ciclo gerado! Ajuste as semanas e os longos à vontade.", icon="✅"); st.rerun()
        con.close(); return

    # ---------- plano existente ----------
    pid, pnome, pdata_s, pini_s = planos[[_plabel(p) for p in planos].index(escolha)]
    pdata=dt.date.fromisoformat(pdata_s)
    sem=con.execute("""SELECT idx,inicio,fase,km,horas,obs,longo_km FROM periodizacao_semanas
                       WHERE plano_id=? ORDER BY idx""",(pid,)).fetchall()
    pvs=con.execute("""SELECT date,nome,prio FROM periodizacao_provas
                       WHERE plano_id=? ORDER BY prio,date""",(pid,)).fetchall()
    if not pvs: pvs=[(pdata_s,pnome,"A")]
    prova_por_seg={}
    for d0,nm,pr in pvs:
        dd=dt.date.fromisoformat(d0); wseg=(dd-dt.timedelta(days=dd.weekday())).isoformat()
        tag=f'{pr} · {nm[:22]} {dd.strftime("%d/%m")}'
        prova_por_seg[wseg]=(prova_por_seg[wseg]+"  |  "+tag) if wseg in prova_por_seg else tag
    hoje=dt.date.today()
    dias=(pdata-hoje).days
    tot_km=sum(x[3] or 0 for x in sem); pico=max((x[3] or 0) for x in sem) if sem else 0
    prova_seg_a=pdata-dt.timedelta(days=pdata.weekday())

    st.caption("  ·  ".join(f'🏁 **{pr}** {nm} — {dt.date.fromisoformat(d0).strftime("%d/%m/%y")}'
                            for d0,nm,pr in pvs))
    k=st.columns(5)
    k[0].metric("Prova A", pdata.strftime("%d/%m/%y"), (f"em {dias}d" if dias>=0 else "realizada"), delta_color="off")
    k[1].metric("Semanas", len(sem))
    k[2].metric("Km do ciclo", f"{tot_km:.0f}")
    k[3].metric("Semana pico", f"{pico:.0f} km")
    # realizado por semana (corrida, do banco)
    real={}
    for d0,kmr,hr_ in con.execute("""SELECT date, dist_km, dur_h FROM treinos
             WHERE atleta_id=? AND type='completed' AND kind='run' AND date>=? AND date<=?""",
             (aid, pini_s, pdata.isoformat())):
        dd=dt.date.fromisoformat(d0); wseg=(dd-dt.timedelta(days=dd.weekday())).isoformat()
        a=real.setdefault(wseg,{"km":0.0,"h":0.0}); a["km"]+=kmr or 0; a["h"]+=hr_ or 0
    plan_ate=sum((x[3] or 0) for x in sem if dt.date.fromisoformat(x[1])+dt.timedelta(days=6)<hoje)
    real_ate=sum(v["km"] for s,v in real.items() if dt.date.fromisoformat(s)+dt.timedelta(days=6)<hoje)
    k[4].metric("Cumprimento", f"{(real_ate/plan_ate*100):.0f}%" if plan_ate else "–",
                f"{real_ate:.0f}/{plan_ate:.0f} km", delta_color="off")

    # gráfico planejado × realizado
    cdf=pd.DataFrame([{"Semana":dt.date.fromisoformat(x[1]).strftime("%d/%m"),
                       "Fase":x[2],"Planejado":x[3] or 0,
                       "Longo":x[6],
                       "Prova":prova_por_seg.get(x[1],""),
                       "Realizado":real.get(x[1],{}).get("km")} for x in sem])
    barras=(alt.Chart(cdf).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=22, opacity=.85)
        .encode(x=alt.X("Semana:N", sort=None, axis=_axis_x()),
                y=alt.Y("Planejado:Q", title=None, axis=_axis_y()),
                color=alt.Color("Fase:N", scale=alt.Scale(domain=list(CORES_FASE), range=list(CORES_FASE.values())),
                                legend=alt.Legend(title=None, orient="top", labelColor=P["text"])),
                tooltip=["Semana","Fase",alt.Tooltip("Planejado:Q",format=".0f"),
                         alt.Tooltip("Longo:Q",format=".0f"),
                         alt.Tooltip("Realizado:Q",format=".0f"),"Prova"]))
    rdf=cdf.dropna(subset=["Realizado"])
    linha=(alt.Chart(rdf).mark_line(point={"size":55,"filled":True}, color=P["fcline"], strokeWidth=2.2)
        .encode(x=alt.X("Semana:N", sort=None), y="Realizado:Q",
                tooltip=["Semana",alt.Tooltip("Realizado:Q",format=".0f")]))
    pfd=cdf[cdf["Prova"]!=""].assign(Y=pico*1.08)
    flags=(alt.Chart(pfd).mark_text(text="🏁", size=15, dy=-2)
        .encode(x=alt.X("Semana:N", sort=None), y=alt.Y("Y:Q"), tooltip=["Semana","Prova"]))
    sect("Km por semana · barras = plano (cor da fase) · linha = realizado · 🏁 = prova")
    st.altair_chart((barras+linha+flags).properties(height=280, background="rgba(0,0,0,0)")
                    .configure_view(strokeWidth=0), width="stretch", theme=None)

    # editor de semanas
    def _falta(ini_s):
        w=int((prova_seg_a-dt.date.fromisoformat(ini_s)).days/7)
        return "prova" if w==0 else (f"{w} sem" if w>0 else f"+{-w} sem")
    sect("Planilha do ciclo · edite e salve · Longo = distância do longão da semana")
    edf=pd.DataFrame([{"Sem":x[0], "Início":dt.date.fromisoformat(x[1]).strftime("%d/%m"),
                       "p/ prova A":_falta(x[1]),
                       "Fase":x[2], "Km":float(x[3] or 0),
                       "Longo":(float(x[6]) if x[6] is not None else None),
                       "Horas":(float(x[4]) if x[4] is not None else None),
                       "Obs":x[5] or "",
                       "Prova":prova_por_seg.get(x[1],""),
                       "Real km":round(real.get(x[1],{}).get("km",0)) or None} for x in sem])
    ed=st.data_editor(edf, hide_index=True, width="stretch", key=f"atp_ed_{pid}",
        disabled=["Sem","Início","p/ prova A","Prova","Real km"],
        column_config={
            "Fase": st.column_config.SelectboxColumn(options=FASES_ATP, required=True),
            "Km": st.column_config.NumberColumn(min_value=0, max_value=300, step=1, format="%.0f"),
            "Longo": st.column_config.NumberColumn(min_value=0.0, max_value=60.0, step=1.0, format="%.0f",
                                                   help="Distância do longo da semana (km)"),
            "Horas": st.column_config.NumberColumn(min_value=0.0, max_value=30.0, step=0.5, format="%.1f"),
        })
    b=st.columns([1.15,1.35,1.5,2.2])
    if b[0].button("💾 Salvar plano", type="primary", key=f"atp_save_{pid}"):
        for (idx,ini_s,*_), (_,row) in zip(sem, ed.iterrows()):
            con.execute("""UPDATE periodizacao_semanas SET fase=?, km=?, horas=?, obs=?, longo_km=?
                           WHERE plano_id=? AND idx=?""",
                        (row["Fase"], float(row["Km"] or 0),
                         (float(row["Horas"]) if pd.notna(row["Horas"]) and row["Horas"] not in ("",None) else None),
                         str(row["Obs"] or ""),
                         (float(row["Longo"]) if pd.notna(row["Longo"]) and row["Longo"] not in ("",None) else None),
                         pid, idx))
        con.commit(); st.toast("Plano salvo!", icon="💾"); st.rerun()
    # provas do ciclo (A/B/C)
    with st.expander("🏁 Provas do ciclo (A/B/C)"):
        pvdf=pd.DataFrame([{"Data":dt.date.fromisoformat(d0),"Nome":nm,"Prioridade":pr} for d0,nm,pr in pvs])
        pved=st.data_editor(pvdf, hide_index=True, num_rows="dynamic", width="stretch", key=f"atp_pv_{pid}",
            column_config={
                "Data": st.column_config.DateColumn(format="DD/MM/YYYY", required=True),
                "Nome": st.column_config.TextColumn(required=True),
                "Prioridade": st.column_config.SelectboxColumn(options=["A","B","C"], required=True),
            })
        if st.button("💾 Salvar provas", key=f"atp_pv_save_{pid}"):
            novas=[(pd.Timestamp(r["Data"]).date(), str(r["Nome"] or "Prova").strip() or "Prova",
                    (str(r["Prioridade"]) if str(r["Prioridade"]) in ("A","B","C") else "C"))
                   for _,r in pved.iterrows() if pd.notna(r["Data"])]
            if not any(p[2]=="A" for p in novas):
                st.warning("Marque pelo menos uma prova como A.")
            else:
                con.execute("DELETE FROM periodizacao_provas WHERE plano_id=?", (pid,))
                con.executemany("""INSERT OR IGNORE INTO periodizacao_provas(plano_id,date,nome,prio)
                                   VALUES(?,?,?,?)""",
                                [(pid,d0.isoformat(),nm,pr) for d0,nm,pr in novas])
                nova_a=max(p[0] for p in novas if p[2]=="A")
                con.execute("UPDATE periodizacao SET prova_data=? WHERE id=?", (nova_a.isoformat(), pid))
                con.commit(); st.toast("Provas salvas!", icon="🏁"); st.rerun()
        st.caption("Alterar a prova A não regera as semanas — ajuste a planilha acima se o ciclo mudar de tamanho.")
    # --- PDF do ciclo estruturado ---
    _pdfp=os.path.join(BASE,"saida","periodizacao",
                       f'{slug(sel)}_{slug(pnome)}_{pdata.strftime("%Y-%m-%d")}.pdf')
    if b[1].button("PDF do ciclo", key=f"atp_pdf_{pid}"):
        try:
            _pa=[(d0,nm) for d0,nm,pr in pvs if pr=="A" and d0==pdata.isoformat()]
            _dados={"atleta":sel, "ciclo":pnome, "prova_data":pdata.isoformat(),
                    "prova_nome":(_pa[0][1] if _pa else ""),
                    "provas":[{"date":d0,"nome":nm,"prio":pr} for d0,nm,pr in pvs],
                    "semanas":[{"idx":x[0],"inicio":x[1],"fase":x[2],
                                "km":x[3],"horas":x[4],"obs":x[5],"longo":x[6]} for x in sem],
                    "realizado":{k:v["km"] for k,v in real.items() if v["km"]>0}}
            pm.pdf_periodizacao(_dados, os.path.relpath(_pdfp, BASE))
            st.toast("PDF do ciclo gerado!", icon="📄")
        except Exception as e:
            st.error(f"Falhou ao gerar o PDF: {e}")
    if pdf_local(_pdfp):
        with open(_pdfp,"rb") as fh:
            b[2].download_button("Baixar PDF", fh.read(), file_name=os.path.basename(_pdfp),
                                 mime="application/pdf", key=f"atp_dl_{pid}")
    _del=st.checkbox("confirmar exclusão do ciclo", key=f"atp_delc_{pid}")
    if st.button("Excluir ciclo", key=f"atp_del_{pid}", disabled=not _del):
        con.execute("DELETE FROM periodizacao_semanas WHERE plano_id=?", (pid,))
        con.execute("DELETE FROM periodizacao WHERE id=?", (pid,))
        con.commit(); con.close()
        st.session_state["_atp_novo"]=-1
        st.toast("Ciclo excluído."); st.rerun()
    b[3].caption("Semana leve a cada 4 · realizado vem da coleta diária (corrida).")
    if pdf_local(_pdfp):
        _png=pdf_preview_png(_pdfp, os.path.getmtime(_pdfp))
        if _png: st.image(_png, width="stretch")
    con.close()

@st.cache_data(show_spinner=False, ttl=600)
def metricas_serie(aid, days, day_iso):
    """Série diária de HRV / sono / FC repouso do banco (últimos N dias)."""
    import db as _db
    con=_db.get_conn(); _db.init_db(con)
    lo=(dt.date.fromisoformat(day_iso)-dt.timedelta(days=days)).isoformat()
    df=pd.read_sql("""SELECT date, hrv, sono_h, fc_rep FROM metricas_diarias
                      WHERE atleta_id=? AND date>=? ORDER BY date""", con, params=(str(aid), lo))
    con.close()
    if len(df):
        df["date"]=pd.to_datetime(df["date"])
        for c in ("hrv","sono_h","fc_rep"):
            df[c+"_m7"]=df[c].rolling(7, min_periods=3).mean()
    return df

def trend_chart(df, col, cor, titulo_y, ref=None, h=220, fmt=".0f", banda=None):
    """Pontos diários + média móvel 7d + linha da média pessoal (ref) + banda opcional."""
    d=df.dropna(subset=[col])
    if d.empty: return None
    xax=alt.X("date:T", title=None, axis=alt.Axis(format="%d/%m", labelColor=P["ax"],
              tickColor=P["line"], domainColor=P["line"], grid=False, labelAngle=0, labelFontSize=10))
    yax=alt.Y(f"{col}:Q", title=None, scale=alt.Scale(zero=False),
              axis=alt.Axis(labelColor=P["ax"], gridColor=P["grid"], domainOpacity=0, tickOpacity=0, labelFontSize=10))
    base=alt.Chart(d).encode(x=xax)
    layers=[]
    if banda:
        bd=pd.DataFrame({"lo":[banda[0]],"hi":[banda[1]]})
        layers.append(alt.Chart(bd).mark_rect(color=cor, opacity=0.08).encode(y="lo:Q", y2="hi:Q"))
    pts=base.mark_circle(size=34, color=cor, opacity=0.45).encode(
        y=yax, tooltip=[alt.Tooltip("date:T",title="Dia",format="%d/%m"),
                        alt.Tooltip(f"{col}:Q",title=titulo_y,format=fmt)])
    m7=base.mark_line(color=cor, strokeWidth=2.6).encode(
        y=alt.Y(f"{col}_m7:Q", scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip(f"{col}_m7:Q",title="média 7d",format=fmt)])
    layers+=[pts, m7]
    if ref is not None:
        rl=alt.Chart(pd.DataFrame({"y":[ref]})).mark_rule(color=P["mut"], strokeDash=[4,4], strokeWidth=1.2).encode(y="y:Q")
        layers.append(rl)
    return alt.layer(*layers).properties(height=h, background="rgba(0,0,0,0)").configure_view(strokeWidth=0)

@st.cache_data(show_spinner=False, ttl=900)
def liga_cached(month, day_iso, modo="geral"):
    from ranking import liga
    return liga(month, dt.date.fromisoformat(day_iso), modo)

@st.cache_data(show_spinner=False, ttl=900)
def liga_semana_cached(wk_iso, day_iso, modo="geral"):
    from ranking import liga_semana
    return liga_semana(dt.date.fromisoformat(wk_iso), dt.date.fromisoformat(day_iso), modo)

def page_liga(month):
    hero("Liga AS", "Competição de comprometimento — disciplina vale mais que velocidade", "Ranking")
    pc0=st.columns([1.6,2.2,2.2])
    modo=pc0[0].radio("Período", ["Semanal","📆 Mensal"], horizontal=True,
                      label_visibility="collapsed", key="liga_modo")
    _mod=pc0[2].radio("Modalidade", ["🏅 Geral","Corrida","Força"], horizontal=True,
                      label_visibility="collapsed", key="liga_modal")
    _modo_key={"🏅 Geral":"geral","Corrida":"corrida","Força":"forca"}[_mod]
    _hj=dt.date.today(); _mon=_hj-dt.timedelta(days=_hj.weekday())
    if modo.startswith("🗓️"):
        _wops=[_mon-dt.timedelta(days=7*i) for i in range(8)]
        def _wl(w):
            e=w+dt.timedelta(days=6)
            return f'{w.strftime("%d/%m")} – {e.strftime("%d/%m")}' + (" · atual" if w==_mon else "")
        wk=pc0[1].selectbox("Semana", _wops, format_func=_wl, key="liga_wk",
                            label_visibility="collapsed")
        rows=liga_semana_cached(wk.isoformat(), _hj.isoformat(), _modo_key)
        _rotulo=f"Semana {_wl(wk)}"
        _qual_txt="mínimo 3 treinos na semana"
        _const_nome="Presença"
        _formula=("**Fórmula (semana):** Disciplina (35%) = % dos planejados da semana realizados · "
                  "Presença (25%) = dias com treino (5+ = 100) · Evolução (25%) = pace da semana vs suas "
                  "4 semanas anteriores · Ritmo (15%) = percentil de pace.")
    else:
        rows=liga_cached(month, _hj.isoformat(), _modo_key)
        _rotulo=f'{MESES[int(month[5:7])-1].capitalize()} {month[:4]}'
        _qual_txt="mínimo 6 treinos e 2 semanas ativas"
        _const_nome="Constância"
        _formula=("**Fórmula (mês):** Disciplina (35%) = % dos treinos planejados realizados · Constância (25%) = "
                  "% das semanas com 3+ treinos · Evolução (25%) = pace do mês vs seus 2 meses anteriores "
                  "(melhorou 2% = 100) · Ritmo (15%) = percentil de pace.")
    if not rows:
        st.info("Sem treinos neste período ainda."); return
    q=[r for r in rows if r["qualificado"]]
    nq=[r for r in rows if not r["qualificado"]]

    # pódio
    if len(q)>=3:
        med=["🥇","🥈","🥉"]
        pc=st.columns(3)
        ordem=[1,0,2] if len(q)>=3 else range(len(q))
        for pos,col in zip([0,1,2],[pc[1],pc[0],pc[2]]):
            r=q[pos]
            col.markdown(f'''<div style="text-align:center;padding:{'26px' if pos==0 else '18px'} 12px;
              background:{P["metric"]};border:1px solid {'rgba(242,165,65,.5)' if pos==0 else P["gbrd"]};
              border-radius:20px;backdrop-filter:blur(12px);{'box-shadow:0 0 24px rgba(242,165,65,.15);' if pos==0 else ''}">
              <div style="font-size:{'2.4rem' if pos==0 else '1.8rem'}">{med[pos]}</div>
              <div style="font-weight:800;font-size:{'1.15rem' if pos==0 else '1rem'};color:{P["text"]}">{r["name"]}</div>
              <div style="font-size:{'2rem' if pos==0 else '1.5rem'};font-weight:800;color:#f2a541">{r["total"]:.1f}</div>
              <div style="font-size:.68rem;color:{P["mut"]};text-transform:uppercase;letter-spacing:.5px">
                {r["sess"]} treinos · {(str(r.get("km_sem",0))+" km/sem") if _modo_key=="corrida" else (str(r["km"])+" km")}</div></div>''', unsafe_allow_html=True)

    # líderes por pilar
    def _lead(k, emoji, nome_p):
        cand=[r for r in q if r.get(k) is not None]
        if not cand: return f"{emoji} {nome_p}: –"
        b=max(cand, key=lambda r:r[k])
        return f'{emoji} **{nome_p}**: {b["name"].split()[0]} ({b[k]:.0f})'
    _leads=[_lead("disciplina","🎯","Disciplina"), _lead("constancia","",_const_nome)]
    if _modo_key=="corrida":
        _leads+=[_lead("evolucao","📈","Evolução"), _lead("volume","📏","Volume")]
    elif _modo_key!="forca":
        _leads+=[_lead("evolucao","📈","Evolução"), _lead("ritmo","⚡","Ritmo")]
    st.markdown(" &nbsp;·&nbsp; ".join(_leads))
    st.divider()

    # tabela geral
    sect(f"Classificação · {_rotulo} · {len(q)} qualificados")
    def _f(v): return f"{v:.0f}" if v is not None else "–"
    if _modo_key=="forca":
        dfq=pd.DataFrame([{ "#":i+1, "Atleta":r["name"], "Total":f'{r["total"]:.1f}',
            "🎯 Disc.":_f(r["disciplina"]), _const_nome:_f(r["constancia"]),
            "Sessões":r["sess"]} for i,r in enumerate(q)])
        html_table(dfq, num={"#","Total","🎯 Disc.",_const_nome,"Sessões"})
    elif _modo_key=="corrida":
        _kmlab="Km/sem" if modo.startswith("📆") else "Km"
        dfq=pd.DataFrame([{ "#":i+1, "Atleta":r["name"], "Total":f'{r["total"]:.1f}',
            "🎯 Disc.":_f(r["disciplina"]), _const_nome:_f(r["constancia"]),
            "📈 Evol.":_f(r["evolucao"]), "📏 Volume":_f(r.get("volume")),
            _kmlab:f'{r.get("km_sem",0):.1f}', "Treinos":r["sess"],
            "Pace":fmt_pace(r["pace"]) if r["pace"] else "–"} for i,r in enumerate(q)])
        html_table(dfq, num={"#","Total","🎯 Disc.",_const_nome,"📈 Evol.","📏 Volume",_kmlab,"Treinos","Pace"})
    else:
        dfq=pd.DataFrame([{ "#":i+1, "Atleta":r["name"], "Total":f'{r["total"]:.1f}',
            "🎯 Disc.":_f(r["disciplina"]), _const_nome:_f(r["constancia"]),
            "📈 Evol.":_f(r["evolucao"]), "⚡ Ritmo":_f(r["ritmo"]),
            "Treinos":r["sess"], "Km":r["km"],
            "Pace":fmt_pace(r["pace"]) if r["pace"] else "–"} for i,r in enumerate(q)])
        html_table(dfq, num={"#","Total","🎯 Disc.",_const_nome,"📈 Evol.","⚡ Ritmo","Treinos","Km","Pace"})
    if nq:
        with st.expander(f"Ainda não qualificados ({len(nq)}) — {_qual_txt}"):
            html_table(pd.DataFrame([{"Atleta":r["name"],"Treinos":r["sess"],"Km":r["km"],
                                      "Total parcial":f'{r["total"]:.1f}'} for r in nq]),
                       num={"Treinos","Km","Total parcial"})
    if _modo_key=="corrida":
        _vlab="km por semana" if modo.startswith("📆") else "km na semana"
        _formula=("**Fórmula (corrida):** Disciplina (30%) = % das corridas planejadas realizadas · "
                  +_const_nome.replace("📅 ","")+" (25%) · Evolução (20%) = pace vs seu próprio histórico · "
                  "**Volume (25%) = percentil de "+_vlab+"**.")
    elif _modo_key=="forca":
        _formula=("**Fórmula (força):** Disciplina (50%) = % dos treinos de força planejados realizados · "
                  +_const_nome.replace("📅 ","")+" (50%) = frequência de força no período.")
    st.caption(_formula + " Pilar sem dados não conta (pesos redistribuídos).")

def page_perdidos(month):
    hero("Treinos Perdidos", "Quem tinha treino planejado e não realizou", "Acompanhamento")
    hoje=dt.date.today()
    dias=[hoje-dt.timedelta(days=i) for i in range(1,15)]     # ontem até 14 dias atrás
    DLBL=["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
    def _dlbl(x):
        lab=f'{DLBL[x.weekday()]} {x.strftime("%d/%m")}'
        return lab+" · ontem" if x==hoje-dt.timedelta(days=1) else lab
    dia=st.selectbox("Dia", dias, format_func=_dlbl)
    rep=absent_report(dia.isoformat())
    if rep is None:
        st.info("Sem dados coletados para esse mês ainda — rode **Atualizar todos** na Visão da Equipe."); return

    n=len(rep["faltas"])
    c=st.columns(3)
    c[0].metric("Não treinaram (tinham plano)", n)
    c[1].metric("Pularam o plano mas treinaram", len(rep["fez_outro"]))
    c[2].metric("Treinaram no dia", rep["treinaram"])

    if n:
        sect(f'❌ Faltas de {_dlbl(dia)}')
        html_table(pd.DataFrame([{"Atleta":a,"Treino planejado":t} for a,t in rep["faltas"]]))
    else:
        st.success("✅ Ninguém faltou — todos que tinham treino planejado realizaram.")
    if rep["fez_outro"]:
        sect("🔁 Pularam o planejado, mas fizeram outro treino")
        html_table(pd.DataFrame([{"Atleta":a,"Treino que estava planejado":t} for a,t in rep["fez_outro"]]))

    # resumo dos últimos 7 dias: quem mais faltou
    st.divider()
    sect("📉 Últimos 7 dias · quem mais faltou")
    cnt={}
    for i in range(1,8):
        r7=absent_report((hoje-dt.timedelta(days=i)).isoformat())
        if not r7: continue
        for a,_t in r7["faltas"]: cnt[a]=cnt.get(a,0)+1
    if cnt:
        rank=sorted(cnt.items(), key=lambda x:(-x[1],x[0].lower()))
        html_table(pd.DataFrame([{"Atleta":a,"Faltas na semana":f} for a,f in rank]), num={"Faltas na semana"})
        st.caption("Contando só dias com treino planejado e nada realizado. Dados da coleta diária das 14h.")
    else:
        st.caption("Nenhuma falta nos últimos 7 dias 🎉")


# ---------- HRV da equipe ----------
HRV_VERM="#cf4a5a"; HRV_AMAR="#f2a541"; HRV_VERD="#37b87f"

@st.cache_data(show_spinner=False, ttl=600)
def hrv_equipe(day_iso, dias=60):
    """Séries diárias (hrv, fc_rep, sono_h) de todos os atletas nos últimos N dias."""
    import db as _db
    con=_db.get_conn(); _db.init_db(con)
    lo=(dt.date.fromisoformat(day_iso)-dt.timedelta(days=dias)).isoformat()
    df=pd.read_sql("""SELECT m.atleta_id AS aid, a.nome, m.date, m.hrv, m.fc_rep, m.sono_h
                      FROM metricas_diarias m LEFT JOIN atletas a ON a.id=m.atleta_id
                      WHERE m.date>=? AND m.date<=? ORDER BY m.date""", con, params=(lo, day_iso))
    con.close()
    return df

def hrv_resumo(g, hoje):
    """Baseline/limiar/CV de um atleta a partir da série dos últimos 60 dias."""
    h=g.dropna(subset=["hrv"]).copy()
    if len(h)<5: return None
    h["d"]=pd.to_datetime(h["date"]).dt.date
    jan=h[h["d"]>=hoje-dt.timedelta(days=30)]
    base_src=jan if len(jan)>=7 else h
    base=float(base_src["hrv"].mean()); sd=float(base_src["hrv"].std(ddof=0)) if len(base_src)>2 else 0.0
    limiar=max(0.0, base-sd); cv=(sd/base*100) if base else 0.0
    ult=h.iloc[-1]
    def status(v):
        if v is None or pd.isna(v): return None
        return "verm" if v<limiar else ("amar" if v<base else "verd")
    por_dia={r.d:float(r.hrv) for r in h.itertuples()}
    dias30=[hoje-dt.timedelta(days=i) for i in range(29,-1,-1)]
    dias14=dias30[-14:]
    s30=[status(por_dia.get(d)) for d in dias30]
    abaixo30=sum(1 for x in s30 if x=="verm")
    abaixo7=sum(1 for x in s30[-7:] if x=="verm")
    # tendência: média 7d vs baseline
    v7=[por_dia[d] for d in dias30[-7:] if d in por_dia]
    m7=sum(v7)/len(v7) if v7 else None
    alerta=(abaixo7>=2) or (m7 is not None and m7<limiar)
    fc7=g.dropna(subset=["fc_rep"]).tail(7)["fc_rep"].mean() if g["fc_rep"].notna().any() else None
    so7=g.dropna(subset=["sono_h"]).tail(7)["sono_h"].mean() if g["sono_h"].notna().any() else None
    return dict(dia=float(ult["hrv"]), data=ult["d"], base=base, sd=sd, limiar=limiar, cv=cv,
                m7=m7, s30=s30, v30=[por_dia.get(d) for d in dias30], s14=s30[-14:],
                abaixo30=abaixo30, abaixo7=abaixo7, alerta=alerta, fc7=fc7, so7=so7, n=len(h))

def hrv_fmt(v):
    """Valor como o TP mostra: inteiro sem decimal, senão 1 casa."""
    return f"{v:.0f}" if abs(v-round(v))<1e-9 else f"{v:.1f}"

def hrv_chart_svg(r, hoje):
    """Linha dos últimos 30 dias: cada ponto é o valor medido no TP (tooltip com data e valor),
    baseline e limiar tracejados com o valor na ponta."""
    W,H=320,84; padl,padr,padt,padb=6,34,10,10
    vals=[v for v in r["v30"] if v is not None]
    lo=min(vals+[r["limiar"]]); hi=max(vals+[r["base"]])
    if hi-lo<4: hi+=2; lo-=2
    span=hi-lo or 1
    def X(i): return padl+i*(W-padl-padr)/29
    def Y(v): return padt+(hi-v)*(H-padt-padb)/span
    cor={"verm":HRV_VERM,"amar":HRV_AMAR,"verd":HRV_VERD}
    dias=[hoje-dt.timedelta(days=i) for i in range(29,-1,-1)]
    path=""; prev=None; pts=""
    for i,(v,s_) in enumerate(zip(r["v30"],r["s30"])):
        if v is None: prev=None; continue
        x,y=X(i),Y(v)
        path+=("L" if prev is not None else " M")+f"{x:.1f},{y:.1f}"; prev=v
        lab=f'{dias[i].strftime("%d/%m")} · {hrv_fmt(v)} ms'
        tw=len(lab)*5.4+8; tx=min(max(x, tw/2+1), W-tw/2-1)
        rect_y=y-21 if y>24 else y+8
        pts+=(f'<g class="pt"><circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="{cor[s_]}"/>'
              f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="transparent"/>'
              f'<g class="tip"><rect x="{tx-tw/2:.1f}" y="{rect_y:.1f}" width="{tw:.1f}" height="12" rx="3"/>'
              f'<text x="{tx:.1f}" y="{(rect_y+9):.1f}" text-anchor="middle">{lab}</text></g></g>')
    yb,yl=Y(r["base"]),Y(r["limiar"])
    return (f'<svg class="ch" viewBox="0 0 {W} {H}" aria-hidden="true">'
            f'<line x1="{padl}" x2="{W-padr}" y1="{yb:.1f}" y2="{yb:.1f}" stroke="{HRV_VERD}" stroke-width="1" stroke-dasharray="4 3" opacity=".7"/>'
            f'<text class="ax" x="{W-padr+3}" y="{yb+3:.1f}" fill="{HRV_VERD}">{r["base"]:.1f}</text>'
            f'<line x1="{padl}" x2="{W-padr}" y1="{yl:.1f}" y2="{yl:.1f}" stroke="{HRV_VERM}" stroke-width="1" stroke-dasharray="4 3" opacity=".7"/>'
            f'<text class="ax" x="{W-padr+3}" y="{yl+3:.1f}" fill="{HRV_VERM}">{r["limiar"]:.1f}</text>'
            f'<path d="{path}" fill="none" stroke="{P["mut"]}" stroke-width="1.4" opacity=".8"/>{pts}</svg>')

def hrv_card(nome, aid, r):
    av=avatar_bytes(aid)
    avh=(f'<img src="data:image/jpeg;base64,{base64.b64encode(av).decode()}">' if av
         else f'<div class="mono">{initials(nome)}</div>')
    cor={"verm":HRV_VERM,"amar":HRV_AMAR,"verd":HRV_VERD,None:P["grid"]}
    _d14=[dt.date.today()-dt.timedelta(days=i) for i in range(13,-1,-1)]
    pr="".join(f'<i style="background:{cor[x]}" title="{d.strftime("%d/%m")} · {hrv_fmt(v)+" ms" if v is not None else "sem medição"}"></i>'
               for d,x,v in zip(_d14, r["s14"], r["v30"][-14:]))
    dias_sem=(dt.date.today()-r["data"]).days
    upd=f'Última atualização: {r["data"].strftime("%d/%m/%Y")}'+(f' · há {dias_sem}d' if dias_sem>1 else '')
    if r["alerta"]: tag='<span class="tag alerta">Alerta</span>'
    elif r["abaixo30"]==0: tag='<span class="tag ok">Estável</span>'
    else: tag='<span class="tag">Monitorar</span>'
    n=r["abaixo30"]
    if n==0: msg="<b>Nenhum dia</b> abaixo do limiar nos últimos 30 dias — HRV estável."
    elif r["alerta"]: msg=f"<b>{n} de 30</b> dias abaixo do limiar, <b>{r['abaixo7']}</b> na última semana — conferir carga, sono e sinais de fadiga."
    elif n<=2: msg=f"<b>{n} de 30</b> dias abaixo do limiar nos últimos 30 dias — monitorar evolução."
    elif n<=5: msg=f"<b>{n} de 30</b> dias abaixo do limiar nos últimos 30 dias — padrão intermitente, acompanhar de perto."
    else: msg=f"<b>{n} de 30</b> dias abaixo do limiar nos últimos 30 dias — padrão recorrente, revisar o bloco."
    aux=[]
    if r["fc7"] is not None: aux.append(f'FC repouso {r["fc7"]:.0f} bpm')
    if r["so7"] is not None: aux.append(f'sono {r["so7"]:.1f} h')
    auxh=f'<div class="aux">Média 7d · {" · ".join(aux)}</div>' if aux else ""
    cd=HRV_VERD if r["s30"][-1]=="verd" else (HRV_AMAR if r["s30"][-1]=="amar" else HRV_VERM)
    vd=r["v30"][-1]
    cd=cd if vd is not None else P["mut"]
    return (f'<div class="hrvc{" alerta" if r["alerta"] else ""}">'
            f'<div class="top">{avh}<div><div class="nm">{_html.escape(nome)}</div><div class="upd">{upd}</div></div>{tag}</div>'
            f'<div class="kp"><div><b style="color:{cd}">{hrv_fmt(r["dia"])}<span style="font-size:.8rem"> ms</span></b><small>Dia · {r["data"].strftime("%d/%m")}</small></div>'
            f'<div><b>{r["limiar"]:.1f}<span style="font-size:.8rem"> ms</span></b><small>Limiar</small></div>'
            f'<div><b>{r["base"]:.1f}<span style="font-size:.8rem"> ms</span></b><small>Baseline</small></div>'
            f'<div><b style="color:{HRV_AMAR if r["cv"]>=15 else P["text"]}">{r["cv"]:.1f}%</b><small>CV do HRV</small></div></div>'
            f'<div class="lg">HRV · últimos 30 dias · vermelho abaixo do limiar · amarelo até o baseline · verde dentro do baseline</div>'
            f'{hrv_chart_svg(r, dt.date.today())}'
            f'<div class="lg">Prontidão · últimos 14 dias</div><div class="pr">{pr}</div>'
            f'<div class="msg">{msg}</div>{auxh}</div>')

def page_hrv(month):
    hero("HRV da Equipe", "Variabilidade da frequência cardíaca de todos os atletas com métricas no TrainingPeaks", "Recuperação")
    hoje=dt.date.today()
    b=st.columns([1.6,4.4], vertical_alignment="center")
    if b[0].button("Atualizar HRV de hoje", key="hrv_refresh"):
        rc=_run_stream([PYBIN,"refresh_metrics.py","--days","10"], st.empty())
        if rc==0:
            hrv_equipe.clear(); metricas_serie.clear()
            st.success("Métricas dos últimos 10 dias atualizadas, incluindo hoje."); st.rerun()
        else: st.error("A atualização falhou — veja o log acima.")
    b[1].caption("Puxa HRV, FC de repouso e sono dos últimos 10 dias de todos os atletas ativos direto do TrainingPeaks (≈1 min). "
                 "A coleta automática das 14h também atualiza.")
    df=hrv_equipe(hoje.isoformat())
    if df.empty or df["hrv"].notna().sum()==0:
        st.info("Nenhuma métrica de HRV no banco ainda — rode **Atualizar todos** na Visão da Equipe."); return
    res=[]; antigos=[]
    for (aid,nome),g in df.groupby(["aid","nome"], sort=False):
        nome=nome or str(aid)
        r=hrv_resumo(g, hoje)
        if r is None:
            if g["hrv"].notna().any(): antigos.append((nome, int(g["hrv"].notna().sum())))
            continue
        if (hoje-r["data"]).days>14: antigos.append((nome, r["n"])); continue
        res.append((nome, str(aid), r))
    n_alerta=sum(1 for _,_,r in res if r["alerta"])
    n_hoje=sum(1 for _,_,r in res if (hoje-r["data"]).days<=1)
    cv_med=(sum(r["cv"] for _,_,r in res)/len(res)) if res else 0
    c=st.columns(4)
    c[0].metric("Atletas monitorados", len(res))
    c[1].metric("Atualizados nas últimas 24h", n_hoje)
    c[2].metric("Em alerta", n_alerta)
    c[3].metric("CV médio do HRV", f"{cv_med:.1f}%")
    f=st.columns([2.2,1.6,1.2], vertical_alignment="bottom")
    busca=f[0].text_input("Buscar atleta", "", key="hrv_busca").strip().lower()
    ordem=f[1].selectbox("Ordenar por", ["Alerta primeiro","Dias abaixo do limiar","Nome","Última atualização"], key="hrv_ordem")
    so_alerta=f[2].checkbox("Só em alerta", key="hrv_so_alerta")
    itens=[x for x in res if (not busca or busca in x[0].lower()) and (not so_alerta or x[2]["alerta"])]
    if ordem=="Nome": itens.sort(key=lambda x: x[0].lower())
    elif ordem=="Dias abaixo do limiar": itens.sort(key=lambda x: (-x[2]["abaixo30"], -x[2]["abaixo7"], x[0].lower()))
    elif ordem=="Última atualização": itens.sort(key=lambda x: (-x[2]["data"].toordinal(), x[0].lower()))
    else: itens.sort(key=lambda x: (not x[2]["alerta"], -x[2]["abaixo7"], -x[2]["abaixo30"], x[0].lower()))
    if not itens:
        st.caption("Nenhum atleta bate com esse filtro."); return
    st.markdown('<div class="hrvg">'+"".join(hrv_card(n,a,r) for n,a,r in itens)+'</div>', unsafe_allow_html=True)
    st.caption("Baseline = média dos últimos 30 dias · limiar = baseline − 1 desvio-padrão · CV = desvio/baseline. "
               "Alerta = 2+ dias abaixo do limiar na última semana ou média 7d abaixo do limiar. "
               "Dados vêm das métricas diárias do TrainingPeaks (relógio/anel do atleta) na coleta das 14h.")
    if antigos:
        with st.expander(f"Sem HRV recente · {len(antigos)} atleta(s)"):
            st.caption("Com dados antigos (mais de 14 dias) ou menos de 5 dias registrados nos últimos 60 dias.")
            html_table(pd.DataFrame([{"Atleta":n,"Dias com HRV (60d)":k} for n,k in sorted(antigos, key=lambda x:(-x[1],x[0].lower()))]), num={"Dias com HRV (60d)"})


def page_revisao(month):
    hero("Revisão semanal", "O que fazer com cada atleta na semana que começa, pelos dados da semana que fechou", "Regulação")
    import revisao_semanal as rs
    hoje=dt.date.today()
    seg=hoje-dt.timedelta(days=hoje.weekday())
    refs=[seg-dt.timedelta(days=7*i) for i in range(6)]
    def _rl(d):
        ini=d-dt.timedelta(days=7); fim=d-dt.timedelta(days=1)
        return f'{ini:%d/%m} – {fim:%d/%m/%Y}'+(" · semana que fechou" if d==seg else "")
    ref=st.selectbox("Semana avaliada", refs, format_func=_rl, key="rev_ref")
    with st.spinner("Lendo a semana de todos os atletas…"):
        rev=rs.revisar(ref)
    it=sorted(rev["itens"], key=lambda x:(rs.ORDEM.get(x["rec"],9), x["nome"].lower()))
    cont={}
    for x in it: cont[x["rec"]]=cont.get(x["rec"],0)+1
    c=st.columns(5)
    for col,k in zip(c, ["aliviar","recuperar","manter","progredir","sem dados"]):
        col.metric(k.capitalize(), cont.get(k,0))
    st.caption(rs.REGRAS)
    filtro=st.multiselect("Mostrar", ["aliviar","recuperar","manter","progredir","sem dados"],
                          default=["aliviar","recuperar","manter","progredir"], key="rev_filtro")
    linhas=[]
    for x in it:
        if x["rec"] not in filtro: continue
        hrv=x["hrv"]; tsb=x["tsb"]; pr=x["proposta"]
        linhas.append({"Atleta":x["nome"], "Ação":x["rec"],
                       "Aderência":(f'{x["ader"]:.0f}% ({x["feitos"]}/{x["plan"]})' if x["ader"] is not None else "sem plano"),
                       "Km feito":f'{x["km"]:.0f}', "Km plano":(f'{x["km_plano"]:.0f}' if x.get("km_plano") else "–"),
                       "HRV":(("alerta" if hrv["alerta"] else "ok")+f' · {hrv["abaixo7"]}d<{hrv["limiar"]:.0f}' if hrv else "–"),
                       "Forma":(f'{tsb:+.0f}' if tsb is not None else "–"),
                       "Próx. semana":(f'{pr["km_atual"]} → {pr["km_novo"]} km' if pr else (f'{x["prox"]["km"]:.0f} km' if x.get("prox") and x["prox"].get("km") else "–")),
                       "Motivo":"; ".join(x["motivos"])})
    if linhas: html_table(pd.DataFrame(linhas), num={"Km feito","Km plano"})
    else: st.caption("Nenhum atleta nesse filtro.")

    props=[x for x in it if x["proposta"]]
    st.divider()
    sect("Aplicar na periodização")
    if not props:
        st.caption("Nenhuma mudança proposta no plano das próximas semanas. Só atletas com ciclo no Lab recebem proposta de km.")
    else:
        nomes=[f'{x["nome"]} · {x["proposta"]["km_atual"]} → {x["proposta"]["km_novo"]} km ({x["rec"]})' for x in props]
        esc=st.multiselect("Mudanças a aplicar na semana que começa", nomes, default=nomes, key="rev_aplicar")
        st.caption("Grava o novo km e o motivo na semana do ciclo do atleta. Os treinos já publicados no TrainingPeaks não mudam; se quiser, gere a semana de novo no Gerador com o plano atualizado.")
        if st.button(f"Aplicar {len(esc)} mudança(s)", type="primary", disabled=not esc, key="rev_go"):
            ok=0; falhas=[]
            for x,n in zip(props,nomes):
                if n not in esc: continue
                try: rs.aplicar(x["proposta"]["plano_id"], x["proposta"]["inicio"], x["proposta"]["km_novo"], x["proposta"]["obs"]); ok+=1
                except Exception as e: falhas.append(f'{x["nome"]}: {e}')
            if ok: st.success(f"{ok} plano(s) atualizado(s).")
            if falhas: st.warning("Falhou: "+"; ".join(falhas))
    st.divider()
    sect("Reteste de limiar")
    st.caption("O gerador agenda o Teste de limiar 30' a cada 6 a 8 semanas, longe da prova. Aqui você confere os testes feitos: "
               "melhor pace de 30 minutos no arquivo do relógio contra o limiar cadastrado no TrainingPeaks. Nada é gravado nas zonas; a decisão é sua.")
    if st.button("Conferir testes feitos (últimas 12 semanas)", key="rev_retest"):
        _err=None
        with st.spinner("Lendo os testes no TrainingPeaks (baixa o arquivo do relógio de cada um)…"):
            try: itens=pm.retest()
            except Exception as e: itens=[]; _err=str(e)
        if _err: st.error(_err[-400:])
        elif not itens: st.info("Nenhum Teste de limiar concluído nas últimas 12 semanas.")
        else:
            linhas=[]
            for x in itens:
                t=x["teste"]
                linhas.append({"Atleta":x["nome"], "Teste":f'{t["data"][8:10]}/{t["data"][5:7]}',
                               "Pace no teste":(t.get("pace","–")+(" ~" if t.get("aprox") else "")) if t.get("ok") else f'não lido ({t.get("motivo","")})',
                               "FC últ. 20'":(str(t["fc_ult20"]) if t.get("fc_ult20") else "–"),
                               "Cadastrado":x.get("cad_pace") or "–",
                               "Diferença":(f'{x["delta_pct"]:+.1f}% ({x["delta_s_km"]:+d} s/km)' if x.get("delta_pct") is not None else "–"),
                               "Zonas":("velhas, revisar" if x.get("zonas_velhas") else ("ok" if x.get("delta_pct") is not None else "–"))})
            html_table(pd.DataFrame(linhas))
            velhas=[x["nome"] for x in itens if x.get("zonas_velhas")]
            if velhas: st.warning("Limiar mudou mais de 3% em: "+", ".join(velhas)+". Atualize as zonas no TrainingPeaks se concordar com o teste.")
    st.divider()
    sect("Resumo para o WhatsApp")
    st.code(rs.resumo_texto(rev), language=None)

# ---------- roteamento ----------
if not month and not page.startswith("Pipeline"):
    st.info("Nenhum mês coletado. Vá em ⚙️ Pipeline para coletar o primeiro mês.")
elif page.startswith("Visão"): page_equipe(month)
elif page.startswith("Atleta"): page_atleta(month)
elif page.startswith("HRV"): page_hrv(month)
elif page.startswith("Liga"): page_liga(month)
elif page.startswith("Periodização"): page_periodizacao(month)
elif page.startswith("Revisão"): page_revisao(month)
elif page.startswith("Provas"): page_provas(month)
elif page.startswith("Treinos"): page_perdidos(month)
elif page.startswith("Relatórios"): page_pdfs(month)
else: page_pipeline(month)
site_footer()
