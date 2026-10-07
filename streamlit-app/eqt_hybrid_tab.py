"""
EQT Hybrid Strategy Tab
-----------------------
Drop this file into your Streamlit app and call render_eqt_hybrid() from
within a tab:

    tab1, tab2 = st.tabs(["VLO", "EQT Hybrid"])
    with tab2:
        from eqt_hybrid_tab import render_eqt_hybrid
        render_eqt_hybrid()

Dependencies: streamlit, plotly, pandas, numpy, openpyxl, yfinance
"""

import json
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import datetime

# ─────────────────────────────────────────────────────────────────────────────
# 1. BACKTEST ENGINE  (M2-aware Z-score hybrid)
# ─────────────────────────────────────────────────────────────────────────────

def _run_backtest(df_hh: pd.DataFrame, df_eqt: pd.DataFrame) -> dict:
    """
    df_hh  : index=date, columns=[m1, m2]
    df_eqt : index=date, columns=[price]
    Returns dict with equity curve, signal series, stats, annual returns.
    """
    data = df_eqt.join(df_hh, how="inner").dropna(subset=["price", "m1"])
    data["m2"] = data["m2"].fillna(data["m1"])
    data = data.reset_index()
    data.columns = ["date", "price", "m1", "m2"]
    data = data[data["date"] >= "2016-01-01"].reset_index(drop=True)

    # M2-aware Z-score
    Z_LB = 20
    m1v = data["m1"].values
    m2v = data["m2"].values
    months = data["date"].dt.month.values
    z_scores = np.full(len(data), np.nan)

    for i in range(Z_LB, len(data)):
        cm = months[i]
        wpx = np.where(months[i - Z_LB:i] == cm, m1v[i - Z_LB:i], m2v[i - Z_LB:i])
        if np.any(np.isnan(wpx)):
            continue
        mu, sd = wpx.mean(), wpx.std()
        if sd > 0:
            z_scores[i] = (m1v[i] - mu) / sd

    data["z"] = z_scores
    data["mom"] = data["m1"].diff(1)

    TC = 0.002  # per side for Z-score; seasonal uses 0.004 round-trip

    def in_seasonal(d):
        return d.month == 12 or (1 <= d.month <= 5)

    n = len(data)
    eq = 1.0
    in_seas = False
    in_z = False
    seas_ep = seas_eq = z_ep = z_eq = None
    dns = 0

    equity = np.zeros(n)
    signal = ["FLAT"] * n

    for i in range(n):
        curr = data.iloc[i]
        prev = data.iloc[i - 1] if i > 0 else curr
        z_sig = (
            not np.isnan(prev["z"])
            and prev["z"] < -0.25
            and not np.isnan(prev["mom"])
            and prev["mom"] < -0.20
        )
        seasonal_now = in_seasonal(curr["date"])

        if seasonal_now and not in_seas:
            if in_z:
                eq = z_eq * (1 + curr["price"] / z_ep - 1 - 2 * TC)
                in_z = False
                dns = 0
            in_seas = True
            seas_ep = curr["price"]
            seas_eq = eq

        if not seasonal_now and in_seas:
            eq = seas_eq * (1 + curr["price"] / seas_ep - 1 - 0.004)
            in_seas = False

        if in_seas:
            signal[i] = "SEASONAL"
            equity[i] = seas_eq * (curr["price"] / seas_ep)
        elif in_z:
            signal[i] = "ZSCORE"
            dns = 0 if z_sig else dns + 1
            equity[i] = z_eq * (curr["price"] / z_ep)
            if dns >= 10:
                eq = z_eq * (1 + curr["price"] / z_ep - 1 - 2 * TC)
                equity[i] = eq
                in_z = False
                dns = 0
        else:
            equity[i] = eq
            if z_sig and not seasonal_now:
                in_z = True
                dns = 0
                z_ep = curr["price"]
                z_eq = eq
                signal[i] = "ZSCORE"

    bh = data["price"].values / data["price"].values[0]

    def sharpe(e):
        r = np.diff(e) / e[:-1]
        return round(float(np.mean(r) / np.std(r) * np.sqrt(252)), 3)

    def maxdd(e):
        pk = np.maximum.accumulate(e)
        return round(float(((e - pk) / pk).min() * 100), 1)

    data["equity"] = equity
    data["bh"] = bh
    data["signal"] = signal

    ann = []
    for yr, grp in data.groupby(data["date"].dt.year):
        ann.append(
            {
                "year": int(yr),
                "hybrid": round(float(grp["equity"].iloc[-1] / grp["equity"].iloc[0] - 1) * 100, 1),
                "bh": round(float(grp["bh"].iloc[-1] / grp["bh"].iloc[0] - 1) * 100, 1),
            }
        )

    weekly = data.set_index("date")[["equity", "bh"]].resample("W").last()

    return {
        "data": data,
        "weekly": weekly,
        "annual": ann,
        "stats": {
            "hybrid": {
                "ret": round(float(equity[-1] - 1) * 100, 1),
                "sharpe": sharpe(equity),
                "maxdd": maxdd(equity),
            },
            "bh": {
                "ret": round(float(bh[-1] - 1) * 100, 1),
                "sharpe": sharpe(bh),
                "maxdd": maxdd(bh),
            },
        },
        "current": {
            "signal": signal[-1],
            "z": round(float(data["z"].iloc[-1]), 3),
            "eqt_last": round(float(data["price"].iloc[-1]), 2),
            "eqt_date": str(data["date"].iloc[-1].date()),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. DATA LOADING  (cached)
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading EQT backtest data…")
def _load_and_run(xlsx_path: str) -> dict:
    df = pd.read_excel(xlsx_path, sheet_name="HH EQT", header=None)
    hh_raw = df.iloc[2:, [5, 6, 8]].copy()
    hh_raw.columns = ["date", "m1", "m2"]
    hh_raw["date"] = pd.to_datetime(hh_raw["date"], errors="coerce")
    hh_raw = hh_raw.dropna(subset=["date"])
    hh_raw["m1"] = pd.to_numeric(hh_raw["m1"], errors="coerce")
    hh_raw["m2"] = pd.to_numeric(hh_raw["m2"], errors="coerce")
    hh_raw = hh_raw.set_index("date").sort_index()

    eqt_raw = df.iloc[2:, [11, 12]].copy()
    eqt_raw.columns = ["date", "price"]
    eqt_raw["date"] = pd.to_datetime(eqt_raw["date"], errors="coerce")
    eqt_raw = eqt_raw.dropna(subset=["date"])
    eqt_raw["price"] = pd.to_numeric(eqt_raw["price"], errors="coerce")
    eqt_raw = eqt_raw.set_index("date").sort_index()

    return _run_backtest(hh_raw, eqt_raw)


def _get_live_eqt_price() -> tuple[float | None, str]:
    """Fetch live EQT price via yfinance (best-effort)."""
    try:
        import yfinance as yf
        t = yf.Ticker("EQT")
        info = t.fast_info
        price = getattr(info, "last_price", None)
        if price:
            return round(float(price), 2), datetime.datetime.now().strftime("%H:%M ET")
    except Exception:
        pass
    return None, ""


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHART BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _equity_chart(weekly: pd.DataFrame, annual: list[dict]) -> go.Figure:
    seasonal_bands = []
    for yr in range(2016, 2027):
        start = pd.Timestamp(f"{yr}-12-01")
        end = pd.Timestamp(f"{yr+1}-05-31")
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
        x=weekly.index, y=weekly["hybrid"],
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
    years = [a["year"] for a in annual]
    hybrid_vals = [a["hybrid"] for a in annual]
    bh_vals = [a["bh"] for a in annual]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=years, x=bh_vals, orientation="h",
        name="EQT B&H", marker_color="#94a3b8",
        hovertemplate="%{y}: %{x:.1f}%<extra>B&H</extra>",
    ))
    fig.add_trace(go.Bar(
        y=years, x=hybrid_vals, orientation="h",
        name="Hybrid", marker_color=[
            "#7c3aed" if v >= 0 else "#dc2626" for v in hybrid_vals
        ],
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
    z_clipped = max(-3, min(3, z_value))
    pct = (z_clipped + 3) / 6  # 0→1 across [-3, +3]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=z_value,
        number={"suffix": "σ", "font": {"size": 28}},
        gauge={
            "axis": {"range": [-3, 3], "tickwidth": 1,
                     "tickvals": [-3, -2, -1, -0.25, 0, 1, 2, 3],
                     "ticktext": ["-3", "-2", "-1", "-0.25", "0", "1", "2", "3"]},
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
# 4. MAIN RENDER FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def render_eqt_hybrid(xlsx_path: str | None = None):
    """
    Call this inside a Streamlit tab (or directly as a page).

    Parameters
    ----------
    xlsx_path : str | None
        Path to the 'HH EQT' workbook (the 3-sheet file with M1/M2/EQT data).
        If None, the function asks the user to upload the file via the sidebar.
    """

    st.markdown("## EQT Hybrid Strategy")
    st.caption("Seasonal (Dec→May) + Z-score off-season | HH M2-aware Z-score | TC: 0.20%/side")

    # ── resolve data source ──────────────────────────────────────────────────
    if xlsx_path is None:
        with st.sidebar:
            st.markdown("### 📂 EQT Data File")
            uploaded = st.file_uploader(
                "Upload HH EQT workbook (.xlsx)",
                type=["xlsx"],
                key="eqt_xlsx_upload",
                help="3-sheet workbook with 'HH EQT' tab (M1, M2, EQT columns)",
            )
        if uploaded is None:
            st.info("Upload your HH EQT workbook in the sidebar to run the backtest.")
            return
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp.write(uploaded.read())
            tmp_path = tmp.name
        results = _load_and_run(tmp_path)
        os.unlink(tmp_path)
    else:
        results = _load_and_run(xlsx_path)

    stats   = results["stats"]
    current = results["current"]
    annual  = results["annual"]
    weekly  = results["weekly"]

    # ── live price ───────────────────────────────────────────────────────────
    live_price, live_time = _get_live_eqt_price()

    # ── signal badge ─────────────────────────────────────────────────────────
    sig = current["signal"]
    sig_color = {"SEASONAL": "#f59e0b", "ZSCORE": "#7c3aed", "FLAT": "#64748b"}[sig]
    sig_icon  = {"SEASONAL": "🌿", "ZSCORE": "⚡", "FLAT": "⏸"}[sig]

    badge_html = f"""
    <div style="display:flex;align-items:center;gap:12px;padding:12px 18px;
                border-radius:10px;background:rgba(0,0,0,0.04);
                border-left:4px solid {sig_color};margin-bottom:4px">
      <span style="font-size:1.6rem">{sig_icon}</span>
      <div>
        <div style="font-size:0.75rem;color:#888;text-transform:uppercase;
                    letter-spacing:.08em">Current Signal</div>
        <div style="font-size:1.3rem;font-weight:700;color:{sig_color}">{sig}</div>
      </div>
      <div style="margin-left:auto;text-align:right">
        <div style="font-size:0.75rem;color:#888">EQT Last</div>
        <div style="font-size:1.1rem;font-weight:600">
          {'${:.2f}'.format(live_price) if live_price else '${:.2f}'.format(current['eqt_last'])}
          {"<span style='font-size:0.7rem;color:#888'>&nbsp;live</span>" if live_price else ""}
        </div>
      </div>
    </div>
    """
    st.markdown(badge_html, unsafe_allow_html=True)

    # ── stat cards ───────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    def _card(col, label, val, delta=None, color=None):
        with col:
            if delta is not None:
                st.metric(label, val, delta)
            else:
                st.metric(label, val)

    _card(c1, "Hybrid Return",  f"+{stats['hybrid']['ret']}%")
    _card(c2, "Hybrid Sharpe",  f"{stats['hybrid']['sharpe']}",
          delta=f"vs B&H {stats['bh']['sharpe']}")
    _card(c3, "Max Drawdown",   f"{stats['hybrid']['maxdd']}%")
    _card(c4, "B&H Return",     f"+{stats['bh']['ret']}%")
    _card(c5, "B&H Sharpe",     f"{stats['bh']['sharpe']}")
    _card(c6, "HH Z-Score",     f"{current['z']:.3f}σ")

    st.divider()

    # ── charts ───────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([3, 1])

    with col_left:
        st.plotly_chart(_equity_chart(weekly, annual), use_container_width=True)

    with col_right:
        st.plotly_chart(_z_gauge(current["z"]), use_container_width=True)
        st.markdown(
            f"""
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
            """,
            unsafe_allow_html=True,
        )

    st.plotly_chart(_annual_chart(annual), use_container_width=True)

    # ── annual returns table ─────────────────────────────────────────────────
    with st.expander("📊 Annual returns table"):
        ann_df = pd.DataFrame(annual).rename(columns={
            "year": "Year", "hybrid": "Hybrid (%)", "bh": "B&H (%)"
        })
        ann_df = ann_df.sort_values("Year", ascending=False).reset_index(drop=True)
        st.dataframe(
            ann_df.style.format({"Hybrid (%)": "{:.1f}", "B&H (%)": "{:.1f}"})
                  .background_gradient(subset=["Hybrid (%)"], cmap="RdYlGn", vmin=-50, vmax=100)
                  .background_gradient(subset=["B&H (%)"],    cmap="RdYlGn", vmin=-50, vmax=100),
            use_container_width=True,
        )

    # ── data download ────────────────────────────────────────────────────────
    with st.expander("⬇️ Download backtest data"):
        dl_df = results["data"][["date", "price", "m1", "m2", "z", "mom", "equity", "bh", "signal"]].copy()
        dl_df["date"] = dl_df["date"].dt.date
        st.download_button(
            "Download CSV",
            dl_df.to_csv(index=False),
            file_name=f"eqt_hybrid_backtest_{datetime.date.today()}.csv",
            mime="text/csv",
        )


# ─────────────────────────────────────────────────────────────────────────────
# 5. STANDALONE MODE  (streamlit run eqt_hybrid_tab.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(
        page_title="EQT Hybrid Strategy",
        page_icon="⛽",
        layout="wide",
    )
    # When running standalone, put the xlsx path here OR leave None to use the uploader
    XLSX_PATH = None   # e.g. r"C:\Users\Admin\...\hh eqt.xlsx"
    render_eqt_hybrid(xlsx_path=XLSX_PATH)
