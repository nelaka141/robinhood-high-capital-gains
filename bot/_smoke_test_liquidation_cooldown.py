"""Coverage for the post-liquidation re-buy cooldown (CLAUDE.md `cool_down_period_after_lquidation`,
v2.92.0: 60 days).

A symbol sold by a Drawdown Audit (or blocked+forceSell) liquidation carries liquidatedPrice/
liquidatedDate in peak/prices.json. While it is unheld, step2_guardrails excludes it from ALL
play (no score, no Underweight fill, no Position Cap Top-Up) until BOTH the cooldown has elapsed
AND the price has recovered `min_recovery_price_percentage` above liquidatedPrice.

1. The live portfolio_targets.json sets the cooldown to at least 60 days.
2. Inside the window the symbol stays excluded even after a full price recovery.
3. From day 60 on, it is back in play once recovered — and still excluded if not recovered.

Run: PYTHONPATH=. python3 bot/_smoke_test_liquidation_cooldown.py
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata, load_portfolio_config
from bot.models import Quote, RunContext
from bot.state import AssetPriceState
from bot import steps

LIQ_DATE = date(2026, 10, 30)
LIQ_PRICE = 29.02


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=1_000_000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=60,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        # Permissive buy-timing legs: this file covers the liquidation gate only.
        sold_asset_repurchase_days=2, leg1_price_change=-999.0, leg2_price_change=-999.0, leg3_price_change=-999.0,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=0.0,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, min_raw_gain_percent_to_sell=-1e9,
        keep_aside_profits_for_tax_percent=35.0,
        momentum_lookback_days=5, min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=30,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    def get_daily_closes(self, symbol, start, end):
        return [30.0, 31.0, 30.5]


def _ctx(days_after: int, price: float) -> RunContext:
    cfg = PortfolioConfig(
        meta=_meta(), targets={"IONQ": AssetTarget("IONQ", weight=1.0)}, force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=LIQ_DATE + timedelta(days=days_after), config=cfg, account_number="TEST")
    ctx.price_state = {
        "IONQ": AssetPriceState(
            liquidatedPrice=LIQ_PRICE, liquidatedDate=LIQ_DATE.isoformat(),
            lastLossSalePrice=LIQ_PRICE, lastLossSaleDate=LIQ_DATE.isoformat(),
        ),
    }
    ctx.positions = {}  # fully liquidated
    ctx.quotes = {"IONQ": Quote("IONQ", last_trade_price=price)}
    ctx.excluded_symbols = {}
    ctx.buy_guarded_symbols = {}
    steps.step2_guardrails(ctx, _Broker())
    return ctx


def test_live_config_cooldown_is_at_least_60_days() -> None:
    cfg = load_portfolio_config(Path(__file__).resolve().parent.parent / "portfolio_targets.json")
    assert cfg.meta.cool_down_period_after_lquidation >= 60, cfg.meta.cool_down_period_after_lquidation
    print(f"[live-config] cool_down_period_after_lquidation = {cfg.meta.cool_down_period_after_lquidation}d — OK")


def test_excluded_inside_window_even_when_recovered() -> None:
    recovered = LIQ_PRICE * 1.5
    for days in (1, 31, 45, 59):
        ctx = _ctx(days, recovered)
        assert "IONQ" in ctx.excluded_symbols, (days, ctx.excluded_symbols)
        assert "IONQ" not in steps.in_play_symbols(ctx)
    print("[inside-window] excluded on days 1/31/45/59 despite +50% recovery — OK")


def test_back_in_play_from_day_60_once_recovered() -> None:
    ctx = _ctx(60, LIQ_PRICE * 1.06)
    assert "IONQ" not in ctx.excluded_symbols, ctx.excluded_symbols
    assert "IONQ" not in ctx.buy_guarded_symbols, ctx.buy_guarded_symbols  # wash-sale window (30d) long gone
    print("[day-60-recovered] back in play — OK")


def test_still_excluded_at_day_60_without_recovery() -> None:
    ctx = _ctx(60, LIQ_PRICE * 1.02)
    assert "IONQ" in ctx.excluded_symbols, ctx.excluded_symbols
    print("[day-60-not-recovered] still excluded (needs +5% over liquidation price) — OK")


if __name__ == "__main__":
    test_live_config_cooldown_is_at_least_60_days()
    test_excluded_inside_window_even_when_recovered()
    test_back_in_play_from_day_60_once_recovered()
    test_still_excluded_at_day_60_without_recovery()
    print("\nSMOKE TEST (post-liquidation re-buy cooldown, v2.92.0) PASSED")
