"""Focused coverage for the "Zero-available-lots fallback" (v2.79.0) in step4_profit_taking:
when LITERALLY ZERO of a symbol's tax lots are priced+selectable yet (most commonly because the
entire current position is a same-day buy still syncing broker-side), GET THE PROFITS should
still be able to fire — as an ordinary order (no tax_lots), gated off an avg_cost_basis dollar
estimate — rather than being blocked by the Fail-Closed pending-basis rule, which is meant for a
*partial* shortfall (some lots priced, some not), not the all-or-nothing case.

Run: PYTHONPATH=. python3 bot/_smoke_test_zero_lots_available.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.steps import step4_profit_taking


class _TaxLotOnlyBroker:
    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        # Flat, well below every test's sell price so selling_price_change trivially passes.
        return [98.0, 98.5, 99.0, 99.5, 100.0]


def _minimal_ctx(targets: dict | None = None) -> RunContext:
    meta = PortfolioMetadata(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=35.0,
        min_cash_absolute=250, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=12.5,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=100,
        materialize_profit_percentage=4.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=12.5, min_raw_gain_percent_to_sell=-1e9,
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    cfg = PortfolioConfig(meta=meta, targets=targets or {}, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 4), config=cfg, account_number="TEST")
    return ctx


def test_zero_lots_available_falls_back_to_ordinary_order() -> None:
    """MU's ENTIRE position (10 whole shares) is a same-day buy: the one lot on record has
    is_selectable=False (still syncing broker-side). avg_cost_basis is nonetheless known (Step
    1's primary source, average_buy_price, populates independently of per-lot sync) and shows a
    real gain. GET THE PROFITS should fire anyway: ordinary order (tax_lots=None), dollar gate
    computed as an avg_cost_basis estimate since there's no lot data to FIFO-walk."""
    targets = {"MU": AssetTarget(symbol="MU", weight=1.0)}
    ctx = _minimal_ctx(targets=targets)
    ctx.positions = {"MU": Position(symbol="MU", quantity=10.0, avg_cost_basis=600.0)}
    ctx.quotes = {"MU": Quote(symbol="MU", last_trade_price=850.0)}  # +41.67% unrealized gain
    lots = {"MU": [TaxLot(open_lot_id="mu-today", quantity=10.0, cost_per_share=600.0,
                           open_date=date(2026, 8, 4), is_selectable=False)]}
    broker = _TaxLotOnlyBroker(lots)

    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, (ctx.profit_taking_sells, ctx.skipped)
    t = ctx.profit_taking_sells[0]
    assert t.symbol == "MU"
    assert t.tax_lots is None, "zero-available-lots fallback must go out as an ordinary order"
    assert t.quantity == 5.0, t.quantity  # profit_sell_percentage=50% of 10 shares
    assert round(t.realized_profit_dollars, 2) == 1250.0, t.realized_profit_dollars  # (850-600)*5
    assert "no priced/selectable lots yet" in t.reason
    assert "avg_cost_basis estimate" in t.reason
    print(f"[zero-lots-fallback] MU sold {t.quantity} shares (tax_lots={t.tax_lots}) — {t.reason}")


def test_partial_lots_still_fail_closed() -> None:
    """Guard against over-broadening the fallback: if even ONE lot is priced+selectable but it
    isn't enough to cover the sale target, this must stay a hard Fail-Closed skip exactly as
    before (e.g. an in-progress ACATS transfer sitting alongside already-settled shares) — NOT
    silently downsized or treated as the zero-available case."""
    targets = {"MU": AssetTarget(symbol="MU", weight=1.0)}
    ctx = _minimal_ctx(targets=targets)
    ctx.positions = {"MU": Position(symbol="MU", quantity=10.0, avg_cost_basis=600.0)}
    ctx.quotes = {"MU": Quote(symbol="MU", last_trade_price=850.0)}
    lots = {"MU": [
        TaxLot(open_lot_id="mu-old", quantity=2.0, cost_per_share=600.0,
               open_date=date(2026, 7, 1), is_selectable=True),
        TaxLot(open_lot_id="mu-today", quantity=8.0, cost_per_share=600.0,
               open_date=date(2026, 8, 4), is_selectable=False),
    ]}
    broker = _TaxLotOnlyBroker(lots)

    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    assert any(
        s.symbol == "MU" and "cost basis pending transfer" in s.reason for s in ctx.skipped
    ), ctx.skipped
    print("[partial-lots-fail-closed] 2 priced sh / 5 sh target -> still fail-closed, not downsized")


def test_zero_lots_available_respects_loss_check() -> None:
    """Same zero-available-lots position, but priced at a loss vs. avg_cost_basis -> the
    estimate-based dollar gate must still refuse to sell at a loss, same as the FIFO path does."""
    targets = {"MU": AssetTarget(symbol="MU", weight=1.0)}
    ctx = _minimal_ctx(targets=targets)
    ctx.positions = {"MU": Position(symbol="MU", quantity=10.0, avg_cost_basis=900.0)}
    ctx.quotes = {"MU": Quote(symbol="MU", last_trade_price=850.0)}  # underwater
    lots = {"MU": [TaxLot(open_lot_id="mu-today", quantity=10.0, cost_per_share=900.0,
                           open_date=date(2026, 8, 4), is_selectable=False)]}
    broker = _TaxLotOnlyBroker(lots)

    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    print("[zero-lots-loss-blocked] underwater same-day-only position -> correctly refused")


def main() -> None:
    test_zero_lots_available_falls_back_to_ordinary_order()
    test_partial_lots_still_fail_closed()
    test_zero_lots_available_respects_loss_check()
    print("\nSMOKE TEST (zero-available-lots fallback) PASSED")


if __name__ == "__main__":
    main()
