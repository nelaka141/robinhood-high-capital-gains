# 2026-07-22 03:16 PM EDT — Scheduled Rebalance Check — NO TRADES (SMCI Alpha Leader GET-THE-PROFITS Suppressed on Same-Day Re-Trigger; MU/SOXL Cooldown Clears Under Revised 6-Day Parameter but Both Pump-Guard-Blocked on Their Own Rebound; AMZN Newly Breaches Drift; TQQQ/PLTR/META Still Negative-Margin-Blocked; Zero Deployable Cash Behind the $9,000 Reserve Wall)

**Status:** NO TRADES. **0 of 0 intended orders filled** — fresh, stateless
run for the 3:15 PM ET scheduled tick. `CLAUDE.md` re-pulled fresh from
`main` (SHA `06d224a15d70614bf5f853cfdcbd9e5cc43755c3`, text version header
"Volume 2.29.0" — unchanged in substance from the 9:52 AM cycle's "Volume
2.28.0" pull, version-string bump only). `portfolio_targets.json` (now
**v2.19.0**, up from v2.17.0 — `cool_down_period_after_lquidation` changed
from the previously-assumed 8 days to **6 days**, see below),
`peak/prices.json`, and `settlement/reserve.json` all re-pulled fresh from
`main` for this run.

## Pre-check state (~3:16 PM ET, regular hours)
* Account `795732718` ("Agentic", cash-type). `buying_power` =
  **$9,250.01**, `cash` (ledger) = **$9,279.24** — a **$29.23 gap**,
  matching this morning's still-unsettled SMCI GET-THE-PROFITS sale
  (filled 9:51 AM ET, expected settle 2026-07-23, T+1). Per the clarified
  rule, `account_cash`/`current_cash` is sourced from `buying_power`, not
  the raw `cash` ledger.
* `current_cash` = Math.min($9,250.01, `cap_on_total_cash_balance_to_use`
  $10,000) = **$9,250.01**.
* Equity value (live quotes, 27 held target symbols; MU, SOXL, IONQ still
  at zero shares): **≈$36,401.66** (broker `get_portfolio` snapshot).
  `account_balance` ≈ **$45,651.67**.
* `get_equity_orders` confirms only one order today (the 9:51 AM SMCI
  sell already logged in the prior entry) — no orders yet this cycle.

## Settlement reserve reconciliation (Step 1)
* `settlement/reserve.json` → `pending_draws` = `[]`, unchanged from this
  morning. Nothing to reconcile.
* `reserve_available_to_draw` = $9,000 − $0 drawn = **$9,000** (full,
  unused). This morning's unsettled SMCI proceeds ($29.23) were never
  recorded as a `pending_draws` entry since no buy needed bridging that
  cycle — the cash/buying_power gap is expected and requires no action.

## Drawdown audit (Step 1)
Checked every held asset against `max_trailing_drawdown_percentage` (25%)
vs. both `peakPrice` and `avg_cost_basis` (both legs must breach). **No
asset breached 25% on either leg.** Closest: SPCX (23.94% off its
$152.9988 peak / 23.25% off its $151.62 cost basis) — nearer the line than
any prior cycle but still short. No emergency liquidations triggered, so
the `lock_in_period` override from Step 2 is not invoked.

## Liquidation recovery / cooldown check (Step 2) — parameter change surfaces two newly-eligible assets
`portfolio_targets.json` v2.19.0 sets `cool_down_period_after_lquidation`
**= 6 days** (down from the 8 days assumed in every prior cycle's log —
confirmed by re-reading the freshly-pulled file, not carried over from
memory).
* **MU**: liquidated 2026-07-16 @ $862.81. Days elapsed = **6**, meets the
  6-day cooldown exactly (6 ≥ 6) — **cooldown cleared for the first time**.
  Recovery: current $966.7412 is **+12.05%** vs. liquidated price, clears
  the 5% `min_recovery_price_percentage` bar. **MU is back in play** —
  but see the pump-guard block below.
* **SOXL**: liquidated 2026-07-16 @ $147.6401. Days elapsed = **6**,
  cooldown cleared. Recovery: current $162.875 is **+10.32%** vs.
  liquidated price, clears the 5% bar. **SOXL is back in play** — also
  pump-guard-blocked below.
* **IONQ**: liquidated 2026-07-13 @ $38.8001. Cooldown cleared (9 days
  elapsed), but current $34.8201 is still **10.26% below** the liquidated
  price — a further decline, not a recovery. **Stays out of drift calc.**

## Drift & Alpha Leader (Step 3)
Target weights sum to 52.3 across 30 symbols. Drift computed against
`account_balance` ≈ $45,651.67.

**Overweight (breaching resolved `asset_drift_tolerance`):**
| Symbol | Current % | Target % | Drift | Asset tolerance |
|---|---|---|---|---|
| META | 15.28% | 1.91% | +13.37% | 0.5% (persistent, unchanged) |
| TQQQ | 5.74% | 2.87% | +2.88% | 0.5% |
| PLTR | 7.03% | 4.78% | +2.25% | 1.0% |

**Underweight (breaching resolved `asset_drift_tolerance`):**
| Symbol | Current % | Target % | Drift | Asset tolerance | Guard status |
|---|---|---|---|---|---|
| MU | 0.00% | 4.78% | 4.78% | 1.0% | Cooldown/recovery cleared, **pump-guard blocked** |
| AAPL | 0.09% | 1.91% | 1.82% | 0.5% | Clear — unfunded |
| IBM | 0.09% | 1.91% | 1.83% | 0.5% | Clear — unfunded |
| GE | 0.09% | 1.91% | 1.82% | 0.5% | Clear — unfunded |
| F | 0.09% | 1.91% | 1.82% | 0.5% | Clear — unfunded |
| NFLX | 0.09% | 1.91% | 1.82% | 0.5% | **Pump-guard blocked** |
| UNH | 0.09% | 1.91% | 1.82% | 0.5% | Clear — unfunded (Alpha-cascade target, see below) |
| SMCI | 0.09% | 1.91% | 1.82% | 0.5% | **Repurchase-lock blocked** (profit-sold today) |
| GM | 0.09% | 1.91% | 1.82% | 0.5% | **Pump-guard blocked** |
| AVGO | 0.16% | 1.91% | 1.76% | 0.5% | **Pump-guard blocked** |
| VRT | 0.15% | 1.91% | 1.76% | 0.5% | **Pump-guard blocked** |
| ARM | 0.26% | 1.91% | 1.65% | 0.5% | Repurchase lock cleared, **pump-guard blocked** |
| HOOD | 0.29% | 1.91% | 1.62% | 0.5% | **Pump-guard blocked** |
| AMD | 0.32% | 1.91% | 1.59% | 0.5% | **Pump-guard blocked** |
| NEE | 0.31% | 1.91% | 1.60% | 0.5% | Clear — unfunded |
| SOXL | 0.00% | 1.91% | 1.91% | 0.5% | Cooldown/recovery cleared, **pump-guard blocked** |
| COIN | 0.66% | 1.91% | 1.26% | 0.5% | **Repurchase-lock blocked** (profit-sold today) |
| **AMZN** | 6.22% | 7.27% | **1.05%** | 1.0% | **Newly breaching** (was 1.05% vs. 1.0% tolerance — first breach in recent cycles) — clear, unfunded |

**Within tolerance, no action:** MSTR (0.45% vs. 0.5%), SPCX (0.25% vs.
0.5%), TSLA (0.53% vs. 1.0%), NVDA (0.51% vs. 1.0%), ORCL (0.31% vs.
2.0%), GOOG (0.63% vs. 1.0%), MSFT (0.23% vs. 1.5%).

**Excluded from drift calc:** IONQ (liquidation recovery not met — see
Step 2).

**Alpha Leader — SMCI (+14.28% over 7 days)**, computed from the
2026-07-15 official close ($26.89) → live $30.73. Ranked field (7-day
gainers): MU +6.91%, AMD +5.05%, GM +4.93%, UNH +3.51%, ARM +2.97%, MSTR
+2.51%, INTC +1.40%.

**GET THE PROFITS check on SMCI:** avg cost basis $27.46, current
$30.73 → unrealized gain **+11.90%**, well past `materialize_profit_percentage`
(4.0%) — would trigger, but `peak/prices.json` shows `profitSellDate`
**2026-07-22** (today, from the 9:51 AM cycle's sale). Per the standing
rule ("do not trigger GET THE PROFITS again if there are any previous
sales on the Alpha Leader within today's business day"), **this cycle's
trigger is suppressed**.

**Alpha-routing cascade (buy-side, independent of the GET-THE-PROFITS
suppression):** SMCI is also independently blocked from any fresh buy —
its own repurchase-lock guard (0 of 2 `sold_asset_repurchase_days`
elapsed since today's profit-sell) and the pump guard (current price
+31.44% above its 3-day low) both fail. Cascading down the momentum
ranking for a buy-eligible, non-blocked target: MU (pump-blocked, +20.24%
above 3-day low) → AMD (pump-blocked, +20.78%) → GM (pump-blocked,
+8.92%) → **UNH (+3.51%, clear of every guard)** — but `base_deployable_cash`
computed below is $0.01, so even this cascade target receives no
allocation this cycle.

`base_deployable_cash` = Math.max(0, $9,250.01 − $250 `min_cash_absolute`
− $9,000 `settlement_reserve_target`) = **$0.01** — immaterial.

## Overweight trim evaluation (Step 4) — zero legal sell source, unchanged
All three Overweight candidates fail the
`overweight_sell_minimum_profit_margin_percent` (1.0%) gate and none is
listed in `forceSell`:
| Symbol | avg_cost_basis | current_price | Raw_Gain_% | Lock-in? | Sellable? |
|---|---|---|---|---|---|
| META | 664.01 | 626.62 | −5.63% | Clear (6d > 2d) | No — underwater |
| TQQQ | 73.92 | 70.745 | −4.30% | Clear (6d > 2d) | No — underwater |
| PLTR | 134.51 | 124.19 | −7.67% | No `lastPurchaseDate` (untracked, treated unlocked) | No — underwater |

No legal Overweight trim source exists this cycle — the High-Beta Gain
Score ranking was not computed (nothing to rank when every candidate is
guardrail-blocked). `Total_High_Beta_Gains_Realized` (overweight-trim
component) = **$0.00**.

## Price limit / volatility halts (Step 5) — the binding constraint this cycle
3-day (`no_of_days_for_price_compare`) low/high window (2026-07-17,
2026-07-20, 2026-07-21) checked for every Underweight candidate against
`buy_price_diff_limit` (5%):

| Symbol | 3-day low | Current | Rally vs. low | Exempt? |
|---|---|---|---|---|
| AMD | 460.21 | 555.845 | +20.78% | Yes |
| SOXL | 116.47 | 162.875 | +39.84% | Yes |
| MU | 804.00 | 966.7412 | +20.24% | Yes |
| ARM | 243.12 | 285.2399 | +17.32% | Yes |
| INTC | 89.59 | 104.43 | +16.56% | Yes |
| VRT | 272.93 | 302.985 | +11.01% | Yes |
| AVGO | 357.80 | 397.01 | +10.96% | Yes |
| GM | 74.80 | 81.47 | +8.92% | Yes |
| HOOD | 96.59 | 104.80 | +8.50% | Yes |
| NFLX | 65.08 | 68.425 | +5.14% | Yes |
| ORCL | 120.03 | 126.415 | +5.32% | (within tolerance anyway) |
| F | 13.85 | 14.315 | +3.36% | No |
| GE | 339.89 | 340.62 | +0.21% | No |
| AAPL | 322.22 | 324.5075 | +0.71% | No |
| IBM | 208.82 | 205.73 | −1.48% | No |
| UNH | 417.38 | 433.22 | +3.80% | No |
| NEE | 87.445 | 89.60 | +2.46% | No |
| AMZN | 243.59 | 244.39 | +0.33% | No |

Ten of the eighteen Underweight-breaching candidates are exempted from
buying today by the pump guard, including both newly-recovered assets
(MU, SOXL) and the repurchase-cleared ARM — the same sharp rebound that
cleared their recovery/repurchase gates is itself over the 5% parabolic
limit. `sell_price_diff_limit` was not reached — no Overweight/stop-loss
sell candidates survived to this stage.

## Execution (Step 6)
**No orders placed this cycle.** Even the eight Underweight candidates
clear of every guard (AMZN, AAPL, IBM, F, GE, UNH, NEE, and the
Alpha-cascade target UNH) could not be funded: `base_deployable_cash`
is $0.01, no legal Overweight trim proceeds exist to harvest, and no
`forceSell` override applies. Every candidate trade this cycle would
have fallen below `sell_or_buy_value_limit` ($10) even before the cash
constraint. No `seek_approval_value` ($10,000) halt was relevant — no
trade was sized at all. No buy/sell same-symbol conflict arose (nothing
executed on either side).

### Settlement reserve — no new draws, no reconciliation
`pending_draws` remains `[]`. `reserve_available_to_draw` stays
**$9,000** for the next cycle. The 9:51 AM SMCI sale ($29.23) is expected
to settle 2026-07-23 (T+1) and will close the current `cash`/
`buying_power` gap next cycle.

## Post-cycle balances (unchanged from pre-check — no trades)
* `cash` **$9,279.24**, `buying_power` **$9,250.01** (gap = $29.23,
  unsettled SMCI proceeds).
* `equity_value` **≈$36,401.66**, `account_balance` **≈$45,651.67**.
* Cash sits well above `min_cash_target` ($500) and `min_cash_absolute`
  ($250); the $9,000 reserve wall-off remains the structural reason cash
  cannot be worked down closer to `min_cash_target` this cycle.

## peak/prices.json updates
* **NVDA**: `peakPrice` 211.875 → **213.205** (new high), `peakDate` →
  **2026-07-22**.
* **AVGO**: `peakPrice` 396.12 → **397.01** (new high), `peakDate` →
  **2026-07-22**.
* All other symbols: current price at or below stored peak — no change.
  No `liquidatedPrice`/`liquidatedDate`, `profitSellPrice`/`profitSellDate`,
  or `lastPurchaseDate` fields changed (no sells or buys executed this
  cycle, so MU/SOXL's newly-cleared cooldown/recovery status is not yet
  reflected in any field change — those fields only update on an actual
  liquidation/repurchase event).

## Total_High_Beta_Gains_Realized
**$0.00** this cycle — no Overweight trims executed (all three candidates
guardrail-blocked) and no GET-THE-PROFITS sale (suppressed as a same-day
repeat on SMCI).

## Reconciliation
No `pending_draws` entries existed at cycle start and none were created —
nothing to reconcile this cycle. The 9:51 AM SMCI sale remains unsettled
outside the reserve-tracking system (no buy needed bridging that cycle,
so no entry was ever created for it), expected to settle 2026-07-23.

## SKIPPED/PENDING trade matrix
| Symbol | Intent | Amount | Reason |
|---|---|---|---|
| META | Sell (overweight trim) | n/a | −5.63% raw loss, below 1.0% profit-margin floor, not in `forceSell` |
| TQQQ | Sell (overweight trim) | n/a | −4.30% raw loss, below 1.0% profit-margin floor, not in `forceSell` |
| PLTR | Sell (overweight trim) | n/a | −7.67% raw loss, below 1.0% profit-margin floor, not in `forceSell` |
| SMCI | Buy (Alpha Leader, rank 1 + drift) | n/a | Repurchase lock unmet (0 of 2 days since today's profit-sell); GET-THE-PROFITS also suppressed (same-day repeat) |
| MU | Buy (repurchase + drift) | n/a | Cooldown/recovery newly cleared (6d, +12.05%) but +20.24% above 3-day low, exceeds 5% `buy_price_diff_limit` |
| SOXL | Buy (repurchase + drift) | n/a | Cooldown/recovery newly cleared (6d, +10.32%) but +39.84% above 3-day low, exceeds 5% pump limit |
| ARM | Buy (repurchase + drift) | n/a | Repurchase lock cleared (13d, −14.48%) but +17.32% above 3-day low, exceeds 5% pump limit |
| INTC | Buy (drift) | n/a | +16.56% above 3-day low, exceeds 5% pump limit |
| AMD | Buy (drift) | n/a | +20.78% above 3-day low, exceeds 5% pump limit |
| GM | Buy (drift) | n/a | +8.92% above 3-day low, exceeds 5% pump limit |
| VRT | Buy (drift) | n/a | +11.01% above 3-day low, exceeds 5% pump limit |
| AVGO | Buy (drift) | n/a | +10.96% above 3-day low, exceeds 5% pump limit |
| HOOD | Buy (drift) | n/a | +8.50% above 3-day low, exceeds 5% pump limit |
| NFLX | Buy (drift) | n/a | +5.14% above 3-day low, exceeds 5% pump limit |
| COIN | Buy (drift) | n/a | Repurchase lock unmet (0 of 2 days since today's profit-sell) |
| IONQ | Buy (repurchase) | n/a | Cooldown cleared (9d) but price still 10.26% below liquidated price — recovery not met |
| AMZN | Buy (drift, newly breaching) | n/a | Zero deployable cash ($0.01 `base_deployable_cash`) |
| AAPL | Buy (drift) | n/a | Zero deployable cash |
| IBM | Buy (drift) | n/a | Zero deployable cash |
| F | Buy (drift) | n/a | Zero deployable cash |
| GE | Buy (drift) | n/a | Zero deployable cash |
| NEE | Buy (drift) | n/a | Zero deployable cash |
| UNH | Buy (drift + Alpha-cascade target) | n/a | Zero deployable cash |

## Notes
Two developments worth flagging for the next cycle. First,
`portfolio_targets.json` moved to v2.19.0 with
`cool_down_period_after_lquidation` cut from 8 to 6 days — this silently
cleared MU and SOXL's liquidation lockout today for the first time since
their 2026-07-16 liquidation, and both also independently cleared the 5%
`min_recovery_price_percentage` recovery bar. Neither could be bought
today only because the same sharp rebound that earned their recovery
clearance also pushed them well past the 5% `buy_price_diff_limit` pump
guard (+20.24% and +39.84% respectively, off 3-day lows) — worth
re-checking next cycle once the rally cools. Second, AMZN crossed into
its first drift breach in recent memory (1.05% vs. its 1.0% asset-level
tolerance) — a narrow breach driven by today's broad down-day pulling
AMZN's current weight below target; unfunded like every other Underweight
candidate this cycle given the $9,000 reserve wall leaves only $0.01 of
`base_deployable_cash`. META's persistent 13.4-point overweight drift
remains structurally un-trimmable under current guardrails, unchanged
from every prior cycle. Zero drawdown breaches, zero legal trims, zero
deployable cash for buys — a fully quiet execution cycle despite an
unusually active drift/guard landscape underneath.
Per repo convention, this entry is committed to a fresh feature branch
and merged directly into `main` to preserve the unalterable paper trail.
---

# 2026-07-22 09:52 AM EDT — Scheduled Rebalance Check — EXECUTED (Alpha Leader Rotates to SMCI on a +14.8% 7-Day Momentum Spike, GET-THE-PROFITS Fires at +12.4% Unrealized Gain — $29.23 Realized, No Alpha Buy This Cycle; PLTR/TQQQ/META Overweight but Negative-Margin-Blocked as Usual; Zero Underweight Breaches; Overnight COIN Settlement Reconciled, Reserve Fully Restored)

**Status:** EXECUTED. **1 of 1 intended order filled** (1 sell, 0 buys) —
fresh, stateless run for the 9:45 AM ET scheduled tick. `CLAUDE.md`
re-pulled fresh from `main` (SHA `2df0e17`, text version header "Volume
2.28.0", unchanged from the last several cycles). `portfolio_targets.json`
(v2.17.0), `peak/prices.json`, and `settlement/reserve.json` all re-pulled
fresh from `main` for this run.

## Pre-check state (~9:47 AM ET, regular hours)
* Account `795732718` ("Agentic", cash-type). `buying_power` =
  **$9,250.01**, `cash` (ledger) = **$9,250.01** — **no gap**, confirming
  yesterday's COIN profit-take sale ($210.87, expected settle
  2026-07-22) has now cleared into spendable buying power.
* `current_cash` = Math.min($9,250.01, `cap_on_total_cash_balance_to_use`
  $10,000) = **$9,250.01**.
* Equity value (live quotes, 27 held target symbols; MU, SOXL, IONQ still
  at zero shares under liquidation cooldown/recovery-fail): broker
  `get_portfolio` snapshot **$36,779.70**. `account_balance` ≈
  **$46,029.71**.

## Settlement reserve reconciliation (Step 1)
* `settlement/reserve.json` → one `pending_draws` entry: COIN, saleDate
  2026-07-21, expectedSettleDate 2026-07-22, saleProceeds $210.87,
  reserveDrawn $210.87, settled: false.
* Settlement check: `cash` − `buying_power` = $9,250.01 − $9,250.01 =
  **$0.00** — the gap has closed exactly as expected on the T+1 settle
  date. **Confirmed settled** — entry marked `settled: true` and removed
  from `pending_draws`, fully replenishing the reserve.
* `reserve_available_to_draw` after reconciliation = $9,000 − $0 =
  **$9,000** (full headroom restored for this cycle).

## Drawdown audit (Step 1)
Checked every held asset against `max_trailing_drawdown_percentage`
(25%) vs. both `peakPrice` and `avg_cost_basis`. **No asset breached 25%
on either leg.** Closest: SPCX (20.2% off its $152.9988 peak / 19.5% off
its $151.62 cost basis), INTC (9.8% off peak / 17.0% off cost basis). No
emergency liquidations triggered.

## Liquidation recovery / cooldown check (Step 2)
* **MU**: liquidated 2026-07-16 @ $862.81. Current $961.68 is +11.5%
  (clears the 7% `min_recovery_price_percentage` bar), but only 6 days
  elapsed vs. the 8-day `cool_down_period_after_lquidation` — still
  locked out. Stays out of drift calc.
* **SOXL**: liquidated 2026-07-16 @ $147.6401. Current $156.61 is only
  +6.1% — below the 7% recovery bar (and cooldown also unmet at 6 days).
  Stays out of drift calc.
* **IONQ**: liquidated 2026-07-13 @ $38.8001. Cooldown cleared (9 days
  elapsed), but current $35.5401 is still **8.4% below** the liquidated
  price — a further decline, not a recovery. Stays out of drift calc.

## Drift & Alpha Leader (Step 3)
Target weights sum to 52.3 across 30 symbols. Drift computed against
`account_balance` ≈ $46,024 (`drift_tolerance_percentage` 2.0%; no
symbol qualifies for the 0.1% first-time-trade tolerance this cycle —
every target has an entry in `peak/prices.json`).

**Overweight (>2.0% drift):**
| Symbol | Current % | Target % | Drift |
|---|---|---|---|
| META | 15.35% | 1.91% | +13.44% |
| TQQQ | 5.68% | 2.87% | +2.82% |
| PLTR | 7.22% | 4.78% | +2.44% |

**Underweight:** none breaching this cycle — F, GM, IBM, NFLX, UNH, GE
all sit at ~1.82% drift, just inside the 2.0% band (each now has an
established `lastPurchaseDate`, so standard tolerance applies, not the
0.1% first-time-trade tolerance from two cycles ago).

**Alpha Leader — SMCI (+14.80% over 7 days)**, computed from the
2026-07-15 official close ($26.89) → live $30.87 at scan time — a sharp
single-day momentum spike (SMCI traded up ~21% intraday vs. its prior
close). Runner-up was GM (+7.60%); MU (+6.35%, cooldown-excluded) and
COIN (+4.52%, repurchase-lock-excluded — only 1 of 2
`sold_asset_repurchase_days` elapsed) both outranked GM but are
ineligible for any Alpha routing this cycle regardless of the outcome
below.

**GET THE PROFITS check on SMCI:** avg cost basis $27.46, current price
$30.8695 at scan time → unrealized gain **+12.42%**, well past
`materialize_profit_percentage` (4.0%). `get_equity_orders` confirmed no
SMCI orders (or any orders) placed on this account yet today — rule
**triggers** cleanly. Per CLAUDE.md: sell `profit_sell_percentage` (40%)
of SMCI and **do not buy any new Alpha Leader shares this cycle** (moot
for SMCI regardless — see below — but the rule would have blocked a
buy-side rotation to GM too, since the "no buy" clause is unconditional
once a GET-THE-PROFITS sale fires).

*Note for the record:* SMCI's own repurchase-lock guard would have
independently blocked any fresh SMCI **buy** this cycle even absent the
profit-take rule — its price is **+6.6% above** (not below) its
`profitSellPrice` ($28.9601, sold 2026-07-09), the opposite of the
required ≥1.5% drop needed to bring a previously profit-sold asset back
into buy-eligibility.

`base_deployable_cash` = Math.max(0, $9,250.01 − $250 `min_cash_absolute`
− $9,000 `settlement_reserve_target`) = **$0.01** — immaterial, and moot
since no Alpha buy occurs this cycle and no Underweight breach exists to
fund (see below).

## Overweight trim evaluation (Step 4) — zero legal sell source, again
All three Overweight candidates fail the
`overweight_sell_minimum_profit_margin_percent` (1.0%) gate and none is
listed in `forceSell`:
| Symbol | avg_cost_basis | current_price | Raw_Gain_% | Lock-in? | Sellable? |
|---|---|---|---|---|---|
| META | 664.01 | 634.62 | −4.43% | Clear (6d > 2d) | No — underwater |
| TQQQ | 73.92 | 70.565 | −4.54% | Clear (6d > 2d) | No — underwater |
| PLTR | 134.51 | 128.65 | −4.36% | No `lastPurchaseDate` (untracked, treated unlocked) | No — underwater |

No legal Overweight trim source exists this cycle, so the High-Beta Gain
Score ranking (Beta × Raw_Gain_%) was not computed — nothing to rank
when every candidate is guardrail-blocked. `Total_High_Beta_Gains_Realized`
(overweight-trim component) = **$0.00** this cycle.

## Underweight targets — none breaching, nothing to fund
All six previously first-time-trade targets (F, GM, IBM, NFLX, UNH, GE)
now sit inside the standard 2.0% tolerance band (~1.82% drift each) —
no Underweight breach exists this cycle, so the pro-rata buy step is a
no-op regardless of the near-zero `base_deployable_cash`.

## Price limit / volatility halts (Step 5)
Not applicable to the SMCI sale — `sell_price_diff_limit` only exempts
routine drift-selling on a **crash** day; SMCI is up sharply (+14.8%
over 7 days, +21% today), so the guard does not apply. No buy or
Overweight-trim candidates reached this stage.

## Execution (Step 6) — sequential, regular market hours
1. **SELL SMCI** 0.939214 sh (40% of the 2.348035-share position) @ avg
   **$31.1228** market → **$29.23** proceeds. Realized gain =
   ($31.1228 − $27.46) × 0.939214 = **+$3.44**. Order
   `6a60cacf-78e0-4595-83dc-e56f2655a8dc`, filled 2026-07-22 13:51:11 UTC
   (9:51:11 AM ET).

No order fell below `sell_or_buy_value_limit` ($10). Gross nominal value
sold ($29.23) was far under `seek_approval_value` ($10,000) — no
user-approval halt required. No buy/sell conflict on the same symbol
this cycle (SMCI buy is explicitly suppressed by the GET-THE-PROFITS
rule; no other buy was ever in play since zero Underweight breaches
existed).

### Settlement reserve — no new draws needed
SMCI's $29.23 sale proceeds are not yet reflected in `buying_power`
(confirmed empirically post-trade: `cash` $9,279.24 vs. `buying_power`
still $9,250.01, a $29.23 gap, expected to settle T+1 ≈ 2026-07-23). No
buy was funded this cycle, so **no bridging draw was created** —
`settlement/reserve.json` is left with an empty `pending_draws` list
(the sole prior entry, COIN, was reconciled and removed in Step 1 above).
`reserve_available_to_draw` remains **$9,000** for the next cycle.

## Post-trade balances
* `cash` **$9,279.24**, `buying_power` **$9,250.01** (gap = $29.23,
  matches the fresh unsettled SMCI proceeds).
* `equity_value` **$36,654.40**, `total_value` (account_balance)
  **$45,933.64**.
* Cash sits well above `min_cash_target` ($500) and `min_cash_absolute`
  ($250); the $9,000 reserve wall-off plus the cash floor account for
  the rest — consistent with "keep cash lean but never below floor."

## peak/prices.json updates
* **SMCI**: `peakPrice` 27.457 → **31.1228** (new all-time high, set by
  today's own execution fill, `peakDate` → **2026-07-22**);
  `profitSellPrice` → **31.1228**, `profitSellDate` → **2026-07-22**
  (fresh GET-THE-PROFITS record, overwriting the 2026-07-09 entry);
  `lastPurchaseDate` unchanged (2026-07-15, no buy this cycle).
* **F**: `peakPrice` 14.39 → **14.605** (new high), `peakDate` →
  **2026-07-22**.
* **GM**: `peakPrice` 79.55 → **83.5424** (new high), `peakDate` →
  **2026-07-22**.
* **NFLX**: `peakPrice` 69.0042 → **70.08** (new high), `peakDate` →
  **2026-07-22**.
* All other symbols: current price below stored peak — no change. No
  `liquidatedPrice`/`liquidatedDate` fields changed this cycle.

## Total_High_Beta_Gains_Realized
$0.00 from overweight trims (all three candidates blocked by the
profit-margin guard, as in every recent cycle). SMCI's GET-THE-PROFITS
sale realized **+$3.44** separately under the Alpha Leader profit-take
rule (not an overweight trim, so excluded from the High-Beta Gains tally
by definition, logged here for completeness — no `Beta_asset` computation
was needed since this wasn't a High-Beta-ranked trim).

## Reconciliation
One prior-cycle settlement reconciled this cycle: COIN's $210.87 draw
(saleDate 2026-07-21) confirmed settled via the closed `cash`/
`buying_power` gap, removed from `pending_draws`, restoring full $9,000
reserve headroom. One fresh sale this cycle (SMCI, $29.23) remains
unsettled but required no reserve bridge since no buy needed funding.

## Notes
This cycle's headline development: SMCI's single-day ~21% pop vaulted it
past every other target-list symbol on the 7-day momentum screen,
triggering its first-ever GET THE PROFITS realization since its original
2026-07-09 profit-take. Notably, SMCI's own repurchase-lock guard was
independently unsatisfied this cycle (price above, not below, its prior
`profitSellPrice`), meaning even without the GET-THE-PROFITS override, no
fresh SMCI buy could have occurred — the sell-side and buy-side guards
pointed the same direction for once. With the COIN settlement clearing
overnight, the reserve wall is now fully restored to $9,000 available,
but it remains structurally irrelevant this cycle since zero Underweight
breaches exist to fund. META's persistent 13.4-point overweight drift
remains the dominant unresolved imbalance — still underwater on cost
basis and thus un-trimmable under current guardrails, unchanged from
every prior cycle's assessment.
Per repo convention, this entry is committed to a fresh feature branch
and merged directly into `main` to preserve the unalterable paper trail.

---

 # 2026-07-21 03:15 PM EDT — Scheduled Rebalance Check — NO TRADES (META/TQQQ/PLTR/SPCX All Overweight but Negative-Margin-Blocked; Alpha Leader COIN Already Profit-Sold Earlier Today, Suppressed From Re-Triggering; Zero Deployable Cash; MU/SOXL/IONQ Still Cooldown/Recovery-Locked)

**Status:** NO TRADES. **0 of 0 intended orders** — fresh, stateless run for
the 3:15 PM ET scheduled tick. `CLAUDE.md` re-pulled fresh from `main` (SHA
`cf54c22`, text version header "Volume 2.28.0", unchanged since the 9:50 AM
cycle). `portfolio_targets.json` (v2.17.0), `peak/prices.json`, and
`settlement/reserve.json` all re-pulled fresh from `main` for this run.

## Pre-check state (~3:12 PM ET, regular hours)
* Account `795732718` ("Agentic", cash-type). `buying_power` = **$9,039.14**,
  `cash` (ledger) = **$9,250.01** — a **$210.87 gap**, exactly matching the
  still-open `pending_draws` entry from this morning's COIN profit-take
  sale. Per the clarified rule, `account_cash`/`current_cash` is sourced
  from `buying_power`, not the raw `cash` ledger.
* `current_cash` = Math.min($9,039.14, `cap_on_total_cash_balance_to_use`
  $10,000) = **$9,039.14**.
* Equity value (live quotes, 24 held target symbols; MU, SOXL, IONQ still at
  zero shares under liquidation cooldown/recovery-fail): **$37,118.34**.
  `account_balance` ≈ **$46,157.48**.

## Settlement reserve reconciliation (Step 1)
* `settlement/reserve.json` → one `pending_draws` entry: COIN, saleDate
  2026-07-21, saleProceeds $210.87, reserveDrawn $210.87, settled: false.
* Settlement check: `cash` − `buying_power` = $9,250.01 − $9,039.14 =
  **$210.87** — matches the lot almost exactly, meaning `buying_power` does
  **not** yet reflect the sale. **Not settled this cycle** — entry left
  unchanged, still pending. Expected settle date 2026-07-22 (T+1).
* `reserve_available_to_draw` = $9,000 − $210.87 (still-pending, fully
  drawn) = **$8,789.13** in theoretical headroom, but the COIN lot itself
  has **zero remaining bridgeable capacity** (`saleProceeds` − `reserveDrawn`
  = $0) and no fresh sell occurred this cycle to bridge against — moot,
  since no buys were funded this cycle regardless (see below).

## Drawdown audit (Step 1)
Checked every held asset against `max_trailing_drawdown_percentage` (25%)
vs. both `peakPrice` and `avg_cost_basis`. **No asset breached 25% on
either leg.** Closest: SPCX at 19.7% off its $152.9988 peak / 18.9% off its
$151.62 cost basis. No emergency liquidations triggered.

## Liquidation recovery / cooldown check (Step 2)
* **MU**: liquidated 2026-07-16 @ $862.81. Current $963.47 is +11.7%
  (clears the 7% `min_recovery_price_percentage` bar), but only 5 days
  elapsed vs. the 8-day `cool_down_period_after_lquidation` — still locked
  out. Stays out of drift calc.
* **SOXL**: liquidated 2026-07-16 @ $147.6401. Current $157.74 is only
  +6.8% — below the 7% recovery bar (and cooldown also unmet at 5 days).
  Stays out of drift calc.
* **IONQ**: liquidated 2026-07-13 @ $38.8001. Cooldown cleared (8 days
  elapsed), but current $35.255 is still **9.1% below** the liquidated
  price — a further decline, not a recovery. Stays out of drift calc.

## Drift & Alpha Leader (Step 3)
Target weights sum to 52.3 across 30 symbols. Drift computed against
`account_balance` ≈ $46,157.48 (`drift_tolerance_percentage` 2.0%).

**Overweight (>2.0% drift):**
| Symbol | Current % | Target % | Drift |
|---|---|---|---|
| META | 15.63% | 1.91% | +13.72% |
| TQQQ | 5.73% | 2.87% | +2.86% |
| PLTR | 7.45% | 4.78% | +2.67% |

(SPCX also nominally overweight at 4.26% vs. 3.82% target, but drift 0.44%
is inside tolerance.)

**Alpha Leader:** **COIN**, +9.47% over the trailing 7 days (vs. next-best
AAPL +4.15%, MSFT +3.76%). COIN's unrealized gain vs. `avg_cost_basis`
($166.64) at the current $176.79 quote is **+6.09%**, clearing the 4.0%
`materialize_profit_percentage` bar for **GET THE PROFITS** — but COIN
already has a profit-take sale recorded today (`profitSellDate`
2026-07-21, $175.7001, $210.87 realized at 9:50 AM ET). Per the standing
rule ("do not trigger GET THE PROFITS again if there are any previous
sales on the Alpha Leader within today's business day"), **this cycle's
GET THE PROFITS trigger is suppressed**. No incremental Alpha buy was
possible regardless — `base_deployable_cash` = Math.max(0, $9,039.14 −
$250 − $9,000) = **$0** (settlement reserve wall absorbs all headroom).

## Overweight trim evaluation (Step 4) — zero legal sell source
All four overweight/near-overweight candidates fail the
`overweight_sell_minimum_profit_margin_percent` (1.0%) gate and none is
listed in `forceSell`:
| Symbol | avg_cost_basis | current_price | Raw_Gain_% | Sellable? |
|---|---|---|---|---|
| META | 664.01 | 648.11 | −2.40% | No — underwater |
| TQQQ | 73.92 | 71.35 | −3.48% | No — underwater |
| PLTR | 134.51 | 133.18 | −0.99% | No — underwater |
| SPCX | 151.62 | 122.90 | −18.94% | No — underwater |

No legal Overweight trim source exists this cycle, so the High-Beta Gain
Score ranking (Beta × Raw_Gain_%) was not computed — there is nothing to
rank when every candidate is guardrail-blocked. `Total_High_Beta_Gains_Realized`
= **$0.00** this cycle.

## Underweight targets — unfunded on zero deployable cash
Every non-excluded target besides META/TQQQ/PLTR (SPCX inside tolerance)
is Underweight, but with `base_deployable_cash` at $0 and no harvestable
Overweight capital, **none could be funded**. Logged as SKIPPED/PENDING —
blocking reason: **zero deployable cash** (settlement reserve wall +
no legal sell source).

## Price limit / volatility halts (Step 5)
Not reached — no buy or sell candidates survived to this stage.

## peak/prices.json updates
New intraday highs recorded (current price exceeds stored `peakPrice`):
* **COIN**: peakPrice 176.195 → **176.79**, peakDate unchanged 2026-07-21.
* **ARM**: peakPrice 287.68 → **288.06**, peakDate 2026-07-14 → **2026-07-21**.
* **GM**: peakPrice 77.74 → **79.55**, peakDate unchanged 2026-07-21.
All other symbols: current price below stored peak — no change. No
`liquidatedPrice`/`liquidatedDate`, `profitSellPrice`/`profitSellDate`, or
`lastPurchaseDate` fields changed (no sells or buys executed this cycle).

## Final balances
* Cash (buying_power): **$9,039.14** (well above `min_cash_absolute` $250;
  above lean `min_cash_target` $500 — cannot be deployed closer to target
  this cycle since the settlement reserve wall consumes all headroom).
* Total equity value: **$37,118.34**.
* Account balance: **$46,157.48**.
* Reserve headroom: $8,789.13 theoretical / $0 bridgeable this cycle (COIN
  lot still pending settlement, expected 2026-07-22).

## Notes
This is the second scheduled tick today (9:50 AM ET cycle already executed
the COIN profit-take and 6 first-time-trade buys). This 3:15 PM ET cycle
found the portfolio essentially frozen: META's 13.7-point drift is the
dominant imbalance but is structurally unfixable under current guardrails
until either its price recovers above the $671.05 breakeven-plus-margin
level or a `forceSell` override is added — the position is underwater
despite being more than 8x its target weight. TQQQ, PLTR, and SPCX face the
same underwater block. With the $9,000 settlement reserve wall exceeding
current buying power net of the cash floor, no organic buying power exists
until the pending COIN sale settles (expected 2026-07-22) or a fresh
legal sell materializes. Zero drawdown breaches, zero cooldown/recovery
clears, zero legal trims, zero deployable cash — a fully quiet cycle.
Per repo convention, this entry is committed to a fresh feature branch and
merged directly into `main` to preserve the unalterable paper trail.

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
