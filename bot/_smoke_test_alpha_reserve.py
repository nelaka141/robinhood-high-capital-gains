"""Focused unit-style coverage for two related Alpha Leader controls:

1. The Alpha Leader buy-guard cascade + Alpha Leader Reserve (steps.step3_alpha_leader's
   ranking/cascade logic + steps.resolve_alpha_leader_reserve) — CLAUDE.md Step 3: when the Top
   Momentum Symbol is buy-guarded, walk down the ranking (while score >=
   alpha_leader_least_momentum_score) for the first non-buy-guarded fallback; that fallback's
   buy draws from (and shrinks) the reserve that was sized for the Top Momentum Symbol. If
   nobody qualifies, the full reserve stays aside, recalculated fresh every cycle.
2. `minimum_alpha_leader_sell_profit` — an extra profit-margin floor that applies ONLY when the
   sell candidate is the current (acting) Alpha Leader, on top of each mechanism's own gate (GET
   THE PROFITS, Momentum Reversal Trim, Overweight trim).

Pure logic tests against RunContext/steps functions directly, no snapshot/CLI plumbing needed
(same style as bot/_smoke_test_min_trade_value.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_alpha_reserve.py
"""
from __future__ import annotations

import math
import statistics
from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import DriftResult, MomentumScore, Position, Quote, RunContext, TaxLot, TradeIntent
from bot.steps import resolve_alpha_leader_reserve, step2_guardrails, step3_alpha_leader, step4_profit_taking


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.25,
        max_portfolio_percentage=90.0, alpha_cash_allocation_percentage=40.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=0.0,
        momentum_reversal_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_dollars=0.0,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
        minimum_alpha_leader_sell_profit=600.0,  # a DOLLAR floor, not a percentage
        alpha_leader_least_momentum_score=10.0,
        alpha_rank_reduction_percent=0.0,  # no rank haircut by default; overridden in rank tests
        min_momentum_score_to_fill_underweight=-1000.0,  # permissive by default; overridden in floor tests
        alpha_leader_fresh_position_days=3,
        alpha_leader_fresh_drawdown_percentage=15.0,
        max_sector_percentage=0.0,  # disabled by default; overridden in sector-cap tests
        wash_sale_lookback_days=0,  # permissive by default; overridden in wash-sale tests
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx_for_step3(mv=None, **meta_overrides) -> RunContext:
    """TOP (highest momentum) mv=$1000, MID (fallback candidate) mv=$500, UW1 (underweight)
    mv=$700 by default, all against a $2000 account_balance. current_cash=$1000, no tax drag ->
    base_deployable_cash=$1000, alpha_cash_allocation_percentage=40% -> raw_alpha_target=$400,
    multiplier_cash=$1000*(1.25-1)=$250 -> alpha_leader_reserve_target=min($650, headroom(TOP)).
    UW1's gap = 1000-700 = $300 <= remaining_for_underweight ($600) by default -> UW1 gets the
    full $600 pool (pro-rata, single underweight symbol -> 100% of it), no harvest needed from
    that side. Pass `mv` to override any symbol's market_value (e.g. to squeeze headroom)."""
    mv = dict(mv or {})
    mv.setdefault("TOP", 1000.0)
    mv.setdefault("MID", 500.0)
    mv.setdefault("UW1", 700.0)

    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides),
        targets={s: AssetTarget(s, weight=1.0) for s in mv},
        force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.current_cash = 1000.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 2000.0
    ctx.quotes = {s: Quote(s, last_trade_price=100.0) for s in mv}
    # ctx.momentum_scores is NOT preset here — step3_alpha_leader always recomputes it fresh from
    # broker.get_daily_closes (see _Step3Broker below), whose engineered closes are what actually
    # determines the ranking (TOP score ~55 > MID score ~15 > UW1 score ~-32, empirically verified
    # against bot/indicators.py's real RSI(14)/EMA(9) math — see _Step3Broker's docstring for why
    # flat or purely-monotonic closes don't work here).
    ctx.drift_results = {
        "TOP": DriftResult("TOP", 50, 50, 50, 50, 0, 1, market_value=mv["TOP"]),
        "MID": DriftResult("MID", 25, 25, 25, 25, 0, 1, market_value=mv["MID"]),
        "UW1": DriftResult("UW1", 35, 35, 50, 50, 15, 1, market_value=mv["UW1"]),
    }
    return ctx


def _series(drift: float, amp: float = 1.0, n: int = 60) -> list:
    """A gently oscillating (not flat, not purely monotonic) 60-day close series with the given
    per-day drift. Flat or purely-monotonic-up closes both make Wilder's RSI degenerate to a
    fixed 100 (avg_loss stays exactly 0, since there's never a down day) — real market data
    always has some down days, so the drift alone doesn't cleanly separate scores without this.
    Empirically calibrated: drift=0.6 -> Momentum_Score ~55, drift=0.0 -> ~15, drift=-0.2 -> ~-32."""
    return [100.0 + drift * i + amp * math.sin(i / 3.0) for i in range(n)]


class _Step3Broker:
    """step3_alpha_leader recomputes Momentum_Score itself from get_daily_closes — TOP/MID/UW1
    each get a distinctly-drifting series (see _series) so the real RSI(14)/EMA(9) math produces
    a reliable TOP > MID > UW1 ranking, with MID's score (~15) deliberately sitting between the
    default alpha_leader_least_momentum_score (10) and the stricter override used in
    test_cascade_stops_at_least_momentum_score_floor (20) below."""

    def get_daily_closes(self, symbol, start, end):
        if symbol == "TOP":
            return _series(drift=0.6)
        if symbol == "MID":
            return _series(drift=0.0)
        return _series(drift=-0.2)  # UW1


def test_top_momentum_not_guarded_becomes_leader() -> None:
    """The common case: TOP isn't buy-guarded, so the cascade ends immediately on it."""
    ctx = _ctx_for_step3()
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.top_momentum_symbol == "TOP"
    assert ctx.alpha_leader == "TOP", f"expected TOP to win outright, got {ctx.alpha_leader}"
    assert allocations.get("TOP") == ctx.alpha_leader_reserve_target
    print(f"[top-not-guarded] TOP wins outright, allocation=${allocations['TOP']:.2f} "
          f"== alpha_leader_reserve_target — OK")


def test_buy_timing_guard_does_not_block_alpha_leader() -> None:
    """TOP is on a strong, steady upward drift (see _series/_Step3Broker) — it never shows the
    three-leg dip-then-turn pattern, so the real step2_guardrails correctly buy-guards it. But
    the buy-timing guard must NOT gate the Alpha Leader (see steps.py step2_guardrails v2.72.0):
    TOP should land in buy_guarded_symbols (blocking it from an Underweight buy or a same-symbol
    repurchase) while staying OUT of alpha_buy_guarded_symbols, so the cascade still picks it."""
    ctx = _ctx_for_step3()
    ctx.price_state = {}  # nobody has a recorded profit-sell or liquidation
    step2_guardrails(ctx, _Step3Broker())
    assert "TOP" in ctx.buy_guarded_symbols, (
        f"TOP's steadily-rising series should fail the buy-timing pattern, got {ctx.buy_guarded_symbols}"
    )
    assert "TOP" not in ctx.alpha_buy_guarded_symbols, (
        f"buy-timing guard must not populate alpha_buy_guarded_symbols, got {ctx.alpha_buy_guarded_symbols}"
    )
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader == "TOP", f"TOP must still win Alpha Leader despite failing buy-timing, got {ctx.alpha_leader}"
    assert allocations.get("TOP") == ctx.alpha_leader_reserve_target
    print("[buy-timing-exempts-alpha] TOP fails the universal buy-timing guard "
          "(buy_guarded=True) but still becomes Alpha Leader (alpha_guarded=False) — OK")


def test_guarded_top_falls_back_to_next_candidate() -> None:
    """TOP is buy-guarded -> MID (next in ranking, score 16 >= floor 10) becomes the acting
    Alpha Leader instead, drawing from (not adding to) the reserve sized for TOP."""
    ctx = _ctx_for_step3()
    ctx.alpha_buy_guarded_symbols = {"TOP": ["profit-sold recently"]}
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.top_momentum_symbol == "TOP"
    assert ctx.alpha_leader == "MID", f"expected MID to act as fallback leader, got {ctx.alpha_leader}"
    assert ctx.alpha_leader_reserve_target == 650.0, (
        f"expected raw $400 + multiplier $250 = $650 (TOP's headroom of $800 doesn't bind), "
        f"got {ctx.alpha_leader_reserve_target}"
    )
    assert allocations.get("MID") == 650.0, f"MID's own headroom ($1300) doesn't bind either -> full $650, got {allocations.get('MID')}"
    print(f"[guarded-falls-back] TOP guarded -> MID acts as leader, allocation=${allocations['MID']:.2f} "
          f"(reserve target ${ctx.alpha_leader_reserve_target:.2f}) — OK")


def test_fallback_rank_reduction_applies_haircut() -> None:
    """MID is rank 2 in the momentum ranking (TOP=1, MID=2, UW1=3). With
    alpha_rank_reduction_percent=10, MID's fully-capped $650 allocation should be scaled by
    Rank_Multiplier = 1 - (2-1)*0.10 = 0.9 -> $585. The reserve TARGET itself (TOP's own
    would-be allocation) stays unreduced -> more of the $650 reserve survives than before."""
    ctx = _ctx_for_step3(alpha_rank_reduction_percent=10.0)
    ctx.alpha_buy_guarded_symbols = {"TOP": ["profit-sold recently"]}
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader == "MID"
    assert ctx.alpha_leader_reserve_target == 650.0, "reserve target itself (TOP's own would-be allocation) is unreduced"
    assert math.isclose(allocations.get("MID"), 585.0), f"expected $650 * 0.9 (rank 2 haircut) = $585, got {allocations.get('MID')}"
    print(f"[fallback-rank-reduced] MID is rank 2 -> allocation ${allocations['MID']:.2f} == $650 * 0.9 — OK")


def test_top_momentum_unaffected_by_rank_reduction() -> None:
    """TOP itself (rank 1) must never be reduced, no matter how large alpha_rank_reduction_percent is."""
    ctx = _ctx_for_step3(alpha_rank_reduction_percent=50.0)
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader == "TOP"
    assert allocations.get("TOP") == ctx.alpha_leader_reserve_target == 650.0, (
        f"rank 1 must be unreduced regardless of alpha_rank_reduction_percent, got {allocations.get('TOP')}"
    )
    print(f"[rank1-unreduced] TOP (rank 1) allocation ${allocations['TOP']:.2f} == full reserve target, "
          f"unaffected by 50% alpha_rank_reduction_percent — OK")


def test_fallback_rank_reduction_floors_at_zero() -> None:
    """alpha_rank_reduction_percent > 100 can drive Rank_Multiplier negative for a rank-2
    fallback -> the allocation must floor at $0.00, never go negative."""
    ctx = _ctx_for_step3(alpha_rank_reduction_percent=150.0)  # rank 2 -> 1-(2-1)*1.5 = -0.5 -> floored to 0
    ctx.alpha_buy_guarded_symbols = {"TOP": ["profit-sold recently"]}
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader == "MID"
    assert allocations.get("MID") == 0.0, f"expected $0 (floored), got {allocations.get('MID')}"
    print("[fallback-rank-reduction-floor] 150%/rank reduction at rank 2 -> allocation floors at $0.00 — OK")


def test_alpha_leader_excluded_from_underweight_pool() -> None:
    """MID (the fallback Alpha Leader here) is ALSO Underweight & breached. It must NOT
    additionally receive an Underweight-gap allocation on top of its $650 Alpha allocation —
    that would double-fund the same symbol from two different pots. UW1 (the only OTHER
    Underweight candidate) should still get its normal share of what's left."""
    ctx = _ctx_for_step3()
    ctx.alpha_buy_guarded_symbols = {"TOP": ["profit-sold recently"]}
    # Make MID itself Underweight & breached (it wasn't, by default) so it would ordinarily also
    # compete for the Underweight cash pool: target_weight 60 vs actual_weight 25, mv unchanged.
    ctx.drift_results["MID"] = DriftResult("MID", 25, 25, 60, 60, 35, 1, market_value=500.0)
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader == "MID"
    assert allocations.get("MID") == 650.0, (
        f"MID's allocation must be exactly its $650 Alpha allocation, no added Underweight gap, "
        f"got {allocations.get('MID')}"
    )
    # remaining_for_underweight = base_deployable_cash $1000 - alpha_leader_reserve_target $650
    # = $350; UW1 is the only remaining Underweight candidate (gap $300 <= $350 available) -> it
    # gets the full $350 pool (over-deploy rule), same as if MID had never been Underweight at all.
    assert allocations.get("UW1") == 350.0, f"expected UW1 to get the full $350 pool alone, got {allocations.get('UW1')}"
    print(f"[alpha-leader-excluded-from-underweight] MID (Alpha Leader + Underweight) allocation "
          f"stays at ${allocations['MID']:.2f} (no double-dip); UW1 alone gets ${allocations['UW1']:.2f} — OK")


def test_fallback_capped_by_own_headroom_leaves_reserve_partially_spent() -> None:
    """MID is already near its own max_portfolio_percentage cap -> it can only draw PART of the
    reserve sized for TOP; the rest stays reserved (checked via resolve_alpha_leader_reserve in
    a separate test below, once ctx.buys reflects what actually got bought)."""
    ctx = _ctx_for_step3(mv={"MID": 1700.0})  # headroom(MID) = 0.9*2000 - 1700 = $100
    ctx.alpha_buy_guarded_symbols = {"TOP": ["profit-sold recently"]}
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader == "MID"
    assert ctx.alpha_leader_reserve_target == 650.0, "TOP's own headroom (unaffected by MID's mv) still $800, doesn't bind"
    assert allocations.get("MID") == 100.0, f"MID's own $100 headroom caps it well below the $650 reserve, got {allocations.get('MID')}"
    print(f"[fallback-headroom-capped] MID only draws ${allocations['MID']:.2f} of the "
          f"${ctx.alpha_leader_reserve_target:.2f} reserve (own headroom binds) — OK")


def test_cascade_stops_at_least_momentum_score_floor() -> None:
    """TOP guarded, and MID's score is now BELOW alpha_leader_least_momentum_score -> the
    cascade must NOT fall back to MID (or anyone else) -> no Alpha Leader this cycle."""
    ctx = _ctx_for_step3(alpha_leader_least_momentum_score=20.0)  # MID's score (16) < 20
    ctx.alpha_buy_guarded_symbols = {"TOP": ["profit-sold recently"]}
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader is None, f"MID's score is below the floor -> no fallback allowed, got {ctx.alpha_leader}"
    assert "MID" not in allocations and "TOP" not in allocations
    assert ctx.alpha_leader_reserve_target == 650.0, "reserve target is still computed fresh even with no acting leader"
    print(f"[floor-stops-cascade] MID's score below alpha_leader_least_momentum_score -> "
          f"no Alpha Leader, ${ctx.alpha_leader_reserve_target:.2f} stays fully reserved — OK")


def test_underweight_shortfall_requests_full_gap_and_harvests() -> None:
    """UW1 mv=$100 (instead of the default $700) -> gap = 1000-100 = $900, exceeding
    remaining_for_underweight (base_deployable_cash $1000 - alpha_leader_reserve_target $650 =
    $350 — the FULL reserve target is carved out now, not just the $400 raw Alpha target, so
    less is "free" for Underweight even though no Alpha Leader actually buys this cycle) -> UW1
    should get its FULL $900 gap request (not a proportionally-reduced pro-rata share), and the
    $550 shortfall should show up in harvest_needed_dollars. Isolate this from the alpha side by
    guarding TOP AND setting the floor above MID's score, so no Alpha Leader buy competes for
    harvest budget."""
    ctx = _ctx_for_step3(mv={"UW1": 100.0}, alpha_leader_least_momentum_score=20.0)
    ctx.alpha_buy_guarded_symbols = {"TOP": ["profit-sold recently"]}
    allocations = step3_alpha_leader(ctx, _Step3Broker())
    assert ctx.alpha_leader is None
    assert allocations.get("UW1") == 900.0, f"expected UW1's full $900 gap (not capped to $350), got {allocations.get('UW1')}"
    assert ctx.harvest_needed_dollars == 550.0, f"expected $550 shortfall ($900 gap - $350 available), got {ctx.harvest_needed_dollars}"
    print("[underweight-shortfall] UW1 requests full $900 gap, $550 harvest shortfall flagged — OK")


def _underweight_series(drift: float) -> list:
    return _series(drift=drift)


class _UnderweightBroker:
    """Per-symbol close series keyed by drift, so step3_alpha_leader's real RSI(14)/EMA(9) math
    produces a controlled, verifiable Momentum_Score per symbol (quotes fixed at $100 in the ctx
    below, so score depends only on the series, not on a separate live price)."""
    def __init__(self, drifts: dict):
        self._drifts = drifts

    def get_daily_closes(self, symbol, start, end):
        return _underweight_series(self._drifts[symbol])


def _ctx_for_underweight_split(symbols: list, weights: dict = None, **meta_overrides) -> tuple:
    """No Alpha Leader competes for the pool (alpha_cash_allocation_percentage=0 and
    reinvestment_multiplier_factor=1.0 -> alpha_leader_reserve_target=0 regardless of who ranks
    top), so remaining_for_underweight = base_deployable_cash exactly ($1000). Each symbol gets a
    small, equal drift gap ($100, well under the $1000 pool) so total_gap never exceeds
    remaining_for_underweight -> always the pro-rata/abundant branch, pool = $1000."""
    # alpha_leader_least_momentum_score set impossibly high so NO symbol here can ever become the
    # acting Alpha Leader (which would exclude it from the Underweight pool via the "no
    # double-dip" rule) -> every symbol in `symbols` competes purely as an Underweight candidate.
    meta_defaults = dict(min_momentum_score_to_fill_underweight=-1000.0, alpha_leader_least_momentum_score=9999.0)
    meta_defaults.update(meta_overrides)
    weights = weights or {s: 1.0 for s in symbols}
    cfg = PortfolioConfig(
        meta=_meta(
            alpha_cash_allocation_percentage=0.0, reinvestment_multiplier_factor=1.0,
            max_portfolio_percentage=90.0, **meta_defaults,
        ),
        targets={s: AssetTarget(s, weight=weights[s]) for s in symbols},
        force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.current_cash = 1000.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 10000.0
    ctx.quotes = {s: Quote(s, last_trade_price=100.0) for s in symbols}
    ctx.drift_results = {
        s: DriftResult(s, current_percentage=0, actual_weight=0, target_weight=1.0,
                        target_percentage=1.0, drift=1.0, asset_drift_tolerance=0.1, market_value=0.0)
        for s in symbols
    }
    return ctx, cfg


def _reference_momentum_split(scores: dict, weights: dict, pool: float) -> dict:
    """Independent reimplementation of CLAUDE.md's "Underweight allocation" formula, used to
    verify step3_alpha_leader's actual output rather than hardcoding brittle float literals."""
    min_score = min(scores.values())
    normalized = {s: scores[s] - min_score for s in scores}
    if len(scores) >= 2 and len(set(normalized.values())) > 1:
        sd = statistics.stdev(normalized.values())
        w = {s: normalized[s] / sd for s in scores}
    else:
        w = {s: 1.0 for s in scores}
    total_w = sum(w.values())
    weight_field_sum = sum(weights.values())
    result = {}
    for s in scores:
        share = pool * w[s] / total_w
        if scores[s] < 0 and weight_field_sum > 0:
            cap = pool * weights[s] / weight_field_sum
            share = min(share, cap)
        result[s] = share
    return result


def test_underweight_floor_excludes_low_momentum_and_zeros_the_minimum() -> None:
    """5-candidate scenario mirroring the user's AMT/HOOD/FCX/UNH/V example: V's Momentum_Score
    falls below min_momentum_score_to_fill_underweight and must be fully excluded (no allocation,
    doesn't compete at all); UNH is the lowest-scoring QUALIFYING candidate, normalizes to 0, and
    gets exactly $0 from the score-weighted split."""
    symbols = ["AMT", "HOOD", "FCX", "UNH", "V"]
    drifts = {"AMT": 0.01, "HOOD": 0.0, "FCX": -0.03, "UNH": -0.1, "V": -0.12}
    ctx, cfg = _ctx_for_underweight_split(symbols, min_momentum_score_to_fill_underweight=-5.0)
    allocations = step3_alpha_leader(ctx, _UnderweightBroker(drifts))

    assert ctx.momentum_scores["V"].score < -5.0, "fixture assumption: V's score must actually fail the floor"
    assert "V" not in allocations, f"V's score is below the floor -> must be fully excluded, got {allocations.get('V')}"
    assert any(s.symbol == "V" and "min_momentum_score_to_fill_underweight" in s.reason for s in ctx.skipped), \
        "V's exclusion should be logged with the floor as the reason"

    qualifying = [s for s in symbols if s != "V"]
    scores = {s: ctx.momentum_scores[s].score for s in qualifying}
    weights = {s: cfg.targets[s].weight for s in qualifying}
    expected = _reference_momentum_split(scores, weights, 1000.0)
    for s in qualifying:
        assert math.isclose(allocations.get(s, 0.0), expected[s], abs_tol=0.01), (
            f"{s}: expected ${expected[s]:.2f} (reference formula), got ${allocations.get(s, 0.0):.2f}"
        )
    assert math.isclose(allocations["UNH"], 0.0, abs_tol=0.01), \
        f"UNH (lowest qualifying score) should normalize to 0 and get ~$0, got ${allocations['UNH']:.2f}"
    assert allocations["AMT"] > allocations["HOOD"] > allocations["FCX"] > allocations["UNH"], \
        "allocation ordering should follow the momentum ranking"
    print(f"[underweight-floor] V excluded (score {ctx.momentum_scores['V'].score:.2f} < -5.0); "
          f"AMT=${allocations['AMT']:.2f} HOOD=${allocations['HOOD']:.2f} "
          f"FCX=${allocations['FCX']:.2f} UNH=${allocations['UNH']:.2f} (all match reference formula) — OK")


def test_underweight_negative_momentum_cap_binds() -> None:
    """B's raw Momentum_Score is negative but B is NOT the minimum (C scores lower), so B's
    score-weighted share alone would be meaningfully positive. Giving B a deliberately tiny
    portfolio_targets.json `weight` (0.05 vs A/C's 1.0) makes the weight-proportional cap bind
    below B's score-weighted share -> B's actual allocation must be the SMALLER, capped figure,
    and the capped-away dollars must NOT be redistributed to A or C (sum < pool)."""
    symbols = ["A", "B", "C"]
    drifts = {"A": 0.2, "B": -0.1, "C": -0.15}
    weights = {"A": 1.0, "B": 0.05, "C": 1.0}
    ctx, cfg = _ctx_for_underweight_split(symbols, weights, min_momentum_score_to_fill_underweight=-20.0)
    allocations = step3_alpha_leader(ctx, _UnderweightBroker(drifts))

    assert ctx.momentum_scores["B"].score < 0, "fixture assumption: B's raw score must be negative"
    assert ctx.momentum_scores["C"].score < ctx.momentum_scores["B"].score, \
        "fixture assumption: C must score lower than B so B is not the normalized minimum"

    scores = {s: ctx.momentum_scores[s].score for s in symbols}
    uncapped = _reference_momentum_split(scores, {s: 1.0 for s in symbols}, 1000.0)  # weights all equal -> no cap
    capped = _reference_momentum_split(scores, weights, 1000.0)

    assert uncapped["B"] > capped["B"], (
        f"sanity check: B's uncapped share (${uncapped['B']:.2f}) must exceed its capped share "
        f"(${capped['B']:.2f}) for this to be a meaningful test of the cap"
    )
    assert math.isclose(allocations["B"], capped["B"], abs_tol=0.01), (
        f"B's negative raw score should cap it at its tiny weight-field's pro-rata share "
        f"(${capped['B']:.2f}), got ${allocations['B']:.2f} (uncapped would be ${uncapped['B']:.2f})"
    )
    total_allocated = sum(allocations.get(s, 0.0) for s in symbols)
    assert total_allocated < 1000.0 - 1.0, (
        f"capped-away dollars must NOT be redistributed to A/C -> total allocated (${total_allocated:.2f}) "
        f"should be meaningfully less than the $1000 pool"
    )
    print(f"[underweight-negative-cap] B capped at ${allocations['B']:.2f} (uncapped would've been "
          f"${uncapped['B']:.2f}); total allocated ${total_allocated:.2f} < $1000 pool, no re-allocation — OK")


def test_resolve_reserve_shrinks_to_zero_when_fully_bought() -> None:
    ctx = RunContext(current_date=date(2026, 8, 7), config=None, account_number="TEST")
    ctx.top_momentum_symbol = "TOP"
    ctx.alpha_leader = "MID"
    ctx.alpha_leader_reserve_target = 650.0
    ctx.buys = [TradeIntent(symbol="MID", side="buy", dollar_amount=650.0)]
    result = resolve_alpha_leader_reserve(ctx)
    assert result.top_momentum_symbol == "TOP" and result.alpha_leader_symbol == "MID"
    assert result.reserve_cash == 0.0, f"fully spent -> reserve should be $0, got {result.reserve_cash}"
    print("[resolve-fully-bought] MID spent the full $650 reserve -> reserve_cash=$0 — OK")


def test_resolve_reserve_shrinks_partially_when_partially_bought() -> None:
    """Mirrors a real cycle: step3 planned $650 for the fallback, but Step 5/6 (price-limit
    halt, hard-cap scale, or min_value_of_trade) only actually placed $100 of it."""
    ctx = RunContext(current_date=date(2026, 8, 7), config=None, account_number="TEST")
    ctx.top_momentum_symbol = "TOP"
    ctx.alpha_leader = "MID"
    ctx.alpha_leader_reserve_target = 650.0
    ctx.buys = [TradeIntent(symbol="MID", side="buy", dollar_amount=100.0)]
    result = resolve_alpha_leader_reserve(ctx)
    assert result.reserve_cash == 550.0, f"expected $650 - $100 = $550 still reserved, got {result.reserve_cash}"
    print("[resolve-partially-bought] MID only actually spent $100 of $650 -> reserve_cash=$550 — OK")


def test_resolve_reserve_stays_full_when_nobody_bought() -> None:
    ctx = RunContext(current_date=date(2026, 8, 7), config=None, account_number="TEST")
    ctx.top_momentum_symbol = "TOP"
    ctx.alpha_leader = None  # nobody cleared the cascade
    ctx.alpha_leader_reserve_target = 650.0
    ctx.buys = []
    result = resolve_alpha_leader_reserve(ctx)
    assert result.alpha_leader_symbol is None
    assert result.reserve_cash == 650.0
    print("[resolve-nobody-bought] no Alpha Leader this cycle -> full $650 stays reserved — OK")


def test_resolve_reserve_none_when_no_top_momentum_symbol() -> None:
    ctx = RunContext(current_date=date(2026, 8, 7), config=None, account_number="TEST")
    ctx.top_momentum_symbol = None
    result = resolve_alpha_leader_reserve(ctx)
    assert result is None, "no in-play symbols at all -> caller should leave alpha_reserve.json untouched"
    print("[resolve-no-top-symbol] Step 3 had nothing to rank -> resolve returns None (file untouched) — OK")


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
    # materialize_profit_in_dollars raised alongside the base materialize_profit_percentage=2.0
    # so GET THE PROFITS (now OR'd, not AND'd, v2.63.0) doesn't fire and pull ALPHA/OTHER out of
    # the Overweight-trim candidate pool this test is actually exercising.
    ctx = _ctx_for_step4(materialize_profit_in_dollars=1e9)
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
    # materialize_profit_in_dollars raised too — under OR semantics (v2.63.0) a sky-high
    # materialize_profit_percentage alone no longer suppresses GET THE PROFITS, since the dollar
    # gate could still pass on its own.
    ctx = _ctx_for_step4(alpha_leader=None, symbols=("LOWSCORE", "HISCORE"),
                          materialize_profit_percentage=1000.0, materialize_profit_in_dollars=1e9)
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
    # materialize_profit_in_dollars raised too — see the OR-semantics note above.
    ctx = _ctx_for_step4(alpha_leader=None, symbols=("A", "B"),
                          materialize_profit_percentage=1000.0, materialize_profit_in_dollars=1e9)
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
    test_top_momentum_not_guarded_becomes_leader()
    test_buy_timing_guard_does_not_block_alpha_leader()
    test_guarded_top_falls_back_to_next_candidate()
    test_fallback_rank_reduction_applies_haircut()
    test_top_momentum_unaffected_by_rank_reduction()
    test_fallback_rank_reduction_floors_at_zero()
    test_alpha_leader_excluded_from_underweight_pool()
    test_fallback_capped_by_own_headroom_leaves_reserve_partially_spent()
    test_cascade_stops_at_least_momentum_score_floor()
    test_underweight_shortfall_requests_full_gap_and_harvests()
    test_underweight_floor_excludes_low_momentum_and_zeros_the_minimum()
    test_underweight_negative_momentum_cap_binds()
    test_resolve_reserve_shrinks_to_zero_when_fully_bought()
    test_resolve_reserve_shrinks_partially_when_partially_bought()
    test_resolve_reserve_stays_full_when_nobody_bought()
    test_resolve_reserve_none_when_no_top_momentum_symbol()
    test_alpha_leader_gtp_blocked_below_threshold_but_fires_above()
    test_non_leader_gtp_unaffected_by_alpha_guard()
    test_alpha_leader_mrt_blocked_below_threshold()
    test_alpha_leader_overweight_trim_blocked_below_threshold()
    test_size_overweight_trims_harvests_top_ranked_first()
    test_size_overweight_trims_walks_down_ranking_for_large_shortfall()
    print("\nSMOKE TEST (Alpha Leader cascade/reserve + minimum_alpha_leader_sell_profit) PASSED")


if __name__ == "__main__":
    main()
