# 2026-11-23 — Scheduled Rebalance Check — EXECUTED (0 sell(s), 0 buy(s))

**Status:** EXECUTED. 0 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$55,254.91**
- `cash` (ledger): **$55,254.91**
- `current_cash` (post-cap): **$55,254.91**
- `account_balance`: **$125,198.16**

## Drawdown Audit
Emergency liquidations: none

## Unrealized-Loss Buy Guard
- Total unrealized losses (underwater positions only): **$9,489.02** vs. `total_unrealized_losses_threshold` **$5,000.00** — **BUYS HALTED** — no buy of any kind this cycle

## Excluded / Buy-Guarded Symbols (Step 2)
- **INTC** (excluded): Profit-sell buy-guard: profit-sold 2026-09-30 @ 119.67 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.815%, need > 0.441% [asset-scaled, x2.21])
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **IONQ** (excluded): liquidated 2026-10-30 @ 29.02 — recovery (5.0%) or cooldown (6d) not yet met
- **HOOD** (excluded): liquidated 2026-11-16 @ 74.9 — recovery (5.0%) or cooldown (6d) not yet met
- **JNJ** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 275.33 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.232%, need > -0.022% [asset-scaled, x0.43]); upturn not confirmed (leg3 close_yesterday→today change=-0.026%, need > 0.034% [asset-scaled, x0.43])
- **HD** (excluded): Profit-sell buy-guard: profit-sold 2026-11-12 @ 353.53 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.688%, need > -0.030% [asset-scaled, x0.61])
- **WMT** (excluded): Profit-sell buy-guard: profit-sold 2026-11-16 @ 129.18 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.495%, need > -0.021% [asset-scaled, x0.42]); upturn not confirmed (leg3 close_yesterday→today change=-0.172%, need > 0.034% [asset-scaled, x0.42])
- **PG** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 164.365 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.897%, need > -0.017% [asset-scaled, x0.33])
- **COST** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 1012.9 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.759%, need > -0.019% [asset-scaled, x0.38]); upturn not confirmed (leg3 close_yesterday→today change=-0.557%, need > 0.030% [asset-scaled, x0.38])
- **XOM** (excluded): Profit-sell buy-guard: profit-sold 2026-09-09 @ 164.59 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.668%, need > -0.028% [asset-scaled, x0.55]); upturn not confirmed (leg3 close_yesterday→today change=-0.813%, need > 0.044% [asset-scaled, x0.55])
- **COP** (excluded): Profit-sell buy-guard: profit-sold 2026-09-04 @ 133.4425 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.438%, need > 0.117% [asset-scaled, x0.59]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.839%, need > -0.029% [asset-scaled, x0.59]); upturn not confirmed (leg3 close_yesterday→today change=-1.062%, need > 0.047% [asset-scaled, x0.59])
- **DUK** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 127.175 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.713%, need > -0.014% [asset-scaled, x0.29]); upturn not confirmed (leg3 close_yesterday→today change=-0.558%, need > 0.023% [asset-scaled, x0.29])
- **IBM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-22 @ 250.52 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.243%, need > -0.023% [asset-scaled, x0.46])
- **UNH** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-22 @ 425.58 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.859%, need > -0.042% [asset-scaled, x0.84]); upturn not confirmed (leg3 close_yesterday→today change=-3.692%, need > 0.068% [asset-scaled, x0.84])
- **CVX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-06 @ 208.5137 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.298%, need > 0.099% [asset-scaled, x0.49]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.899%, need > -0.025% [asset-scaled, x0.49]); upturn not confirmed (leg3 close_yesterday→today change=-0.207%, need > 0.039% [asset-scaled, x0.49])
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-30 @ 188.19 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.667%, need > -0.024% [asset-scaled, x0.47]); upturn not confirmed (leg3 close_yesterday→today change=-0.338%, need > 0.038% [asset-scaled, x0.47])

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $0.26) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| BRK.B | 58.72 | 577.09 | 577.90 | -0.72 | -0.14 | +7.86 |
| GE | 54.52 | 322.19 | 327.11 | -1.38 | -1.50 | +1.63 |
| LLY | 54.43 | 1385.82 | 1406.83 | -1.64 | -1.49 | +1.30 |
| NEE | 51.77 | 84.59 | 85.46 | -1.05 | -1.02 | -0.30 |
| SO | 49.77 | 93.53 | 93.25 | -0.41 | +0.30 | -0.33 |
| SHW | 49.60 | 345.03 | 349.10 | -0.42 | -1.16 | -1.98 |
| EQIX | 47.10 | 1022.18 | 1042.38 | -0.51 | -1.94 | -5.35 |
| AAPL | 44.47 | 349.32 | 350.59 | -0.63 | -0.36 | -6.53 |
| GM | 49.95 | 83.25 | 86.82 | -2.67 | -4.12 | -6.84 |
| AMZN | 46.14 | 258.48 | 262.89 | -1.83 | -1.68 | -7.37 |
| LIN | 43.30 | 514.01 | 520.70 | -0.72 | -1.29 | -8.71 |
| V | 43.80 | 413.56 | 421.33 | -0.87 | -1.85 | -8.92 |
| AMT | 44.15 | 186.10 | 189.92 | -1.35 | -2.01 | -9.21 |
| TSLA | 40.28 | 374.74 | 386.12 | +3.41 | -2.95 | -9.26 |
| UNP | 43.61 | 296.33 | 300.79 | -2.07 | -1.48 | -9.94 |
| SPCX | 36.46 | 137.55 | 139.51 | +2.01 | -1.40 | -12.94 |
| PLD | 38.92 | 125.79 | 128.83 | -0.75 | -2.36 | -14.19 |
| F | 41.82 | 11.57 | 12.15 | -1.27 | -4.80 | -14.25 |
| AVGO | 43.55 | 334.19 | 336.40 | -8.50 | -0.66 | -15.60 |
| VRT | 41.72 | 189.64 | 204.32 | -1.98 | -7.18 | -17.45 |
| MSFT | 36.78 | 509.01 | 528.10 | -1.59 | -3.61 | -18.42 |
| JPM | 35.85 | 328.33 | 341.82 | -3.17 | -3.95 | -21.27 |
| ORCL | 35.14 | 114.86 | 124.57 | -0.40 | -7.79 | -23.05 |
| CVX | 29.93 | 212.38 | 217.88 | -2.09 | -2.52 | -24.68 |
| AMD | 40.19 | 496.14 | 525.74 | -10.16 | -5.63 | -25.60 |
| ARM | 34.32 | 179.17 | 194.92 | -2.38 | -8.08 | -26.14 |
| META | 30.71 | 607.29 | 629.09 | -3.96 | -3.47 | -26.72 |
| GOOG | 25.83 | 278.81 | 291.26 | -1.22 | -4.28 | -29.66 |
| IBM | 26.99 | 234.68 | 247.77 | -1.90 | -5.28 | -30.19 |
| NFLX | 26.70 | 60.19 | 63.33 | -4.60 | -4.94 | -32.84 |
| SMCI | 28.43 | 25.28 | 28.96 | +0.97 | -12.73 | -33.33 |
| MU | 30.90 | 709.56 | 787.53 | -5.33 | -9.90 | -34.32 |
| CAT | 24.74 | 563.36 | 606.04 | -3.33 | -7.04 | -35.63 |
| PLTR | 19.49 | 159.02 | 172.45 | -2.16 | -7.79 | -40.46 |
| TQQQ | 28.20 | 51.85 | 59.22 | -7.52 | -12.45 | -41.77 |
| NVDA | 14.81 | 155.17 | 179.06 | +4.29 | -13.34 | -44.25 |
| UNH | 24.56 | 371.75 | 404.24 | -11.84 | -8.04 | -45.31 |
| FCX | 21.61 | 53.87 | 61.17 | -7.38 | -11.93 | -47.70 |
| COIN | 19.01 | 118.40 | 136.87 | -8.36 | -13.49 | -52.84 |
| MSTR | 15.89 | 99.66 | 123.41 | -11.12 | -19.24 | -64.48 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$74,980.35**
- `net_realized_gains_ytd_effective` (post-sells): **$74,980.35**
- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **$25,000.00**
- `tax_reserve` (final, after subtracting paid taxes): **$16,239.19**

## GET THE PROFITS Sells
- none fired this cycle

## Sell Cleanup Pass
- none fired this cycle

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)
- none this cycle

## Total_High_Beta_Gains_Realized: **$0.00**
## Total_Cleanup_Gains_Realized: **$0.00**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| ALL | total unrealized losses $9,489.02 exceed total_unrealized_losses_threshold $5,000.00 — no buys this cycle | any buy |
| TSLA | loss-lot sell guard: every sellable lot is at or above the current price ($387.50) — nothing can be sold at a gain | partial profit-take sale |
| GOOG | loss-lot sell guard: every sellable lot is at or above the current price ($275.41) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | loss-lot sell guard: every sellable lot is at or above the current price ($47.95) — nothing can be sold at a gain | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($445.75) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($83.69) — nothing can be sold at a gain | partial profit-take sale |
| VRT | loss-lot sell guard: every sellable lot is at or above the current price ($185.88) — nothing can be sold at a gain | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($305.80) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($11.42) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($81.02) — nothing can be sold at a gain | partial profit-take sale |
| IBM | loss-lot sell guard: every sellable lot is at or above the current price ($230.21) — nothing can be sold at a gain | partial profit-take sale |
| NFLX | loss-lot sell guard: every sellable lot is at or above the current price ($57.42) — nothing can be sold at a gain | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($327.75) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($317.73) — nothing can be sold at a gain | partial profit-take sale |
| CVX | loss-lot sell guard: every sellable lot is at or above the current price ($207.94) — nothing can be sold at a gain | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($93.15) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($124.85) — nothing can be sold at a gain | partial profit-take sale |
| AMT | loss-lot sell guard: every sellable lot is at or above the current price ($183.59) — nothing can be sold at a gain | partial profit-take sale |
| EQIX | loss-lot sell guard: every sellable lot is at or above the current price ($1017.00) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($343.60) — nothing can be sold at a gain | partial profit-take sale |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-2,020.95 | -96.24% |
| SHW | 109d | 2026-08-06 | $-104.90 | -5.24% |
| GE | 108d | 2026-08-07 | $-359.85 | -14.64% |
| AVGO | 103d | 2026-08-12 | $-1,171.25 | -27.36% |
| F | 101d | 2026-08-14 | $-503.04 | -22.47% |
| NFLX | 82d | 2026-09-02 | $-1.94 | -28.93% |
| TQQQ | 45d | 2026-10-09 | $-13.83 | -40.52% |
| GOOG | 41d | 2026-10-13 | $-1,245.24 | -22.68% |
| AMD | 41d | 2026-10-13 | $-1,535.01 | -25.58% |
| TSLA | 21d | 2026-11-02 | $-238.35 | -3.97% |
| VRT | 20d | 2026-11-03 | $-1,234.21 | -20.49% |
| UNH | 20d | 2026-11-03 | $-1,270.12 | -20.70% |
| IBM | 19d | 2026-11-04 | $-592.60 | -9.83% |
| CVX | 18d | 2026-11-05 | $-309.42 | -5.22% |
| SO | 18d | 2026-11-05 | $-58.59 | -0.99% |
| AMT | 14d | 2026-11-09 | $-143.16 | -3.52% |
| PLD | 12d | 2026-11-11 | $-11.38 | -7.94% |
| NEE | 11d | 2026-11-12 | $-224.90 | -4.89% |
| GM | 6d | 2026-11-17 | $-267.47 | -4.46% |
| EQIX | 6d | 2026-11-17 | $-203.75 | -3.40% |

## Loss-Only Lot Assets (every sellable lot underwater)
20 asset(s), $69,943.25 market value, $-11,610.90 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $0.26 | $79.05 | $-2,020.95 | -96.24% | 1 | $7.00 / $7.00 |
| TQQQ | 0.4232 | $80.62 | $47.95 | $20.29 | $-13.83 | -40.52% | 1 | $80.62 / $80.62 |
| NFLX | 0.0830 | $80.80 | $57.42 | $4.77 | $-1.94 | -28.93% | 1 | $80.80 / $80.80 |
| AVGO | 10.1667 | $421.00 | $305.80 | $3,108.91 | $-1,171.28 | -27.37% | 2 | $377.86 / $423.11 |
| AMD | 10.0167 | $599.00 | $445.75 | $4,464.99 | $-1,535.01 | -25.58% | 1 | $599.00 / $599.00 |
| GOOG ⚠ | 15.4110 | $360.29 | $275.41 | $4,244.31 | $-1,308.14 | -23.56% | 8 | $344.59 / $377.51 |
| F | 151.9817 | $14.73 | $11.42 | $1,735.65 | $-502.53 | -22.45% | 4 | $14.30 / $14.85 |
| UNH | 14.8483 | $413.37 | $327.75 | $4,866.52 | $-1,271.32 | -20.71% | 2 | $403.15 / $413.61 |
| VRT | 25.7717 | $233.77 | $185.88 | $4,790.45 | $-1,234.30 | -20.49% | 2 | $233.24 / $233.79 |
| GE | 6.6016 | $372.24 | $317.73 | $2,097.54 | $-359.88 | -14.64% | 2 | $356.04 / $373.67 |
| IBM | 23.6003 | $255.32 | $230.21 | $5,433.04 | $-592.49 | -9.83% | 2 | $254.37 / $255.34 |
| PLD | 1.0562 | $135.62 | $124.85 | $131.87 | $-11.38 | -7.94% | 2 | $129.03 / $139.86 |
| SHW | 5.5210 | $362.60 | $343.60 | $1,897.02 | $-104.90 | -5.24% | 1 | $362.60 / $362.60 |
| CVX | 27.0000 | $219.40 | $207.94 | $5,614.38 | $-309.42 | -5.22% | 1 | $219.40 / $219.40 |
| NEE | 52.2424 | $88.00 | $83.69 | $4,372.43 | $-224.83 | -4.89% | 8 | $83.94 / $90.00 |
| TSLA ⚠ | 14.8688 | $406.04 | $387.50 | $5,761.65 | $-275.67 | -4.57% | 1 | $406.04 / $406.04 |
| GM | 70.7589 | $84.80 | $81.02 | $5,732.89 | $-267.47 | -4.46% | 1 | $84.80 / $84.80 |
| AMT | 21.3671 | $190.29 | $183.59 | $3,922.78 | $-143.24 | -3.52% | 2 | $189.49 / $190.50 |
| EQIX | 5.6994 | $1,052.75 | $1,017.00 | $5,796.27 | $-203.75 | -3.40% | 1 | $1,052.75 / $1,052.75 |
| SO | 63.0000 | $94.08 | $93.15 | $5,868.45 | $-58.59 | -0.99% | 1 | $94.08 / $94.08 |

⚠ = the broker's blended `avg_cost_basis` materially disagrees with the cost of the actual lots, so the two views of this position tell different stories:
- **GOOG**: `avg_cost_basis` $356.21 vs. lot-weighted $360.29 (price $275.41) — the blended average implies -22.68%, the lots imply -23.56%
- **TSLA**: `avg_cost_basis` $403.53 vs. lot-weighted $406.04 (price $387.50) — the blended average implies -3.97%, the lots imply -4.57%

## Deferred Wash-Sale Loss Tracking (v2.84.0, observational)
- none this cycle

## Orders Placed
```
```

# 2026-11-20 — Scheduled Rebalance Check — EXECUTED (0 sell(s), 0 buy(s))

**Status:** EXECUTED. 0 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$55,177.44**
- `cash` (ledger): **$55,177.44**
- `current_cash` (post-cap): **$55,177.44**
- `account_balance`: **$123,482.66**

## Drawdown Audit
Emergency liquidations: none

## Unrealized-Loss Buy Guard
- Total unrealized losses (underwater positions only): **$11,120.48** vs. `total_unrealized_losses_threshold` **$5,000.00** — **BUYS HALTED** — no buy of any kind this cycle

## Excluded / Buy-Guarded Symbols (Step 2)
- **INTC** (excluded): Profit-sell buy-guard: profit-sold 2026-09-30 @ 119.67 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.993%, need > -0.115% [asset-scaled, x2.29]); upturn not confirmed (leg3 close_yesterday→today change=-5.761%, need > 0.183% [asset-scaled, x2.29])
- **PLTR** (excluded): Profit-sell buy-guard: profit-sold 2026-10-20 @ 193.8 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.076%, need > 0.189% [asset-scaled, x0.95]); upturn not confirmed (leg3 close_yesterday→today change=-6.368%, need > 0.076% [asset-scaled, x0.95])
- **MU** (excluded): Profit-sell buy-guard: profit-sold 2026-09-08 @ 1020.06 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-16.522%, need > 0.146% [asset-scaled, x1.82])
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **MSTR** (excluded): Profit-sell buy-guard: profit-sold 2026-10-12 @ 155.37 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-8.572%, need > 0.095% [asset-scaled, x1.18])
- **COIN** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 198.75 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-4.753%, need > 0.093% [asset-scaled, x1.17])
- **ARM** (excluded): Profit-sell buy-guard: profit-sold 2026-09-21 @ 302.14 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-15.143%, need > 0.142% [asset-scaled, x1.77])
- **SMCI** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 43.33 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.062%, need > 0.308% [asset-scaled, x1.54]); upturn not confirmed (leg3 close_yesterday→today change=-10.065%, need > 0.123% [asset-scaled, x1.54])
- **IONQ** (excluded): liquidated 2026-10-30 @ 29.02 — recovery (5.0%) or cooldown (6d) not yet met
- **SPCX** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 141.98 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.392%, need > 0.228% [asset-scaled, x1.14]); upturn not confirmed (leg3 close_yesterday→today change=-7.045%, need > 0.091% [asset-scaled, x1.14])
- **AMZN** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 262.07 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-3.968%, need > 0.150% [asset-scaled, x0.75]); upturn not confirmed (leg3 close_yesterday→today change=-3.690%, need > 0.060% [asset-scaled, x0.75])
- **NVDA** (excluded): Profit-sell buy-guard: profit-sold 2026-09-21 @ 224.645 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-14.997%, need > 0.072% [asset-scaled, x0.90])
- **ORCL** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 142.52 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-8.781%, need > 0.115% [asset-scaled, x1.44])
- **MSFT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-06 @ 532.34 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.422%, need > 0.136% [asset-scaled, x0.68]); upturn not confirmed (leg3 close_yesterday→today change=-2.486%, need > 0.054% [asset-scaled, x0.68])
- **HOOD** (excluded): liquidated 2026-11-16 @ 74.9 — recovery (5.0%) or cooldown (6d) not yet met
- **AAPL** (excluded): Profit-sell buy-guard: profit-sold 2026-09-11 @ 331.28 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.157%, need > 0.099% [asset-scaled, x0.50]); upturn not confirmed (leg3 close_yesterday→today change=-1.438%, need > 0.040% [asset-scaled, x0.50])
- **META** (excluded): Profit-sell buy-guard: profit-sold 2026-10-05 @ 740.2801 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-5.837%, need > 0.051% [asset-scaled, x0.64])
- **JPM** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 343.61 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.824%, need > 0.043% [asset-scaled, x0.54])
- **BRK.B** (excluded): Profit-sell buy-guard: profit-sold 2026-10-20 @ 537.475 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.255%, need > 0.031% [asset-scaled, x0.39])
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 853.37 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-4.661%, need > 0.086% [asset-scaled, x1.08])
- **UNP** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 300.32 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.338%, need > 0.101% [asset-scaled, x0.50]); upturn not confirmed (leg3 close_yesterday→today change=-0.449%, need > 0.040% [asset-scaled, x0.50])
- **COP** (excluded): Profit-sell buy-guard: profit-sold 2026-09-04 @ 133.4425 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.430%, need > -0.033% [asset-scaled, x0.66])
- **LIN** (excluded): Profit-sell buy-guard: profit-sold 2026-11-11 @ 526.11 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.890%, need > 0.026% [asset-scaled, x0.32])
- **FCX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-22 @ 73.75 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-6.667%, need > 0.082% [asset-scaled, x1.02])
- **DUK** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 127.175 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.161%, need > 0.060% [asset-scaled, x0.30])
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-09 @ 81.355 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.513%, need > 0.373% [asset-scaled, x1.86]); upturn not confirmed (leg3 close_yesterday→today change=-17.671%, need > 0.149% [asset-scaled, x1.86])
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-26 @ 394.795 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.041%, need > 0.209% [asset-scaled, x1.04]); upturn not confirmed (leg3 close_yesterday→today change=-7.958%, need > 0.084% [asset-scaled, x1.04])
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-13 @ 353.38 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.599%, need > 0.183% [asset-scaled, x0.92]); upturn not confirmed (leg3 close_yesterday→today change=-1.471%, need > 0.073% [asset-scaled, x0.92])
- **AMD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-08 @ 491.68 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-6.264%, need > 0.441% [asset-scaled, x2.20]); upturn not confirmed (leg3 close_yesterday→today change=-14.642%, need > 0.176% [asset-scaled, x2.20])
- **NEE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-04 @ 86.9098 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.428%, need > 0.085% [asset-scaled, x0.42])
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-29 @ 253.0 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.490%, need > 0.411% [asset-scaled, x2.05]); upturn not confirmed (leg3 close_yesterday→today change=-12.061%, need > 0.164% [asset-scaled, x2.05])
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-4.105%, need > 0.258% [asset-scaled, x1.29]); upturn not confirmed (leg3 close_yesterday→today change=-14.291%, need > 0.103% [asset-scaled, x1.29])
- **GM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-10 @ 89.23 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.315%, need > 0.065% [asset-scaled, x0.81])
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.245%, need > 0.113% [asset-scaled, x0.57]); upturn not confirmed (leg3 close_yesterday→today change=-2.480%, need > 0.045% [asset-scaled, x0.57])
- **GE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 382.1775 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.546%, need > 0.158% [asset-scaled, x0.79]); upturn not confirmed (leg3 close_yesterday→today change=-2.351%, need > 0.063% [asset-scaled, x0.79])
- **LTRN** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-17.508%, need > 0.206% [asset-scaled, x2.58])
- **CVX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-06 @ 208.5137 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.296%, need > -0.028% [asset-scaled, x0.56])
- **SO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-02 @ 94.67 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.865%, need > 0.058% [asset-scaled, x0.29])
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-30 @ 188.19 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.886%, need > 0.111% [asset-scaled, x0.55])
- **EQIX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-09 @ 1064.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.171%, need > 0.136% [asset-scaled, x0.68]); upturn not confirmed (leg3 close_yesterday→today change=-4.129%, need > 0.054% [asset-scaled, x0.68])
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.715%, need > 0.166% [asset-scaled, x0.83])

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $0.24) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| COST | 66.07 | 1088.66 | 1061.04 | +1.75 | +2.60 | +20.42 |
| WMT | 60.85 | 126.62 | 125.33 | +1.71 | +1.03 | +13.59 |
| PG | 56.44 | 168.93 | 166.33 | +1.00 | +1.56 | +9.00 |
| NEE | 57.94 | 84.89 | 85.61 | -1.02 | -0.84 | +6.08 |
| SO | 54.71 | 93.62 | 93.14 | +0.07 | +0.52 | +5.30 |
| HD | 55.49 | 342.03 | 345.23 | +0.10 | -0.93 | +4.66 |
| GE | 52.55 | 325.67 | 326.97 | -4.34 | -0.40 | -2.18 |
| LLY | 50.92 | 1396.29 | 1400.10 | -3.06 | -0.27 | -2.41 |
| SHW | 48.54 | 346.83 | 350.32 | -1.24 | -1.00 | -3.71 |
| JNJ | 48.48 | 275.99 | 277.44 | -1.72 | -0.52 | -3.76 |
| EQIX | 50.48 | 1035.91 | 1040.25 | -5.62 | -0.42 | -5.56 |
| AVGO | 52.51 | 341.45 | 333.20 | -11.17 | +2.48 | -6.18 |
| GM | 51.56 | 84.44 | 87.21 | -5.37 | -3.18 | -6.99 |
| AMT | 44.00 | 186.56 | 189.46 | -0.84 | -1.53 | -8.37 |
| V | 42.99 | 416.84 | 421.33 | -2.69 | -1.07 | -10.77 |
| TSLA | 48.37 | 381.64 | 384.07 | -9.13 | -0.63 | -11.39 |
| PLD | 36.68 | 126.67 | 129.05 | -2.19 | -1.84 | -17.36 |
| CVX | 34.31 | 213.16 | 216.70 | -1.58 | -1.63 | -18.90 |
| XOM | 32.27 | 165.55 | 169.69 | -2.80 | -2.44 | -22.96 |
| F | 35.15 | 11.68 | 12.24 | -3.53 | -4.61 | -22.99 |
| AMD | 45.03 | 513.14 | 520.80 | -16.84 | -1.47 | -23.28 |
| VRT | 44.76 | 195.20 | 203.98 | -15.43 | -4.31 | -24.97 |
| IBM | 33.70 | 237.13 | 247.59 | -4.83 | -4.23 | -25.35 |
| NFLX | 28.62 | 61.14 | 63.87 | -6.70 | -4.27 | -32.36 |
| GOOG | 24.31 | 282.58 | 291.15 | -5.48 | -2.95 | -34.11 |
| UNH | 19.46 | 379.82 | 403.71 | -10.04 | -5.92 | -46.49 |
| TQQQ | 31.92 | 54.44 | 59.40 | -23.50 | -8.34 | -49.92 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$74,980.35**
- `net_realized_gains_ytd_effective` (post-sells): **$74,980.35**
- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **$25,000.00**
- `tax_reserve` (final, after subtracting paid taxes): **$16,239.19**

## GET THE PROFITS Sells
- none fired this cycle

## Sell Cleanup Pass
- none fired this cycle

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)
- none this cycle

## Total_High_Beta_Gains_Realized: **$0.00**
## Total_Cleanup_Gains_Realized: **$0.00**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| ALL | total unrealized losses $11,120.48 exceed total_unrealized_losses_threshold $5,000.00 — no buys this cycle | any buy |
| TSLA | loss-lot sell guard: every sellable lot is at or above the current price ($346.81) — nothing can be sold at a gain | partial profit-take sale |
| GOOG | loss-lot sell guard: every sellable lot is at or above the current price ($267.09) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | loss-lot sell guard: every sellable lot is at or above the current price ($41.65) — nothing can be sold at a gain | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($426.71) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($84.03) — nothing can be sold at a gain | partial profit-take sale |
| VRT | loss-lot sell guard: every sellable lot is at or above the current price ($165.08) — nothing can be sold at a gain | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($303.30) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($11.26) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($79.90) — nothing can be sold at a gain | partial profit-take sale |
| IBM | loss-lot sell guard: every sellable lot is at or above the current price ($225.68) — nothing can be sold at a gain | partial profit-take sale |
| NFLX | loss-lot sell guard: every sellable lot is at or above the current price ($57.05) — nothing can be sold at a gain | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($341.69) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($311.56) — nothing can be sold at a gain | partial profit-take sale |
| CVX | loss-lot sell guard: every sellable lot is at or above the current price ($209.80) — nothing can be sold at a gain | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($93.69) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($123.89) — nothing can be sold at a gain | partial profit-take sale |
| AMT | loss-lot sell guard: every sellable lot is at or above the current price ($185.00) — nothing can be sold at a gain | partial profit-take sale |
| EQIX | loss-lot sell guard: every sellable lot is at or above the current price ($977.68) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($342.51) — nothing can be sold at a gain | partial profit-take sale |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-2,027.52 | -96.55% |
| SHW | 106d | 2026-08-06 | $-110.92 | -5.54% |
| GE | 105d | 2026-08-07 | $-400.62 | -16.30% |
| AVGO | 100d | 2026-08-12 | $-1,196.57 | -27.96% |
| F | 98d | 2026-08-14 | $-526.89 | -23.54% |
| NFLX | 79d | 2026-09-02 | $-1.97 | -29.40% |
| TQQQ | 42d | 2026-10-09 | $-16.49 | -48.34% |
| GOOG | 38d | 2026-10-13 | $-1,373.43 | -25.02% |
| AMD | 38d | 2026-10-13 | $-1,725.78 | -28.76% |
| TSLA | 18d | 2026-11-02 | $-843.36 | -14.06% |
| VRT | 17d | 2026-11-03 | $-1,770.26 | -29.38% |
| UNH | 17d | 2026-11-03 | $-1,063.14 | -17.32% |
| IBM | 16d | 2026-11-04 | $-699.63 | -11.61% |
| CVX | 15d | 2026-11-05 | $-259.20 | -4.38% |
| SO | 15d | 2026-11-05 | $-24.57 | -0.41% |
| AMT | 11d | 2026-11-09 | $-113.03 | -2.78% |
| PLD | 9d | 2026-11-11 | $-12.38 | -8.65% |
| NEE | 8d | 2026-11-12 | $-207.66 | -4.52% |

## Loss-Only Lot Assets (every sellable lot underwater)
19 asset(s), $63,915.55 market value, $-13,041.34 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $0.24 | $72.48 | $-2,027.52 | -96.55% | 1 | $7.00 / $7.00 |
| TQQQ | 0.4232 | $80.62 | $41.65 | $17.63 | $-16.49 | -48.34% | 1 | $80.62 / $80.62 |
| NFLX | 0.0830 | $80.80 | $57.05 | $4.74 | $-1.97 | -29.40% | 1 | $80.80 / $80.80 |
| VRT | 25.7717 | $233.77 | $165.08 | $4,254.40 | $-1,770.35 | -29.38% | 2 | $233.24 / $233.79 |
| AMD | 10.0167 | $599.00 | $426.71 | $4,274.22 | $-1,725.78 | -28.76% | 1 | $599.00 / $599.00 |
| AVGO | 10.1667 | $421.00 | $303.30 | $3,083.59 | $-1,196.60 | -27.96% | 2 | $377.86 / $423.11 |
| GOOG ⚠ | 15.4110 | $360.29 | $267.09 | $4,116.13 | $-1,436.32 | -25.87% | 8 | $344.59 / $377.51 |
| F | 151.9817 | $14.73 | $11.26 | $1,711.80 | $-526.38 | -23.52% | 4 | $14.30 / $14.85 |
| UNH | 14.8483 | $413.37 | $341.69 | $5,073.50 | $-1,064.34 | -17.34% | 2 | $403.15 / $413.61 |
| GE | 6.6016 | $372.24 | $311.56 | $2,056.77 | $-400.64 | -16.30% | 2 | $356.04 / $373.67 |
| TSLA ⚠ | 14.8688 | $406.04 | $346.81 | $5,156.64 | $-880.68 | -14.59% | 1 | $406.04 / $406.04 |
| IBM | 23.6003 | $255.32 | $225.68 | $5,326.01 | $-699.52 | -11.61% | 2 | $254.37 / $255.34 |
| PLD | 1.0562 | $135.62 | $123.89 | $130.86 | $-12.39 | -8.65% | 2 | $129.03 / $139.86 |
| EQIX | 5.6994 | $1,052.75 | $977.68 | $5,572.17 | $-427.85 | -7.13% | 1 | $1,052.75 / $1,052.75 |
| GM | 70.7589 | $84.80 | $79.90 | $5,653.64 | $-346.72 | -5.78% | 1 | $84.80 / $84.80 |
| SHW | 5.5210 | $362.60 | $342.51 | $1,891.00 | $-110.92 | -5.54% | 1 | $362.60 / $362.60 |
| CVX | 27.0000 | $219.40 | $209.80 | $5,664.60 | $-259.20 | -4.38% | 1 | $219.40 / $219.40 |
| AMT | 21.3671 | $190.29 | $185.00 | $3,952.91 | $-113.11 | -2.78% | 2 | $189.49 / $190.50 |
| SO | 63.0000 | $94.08 | $93.69 | $5,902.47 | $-24.57 | -0.41% | 1 | $94.08 / $94.08 |

⚠ = the broker's blended `avg_cost_basis` materially disagrees with the cost of the actual lots, so the two views of this position tell different stories:
- **GOOG**: `avg_cost_basis` $356.21 vs. lot-weighted $360.29 (price $267.09) — the blended average implies -25.02%, the lots imply -25.87%
- **TSLA**: `avg_cost_basis` $403.53 vs. lot-weighted $406.04 (price $346.81) — the blended average implies -14.06%, the lots imply -14.59%

## Deferred Wash-Sale Loss Tracking (v2.84.0, observational)
- none this cycle

## Orders Placed
```
```

# 2026-11-20 — Scheduled Rebalance Check — EXECUTED (0 sell(s), 0 buy(s))

**Status:** EXECUTED. 0 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$55,177.44**
- `cash` (ledger): **$55,177.44**
- `current_cash` (post-cap): **$55,177.44**
- `account_balance`: **$125,399.65**

## Drawdown Audit
Emergency liquidations: none

## Unrealized-Loss Buy Guard
- Total unrealized losses (underwater positions only): **$9,228.30** vs. `total_unrealized_losses_threshold` **$5,000.00** — **BUYS HALTED** — no buy of any kind this cycle

## Excluded / Buy-Guarded Symbols (Step 2)
- **INTC** (excluded): Profit-sell buy-guard: profit-sold 2026-09-30 @ 119.67 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.906%, need > -0.115% [asset-scaled, x2.29]); upturn not confirmed (leg3 close_yesterday→today change=-1.163%, need > 0.183% [asset-scaled, x2.29])
- **PLTR** (excluded): Profit-sell buy-guard: profit-sold 2026-10-20 @ 193.8 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.073%, need > 0.189% [asset-scaled, x0.95]); upturn not confirmed (leg3 close_yesterday→today change=-1.893%, need > 0.076% [asset-scaled, x0.95])
- **MU** (excluded): Profit-sell buy-guard: profit-sold 2026-09-08 @ 1020.06 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-6.766%, need > 0.146% [asset-scaled, x1.82])
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **MSTR** (excluded): Profit-sell buy-guard: profit-sold 2026-10-12 @ 155.37 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.713%, need > 0.095% [asset-scaled, x1.18])
- **COIN** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 198.75 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=+0.028%, need > 0.093% [asset-scaled, x1.17])
- **ARM** (excluded): Profit-sell buy-guard: profit-sold 2026-09-21 @ 302.14 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-6.415%, need > 0.142% [asset-scaled, x1.77])
- **SMCI** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 43.33 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.001%, need > 0.308% [asset-scaled, x1.54]); upturn not confirmed (leg3 close_yesterday→today change=-3.735%, need > 0.123% [asset-scaled, x1.54])
- **IONQ** (excluded): liquidated 2026-10-30 @ 29.02 — recovery (5.0%) or cooldown (6d) not yet met
- **SPCX** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 141.98 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.363%, need > 0.228% [asset-scaled, x1.14]); upturn not confirmed (leg3 close_yesterday→today change=-4.824%, need > 0.091% [asset-scaled, x1.14])
- **AMZN** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 262.07 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-3.857%, need > 0.150% [asset-scaled, x0.75]); upturn not confirmed (leg3 close_yesterday→today change=-0.767%, need > 0.060% [asset-scaled, x0.75])
- **NVDA** (excluded): Profit-sell buy-guard: profit-sold 2026-09-21 @ 224.645 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-3.790%, need > 0.072% [asset-scaled, x0.90])
- **ORCL** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 142.52 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.570%, need > 0.115% [asset-scaled, x1.44])
- **MSFT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-06 @ 532.34 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.411%, need > 0.136% [asset-scaled, x0.68])
- **HOOD** (excluded): liquidated 2026-11-16 @ 74.9 — recovery (5.0%) or cooldown (6d) not yet met
- **AAPL** (excluded): Profit-sell buy-guard: profit-sold 2026-09-11 @ 331.28 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.154%, need > 0.099% [asset-scaled, x0.50])
- **META** (excluded): Profit-sell buy-guard: profit-sold 2026-10-05 @ 740.2801 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.897%, need > 0.051% [asset-scaled, x0.64])
- **JPM** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 343.61 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.189%, need > 0.043% [asset-scaled, x0.54])
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 853.37 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.861%, need > 0.086% [asset-scaled, x1.08])
- **UNP** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 300.32 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.319%, need > 0.101% [asset-scaled, x0.50])
- **COP** (excluded): Profit-sell buy-guard: profit-sold 2026-09-04 @ 133.4425 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.435%, need > -0.033% [asset-scaled, x0.66])
- **FCX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-22 @ 73.75 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.440%, need > 0.082% [asset-scaled, x1.02])
- **DUK** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 127.175 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.161%, need > 0.060% [asset-scaled, x0.30])
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-09 @ 81.355 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-1.329%, need > 0.373% [asset-scaled, x1.86]); upturn not confirmed (leg3 close_yesterday→today change=-3.364%, need > 0.149% [asset-scaled, x1.86])
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-26 @ 394.795 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.974%, need > 0.209% [asset-scaled, x1.04]); upturn not confirmed (leg3 close_yesterday→today change=-1.064%, need > 0.084% [asset-scaled, x1.04])
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-13 @ 353.38 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.576%, need > 0.183% [asset-scaled, x0.92])
- **AMD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-08 @ 491.68 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-5.711%, need > 0.441% [asset-scaled, x2.20]); upturn not confirmed (leg3 close_yesterday→today change=-4.521%, need > 0.176% [asset-scaled, x2.20])
- **NEE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-04 @ 86.9098 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.426%, need > 0.085% [asset-scaled, x0.42])
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-29 @ 253.0 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.349%, need > 0.411% [asset-scaled, x2.05]); upturn not confirmed (leg3 close_yesterday→today change=-5.721%, need > 0.164% [asset-scaled, x2.05])
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-3.662%, need > 0.258% [asset-scaled, x1.29]); upturn not confirmed (leg3 close_yesterday→today change=-1.965%, need > 0.103% [asset-scaled, x1.29])
- **GM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-10 @ 89.23 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.603%, need > 0.065% [asset-scaled, x0.81])
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.237%, need > 0.113% [asset-scaled, x0.57])
- **GE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 382.1775 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.533%, need > 0.158% [asset-scaled, x0.79]); upturn not confirmed (leg3 close_yesterday→today change=-0.024%, need > 0.063% [asset-scaled, x0.79])
- **LTRN** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.320%, need > 0.206% [asset-scaled, x2.58])
- **CVX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-06 @ 208.5137 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.299%, need > -0.028% [asset-scaled, x0.56])
- **SO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-02 @ 94.67 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.859%, need > 0.058% [asset-scaled, x0.29])
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-30 @ 188.19 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.890%, need > 0.111% [asset-scaled, x0.55])
- **EQIX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-09 @ 1064.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.168%, need > 0.136% [asset-scaled, x0.68]); upturn not confirmed (leg3 close_yesterday→today change=-2.371%, need > 0.054% [asset-scaled, x0.68])
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.708%, need > 0.166% [asset-scaled, x0.83])

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $0.28) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| COST | 66.07 | 1088.66 | 1061.04 | +1.78 | +2.60 | +20.45 |
| WMT | 60.85 | 126.62 | 125.33 | +1.92 | +1.03 | +13.80 |
| PG | 56.44 | 168.93 | 166.33 | +1.32 | +1.56 | +9.32 |
| BRK.B | 57.90 | 579.20 | 575.16 | -0.69 | +0.70 | +7.92 |
| NEE | 57.94 | 84.89 | 85.61 | -0.35 | -0.84 | +6.76 |
| SO | 54.71 | 93.62 | 93.14 | +0.71 | +0.52 | +5.94 |
| HD | 55.49 | 342.03 | 345.23 | +1.00 | -0.93 | +5.56 |
| AVGO | 52.51 | 341.45 | 333.20 | -0.43 | +2.48 | +4.56 |
| GE | 52.55 | 325.67 | 326.97 | -2.11 | -0.40 | +0.04 |
| LIN | 50.00 | 516.90 | 519.65 | -0.50 | -0.53 | -1.04 |
| LLY | 50.92 | 1396.29 | 1400.10 | -2.28 | -0.27 | -1.63 |
| SHW | 48.54 | 346.83 | 350.32 | -0.19 | -1.00 | -2.65 |
| JNJ | 48.48 | 275.99 | 277.44 | -1.62 | -0.52 | -3.66 |
| EQIX | 50.48 | 1035.91 | 1040.25 | -4.00 | -0.42 | -3.94 |
| TSLA | 48.37 | 381.64 | 384.07 | -2.93 | -0.63 | -5.19 |
| GM | 51.56 | 84.44 | 87.21 | -3.76 | -3.18 | -5.37 |
| AMT | 44.00 | 186.56 | 189.46 | -1.24 | -1.53 | -8.77 |
| V | 42.99 | 416.84 | 421.33 | -2.44 | -1.07 | -10.52 |
| AMD | 45.03 | 513.14 | 520.80 | -8.79 | -1.47 | -15.23 |
| PLD | 36.68 | 126.67 | 129.05 | -1.38 | -1.84 | -16.55 |
| VRT | 44.76 | 195.20 | 203.98 | -10.36 | -4.31 | -19.90 |
| CVX | 34.31 | 213.16 | 216.70 | -2.68 | -1.63 | -20.01 |
| F | 35.15 | 11.68 | 12.24 | -0.99 | -4.61 | -20.45 |
| XOM | 32.27 | 165.55 | 169.69 | -3.71 | -2.44 | -23.88 |
| IBM | 33.70 | 237.13 | 247.59 | -3.39 | -4.23 | -23.91 |
| NFLX | 28.62 | 61.14 | 63.87 | -3.46 | -4.27 | -29.12 |
| GOOG | 24.31 | 282.58 | 291.15 | -1.78 | -2.95 | -30.41 |
| TQQQ | 31.92 | 54.44 | 59.40 | -12.91 | -8.34 | -39.33 |
| UNH | 19.46 | 379.82 | 403.71 | -10.52 | -5.92 | -46.97 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$74,980.35**
- `net_realized_gains_ytd_effective` (post-sells): **$74,980.35**
- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **$25,000.00**
- `tax_reserve` (final, after subtracting paid taxes): **$16,239.19**

## GET THE PROFITS Sells
- none fired this cycle

## Sell Cleanup Pass
- none fired this cycle

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)
- none this cycle

## Total_High_Beta_Gains_Realized: **$0.00**
## Total_Cleanup_Gains_Realized: **$0.00**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| ALL | total unrealized losses $9,228.30 exceed total_unrealized_losses_threshold $5,000.00 — no buys this cycle | any buy |
| TSLA | loss-lot sell guard: every sellable lot is at or above the current price ($370.47) — nothing can be sold at a gain | partial profit-take sale |
| GOOG | loss-lot sell guard: every sellable lot is at or above the current price ($277.54) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | loss-lot sell guard: every sellable lot is at or above the current price ($47.41) — nothing can be sold at a gain | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($468.03) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($84.60) — nothing can be sold at a gain | partial profit-take sale |
| VRT | loss-lot sell guard: every sellable lot is at or above the current price ($174.98) — nothing can be sold at a gain | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($339.97) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($11.56) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($81.26) — nothing can be sold at a gain | partial profit-take sale |
| IBM | loss-lot sell guard: every sellable lot is at or above the current price ($229.10) — nothing can be sold at a gain | partial profit-take sale |
| NFLX | loss-lot sell guard: every sellable lot is at or above the current price ($59.03) — nothing can be sold at a gain | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($339.87) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($318.81) — nothing can be sold at a gain | partial profit-take sale |
| CVX | loss-lot sell guard: every sellable lot is at or above the current price ($207.44) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($124.92) — nothing can be sold at a gain | partial profit-take sale |
| AMT | loss-lot sell guard: every sellable lot is at or above the current price ($184.25) — nothing can be sold at a gain | partial profit-take sale |
| EQIX | loss-lot sell guard: every sellable lot is at or above the current price ($994.47) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($346.16) — nothing can be sold at a gain | partial profit-take sale |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-2,015.94 | -96.00% |
| SHW | 106d | 2026-08-06 | $-90.77 | -4.53% |
| GE | 105d | 2026-08-07 | $-352.76 | -14.35% |
| AVGO | 100d | 2026-08-12 | $-823.80 | -19.25% |
| F | 98d | 2026-08-14 | $-481.78 | -21.52% |
| NFLX | 79d | 2026-09-02 | $-1.81 | -26.95% |
| TQQQ | 42d | 2026-10-09 | $-14.05 | -41.19% |
| GOOG | 38d | 2026-10-13 | $-1,212.38 | -22.09% |
| AMD | 38d | 2026-10-13 | $-1,311.89 | -21.86% |
| TSLA | 18d | 2026-11-02 | $-491.56 | -8.19% |
| VRT | 17d | 2026-11-03 | $-1,515.12 | -25.15% |
| UNH | 17d | 2026-11-03 | $-1,090.16 | -17.76% |
| IBM | 16d | 2026-11-04 | $-618.80 | -10.27% |
| CVX | 15d | 2026-11-05 | $-322.79 | -5.45% |
| SO | 15d | 2026-11-05 | $13.23 | +0.22% |
| AMT | 11d | 2026-11-09 | $-129.06 | -3.17% |
| PLD | 9d | 2026-11-11 | $-11.30 | -7.89% |
| NEE | 8d | 2026-11-12 | $-177.62 | -3.86% |

## Loss-Only Lot Assets (every sellable lot underwater)
18 asset(s), $59,862.23 market value, $-11,167.62 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $0.28 | $84.06 | $-2,015.94 | -96.00% | 1 | $7.00 / $7.00 |
| TQQQ | 0.4232 | $80.62 | $47.41 | $20.07 | $-14.05 | -41.19% | 1 | $80.62 / $80.62 |
| NFLX | 0.0830 | $80.80 | $59.03 | $4.90 | $-1.81 | -26.95% | 1 | $80.80 / $80.80 |
| VRT | 25.7717 | $233.77 | $174.98 | $4,509.54 | $-1,515.21 | -25.15% | 2 | $233.24 / $233.79 |
| GOOG ⚠ | 15.4110 | $360.29 | $277.54 | $4,277.17 | $-1,275.27 | -22.97% | 8 | $344.59 / $377.51 |
| AMD | 10.0167 | $599.00 | $468.03 | $4,688.11 | $-1,311.89 | -21.86% | 1 | $599.00 / $599.00 |
| F | 151.9817 | $14.73 | $11.56 | $1,756.91 | $-481.27 | -21.50% | 4 | $14.30 / $14.85 |
| AVGO | 10.1667 | $421.00 | $339.97 | $3,456.36 | $-823.83 | -19.25% | 2 | $377.86 / $423.11 |
| UNH | 14.8483 | $413.37 | $339.87 | $5,046.48 | $-1,091.36 | -17.78% | 2 | $403.15 / $413.61 |
| GE | 6.6016 | $372.24 | $318.81 | $2,104.63 | $-352.78 | -14.36% | 2 | $356.04 / $373.67 |
| IBM | 23.6003 | $255.32 | $229.10 | $5,406.84 | $-618.69 | -10.27% | 2 | $254.37 / $255.34 |
| TSLA ⚠ | 14.8688 | $406.04 | $370.47 | $5,508.44 | $-528.88 | -8.76% | 1 | $406.04 / $406.04 |
| PLD | 1.0562 | $135.62 | $124.92 | $131.95 | $-11.30 | -7.89% | 2 | $129.03 / $139.86 |
| EQIX | 5.6994 | $1,052.75 | $994.47 | $5,667.86 | $-332.16 | -5.54% | 1 | $1,052.75 / $1,052.75 |
| CVX | 27.0000 | $219.40 | $207.44 | $5,601.01 | $-322.79 | -5.45% | 1 | $219.40 / $219.40 |
| SHW | 5.5210 | $362.60 | $346.16 | $1,911.15 | $-90.77 | -4.53% | 1 | $362.60 / $362.60 |
| GM | 70.7589 | $84.80 | $81.26 | $5,749.87 | $-250.49 | -4.17% | 1 | $84.80 / $84.80 |
| AMT | 21.3671 | $190.29 | $184.25 | $3,936.89 | $-129.13 | -3.18% | 2 | $189.49 / $190.50 |

⚠ = the broker's blended `avg_cost_basis` materially disagrees with the cost of the actual lots, so the two views of this position tell different stories:
- **GOOG**: `avg_cost_basis` $356.21 vs. lot-weighted $360.29 (price $277.54) — the blended average implies -22.09%, the lots imply -22.97%
- **TSLA**: `avg_cost_basis` $403.53 vs. lot-weighted $406.04 (price $370.47) — the blended average implies -8.19%, the lots imply -8.76%

## Deferred Wash-Sale Loss Tracking (v2.84.0, observational)
- none this cycle

## Orders Placed
```
```

# 2026-11-19 — Scheduled Rebalance Check — EXECUTED (0 sell(s), 0 buy(s))

**Status:** EXECUTED. 0 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$55,177.44**
- `cash` (ledger): **$55,177.44**
- `current_cash` (post-cap): **$55,177.44**
- `account_balance`: **$125,670.10**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **PLTR** (excluded): Profit-sell buy-guard: profit-sold 2026-10-20 @ 193.8 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.071%, need > -0.047% [asset-scaled, x0.93]); upturn not confirmed (leg3 close_yesterday→today change=-1.051%, need > 0.075% [asset-scaled, x0.93])
- **MU** (excluded): Profit-sell buy-guard: profit-sold 2026-09-08 @ 1020.06 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.041%, need > 0.145% [asset-scaled, x1.82])
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **MSTR** (excluded): Profit-sell buy-guard: profit-sold 2026-10-12 @ 155.37 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-3.306%, need > 0.093% [asset-scaled, x1.16])
- **COIN** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 198.75 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.163%, need > 0.092% [asset-scaled, x1.15])
- **ARM** (excluded): Profit-sell buy-guard: profit-sold 2026-09-21 @ 302.14 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-4.670%, need > 0.356% [asset-scaled, x1.78]); upturn not confirmed (leg3 close_yesterday→today change=-2.341%, need > 0.142% [asset-scaled, x1.78])
- **SMCI** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 43.33 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.949%, need > -0.076% [asset-scaled, x1.53]); upturn not confirmed (leg3 close_yesterday→today change=-0.536%, need > 0.122% [asset-scaled, x1.53])
- **IONQ** (excluded): liquidated 2026-10-30 @ 29.02 — recovery (5.0%) or cooldown (6d) not yet met
- **SPCX** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 141.98 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-3.160%, need > 0.248% [asset-scaled, x1.24]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.310%, need > -0.062% [asset-scaled, x1.24]); upturn not confirmed (leg3 close_yesterday→today change=-4.474%, need > 0.099% [asset-scaled, x1.24])
- **AMZN** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 262.07 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.054%, need > 0.150% [asset-scaled, x0.75]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.816%, need > -0.038% [asset-scaled, x0.75]); upturn not confirmed (leg3 close_yesterday→today change=-3.731%, need > 0.060% [asset-scaled, x0.75])
- **NVDA** (excluded): Profit-sell buy-guard: profit-sold 2026-09-21 @ 224.645 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.228%, need > 0.071% [asset-scaled, x0.89])
- **ORCL** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 142.52 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.258%, need > 0.112% [asset-scaled, x1.41])
- **MSFT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-06 @ 532.34 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.409%, need > -0.033% [asset-scaled, x0.67]); upturn not confirmed (leg3 close_yesterday→today change=-1.305%, need > 0.053% [asset-scaled, x0.67])
- **HOOD** (excluded): liquidated 2026-11-16 @ 74.9 — recovery (5.0%) or cooldown (6d) not yet met
- **AAPL** (excluded): Profit-sell buy-guard: profit-sold 2026-09-11 @ 331.28 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.155%, need > -0.024% [asset-scaled, x0.49]); upturn not confirmed (leg3 close_yesterday→today change=-0.879%, need > 0.039% [asset-scaled, x0.49])
- **META** (excluded): Profit-sell buy-guard: profit-sold 2026-10-05 @ 740.2801 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.757%, need > 0.058% [asset-scaled, x0.73])
- **LLY** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 1415.74 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.095%, need > 0.054% [asset-scaled, x0.67])
- **JNJ** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 275.33 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.501%, need > 0.039% [asset-scaled, x0.49])
- **JPM** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 343.61 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.922%, need > 0.042% [asset-scaled, x0.53])
- **BRK.B** (excluded): Profit-sell buy-guard: profit-sold 2026-10-20 @ 537.475 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.593%, need > 0.031% [asset-scaled, x0.39])
- **V** (excluded): Profit-sell buy-guard: profit-sold 2026-08-26 @ 383.44 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-3.083%, need > 0.039% [asset-scaled, x0.48])
- **HD** (excluded): Profit-sell buy-guard: profit-sold 2026-11-12 @ 353.53 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.024%, need > 0.056% [asset-scaled, x0.70])
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 853.37 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.055%, need > 0.213% [asset-scaled, x1.07]); upturn not confirmed (leg3 close_yesterday→today change=-3.134%, need > 0.085% [asset-scaled, x1.07])
- **UNP** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 300.32 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.332%, need > -0.025% [asset-scaled, x0.49]); upturn not confirmed (leg3 close_yesterday→today change=-3.534%, need > 0.040% [asset-scaled, x0.49])
- **WMT** (excluded): Profit-sell buy-guard: profit-sold 2026-11-16 @ 129.18 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.353%, need > 0.036% [asset-scaled, x0.46])
- **PG** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 164.365 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.140%, need > 0.041% [asset-scaled, x0.51])
- **COST** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 1012.9 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.562%, need > 0.033% [asset-scaled, x0.42])
- **XOM** (excluded): Profit-sell buy-guard: profit-sold 2026-09-09 @ 164.59 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.213%, need > 0.120% [asset-scaled, x0.60]); upturn not confirmed (leg3 close_yesterday→today change=-0.823%, need > 0.048% [asset-scaled, x0.60])
- **LIN** (excluded): Profit-sell buy-guard: profit-sold 2026-11-11 @ 526.11 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.261%, need > 0.027% [asset-scaled, x0.34])
- **FCX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-22 @ 73.75 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.222%, need > 0.205% [asset-scaled, x1.03]); upturn not confirmed (leg3 close_yesterday→today change=-3.908%, need > 0.082% [asset-scaled, x1.03])
- **DUK** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 127.175 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.163%, need > -0.018% [asset-scaled, x0.37]); upturn not confirmed (leg3 close_yesterday→today change=-1.167%, need > 0.030% [asset-scaled, x0.37])
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-09 @ 81.355 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.269%, need > -0.093% [asset-scaled, x1.85]); upturn not confirmed (leg3 close_yesterday→today change=-5.627%, need > 0.148% [asset-scaled, x1.85])
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-26 @ 394.795 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.098%, need > 0.206% [asset-scaled, x1.03]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.959%, need > -0.052% [asset-scaled, x1.03]); upturn not confirmed (leg3 close_yesterday→today change=-1.988%, need > 0.082% [asset-scaled, x1.03])
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-13 @ 353.38 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.586%, need > -0.045% [asset-scaled, x0.90]); upturn not confirmed (leg3 close_yesterday→today change=-2.282%, need > 0.072% [asset-scaled, x0.90])
- **AMD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-08 @ 491.68 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.179%, need > 0.433% [asset-scaled, x2.16]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-5.498%, need > -0.108% [asset-scaled, x2.16]); upturn not confirmed (leg3 close_yesterday→today change=-9.033%, need > 0.173% [asset-scaled, x2.16])
- **NEE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-04 @ 86.9098 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.430%, need > -0.025% [asset-scaled, x0.49]); upturn not confirmed (leg3 close_yesterday→today change=-1.339%, need > 0.039% [asset-scaled, x0.49])
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-29 @ 253.0 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.909%, need > 0.410% [asset-scaled, x2.05]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.198%, need > -0.102% [asset-scaled, x2.05]); upturn not confirmed (leg3 close_yesterday→today change=-4.022%, need > 0.164% [asset-scaled, x2.05])
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.352%, need > 0.257% [asset-scaled, x1.29]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.571%, need > -0.064% [asset-scaled, x1.29]); upturn not confirmed (leg3 close_yesterday→today change=-1.546%, need > 0.103% [asset-scaled, x1.29])
- **F** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-14 @ 14.4276 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.580%, need > 0.044% [asset-scaled, x0.55])
- **GM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-10 @ 89.23 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.465%, need > 0.160% [asset-scaled, x0.80]); upturn not confirmed (leg3 close_yesterday→today change=-0.558%, need > 0.064% [asset-scaled, x0.80])
- **IBM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-22 @ 250.52 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.086%, need > 0.037% [asset-scaled, x0.47])
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.240%, need > -0.030% [asset-scaled, x0.59]); upturn not confirmed (leg3 close_yesterday→today change=-2.519%, need > 0.047% [asset-scaled, x0.59])
- **UNH** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-22 @ 425.58 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-5.198%, need > 0.064% [asset-scaled, x0.80])
- **GE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 382.1775 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.382%, need > 0.150% [asset-scaled, x0.75]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.532%, need > -0.037% [asset-scaled, x0.75]); upturn not confirmed (leg3 close_yesterday→today change=-2.647%, need > 0.060% [asset-scaled, x0.75])
- **LTRN** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-13.356%, need > 0.195% [asset-scaled, x2.44])
- **SO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-02 @ 94.67 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.868%, need > -0.018% [asset-scaled, x0.36]); upturn not confirmed (leg3 close_yesterday→today change=-1.136%, need > 0.029% [asset-scaled, x0.36])
- **PLD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-11 @ 130.28 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.504%, need > 0.028% [asset-scaled, x0.35])
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-30 @ 188.19 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.905%, need > -0.027% [asset-scaled, x0.54]); upturn not confirmed (leg3 close_yesterday→today change=-1.950%, need > 0.043% [asset-scaled, x0.54])
- **EQIX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-09 @ 1064.59 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.164%, need > -0.036% [asset-scaled, x0.72]); upturn not confirmed (leg3 close_yesterday→today change=-1.612%, need > 0.057% [asset-scaled, x0.72])
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.719%, need > -0.041% [asset-scaled, x0.82]); upturn not confirmed (leg3 close_yesterday→today change=-1.771%, need > 0.065% [asset-scaled, x0.82])

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $0.29) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| AVGO | 55.61 | 340.10 | 325.25 | +2.52 | +4.57 | +12.69 |
| SO | 62.51 | 93.70 | 93.29 | -0.37 | +0.44 | +12.58 |
| NEE | 63.36 | 85.17 | 85.69 | -1.77 | -0.61 | +10.98 |
| EQIX | 55.49 | 1040.45 | 1032.34 | -1.96 | +0.79 | +4.31 |
| TSLA | 53.53 | 383.39 | 380.57 | -1.87 | +0.74 | +2.41 |
| GE | 54.17 | 327.47 | 326.29 | -2.39 | +0.36 | +2.14 |
| SHW | 53.47 | 348.56 | 350.02 | -2.29 | -0.42 | +0.76 |
| AMD | 49.98 | 518.91 | 504.02 | -6.30 | +2.96 | -3.37 |
| AMT | 48.72 | 187.93 | 189.42 | -3.53 | -0.79 | -5.60 |
| PLD | 47.69 | 127.49 | 129.15 | -3.24 | -1.28 | -6.83 |
| VRT | 47.47 | 197.81 | 202.76 | -5.49 | -2.44 | -10.45 |
| GM | 46.06 | 85.17 | 87.63 | -4.10 | -2.81 | -10.85 |
| COP | 38.40 | 138.86 | 139.26 | -2.59 | -0.29 | -14.48 |
| IBM | 39.91 | 240.40 | 248.18 | -6.88 | -3.14 | -20.11 |
| CVX | 34.40 | 214.84 | 216.82 | -3.80 | -0.91 | -20.32 |
| F | 34.60 | 11.79 | 12.33 | -4.86 | -4.43 | -24.69 |
| GOOG | 26.55 | 285.39 | 289.85 | -4.35 | -1.54 | -29.34 |
| NFLX | 29.73 | 61.83 | 64.21 | -5.62 | -3.70 | -29.60 |
| TQQQ | 34.98 | 55.77 | 59.18 | -10.98 | -5.76 | -31.76 |
| INTC | 27.53 | 58.76 | 63.40 | -4.74 | -7.32 | -34.53 |
| UNH | 27.18 | 392.08 | 403.12 | -15.16 | -2.74 | -40.73 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$74,980.35**
- `net_realized_gains_ytd_effective` (post-sells): **$74,980.35**
- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **$25,000.00**
- `tax_reserve` (final, after subtracting paid taxes): **$16,239.19**

## GET THE PROFITS Sells
- none fired this cycle

## Sell Cleanup Pass
- none fired this cycle

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)
- none this cycle

## Total_High_Beta_Gains_Realized: **$0.00**
## Total_Cleanup_Gains_Realized: **$0.00**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| INTC | Momentum_Score (-34.53) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| COP | Momentum_Score (-14.48) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| INTC | Position Cap Top-Up: Momentum_Score (-34.53) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| CVX | Position Cap Top-Up: Momentum_Score (-20.32) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| COP | Position Cap Top-Up: Momentum_Score (-14.48) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| TSLA | loss-lot sell guard: every sellable lot is at or above the current price ($376.24) — nothing can be sold at a gain | partial profit-take sale |
| GOOG | loss-lot sell guard: every sellable lot is at or above the current price ($272.97) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | loss-lot sell guard: every sellable lot is at or above the current price ($49.65) — nothing can be sold at a gain | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($486.22) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($83.66) — nothing can be sold at a gain | partial profit-take sale |
| VRT | loss-lot sell guard: every sellable lot is at or above the current price ($186.96) — nothing can be sold at a gain | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($348.66) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($11.21) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($81.67) — nothing can be sold at a gain | partial profit-take sale |
| IBM | loss-lot sell guard: every sellable lot is at or above the current price ($223.86) — nothing can be sold at a gain | partial profit-take sale |
| NFLX | loss-lot sell guard: every sellable lot is at or above the current price ($58.35) — nothing can be sold at a gain | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($332.62) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($319.64) — nothing can be sold at a gain | partial profit-take sale |
| CVX | loss-lot sell guard: every sellable lot is at or above the current price ($206.67) — nothing can be sold at a gain | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($93.35) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($123.36) — nothing can be sold at a gain | partial profit-take sale |
| AMT | loss-lot sell guard: every sellable lot is at or above the current price ($181.28) — nothing can be sold at a gain | partial profit-take sale |
| EQIX | loss-lot sell guard: every sellable lot is at or above the current price ($1020.06) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($340.57) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | below sell_or_buy_value_limit | sell |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-2,012.85 | -95.85% |
| SHW | 105d | 2026-08-06 | $-121.63 | -6.08% |
| GE | 104d | 2026-08-07 | $-347.25 | -14.13% |
| AVGO | 99d | 2026-08-12 | $-735.46 | -17.18% |
| F | 97d | 2026-08-14 | $-534.22 | -23.86% |
| NFLX | 78d | 2026-09-02 | $-1.86 | -27.78% |
| TQQQ | 41d | 2026-10-09 | $-13.11 | -38.42% |
| GOOG | 37d | 2026-10-13 | $-1,282.81 | -23.37% |
| AMD | 37d | 2026-10-13 | $-1,129.68 | -18.83% |
| TSLA | 17d | 2026-11-02 | $-405.77 | -6.76% |
| VRT | 16d | 2026-11-03 | $-1,206.38 | -20.02% |
| UNH | 16d | 2026-11-03 | $-1,197.81 | -19.52% |
| IBM | 15d | 2026-11-04 | $-742.47 | -12.32% |
| CVX | 14d | 2026-11-05 | $-343.71 | -5.80% |
| SO | 14d | 2026-11-05 | $-45.99 | -0.78% |
| AMT | 10d | 2026-11-09 | $-192.41 | -4.73% |
| PLD | 8d | 2026-11-11 | $-12.94 | -9.04% |
| NEE | 7d | 2026-11-12 | $-226.74 | -4.93% |

## Loss-Only Lot Assets (every sellable lot underwater)
20 asset(s), $70,492.66 market value, $-11,061.49 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $0.29 | $87.15 | $-2,012.85 | -95.85% | 1 | $7.00 / $7.00 |
| TQQQ | 0.4232 | $80.62 | $49.65 | $21.01 | $-13.11 | -38.42% | 1 | $80.62 / $80.62 |
| NFLX | 0.0830 | $80.80 | $58.35 | $4.85 | $-1.86 | -27.78% | 1 | $80.80 / $80.80 |
| GOOG ⚠ | 15.4110 | $360.29 | $272.97 | $4,206.74 | $-1,345.70 | -24.24% | 8 | $344.59 / $377.51 |
| F | 151.9817 | $14.73 | $11.21 | $1,704.47 | $-533.70 | -23.85% | 4 | $14.30 / $14.85 |
| VRT | 25.7717 | $233.77 | $186.96 | $4,818.28 | $-1,206.47 | -20.03% | 2 | $233.24 / $233.79 |
| UNH | 14.8483 | $413.37 | $332.62 | $4,938.83 | $-1,199.01 | -19.53% | 2 | $403.15 / $413.61 |
| AMD | 10.0167 | $599.00 | $486.22 | $4,870.32 | $-1,129.68 | -18.83% | 1 | $599.00 / $599.00 |
| AVGO | 10.1667 | $421.00 | $348.66 | $3,544.70 | $-735.48 | -17.18% | 2 | $377.86 / $423.11 |
| GE | 6.6016 | $372.24 | $319.64 | $2,110.14 | $-347.27 | -14.13% | 2 | $356.04 / $373.67 |
| IBM | 23.6003 | $255.32 | $223.86 | $5,283.17 | $-742.36 | -12.32% | 2 | $254.37 / $255.34 |
| PLD | 1.0562 | $135.62 | $123.36 | $130.30 | $-12.95 | -9.04% | 2 | $129.03 / $139.86 |
| TSLA ⚠ | 14.8688 | $406.04 | $376.24 | $5,594.23 | $-443.09 | -7.34% | 1 | $406.04 / $406.04 |
| SHW | 5.5210 | $362.60 | $340.57 | $1,880.29 | $-121.63 | -6.08% | 1 | $362.60 / $362.60 |
| CVX | 27.0000 | $219.40 | $206.67 | $5,580.09 | $-343.71 | -5.80% | 1 | $219.40 / $219.40 |
| NEE | 52.2424 | $88.00 | $83.66 | $4,370.59 | $-226.66 | -4.93% | 8 | $83.94 / $90.00 |
| AMT | 21.3671 | $190.29 | $181.28 | $3,873.53 | $-192.49 | -4.73% | 2 | $189.49 / $190.50 |
| GM | 70.7589 | $84.80 | $81.67 | $5,779.18 | $-221.17 | -3.69% | 1 | $84.80 / $84.80 |
| EQIX | 5.6994 | $1,052.75 | $1,020.06 | $5,813.71 | $-186.31 | -3.11% | 1 | $1,052.75 / $1,052.75 |
| SO | 63.0000 | $94.08 | $93.35 | $5,881.05 | $-45.99 | -0.78% | 1 | $94.08 / $94.08 |

⚠ = the broker's blended `avg_cost_basis` materially disagrees with the cost of the actual lots, so the two views of this position tell different stories:
- **GOOG**: `avg_cost_basis` $356.21 vs. lot-weighted $360.29 (price $272.97) — the blended average implies -23.37%, the lots imply -24.24%
- **TSLA**: `avg_cost_basis` $403.53 vs. lot-weighted $406.04 (price $376.24) — the blended average implies -6.76%, the lots imply -7.34%

## Deferred Wash-Sale Loss Tracking (v2.84.0, observational)
- none this cycle

## Orders Placed
```
```

# 2026-11-19 — Scheduled Rebalance Check — EXECUTED (0 sell(s), 0 buy(s))

**Status:** EXECUTED. 0 sell order(s), 0 buy order(s) sized this cycle.

## Account Snapshot
- `buying_power` (settled): **$55,177.44**
- `cash` (ledger): **$55,177.44**
- `current_cash` (post-cap): **$55,177.44**
- `account_balance`: **$127,900.90**

## Drawdown Audit
Emergency liquidations: none

## Excluded / Buy-Guarded Symbols (Step 2)
- **PLTR** (excluded): Profit-sell buy-guard: profit-sold 2026-10-20 @ 193.8 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.067%, need > -0.047% [asset-scaled, x0.93])
- **SOXL** (excluded): liquidated 2026-07-16 @ 147.6401 — recovery (5.0%) or cooldown (6d) not yet met
- **ARM** (excluded): Profit-sell buy-guard: profit-sold 2026-09-21 @ 302.14 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-4.434%, need > 0.356% [asset-scaled, x1.78])
- **SMCI** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 43.33 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.897%, need > -0.076% [asset-scaled, x1.53])
- **IONQ** (excluded): liquidated 2026-10-30 @ 29.02 — recovery (5.0%) or cooldown (6d) not yet met
- **SPCX** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 141.98 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-3.022%, need > 0.248% [asset-scaled, x1.24]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.253%, need > -0.062% [asset-scaled, x1.24]); upturn not confirmed (leg3 close_yesterday→today change=+0.087%, need > 0.099% [asset-scaled, x1.24])
- **AMZN** (excluded): Profit-sell buy-guard: profit-sold 2026-11-18 @ 262.07 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.051%, need > 0.150% [asset-scaled, x0.75]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.620%, need > -0.038% [asset-scaled, x0.75])
- **MSFT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-06 @ 532.34 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.392%, need > -0.033% [asset-scaled, x0.67])
- **HOOD** (excluded): liquidated 2026-11-16 @ 74.9 — recovery (5.0%) or cooldown (6d) not yet met
- **AAPL** (excluded): Profit-sell buy-guard: profit-sold 2026-09-11 @ 331.28 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.155%, need > -0.024% [asset-scaled, x0.49]); upturn not confirmed (leg3 close_yesterday→today change=-0.882%, need > 0.039% [asset-scaled, x0.49])
- **LLY** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 1415.74 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.282%, need > 0.054% [asset-scaled, x0.67])
- **JNJ** (excluded): Profit-sell buy-guard: profit-sold 2026-08-19 @ 275.33 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.160%, need > 0.039% [asset-scaled, x0.49])
- **BRK.B** (excluded): Profit-sell buy-guard: profit-sold 2026-10-20 @ 537.475 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.125%, need > 0.031% [asset-scaled, x0.39])
- **V** (excluded): Profit-sell buy-guard: profit-sold 2026-08-26 @ 383.44 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.214%, need > 0.039% [asset-scaled, x0.48])
- **HD** (excluded): Profit-sell buy-guard: profit-sold 2026-11-12 @ 353.53 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.208%, need > 0.056% [asset-scaled, x0.70])
- **CAT** (excluded): Profit-sell buy-guard: profit-sold 2026-10-02 @ 853.37 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.054%, need > 0.213% [asset-scaled, x1.07]); upturn not confirmed (leg3 close_yesterday→today change=+0.080%, need > 0.085% [asset-scaled, x1.07])
- **UNP** (excluded): Profit-sell buy-guard: profit-sold 2026-11-10 @ 300.32 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.318%, need > -0.025% [asset-scaled, x0.49]); upturn not confirmed (leg3 close_yesterday→today change=-2.445%, need > 0.040% [asset-scaled, x0.49])
- **WMT** (excluded): Profit-sell buy-guard: profit-sold 2026-11-16 @ 129.18 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-2.092%, need > 0.036% [asset-scaled, x0.46])
- **PG** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 164.365 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.909%, need > 0.041% [asset-scaled, x0.51])
- **COST** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 1012.9 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.862%, need > 0.033% [asset-scaled, x0.42])
- **XOM** (excluded): Profit-sell buy-guard: profit-sold 2026-09-09 @ 164.59 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.212%, need > 0.120% [asset-scaled, x0.60])
- **LIN** (excluded): Profit-sell buy-guard: profit-sold 2026-11-11 @ 526.11 (full exit) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.189%, need > 0.027% [asset-scaled, x0.34])
- **FCX** (excluded): Profit-sell buy-guard: profit-sold 2026-09-22 @ 73.75 (full exit) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.212%, need > 0.205% [asset-scaled, x1.03])
- **DUK** (excluded): Profit-sell buy-guard: profit-sold 2026-10-30 @ 127.175 (full exit) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.164%, need > -0.018% [asset-scaled, x0.37]); upturn not confirmed (leg3 close_yesterday→today change=-1.514%, need > 0.030% [asset-scaled, x0.37])
- **TQQQ** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-09 @ 81.355 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-1.135%, need > -0.093% [asset-scaled, x1.85])
- **TSLA** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-26 @ 394.795 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.095%, need > 0.206% [asset-scaled, x1.03]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.929%, need > -0.052% [asset-scaled, x1.03])
- **GOOG** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-13 @ 353.38 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.553%, need > -0.045% [asset-scaled, x0.90])
- **AMD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-08 @ 491.68 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=+0.158%, need > 0.433% [asset-scaled, x2.16]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-4.863%, need > -0.108% [asset-scaled, x2.16])
- **NEE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-04 @ 86.9098 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.429%, need > -0.025% [asset-scaled, x0.49]); upturn not confirmed (leg3 close_yesterday→today change=-1.115%, need > 0.039% [asset-scaled, x0.49])
- **VRT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-29 @ 253.0 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.854%, need > 0.410% [asset-scaled, x2.05]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-2.064%, need > -0.102% [asset-scaled, x2.05])
- **AVGO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 422.59 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-2.230%, need > 0.257% [asset-scaled, x1.29]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-3.386%, need > -0.064% [asset-scaled, x1.29])
- **GM** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-10 @ 89.23 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.460%, need > 0.160% [asset-scaled, x0.80])
- **NFLX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-09-02 @ 82.035 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.233%, need > -0.030% [asset-scaled, x0.59])
- **UNH** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-22 @ 425.58 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.709%, need > 0.064% [asset-scaled, x0.80])
- **GE** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-08-05 @ 382.1775 (partial, remainder still held) — blocked because: earlier dip not confirmed (leg1 close_2d_back→close_1d_back change=-0.373%, need > 0.150% [asset-scaled, x0.75]); dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.520%, need > -0.037% [asset-scaled, x0.75]); upturn not confirmed (leg3 close_yesterday→today change=-0.402%, need > 0.060% [asset-scaled, x0.75])
- **LTRN** (buy-guarded only): Buy-timing guard — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-1.105%, need > 0.195% [asset-scaled, x2.44])
- **SO** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-02 @ 94.67 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.871%, need > -0.018% [asset-scaled, x0.36]); upturn not confirmed (leg3 close_yesterday→today change=-1.483%, need > 0.029% [asset-scaled, x0.36])
- **PLD** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-11 @ 130.28 (partial, remainder still held) — blocked because: upturn not confirmed (leg3 close_yesterday→today change=-0.708%, need > 0.028% [asset-scaled, x0.35])
- **AMT** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-10-30 @ 188.19 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.896%, need > -0.027% [asset-scaled, x0.54]); upturn not confirmed (leg3 close_yesterday→today change=-1.014%, need > 0.043% [asset-scaled, x0.54])
- **EQIX** (buy-guarded only): Profit-sell buy-guard: profit-sold 2026-11-09 @ 1064.59 (partial, remainder still held) — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.160%, need > -0.036% [asset-scaled, x0.72])
- **SHW** (buy-guarded only): Buy-timing guard — blocked because: dip not confirmed (leg2 close_1d_back→close_yesterday change=-0.719%, need > -0.041% [asset-scaled, x0.82]); upturn not confirmed (leg3 close_yesterday→today change=-1.723%, need > 0.065% [asset-scaled, x0.82])

## Blocked Assets (`blocked` list)
- **LTRN**: blocked; forceSell trigger not yet met (needs price > $4.50, currently $0.33) — staying frozen this cycle

## Underweight Fill Ranking — Momentum_Score
| Symbol | RSI14 | EMA9_now | EMA9_prior | Price_vs_EMA% | EMA_Slope% | Score |
|---|---|---|---|---|---|---|
| AVGO | 55.61 | 340.10 | 325.25 | +8.12 | +4.57 | +18.30 |
| SO | 62.51 | 93.70 | 93.29 | -0.72 | +0.44 | +12.23 |
| NEE | 63.36 | 85.17 | 85.69 | -1.55 | -0.61 | +11.20 |
| AMD | 49.98 | 518.91 | 504.02 | +5.93 | +2.96 | +8.86 |
| EQIX | 55.49 | 1040.45 | 1032.34 | +0.46 | +0.79 | +6.73 |
| TSLA | 53.53 | 383.39 | 380.57 | +1.35 | +0.74 | +5.63 |
| GE | 54.17 | 327.47 | 326.29 | -0.21 | +0.36 | +4.32 |
| SHW | 53.47 | 348.56 | 350.02 | -2.25 | -0.42 | +0.81 |
| VRT | 47.47 | 197.81 | 202.76 | +0.66 | -2.44 | -4.31 |
| AMT | 48.72 | 187.93 | 189.42 | -2.64 | -0.79 | -4.70 |
| PLD | 47.69 | 127.49 | 129.15 | -2.47 | -1.28 | -6.07 |
| GM | 46.06 | 85.17 | 87.63 | -3.09 | -2.81 | -9.83 |
| JPM | 40.59 | 336.04 | 340.58 | -2.70 | -1.33 | -13.44 |
| ORCL | 40.44 | 119.96 | 122.95 | -1.97 | -2.43 | -13.96 |
| COP | 38.40 | 138.86 | 139.26 | -2.72 | -0.29 | -14.61 |
| MU | 37.61 | 747.91 | 780.41 | -0.03 | -4.17 | -16.59 |
| IBM | 39.91 | 240.40 | 248.18 | -3.90 | -3.14 | -17.13 |
| META | 33.80 | 625.74 | 630.09 | -0.31 | -0.69 | -17.20 |
| CVX | 34.40 | 214.84 | 216.82 | -3.66 | -0.91 | -20.18 |
| TQQQ | 34.98 | 55.77 | 59.18 | -0.46 | -5.76 | -21.24 |
| GOOG | 26.55 | 285.39 | 289.85 | +1.33 | -1.54 | -23.66 |
| F | 34.60 | 11.79 | 12.33 | -3.97 | -4.43 | -23.80 |
| NFLX | 29.73 | 61.83 | 64.21 | -2.76 | -3.70 | -26.74 |
| INTC | 27.53 | 58.76 | 63.40 | +0.33 | -7.32 | -29.46 |
| UNH | 27.18 | 392.08 | 403.12 | -12.25 | -2.74 | -37.82 |
| NVDA | 20.82 | 166.58 | 186.88 | -5.42 | -10.86 | -45.46 |
| COIN | 23.38 | 125.90 | 141.25 | -8.49 | -10.86 | -45.97 |
| MSTR | 26.57 | 109.86 | 129.30 | -14.80 | -15.03 | -53.26 |

## Tax Reserve
- `net_realized_gains_ytd_pretrade`: **$74,980.35**
- `net_realized_gains_ytd_effective` (post-sells): **$74,980.35**
- `total_paid_taxes` (all years, `tax/paid_taxes_by_year.json`): **$25,000.00**
- `tax_reserve` (final, after subtracting paid taxes): **$16,239.19**

## GET THE PROFITS Sells
- none fired this cycle

## Sell Cleanup Pass
- none fired this cycle

## Buys (Underweight fills, momentum-ranked top-down)
- none fired this cycle

## Position Cap Top-Up (leftover-cash pass toward `max_position_value`)
- none this cycle

## Total_High_Beta_Gains_Realized: **$0.00**
## Total_Cleanup_Gains_Realized: **$0.00**

## SKIPPED/PENDING
| Symbol | Reason | Would-be action |
|---|---|---|
| INTC | Momentum_Score (-29.46) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| MU | Momentum_Score (-16.59) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| MSTR | Momentum_Score (-53.26) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| COIN | Momentum_Score (-45.97) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| NVDA | Momentum_Score (-45.46) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| ORCL | Momentum_Score (-13.96) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| META | Momentum_Score (-17.20) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| JPM | Momentum_Score (-13.44) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| COP | Momentum_Score (-14.61) below min_momentum_score_to_fill_underweight (-5.00) | Underweight buy |
| INTC | Position Cap Top-Up: Momentum_Score (-29.46) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| MU | Position Cap Top-Up: Momentum_Score (-16.59) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| MSTR | Position Cap Top-Up: Momentum_Score (-53.26) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| COIN | Position Cap Top-Up: Momentum_Score (-45.97) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| NVDA | Position Cap Top-Up: Momentum_Score (-45.46) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| ORCL | Position Cap Top-Up: Momentum_Score (-13.96) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| META | Position Cap Top-Up: Momentum_Score (-17.20) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| F | Position Cap Top-Up: Momentum_Score (-23.80) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| IBM | Position Cap Top-Up: Momentum_Score (-17.13) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| JPM | Position Cap Top-Up: Momentum_Score (-13.44) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| CVX | Position Cap Top-Up: Momentum_Score (-20.18) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| COP | Position Cap Top-Up: Momentum_Score (-14.61) below min_momentum_score_to_fill_underweight (-5.00) | Position Cap Top-Up |
| TSLA | loss-lot sell guard: every sellable lot is at or above the current price ($388.57) — nothing can be sold at a gain | partial profit-take sale |
| GOOG | loss-lot sell guard: every sellable lot is at or above the current price ($289.18) — nothing can be sold at a gain | partial profit-take sale |
| TQQQ | loss-lot sell guard: every sellable lot is at or above the current price ($55.51) — nothing can be sold at a gain | partial profit-take sale |
| AMD | loss-lot sell guard: every sellable lot is at or above the current price ($549.69) — nothing can be sold at a gain | partial profit-take sale |
| NEE | loss-lot sell guard: every sellable lot is at or above the current price ($83.84) — nothing can be sold at a gain | partial profit-take sale |
| VRT | loss-lot sell guard: every sellable lot is at or above the current price ($199.11) — nothing can be sold at a gain | partial profit-take sale |
| AVGO | loss-lot sell guard: every sellable lot is at or above the current price ($367.73) — nothing can be sold at a gain | partial profit-take sale |
| F | loss-lot sell guard: every sellable lot is at or above the current price ($11.32) — nothing can be sold at a gain | partial profit-take sale |
| GM | loss-lot sell guard: every sellable lot is at or above the current price ($82.54) — nothing can be sold at a gain | partial profit-take sale |
| IBM | loss-lot sell guard: every sellable lot is at or above the current price ($231.03) — nothing can be sold at a gain | partial profit-take sale |
| NFLX | loss-lot sell guard: every sellable lot is at or above the current price ($60.12) — nothing can be sold at a gain | partial profit-take sale |
| UNH | loss-lot sell guard: every sellable lot is at or above the current price ($344.03) — nothing can be sold at a gain | partial profit-take sale |
| GE | loss-lot sell guard: every sellable lot is at or above the current price ($326.79) — nothing can be sold at a gain | partial profit-take sale |
| CVX | loss-lot sell guard: every sellable lot is at or above the current price ($206.97) — nothing can be sold at a gain | partial profit-take sale |
| SO | loss-lot sell guard: every sellable lot is at or above the current price ($93.03) — nothing can be sold at a gain | partial profit-take sale |
| PLD | loss-lot sell guard: every sellable lot is at or above the current price ($124.34) — nothing can be sold at a gain | partial profit-take sale |
| AMT | loss-lot sell guard: every sellable lot is at or above the current price ($182.97) — nothing can be sold at a gain | partial profit-take sale |
| EQIX | loss-lot sell guard: every sellable lot is at or above the current price ($1045.18) — nothing can be sold at a gain | partial profit-take sale |
| SHW | loss-lot sell guard: every sellable lot is at or above the current price ($340.73) — nothing can be sold at a gain | partial profit-take sale |

## Dormant Assets (no activity > 5d)
| Symbol | Days Dormant | Last Activity | Unrealized $ | Unrealized % |
|---|---|---|---|---|
| LTRN | never | n/a | $-2,002.29 | -95.35% |
| SHW | 105d | 2026-08-06 | $-120.74 | -6.03% |
| GE | 104d | 2026-08-07 | $-300.08 | -12.21% |
| AVGO | 99d | 2026-08-12 | $-541.58 | -12.65% |
| F | 97d | 2026-08-14 | $-518.26 | -23.15% |
| NFLX | 78d | 2026-09-02 | $-1.72 | -25.59% |
| TQQQ | 41d | 2026-10-09 | $-10.63 | -31.15% |
| GOOG | 37d | 2026-10-13 | $-1,033.00 | -18.82% |
| AMD | 37d | 2026-10-13 | $-493.92 | -8.23% |
| TSLA | 17d | 2026-11-02 | $-222.36 | -3.71% |
| VRT | 16d | 2026-11-03 | $-893.25 | -14.83% |
| UNH | 16d | 2026-11-03 | $-1,028.39 | -16.76% |
| IBM | 15d | 2026-11-04 | $-573.25 | -9.51% |
| CVX | 14d | 2026-11-05 | $-335.61 | -5.67% |
| SO | 14d | 2026-11-05 | $-66.15 | -1.12% |
| AMT | 10d | 2026-11-09 | $-156.51 | -3.85% |
| PLD | 8d | 2026-11-11 | $-11.91 | -8.32% |
| NEE | 7d | 2026-11-12 | $-217.07 | -4.72% |

## Loss-Only Lot Assets (every sellable lot underwater)
20 asset(s), $72,723.46 market value, $-8,830.69 total unrealized. GET THE PROFITS is structurally unable to fire on these (the loss-lot sell guard leaves no sellable lot), so they can only exit via an emergency stop or a manual action.

Unrealized figures are on the LOT basis (summed over the actual lots), not the broker's blended `avg_cost_basis` — so they can never contradict this list's own membership test.

| Symbol | Qty | Lot Cost | Price | Market Value | Unrealized $ | Unrealized % | Lots | Best/Worst Lot Cost |
|---|---|---|---|---|---|---|---|---|
| LTRN | 300.0000 | $7.00 | $0.33 | $97.71 | $-2,002.29 | -95.35% | 1 | $7.00 / $7.00 |
| TQQQ | 0.4232 | $80.62 | $55.51 | $23.49 | $-10.63 | -31.15% | 1 | $80.62 / $80.62 |
| NFLX | 0.0830 | $80.80 | $60.12 | $4.99 | $-1.72 | -25.59% | 1 | $80.80 / $80.80 |
| F | 151.9817 | $14.73 | $11.32 | $1,720.43 | $-517.74 | -23.13% | 4 | $14.30 / $14.85 |
| GOOG ⚠ | 15.4110 | $360.29 | $289.18 | $4,456.56 | $-1,095.89 | -19.74% | 8 | $344.59 / $377.51 |
| UNH | 14.8483 | $413.37 | $344.03 | $5,108.25 | $-1,029.60 | -16.77% | 2 | $403.15 / $413.61 |
| VRT | 25.7717 | $233.77 | $199.11 | $5,131.41 | $-893.34 | -14.83% | 2 | $233.24 / $233.79 |
| AVGO | 10.1667 | $421.00 | $367.73 | $3,738.58 | $-541.61 | -12.65% | 2 | $377.86 / $423.11 |
| GE | 6.6016 | $372.24 | $326.79 | $2,157.31 | $-300.10 | -12.21% | 2 | $356.04 / $373.67 |
| IBM | 23.6003 | $255.32 | $231.03 | $5,452.39 | $-573.14 | -9.51% | 2 | $254.37 / $255.34 |
| PLD | 1.0562 | $135.62 | $124.34 | $131.33 | $-11.92 | -8.32% | 2 | $129.03 / $139.86 |
| AMD | 10.0167 | $599.00 | $549.69 | $5,506.08 | $-493.92 | -8.23% | 1 | $599.00 / $599.00 |
| SHW | 5.5210 | $362.60 | $340.73 | $1,881.18 | $-120.74 | -6.03% | 1 | $362.60 / $362.60 |
| CVX | 27.0000 | $219.40 | $206.97 | $5,588.19 | $-335.61 | -5.67% | 1 | $219.40 / $219.40 |
| NEE | 52.2424 | $88.00 | $83.84 | $4,380.26 | $-216.99 | -4.72% | 8 | $83.94 / $90.00 |
| TSLA ⚠ | 14.8688 | $406.04 | $388.57 | $5,777.64 | $-259.68 | -4.30% | 1 | $406.04 / $406.04 |
| AMT | 21.3671 | $190.29 | $182.97 | $3,909.43 | $-156.59 | -3.85% | 2 | $189.49 / $190.50 |
| GM | 70.7589 | $84.80 | $82.54 | $5,840.44 | $-159.92 | -2.67% | 1 | $84.80 / $84.80 |
| SO | 63.0000 | $94.08 | $93.03 | $5,860.89 | $-66.15 | -1.12% | 1 | $94.08 / $94.08 |
| EQIX | 5.6994 | $1,052.75 | $1,045.18 | $5,956.90 | $-43.12 | -0.72% | 1 | $1,052.75 / $1,052.75 |

⚠ = the broker's blended `avg_cost_basis` materially disagrees with the cost of the actual lots, so the two views of this position tell different stories:
- **GOOG**: `avg_cost_basis` $356.21 vs. lot-weighted $360.29 (price $289.18) — the blended average implies -18.82%, the lots imply -19.74%
- **TSLA**: `avg_cost_basis` $403.53 vs. lot-weighted $406.04 (price $388.57) — the blended average implies -3.71%, the lots imply -4.30%

## Deferred Wash-Sale Loss Tracking (v2.84.0, observational)
- none this cycle

## Orders Placed
```
```
