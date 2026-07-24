# Strategy: MVRV-tiered dollar-cost averaging

Audience: anyone deciding whether to run this monitor with real money. No prior
on-chain-analysis knowledge assumed.

## The two indicators

**Market Value to Realized Value (MVRV)** is Bitcoin's market capitalization
divided by its realized capitalization. Realized capitalization values every
coin at the price of its last on-chain movement, which makes it an aggregate
cost basis for all holders. MVRV therefore reads as "how many times its
average acquisition price is Bitcoin trading at":

- MVRV below 1.0 means the market trades below the average holder's cost
  basis. Historically this occurs at capitulation lows.
- MVRV above 2.5 means the average holder sits on a 2.5× paper gain.
  Historically this precedes cycle tops, where profit-taking accelerates.

**Short-Term Holder MVRV (STH-MVRV)** is the same ratio restricted to coins
that moved within the last 155 days — the cost basis of recent buyers. It
mean-reverts much faster than MVRV and frames the short-term picture: above
1.0, recent buyers are in profit and their cost basis tends to act as
support; below 1.0, recent buyers are underwater and rallies tend to stall
where they break even.

Dollar-cost averaging (DCA) is the practice of buying a fixed amount on a
fixed schedule regardless of price. This strategy keeps the schedule but
scales the amount by cycle position.

## The rules

Daily guidance = `mvrv_mult × sth_mult`, a multiplier on whatever base amount
the reader normally DCAs. The monitor recommends the multiplier only; the
base amount and the order stay with the reader.

MVRV sets the macro tier:

| MVRV | Zone | mvrv_mult | Rationale |
|---|---|---|---|
| < 1.0 | very cheap | 2.0 | Market below aggregate cost basis; historically the best accumulation zone |
| 1.0 – 1.5 | cheap | 1.5 | Early-recovery range; still below historical fair-value bands |
| 1.5 – 2.0 | normal | 1.0 | Mid-cycle; standard DCA |
| 2.0 – 2.5 | expensive | 0.5 | Late-cycle froth building; reduce exposure to top-heavy entries |
| ≥ 2.5 | very expensive | 0 (stop) | Historical top zone; stop buying entirely |

STH-MVRV scales the amount within every non-stop tier:

| STH-MVRV | sth_mult | Rationale |
|---|---|---|
| < 0.9 | 1.5 | Recent buyers capitulating; local-bottom conditions |
| 0.9 – 1.0 | 1.25 | Recent buyers near break-even; dips into support |
| 1.0 – 1.1 | 1.0 | Neutral short-term positioning |
| ≥ 1.1 | 0.5 | Short-term overheated; halve the buy |

Tier boundaries are lower-bound inclusive: MVRV of exactly 1.0 classifies as
"cheap", STH-MVRV of exactly 0.9 as the 1.25 bucket.

## Conflict rule

When MVRV reads "stop" (≥ 2.5), the stop wins regardless of STH-MVRV. The
rule matters less than it appears: across 4,947 daily observations
(2013–2026), MVRV > 2.5 never coincided with STH-MVRV < 1.0 — when the macro
cycle is expensive, recent buyers are in profit. See
[backtest-results.md](backtest-results.md) for the full evidence.

## What the strategy does and does not do

- It scales a recurring buy. It never sells, never times exits, and never
  places orders — the monitor emits a signal; execution stays manual.
- It deploys more capital in bear markets by design. Over 2022–2026 the
  strategy invested 26% more than uniform DCA in exchange for a 20% lower
  average cost. The budget must tolerate multi-month stretches at 2–3× the
  base amount.
- It covers Bitcoin only. The multiplier tables are calibrated to Bitcoin's
  MVRV history and do not transfer to other assets.

## Known risks

1. **Threshold compression.** MVRV cycle peaks have declined every cycle:
   5.88 (2013), 4.72 (2017), 3.96 (2021), 2.78 (2024). The 2024 cycle spent
   only 65 days above 2.5. If compression continues, the stop tier never
   triggers and 2.0–2.5 becomes the effective top signal. Every alert shows
   the current MVRV percentile against the trailing 4 years so the drift
   stays visible. Re-run `backtest.py` before changing any boundary.
2. **Data lag.** The upstream indicator data lags realtime by one to two
   days. MVRV moves slowly enough that the tier rarely changes within the
   lag window; each alert displays the data date it was computed from.
3. **Regime dependence.** The multipliers are calibrated on 2013–2026
   history. A structurally different future regime (for example, MVRV
   permanently range-bound near 1.0) reduces the strategy to
   near-uniform DCA with extra machinery.
