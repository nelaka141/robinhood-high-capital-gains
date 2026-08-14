"""Focused coverage for the two price-target controls (CLAUDE.md, portfolio_targets.json):

1. `target_price_to_sell` (symbol -> price floor): blocks a sale of that symbol by ANY
   mechanism — Drawdown Audit, blocked+forceSell liquidation, and GET THE
   PROFITS alike — until
   `current_price` crosses (reaches/exceeds) the floor.
2. `target_price_to_buy` (symbol -> price ceiling): blocks a buy of that symbol by ANY
   mechanism (Underweight allocation, profit-sell repurchase) until
   `current_price` drops to/below the ceiling.

Pure logic tests against RunContext/steps functions directly (same style as
bot/_smoke_test_wash_sale.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_price_targets.py
"""
from __future__ import annotations

import math
from datetime import date, timedelta

from bot.config import AssetTarget, ForceSellEntry, PortfolioConfig, PortfolioMetadata
from bot.models import DriftResult, Position, Quote, RunContext, TaxLot
from bot.state import AssetPriceState
from bot import steps


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=1_000_000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg1_price_change=-999.0, leg2_price_change=-999.0,
        leg3_price_change=-999.0,
        lock_in_period=0, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=0.0,
        profit_resell_cooldown_days=0,
        selling_price_change=999.0,
        sell_or_buy_value_limit=1, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, min_raw_gain_percent_to_sell=-1e9,
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _cfg(symbols, force_sell=None, target_price_to_sell=None, target_price_to_buy=None, **meta_overrides):
    return PortfolioConfig(
        meta=_meta(**meta_overrides),
        targets={s: AssetTarget(s, weight=1.0) for s in symbols},
        force_sell=force_sell or {}, blocked=[],
        target_price_to_sell=target_price_to_sell or {},
        target_price_to_buy=target_price_to_buy or {},
    )


class _Broker:
    def __init__(self, positions=None, quotes=None, lots=None, closes=None):
        self._positions = positions or {}
        self._quotes = quotes or {}
        self._lots = lots or {}
        self._closes = closes or {}

    def get_positions(self, account_number):
        return dict(self._positions)

    def get_quotes(self, symbols):
        return {s: self._quotes[s] for s in symbols}

    def get_tax_lots(self, account_number, symbol):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol, start, end):
        return self._closes.get(symbol, [95.0, 96.0, 94.5])

    def get_buying_power(self, account_number):
        return 10_000.0

    def get_cash_ledger(self, account_number):
        return 10_000.0

    def get_realized_pnl_ytd(self, account_number, year_start, as_of):
        return 0.0


# ------------------------------------------------------------------------------------------
# target_price_to_sell — Drawdown Audit
# ------------------------------------------------------------------------------------------

def test_sell_target_blocks_drawdown_audit() -> None:
    """DROP is deep enough underwater to trip the Drawdown Audit, but its price ($60) is still
    below its target_price_to_sell ($75) -> the liquidation must NOT fire."""
    cfg = _cfg(["DROP"], target_price_to_sell={"DROP": 75.0})
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.price_state = {"DROP": AssetPriceState(peakPrice=100.0)}
    positions = {"DROP": Position(symbol="DROP", quantity=10.0, avg_cost_basis=100.0)}
    quotes = {"DROP": Quote(symbol="DROP", last_trade_price=60.0)}  # -40% vs peak and cost
    steps.step1_fetch_state(ctx, _Broker(positions, quotes), repo_dir="/nonexistent")
    assert ctx.drawdown_liquidations == [], ctx.drawdown_liquidations
    assert any(
        s.symbol == "DROP" and "target_price_to_sell" in s.reason and s.would_be_action == "Drawdown Audit liquidation"
        for s in ctx.skipped
    ), ctx.skipped
    print("[sell-target-blocks-drawdown] DROP would breach Drawdown Audit but target_price_to_sell blocks it — OK")


def test_sell_target_allows_drawdown_audit_once_crossed() -> None:
    """Same setup, but price ($80) has crossed the $75 target -> Drawdown Audit fires normally."""
    cfg = _cfg(["DROP"], target_price_to_sell={"DROP": 75.0})
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.price_state = {"DROP": AssetPriceState(peakPrice=200.0)}
    positions = {"DROP": Position(symbol="DROP", quantity=10.0, avg_cost_basis=200.0)}
    quotes = {"DROP": Quote(symbol="DROP", last_trade_price=80.0)}  # -60% vs peak and cost, but >= $75 target
    steps.step1_fetch_state(ctx, _Broker(positions, quotes), repo_dir="/nonexistent")
    assert ctx.drawdown_liquidations == ["DROP"], ctx.drawdown_liquidations
    print("[sell-target-crossed-drawdown] price at/above target_price_to_sell -> Drawdown Audit fires normally — OK")


def test_sell_target_blocks_blocked_forcesell_liquidation() -> None:
    """LTRN is blocked + forceSell (no trigger) + held, so it would normally liquidate in full —
    but target_price_to_sell ($5.00) hasn't been crossed at the current $2.70 price."""
    cfg = _cfg(["LTRN"], force_sell={"LTRN": ForceSellEntry(asset="LTRN")}, target_price_to_sell={"LTRN": 5.0})
    cfg = PortfolioConfig(
        meta=cfg.meta, targets=cfg.targets, force_sell=cfg.force_sell, blocked=["LTRN"],
        target_price_to_sell=cfg.target_price_to_sell, target_price_to_buy=cfg.target_price_to_buy,
    )
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.price_state = {"LTRN": AssetPriceState()}
    positions = {"LTRN": Position(symbol="LTRN", quantity=300.0, avg_cost_basis=7.0)}
    quotes = {"LTRN": Quote(symbol="LTRN", last_trade_price=2.70)}
    steps.step1_fetch_state(ctx, _Broker(positions, quotes), repo_dir="/nonexistent")
    assert ctx.blocked_liquidations == [], ctx.blocked_liquidations
    assert "target_price_to_sell" in ctx.blocked_symbols["LTRN"], ctx.blocked_symbols["LTRN"]
    print(f"[sell-target-blocks-forcesell-liquidation] {ctx.blocked_symbols['LTRN']}")


def test_sell_target_blocks_gtp() -> None:
    """PROFIT clears GET THE PROFITS' percent gate handily (+60%), but its target_price_to_sell
    ($90) hasn't been crossed at the current $80 price -> the sale must not fire."""
    cfg = _cfg(["PROFIT"], target_price_to_sell={"PROFIT": 90.0})
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.positions = {"PROFIT": Position(symbol="PROFIT", quantity=20.0, avg_cost_basis=50.0)}
    ctx.quotes = {"PROFIT": Quote(symbol="PROFIT", last_trade_price=80.0)}
    lots = {"PROFIT": [TaxLot("lot1", quantity=20.0, cost_per_share=50.0, open_date=date(2026, 1, 1), is_selectable=True)]}
    steps.step4_profit_taking(ctx, _Broker(lots=lots))
    assert ctx.profit_taking_sells == [], ctx.profit_taking_sells
    assert any(s.symbol == "PROFIT" and "target_price_to_sell" in s.reason for s in ctx.skipped), ctx.skipped
    print("[sell-target-blocks-gtp] PROFIT clears GTP's gates but target_price_to_sell blocks the sale — OK")


# ------------------------------------------------------------------------------------------
# target_price_to_buy — Underweight allocation
# ------------------------------------------------------------------------------------------

def _series(drift: float, amp: float = 1.0, n: int = 60) -> list:
    return [100.0 + drift * i + amp * math.sin(i / 3.0) for i in range(n)]


class _Step3Broker:
    def __init__(self, drifts: dict):
        self._drifts = drifts

    def get_daily_closes(self, symbol, start, end):
        return _series(self._drifts[symbol])


def test_buy_target_blocks_underweight_allocation() -> None:
    """CHASE is the sole qualifying Underweight candidate, but its live price ($150) is above its
    target_price_to_buy ($120) -> step2's buy-guard must exclude it from the Underweight pool."""
    cfg = _cfg(["CHASE"], target_price_to_buy={"CHASE": 120.0})
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.current_cash = 1000.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 10000.0
    ctx.price_state = {}
    ctx.positions = {}
    ctx.quotes = {"CHASE": Quote("CHASE", last_trade_price=150.0)}
    ctx.drift_results = {
        "CHASE": DriftResult("CHASE", current_percentage=0, actual_weight=0, target_weight=1.0,
                              target_percentage=90.0, drift=1.0, asset_drift_tolerance=0.1, market_value=0.0),
    }
    steps.step2_guardrails(ctx, _Step3Broker({"CHASE": 0.6}))
    assert "CHASE" in ctx.buy_guarded_symbols, ctx.buy_guarded_symbols
    assert any("target_price_to_buy" in r for r in ctx.buy_guarded_symbols["CHASE"]), ctx.buy_guarded_symbols["CHASE"]
    allocations = steps.step3_underweight_buys(ctx, _Step3Broker({"CHASE": 0.6}))
    assert allocations.get("CHASE", 0.0) == 0.0, f"CHASE must get no Underweight allocation, got {allocations.get('CHASE')}"
    print("[buy-target-blocks-underweight] CHASE (price above target_price_to_buy) excluded from the Underweight pool — OK")


def test_buy_target_shifts_fill_to_next_ranked_candidate() -> None:
    """TOP has the highest Momentum_Score but its price ($150) is above its target_price_to_buy
    ($120) -> it is buy-guarded, and the top-down Underweight fill must shift down to MID (next
    in the ranking) instead — the user's rule: a guarded top-ranked candidate's allocation moves
    down the ranking, it is never held back for the guarded symbol."""
    cfg = _cfg(["TOP", "MID"], target_price_to_buy={"TOP": 120.0})
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.current_cash = 1000.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 10000.0
    ctx.price_state = {}
    ctx.positions = {}
    ctx.quotes = {"TOP": Quote("TOP", last_trade_price=150.0), "MID": Quote("MID", last_trade_price=100.0)}
    ctx.drift_results = {
        "TOP": DriftResult("TOP", 0, 0, 1.0, 20.0, 1.0, 0.1, market_value=0.0),
        "MID": DriftResult("MID", 0, 0, 1.0, 20.0, 1.0, 0.1, market_value=0.0),
    }
    broker = _Step3Broker({"TOP": 0.6, "MID": 0.0})
    steps.step2_guardrails(ctx, broker)
    assert "TOP" in ctx.buy_guarded_symbols, ctx.buy_guarded_symbols
    allocations = steps.step3_underweight_buys(ctx, broker)
    assert allocations.get("TOP", 0.0) == 0.0, f"TOP is buy-guarded and must get nothing, got {allocations.get('TOP')}"
    assert allocations.get("MID", 0.0) > 0.0, f"the fill must shift down to MID, got {allocations}"
    print("[buy-target-shifts-fill-down] TOP guarded -> allocation shifts down to MID — OK")


def test_buy_target_allows_once_price_at_or_below() -> None:
    """Same TOP/MID setup, but TOP's price ($115) has now dropped to/below its $120 target ->
    the buy-target guard no longer applies and TOP (highest score) is filled first."""
    cfg = _cfg(["TOP", "MID"], target_price_to_buy={"TOP": 120.0})
    ctx = RunContext(current_date=date(2026, 8, 14), config=cfg, account_number="TEST")
    ctx.current_cash = 1000.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 10000.0
    ctx.price_state = {}
    ctx.positions = {}
    ctx.quotes = {"TOP": Quote("TOP", last_trade_price=115.0), "MID": Quote("MID", last_trade_price=100.0)}
    ctx.drift_results = {
        "TOP": DriftResult("TOP", 0, 0, 1.0, 20.0, 1.0, 0.1, market_value=0.0),
        "MID": DriftResult("MID", 0, 0, 1.0, 20.0, 1.0, 0.1, market_value=0.0),
    }
    broker = _Step3Broker({"TOP": 0.6, "MID": 0.0})
    steps.step2_guardrails(ctx, broker)
    assert "TOP" not in ctx.buy_guarded_symbols, ctx.buy_guarded_symbols
    allocations = steps.step3_underweight_buys(ctx, broker)
    assert allocations.get("TOP", 0.0) == 1000.0, (
        f"TOP (highest score, $2000 gap) should absorb the full $1000 cash first, got {allocations}"
    )
    assert allocations.get("MID", 0.0) == 0.0, allocations
    print("[buy-target-allows-at-target] TOP's price at/below target_price_to_buy -> filled first — OK")


def test_no_price_target_entry_unaffected() -> None:
    """A symbol with no target_price_to_sell/target_price_to_buy entry is never touched by
    either helper, at any price."""
    cfg = _cfg(["PLAIN"])
    assert not cfg.sell_price_target_blocks("PLAIN", 0.01)
    assert not cfg.buy_price_target_blocks("PLAIN", 1_000_000.0)
    print("[no-price-target-entry] symbol with no configured target is never gated by either control — OK")


def main() -> None:
    test_sell_target_blocks_drawdown_audit()
    test_sell_target_allows_drawdown_audit_once_crossed()
    test_sell_target_blocks_blocked_forcesell_liquidation()
    test_sell_target_blocks_gtp()
    test_buy_target_blocks_underweight_allocation()
    test_buy_target_shifts_fill_to_next_ranked_candidate()
    test_buy_target_allows_once_price_at_or_below()
    test_no_price_target_entry_unaffected()
    print("\nSMOKE TEST (target_price_to_sell / target_price_to_buy) PASSED")


if __name__ == "__main__":
    main()
