"""Focused coverage for `max_allocation_percent` — the per-asset override of `max_portfolio_percentage`
(CLAUDE.md Core Parameters, `max_portfolio_percentage`). `_headroom()` in step3_underweight_buys
uses `cfg.max_allocation_percentage(symbol)` (asset's own override if set in
portfolio_targets.json, else the global default) to cap every Underweight candidate's top-down
gap fill, so a symbol's market value (existing holdings + this
cycle's planned buy) never exceeds this cap — even when its drift gap is much larger than the cap
allows (only caught afterwards by the separate, coarser `max_sector_percentage` group cap).

Pure logic tests against RunContext/steps functions directly (same style as
bot/_smoke_test_sector_cap.py). Test symbols share an IDENTICAL close-price series so every
Momentum_Score ties, giving
easy-to-verify dollar amounts without needing to calibrate distinct scores.

Run: PYTHONPATH=. python3 bot/_smoke_test_max_allocation.py
"""
from __future__ import annotations

import math
from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import DriftResult, Quote, RunContext
from bot.steps import step3_underweight_buys


def _flat_series(n: int = 60) -> list:
    return [100.0 + math.sin(i / 3.0) for i in range(n)]


class _TiedBroker:
    """Every symbol gets the IDENTICAL series -> identical Momentum_Score for all of them."""
    def get_daily_closes(self, symbol, start, end):
        return _flat_series()


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=20.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=1_000_000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=0.0,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=100.0,  # loose -> isolates the per-asset cap from the sector cap
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx(targets: dict, market_values: dict = None, target_pct: float = 1.0, **meta_overrides) -> RunContext:
    """current_cash=$9000, no tax reserve -> base_deployable_cash = $9000 exactly. Every
    candidate's drift gap is target_pct% of the $10,000 account_balance minus its market value;
    the top-down fill grants each its full gap (capped at its per-asset headroom) in ranking
    order until the cash runs out.

    `targets` maps symbol -> AssetTarget (so callers can set max_allocation_percent per symbol)."""
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
    """A single qualifying Underweight candidate with a $9000 drift gap would otherwise absorb
    the FULL $9000 deployable cash. With no per-asset override, it falls back to the global
    max_portfolio_percentage=20% of $10,000 account_balance = $2000 cap. Unheld -> full $2000
    headroom -> allocation lands at exactly $2000, not $9000."""
    targets = {"X": AssetTarget("X", weight=1.0)}
    ctx = _ctx(targets, target_pct=90.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())
    assert math.isclose(allocations["X"], 2000.0, abs_tol=0.01), (
        f"sole candidate must be capped at the global 20% * $10,000 = $2000, got {allocations['X']:.2f}"
    )
    print(f"[max-alloc-sole-candidate-global-cap] X capped at ${allocations['X']:.2f} "
          f"instead of absorbing the full $9000 pool — OK")


def test_per_asset_override_tighter_than_global() -> None:
    """X has its own max_allocation_percent=5% (tighter than the 20% global default) -> capped at
    $500 on $10,000 account_balance, not the global $2000."""
    targets = {"X": AssetTarget("X", weight=1.0, max_allocation_percent=5.0)}
    ctx = _ctx(targets, target_pct=90.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())
    assert math.isclose(allocations["X"], 500.0, abs_tol=0.01), (
        f"X's own 5% override -> $500 cap on $10,000 account_balance, got {allocations['X']:.2f}"
    )
    print(f"[max-alloc-per-asset-override-tighter] X (5% override) capped at ${allocations['X']:.2f} "
          f"(tighter than the 20% global default) — OK")


def test_per_asset_override_looser_than_global() -> None:
    """X has its own max_allocation_percent=50% (looser than the 20% global default) -> its full
    $4500 gap fill survives uncapped, since $4500 < the 50%
    * $10,000 = $5000 override cap. Y (same $4500 gap, no override) is capped at the global 20%
    -> $2000."""
    targets = {
        "X": AssetTarget("X", weight=1.0, max_allocation_percent=50.0),
        "Y": AssetTarget("Y", weight=1.0),
    }
    ctx = _ctx(targets, target_pct=45.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())
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
    allocations = step3_underweight_buys(ctx, _TiedBroker())
    assert math.isclose(allocations.get("X", 0.0), 200.0, abs_tol=0.01), (
        f"X already holds $1800 of its $2000 cap -> only $200 headroom left, got {allocations.get('X')}"
    )
    print(f"[max-alloc-existing-holdings-reduce-headroom] X capped at only ${allocations['X']:.2f} "
          f"of headroom given its existing $1800 holding — OK")


def main() -> None:
    test_sole_candidate_capped_at_global_default()
    test_per_asset_override_tighter_than_global()
    test_per_asset_override_looser_than_global()
    test_existing_holdings_reduce_headroom()
    print("\nSMOKE TEST (max_allocation_percent) PASSED")


if __name__ == "__main__":
    main()
