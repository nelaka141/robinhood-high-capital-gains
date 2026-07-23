
 # 2026-07-20 03:22 PM EDT — Scheduled Rebalance Check — EXECUTED (Alpha Leader Rotates to AAPL as Profit-Sell Repurchase Lock Finally Clears — $16.47 Alpha Buy Filled; Runners-Up MSTR/PLTR Blocked by Pump-Limit Guard; Zero Legal Overweight Sell Source Persists; 6 First-Time-Trade Underweight Buys Pro-Rata Split Below $10 Floor)

**Status:** EXECUTED. **1 of 1 intended order filled** — fresh, stateless
run for the 3:15 PM ET scheduled tick. `CLAUDE.md` re-pulled fresh from
`main` (SHA `70f9b43`, text version header "Volume 2.28.0", unchanged
since this morning's 9:47 AM cycle). `portfolio_targets.json` (v2.17.0),
`peak/prices.json`, and `settlement/reserve.json` all re-pulled fresh
from `main` for this run.

## Pre-check state (~3:16 PM ET, regular hours)
* Account `795732718` ("Agentic", cash-type). `buying_power` =
  **$9,297.05**, `cash` (ledger) = **$9,297.05** — no gap, identical to
  this morning's 9:47 AM reading; `get_equity_orders` confirms zero
  orders placed on this account since midnight ET prior to this cycle.
* `current_cash` = Math.min($9,297.05, `cap_on_total_cash_balance_to_use`
  $10,000) = **$9,297.05**.
* Equity value (live quotes, 21 held target symbols; MU, SOXL, IONQ at
  zero shares under liquidation cooldown; F/GM/IBM/NFLX/UNH/GE still
  unpurchased first-time-trade targets): broker `get_portfolio` snapshot
  **$36,652.69**. `account_balance` ≈ **$45,949.74**.
* `settlement/reserve.json`: `pending_draws` = `[]` — nothing to
  reconcile. `reserve_available_to_draw` = `settlement_reserve_target`
  ($9,000) − $0 drawn = **$9,000** (unused, no draws needed this cycle).

## Drawdown audit (Step 1)
Checked every held asset against `max_trailing_drawdown_percentage`
(25%) vs both `peakPrice` and `avg_cost_basis`. Broad down day
continuing from this morning across the target list, but **no asset
breached 25% on either leg** — closest were SPCX (20.8% off peak / 20.0%
off cost basis) and INTC (16.1% off peak / 22.8% off cost basis).
**Zero emergency liquidations triggered.**

## Drift assessment (Step 1–2)
Drift breaches (> `drift_tolerance_percentage` 2.0% for established
holdings, > `drift_tolerance_percentage_for_first_time_trades` 0.1% for
never-purchased targets — F/GM/IBM/NFLX/UNH/GE all show
`lastPurchaseDate: null`):
* **Overweight, breaching:** TQQQ (current 5.47% vs. target 2.87%, drift
  +2.61pp), PLTR (current 7.62% vs. target 4.78%, drift +2.84pp),
  **META (current 15.72% vs. target 1.91%, drift +13.81pp — persistent
  large overweight)**.
* **Underweight, breaching (first-time-trade tolerance):** F, GM, IBM,
  NFLX, UNH, GE — each 0% held vs. ~1.91% target, 1.91pp drift.
* MU, SOXL, IONQ remain **excluded from drift calc** — liquidation
  cooldown (8 days) not yet cleared: MU/SOXL liquidated 2026-07-16 (4 of
  8 days elapsed), IONQ liquidated 2026-07-13 (7 of 8 days elapsed, 1
  day short).

Since breaches exist, the cycle proceeds past the "no trades needed"
early-exit check.

## Overweight sell-source screen (Step 2/4)
All three actionable Overweight assets screened against
`overweight_sell_minimum_profit_margin_percent` (1.0%) — `forceSell` is
empty, no override available. Lock-in check (`lock_in_period` 2 days)
also run: TQQQ (`lastPurchaseDate` 2026-07-16, 4 days — clear) and META
(`lastPurchaseDate` 2026-07-16, 4 days — clear) are both past lock-in,
but neither clears the profit-margin gate anyway:
* TQQQ: avg cost $73.92 vs. current $67.87 → **−8.18%** (loss) — not
  sellable.
* PLTR: avg cost $134.51 vs. current $135.61 → **+0.82%** — below the
  1.0% floor, not sellable.
* META: avg cost $664.01 vs. current $648.77 → **−2.30%** (loss) — not
  sellable.

**Zero legal overweight trim source this cycle** — unchanged from this
morning. No High-Beta Gain Score ranking was computable (no candidate
cleared the profit-margin gate to be trim-eligible).

## Alpha Leader identification & multiplier (Step 3)
7-day price gain computed for all 30 target-list symbols (2026-07-13
official close → live 2026-07-20 ~3:16 PM ET quote):
1. **MSTR +5.82%** — highest 7-day gain, but current price ($97.46) sits
   **+8.22%** above its trailing 3-day low ($90.06, set 2026-07-17),
   over the 5% `buy_price_diff_limit` — **exempt from buying today**
   (parabolic-rally guard; worse than this morning's 6.16% reading as
   the rally extended into the afternoon).
2. **PLTR +4.28%** — runner-up, current price ($135.61) sits **+5.39%**
   above its trailing 3-day low ($128.68, set 2026-07-16), also over the
   5% limit — **exempt from buying today** (also already an Overweight
   position, drift +2.84pp).
3. **AAPL +3.38%** — third-highest and the first candidate clear of
   every guard:
   - **Repurchase lock check:** `profitSellDate` 2026-07-17 (3 days ago,
     clears the 2-day `sold_asset_repurchase_days` gate). Price has now
     dropped **1.63%** from `profitSellPrice` ($333.4801 → live
     $328.15), clearing the 1.5% `sold_asset_price_change_percentage`
     bar for the first time since the profit-sell (this morning's
     reading was only −0.88%, short of the bar). **Repurchase guard
     satisfied — AAPL is back in play.**
   - **Pump guard:** 3-day low $317.32 (2026-07-09... 2026-07-15 window
     used the 07-15/16/17 lows); current $328.15 is **+3.38%** above it,
     clear of the 5% limit.
   - **GET-THE-PROFITS check** (sell-side, run regardless of buy
     eligibility): raw gain vs. `avg_cost_basis` = +2.57% ($319.83 →
     $328.04 pre-trade), below the 4.0% `materialize_profit_percentage`
     bar — **not triggered**. Proceeds to BUY path.

`base_deployable_cash` = max(0, $9,297.05 − `min_cash_absolute` $250 −
`settlement_reserve_target` $9,000) = **$47.05**. No overweight trim
source exists to harvest `multiplier_cash` (would have been
$47.05 × 0.25 = $11.76), so the reinvestment multiplier (1.25×)
generated **$0** in practice this cycle — only the organic $47.05 base
is real.

**Alpha allocation:** `alpha_cash_allocation_percentage` (35%) of the
$47.05 base = **$16.4675 → $16.47**, routed to AAPL (Alpha Leader).
Resulting AAPL concentration post-trade is still a small fraction of
`max_portfolio_percentage` (35% cap) — no cap constraint bound.

## Underweight pro-rata coverage (Step 3, remainder)
Remaining base pool after the Alpha allocation = $47.05 − $16.47 =
**$30.58**. The only actionable Underweight assets are the six
first-time-trade targets (F, GM, IBM, NFLX, UNH, GE), all equal-weighted
(1.0 each) and all clear of the `buy_price_diff_limit` pump guard
(largest: IBM at +4.42% off its 3-day low, still under the 5% cap).
Pro-rata split of $30.58 across 6 equal-weight targets = **$5.10
each** — below the `sell_or_buy_value_limit` ($10) per-trade floor.
**All six buys evaluated and SKIPPED.**

## Execution (Step 6)
* **AAPL — BUY, market order, regular hours, $16.47 notional.**
  Reviewed via `review_equity_order` (zero broker alerts; quote at
  review: bid $328.12 / ask $328.14 / last $328.125, 3:21 PM ET).
  Placed via `place_equity_order` (ref_id
  `147c46b9-847d-4ad3-8f05-0eb839445b03`, order id
  `6a5e752d-faeb-4837-8972-a3fdd118ffb9`). **Filled** 2026-07-20
  19:21:17 UTC (3:21:17 PM ET) — 0.050190 shares @ avg price
  $328.1499, $16.47 total, $0.00 fees.
* No sells executed (zero legal overweight trim source; GET-THE-PROFITS
  not triggered). Per the same-cycle buy/sell exclusivity rule, this was
  moot — no conflicting sell was ever in play for AAPL.
* No `seek_approval_value` ($10,000) halt triggered — trade size $16.47
  is far below the threshold.
* No settlement-reserve draws created or reconciled this cycle — the buy
  was funded entirely from organic `buying_power`, no bridging
  required. `pending_draws` stayed empty throughout.

## Peak-price ledger (`peak/prices.json`)
* **AAPL**: repurchased after a prior profit-sell → `peakPrice` **reset**
  to the purchase fill price **$328.1499**, `peakDate` and
  `lastPurchaseDate` set to **2026-07-20**, per the repo rule to reset
  peak tracking on post-profit-sell repurchase. `profitSellPrice`
  ($333.4801) / `profitSellDate` (2026-07-17) preserved as historical
  record.
* All other 29 symbols: broad down day continuing — every held/tracked
  symbol's live price came in below its stored `peakPrice`, so no other
  peak values required updating.

## Final balances
* Cash (`buying_power`): **$9,280.58** post-trade (well above
  `min_cash_target` $500 lean-buffer goal, but still immobilized behind
  the $9,000 `settlement_reserve_target` wall and a now-exhausted $30.58
  residual — cannot be worked down further this cycle without a legal
  sell source).
* Equity value: **≈$36,653.74** (broker snapshot, post-trade).
* Account value: **≈$45,934.32** (broker snapshot, post-trade).
* Execution window: 2026-07-20 19:21:11–19:22:27 UTC (3:21:11–3:22:27 PM
  EDT), regular market hours.

## SKIPPED/PENDING trade matrix
| Symbol | Intent | Amount | Reason |
|---|---|---|---|
| MSTR | Buy (Alpha Leader, rank 1) | n/a | 3-day-low rally +8.22% exceeds 5% `buy_price_diff_limit` |
| PLTR | Buy (Alpha Leader, rank 2) | n/a | 3-day-low rally +5.39% exceeds 5% `buy_price_diff_limit` |
| F | Buy (pro-rata underweight) | $5.10 | Below $10 `sell_or_buy_value_limit` |
| GM | Buy (pro-rata underweight) | $5.10 | Below $10 `sell_or_buy_value_limit` |
| IBM | Buy (pro-rata underweight) | $5.10 | Below $10 `sell_or_buy_value_limit` |
| NFLX | Buy (pro-rata underweight) | $5.10 | Below $10 `sell_or_buy_value_limit` |
| UNH | Buy (pro-rata underweight) | $5.10 | Below $10 `sell_or_buy_value_limit` |
| GE | Buy (pro-rata underweight) | $5.10 | Below $10 `sell_or_buy_value_limit` |
| TQQQ | Sell (overweight trim) | n/a | −8.18% raw gain, below 1.0% profit-margin floor, not in `forceSell` |
| PLTR | Sell (overweight trim) | n/a | +0.82% raw gain, below 1.0% profit-margin floor, not in `forceSell` |
| META | Sell (overweight trim) | n/a | −2.30% raw gain, below 1.0% profit-margin floor, not in `forceSell` |
| MU | Buy (repurchase) | n/a | Liquidation cooldown: 4 of 8 days elapsed |
| SOXL | Buy (repurchase) | n/a | Liquidation cooldown: 4 of 8 days elapsed |
| IONQ | Buy (repurchase) | n/a | Liquidation cooldown: 7 of 8 days elapsed |

`Total_High_Beta_Gains_Realized` this cycle: **$0.00** (no trim-eligible
candidates cleared the profit-margin gate; the only execution this cycle
was the AAPL Alpha Leader buy).

Per repo convention, this entry is committed to a fresh feature branch
and merged directly into `main` to preserve the unalterable paper
trail.



---

 # 2026-07-21 09:50 AM EDT — Scheduled Rebalance Check — EXECUTED (Alpha Leader COIN Triggers GET THE PROFITS Sale at +4.30% Gain — $210.87 Realized, No Alpha Buy This Cycle; PLTR/TQQQ/META All Overweight but Negative-Margin-Blocked; 6 First-Time-Trade Underweight Buys Pro-Rata Funded via Reserve Bridge)

**Status:** EXECUTED. **7 of 7 intended orders filled** (1 sell, 6 buys) —
fresh, stateless run for the 9:45 AM ET scheduled tick. `CLAUDE.md`
re-pulled fresh from `main` (SHA `56bdab8`, text version header "Volume
2.28.0"). `portfolio_targets.json` (v2.17.0), `peak/prices.json`, and
`settlement/reserve.json` all re-pulled fresh from `main` for this run.

## Pre-check state (~9:46 AM ET, regular hours)
* Account `795732718` ("Agentic", cash-type). `buying_power` =
  **$9,280.58**, `cash` (ledger) = **$9,280.58** — no gap, confirms no
  unsettled proceeds carried in from a prior cycle.
* `current_cash` = Math.min($9,280.58, `cap_on_total_cash_balance_to_use`
  $10,000) = **$9,280.58**.
* Equity value (live quotes, 21 held target symbols; MU, SOXL, IONQ at
  zero shares under liquidation cooldown/recovery-fail; F/GM/IBM/NFLX/UNH/GE
  still unpurchased first-time-trade targets): broker `get_portfolio`
  snapshot **$37,033.75**. `account_balance` ≈ **$46,314.33**.
* `settlement/reserve.json`: `pending_draws` = `[]` — nothing to
  reconcile. `reserve_available_to_draw` = `settlement_reserve_target`
  ($9,000) − $0 drawn = **$9,000** (fully available at cycle start).

## Drawdown audit (Step 1)
Checked every held asset against `max_trailing_drawdown_percentage`
(25%) vs both `peakPrice` and `avg_cost_basis`. **No asset breached 25%
on either leg** this cycle — closest was SPCX (19.6% off its $152.9988
peak). No emergency liquidations triggered.

## Liquidation recovery / cooldown check (Step 2)
* **MU**: liquidated 2026-07-16 @ $862.81. Only 5 days elapsed vs
  `cool_down_period_after_lquidation` (8 days) — still locked out
  regardless of price. Stays out of drift calc.
* **SOXL**: liquidated 2026-07-16 @ $147.6401. Same 5-day cooldown gate —
  still locked out. Stays out of drift calc.
* **IONQ**: liquidated 2026-07-13 @ $38.8001. Cooldown cleared (8 days
  elapsed), but current price $34.88 is **10.1% below** the liquidated
  price (a further decline, not a ≥7% recovery) — recovery condition
  fails. Stays out of drift calc.

## Drift & Alpha Leader (Step 3)
Target weights sum to 52.3 across 30 symbols. Drift computed against
`account_balance` ≈ $46,314.33 (`drift_tolerance_percentage` 2.0% /
0.1% for never-purchased first-time assets).

**Overweight (>2.0% drift):**
| Symbol | Current % | Target % | Drift |
|---|---|---|---|
| META | 15.61% | 1.91% | +13.69% |
| TQQQ | 5.61% | 2.87% | +2.74% |
| PLTR | 7.48% | 4.78% | +2.70% |

**Underweight first-time-trade (0% held, 0.1% tolerance):** F, GM, IBM,
NFLX, UNH, GE — all ~1.91% target drift, all first purchases this cycle.

All other held positions (INTC, AMZN, TSLA, NVDA, ORCL, GOOG, MSFT,
MSTR, ARM, SMCI, HOOD, AAPL, AMD, NEE, VRT, AVGO, SPCX) sat inside the
2.0% band — no action.

**Alpha Leader — COIN (+7.62% over 7 days)**, computed from 07-14 close
$161.50 → live $173.80 at scan time. Runner-up was MSFT (+3.87%);
TQQQ/HOOD/NFLX all posted double-digit *negative* 7-day moves and were
excluded from leadership contention.

**GET THE PROFITS check on COIN:** avg cost basis $166.64, current price
$173.80 at scan time → unrealized gain **+4.30%**, exceeding
`materialize_profit_percentage` (4.0%). `peak/prices.json` shows no
prior `profitSellDate` for COIN (null) — rule **triggers**. Per
CLAUDE.md: sell `profit_sell_percentage` (40%) of COIN and **do not buy
any new Alpha Leader shares this cycle**, even though COIN's own
drift (target 1.91% vs. held 1.13%, i.e. technically underweight) would
otherwise argue for a buy.

`base_deployable_cash` = Math.max(0, $9,280.58 − $250 `min_cash_absolute`
− $9,000 `settlement_reserve_target`) = **$30.58** — the alpha
multiplier math was moot since no Alpha Leader buy occurs this cycle.

## Profit-taking & overweight evaluation (Step 4)
Guard check `overweight_sell_minimum_profit_margin_percent` (1.0%) on
all three overweight candidates — **none qualify, none are in
`forceSell`**:
| Symbol | Avg Cost | Current | Margin | Verdict |
|---|---|---|---|---|
| PLTR | $134.51 | $134.05 | −0.34% | BLOCKED |
| TQQQ | $73.92 | $70.0307 | −5.26% | BLOCKED |
| META | $664.01 | $648.905 | −2.28% | BLOCKED |

High-Beta Gain scoring computed for the record (30-day daily-return
regression vs. SPY) even though no trim executes:
| Symbol | Beta (30d) | Raw Gain % | High-Beta Gain Score |
|---|---|---|---|
| TQQQ | 5.53 | −5.26% | −29.10 |
| META | 1.71 | −2.28% | −3.87 |
| PLTR | 0.75 | −0.34% | −0.26 |

All three would have ranked TQQQ first for trimming had any cleared the
profit-margin floor — none did. **Zero overweight sell proceeds
generated this cycle**; the only sell executed is the COIN profit-take
below.

## Price-limit / volatility halts (Step 5)
3-day (`no_of_days_for_price_compare`) min/max window checked for all
buy/sell candidates:
* COIN sale: current $175.70–176.37 sits *above* the 3-day max ($166.57)
  — a rally, not a crash, so `sell_price_diff_limit` is not a factor
  (that guard only exempts drops, not new highs).
* F/GM/IBM/NFLX/UNH/GE buys: all comfortably inside
  `buy_price_diff_limit` (5%) off their 3-day lows — largest was IBM at
  +4.05%, closest to the cap but still compliant.

## Execution (Step 6) — sequential, regular market hours
1. **SELL COIN** 1.200189 sh (40% of the 3.000472-share position) @
   avg **$175.7001** market → **$210.87** proceeds. Realized gain =
   ($175.7001 − $166.64) × 1.200189 = **+$10.87**. Order
   `6a5f78fc…f185`, filled 09:49:48 AM ET.
2. **BUY F** $40.24 → 2.837799 sh @ avg $14.1800. Order `6a5f7921…6297`,
   filled 09:50:25 AM ET.
3. **BUY GM** $40.24 → 0.512931 sh @ avg $78.4510. Order `6a5f7926…f3e`,
   filled 09:50:30 AM ET.
4. **BUY IBM** $40.24 → 0.190050 sh @ avg $211.7332. Order
   `6a5f792b…89a`, filled 09:50:35 AM ET.
5. **BUY NFLX** $40.24 → 0.595310 sh @ avg $67.5950. Order
   `6a5f792f…eb4`, filled 09:50:39 AM ET.
6. **BUY UNH** $40.24 → 0.093548 sh @ avg $430.1500. Order
   `6a5f7933…7d`, filled 09:50:43 AM ET.
7. **BUY GE** $40.24 → 0.117441 sh @ avg $342.6400. Order
   `6a5f7937…6bc`, filled 09:50:48 AM ET.

No order size fell below `sell_or_buy_value_limit` ($10). Gross nominal
value sold ($210.87) was far under `seek_approval_value` ($10,000) — no
user-approval halt required. No buy/sell conflict on the same symbol
this cycle.

### Settlement reserve bridge
COIN's $210.87 sale proceeds had not yet posted to `buying_power`
(confirmed empirically: post-sale `cash` $9,491.45 vs. `buying_power`
still $9,280.58, a $210.87 gap). Total buy spend this cycle was $241.44
($40.24 × 6), exceeding the $30.58 `base_deployable_cash` floor by
$210.86 — bridged in full from the reserve against the fresh COIN sale:
* New `pending_draws` entry: symbol `COIN`, `saleProceeds` $210.87,
  `reserveDrawn` $210.87 (full bridgeable capacity, well under the
  $9,000 `reserve_available_to_draw`), `saleDate` 2026-07-21,
  `expectedSettleDate` 2026-07-22 (`settlement_lag_days` = 1),
  `settled: false`.
* `reserve_available_to_draw` after this draw = $9,000 − $210.87 =
  **$8,789.13**.

## Post-trade balances
* `cash` **$9,250.01**, `buying_power` **$9,039.14** (gap = $210.87,
  matches the pending COIN draw exactly).
* `equity_value` **$37,119.31**, `total_value` (account_balance)
  **$46,369.32**.
* Cash sits well above `min_cash_target` ($500) and `min_cash_absolute`
  ($250); the reserve wall-off ($9,000) plus min-cash floor account for
  the rest — consistent with "keep cash lean but never below floor."

## peak/prices.json updates
* **COIN**: `peakPrice` 167.12 → **176.195** (new high, `peakDate`
  2026-07-21); `profitSellPrice` → **175.7001**, `profitSellDate` →
  **2026-07-21** (first-ever profit-sell recorded for this asset);
  `lastPurchaseDate` unchanged (no buy this cycle).
* **GM**: `peakPrice` 77.42 → **77.74** (new high, `peakDate`
  2026-07-21); `lastPurchaseDate` → **2026-07-21** (first purchase).
* **F, IBM, NFLX, UNH, GE**: `lastPurchaseDate` → **2026-07-21** (first
  purchase); `peakPrice`/`peakDate` unchanged — current prices did not
  exceed stored peaks.
* All other symbols: peaks unchanged (no new highs this cycle).

## Total_High_Beta_Gains_Realized
$0.00 from overweight trims (all blocked by profit-margin guard).
COIN's profit-take realized **+$10.87** separately under the GET THE
PROFITS rule (not an overweight trim, so excluded from the High-Beta
Gains tally by definition, logged here for completeness).

## Reconciliation
`settlement/reserve.json` had zero pending entries at cycle start — no
prior-cycle settlements to reconcile. One new pending draw recorded
this cycle (COIN, see above).



---
