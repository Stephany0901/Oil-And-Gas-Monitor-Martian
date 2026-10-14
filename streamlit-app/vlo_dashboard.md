# VLO Crack-Spread Trading Model

**Data through 2026-10-13** · 1942 bars · generated 2026-10-14 03:56 UTC

> Long-only refinery-margin mean reversion on Valero. Buy when the de-RINs Profit Index is statistically high *and* rising; exit after three consecutive signal-free sessions.

---

## Live signal — 2026-10-13

| | |
|---|---|
| Signal | 🟢 **FIRING** |
| Position | **LONG** since 2026-10-13 @ $456.46 · **+0.0%** open |
| VLO close | **$456.46** |
| Profit Index | **47.24** $/bbl (RBOB 12.74 · HO 81.74) |
| Z-score | **+1.17** (entry > +1.0) — pass |
| Momentum (30d) | **+2.09** $/bbl (entry > +0.5) — pass |
| Crack → VLO linkage | 0.27 (120d corr, diagnostic only) |
| **Next bar** | PI must **rise to 47.93** (+0.69) to keep the signal alive — *momentum leg binds* |

### Distance to the signal boundary

Entry needs z > +1.0 **and** momentum > +0.5. Both rise monotonically with the next bar's
Profit Index, so a single level separates signal from no signal, and the binding leg sets it.

| Leg | Level the next bar needs | Why |
|---|---:|---|
| z-score | 47.01 | the 30-bar window's mean and sd move with the trial value |
| momentum | **47.93** | 30d-ago bar steps to 2026-09-01 at 47.43, plus the 0.5 minimum |
| **Binding** | **47.93** | +0.69 from today's 47.24 |

Today's signal is on, but the momentum window's back end steps forward tomorrow: an
**unchanged** Profit Index print would kill it. Three consecutive signal-free bars then
close the position — 0 of 3 used.

## Last 10 sessions

Profit Index `█▄▁▂▃▄▆▄▂▆`  50.20 → 47.24

| Date | Profit Index | RBOB | HO | M1−M2 | z | Momentum | VLO | Signal |
|---|---:|---:|---:|---:|---:|---:|---:|:--:|
| 2026-09-30 | 50.20 | 20.22 | 80.18 | +2.78 | +0.90 | +1.68 | 387.61 | · |
| 2026-10-01 | 45.48 | 17.80 | 73.15 | +1.64 | +0.62 | -1.55 | 408.46 | · |
| 2026-10-02 | 41.12 | 14.97 | 67.28 | +1.21 | -1.20 | -5.52 | 406.30 | · |
| 2026-10-05 | 42.69 | 14.80 | 70.58 | +1.64 | -0.55 | -4.71 | 419.33 | · |
| 2026-10-06 | 43.30 | 15.26 | 71.33 | +1.62 | -0.34 | -2.09 | 419.22 | · |
| 2026-10-07 | 44.78 | 15.27 | 74.30 | +1.51 | +0.27 | -2.65 | 424.10 | · |
| 2026-10-08 | 47.76 | 15.06 | 80.45 | +1.24 | +1.46 | -1.74 | 443.80 | · |
| 2026-10-09 | 44.50 | 14.36 | 74.63 | +0.67 | +0.06 | -3.98 | 433.75 | · |
| 2026-10-12 | 42.65 | 12.91 | 72.39 | +0.22 | -0.70 | -7.13 | 436.00 | · |
| 2026-10-13 | 47.24 | 12.74 | 81.74 | +1.37 | +1.17 | +2.09 | 456.46 | 🟢 |

## Performance

Locked window (2022-07-01 onward), costs 7 bps per side:

| | Strategy | Buy & hold |
|---|---:|---:|
| Compound return | **+292.3%** | +322.7% |
| CAGR | **+37.6%** | — |
| Sharpe | **1.63** | — |
| Annualised vol | 21% | — |
| Max drawdown | **-18.9%** | — |
| Win rate | 75.0% | — |
| Closed trades | 32 | — |
| Average hold | 12.4 bars | — |

### Four windows

| Window | Period | Sharpe | Compound | Max DD | Trades |
|---|---|---:|---:|---:|---:|
| **doc** | in-sample, the locked window | **1.63** | +292% | -19% | 32 |
| **oos** | out-of-sample 2019-02 to 2022-06 | **1.07** | +163% | -28% | 32 |
| **live** | live regime | **1.64** | +240% | -19% | 27 |
| **full** | all history | **1.31** | +930% | -28% | 64 |

Worst window Sharpe: **1.07**. `oos` is the only window disjoint from the one the parameters were chosen on.

## Recent trades

| Entry | Price | Exit | Price | Bars | Net | Why |
|---|---:|---|---:|---:|---:|---|
| 2026-09-15 | $397.04 | 2026-09-28 | $389.57 | 9 | **-2.02%** | expire |
| 2026-08-10 | $314.95 | 2026-09-10 | $385.43 | 22 | **+22.24%** | expire |
| 2026-06-24 | $242.43 | 2026-08-04 | $308.73 | 28 | **+27.21%** | expire |
| 2026-05-07 | $236.35 | 2026-05-22 | $246.96 | 11 | **+4.35%** | expire |
| 2026-04-30 | $252.58 | 2026-05-05 | $253.45 | 3 | **+0.20%** | expire |
| 2026-04-21 | $233.39 | 2026-04-29 | $251.30 | 6 | **+7.53%** | expire |
| 2026-02-19 | $199.24 | 2026-04-20 | $226.28 | 41 | **+13.43%** | expire |
| 2026-01-30 | $181.43 | 2026-02-04 | $197.41 | 3 | **+8.67%** | expire |
| 2026-10-13 | $456.46 | *open* | $456.46 | 0 | **+0.00%** | open |

## Model specification

```
Profit Index  = 0.5 x RBOB crack + 0.5 x HO crack   (de-RINs, front month)
de-RINs crack = raw crack - 42 x RVO

z-score    month-aware, lookback 30, alignment capped at M2
momentum   PI(t) - PI(t-30), raw front month
entry      z > +1.0 AND momentum > +0.5
exit       signal absent for 3 consecutive bars
direction  long only        execution  signal-day close
cost       7 bps per side
```

**Data integrity checks run on every refresh:** de-RINs reconstruction asserted against the workbook (worst diff 0.0e+00 over 1944 rows); RVO outlier quarantine (|ΔRVO| > 0.15); permanent archive union so the panel can only grow; date-aligned revision check against the prior panel.

### Caveats

- The panel is **RVO-limited**: RVO CY01 prints one business day behind the raw cracks, so the last bar is normally T−1 of the crack data.
- The **newest bar is provisional**. Measured against later settles, the last bar's Profit Index carries ~$1.9/bbl of typical error and up to $6.6, biased high on the distillate leg. Do not act on a same-day print.
- Returns are **price only** — no dividends, financing or borrow.
- Linkage is a **displayed diagnostic, not a gate**. Tested as an entry filter and rejected (selection-aware placebo p = 0.295).

---

*Generated by `mkmd.py` from `engine4.py`. Numbers match the interactive dashboard by construction — both read the same engine.*
