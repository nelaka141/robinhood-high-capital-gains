# Trade Decision Logic (v2.74.0)

This document details every step of the bot's **sell decision** and **buy decision** as of
v2.74.0, when the Alpha Leader concept (the extra Alpha allocation, the re-investment
multiplier, the Alpha Leader Reserve, the Fresh Alpha Leader Stop) and the Momentum Reversal
Trim / Overweight High-Beta trim sell mechanisms were removed. The rules below are exactly what
`bot/steps.py` implements and what `CLAUDE.md`'s Business Rules Reference specifies — if the
three ever disagree, that is a bug to flag, not a choice to make silently.

**The strategy in one sentence:** the only routine sell is the **GET THE PROFITS**
profit-taking sale; the only buys are **Underweight fills, ranked by Momentum_Score and filled
top-down to each target's full drift gap (never pro-rated)**; every pre-existing guard on both
sides still applies.

---

## Inputs gathered before any decision (Step 1)

1. Positions, live quotes, buying power (`account_cash`), and the raw cash ledger from the
   Robinhood MCP snapshot.
2. `avg_cost_basis` per held asset, resolved by the waterfall: broker
   `average_buy_price` → tax-lot share-weighted average (only if lots cover the whole
   position) → `transferred_basis.json` blended override → **fail closed** (the asset's
   cost-basis-dependent sell gates are treated as NOT satisfied this cycle; drift math still
   applies).
3. `current_cash` = min(`account_cash`, `cap_on_total_cash_balance_to_use`);
   `account_balance` = market value of all target assets + `current_cash`.
4. Per-asset drift in weight units: `Drift = |weight − actual_weight|`, compared against the
   asset's own `drift` override or the global `global_drift_tolerance`.
5. State from `peak/prices.json`: `peakPrice/Date`, `liquidatedPrice/Date`,
   `profitSellPrice/Date`, `lastPurchaseDate`, `lastLossSalePrice/Date`.
   (The retired `lastAlphaLeaderBuyPrice/Date` fields are ignored on load and dropped on the
   next save.)
6. Pre-trade YTD realized P&L → provisional `tax_reserve` =
   (prior-years base from `tax/realized_gains_by_year.json` + max(0, YTD)) ×
   `keep_aside_profits_for_tax_percent` / 100.
7. **NO TRADES early exit:** if no asset breaches its drift tolerance, no Drawdown Audit
   fires, and no `blocked`+`forceSell`+held liquidation is pending, the cycle logs a status
   entry and terminates.

---

## SELL DECISION

Sells come from exactly three mechanisms, evaluated in this order. Nothing else ever sells.

### S1. Emergency liquidation — `blocked` + `forceSell` + held (Step 1)

* A symbol in the `blocked` list is normally frozen from ALL activity.
* Exception: if it is **also** in `forceSell` (with its optional `triggerPrice` cleared, i.e.
  `current_price > triggerPrice` when one is set) **and** currently held → liquidate 100% of
  the position. Unconditional: overrides `lock_in_period` and every routine gate.
* **Override that still applies:** `target_price_to_sell` — if a floor is configured and
  `current_price` is below it, the liquidation stays frozen this cycle (logged with both
  reasons).
* If the sale is a loss vs. `avg_cost_basis`, the symbol is recorded to
  `lastLossSalePrice/Date`, arming the wash-sale forward buy-guard.

### S2. Emergency liquidation — Drawdown Audit (Step 1)

* Fires only when **both** legs breach simultaneously:
  * price is ≥ `max_trailing_drawdown_percentage` below `peakPrice`, **and**
  * price is ≥ `max_trailing_drawdown_percentage` below `avg_cost_basis`.
* Liquidates 100%, overriding target weights and `lock_in_period`.
* Skipped entirely for `blocked` symbols (S1 is their only sell path) and for a symbol whose
  `target_price_to_sell` floor hasn't been crossed (logged SKIPPED/PENDING).
* Skipped (fail closed) when `avg_cost_basis` is unresolved.
* Always arms `lastLossSalePrice/Date` (the cost-basis leg guarantees a loss).
* Never blocked on wash-sale grounds — a wash sale only defers the loss; blocking a genuine
  stop-loss for a tax-timing benefit would be poor risk management.

### S3. GET THE PROFITS — the only routine sell (Step 4)

Evaluated for **every currently-held target asset** (not just Overweight ones), excluding
`blocked` symbols and assets with unresolved cost basis (fail closed). For each candidate, in
order:

1. **Size the sale:** target = `Quantity_Held × profit_sell_percentage / 100`.
   * Whole-share positions: round the target to the nearest whole share (a specified-lot
     order requires a whole-share top-level quantity); if it rounds to 0, skip (logged).
   * If the slice is worth less than `min_value_of_trade`: bump up — compute
     `min_value_of_trade / price`, round UP to the 3rd decimal, then whole-share-round —
     capped at everything held, even past `profit_sell_percentage`. If even selling every
     share held falls short of the floor, skip entirely (logged SKIPPED).
   * Sub-whole-share positions (< 1 share total): size in raw fractional shares and plan an
     **ordinary order** (no `tax_lots`) instead — the FIFO figure below becomes an estimate,
     noted in the journal.
2. **Profitability gates (OR, not AND — either alone is enough):**
   * percentage gate: `((price − avg_cost_basis) / avg_cost_basis) × 100 >
     materialize_profit_percentage`, or
   * dollar gate: FIFO lot-matched `Realized_Profit_Dollars > materialize_profit_in_dollars`.
   * The FIFO figure walks the tax lots **oldest-first** (never the API's default
     newest-first order), skipping unpriced/unselectable lots; if the priced+selectable lots
     can't cover the sale size, fail closed (skip).
3. **Mandatory positive-FIFO invariant:** regardless of which gate passed, require
   `fifo.fully_covered` and `Realized_Profit_Dollars > 0`. A blended-average "gain" whose
   actual FIFO-matched lots would realize a loss is refused (logged SKIPPED). This is what
   makes GET THE PROFITS structurally loss-proof — and why no backward wash-sale sell-guard
   is needed anywhere anymore.
4. **Same-day repeat guard:** skip if `profitSellDate` already equals today.
5. **Resell cooldown:** skip if `(current_date − profitSellDate) <
   profit_resell_cooldown_days` (strict `<`; a gap exactly equal to the window clears).
   First-ever profit-sell (no `profitSellDate` on record) is never blocked by this.
6. **`selling_price_change` guard:** require
   `(close_yesterday − price) × 100 / price < selling_price_change` — i.e. don't sell into a
   sharp same-day drop. Missing price history fails closed (skip).
7. **`target_price_to_sell` guard:** if a floor is configured and price hasn't crossed it,
   skip — this override outranks everything, including the emergency stops above.
8. If all of the above pass: plan the sale with the exact FIFO lot selection passed via
   `tax_lots` (so what's realized matches what was gated on). Overrides `lock_in_period`;
   fires whether the asset is Underweight, Overweight, or within tolerance.

### Sell-side finalization (Step 6a)

* Every planned sell (S1 + S2 + S3) below `sell_or_buy_value_limit` is dropped (logged
  SKIPPED); journal counts reflect only what was actually placed.
* **Per-trade approval halt:** if any single planned sell — or any single provisionally-sized
  buy — exceeds `seek_approval_value`, the whole cycle halts before ANY order is placed and
  waits for explicit user approval. (Buys that could never actually be placed — same-cycle
  sellers, `blocked` symbols — are excluded from this check.)
* Consequences recorded after fills: profit sales stamp `profitSellPrice/Date` (arming the
  buy-side repurchase guard); liquidations stamp `liquidatedPrice/Date`; loss sales stamp
  `lastLossSalePrice/Date`.

**Removed sell mechanisms (v2.74.0):** Momentum Reversal Trim, routine Overweight High-Beta
trims, harvest sizing (`harvest_needed_dollars`), the `minimum_alpha_leader_sell_profit`
floor, and the Fresh Alpha Leader Stop. Parameters that only served them
(`overweight_sell_minimum_profit_margin_percent/_dollars`, `sell_price_diff_limit`,
`lock_in_period`) are retained in `portfolio_targets.json` but are currently inert.

---

## BUY DECISION

Buys come from exactly one mechanism: momentum-ranked top-down Underweight fills.

### B1. Which symbols are even in play (Step 2)

A symbol is **excluded entirely** this cycle (no score, no ranking, no fill) if:
* it is in the `blocked` list; or
* it was previously liquidated, is currently unheld, and has not yet cleared BOTH the
  recovery gate (price ≥ `liquidatedPrice` × (1 + `min_recovery_price_percentage`/100)) and
  the cooldown (`current_date − liquidatedDate ≥ cool_down_period_after_lquidation`); or
* it was fully exited via a profit-sell (zero position + recorded `profitSellDate`) and the
  buy guards below haven't cleared yet.

### B2. Buy guards (Step 2 — ALL apply to EVERY buy; no exemptions)

A symbol that fails any of these is **buy-guarded**: it stays in play for drift monitoring and
future sells, but receives NO buy this cycle. Under the top-down fill, a guarded symbol is not
in the ranking at all — **its would-be allocation shifts down to the next-ranked qualifying
candidate; cash is never held back for it.**

1. **Three-leg buy-timing guard** (all three must clear; all measured as a % of the live
   price; missing history fails closed):
   * leg 1 — earlier dip: `(close_2day_back − close_1day_back) × 100 / price >
     1st_leg_price_change`
   * leg 2 — dip continued: `(close_1day_back − close_yesterday) × 100 / price >
     2nd_leg_price_change`
   * leg 3 — turn confirmed: `(price − close_yesterday) × 100 / price >
     3rd_leg_price_change`
2. **Profit-sell repurchase cooldown:** if the symbol has a recorded `profitSellDate`
   (partial or full), additionally require `(current_date − profitSellDate) ≥
   sold_asset_repurchase_days`.
3. **Wash-sale forward buy-guard:** if `(current_date − lastLossSaleDate) ≤
   wash_sale_lookback_days`, block all new buys (flat calendar check; stacks with the
   guards above).
4. **`target_price_to_buy` ceiling:** while `current_price` is above the configured ceiling,
   block all new buys of that symbol.

### B3. Momentum scoring (Step 3)

For every in-play symbol with enough history (~30 daily closes):

* `Momentum_Score = Price_vs_EMA_Pct + EMA_Slope_Pct + (RSI14 − 50)`, where
  `Price_vs_EMA_Pct = (price − EMA9_now)/EMA9_now × 100` and
  `EMA_Slope_Pct = (EMA9_now − EMA9_prior)/EMA9_prior × 100` (`EMA9_prior` is from
  `momentum_lookback_days` trading days earlier).

### B4. Qualifying Underweight candidates (Step 3)

A candidate qualifies only if ALL of:
* in play (B1), and not buy-guarded (B2);
* drift-breached (`Drift > asset_drift_tolerance`) **and** Underweight
  (`target_percentage > current_percentage`);
* `Momentum_Score ≥ min_momentum_score_to_fill_underweight`. A candidate below this floor —
  or with no computable score — **receives nothing, even if deployable cash is left over
  after every other candidate is filled** (logged SKIPPED).

### B5. Top-down full fills (Step 3) — NOT pro-rated

* `base_deployable_cash = max(0, current_cash − min_cash_absolute − tax_reserve)`. Buys are
  funded from this cash only — there is no harvesting/trimming of other positions to raise
  buy cash.
* Rank the qualifying candidates by `Momentum_Score` **descending** and walk the ranking from
  the top. Each candidate receives, in turn:
  `min( full drift gap, per-asset headroom, remaining cash )`, where
  * full drift gap = `target_percentage/100 × account_balance − market_value` (a full fill,
    never a pro-rata share);
  * per-asset headroom = (`max_allocation_percent` override, else global
    `max_portfolio_percentage`) % of `account_balance` − current market value;
  * remaining cash = what's left after every higher-ranked candidate was filled.
* A higher-ranked candidate is always fully funded before the next gets anything. When cash
  runs out, every remaining candidate is logged SKIPPED and waits for a future cycle.
* Leftover cash after all gaps are closed stays as cash — the fill never deploys past a
  candidate's own gap.

### B6. Sector concentration cap (Step 3, final pass)

* For each `sector_groups` group: if current group market value + planned group buys would
  exceed the group's cap (`maxPercentage` override, else global `max_sector_percentage`) as a
  percent of `account_balance`, scale every member's planned buy down proportionally to land
  exactly at the cap (floored at 0). Capped-away dollars are NOT redistributed.

### B7. Price-limit halts (Step 5 — per planned buy)

* **`buy_price_diff_limit`:** drop the buy if price is more than that % above the
  `no_of_days_for_price_compare`-day low (don't chase a pump).
* **`52_week_high_guard`:** drop the buy if `price / 52_week_high × 100 >` the guard (95).
  Missing 52-week-high data fails OPEN (buy allowed).

### B8. Buy-side finalization (Step 6b — after this cycle's sells are confirmed filled)

1. Re-fetch post-sell YTD realized P&L and fresh `buying_power`; finalize `tax_reserve` from
   the actual post-sell figure (never hand-reconstructed from estimates).
2. **Same-cycle buy/sell exclusivity:** drop any planned buy whose symbol sold this cycle
   (via any mechanism) or is `blocked`.
3. **Hard cap:** total buy spend ≤ `buying_power − min_cash_absolute − tax_reserve`; scale all
   buys down proportionally if needed.
4. **`min_value_of_trade` floor:** a buy under the floor is bumped up by draining
   lower-priority buys (priority = planned dollar amount descending), cascading; a buy that
   still can't reach the floor is dropped (logged SKIPPED), never placed under-sized.
5. **`sell_or_buy_value_limit`:** drop any surviving buy under this absolute floor.
6. Place the buys sequentially (429/502 → up to 3 retries, 1-minute wait). Fills stamp
   `lastPurchaseDate`; a repurchase after a full-exit profit-sell resets `peakPrice` to the
   purchase price; any stale `liquidatedPrice/Date` is cleared.

**Removed buy mechanisms (v2.74.0):** the Alpha Leader selection cascade, the raw Alpha
allocation (`alpha_cash_allocation_percentage`), the re-investment multiplier
(`reinvestment_multiplier_factor`), the rank haircut (`alpha_rank_reduction_percent`), the
Alpha Leader Reserve (`alpha_reserve.json` — file deleted), the momentum-weighted /
normalized-score pro-rata Underweight split (replaced by top-down full fills), the
"deploy every leftover dollar beyond the gaps" behavior, and the Alpha Leader's exemptions
from the buy-timing guard.

---

## Worked example

Deployable cash $10,000. Qualifying Underweight candidates after all guards, ranked by
Momentum_Score: `A (+40, gap $6,000)`, `B (+25, gap $7,000)`, `C (+10, gap $2,000)`,
`D (−15, gap $4,000, below the −12 floor)`. Suppose the top-scoring symbol overall, `T (+55,
gap $5,000)`, failed the buy-timing guard.

* `T` is buy-guarded → not in the ranking at all; its cash is NOT reserved.
* `A` is filled first: full $6,000 gap. Remaining cash $4,000.
* `B` is next: gap is $7,000 but only $4,000 remains → `B` gets $4,000. Remaining $0.
* `C` gets nothing (cash exhausted — logged SKIPPED).
* `D` gets nothing regardless of cash (below `min_momentum_score_to_fill_underweight` —
  logged SKIPPED). Even if $9,000 had been left over, `D` would still get nothing.

Nothing is pro-rated; nothing is harvested from Overweight positions to cover `B`'s or `C`'s
shortfall; the sector-cap pass then runs over the `A`/`B` allocations, and Step 5/6's price
limits, exclusivity, hard cap, and dollar floors apply before any order is placed.
