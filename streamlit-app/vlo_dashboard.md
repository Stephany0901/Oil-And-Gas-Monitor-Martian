# VLO Crack-Spread Trading Model

**Data through 2026-10-23** · 1950 bars · generated 2026-10-26 02:56 UTC

> Long-only refinery-margin mean reversion on Valero. Buy when the de-RINs Profit Index is statistically high *and* rising; exit after three consecutive signal-free sessions. **Signal is read off the previous session’s close; the position is filled at the next morning’s open.**

---

## Live signal — 2026-10-23

| | |
|---|---|
| Signal | 🔴 short condition — *not traded, long only* |
| Position | **FLAT** |
| Last trade | 2026-10-14 @ $459.79 → 2026-10-19 @ $445.76 · 3 bars · **-3.19%** (expire) |
| VLO close | **$419.28** |
| VLO open | *not published yet* |
| Profit Index | **37.87** $/bbl (RBOB 3.04 · HO 72.70) |
| Z-score | **-2.40** (entry > +1.0) — fail |
| Momentum (30d) | **-9.23** $/bbl (entry > +0.5) — fail |
| Crack → VLO linkage | 0.28 (120d corr, diagnostic only) |

## Last 10 sessions

Profit Index `▅██▆▅▅▅▂▂▁`  42.65 → 37.87

| Date | Open | Close | Profit Index | RBOB | HO | z | Momentum | Signal |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| 2026-10-12 | 440.26 | 436.00 | 42.65 | 12.91 | 72.39 | -0.70 | -7.13 | · |
| 2026-10-13 | 440.00 | 456.46 | 47.24 | 12.74 | 81.74 | +1.17 | +2.09 | 🟢 |
| 2026-10-14 | 459.79 | 459.78 | 46.71 | 12.92 | 80.49 | +0.88 | -0.72 | · |
| 2026-10-15 | 456.50 | 444.06 | 44.03 | 10.96 | 77.10 | -0.30 | -2.08 | · |
| 2026-10-16 | 447.34 | 444.71 | 43.22 | 10.06 | 76.37 | -0.68 | -2.25 | · |
| 2026-10-19 | 445.76 | 433.31 | 43.09 | 9.05 | 77.14 | -0.78 | -1.90 | · |
| 2026-10-20 | 433.58 | 433.42 | 42.62 | 7.55 | 77.69 | -1.04 | -2.44 | · |
| 2026-10-21 | 433.64 | 436.75 | 40.07 | 7.77 | 72.37 | -2.05 | -5.73 | · |
| 2026-10-22 | 439.55 | 426.28 | 39.92 | 5.32 | 74.51 | -1.92 | -7.48 | · |
| 2026-10-23 | — | 419.28 | 37.87 | 3.04 | 72.70 | -2.40 | -9.23 | · |

## Performance

Locked window (2022-07-01 onward), **next-day-open fill**, costs 7 bps per side:

| | Strategy | Buy & hold |
|---|---:|---:|
| Compound return | **+228.7%** | +288.3% |
| CAGR | **+31.8%** | +37.0% |
| Sharpe | **1.41** | 1.07 |
| Annualised vol | 21% | 36% |
| Max drawdown | **-17.8%** | -42.9% |
| Win rate | 60.6% | — |
| Closed trades | 33 | — |
| Average hold | 12.1 bars | — |

### Execution sensitivity

Same signal, same bars, same 33 trades — only the price moves.

| Execution | Sharpe | Compound | Max DD | Win rate |
|---|---:|---:|---:|---:|
| **Next-day open** *(adopted)* | 1.41 | +228.7% | -17.8% | 60.6% |
| Signal-day close *(the doc)* | 1.59 | +281.9% | -18.9% | 72.7% |
| Next-day close | 1.13 | +153.4% | -18.0% | 63.6% |

VLO gaps up the morning after a signal — the overnight close→open return averages **+0.27%** on entry bars against +0.07% on all bars — so the open fill pays up on entry and gives back on exit, **0.42% per trade** in all.

### Four windows — next-day-open fill

| Window | Period | Sharpe | Compound | Max DD | Trades |
|---|---|---:|---:|---:|---:|
| **doc** | in-sample, the locked window | **1.41** | +229% | -18% | 33 |
| **oos** | out-of-sample 2019-02 to 2022-06 | **1.02** | +146% | -28% | 32 |
| **live** | live regime | **1.44** | +196% | -18% | 28 |
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
- The **newest bar is provisional**. The last bar’s Profit Index carries ~$1.9/bbl of typical error and up to $6.6, biased high on the distillate leg. Do not act on a same-day print.
- The next-day-open fill needs an **Open column in the VLO export**. The daily export carries closes only; opens currently come from a one-off file and the archive.
- Returns are **price only** — no dividends, financing or borrow.
- Linkage is a **displayed diagnostic, not a gate**. Tested as an entry filter and rejected (selection-aware placebo p = 0.295).

---

*Generated by `mkmd.py` from `engine5.py`. Numbers match the interactive dashboard by construction — both read the same panel.*
