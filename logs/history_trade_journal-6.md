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
