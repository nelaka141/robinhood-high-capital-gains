"""Coverage for `min_raw_gain_percent_to_sell` — v2.77.0 floor, narrowed in v2.90.0.

v2.77.0 added a floor on the position's OVERALL blended-average gain: GET THE PROFITS refused to
sell even its individually-profitable lots out of a position that was a loser (or only marginally
ahead) overall. Confirmed live on 2026-10-01: ORCL's profitable lots cleared the decayed $40
dollar bar, but the position sat at -14.5% and the 0.5% floor blocked the sale.

v2.90.0: the account's tax-lot disposal preference is now lowest-cost-first, and the planner ships
the exact profitable lots on a specified-lot order anyway, so a sale of profitable lots realizes a
real gain whatever the position-level figure says. The floor no longer gates that path. It still
gates the v2.83.0 net-profit full exit, the one path that disposes of underwater lots (covered in
bot/_smoke_test_net_profit_full_exit.py and below).

Pure logic tests against step4_profit_taking directly, no snapshot/CLI plumbing needed (same
style as bot/_smoke_test_gtp_profit_invariant.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_min_raw_gain_percent.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.steps import step4_profit_taking


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
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1.0,  # low enough that the FIFO dollar gate alone can fire
        materialize_profit_percentage_max=2.5,  # ramp disabled (flat at the static 2.5% bar) ->
        materialize_profit_in_dollars_max=1.0,  # not what this file tests; see
        profit_threshold_ramp_days=30,          # _smoke_test_dynamic_profit_threshold.py
        min_raw_gain_percent_to_sell=0.5,   # the production default
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
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.positions = {sym: Position(symbol=sym, quantity=quantity, avg_cost_basis=avg_cost)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    return ctx, _Broker({sym: lots})


def test_underwater_position_sells_its_profitable_lots() -> None:
    """The ORCL/TSLA shape: position overall at -11.91% on the blended average, but one lot is
    in profit and clears the FIFO dollar gate. v2.77.0-v2.89.0 refused this; it now fires, selling
    only the profitable lot (the underwater one stays put)."""
    ctx, broker = _position("TSLA", price=88.09, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="old", quantity=15.0, cost_per_share=105.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="new", quantity=5.0, cost_per_share=80.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.tax_lots == [{"open_lot_id": "new", "quantity": 5.0}], t.tax_lots
    assert t.realized_profit_dollars > 0, t.realized_profit_dollars
    assert not any("losing/marginal position" in s.reason for s in ctx.skipped), ctx.skipped
    print(f"[underwater-sells-winners] position at -11.91% overall -> profitable lot sold, "
          f"FIFO ${t.realized_profit_dollars:.2f}; underwater lot untouched")


def test_marginal_position_sells_its_profitable_lots() -> None:
    """Position only marginally positive overall (+0.10%, under the 0.5% floor): the profitable
    lot is sold rather than the whole sale being refused."""
    ctx, broker = _position("F", price=100.1, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="old", quantity=15.0, cost_per_share=100.5, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="new", quantity=5.0, cost_per_share=80.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    assert ctx.profit_taking_sells[0].tax_lots == [{"open_lot_id": "new", "quantity": 5.0}]
    print("[marginal-sells-winners] position at +0.10% overall -> profitable lot sold")


def test_position_above_floor_still_fires() -> None:
    """Unchanged case: a position genuinely ahead on the blended average fires exactly as before."""
    ctx, broker = _position("HEALTHY", price=110.0, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=20.0, cost_per_share=90.0, open_date=date(2026, 1, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert "min_raw_gain_percent_to_sell" not in t.reason, t.reason
    print(f"[above-floor-fires] position at +10.00% overall -> fires normally, "
          f"FIFO ${t.realized_profit_dollars:.2f}")


def test_high_floor_no_longer_blocks_profitable_lot_sale() -> None:
    """Even a strict 5% floor no longer blocks a +3.0% position whose lots are all in profit."""
    ctx, broker = _position("MOD", price=103.0, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=20.0, cost_per_share=95.0, open_date=date(2026, 1, 1), is_selectable=True),
    ], meta_overrides={"min_raw_gain_percent_to_sell": 5.0})
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    print("[floor-ignored-for-winners] 5% floor, +3.0% position -> profitable-lot sale fires")


def test_floor_still_gates_net_profit_full_exit() -> None:
    """The floor still governs the net-profit full exit (which would dispose of the underwater
    lot): with a 5% floor the full exit declines and only the profitable lot is sold."""
    ctx, broker = _position("MIX", price=100.0, quantity=20.0, avg_cost=97.0, lots=[
        TaxLot(open_lot_id="loss", quantity=10.0, cost_per_share=104.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="gain", quantity=10.0, cost_per_share=90.0, open_date=date(2026, 6, 1), is_selectable=True),
    ], meta_overrides={"min_raw_gain_percent_to_sell": 5.0})
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.tax_lots == [{"open_lot_id": "gain", "quantity": 10.0}], t.tax_lots
    assert "net-profit full exit declined" in t.reason and "min_raw_gain_percent_to_sell (5.0%)" in t.reason, t.reason
    print("[floor-gates-full-exit] +3.09% mixed position, 5% floor -> full exit declined, gain lot sold")


def main() -> None:
    test_underwater_position_sells_its_profitable_lots()
    test_marginal_position_sells_its_profitable_lots()
    test_position_above_floor_still_fires()
    test_high_floor_no_longer_blocks_profitable_lot_sale()
    test_floor_still_gates_net_profit_full_exit()
    print("\nSMOKE TEST (min_raw_gain_percent_to_sell, v2.90.0 scope) PASSED")


if __name__ == "__main__":
    main()
