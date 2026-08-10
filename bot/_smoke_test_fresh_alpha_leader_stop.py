"""Focused coverage for the Fresh Alpha Leader Stop (CLAUDE.md Step 1) — a tighter,
faster-acting stop-loss scoped to a position bought AS the Alpha Leader within the last
`alpha_leader_fresh_position_days` days, measured against that specific buy's price
(`lastAlphaLeaderBuyPrice`/`lastAlphaLeaderBuyDate` in peak/prices.json) rather than the
portfolio-wide peak/cost-basis pair the main Drawdown Audit uses.

Pure logic tests against RunContext/steps functions directly (same style as
bot/_smoke_test_min_trade_value.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_fresh_alpha_leader_stop.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TradeIntent
from bot.state import AssetPriceState
from bot import steps
from bot.cli import _update_profit_sell_and_purchase_dates


class _Broker:
    def __init__(self, positions, quotes):
        self._positions = positions
        self._quotes = quotes

    def get_positions(self, account_number):
        return self._positions

    def get_quotes(self, symbols):
        return self._quotes

    def get_tax_lots(self, account_number, symbol):
        return []

    def get_buying_power(self, account_number):
        return 1000.0

    def get_cash_ledger(self, account_number):
        return 1000.0

    def get_realized_pnl_ytd(self, account_number, year_start, as_of):
        return 0.0


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.25,
        max_portfolio_percentage=90.0, alpha_cash_allocation_percentage=35.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, z_score_points=0.5, z_score_upward_points=0.1,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=0.0,
        momentum_reversal_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_dollars=0.0, z_score_sell_points=0.2,
        profit_resell_cooldown_days=15,
        sell_or_buy_value_limit=10, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
        minimum_alpha_leader_sell_profit=0.0, alpha_leader_least_momentum_score=-1000.0,
        alpha_rank_reduction_percent=0.0, min_momentum_score_to_fill_underweight=-1000.0,
        alpha_leader_fresh_position_days=3, alpha_leader_fresh_drawdown_percentage=15.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx(symbol="ALPHA", price=85.0, quantity=10.0, avg_cost_basis=80.0,
          last_alpha_buy_price=100.0, last_alpha_buy_date="2026-08-05",
          current_date=date(2026, 8, 7), peak_price=None, blocked=None,
          **meta_overrides) -> RunContext:
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides),
        targets={symbol: AssetTarget(symbol, weight=1.0)},
        force_sell={}, blocked=blocked or [],
    )
    ctx = RunContext(current_date=current_date, config=cfg, account_number="TEST")
    ctx.price_state = {
        symbol: AssetPriceState(
            peakPrice=peak_price, lastAlphaLeaderBuyPrice=last_alpha_buy_price,
            lastAlphaLeaderBuyDate=last_alpha_buy_date,
        )
    }
    positions = {symbol: Position(symbol, quantity=quantity, avg_cost_basis=avg_cost_basis)}
    quotes = {symbol: Quote(symbol, last_trade_price=price)}
    broker = _Broker(positions, quotes)
    ctx.current_cash = 1000.0
    steps.step1_fetch_state(ctx, broker, repo_dir="/nonexistent")  # transferred_basis.json read
    return ctx


def test_fires_within_window_and_over_threshold() -> None:
    """Bought as Alpha Leader at $100 two days ago, now $83 -> -17% >= 15% threshold -> fires."""
    ctx = _ctx(price=83.0, last_alpha_buy_price=100.0, last_alpha_buy_date="2026-08-05",
               current_date=date(2026, 8, 7), avg_cost_basis=100.0, peak_price=100.0)
    assert "ALPHA" in ctx.fresh_alpha_leader_liquidations, (
        f"expected a -17% drop 2 days after the Alpha Leader buy to fire, got "
        f"{ctx.fresh_alpha_leader_liquidations}"
    )
    assert steps.has_any_breach(ctx), "a pending fresh-stop liquidation alone must count as a breach"
    print("[fresh-stop-fires] -17% drop 2 days after Alpha Leader buy -> liquidation flagged — OK")


def test_does_not_fire_below_threshold() -> None:
    """Only a -10% drop (< 15% threshold) -> must NOT fire."""
    ctx = _ctx(price=90.0, last_alpha_buy_price=100.0, last_alpha_buy_date="2026-08-05",
               current_date=date(2026, 8, 7), avg_cost_basis=100.0, peak_price=100.0)
    assert ctx.fresh_alpha_leader_liquidations == [], (
        f"a -10% drop is under the 15% threshold, must not fire, got {ctx.fresh_alpha_leader_liquidations}"
    )
    print("[fresh-stop-under-threshold] -10% drop (< 15%) -> does not fire — OK")


def test_does_not_fire_outside_window() -> None:
    """-17% drop, but the Alpha Leader buy was 10 days ago (> alpha_leader_fresh_position_days=3)."""
    ctx = _ctx(price=83.0, last_alpha_buy_price=100.0, last_alpha_buy_date="2026-07-28",
               current_date=date(2026, 8, 7), avg_cost_basis=100.0, peak_price=100.0)
    assert ctx.fresh_alpha_leader_liquidations == [], (
        f"buy was 10 days ago (> 3-day window) -> must not fire, got {ctx.fresh_alpha_leader_liquidations}"
    )
    print("[fresh-stop-outside-window] -17% drop but buy was 10 days ago (window=3d) -> does not fire — OK")


def test_does_not_fire_with_no_alpha_leader_buy_on_record() -> None:
    """No lastAlphaLeaderBuyPrice/Date at all (this symbol was never bought as Alpha Leader)."""
    ctx = _ctx(price=50.0, last_alpha_buy_price=None, last_alpha_buy_date=None,
               avg_cost_basis=100.0, peak_price=100.0)
    assert ctx.fresh_alpha_leader_liquidations == [], (
        f"no Alpha Leader buy on record -> must not fire, got {ctx.fresh_alpha_leader_liquidations}"
    )
    print("[fresh-stop-no-record] no lastAlphaLeaderBuyPrice/Date -> does not fire — OK")


def test_blocked_symbol_exempt() -> None:
    ctx = _ctx(price=83.0, last_alpha_buy_price=100.0, last_alpha_buy_date="2026-08-05",
               current_date=date(2026, 8, 7), avg_cost_basis=100.0, peak_price=100.0,
               blocked=["ALPHA"])
    assert ctx.fresh_alpha_leader_liquidations == [], (
        f"blocked symbols are exempt even from this stop, got {ctx.fresh_alpha_leader_liquidations}"
    )
    print("[fresh-stop-blocked-exempt] blocked symbol -> exempt from the Fresh Alpha Leader Stop — OK")


def test_no_double_liquidation_with_main_drawdown_audit() -> None:
    """A -40% drop from both peak AND cost basis clears the main Drawdown Audit's 35% bar too --
    it must land in drawdown_liquidations only, not ALSO in fresh_alpha_leader_liquidations
    (step6a_prepare_sells would otherwise try to sell the same position twice)."""
    ctx = _ctx(price=60.0, last_alpha_buy_price=100.0, last_alpha_buy_date="2026-08-05",
               current_date=date(2026, 8, 7), avg_cost_basis=100.0, peak_price=100.0)
    assert ctx.drawdown_liquidations == ["ALPHA"], f"expected main Drawdown Audit to fire, got {ctx.drawdown_liquidations}"
    assert ctx.fresh_alpha_leader_liquidations == [], (
        f"already caught by the main Drawdown Audit -> must not also appear here, "
        f"got {ctx.fresh_alpha_leader_liquidations}"
    )
    print("[fresh-stop-no-double-sell] -40% drop clears BOTH stops -> only drawdown_liquidations fires, no double-sell — OK")


def test_step6a_builds_sell_order_and_filters_correctly() -> None:
    ctx = _ctx(price=83.0, last_alpha_buy_price=100.0, last_alpha_buy_date="2026-08-05",
               current_date=date(2026, 8, 7), avg_cost_basis=100.0, peak_price=100.0, quantity=10.0)
    assert ctx.fresh_alpha_leader_liquidations == ["ALPHA"]
    sells, halted, reason = steps.step6a_prepare_sells(ctx, planned_buys={})
    assert not halted
    assert len(sells) == 1 and sells[0].symbol == "ALPHA" and sells[0].quantity == 10.0
    assert "Fresh Alpha Leader Stop" in sells[0].reason
    assert ctx.fresh_alpha_leader_liquidations == ["ALPHA"], "survived sell_or_buy_value_limit -> stays in the list"
    print(f"[fresh-stop-step6a] sell order built: {sells[0].reason} — OK")


def test_lastAlphaLeaderBuyPrice_set_when_buy_fires_for_alpha_leader() -> None:
    """cli.py's _update_profit_sell_and_purchase_dates should stamp lastAlphaLeaderBuyPrice/Date
    whenever a buy fires for whichever symbol is ctx.alpha_leader this cycle -- the basis the
    Fresh Alpha Leader Stop reads on a FUTURE cycle."""
    cfg = PortfolioConfig(
        meta=_meta(), targets={"ALPHA": AssetTarget("ALPHA", weight=1.0), "OTHER": AssetTarget("OTHER", weight=1.0)},
        force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.alpha_leader = "ALPHA"
    ctx.price_state = {"ALPHA": AssetPriceState(), "OTHER": AssetPriceState()}
    ctx.positions = {}
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=105.0), "OTHER": Quote("OTHER", last_trade_price=50.0)}
    ctx.buys = [
        TradeIntent(symbol="ALPHA", side="buy", dollar_amount=500.0),
        TradeIntent(symbol="OTHER", side="buy", dollar_amount=200.0),
    ]
    _update_profit_sell_and_purchase_dates(ctx)
    assert ctx.price_state["ALPHA"].lastAlphaLeaderBuyPrice == 105.0
    assert ctx.price_state["ALPHA"].lastAlphaLeaderBuyDate == "2026-08-07"
    assert ctx.price_state["OTHER"].lastAlphaLeaderBuyPrice is None, "OTHER wasn't the Alpha Leader -> must stay unset"
    print("[fresh-stop-stamps-on-buy] ALPHA (Alpha Leader) buy stamps lastAlphaLeaderBuyPrice=$105.00; "
          "OTHER (non-leader) buy leaves it unset — OK")


def main() -> None:
    test_fires_within_window_and_over_threshold()
    test_does_not_fire_below_threshold()
    test_does_not_fire_outside_window()
    test_does_not_fire_with_no_alpha_leader_buy_on_record()
    test_blocked_symbol_exempt()
    test_no_double_liquidation_with_main_drawdown_audit()
    test_step6a_builds_sell_order_and_filters_correctly()
    test_lastAlphaLeaderBuyPrice_set_when_buy_fires_for_alpha_leader()
    print("\nSMOKE TEST (Fresh Alpha Leader Stop) PASSED")


if __name__ == "__main__":
    main()
