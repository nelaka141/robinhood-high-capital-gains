"""Coverage for the v2.91.0 pre-sell re-quote check (`sell-recheck`, steps.recheck_sells_against_requotes).

`plan` gates and sizes every profit sell off the snapshot quote, but the market orders go out
minutes later. On 2026-10-02 COIN was quoted at $198.75 (+2.72% on a single $193.49 lot), GET THE
PROFITS sold 12 shares and the cleanup pass swept the 0.8167-share remainder — and both filled at
~$191.29, realizing -$28.19 instead of the planned +$63. Right before placing any sell the agent
now re-quotes, and any profit sell whose fresh price no longer clears its own `min_sell_price`
(plus requote_min_margin_percent) is dropped.

Run: PYTHONPATH=. python3 bot/_smoke_test_sell_requote.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot, TradeIntent
from bot.serialize import ctx_to_jsonable
from bot.steps import (
    recheck_sells_against_requotes, step4_profit_taking, step4b_sell_cleanup, step6a_prepare_sells,
)


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0,
        no_of_days_for_price_compare=3, cap_on_total_cash_balance_to_use=30000,
        cool_down_period_after_lquidation=6, beta_benchmark_symbol="SPY",
        beta_calculation_lookback_days=30, sold_asset_repurchase_days=2,
        leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9, profit_resell_cooldown_days=15,
        selling_price_change=0.1, sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.0, profit_sell_percentage=90.0,
        materialize_profit_in_dollars=40.0,
        materialize_profit_percentage_max=2.0, materialize_profit_in_dollars_max=40.0,
        profit_threshold_ramp_days=30, min_raw_gain_percent_to_sell=0.5,
        keep_aside_profits_for_tax_percent=30.0, momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0, max_sector_percentage=0.0,
        wash_sale_lookback_days=0, dormant_asset_days=5,
        cleanup_dust_threshold_dollars=200.0, requote_min_margin_percent=0.25,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        # Flat-to-rising closes so the selling_price_change guard clears.
        return [190.0, 192.0, 194.0, 196.0, 198.0]


def _coin_ctx():
    """The 2026-10-02 COIN position: one lot of 12.816725 sh @ $193.49, snapshot quote $198.75."""
    cfg = PortfolioConfig(meta=_meta(), targets={"COIN": AssetTarget(symbol="COIN", weight=1.0)},
                          force_sell={}, blocked=[])
    ctx = RunContext(current_date=date(2026, 10, 2), config=cfg, account_number="TEST")
    ctx.positions = {"COIN": Position(symbol="COIN", quantity=12.816725, avg_cost_basis=193.49)}
    ctx.quotes = {"COIN": Quote(symbol="COIN", last_trade_price=198.75)}
    broker = _Broker({"COIN": [
        TaxLot(open_lot_id="l1", quantity=12.816725, cost_per_share=193.49, open_date=date(2026, 9, 29)),
    ]})
    step4_profit_taking(ctx, broker)
    step4b_sell_cleanup(ctx, broker)
    sells, halted, _ = step6a_prepare_sells(ctx, {})
    assert not halted
    return ctx, sells


def test_plan_stamps_min_sell_price() -> None:
    ctx, sells = _coin_ctx()
    assert len(ctx.profit_taking_sells) == 1 and len(ctx.cleanup_sells) == 1, (ctx.profit_taking_sells, ctx.cleanup_sells)
    assert [t.min_sell_price for t in sells] == [193.49, 193.49], [t.min_sell_price for t in sells]
    print("[stamps-floor] COIN GTP sale + cleanup sweep both carry min_sell_price $193.49 — OK")


def test_coin_drop_drops_both_sells() -> None:
    ctx, sells = _coin_ctx()
    planned_buys = {"COIN": 500.0}
    kept = recheck_sells_against_requotes(ctx, sells, {"COIN": 191.29}, planned_buys)
    assert kept == [], kept
    assert ctx.profit_taking_sells == [] and ctx.cleanup_sells == []
    assert ctx.total_high_beta_gains_realized == 0.0 and ctx.total_cleanup_gains_realized == 0.0
    assert "COIN" not in planned_buys, planned_buys
    skip = [s for s in ctx.skipped if s.symbol == "COIN"]
    assert len(skip) == 1 and "191.29" in skip[0].reason and "GET THE PROFITS + Sell Cleanup Pass" in skip[0].would_be_action, skip
    print(f"[coin-drop] fresh $191.29 < $193.97 bar -> both COIN sells dropped, buy removed: {skip[0].reason} — OK")


def test_price_holds_keeps_sells() -> None:
    ctx, sells = _coin_ctx()
    kept = recheck_sells_against_requotes(ctx, sells, {"COIN": 197.10}, {})
    assert len(kept) == 2 and len(ctx.profit_taking_sells) == 1 and len(ctx.cleanup_sells) == 1
    assert ctx.total_high_beta_gains_realized > 0
    print("[price-holds] fresh $197.10 clears the bar -> both sells kept — OK")


def test_margin_is_applied() -> None:
    ctx, sells = _coin_ctx()
    # 193.60 is above the lot cost but below 193.49 * 1.0025 = 193.97.
    kept = recheck_sells_against_requotes(ctx, sells, {"COIN": 193.60}, {})
    assert kept == [], kept
    print("[margin] fresh $193.60 above cost but inside the 0.25% margin -> dropped — OK")


def test_missing_quote_fails_closed() -> None:
    ctx, sells = _coin_ctx()
    kept = recheck_sells_against_requotes(ctx, sells, {}, {})
    assert kept == [] and "fail-closed" in ctx.skipped[-1].reason, ctx.skipped
    print("[missing-quote] no fresh COIN quote -> dropped (fail-closed) — OK")


def test_liquidations_never_rechecked() -> None:
    ctx, sells = _coin_ctx()
    ctx.positions["DD"] = Position(symbol="DD", quantity=5.0, avg_cost_basis=100.0)
    ctx.quotes["DD"] = Quote(symbol="DD", last_trade_price=40.0)
    liq = TradeIntent(symbol="DD", side="sell", quantity=5.0, reason="Drawdown Audit emergency liquidation (100%)")
    kept = recheck_sells_against_requotes(ctx, [liq] + sells, {"COIN": 191.29}, {})
    assert kept == [liq], kept
    print("[liquidation] emergency liquidation with no fresh quote still placed; COIN dropped — OK")


def test_net_exit_floor_is_lot_weighted_break_even() -> None:
    cfg = PortfolioConfig(meta=_meta(profit_resell_cooldown_days=0), force_sell={}, blocked=[],
                          targets={"MIX": AssetTarget(symbol="MIX", weight=1.0)})
    ctx = RunContext(current_date=date(2026, 10, 2), config=cfg, account_number="TEST")
    ctx.positions = {"MIX": Position(symbol="MIX", quantity=10.0, avg_cost_basis=180.0)}
    ctx.quotes = {"MIX": Quote(symbol="MIX", last_trade_price=198.75)}
    broker = _Broker({"MIX": [
        TaxLot(open_lot_id="a", quantity=8.0, cost_per_share=170.0, open_date=date(2026, 8, 1)),
        TaxLot(open_lot_id="b", quantity=2.0, cost_per_share=220.0, open_date=date(2026, 9, 1)),
    ]})
    step4_profit_taking(ctx, broker)
    assert len(ctx.profit_taking_sells) == 1 and "FULL EXIT" in ctx.profit_taking_sells[0].reason, ctx.profit_taking_sells
    floor = ctx.profit_taking_sells[0].min_sell_price
    assert abs(floor - 180.0) < 1e-6, floor  # (8*170 + 2*220) / 10
    print(f"[net-exit-floor] mixed position full exit floor = lot-weighted break-even ${floor:.2f} — OK")


def test_cli_round_trip() -> None:
    ctx, sells = _coin_ctx()
    from bot.cli import _intent_to_dict
    repo_root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "plan_result.json").write_text(json.dumps({
            "no_trades": False, "halted_for_approval": False, "halt_reason": None,
            "sells_to_place": [_intent_to_dict(t) for t in sells], "gross_sell_value": 0.0,
            "resume_state": {"ctx": ctx_to_jsonable(ctx), "planned_buys": {"COIN": 300.0}},
        }))
        (tmp / "requotes.json").write_text(json.dumps({"COIN": 191.29}))
        subprocess.run(
            [sys.executable, "-m", "bot.cli", "sell-recheck", "--plan", str(tmp / "plan_result.json"),
             "--quotes", str(tmp / "requotes.json"), "--repo-dir", str(repo_root),
             "--out", str(tmp / "plan_result.json")],
            check=True, cwd=repo_root, capture_output=True,
        )
        out = json.loads((tmp / "plan_result.json").read_text())
        assert out["sells_to_place"] == [], out["sells_to_place"]
        assert out["sell_recheck"]["dropped_symbols"] == ["COIN"], out["sell_recheck"]
        rs = out["resume_state"]
        assert rs["planned_buys"] == {} and rs["ctx"]["profit_taking_sells"] == [] and rs["ctx"]["cleanup_sells"] == []
    print("[cli] sell-recheck rewrote plan_result.json: no sells, COIN dropped, buy removed — OK")


if __name__ == "__main__":
    test_plan_stamps_min_sell_price()
    test_coin_drop_drops_both_sells()
    test_price_holds_keeps_sells()
    test_margin_is_applied()
    test_missing_quote_fails_closed()
    test_liquidations_never_rechecked()
    test_net_exit_floor_is_lot_weighted_break_even()
    test_cli_round_trip()
    print("\nSMOKE TEST (pre-sell re-quote check, v2.91.0) PASSED")
