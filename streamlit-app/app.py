"""
EQT Hybrid Strategy — Standalone Streamlit App
Run locally first:  python run_backtest.py
Then deploy:        streamlit run app.py
"""
import streamlit as st
import eqt_hybrid_tab

st.set_page_config(
    page_title="EQT Hybrid Strategy",
    page_icon="⛽",
    layout="wide",
)

eqt_hybrid_tab.render_eqt_hybrid()
