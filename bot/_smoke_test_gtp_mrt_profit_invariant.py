"""Regression coverage for the v2.66.0 fix: GET THE PROFITS and Momentum Reversal Trim must
never realize an actual FIFO-matched dollar loss, even when the percent/margin gate — which is
based on avg_cost_basis, a whole-position BLENDED average — passes on paper.

The gap this closes: a position built at DECREASING cost over time (expensive shares bought
first, cheaper shares bought later) can show a positive raw_gain_pct against the blended average
while FIFO — which always disposes of the OLDEST lots first — actually sells the expensive shares
first, realizing a real dollar loss on the specific lots consumed. Before this fix, GTP/MRT fired
in that case (the percent gate alone was enough via the OR-gate semantics, with no check that the
FIFO-matched dollars were actually positive). Both mechanisms now require
`fifo.fully_covered and fifo.realized_profit_dollars > 0` unconditionally, on top of whichever
gate (percent/margin or dollar) actually passed.

Pure logic tests against step4_profit_taking directly, no snapshot/CLI plumbing needed (same
style as bot/_smoke_test_min_trade_value.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_gtp_mrt_profit_invariant.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import MomentumScore, Position, Quote, RunContext, TaxLot
from bot.steps import step4_profit_taking


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
        profit_resell_cooldown_days=15,
        z_score_sell_points=0.1,
        sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1e9,  # unreachable -> only the percent gate can fire in GTP tests
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
    """Minimal BrokerClient stub: only get_tax_lots (FIFO dollar-gate) and get_daily_closes
    (unconditionally called once for the beta benchmark in step4's Overweight-ranking tail) are
    needed."""

    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        # Mildly oscillating series well below every test's sell price (all $80 or $100 vs. a
        # ~$60 basis) so the new z_score_sell_points guard (Z_yesterday - Z_today < threshold)
        # passes trivially: Z_today is far above Z_yesterday, giving a strongly negative diff.
        return [58.0, 58.5, 59.0, 59.5, 60.0]


def _decreasing_cost_position(sym: str, price: float, meta_overrides: dict | None = None) -> tuple:
    """Position built at DECREASING cost: 10 old shares @ $100 (bought first, so FIFO-oldest),
    10 new shares @ $50 (bought later). Blended avg_cost_basis = $75 — the setup that exposes the
    gap between the percent gate (blended average) and the true FIFO-matched dollars."""
    targets = {sym: AssetTarget(symbol=sym, weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(**(meta_overrides or {})), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 11), config=cfg, account_number="TEST")
    ctx.alpha_leader = None
    ctx.positions = {sym: Position(symbol=sym, quantity=20.0, avg_cost_basis=75.0)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    lots = {sym: [
        TaxLot(open_lot_id="old", quantity=10.0, cost_per_share=100.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="new", quantity=10.0, cost_per_share=50.0, open_date=date(2026, 6, 1), is_selectable=True),
    ]}
    return ctx, _Broker(lots)


def test_gtp_refuses_to_sell_at_fifo_loss() -> None:
    """price=$80 -> raw_gain_pct=+6.67% clears materialize_profit_percentage (2.5%) on the
    blended average, but FIFO sells the $100 lot first at $80 -> realized $-200. Must NOT fire."""
    ctx, broker = _decreasing_cost_position("XYZ", price=80.0)
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    assert ctx.loss_sale_symbols == [], ctx.loss_sale_symbols  # never armed -> nothing to arm
    reasons = [s.reason for s in ctx.skipped if s.symbol == "XYZ"]
    assert any("not a real profit" in r and "refusing to sell at a loss" in r for r in reasons), reasons
    print("[gtp-refuses-fifo-loss] percent gate passes on blended average (+6.67%) but FIFO would "
          "realize $-200 -> correctly refused, no sale placed")


def test_mrt_refuses_to_sell_at_fifo_loss() -> None:
    """Same decreasing-cost setup, but routed through Momentum Reversal Trim instead: downtrend
    confirmed (Momentum_Score <= momentum_reversal_threshold) and the margin gate clears on the
    blended average, but FIFO on the oldest lot is still a loss. Must NOT fire."""
    ctx, broker = _decreasing_cost_position(
        "ABC", price=80.0, meta_overrides={"materialize_profit_percentage": 1e9},  # keep GTP out of the way
    )
    ctx.momentum_scores = {"ABC": MomentumScore(
        symbol="ABC", rsi14=20.0, ema9_now=70.0, ema9_prior=90.0,
        price_vs_ema_pct=0.0, ema_slope_pct=-30.0,  # score = 0 + (-30) + (20-50) = -60 <= -10 threshold
    )}
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    assert ctx.loss_sale_symbols == [], ctx.loss_sale_symbols
    reasons = [s.reason for s in ctx.skipped if s.symbol == "ABC"]
    assert any("not a real profit" in r and "refusing to sell at a loss" in r for r in reasons), reasons
    print("[mrt-refuses-fifo-loss] margin gate passes on blended average but FIFO would realize a "
          "loss -> correctly refused, no trim placed")


def test_gtp_still_fires_when_fifo_is_genuinely_profitable() -> None:
    """Sanity check the fix didn't over-tighten anything: a position built at INCREASING cost
    (cheap shares first, expensive later) has FIFO consume the CHEAP lot first, so the realized
    dollars are unambiguously positive and the sale should still fire normally."""
    targets = {"INC": AssetTarget(symbol="INC", weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 11), config=cfg, account_number="TEST")
    ctx.alpha_leader = None
    ctx.positions = {"INC": Position(symbol="INC", quantity=20.0, avg_cost_basis=75.0)}
    ctx.quotes = {"INC": Quote(symbol="INC", last_trade_price=80.0)}
    lots = {"INC": [
        TaxLot(open_lot_id="cheap", quantity=10.0, cost_per_share=50.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="expensive", quantity=10.0, cost_per_share=100.0, open_date=date(2026, 6, 1), is_selectable=True),
    ]}
    broker = _Broker(lots)
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.realized_profit_dollars == 300.0, t.realized_profit_dollars  # (80-50)*10 from the FIFO-first cheap lot
    print(f"[gtp-still-fires-genuine-profit] FIFO realized ${t.realized_profit_dollars:.2f} — fires as expected")


def test_mrt_still_fires_when_fifo_is_genuinely_profitable() -> None:
    targets = {"INC2": AssetTarget(symbol="INC2", weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(materialize_profit_percentage=1e9), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 11), config=cfg, account_number="TEST")
    ctx.alpha_leader = None
    ctx.positions = {"INC2": Position(symbol="INC2", quantity=20.0, avg_cost_basis=75.0)}
    ctx.quotes = {"INC2": Quote(symbol="INC2", last_trade_price=80.0)}
    ctx.momentum_scores = {"INC2": MomentumScore(
        symbol="INC2", rsi14=20.0, ema9_now=70.0, ema9_prior=90.0,
        price_vs_ema_pct=0.0, ema_slope_pct=-30.0,
    )}
    lots = {"INC2": [
        TaxLot(open_lot_id="cheap", quantity=10.0, cost_per_share=50.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="expensive", quantity=10.0, cost_per_share=100.0, open_date=date(2026, 6, 1), is_selectable=True),
    ]}
    broker = _Broker(lots)
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.realized_profit_dollars == 300.0, t.realized_profit_dollars
    print(f"[mrt-still-fires-genuine-profit] FIFO realized ${t.realized_profit_dollars:.2f} — fires as expected")


def test_gtp_refuses_at_exact_breakeven() -> None:
    """FIFO-matched realized profit of exactly $0.00 (breakeven) must also be refused — the guard
    is `> 0`, not `>= 0`, since a breakeven sale is not a real profit either."""
    targets = {"FLAT": AssetTarget(symbol="FLAT", weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 11), config=cfg, account_number="TEST")
    ctx.alpha_leader = None
    # avg_cost_basis=75 (blended) but the single lot actually held costs exactly today's price
    ctx.positions = {"FLAT": Position(symbol="FLAT", quantity=20.0, avg_cost_basis=75.0)}
    ctx.quotes = {"FLAT": Quote(symbol="FLAT", last_trade_price=80.0)}
    lots = {"FLAT": [
        TaxLot(open_lot_id="breakeven", quantity=20.0, cost_per_share=80.0, open_date=date(2026, 1, 1), is_selectable=True),
    ]}
    broker = _Broker(lots)
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "FLAT"]
    assert any("not a real profit" in r for r in reasons), reasons
    print("[gtp-refuses-breakeven] FIFO realized exactly $0.00 -> correctly refused (not > 0)")


def main() -> None:
    test_gtp_refuses_to_sell_at_fifo_loss()
    test_mrt_refuses_to_sell_at_fifo_loss()
    test_gtp_still_fires_when_fifo_is_genuinely_profitable()
    test_mrt_still_fires_when_fifo_is_genuinely_profitable()
    test_gtp_refuses_at_exact_breakeven()
    print("\nSMOKE TEST (GTP/MRT FIFO-vs-blended-average profit invariant) PASSED")


if __name__ == "__main__":
    main()
