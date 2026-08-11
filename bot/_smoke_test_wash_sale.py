"""Focused coverage for the wash-sale-avoidance guards (CLAUDE.md `wash_sale_lookback_days`):

1. Forward buy-guard (Step 2, step2_guardrails): blocks a NEW BUY of a symbol for
   `wash_sale_lookback_days` days after ANY sell that realized a loss (peak/prices.json's
   lastLossSalePrice/lastLossSaleDate) — independent of, and stacks with, the existing
   profit-sell buy-guard.
2. Backward sell-guard (Step 4, _size_overweight_trims): the ONE deliberate-but-not-urgent path
   that can realize a loss is a forceSell-driven Overweight trim (routine trims/GTP/MRT are all
   profit-gated by construction). If ANY tax lot of that symbol was opened within
   `wash_sale_lookback_days` days, the loss sale is skipped entirely rather than locking in a
   disallowed loss.
3. Emergency stops (Drawdown Audit, Fresh Alpha Leader Stop, blocked+forceSell liquidation)
   remain UNCONDITIONAL — wash sale only defers tax recognition, it doesn't forfeit it, so a
   stop-loss must never be blocked on wash-sale grounds. This is a design absence, not a
   guard: Step 1 has no backward-looking check at all for these liquidations.
4. Step 7 state-writing (cli._update_peak_prices / main._update_price_state) stamps
   lastLossSalePrice/lastLossSaleDate for every symbol in ctx.loss_sale_symbols, which is what
   arms guard #1 on a future cycle.

Run: PYTHONPATH=. python3 bot/_smoke_test_wash_sale.py
"""
from __future__ import annotations

from datetime import date

from bot.cli import _update_peak_prices
from bot.config import AssetTarget, ForceSellEntry, PortfolioConfig, PortfolioMetadata
from bot.main import _update_price_state
from bot.models import DriftResult, Position, Quote, RunContext, TaxLot
from bot.state import AssetPriceState
from bot import steps


def _meta(**overrides) -> PortfolioMetadata:
    base = dict(
        global_drift_tolerance=1.0, max_trailing_drawdown_percentage=35,
        min_recovery_price_percentage=5.0, reinvestment_multiplier_factor=1.25,
        max_portfolio_percentage=90.0, alpha_cash_allocation_percentage=0.0,
        min_cash_absolute=0, min_cash_target=500, seek_approval_value=1_000_000,
        sell_price_diff_limit=5, buy_price_diff_limit=5, no_of_days_for_price_compare=3,
        cap_on_total_cash_balance_to_use=30000, cool_down_period_after_lquidation=6,
        beta_benchmark_symbol="SPY", beta_calculation_lookback_days=30,
        sold_asset_repurchase_days=2, z_score_points=0.5, z_score_upward_points=0.1,
        lock_in_period=2, overweight_sell_minimum_profit_margin_percent=1.0,
        overweight_sell_minimum_profit_margin_dollars=0.0,
        momentum_reversal_minimum_profit_margin_percent=1.0,
        momentum_reversal_minimum_profit_dollars=0.0,
        profit_resell_cooldown_days=15,
        z_score_sell_points=0.1,
        sell_or_buy_value_limit=10, min_value_of_trade=0,
        materialize_profit_percentage=2.0, profit_sell_percentage=50.0,
        materialize_profit_in_dollars=0.0, keep_aside_profits_for_tax_percent=35.0,
        momentum_lookback_days=5, momentum_reversal_threshold=-10.0,
        minimum_alpha_leader_sell_profit=0.0, alpha_leader_least_momentum_score=-1000.0,
        alpha_rank_reduction_percent=0.0, min_momentum_score_to_fill_underweight=-1000.0,
        alpha_leader_fresh_position_days=3, alpha_leader_fresh_drawdown_percentage=15.0,
        max_sector_percentage=0.0,
        wash_sale_lookback_days=30,
        dormant_asset_days=5,
    )
    base.update(overrides)
    return PortfolioMetadata(**base)


class _Broker:
    """Minimal BrokerClient stub for step2_guardrails/step4_profit_taking coverage."""

    def __init__(self, positions=None, quotes=None, lots=None):
        self._positions = positions or {}
        self._quotes = quotes or {}
        self._lots = lots or {}

    def get_positions(self, account_number):
        return dict(self._positions)

    def get_quotes(self, symbols):
        return {s: self._quotes[s] for s in symbols}

    def get_tax_lots(self, account_number, symbol):
        return self._lots.get(symbol, [])

    def get_daily_closes(self, symbol, start, end):
        return []  # empty history -> Z-score guards fail closed (not exercised here) / beta=0

    def get_buying_power(self, account_number):
        return 10_000.0

    def get_cash_ledger(self, account_number):
        return 10_000.0

    def get_realized_pnl_ytd(self, account_number, year_start, as_of):
        return 0.0


# ------------------------------------------------------------------------------------------
# 1. Forward buy-guard (Step 2)
# ------------------------------------------------------------------------------------------

def _step2_ctx(loss_sale_date: str, current_date: date, **meta_overrides) -> RunContext:
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides),
        targets={"SYM": AssetTarget("SYM", weight=1.0)},
        force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=current_date, config=cfg, account_number="TEST")
    ctx.price_state = {
        "SYM": AssetPriceState(lastLossSalePrice=90.0, lastLossSaleDate=loss_sale_date),
    }
    ctx.positions = {}
    ctx.quotes = {"SYM": Quote("SYM", last_trade_price=95.0)}
    ctx.excluded_symbols = {}
    ctx.buy_guarded_symbols = {}
    steps.step2_guardrails(ctx, _Broker())
    return ctx


def test_forward_guard_blocks_buy_within_window() -> None:
    """Loss-sold 10 days ago, wash_sale_lookback_days=30 -> still inside the window -> buy-guarded."""
    ctx = _step2_ctx(loss_sale_date="2026-07-28", current_date=date(2026, 8, 7))
    assert "SYM" in ctx.buy_guarded_symbols, ctx.buy_guarded_symbols
    assert "wash sale" in ctx.buy_guarded_symbols["SYM"].lower()
    print(f"[wash-forward-blocks] {ctx.buy_guarded_symbols['SYM']}")


def test_forward_guard_clears_outside_window() -> None:
    """Loss-sold 40 days ago, wash_sale_lookback_days=30 -> window has elapsed -> not guarded."""
    ctx = _step2_ctx(loss_sale_date="2026-06-28", current_date=date(2026, 8, 7))
    assert "SYM" not in ctx.buy_guarded_symbols, ctx.buy_guarded_symbols
    print("[wash-forward-clears] loss-sold 40d ago (window=30d) -> buy-guard no longer active — OK")


def test_forward_guard_no_prior_loss_sale() -> None:
    """No lastLossSaleDate on record at all -> never guarded on this basis."""
    ctx = _step2_ctx(loss_sale_date=None, current_date=date(2026, 8, 7))
    assert "SYM" not in ctx.buy_guarded_symbols, ctx.buy_guarded_symbols
    print("[wash-forward-no-record] no lastLossSaleDate on record -> not guarded — OK")


# ------------------------------------------------------------------------------------------
# 2. Backward sell-guard (Step 4, forceSell-driven Overweight trim)
# ------------------------------------------------------------------------------------------

def _step4_ctx(lot_open_date: date, current_date=date(2026, 8, 7), **meta_overrides) -> RunContext:
    """AAPL: overweight, underwater vs. avg_cost_basis (a loss), forceSell-listed with no
    triggerPrice (override always active) so it reaches the ranking/sizing stage despite being
    underwater — the only path capable of a loss sale."""
    cfg = PortfolioConfig(
        meta=_meta(**meta_overrides),
        targets={"AAPL": AssetTarget("AAPL", weight=1.0)},
        force_sell={"AAPL": ForceSellEntry(asset="AAPL")}, blocked=[],
    )
    ctx = RunContext(current_date=current_date, config=cfg, account_number="TEST")
    ctx.positions = {"AAPL": Position(symbol="AAPL", quantity=10.0, avg_cost_basis=300.0)}
    ctx.quotes = {"AAPL": Quote(symbol="AAPL", last_trade_price=260.0)}
    ctx.price_state = {"AAPL": AssetPriceState()}
    ctx.account_balance = 10_000.0
    ctx.drift_results = {
        "AAPL": DriftResult(
            symbol="AAPL", current_percentage=90.0, actual_weight=5.0, target_weight=1.1,
            target_percentage=10.0, drift=3.9, asset_drift_tolerance=0.5, market_value=2600.0,
        ),
    }
    ctx.harvest_needed_dollars = 500.0
    lots = {"AAPL": [
        TaxLot(open_lot_id="AAPL-lot1", quantity=10.0, cost_per_share=300.0,
               open_date=lot_open_date, is_selectable=True),
    ]}
    broker = _Broker(positions=ctx.positions, quotes=ctx.quotes, lots=lots)
    steps.step4_profit_taking(ctx, broker)
    return ctx


def test_backward_guard_blocks_loss_sale_with_recent_lot() -> None:
    """The only lot was opened 5 days ago (well within wash_sale_lookback_days=30) -> the loss
    sale is skipped entirely, not placed under a disallowed loss."""
    ctx = _step4_ctx(lot_open_date=date(2026, 8, 2))  # 5 days before current_date
    assert all(t.symbol != "AAPL" for t in ctx.overweight_trims), ctx.overweight_trims
    assert any(s.symbol == "AAPL" and "wash sale" in s.reason.lower() for s in ctx.skipped), ctx.skipped
    assert "AAPL" not in ctx.loss_sale_symbols, "skipped sale must not arm the forward buy-guard"
    print("[wash-backward-blocks] recent lot (5d old) -> loss sale skipped, wash-sale guard fired — OK")


def test_backward_guard_allows_loss_sale_with_old_lot() -> None:
    """The only lot was opened 60 days ago (outside the 30-day window) -> no wash-sale risk ->
    the loss sale proceeds normally and arms loss_sale_symbols for the forward buy-guard."""
    ctx = _step4_ctx(lot_open_date=date(2026, 6, 8))  # 60 days before current_date
    assert any(t.symbol == "AAPL" for t in ctx.overweight_trims), ctx.overweight_trims
    assert "AAPL" in ctx.loss_sale_symbols, ctx.loss_sale_symbols
    print("[wash-backward-allows] old lot (60d, outside 30d window) -> loss sale proceeds, arms forward guard — OK")


# ------------------------------------------------------------------------------------------
# 3. Emergency stops remain unconditional (no backward-looking wash-sale check in Step 1)
# ------------------------------------------------------------------------------------------

class _Step1Broker:
    def __init__(self, positions, quotes):
        self._positions = positions
        self._quotes = quotes

    def get_positions(self, account_number):
        return self._positions

    def get_quotes(self, symbols):
        return self._quotes

    def get_tax_lots(self, account_number, symbol):
        return []

    def get_buying_power(self, account_number):
        return 1000.0

    def get_cash_ledger(self, account_number):
        return 1000.0

    def get_realized_pnl_ytd(self, account_number, year_start, as_of):
        return 0.0


def test_drawdown_stop_unconditional_despite_wash_sale_risk() -> None:
    """A Drawdown Audit liquidation fires and arms loss_sale_symbols purely from being a genuine
    loss vs. avg_cost_basis -- there is no lot-recency check gating it (unlike the backward
    Overweight-trim guard above), confirming the stop is unconditional even though, in reality,
    this symbol might also have a recent purchase lot outstanding."""
    cfg = PortfolioConfig(
        meta=_meta(), targets={"DROP": AssetTarget("DROP", weight=1.0)}, force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.price_state = {"DROP": AssetPriceState(peakPrice=100.0)}
    ctx.positions = {"DROP": Position(symbol="DROP", quantity=10.0, avg_cost_basis=100.0)}
    ctx.quotes = {"DROP": Quote(symbol="DROP", last_trade_price=60.0)}  # -40% vs. both peak and cost
    broker = _Step1Broker(ctx.positions, ctx.quotes)
    steps.step1_fetch_state(ctx, broker, repo_dir="/nonexistent")
    assert ctx.drawdown_liquidations == ["DROP"], ctx.drawdown_liquidations
    assert "DROP" in ctx.loss_sale_symbols, ctx.loss_sale_symbols
    print("[wash-drawdown-unconditional] Drawdown Audit fires + arms loss_sale_symbols regardless of wash-sale risk — OK")


# ------------------------------------------------------------------------------------------
# 4. Step 7 state writes stamp lastLossSalePrice/Date
# ------------------------------------------------------------------------------------------

def test_cli_stamps_loss_sale_state() -> None:
    cfg = PortfolioConfig(
        meta=_meta(), targets={"SYM": AssetTarget("SYM", weight=1.0)}, force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.price_state = {"SYM": AssetPriceState()}
    ctx.quotes = {"SYM": Quote("SYM", last_trade_price=42.0)}
    ctx.loss_sale_symbols = ["SYM"]
    ctx.drawdown_liquidations = []
    ctx.blocked_liquidations = []
    ctx.fresh_alpha_leader_liquidations = []
    _update_peak_prices(ctx)
    assert ctx.price_state["SYM"].lastLossSalePrice == 42.0
    assert ctx.price_state["SYM"].lastLossSaleDate == "2026-08-07"
    print("[wash-cli-stamps] cli._update_peak_prices stamps lastLossSalePrice/Date — OK")


def test_main_stamps_loss_sale_state() -> None:
    cfg = PortfolioConfig(
        meta=_meta(), targets={"SYM": AssetTarget("SYM", weight=1.0)}, force_sell={}, blocked=[],
    )
    ctx = RunContext(current_date=date(2026, 8, 7), config=cfg, account_number="TEST")
    ctx.price_state = {"SYM": AssetPriceState()}
    ctx.quotes = {"SYM": Quote("SYM", last_trade_price=42.0)}
    ctx.positions = {}
    ctx.buys = []
    ctx.profit_taking_sells = []
    ctx.loss_sale_symbols = ["SYM"]
    ctx.drawdown_liquidations = []
    ctx.blocked_liquidations = []
    ctx.fresh_alpha_leader_liquidations = []
    _update_price_state(ctx)
    assert ctx.price_state["SYM"].lastLossSalePrice == 42.0
    assert ctx.price_state["SYM"].lastLossSaleDate == "2026-08-07"
    print("[wash-main-stamps] main._update_price_state stamps lastLossSalePrice/Date — OK")


def main() -> None:
    test_forward_guard_blocks_buy_within_window()
    test_forward_guard_clears_outside_window()
    test_forward_guard_no_prior_loss_sale()
    test_backward_guard_blocks_loss_sale_with_recent_lot()
    test_backward_guard_allows_loss_sale_with_old_lot()
    test_drawdown_stop_unconditional_despite_wash_sale_risk()
    test_cli_stamps_loss_sale_state()
    test_main_stamps_loss_sale_state()
    print("\nSMOKE TEST (wash sale guards) PASSED")


if __name__ == "__main__":
    main()
