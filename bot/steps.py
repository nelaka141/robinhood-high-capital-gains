"""The ordered CLAUDE.md Execution Sequence, Steps 1-6, as separate functions called in strict
order by main.run_cycle(). Step 7 (journal/state-file writes/git/email) lives in
journal.py / gitops.py / notify.py and is orchestrated from main.py.

Each step function mutates the shared RunContext (models.py) — this mirrors the markdown spec's
own structure section-by-section, so you can read a step's code next to its CLAUDE.md section.
"""
from __future__ import annotations

import math
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from .broker import BrokerClient
from .cost_basis import resolve_avg_cost_basis
from .fifo import fifo_realized_profit, round_sell_quantity
from .indicators import beta, daily_returns, ema_series, rsi_series
from .models import DriftResult, MomentumScore, RunContext, SkippedTrade, TradeIntent
from .state import AlphaReserve, AssetPriceState, load_transferred_basis


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


# ============================================================================================
# Step 1 — Fetch State & Track Trailing Drawdowns
# ============================================================================================

def step1_fetch_state(ctx: RunContext, broker: BrokerClient, repo_dir: str = ".") -> None:
    cfg = ctx.config
    symbols = list(cfg.targets.keys())

    ctx.positions = broker.get_positions(ctx.account_number)
    ctx.quotes = broker.get_quotes(symbols)

    # avg_cost_basis waterfall (primary -> tax-lots -> transferred_basis.json -> fail closed)
    transferred_basis = load_transferred_basis(f"{repo_dir}/transferred_basis.json")
    for sym, pos in ctx.positions.items():
        if sym not in cfg.targets or pos.avg_cost_basis is not None or pos.quantity <= 0:
            continue
        lots = broker.get_tax_lots(ctx.account_number, sym)
        pos.avg_cost_basis = resolve_avg_cost_basis(sym, pos.quantity, None, lots, transferred_basis)
        if pos.avg_cost_basis is None:
            ctx.skipped.append(SkippedTrade(sym, "cost basis pending transfer (fail-closed)", "any sell"))

    # `account_cash`/`current_cash` = buying_power (settled, spendable) — NOT the raw cash ledger.
    ctx.account_cash = broker.get_buying_power(ctx.account_number)
    ctx.account_cash_ledger = broker.get_cash_ledger(ctx.account_number)
    ctx.current_cash = min(
        ctx.account_cash,
        cfg.meta.cap_on_total_cash_balance_to_use + cfg.meta.settlement_reserve_target,
    )

    equity_value = sum(
        (ctx.positions[sym].quantity if sym in ctx.positions else 0.0) * ctx.quotes[sym].last_trade_price
        for sym in symbols
    )
    ctx.account_balance = equity_value + ctx.current_cash

    # --- `blocked` list: exempt from ALL buy/sell this cycle (drawdown audit included), except
    # when the same symbol is ALSO in `forceSell` and currently held — in that one case, liquidate
    # the full position instead of freezing it. Computed before the Drawdown Audit loop below so a
    # blocked (non-exception) symbol is skipped there too, and before has_any_breach() so a
    # blocked+forceSell+held liquidation alone is enough to keep the cycle from taking the NO
    # TRADES early exit.
    for sym in cfg.blocked:
        if sym not in cfg.targets:
            continue  # stale/unknown symbol in the blocked list — nothing to do
        pos = ctx.positions.get(sym)
        held = pos is not None and pos.quantity > 0
        price = ctx.quotes[sym].last_trade_price
        if held and cfg.force_sell_active(sym, price):
            ctx.blocked_symbols[sym] = "blocked, but forceSell + currently held — liquidating full position instead of freezing"
            ctx.blocked_liquidations.append(sym)
        elif held and sym in cfg.force_sell:
            # Listed in forceSell but its triggerPrice hasn't been cleared yet this cycle —
            # stays frozen (not liquidated) until price recovers above the trigger.
            trigger = cfg.force_sell[sym].trigger_price
            ctx.blocked_symbols[sym] = (
                f"blocked; forceSell trigger not yet met (needs price > ${trigger:,.2f}, "
                f"currently ${price:,.2f}) — staying frozen this cycle"
            )
        else:
            ctx.blocked_symbols[sym] = "blocked — exempt from all buy/sell activity this cycle"

    # --- Drawdown Audit: BOTH the peak leg AND the cost-basis leg must breach simultaneously ---
    drawdown_pct = cfg.meta.max_trailing_drawdown_percentage
    for sym in symbols:
        if sym in ctx.blocked_symbols:
            continue  # blocked -> exempt even from the drawdown stop-loss (the forceSell+held
                       # exception is handled unconditionally via blocked_liquidations above)
        pos = ctx.positions.get(sym)
        if not pos or pos.quantity <= 0 or pos.avg_cost_basis is None:
            continue
        st = ctx.price_state.get(sym, AssetPriceState())
        price = ctx.quotes[sym].last_trade_price
        peak = st.peakPrice if st.peakPrice else price  # null peak -> assume current price is the peak
        drop_vs_peak = (peak - price) / peak * 100 if peak else 0.0
        drop_vs_cost = (pos.avg_cost_basis - price) / pos.avg_cost_basis * 100
        if drop_vs_peak >= drawdown_pct and drop_vs_cost >= drawdown_pct:
            ctx.drawdown_liquidations.append(sym)  # overrides target weights + lock_in_period

    # --- Per-asset drift (weight units) ---
    for sym in symbols:
        pos = ctx.positions.get(sym)
        qty = pos.quantity if pos else 0.0
        price = ctx.quotes[sym].last_trade_price
        mv = qty * price
        current_pct = (mv / ctx.account_balance * 100) if ctx.account_balance else 0.0
        actual_weight = current_pct / 100 * cfg.sum_of_weights
        target_weight = cfg.targets[sym].weight
        ctx.drift_results[sym] = DriftResult(
            symbol=sym,
            current_percentage=current_pct,
            actual_weight=actual_weight,
            target_weight=target_weight,
            target_percentage=cfg.target_percentage(sym),
            drift=abs(target_weight - actual_weight),
            asset_drift_tolerance=cfg.drift_tolerance(sym),
            market_value=mv,
        )

    # --- Settlement reserve reconciliation (empirical settle-check is broker-specific; here we
    # trust the `settled` flag the caller/broker maintains on each pending draw) ---
    ctx.reserve.pending_draws = [d for d in ctx.reserve.pending_draws if not d.settled]
    drawn_total = sum(d.reserveDrawn for d in ctx.reserve.pending_draws)
    ctx.reserve_available_to_draw = max(0.0, cfg.meta.settlement_reserve_target - drawn_total)

    # --- Tax reserve: pretrade placeholder (finalized again in Step 6 after this cycle's sells) ---
    year_start = date(ctx.current_date.year, 1, 1)
    ctx.net_realized_gains_ytd_pretrade = broker.get_realized_pnl_ytd(
        ctx.account_number, year_start, ctx.current_date
    )
    prior_years_base = sum(v for y, v in ctx.tax_by_year.items() if int(y) < ctx.current_date.year)
    ctx.tax_reserve = (
        prior_years_base + max(0.0, ctx.net_realized_gains_ytd_pretrade)
    ) * cfg.meta.keep_aside_profits_for_tax_percent / 100


def has_any_breach(ctx: RunContext) -> bool:
    """Step 1's early-exit condition: no breach, no drawdown, and no pending blocked+forceSell
    liquidation -> log status & terminate."""
    return (
        bool(ctx.drawdown_liquidations)
        or bool(ctx.blocked_liquidations)
        or any(d.breached for d in ctx.drift_results.values())
    )


# ============================================================================================
# Step 2 — Rules and Guardrails (in-play exclusions; places no trades itself)
# ============================================================================================

def step2_guardrails(ctx: RunContext) -> None:
    cfg = ctx.config

    for sym in cfg.targets:
        st = ctx.price_state.get(sym, AssetPriceState())
        price = ctx.quotes[sym].last_trade_price

        # Liquidation recovery gate — excludes the symbol from ALL drift/Alpha-Leader play.
        # Only applies while NOT currently held: once repurchased (quantity > 0), the position
        # is back in normal play regardless of a stale liquidatedPrice/liquidatedDate left over
        # from before the repurchase — peak/prices.json has no field that clears these on
        # repurchase (unlike profitSellPrice/profitSellDate for the buy-guard below), so this
        # check must gate on live position state, not just presence of the stored fields.
        pos = ctx.positions.get(sym)
        currently_held = pos is not None and pos.quantity > 0
        if st.liquidatedPrice not in (None, "") and not currently_held:
            liquidated_price = float(st.liquidatedPrice)
            recovered = (
                (price - liquidated_price) / liquidated_price * 100 >= cfg.meta.min_recovery_price_percentage
            )
            liq_date = _parse_date(st.liquidatedDate)
            cooled_down = (
                (ctx.current_date - liq_date).days >= cfg.meta.cool_down_period_after_lquidation
                if liq_date else False
            )
            if not (recovered and cooled_down):
                ctx.excluded_symbols[sym] = (
                    f"liquidated {st.liquidatedDate} @ {liquidated_price} — "
                    f"recovery ({cfg.meta.min_recovery_price_percentage}%) or "
                    f"cooldown ({cfg.meta.cool_down_period_after_lquidation}d) not yet met"
                )
                continue  # nothing more to check — fully excluded

        # Profit-sell buy-guard (v2.41.0: applies uniformly to partial AND full profit-sells).
        # Blocks NEW BUYS only; a partial-sell remainder otherwise stays fully in play.
        if st.profitSellPrice is not None and st.profitSellDate:
            pulled_back = (
                (st.profitSellPrice - price) / st.profitSellPrice * 100
                >= cfg.meta.sold_asset_price_change_percentage
            )
            sell_date = _parse_date(st.profitSellDate)
            cooled_down = (ctx.current_date - sell_date).days >= cfg.meta.sold_asset_repurchase_days
            if not (pulled_back and cooled_down):
                pos = ctx.positions.get(sym)
                is_full_exit = not pos or pos.quantity <= 0
                reason = (
                    f"profit-sold {st.profitSellDate} @ {st.profitSellPrice} — "
                    f"buy-guard active ({'full exit' if is_full_exit else 'partial, remainder still held'})"
                )
                ctx.buy_guarded_symbols[sym] = reason
                if is_full_exit:
                    # Zero position AND buy-guarded => fully out of play, same treatment as a liquidation.
                    ctx.excluded_symbols[sym] = reason

        # Overweight sell profit-margin / lock-in checks are evaluated per-candidate in Step 4,
        # since they only matter for symbols actually being considered for a trim.


def in_play_symbols(ctx: RunContext) -> List[str]:
    return [s for s in ctx.config.targets if s not in ctx.excluded_symbols and s not in ctx.blocked_symbols]


# ============================================================================================
# Step 3 — Calculate Alpha Leader & Apply Re-investment Multiplier
# ============================================================================================

def step3_alpha_leader(ctx: RunContext, broker: BrokerClient) -> Dict[str, float]:
    """Computes Momentum_Score for every in-play symbol, selects the Alpha Leader, and returns
    the PLANNED buy-dollar allocation {symbol: dollars} — Step 6 does the actual placing.
    `multiplier_cash` only materializes if Step 4 harvests real capital via a legal Overweight
    trim; that reconciliation happens in step6_execute, not here (this is a pre-trade estimate,
    same as CLAUDE.md's own "treat as a placeholder" note in Step 1/3).

    Sets `ctx.alpha_target_dollars` — this cycle's full desired Alpha Leader allocation, used by
    `resolve_alpha_reserve` (called after Step 6b) to refresh `alpha_reserve.json` if the leader
    doesn't end up with an actual buy this cycle, for any reason."""
    cfg = ctx.config

    lookback_days = max(30, cfg.meta.momentum_lookback_days + 25)
    end = ctx.current_date - timedelta(days=1)
    start = end - timedelta(days=lookback_days)

    for sym in in_play_symbols(ctx):
        closes = broker.get_daily_closes(sym, start, end)
        rsi = rsi_series(closes, period=14)
        ema = ema_series(closes, period=9)
        ema_now = ema[-1]
        idx_prior = -1 - cfg.meta.momentum_lookback_days
        if len(ema) < abs(idx_prior):
            continue  # not enough history yet for this symbol — skip its score this cycle
        ema_prior = ema[idx_prior]
        price = ctx.quotes[sym].last_trade_price
        ctx.momentum_scores[sym] = MomentumScore(
            symbol=sym,
            rsi14=rsi[-1],
            ema9_now=ema_now,
            ema9_prior=ema_prior,
            price_vs_ema_pct=(price - ema_now) / ema_now * 100,
            ema_slope_pct=(ema_now - ema_prior) / ema_prior * 100,
        )

    if not ctx.momentum_scores:
        return {}
    ctx.alpha_leader = max(ctx.momentum_scores, key=lambda s: ctx.momentum_scores[s].score)

    base_deployable_cash = max(
        0.0,
        ctx.current_cash - cfg.meta.min_cash_absolute - cfg.meta.settlement_reserve_target - ctx.tax_reserve,
    )
    if base_deployable_cash <= 0:
        ctx.alpha_target_dollars = 0.0
        return {}

    raw_alpha_target = base_deployable_cash * cfg.meta.alpha_cash_allocation_percentage / 100
    # This portion of base_deployable_cash is always carved out for the Alpha Leader's benefit —
    # either given to it directly this cycle, or held in the Alpha Reserve for it below — never
    # redirected to Underweight targets (CLAUDE.md Step 3, "Alpha Reserve").
    remaining_for_underweight = base_deployable_cash - raw_alpha_target

    underweight = [
        sym for sym in in_play_symbols(ctx)
        if ctx.drift_results[sym].breached
        and ctx.drift_results[sym].is_underweight
        and sym not in ctx.buy_guarded_symbols
    ]

    def _gap(sym: str) -> float:
        dr = ctx.drift_results[sym]
        return max(0.0, dr.target_percentage / 100 * ctx.account_balance - dr.market_value)

    allocations: Dict[str, float] = {}
    cap_dollars = cfg.meta.max_portfolio_percentage / 100 * ctx.account_balance
    current_mv = ctx.drift_results[ctx.alpha_leader].market_value
    headroom = max(0.0, cap_dollars - current_mv)

    if ctx.alpha_leader in ctx.buy_guarded_symbols:
        # Alpha Leader itself buy-guarded (Step 2's profit-sell guard) -> hold this cycle's
        # would-be allocation aside in the Alpha Reserve instead of giving it to the Alpha
        # Leader OR redirecting it to Underweight targets. steps.resolve_alpha_reserve (called
        # from finalize, once the cycle's final buy list is known) persists this to
        # alpha_reserve.json — always a fresh snapshot of TODAY's target, never cumulative, so
        # it can never exceed what would ever actually be deployable.
        ctx.alpha_target_dollars = min(raw_alpha_target, headroom)
    else:
        # Eligible to buy: this cycle's raw target PLUS whatever was reserved for THIS symbol
        # from a prior cycle it couldn't buy in (CLAUDE.md: "if this asset is Alpha Leader in
        # next day or few it can fill the buys with that cash reserve"). A reserve for a
        # DIFFERENT symbol (stale — the Alpha Leader changed) is simply not applied here; it's
        # released/overwritten by resolve_alpha_reserve once this cycle's outcome is known.
        reserve_bonus = (
            ctx.alpha_reserve.amount
            if ctx.alpha_reserve is not None and ctx.alpha_reserve.symbol == ctx.alpha_leader
            else 0.0
        )
        desired = raw_alpha_target + reserve_bonus
        allocations[ctx.alpha_leader] = max(0.0, min(desired, headroom))
        ctx.alpha_target_dollars = allocations[ctx.alpha_leader]

    total_gap = sum(_gap(s) for s in underweight)
    if total_gap > 0 and remaining_for_underweight > 0:
        for sym in underweight:
            allocations[sym] = allocations.get(sym, 0.0) + remaining_for_underweight * (_gap(sym) / total_gap)

    return allocations


# ============================================================================================
# Step 4 — Evaluate Aggressive Profit-Taking & Reallocation
# ============================================================================================

def step4_profit_taking(ctx: RunContext, broker: BrokerClient) -> None:
    cfg = ctx.config
    fired_today: set = set()

    for sym, pos in ctx.positions.items():
        if sym not in cfg.targets or pos.quantity <= 0 or pos.avg_cost_basis is None:
            continue  # not a target, not held, or cost basis unresolved (fail closed)
        if sym in ctx.blocked_symbols:
            continue  # blocked -> exempt from GET THE PROFITS / Momentum Reversal Trim too;
                       # a forceSell+held exception is liquidated separately via blocked_liquidations

        st = ctx.price_state.get(sym, AssetPriceState())
        price = ctx.quotes[sym].last_trade_price
        raw_gain_pct = (price - pos.avg_cost_basis) / pos.avg_cost_basis * 100
        min_trade_value = cfg.meta.min_value_of_trade
        whole_shares_held = math.floor(pos.quantity + 1e-9)

        # Whole position is itself a sub-whole-share balance (e.g. 0.5 shares left after a
        # fractional buy) -> a specified-lot (tax_lots) sell can NEVER work here, no matter how
        # the lots are chosen: place_equity_order rejects any tax_lots order whose top-level
        # quantity is fractional, and every possible sell target from a <1-share position is
        # fractional by definition. round_sell_quantity would floor this to 0 every time (see its
        # docstring), permanently blocking GET THE PROFITS / Momentum Reversal Trim on this
        # position even though Robinhood happily sells fractional quantities on an ORDINARY
        # (non-specified-lot) order. Fall back to that instead: size the sale in raw fractional
        # shares (uncapped by whole-share rounding), and — down in the TradeIntent construction
        # below — omit `tax_lots` so it goes out as an ordinary order using Robinhood's own
        # default lot matching. `fifo_realized_profit` below still walks the held lots oldest-
        # first for gating purposes, but since those lots aren't shipped to the order, its figure
        # is only an estimate of what Robinhood will actually realize (see CLAUDE.md's own note
        # that default matching isn't guaranteed to be date-ordered FIFO).
        fractional_position = whole_shares_held == 0

        if fractional_position:
            sell_qty = min(pos.quantity, pos.quantity * cfg.meta.profit_sell_percentage / 100)
            if min_trade_value > 0 and sell_qty * price < min_trade_value:
                sell_qty = max(sell_qty, min(pos.quantity, min_trade_value / price))
        else:
            # Rounded to a whole share up front (not after the fact) so the FIFO dollar-gate
            # figure below is computed against the exact quantity that will actually be ordered
            # — see round_sell_quantity's docstring for why the broker requires this.
            sell_qty = round_sell_quantity(pos.quantity * cfg.meta.profit_sell_percentage / 100, pos.quantity)

            # min_value_of_trade: if the profit_sell_percentage slice alone is worth less than
            # the floor, sell additional shares from the same position — up to everything held —
            # to clear it, even past profit_sell_percentage. Checked before the zero-quantity
            # skip below so a slice that rounds to 0 shares still gets a chance to reach the
            # floor.
            #
            # The bump target is computed in two stages, same as profit_sell_percentage's own
            # target above: (1) the exact fractional share count needed, rounded UP to the 3rd
            # decimal (not nearest) so the rounded figure still clears the floor — e.g.
            # min_value_of_trade=$100 at $35/share needs 2.857142... shares; a plain
            # round-to-3-decimals gives 2.857 ($99.995, short), so this rounds up to 2.858
            # ($100.03) instead; then (2) that 3-decimal target is run through
            # round_sell_quantity — the same whole-share lot-rounding fix applied to the
            # profit_sell_percentage target above — since this sale still goes out as a
            # specified-lot (tax_lots) order, which requires a whole-share top-level quantity.
            if min_trade_value > 0 and sell_qty * price < min_trade_value:
                target_3dp = math.ceil(min_trade_value / price * 1000 - 1e-9) / 1000
                sell_qty = max(sell_qty, round_sell_quantity(target_3dp, pos.quantity))

        if sell_qty <= 0:
            ctx.skipped.append(SkippedTrade(
                sym,
                "position is a sub-whole-share balance too small to sell any amount"
                if fractional_position else
                f"profit_sell_percentage of {pos.quantity:.4f} shares rounds to 0 whole shares",
                "partial profit-take sale",
            ))
            continue

        if min_trade_value > 0 and sell_qty * price < min_trade_value:
            held_desc = (
                f"all {pos.quantity:.4f} fractional share(s) held" if fractional_position
                else f"all {whole_shares_held} whole share(s) held"
            )
            ctx.skipped.append(SkippedTrade(
                sym, f"even selling {held_desc} (${sell_qty * price:.2f}) falls short of "
                     f"min_value_of_trade (${min_trade_value:.2f})",
                "partial profit-take sale",
            ))
            continue

        already_today = st.profitSellDate == ctx.current_date.isoformat()
        cooldown_blocks = (
            st.profitSellDate is not None
            and (ctx.current_date - _parse_date(st.profitSellDate)).days <= cfg.meta.profit_resell_cooldown_days
            and price < (st.profitSellPrice if st.profitSellPrice is not None else float("inf"))
        )

        # --- GET THE PROFITS ---
        if not already_today and raw_gain_pct > cfg.meta.materialize_profit_percentage:
            if cooldown_blocks:
                ctx.skipped.append(SkippedTrade(
                    sym, f"GTP % gate clears (+{raw_gain_pct:.2f}%) but profit_resell_cooldown_days active",
                    "partial profit-take sale",
                ))
            else:
                fifo = fifo_realized_profit(broker.get_tax_lots(ctx.account_number, sym), sell_qty, price)
                # Extra dollar-profit floor when the candidate is the CURRENT Alpha Leader —
                # protects it from being sold too cheaply just because a routine sell gate
                # cleared. Checked against the same FIFO-matched realized dollar figure the
                # mechanism's own dollar gate uses (not the raw percentage) — independent of,
                # and typically stricter than, materialize_profit_in_dollars.
                alpha_leader_guard_blocks = (
                    sym == ctx.alpha_leader and fifo.fully_covered
                    and fifo.realized_profit_dollars < cfg.meta.minimum_alpha_leader_sell_profit
                )
                if alpha_leader_guard_blocks:
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        f"GTP gates clear (FIFO ${fifo.realized_profit_dollars:.2f}) but Alpha Leader sell "
                        f"guard blocks (needs >= ${cfg.meta.minimum_alpha_leader_sell_profit:.2f})",
                        "partial profit-take sale",
                    ))
                elif fifo.fully_covered and fifo.realized_profit_dollars > cfg.meta.materialize_profit_in_dollars:
                    reason = f"GET THE PROFITS: +{raw_gain_pct:.2f}%, FIFO ${fifo.realized_profit_dollars:.2f}"
                    if fractional_position:
                        reason += (" (ordinary order — sub-whole-share position, Robinhood "
                                    "default lot matching; FIFO figure is an estimate)")
                    ctx.profit_taking_sells.append(TradeIntent(
                        symbol=sym, side="sell", quantity=sell_qty, reason=reason,
                        tax_lots=None if fractional_position else
                            [{"open_lot_id": l["open_lot_id"], "quantity": l["quantity"]} for l in fifo.lots_consumed],
                        realized_profit_dollars=fifo.realized_profit_dollars,
                        raw_gain_pct=raw_gain_pct,
                    ))
                    fired_today.add(sym)
                    continue  # GTP is exclusive with MRT for the same symbol/cycle
                else:
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        f"GTP % gate clears (+{raw_gain_pct:.2f}%) but FIFO dollar gate fails "
                        f"(${fifo.realized_profit_dollars:.2f} < ${cfg.meta.materialize_profit_in_dollars})",
                        "partial profit-take sale",
                    ))

        # --- MOMENTUM REVERSAL TRIM (independent of GTP; one shared same-day guard) ---
        mscore = ctx.momentum_scores.get(sym)
        if (
            sym not in fired_today and not already_today and mscore is not None
            and mscore.score <= cfg.meta.momentum_reversal_threshold
            and raw_gain_pct >= cfg.meta.momentum_reversal_minimum_profit_margin_percent
        ):
            if cooldown_blocks:
                ctx.skipped.append(SkippedTrade(
                    sym, f"MRT gates clear (score {mscore.score:.2f}) but profit_resell_cooldown_days active",
                    "partial profit-take sale",
                ))
            else:
                fifo = fifo_realized_profit(broker.get_tax_lots(ctx.account_number, sym), sell_qty, price)
                alpha_leader_guard_blocks = (
                    sym == ctx.alpha_leader and fifo.fully_covered
                    and fifo.realized_profit_dollars < cfg.meta.minimum_alpha_leader_sell_profit
                )
                if alpha_leader_guard_blocks:
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        f"MRT gates clear (FIFO ${fifo.realized_profit_dollars:.2f}) but Alpha Leader sell "
                        f"guard blocks (needs >= ${cfg.meta.minimum_alpha_leader_sell_profit:.2f})",
                        "partial profit-take sale",
                    ))
                elif fifo.fully_covered and fifo.realized_profit_dollars > cfg.meta.momentum_reversal_minimum_profit_dollars:
                    reason = f"MOMENTUM REVERSAL TRIM: score {mscore.score:.2f}, FIFO ${fifo.realized_profit_dollars:.2f}"
                    if fractional_position:
                        reason += (" (ordinary order — sub-whole-share position, Robinhood "
                                    "default lot matching; FIFO figure is an estimate)")
                    ctx.profit_taking_sells.append(TradeIntent(
                        symbol=sym, side="sell", quantity=sell_qty, reason=reason,
                        tax_lots=None if fractional_position else
                            [{"open_lot_id": l["open_lot_id"], "quantity": l["quantity"]} for l in fifo.lots_consumed],
                        realized_profit_dollars=fifo.realized_profit_dollars,
                        raw_gain_pct=raw_gain_pct,
                    ))
                    fired_today.add(sym)
                else:
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        f"MRT momentum/margin gates clear but FIFO dollar gate fails "
                        f"(${fifo.realized_profit_dollars:.2f} < ${cfg.meta.momentum_reversal_minimum_profit_dollars})",
                        "partial profit-take sale",
                    ))

    ctx.total_high_beta_gains_realized = sum(t.realized_profit_dollars or 0.0 for t in ctx.profit_taking_sells)

    # --- Overweight High-Beta ranking (routine, non-mandatory trim source) ---
    already_sold = {t.symbol for t in ctx.profit_taking_sells}
    candidates = [
        sym for sym, dr in ctx.drift_results.items()
        if sym in cfg.targets and dr.breached and dr.is_overweight and sym not in already_sold
        and sym not in ctx.blocked_symbols
    ]

    bench = cfg.meta.beta_benchmark_symbol
    lb = cfg.meta.beta_calculation_lookback_days
    end = ctx.current_date - timedelta(days=1)
    start = end - timedelta(days=int(lb * 1.6))
    bench_closes = broker.get_daily_closes(bench, start, end)
    bench_returns = daily_returns(bench_closes)

    ranked: List[TradeIntent] = []
    for sym in candidates:
        pos = ctx.positions[sym]
        st = ctx.price_state.get(sym, AssetPriceState())
        price = ctx.quotes[sym].last_trade_price

        if pos.avg_cost_basis is None:
            ctx.skipped.append(SkippedTrade(
                sym, "cost basis pending transfer (fail-closed)", "Overweight trim",
            ))
            continue

        lp_date = _parse_date(st.lastPurchaseDate)
        locked_in = lp_date is not None and (ctx.current_date - lp_date).days <= cfg.meta.lock_in_period
        if locked_in and sym not in ctx.drawdown_liquidations:
            ctx.skipped.append(SkippedTrade(sym, f"within lock_in_period ({cfg.meta.lock_in_period}d)", "Overweight trim"))
            continue

        margin_pct = (price - pos.avg_cost_basis) / pos.avg_cost_basis * 100
        if margin_pct < cfg.meta.overweight_sell_minimum_profit_margin_percent and not cfg.force_sell_active(sym, price):
            if sym in cfg.force_sell:
                trigger = cfg.force_sell[sym].trigger_price
                reason = (
                    f"underwater ({margin_pct:.2f}% margin); forceSell trigger not yet met "
                    f"(needs price > ${trigger:,.2f}, currently ${price:,.2f})"
                )
            else:
                reason = f"underwater ({margin_pct:.2f}% margin) and not in forceSell"
            ctx.skipped.append(SkippedTrade(sym, reason, "Overweight trim to fund Underweight/Multiplier"))
            continue

        # minimum_alpha_leader_sell_profit is a DOLLAR floor. Overweight-trim sizing isn't
        # determined until later (Step 6 harvests only as much as Underweight/Alpha buys
        # actually need), so at ranking time the best available estimate is the FULL held
        # position's unrealized dollar gain — the ceiling on what this trim could ever realize.
        unrealized_dollars = (price - pos.avg_cost_basis) * pos.quantity
        if (
            sym == ctx.alpha_leader
            and unrealized_dollars < cfg.meta.minimum_alpha_leader_sell_profit
            and not cfg.force_sell_active(sym, price)
        ):
            ctx.skipped.append(SkippedTrade(
                sym,
                f"Alpha Leader sell guard blocks Overweight trim (est. unrealized ${unrealized_dollars:.2f} < "
                f"minimum_alpha_leader_sell_profit ${cfg.meta.minimum_alpha_leader_sell_profit:.2f})",
                "Overweight trim to fund Underweight/Multiplier",
            ))
            continue

        asset_closes = broker.get_daily_closes(sym, start, end)
        asset_returns = daily_returns(asset_closes)
        n = min(len(asset_returns), len(bench_returns))
        b = beta(asset_returns[-n:], bench_returns[-n:]) if n >= 2 else 0.0
        score = margin_pct * b
        ranked.append(TradeIntent(
            symbol=sym, side="sell", reason=f"Overweight High-Beta trim (score {score:.2f})",
            beta=b, raw_gain_pct=margin_pct,
        ))

    ranked.sort(key=lambda t: (t.raw_gain_pct or 0.0) * (t.beta or 0.0), reverse=True)
    ctx.overweight_trims = ranked


# ============================================================================================
# Step 5 — Price Limit & Volatility Halts
# ============================================================================================

def step5_price_limits(ctx: RunContext, broker: BrokerClient, buy_candidates: Dict[str, float]) -> Dict[str, float]:
    """sell_price_diff_limit only exempts ROUTINE Overweight drift-selling (not the mandatory
    GET THE PROFITS / Momentum Reversal Trim sales, already placed into ctx.profit_taking_sells
    and untouched here). buy_price_diff_limit applies to every planned buy."""
    cfg = ctx.config
    n_days = cfg.meta.no_of_days_for_price_compare
    end = ctx.current_date - timedelta(days=1)
    start = end - timedelta(days=n_days * 3)  # pad for weekends/holidays

    filtered_buys: Dict[str, float] = {}
    for sym, dollars in buy_candidates.items():
        bars = broker.get_daily_lows_highs(sym, start, end)[-n_days:]
        price = ctx.quotes[sym].last_trade_price
        if not bars:
            filtered_buys[sym] = dollars
            continue
        low_n = min(l for l, _ in bars)
        pump_pct = (price - low_n) / low_n * 100
        if pump_pct > cfg.meta.buy_price_diff_limit:
            ctx.skipped.append(SkippedTrade(
                sym, f"buy_price_diff_limit: +{pump_pct:.2f}% vs. {n_days}-day low "
                     f"(limit {cfg.meta.buy_price_diff_limit}%)",
                "Underweight/Alpha buy",
            ))
        else:
            filtered_buys[sym] = dollars

    kept_trims: List[TradeIntent] = []
    for intent in ctx.overweight_trims:
        bars = broker.get_daily_lows_highs(intent.symbol, start, end)[-n_days:]
        price = ctx.quotes[intent.symbol].last_trade_price
        if not bars:
            kept_trims.append(intent)
            continue
        high_n = max(h for _, h in bars)
        crash_pct = (high_n - price) / high_n * 100
        if crash_pct > cfg.meta.sell_price_diff_limit:
            ctx.skipped.append(SkippedTrade(
                intent.symbol, f"sell_price_diff_limit: -{crash_pct:.2f}% vs. {n_days}-day high",
                "Overweight trim",
            ))
        else:
            kept_trims.append(intent)
    ctx.overweight_trims = kept_trims

    return filtered_buys


# ============================================================================================
# Step 6 — Execute Sequential Trades
#
# Two flavors are provided:
#   * step6a_prepare_sells / step6b_finalize_buys — PLANNING ONLY, never call
#     broker.place_market_order. This is the snapshot-driven mode (bot/cli.py `plan`/
#     `finalize`): an MCP-connected orchestrator supplies the data and executes the returned
#     order plan itself. Use this when the caller (not this package) owns the broker connection.
#   * step6_execute_live — the original all-in-one version that actually calls
#     broker.place_market_order, for fully-standalone use when bot/ has its own direct broker
#     credentials (see broker.RobinStocksBroker).
# ============================================================================================

def _selling_symbols(ctx: RunContext) -> set:
    """Every symbol with a sell/liquidation firing this cycle — used both to enforce the
    standing same-cycle buy/sell exclusivity rule (CLAUDE.md Step 6) and, in
    step6a_prepare_sells, to filter which planned buys are actually eligible before the
    per-trade seek_approval_value check."""
    return (
        {t.symbol for t in ctx.profit_taking_sells}
        | {t.symbol for t in ctx.overweight_trims}
        | set(ctx.drawdown_liquidations)
        | set(ctx.blocked_liquidations)
    )


def step6a_prepare_sells(
    ctx: RunContext, planned_buys: Optional[Dict[str, float]] = None
) -> tuple[List[TradeIntent], bool, Optional[str]]:
    """Builds the final sell order list (drawdown liquidations + blocked+forceSell liquidations +
    GET THE PROFITS/Momentum Reversal Trim + Overweight High-Beta trims), applies
    sell_or_buy_value_limit, and checks the seek_approval_value halt — evaluated PER INDIVIDUAL
    TRADE (each planned sell, and each planned buy in `planned_buys`), not the old aggregate
    "sum of all sells this cycle" total: a single oversized trade now halts the cycle even if
    the total is small, and a cycle full of many small trades no longer halts just because their
    sum is large.

    `planned_buys` is the provisional buy sizing from step3/step5 (pre-tax-reserve-finalization,
    pre-hard-cap-scaling) — the exact final buy amounts aren't known until step6b runs, which
    only happens after this cycle's sells are confirmed filled, so checking post-finalization
    amounts would mean the sells already executed before an oversized buy could ever halt
    anything. Using the provisional figure here keeps the original "nothing is placed until
    approved" guarantee intact. It's a safe upper bound in practice: step6b only ever scales
    planned buys DOWN (the hard-cap proportional scale) or nudges an under-floor buy UP to
    min_value_of_trade (a few dollars at most, never enough to newly cross seek_approval_value).
    Symbols excluded from buying this cycle (selling the same symbol, or on the `blocked` list)
    are filtered out here too, mirroring step6b's own exclusion, so a buy that will never
    actually be placed can't trigger a halt.

    Returns (sells_to_place, halted, halt_reason). Places nothing.
    """
    cfg = ctx.config
    planned_buys = planned_buys or {}

    liquidations = [
        TradeIntent(symbol=sym, side="sell", quantity=ctx.positions[sym].quantity,
                    reason="Drawdown Audit emergency liquidation (100%)")
        for sym in ctx.drawdown_liquidations if sym in ctx.positions
    ]
    blocked_liquidations = [
        TradeIntent(symbol=sym, side="sell", quantity=ctx.positions[sym].quantity,
                    reason="Blocked + forceSell: liquidating full position (100%)")
        for sym in ctx.blocked_liquidations if sym in ctx.positions
    ]
    all_sells = liquidations + blocked_liquidations + ctx.profit_taking_sells + ctx.overweight_trims

    selling_syms = _selling_symbols(ctx)
    eligible_buys = {
        sym: dollars for sym, dollars in planned_buys.items()
        if sym not in selling_syms and sym not in ctx.blocked_symbols
    }
    oversized = [
        (t.symbol, "sell", (t.quantity or 0.0) * ctx.quotes[t.symbol].last_trade_price)
        for t in all_sells
        if (t.quantity or 0.0) * ctx.quotes[t.symbol].last_trade_price > cfg.meta.seek_approval_value
    ] + [
        (sym, "buy", dollars)
        for sym, dollars in eligible_buys.items()
        if dollars > cfg.meta.seek_approval_value
    ]

    if oversized:
        biggest = max(oversized, key=lambda o: o[2])
        reason = (
            f"{biggest[1]} {biggest[0]} at ${biggest[2]:,.2f} exceeds seek_approval_value "
            f"(${cfg.meta.seek_approval_value:,.2f}) — halting for user approval "
            f"({len(oversized)} individual trade(s) over threshold this cycle)"
        )
        ctx.skipped.append(SkippedTrade("ALL TRADES", reason, "sell+buy batch"))
        return [], True, reason

    sells_to_place = []
    placed_symbols = set()
    for intent in all_sells:
        qty = intent.quantity or 0.0
        value = qty * ctx.quotes[intent.symbol].last_trade_price
        if value < cfg.meta.sell_or_buy_value_limit:
            ctx.skipped.append(SkippedTrade(intent.symbol, "below sell_or_buy_value_limit", "sell"))
            continue
        sells_to_place.append(intent)
        placed_symbols.add(intent.symbol)

    # Keep ctx's per-category sell lists in sync with what actually survived this filter. Before
    # this, ctx.overweight_trims/ctx.profit_taking_sells/ctx.drawdown_liquidations still held
    # every ranked/logged candidate regardless of whether it cleared sell_or_buy_value_limit here
    # — which desynced Step 7's journal (its "N sell(s)" header count and per-section listings
    # counted candidates that were actually skipped) and, for drawdown_liquidations specifically,
    # would have made cli.py's _update_peak_prices mark a never-sold symbol as liquidated.
    ctx.drawdown_liquidations = [s for s in ctx.drawdown_liquidations if s in placed_symbols]
    ctx.blocked_liquidations = [s for s in ctx.blocked_liquidations if s in placed_symbols]
    ctx.profit_taking_sells = [t for t in ctx.profit_taking_sells if t.symbol in placed_symbols]
    ctx.overweight_trims = [t for t in ctx.overweight_trims if t.symbol in placed_symbols]

    return sells_to_place, False, None


def step6b_finalize_buys(
    ctx: RunContext,
    planned_buys: Dict[str, float],
    net_realized_gains_ytd_effective: float,
    buying_power_now: float,
) -> List[TradeIntent]:
    """Given the caller's post-sell realized P&L and fresh buying power (fetched via MCP/broker
    AFTER the Step 6a sells were confirmed filled), finalizes tax_reserve, applies the
    settlement-bridge + hard-cap scaling, and returns the final buy order list. Places nothing.
    """
    cfg = ctx.config

    selling_syms = _selling_symbols(ctx)
    planned_buys = {s: d for s, d in planned_buys.items() if s not in selling_syms and s not in ctx.blocked_symbols}

    ctx.net_realized_gains_ytd_effective = net_realized_gains_ytd_effective
    prior_years_base = sum(v for y, v in ctx.tax_by_year.items() if int(y) < ctx.current_date.year)
    ctx.tax_reserve = (
        prior_years_base + max(0.0, net_realized_gains_ytd_effective)
    ) * cfg.meta.keep_aside_profits_for_tax_percent / 100

    total_planned = sum(planned_buys.values())
    shortfall = max(0.0, total_planned - (buying_power_now - cfg.meta.min_cash_absolute))
    bridged = _apply_settlement_bridge(ctx, shortfall)
    hard_cap = max(0.0, buying_power_now - cfg.meta.min_cash_absolute - ctx.tax_reserve) + bridged

    if total_planned > hard_cap and total_planned > 0:
        scale = hard_cap / total_planned
        planned_buys = {s: d * scale for s, d in planned_buys.items()}

    planned_buys = _enforce_min_trade_value_buys(ctx, planned_buys, cfg.meta.min_value_of_trade)

    buys: List[TradeIntent] = []
    for sym, dollars in planned_buys.items():
        if dollars < cfg.meta.sell_or_buy_value_limit:
            continue
        intent = TradeIntent(symbol=sym, side="buy", dollar_amount=dollars)
        buys.append(intent)
        ctx.buys.append(intent)

    return buys


def resolve_alpha_reserve(ctx: RunContext) -> AlphaReserve:
    """CLAUDE.md's Alpha Reserve (Step 3): call once `ctx.buys` is final (i.e. after
    step6b_finalize_buys has run) to compute what `alpha_reserve.json` should hold for next
    cycle. If the Alpha Leader ended up with an actual buy this cycle, the reserve is spent —
    clear it. Otherwise — for ANY reason it didn't buy (Step 2's buy-guard, a same-cycle sell of
    the same symbol via GET THE PROFITS/Momentum Reversal Trim/Overweight trim, a price-limit
    halt, falling under a dollar floor, hard-cap scaling to zero, ...) — refresh the reserve to
    `ctx.alpha_target_dollars`, tagged to the current Alpha Leader. This is always an overwrite,
    never a sum: a change in Alpha Leader or in the target dollar amount simply replaces
    whatever was stored, exactly matching CLAUDE.md's "if Alpha leader changes or the cash
    amount changes the Alpha reserve also change." Returns the state to persist; the caller
    (bot/cli.py) writes it to alpha_reserve.json."""
    if ctx.alpha_leader is None:
        return ctx.alpha_reserve if ctx.alpha_reserve is not None else AlphaReserve()

    today = ctx.current_date.isoformat()
    bought = any(t.symbol == ctx.alpha_leader for t in ctx.buys)
    if bought:
        return AlphaReserve(symbol=None, amount=0.0, lastUpdatedDate=today)
    return AlphaReserve(symbol=ctx.alpha_leader, amount=ctx.alpha_target_dollars, lastUpdatedDate=today)


def _enforce_min_trade_value_buys(
    ctx: RunContext, planned_buys: Dict[str, float], min_value: float
) -> Dict[str, float]:
    """CLAUDE.md's `min_value_of_trade` control: every buy that survives should be worth at
    least `min_value_of_trade` dollars. Rather than simply dropping anything under the floor (as
    `sell_or_buy_value_limit` already does for genuinely tiny amounts), a buy that's short of the
    floor is bumped up to it by borrowing dollars from lower-priority buys — the Alpha Leader buy
    (if any) is always highest priority, then the rest ranked by their own planned dollar amount
    descending (a bigger amount reflects a bigger drift gap, i.e. more urgent). Lower-priority
    buys are drained from the bottom of that ranking first, cascading: a buy drained below its
    own floor gets its own turn to borrow from whatever is left further down. A buy that still
    can't reach the floor once every lower-ranked buy is exhausted is dropped (logged to
    ctx.skipped) rather than placed under-sized; its dollars simply stay wherever they were
    already redirected to.
    """
    if min_value <= 0 or not planned_buys:
        return planned_buys

    order = sorted(planned_buys, key=lambda s: (s != ctx.alpha_leader, -planned_buys[s]))
    amounts = dict(planned_buys)
    n = len(order)
    for i, sym in enumerate(order):
        val = amounts.get(sym, 0.0)
        if val <= 0 or val >= min_value:
            continue
        shortfall = min_value - val
        for j in range(n - 1, i, -1):
            if shortfall <= 0:
                break
            donor = order[j]
            donor_val = amounts.get(donor, 0.0)
            if donor_val <= 0:
                continue
            take = min(donor_val, shortfall)
            amounts[donor] = donor_val - take
            val += take
            shortfall -= take
        amounts[sym] = val

    result: Dict[str, float] = {}
    for sym in order:
        val = amounts.get(sym, 0.0)
        original = planned_buys.get(sym, 0.0)
        if val >= min_value:
            result[sym] = val
        elif val > 1e-9:
            ctx.skipped.append(SkippedTrade(
                sym, f"below min_value_of_trade (${val:.2f} < ${min_value:.2f}) even after "
                     "borrowing from lower-ranked buys", "buy",
            ))
        elif original > 1e-9:
            ctx.skipped.append(SkippedTrade(
                sym, f"drained to fund a higher-ranked buy's min_value_of_trade floor "
                     f"(started at ${original:.2f})", "buy",
            ))
    return result


def step6_execute_live(ctx: RunContext, broker: BrokerClient, planned_buys: Dict[str, float], dry_run: bool = True) -> None:
    """All-in-one live version: builds sells, places them, re-queries realized P&L and buying
    power from `broker` itself, finalizes and places buys. Only use this when bot/ has its own
    direct broker credentials (broker.RobinStocksBroker or your own BrokerClient) — for the
    snapshot-driven / MCP-orchestrated mode use step6a_prepare_sells + step6b_finalize_buys via
    bot/cli.py instead, which never call broker.place_market_order."""
    sells, halted, _ = step6a_prepare_sells(ctx, planned_buys)
    if halted:
        return

    for intent in sells:
        order = _place(broker, ctx.account_number, intent.symbol, "sell",
                        quantity=intent.quantity, tax_lots=intent.tax_lots, dry_run=dry_run)
        ctx.executed_orders.append(order)

    year_start = date(ctx.current_date.year, 1, 1)
    net_realized_gains_ytd_effective = broker.get_realized_pnl_ytd(ctx.account_number, year_start, ctx.current_date)
    buying_power_now = broker.get_buying_power(ctx.account_number)

    buys = step6b_finalize_buys(ctx, planned_buys, net_realized_gains_ytd_effective, buying_power_now)
    for intent in buys:
        order = _place(broker, ctx.account_number, intent.symbol, "buy",
                        dollar_amount=intent.dollar_amount, dry_run=dry_run)
        ctx.executed_orders.append(order)


def _apply_settlement_bridge(ctx: RunContext, needed: float) -> float:
    """Draws against pre-existing unsettled pending_draws entries (FIFO by saleDate) to bridge
    this cycle's buys, per CLAUDE.md Step 6. Creating a FRESH same-cycle-sell pending_draws
    entry requires knowing that specific sell's settlement status via your broker (e.g.
    review_equity_order / a rejected buy) — that check is broker-specific and is left as a
    TODO for your BrokerClient implementation; this function only bridges pre-existing entries."""
    cfg = ctx.config
    reserve_headroom = max(
        0.0,
        cfg.meta.settlement_reserve_target
        - sum(d.reserveDrawn for d in ctx.reserve.pending_draws if not d.settled)
        - ctx.tax_reserve,
    )
    if reserve_headroom <= 0 or needed <= 0:
        return 0.0

    bridged = 0.0
    for draw in sorted((d for d in ctx.reserve.pending_draws if not d.settled), key=lambda d: d.saleDate):
        if needed - bridged <= 0 or reserve_headroom - bridged <= 0:
            break
        capacity = draw.saleProceeds - draw.reserveDrawn
        take = min(capacity, reserve_headroom - bridged, needed - bridged)
        if take > 0:
            draw.reserveDrawn += take
            bridged += take
    return bridged


def _place(
    broker: BrokerClient, account: str, symbol: str, side: str,
    quantity: Optional[float] = None, dollar_amount: Optional[float] = None,
    tax_lots: Optional[List[dict]] = None, dry_run: bool = True, retries: int = 3,
) -> dict:
    """Places one order. Retries up to 3x with a 60s wait on 429/502 errors only — no other
    retry loop, per CLAUDE.md's Error Handling rule."""
    if dry_run:
        return {
            "symbol": symbol, "side": side, "quantity": quantity, "dollar_amount": dollar_amount,
            "tax_lots": tax_lots, "state": "DRY_RUN",
        }
    for attempt in range(retries + 1):
        try:
            return broker.place_market_order(
                account, symbol, side, dollar_amount=dollar_amount, quantity=quantity, tax_lots=tax_lots,
            )
        except Exception as exc:  # noqa: BLE001 — the specific exception type varies by broker client
            msg = str(exc)
            if attempt < retries and ("429" in msg or "502" in msg):
                time.sleep(60)
                continue
            raise
