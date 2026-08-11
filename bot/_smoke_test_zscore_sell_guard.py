"""Focused coverage for the v2.70.0 `z_score_sell_points` guard on GET THE PROFITS and Momentum
Reversal Trim (bot/steps.py::step4_profit_taking): a sale is only allowed to fire once
`Z_yesterday - Z_today < z_score_sell_points` — i.e. today's price hasn't already dropped too
far, in standard-deviation terms, below yesterday's close. This guard is independent of, and
stacks with, `profit_resell_cooldown_days`; both must clear for either mechanism to fire.

Pure logic tests against step4_profit_taking directly (same style as
bot/_smoke_test_gtp_mrt_profit_invariant.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_zscore_sell_guard.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.steps import step4_profit_taking

# Ascending closes ending at 100.0 (mean=95, stdev~3.742) -> Z_yesterday = (100-95)/3.742 ~ 1.336
_RISING_CLOSES = [90.0, 92.0, 94.0, 96.0, 98.0, 100.0]


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.25,
        max_portfolio_percentage=90.0, alpha_cash_allocation_percentage=40.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, z_score_points=0.5, z_score_upward_points=0.1,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9,
        momentum_reversal_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_dollars=1e9,
        profit_resell_cooldown_days=0,
        z_score_sell_points=0.1,
        sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1e9,  # unreachable -> only the percent gate can fire
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
        minimum_alpha_leader_sell_profit=0.0,
        alpha_leader_least_momentum_score=-1000.0,
        alpha_rank_reduction_percent=10.0,
        min_momentum_score_to_fill_underweight=-1000.0,
        alpha_leader_fresh_position_days=3, alpha_leader_fresh_drawdown_percentage=15.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    """Minimal BrokerClient stub: get_tax_lots (FIFO dollar-gate) + get_daily_closes (the
    z_score_sell_points guard, and the beta benchmark call in step4's Overweight-ranking tail)."""

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
    ctx.alpha_leader = None
    ctx.positions = {sym: Position(symbol=sym, quantity=20.0, avg_cost_basis=50.0)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    lots = {sym: [
        TaxLot(open_lot_id="lot1", quantity=20.0, cost_per_share=50.0, open_date=date(2026, 1, 1), is_selectable=True),
    ]}
    return ctx, _Broker(lots, closes)


def test_sharp_drop_blocks_gtp() -> None:
    """Price dropped sharply today (80.0) off yesterday's close (100.0, top of _RISING_CLOSES).
    Z_yesterday ~ 1.336, Z_today = (80-95)/3.742 ~ -4.008 -> Z_yesterday - Z_today ~ 5.34, well
    over z_score_sell_points (0.1) -> GTP must be blocked even though the percent gate clears
    ((80-50)/50 = +60%) and FIFO is unambiguously profitable."""
    ctx, broker = _ctx_and_broker("DROP", price=80.0, closes=_RISING_CLOSES)
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "DROP"]
    assert any("z_score_sell_points guard active" in r for r in reasons), reasons
    print(f"[zscore-sell-blocks-sharp-drop] {reasons[0]}")


def test_flat_or_rising_price_allows_gtp() -> None:
    """Price at/above yesterday's close (105.0 vs. yesterday's 100.0) -> Z_today ends up above
    Z_yesterday -> Z_yesterday - Z_today is negative, comfortably clears z_score_sell_points ->
    GTP fires normally."""
    ctx, broker = _ctx_and_broker("RISE", price=105.0, closes=_RISING_CLOSES)
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.symbol == "RISE"
    assert t.realized_profit_dollars == (105.0 - 50.0) * 10.0  # profit_sell_percentage=50% of 20
    print(f"[zscore-sell-allows-rise] FIFO realized ${t.realized_profit_dollars:.2f} — fires as expected")


def test_insufficient_history_fails_closed() -> None:
    """No price history at all (empty closes) -> both Z-scores are None -> guard fails closed
    (blocks the sale) even though the percent gate and FIFO dollars both clear."""
    ctx, broker = _ctx_and_broker("NOHIST", price=80.0, closes=[])
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "NOHIST"]
    assert any("z_score_sell_points guard active" in r for r in reasons), reasons
    print("[zscore-sell-fails-closed] empty price history -> guard blocks rather than assuming a pass")


def test_sharp_drop_blocks_mrt() -> None:
    """Same sharp-drop setup, routed through Momentum Reversal Trim instead: downtrend confirmed
    (Momentum_Score <= momentum_reversal_threshold) and the margin gate clears, but the
    z_score_sell_points guard still blocks it."""
    from bot.models import MomentumScore

    ctx, broker = _ctx_and_broker(
        "MRTDROP", price=80.0, closes=_RISING_CLOSES,
        meta_overrides={"materialize_profit_percentage": 1e9},  # keep GTP out of the way
    )
    ctx.momentum_scores = {"MRTDROP": MomentumScore(
        symbol="MRTDROP", rsi14=20.0, ema9_now=70.0, ema9_prior=90.0,
        price_vs_ema_pct=0.0, ema_slope_pct=-30.0,  # score = -60 <= -10 threshold
    )}
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "MRTDROP"]
    assert any("z_score_sell_points guard active" in r for r in reasons), reasons
    print(f"[zscore-sell-blocks-mrt] {reasons[0]}")


def main() -> None:
    test_sharp_drop_blocks_gtp()
    test_flat_or_rising_price_allows_gtp()
    test_insufficient_history_fails_closed()
    test_sharp_drop_blocks_mrt()
    print("\nSMOKE TEST (z_score_sell_points guard) PASSED")


if __name__ == "__main__":
    main()
