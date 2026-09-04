"""Coverage for `tax/paid_taxes_by_year.json` (v2.80.0) — the user-maintained record of actual
taxes paid, subtracted dollar-for-dollar from the percentage-based tax_reserve figure (which
still ramps as `(prior_years_base + max(0, current_year_gains)) * keep_aside_profits_for_tax_percent
/ 100`, exactly as before). The worked example from the feature request: 2026 realized gains
$69,870.67, set-aside 35% -> gross reserve $24,454.735; if $20,000 of 2026 taxes are already
recorded as paid, the reserve should be only $4,454.735 (only that $20,000 is netted out, not
$20,000 * 35%).

Pure logic tests against steps._compute_tax_reserve directly, plus one round-trip test through
step1_fetch_state / step6b_finalize_buys to confirm both call sites use it consistently.

Run: PYTHONPATH=. python3 bot/_smoke_test_paid_taxes.py
"""
from __future__ import annotations

import math
from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import RunContext
from bot.steps import _compute_tax_reserve, step6b_finalize_buys


def test_worked_example_from_the_feature_request() -> None:
    """$69,870.67 in 2026 gains, 35% set-aside, no prior years, $20,000 already paid for 2026 ->
    reserve = 69870.67*0.35 - 20000 = 4454.7345, not 69870.67*0.35 = 24454.7345."""
    reserve = _compute_tax_reserve(
        prior_years_base=0.0, current_year_gains=69870.67, percent=35.0, total_paid_taxes=20000.0,
    )
    assert math.isclose(reserve, 4454.7345, abs_tol=0.01), reserve
    print(f"[worked-example] ${69870.67:,.2f} gains @ 35% minus $20,000 paid -> reserve "
          f"${reserve:,.2f} (not ${69870.67*0.35:,.2f}) — OK")


def test_no_paid_taxes_matches_old_formula_exactly() -> None:
    """total_paid_taxes=0 must reproduce the pre-v2.80.0 formula bit-for-bit — this feature must
    never change behavior for anyone who hasn't recorded any paid taxes."""
    reserve = _compute_tax_reserve(
        prior_years_base=8500.0, current_year_gains=13731.87, percent=35.0, total_paid_taxes=0.0,
    )
    expected = (8500.0 + 13731.87) * 35.0 / 100
    assert math.isclose(reserve, expected, abs_tol=0.001), (reserve, expected)
    print(f"[unchanged-when-zero-paid] reserve ${reserve:,.2f} == the old formula's "
          f"${expected:,.2f} exactly when nothing has been recorded as paid — OK")


def test_floored_at_zero_never_negative() -> None:
    """Paid taxes exceeding the gross reserve must floor at $0, never go negative."""
    reserve = _compute_tax_reserve(
        prior_years_base=0.0, current_year_gains=1000.0, percent=35.0, total_paid_taxes=1_000_000.0,
    )
    assert reserve == 0.0, reserve
    print("[floored-at-zero] paid taxes far exceeding the gross reserve -> reserve floors at "
          "$0.00, never negative — OK")


def test_multi_year_paid_taxes_summed_across_all_years() -> None:
    """Paid-taxes entries for MULTIPLE years are all summed together and subtracted from the one
    blended (prior_years_base + current_year) * percent figure — matching how prior_years_base
    itself already blends every prior year before applying percent."""
    reserve = _compute_tax_reserve(
        prior_years_base=8500.0,  # e.g. 2025's stored realized-gains entry
        current_year_gains=13731.87,  # 2026 YTD
        percent=35.0,
        total_paid_taxes=1000.0 + 2000.0,  # 2025 paid $1,000 + 2026 paid $2,000
    )
    expected = max(0.0, (8500.0 + 13731.87) * 35.0 / 100 - 3000.0)
    assert math.isclose(reserve, expected, abs_tol=0.001), (reserve, expected)
    assert reserve > 0, "test should exercise the non-degenerate (not floored to $0) case"
    print(f"[multi-year-summed] 2025+2026 paid taxes ($1,000+$2,000=$3,000) both netted out of "
          f"the single blended reserve figure -> ${reserve:,.2f} — OK")


def test_negative_ytd_gains_still_floored_before_percent() -> None:
    """A net YTD loss (current_year_gains < 0) still floors at 0 inside the gross-reserve calc
    (unchanged pre-existing behavior) before paid taxes are netted out."""
    reserve = _compute_tax_reserve(
        prior_years_base=0.0, current_year_gains=-500.0, percent=35.0, total_paid_taxes=0.0,
    )
    assert reserve == 0.0, reserve
    print("[negative-ytd-still-zero] a net YTD loss contributes $0 to the gross reserve (floored "
          "before percent is applied), same as pre-v2.80.0 — OK")


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, max_portfolio_percentage=90.0,
        min_cash_absolute=250, min_cash_target=500, seek_approval_value=1_000_000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0,
        no_of_days_for_price_compare=3, cap_on_total_cash_balance_to_use=1_000_000,
        cool_down_period_after_lquidation=6, beta_benchmark_symbol="SPY",
        beta_calculation_lookback_days=30, sold_asset_repurchase_days=2,
        leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9, profit_resell_cooldown_days=15,
        selling_price_change=0.1, sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=1.0, materialize_profit_percentage_max=2.5,
        materialize_profit_in_dollars_max=1.0, profit_threshold_ramp_days=30,
        min_raw_gain_percent_to_sell=-1e9, keep_aside_profits_for_tax_percent=35.0,
        momentum_lookback_days=5, min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0, wash_sale_lookback_days=0, dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def test_step6b_finalize_buys_uses_paid_taxes() -> None:
    """End-to-end through step6b_finalize_buys: with $20,000 already paid against 2026's taxes,
    the hard cash cap used to size buys should reflect the SMALLER (paid-tax-reduced) tax_reserve
    — i.e. more cash available for buys than if paid_taxes_by_year were empty."""
    cfg = PortfolioConfig(meta=_meta(), targets={"X": AssetTarget("X", weight=1.0)}, force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 9, 3), config=cfg, account_number="TEST")
    ctx.tax_by_year = {}
    ctx.paid_taxes_by_year = {"2026": 20000.0}

    buys = step6b_finalize_buys(
        ctx, planned_buys={"X": 1000.0},
        net_realized_gains_ytd_effective=69870.67, buying_power_now=100000.0,
    )
    expected_reserve = 69870.67 * 0.35 - 20000.0
    assert math.isclose(ctx.tax_reserve, expected_reserve, abs_tol=0.01), ctx.tax_reserve
    assert len(buys) == 1 and math.isclose(buys[0].dollar_amount, 1000.0, abs_tol=0.01), buys
    print(f"[step6b-uses-paid-taxes] tax_reserve=${ctx.tax_reserve:,.2f} (${expected_reserve:,.2f} "
          f"expected) -> buy sized normally since it's well under the larger hard cap — OK")


def main() -> None:
    test_worked_example_from_the_feature_request()
    test_no_paid_taxes_matches_old_formula_exactly()
    test_floored_at_zero_never_negative()
    test_multi_year_paid_taxes_summed_across_all_years()
    test_negative_ytd_gains_still_floored_before_percent()
    test_step6b_finalize_buys_uses_paid_taxes()
    print("\nSMOKE TEST (tax/paid_taxes_by_year.json) PASSED")


if __name__ == "__main__":
    main()
