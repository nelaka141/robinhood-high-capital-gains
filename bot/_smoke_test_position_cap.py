"""Focused coverage for `max_position_value` / Step 3's Position Cap Top-Up (v2.80.0): after the
momentum-ranked top-down drift-gap fill, any deployable cash left over is used to top candidate
symbols' market value up toward their own configured `max_position_value` (a flat dollar cap set
alongside `weight`/`drift` in portfolio_targets.json) — independent of drift/Underweight/momentum
status, pro-rated by `weight` when several candidates compete for the same leftover cash, and
still bounded by the existing per-asset (`max_allocation_percent`) and sector caps.

Pure logic tests against RunContext/steps functions directly (same style as
bot/_smoke_test_sector_cap.py).

Run: PYTHONPATH=. python3 bot/_smoke_test_position_cap.py
"""
from __future__ import annotations

import math
from datetime import date

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata, SectorGroup
from bot.models import DriftResult, Position, Quote, RunContext
from bot.steps import step3_underweight_buys


def _flat_series(n: int = 60) -> list:
    return [100.0 + math.sin(i / 3.0) for i in range(n)]


class _TiedBroker:
    def get_daily_closes(self, symbol, start, end):
        return _flat_series()


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
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
        materialize_profit_in_dollars=0.0, min_raw_gain_percent_to_sell=-1e9,
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=90.0,
        wash_sale_lookback_days=0,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


def _ctx(targets: dict, drift: dict, current_cash: float = 4500.0, sector_groups: dict = None,
          **meta_overrides) -> RunContext:
    """`targets`: {symbol: AssetTarget}. `drift`: {symbol: DriftResult} — full control per symbol
    (unlike _smoke_test_sector_cap.py's generic builder), so a topup-only candidate can be given
    drift=0/not-underweight while a normal candidate still gets its usual gap fill."""
    groups = {
        group: (entry if isinstance(entry, SectorGroup) else SectorGroup(members=list(entry)))
        for group, entry in (sector_groups or {}).items()
    }
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides), targets=targets,
        force_sell={}, blocked=[], sector_groups=groups,
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.current_cash = current_cash
    ctx.tax_reserve = 0.0
    ctx.account_balance = 10000.0
    ctx.quotes = {s: Quote(s, last_trade_price=100.0) for s in targets}
    ctx.drift_results = drift
    return ctx


def _dr(target_weight: float, actual_weight: float, target_pct: float, mv: float,
        tolerance: float = 0.1) -> DriftResult:
    return DriftResult(
        symbol="?", current_percentage=mv / 100.0, actual_weight=actual_weight,
        target_weight=target_weight, target_percentage=target_pct,
        drift=abs(target_weight - actual_weight), asset_drift_tolerance=tolerance,
        market_value=mv,
    )


def test_topup_only_candidate_gets_leftover_cash() -> None:
    """Y is a normal Underweight candidate with a $1500 drift gap (filled first, as always).
    X has NO drift gap of its own (already at/above target -> not breached, excluded from the
    top-down fill entirely) but carries max_position_value=$800 and currently sits at $0 market
    value. Of the $4500 deployable cash, $1500 funds Y's gap; the $3000 left over tops X up to
    exactly its $800 cap (not the full leftover) — the rest of the leftover cash is simply unspent."""
    targets = {
        "Y": AssetTarget("Y", weight=1.0),
        "X": AssetTarget("X", weight=1.0, max_position_value=800.0),
    }
    drift = {
        "Y": _dr(target_weight=1.0, actual_weight=0.0, target_pct=15.0, mv=0.0),
        "X": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),  # not breached -> no gap fill
    }
    ctx = _ctx(targets, drift)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations["Y"], 1500.0, abs_tol=0.01), f"Y's normal drift-gap fill unaffected, got {allocations['Y']:.2f}"
    assert math.isclose(allocations.get("X", 0.0), 800.0, abs_tol=0.01), (
        f"X should be topped up to exactly its $800 max_position_value cap, got {allocations.get('X')}"
    )
    assert math.isclose(ctx.position_cap_topups.get("X", 0.0), 800.0, abs_tol=0.01), "reporting dict should match"
    print(f"[topup-only-candidate] Y=${allocations['Y']:.2f} (normal gap fill), "
          f"X=${allocations['X']:.2f} (topped up to its $800 cap out of $3000 leftover) — OK")


def test_topup_extends_a_symbol_already_partially_filled() -> None:
    """Z is BOTH Underweight (drift gap $500, existing $500 mv -> $1000 target dollar amount) AND
    carries max_position_value=$1500. It should receive its $500 gap fill from the primary pass
    (mv now $1000 planned), then get topped up FURTHER by leftover cash afterward — only the
    remaining $500 of room toward its $1500 cap, not the cap's full amount from scratch."""
    targets = {"Z": AssetTarget("Z", weight=1.0, max_position_value=1500.0)}
    drift = {"Z": _dr(target_weight=1.0, actual_weight=0.5, target_pct=10.0, mv=500.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations["Z"], 1000.0, abs_tol=0.01), (
        f"Z's total planned allocation: $500 gap fill (closing existing $500 mv up to the $1000 "
        f"drift target) + $500 top-up (the remaining room up to the $1500 cap) = $1000, got {allocations['Z']:.2f}"
    )
    assert math.isclose(ctx.position_cap_topups.get("Z", 0.0), 500.0, abs_tol=0.01), (
        f"only the EXTRA $500 beyond the normal $500 gap fill should count as top-up, got {ctx.position_cap_topups.get('Z')}"
    )
    print(f"[topup-extends-partial-fill] Z gap-filled by $500 then topped up +$500 more "
          f"to reach its $1500 cap (total planned mv ${500 + allocations['Z']:.2f}) — OK")


def test_topup_prorated_by_weight_across_multiple_candidates() -> None:
    """A (weight=3) and B (weight=1) both want top-up room far exceeding the $4500 leftover cash
    (no other candidate consumes any of it) -> split 3:1 by weight -> A=$3375, B=$1125."""
    targets = {
        "A": AssetTarget("A", weight=3.0, max_position_value=100000.0),
        "B": AssetTarget("B", weight=1.0, max_position_value=100000.0),
    }
    drift = {
        "A": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),
        "B": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),
    }
    ctx = _ctx(targets, drift, current_cash=4500.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations["A"], 3375.0, abs_tol=0.01), f"A (weight 3) should get 3/4 of $4500, got {allocations['A']:.2f}"
    assert math.isclose(allocations["B"], 1125.0, abs_tol=0.01), f"B (weight 1) should get 1/4 of $4500, got {allocations['B']:.2f}"
    print(f"[topup-prorated-by-weight] A(w=3)=${allocations['A']:.2f} B(w=1)=${allocations['B']:.2f} "
          f"— split 3:1 as expected — OK")


def test_topup_water_filling_when_one_candidate_caps_out() -> None:
    """A (weight=1, room only $200) and B (weight=1, room $100000) split $4500 evenly at first
    ($2250 each), but A's room caps at $200 -> A gets $200, and the freed-up $4300 all flows to B
    on the next round (water-filling, not a one-shot equal split)."""
    targets = {
        "A": AssetTarget("A", weight=1.0, max_position_value=200.0),
        "B": AssetTarget("B", weight=1.0, max_position_value=100000.0),
    }
    drift = {
        "A": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),
        "B": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),
    }
    ctx = _ctx(targets, drift, current_cash=4500.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations["A"], 200.0, abs_tol=0.01), f"A capped at its $200 room, got {allocations['A']:.2f}"
    assert math.isclose(allocations["B"], 4300.0, abs_tol=0.01), (
        f"B should absorb the $4300 A couldn't use (water-filling redistribution), got {allocations['B']:.2f}"
    )
    print(f"[topup-water-filling] A capped at ${allocations['A']:.2f}, B absorbed the rest "
          f"(${allocations['B']:.2f}) once A hit its cap — OK")


def test_topup_bounded_by_per_asset_headroom_cap() -> None:
    """C has max_position_value=$5000 (plenty of room by that measure alone) but the GLOBAL
    max_portfolio_percentage is tight (10% of $10,000 = $1000) and C already holds $900 -> only
    $100 of headroom regardless of what max_position_value would otherwise allow."""
    targets = {"C": AssetTarget("C", weight=1.0, max_position_value=5000.0)}
    drift = {"C": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=900.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0, max_portfolio_percentage=10.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("C", 0.0), 100.0, abs_tol=0.01), (
        f"the tighter global per-asset cap (10% of $10,000 minus existing $900 = $100 headroom) "
        f"must still bind even though max_position_value alone would allow far more, got {allocations.get('C')}"
    )
    print(f"[topup-bounded-by-headroom] C's top-up capped at ${allocations.get('C', 0.0):.2f} by the "
          f"global max_portfolio_percentage headroom, not its much higher max_position_value — OK")


def test_topup_bounded_by_sector_cap() -> None:
    """D and E share a sector group capped at 15% of $10,000 = $1500 (global default). Both have
    huge max_position_value room and no existing holdings -> pro-rated 1:1 to $2250 each before
    the sector cap pass, then scaled down together so the group lands at exactly $1500 total."""
    targets = {
        "D": AssetTarget("D", weight=1.0, max_position_value=100000.0),
        "E": AssetTarget("E", weight=1.0, max_position_value=100000.0),
    }
    drift = {
        "D": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),
        "E": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),
    }
    ctx = _ctx(targets, drift, current_cash=4500.0, max_sector_percentage=15.0,
               sector_groups={"grp": ["D", "E"]})
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    total = allocations["D"] + allocations["E"]
    assert math.isclose(total, 1500.0, abs_tol=0.01), f"D+E must land at the $1500 sector cap, got ${total:.2f}"
    assert math.isclose(allocations["D"], allocations["E"], abs_tol=0.01), "equal pre-scale top-up shares stay equal after scaling"
    assert math.isclose(ctx.position_cap_topups["D"] + ctx.position_cap_topups["E"], 1500.0, abs_tol=0.01), (
        "the reporting dict must reflect the POST-sector-cap-scaled figures, not the pre-scale ones"
    )
    print(f"[topup-bounded-by-sector-cap] D=${allocations['D']:.2f} E=${allocations['E']:.2f} "
          f"(sum ${total:.2f} == $1500 sector cap; position_cap_topups dict scaled in sync) — OK")


def test_resolved_max_position_value_override_vs_global_default() -> None:
    """Direct unit coverage of PortfolioConfig.resolved_max_position_value (v2.80.1): a
    per-asset override always wins; absent that, the global `default_max_position_value`
    applies; absent both, the symbol resolves to None (doesn't participate at all)."""
    targets = {
        "OVERRIDE": AssetTarget("OVERRIDE", weight=1.0, max_position_value=999.0),
        "DEFAULTED": AssetTarget("DEFAULTED", weight=1.0),
        "NEITHER": AssetTarget("NEITHER", weight=1.0),
    }
    cfg = PortfolioConfig(
        meta=_meta(default_max_position_value=6000.0), targets=targets, force_sell={}, blocked=[],
    )
    assert cfg.resolved_max_position_value("OVERRIDE") == 999.0, "per-asset override must win over the global default"
    assert cfg.resolved_max_position_value("DEFAULTED") == 6000.0, "no override -> falls back to the global default"

    cfg_no_default = PortfolioConfig(
        meta=_meta(default_max_position_value=None), targets=targets, force_sell={}, blocked=[],
    )
    assert cfg_no_default.resolved_max_position_value("NEITHER") is None, (
        "no override AND no global default -> None, symbol never participates in the top-up pass"
    )
    print("[resolved-max-position-value] override wins ($999), no-override falls back to global "
          "default ($6000), neither-set resolves to None — OK")


def test_global_default_opts_every_target_into_topup() -> None:
    """With `default_max_position_value` set, a symbol carrying NO per-asset override still
    gets topped up toward that global figure — the whole point of the v2.80.1 feature request:
    every target participates by default unless it overrides or is excluded/guarded."""
    targets = {
        "PLAIN": AssetTarget("PLAIN", weight=1.0),  # no per-asset max_position_value at all
    }
    drift = {"PLAIN": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0, default_max_position_value=6000.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("PLAIN", 0.0), 4500.0, abs_tol=0.01), (
        f"PLAIN has no override but the global default ($6000) exceeds the $4500 leftover cash, "
        f"so it should absorb all of it, got {allocations.get('PLAIN')}"
    )
    print(f"[global-default-opts-in] PLAIN (no per-asset max_position_value) still topped up "
          f"${allocations['PLAIN']:.2f} via the $6000 global default — OK")


def test_per_asset_override_still_wins_when_global_default_set() -> None:
    """G has its OWN max_position_value ($500), tighter than the global default ($6000) — the
    override must still win, not silently get replaced by the (looser) global figure."""
    targets = {"G": AssetTarget("G", weight=1.0, max_position_value=500.0)}
    drift = {"G": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0, default_max_position_value=6000.0)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("G", 0.0), 500.0, abs_tol=0.01), (
        f"G's own $500 override must cap the top-up, not the looser $6000 global default, got {allocations.get('G')}"
    )
    print(f"[override-wins-over-global-default] G capped at its own $500 override "
          f"(not the $6000 global default) — OK")


def test_topup_skips_buy_guarded_symbol() -> None:
    """F carries max_position_value but is buy-guarded (Step 2) -> gets nothing, and the
    leftover cash it would have used simply goes unspent (no other candidate to redirect to)."""
    targets = {"F": AssetTarget("F", weight=1.0, max_position_value=5000.0)}
    drift = {"F": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0)
    ctx.buy_guarded_symbols["F"] = ["Buy-timing guard active"]
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("F", 0.0), 0.0, abs_tol=0.01), f"buy-guarded F must get no top-up, got {allocations.get('F')}"
    reasons = [s.reason for s in ctx.skipped if s.symbol == "F" and s.would_be_action == "Position Cap Top-Up"]
    print(f"[topup-skips-buy-guarded] F (buy-guarded) got no top-up; logged={bool(reasons)} — OK")


def test_topup_skips_below_momentum_floor() -> None:
    """H has zero market value and ample max_position_value room, but the portfolio's momentum
    floor is set so high that H's real (near-zero, flat-series) Momentum_Score can't possibly
    clear it — v2.81.0 closes the gap where Top-Up previously ignored
    min_momentum_score_to_fill_underweight entirely (the dry run that surfaced this: a symbol
    ranked LAST of 53 by Momentum_Score still got a multi-thousand-dollar top-up)."""
    targets = {"H": AssetTarget("H", weight=1.0, max_position_value=5000.0)}
    drift = {"H": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0, min_momentum_score_to_fill_underweight=1e6)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("H", 0.0), 0.0, abs_tol=0.01), (
        f"H's Momentum_Score can't clear a 1e6 floor -> no top-up, got {allocations.get('H')}"
    )
    reasons = [s.reason for s in ctx.skipped if s.symbol == "H" and s.would_be_action == "Position Cap Top-Up"]
    assert reasons and "min_momentum_score_to_fill_underweight" in reasons[0], (
        f"expected a momentum-floor SKIPPED entry for H, got {reasons}"
    )
    print("[topup-skips-below-momentum-floor] H excluded from top-up by the momentum floor — OK")


def test_topup_skips_held_position_at_a_loss() -> None:
    """I is currently held (small quantity) with avg_cost_basis ABOVE the live quote (100.0) ->
    the position is at a loss, so v2.81.0's held-at-a-loss guard excludes it from top-up even
    though it has ample max_position_value room and clears every other guard."""
    targets = {"I": AssetTarget("I", weight=1.0, max_position_value=5000.0)}
    drift = {"I": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=50.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0)
    ctx.positions["I"] = Position(symbol="I", quantity=0.5, avg_cost_basis=120.0)  # quote 100.0 -> at a loss
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("I", 0.0), 0.0, abs_tol=0.01), (
        f"held-at-a-loss guard should block top-up entirely, got {allocations.get('I')}"
    )
    reasons = [s.reason for s in ctx.skipped if s.symbol == "I" and s.would_be_action == "Position Cap Top-Up"]
    assert reasons and "at a loss" in reasons[0], f"expected a held-at-a-loss SKIPPED entry for I, got {reasons}"
    print("[topup-skips-held-at-a-loss] I (held, underwater vs avg_cost_basis) excluded from top-up — OK")


def test_topup_still_fires_for_held_position_at_a_gain() -> None:
    """Regression: J is held with avg_cost_basis BELOW the live quote (a real gain) -> the
    held-at-a-loss guard must NOT block it; top-up proceeds normally."""
    targets = {"J": AssetTarget("J", weight=1.0, max_position_value=5000.0)}
    drift = {"J": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=50.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0)
    ctx.positions["J"] = Position(symbol="J", quantity=0.5, avg_cost_basis=80.0)  # quote 100.0 -> at a gain
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    # room = min(cap - mv, headroom - planned) = min(5000-50, 0.9*10000-50) = min(4950, 8950) = 4950,
    # bounded by the $4500 leftover cash (sole candidate) -> full $4500 flows to J.
    assert math.isclose(allocations.get("J", 0.0), 4500.0, abs_tol=0.01), (
        f"J is at a gain, not a loss -> should be topped up normally, got {allocations.get('J')}"
    )
    print(f"[topup-fires-for-held-at-a-gain] J (held, in-the-money) topped up ${allocations['J']:.2f} — OK")


def test_topup_skips_unresolved_cost_basis() -> None:
    """K is held with avg_cost_basis=None (unresolved, per Step 1's fail-closed rule) -> can't
    prove it isn't a loss, so v2.81.0 excludes it from top-up the same as a confirmed loss."""
    targets = {"K": AssetTarget("K", weight=1.0, max_position_value=5000.0)}
    drift = {"K": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=50.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0)
    ctx.positions["K"] = Position(symbol="K", quantity=0.5, avg_cost_basis=None)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("K", 0.0), 0.0, abs_tol=0.01), (
        f"unresolved cost basis must fail closed for top-up, got {allocations.get('K')}"
    )
    print("[topup-skips-unresolved-cost-basis] K (avg_cost_basis unresolved) excluded from top-up — OK")


def test_topup_unaffected_for_zero_quantity_position_record() -> None:
    """Regression: a symbol with a Position record but quantity=0 (fully liquidated/never
    filled) has no cost basis to be 'at a loss' against -> the held-at-a-loss guard must not
    touch it, matching every existing topup-only-candidate test's assumption that an unheld
    symbol tops up normally."""
    targets = {"L": AssetTarget("L", weight=1.0, max_position_value=5000.0)}
    drift = {"L": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0)}
    ctx = _ctx(targets, drift, current_cash=4500.0)
    ctx.positions["L"] = Position(symbol="L", quantity=0.0, avg_cost_basis=None)
    allocations = step3_underweight_buys(ctx, _TiedBroker())

    assert math.isclose(allocations.get("L", 0.0), 4500.0, abs_tol=0.01), (
        f"a zero-quantity position record must not trigger the held-at-a-loss guard, got {allocations.get('L')}"
    )
    print(f"[topup-unaffected-zero-qty-position] L (quantity=0) topped up ${allocations['L']:.2f} normally — OK")


def main() -> None:
    test_topup_only_candidate_gets_leftover_cash()
    test_topup_extends_a_symbol_already_partially_filled()
    test_topup_prorated_by_weight_across_multiple_candidates()
    test_topup_water_filling_when_one_candidate_caps_out()
    test_topup_bounded_by_per_asset_headroom_cap()
    test_topup_bounded_by_sector_cap()
    test_resolved_max_position_value_override_vs_global_default()
    test_global_default_opts_every_target_into_topup()
    test_per_asset_override_still_wins_when_global_default_set()
    test_topup_skips_buy_guarded_symbol()
    test_topup_skips_below_momentum_floor()
    test_topup_skips_held_position_at_a_loss()
    test_topup_still_fires_for_held_position_at_a_gain()
    test_topup_skips_unresolved_cost_basis()
    test_topup_unaffected_for_zero_quantity_position_record()
    print("\nSMOKE TEST (max_position_value / Position Cap Top-Up) PASSED")


if __name__ == "__main__":
    main()
