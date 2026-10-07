"""
EQT Hybrid Strategy Tab
-----------------------
Loads a pre-computed JSON produced by run_backtest.py (run locally) and
renders the full dashboard.  No backtest computation happens here — the
server only reads a JSON file and draws charts.

Drop this file and eqt_backtest.json into your Streamlit app:

    tab1, tab2 = st.tabs(["VLO", "EQT Hybrid"])
    with tab2:
        from eqt_hybrid_tab import render_eqt_hybrid
        render_eqt_hybrid(json_path="data/eqt_backtest.json")

Dependencies: streamlit, plotly, pandas, numpy, yfinance
"""

import json
import datetime
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# 1. DATA LOADING  (reads pre-computed JSON)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading EQT backtest data…")
def _load_json(json_path: str) -> dict:
    """Load the pre-computed backtest JSON and reconstruct typed objects."""
    with open(json_path, "r") as f:
        raw = json.load(f)

    # Reconstruct weekly DataFrame with DatetimeIndex
    weekly_df = pd.DataFrame(raw["weekly"])
    weekly_df["date"] = pd.to_datetime(weekly_df["date"])
    weekly_df = weekly_df.set_index("date")

    return {
        "stats":   raw["stats"],
        "current": raw["current"],
        "annual":  raw["annual"],
        "weekly":  weekly_df,
        "daily":   raw.get("daily", []),
        "generated": raw.get("generated", ""),
    }


def _get_live_eqt_price() -> tuple[float | None, str]:
    """Fetch live EQT price via yfinance (best-effort)."""
    try:
        import yfinance as yf
        info = yf.Ticker("EQT").fast_info
        price = getattr(info, "last_price", None)
        if price:
            return round(float(price), 2), datetime.datetime.now().strftime("%H:%M ET")
    except Exception:
        pass
    return None, ""


# ─────────────────────────────────────────────────────────────────────────────
# 2. CHART BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _equity_chart(weekly: pd.DataFrame, annual: list[dict]) -> go.Figure:
    seasonal_bands = []
    for yr in range(2016, 2028):
        start = pd.Timestamp(f"{yr}-12-01")
        end   = pd.Timestamp(f"{yr+1}-05-31")
        if start <= weekly.index[-1]:
            seasonal_bands.append((start, min(end, weekly.index[-1])))

    fig = go.Figure()
    for s, e in seasonal_bands:
        fig.add_vrect(x0=s, x1=e, fillcolor="rgba(255,215,0,0.08)",
                      layer="below", line_width=0)

    fig.add_trace(go.Scatter(
        x=weekly.index, y=weekly["bh"],
        name="EQT B&H", line=dict(color="#94a3b8", width=1.5, dash="dot"),
        hovertemplate="B&H: %{y:.2f}x<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=weekly.index, y=weekly["equity"],
        name="Hybrid Strategy", line=dict(color="#7c3aed", width=2.5),
        hovertemplate="Hybrid: %{y:.2f}x<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="EQT Hybrid Strategy — Equity Curve (2016–Present)",
                   font=dict(size=15)),
        xaxis=dict(title="", showgrid=False),
        yaxis=dict(title="Growth of $1", tickformat=".1f", showgrid=True,
                   gridcolor="rgba(128,128,128,0.15)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
        hovermode="x unified",
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _annual_chart(annual: list[dict]) -> go.Figure:
    years       = [a["year"]   for a in annual]
    hybrid_vals = [a["hybrid"] for a in annual]
    bh_vals     = [a["bh"]     for a in annual]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=years, x=bh_vals, orientation="h",
        name="EQT B&H", marker_color="#94a3b8",
        hovertemplate="%{y}: %{x:.1f}%<extra>B&H</extra>",
    ))
    fig.add_trace(go.Bar(
        y=years, x=hybrid_vals, orientation="h",
        name="Hybrid",
        marker_color=["#7c3aed" if v >= 0 else "#dc2626" for v in hybrid_vals],
        hovertemplate="%{y}: %{x:.1f}%<extra>Hybrid</extra>",
    ))

    fig.update_layout(
        title=dict(text="Annual Returns", font=dict(size=13)),
        barmode="group",
        xaxis=dict(title="Return (%)", zeroline=True, zerolinecolor="#666",
                   ticksuffix="%"),
        yaxis=dict(type="category", autorange="reversed", tickfont=dict(size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
        height=380,
        margin=dict(l=10, r=10, t=50, b=10),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def _z_gauge(z_value: float) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=z_value,
        number={"suffix": "σ", "font": {"size": 28}},
        gauge={
            "axis": {
                "range": [-3, 3], "tickwidth": 1,
                "tickvals": [-3, -2, -1, -0.25, 0, 1, 2, 3],
                "ticktext": ["-3", "-2", "-1", "-0.25", "0", "1", "2", "3"],
            },
            "bar": {"color": "#7c3aed", "thickness": 0.25},
            "bgcolor": "white",
            "steps": [
                {"range": [-3, -0.25], "color": "rgba(124,58,237,0.15)"},
                {"range": [-0.25, 3],  "color": "rgba(200,200,200,0.1)"},
            ],
            "threshold": {
                "line": {"color": "#dc2626", "width": 3},
                "thickness": 0.75,
                "value": -0.25,
            },
        },
        title={"text": "HH Z-Score (20d M2-aware)", "font": {"size": 12}},
    ))
    fig.update_layout(
        height=220,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 3. MAIN RENDER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def render_eqt_hybrid(json_path: str | None = None):
    """
    Call this inside a Streamlit tab (or directly as a page).

    Parameters
    ----------
    json_path : str | None
        Path to the pre-computed JSON produced by run_backtest.py.
        If None, a sidebar file uploader is shown.
    """

    st.markdown("## EQT Hybrid Strategy")
    st.caption("Seasonal (Dec→May) + Z-score off-season | HH M2-aware Z-score | TC: 0.20%/side")

    # ── resolve JSON source ──────────────────────────────────────────────────
    if json_path is None:
        with st.sidebar:
            st.markdown("### 📂 EQT Backtest JSON")
            uploaded = st.file_uploader(
                "Upload eqt_backtest.json",
                type=["json"],
                key="eqt_json_upload",
                help="Generated locally by running: python run_backtest.py",
            )
        if uploaded is None:
            st.info(
                "No backtest data found. Run `python run_backtest.py` locally "
                "to generate `data/eqt_backtest.json`, then commit & push — "
                "or upload the JSON via the sidebar."
            )
            return
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name
        results = _load_json(tmp_path)
        os.unlink(tmp_path)
    else:
        if not Path(json_path).exists():
            st.warning(
                f"`{json_path}` not found. Run `python run_backtest.py` locally "
                "to generate it, then commit & push."
            )
            return
        results = _load_json(json_path)

    stats   = results["stats"]
    current = results["current"]
    annual  = results["annual"]
    weekly  = results["weekly"]
    daily   = results["daily"]
    gen     = results["generated"]

    # ── live price ───────────────────────────────────────────────────────────
    live_price, live_time = _get_live_eqt_price()

    # ── signal badge ─────────────────────────────────────────────────────────
    sig       = current["signal"]
    sig_color = {"SEASONAL": "#f59e0b", "ZSCORE": "#7c3aed", "FLAT": "#64748b"}[sig]
    sig_icon  = {"SEASONAL": "🌿", "ZSCORE": "⚡", "FLAT": "⏸"}[sig]

    display_price = (
        f"${live_price:.2f}"
        if live_price
        else f"${current['eqt_last']:.2f}"
    )
    live_label = (
        f"<span style='font-size:0.7rem;color:#888'>&nbsp;live {live_time}</span>"
        if live_price
        else f"<span style='font-size:0.7rem;color:#888'>&nbsp;as of {current['eqt_date']}</span>"
    )

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:12px 18px;
                border-radius:10px;background:rgba(0,0,0,0.04);
                border-left:4px solid {sig_color};margin-bottom:4px">
      <span style="font-size:1.6rem">{sig_icon}</span>
      <div>
        <div style="font-size:0.75rem;color:#888;text-transform:uppercase;letter-spacing:.08em">Current Signal</div>
        <div style="font-size:1.3rem;font-weight:700;color:{sig_color}">{sig}</div>
      </div>
      <div style="margin-left:auto;text-align:right">
        <div style="font-size:0.75rem;color:#888">EQT Last</div>
        <div style="font-size:1.1rem;font-weight:600">{display_price}{live_label}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if gen:
        st.caption(f"Backtest data generated: {gen[:16].replace('T', ' ')}")

    # ── stat cards ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Hybrid Return",  f"+{stats['hybrid']['ret']}%")
    c2.metric("Hybrid Sharpe",  f"{stats['hybrid']['sharpe']}",
              delta=f"vs B&H {stats['bh']['sharpe']}")
    c3.metric("Max Drawdown",   f"{stats['hybrid']['maxdd']}%")
    c4.metric("B&H Return",     f"+{stats['bh']['ret']}%")
    c5.metric("B&H Sharpe",     f"{stats['bh']['sharpe']}")
    c6.metric("HH Z-Score",     f"{current['z']:.3f}σ")

    st.divider()

    # ── charts ───────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.plotly_chart(_equity_chart(weekly, annual), use_container_width=True)

    with col_right:
        st.plotly_chart(_z_gauge(current["z"]), use_container_width=True)
        st.markdown("""
        <div style="font-size:0.78rem;color:#888;padding:8px 0">
        <b>Entry trigger:</b><br>
        Z-score &lt; −0.25 <b>AND</b><br>
        1-day HH momentum &lt; −$0.20<br><br>
        <b>Exit:</b> 10 consecutive days without signal<br><br>
        <b>Seasonal window:</b><br>
        Dec 1 → May 31 (buy last TD Dec, sell last TD May)<br><br>
        <b>Transaction costs:</b><br>
        Z-score: 0.20%/side&nbsp;&nbsp;Seasonal: 0.40% RT<br><br>
        <b>Z-score lookback:</b><br>
        20-day, M2-aware (prior-month days use M2 futures to avoid roll distortion)
        </div>
        """, unsafe_allow_html=True)

    st.plotly_chart(_annual_chart(annual), use_container_width=True)

    # ── annual returns table ─────────────────────────────────────────────────
    with st.expander("📊 Annual returns table"):
        ann_df = pd.DataFrame(annual).rename(columns={
            "year": "Year", "hybrid": "Hybrid (%)", "bh": "B&H (%)"
        })
        ann_df = ann_df.sort_values("Year", ascending=False).reset_index(drop=True)
        st.dataframe(
            ann_df.style
                  .format({"Hybrid (%)": "{:.1f}", "B&H (%)": "{:.1f}"})
                  .background_gradient(subset=["Hybrid (%)"], cmap="RdYlGn", vmin=-50, vmax=100)
                  .background_gradient(subset=["B&H (%)"],    cmap="RdYlGn", vmin=-50, vmax=100),
            use_container_width=True,
        )

    # ── data download ────────────────────────────────────────────────────────
    if daily:
        with st.expander("⬇️ Download daily backtest data"):
            dl_df = pd.DataFrame(daily)
            st.download_button(
                "Download CSV",
                dl_df.to_csv(index=False),
                file_name=f"eqt_hybrid_backtest_{datetime.date.today()}.csv",
                mime="text/csv",
            )


# ─────────────────────────────────────────────────────────────────────────────
# 4. STANDALONE MODE  (streamlit run eqt_hybrid_tab.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(
        page_title="EQT Hybrid Strategy",
        page_icon="⛽",
        layout="wide",
    )
    import pathlib
    _json = None
    for _cand in [
        pathlib.Path(__file__).parent / "data" / "eqt_backtest.json",
        pathlib.Path(__file__).parent / "data" / "backtest_output.json",
    ]:
        if _cand.exists():
            _json = str(_cand)
            break
    render_eqt_hybrid(json_path=_json)
