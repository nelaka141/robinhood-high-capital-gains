"""Coverage for Step 4b's Sell Cleanup Pass (v2.80.0) — sweeps small/single-lot remainders GET
THE PROFITS' whole-share rounding and loss-lot exclusion routinely leave behind, plus any other
stray single-lot position too small to keep tracking, as long as the remaining lot is not a loss.
Two independent rules, unioned:
  (a) single remaining lot, not a loss, market value < cleanup_dust_threshold_dollars
  (b) single remaining lot, not a loss, left over from THIS cycle's own GET THE PROFITS sale
      (no dollar threshold)

Pure logic tests against step4b_sell_cleanup (and, for the interaction cases, step4_profit_taking
first) directly — same style as bot/_smoke_test_min_raw_gain_percent.py.

Run: PYTHONPATH=. python3 bot/_smoke_test_sell_cleanup.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot
from bot.steps import step4_profit_taking, step4b_sell_cleanup


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
        materialize_profit_percentage=2.5, profit_sell_percentage=90.0,
        materialize_profit_in_dollars=1.0,
        materialize_profit_percentage_max=2.5, materialize_profit_in_dollars_max=1.0,
        profit_threshold_ramp_days=30, min_raw_gain_percent_to_sell=-1e9,
        keep_aside_profits_for_tax_percent=30.0, momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0, max_sector_percentage=0.0,
        wash_sale_lookback_days=0, dormant_asset_days=5,
        cleanup_dust_threshold_dollars=200.0,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        return [58.0, 58.5, 59.0, 59.5, 60.0]


def _position(sym: str, price: float, quantity: float, avg_cost: float, lots: list,
              meta_overrides: dict | None = None, target_price_to_sell: dict | None = None,
              blocked: list | None = None) -> tuple:
    targets = {sym: AssetTarget(symbol=sym, weight=1.0)}
    cfg = PortfolioConfig(
        meta=_meta(**(meta_overrides or {})), targets=targets, force_sell={}, blocked=blocked or [],
        target_price_to_sell=target_price_to_sell or {},
    )
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.positions = {sym: Position(symbol=sym, quantity=quantity, avg_cost_basis=avg_cost)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    if sym in (blocked or []):
        ctx.blocked_symbols[sym] = "blocked"
    return ctx, _Broker({sym: lots})


def test_rule_a_sweeps_small_single_green_lot() -> None:
    """No GET THE PROFITS fire this cycle. 1.5 shares @ $100 = $150 (< $200 threshold), single
    lot, cost $80 < price $100 (green) -> fully swept."""
    ctx, broker = _position("DUST", price=100.0, quantity=1.5, avg_cost=80.0, lots=[
        TaxLot(open_lot_id="a", quantity=1.5, cost_per_share=80.0, open_date=date(2026, 1, 1)),
    ])
    step4b_sell_cleanup(ctx, broker)

    assert len(ctx.cleanup_sells) == 1, ctx.cleanup_sells
    t = ctx.cleanup_sells[0]
    assert t.quantity == 1.5 and t.tax_lots is None, t
    assert abs(t.realized_profit_dollars - 30.0) < 0.01, t.realized_profit_dollars  # (100-80)*1.5
    print(f"[rule-a-sweeps-dust] DUST: 1.5 sh swept, $150 mv (< $200 threshold), "
          f"realized ${t.realized_profit_dollars:.2f} — OK")


def test_rule_a_skips_when_above_threshold() -> None:
    """Same shape but market value $2000 (>= $200 threshold), and no GET THE PROFITS sale this
    cycle to trigger rule (b) either -> no cleanup."""
    ctx, broker = _position("BIG", price=1000.0, quantity=2.0, avg_cost=800.0, lots=[
        TaxLot(open_lot_id="a", quantity=2.0, cost_per_share=800.0, open_date=date(2026, 1, 1)),
    ])
    step4b_sell_cleanup(ctx, broker)
    assert ctx.cleanup_sells == [], ctx.cleanup_sells
    print("[rule-a-skips-above-threshold] BIG: single green lot but $2000 mv >= $200 threshold, "
          "no GTP this cycle -> not swept — OK")


def test_rule_a_skips_loss_lot() -> None:
    """Single lot, small market value, but the lot is UNDERWATER (cost $120 > price $100) ->
    never swept, regardless of dollar size."""
    ctx, broker = _position("REDDUST", price=100.0, quantity=1.0, avg_cost=120.0, lots=[
        TaxLot(open_lot_id="a", quantity=1.0, cost_per_share=120.0, open_date=date(2026, 1, 1)),
    ])
    step4b_sell_cleanup(ctx, broker)
    assert ctx.cleanup_sells == [], ctx.cleanup_sells
    print("[rule-a-skips-loss] REDDUST: single small lot but underwater (cost $120 > price $100) "
          "-> never swept — OK")


def test_rule_a_skips_multi_lot_position() -> None:
    """Small total market value, but TWO lots -> neither rule (a) nor (b) applies (both require
    exactly one remaining lot)."""
    ctx, broker = _position("TWOLOTS", price=100.0, quantity=1.5, avg_cost=80.0, lots=[
        TaxLot(open_lot_id="a", quantity=1.0, cost_per_share=80.0, open_date=date(2026, 1, 1)),
        TaxLot(open_lot_id="b", quantity=0.5, cost_per_share=70.0, open_date=date(2026, 2, 1)),
    ])
    step4b_sell_cleanup(ctx, broker)
    assert ctx.cleanup_sells == [], ctx.cleanup_sells
    print("[rule-a-skips-multi-lot] TWOLOTS: $150 mv but 2 lots -> not swept (needs exactly 1) — OK")


def test_rule_b_sweeps_large_remainder_after_gtp_this_cycle() -> None:
    """GET THE PROFITS fires this cycle (specified-lot, selling most of the position), leaving
    exactly one lot behind that's green — swept in full even though its market value ($5000) is
    far above cleanup_dust_threshold_dollars, since rule (b) has no dollar cap."""
    lots = [
        TaxLot(open_lot_id="old", quantity=90.0, cost_per_share=50.0, open_date=date(2026, 1, 1)),
        TaxLot(open_lot_id="new", quantity=10.0, cost_per_share=60.0, open_date=date(2026, 6, 1)),
    ]
    ctx, broker = _position("BIGPOS", price=100.0, quantity=100.0, avg_cost=51.0, lots=lots)
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1, ctx.profit_taking_sells
    gtp = ctx.profit_taking_sells[0]
    assert gtp.tax_lots is not None, "expected a specified-lot GTP sale for this test to be meaningful"
    sold_qty = sum(l["quantity"] for l in gtp.tax_lots)
    remaining_qty = 100.0 - sold_qty
    assert remaining_qty > 0, "test setup expects a partial sale leaving a remainder"

    step4b_sell_cleanup(ctx, broker)
    # Only meaningful if GTP left exactly one lot behind — assert the scenario landed there.
    if remaining_qty == 10.0:  # the "new" lot fully intact (profit_sell_percentage=90% consumed "old")
        assert len(ctx.cleanup_sells) == 1, ctx.cleanup_sells
        t = ctx.cleanup_sells[0]
        assert abs(t.quantity - 10.0) < 0.01, t.quantity
        assert t.tax_lots is None
        print(f"[rule-b-sweeps-large-remainder] BIGPOS: GTP sold {sold_qty:.2f} sh this cycle, "
              f"cleanup swept the remaining {t.quantity:.2f} sh (mv ${t.quantity * 100:.2f}, "
              f"well above the $200 dust threshold) via rule (b) — OK")
    else:
        raise AssertionError(f"unexpected remainder shape: sold={sold_qty}, remaining={remaining_qty}")


def test_rule_b_skipped_when_gtp_used_ordinary_order() -> None:
    """A GET THE PROFITS sale that itself went out as an ordinary order (tax_lots=None — the
    sub-whole-share or zero-available-lots fallback) means the remaining lot structure can't be
    determined -> cleanup pass skips the symbol entirely, even if it would otherwise qualify."""
    ctx, broker = _position("FRAC", price=100.0, quantity=0.5, avg_cost=50.0, lots=[
        TaxLot(open_lot_id="a", quantity=0.5, cost_per_share=50.0, open_date=date(2026, 1, 1)),
    ])
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1
    assert ctx.profit_taking_sells[0].tax_lots is None, "expected the sub-whole-share ordinary-order fallback"

    step4b_sell_cleanup(ctx, broker)
    assert ctx.cleanup_sells == [], ctx.cleanup_sells
    print("[rule-b-skips-ordinary-order-gtp] FRAC: GTP fired via ordinary order (fractional "
          "position) -> cleanup can't know the remaining lot structure, skipped — OK")


def test_target_price_to_sell_blocks_cleanup() -> None:
    """target_price_to_sell overrides every sell mechanism 'by any means' — including the
    cleanup sweep."""
    ctx, broker = _position(
        "FLOOR", price=100.0, quantity=1.0, avg_cost=80.0,
        lots=[TaxLot(open_lot_id="a", quantity=1.0, cost_per_share=80.0, open_date=date(2026, 1, 1))],
        target_price_to_sell={"FLOOR": 150.0},
    )
    step4b_sell_cleanup(ctx, broker)
    assert ctx.cleanup_sells == [], ctx.cleanup_sells
    reasons = [s.reason for s in ctx.skipped if s.symbol == "FLOOR"]
    assert any("target_price_to_sell" in r for r in reasons), reasons
    print("[target-price-blocks-cleanup] FLOOR: target_price_to_sell ($150) not yet crossed "
          "(price $100) -> cleanup sweep blocked — OK")


def test_blocked_symbol_never_swept() -> None:
    ctx, broker = _position(
        "FROZEN", price=100.0, quantity=1.0, avg_cost=80.0,
        lots=[TaxLot(open_lot_id="a", quantity=1.0, cost_per_share=80.0, open_date=date(2026, 1, 1))],
        blocked=["FROZEN"],
    )
    step4b_sell_cleanup(ctx, broker)
    assert ctx.cleanup_sells == [], ctx.cleanup_sells
    print("[blocked-never-swept] FROZEN (blocked list) -> exempt from the cleanup pass too — OK")


def test_breakeven_lot_counts_as_green() -> None:
    """cost_per_share == current_price (exact breakeven) is 'not losing' -> still eligible."""
    ctx, broker = _position("EVEN", price=100.0, quantity=1.0, avg_cost=100.0, lots=[
        TaxLot(open_lot_id="a", quantity=1.0, cost_per_share=100.0, open_date=date(2026, 1, 1)),
    ])
    step4b_sell_cleanup(ctx, broker)
    assert len(ctx.cleanup_sells) == 1, ctx.cleanup_sells
    assert abs(ctx.cleanup_sells[0].realized_profit_dollars - 0.0) < 0.01
    print("[breakeven-counts-as-green] EVEN: exact breakeven lot -> still swept, $0.00 realized — OK")


def main() -> None:
    test_rule_a_sweeps_small_single_green_lot()
    test_rule_a_skips_when_above_threshold()
    test_rule_a_skips_loss_lot()
    test_rule_a_skips_multi_lot_position()
    test_rule_b_sweeps_large_remainder_after_gtp_this_cycle()
    test_rule_b_skipped_when_gtp_used_ordinary_order()
    test_target_price_to_sell_blocks_cleanup()
    test_blocked_symbol_never_swept()
    test_breakeven_lot_counts_as_green()
    print("\nSMOKE TEST (Sell Cleanup Pass) PASSED")


if __name__ == "__main__":
    main()
