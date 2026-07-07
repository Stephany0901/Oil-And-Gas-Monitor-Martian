"""
Oil & Gas Equity Monitor — Streamlit app.
Deploy on Streamlit Community Cloud (https://share.streamlit.io) for a *.streamlit.app URL.
Data: Financial Modeling Prep (FMP) /stable endpoints (Starter-plan friendly).
Set your key in .streamlit/secrets.toml as  FMP_API_KEY = "xxxx"  or paste it in the sidebar.
"""
import datetime as dt
import pathlib
import re
import numpy as np
import pandas as pd
import requests
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from universe import UNIVERSE

st.set_page_config(page_title="Oil & Gas Equity Monitor", layout="wide", page_icon="🛢️")

st.markdown("""
<style>
:root{--bg:#f6f7f9;--card:#ffffff;--ink:#10161d;--mut:#5b6776;--line:#e4e8ee;--accent:#0b6b53;}
html, body, [class*="css"]{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
.stApp{background:var(--bg);}
.block-container{max-width:1200px;padding-top:1.1rem;padding-bottom:3rem;}
h1{font-size:26px !important;letter-spacing:-.3px;color:var(--ink);font-weight:700;}
h2,h3{color:var(--ink);font-weight:650;}
div[data-baseweb="tab-list"]{gap:6px;flex-wrap:wrap;border-bottom:1px solid var(--line);}
button[data-baseweb="tab"]{background:#fff;border:1px solid var(--line) !important;border-radius:999px;padding:6px 14px;margin:0 2px 0 0;color:var(--mut);font-size:12.5px;}
button[data-baseweb="tab"][aria-selected="true"]{background:var(--ink);color:#fff;border-color:var(--ink) !important;}
div[data-baseweb="tab-highlight"],div[data-baseweb="tab-border"]{display:none !important;}
div[data-testid="stMetric"]{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;}
div[data-testid="stMetricLabel"] p{color:var(--mut);font-size:11px;}
div[data-testid="stMetricValue"]{font-size:20px;font-weight:680;}
.stButton>button{background:var(--ink);color:#fff;border:1px solid var(--ink);border-radius:8px;font-weight:600;}
.stButton>button:hover{background:var(--accent);border-color:var(--accent);color:#fff;}
div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:10px;overflow:hidden;}
section[data-testid="stSidebar"]{background:#ffffff;border-right:1px solid var(--line);}
section[data-testid="stSidebar"] .stButton>button{width:100%;}
div[data-testid="stAlert"]{border-radius:10px;}
.ogtblwrap{max-height:560px;overflow:auto;border:1px solid var(--line);border-radius:10px;}
.ogtbl{width:100%;border-collapse:collapse;font-size:12.5px;}
.ogtbl th{position:sticky;top:0;background:#fff;font-weight:700;text-align:right;padding:6px 9px;border-bottom:1px solid var(--line);box-shadow:0 1px 0 var(--line);color:var(--ink);white-space:nowrap;}
.ogtbl th:first-child,.ogtbl td:first-child{text-align:left;}
.ogtbl td{padding:6px 9px;text-align:right;border-bottom:1px solid #eef2f6;white-space:nowrap;}
.ogtbl tbody tr:hover{background:#fafbfc;}
.ogtbl .pos{color:#137a4b;font-weight:600;}
.ogtbl .neg{color:#c0392b;font-weight:600;}
.ogtbl .tk{font-weight:650;color:#0e7490;}
.ogtbl .ognm{max-width:220px;overflow:hidden;text-overflow:ellipsis;color:var(--mut);}
</style>
""", unsafe_allow_html=True)

FMP = "https://financialmodelingprep.com/stable/"
YTD_FROM = f"{dt.date.today().year - 1}-12-29"

ENERGY_MAP = [("XLE", "Energy (XLE)"), ("XOP", "E&P (XOP)"), ("XES", "Equip/Svc (XES)"),
              ("USO", "Crude (USO)"), ("BNO", "Brent (BNO)"), ("UNG", "Nat gas (UNG)"),
              ("CRAK", "Refiners (CRAK)"), ("SPY", "S&P 500")]
SP_MAP = [("XLK", "Technology"), ("XLV", "Health Care"), ("XLE", "Energy"), ("XLF", "Financials"),
          ("XLI", "Industrials"), ("XLP", "Consumer Staples"), ("XLB", "Materials"),
          ("XLU", "Utilities"), ("XLRE", "Real Estate"), ("XLC", "Communication Services")]
GREEN, RED, GRAY = "#137a4b", "#c0392b", "#94a3b8"

U_BY_T = {u["t"]: u for u in UNIVERSE}

# --- briefing markdown renderer: uniform font, bold tickers, colored % returns ---
_BRIEF_BLOCK = {"E", "EP", "AE", "AR", "DO", "HP", "GI", "SD", "PR", "INT", "SUN",
                "WTI", "LNG", "MNR", "US", "IT", "ON", "BP", "NEX", "REX", "EC"}
_BRIEF_TICKERS = [t for t in sorted(
    {u["t"] for u in UNIVERSE} | {"XLE", "XOP", "XES", "USO", "BNO", "UNG", "CRAK", "SPY"},
    key=len, reverse=True) if t not in _BRIEF_BLOCK and len(t) >= 2]
_TICK_RE = re.compile(r'(?<![A-Za-z0-9$*])(' + "|".join(re.escape(t) for t in _BRIEF_TICKERS) + r')(?![A-Za-z0-9*])')
_PCT_RE = re.compile(r'([+\-−]\d+(?:\.\d+)?\s?%)')


def _pct_span(mm):
    s = mm.group(1)
    col = "#c0392b" if s[0] in "-−" else "#137a4b"
    return f'<span style="color:{col};font-weight:600">{s}</span>'


def render_brief(text):
    text = text.replace("$", "\\$")  # escape $ so Streamlit doesn't render $...$ as LaTeX math
    lines = [(f"**{m.group(1)}**" if (m := re.match(r'^\s*#{1,6}\s+(.*)$', ln)) else ln)
             for ln in text.split("\n")]
    md = "\n".join(lines)
    md = _PCT_RE.sub(_pct_span, md)
    md = _TICK_RE.sub(lambda m: f"**{m.group(1)}**", md)
    return md.replace("****", "**")


# ----------------------------- API key -----------------------------
def get_key() -> str:
    k = st.session_state.get("fmp_key", "")
    if not k:
        try:
            k = st.secrets.get("FMP_API_KEY", "")
        except Exception:
            k = ""
    return (k or "").strip()


# ----------------------------- FMP fetchers -----------------------------
def _get(url):
    import time as _t
    for attempt in range(3):
        r = requests.get(url, timeout=30)
        if r.status_code != 429:
            break
        try:
            wait = min(float(r.headers.get("Retry-After") or 1.5), 6)
        except ValueError:
            wait = 1.5
        _t.sleep(wait)
    if r.status_code == 429:
        raise RuntimeError("FMP rate limit (HTTP 429) — too many calls this minute; retry shortly.")
    if r.status_code in (401, 402, 403):
        raise RuntimeError(f"FMP plan/auth error HTTP {r.status_code} — your key/plan may not cover this endpoint.")
    r.raise_for_status()
    j = r.json()
    if isinstance(j, dict) and (j.get("Error Message") or j.get("error")):
        raise RuntimeError(j.get("Error Message") or j.get("error"))
    return j


def _normq(q):
    if q.get("changePercentage") is None and q.get("changesPercentage") is not None:
        q["changePercentage"] = q["changesPercentage"]
    return q


def _fetch_quotes(symbols: tuple, key: str) -> dict:
    """Batch quote is premium on Starter; fall back to threaded single-symbol
    /stable/quote?symbol= which lower plans allow."""
    import concurrent.futures as cf
    out = {}
    syms = list(symbols)
    # try premium batch first (works on higher plans / no-op on Starter)
    try:
        for i in range(0, len(syms), 50):
            for q in _get(FMP + "batch-quote?symbols=" + ",".join(syms[i:i + 50]) + "&apikey=" + key):
                out[q.get("symbol")] = _normq(q)
    except Exception:
        out = {}
    if out:
        return out
    # fallback: single-symbol quotes, threaded
    def one(s):
        import time as _t
        for attempt in range(2):
            try:
                d = _get(FMP + "quote?symbol=" + s + "&apikey=" + key)
                return _normq(d[0]) if d else None
            except Exception:
                _t.sleep(0.4)
        return None
    with cf.ThreadPoolExecutor(max_workers=5) as ex:
        for s, res in zip(syms, ex.map(one, syms)):
            if res:
                out[s] = res
    return out


@st.cache_data(ttl=1800, show_spinner=False)
def _quotes_cached(symbols: tuple, key: str) -> dict:
    out = _fetch_quotes(symbols, key)
    # Never cache a failed/mostly-failed fetch (e.g. rate-limited): raising
    # prevents st.cache_data from storing it, so the next rerun retries.
    if len(out) < max(1, int(len(symbols) * 0.8)):
        raise RuntimeError(f"quotes incomplete: {len(out)}/{len(symbols)} — likely FMP rate limit")
    return out


def quotes_for(symbols: tuple, key: str) -> dict:
    try:
        return _quotes_cached(symbols, key)
    except Exception:
        return {}


batch_quote = quotes_for  # alias used by the sector tab


@st.cache_data(ttl=600, show_spinner=False)
def probe(key: str) -> dict:
    tests = [("single quote", "quote?symbol=XOM"),
             ("batch quote", "batch-quote?symbols=XOM,CVX"),
             ("ETF quote (XLE)", "quote?symbol=XLE"),
             ("ETF quote (USO)", "quote?symbol=USO"),
             ("commodities", "all-commodities-quotes"),
             ("history (light)", "historical-price-eod/light?symbol=XOM&from=" + YTD_FROM),
             ("key-metrics-ttm", "key-metrics-ttm?symbol=XOM")]
    res = {}
    for nm, path in tests:
        sep = "&" if "?" in path else "?"
        try:
            _get(FMP + path + sep + "apikey=" + key)
            res[nm] = "OK"
        except Exception as e:
            res[nm] = str(e)
    return res


def _hist_rows(j):
    if isinstance(j, list):
        return j
    if isinstance(j, dict):
        return j.get("historical") or j.get("historicalStockList") or []
    return []


@st.cache_data(ttl=600, show_spinner=False)
def hist(symbol: str, frm: str, full: bool, key: str) -> pd.DataFrame:
    kind = "full" if full else "light"
    url = FMP + f"historical-price-eod/{kind}?symbol={symbol}&from={frm}&apikey=" + key
    try:
        j = _get(url)
    except Exception:
        return pd.DataFrame()
    df = pd.DataFrame(_hist_rows(j))
    if df.empty or "date" not in df.columns:
        return pd.DataFrame()
    df = df.sort_values("date").reset_index(drop=True)  # ascending by date
    if "price" not in df.columns and "close" in df.columns:
        df["price"] = df["close"]
    if "close" not in df.columns and "price" in df.columns:
        df["close"] = df["price"]
    return df


@st.cache_data(ttl=600, show_spinner=False)
def key_metrics_ttm(symbol: str, key: str) -> dict:
    try:
        arr = _get(FMP + "key-metrics-ttm?symbol=" + symbol + "&apikey=" + key)
    except Exception:
        return {}
    return arr[0] if arr else {}


@st.cache_data(ttl=600, show_spinner=False)
def key_metrics(symbol: str, key: str, limit: int = 6) -> list:
    try:
        return _get(FMP + f"key-metrics?symbol={symbol}&period=annual&limit={limit}&apikey=" + key) or []
    except Exception:
        return []


@st.cache_data(ttl=300, show_spinner=False)
def _commodities_cached(key: str) -> dict:
    for path in ("all-commodities-quotes", "batch-commodity-quotes"):
        try:
            arr = _get(FMP + path + "?apikey=" + key)
            if arr:
                return {q.get("symbol"): q for q in arr}
        except Exception:
            continue
    raise RuntimeError("no commodities data — don't cache the failure")


def commodities(key: str) -> dict:
    try:
        return _commodities_cached(key)
    except Exception:
        return {}


@st.cache_data(ttl=600, show_spinner=False)
def stock_news(symbols: tuple, key: str, limit: int = 40) -> list:
    try:
        return _get(FMP + "news/stock?symbols=" + ",".join(symbols) + f"&limit={limit}&apikey=" + key) or []
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def general_news(key: str, limit: int = 50) -> list:
    try:
        return _get(FMP + f"news/general-latest?page=0&limit={limit}&apikey=" + key) or []
    except Exception:
        return []


def km_get(m, *names):
    for n in names:
        if m and m.get(n) is not None:
            return m.get(n)
    return None


# ----------------------------- indicators -----------------------------
def ema(s, p):
    return s.ewm(span=p, adjust=False).mean()


def rsi(s, p=14):
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    ru = up.ewm(alpha=1 / p, adjust=False).mean()
    rd = dn.ewm(alpha=1 / p, adjust=False).mean()
    rs = ru / rd.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def macd(s, f=12, sl=26, sig=9):
    line = ema(s, f) - ema(s, sl)
    signal = ema(line, sig)
    return line, signal, line - signal


def obv(close, vol):
    dirn = np.sign(close.diff().fillna(0))
    return (dirn * vol).cumsum()


def pivots_sr(high, low, cur, lr=5):
    h, l = high.values, low.values
    n = len(h)
    R, S = [], []
    for i in range(lr, n - lr):
        if h[i] == max(h[i - lr:i + lr + 1]):
            R.append(h[i])
        if l[i] == min(l[i - lr:i + lr + 1]):
            S.append(l[i])
    res = min([x for x in R if x > cur], default=float(np.nanmax(h)))
    sup = max([x for x in S if x < cur], default=float(np.nanmin(l)))
    return sup, res


def slope(a):
    a = np.asarray(a, dtype=float)
    n = len(a)
    if n < 2:
        return 0.0
    x = np.arange(n)
    return np.polyfit(x, a, 1)[0]


def pct(v, d=1):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:+.{d}f}%"


def fnum(v, d=2):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:,.{d}f}"


def ogtable(df, coltypes, height=None):
    """Render a DataFrame as the styled HTML table (bold headers, green/red %, comma numbers)."""
    def fmt(col, v):
        t = coltypes.get(col, "text")
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "<td>–</td>"
        if t == "pct":
            return f'<td class="{"pos" if v >= 0 else "neg"}">{v:+.2f}%</td>'
        if t == "num":
            return f"<td>{v:,.2f}</td>"
        if t == "int":
            return f"<td>{int(v):,}</td>"
        if t == "x":
            return f"<td>{v:,.2f}x</td>"
        if t == "tk":
            return f'<td class="tk">{v}</td>'
        return f"<td>{v}</td>"
    head = "".join(f"<th>{c}</th>" for c in df.columns)
    body = "".join("<tr>" + "".join(fmt(c, r[c]) for c in df.columns) + "</tr>" for _, r in df.iterrows())
    wrap = '<div class="ogtblwrap">' if height is None else f'<div class="ogtblwrap" style="max-height:{height}px">'
    st.markdown(f'{wrap}<table class="ogtbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
                unsafe_allow_html=True)


# ----------------------------- sidebar -----------------------------
st.sidebar.title("🛢️ Oil & Gas Monitor")
try:
    _secret_key = st.secrets.get("FMP_API_KEY", "")
except Exception:
    _secret_key = ""
if _secret_key:
    # key provided via Streamlit Secrets — use it silently, never show the field
    st.session_state["fmp_key"] = _secret_key.strip()
else:
    key_in = st.sidebar.text_input("FMP API key", value="", type="password",
                                   help="Get one at financialmodelingprep.com. Or set FMP_API_KEY in the app's Secrets to hide this box.")
    if key_in:
        st.session_state["fmp_key"] = key_in.strip()
if st.sidebar.button("🔄 Refresh data (clear cache)"):
    st.cache_data.clear()
    st.rerun()
KEY = get_key()
st.sidebar.caption("Data: Financial Modeling Prep · /stable · educational, not investment advice.")

st.title("Oil & Gas Equity Monitor")
st.caption(f"{len(UNIVERSE)} names · live prices, technicals, sector & commodity context. Data via FMP.")

if not KEY:
    st.warning("Enter your **FMP API key** in the left sidebar (or set `FMP_API_KEY` in Streamlit secrets) to load data.")
    st.stop()

# ----------------------------- load quotes -----------------------------
with st.spinner("Loading quotes… (first load can take ~1 min if your plan needs single-symbol mode)"):
    QUOTES = quotes_for(tuple(u["t"] for u in UNIVERSE), KEY)

if not QUOTES:
    p = probe(KEY)
    st.error("No quotes returned. Endpoint diagnostics for your FMP key (stable API):")
    for nm, val in p.items():
        st.write(f"- **{nm}** → {val}")
    st.info("If **single quote** is OK, just reload — data loads via single-symbol mode. "
            "If it shows 401/402/403, your key/plan doesn't include stock quotes (check the key, or upgrade FMP). "
            "Endpoints that show OK here are the ones this app can use on your plan.")
    st.stop()

# Self-prune: drop delisted/stale names — FMP still serves stale quotes for delisted
# tickers, so keep only names whose last quote is within STALE_DAYS of the newest quote.
STALE_DAYS = 20
_ts_all = [(QUOTES.get(u["t"]) or {}).get("timestamp") for u in UNIVERSE]
_ts_all = [t for t in _ts_all if t]
_max_ts = max(_ts_all) if _ts_all else 0
_cutoff = _max_ts - STALE_DAYS * 86400 if _max_ts else 0


def _is_live(u):
    q = QUOTES.get(u["t"]) or {}
    if not q.get("price"):
        return False
    ts = q.get("timestamp")
    if _max_ts and ts is not None:
        return ts >= _cutoff
    return True


LIVE = [u for u in UNIVERSE if _is_live(u)]
SECTORS = sorted({u["s"] for u in UNIVERSE})
_dropped = sum(1 for u in UNIVERSE if (QUOTES.get(u["t"]) or {}).get("price")) - len(LIVE)
_no_quote = sorted(u["t"] for u in UNIVERSE if not (QUOTES.get(u["t"]) or {}).get("price"))
st.caption(f"Loaded {len(LIVE)} active names · {_dropped} delisted/stale removed · {dt.datetime.now():%Y-%m-%d %H:%M}")
if _no_quote:
    with st.expander(f"⚠ {len(_no_quote)} names returned no quote this load — a fetch failure (rate limit) or a dead ticker. "
                     f"Use 🔄 Refresh in the sidebar to retry."):
        st.write(", ".join(_no_quote))

tabs = st.tabs(["1 · Price", "2 · Peers", "3 · Hist. Val", "4 · Technical",
                "5 · Crude/Gas", "6 · News", "7 · Sector", "★ Recommend", "📰 Briefing",
                "🔎 Screeners"])


# ============================= 1 · PRICE =============================
with tabs[0]:
    st.subheader("Price filter")
    c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
    flt = c1.text_input("Filter ticker / name", "")
    sec = c2.selectbox("Sector", ["All"] + SECTORS)
    sort_opts = ["Daily%", "52w pos%", "vs50d%", "vs200d%", "Volume", "Ticker"]
    sort_by = c3.selectbox("Sort by", sort_opts)
    want_ret = c4.checkbox("Compute weekly & YTD (slower)", value=False)

    rows = []
    for u in LIVE:
        q = QUOTES.get(u["t"], {})
        price = q.get("price")
        yh, yl = q.get("yearHigh"), q.get("yearLow")
        p52 = (price - yl) / (yh - yl) * 100 if (yh and yl and yh != yl) else None
        a50, a200 = q.get("priceAvg50"), q.get("priceAvg200")
        rows.append({
            "Ticker": u["t"], "Name": u["n"], "Sector": u["s"],
            "Price": price, "Daily%": q.get("changePercentage"),
            "Volume": q.get("volume"),
            "52w pos%": p52,
            "vs50d%": (price / a50 - 1) * 100 if a50 else None,
            "vs200d%": (price / a200 - 1) * 100 if a200 else None,
        })
    df = pd.DataFrame(rows)
    if sec != "All":
        df = df[df["Sector"] == sec]
    if flt:
        f = flt.upper()
        df = df[df["Ticker"].str.contains(f) | df["Name"].str.upper().str.contains(f)]

    if want_ret:
        wk, ytd = [], []
        prog = st.progress(0.0, text="Loading weekly & YTD returns…")
        syms = df["Ticker"].tolist()
        for i, t in enumerate(syms):
            h = hist(t, YTD_FROM, False, KEY)
            if not h.empty:
                last = h["price"].iloc[-1]
                base = h["price"].iloc[0]
                ytd.append((last / base - 1) * 100 if base else None)
                wk.append((last / h["price"].iloc[-6] - 1) * 100 if len(h) >= 6 else None)
            else:
                ytd.append(None); wk.append(None)
            if i % 10 == 0:
                prog.progress(min(1.0, (i + 1) / max(1, len(syms))))
        prog.empty()
        df["Weekly%"] = wk
        df["YTD%"] = ytd

    if sort_by == "Ticker":
        df = df.sort_values("Ticker")
    else:
        df = df.sort_values(sort_by, ascending=False, na_position="last")

    cols = ["Ticker", "Name", "Sector", "Price", "Daily%", "Volume", "52w pos%", "vs50d%", "vs200d%"]
    if want_ret:
        cols += ["Weekly%", "YTD%"]
    pctcols = {"Daily%", "52w pos%", "vs50d%", "vs200d%", "Weekly%", "YTD%"}

    def cell(col, v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return "<td>–</td>"
        if col in pctcols:
            return f'<td class="{"pos" if v >= 0 else "neg"}">{v:+.2f}%</td>'
        if col == "Price":
            return f"<td>{v:,.2f}</td>"
        if col == "Volume":
            return f"<td>{int(v):,}</td>"
        if col == "Ticker":
            return f'<td class="tk">{v}</td>'
        if col == "Name":
            return f'<td class="ognm" title="{str(v).replace(chr(34), "")}">{v}</td>'
        return f"<td>{v}</td>"

    head = "".join(f"<th>{c}</th>" for c in cols)
    body = "".join("<tr>" + "".join(cell(c, r[c]) for c in cols) + "</tr>" for _, r in df.iterrows())
    st.markdown(f'<div class="ogtblwrap"><table class="ogtbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',
                unsafe_allow_html=True)
    st.caption(f"{len(df)} names")


# ============================= 2 · PEERS =============================
with tabs[1]:
    st.subheader("Peer comparison")
    t = st.selectbox("Stock", [u["t"] for u in LIVE], key="peer",
                     format_func=lambda x: f"{x} · {U_BY_T[x]['n']}")
    if st.button("Compare", key="peer_go"):
        me = U_BY_T[t]
        mc = QUOTES.get(t, {}).get("marketCap") or 0
        cand = [u for u in LIVE if u["t"] != t and u["s"] == me["s"] and (QUOTES.get(u["t"], {}).get("marketCap") or 0) > 0]
        if mc:
            cand.sort(key=lambda u: abs(np.log((QUOTES[u["t"]]["marketCap"]) / mc)))
        picks = [t] + [u["t"] for u in cand[:10]]
        data = []
        with st.spinner("Fetching key metrics…"):
            for s in picks:
                m = key_metrics_ttm(s, KEY)
                if not m:
                    continue
                data.append({
                    "Ticker": s + (" ★" if s == t else ""),
                    "Mkt cap": QUOTES.get(s, {}).get("marketCap"),
                    "EV/EBITDA": km_get(m, "evToEBITDATTM", "enterpriseValueOverEBITDATTM"),
                    "FCF yld%": (km_get(m, "freeCashFlowYieldTTM") or 0) * 100 if km_get(m, "freeCashFlowYieldTTM") is not None else None,
                    "NetDebt/EBITDA": km_get(m, "netDebtToEBITDATTM"),
                    "ROE%": (km_get(m, "returnOnEquityTTM", "roeTTM") or 0) * 100 if km_get(m, "returnOnEquityTTM", "roeTTM") is not None else None,
                })
        if data:
            st.caption(f"{t} vs same-sector peers (nearest market caps)")
            ogtable(pd.DataFrame(data), {
                "Ticker": "tk", "Mkt cap": "int", "EV/EBITDA": "x",
                "FCF yld%": "pct", "NetDebt/EBITDA": "x", "ROE%": "pct",
            })
        else:
            st.info("No key-metrics returned (your plan may not include this endpoint).")


# ============================= 3 · HIST. VAL =============================
with tabs[2]:
    st.subheader("Historical valuation — TTM vs 5-year range")
    t = st.selectbox("Stock", [u["t"] for u in LIVE], key="hist",
                     format_func=lambda x: f"{x} · {U_BY_T[x]['n']}")
    if st.button("Analyze", key="hist_go"):
        ttm = key_metrics_ttm(t, KEY)
        ann = key_metrics(t, KEY, 6)[:5]
        defs = [("EV / EBITDA", ["evToEBITDA", "enterpriseValueOverEBITDA"], ["evToEBITDATTM", "enterpriseValueOverEBITDATTM"], 1, "x"),
                ("FCF yield", ["freeCashFlowYield"], ["freeCashFlowYieldTTM"], 1, "%"),
                ("Net Debt / EBITDA", ["netDebtToEBITDA"], ["netDebtToEBITDATTM"], 1, "x"),
                ("ROE", ["returnOnEquity", "roe"], ["returnOnEquityTTM", "roeTTM"], 1, "%")]
        out = []
        for nm, ak, tk, d, unit in defs:
            histvals = [km_get(y, *ak) for y in ann]
            histvals = [v for v in histvals if v is not None]
            spot = km_get(ttm, *tk)
            if unit == "%":
                histvals = [v * 100 for v in histvals]
                spot = spot * 100 if spot is not None else None
            if not histvals or spot is None:
                out.append({"Metric": nm, "Spot(TTM)": None, "5y low": None, "5y avg": None, "5y high": None})
            else:
                out.append({"Metric": nm, "Spot(TTM)": spot, "5y low": min(histvals),
                            "5y avg": sum(histvals) / len(histvals), "5y high": max(histvals)})
        ogtable(pd.DataFrame(out), {
            "Metric": "text", "Spot(TTM)": "num", "5y low": "num", "5y avg": "num", "5y high": "num",
        })


# ============================= 4 · TECHNICAL =============================
with tabs[3]:
    st.subheader("Technical analysis")
    c1, c2 = st.columns([3, 2])
    t = c1.selectbox("Stock", [u["t"] for u in LIVE], key="tech",
                     format_func=lambda x: f"{x} · {U_BY_T[x]['n']}")
    win = c2.selectbox("Window", [("6 months", 180), ("1 year", 365), ("2 years", 730),
                                  ("3 years", 1095), ("5 years", 1825)], index=1,
                       format_func=lambda x: x[0])[1]
    if st.button("Run", key="tech_go"):
        frm = (dt.date.today() - dt.timedelta(days=win)).isoformat()
        h = hist(t, frm, True, KEY)
        if h.empty or len(h) < 30:
            st.info("Not enough history for this name/window.")
        else:
            close, high, low, opn = h["close"], h["high"], h["low"], h["open"]
            vol = h.get("volume", pd.Series([0] * len(h)))
            n = len(close)
            cur = close.iloc[-1]
            m20, m50, m200 = close.rolling(20).mean(), close.rolling(50).mean(), close.rolling(200).mean()
            e21 = ema(close, 21)
            R = rsi(close, 14)
            ML, MS, MH = macd(close)
            OB = obv(close, vol)
            sup, res = pivots_sr(high, low, cur, 5)

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("Last", fnum(cur))
            k2.metric("vs 50d", pct((cur / m50.iloc[-1] - 1) * 100) if not np.isnan(m50.iloc[-1]) else "–")
            k3.metric("vs 200d", pct((cur / m200.iloc[-1] - 1) * 100) if not np.isnan(m200.iloc[-1]) else "–")
            k4.metric("RSI(14)", fnum(R.iloc[-1], 0))
            k5.metric("Support / Resist", f"{fnum(sup)} / {fnum(res)}")

            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=h["date"], open=opn, high=high, low=low, close=close, name=t,
                                         increasing_line_color=GREEN, decreasing_line_color=RED))
            for series, nm, col, dash in [(m20, "MA20", "#0e7490", None), (m50, "MA50", "#0b6b53", None),
                                          (m200, "MA200", "#9333ea", None), (e21, "EMA21", "#e11d48", "dash")]:
                fig.add_trace(go.Scatter(x=h["date"], y=series, name=nm, line=dict(color=col, width=1.2, dash=dash)))
            fig.add_hline(y=res, line=dict(color=RED, width=1, dash="dot"), annotation_text="Resistance")
            fig.add_hline(y=sup, line=dict(color=GREEN, width=1, dash="dot"), annotation_text="Support")
            fig.update_layout(height=460, margin=dict(l=0, r=0, t=10, b=0), xaxis_rangeslider_visible=False,
                              legend=dict(orientation="h", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

            sub = make_subplots(rows=1, cols=3, subplot_titles=("RSI (14)", "MACD (12,26,9)", "On-Balance Volume"))
            sub.add_trace(go.Scatter(x=h["date"], y=R, line=dict(color="#0e7490", width=1.2)), 1, 1)
            sub.add_hline(y=70, line=dict(color=RED, width=1, dash="dot"), row=1, col=1)
            sub.add_hline(y=30, line=dict(color=GREEN, width=1, dash="dot"), row=1, col=1)
            sub.add_trace(go.Bar(x=h["date"], y=MH, marker_color=[GREEN if v >= 0 else RED for v in MH]), 1, 2)
            sub.add_trace(go.Scatter(x=h["date"], y=ML, line=dict(color="#10161d", width=1)), 1, 2)
            sub.add_trace(go.Scatter(x=h["date"], y=MS, line=dict(color="#e11d48", width=1)), 1, 2)
            sub.add_trace(go.Scatter(x=h["date"], y=OB, line=dict(color="#7c3aed", width=1.2), fill="tozeroy"), 1, 3)
            sub.update_layout(height=240, margin=dict(l=0, r=0, t=24, b=0), showlegend=False)
            st.plotly_chart(sub, use_container_width=True)

            # ---- written analysis ----
            ma_sig = 1 if cur > m200.iloc[-1] else -1
            cross = "golden (50≥200)" if m50.iloc[-1] >= m200.iloc[-1] else "death (50<200)"
            ema_sig = 1 if cur > e21.iloc[-1] else -1
            ema_up = slope(e21.tail(20)) > 0
            rv = R.iloc[-1]
            rsi_score = -0.6 if rv > 70 else (0.6 if rv < 30 else (rv - 50) / 30)
            macd_sig = 1 if ML.iloc[-1] >= MS.iloc[-1] else -1
            hist_up = MH.iloc[-1] > MH.iloc[-2]
            obv_sl, prc_sl = slope(OB.tail(20)), slope(close.tail(20))
            obv_sig = 1 if obv_sl > 0 else (-1 if obv_sl < 0 else 0)
            diverge = ("bullish divergence vs price" if obv_sl > 0 and prc_sl < 0 else
                       "bearish divergence vs price" if obv_sl < 0 and prc_sl > 0 else "confirming the price move")
            score = ma_sig + ema_sig + rsi_score + macd_sig + obv_sig
            stance = "Bullish" if score >= 1.5 else ("Bearish" if score <= -1.5 else "Neutral / mixed")

            def badge(s):
                return "🟢 Bullish" if s > 0 else ("🔴 Bearish" if s < 0 else "⚪ Neutral")

            st.markdown("#### Indicator analysis")
            st.markdown(f"- **Moving averages** — {badge(ma_sig)}. Price is {'above' if cur>m200.iloc[-1] else 'below'} its 200-day and "
                        f"{'above' if cur>m50.iloc[-1] else 'below'} its 50-day; **{cross}** configuration.")
            st.markdown(f"- **EMA (21)** — {badge(ema_sig)}. Price is {'above' if ema_sig>0 else 'below'} the 21-day EMA and it is "
                        f"{'rising' if ema_up else 'falling'}.")
            st.markdown(f"- **RSI (14)** = {rv:.0f} — {'overbought (>70)' if rv>70 else ('oversold (<30)' if rv<30 else 'neutral 30–70')}.")
            st.markdown(f"- **MACD** — {badge(macd_sig)}. MACD is {'above' if macd_sig>0 else 'below'} signal; histogram "
                        f"{'expanding' if hist_up else 'contracting'}.")
            st.markdown(f"- **OBV** — {badge(obv_sig)}. Volume flow is {'accumulating' if obv_sig>0 else ('distributing' if obv_sig<0 else 'flat')}, {diverge}.")
            st.markdown(f"- **Support & Resistance** — nearest pivot support **{fnum(sup)}**, resistance **{fnum(res)}** (±5-bar swing pivots).")
            st.success(f"**Overall conclusion — {stance}** (signal score {score:+.1f}). Watch resistance {fnum(res)} and support {fnum(sup)}. "
                       f"_Educational technical read, not investment advice._")


# ============================= 5 · CRUDE / GAS =============================
with tabs[4]:
    st.subheader("Stock vs crude & natural gas")
    t = st.selectbox("Stock", [u["t"] for u in LIVE], key="mac",
                     format_func=lambda x: f"{x} · {U_BY_T[x]['n']}")
    if st.button("Analyze", key="mac_go"):
        with st.spinner("Fetching…"):
            S = hist(t, YTD_FROM, False, KEY)
            O = hist("USO", YTD_FROM, False, KEY)
            G = hist("UNG", YTD_FROM, False, KEY)
        if S.empty or O.empty:
            st.info("Insufficient data.")
        else:
            def align(a, b):
                m = pd.merge(a[["date", "price"]], b[["date", "price"]], on="date", suffixes=("_s", "_c")).dropna()
                return m
            def corr(m):
                if len(m) < 5:
                    return None
                rs = m["price_s"].pct_change().dropna()
                rc = m["price_c"].pct_change().dropna()
                k = min(len(rs), len(rc))
                return float(np.corrcoef(rs[-k:], rc[-k:])[0, 1])
            mo, mg = align(S, O), align(S, G)
            cO, cG = corr(mo), corr(mg)
            use_gas = (cG is not None) and (cO is None or abs(cG) > abs(cO))
            cm_sym, cm_name = ("UNG", "nat gas") if use_gas else ("USO", "crude")
            m = mg if use_gas else mo
            comm = commodities(KEY)
            cl = (comm.get("CLUSD") or {}).get("price")
            rb = (comm.get("RBUSD") or {}).get("price")
            ho = (comm.get("HOUSD") or {}).get("price")
            crack = (2 * rb + ho) / (3 * cl) if cl and rb and ho else None

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Corr vs crude (USO)", "–" if cO is None else f"{cO:.2f}")
            k2.metric("Corr vs nat gas (UNG)", "–" if cG is None else f"{cG:.2f}")
            k3.metric("Stronger link", cm_name)
            k4.metric("Spot 3-2-1 CRACK", fnum(crack, 3) if crack else "–")

            rs = m["price_s"].pct_change().dropna() * 100
            rc = m["price_c"].pct_change().dropna() * 100
            kk = min(len(rs), len(rc))
            c1, c2 = st.columns(2)
            xr, yr = rc[-kk:], rs[-kk:]
            sc = go.Figure()
            sc.add_trace(go.Scatter(x=xr, y=yr, mode="markers", name="history",
                                    marker=dict(color=("#b7791f" if use_gas else "#0e7490"), size=5)))
            sc.add_trace(go.Scatter(x=[float(xr.iloc[-1])], y=[float(yr.iloc[-1])], mode="markers", name="today",
                                    marker=dict(color="#c0392b", size=12, line=dict(color="#ffffff", width=1.5))))
            sc.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), showlegend=False,
                             xaxis_title=f"{cm_name} daily %", yaxis_title=f"{t} daily %")
            c1.caption(f"Daily-return scatter: {t} vs {cm_name} — red dot = today")
            c1.plotly_chart(sc, use_container_width=True)

            ratio = (m["price_s"] / m["price_c"]).dropna()
            rNow = float(ratio.iloc[-1])
            vals = ratio.values
            mn, mx = float(vals.min()), float(vals.max())
            nb = 20
            edges = np.linspace(mn, mx, nb + 1)
            counts, _ = np.histogram(vals, bins=edges)
            centers = (edges[:-1] + edges[1:]) / 2
            cur_bin = int(min(nb - 1, max(0, (rNow - mn) / ((mx - mn) / nb)))) if mx > mn else 0
            barcol = ["#c0392b" if i == cur_bin else "#0b6b53" for i in range(nb)]
            hh = go.Figure(go.Bar(x=[f"{c:.2f}" for c in centers], y=counts, marker_color=barcol,
                                  hovertemplate="ratio ~%{x}<br>%{y} days<extra></extra>"))
            hh.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), bargap=0.03,
                             xaxis_title=f"{t} / {cm_name} ratio — red bar = current ({rNow:.2f})")
            c2.caption(f"Stock / {cm_name} price-ratio histogram")
            c2.plotly_chart(hh, use_container_width=True)

            with st.spinner("Fetching 5-year ratio…"):
                frm5 = (dt.date.today() - dt.timedelta(days=365 * 5)).isoformat()
                S5 = hist(t, frm5, False, KEY)
                C5 = hist(cm_sym, frm5, False, KEY)
            if not S5.empty and not C5.empty:
                r5 = pd.merge(S5[["date", "price"]], C5[["date", "price"]], on="date", suffixes=("_s", "_c")).dropna()
                r5["ratio"] = r5["price_s"] / r5["price_c"]
                avg = r5["ratio"].mean()
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=r5["date"], y=r5["ratio"], line=dict(color=("#b7791f" if use_gas else "#0e7490"), width=1.3)))
                fig.add_hline(y=avg, line=dict(color=GRAY, width=1, dash="dash"), annotation_text="5y avg")
                fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
                st.caption(f"5-year price ratio: {t} / {cm_name} (avg {fnum(avg,3)})")
                st.plotly_chart(fig, use_container_width=True)
            st.caption("Commodity correlations use liquid ETF proxies (USO, UNG); the crack is a live spot value from NYMEX futures. Educational, not advice.")


# ============================= 6 · NEWS =============================
with tabs[5]:
    st.subheader("News")
    pick = st.selectbox("Stock news (optional)", ["— market only —"] + [u["t"] for u in LIVE], key="news")
    OIL_KW = ("oil", "crude", "gas", "lng", "opec", "wti", "brent", "petroleum", "refin",
              "shale", "drilling", "pipeline", "barrel", "gasoline", "diesel", "energy")
    uni = {u["t"] for u in UNIVERSE}
    if st.button("Load news", key="news_go"):
        majors = [u["t"] for u in sorted(LIVE, key=lambda u: QUOTES.get(u["t"], {}).get("marketCap") or 0, reverse=True)[:30]]
        arr = list(stock_news(tuple(majors), KEY, 60))
        for a in general_news(KEY, 60):
            txt = f"{a.get('title','')} {a.get('text','')}".lower()
            if any(k in txt for k in OIL_KW):
                arr.append(a)
        arr = [a for a in arr if (not a.get("symbol")) or a.get("symbol", "").upper() in uni]
        seen, dedup = set(), []
        for a in sorted(arr, key=lambda a: a.get("publishedDate", ""), reverse=True):
            k = a.get("url") or a.get("title")
            if k and k not in seen:
                seen.add(k); dedup.append(a)
        colm, cols = st.columns(2)
        with colm:
            st.markdown("**Market headlines**")
            for a in dedup[:18]:
                st.markdown(f"[{a.get('title','(untitled)')}]({a.get('url','#')})  \n"
                            f"<span style='color:#888;font-size:11px'>{a.get('site') or a.get('publisher','')} · {a.get('publishedDate','')[:16]}</span>",
                            unsafe_allow_html=True)
        with cols:
            if pick != "— market only —":
                st.markdown(f"**{pick} headlines**")
                for a in stock_news((pick,), KEY, 18):
                    st.markdown(f"[{a.get('title','(untitled)')}]({a.get('url','#')})  \n"
                                f"<span style='color:#888;font-size:11px'>{a.get('site') or a.get('publisher','')} · {a.get('publishedDate','')[:16]}</span>",
                                unsafe_allow_html=True)


# ============================= 7 · SECTOR =============================
with tabs[6]:
    st.subheader("Sector performance")

    @st.cache_data(ttl=300, show_spinner=False)
    def sector_returns(symbols: tuple, key: str) -> dict:
        q = batch_quote(symbols, key)
        if not q:
            # don't cache a failed fetch — caller catches and shows a retry hint
            raise RuntimeError("no sector quotes — likely FMP rate limit")
        out = {}
        for s in symbols:
            h = hist(s, YTD_FROM, False, key)
            d = (q.get(s, {}) or {}).get("changePercentage")
            w = y = None
            if not h.empty:
                last, base = h["price"].iloc[-1], h["price"].iloc[0]
                y = (last / base - 1) * 100 if base else None
                if len(h) >= 6:
                    w = (last / h["price"].iloc[-6] - 1) * 100
            out[s] = {"d": d, "w": w, "y": y}
        return out

    def bar(mp, store, key, title):
        labels = [s for s, _ in mp]
        vals = [store.get(s, {}).get(key) for s in labels]
        names = [nm for _, nm in mp]
        fig = go.Figure(go.Bar(x=labels, y=vals, customdata=names,
                               marker_color=[GREEN if (v or 0) >= 0 else RED for v in vals],
                               hovertemplate="%{x} · %{customdata}<br>%{y:.2f}%<extra></extra>"))
        fig.update_layout(height=230, margin=dict(l=0, r=0, t=24, b=0), title=title,
                          yaxis_ticksuffix="%")
        return fig

    with st.spinner("Loading sector data…"):
        try:
            en_store = sector_returns(tuple(s for s, _ in ENERGY_MAP), KEY)
            sp_store = sector_returns(tuple(s for s, _ in SP_MAP), KEY)
        except Exception:
            en_store, sp_store = {}, {}
            st.warning("Sector quotes unavailable right now — most likely the FMP per-minute "
                       "rate limit after the initial load. Wait ~1 min and reload; nothing is cached from this failure.")

    st.markdown("**Energy complex — returns**")
    c = st.columns(3)
    c[0].plotly_chart(bar(ENERGY_MAP, en_store, "d", "Daily %"), use_container_width=True)
    c[1].plotly_chart(bar(ENERGY_MAP, en_store, "w", "Weekly %"), use_container_width=True)
    c[2].plotly_chart(bar(ENERGY_MAP, en_store, "y", "YTD %"), use_container_width=True)

    st.markdown("**S&P 500 sectors — returns**")
    c = st.columns(3)
    c[0].plotly_chart(bar(SP_MAP, sp_store, "d", "Daily %"), use_container_width=True)
    c[1].plotly_chart(bar(SP_MAP, sp_store, "w", "Weekly %"), use_container_width=True)
    c[2].plotly_chart(bar(SP_MAP, sp_store, "y", "YTD %"), use_container_width=True)
    st.caption(" · ".join(f"**{s}** {nm}" for s, nm in SP_MAP))


# ============================= ★ RECOMMEND =============================
with tabs[7]:
    st.subheader("Recommendation engine")
    sec = st.selectbox("Sector", ["All"] + SECTORS, key="rec")
    if st.button("Generate", key="rec_go"):
        pool = [u for u in LIVE if sec == "All" or u["s"] == sec]

        def tscore(u):
            q = QUOTES.get(u["t"], {})
            price = q.get("price") or 0
            yh, yl = q.get("yearHigh") or 0, q.get("yearLow") or 0
            p52 = (price - yl) / (yh - yl) if yh > yl else 0.5
            v50 = price / q["priceAvg50"] - 1 if q.get("priceAvg50") else 0
            v200 = price / q["priceAvg200"] - 1 if q.get("priceAvg200") else 0
            return p52 * 0.4 + max(-.3, min(.3, v50)) * 1.2 + max(-.3, min(.3, v200)) * 1.0

        for u in pool:
            u["_ts"] = tscore(u)
        short = sorted(pool, key=lambda u: u["_ts"], reverse=True)[:14]
        with st.spinner("Scoring valuation…"):
            for u in short:
                m = key_metrics_ttm(u["t"], KEY)
                s = 0.0
                ev = km_get(m, "evToEBITDATTM", "enterpriseValueOverEBITDATTM")
                fcf = km_get(m, "freeCashFlowYieldTTM")
                nd = km_get(m, "netDebtToEBITDATTM")
                roe = km_get(m, "returnOnEquityTTM", "roeTTM")
                if ev and ev > 0:
                    s += max(-1, min(1, (8 - ev) / 8))
                if fcf is not None:
                    s += max(-1, min(1, fcf * 10))
                if nd is not None:
                    s += max(-1, min(1, (1.5 - nd) / 2))
                if roe is not None:
                    s += max(-1, min(1, roe * 4))
                u["_vs"] = s / 4
                u["_m"] = m
                u["_comp"] = u["_ts"] * 0.5 + u["_vs"] * 0.9
        short.sort(key=lambda u: u["_comp"], reverse=True)
        top = short[0]
        q = QUOTES.get(top["t"], {})
        st.success(f"★ **Top idea: {top['t']}** ({top['s']}) — {top['n']} · {fnum(q.get('price'))} "
                   f"({pct(q.get('changePercentage'))}) · score {top['_comp']:.2f}")
        ogtable(pd.DataFrame([{
            "Ticker": u["t"], "Sector": u["s"], "Name": u["n"],
            "Price": QUOTES.get(u["t"], {}).get("price"),
            "Daily%": QUOTES.get(u["t"], {}).get("changePercentage"),
            "EV/EBITDA": km_get(u.get("_m", {}), "evToEBITDATTM", "enterpriseValueOverEBITDATTM"),
            "Score": round(u["_comp"], 2),
        } for u in short]), {
            "Ticker": "tk", "Sector": "text", "Name": "text",
            "Price": "num", "Daily%": "pct", "EV/EBITDA": "x", "Score": "num",
        })
        st.caption("Educational screen — momentum (price vs 50/200-day MA, 52-week position) blended with TTM valuation. Not investment advice.")


# ============================= 📰 BRIEFING =============================
with tabs[8]:
    st.subheader(f"Daily briefing · {dt.datetime.now():%B %d, %Y}")

    # 1) Show the scheduled 7am morning briefing.md if it's in the repo
    bpath = None
    for cand in [pathlib.Path(__file__).with_name("briefing.md"),
                 pathlib.Path(__file__).parent.parent / "briefing.md"]:
        if cand.exists():
            bpath = cand
            break
    if bpath:
        with st.expander("Morning briefing (web-search narrative from the 7am scheduled task)", expanded=True):
            st.markdown(render_brief(bpath.read_text(encoding="utf-8")), unsafe_allow_html=True)
        st.caption("Below: a live, data-driven snapshot generated on load.")

    # 2) Market at a glance (live, from quotes)
    st.markdown("#### Market at a glance")
    bench = [("USO", "Crude (USO)"), ("BNO", "Brent (BNO)"), ("UNG", "Nat gas (UNG)"), ("SPY", "S&P 500"),
             ("XLE", "Energy (XLE)"), ("XOP", "E&P (XOP)"), ("XES", "Equip/Svc (XES)"), ("CRAK", "Refiners (CRAK)")]
    bq = quotes_for(tuple(s for s, _ in bench), KEY)
    if not bq:
        st.warning("Benchmark quotes unavailable — most likely the FMP per-minute rate limit "
                   "after loading the universe. Wait ~1 min and reload; this failure is not cached. "
                   "If it persists, check the ETF-quote rows in the key diagnostics (clear key and reload to see them).")
    bcols = st.columns(4)
    for i, (s, nm) in enumerate(bench):
        q = bq.get(s, {}) or QUOTES.get(s, {})
        bcols[i % 4].metric(nm, fnum(q.get("price")), pct(q.get("changePercentage")))
    comm = commodities(KEY)
    cl = (comm.get("CLUSD") or {}).get("price")
    rb = (comm.get("RBUSD") or {}).get("price")
    ho = (comm.get("HOUSD") or {}).get("price")
    if cl and rb and ho:
        st.caption(f"Spot 3-2-1 crack ≈ **{(2*rb + ho)/(3*cl):.3f}**  ·  WTI {fnum(cl)} · RBOB {fnum(rb)} · Heating oil {fnum(ho)}")

    # 3) Today's movers (from the universe)
    st.markdown("#### Today's movers")
    mv = [(u["t"], u["n"], u["s"], QUOTES.get(u["t"], {}).get("changePercentage"))
          for u in LIVE if QUOTES.get(u["t"], {}).get("changePercentage") is not None]
    mv.sort(key=lambda r: r[3], reverse=True)
    ups, downs = mv[:5], mv[-5:][::-1]
    mc1, mc2 = st.columns(2)
    mc1.markdown("**Top gainers**")
    for t_, n_, s_, ch in ups:
        mc1.markdown(f"- **{t_}** · {s_} · <span style='color:#137a4b;font-weight:600'>{ch:+.2f}%</span> — {n_}", unsafe_allow_html=True)
    mc2.markdown("**Top decliners**")
    for t_, n_, s_, ch in downs:
        mc2.markdown(f"- **{t_}** · {s_} · <span style='color:#c0392b;font-weight:600'>{ch:+.2f}%</span> — {n_}", unsafe_allow_html=True)

    # 4) Stocks to watch — cheap-and-out-of-favour vs momentum leaders
    st.markdown("#### Stocks to watch")
    below200 = [(u["t"], u["n"], QUOTES[u["t"]]["price"] / QUOTES[u["t"]]["priceAvg200"] - 1)
                for u in LIVE
                if QUOTES.get(u["t"], {}).get("priceAvg200") and QUOTES[u["t"]].get("price")]
    below200.sort(key=lambda r: r[2])
    watch = below200[:5]
    if watch:
        st.markdown("Trading furthest **below** their 200-day average (value / contrarian watch):")
        for t_, n_, d in watch:
            col = "#137a4b" if d >= 0 else "#c0392b"
            st.markdown(f"- **{t_}** — <span style='color:{col};font-weight:600'>{d*100:+.1f}%</span> vs 200-day · {n_}",
                        unsafe_allow_html=True)

    # 5) Oil & gas headlines
    st.markdown("#### Oil & gas headlines")
    OIL_KW = ("oil", "crude", "gas", "lng", "opec", "wti", "brent", "petroleum", "refin",
              "shale", "drilling", "pipeline", "barrel", "gasoline", "diesel", "energy")
    uni = {u["t"] for u in UNIVERSE}
    majors = [u["t"] for u in sorted(LIVE, key=lambda u: QUOTES.get(u["t"], {}).get("marketCap") or 0, reverse=True)[:25]]
    arr = list(stock_news(tuple(majors), KEY, 50))
    for a in general_news(KEY, 50):
        txt = f"{a.get('title','')} {a.get('text','')}".lower()
        if any(k in txt for k in OIL_KW):
            arr.append(a)
    arr = [a for a in arr if (not a.get("symbol")) or a.get("symbol", "").upper() in uni]
    seen, items = set(), []
    for a in sorted(arr, key=lambda a: a.get("publishedDate", ""), reverse=True):
        k = a.get("url") or a.get("title")
        if k and k not in seen:
            seen.add(k)
            items.append(a)
    if not items:
        st.caption("No headlines returned (the news endpoint may not be on your FMP plan).")
    for a in items[:12]:
        st.markdown(f"[{a.get('title','(untitled)')}]({a.get('url','#')})  \n"
                    f"<span style='color:#888;font-size:11px'>{a.get('site') or a.get('publisher','')} · {a.get('publishedDate','')[:16]}</span>",
                    unsafe_allow_html=True)
    st.caption("Live data-driven snapshot from FMP. Educational, not investment advice.")


# ============================= 🔎 SCREENERS =============================
H_FROM = (dt.date.today() - dt.timedelta(days=460)).isoformat()


def _cross_up(line, signal, within):
    """Bars since the most recent line-over-signal upward cross within `within` sessions; -1 if none."""
    a, b = np.asarray(line, float), np.asarray(signal, float)
    n = min(len(a), len(b))
    for k in range(within):
        i = n - 1 - k
        if i < 1:
            break
        if not (np.isnan(a[i]) or np.isnan(b[i]) or np.isnan(a[i - 1]) or np.isnan(b[i - 1])):
            if a[i] > b[i] and a[i - 1] <= b[i - 1]:
                return k
    return -1


@st.cache_data(ttl=600, show_spinner=False)
def dividend_screen_list(key: str) -> dict:
    """symbol -> lastAnnualDividend from the FMP company screener (Energy + Basic Materials)."""
    out = {}
    for sec in ("Energy", "Basic Materials"):
        try:
            arr = _get(FMP + f"company-screener?sector={sec.replace(' ', '%20')}"
                             f"&dividendMoreThan=0.01&isActivelyTrading=true&limit=1000&apikey=" + key) or []
            for c in arr:
                if c.get("symbol"):
                    out[c["symbol"]] = c.get("lastAnnualDividend")
        except Exception:
            continue
    return out


@st.cache_data(ttl=600, show_spinner=False)
def dividends_paid(symbol: str, key: str, limit: int = 60) -> list:
    try:
        return _get(FMP + f"dividends?symbol={symbol}&limit={limit}&apikey=" + key) or []
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def latest_ma(key: str, limit: int = 100) -> list:
    for path in ("mergers-acquisitions-latest?page=0", "latest-mergers-acquisitions?page=0"):
        try:
            arr = _get(FMP + path + f"&limit={limit}&apikey=" + key)
            if arr:
                return arr
        except Exception:
            continue
    return []


@st.cache_data(ttl=600, show_spinner=False)
def stock_news_from(symbols: tuple, frm: str, key: str, limit: int = 100) -> list:
    try:
        return _get(FMP + "news/stock?symbols=" + ",".join(symbols)
                    + f"&from={frm}&limit={limit}&apikey=" + key) or []
    except Exception:
        return []


def _mcap(t):
    return (QUOTES.get(t) or {}).get("marketCap") or 0


def _daily(t):
    return (QUOTES.get(t) or {}).get("changePercentage")


def scr_momentum(prog):
    """Above 200d MA + RSI(14) 40–60 + MACD bullish crossover within 10 sessions."""
    cand = [u for u in LIVE if (QUOTES.get(u["t"]) or {}).get("priceAvg200")
            and QUOTES[u["t"]].get("price") and QUOTES[u["t"]]["price"] > QUOTES[u["t"]]["priceAvg200"]]
    above = len(cand)
    cand.sort(key=lambda u: (QUOTES[u["t"]].get("price") or 0) * (QUOTES[u["t"]].get("volume") or 0), reverse=True)
    cand = cand[:60]
    res = []
    for i, u in enumerate(cand):
        prog((i + 1) / max(1, len(cand)))
        h = hist(u["t"], H_FROM, True, KEY)
        if h.empty or len(h) < 60:
            continue
        cl = h["close"].astype(float)
        r = float(rsi(cl).iloc[-1])
        if not (40 <= r <= 60):
            continue
        line, signal, histo = macd(cl)
        if line.iloc[-1] <= signal.iloc[-1]:
            continue
        k = _cross_up(line.values, signal.values, 10)
        if k < 0:
            continue
        q = QUOTES[u["t"]]
        res.append({"Ticker": u["t"], "Name": u["n"], "Sector": u["s"], "Price": q.get("price"),
                    "Daily%": _daily(u["t"]), "vs 200d %": (q["price"] / q["priceAvg200"] - 1) * 100,
                    "RSI(14)": r, "Cross (d ago)": k, "MACD hist": float(histo.iloc[-1])})
    res.sort(key=lambda x: (x["Cross (d ago)"], -x["vs 200d %"]))
    note = (f"{len(res)} pass out of the 60 most liquid above-200d names scanned ({above} names trade above "
            f"their 200-day). RSI(14) must sit in 40–60 and the MACD(12,26,9) line must have crossed above "
            f"its signal within the last 10 sessions and still be above it.")
    return (pd.DataFrame(res[:10]), {"Ticker": "tk", "Name": "text", "Sector": "text", "Price": "num",
                                     "Daily%": "pct", "vs 200d %": "pct", "RSI(14)": "num",
                                     "Cross (d ago)": "int", "MACD hist": "num"}, note)


def scr_dividend(prog):
    """Yield > 3% + long-term payout uptrend; royalty trusts / MLPs excluded."""
    dm = dividend_screen_list(KEY)
    noroy = re.compile(r"royalty|trust|partners|\bl\.?p\.?\b", re.I)
    cand = []
    for u in LIVE:
        d = dm.get(u["t"])
        q = QUOTES.get(u["t"]) or {}
        if d and d > 0 and q.get("price") and not noroy.search(u["n"] or ""):
            y = d / q["price"] * 100
            if y > 3:
                cand.append((u, q, d, y))
    cand.sort(key=lambda x: x[3], reverse=True)
    cand = cand[:45]  # history-check the 45 highest yielders so steady growers aren't crowded out
    res = []
    for i, (u, q, d, y) in enumerate(cand):
        prog((i + 1) / max(1, len(cand)))
        dv = dividends_paid(u["t"], KEY)
        if len(dv) < 8:
            continue
        by = {}
        for row in dv:
            yr = str(row.get("date", ""))[:4]
            if yr.isdigit():
                by[int(yr)] = by.get(int(yr), 0) + (row.get("adjDividend") or row.get("dividend") or 0)
        now_y = dt.date.today().year
        yrs = sorted(k for k in by if now_y - 10 <= k < now_y)
        if len(yrs) < 4:
            continue
        first, last = by[yrs[0]], by[yrs[-1]]
        a3 = sum(by[k] for k in yrs[:3]) / min(3, len(yrs))
        b3 = sum(by[k] for k in yrs[-3:]) / min(3, len(yrs))
        if not (b3 > a3 and last >= first):
            continue
        cagr = ((last / first) ** (1 / (len(yrs) - 1)) - 1) * 100 if first > 0 else None
        res.append({"Ticker": u["t"], "Name": u["n"], "Sector": u["s"], "Price": q.get("price"),
                    "Yield %": y, "Div/sh (ann.)": d, "Payout CAGR %": cagr, "History (yrs)": len(yrs)})
    res.sort(key=lambda x: x["Yield %"], reverse=True)
    note = ("Yield = last indicated annual dividend ÷ current price, must exceed 3%. Royalty trusts, royalty "
            "partners and MLPs/LPs are excluded — their distributions are pass-through rather than a managed "
            "corporate dividend. Payout-history test on the 45 highest-yielding qualifiers: the recent 3-year "
            "average payout must exceed the earliest 3-year average and the latest full year must be ≥ the "
            "first, over up to 10 full years (payout growth is a sturdier test than a rising yield, which can "
            "just reflect a falling share price).")
    return (pd.DataFrame(res[:10]), {"Ticker": "tk", "Name": "text", "Sector": "text", "Price": "num",
                                     "Yield %": "pct", "Div/sh (ann.)": "num", "Payout CAGR %": "pct",
                                     "History (yrs)": "int"}, note)


def scr_value(prog):
    """TTM EV/EBITDA at the low end of own 10y range AND FCF yield at the high end."""
    cand = [u for u in LIVE if _mcap(u["t"]) > 1e9]
    cand.sort(key=lambda u: _mcap(u["t"]), reverse=True)
    cand = cand[:60]
    res = []
    for i, u in enumerate(cand):
        prog((i + 1) / max(1, len(cand)))
        ann = key_metrics(u["t"], KEY, limit=10)
        ttm = key_metrics_ttm(u["t"], KEY)
        if len(ann) < 5 or not ttm:
            continue
        ev_h = [km_get(y, "evToEBITDA", "enterpriseValueOverEBITDA") for y in ann]
        ev_h = [v for v in ev_h if v is not None and np.isfinite(v) and v > 0]
        fc_h = [y.get("freeCashFlowYield") for y in ann]
        fc_h = [v for v in fc_h if v is not None and np.isfinite(v)]
        ev = km_get(ttm, "evToEBITDATTM", "enterpriseValueOverEBITDATTM")
        fc = km_get(ttm, "freeCashFlowYieldTTM")
        if len(ev_h) < 5 or len(fc_h) < 5 or not ev or ev <= 0 or fc is None:
            continue
        p_e = max(0, min(1, (ev - min(ev_h)) / ((max(ev_h) - min(ev_h)) or 1)))
        p_f = max(0, min(1, (fc - min(fc_h)) / ((max(fc_h) - min(fc_h)) or 1)))
        res.append({"Ticker": u["t"], "Name": u["n"], "Sector": u["s"], "Mkt cap $B": _mcap(u["t"]) / 1e9,
                    "EV/EBITDA": ev, "EV pos %": p_e * 100, "FCF yield %": fc * 100, "FCF pos %": p_f * 100,
                    "Screen": "pass" if (p_e <= 0.35 and p_f >= 0.65) else "near",
                    "_score": (p_e <= 0.35 and p_f >= 0.65, p_f - p_e)})
    res.sort(key=lambda x: x["_score"], reverse=True)
    np_pass = sum(1 for r in res if r["Screen"] == "pass")
    for r in res:
        r.pop("_score", None)
    note = (f"{np_pass} strict passes: TTM EV/EBITDA in the bottom 35% of the stock's own 10-year range AND "
            f"TTM FCF yield in the top 35% of its range. pos = where today sits in that 10-year range "
            f"(0% = decade low, 100% = decade high). 'Near' rows fill remaining slots ranked by "
            f"(FCF pos − EV pos). Scanned the 60 largest names (>$1B cap, ≥5 yrs of history).")
    return (pd.DataFrame(res[:10]), {"Ticker": "tk", "Name": "text", "Sector": "text", "Mkt cap $B": "num",
                                     "EV/EBITDA": "x", "EV pos %": "num", "FCF yield %": "num",
                                     "FCF pos %": "num", "Screen": "text"}, note)


def scr_event(prog):
    """Order wins / M&A in the past month: news keyword scan + SEC M&A filings, ranked by hits."""
    frm = (dt.date.today() - dt.timedelta(days=31)).isoformat()
    uni = {u["t"] for u in LIVE}
    ma = latest_ma(KEY)
    ma_hits = [m for m in ma if str(m.get("transactionDate", "")) >= frm
               and (m.get("symbol") in uni or m.get("targetedSymbol") in uni)]
    majors = sorted(LIVE, key=lambda u: _mcap(u["t"]), reverse=True)[:60]
    kw = re.compile(r"(awarded|award|wins |win |secures|contract|order (worth|valued|book)|merger|acquisition"
                    r"|acquires|to acquire|agrees to buy|to buy|takeover|buyout|bid for|combine|all-stock"
                    r"|\bFID\b|final investment decision|supply agreement|offtake|charter)", re.I)
    news = []
    groups = [majors[i:i + 20] for i in range(0, len(majors), 20)]
    for gi, g in enumerate(groups):
        prog((gi + 1) / (len(groups) + 1))
        news.extend(stock_news_from(tuple(u["t"] for u in g), frm, KEY))
    hits = [a for a in news if a and a.get("symbol") in uni and kw.search(a.get("title") or "")]
    by_t = {}
    for a in hits:
        by_t.setdefault(a["symbol"], {"items": [], "ma": None})["items"].append(a)
    for m in ma_hits:
        t = m.get("symbol") if m.get("symbol") in uni else m.get("targetedSymbol")
        by_t.setdefault(t, {"items": [], "ma": None})["ma"] = m
    prog(1.0)
    ranked = sorted(by_t.items(), key=lambda kv: (3 if kv[1]["ma"] else 0) + len(kv[1]["items"]), reverse=True)
    res = []
    for t, d in ranked[:10]:
        u = U_BY_T.get(t, {})
        it = d["items"][0] if d["items"] else None
        m = d["ma"]
        if it:
            head = f'<a href="{it.get("url", "#")}" target="_blank" rel="noopener">{it.get("title", "")}</a>'
            date = str(it.get("publishedDate", ""))[:10]
        elif m:
            head = (f'<a href="{m.get("link", "#")}" target="_blank" rel="noopener">SEC filing: '
                    f'{m.get("companyName", "")} / {m.get("targetedCompanyName", "")}</a>')
            date = m.get("transactionDate", "")
        else:
            head, date = "–", ""
        res.append({"Ticker": t, "Sector": u.get("s", ""), "Daily%": _daily(t),
                    "Event": "M&A" if m else "order/news", "Headline / filing": head, "Date": date})
    note = ("Scans the past 31 days: stock news for the 60 largest names plus SEC M&A filings, keyword-filtered "
            "and ranked by keyword hits (an SEC M&A filing counts as +3). Unlike the artifact version there is "
            "no AI significance pass here, so expect a little more noise.")
    return (pd.DataFrame(res), {"Ticker": "tk", "Sector": "text", "Daily%": "pct", "Event": "text",
                                "Headline / filing": "text", "Date": "text"}, note)


def scr_leader(prog):
    """Sector leader + cost leader + low leverage + cheap vs own 10y history."""
    secs = sorted({u["s"] for u in LIVE if u["s"] != "Other"})
    cand = []
    for s in secs:
        top = sorted([u for u in LIVE if u["s"] == s and _mcap(u["t"]) > 0],
                     key=lambda u: _mcap(u["t"]), reverse=True)[:4]
        cand.extend((u, i + 1) for i, u in enumerate(top))
    res = []
    for i, (u, rank) in enumerate(cand):
        prog((i + 1) / max(1, len(cand)))
        ann = key_metrics(u["t"], KEY, limit=10)
        ttm = key_metrics_ttm(u["t"], KEY)
        ev = km_get(ttm, "evToEBITDATTM", "enterpriseValueOverEBITDATTM")
        es = km_get(ttm, "evToSalesTTM")
        nd = km_get(ttm, "netDebtToEBITDATTM")
        if not ev or ev <= 0:
            continue
        margin = es / ev * 100 if es and es > 0 else None
        p_e = None
        if len(ann) >= 5:
            h = [km_get(y, "evToEBITDA", "enterpriseValueOverEBITDA") for y in ann]
            h = [v for v in h if v is not None and np.isfinite(v) and v > 0]
            if len(h) >= 5:
                p_e = max(0, min(1, (ev - min(h)) / ((max(h) - min(h)) or 1)))
        res.append({"u": u, "rank": rank, "ev": ev, "nd": nd, "margin": margin, "p_e": p_e})
    by_sec = {}
    for r in res:
        by_sec.setdefault(r["u"]["s"], []).append(r)
    for r in res:
        ms = sorted(x["margin"] for x in by_sec[r["u"]["s"]] if x["margin"] is not None)
        med = ms[len(ms) // 2] if ms else None
        r["cost"] = r["margin"] is not None and med is not None and r["margin"] >= med
        r["score"] = ((1 if r["rank"] == 1 else 0.6 if r["rank"] == 2 else 0.35)
                      + (0.8 if r["cost"] else 0)
                      + (0 if r["nd"] is None else 0.6 if r["nd"] < 1 else 0.4 if r["nd"] < 1.5
                         else 0 if r["nd"] < 2.5 else -0.5)
                      + ((1 - r["p_e"]) if r["p_e"] is not None else 0.3))
        r["pass"] = (r["rank"] <= 2 and r["cost"] and r["nd"] is not None and r["nd"] < 1.5
                     and r["p_e"] is not None and r["p_e"] <= 0.4)
    res.sort(key=lambda r: (r["pass"], r["score"]), reverse=True)
    np_pass = sum(1 for r in res if r["pass"])
    rows = [{"Ticker": r["u"]["t"], "Name": r["u"]["n"], "Sector rank": f'{r["u"]["s"]} #{r["rank"]}',
             "Mkt cap $B": _mcap(r["u"]["t"]) / 1e9,
             "EBITDA margin %": r["margin"], "Cost leader": "✓" if r["cost"] else "",
             "NetDebt/EBITDA": r["nd"], "EV/EBITDA": r["ev"],
             "EV pos %": r["p_e"] * 100 if r["p_e"] is not None else None,
             "Screen": "pass" if r["pass"] else "near"} for r in res[:10]]
    note = (f"{np_pass} strict passes. Candidates = top 4 by market cap in each sub-sector. Pass = top-2 "
            f"sector leader + EBITDA margin at/above cohort median (cost leadership) + Net Debt/EBITDA < 1.5x "
            f"+ EV/EBITDA in the bottom 40% of its own 10-yr range (EV pos: 0% = decade-low multiple). "
            f"EBITDA margin is derived as EV/Sales ÷ EV/EBITDA.")
    return (pd.DataFrame(rows), {"Ticker": "tk", "Name": "text", "Sector rank": "text", "Mkt cap $B": "num",
                                 "EBITDA margin %": "num", "Cost leader": "text", "NetDebt/EBITDA": "x",
                                 "EV/EBITDA": "x", "EV pos %": "num", "Screen": "text"}, note)


with tabs[9]:
    st.subheader("Screeners")
    st.caption("Five systematic screens over the live universe, each listing its top 10. The momentum screen "
               "computes RSI and MACD from daily price history; valuation screens compare today's TTM metrics "
               "with each stock's own 10-year range; the dividend screen tests payout history; the event screen "
               "scans a month of news and SEC M&A filings.")
    _SCREENS = {"1 · Momentum": scr_momentum, "2 · High Dividend": scr_dividend, "3 · Value": scr_value,
                "4 · Event-Driven": scr_event, "5 · Quality Leader": scr_leader}
    _pick = st.radio("Screen", list(_SCREENS), horizontal=True, key="scr_pick", label_visibility="collapsed")
    if st.button("Run screen", key="scr_go"):
        _bar = st.progress(0.0)
        try:
            with st.spinner("Screening… (first run fetches per-name data and can take a minute)"):
                _df, _cols, _note = _SCREENS[_pick](lambda f: _bar.progress(min(1.0, f)))
        finally:
            _bar.empty()
        if _df.empty:
            st.info("No names pass this screen today (or the required FMP endpoints aren't on your plan).")
        else:
            st.markdown(f"**{_pick} — top 10**")
            ogtable(_df, _cols)
        st.caption(_note + " Educational screen, not investment advice.")
