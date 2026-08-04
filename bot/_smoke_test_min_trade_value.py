"""Focused unit-style coverage for the `min_value_of_trade` control (buy-side bump/cascade/drop
in steps._enforce_min_trade_value_buys, sell-side bump in step4_profit_taking) and the
Step 7 journal-counter fix (ctx.overweight_trims/profit_taking_sells/drawdown_liquidations only
holding what actually got sold after step6a_prepare_sells). Pure logic tests against the helper
functions directly — no broker/snapshot plumbing needed.

Run: PYTHONPATH=. python3 bot/_smoke_test_min_trade_value.py
"""
from __future__ import annotations

import math
from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, SkippedTrade, TaxLot, TradeIntent
from bot.steps import _enforce_min_trade_value_buys, round_sell_quantity, step4_profit_taking


class _TaxLotOnlyBroker:
    """Minimal BrokerClient stub for step4_profit_taking: only get_tax_lots (for the FIFO
    dollar-gate) and get_daily_closes (unconditionally called once for the beta benchmark in
    step4's Overweight-ranking tail, even when there are no Overweight candidates) are needed."""

    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        return []


def _minimal_ctx(alpha_leader: str | None = None, targets: dict | None = None) -> RunContext:
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
    cfg = PortfolioConfig(meta=meta, targets=targets or {}, force_sell=[], blocked=[])
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


def _bump_target_3dp(min_trade_value: float, price: float) -> float:
    """Mirrors step4_profit_taking's exact two-stage bump target: round UP to the 3rd decimal
    (not nearest) so the intermediate figure still clears the floor, then hand off to
    round_sell_quantity for the whole-share specified-lot-order rounding."""
    return math.ceil(min_trade_value / price * 1000 - 1e-9) / 1000


def test_sell_bump_matches_user_example() -> None:
    """User's own example, refined: profit_sell_percentage produces 2 shares @ $35 = $70
    (< $100 floor). The bump target is 100/35 = 2.857142... shares, rounded UP to the 3rd
    decimal (not nearest — a plain round(2.857142, 3) gives 2.857, i.e. $99.995, which still
    falls short) so it becomes 2.858 ($100.03). That 3-decimal figure then goes through
    round_sell_quantity — the same whole-share lot-rounding fix specified-lot sell orders
    require — which rounds 2.858 to 3 whole shares (1 more share is held). Final: 3 shares =
    $105."""
    sell_qty = round_sell_quantity(2.0, 3.0)  # profit_sell_percentage slice = 2 shares
    price = 35.0
    min_trade_value = 100.0
    assert sell_qty * price == 70.0

    target_3dp = _bump_target_3dp(min_trade_value, price)
    assert target_3dp == 2.858, target_3dp
    assert round(target_3dp * price, 2) == 100.03  # confirms 2.858, not a naive round-to-3dp

    bumped = max(sell_qty, round_sell_quantity(target_3dp, 3.0))
    assert bumped == 3.0, bumped
    assert bumped * price == 105.0
    print(f"[sell-bump] {sell_qty} shares (${sell_qty*price}) -> target {target_3dp} -> {bumped} shares (${bumped*price})")


def test_sell_bump_capped_at_shares_held() -> None:
    """If bumping to the floor would need more shares than are actually held, round_sell_quantity
    caps at what's held (still short of the floor) — the caller then skips the sale."""
    sell_qty = round_sell_quantity(1.0, 1.0)  # only 1 share held, all of it in the slice
    price = 35.0
    min_trade_value = 100.0
    target_3dp = _bump_target_3dp(min_trade_value, price)
    bumped = max(sell_qty, round_sell_quantity(target_3dp, 1.0))
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


def test_fractional_position_falls_back_to_ordinary_order() -> None:
    """The exact scenario raised in review: a position whose ENTIRE remaining balance is a
    sub-whole-share quantity (e.g. 0.5 MU shares left after a fractional buy). A specified-lot
    sell can never work here (round_sell_quantity would floor everything to 0 shares forever),
    so GET THE PROFITS should still fire, sized in raw fractional shares, going out as an
    ordinary order (tax_lots=None) rather than being permanently blocked."""
    targets = {"MU": AssetTarget(symbol="MU", weight=1.0)}
    ctx = _minimal_ctx(targets=targets)
    ctx.positions = {"MU": Position(symbol="MU", quantity=0.5, avg_cost_basis=600.0)}
    ctx.quotes = {"MU": Quote(symbol="MU", last_trade_price=850.0)}  # +41.67% unrealized gain
    lots = {"MU": [TaxLot(open_lot_id="mu-1", quantity=0.5, cost_per_share=600.0,
                           open_date=date(2026, 7, 1), is_selectable=True)]}
    broker = _TaxLotOnlyBroker(lots)

    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.symbol == "MU"
    assert t.tax_lots is None, "sub-whole-share position must go out as an ordinary order"
    assert t.quantity == 0.25, t.quantity  # profit_sell_percentage=50% of 0.5 shares, unrounded
    assert round(t.quantity * 850.0, 2) == 212.5, "well above the $100 floor, no bump needed"
    assert "ordinary order" in t.reason
    print(f"[fractional-position-fallback] MU sold {t.quantity} shares (tax_lots={t.tax_lots}) — {t.reason}")


def test_fractional_position_still_skipped_if_unreachable() -> None:
    """Same sub-whole-share position, but priced low enough that even selling all 0.5 shares
    can't clear the $100 min_value_of_trade floor -> skipped, not placed under the floor."""
    targets = {"MU": AssetTarget(symbol="MU", weight=1.0)}
    ctx = _minimal_ctx(targets=targets)
    ctx.positions = {"MU": Position(symbol="MU", quantity=0.5, avg_cost_basis=100.0)}
    ctx.quotes = {"MU": Quote(symbol="MU", last_trade_price=150.0)}  # +50% gain, but 0.5*150=$75
    lots = {"MU": [TaxLot(open_lot_id="mu-1", quantity=0.5, cost_per_share=100.0,
                           open_date=date(2026, 7, 1), is_selectable=True)]}
    broker = _TaxLotOnlyBroker(lots)

    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    assert any(
        s.symbol == "MU" and "fractional share(s) held" in s.reason and "min_value_of_trade" in s.reason
        for s in ctx.skipped
    ), ctx.skipped
    print("[fractional-position-unreachable] MU (0.5 sh @ $150 = $75) correctly skipped, not under-floored")


def main() -> None:
    test_buy_bump_within_budget()
    test_buy_cascading_drop_when_pool_too_small()
    test_buy_alpha_leader_always_protected_first()
    test_buy_noop_when_min_value_zero()
    test_sell_bump_matches_user_example()
    test_sell_bump_capped_at_shares_held()
    test_journal_counter_ctx_filtering()
    test_fractional_position_falls_back_to_ordinary_order()
    test_fractional_position_still_skipped_if_unreachable()
    print("\nSMOKE TEST (min_value_of_trade + journal counter) PASSED")


if __name__ == "__main__":
    main()
