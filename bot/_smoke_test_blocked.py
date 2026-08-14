"""Focused unit-style coverage for the `blocked` list control (portfolio_targets.json):
an asset in `blocked` is exempt from ALL buy/sell activity this cycle — drawdown audit,
GET THE PROFITS, and Underweight
buys — EXCEPT when it's ALSO in `forceSell` and currently held, in which case it's liquidated
in full instead of being frozen.

Run: PYTHONPATH=. python3 bot/_smoke_test_blocked.py
"""
from __future__ import annotations

from datetime import date

from bot.config import AssetTarget, ForceSellEntry, PortfolioConfig, PortfolioMetadata
from bot.models import DriftResult, Position, Quote, RunContext, TaxLot
from bot.steps import (
    has_any_breach, in_play_symbols, step1_fetch_state, step2_guardrails,
    step4_profit_taking, step6a_prepare_sells,
)


def _force_sell_dict(entries) -> dict:
    """entries: list of symbol strings (no trigger) or (symbol, trigger_price) tuples."""
    out = {}
    for e in entries:
        if isinstance(e, tuple):
            sym, trigger = e
            out[sym] = ForceSellEntry(asset=sym, trigger_price=trigger)
        else:
            out[e] = ForceSellEntry(asset=e)
    return out


def _cfg(blocked, force_sell) -> PortfolioConfig:
    meta = PortfolioMetadata(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=35.0,
        min_cash_absolute=250, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg1_price_change=0.5, leg2_price_change=0.5, leg3_price_change=0.1,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=12.5,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=100,
        materialize_profit_percentage=4.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=12.5, min_raw_gain_percent_to_sell=-1e9,  # disabled -> not what this file tests
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    targets = {
        "LTRN": AssetTarget(symbol="LTRN", weight=0.5, drift=0.3),
        "AAPL": AssetTarget(symbol="AAPL", weight=1.1, drift=0.5),
    }
    return PortfolioConfig(meta=meta, targets=targets, force_sell=_force_sell_dict(force_sell), blocked=blocked)


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
        pos = self._positions.get(symbol)
        if not pos:
            return []
        return [TaxLot(open_lot_id=f"{symbol}-lot1", quantity=pos.quantity,
                        cost_per_share=pos.avg_cost_basis, open_date=date(2026, 1, 1), is_selectable=True)]

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

    step2_guardrails(ctx, broker)
    assert "LTRN" not in in_play_symbols(ctx), "blocked -> excluded from Underweight buys"

    step4_profit_taking(ctx, broker)
    assert all(t.symbol != "LTRN" for t in ctx.profit_taking_sells)

    sells, halted, _ = step6a_prepare_sells(ctx)
    assert not halted
    assert all(t.symbol != "LTRN" for t in sells), "LTRN must not appear in any sell order this cycle"
    print("[blocked-frozen] LTRN (blocked, not forceSell) fully exempt from drawdown/sell/buy — OK")


def test_blocked_and_forcesell_and_held_liquidates_fully() -> None:
    """LTRN blocked AND forceSell AND currently held -> liquidate the full position, even though
    it's deep underwater (forceSell overrides the usual freeze)."""
    cfg = _cfg(blocked=["LTRN"], force_sell=["LTRN"])
    ctx = _base_ctx(cfg)
    positions = {"LTRN": Position(symbol="LTRN", quantity=300.0, avg_cost_basis=7.0)}
    price = {"LTRN": 2.7, "AAPL": 300.0}
    broker = _FakeBroker(positions, price)

    step1_fetch_state(ctx, broker)
    assert ctx.blocked_liquidations == ["LTRN"], ctx.blocked_liquidations
    assert "LTRN" in ctx.blocked_symbols
    assert has_any_breach(ctx), "a pending blocked+forceSell liquidation must not be a NO TRADES cycle"

    step2_guardrails(ctx, broker)
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

    step2_guardrails(ctx, broker)
    assert "LTRN" not in in_play_symbols(ctx), "still blocked -> not a buy candidate either"
    print("[blocked-forcesell-unheld] LTRN (blocked+forceSell, not held) stays frozen — OK")


def test_forcesell_trigger_price_not_met_stays_frozen() -> None:
    """LTRN blocked + forceSell with triggerPrice=4.5, currently $2.70 (below trigger) and
    held -> forceSell's override is NOT active yet, so it stays frozen rather than liquidating."""
    cfg = _cfg(blocked=["LTRN"], force_sell=[("LTRN", 4.5)])
    ctx = _base_ctx(cfg)
    positions = {"LTRN": Position(symbol="LTRN", quantity=300.0, avg_cost_basis=7.0)}
    price = {"LTRN": 2.70, "AAPL": 300.0}
    broker = _FakeBroker(positions, price)

    step1_fetch_state(ctx, broker)
    assert ctx.blocked_liquidations == [], "triggerPrice not cleared -> no liquidation yet"
    assert "trigger not yet met" in ctx.blocked_symbols["LTRN"], ctx.blocked_symbols["LTRN"]
    print(f"[forcesell-trigger-not-met] {ctx.blocked_symbols['LTRN']}")


def test_forcesell_trigger_price_met_liquidates() -> None:
    """Same setup, but price has recovered to $5.00 (above the $4.50 trigger) -> forceSell's
    override is now active, so the blocked+held position gets liquidated in full."""
    cfg = _cfg(blocked=["LTRN"], force_sell=[("LTRN", 4.5)])
    ctx = _base_ctx(cfg)
    positions = {"LTRN": Position(symbol="LTRN", quantity=300.0, avg_cost_basis=7.0)}
    price = {"LTRN": 5.00, "AAPL": 300.0}
    broker = _FakeBroker(positions, price)

    step1_fetch_state(ctx, broker)
    assert ctx.blocked_liquidations == ["LTRN"], ctx.blocked_liquidations
    sells, halted, _ = step6a_prepare_sells(ctx)
    assert not halted
    matches = [t for t in sells if t.symbol == "LTRN"]
    assert len(matches) == 1 and matches[0].quantity == 300.0
    print(f"[forcesell-trigger-met] LTRN liquidated at ${price['LTRN']} (trigger $4.50): {matches[0].reason}")


def main() -> None:
    test_blocked_and_not_forcesell_is_fully_frozen()
    test_blocked_and_forcesell_and_held_liquidates_fully()
    test_blocked_but_forcesell_not_held_is_still_frozen()
    test_forcesell_trigger_price_not_met_stays_frozen()
    test_forcesell_trigger_price_met_liquidates()
    print("\nSMOKE TEST (blocked list) PASSED")


if __name__ == "__main__":
    main()
