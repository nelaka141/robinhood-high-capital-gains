"""Focused coverage for `max_allocation_percent` — the per-asset override of `max_portfolio_percentage`
(CLAUDE.md Core Parameters, `max_portfolio_percentage`). `_headroom()` in step3_alpha_leader uses
`cfg.max_allocation_percentage(symbol)` (asset's own override if set in portfolio_targets.json,
else the global default) to cap BOTH the Alpha Leader allocation and every Underweight
candidate's momentum-weighted allocation, so a symbol's market value (existing holdings + this
cycle's planned buy) never exceeds this cap — even when it's the sole/dominant qualifier for an
otherwise much larger leftover cash pool (the scenario that motivated this parameter: a lone
Underweight candidate absorbing the ENTIRE `remaining_for_underweight` pool with no per-asset
brake, only caught afterwards by the separate, coarser `max_sector_percentage` group cap).

Pure logic tests against RunContext/steps functions directly (same style as
bot/_smoke_test_sector_cap.py). Test symbols share an IDENTICAL close-price series so every
Momentum_Score ties -> _momentum_weighted_split's tie-fallback (equal split) applies, giving
easy-to-verify dollar amounts without needing to calibrate distinct scores.

Run: PYTHONPATH=. python3 bot/_smoke_test_max_allocation.py
"""
from __future__ import annotations

import math
from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import DriftResult, Quote, RunContext
from bot.steps import step3_alpha_leader


def _flat_series(n: int = 60) -> list:
    return [100.0 + math.sin(i / 3.0) for i in range(n)]


class _TiedBroker:
    """Every symbol gets the IDENTICAL series -> identical Momentum_Score for all of them."""
    def get_daily_closes(self, symbol, start, end):
        return _flat_series()


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.0,
        max_portfolio_percentage=20.0, alpha_cash_allocation_percentage=0.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=1_000_000,
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
        minimum_alpha_leader_sell_profit=0.0,
        alpha_leader_least_momentum_score=9999.0,  # nobody becomes Alpha Leader -> pure Underweight test
        alpha_rank_reduction_percent=0.0, min_momentum_score_to_fill_underweight=-1000.0,
        alpha_leader_fresh_position_days=3, alpha_leader_fresh_drawdown_percentage=15.0,
        max_sector_percentage=100.0,  # loose -> isolates the per-asset cap from the sector cap
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx(targets: dict, market_values: dict = None, target_pct: float = 1.0, **meta_overrides) -> RunContext:
    """current_cash=$9000, no tax reserve, no alpha allocation (alpha_cash_allocation_percentage=0,
    reinvestment_multiplier_factor=1.0) -> remaining_for_underweight = $9000 exactly, split evenly
    across every tied-score candidate before any per-asset cap is applied.

    `targets` maps symbol -> AssetTarget (so callers can set max_allocation_percent per symbol).
    `target_pct` (default 1.0, i.e. a $100 drift-math target on the $10,000 account_balance) only
    needs to be raised when a test also sets a non-trivial `market_values` entry — the momentum
    pool only funds a candidate whose drift-math `_gap` (target $ minus market_value) is still
    positive; it's independent of, and not to be confused with, the max_allocation_percent/
    max_portfolio_percentage headroom cap under test here."""
    market_values = market_values or {}
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides), targets=targets,
        force_sell={}, blocked=[], sector_groups={},
    )
    ctx = RunContext(current_date=date(2026, 8, 13), config=cfg, account_number="TEST")
    ctx.current_cash = 9000.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 10000.0
    ctx.quotes = {s: Quote(s, last_trade_price=100.0) for s in targets}
    ctx.drift_results = {
        s: DriftResult(s, current_percentage=0, actual_weight=0, target_weight=1.0,
                        target_percentage=target_pct, drift=1.0, asset_drift_tolerance=0.1,
                        market_value=market_values.get(s, 0.0))
        for s in targets
    }
    return ctx


def test_sole_candidate_capped_at_global_default() -> None:
    """A single qualifying Underweight candidate would otherwise absorb the FULL $9000
    remaining_for_underweight pool. With no per-asset override, it falls back to the global
    max_portfolio_percentage=20% of $10,000 account_balance = $2000 cap. Unheld -> full $2000
    headroom -> allocation lands at exactly $2000, not $9000."""
    targets = {"X": AssetTarget("X", weight=1.0)}
    ctx = _ctx(targets)
    allocations = step3_alpha_leader(ctx, _TiedBroker())
    assert math.isclose(allocations["X"], 2000.0, abs_tol=0.01), (
        f"sole candidate must be capped at the global 20% * $10,000 = $2000, got {allocations['X']:.2f}"
    )
    print(f"[max-alloc-sole-candidate-global-cap] X capped at ${allocations['X']:.2f} "
          f"instead of absorbing the full $9000 pool — OK")


def test_per_asset_override_tighter_than_global() -> None:
    """X has its own max_allocation_percent=5% (tighter than the 20% global default) -> capped at
    $500 on $10,000 account_balance, not the global $2000."""
    targets = {"X": AssetTarget("X", weight=1.0, max_allocation_percent=5.0)}
    ctx = _ctx(targets)
    allocations = step3_alpha_leader(ctx, _TiedBroker())
    assert math.isclose(allocations["X"], 500.0, abs_tol=0.01), (
        f"X's own 5% override -> $500 cap on $10,000 account_balance, got {allocations['X']:.2f}"
    )
    print(f"[max-alloc-per-asset-override-tighter] X (5% override) capped at ${allocations['X']:.2f} "
          f"(tighter than the 20% global default) — OK")


def test_per_asset_override_looser_than_global() -> None:
    """X has its own max_allocation_percent=50% (looser than the 20% global default) -> its full
    momentum-weighted share ($4500, tied 50/50 with Y) survives uncapped, since $4500 < the 50%
    * $10,000 = $5000 override cap."""
    targets = {
        "X": AssetTarget("X", weight=1.0, max_allocation_percent=50.0),
        "Y": AssetTarget("Y", weight=1.0),
    }
    ctx = _ctx(targets)
    allocations = step3_alpha_leader(ctx, _TiedBroker())
    assert math.isclose(allocations["X"], 4500.0, abs_tol=0.01), (
        f"X's looser 50% override ($5000 cap) shouldn't bite on its $4500 tied share, got {allocations['X']:.2f}"
    )
    assert math.isclose(allocations["Y"], 2000.0, abs_tol=0.01), (
        f"Y has no override -> capped at the global 20% * $10,000 = $2000, got {allocations['Y']:.2f}"
    )
    print(f"[max-alloc-per-asset-override-looser] X (50% override) uncapped at ${allocations['X']:.2f}; "
          f"Y (no override, global 20%) capped at ${allocations['Y']:.2f} — OK")


def test_existing_holdings_reduce_headroom() -> None:
    """X already holds $1800 of its $2000 global-default cap before this cycle starts -> only
    $200 of headroom left, regardless of how large its momentum-weighted share would otherwise be.
    target_pct=90.0 keeps X's drift-math gap ($9000 - $1800 = $7200) comfortably positive so the
    momentum pool still funds it in the first place -- the headroom cap is the constraint under
    test, not the unrelated drift-gap eligibility check."""
    targets = {"X": AssetTarget("X", weight=1.0)}
    ctx = _ctx(targets, market_values={"X": 1800.0}, target_pct=90.0)
    allocations = step3_alpha_leader(ctx, _TiedBroker())
    assert math.isclose(allocations.get("X", 0.0), 200.0, abs_tol=0.01), (
        f"X already holds $1800 of its $2000 cap -> only $200 headroom left, got {allocations.get('X')}"
    )
    print(f"[max-alloc-existing-holdings-reduce-headroom] X capped at only ${allocations['X']:.2f} "
          f"of headroom given its existing $1800 holding — OK")


def test_alpha_leader_respects_per_asset_override() -> None:
    """The same per-asset override also caps the ALPHA allocation, not just Underweight. Give A
    a strong enough score to clear alpha_leader_least_momentum_score and become Alpha Leader, with
    alpha_cash_allocation_percentage + reinvestment_multiplier_factor sized so its uncapped Alpha
    allocation would exceed a tight 3% override -> must land at the override's dollar cap instead."""
    targets = {"A": AssetTarget("A", weight=1.0, max_allocation_percent=3.0)}
    ctx = _ctx(
        targets,
        alpha_leader_least_momentum_score=-9999.0,  # A always clears the cascade floor
        alpha_cash_allocation_percentage=50.0, reinvestment_multiplier_factor=2.0,
        min_momentum_score_to_fill_underweight=9999.0,  # no Underweight candidates -> isolate Alpha math
    )
    ctx.current_cash = 9000.0
    allocations = step3_alpha_leader(ctx, _TiedBroker())
    assert ctx.alpha_leader == "A", f"A should have become Alpha Leader, got {ctx.alpha_leader}"
    # Uncapped: raw_alpha_target=50%*9000=4500, multiplier_cash=9000*(2.0-1.0)=9000 -> 13500 desired,
    # but A's own 3% override caps it at 3% * $10,000 = $300 (unheld -> full headroom).
    assert math.isclose(allocations["A"], 300.0, abs_tol=0.01), (
        f"Alpha Leader A's own 3% override -> $300 cap on $10,000 account_balance, got {allocations['A']:.2f}"
    )
    print(f"[max-alloc-alpha-leader-override] Alpha Leader A (3% override) capped at "
          f"${allocations['A']:.2f} instead of its uncapped $13,500 desired allocation — OK")


def main() -> None:
    test_sole_candidate_capped_at_global_default()
    test_per_asset_override_tighter_than_global()
    test_per_asset_override_looser_than_global()
    test_existing_holdings_reduce_headroom()
    test_alpha_leader_respects_per_asset_override()
    print("\nSMOKE TEST (max_allocation_percent) PASSED")


if __name__ == "__main__":
    main()
