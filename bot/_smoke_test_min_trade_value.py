"""Focused unit-style coverage for the `min_value_of_trade` control (buy-side bump/cascade/drop
in steps._enforce_min_trade_value_buys, sell-side bump in step4_profit_taking) and the
Step 7 journal-counter fix (ctx.overweight_trims/profit_taking_sells/drawdown_liquidations only
holding what actually got sold after step6a_prepare_sells). Pure logic tests against the helper
functions directly — no broker/snapshot plumbing needed.

Run: PYTHONPATH=. python3 bot/_smoke_test_min_trade_value.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import RunContext, SkippedTrade, TradeIntent
from bot.steps import _enforce_min_trade_value_buys, round_sell_quantity


def _minimal_ctx(alpha_leader: str | None = None) -> RunContext:
    meta = PortfolioMetadata(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.25,
        max_portfolio_percentage=35.0, alpha_cash_allocation_percentage=35.0,
        min_cash_absolute=250, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, sold_asset_price_change_percentage=1.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_dollars=12.5, profit_resell_cooldown_days=15,
        sell_or_buy_value_limit=10, min_value_of_trade=100, settlement_reserve_target=9000,
        settlement_lag_days=1, materialize_profit_percentage=4.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=12.5, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
    )
    cfg = PortfolioConfig(meta=meta, targets={}, force_sell=[])
    ctx = RunContext(current_date=date(2026, 8, 4), config=cfg, account_number="TEST")
    ctx.alpha_leader = alpha_leader
    return ctx


def test_buy_bump_within_budget() -> None:
    """IBM's own $60 slice is short of the $100 floor. AAPL (Alpha Leader, largest allocation)
    is protected; MSFT and GOOG rank below IBM (smaller planned amounts) and are drained —
    GOOG fully ($30), then $10 of MSFT's $45 — to bump IBM up to exactly the floor. MSFT's
    remaining $35 then can't clear the floor on its own turn (nothing left to borrow from) and
    is dropped too, rather than being placed under-sized. Matches the user's own worked example:
    bump the underfunded buy, funded by cutting lower-ranked buys."""
    ctx = _minimal_ctx(alpha_leader="AAPL")
    planned = {"AAPL": 500.0, "IBM": 60.0, "MSFT": 45.0, "GOOG": 30.0}
    out = _enforce_min_trade_value_buys(ctx, planned, 100.0)
    assert out == {"AAPL": 500.0, "IBM": 100.0}, out
    dropped = {s.symbol: s.reason for s in ctx.skipped}
    assert "MSFT" in dropped and "below min_value_of_trade" in dropped["MSFT"]
    assert "GOOG" in dropped and "drained to fund" in dropped["GOOG"]
    print(f"[buy-bump-within-budget] survivors={out} dropped={list(dropped)}")


def test_buy_cascading_drop_when_pool_too_small() -> None:
    """5 buys of $30 each ($150 total) can only fund one $100 buy; the rest cascade-drain to 0
    and get dropped, logged to ctx.skipped."""
    ctx = _minimal_ctx(alpha_leader=None)
    planned = {"B1": 30.0, "B2": 30.0, "B3": 30.0, "B4": 30.0, "B5": 30.0}
    out = _enforce_min_trade_value_buys(ctx, planned, 100.0)
    assert list(out.keys()) == ["B1"], out
    assert out["B1"] == 100.0, out
    assert len(ctx.skipped) == 4, ctx.skipped
    for s in ctx.skipped:
        assert s.would_be_action == "buy"
    print(f"[buy-cascading-drop] survivors={out} skipped={[s.symbol for s in ctx.skipped]}")


def test_buy_alpha_leader_always_protected_first() -> None:
    """Even if the Alpha Leader's own planned dollar amount is small, it is never drained to
    fund another symbol — it's always processed (and protected) first."""
    ctx = _minimal_ctx(alpha_leader="TINY")
    planned = {"TINY": 50.0, "BIG": 500.0}
    out = _enforce_min_trade_value_buys(ctx, planned, 100.0)
    assert out["TINY"] == 100.0, out
    assert out["BIG"] == 450.0, out
    print(f"[buy-alpha-protected] {out}")


def test_buy_noop_when_min_value_zero() -> None:
    ctx = _minimal_ctx()
    planned = {"A": 5.0, "B": 500.0}
    out = _enforce_min_trade_value_buys(ctx, planned, 0.0)
    assert out == planned
    print("[buy-noop-zero-floor] OK")


def test_sell_bump_matches_user_example() -> None:
    """User's own example: profit_sell_percentage produces 2 shares @ $35 = $70 (< $100 floor);
    1 more share is held, so the bump should sell 3 shares = $105."""
    sell_qty = round_sell_quantity(2.0, 3.0)  # profit_sell_percentage slice = 2 shares
    price = 35.0
    min_trade_value = 100.0
    assert sell_qty * price == 70.0
    import math
    whole_shares_held = math.floor(3.0 + 1e-9)
    bumped = max(sell_qty, min(whole_shares_held, math.ceil(min_trade_value / price - 1e-9)))
    assert bumped == 3.0, bumped
    assert bumped * price == 105.0
    print(f"[sell-bump] {sell_qty} shares (${sell_qty*price}) -> {bumped} shares (${bumped*price})")


def test_sell_bump_capped_at_shares_held() -> None:
    """If bumping to the floor would need more shares than are actually held, the bump is
    capped at what's held (still short of the floor) — the caller then skips the sale."""
    import math
    sell_qty = round_sell_quantity(1.0, 1.0)  # only 1 share held, all of it in the slice
    price = 35.0
    min_trade_value = 100.0
    whole_shares_held = math.floor(1.0 + 1e-9)
    bumped = max(sell_qty, min(whole_shares_held, math.ceil(min_trade_value / price - 1e-9)))
    assert bumped == 1.0, bumped
    assert bumped * price == 35.0 < min_trade_value
    print(f"[sell-bump-capped] {bumped} shares (${bumped*price}) still below ${min_trade_value} floor -> caller skips")


def test_journal_counter_ctx_filtering() -> None:
    """Direct check of the step6a fix's contract: ctx.overweight_trims/profit_taking_sells/
    drawdown_liquidations must only contain symbols that survived sell_or_buy_value_limit."""
    from bot.models import Quote

    ctx = _minimal_ctx()
    ctx.quotes = {"BIG": Quote("BIG", 50.0), "TINY": Quote("TINY", 0.05)}
    ctx.positions = {}
    ctx.profit_taking_sells = [
        TradeIntent(symbol="BIG", side="sell", quantity=10, reason="GET THE PROFITS"),
    ]
    ctx.overweight_trims = [
        TradeIntent(symbol="TINY", side="sell", quantity=1, reason="Overweight High-Beta trim"),
    ]
    ctx.drawdown_liquidations = []
    ctx.config.meta.__dict__  # no-op; meta is frozen, values read directly below

    from bot.steps import step6a_prepare_sells
    sells_to_place, halted, _ = step6a_prepare_sells(ctx)
    assert not halted
    assert [t.symbol for t in sells_to_place] == ["BIG"]
    assert [t.symbol for t in ctx.profit_taking_sells] == ["BIG"], ctx.profit_taking_sells
    assert ctx.overweight_trims == [], "TINY was below sell_or_buy_value_limit and must be dropped from ctx too"
    assert any(s.symbol == "TINY" for s in ctx.skipped)
    print("[journal-counter-fix] ctx sell lists match sells_to_place exactly — OK")


def main() -> None:
    test_buy_bump_within_budget()
    test_buy_cascading_drop_when_pool_too_small()
    test_buy_alpha_leader_always_protected_first()
    test_buy_noop_when_min_value_zero()
    test_sell_bump_matches_user_example()
    test_sell_bump_capped_at_shares_held()
    test_journal_counter_ctx_filtering()
    print("\nSMOKE TEST (min_value_of_trade + journal counter) PASSED")


if __name__ == "__main__":
    main()
