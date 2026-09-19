# Trade Decision Logic (v2.88.0)

This document details every step of the bot's **sell decision** and **buy decision** as of
v2.88.0. The rules below are exactly what `bot/steps.py` implements and what `CLAUDE.md`'s
Business Rules Reference specifies — if the three ever disagree, that is a bug to flag, not a
choice to make silently.

**The strategy in one sentence:** the only routine sells are the **GET THE PROFITS**
profit-taking sale and the **Sell Cleanup Pass** remainder sweep; the only buys are
**Underweight fills, ranked by Momentum_Score and filled top-down to each target's full drift
gap (never pro-rated)**, followed by a **Position Cap Top-Up** that spends whatever cash that
fill left over; every pre-existing guard on both sides still applies.

---

## Before any decision: the cycle can stop before it starts

1. **Drive state sync (v2.86.0).** `peak/prices.json`, `tax/realized_gains_by_year.json`,
   `price_history/daily_bars.json` and the rotated `logs/history_trade_journal-*.md` files live
   on Google Drive, not git — the container running a cycle is ephemeral. `drive-pull` runs
   first; without it every decision below would read a fresh checkout's empty/stale state.
   `logs/trade_journal.md` is the one state file still git-tracked.
2. **Market-hours gate (v2.88.0).** `market-check` then decides, with no network dependency,
   whether it is a weekend, an NYSE holiday, or outside the 7:00 AM–8:00 PM ET extended-trading
   window. If closed, a "MARKET CLOSED" journal entry is written and **the cycle aborts before
   any Robinhood call** — no snapshot, no `plan`, no `finalize`, no decision at all.

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
   `profitSellPrice/Date`, `lastPurchaseDate`, `lastLossSalePrice/Date`, and (v2.84.0,
   observational only) `lastNettedLossDollars/Shares/Date` + `washVerifyPending`.
   (The retired `lastAlphaLeaderBuyPrice/Date` fields are ignored on load and dropped on the
   next save.)
6. Daily closes and lows/highs come from the rolling ~90-day cache in
   `price_history/daily_bars.json`, not a fresh full re-fetch each cycle — a normal day-over-day
   cycle only needs a 1-day incremental fetch per symbol.
7. Pre-trade YTD realized P&L → provisional `tax_reserve` =
   max(0, (prior-years base from `tax/realized_gains_by_year.json` + max(0, YTD)) ×
   `keep_aside_profits_for_tax_percent` / 100 **− the summed entries of
   `tax/paid_taxes_by_year.json`**). That last term (v2.80.0) comes off the percentage-based
   figure dollar-for-dollar, floored at 0; the file is purely user-maintained — the bot only
   ever reads it.
8. **NO TRADES early exit:** if no asset breaches its drift tolerance, no Drawdown Audit
   fires, and no `blocked`+`forceSell`+held liquidation is pending, the cycle logs a status
   entry and terminates.

---

## SELL DECISION

Sells come from exactly four mechanisms, evaluated in this order. Nothing else ever sells.

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

### S3. GET THE PROFITS — the only routine profit-taking sell (Step 4)

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
2. **Zero-available-lots fallback (v2.79.0):** if **literally zero** of the symbol's lots are
   priced+selectable **and every one of them is dated today** — i.e. the whole position is
   today's buy(s), not yet synced broker-side — place an **ordinary order** and gate the dollar
   leg off `(price − avg_cost_basis) × Quantity_Sold` instead of a FIFO walk; `days_held` is
   treated as 0. Both conditions are required: a lot dated before today is a stale-data problem,
   not sync latency, so it stays fail-closed. A same-day round-trip is intentionally allowed —
   nothing gates GET THE PROFITS on holding period.
3. **Net-profit full exit (v2.83.0) — evaluated FIRST, ahead of the loss-lot guard below.** For
   a **mixed** position (at least one priced lot underwater AND at least one in profit), walk
   **every** lot for the **entire** position — no loss-lot exclusion — and if the NET FIFO figure
   is `> 0`, clears the OR-gate at step 5's dynamic thresholds, clears
   `min_raw_gain_percent_to_sell`, and the whole position's market value clears
   `min_value_of_trade`, then sell **100% of the position** (`profit_sell_percentage` ignored,
   fractional remainder included) as an **ordinary order**. The underwater lot's loss is netted
   against the winners' gain inside the same transaction, which is how the IRS computes that sale
   anyway. Fails closed on lot data: every lot must be priced+selectable. If this path declines,
   the journal records *why*, and the loss-lot guard below governs unchanged.
   * **Wash-sale bookkeeping:** this is a net-gain sale, so it does **not** arm
     `lastLossSalePrice/Date` — the symbol is not blocked from repurchase on the strength of a
     lot loss that was netted out (operator decision, 2026-09-04). The netted loss is instead
     recorded observationally (v2.84.0) so Step 7 can journal and later verify the deferral.
4. **Loss-lot sell guard (v2.75.0):** exclude every lot that would not realize a strict gain at
   the current price (`cost_per_share >= price` — loss lots plus exact-breakeven lots), cap the
   sale quantity at the profitable lots' total, and re-floor to a whole share (floor, never round
   up — rounding up could re-admit an excluded lot). Ordering is load-bearing:
   * the **pending-basis fail-closed check comes first and is untouched** — if the sale target
     exceeds the priced+selectable quantity, some basis is still syncing and the sale is skipped
     outright, never silently downsized to "whatever happens to be priced" (the one exception is
     step 2's zero-lots case);
   * the **`min_value_of_trade` floor is re-checked after the cap** — the cap can only shrink a
     sale, so one that cleared the floor beforehand may fall under it afterwards, and is then
     skipped (logged, naming how much was held back) rather than placed under-sized;
   * if *every* sellable lot is at or above the current price, skip entirely.
5. **Profitability gates (OR, not AND — either alone is enough), against DYNAMIC thresholds
   (v2.78.0):** neither leg is a flat bar. Each ramps *parabolically* and independently from its
   own day-0 floor to its own cap —
   `threshold(days_held) = base + (max − base) × min(1, days_held / profit_threshold_ramp_days)²`
   — where `days_held` is the **quantity-weighted average age of the specific profitable lots
   this sale would actually consume** (post loss-lot exclusion), not the position's full lot
   history:
   * percentage leg: `((price − avg_cost_basis) / avg_cost_basis) × 100 >` the ramped
     `materialize_profit_percentage` → `materialize_profit_percentage_max`;
   * dollar leg: FIFO lot-matched `Realized_Profit_Dollars >` the ramped
     `materialize_profit_in_dollars` → `materialize_profit_in_dollars_max`.
   * The FIFO figure walks the tax lots **oldest-first** (never the API's default
     newest-first order), skipping unpriced/unselectable lots.
   * The intent: a position that just crossed into profit shouldn't be harvested on a razor-thin
     move, but one that's been sitting on a gain for a while can be harvested on a smaller move
     before it slips back.
6. **Mandatory positive-FIFO invariant (v2.66.0):** regardless of which gate passed, require
   `fifo.fully_covered` and `Realized_Profit_Dollars > 0`. A blended-average "gain" whose
   actual FIFO-matched lots would realize a loss is refused (logged SKIPPED). The loss-lot guard
   at step 4 makes this structurally redundant — every consumed lot is now individually
   profitable — and it is deliberately retained as a backstop.
7. **`min_raw_gain_percent_to_sell` floor (v2.77.0):** the position's OVERALL blended-average
   `raw_gain_pct` must exceed this, regardless of which gate cleared or how many lots the
   loss-lot guard excluded. This is what stops GET THE PROFITS from cherry-picking the few
   profitable lots out of a position that is a loser overall.
8. **Same-day repeat guard:** skip if `profitSellDate` already equals today.
9. **Resell cooldown:** skip if `(current_date − profitSellDate) <
   profit_resell_cooldown_days` (strict `<`; a gap exactly equal to the window clears).
   First-ever profit-sell (no `profitSellDate` on record) is never blocked by this.
10. **`selling_price_change` guard:** require
    `(close_yesterday − price) × 100 / price < selling_price_change` — i.e. don't sell into a
    sharp same-day drop. Missing price history fails closed (skip).
11. **`target_price_to_sell` guard:** if a floor is configured and price hasn't crossed it,
    skip — this override outranks everything, including the emergency stops above.
12. If all of the above pass: plan the sale with the exact FIFO lot selection passed via
    `tax_lots` (so what's realized matches what was gated on). Overrides `lock_in_period`;
    fires whether the asset is Underweight, Overweight, or within tolerance.

### S4. Sell Cleanup Pass (Step 4b, v2.80.0)

Runs immediately after S3, over the state S3 leaves behind (so it sees this cycle's own GET THE
PROFITS fills). It disposes of the small single-lot remainders that whole-share rounding and
loss-lot exclusion routinely leave behind. Two independent rules, unioned:

* **(a) Dust cleanup — any held target asset:** remaining position is exactly ONE tax lot, that
  lot is not a loss (`cost_per_share <= price`; breakeven counts as not losing), AND the
  remaining market value is under `cleanup_dust_threshold_dollars` → sweep the whole remainder.
* **(b) Finish-the-job — a symbol whose GET THE PROFITS sale fired THIS cycle:** exactly ONE
  non-loss lot left → sweep it in full regardless of dollar size.

Both rules **bypass every GET THE PROFITS profit gate** (the percent/dollar OR-gate,
`min_raw_gain_percent_to_sell`, `profit_resell_cooldown_days`, `selling_price_change`) — this is
remainder cleanup, not a profit-taking decision. They still respect the `blocked` list and
`target_price_to_sell`. Always sized as an ORDINARY order (the remainder is very often itself
fractional, and with one lot involved default matching disposes of that same lot anyway).

A symbol whose GET THE PROFITS sale this cycle went out as an ordinary order (the
sub-whole-share or zero-available-lots fallback) is **skipped by this pass entirely** — without
knowing which lots Robinhood actually consumed, the remaining lot structure isn't knowable.

A cleanup sale realizes a gain or exact breakeven by construction, so it is treated like a GET
THE PROFITS sale for `peak/prices.json` bookkeeping (it stamps `profitSellPrice/Date`, arming the
buy-side repurchase guard) and can never need to arm the wash-sale buy-guard. Its realized
dollars are reported separately as `Total_Cleanup_Gains_Realized`, not folded into
`Total_High_Beta_Gains_Realized`.

### Sell-side finalization (Step 6a)

* Every planned sell below `sell_or_buy_value_limit` is dropped (logged SKIPPED) — **except S4
  cleanup sweeps, which are exempt (v2.82.0)**. The cleanup pass exists precisely to place tiny
  orders; gating them on this floor just re-created the dust the pass was meant to clear (a
  sub-$50 remainder got swept by S4 and dropped here every cycle, forever). Journal counts
  reflect only what was actually placed.
* **Per-trade approval halt:** if any single planned sell — or any single provisionally-sized
  buy — exceeds `seek_approval_value`, the whole cycle halts before ANY order is placed and
  waits for explicit user approval. (Buys that could never actually be placed — same-cycle
  sellers, `blocked` symbols — are excluded from this check.)
* Consequences recorded after fills: profit sales and cleanup sweeps stamp `profitSellPrice/Date`
  (arming the buy-side repurchase guard); liquidations stamp `liquidatedPrice/Date`; loss sales
  stamp `lastLossSalePrice/Date`. **"Realized a loss" is judged on the sale's NET figure, never
  lot-by-lot (v2.83.0)** — a net-profit full exit that disposes of an underwater lot does not arm
  the wash-sale guard.

**Removed sell mechanisms (v2.74.0):** Momentum Reversal Trim, routine Overweight High-Beta
trims, harvest sizing (`harvest_needed_dollars`), the `minimum_alpha_leader_sell_profit`
floor, and the Fresh Alpha Leader Stop. Parameters that only served them
(`overweight_sell_minimum_profit_margin_percent/_dollars`, `sell_price_diff_limit`,
`lock_in_period`) are retained in `portfolio_targets.json` but are currently inert.

---

## BUY DECISION

Buys come from two passes over the same deployable cash: momentum-ranked top-down Underweight
fills, then a Position Cap Top-Up of whatever that fill left unspent.

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
future sells, but receives NO buy this cycle — from either buy pass. Under the top-down fill, a
guarded symbol is not in the ranking at all — **its would-be allocation shifts down to the
next-ranked qualifying candidate; cash is never held back for it.**

1. **Three-leg buy-timing guard** (all three must clear; all measured as a % of the live
   price; missing history fails closed):
   * leg 1 — earlier dip: `(close_2day_back − close_1day_back) × 100 / price >
     1st_leg_price_change`
   * leg 2 — dip continued: `(close_1day_back − close_yesterday) × 100 / price >
     2nd_leg_price_change`
   * leg 3 — turn confirmed: `(price − close_yesterday) × 100 / price >
     3rd_leg_price_change`

   **Per-asset volatility scaling (v2.87.0):** those three parameters are global *baselines*,
   not the literal bars applied to each symbol — a flat bar treats a 3x leveraged ETF and a slow
   utility identically, which is backwards, since normal day-to-day noise scales with an asset's
   own volatility. Each leg is scaled by
   `asset_20d_stdev / portfolio_average_20d_stdev` (the average across every target with enough
   history that cycle — deliberately **not** measured against SPY, which would come out above 1.0
   for every name in a high-beta book and just loosen the guard uniformly). Fewer than 5 trailing
   daily returns falls back to scale `1.0`; a true missing-history case still fails closed via the
   legs' own check. Any target may override `leg1_price_change`/`leg2_price_change`/
   `leg3_price_change` outright, independently per leg. The journal logs each blocked symbol's
   resolved threshold and its scale factor, e.g. `need > 0.571% [asset-scaled, x2.85]`.
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
* This pass never deploys past a candidate's own drift gap — leftover cash falls through to B5b.

### B5b. Position Cap Top-Up (Step 3, v2.80.0) — a SECOND pass over the leftover cash

A weight-driven drift gap can't reach cash that no symbol is currently underweight enough to
absorb. This pass deploys it instead, by topping positions up toward a flat **dollar** cap.

* **Which symbols participate:** each target resolves an effective `max_position_value` — its own
  field if set, else the global `default_max_position_value` (v2.80.1) if the portfolio configures
  one, else the symbol doesn't participate at all. Setting the global opts every target in by
  default.
* **Independent of drift/Underweight status** — that is the entire point. A symbol already filled
  in B5 is topped up *further* from where that fill left it, not from zero.
* **Guards that still apply:**
  * every Step 2 buy guard (B2) — the same `buy_guarded_symbols` set the top-down fill checks;
  * `min_momentum_score_to_fill_underweight` (v2.81.0) — a candidate below the floor, or with no
    computable score, is excluded here too, closing the gap where Top-Up could route dollars into
    the single worst-ranked candidate purely because it had room under its cap;
  * **held-at-a-loss guard (v2.81.0, configurable since v2.85.0)** — a symbol already held (any
    quantity > 0) whose `raw_gain_pct` is below `held_at_loss_rebuy_threshold_percent` is
    excluded: don't add fresh dollars to a position sitting on too large a loss just to chase the
    dollar cap. The default `0.0` means any loss excludes; a more negative setting (e.g. `-3.0`)
    tolerates a small one — a position at `-2.0%` clears `-3.0` and stays eligible, one at
    `-4.0%` does not. An unresolved cost basis fails closed (excluded). A currently-unheld symbol
    is unaffected — it has no basis to be at a loss against.
  * the SAME per-asset `max_allocation_percent`/`max_portfolio_percentage` headroom B5 respects,
    so `max_position_value` can never push a symbol past its percent cap even when set higher.
* **Room** = `min(effective_max_position_value − projected_market_value, per-asset headroom −
  already-planned dollars)`, floored at 0.
* **Multiple candidates share the leftover cash pro-rata by `weight`, via water-filling:**
  repeatedly split whatever remains proportionally to each active candidate's `weight`, drop any
  candidate whose room fills up that round, and repeat with the rest — so a low-room candidate
  isn't starved by iteration order and a high-room one doesn't hog everything in one pass.
* Runs BEFORE the sector cap below, so B6 caps the combined B5 + B5b total.

### B6. Sector concentration cap (Step 3, final pass)

* For each `sector_groups` group: if current group market value + planned group buys (B5 **and**
  B5b) would exceed the group's cap (`maxPercentage` override, else global
  `max_sector_percentage`) as a percent of `account_balance`, scale every member's planned buy
  down proportionally to land exactly at the cap (floored at 0). Capped-away dollars are NOT
  redistributed.

### B7. Price-limit halts (Step 5 — per planned buy)

* **`buy_price_diff_limit`:** drop the buy if price is more than that % above the
  `no_of_days_for_price_compare`-day low (don't chase a pump).
* **`52_week_high_guard`:** drop the buy if `price / 52_week_high × 100 >` the guard (95).
  Missing 52-week-high data fails OPEN (buy allowed).

### B8. Buy-side finalization (Step 6b — after this cycle's sells are confirmed filled)

1. Re-fetch post-sell YTD realized P&L and fresh `buying_power`; finalize `tax_reserve` from
   the actual post-sell figure (never hand-reconstructed from estimates), net of
   `tax/paid_taxes_by_year.json`.
2. **Same-cycle buy/sell exclusivity:** drop any planned buy whose symbol sold this cycle
   (via any mechanism, including an S4 cleanup sweep) or is `blocked`.
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

## Reporting-only outputs (Step 7)

These are rendered into `logs/trade_journal.md` and the email report. **None of them gates,
sizes, delays or influences any decision above** — they are observational by design, and a
failure to compute one degrades that section rather than aborting the cycle:

* **Dormant Assets** — held targets whose last activity is older than `dormant_asset_days`.
* **Loss-Only Lot Assets (v2.76.0)** — held targets where every sellable priced lot sits at or
  above the current price, i.e. exactly the population S3's loss-lot guard can never sell any
  part of. Computed *after* this cycle's buys are sized, so a symbol bought this cycle drops off.
* **Deferred Wash-Sale Loss Tracking (v2.84.0)** — when a net-profit full exit (S3 step 3) nets
  out an underwater lot and the symbol is bought back inside `wash_sale_lookback_days`, the
  deferral is journaled and a later cycle checks that Robinhood carried the adjustment into the
  new lot's basis. **The bot never adjusts a cost basis itself** — Robinhood already does that
  same-account, and doing it again would double-count.
* **Position Cap Top-Up breakdown** — which symbols B5b topped up and by how much; a breakdown of
  dollars already counted in the Buys section, not a separate trade category.

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
shortfall.

Now suppose only $3,000 of gaps existed and $7,000 were left over after B5. That leftover does
**not** just sit as cash: B5b water-fills it pro-rata by `weight` toward each participating
symbol's `max_position_value` — skipping anything buy-guarded, below the momentum floor, or held
at a loss worse than `held_at_loss_rebuy_threshold_percent`, and never exceeding a symbol's own
percent headroom. The sector-cap pass then runs over the combined B5 + B5b allocations, and Step
5/6's price limits, exclusivity, hard cap, and dollar floors apply before any order is placed.
