"""Focused unit-style coverage for the per-individual-trade `seek_approval_value` halt in
steps.step6a_prepare_sells — replaces the old "sum of all sells this cycle" aggregate check.
Pure logic tests against RunContext directly, no broker/snapshot plumbing needed (same style as
bot/_smoke_test_min_trade_value.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_seek_approval.py
"""
from __future__ import annotations

from datetime import date

from bot.config import PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TradeIntent
from bot.steps import step6a_prepare_sells


def _minimal_ctx(seek_approval_value: float = 1000.0) -> RunContext:
    meta = PortfolioMetadata(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.25,
        max_portfolio_percentage=35.0, alpha_cash_allocation_percentage=35.0,
        min_cash_absolute=250, min_cash_target=500, seek_approval_value=seek_approval_value,
        sell_price_diff_limit=5, buy_price_diff_limit=5, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, z_score_points=0.5, z_score_upward_points=0.1,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=12.5,
        momentum_reversal_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_dollars=12.5,
        profit_resell_cooldown_days=15,
        z_score_sell_points=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=60,
        materialize_profit_percentage=4.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=12.5, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
        minimum_alpha_leader_sell_profit=5.0, alpha_leader_least_momentum_score=-1000.0,
        alpha_rank_reduction_percent=10.0,
        min_momentum_score_to_fill_underweight=-1000.0,
        alpha_leader_fresh_position_days=3, alpha_leader_fresh_drawdown_percentage=15.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    cfg = PortfolioConfig(meta=meta, targets={}, force_sell={}, blocked=[])
    return RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")


def test_many_small_sells_do_not_sum_to_a_halt() -> None:
    """Four sells at $300 each ($1,200 total) — each individually under the $1,000 threshold.
    The OLD aggregate-sum check would have halted (sum > threshold); the new per-trade check
    must not."""
    ctx = _minimal_ctx(seek_approval_value=1000.0)
    ctx.quotes = {s: Quote(symbol=s, last_trade_price=30.0) for s in "ABCD"}
    ctx.profit_taking_sells = [
        TradeIntent(symbol=s, side="sell", quantity=10.0, reason="GET THE PROFITS") for s in "ABCD"
    ]
    sells, halted, reason = step6a_prepare_sells(ctx)
    assert not halted, f"should not halt on 4x$300 sells under a $1000 per-trade threshold, got: {reason}"
    assert len(sells) == 4
    print("[many-small-sells] $1,200 total across 4 sells, each $300 < $1000 threshold -> no halt — OK")


def test_single_oversized_sell_halts() -> None:
    """One sell alone worth $1,500 clears the $1,000 threshold -> halt, even though it's the
    only trade this cycle (old aggregate check would have halted here too, but for the right
    per-trade reason now)."""
    ctx = _minimal_ctx(seek_approval_value=1000.0)
    ctx.quotes = {"BIG": Quote(symbol="BIG", last_trade_price=150.0)}
    ctx.profit_taking_sells = [TradeIntent(symbol="BIG", side="sell", quantity=10.0, reason="GET THE PROFITS")]
    sells, halted, reason = step6a_prepare_sells(ctx)
    assert halted, "a single $1,500 sell should halt against a $1,000 threshold"
    assert "BIG" in reason and "sell" in reason
    print(f"[single-oversized-sell] halted correctly: {reason}")


def test_single_oversized_buy_halts_with_no_sells() -> None:
    """A provisional buy alone worth $1,500 must also halt — the OLD check never looked at buys
    at all, so this is new coverage, not just a rename."""
    ctx = _minimal_ctx(seek_approval_value=1000.0)
    ctx.quotes = {}
    sells, halted, reason = step6a_prepare_sells(ctx, planned_buys={"XYZ": 1500.0})
    assert halted, "a single $1,500 planned buy should halt against a $1,000 threshold"
    assert "XYZ" in reason and "buy" in reason
    print(f"[single-oversized-buy] halted correctly: {reason}")


def test_excluded_buy_does_not_falsely_halt() -> None:
    """A planned buy for a symbol that's ALSO selling this cycle (same-cycle buy/sell
    exclusivity — it will never actually be placed, per step6b's own filtering) must not trigger
    a halt just because its raw provisional dollar figure is large. Its own (small) sell must
    not halt either."""
    ctx = _minimal_ctx(seek_approval_value=1000.0)
    ctx.quotes = {"Y": Quote(symbol="Y", last_trade_price=5.0)}
    ctx.overweight_trims = [TradeIntent(symbol="Y", side="sell", quantity=10.0, reason="Overweight trim")]  # $50
    sells, halted, reason = step6a_prepare_sells(ctx, planned_buys={"Y": 1500.0})
    assert not halted, f"a buy excluded by same-cycle sell should never reach the halt check, got: {reason}"
    assert len(sells) == 1 and sells[0].symbol == "Y"
    print("[excluded-buy-same-symbol-sell] $1,500 phantom buy for a symbol also selling -> no halt — OK")


def test_blocked_buy_does_not_falsely_halt() -> None:
    """A planned buy for a `blocked` symbol will never actually be placed either — must not
    trigger a halt."""
    ctx = _minimal_ctx(seek_approval_value=1000.0)
    ctx.quotes = {}
    ctx.blocked_symbols = {"Z": "frozen"}
    sells, halted, reason = step6a_prepare_sells(ctx, planned_buys={"Z": 1500.0})
    assert not halted, f"a buy for a blocked symbol should never reach the halt check, got: {reason}"
    print("[excluded-buy-blocked] $1,500 phantom buy for a blocked symbol -> no halt — OK")


def test_mixed_small_sells_and_one_big_buy_halts_on_the_buy() -> None:
    """Sells are all individually small (no sell-side halt), but one provisional buy is
    oversized -> the cycle still halts, on the buy."""
    ctx = _minimal_ctx(seek_approval_value=1000.0)
    ctx.quotes = {"A": Quote(symbol="A", last_trade_price=30.0)}
    ctx.profit_taking_sells = [TradeIntent(symbol="A", side="sell", quantity=10.0, reason="GET THE PROFITS")]  # $300
    sells, halted, reason = step6a_prepare_sells(ctx, planned_buys={"NVDA": 2000.0})
    assert halted, "an oversized buy should halt even when all sells are individually small"
    assert "NVDA" in reason and "buy" in reason
    print(f"[mixed-small-sells-big-buy] halted correctly on the buy: {reason}")


def main() -> None:
    test_many_small_sells_do_not_sum_to_a_halt()
    test_single_oversized_sell_halts()
    test_single_oversized_buy_halts_with_no_sells()
    test_excluded_buy_does_not_falsely_halt()
    test_blocked_buy_does_not_falsely_halt()
    test_mixed_small_sells_and_one_big_buy_halts_on_the_buy()
    print("\nSMOKE TEST (per-trade seek_approval_value) PASSED")


if __name__ == "__main__":
    main()
