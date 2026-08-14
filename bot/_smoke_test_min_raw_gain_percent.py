"""Coverage for `min_raw_gain_percent_to_sell` (v2.77.0) — the floor that closes the gap the
v2.75.0 loss-lot sell guard opened.

The gap: the loss-lot sell guard lets GET THE PROFITS cherry-pick a position's profitable lots
and fire even when the position as a whole is a loser (or only marginally ahead) on the blended
average — the percent/dollar OR-gate and the per-sold-lot FIFO profit check only look at the lots
actually being sold, never at the position overall. Confirmed against the live account on
2026-08-14: TSLA at -11.91% overall and F at -0.04% overall both fired under the loss-lot guard
alone, extracting gains from lots while the position itself was underwater.

`min_raw_gain_percent_to_sell` adds one more mandatory gate: `raw_gain_pct` (the whole-position
blended-average gain) must clear this floor, regardless of which OR-gate leg passed or how many
lots the loss-lot guard already excluded. Default 0.5%.

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


def test_underwater_position_no_longer_harvests_via_loss_lot_guard() -> None:
    """The exact TSLA-shaped scenario: position overall at -11.91% on the blended average, but
    the loss-lot guard leaves one profitable lot that clears the FIFO dollar gate. Before this
    guard, that fired. It must now be skipped."""
    ctx, broker = _position("TSLA", price=88.09, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="old", quantity=15.0, cost_per_share=105.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="new", quantity=5.0, cost_per_share=80.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "TSLA"]
    assert any("min_raw_gain_percent_to_sell" in r and "losing/marginal position" in r for r in reasons), reasons
    print("[underwater-blocked] position at -11.91% overall -> GTP refused even though a lot "
          "would clear the FIFO dollar gate")


def test_marginal_position_below_floor_is_blocked() -> None:
    """F-shaped scenario: position only marginally positive (or breakeven) overall — below the
    0.5% floor — must also be blocked, not just outright-negative positions."""
    ctx, broker = _position("F", price=100.1, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="old", quantity=15.0, cost_per_share=100.5, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="new", quantity=5.0, cost_per_share=80.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells  # raw_gain_pct = +0.10%, < 0.5% floor
    reasons = [s.reason for s in ctx.skipped if s.symbol == "F"]
    assert any("min_raw_gain_percent_to_sell" in r for r in reasons), reasons
    print("[marginal-blocked] position at +0.10% overall (below the 0.5% floor) -> refused")


def test_position_above_floor_still_fires() -> None:
    """Sanity check the floor doesn't over-tighten: a position genuinely ahead on the blended
    average, above the floor, fires exactly as before."""
    ctx, broker = _position("HEALTHY", price=110.0, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=20.0, cost_per_share=90.0, open_date=date(2026, 1, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert "min_raw_gain_percent_to_sell" not in t.reason, t.reason
    print(f"[above-floor-fires] position at +10.00% overall (above the 0.5% floor) -> fires "
          f"normally, FIFO ${t.realized_profit_dollars:.2f}")


def test_floor_is_configurable() -> None:
    """A stricter floor (e.g. 5%) blocks a position that would have cleared a looser one — proves
    the value in portfolio_targets.json actually drives the gate, not a hardcoded constant."""
    ctx, broker = _position("MOD", price=103.0, quantity=20.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=20.0, cost_per_share=95.0, open_date=date(2026, 1, 1), is_selectable=True),
    ], meta_overrides={"min_raw_gain_percent_to_sell": 5.0})
    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells  # raw_gain_pct = +3.0%, < 5% floor
    reasons = [s.reason for s in ctx.skipped if s.symbol == "MOD"]
    assert any("min_raw_gain_percent_to_sell (5.0%)" in r for r in reasons), reasons
    print("[configurable] a stricter 5% floor blocks a +3.0% position that a 0.5% floor "
          "would have allowed")


def main() -> None:
    test_underwater_position_no_longer_harvests_via_loss_lot_guard()
    test_marginal_position_below_floor_is_blocked()
    test_position_above_floor_still_fires()
    test_floor_is_configurable()
    print("\nSMOKE TEST (min_raw_gain_percent_to_sell floor) PASSED")


if __name__ == "__main__":
    main()
