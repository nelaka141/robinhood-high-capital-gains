"""Focused unit-style coverage for steps.compute_dormant_assets — CLAUDE.md Step 7's
Dormant Assets report (`dormant_asset_days`). Purely observational: never gates a buy/sell
decision, only ever read by journal.py's render functions.

Pure logic tests against RunContext/steps.compute_dormant_assets directly, no snapshot/CLI
plumbing needed (same style as bot/_smoke_test_min_trade_value.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_dormant_assets.py
"""
from __future__ import annotations

from datetime import date, timedelta

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext
from bot.state import AssetPriceState
from bot.steps import compute_dormant_assets

CURRENT_DATE = date(2026, 8, 10)


def _meta(dormant_asset_days: int = 5) -> PortfolioMetadata:
    return PortfolioMetadata(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=1_000_000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=0.0,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0, wash_sale_lookback_days=0,
        dormant_asset_days=dormant_asset_days,
    )


def _ctx(symbols: list, dormant_asset_days: int = 5) -> RunContext:
    cfg = PortfolioConfig(
        meta=_meta(dormant_asset_days), targets={s: AssetTarget(s, weight=1.0) for s in symbols},
        force_sell={}, blocked=[],
    )
    return RunContext(current_date=CURRENT_DATE, config=cfg, account_number="TEST")


def _iso(days_ago: int) -> str:
    return (CURRENT_DATE - timedelta(days=days_ago)).isoformat()


def test_recently_active_not_dormant() -> None:
    ctx = _ctx(["AAPL"])
    ctx.positions = {"AAPL": Position("AAPL", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"AAPL": Quote("AAPL", last_trade_price=110.0)}
    ctx.price_state = {"AAPL": AssetPriceState(lastPurchaseDate=_iso(3))}  # 3d ago, threshold=5
    out = compute_dormant_assets(ctx)
    assert out == [], out
    print("[recently-active] bought 3d ago (threshold 5d) -> not dormant — OK")


def test_boundary_exactly_at_threshold_not_dormant() -> None:
    ctx = _ctx(["AAPL"])
    ctx.positions = {"AAPL": Position("AAPL", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"AAPL": Quote("AAPL", last_trade_price=110.0)}
    ctx.price_state = {"AAPL": AssetPriceState(lastPurchaseDate=_iso(5))}  # exactly threshold
    out = compute_dormant_assets(ctx)
    assert out == [], out
    print("[boundary-at-threshold] days_since == dormant_asset_days (5) -> not dormant (uses >) — OK")


def test_dormant_via_old_purchase() -> None:
    ctx = _ctx(["AAPL"])
    ctx.positions = {"AAPL": Position("AAPL", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"AAPL": Quote("AAPL", last_trade_price=115.0)}
    ctx.price_state = {"AAPL": AssetPriceState(lastPurchaseDate=_iso(10))}  # 10d ago, threshold=5
    out = compute_dormant_assets(ctx)
    assert len(out) == 1, out
    d = out[0]
    assert d.symbol == "AAPL" and d.days_since_activity == 10 and d.last_activity_date == _iso(10)
    assert round(d.unrealized_dollars, 2) == 150.0, d.unrealized_dollars  # (115-100)*10
    assert round(d.unrealized_pct, 2) == 15.0, d.unrealized_pct
    print(f"[dormant-via-purchase] 10d since last buy (threshold 5d) -> dormant, "
          f"unrealized ${d.unrealized_dollars:.2f} ({d.unrealized_pct:+.2f}%) — OK")


def test_last_activity_uses_more_recent_of_purchase_and_profit_sell() -> None:
    ctx = _ctx(["AAPL"])
    ctx.positions = {"AAPL": Position("AAPL", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"AAPL": Quote("AAPL", last_trade_price=90.0)}
    # Bought 30d ago (stale) but partially profit-sold only 2d ago -> NOT dormant, since
    # last_activity = max(lastPurchaseDate, profitSellDate) = 2d ago < threshold.
    ctx.price_state = {"AAPL": AssetPriceState(lastPurchaseDate=_iso(30), profitSellDate=_iso(2))}
    out = compute_dormant_assets(ctx)
    assert out == [], out
    print("[last-activity-max] bought 30d ago but profit-sold 2d ago -> uses the more recent date, not dormant — OK")


def test_never_recorded_is_dormant_with_none_days() -> None:
    ctx = _ctx(["AAPL"])
    ctx.positions = {"AAPL": Position("AAPL", quantity=5.0, avg_cost_basis=200.0)}
    ctx.quotes = {"AAPL": Quote("AAPL", last_trade_price=180.0)}
    ctx.price_state = {"AAPL": AssetPriceState()}  # no lastPurchaseDate, no profitSellDate at all
    out = compute_dormant_assets(ctx)
    assert len(out) == 1, out
    d = out[0]
    assert d.days_since_activity is None and d.last_activity_date is None
    assert round(d.unrealized_dollars, 2) == -100.0, d.unrealized_dollars  # (180-200)*5, a loss
    print("[never-recorded] no lastPurchaseDate/profitSellDate on record -> dormant, days=None — OK")


def test_sorted_most_dormant_first_no_record_sorts_ahead() -> None:
    ctx = _ctx(["OLD", "OLDER", "NEVER"])
    ctx.positions = {
        "OLD": Position("OLD", quantity=1.0, avg_cost_basis=10.0),
        "OLDER": Position("OLDER", quantity=1.0, avg_cost_basis=10.0),
        "NEVER": Position("NEVER", quantity=1.0, avg_cost_basis=10.0),
    }
    ctx.quotes = {s: Quote(s, last_trade_price=12.0) for s in ("OLD", "OLDER", "NEVER")}
    ctx.price_state = {
        "OLD": AssetPriceState(lastPurchaseDate=_iso(6)),
        "OLDER": AssetPriceState(lastPurchaseDate=_iso(20)),
        "NEVER": AssetPriceState(),
    }
    out = compute_dormant_assets(ctx)
    assert [d.symbol for d in out] == ["NEVER", "OLDER", "OLD"], [d.symbol for d in out]
    print(f"[sort-order] {[d.symbol for d in out]} — no-record sorts first, then most-days-dormant — OK")


def test_unresolved_cost_basis_omitted() -> None:
    ctx = _ctx(["AAPL"])
    ctx.positions = {"AAPL": Position("AAPL", quantity=10.0, avg_cost_basis=None)}
    ctx.quotes = {"AAPL": Quote("AAPL", last_trade_price=110.0)}
    ctx.price_state = {"AAPL": AssetPriceState(lastPurchaseDate=_iso(30))}
    out = compute_dormant_assets(ctx)
    assert out == [], out
    print("[cost-basis-pending] avg_cost_basis=None -> omitted from dormant report (Fail-Closed) — OK")


def test_unheld_symbol_omitted() -> None:
    ctx = _ctx(["AAPL"])
    ctx.positions = {"AAPL": Position("AAPL", quantity=0.0, avg_cost_basis=100.0)}
    ctx.quotes = {"AAPL": Quote("AAPL", last_trade_price=110.0)}
    ctx.price_state = {"AAPL": AssetPriceState(lastPurchaseDate=_iso(30))}
    out = compute_dormant_assets(ctx)
    assert out == [], out
    print("[unheld-omitted] quantity=0 -> not currently held, omitted — OK")


def main() -> None:
    test_recently_active_not_dormant()
    test_boundary_exactly_at_threshold_not_dormant()
    test_dormant_via_old_purchase()
    test_last_activity_uses_more_recent_of_purchase_and_profit_sell()
    test_never_recorded_is_dormant_with_none_days()
    test_sorted_most_dormant_first_no_record_sorts_ahead()
    test_unresolved_cost_basis_omitted()
    test_unheld_symbol_omitted()
    print("\nSMOKE TEST (dormant assets) PASSED")


if __name__ == "__main__":
    main()
