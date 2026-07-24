# Backtest results

Audience: anyone evaluating whether the tier multipliers in
[strategy.md](strategy.md) earn their complexity over plain dollar-cost
averaging (DCA). Indicator definitions — Market Value to Realized Value
(MVRV) and Short-Term Holder MVRV (STH-MVRV) — are in
[strategy.md](strategy.md). All figures below were produced on 2026-07-23 from the data
sources listed; `backtest.py` reproduces the headline comparison against live
data at any time.

## Data sources and validation

| Source | Series | Range used | Role |
|---|---|---|---|
| CoinMetrics community CSV | MVRV (`CapMVRVCur`), price | 2013–2026 | Long-history MVRV |
| checkonchain | STH-MVRV, price | 2013-01-02 – 2026-07-19 | Long-history STH-MVRV |
| bitcoin-data.com API | MVRV, STH-MVRV, price | trailing 4 years | Live source the monitor uses; cross-check |

Cross-validation of independent sources over their overlap:

- MVRV, CoinMetrics vs bitcoin-data.com: mean absolute difference 0.023
  (maximum 0.228) across 1,402 overlapping days.
- STH-MVRV, checkonchain vs bitcoin-data.com: mean absolute difference
  0.0097 (maximum 0.081) across 1,459 overlapping days.

The merged dataset covers 4,947 daily observations, 2013-01-02 to
2026-07-19.

## Tier occupancy

How often each tier actually occurs (share of the 4,947 days):

| MVRV tier | Days | Share | | STH-MVRV bucket | Days | Share |
|---|---|---|---|---|---|---|
| < 1.0 | 623 | 12.6% | | < 0.9 | 1,232 | 24.9% |
| 1.0 – 1.5 | 1,267 | 25.6% | | 0.9 – 1.0 | 904 | 18.3% |
| 1.5 – 2.0 | 1,433 | 29.0% | | 1.0 – 1.1 | 1,026 | 20.7% |
| 2.0 – 2.5 | 920 | 18.6% | | ≥ 1.1 | 1,785 | 36.1% |
| ≥ 2.5 | 704 | 14.2% | | | | |

Every tier gets meaningful use; no boundary is dead weight.

## Headline comparison

Simulation: $10/day base, one buy per day at the daily close, multipliers
from [strategy.md](strategy.md). "Uniform" buys $10 every day. "MVRV-only"
applies the MVRV multiplier alone. "Combined" applies both multipliers.
Average cost is total invested divided by total BTC acquired — the metric
that stays comparable when strategies invest different totals.

| Window | Strategy | Invested ($) | BTC | Avg cost ($) | Cost edge vs uniform |
|---|---|---|---|---|---|
| 2018–2021 | uniform | 14,610 | 1.5669 | 9,324 | — |
| | MVRV-only | 14,650 | 2.1011 | 6,973 | +25.2% |
| | combined | 17,320 | 2.6005 | 6,660 | +28.6% |
| 2022–2026 | uniform | 16,610 | 0.4006 | 41,464 | — |
| | MVRV-only | 18,075 | 0.5377 | 33,615 | +18.9% |
| | combined | 20,846 | 0.6282 | 33,183 | +20.0% |
| 2013–2017 | uniform | 18,250 | 86.6988 | 210 | — |
| | combined | 19,595 | 78.5203 | 250 | −18.6% |
| Full 2013–2026 | uniform | 49,470 | 88.6663 | 558 | — |
| | combined | 57,761 | 81.7490 | 707 | −26.6% |

Reading the table:

- In both modern cycles the combined strategy beat uniform DCA by 20–29% on
  average cost, and the STH-MVRV modifier added 1–4 points over MVRV alone.
- The 2013–2017 window and the full-period row favor uniform DCA. The cause
  is concentrated in 2013: MVRV spent 197 days above 2.5 while Bitcoin
  traded between $100 and $1,000, so the strategy stopped buying at prices
  that later grew 60×. Any rule that skips purchases loses that comparison.
  MVRV's behavior before the 2017 cycle differs enough from the modern
  regime that the 2018+ windows are the relevant evidence for a strategy
  starting today.
- The combined strategy invests more than uniform in every window — by
  design, the extra capital deploys in cheap zones. Budgets must
  accommodate this (see [strategy.md](strategy.md), scope section).

## Conflict rule evidence

Days where MVRV > 2.5 coincided with a bullish STH-MVRV reading:

| Condition | Days (of 4,947) |
|---|---|
| MVRV > 2.5 and STH-MVRV < 0.9 | 0 |
| MVRV > 2.5 and STH-MVRV < 1.0 | 0 |

The "MVRV dominates" conflict rule has never been exercised; the code path
exists as a safety default, not an active decision.

## Threshold compression

MVRV cycle peaks and time spent above the stop threshold, per cycle:

| Cycle | MVRV peak | Peak date | Days above 2.5 |
|---|---|---|---|
| 2013–2015 | 5.88 | 2013-11-18 | 197 |
| 2015–2018 | 4.72 | 2017-12-07 | 237 |
| 2018–2022 | 3.96 | 2021-02-21 | 205 |
| 2022–2026 | 2.78 | 2024-03-11 | 65 |

Peaks decline monotonically. Sensitivity runs on the modern windows:

| Variant | 2018–2021 avg cost ($) | 2022–2026 avg cost ($) |
|---|---|---|
| Uniform | 9,324 | 41,464 |
| v1 combined (shipped) | 6,660 | 33,183 |
| Steeper buys (3.0/2.0/1.0/0.5/stop) | 6,249 | 31,122 |
| Lower stop (tiers at 1.8/2.2) | 6,365 | 31,243 |

Both variants outperform the shipped tiers by small margins while investing
more capital or stopping earlier. The shipped version keeps the original
boundaries because two windows are thin evidence for retuning; the alert's
MVRV 4-year percentile field exists to flag when compression makes retuning
worth revisiting.

## Reproducing

```bash
uv run python backtest.py
```

The script downloads the live API's trailing-4-year history and prints the
uniform-vs-combined comparison. Run on 2026-07-23 it reported a +21.3%
average-cost edge over 1,452 days, consistent with the 2022–2026 row above.
The long-history windows require the CoinMetrics and checkonchain sources,
which the script does not fetch; those figures are recorded here.

## Limitations

- STH-MVRV history starts in 2013; the strategy cannot be tested on earlier
  cycles.
- No fees, spread, or slippage modeled. At daily DCA scale on a liquid pair
  these costs are near-identical across the compared strategies and do not
  change the ranking.
- Idle cash during stop periods earns nothing in the simulation. Parking it
  in a yield instrument would improve the strategy's relative result.
- Buys execute at the daily close of the indicator's data date; intraday
  timing is not modeled.
- Two modern cycles constitute the supporting evidence. The strategy is
  calibrated to, not proven beyond, this regime.
