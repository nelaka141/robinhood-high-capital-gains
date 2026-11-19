"""Focused coverage for the v2.92.0 portfolio-wide unrealized-loss buy halt
(`total_unrealized_losses_threshold`): Step 1 sums the dollar loss of every held target position
that is underwater vs. avg_cost_basis (positions in profit do NOT offset it), and when that total
is MORE than the threshold Step 3 plans no buys at all — top-down fill and Position Cap Top-Up
alike — while sells are untouched.

Run: PYTHONPATH=. python3 bot/_smoke_test_unrealized_loss_guard.py
"""
from __future__ import annotations

import math
from datetime import date

from bot import steps
from bot.config import AssetTarget, PortfolioConfig
from bot.journal import render_entry
from bot.models import Position, Quote, RunContext
from bot.state import AssetPriceState
from bot.serialize import ctx_from_jsonable, ctx_to_jsonable
from bot._smoke_test_position_cap import _TiedBroker, _ctx, _dr, _meta
from bot._smoke_test_wash_sale import _Step1Broker


def _step1_ctx(positions, prices, blocked=(), **meta_overrides) -> RunContext:
    targets = {s: AssetTarget(s, weight=1.0) for s in prices}
    cfg = PortfolioConfig(meta=_meta(**meta_overrides), targets=targets, force_sell={}, blocked=list(blocked))
    ctx = RunContext(current_date=date(2026, 11, 19), config=cfg, account_number="TEST")
    ctx.price_state = {s: AssetPriceState(peakPrice=p) for s, p in prices.items()}
    quotes = {s: Quote(s, last_trade_price=p) for s, p in prices.items()}
    steps.step1_fetch_state(ctx, _Step1Broker(positions, quotes), repo_dir="/nonexistent")
    return ctx


def test_total_counts_only_underwater_positions() -> None:
    positions = {
        "LOSS1": Position("LOSS1", quantity=10.0, avg_cost_basis=100.0),   # -$200
        "LOSS2": Position("LOSS2", quantity=5.0, avg_cost_basis=50.0),     # -$100
        "GAIN": Position("GAIN", quantity=100.0, avg_cost_basis=10.0),     # +$1000, must NOT offset
        "NOBASIS": Position("NOBASIS", quantity=10.0, avg_cost_basis=None),  # unmeasurable -> left out
        "FROZEN": Position("FROZEN", quantity=300.0, avg_cost_basis=7.0),  # blocked/exempt -> left out
    }
    prices = {"LOSS1": 80.0, "LOSS2": 30.0, "GAIN": 20.0, "NOBASIS": 1.0, "FROZEN": 0.3}
    ctx = _step1_ctx(positions, prices, blocked=["FROZEN"])
    assert math.isclose(ctx.total_unrealized_losses, 300.0), ctx.total_unrealized_losses
    print(f"[unrealized-loss-total] ${ctx.total_unrealized_losses:.2f} (gains don't offset, blocked excluded) — OK")


def _buy_ctx(total_losses: float, threshold):
    targets = {
        "Y": AssetTarget("Y", weight=1.0),
        "X": AssetTarget("X", weight=1.0, max_position_value=800.0),
    }
    drift = {
        "Y": _dr(target_weight=1.0, actual_weight=0.0, target_pct=15.0, mv=0.0),
        "X": _dr(target_weight=0.0, actual_weight=0.0, target_pct=0.0, mv=0.0),
    }
    ctx = _ctx(targets, drift, total_unrealized_losses_threshold=threshold)
    ctx.total_unrealized_losses = total_losses
    return ctx


def test_over_threshold_halts_every_buy_path() -> None:
    ctx = _buy_ctx(total_losses=5000.01, threshold=5000.0)
    allocations = steps.step3_underweight_buys(ctx, _TiedBroker())
    assert allocations == {}, allocations
    assert not ctx.position_cap_topups, ctx.position_cap_topups
    assert ctx.unrealized_loss_buy_halt and "5,000.01" in ctx.unrealized_loss_buy_halt
    assert ctx.momentum_scores, "ranking table is still computed for the journal"
    assert any(s.symbol == "ALL" for s in ctx.skipped)
    entry = render_entry(ctx)
    assert "BUYS HALTED" in entry, entry
    print("[unrealized-loss-halt] $5,000.01 > $5,000 -> no top-down fill, no top-up — OK")


def test_at_or_under_threshold_buys_normally() -> None:
    ctx = _buy_ctx(total_losses=5000.0, threshold=5000.0)  # "more than" — equal does not halt
    allocations = steps.step3_underweight_buys(ctx, _TiedBroker())
    assert math.isclose(allocations["Y"], 1500.0, abs_tol=0.01), allocations
    assert math.isclose(allocations["X"], 800.0, abs_tol=0.01), allocations
    assert ctx.unrealized_loss_buy_halt is None
    print("[unrealized-loss-equal] exactly at threshold -> buys proceed — OK")


def test_unset_threshold_disables_guard() -> None:
    ctx = _buy_ctx(total_losses=1e9, threshold=None)
    allocations = steps.step3_underweight_buys(ctx, _TiedBroker())
    assert allocations.get("Y", 0) > 0, allocations
    print("[unrealized-loss-off] threshold unset -> guard inactive — OK")


def test_finalize_backstop_and_roundtrip() -> None:
    ctx = _buy_ctx(total_losses=9000.0, threshold=5000.0)
    steps.step3_underweight_buys(ctx, _TiedBroker())
    restored = ctx_from_jsonable(ctx_to_jsonable(ctx), ctx.config)
    assert restored.unrealized_loss_buy_halt == ctx.unrealized_loss_buy_halt
    assert restored.total_unrealized_losses == 9000.0
    buys = steps.step6b_finalize_buys(restored, {"Y": 1500.0}, 0.0, 100000.0)
    assert buys == [], buys
    print("[unrealized-loss-finalize] halt survives plan->finalize and drops stray buys — OK")


def main() -> None:
    test_total_counts_only_underwater_positions()
    test_over_threshold_halts_every_buy_path()
    test_at_or_under_threshold_buys_normally()
    test_unset_threshold_disables_guard()
    test_finalize_backstop_and_roundtrip()
    print("\nSMOKE TEST (total_unrealized_losses_threshold buy halt) PASSED")


if __name__ == "__main__":
    main()
