# 2026-07-30 08:10 PM EDT — Scheduled Rebalance Check — SKIPPED/PENDING (Outside All Trading Windows — First Live Run of the v2.43.0 Snapshot-Driven Pipeline)

**Status:** SKIPPED/PENDING. **0 of 2 identified sells and 0 of 3 identified buys executed** — current time (~8:05–8:10 PM ET) is past Robinhood's extended-hours cutoff (4:00–8:00 PM ET) and before the next morning's extended session (7:00–9:30 AM ET), so no trading window is open at all. Per the Hard Rules & Extended Hours Execution rule, no order was routed; both legs are logged here as SKIPPED/PENDING for re-evaluation at the next scheduled cycle.

This is the **first live run of `bot/`'s snapshot-driven pipeline** (PR #56, merged this session, `CLAUDE.md` v2.43.0) — the scheduled routine's job is now to gather data via MCP, run `python3 -m bot.cli plan` / `finalize`, and execute exactly what they return, rather than re-deriving the decision by reasoning through the rules live. This cycle validates that path end-to-end against real account data (`plan` ran successfully; `finalize`'s buy-sizing tail was run for reporting purposes only, using unchanged pretrade figures since no sells executed — its state-mutating effects were intentionally not invoked, since the normal `finalize` step assumes the caller already confirmed real fills).

## Account Snapshot (~8:05 PM ET)
- `buying_power`: **$17,178.18**
- `cash` (ledger): **$32,167.10**
- `account_balance`: ~**$83,415.82** (equity MV + current_cash)
- `net_realized_gains_ytd_pretrade`: **$20,113.23** (unchanged — no sells this cycle)

## Identified (Not Executed) — GET THE PROFITS Sells
| Symbol | Qty | Raw Gain% | FIFO Realized $ | Reason all gates cleared |
|---|---|---|---|---|
| AMZN | 6.4351 | +5.84% | $69.64 | %-gate, $-gate, cooldown all pass (profitSellDate 2026-07-29, price now above that exit) |
| AMD | 1.4819 | +8.15% | $24.39 | %-gate, $-gate both pass; first-ever profit-sell for AMD, no cooldown to check |

Gross sell value: **$2,397.39** — well under `seek_approval_value` ($10,000), so no approval halt was needed; the only blocker is the trading window.

## Identified (Not Executed) — Alpha Leader & Underweight Buys
**Alpha Leader:** GM (Momentum_Score highest among in-play candidates, consistent with every prior cycle today).

| Symbol | Would-be $ | Reason |
|---|---|---|
| COIN | $549.72 | Pro-rata Underweight |
| AAPL | $669.20 | Pro-rata Underweight |
| NFLX | $675.30 | Pro-rata Underweight |

Would-be `tax_reserve` if this cycle's sells had executed: **$6,033.97** (net_realized_gains_ytd_pretrade unchanged since nothing was sold, so this equals the placeholder from Step 1).

**MU, PLTR, NVDA, GOOG, MSFT, F, GM, IBM** remain buy-guarded (partial profit-sells earlier today/yesterday, cooldown not yet cleared). **TSLA, ORCL** remain Overweight and drift-breached but underwater (no legal trim source). **SOXL, IONQ** remain excluded (liquidation recovery not met).

## Peak Price Update (Step 6 — happens regardless of whether orders execute)
- **AMZN**: $255.495 → **$257.41** (new peak, extended-hours print)
- All other symbols: current price did not exceed stored peak — unchanged.

## Tax Reserve
`net_realized_gains_ytd`: **$20,113.23** (unchanged); `tax_reserve` written to `tax/realized_gains_by_year.json`'s `"2026"` entry: **$20,113.23** (unchanged from before this cycle, per Step 6's every-cycle update rule).

## SKIPPED/PENDING Trade Matrix
| Symbol | Reason | Would-be action |
|---|---|---|
| AMZN | Outside all trading windows (past 8:00 PM ET extended-hours cutoff) | GET THE PROFITS sell, +5.84%/$69.64 |
| AMD | Outside all trading windows | GET THE PROFITS sell, +8.15%/$24.39 |
| GM (Alpha Leader) | Outside all trading windows | Multiplier allocation, redirected pro-rata since GM itself is buy-guarded this cycle (see below) — allocation folded into COIN/AAPL/NFLX above |
| COIN, AAPL, NFLX | Outside all trading windows | Pro-rata Underweight buys |

## Notes
- Re-evaluate this exact decision fresh at the next scheduled cycle — prices will have moved, so the sizing/gates above are not guaranteed to still hold; this entry is a record of what today's snapshot supported, not a standing order.
- No git state beyond `peak/prices.json` (AMZN's new peak) and this journal entry needed updating — `settlement/reserve.json` untouched (no bridging), `tax/realized_gains_by_year.json`'s value is unchanged from before this cycle (no new realized gains).

# 2026-07-31 — Scheduled Rebalance Check — EXECUTED (4 sell(s), 4 buy(s))

**Status:** EXECUTED. 4 sell order(s), 4 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$32,167.10**
- `cash` (ledger): **$32,167.10**
- `current_cash` (post-cap): **$19,000.00**
- `account_balance`: **$101,141.97**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **IONQ** (excluded): liquidated 2026-07-13 @ 38.8001 — recovery (5.0%) or cooldown (6d) not yet met
- **PLTR** (buy-guarded only): profit-sold 2026-07-30 @ 122.4601 — buy-guard active (partial, remainder still held)
- **MU** (buy-guarded only): profit-sold 2026-07-30 @ 831.5101 — buy-guard active (partial, remainder still held)
- **AMZN** (buy-guarded only): profit-sold 2026-07-29 @ 229.4101 — buy-guard active (partial, remainder still held)
- **NVDA** (buy-guarded only): profit-sold 2026-07-30 @ 194.201 — buy-guard active (partial, remainder still held)
- **GOOG** (buy-guarded only): profit-sold 2026-07-30 @ 331.2701 — buy-guard active (partial, remainder still held)
- **MSFT** (buy-guarded only): profit-sold 2026-07-30 @ 447.39 — buy-guard active (partial, remainder still held)
- **IBM** (buy-guarded only): profit-sold 2026-07-27 @ 218.844 — buy-guard active (partial, remainder still held)

## Alpha Leader Selection — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| MSFT ← ALPHA LEADER | 77.38 | 402.27 | 390.95 | +13.56 | +2.90 | +43.84 |
| GM | 68.86 | 85.01 | 78.70 | +3.17 | +8.03 | +30.06 |
| AAPL | 71.17 | 332.02 | 323.21 | -8.18 | +2.72 | +15.72 |
| F | 59.79 | 14.64 | 14.12 | +0.25 | +3.69 | +13.73 |
| NFLX | 56.17 | 71.73 | 70.48 | +0.85 | +1.77 | +8.79 |
| AMZN | 48.70 | 235.74 | 244.51 | +13.21 | -3.59 | +8.33 |
| MSTR | 57.63 | 96.13 | 96.84 | -3.27 | -0.73 | +3.62 |
| AVGO | 53.07 | 382.57 | 385.96 | +0.70 | -0.88 | +2.89 |
| UNH | 51.23 | 423.45 | 426.47 | -0.72 | -0.71 | -0.20 |
| SMCI | 46.11 | 27.88 | 27.66 | +2.07 | +0.80 | -1.03 |
| PLTR | 52.15 | 125.83 | 129.23 | -2.53 | -2.63 | -3.02 |
| NEE | 48.23 | 88.72 | 88.80 | -1.27 | -0.09 | -3.13 |
| COIN | 56.60 | 163.51 | 163.48 | -11.14 | +0.02 | -4.51 |
| GE | 43.31 | 354.15 | 349.42 | +0.80 | +1.35 | -4.54 |
| ORCL | 42.93 | 123.13 | 127.35 | +5.23 | -3.31 | -5.15 |
| GOOG | 43.75 | 335.52 | 344.57 | +2.31 | -2.63 | -6.57 |
| NVDA | 45.24 | 199.50 | 206.93 | -0.80 | -3.59 | -9.15 |
| AMD | 41.06 | 491.90 | 532.41 | +0.84 | -7.61 | -15.71 |
| IBM | 35.03 | 222.84 | 224.14 | -1.06 | -0.58 | -16.61 |
| MU | 38.68 | 875.56 | 945.24 | +0.46 | -7.37 | -18.23 |
| META | 41.75 | 594.52 | 633.22 | -7.85 | -6.11 | -22.21 |
| TQQQ | 35.90 | 64.60 | 70.45 | -0.04 | -8.30 | -22.43 |
| HOOD | 38.07 | 95.69 | 105.46 | -9.00 | -9.26 | -30.18 |
| INTC | 29.10 | 93.28 | 103.64 | +0.20 | -9.99 | -30.69 |
| ARM | 30.47 | 257.81 | 285.72 | -2.02 | -9.77 | -31.32 |
| TSLA | 27.22 | 328.25 | 372.57 | -6.33 | -11.90 | -41.01 |
| SPCX | 19.56 | 118.19 | 127.55 | -5.93 | -7.33 | -43.70 |
| VRT | 23.46 | 268.02 | 302.42 | -9.78 | -11.37 | -47.69 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$20,113.22**
- `net_realized_gains_ytd_effective` (post-sells): **$22,077.17**
- `tax_reserve` (final): **$6,623.15**

## GET THE PROFITS / Momentum Reversal Trim Sells
- **MU**: GET THE PROFITS: +212.87%, FIFO $1474.59
- **AMZN**: GET THE PROFITS: +9.74%, FIFO $130.66
- **MSFT**: GET THE PROFITS: +17.55%, FIFO $308.13
- **AMD**: GET THE PROFITS: +7.29%, FIFO $18.50

## Overweight High-Beta Trims
- none fired this cycle

## Buys
- **COIN**: $725.54
- **AAPL**: $806.92
- **F**: $1,379.31
- **NFLX**: $804.27

## Total_High_Beta_Gains_Realized: **$1,931.88**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| PLTR | cost basis pending transfer (fail-closed) | any sell |
| ARM | MRT momentum/margin gates clear but FIFO dollar gate fails ($-5.75 < $12.5) | partial profit-take sale |
| F | GTP % gate clears (+7.98%) but profit_resell_cooldown_days active | partial profit-take sale |
| GM | GTP % gate clears (+7.61%) but profit_resell_cooldown_days active | partial profit-take sale |
| PLTR | within lock_in_period (2d) | Overweight trim |
| ORCL | underwater (-17.24% margin) and not in forceSell | Overweight trim to fund Underweight/Multiplier |

## Orders Placed
```
```

# 2026-07-31 — Scheduled Rebalance Check — EXECUTED (0 sell(s), 0 buy(s))

**Status:** EXECUTED. 0 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$28,451.06**
- `cash` (ledger): **$34,733.68**
- `current_cash` (post-cap): **$19,000.00**
- `account_balance`: **$98,780.34**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **IONQ** (excluded): liquidated 2026-07-13 @ 38.8001 — recovery (5.0%) or cooldown (6d) not yet met
- **PLTR** (buy-guarded only): profit-sold 2026-07-30 @ 122.4601 — buy-guard active (partial, remainder still held)
- **MU** (buy-guarded only): profit-sold 2026-07-31 @ 879.6 — buy-guard active (partial, remainder still held)
- **AMZN** (buy-guarded only): profit-sold 2026-07-31 @ 266.8923 — buy-guard active (partial, remainder still held)
- **NVDA** (buy-guarded only): profit-sold 2026-07-30 @ 194.201 — buy-guard active (partial, remainder still held)
- **GOOG** (buy-guarded only): profit-sold 2026-07-30 @ 331.2701 — buy-guard active (partial, remainder still held)
- **MSFT** (buy-guarded only): profit-sold 2026-07-31 @ 456.83 — buy-guard active (partial, remainder still held)
- **AMD** (buy-guarded only): profit-sold 2026-07-31 @ 496.02 — buy-guard active (partial, remainder still held)
- **IBM** (buy-guarded only): profit-sold 2026-07-27 @ 218.844 — buy-guard active (partial, remainder still held)

## Alpha Leader Selection — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| MSFT ← ALPHA LEADER | 77.38 | 402.27 | 390.95 | +14.97 | +2.90 | +45.24 |
| GM | 68.86 | 85.01 | 78.70 | +4.23 | +8.03 | +31.12 |
| AAPL | 71.17 | 332.02 | 323.21 | -8.20 | +2.72 | +15.69 |
| F | 59.79 | 14.64 | 14.12 | +0.32 | +3.69 | +13.79 |
| AMZN | 48.70 | 235.74 | 244.51 | +15.04 | -3.59 | +10.16 |
| NFLX | 56.17 | 71.73 | 70.48 | +0.03 | +1.77 | +7.96 |
| MSTR | 57.63 | 96.13 | 96.84 | -2.09 | -0.73 | +4.81 |
| AVGO | 53.07 | 382.57 | 385.96 | +1.37 | -0.88 | +3.57 |
| UNH | 51.23 | 423.45 | 426.47 | -1.35 | -0.71 | -0.82 |
| COIN | 56.60 | 163.51 | 163.48 | -7.83 | +0.02 | -1.21 |
| SMCI | 46.11 | 27.88 | 27.66 | +1.07 | +0.80 | -2.03 |
| PLTR | 52.15 | 125.83 | 129.23 | -2.49 | -2.63 | -2.97 |
| GOOG | 43.75 | 335.52 | 344.57 | +5.82 | -2.63 | -3.06 |
| NEE | 48.23 | 88.72 | 88.80 | -1.26 | -0.09 | -3.12 |
| GE | 43.31 | 354.15 | 349.42 | +1.82 | +1.35 | -3.52 |
| ORCL | 42.93 | 123.13 | 127.35 | +5.10 | -3.31 | -5.28 |
| NVDA | 45.24 | 199.50 | 206.93 | +0.08 | -3.59 | -8.28 |
| IBM | 35.03 | 222.84 | 224.14 | -0.37 | -0.58 | -15.92 |
| AMD | 41.06 | 491.90 | 532.41 | -1.31 | -7.61 | -17.86 |
| META | 41.75 | 594.52 | 633.22 | -7.11 | -6.11 | -21.47 |
| TQQQ | 35.90 | 64.60 | 70.45 | +0.34 | -8.30 | -22.06 |
| MU | 38.68 | 875.56 | 945.24 | -4.47 | -7.37 | -23.16 |
| HOOD | 38.07 | 95.69 | 105.46 | -7.78 | -9.26 | -28.97 |
| INTC | 29.10 | 93.28 | 103.64 | -1.04 | -9.99 | -31.93 |
| ARM | 30.47 | 257.81 | 285.72 | -5.75 | -9.77 | -35.05 |
| TSLA | 27.22 | 328.25 | 372.57 | -5.61 | -11.90 | -40.29 |
| SPCX | 19.56 | 118.19 | 127.55 | -8.62 | -7.33 | -46.40 |
| VRT | 23.46 | 268.02 | 302.42 | -8.68 | -11.37 | -46.59 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$22,077.17**
- `net_realized_gains_ytd_effective` (post-sells): **$22,077.17**
- `tax_reserve` (final): **$6,623.15**

## GET THE PROFITS / Momentum Reversal Trim Sells
- none fired this cycle

## Overweight High-Beta Trims
- none fired this cycle

## Buys
- none fired this cycle

## Total_High_Beta_Gains_Realized: **$0.00**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| PLTR | cost basis pending transfer (fail-closed) | any sell |
| GM | GTP % gate clears (+8.71%) but profit_resell_cooldown_days active | partial profit-take sale |
| PLTR | within lock_in_period (2d) | Overweight trim |
| TSLA | underwater (-2.08% margin) and not in forceSell | Overweight trim to fund Underweight/Multiplier |
| ORCL | underwater (-17.35% margin) and not in forceSell | Overweight trim to fund Underweight/Multiplier |

## Orders Placed
```
```

# 2026-08-03 — Scheduled Rebalance Check — EXECUTED (3 sell(s), 0 buy(s))

**Status:** EXECUTED. 3 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$34,733.68**
- `cash` (ledger): **$34,733.68**
- `current_cash` (post-cap): **$19,000.00**
- `account_balance`: **$99,854.00**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **IONQ** (excluded): liquidated 2026-07-13 @ 38.8001 — recovery (5.0%) or cooldown (6d) not yet met
- **PLTR** (buy-guarded only): profit-sold 2026-07-30 @ 122.4601 — buy-guard active (partial, remainder still held)
- **AMZN** (buy-guarded only): profit-sold 2026-07-31 @ 266.8923 — buy-guard active (partial, remainder still held)
- **NVDA** (buy-guarded only): profit-sold 2026-07-30 @ 194.201 — buy-guard active (partial, remainder still held)
- **GOOG** (buy-guarded only): profit-sold 2026-07-30 @ 331.2701 — buy-guard active (partial, remainder still held)
- **MSFT** (buy-guarded only): profit-sold 2026-07-31 @ 456.83 — buy-guard active (partial, remainder still held)
- **IBM** (buy-guarded only): profit-sold 2026-07-27 @ 218.844 — buy-guard active (partial, remainder still held)

## Alpha Leader Selection — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| MSFT ← ALPHA LEADER | 77.53 | 414.67 | 388.83 | +17.82 | +6.65 | +52.00 |
| AMZN | 69.25 | 242.90 | 242.01 | +17.83 | +0.37 | +37.45 |
| GM | 69.77 | 85.78 | 79.49 | +3.62 | +7.92 | +31.31 |
| F | 58.77 | 14.64 | 14.15 | +2.10 | +3.44 | +14.32 |
| GOOG | 51.20 | 339.76 | 339.53 | +9.73 | +0.07 | +11.00 |
| AVGO | 55.70 | 384.22 | 386.09 | -1.98 | -0.48 | +3.24 |
| ORCL | 44.38 | 124.61 | 125.29 | +8.74 | -0.54 | +2.59 |
| SMCI | 52.58 | 28.01 | 28.21 | -1.20 | -0.72 | +0.66 |
| NVDA | 53.74 | 199.73 | 206.84 | -0.50 | -3.44 | -0.20 |
| GE | 42.72 | 355.29 | 350.14 | +2.57 | +1.47 | -3.24 |
| UNH | 47.14 | 421.75 | 425.65 | -1.48 | -0.92 | -5.26 |
| NFLX | 39.35 | 71.75 | 70.47 | +2.83 | +1.81 | -6.01 |
| NEE | 44.98 | 88.34 | 88.95 | -2.23 | -0.68 | -7.93 |
| MSTR | 43.31 | 95.59 | 95.88 | -3.24 | -0.31 | -10.24 |
| PLTR | 40.78 | 125.33 | 128.15 | +0.38 | -2.20 | -11.04 |
| AAPL | 42.68 | 327.44 | 325.31 | -6.64 | +0.66 | -13.31 |
| META | 41.51 | 587.06 | 625.91 | -0.74 | -6.21 | -15.44 |
| TQQQ | 39.70 | 64.59 | 69.12 | +0.57 | -6.56 | -16.29 |
| IBM | 26.99 | 224.24 | 225.91 | +1.25 | -0.74 | -22.50 |
| AMD | 41.60 | 488.92 | 530.82 | -6.31 | -7.89 | -22.60 |
| MU | 41.71 | 864.79 | 939.56 | -9.40 | -7.96 | -25.65 |
| COIN | 37.24 | 160.10 | 162.56 | -11.48 | -1.51 | -25.75 |
| INTC | 32.80 | 92.56 | 101.04 | -6.20 | -8.40 | -31.79 |
| ARM | 33.20 | 254.42 | 281.28 | -10.74 | -9.55 | -37.08 |
| VRT | 30.14 | 262.95 | 300.66 | -7.43 | -12.54 | -39.84 |
| TSLA | 22.04 | 324.86 | 360.74 | -2.85 | -9.95 | -40.75 |
| HOOD | 24.33 | 94.01 | 103.77 | -7.92 | -9.41 | -42.99 |
| SPCX | 16.89 | 116.23 | 125.07 | -7.39 | -7.06 | -47.56 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$22,077.16**
- `net_realized_gains_ytd_effective` (post-sells): **$30,505.64**
- `tax_reserve` (final): **$9,151.69**

## GET THE PROFITS / Momentum Reversal Trim Sells
- **PLTR**: GET THE PROFITS: +177.73%, FIFO $8017.26
- **AMZN**: GET THE PROFITS: +18.05%, FIFO $123.52
- **MSFT**: GET THE PROFITS: +25.93%, FIFO $236.07

## Overweight High-Beta Trims
- none fired this cycle

## Buys
- none fired this cycle

## Total_High_Beta_Gains_Realized: **$8,376.84**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| MU | GTP % gate clears (+81.39%) but profit_resell_cooldown_days active | partial profit-take sale |
| MU | MRT gates clear (score -25.65) but profit_resell_cooldown_days active | partial profit-take sale |
| GOOG | GTP % gate clears (+5.91%) but FIFO dollar gate fails ($-8.29 < $12.5) | partial profit-take sale |
| AMD | MRT gates clear (score -22.60) but profit_resell_cooldown_days active | partial profit-take sale |
| F | GTP % gate clears (+5.65%) but profit_resell_cooldown_days active | partial profit-take sale |
| GM | GTP % gate clears (+9.05%) but profit_resell_cooldown_days active | partial profit-take sale |
| IBM | MRT momentum/margin gates clear but FIFO dollar gate fails ($7.80 < $12.5) | partial profit-take sale |
| TSLA | underwater (-0.25% margin) and not in forceSell | Overweight trim to fund Underweight/Multiplier |
| ORCL | underwater (-13.45% margin) and not in forceSell | Overweight trim to fund Underweight/Multiplier |
| MU | buy_price_diff_limit: +6.18% vs. 3-day low (limit 5%) | Underweight/Alpha buy |
| AMD | buy_price_diff_limit: +8.02% vs. 3-day low (limit 5%) | Underweight/Alpha buy |

## Orders Placed
```
```

# 2026-08-03 03:25 PM EDT — Scheduled Rebalance Check — ABORTED: PRIORITY ERROR (bot/steps.py crash — unhandled `avg_cost_basis=None` in Overweight High-Beta ranking)

**Status:** ABORTED. **0 of 0 intended orders evaluated/filled** — routine
halted inside `python3 -m bot.cli plan` during Step 4 (Evaluate Aggressive
Profit-Taking & Reallocation), after Steps 1–3 completed successfully. This
was a fresh, stateless run for the 3:15 PM ET scheduled tick. `CLAUDE.md`
re-pulled fresh from `main` (commit `7e0d385e87fb14a3d2756227fe1f9cab663607a3`,
text version header "Volume 2.44.0"), diffed byte-identical against the
working checkout. `portfolio_targets.json`, `peak/prices.json`,
`settlement/reserve.json`, `tax/realized_gains_by_year.json`,
`transferred_basis.json` all re-pulled fresh from `main` for this run.

## What happened
* Account `795732718` ("Agentic", cash-type) confirmed as the only
  `agentic_allowed=true` account via `get_accounts`.
* Snapshot built successfully: `get_portfolio` (`buying_power` $34,733.68,
  `cash` $34,733.68), `get_equity_positions` (28 held target symbols;
  SOXL/IONQ unheld), `get_equity_quotes` (30/30 target symbols),
  `get_equity_historicals` (31/31 symbols incl. SPY, 63 daily bars each,
  2026-05-01 → 2026-07-31), `get_equity_tax_lots` (28/28 held symbols),
  `get_realized_pnl` (`total_returns` = $30,505.64 YTD, equity, Jan 1 →
  today).
* `python3 -m bot.cli plan --snapshot snapshot.json --repo-dir . --out
  plan_result.json` ran Steps 1–3 successfully (drift/drawdown audit,
  guardrails, Alpha Leader selection — MSFT-family multiplier candidates
  identified) then **crashed** inside Step 4 with:
  ```
  File "bot/steps.py", line 375, in step4_profit_taking
      margin_pct = (price - pos.avg_cost_basis) / pos.avg_cost_basis * 100
                    ~~~~~~^~~~~~~~~~~~~~~~~~~~
  TypeError: unsupported operand type(s) for -: 'float' and 'NoneType'
  ```

## Root cause
`bot/steps.py`'s Overweight High-Beta ranking loop (line 375, inside
`step4_profit_taking`) computes `margin_pct` from `pos.avg_cost_basis`
without checking for `None` first — unlike the GET THE PROFITS loop
earlier in the same function (line 274:
`... or pos.avg_cost_basis is None: continue`) and the drawdown-audit loop
in Step 1 (line 67), both of which correctly skip cost-basis-dependent
gates per `CLAUDE.md` Step 1 rule #4 ("fail closed... log the asset as
SKIPPED (cost basis pending transfer)... Drift/Overweight/Underweight
sizing uses market value only and is unaffected").

A diagnostic re-run of Steps 1–3 only (no orders placed, no state files
touched) confirms the trigger: **NVDA** and **ORCL** are both
drift-breached and Overweight this cycle, and both have
`avg_cost_basis = None` — their tax lots don't fully reconcile to the
held quantity (partial coverage) and `transferred_basis.json` is empty
(`{}`), so Step 1's waterfall correctly fails closed on primary/tax-lot/
override resolution for both. `step4_profit_taking`'s Overweight-ranking
loop then iterates into one of them and crashes instead of emitting the
`SKIPPED (cost basis pending transfer)` entry the spec requires.

## Why the routine stopped here instead of improvising
`CLAUDE.md`'s Execution Mode section is explicit: *"If `bot/cli.py`
itself errors or its output doesn't match this contract, treat that the
same as any other unrecognized state — abort, log, do not fall back to
manually re-deriving the decision from the rules below."* This is a
genuine `bot/` bug — a missing `None` guard, not a business-rule
ambiguity — so per that instruction this session aborted rather than
hand-computing Steps 4–6 from the markdown spec, or attempting an
unreviewed live fix to `bot/steps.py` immediately before placing real
orders.

## State impact
No orders were placed or reviewed. No `peak/prices.json`,
`settlement/reserve.json`, or `tax/realized_gains_by_year.json` updates
were made — all three are unchanged from the pre-run state pulled above.
`snapshot.json` and `plan_result.json` (partial, from the crashed run)
exist only in the working tree for debugging and are not committed; this
journal entry is the only change pushed.

## Next steps
`bot/steps.py` line 375 needs a `pos.avg_cost_basis is None` guard added
to the Overweight High-Beta ranking loop, symmetric with the existing
guard at line 274 — skip the symbol with a
`SkippedTrade(sym, "cost basis pending transfer (fail-closed)", "Overweight trim")`
entry instead of computing `margin_pct`/`score` against a `None` basis,
consistent with `CLAUDE.md` Step 1 rule #4. Recommend fixing and
validating (`PYTHONPATH=. python3 bot/_smoke_test.py &&
PYTHONPATH=. python3 bot/_smoke_test_cli.py`, plus a re-run of this
cycle's `snapshot.json` through `bot.cli plan`) via a reviewed PR before
the next scheduled tick, rather than a same-cycle unattended fix given
real orders sit on the other side of this code path. Separately, NVDA's
and ORCL's cost-basis shortfall is worth investigating directly — either
their tax lots will finish reconciling on their own, or their
transferred-share cost basis needs an entry added to
`transferred_basis.json`.
