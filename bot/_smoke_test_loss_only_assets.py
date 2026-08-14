"""Coverage for CLAUDE.md Step 7's Loss-Only Lot Assets report (v2.76.0).

Lists every currently-held target asset whose EVERY sellable, priced lot is underwater at today's
price — exactly the population the v2.75.0 loss-lot sell guard can never sell any part of, so
GET THE PROFITS is structurally unable to fire on them. Purely observational: it must never
influence a buy/sell decision.

The report is split across the two CLI commands because of where the data lives:
`compute_loss_only_assets` needs the broker (tax lots) and so runs in `plan`;
`drop_bought_symbols` needs this cycle's buys and so runs in `finalize`, which has no broker.

Run: PYTHONPATH=. python3 bot/_smoke_test_loss_only_assets.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot, TradeIntent
from bot.steps import compute_loss_only_assets, drop_bought_symbols


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0,
        no_of_days_for_price_compare=3, cap_on_total_cash_balance_to_use=30000,
        cool_down_period_after_lquidation=6, beta_benchmark_symbol="SPY",
        beta_calculation_lookback_days=30, sold_asset_repurchase_days=2,
        leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9, profit_resell_cooldown_days=15,
        selling_price_change=0.1, sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1e9, min_raw_gain_percent_to_sell=-1e9,
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0, wash_sale_lookback_days=0, dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])


def _ctx(positions: dict, quotes: dict) -> RunContext:
    targets = {sym: AssetTarget(symbol=sym, weight=1.0) for sym in positions}
    cfg = PortfolioConfig(meta=_meta(), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.positions = {s: Position(symbol=s, quantity=q, avg_cost_basis=c) for s, (q, c) in positions.items()}
    ctx.quotes = {s: Quote(symbol=s, last_trade_price=p) for s, p in quotes.items()}
    return ctx


def test_flags_only_all_underwater_positions() -> None:
    """ALLBAD's lots are all above the price -> listed. MIXED has one profitable lot -> not
    listed, since that lot is still sellable at a gain."""
    ctx = _ctx(
        positions={"ALLBAD": (10.0, 100.0), "MIXED": (10.0, 75.0)},
        quotes={"ALLBAD": 80.0, "MIXED": 80.0},
    )
    broker = _Broker({
        "ALLBAD": [
            TaxLot(open_lot_id="a", quantity=6.0, cost_per_share=110.0, open_date=date(2026, 1, 1), is_selectable=True),
            TaxLot(open_lot_id="b", quantity=4.0, cost_per_share=85.0, open_date=date(2026, 6, 1), is_selectable=True),
        ],
        "MIXED": [
            TaxLot(open_lot_id="c", quantity=5.0, cost_per_share=100.0, open_date=date(2026, 1, 1), is_selectable=True),
            TaxLot(open_lot_id="d", quantity=5.0, cost_per_share=50.0, open_date=date(2026, 6, 1), is_selectable=True),
        ],
    })
    out = compute_loss_only_assets(ctx, broker)
    assert [a.symbol for a in out] == ["ALLBAD"], [a.symbol for a in out]
    a = out[0]
    assert a.lot_count == 2, a.lot_count
    assert a.best_lot_cost == 85.0 and a.worst_lot_cost == 110.0, (a.best_lot_cost, a.worst_lot_cost)
    assert a.market_value == 800.0, a.market_value
    # Lot basis: (80-110)*6 + (80-85)*4 = -180 + -20 = -200
    assert a.unrealized_dollars == -200.0, a.unrealized_dollars
    assert abs(a.lot_weighted_cost - 100.0) < 1e-9, a.lot_weighted_cost
    assert not a.basis_mismatch, a.basis_mismatch  # lot-weighted 100.0 == avg_cost_basis 100.0
    print(f"[flags-all-underwater] ALLBAD listed ({a.lot_count} lots, ${a.unrealized_dollars:,.2f}); "
          f"MIXED excluded — it still has a profitable lot")


def test_breakeven_lot_counts_as_not_sellable_at_a_gain() -> None:
    """A lot priced exactly at today's price cannot be sold at a gain, so a position holding only
    such lots is loss-only — consistent with the v2.75.0 guard, which excludes breakeven lots."""
    ctx = _ctx(positions={"FLAT": (10.0, 80.0)}, quotes={"FLAT": 80.0})
    broker = _Broker({"FLAT": [
        TaxLot(open_lot_id="e", quantity=10.0, cost_per_share=80.0, open_date=date(2026, 1, 1), is_selectable=True),
    ]})
    assert [a.symbol for a in compute_loss_only_assets(ctx, broker)] == ["FLAT"]
    print("[breakeven-counts] exact-breakeven-only position is reported as loss-only")


def test_omits_unresolved_basis_and_unpriced_lots() -> None:
    """NOBASIS has no avg_cost_basis (Step 1 fail-closed) and NOLOTS has nothing priced/selectable
    — in neither case can 'every lot is underwater' be established, so neither is claimed."""
    ctx = _ctx(positions={"NOBASIS": (10.0, 100.0), "NOLOTS": (10.0, 100.0)},
               quotes={"NOBASIS": 80.0, "NOLOTS": 80.0})
    ctx.positions["NOBASIS"].avg_cost_basis = None
    broker = _Broker({
        "NOBASIS": [TaxLot(open_lot_id="f", quantity=10.0, cost_per_share=110.0, open_date=date(2026, 1, 1), is_selectable=True)],
        "NOLOTS": [TaxLot(open_lot_id="g", quantity=10.0, cost_per_share=None, open_date=date(2026, 1, 1), is_selectable=True)],
    })
    assert compute_loss_only_assets(ctx, broker) == []
    print("[omits-unknowns] unresolved basis / unpriced lots are never claimed as loss-only")


def test_symbol_bought_this_cycle_is_dropped() -> None:
    """'after the buys are placed': a symbol bought this cycle gains a fresh lot at ~today's
    price, so it is no longer a loss-only-lot asset and drops off the report."""
    ctx = _ctx(positions={"ALLBAD": (10.0, 100.0), "ALSOBAD": (10.0, 100.0)},
               quotes={"ALLBAD": 80.0, "ALSOBAD": 80.0})
    broker = _Broker({
        s: [TaxLot(open_lot_id=s, quantity=10.0, cost_per_share=110.0, open_date=date(2026, 1, 1), is_selectable=True)]
        for s in ("ALLBAD", "ALSOBAD")
    })
    candidates = compute_loss_only_assets(ctx, broker)
    assert {a.symbol for a in candidates} == {"ALLBAD", "ALSOBAD"}

    ctx.buys = [TradeIntent(symbol="ALSOBAD", side="buy", dollar_amount=500.0)]
    final = drop_bought_symbols(candidates, ctx)
    assert [a.symbol for a in final] == ["ALLBAD"], [a.symbol for a in final]
    print("[drops-bought] ALSOBAD bought this cycle -> dropped; ALLBAD remains")


def test_basis_mismatch_is_flagged() -> None:
    """Real case from the 2026-08-14 account: HOOD's broker avg_cost_basis ($91.60) sat BELOW the
    price ($97.40) while its only lot ($103.03) sat above it. The row must be reported on the lot
    basis (negative, consistent with membership) and the divergence flagged rather than hidden."""
    ctx = _ctx(positions={"HOOD": (0.382215, 91.60)}, quotes={"HOOD": 97.40})
    broker = _Broker({"HOOD": [
        TaxLot(open_lot_id="j", quantity=0.382215, cost_per_share=103.03, open_date=date(2026, 7, 29), is_selectable=True),
    ]})
    out = compute_loss_only_assets(ctx, broker)
    assert [a.symbol for a in out] == ["HOOD"]
    a = out[0]
    assert a.basis_mismatch, a.basis_mismatch
    assert a.unrealized_pct < 0, a.unrealized_pct  # lot basis -> negative, not the +6.33% avg implies
    assert a.unrealized_dollars < 0, a.unrealized_dollars
    print(f"[basis-mismatch] HOOD reported on lot basis ({a.unrealized_pct:+.2f}%) and flagged; "
          f"avg_cost_basis would have implied "
          f"{(a.current_price - a.avg_cost_basis) / a.avg_cost_basis * 100:+.2f}%")


def test_partial_lot_coverage_is_omitted() -> None:
    """If the priced lots don't cover the whole position, 'every sellable lot is underwater'
    cannot be established for the uncovered shares — omit rather than overclaim."""
    ctx = _ctx(positions={"PARTIAL": (10.0, 100.0)}, quotes={"PARTIAL": 80.0})
    broker = _Broker({"PARTIAL": [
        TaxLot(open_lot_id="k", quantity=4.0, cost_per_share=110.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="l", quantity=6.0, cost_per_share=None, open_date=date(2026, 6, 1), is_selectable=True),
    ]})
    assert compute_loss_only_assets(ctx, broker) == []
    print("[partial-coverage] priced lots covering only part of the position -> omitted")


def test_sorted_worst_first() -> None:
    ctx = _ctx(positions={"MILD": (10.0, 82.0), "BAD": (10.0, 160.0)},
               quotes={"MILD": 80.0, "BAD": 80.0})
    broker = _Broker({
        "MILD": [TaxLot(open_lot_id="h", quantity=10.0, cost_per_share=82.0, open_date=date(2026, 1, 1), is_selectable=True)],
        "BAD": [TaxLot(open_lot_id="i", quantity=10.0, cost_per_share=160.0, open_date=date(2026, 1, 1), is_selectable=True)],
    })
    assert [a.symbol for a in compute_loss_only_assets(ctx, broker)] == ["BAD", "MILD"]
    print("[sorted] worst unrealized percentage first")


def main() -> None:
    test_flags_only_all_underwater_positions()
    test_breakeven_lot_counts_as_not_sellable_at_a_gain()
    test_omits_unresolved_basis_and_unpriced_lots()
    test_symbol_bought_this_cycle_is_dropped()
    test_basis_mismatch_is_flagged()
    test_partial_lot_coverage_is_omitted()
    test_sorted_worst_first()
    print("\nSMOKE TEST (Loss-Only Lot Assets report) PASSED")


if __name__ == "__main__":
    main()
