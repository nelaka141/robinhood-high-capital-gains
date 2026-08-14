"""Focused coverage for the v2.72.0 `selling_price_change` guard on GET THE PROFITS and Momentum
Reversal Trim (bot/steps.py::step4_profit_taking): a sale is only allowed to fire once
`(close_yesterday - price) * 100 / price < selling_price_change` — i.e. today's live price hasn't
already dropped too far (as a percentage of itself) below yesterday's stored close. This guard is
independent of, and stacks with, `profit_resell_cooldown_days`; both must clear for either
mechanism to fire. (Superseded the pre-v2.72.0 `z_score_sell_points` guard, which compared
Z-scores of the same two prices against the mean/stdev of the stored closes instead of a raw
percentage change — see git history for that version's `_smoke_test_zscore_sell_guard.py`.)

Pure logic tests against step4_profit_taking directly (same style as
bot/_smoke_test_gtp_mrt_profit_invariant.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_selling_price_guard.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.steps import step4_profit_taking

# Only the last close (yesterday) actually matters to selling_price_change; the guard only reads
# closes[-1]. Yesterday's close is 100.0.
_CLOSES = [90.0, 92.0, 94.0, 96.0, 98.0, 100.0]


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg1_price_change=0.5, leg2_price_change=0.5, leg3_price_change=0.1,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9,
        profit_resell_cooldown_days=0,
        selling_price_change=1.0,
        sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1e9,  # unreachable -> only the percent gate can fire
        min_raw_gain_percent_to_sell=-1e9,  # disabled -> not what this file tests
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    """Minimal BrokerClient stub: get_tax_lots (FIFO dollar-gate) + get_daily_closes (the
    selling_price_change guard)."""

    def __init__(self, lots: dict, closes):
        self._lots = lots
        self._closes = closes

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        return self._closes


def _ctx_and_broker(sym: str, price: float, closes, meta_overrides: dict | None = None) -> tuple:
    """20 shares @ $50 avg cost -> any price above ~$51.25 clears materialize_profit_percentage
    (2.5%) and the FIFO-matched realized dollars are unambiguously positive (single lot, no
    decreasing-cost trap)."""
    targets = {sym: AssetTarget(symbol=sym, weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(**(meta_overrides or {})), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 11), config=cfg, account_number="TEST")
    ctx.positions = {sym: Position(symbol=sym, quantity=20.0, avg_cost_basis=50.0)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    lots = {sym: [
        TaxLot(open_lot_id="lot1", quantity=20.0, cost_per_share=50.0, open_date=date(2026, 1, 1), is_selectable=True),
    ]}
    return ctx, _Broker(lots, closes)


def test_sharp_drop_blocks_gtp() -> None:
    """Price dropped sharply today (80.0) off yesterday's close (100.0, top of _CLOSES).
    sell_price_change = (100 - 80) * 100 / 80 = +25.0%, well over selling_price_change (1.0) ->
    GTP must be blocked even though the percent gate clears ((80-50)/50 = +60%) and FIFO is
    unambiguously profitable."""
    ctx, broker = _ctx_and_broker("DROP", price=80.0, closes=_CLOSES)
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "DROP"]
    assert any("selling_price_change guard active" in r for r in reasons), reasons
    print(f"[selling-price-blocks-sharp-drop] {reasons[0]}")


def test_flat_or_rising_price_allows_gtp() -> None:
    """Price at/above yesterday's close (105.0 vs. yesterday's 100.0) -> sell_price_change =
    (100 - 105) * 100 / 105 = -4.76%, comfortably clears selling_price_change (1.0) -> GTP fires
    normally."""
    ctx, broker = _ctx_and_broker("RISE", price=105.0, closes=_CLOSES)
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.symbol == "RISE"
    assert t.realized_profit_dollars == (105.0 - 50.0) * 10.0  # profit_sell_percentage=50% of 20
    print(f"[selling-price-allows-rise] FIFO realized ${t.realized_profit_dollars:.2f} — fires as expected")


def test_insufficient_history_fails_closed() -> None:
    """No price history at all (empty closes) -> close_yesterday is None -> guard fails closed
    (blocks the sale) even though the percent gate and FIFO dollars both clear."""
    ctx, broker = _ctx_and_broker("NOHIST", price=80.0, closes=[])
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "NOHIST"]
    assert any("selling_price_change guard active" in r for r in reasons), reasons
    print("[selling-price-fails-closed] empty price history -> guard blocks rather than assuming a pass")


def test_small_drop_under_threshold_still_allows() -> None:
    """A small drop that stays UNDER selling_price_change (1.0) should still clear the guard —
    not just a flat/rising price. Yesterday's close 100.0, price 99.5 -> sell_price_change =
    (100 - 99.5) * 100 / 99.5 = +0.503%, comfortably under the 1.0 threshold -> GTP fires."""
    ctx, broker = _ctx_and_broker("SMALLDROP", price=99.5, closes=_CLOSES)
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    print("[selling-price-small-drop-allows] +0.50% drop (< 1.0% threshold) -> GTP still fires — OK")


def main() -> None:
    test_sharp_drop_blocks_gtp()
    test_flat_or_rising_price_allows_gtp()
    test_insufficient_history_fails_closed()
    test_small_drop_under_threshold_still_allows()
    print("\nSMOKE TEST (selling_price_change guard) PASSED")


if __name__ == "__main__":
    main()
