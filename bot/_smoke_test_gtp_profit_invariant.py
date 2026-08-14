"""Regression coverage for the FIFO-vs-blended-average profit invariant in GET THE PROFITS, and
for the v2.75.0 loss-lot sell guard that now enforces it lot-by-lot.

The gap being closed: a position built at DECREASING cost over time (expensive shares bought
first, cheaper shares bought later) can show a positive raw_gain_pct against `avg_cost_basis` — a
whole-position BLENDED average — while FIFO, which always disposes of the OLDEST lots first,
actually reaches for the expensive shares and realizes a real dollar loss on them.

Two generations of fix, both covered here:

* **v2.66.0** required `fifo.fully_covered and fifo.realized_profit_dollars > 0` unconditionally,
  on top of whichever gate (percent or dollar) passed — an all-or-nothing check that refused the
  whole sale whenever the FIFO-matched total came out ≤ 0.
* **v2.75.0** (the loss-lot sell guard) goes finer-grained: instead of refusing the entire sale,
  it EXCLUDES the individual lots that would not realize a strict gain and proceeds on the
  profitable remainder. So the decreasing-cost case that v2.66.0 refused outright now fires — but
  only over the profitable lots, and downsized to their quantity. The v2.66.0 total check is
  retained as a backstop and is now structurally unreachable in normal operation (every consumed
  lot is individually profitable, so the total cannot be ≤ 0).

Pure logic tests against step4_profit_taking directly, no snapshot/CLI plumbing needed (same
style as bot/_smoke_test_min_trade_value.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_gtp_profit_invariant.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.steps import step4_profit_taking


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1e9,  # unreachable -> only the percent gate can fire in GTP tests
        min_raw_gain_percent_to_sell=-1e9,  # disabled -> not what this file tests; see
            # _smoke_test_min_raw_gain_percent.py
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
    """Minimal BrokerClient stub: only get_tax_lots (FIFO dollar-gate) and get_daily_closes
    (the selling_price_change guard) are needed."""

    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        # Mildly oscillating series well below every test's sell price so the
        # selling_price_change guard ((close_yesterday - price)*100/price < threshold) passes
        # trivially: price is far above close_yesterday, giving a strongly negative change.
        return [58.0, 58.5, 59.0, 59.5, 60.0]


def _position(sym: str, price: float, quantity: float, avg_cost: float, lots: list,
              meta_overrides: dict | None = None) -> tuple:
    targets = {sym: AssetTarget(symbol=sym, weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(**(meta_overrides or {})), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 11), config=cfg, account_number="TEST")
    ctx.positions = {sym: Position(symbol=sym, quantity=quantity, avg_cost_basis=avg_cost)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    return ctx, _Broker({sym: lots})


def test_loss_lot_excluded_sale_proceeds_on_profitable_lot() -> None:
    """The classic decreasing-cost trap: 10 old shares @ $100 (FIFO-oldest, underwater at $80)
    and 10 newer @ $50. v2.66.0 refused this sale outright. v2.75.0 must instead skip the $100
    lot and sell the profitable $50 lot — the sale fires, and the underwater lot is NOT shipped
    to the order."""
    ctx, broker = _position("XYZ", price=80.0, quantity=20.0, avg_cost=75.0, lots=[
        TaxLot(open_lot_id="old", quantity=10.0, cost_per_share=100.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="new", quantity=10.0, cost_per_share=50.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    # profit_sell_percentage=50% of 20 shares = 10, fully covered by the profitable lot alone.
    assert t.quantity == 10, t.quantity
    assert t.realized_profit_dollars == 300.0, t.realized_profit_dollars  # (80-50)*10
    shipped = {l["open_lot_id"] for l in t.tax_lots}
    assert shipped == {"new"}, shipped  # the underwater "old" lot must never reach the order
    assert ctx.loss_sale_symbols == [], ctx.loss_sale_symbols
    print(f"[loss-lot-excluded] underwater $100 lot skipped; sold 10 sh from the $50 lot for "
          f"${t.realized_profit_dollars:.2f}")


def test_loss_lot_exclusion_downsizes_the_sale() -> None:
    """When the profitable lots cannot cover the full profit_sell_percentage target, the sale is
    capped at the profitable quantity and proceeds downsized — rather than reaching into the
    underwater lots to make up the difference."""
    ctx, broker = _position("DOWN", price=80.0, quantity=20.0, avg_cost=75.0, lots=[
        TaxLot(open_lot_id="old", quantity=15.0, cost_per_share=100.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="new", quantity=5.0, cost_per_share=50.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    # Target was 10 shares (50% of 20); only 5 profitable shares exist -> capped to 5.
    assert t.quantity == 5, t.quantity
    assert t.realized_profit_dollars == 150.0, t.realized_profit_dollars  # (80-50)*5
    assert {l["open_lot_id"] for l in t.tax_lots} == {"new"}
    assert "loss-lot sell guard" in t.reason, t.reason
    print(f"[loss-lot-downsize] target 10 sh capped to {t.quantity} profitable sh "
          f"(${t.realized_profit_dollars:.2f}); reason records the held-back shares")


def test_all_lots_underwater_skips_entirely() -> None:
    """If EVERY sellable lot is at or above the current price there is nothing to sell at a gain,
    so the sale is skipped outright — the v2.66.0 refusal outcome, now reached via the loss-lot
    guard rather than the total-dollars check."""
    ctx, broker = _position("UNDER", price=80.0, quantity=20.0, avg_cost=75.0, lots=[
        TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=100.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="b", quantity=10.0, cost_per_share=95.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    assert ctx.loss_sale_symbols == [], ctx.loss_sale_symbols
    reasons = [s.reason for s in ctx.skipped if s.symbol == "UNDER"]
    assert any("loss-lot sell guard" in r for r in reasons), reasons
    print("[all-underwater] every lot above the current price -> sale correctly skipped")


def test_exact_breakeven_lot_is_excluded() -> None:
    """A lot priced exactly at today's price realizes $0 while consuming sale quantity, so it is
    excluded alongside true loss lots. With only such a lot held, nothing is sellable at a gain."""
    ctx, broker = _position("FLAT", price=80.0, quantity=20.0, avg_cost=75.0, lots=[
        TaxLot(open_lot_id="breakeven", quantity=20.0, cost_per_share=80.0, open_date=date(2026, 1, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "FLAT"]
    assert any("loss-lot sell guard" in r for r in reasons), reasons
    print("[breakeven-excluded] exact-breakeven lot contributes $0 -> excluded, sale skipped")


def test_pending_basis_still_fails_closed() -> None:
    """Ordering rule: the Fail-Closed pending-basis check runs BEFORE the loss-lot cap. A target
    that exceeds the priced+selectable quantity must still be skipped outright, NOT quietly
    downsized to 'sell only the lots that happen to be priced'."""
    ctx, broker = _position("PEND", price=80.0, quantity=20.0, avg_cost=75.0, lots=[
        TaxLot(open_lot_id="priced", quantity=5.0, cost_per_share=50.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="pending", quantity=15.0, cost_per_share=None, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "PEND"]
    assert any("cost basis pending transfer" in r for r in reasons), reasons
    print("[pending-basis-fail-closed] 10 sh target vs. 5 priced sh -> fail-closed skip, "
          "not a silent downsize")


def test_gtp_still_fires_when_fifo_is_genuinely_profitable() -> None:
    """Sanity check nothing over-tightened: a position built at INCREASING cost (cheap first) has
    FIFO consume the cheap lot first, so the sale fires normally and the guard is a no-op."""
    ctx, broker = _position("INC", price=80.0, quantity=20.0, avg_cost=75.0, lots=[
        TaxLot(open_lot_id="cheap", quantity=10.0, cost_per_share=50.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="expensive", quantity=10.0, cost_per_share=100.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.quantity == 10, t.quantity
    assert t.realized_profit_dollars == 300.0, t.realized_profit_dollars  # (80-50)*10
    assert "loss-lot sell guard" not in t.reason, t.reason  # guard was a no-op here
    print(f"[genuine-profit-unchanged] FIFO realized ${t.realized_profit_dollars:.2f} — fires as "
          f"before, guard is a no-op")


def main() -> None:
    test_loss_lot_excluded_sale_proceeds_on_profitable_lot()
    test_loss_lot_exclusion_downsizes_the_sale()
    test_all_lots_underwater_skips_entirely()
    test_exact_breakeven_lot_is_excluded()
    test_pending_basis_still_fails_closed()
    test_gtp_still_fires_when_fifo_is_genuinely_profitable()
    print("\nSMOKE TEST (GTP FIFO profit invariant + v2.75.0 loss-lot sell guard) PASSED")


if __name__ == "__main__":
    main()
