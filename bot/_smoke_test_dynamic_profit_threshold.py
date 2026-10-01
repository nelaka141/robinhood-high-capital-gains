"""Coverage for the v2.78.0 dynamic profit-threshold ramp — GET THE PROFITS' percent/dollar
OR-gate no longer uses flat bars (`materialize_profit_percentage`/`materialize_profit_in_dollars`).
Each leg now ramps parabolically, independently, from its own day-0 floor up to its own cap
(`materialize_profit_percentage_max`/`materialize_profit_in_dollars_max`) as the quantity-weighted
average age of the SPECIFIC profitable lots a sale would consume (post loss-lot-guard exclusion)
increases, reaching the cap at `profit_threshold_ramp_days` and staying flat beyond it:

    threshold(days_held) = base + (max - base) * min(1, days_held / ramp_days) ** 2

Pure logic tests against step4_profit_taking directly, no snapshot/CLI plumbing needed (same
style as bot/_smoke_test_min_raw_gain_percent.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_dynamic_profit_threshold.py
"""
from __future__ import annotations

from datetime import date, timedelta

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.steps import _dynamic_profit_threshold, _weighted_avg_lot_age_days, step4_profit_taking

CURRENT_DATE = date(2026, 8, 18)


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0,
        no_of_days_for_price_compare=3, cap_on_total_cash_balance_to_use=30000,
        cool_down_period_after_lquidation=6, beta_benchmark_symbol="SPY",
        beta_calculation_lookback_days=30, sold_asset_repurchase_days=2,
        leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9, profit_resell_cooldown_days=15,
        selling_price_change=0.1, sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.0, profit_sell_percentage=100.0,
        materialize_profit_in_dollars=1e9,       # dollar leg disabled by default (percent tests)
        materialize_profit_percentage_max=10.0,  # production default
        materialize_profit_in_dollars_max=1e9,   # dollar leg disabled by default
        profit_threshold_ramp_days=30,           # production default
        min_raw_gain_percent_to_sell=0.5,
        keep_aside_profits_for_tax_percent=30.0, momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0, max_sector_percentage=0.0,
        wash_sale_lookback_days=0, dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        # Price far above this series -> selling_price_change guard passes trivially.
        return [58.0, 58.5, 59.0, 59.5, 60.0]


def _position(sym: str, price: float, quantity: float, avg_cost: float, lots: list,
              meta_overrides: dict | None = None) -> tuple:
    targets = {sym: AssetTarget(symbol=sym, weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(**(meta_overrides or {})), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=CURRENT_DATE, config=cfg, account_number="TEST")
    ctx.positions = {sym: Position(symbol=sym, quantity=quantity, avg_cost_basis=avg_cost)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    return ctx, _Broker({sym: lots})


def test_dynamic_threshold_formula_unit() -> None:
    """The parabolic formula itself: day-0 floor, flat at the cap once ramp_days is reached, and
    a value strictly between the two at a partial ramp."""
    assert _dynamic_profit_threshold(base=2.0, max_value=10.0, ramp_days=30, days_held=0) == 2.0
    assert _dynamic_profit_threshold(base=2.0, max_value=10.0, ramp_days=30, days_held=30) == 10.0
    assert _dynamic_profit_threshold(base=2.0, max_value=10.0, ramp_days=30, days_held=60) == 10.0  # capped, not linear-unbounded
    # days_held=15 -> t=0.5 -> t**2=0.25 -> 2.0 + 8.0*0.25 = 4.0
    assert abs(_dynamic_profit_threshold(base=2.0, max_value=10.0, ramp_days=30, days_held=15) - 4.0) < 1e-9
    print("[formula] day-0 floor, capped-flat past ramp_days, parabolic (not linear) in between")


def test_weighted_avg_lot_age_helper() -> None:
    """Quantity-weighted, not simple, average across the lots actually consumed."""
    lots = [
        TaxLot(open_lot_id="a", quantity=5.0, cost_per_share=90.0, open_date=CURRENT_DATE, is_selectable=True),
        TaxLot(open_lot_id="b", quantity=15.0, cost_per_share=90.0, open_date=CURRENT_DATE - timedelta(days=30), is_selectable=True),
    ]
    consumed = [
        {"open_lot_id": "a", "quantity": 5.0, "cost_per_share": 90.0},
        {"open_lot_id": "b", "quantity": 15.0, "cost_per_share": 90.0},
    ]
    # (5*0 + 15*30) / 20 = 22.5, NOT the simple average of 0 and 30 (15.0)
    got = _weighted_avg_lot_age_days(consumed, lots, CURRENT_DATE)
    assert abs(got - 22.5) < 1e-9, got
    assert _weighted_avg_lot_age_days([], lots, CURRENT_DATE) == 0.0  # no consumed lots -> day-0 floor
    print(f"[weighted-avg] mixed 5-share/0d + 15-share/30d lot -> {got}d (quantity-weighted, not 15d)")


def test_fresh_lot_fires_at_low_bar_old_lot_blocked_at_same_gain() -> None:
    """Percent leg: the SAME +5% gain fires when the profitable lot is brand new (threshold at
    the 2% floor) but is blocked once that lot has aged to profit_threshold_ramp_days (threshold
    at the 10% cap) -- the whole point of the ramp."""
    fresh_ctx, fresh_broker = _position("FRESH", price=105.0, quantity=10.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=90.0, open_date=CURRENT_DATE, is_selectable=True),
    ])
    step4_profit_taking(fresh_ctx, fresh_broker)
    assert len(fresh_ctx.profit_taking_sells) == 1, fresh_ctx.profit_taking_sells
    assert "2.00% / $" in fresh_ctx.profit_taking_sells[0].reason, fresh_ctx.profit_taking_sells[0].reason
    print("[fresh-fires] +5% gain, 0-day-old profitable lot, 2% floor -> fires")

    old_ctx, old_broker = _position("OLD", price=105.0, quantity=10.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=90.0, open_date=CURRENT_DATE - timedelta(days=30), is_selectable=True),
    ])
    step4_profit_taking(old_ctx, old_broker)
    assert old_ctx.profit_taking_sells == [], old_ctx.profit_taking_sells
    print("[old-blocked] identical +5% gain, 30-day-old profitable lot, 10% cap -> blocked")


def test_mixed_age_lots_land_between_floor_and_cap() -> None:
    """Two lots of different ages, weighted 5:15 -> weighted age 22.5d -> threshold 6.5% (not the
    2% floor, not the 10% cap, not the simple-average midpoint of 6%). A 6% gain (below 6.5%) is
    blocked; a 7% gain (above) fires."""
    def _mixed(price: float):
        return _position(price=price, sym="MIX", quantity=20.0, avg_cost=100.0, lots=[
            TaxLot(open_lot_id="new", quantity=5.0, cost_per_share=90.0, open_date=CURRENT_DATE, is_selectable=True),
            TaxLot(open_lot_id="old", quantity=15.0, cost_per_share=90.0, open_date=CURRENT_DATE - timedelta(days=30), is_selectable=True),
        ])

    ctx6, broker6 = _mixed(106.0)  # +6.0%
    step4_profit_taking(ctx6, broker6)
    assert ctx6.profit_taking_sells == [], ctx6.profit_taking_sells
    print("[mixed-below] +6.0% gain vs. 6.50% dynamic threshold (22.5d weighted age) -> blocked")

    ctx7, broker7 = _mixed(107.0)  # +7.0%
    step4_profit_taking(ctx7, broker7)
    assert len(ctx7.profit_taking_sells) == 1, ctx7.profit_taking_sells
    assert "6.50%" in ctx7.profit_taking_sells[0].reason, ctx7.profit_taking_sells[0].reason
    assert "22.5d" in ctx7.profit_taking_sells[0].reason, ctx7.profit_taking_sells[0].reason
    print("[mixed-above] +7.0% gain vs. 6.50% dynamic threshold (22.5d weighted age) -> fires")


def test_dollar_leg_ramps_independently_of_percent_leg() -> None:
    """Dollar leg has its own base/max/ramp, evaluated independently — with the percent leg
    pinned unreachable (base=max=1000%), a $10 FIFO profit fires on a fresh lot ($5 floor) but is
    blocked on an aged lot ($50 cap)."""
    overrides = dict(
        materialize_profit_percentage=1000.0, materialize_profit_percentage_max=1000.0,
        materialize_profit_in_dollars=5.0, materialize_profit_in_dollars_max=50.0,
    )
    fresh_ctx, fresh_broker = _position("DFRESH", price=100.0, quantity=1.0, avg_cost=90.0, lots=[
        TaxLot(open_lot_id="a", quantity=1.0, cost_per_share=90.0, open_date=CURRENT_DATE, is_selectable=True),
    ], meta_overrides=overrides)
    step4_profit_taking(fresh_ctx, fresh_broker)
    assert len(fresh_ctx.profit_taking_sells) == 1, fresh_ctx.profit_taking_sells
    assert fresh_ctx.profit_taking_sells[0].realized_profit_dollars == 10.0
    print("[dollar-fresh-fires] $10 FIFO profit, 0-day-old lot, $5 floor -> fires")

    old_ctx, old_broker = _position("DOLD", price=100.0, quantity=1.0, avg_cost=90.0, lots=[
        TaxLot(open_lot_id="a", quantity=1.0, cost_per_share=90.0, open_date=CURRENT_DATE - timedelta(days=30), is_selectable=True),
    ], meta_overrides=overrides)
    step4_profit_taking(old_ctx, old_broker)
    assert old_ctx.profit_taking_sells == [], old_ctx.profit_taking_sells
    print("[dollar-old-blocked] identical $10 FIFO profit, 30-day-old lot, $50 cap -> blocked")


def test_ramp_is_configurable() -> None:
    """A shorter ramp (10 days instead of 30) reaches the cap sooner — proves the value in
    portfolio_targets.json actually drives the curve, not a hardcoded constant."""
    ctx, broker = _position("SHORTRAMP", price=105.0, quantity=10.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=90.0, open_date=CURRENT_DATE - timedelta(days=10), is_selectable=True),
    ], meta_overrides={"profit_threshold_ramp_days": 10})
    step4_profit_taking(ctx, broker)
    # At 10 days held with a 10-day ramp, threshold is already at the 10% cap -> +5% gain blocked.
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    print("[configurable-ramp] a 10-day ramp reaches the 10% cap by day 10 -> +5% gain blocked "
          "(would have fired under the 30-day production ramp, still short of its own cap at day 10)")


def test_decay_leg_formula_unit() -> None:
    """v2.89.0 downward leg: past the peak the threshold falls along a mirrored parabola from the
    cap to the final floor over decay_days, then holds flat there."""
    f = lambda d, **kw: _dynamic_profit_threshold(base=2.0, max_value=10.0, ramp_days=30, days_held=d, **kw)
    kw = dict(decay_days=30, final_value=1.0)
    assert f(30, **kw) == 10.0                        # peak unchanged
    # 15 days past the peak -> u=0.5 -> 1.0 + 9.0*0.25 = 3.25 (drops fastest just after the peak)
    assert abs(f(45, **kw) - 3.25) < 1e-9, f(45, **kw)
    assert f(60, **kw) == 1.0 and f(200, **kw) == 1.0  # lands on, then flat at, the final floor
    assert abs(f(15, **kw) - 4.0) < 1e-9               # rising leg untouched
    assert f(45, decay_days=30) == 2.0 + 8.0 * 0.25    # final_value=None -> falls back to base
    assert f(200) == 10.0 and f(200, decay_days=0, final_value=1.0) == 10.0  # off -> flat at cap
    print("[decay-formula] cap at the peak, mirrored parabola down, flat at the final floor; off when decay_days=0")


def test_decay_leg_end_to_end() -> None:
    """A +5% gain on a 30-day-old lot is blocked at the 10% cap, but the identical gain fires once
    the lot is 60 days old under a 30-day decay back to a 2% final floor -- and is still blocked
    at 35 days (threshold ~6.89%, barely off the peak)."""
    decay = {"profit_threshold_decay_days": 30, "materialize_profit_percentage_final": 2.0}
    for age, fires in ((30, False), (35, False), (60, True), (90, True)):
        ctx, broker = _position(f"D{age}", price=105.0, quantity=10.0, avg_cost=100.0, lots=[
            TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=90.0,
                   open_date=CURRENT_DATE - timedelta(days=age), is_selectable=True),
        ], meta_overrides=decay)
        step4_profit_taking(ctx, broker)
        assert (len(ctx.profit_taking_sells) == 1) == fires, (age, ctx.profit_taking_sells)
    print("[decay-e2e] +5% gain: blocked at 30d and 35d, fires again at 60d and 90d once decayed to 2%")


def test_decay_final_floors_are_independent_per_leg() -> None:
    """Dollar leg decays to its own final figure regardless of the percent leg's."""
    ctx, broker = _position("DDOL", price=105.0, quantity=10.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=100.0,
               open_date=CURRENT_DATE - timedelta(days=60), is_selectable=True),
    ], meta_overrides=dict(
        materialize_profit_percentage=1000.0, materialize_profit_percentage_max=1000.0,  # percent leg off
        materialize_profit_in_dollars=5.0, materialize_profit_in_dollars_max=100.0,
        profit_threshold_decay_days=30, materialize_profit_in_dollars_final=40.0,
    ))
    step4_profit_taking(ctx, broker)
    # FIFO profit = 10 * (105 - 100) = $50 > $40 final floor (would fail the $100 cap) -> fires
    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    print("[decay-dollar] $50 FIFO profit fires at 60d against the dollar leg's own $40 final floor")


def test_portfolio_targets_json_loads_decay_params() -> None:
    from bot.config import load_portfolio_config
    m = load_portfolio_config("portfolio_targets.json").meta
    assert m.profit_threshold_decay_days >= 0
    for v in (m.materialize_profit_percentage_final, m.materialize_profit_in_dollars_final):
        assert v is None or v >= 0
    print(f"[config] portfolio_targets.json: decay {m.profit_threshold_decay_days}d -> "
          f"{m.materialize_profit_percentage_final}% / ${m.materialize_profit_in_dollars_final}")


def main() -> None:
    test_dynamic_threshold_formula_unit()
    test_weighted_avg_lot_age_helper()
    test_fresh_lot_fires_at_low_bar_old_lot_blocked_at_same_gain()
    test_mixed_age_lots_land_between_floor_and_cap()
    test_dollar_leg_ramps_independently_of_percent_leg()
    test_ramp_is_configurable()
    test_decay_leg_formula_unit()
    test_decay_leg_end_to_end()
    test_decay_final_floors_are_independent_per_leg()
    test_portfolio_targets_json_loads_decay_params()
    print("\nSMOKE TEST (dynamic profit-threshold ramp) PASSED")


if __name__ == "__main__":
    main()
