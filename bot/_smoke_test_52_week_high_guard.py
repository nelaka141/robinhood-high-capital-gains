"""Focused coverage for the `52_week_high_guard` control (bot/steps.py::step5_price_limits): a
planned buy — Underweight allocation or Alpha Multiplier allocation alike, since Step 5 operates
on the single merged buy_candidates dict from Step 3 — is blocked whenever
`current_price / fifty_two_week_high > 52_week_high_guard`% of the 52-week high. Missing 52-week
high data (broker.get_fifty_two_week_high returns None) fails OPEN (allows the buy), matching the
existing buy_price_diff_limit/sell_price_diff_limit posture elsewhere in this same function.

Pure logic tests against step5_price_limits directly (same style as
bot/_smoke_test_selling_price_guard.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_52_week_high_guard.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Quote, RunContext
from bot.steps import step5_price_limits


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=1000, buy_price_diff_limit=1000, fifty_two_week_high_guard=95.0,
        no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg1_price_change=0.5, leg2_price_change=0.5, leg3_price_change=0.1,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9,
        profit_resell_cooldown_days=0,
        selling_price_change=1.0,
        sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1e9,
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
    """Minimal BrokerClient stub: get_daily_lows_highs (buy_price_diff_limit — the low is pinned
    to the test's own price so pump_pct is always 0%, keeping this guard fully out of the way) +
    get_fifty_two_week_high (the guard under test)."""

    def __init__(self, highs: dict, price: float):
        self._highs = highs
        self._price = price

    def get_daily_lows_highs(self, symbol: str, start, end):
        return [(self._price, self._price)]  # pump_pct == 0% -> never trips buy_price_diff_limit

    def get_fifty_two_week_high(self, symbol: str):
        return self._highs.get(symbol)


def _ctx(sym: str, price: float) -> RunContext:
    targets = {sym: AssetTarget(symbol=sym, weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 13), config=cfg, account_number="TEST")
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    return ctx


def test_price_above_guard_blocks_buy() -> None:
    """52-week high $100, guard 95% -> ceiling $95.00. Price $96 is 96% of the high -> blocked,
    for both an Underweight-style and an Alpha-style dollar amount alike (Step 5 doesn't
    distinguish — it's the same merged dict)."""
    ctx = _ctx("HIGH", price=96.0)
    broker = _Broker({"HIGH": 100.0}, price=96.0)
    kept = step5_price_limits(ctx, broker, {"HIGH": 500.0})
    assert kept == {}, kept
    reasons = [s.reason for s in ctx.skipped if s.symbol == "HIGH"]
    assert any("52_week_high_guard" in r for r in reasons), reasons
    print(f"[52wk-guard-blocks] {reasons[0]}")


def test_price_at_or_below_guard_allows_buy() -> None:
    """Price exactly at the 95% ceiling ($95 of a $100 high) clears the guard (not strictly
    greater than the limit) -> buy proceeds."""
    ctx = _ctx("ATLIMIT", price=95.0)
    broker = _Broker({"ATLIMIT": 100.0}, price=95.0)
    kept = step5_price_limits(ctx, broker, {"ATLIMIT": 500.0})
    assert kept == {"ATLIMIT": 500.0}, kept
    print("[52wk-guard-at-limit-allows] price exactly at 95% of 52-week high -> buy proceeds")


def test_price_well_under_guard_allows_buy() -> None:
    ctx = _ctx("LOW", price=60.0)
    broker = _Broker({"LOW": 100.0}, price=60.0)
    kept = step5_price_limits(ctx, broker, {"LOW": 500.0})
    assert kept == {"LOW": 500.0}, kept
    print("[52wk-guard-well-under-allows] 60% of 52-week high -> buy proceeds")


def test_missing_52_week_high_fails_open() -> None:
    """No 52-week-high data available (broker returns None) -> guard fails OPEN, same posture as
    buy_price_diff_limit/sell_price_diff_limit elsewhere in step5_price_limits when historical
    data is unavailable."""
    ctx = _ctx("NOHIGH", price=9999.0)
    broker = _Broker({}, price=9999.0)  # NOHIGH not in highs -> get_fifty_two_week_high returns None
    kept = step5_price_limits(ctx, broker, {"NOHIGH": 500.0})
    assert kept == {"NOHIGH": 500.0}, kept
    print("[52wk-guard-fails-open] missing 52-week high -> guard does not block (fail-open)")


def main() -> None:
    test_price_above_guard_blocks_buy()
    test_price_at_or_below_guard_allows_buy()
    test_price_well_under_guard_allows_buy()
    test_missing_52_week_high_fails_open()
    print("\nSMOKE TEST (52_week_high_guard) PASSED")


if __name__ == "__main__":
    main()
