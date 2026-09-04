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
from .fifo import (
    fifo_realized_profit,
    priced_lot_quantity,
    profitable_lot_quantity,
    round_sell_quantity,
)
from .indicators import ema_series, rsi_series
from .models import (
    DormantAsset,
    DriftResult,
    FifoSaleResult,
    LossOnlyAsset,
    MomentumScore,
    RunContext,
    SkippedTrade,
    TaxLot,
    TradeIntent,
)
from .state import AssetPriceState, load_transferred_basis

# Lookback for the leg1/leg2/leg3_price_change buy-guard and selling_price_change resell-guard
# (Step 2/4) — matches price_history/daily_bars.json's rolling ~90-day cache, so this reads
# whatever history is already there without requesting a wider window than the cache carries.
_PRICE_CHANGE_LOOKBACK_DAYS = 95


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def _price_change_window(current_date: date) -> tuple[date, date]:
    end = current_date - timedelta(days=1)
    start = end - timedelta(days=_PRICE_CHANGE_LOOKBACK_DAYS)
    return start, end


def _is_loss(ctx: RunContext, sym: str) -> bool:
    """Whether `sym`'s current price sits below its avg_cost_basis — used to decide whether a
    liquidation/trim should arm the wash-sale buy-guard (ctx.loss_sale_symbols). Fails closed
    (False, i.e. not flagged as a loss) if cost basis is unresolved — same "can't evaluate ->
    don't assume" posture as the rest of the cost-basis-dependent gates."""
    pos = ctx.positions.get(sym)
    if not pos or pos.avg_cost_basis is None:
        return False
    return ctx.quotes[sym].last_trade_price < pos.avg_cost_basis


def _weighted_avg_lot_age_days(lots_consumed: List[dict], lots: List[TaxLot], current_date: date) -> float:
    """Quantity-weighted average age (in days) of the SPECIFIC lots a GET THE PROFITS sale
    actually consumes (`fifo.lots_consumed`, already post loss-lot exclusion) — v2.78.0's dynamic
    profit-threshold ramp measures "how long the profit-making lots have been held" against
    exactly this population, not the position's full lot history or its unconsumed lots.
    Returns 0.0 (the day-0 floor of the ramp) if there's nothing to weight, e.g. a not-fully-
    covered FIFO walk that consumed no lots — that case is already handled as a fail-closed skip
    by the caller regardless of what this returns."""
    if not lots_consumed:
        return 0.0
    open_dates = {lot.open_lot_id: lot.open_date for lot in lots}
    total_qty = sum(c["quantity"] for c in lots_consumed)
    if total_qty <= 0:
        return 0.0
    weighted_days = sum(
        c["quantity"] * (current_date - open_dates[c["open_lot_id"]]).days
        for c in lots_consumed
    )
    return weighted_days / total_qty


def _dynamic_profit_threshold(base: float, max_value: float, ramp_days: float, days_held: float) -> float:
    """v2.78.0: parabolic ramp from `base` (day 0) up to `max_value` (reached at `ramp_days` and
    held flat beyond it) — threshold(days) = base + (max_value - base) * min(1, days/ramp_days)**2.
    Applies independently to each leg of GET THE PROFITS' percent/dollar OR-gate; `ramp_days<=0`
    degenerates to the max (no ramp at all, i.e. always at the cap)."""
    if ramp_days <= 0:
        return max_value
    t = min(1.0, max(0.0, days_held) / ramp_days)
    return base + (max_value - base) * t * t


def _compute_tax_reserve(
    prior_years_base: float, current_year_gains: float, percent: float, total_paid_taxes: float
) -> float:
    """v2.80.0: `tax/paid_taxes_by_year.json` — the percentage-based reserve (unchanged formula:
    (prior_years_base + max(0, current_year_gains)) * percent / 100) is reduced dollar-for-dollar
    by every year's recorded actual tax payment, summed across ALL years on file (not just the
    current one — the underlying base already blends prior years and the current year together
    before applying `percent`, so paid taxes are netted out the same way). Floored at 0 — already-
    paid taxes can shrink the reserve to nothing, never go negative. `total_paid_taxes` is the
    sum of every entry in paid_taxes_by_year.json; see state.load_paid_taxes_by_year."""
    gross = (prior_years_base + max(0.0, current_year_gains)) * percent / 100
    return max(0.0, gross - total_paid_taxes)


def _sell_price_target_blocked(ctx: RunContext, sym: str, price: float, mechanism: str) -> bool:
    """target_price_to_sell (CLAUDE.md): blocks a sale that would otherwise fire, by ANY
    mechanism — including the emergency Drawdown Audit stop-loss and
    a blocked+forceSell liquidation, not just the routine profit-taking path — until
    `price` crosses (reaches or exceeds) the configured floor. Only call this once the caller has
    already determined the mechanism WOULD otherwise fire, so a SkippedTrade is only logged when
    it actually changes the outcome, not for every symbol that merely has a configured target."""
    if not ctx.config.sell_price_target_blocks(sym, price):
        return False
    target = ctx.config.target_price_to_sell[sym]
    ctx.skipped.append(SkippedTrade(
        sym,
        f"target_price_to_sell (${target:,.2f}) not yet crossed (current price ${price:,.2f})",
        mechanism,
    ))
    return True


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

    # `account_cash`/`current_cash` = buying_power — NOT the raw cash ledger. With limited margin
    # enabled on this account, buying_power already reflects unsettled sale proceeds immediately,
    # so no settlement-reserve buffer/bridging is needed.
    ctx.account_cash = broker.get_buying_power(ctx.account_number)
    ctx.account_cash_ledger = broker.get_cash_ledger(ctx.account_number)
    ctx.current_cash = min(ctx.account_cash, cfg.meta.cap_on_total_cash_balance_to_use)

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
        if held and cfg.force_sell_active(sym, price) and cfg.sell_price_target_blocks(sym, price):
            # target_price_to_sell overrides even forceSell+blocked — "by any means" — so this
            # liquidation stays frozen instead of firing until price crosses the floor.
            target = cfg.target_price_to_sell[sym]
            ctx.blocked_symbols[sym] = (
                f"blocked + forceSell active, but target_price_to_sell (${target:,.2f}) not yet "
                f"crossed (currently ${price:,.2f}) — staying frozen this cycle"
            )
        elif held and cfg.force_sell_active(sym, price):
            ctx.blocked_symbols[sym] = "blocked, but forceSell + currently held — liquidating full position instead of freezing"
            ctx.blocked_liquidations.append(sym)
            if _is_loss(ctx, sym):
                ctx.loss_sale_symbols.append(sym)
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
            if _sell_price_target_blocked(ctx, sym, price, "Drawdown Audit liquidation"):
                continue  # target_price_to_sell overrides even this emergency stop — "any means"
            ctx.drawdown_liquidations.append(sym)  # overrides target weights + lock_in_period
            ctx.loss_sale_symbols.append(sym)  # drop_vs_cost >= drawdown_pct guarantees a loss

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

    # --- Tax reserve: pretrade placeholder (finalized again in Step 6 after this cycle's sells) ---
    year_start = date(ctx.current_date.year, 1, 1)
    ctx.net_realized_gains_ytd_pretrade = broker.get_realized_pnl_ytd(
        ctx.account_number, year_start, ctx.current_date
    )
    prior_years_base = sum(v for y, v in ctx.tax_by_year.items() if int(y) < ctx.current_date.year)
    total_paid_taxes = sum(ctx.paid_taxes_by_year.values())
    ctx.tax_reserve = _compute_tax_reserve(
        prior_years_base, ctx.net_realized_gains_ytd_pretrade,
        cfg.meta.keep_aside_profits_for_tax_percent, total_paid_taxes,
    )


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

def step2_guardrails(ctx: RunContext, broker: BrokerClient) -> None:
    cfg = ctx.config
    hist_start, hist_end = _price_change_window(ctx.current_date)

    for sym in cfg.targets:
        st = ctx.price_state.get(sym, AssetPriceState())
        price = ctx.quotes[sym].last_trade_price

        # Liquidation recovery gate — excludes the symbol from ALL drift/rebalance play.
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

        # Buy-timing guard (v2.71.0: UNIVERSAL — applies to every in-play symbol before ANY buy
        # this cycle, not just a profit-sell repurchase: an
        # Underweight allocation and a profit-sell repurchase are both gated by the same
        # three-leg dip-then-turn confirmation. v2.41.0: the profit-sell-specific cooldown
        # (sold_asset_repurchase_days) still applies uniformly to partial AND full profit-sells,
        # but only when the symbol actually HAS a recorded profit-sell — it's meaningless without
        # one and never blocks a never-sold symbol. v2.72.0: the pullback check compares raw
        # daily-close percentage price changes directly (against the live current price as the
        # denominator) instead of Z-scores — see leg1_price_change / leg2_price_change /
        # leg3_price_change.
        closes = broker.get_daily_closes(sym, hist_start, hist_end)
        # closes[-1] is yesterday (ascending-date, cache trails one session), so 1 trading
        # session further back is closes[-2], and 2 sessions further back is closes[-3].
        close_yesterday = closes[-1] if closes else None
        close_1day_back = closes[-2] if len(closes) >= 2 else None
        close_2day_back = closes[-3] if len(closes) >= 3 else None
        leg1_change = (
            (close_2day_back - close_1day_back) * 100 / price
            if close_2day_back is not None and close_1day_back is not None else None
        )
        leg2_change = (
            (close_1day_back - close_yesterday) * 100 / price
            if close_1day_back is not None and close_yesterday is not None else None
        )
        leg3_change = (
            (price - close_yesterday) * 100 / price
            if close_yesterday is not None else None
        )
        # Missing/insufficient history fails closed — pulled_back stays False (guard active)
        # rather than silently letting a symbol we can't evaluate slip back into play.
        # Three-part confirmation: (1) an earlier downward leg already happened between 2
        # sessions back and 1 session back (close_2day_back well above close_1day_back), AND (2)
        # a real dip continued between the session before yesterday and yesterday (close_1day_back
        # well above close_yesterday), AND (3) today shows the price ticking back up off that dip
        # (today's live price above close_yesterday by at least the smaller leg3_price_change
        # bar) — i.e. wait for a confirmed downtrend AND the start of a turn, not just "still
        # below where it was." All three legs are measured as a percentage of the live current
        # price, so they're directly comparable regardless of the symbol's own price level.
        pulled_back = (
            leg1_change is not None and leg2_change is not None and leg3_change is not None
            and leg1_change > cfg.meta.leg1_price_change
            and leg2_change > cfg.meta.leg2_price_change
            and leg3_change > cfg.meta.leg3_price_change
        )
        cooled_down = True
        days_since_sell: Optional[int] = None
        if st.profitSellDate:
            sell_date = _parse_date(st.profitSellDate)
            days_since_sell = (ctx.current_date - sell_date).days if sell_date else 0
            cooled_down = days_since_sell >= cfg.meta.sold_asset_repurchase_days
        if not (pulled_back and cooled_down):
            pos = ctx.positions.get(sym)
            is_full_exit = st.profitSellPrice is not None and (not pos or pos.quantity <= 0)
            # Report exactly which sub-condition hasn't cleared yet, so the journal/email
            # doesn't just say "buy-guard active" with no way to tell whether it's waiting on
            # the calendar, the earlier dip, the dip, or the upturn.
            unmet: List[str] = []
            if st.profitSellDate and not cooled_down:
                unmet.append(
                    f"cooldown not met ({days_since_sell}d/{cfg.meta.sold_asset_repurchase_days}d "
                    f"required)"
                )
            if leg1_change is None or leg2_change is None or leg3_change is None:
                unmet.append("insufficient price history to compute leg price changes")
            else:
                if not (leg1_change > cfg.meta.leg1_price_change):
                    unmet.append(
                        f"earlier dip not confirmed (leg1 close_2d_back→close_1d_back change="
                        f"{leg1_change:+.3f}%, need > {cfg.meta.leg1_price_change:.3f}%)"
                    )
                if not (leg2_change > cfg.meta.leg2_price_change):
                    unmet.append(
                        f"dip not confirmed (leg2 close_1d_back→close_yesterday change="
                        f"{leg2_change:+.3f}%, need > {cfg.meta.leg2_price_change:.3f}%)"
                    )
                if not (leg3_change > cfg.meta.leg3_price_change):
                    unmet.append(
                        f"upturn not confirmed (leg3 close_yesterday→today change="
                        f"{leg3_change:+.3f}%, need > {cfg.meta.leg3_price_change:.3f}%)"
                    )
            if st.profitSellPrice is not None and st.profitSellDate:
                prefix = (
                    f"Profit-sell buy-guard: profit-sold {st.profitSellDate} @ {st.profitSellPrice} "
                    f"({'full exit' if is_full_exit else 'partial, remainder still held'})"
                )
            else:
                prefix = "Buy-timing guard"
            reason = f"{prefix} — blocked because: {'; '.join(unmet)}"
            # Gates every new buy of this symbol this cycle — an Underweight allocation and a
            # same-symbol profit-sell repurchase alike.
            ctx.buy_guarded_symbols.setdefault(sym, []).append(reason)
            if is_full_exit:
                # Zero position AND buy-guarded on a recorded profit-sell => fully out of play,
                # same treatment as a liquidation. A never-sold symbol that merely fails the
                # buy-timing pattern stays fully in play for everything except new buys.
                ctx.excluded_symbols[sym] = reason

        # Wash-sale buy-guard: blocks a NEW BUY of this symbol for wash_sale_lookback_days after
        # ANY sell that realized a loss (Drawdown Audit or blocked+forceSell liquidation — see
        # ctx.loss_sale_symbols in Step 1) — independent of, and can stack with, the buy-timing
        # guard above (a symbol could carry both an old profitSellDate and a newer
        # lastLossSaleDate). Deliberately date-only (no price-change/recovery condition, unlike
        # the buy-timing guard) — the IRS wash-sale rule is a flat calendar window, not a
        # momentum/price test. Does NOT block the emergency stop itself from firing (the Drawdown
        # Audit stays unconditional, CLAUDE.md Step 1) — it only blocks the REPURCHASE afterward,
        # which is where the actual wash-sale risk lives for an active trading bot.
        if st.lastLossSaleDate:
            sell_date = _parse_date(st.lastLossSaleDate)
            days_since = (ctx.current_date - sell_date).days if sell_date else 0
            if days_since <= cfg.meta.wash_sale_lookback_days:
                reason = (
                    f"Wash-sale buy-guard: sold at a loss {st.lastLossSaleDate} @ {st.lastLossSalePrice} — "
                    f"blocked until {cfg.meta.wash_sale_lookback_days}d have passed "
                    f"({days_since}d so far)"
                )
                ctx.buy_guarded_symbols.setdefault(sym, []).append(reason)

        # Buy price target gate (target_price_to_buy): blocks a NEW BUY of this symbol — an
        # Underweight allocation or a profit-sell repurchase alike ("by any means") — while
        # `price` is still above the configured ceiling.
        if cfg.buy_price_target_blocks(sym, price):
            target = cfg.target_price_to_buy[sym]
            reason = (
                f"target_price_to_buy (${target:,.2f}) not yet met (current price ${price:,.2f}) "
                f"— blocked from any buy"
            )
            ctx.buy_guarded_symbols.setdefault(sym, []).append(reason)


def in_play_symbols(ctx: RunContext) -> List[str]:
    return [s for s in ctx.config.targets if s not in ctx.excluded_symbols and s not in ctx.blocked_symbols]


# ============================================================================================
# Step 3 — Rank Underweight Targets by Momentum_Score & Size Buys (top-down full fills)
# ============================================================================================

def step3_underweight_buys(ctx: RunContext, broker: BrokerClient) -> Dict[str, float]:
    """Computes Momentum_Score for every in-play symbol, then sizes this cycle's buys: the
    qualifying Underweight candidates are ranked by Momentum_Score descending and filled
    TOP-DOWN, each to its FULL drift gap (target_percentage/100 * account_balance − market
    value) — NOT pro-rated or momentum-weighted — until `base_deployable_cash` runs out.
    Returns the PLANNED buy-dollar allocation {symbol: dollars} — Step 6 does the actual placing.

    A candidate must be in-play, drift-breached, Underweight, not buy-guarded (every Step 2 buy
    guard applies to every buy — buy-timing legs, sold_asset_repurchase_days, wash-sale window,
    target_price_to_buy), and clear `min_momentum_score_to_fill_underweight` on its
    Momentum_Score. A candidate below that floor — or with no computable score — is fully
    excluded this cycle (logged SKIPPED).

    Each fill is capped by `_headroom()` — the asset's own `max_allocation_percent` override if
    set, else the global `max_portfolio_percentage` — so a symbol's total planned allocation can
    never push its market value past its per-asset concentration cap. A lower-ranked candidate
    is only funded from whatever cash the higher-ranked fills left over; once cash is exhausted,
    every remaining candidate is logged SKIPPED. Buys are funded from deployable cash only —
    there is no Overweight-trim harvesting to raise extra cash (sells are GET THE PROFITS only).

    Finally, every allocation is subject to `max_sector_percentage` — see the sector-cap pass at
    the end of this function — so a single correlated theme (`sector_groups` in
    portfolio_targets.json) can't be over-concentrated across several simultaneously-funded
    symbols even when each individually clears `max_portfolio_percentage`. Dollars removed by
    the sector cap are NOT redistributed to other candidates (same "no re-allocation" principle
    as every downstream gate)."""
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

    def _headroom(sym: str) -> float:
        """Dollar room left before `sym`'s market value (existing holdings + this cycle's
        planned buy) would exceed its per-asset concentration cap — the asset's own
        `max_allocation_percent` override if set in portfolio_targets.json, else the global
        `max_portfolio_percentage` default (`cfg.max_allocation_percentage`)."""
        cap_dollars = cfg.max_allocation_percentage(sym) / 100 * ctx.account_balance
        current_mv = ctx.drift_results[sym].market_value
        return max(0.0, cap_dollars - current_mv)

    base_deployable_cash = max(0.0, ctx.current_cash - cfg.meta.min_cash_absolute - ctx.tax_reserve)
    if base_deployable_cash <= 0:
        return {}

    # A candidate must clear min_momentum_score_to_fill_underweight to be considered at all —
    # a symbol below the floor (or with no computable Momentum_Score) is fully excluded from
    # the Underweight fill this cycle (CLAUDE.md Step 3).
    momentum_floor = cfg.meta.min_momentum_score_to_fill_underweight
    underweight: List[str] = []
    for sym in in_play_symbols(ctx):
        dr = ctx.drift_results[sym]
        if not (dr.breached and dr.is_underweight):
            continue
        if sym in ctx.buy_guarded_symbols:
            continue  # every Step 2 buy guard applies to every buy
        score = ctx.momentum_scores[sym].score if sym in ctx.momentum_scores else None
        if score is None or score < momentum_floor:
            reason = (
                f"Momentum_Score ({score:.2f}) below min_momentum_score_to_fill_underweight "
                f"({momentum_floor:.2f})" if score is not None
                else f"no Momentum_Score available (below min_momentum_score_to_fill_underweight "
                     f"floor of {momentum_floor:.2f})"
            )
            ctx.skipped.append(SkippedTrade(sym, reason, "Underweight buy"))
            continue
        underweight.append(sym)

    # Rank the qualifying candidates by Momentum_Score descending — the fill order.
    underweight.sort(key=lambda s: ctx.momentum_scores[s].score, reverse=True)

    def _gap(sym: str) -> float:
        dr = ctx.drift_results[sym]
        return max(0.0, dr.target_percentage / 100 * ctx.account_balance - dr.market_value)

    # --- Top-down full fills: walk the ranking, giving each candidate its FULL drift gap
    # (capped by its own per-asset headroom) out of whatever deployable cash remains. Not
    # pro-rated: a higher-momentum candidate is fully funded before the next one gets anything,
    # and once cash runs out every remaining candidate simply waits for a future cycle.
    allocations: Dict[str, float] = {}
    remaining_cash = base_deployable_cash
    for sym in underweight:
        ask = min(_gap(sym), _headroom(sym))
        if ask <= 0:
            continue  # gap already closed, or no headroom under the per-asset cap
        if remaining_cash <= 1e-9:
            ctx.skipped.append(SkippedTrade(
                sym,
                "deployable cash exhausted by higher-ranked (higher Momentum_Score) "
                "Underweight fills",
                "Underweight buy",
            ))
            continue
        dollars = min(ask, remaining_cash)
        allocations[sym] = dollars
        remaining_cash -= dollars

    # --- Position Cap Top-Up (v2.80.0) — a SECOND, independent use of whatever deployable cash
    # the top-down fill above left unspent. Any target symbol with a configured
    # `max_position_value` (a flat dollar cap on its own market value, set alongside `weight`/
    # `drift` in portfolio_targets.json) is topped up toward that cap — regardless of whether it
    # was Underweight or drift-breached, since the whole point is to deploy cash a symbol's normal
    # weight-based drift gap wouldn't otherwise reach. Still gated by every universal buy guard
    # (in-play, not blocked, not buy-guarded — the same Step 2 guards that apply to every buy) and
    # by the SAME per-asset (`max_allocation_percent`/`max_portfolio_percentage`) headroom the
    # top-down fill above respects, so this can never push a symbol's concentration past its
    # existing percent-of-account_balance cap even if `max_position_value` itself is set higher
    # than that cap implies.
    #
    # v2.81.0: two more guards, both closing gaps the dry-run of the $6,000 global default
    # surfaced — Top-Up was routing real dollars into the WORST-ranked and even loss-making
    # candidates simply because they had leftover room under the cap:
    #   - `min_momentum_score_to_fill_underweight` now applies to Top-Up too, same floor and same
    #     "no computable score fails closed" posture as the top-down fill above.
    #   - A symbol already held (any quantity > 0) whose current price sits below its
    #     `avg_cost_basis` is excluded — don't add fresh dollars to a position that's already
    #     losing money just to chase the dollar cap. An unresolved cost basis fails closed too
    #     (can't prove it isn't a loss), same posture as every other cost-basis-dependent gate in
    #     this document.
    #
    # Multiple candidates share the leftover cash pro-rata by `weight` (water-filling: repeatedly
    # split whatever's left proportionally, remove any candidate that hits its own room this
    # round, and repeat with what's left over among the rest) so a candidate with little room
    # doesn't get skipped just because it comes second in an arbitrary iteration order, and a
    # candidate with lots of room doesn't starve the others by claiming everything in one pass.
    leftover_cash = max(0.0, remaining_cash)
    if leftover_cash > 1e-9:
        topup_candidates: Dict[str, tuple[float, float]] = {}  # symbol -> (room, weight)
        for sym, target in cfg.targets.items():
            cap = cfg.resolved_max_position_value(sym)  # own override, else global default_max_position_value
            if cap is None:
                continue
            if sym in ctx.excluded_symbols or sym in ctx.blocked_symbols or sym in ctx.buy_guarded_symbols:
                continue
            if sym not in ctx.drift_results:
                continue

            score = ctx.momentum_scores[sym].score if sym in ctx.momentum_scores else None
            if score is None or score < momentum_floor:
                reason = (
                    f"Position Cap Top-Up: Momentum_Score ({score:.2f}) below "
                    f"min_momentum_score_to_fill_underweight ({momentum_floor:.2f})" if score is not None
                    else "Position Cap Top-Up: no Momentum_Score available (below "
                         f"min_momentum_score_to_fill_underweight floor of {momentum_floor:.2f})"
                )
                ctx.skipped.append(SkippedTrade(sym, reason, "Position Cap Top-Up"))
                continue

            pos = ctx.positions.get(sym)
            if pos is not None and pos.quantity > 0:
                price = ctx.quotes[sym].last_trade_price
                if pos.avg_cost_basis is None or price < pos.avg_cost_basis:
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        "Position Cap Top-Up: held position is at a loss (or cost basis "
                        "unresolved) vs. avg_cost_basis — excluded from top-up",
                        "Position Cap Top-Up",
                    ))
                    continue

            current_mv = ctx.drift_results[sym].market_value + allocations.get(sym, 0.0)
            room = min(
                cap - current_mv,
                _headroom(sym) - allocations.get(sym, 0.0),
            )
            if room > 1e-9:
                topup_candidates[sym] = (room, target.weight)
            else:
                ctx.skipped.append(SkippedTrade(
                    sym,
                    f"Position Cap Top-Up: no room left toward max_position_value "
                    f"(${cap:,.2f}) or per-asset concentration cap",
                    "Position Cap Top-Up",
                ))

        active = dict(topup_candidates)
        while leftover_cash > 1e-9 and active:
            total_weight = sum(w for _, w in active.values())
            if total_weight <= 0:
                break
            capped_this_round = []
            spent_this_round = 0.0
            for sym, (room, weight) in list(active.items()):
                give = min(leftover_cash * weight / total_weight, room)
                if give <= 0:
                    continue
                allocations[sym] = allocations.get(sym, 0.0) + give
                ctx.position_cap_topups[sym] = ctx.position_cap_topups.get(sym, 0.0) + give
                spent_this_round += give
                room -= give
                if room <= 1e-9:
                    capped_this_round.append(sym)
                else:
                    active[sym] = (room, weight)
            leftover_cash -= spent_this_round
            for sym in capped_this_round:
                del active[sym]
            if not capped_this_round:
                break  # every candidate's share was fully absorbed without hitting a cap — done

    # --- Sector/theme concentration cap (max_sector_percentage) — final pass over the complete
    # allocations dict (top-down fill AND Position Cap Top-Up alike). For each sector_groups
    # member group whose PROJECTED total (current market
    # value + everything planned above) would exceed the group's cap percentage of
    # account_balance, scale every member's planned dollars down proportionally so the group's
    # projected total lands exactly at the cap. Symbols in no group are entirely unaffected.
    # Capped-away dollars are NOT redistributed to other groups or candidates — the money simply
    # isn't spent this cycle, the same graceful-degradation behavior as any other downstream gate.
    for group, sector in cfg.sector_groups.items():
        cap_pct = cfg.sector_cap_percentage(group)  # group's own maxPercentage override, else global
        if cap_pct <= 0:
            continue
        members = sector.members
        planned = sum(allocations.get(s, 0.0) for s in members)
        if planned <= 0:
            continue
        sector_cap_dollars = cap_pct / 100 * ctx.account_balance
        current_mv = sum(
            ctx.drift_results[s].market_value for s in members if s in ctx.drift_results
        )
        projected = current_mv + planned
        if projected <= sector_cap_dollars:
            continue
        headroom = max(0.0, sector_cap_dollars - current_mv)
        scale = headroom / planned
        for s in members:
            if s in allocations:
                allocations[s] *= scale
            if s in ctx.position_cap_topups:
                # Keep the reporting-only breakdown in sync with what actually survived the
                # sector cap, same reasoning as the top-down fill's own allocations.
                ctx.position_cap_topups[s] *= scale

    return allocations


# ============================================================================================
# Step 4 — Evaluate Aggressive Profit-Taking (GET THE PROFITS — the only routine sell mechanism)
# ============================================================================================

def step4_profit_taking(ctx: RunContext, broker: BrokerClient) -> None:
    cfg = ctx.config
    hist_start, hist_end = _price_change_window(ctx.current_date)

    for sym, pos in ctx.positions.items():
        if sym not in cfg.targets or pos.quantity <= 0 or pos.avg_cost_basis is None:
            continue  # not a target, not held, or cost basis unresolved (fail closed)
        if sym in ctx.blocked_symbols:
            continue  # blocked -> exempt from GET THE PROFITS too;
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
        # docstring), permanently blocking GET THE PROFITS on this
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

        # --- Loss-lot sell guard (v2.75.0) ---
        # A multi-lot sale walks lots in FIFO order, so a position built at rising cost can hand
        # an underwater lot to the order purely because it is next in line — realizing a loss on
        # that lot even though the sale as a whole clears the profit gates. Exclude any lot that
        # would not realize a strict gain at today's price and proceed on the profitable ones.
        #
        # Ordering matters here. The pending-basis check comes FIRST and is left alone: if the
        # target exceeds the priced+selectable quantity, some shares' basis is still syncing, and
        # CLAUDE.md's Fail-Closed rule requires the sale to be skipped outright — NOT silently
        # downsized to whatever happens to be priced. Only when basis is fully available does the
        # loss-lot cap apply, so the two rules stay independent.
        lots = broker.get_tax_lots(ctx.account_number, sym)

        # --- Zero-available-lots fallback (v2.79.0) ---
        # The Fail-Closed pending-basis rule (below, via `fifo.fully_covered`) exists for a
        # PARTIAL shortfall — some lots priced, some not, not enough to cover the sale target —
        # where downsizing to whatever's priced would produce a guessed figure. It should NOT
        # extend to the all-or-nothing case where LITERALLY ZERO of this symbol's lots are
        # priced+selectable yet — but ONLY when that's genuinely same-day lot-sync latency, not
        # a stale/unresolved position. Concretely, this requires BOTH:
        #   1. every one of the symbol's lots is dated TODAY (open_date == ctx.current_date) —
        #      distinguishes "bought this morning, still syncing" from an older position whose
        #      lots simply never finished syncing (a genuine data problem that should stay
        #      fail-closed, not be papered over with an estimate); and
        #   2. avg_cost_basis is resolved — already guaranteed by this function's own entry
        #      check (`pos.avg_cost_basis is None: continue`, above), so no separate test is
        #      needed here, but it's worth spelling out why this fallback can never fire for a
        #      same-day TRANSFERRED position with no basis yet: a transfer's cost basis can only
        #      come from `transferred_basis.json` (Step 1's override waterfall) or from the lots
        #      themselves — if neither has resolved same-day, avg_cost_basis stays None and the
        #      entry check above already excludes the symbol before this code ever runs, so
        #      there's no profit figure to estimate from in the first place.
        # There's no lot data to shortchange in case 1, so rather than block a same-day round-
        # trip purely on lot-sync latency (nothing in CLAUDE.md's rules gates GET THE PROFITS on
        # holding period — lock_in_period is inert for it), fall back to an ORDINARY order
        # exactly like the sub-whole-share fallback above: omit `tax_lots`, let Robinhood's own
        # default matching decide what's disposed (not guaranteed date-ordered FIFO — same
        # caveat as that fallback), and gate the dollar leg off `(price - avg_cost_basis) *
        # sell_qty` since there's no lot-level cost data to walk. avg_cost_basis is already
        # independently known via Step 1's primary source (average_buy_price, populated on fill)
        # even when every lot is still unselectable.
        # Scoped narrowly: the moment even ONE lot is priced+selectable, OR any of the symbol's
        # lots is dated before today (a same-day buy sitting alongside an older, still-pending
        # transfer, say), this fallback does not apply and the existing Fail-Closed skip governs
        # unchanged (see `fifo.fully_covered` below) — a genuine partial-sync or multi-day-stale
        # shortfall still fails closed rather than being downsized or guessed at.
        no_lots_available = (
            bool(lots)
            and priced_lot_quantity(lots) <= 1e-9
            and all(lot.open_date == ctx.current_date for lot in lots)
        )

        loss_excluded_qty = 0.0
        if not no_lots_available and sell_qty <= priced_lot_quantity(lots) + 1e-9:
            capped_qty = min(sell_qty, profitable_lot_quantity(lots, price))
            if not fractional_position:
                # A specified-lot order still needs a whole-share TOTAL (round_sell_quantity's
                # docstring), and the cap can only ever move the quantity down, so floor rather
                # than round — rounding up could re-admit an excluded loss lot.
                capped_qty = math.floor(capped_qty + 1e-9)
            if capped_qty < sell_qty - 1e-9:
                loss_excluded_qty = sell_qty - capped_qty
                sell_qty = capped_qty

        if sell_qty <= 0:
            ctx.skipped.append(SkippedTrade(
                sym,
                f"loss-lot sell guard: every sellable lot is at or above the current price "
                f"(${price:.2f}) — nothing can be sold at a gain",
                "partial profit-take sale",
            ))
            continue

        if min_trade_value > 0 and sell_qty * price < min_trade_value:
            if loss_excluded_qty > 0:
                held_desc = (
                    f"all {sell_qty:.4f} profitable share(s) "
                    f"({loss_excluded_qty:.4f} excluded by the loss-lot sell guard)"
                )
            else:
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
        # v2.65.0: purely a flat calendar-day check — the earlier Z-score recovery leg
        # (pre-v2.70.0's z_score_sell_points) was removed; profit_resell_cooldown_days is now the
        # sole guard, paired only with each mechanism's own percentage/dollar gate above.
        # v2.69.0: strict "<" — only a gap strictly less than the cooldown window blocks; a gap
        # exactly equal to profit_resell_cooldown_days now clears.
        cooldown_blocks = (
            st.profitSellDate is not None
            and (ctx.current_date - _parse_date(st.profitSellDate)).days < cfg.meta.profit_resell_cooldown_days
        )

        # v2.70.0/2.72.0: selling_price_change — additional mandatory guard for GET THE PROFITS,
        # independent of cooldown_blocks above. Compares the most
        # recent stored close (price_history/daily_bars.json, cache trails one session) against
        # the live current price, as a percentage of the live current price — same basis as the
        # Step 2 buy-guard's leg1/leg2/leg3_price_change. The sale is only allowed to fire when
        # (close_yesterday - price) * 100 / price < selling_price_change — i.e. today's price
        # hasn't already dropped too far off yesterday's close. Missing/insufficient price
        # history fails closed (guard stays active, blocking the sale), same posture as every
        # other price-change guard in this file.
        sell_closes = broker.get_daily_closes(sym, hist_start, hist_end)
        sell_close_yesterday = sell_closes[-1] if sell_closes else None
        sell_price_change = (
            (sell_close_yesterday - price) * 100 / price if sell_close_yesterday is not None else None
        )
        sell_price_guard_blocks = not (
            sell_price_change is not None and sell_price_change < cfg.meta.selling_price_change
        )

        # --- GET THE PROFITS ---
        # v2.63.0: the percentage gate and dollar gate are OR'd, not AND'd — either one clearing
        # its own bar is enough to fire. The dollar gate needs the FIFO figure regardless of
        # which leg passed, so it's computed unconditionally here rather than only after the
        # percentage gate clears (as it was under the old AND semantics).
        if not already_today:
            if no_lots_available:
                # No lot-level cost data exists at all to walk — estimate off the blended
                # avg_cost_basis instead (see the Zero-available-lots fallback note above).
                fifo = FifoSaleResult(
                    realized_profit_dollars=(price - pos.avg_cost_basis) * sell_qty,
                    lots_consumed=[],
                    quantity_sold=sell_qty,
                    fully_covered=True,
                )
            else:
                fifo = fifo_realized_profit(lots, sell_qty, price, exclude_loss_lots=True)

            # v2.78.0: dynamic profit-threshold ramp — the percent/dollar OR-gate is no longer a
            # flat bar. Each leg ramps parabolically from its own base (materialize_profit_percentage
            # / materialize_profit_in_dollars, the day-0 floor) up to its own cap
            # (materialize_profit_percentage_max / materialize_profit_in_dollars_max) over
            # profit_threshold_ramp_days, independently — measured against the quantity-weighted
            # average age of the SPECIFIC profitable lots this sale actually consumes (post
            # loss-lot exclusion), not the position's full lot history. A freshly-profitable
            # position clears a low bar; one that's sat on its gains for a while must clear a
            # much higher one before GTP will harvest it.
            weighted_days_held = _weighted_avg_lot_age_days(fifo.lots_consumed, lots, ctx.current_date)
            dynamic_percent_threshold = _dynamic_profit_threshold(
                cfg.meta.materialize_profit_percentage, cfg.meta.materialize_profit_percentage_max,
                cfg.meta.profit_threshold_ramp_days, weighted_days_held,
            )
            dynamic_dollar_threshold = _dynamic_profit_threshold(
                cfg.meta.materialize_profit_in_dollars, cfg.meta.materialize_profit_in_dollars_max,
                cfg.meta.profit_threshold_ramp_days, weighted_days_held,
            )
            percent_gate_passes = raw_gain_pct > dynamic_percent_threshold
            dollar_gate_passes = fifo.fully_covered and fifo.realized_profit_dollars > dynamic_dollar_threshold
            if percent_gate_passes or dollar_gate_passes:
                # v2.66.0: percent_gate_passes is based on avg_cost_basis (a whole-position
                # blended average) and can pass even when the FIFO-matched lots actually being
                # sold realize a loss — this happens whenever the position was built at
                # decreasing cost over time (expensive shares bought first, cheaper ones bought
                # later), since FIFO always disposes of the oldest (here, priciest) lots first.
                # Require the true FIFO-matched dollar figure to be positive unconditionally,
                # regardless of which gate (percent or dollar) is what actually passed — this is
                # what CLAUDE.md's "structurally profit-gated" assumption for GTP/MRT (used to
                # exempt them from the wash-sale backward sell-guard) depends on holding in fact,
                # not just on paper via the blended-average estimate.
                if not fifo.fully_covered:
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        "cost basis pending transfer on required lots (fail-closed)",
                        "partial profit-take sale",
                    ))
                elif fifo.realized_profit_dollars <= 0:
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        f"GTP gate clears on blended-average ({raw_gain_pct:+.2f}%) but the FIFO-matched "
                        f"lots actually being sold would realize ${fifo.realized_profit_dollars:.2f} "
                        f"(not a real profit) — refusing to sell at a loss",
                        "partial profit-take sale",
                    ))
                elif raw_gain_pct <= cfg.meta.min_raw_gain_percent_to_sell:
                    # v2.77.0: the loss-lot sell guard (Step 4) lets GTP fire by cherry-picking a
                    # position's profitable lots even when the position is overall a loser (or
                    # only marginally ahead) on the blended average — the percent/dollar OR-gate
                    # above and the per-lot profit check just above only look at the lots actually
                    # being sold, not at the position as a whole. This floor closes that: refuse
                    # to sell out of a losing/marginal position at all, regardless of which gate
                    # cleared or how many lots the loss-lot guard already excluded.
                    ctx.skipped.append(SkippedTrade(
                        sym,
                        f"GTP gate clears (FIFO ${fifo.realized_profit_dollars:.2f} on the profitable "
                        f"lots) but the position's overall blended-average gain ({raw_gain_pct:+.2f}%) "
                        f"doesn't clear min_raw_gain_percent_to_sell ({cfg.meta.min_raw_gain_percent_to_sell}%) "
                        f"— refusing to harvest gains out of a losing/marginal position",
                        "partial profit-take sale",
                    ))
                elif cooldown_blocks:
                    ctx.skipped.append(SkippedTrade(
                        sym, f"GTP gate clears ({raw_gain_pct:+.2f}% / FIFO ${fifo.realized_profit_dollars:.2f}) "
                             f"but profit_resell_cooldown_days active",
                        "partial profit-take sale",
                    ))
                elif sell_price_guard_blocks:
                    ctx.skipped.append(SkippedTrade(
                        sym, f"GTP gate clears ({raw_gain_pct:+.2f}% / FIFO ${fifo.realized_profit_dollars:.2f}) "
                             f"but selling_price_change guard active (price hasn't turned back up)",
                        "partial profit-take sale",
                    ))
                elif _sell_price_target_blocked(ctx, sym, price, "partial profit-take sale"):
                    pass  # target_price_to_sell overrides GTP too — "any means" — already logged
                else:
                    reason = (
                        f"GET THE PROFITS: {raw_gain_pct:+.2f}%, FIFO ${fifo.realized_profit_dollars:.2f} "
                        f"(dynamic thresholds {dynamic_percent_threshold:.2f}% / ${dynamic_dollar_threshold:.2f} "
                        f"at {weighted_days_held:.1f}d weighted profitable-lot age)"
                    )
                    if loss_excluded_qty > 0:
                        reason += (f" (loss-lot sell guard: {loss_excluded_qty:.4f} share(s) held back — "
                                   f"their lots are underwater at ${price:.2f})")
                    if fractional_position:
                        reason += (" (ordinary order — sub-whole-share position, Robinhood "
                                    "default lot matching; FIFO figure is an estimate)")
                    elif no_lots_available:
                        reason += (" (ordinary order — no priced/selectable lots yet, e.g. a "
                                    "same-day buy still syncing broker-side; Robinhood default "
                                    "lot matching, dollar figure is an avg_cost_basis estimate, "
                                    "not a FIFO walk)")
                    ctx.profit_taking_sells.append(TradeIntent(
                        symbol=sym, side="sell", quantity=sell_qty, reason=reason,
                        tax_lots=None if (fractional_position or no_lots_available) else
                            [{"open_lot_id": l["open_lot_id"], "quantity": l["quantity"]} for l in fifo.lots_consumed],
                        realized_profit_dollars=fifo.realized_profit_dollars,
                        raw_gain_pct=raw_gain_pct,
                    ))
                    if fifo.realized_profit_dollars <= 0:
                        # Defensive backstop — unreachable given the guard above, but keeps
                        # the wash-sale forward buy-guard armed correctly if this invariant is
                        # ever loosened by a future change.
                        ctx.loss_sale_symbols.append(sym)

    ctx.total_high_beta_gains_realized = sum(
        t.realized_profit_dollars or 0.0 for t in ctx.profit_taking_sells
    )


# ============================================================================================
# Step 4b — Sell Cleanup Pass (v2.80.0)
# ============================================================================================

def _lots_after_consumption(lots: List[TaxLot], consumed: Optional[List[dict]]) -> List[TaxLot]:
    """The lot structure that would remain after a sale consumes `consumed` (a GET THE PROFITS
    TradeIntent's own `tax_lots`, `{"open_lot_id", "quantity"}` per entry) out of `lots`. Lots
    left with ~0 quantity are dropped entirely. `consumed=None` (no sale this cycle, or a sale
    that went out as an ordinary/non-specified-lot order — see step4b_sell_cleanup) returns
    `lots` unchanged."""
    if not consumed:
        return list(lots)
    used = {c["open_lot_id"]: c["quantity"] for c in consumed}
    out = []
    for lot in lots:
        remaining_qty = lot.quantity - used.get(lot.open_lot_id, 0.0)
        if remaining_qty > 1e-9:
            out.append(TaxLot(
                open_lot_id=lot.open_lot_id, quantity=remaining_qty,
                cost_per_share=lot.cost_per_share, open_date=lot.open_date,
                is_selectable=lot.is_selectable,
            ))
    return out


def step4b_sell_cleanup(ctx: RunContext, broker: BrokerClient) -> None:
    """Cleans up the small/single-lot remainders GET THE PROFITS' whole-share rounding and
    loss-lot exclusion routinely leave behind, plus any other stray single-lot position that's
    too small to be worth tracking further — as long as the remaining lot is NOT a loss. Runs
    AFTER step4_profit_taking so it sees this cycle's own GET THE PROFITS fills. Two independent
    rules, unioned (a symbol matching either fires, evaluated once):

      (a) ANY currently-held target asset whose remaining position (after this cycle's own GET
          THE PROFITS sale, if one fired) is exactly ONE tax lot, that lot is not a loss (its
          cost_per_share is at or below the current price), AND the remaining market value is
          under `cleanup_dust_threshold_dollars` — sweep the whole remainder.
      (b) Specifically for a symbol whose GET THE PROFITS sale fired THIS cycle: if what's left
          over is exactly ONE tax lot and it's not a loss, sweep it regardless of dollar size —
          "finish the job" rather than leave an odd remainder hanging after a profit-take that
          already fired this cycle.

    Bypasses every GET THE PROFITS profit gate (percent/dollar OR-gate, min_raw_gain_percent_to_sell,
    profit_resell_cooldown_days, selling_price_change) — this is a dust/remainder cleanup, not a
    profit-taking decision, so none of those gates are meaningful here. Still respects the
    `blocked` list (checked via the caller loop skipping blocked_symbols) and target_price_to_sell
    (the one guard CLAUDE.md says overrides even the emergency stop-losses). Never fires on a
    loss — the single remaining lot must clear cost_per_share <= current_price — so this can never
    need to arm the wash-sale buy-guard.

    Always sized as an ORDINARY order (tax_lots=None): the whole point is disposing of the
    ENTIRE remaining position, which is very often a fractional-share remainder (that's the
    premise of rule (a)/(b) existing at all), and a specified-lot order requires a whole-share
    top-level quantity — see fifo.round_sell_quantity's docstring. With only one lot involved,
    Robinhood's own default lot matching disposes of that same lot regardless, so nothing is
    lost by not specifying it.

    A symbol whose GET THE PROFITS sale this cycle went out as an ordinary order itself (the
    sub-whole-share or zero-available-lots fallback in step4_profit_taking — `tax_lots is None`
    on that TradeIntent) is skipped here entirely: without knowing exactly which lot(s) Robinhood
    actually consumed, the remaining lot structure can't be determined, and guessing would risk
    double-counting or missing a lot."""
    cfg = ctx.config
    gtp_by_symbol = {t.symbol: t for t in ctx.profit_taking_sells}

    for sym, pos in ctx.positions.items():
        if sym not in cfg.targets or pos.quantity <= 0 or pos.avg_cost_basis is None:
            continue
        if sym in ctx.blocked_symbols:
            continue
        if sym in ctx.drawdown_liquidations or sym in ctx.blocked_liquidations:
            continue  # already being fully liquidated by another mechanism this cycle

        gtp_intent = gtp_by_symbol.get(sym)
        if gtp_intent is not None and gtp_intent.tax_lots is None:
            continue  # ordinary-order GTP fallback — remaining lot structure isn't knowable

        lots = broker.get_tax_lots(ctx.account_number, sym)
        remaining_lots = _lots_after_consumption(lots, gtp_intent.tax_lots if gtp_intent else None)
        remaining_qty = sum(l.quantity for l in remaining_lots)
        if remaining_qty <= 1e-9 or len(remaining_lots) != 1:
            continue

        lot = remaining_lots[0]
        if lot.cost_per_share is None:
            continue  # can't judge green/loss without a priced lot
        price = ctx.quotes[sym].last_trade_price
        is_green = lot.cost_per_share <= price
        if not is_green:
            continue

        remaining_mv = remaining_qty * price
        rule_a = remaining_mv < cfg.meta.cleanup_dust_threshold_dollars
        rule_b = gtp_intent is not None
        if not (rule_a or rule_b):
            continue

        if _sell_price_target_blocked(ctx, sym, price, "Sell Cleanup Pass"):
            continue  # target_price_to_sell overrides even this cleanup sweep — "any means"

        realized = (price - lot.cost_per_share) * remaining_qty
        fired_rules = " + ".join(
            r for r, active in (
                (f"dust (<${cfg.meta.cleanup_dust_threshold_dollars:,.2f}, single green lot)", rule_a),
                ("single green lot left after this cycle's own GET THE PROFITS sale", rule_b),
            ) if active
        )
        reason = (
            f"Sell Cleanup Pass: sweeping {remaining_qty:.4f} remaining share(s) "
            f"(${remaining_mv:,.2f}, lot cost ${lot.cost_per_share:,.2f} vs. price ${price:,.2f}) "
            f"— {fired_rules}"
        )
        ctx.cleanup_sells.append(TradeIntent(
            symbol=sym, side="sell", quantity=remaining_qty, reason=reason,
            tax_lots=None, realized_profit_dollars=realized,
        ))

    ctx.total_cleanup_gains_realized = sum(
        t.realized_profit_dollars or 0.0 for t in ctx.cleanup_sells
    )


# ============================================================================================
# Step 5 — Price Limit & Volatility Halts
# ============================================================================================

def step5_price_limits(ctx: RunContext, broker: BrokerClient, buy_candidates: Dict[str, float]) -> Dict[str, float]:
    """buy_price_diff_limit and 52_week_high_guard both apply to every planned buy (the Step 3
    Underweight fills). sell_price_diff_limit is retained as a parameter but has no applicable
    sell path anymore: it only ever exempted ROUTINE Overweight drift-selling, a mechanism that
    no longer exists — GET THE PROFITS sales (ctx.profit_taking_sells) were always exempt from
    it and remain untouched here."""
    cfg = ctx.config
    n_days = cfg.meta.no_of_days_for_price_compare
    end = ctx.current_date - timedelta(days=1)
    start = end - timedelta(days=n_days * 3)  # pad for weekends/holidays

    filtered_buys: Dict[str, float] = {}
    for sym, dollars in buy_candidates.items():
        price = ctx.quotes[sym].last_trade_price

        bars = broker.get_daily_lows_highs(sym, start, end)[-n_days:]
        if bars:
            low_n = min(l for l, _ in bars)
            pump_pct = (price - low_n) / low_n * 100
            if pump_pct > cfg.meta.buy_price_diff_limit:
                ctx.skipped.append(SkippedTrade(
                    sym, f"buy_price_diff_limit: +{pump_pct:.2f}% vs. {n_days}-day low "
                         f"(limit {cfg.meta.buy_price_diff_limit}%)",
                    "Underweight buy",
                ))
                continue

        # 52_week_high_guard: blocks chasing a symbol already trading near its 52-week high, by
        # ANY means. Missing 52-week-high data fails OPEN (allows the buy) — same posture as the
        # buy_price_diff_limit check in this function when historical data is unavailable.
        high_52w = broker.get_fifty_two_week_high(sym)
        if high_52w:
            pct_of_high = price / high_52w * 100
            if pct_of_high > cfg.meta.fifty_two_week_high_guard:
                ctx.skipped.append(SkippedTrade(
                    sym, f"52_week_high_guard: price ${price:,.2f} is {pct_of_high:.2f}% of "
                         f"52-week high ${high_52w:,.2f} (limit {cfg.meta.fifty_two_week_high_guard}%)",
                    "Underweight buy",
                ))
                continue

        filtered_buys[sym] = dollars

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
        | {t.symbol for t in ctx.cleanup_sells}
        | set(ctx.drawdown_liquidations)
        | set(ctx.blocked_liquidations)
    )


def step6a_prepare_sells(
    ctx: RunContext, planned_buys: Optional[Dict[str, float]] = None
) -> tuple[List[TradeIntent], bool, Optional[str]]:
    """Builds the final sell order list (drawdown liquidations + blocked+forceSell liquidations +
    GET THE PROFITS sales), applies
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
    all_sells = liquidations + blocked_liquidations + ctx.profit_taking_sells + ctx.cleanup_sells

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
    # this, ctx.profit_taking_sells/ctx.drawdown_liquidations still held
    # every ranked/logged candidate regardless of whether it cleared sell_or_buy_value_limit here
    # — which desynced Step 7's journal (its "N sell(s)" header count and per-section listings
    # counted candidates that were actually skipped) and, for drawdown_liquidations specifically,
    # would have made cli.py's _update_peak_prices mark a never-sold symbol as liquidated.
    ctx.drawdown_liquidations = [s for s in ctx.drawdown_liquidations if s in placed_symbols]
    ctx.blocked_liquidations = [s for s in ctx.blocked_liquidations if s in placed_symbols]
    ctx.profit_taking_sells = [t for t in ctx.profit_taking_sells if t.symbol in placed_symbols]
    ctx.cleanup_sells = [t for t in ctx.cleanup_sells if t.symbol in placed_symbols]
    ctx.total_cleanup_gains_realized = sum(t.realized_profit_dollars or 0.0 for t in ctx.cleanup_sells)

    return sells_to_place, False, None


def step6b_finalize_buys(
    ctx: RunContext,
    planned_buys: Dict[str, float],
    net_realized_gains_ytd_effective: float,
    buying_power_now: float,
) -> List[TradeIntent]:
    """Given the caller's post-sell realized P&L and fresh buying power (fetched via MCP/broker
    AFTER the Step 6a sells were confirmed filled), finalizes tax_reserve, applies the hard-cap
    scaling, and returns the final buy order list. Places nothing.

    `buying_power_now` is expected to already reflect this cycle's sale proceeds immediately
    (limited margin enabled on this account makes unsettled proceeds spendable right away), so no
    settlement-reserve bridging is needed here.
    """
    cfg = ctx.config

    selling_syms = _selling_symbols(ctx)
    planned_buys = {s: d for s, d in planned_buys.items() if s not in selling_syms and s not in ctx.blocked_symbols}

    ctx.net_realized_gains_ytd_effective = net_realized_gains_ytd_effective
    prior_years_base = sum(v for y, v in ctx.tax_by_year.items() if int(y) < ctx.current_date.year)
    total_paid_taxes = sum(ctx.paid_taxes_by_year.values())
    ctx.tax_reserve = _compute_tax_reserve(
        prior_years_base, net_realized_gains_ytd_effective,
        cfg.meta.keep_aside_profits_for_tax_percent, total_paid_taxes,
    )

    total_planned = sum(planned_buys.values())
    hard_cap = max(0.0, buying_power_now - cfg.meta.min_cash_absolute - ctx.tax_reserve)

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


def compute_dormant_assets(ctx: RunContext) -> List[DormantAsset]:
    """CLAUDE.md Step 7's Dormant Assets report — purely observational, never influences any
    buy/sell decision. For every currently-held target asset whose last trading activity (the
    more recent of `lastPurchaseDate` and `profitSellDate` in peak/prices.json) is more than
    `dormant_asset_days` days old — or has no recorded activity at all — report its current
    unrealized dollar profit/loss and percentage. A held asset whose cost basis hasn't fully
    reconciled yet (Step 1's Fail-Closed rule) is omitted since its unrealized P&L can't be
    computed. Sorted most-dormant first (no-record assets sort ahead of everything else)."""
    threshold = ctx.config.meta.dormant_asset_days
    out: List[DormantAsset] = []
    for sym, pos in ctx.positions.items():
        if sym not in ctx.config.targets or pos.quantity <= 0 or pos.avg_cost_basis is None:
            continue
        st = ctx.price_state.get(sym, AssetPriceState())
        candidates = [d for d in (_parse_date(st.lastPurchaseDate), _parse_date(st.profitSellDate)) if d is not None]
        last_activity = max(candidates) if candidates else None
        days = (ctx.current_date - last_activity).days if last_activity is not None else None
        if days is not None and days <= threshold:
            continue  # recently active -> not dormant

        price = ctx.quotes[sym].last_trade_price
        out.append(DormantAsset(
            symbol=sym,
            days_since_activity=days,
            last_activity_date=last_activity.isoformat() if last_activity is not None else None,
            unrealized_dollars=(price - pos.avg_cost_basis) * pos.quantity,
            unrealized_pct=(price - pos.avg_cost_basis) / pos.avg_cost_basis * 100,
        ))

    out.sort(key=lambda d: d.days_since_activity if d.days_since_activity is not None else float("inf"), reverse=True)
    return out


def compute_loss_only_assets(ctx: RunContext, broker: BrokerClient) -> List[LossOnlyAsset]:
    """CLAUDE.md Step 7's Loss-Only Lot Assets report — purely observational, never influences any
    buy/sell decision.

    Lists every currently-held target asset for which EVERY sellable, priced lot is at or above
    today's price, i.e. the position holds no lot that could be sold at a gain. This is exactly
    the population the v2.75.0 loss-lot sell guard can never sell any part of: GET THE PROFITS is
    structurally unable to fire on them, so short of an emergency stop they can only leave the
    portfolio by a manual/off-platform action (the broker exposes no transfer API to this agent).

    Returns CANDIDATES: tax-lot data is only reachable while the broker is in hand (the `plan`
    command), but the buys aren't sized until `finalize`, which has no broker. So `plan` calls
    this and `finalize` filters the result down with `drop_bought_symbols` — a symbol bought this
    cycle gains a fresh lot at ~today's price and is no longer loss-only.

    Omits assets whose cost basis hasn't fully reconciled (Step 1's Fail-Closed rule) and assets
    with no priced+selectable lots at all — in both cases "every lot is underwater" cannot be
    established, and this report never guesses. Sorted worst unrealized percentage first."""
    out: List[LossOnlyAsset] = []
    for sym, pos in ctx.positions.items():
        if sym not in ctx.config.targets or pos.quantity <= 0 or pos.avg_cost_basis is None:
            continue

        price = ctx.quotes[sym].last_trade_price
        lots = [
            lot for lot in broker.get_tax_lots(ctx.account_number, sym)
            if lot.is_selectable and lot.cost_per_share is not None
        ]
        if not lots:
            continue  # nothing priced/selectable to judge -> can't establish the claim
        lot_qty = sum(lot.quantity for lot in lots)
        if lot_qty < pos.quantity - 1e-6:
            continue  # priced lots don't cover the whole position -> claim unprovable for the rest
        if profitable_lot_quantity(lots, price) > 0:
            continue  # at least one lot could still be sold at a gain

        costs = [lot.cost_per_share for lot in lots]
        # Unrealized on the LOT basis, so it can never contradict this list's membership test.
        # The broker's blended avg_cost_basis is kept for reference and flagged when it disagrees.
        lot_weighted_cost = sum(lot.quantity * lot.cost_per_share for lot in lots) / lot_qty
        out.append(LossOnlyAsset(
            symbol=sym,
            quantity=pos.quantity,
            avg_cost_basis=pos.avg_cost_basis,
            lot_weighted_cost=lot_weighted_cost,
            current_price=price,
            market_value=price * pos.quantity,
            unrealized_dollars=sum((price - lot.cost_per_share) * lot.quantity for lot in lots),
            unrealized_pct=(price - lot_weighted_cost) / lot_weighted_cost * 100,
            lot_count=len(lots),
            worst_lot_cost=max(costs),
            best_lot_cost=min(costs),
            basis_mismatch=abs(lot_weighted_cost - pos.avg_cost_basis) > 0.005 * pos.avg_cost_basis,
        ))

    out.sort(key=lambda a: a.unrealized_pct)
    return out


def drop_bought_symbols(assets: List[LossOnlyAsset], ctx: RunContext) -> List[LossOnlyAsset]:
    """Final leg of the Loss-Only Lot Assets report: drop any symbol this cycle bought. The buy
    adds a lot at ~today's price, so that position no longer holds only losing lots. Split out
    from compute_loss_only_assets because the buys are only known in `finalize`, which has no
    broker to re-read tax lots with."""
    bought = {t.symbol for t in ctx.buys}
    return [a for a in assets if a.symbol not in bought]


def _enforce_min_trade_value_buys(
    ctx: RunContext, planned_buys: Dict[str, float], min_value: float
) -> Dict[str, float]:
    """CLAUDE.md's `min_value_of_trade` control: every buy that survives should be worth at
    least `min_value_of_trade` dollars. Rather than simply dropping anything under the floor (as
    `sell_or_buy_value_limit` already does for genuinely tiny amounts), a buy that's short of the
    floor is bumped up to it by borrowing dollars from lower-priority buys — buys rank by their
    own planned dollar amount descending (a bigger amount reflects a bigger drift gap, i.e. more
    urgent). Lower-priority buys are drained from the bottom of that ranking first, cascading: a
    buy drained below its own floor gets its own turn to borrow from whatever is left further
    down. A buy that still can't reach the floor once every lower-ranked buy is exhausted is
    dropped (logged to ctx.skipped) rather than placed under-sized; its dollars simply stay
    wherever they were already redirected to.
    """
    if min_value <= 0 or not planned_buys:
        return planned_buys

    order = sorted(planned_buys, key=lambda s: -planned_buys[s])
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
