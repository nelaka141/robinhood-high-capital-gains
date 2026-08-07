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
        sell_or_buy_value_limit=10, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
        minimum_alpha_leader_sell_profit=600.0,  # a DOLLAR floor, not a percentage
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx_for_step3(uw1_market_value: float = 700.0, **meta_overrides) -> RunContext:
    """ALPHA (alpha leader) mv=$1000, UW1 (underweight) mv=$700 by default, both target 50% of a
    $2000 account_balance -> UW1's gap = 1000-700 = $300. current_cash=$1000, no tax drag ->
    base_deployable_cash=$1000, alpha_cash_allocation_percentage=40% ->
    raw_alpha_target=$400, remaining_for_underweight=$600. Since total_gap($300) <=
    remaining_for_underweight($600) at the default mv, cash is abundant enough to close UW1's
    gap and then some -> existing pro-rata behavior: UW1 gets the FULL remaining_for_underweight
    pool ($600), not just its own $300 gap (CLAUDE.md Step 7: keep cash deployed) -> no harvest
    needed. Pass a smaller uw1_market_value to widen the gap past remaining_for_underweight and
    exercise the harvest-triggering path instead (see test_underweight_shortfall_* below)."""
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
        "UW1": DriftResult("UW1", 35, 35, 50, 50, 15, 1, market_value=uw1_market_value),
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
    assert ctx.alpha_target_dollars == 400.0, f"expected raw_alpha_target $400 held aside (no multiplier while guarded), got {ctx.alpha_target_dollars}"
    assert ctx.harvest_needed_dollars == 0.0, f"guarded leader requests no multiplier, UW1 gap is cash-covered -> no harvest, got {ctx.harvest_needed_dollars}"
    print(f"[guarded-holds-aside] ALPHA excluded, UW1=${allocations['UW1']:.2f}, "
          f"alpha_target_dollars=${ctx.alpha_target_dollars:.2f} (NOT redirected to UW1), harvest=$0 — OK")


def test_eligible_leader_merges_matching_reserve() -> None:
    # base_deployable_cash=$1000, raw_alpha_target=$400, multiplier_cash=$1000*(1.25-1)=$250,
    # reserve_bonus=$250 -> desired=$900, headroom=0.9*2000-1000=$800 -> capped to $800.
    # cash_fundable=min($800, raw $400 + reserve $250=$650)=$650 -> harvest=$800-$650=$150
    # (exactly the portion of multiplier_cash that actually fit under the cap).
    ctx = _ctx_for_step3()
    ctx.alpha_reserve = AlphaReserve(symbol="ALPHA", amount=250.0, lastUpdatedDate="2026-08-06")
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert allocations.get("ALPHA") == 800.0, f"expected raw $400 + multiplier $250 + reserve $250, capped to $800 headroom, got {allocations.get('ALPHA')}"
    assert allocations.get("UW1") == 600.0, "UW1's share must be unaffected by the alpha side"
    assert ctx.alpha_target_dollars == 800.0
    assert ctx.harvest_needed_dollars == 150.0, f"expected $150 to harvest (the capped multiplier slice), got {ctx.harvest_needed_dollars}"
    print(f"[eligible-merges-reserve] ALPHA=${allocations['ALPHA']:.2f} (raw $400 + multiplier $250 + reserve $250, capped), harvest=$150 — OK")


def test_eligible_leader_ignores_stale_reserve_for_other_symbol() -> None:
    # desired = raw $400 + multiplier $250 + reserve $0 (stale, different symbol) = $650,
    # under the $800 headroom -> uncapped. cash_fundable=min($650, $400)=$400 -> harvest=$250
    # (exactly multiplier_cash, since no reserve bonus this time).
    ctx = _ctx_for_step3()
    ctx.alpha_reserve = AlphaReserve(symbol="SOME_OLD_LEADER", amount=999.0, lastUpdatedDate="2026-08-01")
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert allocations.get("ALPHA") == 650.0, f"stale reserve for a different symbol must not be applied, got {allocations.get('ALPHA')}"
    assert ctx.harvest_needed_dollars == 250.0, f"expected $250 harvest (multiplier_cash only), got {ctx.harvest_needed_dollars}"
    print("[stale-reserve-ignored] reserve tagged to a different (old) leader is not merged; harvest=$250 (multiplier only) — OK")


def test_reserve_merge_respects_portfolio_cap() -> None:
    # cap_dollars=0.65*2000=$1300, current_mv=$1000 -> headroom=$300. desired=$400+$250+$250=$900
    # clamped to $300. cash_fundable=min($300, raw $400+reserve $250=$650)=$300 (the cap itself
    # is tighter than what cash alone could already cover) -> harvest=$300-$300=$0: no point
    # harvesting when the cap suppresses the allocation below what cash already funds.
    ctx = _ctx_for_step3(max_portfolio_percentage=65.0)
    ctx.alpha_reserve = AlphaReserve(symbol="ALPHA", amount=250.0, lastUpdatedDate="2026-08-06")
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert allocations.get("ALPHA") == 300.0, f"combined $900 must be clamped to the $300 headroom, got {allocations.get('ALPHA')}"
    assert ctx.alpha_target_dollars == 300.0
    assert ctx.harvest_needed_dollars == 0.0, f"cap already suppresses below cash-fundable amount -> no harvest needed, got {ctx.harvest_needed_dollars}"
    print("[reserve-respects-cap] $900 desired clamped to $300 max_portfolio_percentage headroom; harvest=$0 — OK")


def test_underweight_shortfall_requests_full_gap_and_harvests() -> None:
    """UW1 mv=$100 (instead of the default $700) -> gap = 1000-100 = $900, exceeding
    remaining_for_underweight ($600) -> UW1 should get its FULL $900 gap request (not a
    proportionally-reduced pro-rata share), and the $300 shortfall should show up in
    harvest_needed_dollars."""
    ctx = _ctx_for_step3(uw1_market_value=100.0)
    ctx.buy_guarded_symbols = {"ALPHA": "profit-sold recently"}  # isolate the underweight-only harvest component
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert allocations.get("UW1") == 900.0, f"expected UW1's full $900 gap (not capped to $600), got {allocations.get('UW1')}"
    assert ctx.harvest_needed_dollars == 300.0, f"expected $300 shortfall ($900 gap - $600 available), got {ctx.harvest_needed_dollars}"
    print("[underweight-shortfall] UW1 requests full $900 gap, $300 harvest shortfall flagged — OK")


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


def _ctx_for_step4(alpha_leader: str = "ALPHA", symbols=("ALPHA", "OTHER"), **meta_overrides) -> RunContext:
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides), targets={s: AssetTarget(s, weight=1.0) for s in symbols},
        force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.alpha_leader = alpha_leader
    return ctx


def test_alpha_leader_gtp_blocked_below_threshold_but_fires_above() -> None:
    # sell_qty = 5 shares (profit_sell_percentage=50% of 10 held). _Step4Broker's tax lot has
    # cost_per_share=1.0, so FIFO realized profit = (price - 1.0) * 5.
    ctx = _ctx_for_step4()
    ctx.positions = {"ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=103.0)}  # FIFO=(103-1)*5=$510 < $600 guard
    step4_profit_taking(ctx, _Step4Broker())
    assert not ctx.profit_taking_sells, "GTP should be blocked for the Alpha Leader below minimum_alpha_leader_sell_profit"
    assert any("Alpha Leader sell guard" in s.reason for s in ctx.skipped)
    print("[alpha-gtp-blocked] ALPHA FIFO $510 (< $600 guard) -> GTP correctly blocked")

    ctx2 = _ctx_for_step4()
    ctx2.positions = {"ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0)}
    ctx2.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=250.0)}  # FIFO=(250-1)*5=$1,245 > $600 guard
    step4_profit_taking(ctx2, _Step4Broker())
    assert any(t.symbol == "ALPHA" for t in ctx2.profit_taking_sells), "GTP should fire once ALPHA clears the guard"
    print("[alpha-gtp-fires-above] ALPHA FIFO $1,245 (> $600 guard) -> GTP fires normally")


def test_non_leader_gtp_unaffected_by_alpha_guard() -> None:
    ctx = _ctx_for_step4(alpha_leader="ALPHA")
    ctx.positions = {"OTHER": Position("OTHER", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"OTHER": Quote("OTHER", last_trade_price=103.0)}  # FIFO=$510, would be blocked if it were the leader
    step4_profit_taking(ctx, _Step4Broker())
    assert any(t.symbol == "OTHER" for t in ctx.profit_taking_sells), "non-leader GTP must be unaffected by the Alpha Leader guard"
    print("[non-leader-gtp-unaffected] OTHER (not Alpha Leader) FIFO $510 -> GTP fires, guard doesn't apply")


def test_alpha_leader_mrt_blocked_below_threshold() -> None:
    ctx = _ctx_for_step4()
    ctx.positions = {"ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=101.5)}  # +1.5%: below materialize_profit_percentage(2%) so GTP never fires; FIFO=(101.5-1)*5=$502.50 < $600 guard
    ctx.momentum_scores = {"ALPHA": MomentumScore("ALPHA", rsi14=20, ema9_now=95, ema9_prior=100,
                                                   price_vs_ema_pct=-15, ema_slope_pct=-5)}  # score well below threshold -10
    step4_profit_taking(ctx, _Step4Broker())
    assert not ctx.profit_taking_sells, "MRT should be blocked for the Alpha Leader below minimum_alpha_leader_sell_profit"
    assert any("Alpha Leader sell guard" in s.reason for s in ctx.skipped)
    print("[alpha-mrt-blocked] ALPHA FIFO $502.50 (MRT gates clear, but < $600 guard) -> MRT correctly blocked")


def test_alpha_leader_overweight_trim_blocked_below_threshold() -> None:
    ctx = _ctx_for_step4()
    ctx.positions = {
        "ALPHA": Position("ALPHA", quantity=10.0, avg_cost_basis=100.0),
        "OTHER": Position("OTHER", quantity=10.0, avg_cost_basis=100.0),
    }
    # unrealized_dollars = (price - avg_cost_basis) * quantity = (102-100)*10 = $20, well under
    # the $600 guard (the Overweight-trim path estimates off the full position, not a FIFO slice).
    ctx.quotes = {"ALPHA": Quote("ALPHA", last_trade_price=102.0), "OTHER": Quote("OTHER", last_trade_price=102.0)}
    ctx.momentum_scores = {}  # keep MRT out of the picture entirely
    ctx.account_balance = 2000.0
    # target_percentage=10 (well below current weight) -> plenty of "overweight excess" room for
    # sizing to actually harvest from OTHER once it clears the ranking gates.
    ctx.drift_results = {
        "ALPHA": DriftResult("ALPHA", 60, 60, 50, 10, 10, 1, market_value=1020.0),
        "OTHER": DriftResult("OTHER", 60, 60, 50, 10, 10, 1, market_value=1020.0),
    }
    ctx.harvest_needed_dollars = 500.0  # a real shortfall so a qualifying candidate gets SIZED
    step4_profit_taking(ctx, _Step4Broker())
    trimmed = {t.symbol for t in ctx.overweight_trims}
    assert "ALPHA" not in trimmed, "Overweight trim should be blocked for the Alpha Leader below the guard"
    assert "OTHER" in trimmed, "non-leader Overweight trim must be unaffected by the Alpha Leader guard"
    print(f"[alpha-overweight-blocked] est. unrealized $20 (< $600 guard) -> ranked candidates={trimmed} — ALPHA excluded, OTHER included — OK")


def test_size_overweight_trims_harvests_top_ranked_first() -> None:
    """Two Overweight candidates, LOW-beta HIGH-margin (worse score) and HIGH-beta HIGH-margin
    (better score). harvest_needed_dollars is small enough that only the top-ranked candidate
    should get sized; the other should be skipped as "no harvest shortfall remains"."""
    ctx = _ctx_for_step4(alpha_leader=None, symbols=("LOWSCORE", "HISCORE"), materialize_profit_percentage=1000.0)
    ctx.positions = {
        "LOWSCORE": Position("LOWSCORE", quantity=100.0, avg_cost_basis=50.0),
        "HISCORE": Position("HISCORE", quantity=100.0, avg_cost_basis=50.0),
    }
    ctx.quotes = {"LOWSCORE": Quote("LOWSCORE", last_trade_price=60.0), "HISCORE": Quote("HISCORE", last_trade_price=60.0)}
    ctx.momentum_scores = {}
    ctx.account_balance = 20000.0
    ctx.drift_results = {
        "LOWSCORE": DriftResult("LOWSCORE", 30, 30, 20, 10, 10, 1, market_value=6000.0),
        "HISCORE": DriftResult("HISCORE", 30, 30, 20, 10, 10, 1, market_value=6000.0),
    }
    ctx.harvest_needed_dollars = 300.0  # small -> should be fully covered by ONE candidate

    class _BetaAwareBroker(_Step4Broker):
        def get_daily_closes(self, symbol, start, end):
            # HISCORE tracks the benchmark's own oscillation pattern at 2x amplitude -> beta≈2.0
            # (LOWSCORE, unmodified, IS the benchmark series -> beta≈1.0) -> higher High-Beta
            # score -> ranked first. (Verified numerically — an unrelated/uncorrelated series,
            # e.g. a smooth linear ramp, actually yields beta≈0 against an oscillating
            # benchmark, the opposite of "high beta": beta measures correlated co-movement, not
            # magnitude of movement.)
            if symbol == "HISCORE":
                return [100.0 + (i % 5) * 0.6 for i in range(60)]
            return super().get_daily_closes(symbol, start, end)

    step4_profit_taking(ctx, _BetaAwareBroker())
    trimmed = {t.symbol: t for t in ctx.overweight_trims}
    assert "HISCORE" in trimmed, f"the higher-scored candidate should be trimmed first, got {trimmed.keys()}"
    assert "LOWSCORE" not in trimmed, "the shortfall should already be covered by the top-ranked candidate alone"
    harvested = trimmed["HISCORE"].quantity * 60.0
    assert harvested >= 300.0, f"expected at least the $300 shortfall harvested, got ${harvested:.2f}"
    print(f"[size-overweight-top-ranked] HISCORE harvested ${harvested:.2f} (>= $300 shortfall), LOWSCORE untouched — OK")


def test_size_overweight_trims_walks_down_ranking_for_large_shortfall() -> None:
    """A shortfall larger than the top-ranked candidate's own overweight excess should spill
    over into the next-ranked candidate too."""
    ctx = _ctx_for_step4(alpha_leader=None, symbols=("A", "B"), materialize_profit_percentage=1000.0)
    ctx.positions = {
        "A": Position("A", quantity=100.0, avg_cost_basis=50.0),
        "B": Position("B", quantity=100.0, avg_cost_basis=50.0),
    }
    ctx.quotes = {"A": Quote("A", last_trade_price=60.0), "B": Quote("B", last_trade_price=60.0)}
    ctx.momentum_scores = {}
    ctx.account_balance = 20000.0
    # Both capped at a modest $500 overweight excess each (target_mv=5500, market_value=6000).
    ctx.drift_results = {
        "A": DriftResult("A", 30, 30, 27.5, 27.5, 2.5, 1, market_value=6000.0),
        "B": DriftResult("B", 30, 30, 27.5, 27.5, 2.5, 1, market_value=6000.0),
    }
    ctx.harvest_needed_dollars = 900.0  # exceeds any single candidate's $500 excess
    step4_profit_taking(ctx, _Step4Broker())  # identical closes -> same beta/score -> both rank, order stable
    trimmed = {t.symbol: t for t in ctx.overweight_trims}
    assert len(trimmed) == 2, f"expected both candidates to contribute to the shortfall, got {trimmed.keys()}"
    total_harvested = sum(t.quantity * 60.0 for t in trimmed.values())
    assert total_harvested >= 900.0, f"expected at least $900 harvested across both, got ${total_harvested:.2f}"
    print(f"[size-overweight-walks-down] both A and B trimmed, ${total_harvested:.2f} total harvested (>= $900) — OK")


def main() -> None:
    test_guarded_leader_holds_cash_aside_not_redirected()
    test_eligible_leader_merges_matching_reserve()
    test_eligible_leader_ignores_stale_reserve_for_other_symbol()
    test_reserve_merge_respects_portfolio_cap()
    test_underweight_shortfall_requests_full_gap_and_harvests()
    test_resolve_alpha_reserve_clears_when_bought()
    test_resolve_alpha_reserve_refreshes_when_not_bought()
    test_resolve_alpha_reserve_leader_change_overwrites_not_accumulates()
    test_resolve_alpha_reserve_untouched_when_no_leader()
    test_alpha_leader_gtp_blocked_below_threshold_but_fires_above()
    test_non_leader_gtp_unaffected_by_alpha_guard()
    test_alpha_leader_mrt_blocked_below_threshold()
    test_alpha_leader_overweight_trim_blocked_below_threshold()
    test_size_overweight_trims_harvests_top_ranked_first()
    test_size_overweight_trims_walks_down_ranking_for_large_shortfall()
    print("\nSMOKE TEST (Alpha Reserve + minimum_alpha_leader_sell_profit) PASSED")


if __name__ == "__main__":
    main()
