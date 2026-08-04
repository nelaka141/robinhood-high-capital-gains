"""Focused unit-style coverage for the `blocked` list control (portfolio_targets.json):
an asset in `blocked` is exempt from ALL buy/sell activity this cycle — drawdown audit,
GET THE PROFITS / Momentum Reversal Trim, Overweight High-Beta trims, and Underweight/Alpha
buys — EXCEPT when it's ALSO in `forceSell` and currently held, in which case it's liquidated
in full instead of being frozen.

Run: PYTHONPATH=. python3 bot/_smoke_test_blocked.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext
from bot.state import SettlementReserve
from bot.steps import (
    has_any_breach, in_play_symbols, step1_fetch_state, step2_guardrails,
    step4_profit_taking, step6a_prepare_sells,
)


def _cfg(blocked, force_sell) -> PortfolioConfig:
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
    targets = {
        "LTRN": AssetTarget(symbol="LTRN", weight=0.5, drift=0.3),
        "AAPL": AssetTarget(symbol="AAPL", weight=1.1, drift=0.5),
    }
    return PortfolioConfig(meta=meta, targets=targets, force_sell=force_sell, blocked=blocked)


class _FakeBroker:
    """Minimal BrokerClient stub covering everything step1/step2/step4 touch."""

    def __init__(self, positions, price):
        self._positions = positions
        self._price = price

    def get_positions(self, account_number):
        return dict(self._positions)

    def get_quotes(self, symbols):
        return {s: Quote(symbol=s, last_trade_price=self._price[s]) for s in symbols}

    def get_tax_lots(self, account_number, symbol):
        return []

    def get_daily_closes(self, symbol, start, end):
        return []

    def get_buying_power(self, account_number):
        return 5000.0

    def get_cash_ledger(self, account_number):
        return 5000.0

    def get_realized_pnl_ytd(self, account_number, year_start, as_of):
        return 0.0


def _base_ctx(cfg) -> RunContext:
    ctx = RunContext(current_date=date(2026, 8, 4), config=cfg, account_number="TEST")
    ctx.reserve = SettlementReserve(pending_draws=[])
    ctx.price_state = {}
    return ctx


def test_blocked_and_not_forcesell_is_fully_frozen() -> None:
    """LTRN blocked but NOT in forceSell, deep in a drawdown (would otherwise trigger emergency
    liquidation) and severely underweight (would otherwise be an Underweight buy candidate) —
    must be completely exempt from both."""
    cfg = _cfg(blocked=["LTRN"], force_sell=[])
    ctx = _base_ctx(cfg)
    positions = {"LTRN": Position(symbol="LTRN", quantity=300.0, avg_cost_basis=7.0),
                 "AAPL": Position(symbol="AAPL", quantity=1.0, avg_cost_basis=300.0)}
    price = {"LTRN": 2.7, "AAPL": 300.0}  # LTRN down ~61% from cost -> would breach drawdown
    broker = _FakeBroker(positions, price)

    step1_fetch_state(ctx, broker)
    assert "LTRN" in ctx.blocked_symbols, ctx.blocked_symbols
    assert ctx.blocked_liquidations == [], "not in forceSell -> no forced liquidation"
    assert "LTRN" not in ctx.drawdown_liquidations, "blocked -> exempt even from drawdown audit"

    step2_guardrails(ctx)
    assert "LTRN" not in in_play_symbols(ctx), "blocked -> excluded from Alpha Leader/Underweight buys"

    step4_profit_taking(ctx, broker)
    assert all(t.symbol != "LTRN" for t in ctx.profit_taking_sells)
    assert all(t.symbol != "LTRN" for t in ctx.overweight_trims)

    sells, halted, _ = step6a_prepare_sells(ctx)
    assert not halted
    assert all(t.symbol != "LTRN" for t in sells), "LTRN must not appear in any sell order this cycle"
    print("[blocked-frozen] LTRN (blocked, not forceSell) fully exempt from drawdown/sell/buy — OK")


def test_blocked_and_forcesell_and_held_liquidates_fully() -> None:
    """LTRN blocked AND forceSell AND currently held -> liquidate the full position, even though
    it's deep underwater (forceSell overrides the usual profit-margin/lock-in gates, same as it
    already does for routine Overweight trims)."""
    cfg = _cfg(blocked=["LTRN"], force_sell=["LTRN"])
    ctx = _base_ctx(cfg)
    positions = {"LTRN": Position(symbol="LTRN", quantity=300.0, avg_cost_basis=7.0)}
    price = {"LTRN": 2.7, "AAPL": 300.0}
    broker = _FakeBroker(positions, price)

    step1_fetch_state(ctx, broker)
    assert ctx.blocked_liquidations == ["LTRN"], ctx.blocked_liquidations
    assert "LTRN" in ctx.blocked_symbols
    assert has_any_breach(ctx), "a pending blocked+forceSell liquidation must not be a NO TRADES cycle"

    step2_guardrails(ctx)
    step4_profit_taking(ctx, broker)  # must not ALSO try to profit-take/trim it — blocked_symbols skips it
    assert all(t.symbol != "LTRN" for t in ctx.profit_taking_sells)

    sells, halted, _ = step6a_prepare_sells(ctx)
    assert not halted
    matches = [t for t in sells if t.symbol == "LTRN"]
    assert len(matches) == 1, sells
    assert matches[0].quantity == 300.0, "must liquidate the entire position"
    assert "forceSell" in matches[0].reason
    print(f"[blocked-forcesell-liquidate] LTRN liquidated in full: {matches[0].quantity} sh — {matches[0].reason}")


def test_blocked_but_forcesell_not_held_is_still_frozen() -> None:
    """forceSell alone doesn't override `blocked` — the exception is forceSell AND currently
    held. An unheld blocked+forceSell symbol stays frozen (nothing to liquidate, and it must
    not become a buy candidate just because it's in forceSell)."""
    cfg = _cfg(blocked=["LTRN"], force_sell=["LTRN"])
    ctx = _base_ctx(cfg)
    positions = {}  # not held
    price = {"LTRN": 2.7, "AAPL": 300.0}
    broker = _FakeBroker(positions, price)

    step1_fetch_state(ctx, broker)
    assert ctx.blocked_liquidations == [], "nothing held -> nothing to liquidate"
    assert "LTRN" in ctx.blocked_symbols

    step2_guardrails(ctx)
    assert "LTRN" not in in_play_symbols(ctx), "still blocked -> not a buy candidate either"
    print("[blocked-forcesell-unheld] LTRN (blocked+forceSell, not held) stays frozen — OK")


def main() -> None:
    test_blocked_and_not_forcesell_is_fully_frozen()
    test_blocked_and_forcesell_and_held_liquidates_fully()
    test_blocked_but_forcesell_not_held_is_still_frozen()
    print("\nSMOKE TEST (blocked list) PASSED")


if __name__ == "__main__":
    main()
