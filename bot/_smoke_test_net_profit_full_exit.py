"""Coverage for the v2.83.0 net-profit full exit in GET THE PROFITS (CLAUDE.md Step 4).

Background (operator request, 2026-09-04): the v2.75.0 loss-lot sell guard strips every
underwater lot out of a GET THE PROFITS sale and sells only the winners — which parks the loss
lot in the account indefinitely, since it can never be sold at a gain. For a MIXED position (at
least one lot underwater AND at least one lot in profit at today's price) the operator instead
wants: if the NET realized figure across ALL lots still clears the GET THE PROFITS gate, sell the
ENTIRE position (100%, fractional remainder included, ignoring profit_sell_percentage) as one
ORDINARY order and let Robinhood's default FIFO matching dispose of every lot. The underwater
lot's loss is simply netted against the winners' gain in the same transaction, exactly as the
IRS computes it.

Second half of the same request: the wash-sale forward buy-guard (`lastLossSaleDate`) is keyed
on a sale's NET realized figure, never per lot — so a net-profit full exit that disposes of an
individually-underwater lot must NOT arm it (ctx.loss_sale_symbols stays empty).

Pure logic tests against step4_profit_taking directly, same style as
bot/_smoke_test_gtp_profit_invariant.py.

Run: PYTHONPATH=. python3 bot/_smoke_test_net_profit_full_exit.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.state import AssetPriceState
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
        # Flat (non-ramping) bars so the arithmetic in each test is exact:
        materialize_profit_percentage=2.5, materialize_profit_percentage_max=2.5,
        materialize_profit_in_dollars=1e9, materialize_profit_in_dollars_max=1e9,
        profit_threshold_ramp_days=30,
        profit_sell_percentage=50.0,   # deliberately NOT 100 — the full exit must ignore it
        min_raw_gain_percent_to_sell=0.5,
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=30,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        # Closes well below every test's sell price -> selling_price_change guard passes.
        return [58.0, 58.5, 59.0, 59.5, 60.0]


def _position(sym: str, price: float, quantity: float, avg_cost: float, lots: list,
              meta_overrides: dict | None = None, price_state: AssetPriceState | None = None) -> tuple:
    targets = {sym: AssetTarget(symbol=sym, weight=1.0)}
    cfg = PortfolioConfig(meta=_meta(**(meta_overrides or {})), targets=targets, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 9, 4), config=cfg, account_number="TEST")
    ctx.positions = {sym: Position(symbol=sym, quantity=quantity, avg_cost_basis=avg_cost)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    if price_state is not None:
        ctx.price_state = {sym: price_state}
    return ctx, _Broker({sym: lots})


# The operator's MU example, scaled: one lot $10 underwater, one lot $120 in profit, net +$110.
_MU_LOTS = [
    TaxLot(open_lot_id="loss", quantity=1.0, cost_per_share=110.0, open_date=date(2026, 8, 20), is_selectable=True),
    TaxLot(open_lot_id="gain", quantity=2.0, cost_per_share=40.0, open_date=date(2026, 8, 1), is_selectable=True),
]
_MU_PRICE = 100.0            # loss lot: (100-110)*1 = -10 ; gain lot: (100-40)*2 = +120
_MU_AVG = (110.0 + 80.0) / 3  # blended avg 63.33 -> raw_gain +57.9%


def test_mixed_position_net_gain_sells_full_position_as_ordinary_order() -> None:
    """MU-style: net +$110 clears the gate -> the WHOLE 3-share position goes out as one
    ordinary order (tax_lots=None), profit_sell_percentage=50% is ignored, the realized figure
    is the net (loss netted against gain), and the wash-sale guard is NOT armed."""
    ctx, broker = _position("MU", price=_MU_PRICE, quantity=3.0, avg_cost=_MU_AVG, lots=_MU_LOTS)
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.quantity == 3.0, t.quantity                      # 100%, not 50%
    assert t.tax_lots is None, t.tax_lots                     # ordinary order, Robinhood FIFO
    assert abs(t.realized_profit_dollars - 110.0) < 1e-9, t.realized_profit_dollars
    assert "net-profit FULL EXIT" in t.reason, t.reason
    assert "$-10.00 of lot loss" in t.reason, t.reason
    assert "wash-sale buy-guard NOT armed" in t.reason, t.reason
    assert ctx.loss_sale_symbols == [], ctx.loss_sale_symbols  # the second half of the request
    assert ctx.total_high_beta_gains_realized == 110.0
    print(f"[net-full-exit] sold all {t.quantity} sh as an ordinary order, net ${t.realized_profit_dollars:.2f}; "
          f"loss_sale_symbols={ctx.loss_sale_symbols}")


def test_fractional_remainder_is_included_in_the_full_exit() -> None:
    """A mixed position with a fractional share count exits in full — the ordinary order accepts
    fractional quantities, so nothing is left behind for the Step 4b cleanup pass."""
    lots = [
        TaxLot(open_lot_id="loss", quantity=0.7, cost_per_share=110.0, open_date=date(2026, 8, 20), is_selectable=True),
        TaxLot(open_lot_id="gain", quantity=2.55, cost_per_share=40.0, open_date=date(2026, 8, 1), is_selectable=True),
    ]
    qty = 3.25
    avg = (0.7 * 110.0 + 2.55 * 40.0) / qty
    ctx, broker = _position("FRAC", price=100.0, quantity=qty, avg_cost=avg, lots=lots)
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert abs(t.quantity - qty) < 1e-9, t.quantity
    assert t.tax_lots is None
    expected_net = (100.0 - 110.0) * 0.7 + (100.0 - 40.0) * 2.55
    assert abs(t.realized_profit_dollars - expected_net) < 1e-9, (t.realized_profit_dollars, expected_net)
    print(f"[net-full-exit-fractional] sold {t.quantity} sh (fractional) for net ${t.realized_profit_dollars:.2f}")


def test_net_loss_falls_back_to_profitable_lots_only() -> None:
    """Loss lot bigger than the gain lot -> net is NEGATIVE -> the full exit stands aside and the
    v2.75.0 loss-lot guard governs unchanged: sell only the profitable lot (specified-lot order),
    keep the underwater one, and — since the sale is a gain — still no wash-sale arming."""
    lots = [
        TaxLot(open_lot_id="loss", quantity=10.0, cost_per_share=130.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="gain", quantity=10.0, cost_per_share=90.0, open_date=date(2026, 6, 1), is_selectable=True),
    ]
    # net at $100: (100-130)*10 + (100-90)*10 = -300 + 100 = -200
    ctx, broker = _position("NET-", price=100.0, quantity=20.0, avg_cost=110.0, lots=lots,
                            meta_overrides=dict(min_raw_gain_percent_to_sell=-1e9,  # isolate the net check
                                                materialize_profit_percentage=-1e9,  # percent gate always on
                                                materialize_profit_percentage_max=-1e9))
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.quantity == 10, t.quantity                        # 50% of 20 = 10, all from "gain"
    assert {l["open_lot_id"] for l in t.tax_lots} == {"gain"}, t.tax_lots
    assert t.realized_profit_dollars == 100.0, t.realized_profit_dollars
    assert "net-profit full exit declined" in t.reason and "is not a gain" in t.reason, t.reason
    assert ctx.loss_sale_symbols == [], ctx.loss_sale_symbols
    print(f"[net-loss-fallback] net -$200 -> declined; sold {t.quantity} sh from the gain lot only")


def test_net_gain_below_gate_falls_back_to_profitable_lots_only() -> None:
    """Net is positive but too small for the dollar bar, while the profitable lot alone clears
    it -> full exit declines on the gate, fallback fires on the profitable lot as before."""
    lots = [
        TaxLot(open_lot_id="loss", quantity=10.0, cost_per_share=120.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="gain", quantity=10.0, cost_per_share=70.0, open_date=date(2026, 6, 1), is_selectable=True),
    ]
    # net at $100: -200 + 300 = +100 ; profitable-only: +300 ; dollar bar $150 flat, percent off
    ctx, broker = _position("GATE", price=100.0, quantity=20.0, avg_cost=95.0, lots=lots,
                            meta_overrides=dict(materialize_profit_percentage=99.0, materialize_profit_percentage_max=99.0,
                                                materialize_profit_in_dollars=150.0, materialize_profit_in_dollars_max=150.0))
    step4_profit_taking(ctx, broker)

    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    t = ctx.profit_taking_sells[0]
    assert t.quantity == 10 and t.tax_lots is not None, (t.quantity, t.tax_lots)
    assert t.realized_profit_dollars == 300.0, t.realized_profit_dollars
    assert "doesn't clear the dynamic thresholds" in t.reason, t.reason
    print("[net-gate-fallback] net +$100 < $150 bar -> declined; profitable lot ($300) fired instead")


def test_min_raw_gain_floor_applies_to_the_full_exit() -> None:
    """The position is only marginally ahead on the blended average -> min_raw_gain_percent_to_sell
    blocks the full exit (and, as before, the fallback path too)."""
    lots = [
        TaxLot(open_lot_id="loss", quantity=10.0, cost_per_share=105.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="gain", quantity=10.0, cost_per_share=94.0, open_date=date(2026, 6, 1), is_selectable=True),
    ]
    # net at $100: -50 + 60 = +10 ; broker blended avg 99.6 -> raw +0.40%, under the 0.5% floor
    ctx, broker = _position("MARG", price=100.0, quantity=20.0, avg_cost=99.6, lots=lots,
                            meta_overrides=dict(materialize_profit_percentage=-1e9, materialize_profit_percentage_max=-1e9))
    step4_profit_taking(ctx, broker)

    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "MARG"]
    assert any("min_raw_gain_percent_to_sell" in r for r in reasons), reasons
    print("[net-min-raw-gain] marginal position -> full exit and fallback both refused")


def test_pending_basis_lot_disables_the_full_exit() -> None:
    """A lot with no cost basis yet means the net figure can't be trusted -> the full exit
    stands aside (fails closed); the existing pending-basis rule then governs."""
    lots = [
        TaxLot(open_lot_id="loss", quantity=2.0, cost_per_share=110.0, open_date=date(2026, 8, 20), is_selectable=True),
        TaxLot(open_lot_id="gain", quantity=3.0, cost_per_share=40.0, open_date=date(2026, 8, 1), is_selectable=True),
        TaxLot(open_lot_id="pending", quantity=15.0, cost_per_share=None, open_date=date(2026, 9, 1), is_selectable=True),
    ]
    # 50% target = 10 sh > 5 priced sh -> the pre-existing Fail-Closed rule must be what fires.
    ctx, broker = _position("PEND", price=100.0, quantity=20.0, avg_cost=70.0, lots=lots)
    step4_profit_taking(ctx, broker)

    assert all("FULL EXIT" not in t.reason for t in ctx.profit_taking_sells), ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "PEND"]
    assert any("cost basis pending transfer" in r for r in reasons), (reasons, ctx.profit_taking_sells)
    print("[net-pending-basis] unpriced lot present -> full exit disabled, pending-basis rule governs")


def test_not_mixed_positions_are_untouched() -> None:
    """All-profitable and all-underwater positions are not 'mixed' -> the pre-v2.83.0 behaviour
    is byte-for-byte unchanged (profit_sell_percentage slice / skip, respectively)."""
    ctx, broker = _position("ALLUP", price=100.0, quantity=20.0, avg_cost=50.0, lots=[
        TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=40.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="b", quantity=10.0, cost_per_share=60.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx, broker)
    t = ctx.profit_taking_sells[0]
    assert t.quantity == 10 and t.tax_lots is not None and "FULL EXIT" not in t.reason, t

    ctx2, broker2 = _position("ALLDOWN", price=100.0, quantity=20.0, avg_cost=120.0, lots=[
        TaxLot(open_lot_id="a", quantity=10.0, cost_per_share=110.0, open_date=date(2026, 1, 1), is_selectable=True),
        TaxLot(open_lot_id="b", quantity=10.0, cost_per_share=130.0, open_date=date(2026, 6, 1), is_selectable=True),
    ])
    step4_profit_taking(ctx2, broker2)
    assert ctx2.profit_taking_sells == [] and ctx2.loss_sale_symbols == []
    print("[not-mixed-unchanged] all-profitable -> 50% slice as before; all-underwater -> skipped as before")


def test_cooldown_and_already_today_still_gate_the_full_exit() -> None:
    """profit_resell_cooldown_days and the same-day re-trigger check apply to the full exit
    exactly as to any GET THE PROFITS sale."""
    ctx, broker = _position("COOL", price=_MU_PRICE, quantity=3.0, avg_cost=_MU_AVG, lots=_MU_LOTS,
                            price_state=AssetPriceState(profitSellDate="2026-09-01", profitSellPrice=95.0))
    step4_profit_taking(ctx, broker)
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "COOL"]
    assert any("profit_resell_cooldown_days" in r and "net-profit full exit" in r for r in reasons), reasons
    # exactly one skip — the fallback path shares the guard and must not double-log
    assert len(reasons) == 1, reasons

    ctx2, broker2 = _position("TODAY", price=_MU_PRICE, quantity=3.0, avg_cost=_MU_AVG, lots=_MU_LOTS,
                              price_state=AssetPriceState(profitSellDate="2026-09-04", profitSellPrice=95.0))
    step4_profit_taking(ctx2, broker2)
    assert ctx2.profit_taking_sells == [], ctx2.profit_taking_sells
    print("[net-guards] cooldown blocks (single skip, no double-log); same-day re-trigger blocks")


def main() -> None:
    test_mixed_position_net_gain_sells_full_position_as_ordinary_order()
    test_fractional_remainder_is_included_in_the_full_exit()
    test_net_loss_falls_back_to_profitable_lots_only()
    test_net_gain_below_gate_falls_back_to_profitable_lots_only()
    test_min_raw_gain_floor_applies_to_the_full_exit()
    test_pending_basis_lot_disables_the_full_exit()
    test_not_mixed_positions_are_untouched()
    test_cooldown_and_already_today_still_gate_the_full_exit()
    print("\nSMOKE TEST (v2.83.0 net-profit full exit + wash-sale non-arming) PASSED")


if __name__ == "__main__":
    main()
