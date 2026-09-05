"""Coverage for v2.84.0 — Deferred Wash-Sale Loss Tracking (CLAUDE.md Step 7, observational).

The chain under test:
  1. A v2.83.0 net-profit full exit hands the netted underwater-lot loss to its TradeIntent, and
     the Step 6 state update stamps it into peak/prices.json (lastNettedLoss*).
  2. A later buy of that symbol inside wash_sale_lookback_days produces a REPURCHASE note and
     arms washVerifyPending (note_wash_window_repurchases). Outside the window: nothing.
  3. On a following cycle, verify_deferred_losses compares the new lot's basis against the buy
     quote and reports verified / not_detected / pending / expired, clearing the pending record
     in every case except pending.
  4. The new fields round-trip through peak/prices.json (including a legacy file that lacks
     them) and through the plan->finalize resume blob; the journal renders the section.

Nothing here touches a decision or a basis figure — that is the whole point of the feature.

Run: PYTHONPATH=. python3 bot/_smoke_test_deferred_loss_tracking.py
"""
from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from bot import cli, journal
from bot.config import AssetTarget, PortfolioConfig, PortfolioMetadata
from bot.models import Position, Quote, RunContext, TaxLot, TradeIntent
from bot.serialize import ctx_from_jsonable, ctx_to_jsonable
from bot.state import AssetPriceState, load_price_state, save_price_state
from bot.steps import note_wash_window_repurchases, step4_profit_taking, verify_deferred_losses


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0,
        max_portfolio_percentage=90.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=15000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, fifty_two_week_high_guard=1000.0, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, leg2_price_change=0.5, leg3_price_change=0.1, leg1_price_change=0.5,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=1e9,
        profit_resell_cooldown_days=15,
        selling_price_change=0.1,
        sell_or_buy_value_limit=1, min_value_of_trade=1,
        materialize_profit_percentage=2.5, materialize_profit_percentage_max=2.5,
        materialize_profit_in_dollars=1e9, materialize_profit_in_dollars_max=1e9,
        profit_threshold_ramp_days=30,
        profit_sell_percentage=100.0,
        min_raw_gain_percent_to_sell=0.5,
        keep_aside_profits_for_tax_percent=30.0,
        momentum_lookback_days=5,
        min_momentum_score_to_fill_underweight=-1000.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=30,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    def __init__(self, lots: dict):
        self._lots = lots

    def get_tax_lots(self, account_number: str, symbol: str):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol: str, start, end):
        return [58.0, 58.5, 59.0, 59.5, 60.0]


def _ctx(sym: str, today: date, price: float, quantity: float, avg_cost: float | None = None,
         price_state: AssetPriceState | None = None) -> RunContext:
    cfg = PortfolioConfig(meta=_meta(), targets={sym: AssetTarget(symbol=sym, weight=1.0)}, force_sell={}, blocked=[])
    ctx = RunContext(current_date=today, config=cfg, account_number="TEST")
    if quantity > 0:
        ctx.positions = {sym: Position(symbol=sym, quantity=quantity, avg_cost_basis=avg_cost)}
    ctx.quotes = {sym: Quote(symbol=sym, last_trade_price=price)}
    ctx.price_state = {sym: price_state or AssetPriceState()}
    return ctx


# The operator's MU example: one lot $10 underwater, one lot $120 in profit, net +$110.
_MU_LOTS = [
    TaxLot(open_lot_id="loss", quantity=1.0, cost_per_share=110.0, open_date=date(2026, 8, 20), is_selectable=True),
    TaxLot(open_lot_id="gain", quantity=2.0, cost_per_share=40.0, open_date=date(2026, 8, 1), is_selectable=True),
]


def test_full_exit_stamps_netted_loss_into_state() -> None:
    ctx = _ctx("MU", date(2026, 9, 4), price=100.0, quantity=3.0, avg_cost=(110.0 + 80.0) / 3)
    step4_profit_taking(ctx, _Broker({"MU": _MU_LOTS}))
    t = ctx.profit_taking_sells[0]
    assert abs(t.netted_loss_dollars - 10.0) < 1e-9 and t.netted_loss_shares == 1.0, t

    cli._update_profit_sell_and_purchase_dates(ctx)
    st = ctx.price_state["MU"]
    assert st.lastNettedLossDollars == 10.0 and st.lastNettedLossShares == 1.0
    assert st.lastNettedLossDate == "2026-09-04"
    assert st.lastLossSaleDate is None  # still not a loss sale — the v2.83.0 guarantee holds
    print("[stamp] net-profit full exit -> lastNettedLossDollars=10.00 / 1 sh / 2026-09-04; no wash-sale arming")


def test_repurchase_inside_window_notes_and_arms_pending() -> None:
    st = AssetPriceState(lastNettedLossDollars=10.0, lastNettedLossShares=1.0, lastNettedLossDate="2026-09-04")
    ctx = _ctx("MU", date(2026, 9, 10), price=105.0, quantity=0.0, price_state=st)
    ctx.buys = [TradeIntent(symbol="MU", side="buy", dollar_amount=500.0)]

    notes = note_wash_window_repurchases(ctx)
    assert len(notes) == 1 and notes[0].kind == "repurchase" and notes[0].symbol == "MU", notes
    assert "6d after the 2026-09-04" in notes[0].text and "$10.00" in notes[0].text, notes[0].text
    pending = ctx.price_state["MU"].washVerifyPending
    assert pending == {
        "purchaseDate": "2026-09-10", "buyQuotePrice": 105.0, "expectedLossDollars": 10.0,
        "exitDate": "2026-09-04", "exitShares": 1.0,
    }, pending
    print(f"[repurchase-in-window] note + washVerifyPending armed: {pending}")


def test_repurchase_outside_window_or_without_record_is_silent() -> None:
    st = AssetPriceState(lastNettedLossDollars=10.0, lastNettedLossShares=1.0, lastNettedLossDate="2026-08-01")
    ctx = _ctx("MU", date(2026, 9, 10), price=105.0, quantity=0.0, price_state=st)  # 40d > 30d
    ctx.buys = [TradeIntent(symbol="MU", side="buy", dollar_amount=500.0)]
    assert note_wash_window_repurchases(ctx) == [] and ctx.price_state["MU"].washVerifyPending is None

    ctx2 = _ctx("MU", date(2026, 9, 10), price=105.0, quantity=0.0)  # no netted-loss record at all
    ctx2.buys = [TradeIntent(symbol="MU", side="buy", dollar_amount=500.0)]
    assert note_wash_window_repurchases(ctx2) == [] and ctx2.price_state["MU"].washVerifyPending is None
    print("[repurchase-silent] outside the window / no record -> no note, nothing armed")


def _pending() -> AssetPriceState:
    return AssetPriceState(
        lastNettedLossDollars=10.0, lastNettedLossShares=1.0, lastNettedLossDate="2026-09-04",
        washVerifyPending={"purchaseDate": "2026-09-10", "buyQuotePrice": 105.0,
                           "expectedLossDollars": 10.0, "exitDate": "2026-09-04", "exitShares": 1.0},
    )


def test_verify_detects_the_adjustment() -> None:
    qty = 500.0 / 105.0                       # what $500 bought at the $105 quote
    adjusted_cost = 105.0 + 10.0 / qty        # Robinhood added the $10 deferral to the lot
    ctx = _ctx("MU", date(2026, 9, 11), price=106.0, quantity=qty, avg_cost=adjusted_cost, price_state=_pending())
    lots = [TaxLot(open_lot_id="new", quantity=qty, cost_per_share=adjusted_cost, open_date=date(2026, 9, 10), is_selectable=True)]

    notes = verify_deferred_losses(ctx, _Broker({"MU": lots}))
    assert len(notes) == 1 and notes[0].kind == "verified", notes
    assert "uplift $10.00" in notes[0].text, notes[0].text
    assert ctx.price_state["MU"].washVerifyPending is None
    print(f"[verify-present] {notes[0].text[:90]}...")


def test_verify_reports_missing_adjustment() -> None:
    qty = 500.0 / 105.0
    ctx = _ctx("MU", date(2026, 9, 11), price=106.0, quantity=qty, avg_cost=105.0, price_state=_pending())
    lots = [TaxLot(open_lot_id="new", quantity=qty, cost_per_share=105.0, open_date=date(2026, 9, 10), is_selectable=True)]

    notes = verify_deferred_losses(ctx, _Broker({"MU": lots}))
    assert len(notes) == 1 and notes[0].kind == "not_detected", notes
    assert "uplift $0.00" in notes[0].text and "expected ≈ $10.00" in notes[0].text, notes[0].text
    assert ctx.price_state["MU"].washVerifyPending is None
    print("[verify-not-detected] lot basis equals the quote -> NOT DETECTED, check dropped")


def test_verify_waits_while_lot_unpriced_then_expires() -> None:
    qty = 500.0 / 105.0
    unpriced = [TaxLot(open_lot_id="new", quantity=qty, cost_per_share=None, open_date=date(2026, 9, 10), is_selectable=False)]

    ctx = _ctx("MU", date(2026, 9, 11), price=106.0, quantity=qty, avg_cost=105.0, price_state=_pending())
    notes = verify_deferred_losses(ctx, _Broker({"MU": unpriced}))
    assert notes[0].kind == "pending" and ctx.price_state["MU"].washVerifyPending is not None, notes

    ctx2 = _ctx("MU", date(2026, 9, 25), price=106.0, quantity=0.0, price_state=_pending())  # sold again, 15d later
    notes2 = verify_deferred_losses(ctx2, _Broker({}))
    assert notes2[0].kind == "expired" and ctx2.price_state["MU"].washVerifyPending is None, notes2
    print("[verify-pending/expired] unpriced lot -> PENDING (kept); no lot after 10d -> EXPIRED (cleared)")


def test_state_file_round_trip_and_legacy_load() -> None:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "prices.json"
        save_price_state({"MU": _pending(), "AAPL": AssetPriceState(peakPrice=1.0)}, p)
        back = load_price_state(p)
        assert back["MU"].washVerifyPending["purchaseDate"] == "2026-09-10"
        assert back["MU"].lastNettedLossDollars == 10.0
        assert back["AAPL"].washVerifyPending is None and back["AAPL"].lastNettedLossDate is None

        # A pre-v2.84.0 file has none of the new keys — it must still load, with None defaults.
        p.write_text('{"MU": {"peakPrice": 5.0, "peakDate": "2026-09-01", "liquidatedPrice": "", '
                     '"liquidatedDate": null, "profitSellPrice": null, "profitSellDate": null, '
                     '"lastPurchaseDate": null, "lastLossSalePrice": null, "lastLossSaleDate": null}}')
        legacy = load_price_state(p)
        assert legacy["MU"].lastNettedLossDollars is None and legacy["MU"].washVerifyPending is None
    print("[state-roundtrip] new fields persist; legacy peak/prices.json without them still loads")


def test_resume_blob_round_trip_and_journal_render() -> None:
    ctx = _ctx("MU", date(2026, 9, 4), price=100.0, quantity=3.0, avg_cost=(110.0 + 80.0) / 3)
    step4_profit_taking(ctx, _Broker({"MU": _MU_LOTS}))
    ctx.deferred_loss_notes = verify_deferred_losses(ctx, _Broker({}))  # nothing pending -> []
    blob = ctx_to_jsonable(ctx)
    back = ctx_from_jsonable(blob, ctx.config)
    assert back.profit_taking_sells[0].netted_loss_dollars == ctx.profit_taking_sells[0].netted_loss_dollars
    assert back.deferred_loss_notes == []

    # Render both entry shapes with a note present and absent.
    ctx.buys = []
    md = journal.render_entry(ctx)
    assert "## Deferred Wash-Sale Loss Tracking (v2.84.0, observational)" in md and "- none this cycle" in md
    st = _pending()
    ctx2 = _ctx("MU", date(2026, 9, 10), price=105.0, quantity=0.0, price_state=st)
    ctx2.buys = [TradeIntent(symbol="MU", side="buy", dollar_amount=500.0)]
    ctx2.deferred_loss_notes = note_wash_window_repurchases(ctx2)
    md2 = journal.render_no_trades_entry(ctx2)
    assert "[REPURCHASE INSIDE WASH-SALE WINDOW]" in md2, md2
    assert "Deferred wash-sale loss notes: 1." in journal.render_email_summary(ctx2)
    assert "Deferred wash-sale loss notes" not in journal.render_email_summary(ctx)
    print("[serialize+journal] notes and intent fields round-trip; section renders in both entry shapes")


def main() -> None:
    test_full_exit_stamps_netted_loss_into_state()
    test_repurchase_inside_window_notes_and_arms_pending()
    test_repurchase_outside_window_or_without_record_is_silent()
    test_verify_detects_the_adjustment()
    test_verify_reports_missing_adjustment()
    test_verify_waits_while_lot_unpriced_then_expires()
    test_state_file_round_trip_and_legacy_load()
    test_resume_blob_round_trip_and_journal_render()
    print("\nSMOKE TEST (v2.84.0 deferred wash-sale loss tracking) PASSED")


if __name__ == "__main__":
    main()
