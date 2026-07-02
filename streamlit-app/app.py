"""
Oil & Gas Equity Monitor — Streamlit wrapper that renders the original HTML dashboard
pixel-for-pixel inside Streamlit (so it deploys on Community Cloud with a *.streamlit.app URL).

The dashboard fetches live data client-side from FMP's /stable API. Provide the key either:
  • in Streamlit secrets as  FMP_API_KEY = "xxxx"   (auto-used, no prompt), or
  • by pasting it into the key box at the top of the dashboard (stored in the browser).
"""
import json
import pathlib
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Oil & Gas Equity Monitor", layout="wide", page_icon="🛢️")

# hide Streamlit chrome so the embedded dashboard fills the page
st.markdown("""
<style>
#MainMenu {visibility:hidden;}
header[data-testid="stHeader"] {display:none;}
footer {visibility:hidden;}
[data-testid="stAppViewContainer"] > .main .block-container {padding:0rem; max-width:100%;}
[data-testid="stAppViewContainer"] {background:#f6f7f9;}
</style>
""", unsafe_allow_html=True)

key = ""
try:
    key = st.secrets.get("FMP_API_KEY", "")
except Exception:
    key = ""

html = pathlib.Path(__file__).with_name("dashboard.html").read_text(encoding="utf-8")
inject = f"<script>window.__FMPKEY__ = {json.dumps(key or '')};</script>\n"
components.html(inject + html, height=2400, scrolling=True)
