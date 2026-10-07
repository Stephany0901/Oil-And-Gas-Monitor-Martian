# EQT Hybrid Strategy

**Ticker:** EQT Corporation (NYSE: EQT)  
**Universe:** US natural gas E&P  
**Backtest:** Jan 2016 – Oct 2026 (daily, ~2,700 observations)

---

## Strategy Overview

A two-regime rules-based strategy on EQT stock, driven by Henry Hub natural gas prices.

| Window | Rule |
|--------|------|
| **Seasonal (Dec → May)** | Buy on last trading day of December; sell on last trading day of May |
| **Off-season (Jun → Nov)** | Enter when HH Z-score < −0.25 **AND** 1-day HH momentum < −$0.20 |

Open Z-score trades are closed at the seasonal entry date. The two regimes never overlap.

---

## Signal Logic

### Seasonal leg
- Entry: last business day of December each year
- Exit: last business day of May each year
- Transaction cost: 0.40% round-trip

### Z-score leg (off-season only)
- **Z-score**: 20-day rolling, M2-aware
- **M2-aware lookback**: days in the prior calendar month use the M2 (second-month) Henry Hub futures price instead of M1, avoiding roll distortion at month-end
- Entry trigger (day *t*): Z[t−1] < −0.25 AND (M1[t−1] − M1[t−2]) < −$0.20
- Exit: 10 consecutive days without entry signal
- Transaction cost: 0.20% per side (0.40% round-trip)

---

## Performance (2016–Oct 2026)

| Metric | Hybrid | EQT B&H |
|--------|--------|---------|
| Total Return | **+482%** | +81% |
| Annualised Sharpe | **0.608** | 0.353 |
| Max Drawdown | −63.0% | −88.5% |

### Annual Returns

| Year | Hybrid | B&H |
|------|--------|-----|
| 2016 | +24.9% | +23.0% |
| 2017 | −16.7% | −11.2% |
| 2018 | −11.9% | −40.8% |
| 2019 | +19.1% | −45.2% |
| 2020 | −1.2% | +22.7% |
| 2021 | +77.3% | +62.6% |
| 2022 | +90.6% | +55.0% |
| 2023 | +3.1% | +21.5% |
| 2024 | +27.0% | +18.5% |
| 2025 | +5.9% | +13.2% |
| 2026 YTD | +11.3% | −1.9% |

---

## Sharpe Comparison (2016–2026)

| Asset | Return | Sharpe | Max DD |
|-------|--------|--------|--------|
| MSFT B&H | +1,010% | 0.953 | −37% |
| QQQ B&H | +650% | 0.957 | −35% |
| SPY B&H | +361% | 0.894 | −34% |
| AMZN B&H | +705% | 0.754 | −56% |
| VLO B&H | +808% | 0.711 | −72% |
| **EQT Hybrid** | **+482%** | **0.608** | **−63%** |
| EQT B&H | +81% | 0.336 | −89% |

The hybrid nearly doubles EQT's Sharpe ratio and cuts max drawdown from 89% to 63%.

---

## Data Sources

- **HH M1 / M2**: NYMEX Henry Hub front-month and second-month futures (daily settlement)
- **EQT price**: Dividend-adjusted closing price (split-adjusted)
- **Tetco M-2**: Appalachian gas basis (Platts / NGI confirmed prices where available)

---

## Files

| File | Description |
|------|-------------|
| `eqt_hybrid_tab.py` | Streamlit tab — drop into your app and call `render_eqt_hybrid()` |
| `eqt_hybrid_dashboard.html` | Standalone dashboard — add to `public-website/` |
| `eqt_strategy.md` | This file |

### Adding to Streamlit `app.py`

```python
# 1. Copy eqt_hybrid_tab.py into your streamlit-app/ folder
# 2. In app.py, add a tab:

from eqt_hybrid_tab import render_eqt_hybrid

XLSX_PATH = r"path\to\hh eqt.xlsx"   # your 3-sheet HH M1/M2/EQT file

tab_vlo, tab_eqt, tab_other = st.tabs(["VLO", "EQT Hybrid", "..."])

with tab_eqt:
    render_eqt_hybrid(xlsx_path=XLSX_PATH)
```

---

## Disclaimers

- Backtest results are hypothetical and do not reflect actual trading.
- Transaction costs are estimates; slippage not modelled.
- Past performance does not guarantee future results.
- This is not investment advice.
