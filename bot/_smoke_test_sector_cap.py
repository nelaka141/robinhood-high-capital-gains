"""Focused coverage for max_sector_percentage — CLAUDE.md Step 3's sector/theme concentration
cap. Applied as a final pass over step3_alpha_leader's complete allocations dict (Alpha AND
Underweight allocations alike): for each sector_groups member group whose projected total
(current market value + everything planned this cycle) would exceed max_sector_percentage of
account_balance, every member's planned dollars are scaled down proportionally so the group's
projected total lands exactly at the cap. A symbol in no group is never affected.

Pure logic tests against RunContext/steps functions directly (same style as
bot/_smoke_test_fresh_alpha_leader_stop.py). All test symbols share an IDENTICAL close-price
series so step3_alpha_leader's real RSI/EMA math ties every Momentum_Score -> the
_momentum_weighted_split tie-fallback (equal split) applies, giving easy-to-verify dollar amounts
without needing to calibrate distinct scores.

Run: PYTHONPATH=. python3 bot/_smoke_test_sector_cap.py
"""
from __future__ import annotations

import math
from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata, SectorGroup
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
        max_portfolio_percentage=90.0, alpha_cash_allocation_percentage=0.0,
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
        max_sector_percentage=20.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx(symbols: list, sector_groups: dict, market_values: dict = None, **meta_overrides) -> RunContext:
    """current_cash=$4500, no tax reserve, no alpha allocation (alpha_cash_allocation_percentage=0,
    reinvestment_multiplier_factor=1.0) -> remaining_for_underweight = $4500 exactly, split evenly
    across every tied-score candidate (all symbols share the identical series).

    `sector_groups` values may be a plain list (no per-group override -> uses the global
    max_sector_percentage) or an already-built SectorGroup (to set a maxPercentage override)."""
    market_values = market_values or {}
    groups = {
        group: (entry if isinstance(entry, SectorGroup) else SectorGroup(members=list(entry)))
        for group, entry in sector_groups.items()
    }
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides),
        targets={s: AssetTarget(s, weight=1.0) for s in symbols},
        force_sell={}, blocked=[],
        sector_groups=groups,
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.current_cash = 4500.0
    ctx.tax_reserve = 0.0
    ctx.account_balance = 10000.0
    ctx.quotes = {s: Quote(s, last_trade_price=100.0) for s in symbols}
    ctx.drift_results = {
        s: DriftResult(s, current_percentage=0, actual_weight=0, target_weight=1.0,
                        target_percentage=1.0, drift=1.0, asset_drift_tolerance=0.1,
                        market_value=market_values.get(s, 0.0))
        for s in symbols
    }
    return ctx


def test_same_sector_pair_scaled_down_to_cap() -> None:
    """X1/X2 (same group, both unheld) and Y1 (ungrouped) tie on Momentum_Score -> each would get
    an equal $1500 share of the $4500 pool. X1+X2 = $3000 exceeds the 20%-of-$10,000 = $2000
    sector cap (both start at $0 market value) -> both scaled down so X1+X2 lands at exactly
    $2000; Y1 (different group) is untouched at $1500."""
    ctx = _ctx(["X1", "X2", "Y1"], sector_groups={"grp": ["X1", "X2"]})
    allocations = step3_alpha_leader(ctx, _TiedBroker())

    assert math.isclose(allocations["Y1"], 1500.0, abs_tol=0.01), (
        f"Y1 is in no sector group -> must be untouched at its $1500 equal share, got {allocations['Y1']:.2f}"
    )
    group_total = allocations["X1"] + allocations["X2"]
    assert math.isclose(group_total, 2000.0, abs_tol=0.01), (
        f"X1+X2 (same group, cap $2000) must land at exactly the cap, got ${group_total:.2f}"
    )
    assert math.isclose(allocations["X1"], allocations["X2"], abs_tol=0.01), (
        "the scale-down is proportional -> X1 and X2 (equal pre-scale shares) should stay equal"
    )
    print(f"[sector-cap-scales-pair] X1=${allocations['X1']:.2f} X2=${allocations['X2']:.2f} "
          f"(sum ${group_total:.2f} == $2000 cap); Y1=${allocations['Y1']:.2f} (different group, untouched) — OK")


def test_ungrouped_symbols_never_capped() -> None:
    """No sector_groups configured at all -> nobody is scaled, no matter how concentrated."""
    ctx = _ctx(["A", "B", "C"], sector_groups={})
    allocations = step3_alpha_leader(ctx, _TiedBroker())
    for s in ["A", "B", "C"]:
        assert math.isclose(allocations[s], 1500.0, abs_tol=0.01), (
            f"no sector_groups configured -> {s} should get its full $1500 equal share, got {allocations[s]:.2f}"
        )
    print("[sector-cap-no-groups] no sector_groups configured -> full $1500 shares, no scaling — OK")


def test_existing_holdings_alone_can_exhaust_sector_headroom() -> None:
    """X1 already holds $2000 of market value (== the entire $2000 sector cap) before this cycle
    even starts -> zero headroom left -> any NEW planned allocation for X1 or X2 (same group)
    must scale to $0, never negative. Y1 (different group) is still untouched."""
    ctx = _ctx(["X1", "X2", "Y1"], sector_groups={"grp": ["X1", "X2"]}, market_values={"X1": 2000.0})
    allocations = step3_alpha_leader(ctx, _TiedBroker())
    assert math.isclose(allocations.get("X1", 0.0), 0.0, abs_tol=0.01), (
        f"X1 alone already sits at the $2000 cap -> no new allocation, got {allocations.get('X1')}"
    )
    assert math.isclose(allocations.get("X2", 0.0), 0.0, abs_tol=0.01), (
        f"X2 shares X1's exhausted group headroom -> no new allocation either, got {allocations.get('X2')}"
    )
    assert math.isclose(allocations["Y1"], 1500.0, abs_tol=0.01), "Y1 (different group) still gets its full share"
    print("[sector-cap-exhausted-by-holdings] X1's existing $2000 holding alone exhausts the cap -> "
          "X1 and X2 both scale to $0.00, floored (never negative); Y1 unaffected — OK")


def test_per_group_max_percentage_override() -> None:
    """4 symbols tie on Momentum_Score -> each would get an equal $1125 share of the $4500 pool
    absent any cap ($2250 raw ask per group). grp1 (X1/X2) has its own maxPercentage=10% ->
    a tighter $1000 cap on $10,000 account_balance -> scaled down to $500 each. grp2 (Z1/Z2) has
    no override -> uses the global 20% -> a looser $2000 cap -> scaled down to $1000 each. Both
    groups get capped, but grp1's tighter override bites harder, proving the per-group override
    actually takes effect instead of silently falling back to the global value."""
    ctx = _ctx(
        ["X1", "X2", "Z1", "Z2"],
        sector_groups={
            "grp1": SectorGroup(members=["X1", "X2"], max_percentage=10.0),
            "grp2": ["Z1", "Z2"],
        },
    )
    allocations = step3_alpha_leader(ctx, _TiedBroker())

    grp1_total = allocations["X1"] + allocations["X2"]
    grp2_total = allocations["Z1"] + allocations["Z2"]
    assert math.isclose(grp1_total, 1000.0, abs_tol=0.01), (
        f"grp1's own maxPercentage=10% -> $1000 cap on $10,000 account_balance, got ${grp1_total:.2f}"
    )
    assert math.isclose(grp2_total, 2000.0, abs_tol=0.01), (
        f"grp2 has no override -> uses the global 20% -> $2000 cap, got ${grp2_total:.2f}"
    )
    assert grp1_total < grp2_total, "grp1's tighter 10% override must bind harder than grp2's looser global 20%"
    print(f"[sector-cap-per-group-override] grp1 (10% override) capped at ${grp1_total:.2f}; "
          f"grp2 (20% global default) capped at ${grp2_total:.2f} — different caps applied correctly — OK")


def main() -> None:
    test_same_sector_pair_scaled_down_to_cap()
    test_ungrouped_symbols_never_capped()
    test_existing_holdings_alone_can_exhaust_sector_headroom()
    test_per_group_max_percentage_override()
    print("\nSMOKE TEST (max_sector_percentage) PASSED")


if __name__ == "__main__":
    main()
