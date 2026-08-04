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
