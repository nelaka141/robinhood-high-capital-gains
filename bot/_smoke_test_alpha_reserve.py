"""Focused unit-style coverage for two related Alpha Leader controls:

1. The Alpha Reserve (steps.step3_alpha_leader's hold-aside/merge logic +
   steps.resolve_alpha_reserve) — CLAUDE.md Step 3: when the Alpha Leader's multiplier
   allocation can't be deployed this cycle, hold that cash aside instead of redirecting it to
   Underweight targets, and give it back to the Alpha Leader (as a bonus on top of that day's
   normal target) once it's eligible to buy again.
2. `minimum_alpha_leader_sell_profit` — an extra profit-margin floor that applies ONLY when the
   sell candidate is the current Alpha Leader, on top of each mechanism's own gate (GET THE
   PROFITS, Momentum Reversal Trim, Overweight trim).

Pure logic tests against RunContext/steps functions directly, no snapshot/CLI plumbing needed
(same style as bot/_smoke_test_min_trade_value.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_alpha_reserve.py
"""
from __future__ import annotations

from datetime import date, timedelta

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import DriftResult, MomentumScore, Position, Quote, RunContext, TaxLot, TradeIntent
from bot.state import AlphaReserve
from bot.steps import resolve_alpha_reserve, step3_alpha_leader, step4_profit_taking


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.25,
        max_portfolio_percentage=90.0, alpha_cash_allocation_percentage=40.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, sold_asset_price_change_percentage=1.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_dollars=0.0, profit_resell_cooldown_days=15,
        sell_or_buy_value_limit=10, min_value_of_trade=0, settlement_reserve_target=0,
        settlement_lag_days=1, materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
        minimum_alpha_leader_sell_profit=5.0,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx_for_step3(**meta_overrides) -> RunContext:
    """ALPHA (alpha leader) mv=$1000, UW1 (underweight) mv=$100, both target 50% of a $2000
    account_balance. current_cash=$1000, no tax/settlement drag -> base_deployable_cash=$1000,
    alpha_cash_allocation_percentage=40% -> raw_alpha_target=$400, remaining_for_underweight=$600
    (UW1's entire gap, so allocations["UW1"] should always land on exactly $600)."""
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides),
        targets={"ALPHA": AssetTarget("ALPHA", weight=1.0), "UW1": AssetTarget("UW1", weight=1.0)},
        force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.alpha_leader = "ALPHA"
    ctx.current_cash = 1000.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 2000.0
    # Quotes must match _Step3Broker's closes ([-1] = 100 + 59*0.5 = 129.5 for ALPHA, flat 100
    # for UW1) so the Momentum_Score's Price_vs_EMA term reflects the same rising trend the
    # closes encode — a stale/mismatched quote would flip which symbol actually wins.
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=129.5), "UW1": Quote("UW1", last_trade_price=100.0)}
    ctx.momentum_scores = {"ALPHA": MomentumScore("ALPHA", 70, 100, 90, 5, 5), "UW1": MomentumScore("UW1", 50, 100, 100, 0, 0)}
    ctx.drift_results = {
        "ALPHA": DriftResult("ALPHA", 50, 50, 50, 50, 0, 1, market_value=1000.0),
        "UW1": DriftResult("UW1", 5, 5, 50, 50, 45, 1, market_value=100.0),
    }
    ctx.alpha_reserve = AlphaReserve()
    return ctx


class _Step3Broker:
    """step3_alpha_leader recomputes Momentum_Score itself from get_daily_closes — ALPHA gets a
    steadily rising series (real momentum winner), UW1 stays flat, so ctx.alpha_leader lands on
    "ALPHA" from the actual RSI/EMA math, not just the pre-set value."""

    def get_daily_closes(self, symbol, start, end):
        if symbol == "ALPHA":
            return [100.0 + i * 0.5 for i in range(60)]
        return [100.0] * 60


def test_guarded_leader_holds_cash_aside_not_redirected() -> None:
    ctx = _ctx_for_step3()
    ctx.buy_guarded_symbols = {"ALPHA": "profit-sold recently"}
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert "ALPHA" not in allocations, "guarded Alpha Leader must get nothing this cycle"
    assert allocations.get("UW1") == 600.0, f"UW1 should get exactly remaining_for_underweight ($600), got {allocations.get('UW1')}"
    assert ctx.alpha_target_dollars == 400.0, f"expected raw_alpha_target $400 held aside, got {ctx.alpha_target_dollars}"
    print(f"[guarded-holds-aside] ALPHA excluded, UW1=${allocations['UW1']:.2f}, "
          f"alpha_target_dollars=${ctx.alpha_target_dollars:.2f} (NOT redirected to UW1) — OK")


def test_eligible_leader_merges_matching_reserve() -> None:
    ctx = _ctx_for_step3()
    ctx.alpha_reserve = AlphaReserve(symbol="ALPHA", amount=250.0, lastUpdatedDate="2026-08-06")
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert allocations.get("ALPHA") == 650.0, f"expected raw $400 + reserve $250 = $650, got {allocations.get('ALPHA')}"
    assert allocations.get("UW1") == 600.0, "UW1's share must be unaffected by the reserve bonus"
    assert ctx.alpha_target_dollars == 650.0
    print(f"[eligible-merges-reserve] ALPHA=${allocations['ALPHA']:.2f} (raw $400 + reserve $250) — OK")


def test_eligible_leader_ignores_stale_reserve_for_other_symbol() -> None:
    ctx = _ctx_for_step3()
    ctx.alpha_reserve = AlphaReserve(symbol="SOME_OLD_LEADER", amount=999.0, lastUpdatedDate="2026-08-01")
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert allocations.get("ALPHA") == 400.0, f"stale reserve for a different symbol must not be applied, got {allocations.get('ALPHA')}"
    print("[stale-reserve-ignored] reserve tagged to a different (old) leader is not merged — OK")


def test_reserve_merge_respects_portfolio_cap() -> None:
    ctx = _ctx_for_step3(max_portfolio_percentage=65.0)  # cap_dollars=$1300, current_mv=$1000 -> headroom=$300
    ctx.alpha_reserve = AlphaReserve(symbol="ALPHA", amount=250.0, lastUpdatedDate="2026-08-06")
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert allocations.get("ALPHA") == 300.0, f"combined $650 must be clamped to the $300 headroom, got {allocations.get('ALPHA')}"
    assert ctx.alpha_target_dollars == 300.0
    print("[reserve-respects-cap] $650 desired clamped to $300 max_portfolio_percentage headroom — OK")


def test_resolve_alpha_reserve_clears_when_bought() -> None:
    ctx = RunContext(current_date=date(2026, 8, 7), config=None, account_number="TEST")
    ctx.alpha_leader = "ALPHA"
    ctx.alpha_target_dollars = 400.0
    ctx.buys = [TradeIntent(symbol="ALPHA", side="buy", dollar_amount=650.0)]
    result = resolve_alpha_reserve(ctx)
    assert result.symbol is None and result.amount == 0.0
    print("[resolve-clears-on-buy] Alpha Leader bought this cycle -> reserve cleared — OK")


def test_resolve_alpha_reserve_refreshes_when_not_bought() -> None:
    ctx = RunContext(current_date=date(2026, 8, 7), config=None, account_number="TEST")
    ctx.alpha_leader = "ALPHA"
    ctx.alpha_target_dollars = 400.0
    ctx.buys = [TradeIntent(symbol="OTHER", side="buy", dollar_amount=100.0)]  # ALPHA absent
    result = resolve_alpha_reserve(ctx)
    assert result.symbol == "ALPHA" and result.amount == 400.0 and result.lastUpdatedDate == "2026-08-07"
    print("[resolve-refreshes-on-no-buy] Alpha Leader didn't buy -> reserve refreshed to $400 — OK")


def test_resolve_alpha_reserve_leader_change_overwrites_not_accumulates() -> None:
    """A leader change (or the same leader's target changing day to day) must simply overwrite
    — never sum with — whatever was stored before."""
    ctx = RunContext(current_date=date(2026, 8, 8), config=None, account_number="TEST")
    ctx.alpha_leader = "NEWLEADER"
    ctx.alpha_target_dollars = 123.45
    ctx.buys = []
    ctx.alpha_reserve = AlphaReserve(symbol="OLDLEADER", amount=999.0, lastUpdatedDate="2026-08-07")
    result = resolve_alpha_reserve(ctx)
    assert result.symbol == "NEWLEADER" and result.amount == 123.45, "must overwrite, not add to, the old reserve"
    print("[resolve-overwrites-on-leader-change] old $999 reserve for OLDLEADER replaced by $123.45 for NEWLEADER — OK")


def test_resolve_alpha_reserve_untouched_when_no_leader() -> None:
    ctx = RunContext(current_date=date(2026, 8, 7), config=None, account_number="TEST")
    ctx.alpha_leader = None
    existing = AlphaReserve(symbol="X", amount=50.0, lastUpdatedDate="2026-08-01")
    ctx.alpha_reserve = existing
    result = resolve_alpha_reserve(ctx)
    assert result is existing
    print("[resolve-untouched-no-leader] Step 3 never ran (no alpha_leader) -> reserve left as-is — OK")


class _Step4Broker:
    def __init__(self):
        # Mildly oscillating (not perfectly flat) 60-day close series for every symbol,
        # including the beta benchmark — Step 4's Overweight-ranking tail unconditionally pulls
        # benchmark closes and computes beta, which errors on zero-variance input.
        self._series = [100.0 + (i % 5) * 0.3 for i in range(60)]

    def get_tax_lots(self, account_number: str, symbol: str):
        return [TaxLot(f"{symbol}-lot1", quantity=100.0, cost_per_share=1.0,
                        open_date=date(2026, 1, 1), is_selectable=True)]

    def get_daily_closes(self, symbol: str, start, end):
        return self._series


def _ctx_for_step4(alpha_leader: str = "ALPHA") -> RunContext:
    cfg = PortfolioConfig(
        meta=_meta(), targets={"ALPHA": AssetTarget("ALPHA", weight=1.0), "OTHER": AssetTarget("OTHER", weight=1.0)},
        force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.alpha_leader = alpha_leader
    return ctx


def test_alpha_leader_gtp_blocked_below_threshold_but_fires_above() -> None:
    ctx = _ctx_for_step4()
    ctx.positions = {"ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=103.0)}  # +3% > materialize_profit_percentage(2%) but < 5% guard
    step4_profit_taking(ctx, _Step4Broker())
    assert not ctx.profit_taking_sells, "GTP should be blocked for the Alpha Leader below minimum_alpha_leader_sell_profit"
    assert any("Alpha Leader sell guard" in s.reason for s in ctx.skipped)
    print("[alpha-gtp-blocked] ALPHA at +3% margin (< 5% guard) -> GTP correctly blocked")

    ctx2 = _ctx_for_step4()
    ctx2.positions = {"ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0)}
    ctx2.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=106.0)}  # +6% > 5% guard
    step4_profit_taking(ctx2, _Step4Broker())
    assert any(t.symbol == "ALPHA" for t in ctx2.profit_taking_sells), "GTP should fire once ALPHA clears the guard"
    print("[alpha-gtp-fires-above] ALPHA at +6% margin (> 5% guard) -> GTP fires normally")


def test_non_leader_gtp_unaffected_by_alpha_guard() -> None:
    ctx = _ctx_for_step4(alpha_leader="ALPHA")
    ctx.positions = {"OTHER": Position("OTHER", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"OTHER": Quote("OTHER", last_trade_price=103.0)}  # +3%, would be blocked if it were the leader
    step4_profit_taking(ctx, _Step4Broker())
    assert any(t.symbol == "OTHER" for t in ctx.profit_taking_sells), "non-leader GTP must be unaffected by the Alpha Leader guard"
    print("[non-leader-gtp-unaffected] OTHER (not Alpha Leader) at +3% -> GTP fires, guard doesn't apply")


def test_alpha_leader_mrt_blocked_below_threshold() -> None:
    ctx = _ctx_for_step4()
    ctx.positions = {"ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=101.5)}  # +1.5%: below materialize_profit_percentage(2%) so GTP never fires
    ctx.momentum_scores = {"ALPHA": MomentumScore("ALPHA", rsi14=20, ema9_now=95, ema9_prior=100,
                                                   price_vs_ema_pct=-15, ema_slope_pct=-5)}  # score well below threshold -10
    step4_profit_taking(ctx, _Step4Broker())
    assert not ctx.profit_taking_sells, "MRT should be blocked for the Alpha Leader below minimum_alpha_leader_sell_profit"
    assert any("Alpha Leader sell guard" in s.reason for s in ctx.skipped)
    print("[alpha-mrt-blocked] ALPHA at +1.5% margin (MRT gates clear, but < 5% guard) -> MRT correctly blocked")


def test_alpha_leader_overweight_trim_blocked_below_threshold() -> None:
    ctx = _ctx_for_step4()
    ctx.positions = {
        "ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0),
        "OTHER": Position("OTHER", quantity=10.0, avg_cost_basis=100.0),
    }
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=102.0), "OTHER": Quote("OTHER", last_trade_price=102.0)}  # both +2%
    ctx.momentum_scores = {}  # keep MRT out of the picture entirely
    ctx.drift_results = {
        "ALPHA": DriftResult("ALPHA", 60, 60, 50, 50, 10, 1, market_value=1020.0),
        "OTHER": DriftResult("OTHER", 60, 60, 50, 50, 10, 1, market_value=1020.0),
    }
    step4_profit_taking(ctx, _Step4Broker())
    trimmed = {t.symbol for t in ctx.overweight_trims}
    assert "ALPHA" not in trimmed, "Overweight trim should be blocked for the Alpha Leader below the guard"
    assert "OTHER" in trimmed, "non-leader Overweight trim must be unaffected by the Alpha Leader guard"
    print(f"[alpha-overweight-blocked] ranked candidates={trimmed} — ALPHA excluded, OTHER included — OK")


def main() -> None:
    test_guarded_leader_holds_cash_aside_not_redirected()
    test_eligible_leader_merges_matching_reserve()
    test_eligible_leader_ignores_stale_reserve_for_other_symbol()
    test_reserve_merge_respects_portfolio_cap()
    test_resolve_alpha_reserve_clears_when_bought()
    test_resolve_alpha_reserve_refreshes_when_not_bought()
    test_resolve_alpha_reserve_leader_change_overwrites_not_accumulates()
    test_resolve_alpha_reserve_untouched_when_no_leader()
    test_alpha_leader_gtp_blocked_below_threshold_but_fires_above()
    test_non_leader_gtp_unaffected_by_alpha_guard()
    test_alpha_leader_mrt_blocked_below_threshold()
    test_alpha_leader_overweight_trim_blocked_below_threshold()
    print("\nSMOKE TEST (Alpha Reserve + minimum_alpha_leader_sell_profit) PASSED")


if __name__ == "__main__":
    main()
