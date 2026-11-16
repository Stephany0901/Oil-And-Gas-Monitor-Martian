# VLO Crack-Spread Trading Model

**Data through 2026-11-11** · 1963 bars · generated 2026-11-16 01:45 UTC

> Long-only refinery-margin mean reversion on Valero. Buy when the de-RINs Profit Index is statistically high *and* rising; exit after three consecutive signal-free sessions. **Signal is read off the previous session's close; the position is filled at the next morning's open.**

---

## Live signal — 2026-11-11

| | |
|---|---|
| Signal | 🔴 short condition — *not traded, long only* |
| Position | **FLAT** |
| Last trade | 2026-10-14 @ $459.79 → 2026-10-19 @ $445.76 · 3 bars · **-3.19%** (expire) |
| VLO close | **$363.71** |
| VLO open | $357.17 |
| Profit Index | **34.73** $/bbl (RBOB 2.36 · HO 67.10) |
| Z-score | **-1.30** (entry > +1.0) — fail |
| Momentum (30d) | **-15.47** $/bbl (entry > +0.5) — fail |
| Distance to signal | next bar's PI must reach **45.98** from 34.73 — momentum leg binds (z leg 43.55, momentum leg 45.98) |
| Crack → VLO linkage | 0.29 (120d corr, diagnostic only) |

## Last 10 sessions

Profit Index `▂▃▁█▄▄▃▄▁▂`  34.30 → 34.73

| Date | Open | Close | Profit Index | RBOB | HO | z | Momentum | Signal |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| 2026-10-29 | 392.05 | 384.57 | 34.30 | 2.81 | 65.79 | -2.24 | -18.54 | · |
| 2026-10-30 | 387.10 | 399.66 | 34.83 | 2.92 | 66.75 | -1.91 | -18.88 | · |
| 2026-11-02 | 392.68 | 381.46 | 34.00 | 2.83 | 65.16 | -2.15 | -18.52 | · |
| 2026-11-03 | 378.90 | 387.65 | 37.75 | 5.23 | 70.26 | -1.10 | -17.28 | · |
| 2026-11-04 | 378.30 | 365.34 | 35.48 | 5.41 | 65.55 | -1.62 | -15.28 | · |
| 2026-11-05 | 367.01 | 351.23 | 35.60 | 3.53 | 67.67 | -1.47 | -9.41 | · |
| 2026-11-06 | 353.23 | 346.45 | 35.19 | 3.77 | 66.61 | -1.46 | -7.66 | · |
| 2026-11-09 | 344.50 | 356.75 | 35.81 | 4.25 | 67.37 | -1.20 | -6.39 | · |
| 2026-11-10 | 346.08 | 350.71 | 34.23 | 3.50 | 64.96 | -1.49 | -10.35 | · |
| 2026-11-11 | 357.17 | 363.71 | 34.73 | 2.36 | 67.10 | -1.30 | -15.47 | · |

## Performance

Locked window (2022-07-01 onward), **next-day-open fill**, costs 7 bps per side:

| | Strategy | Buy & hold |
|---|---:|---:|
| Compound return | **+228.7%** | +236.8% |
| CAGR | **+31.3%** | +32.1% |
| Sharpe | **1.40** | 0.96 |
| Annualised vol | 21% | 36% |
| Max drawdown | **-17.8%** | -42.9% |
| Win rate | 60.6% | — |
| Closed trades | 33 | — |
| Average hold | 12.1 bars | — |

### Four windows — next-day-open fill

| Window | Period | Sharpe | Compound | Max DD | Trades |
|---|---|---:|---:|---:|---:|
| **doc** | in-sample, the locked window | **1.40** | +229% | -18% | 33 |
| **oos** | out-of-sample 2019-02 to 2022-06 | **1.02** | +146% | -28% | 32 |
| **live** | live regime | **1.43** | +196% | -18% | 28 |
| **full** | all history | **1.18** | +709% | -28% | 65 |

Worst window Sharpe: **1.02**. `oos` is the only window disjoint from the one the parameters were chosen on. Circular-shift placebo on the open fill: **p = 0.021**.

## Recent trades

| Entry | Price | Exit | Price | Bars | Net | Why |
|---|---:|---|---:|---:|---:|---|
| 2026-10-14 | $459.79 | 2026-10-19 | $445.76 | 3 | **-3.19%** | expire |
| 2026-09-16 | $391.68 | 2026-09-29 | $381.57 | 9 | **-2.72%** | expire |
| 2026-08-11 | $315.25 | 2026-09-11 | $388.00 | 22 | **+22.94%** | expire |
| 2026-06-25 | $240.70 | 2026-08-05 | $315.00 | 28 | **+30.73%** | expire |
| 2026-05-08 | $235.21 | 2026-05-26 | $243.26 | 11 | **+3.28%** | expire |
| 2026-05-01 | $250.40 | 2026-05-06 | $242.72 | 3 | **-3.21%** | expire |
| 2026-04-22 | $236.40 | 2026-04-30 | $245.88 | 6 | **+3.87%** | expire |
| 2026-02-20 | $198.54 | 2026-04-21 | $226.70 | 41 | **+14.04%** | expire |

## Model specification

```
Profit Index  = 0.5 x RBOB crack + 0.5 x HO crack   (de-RINs, front month)
de-RINs crack = raw crack - 42 x RVO

z-score    month-aware, lookback 30, alignment capped at M2
momentum   PI(t) - PI(t-30), raw front month
entry      z > +1.0 AND momentum > +0.5
exit       signal absent for 3 consecutive bars
direction  long only        execution  NEXT-DAY OPEN
cost       7 bps per side
```

**Data integrity checks run on every refresh:** de-RINs reconstruction asserted against the workbook (worst diff 0.0e+00); RVO outlier quarantine (|ΔRVO| > 0.15); permanent archive union with cell-wise precedence so the panel can only grow; date-aligned revision check against the prior panel; open-price coverage check.

### Caveats

- The panel is **RVO-limited**: RVO CY01 prints one business day behind the raw cracks, so the last bar is normally T−1 of the crack data.
- The **newest bar is provisional**. The last bar's Profit Index carries ~$1.9/bbl of typical error and up to $6.6, biased high on the distillate leg. Do not act on a same-day print.
- Returns are **price only** — no dividends, financing or borrow.
- Linkage is a **displayed diagnostic, not a gate**. Tested as an entry filter and rejected (selection-aware placebo p = 0.295).
- The forward curve is likewise a diagnostic. Tested as a replacement index and as an agreement gate; both rejected (`vlo-forward-index-swap.md`, `vlo-forward-agreement-gate.md`).

---

*Generated by `mkmd.py` from `engine5.py`. Numbers match the interactive dashboard by construction — both read the same panel.*
