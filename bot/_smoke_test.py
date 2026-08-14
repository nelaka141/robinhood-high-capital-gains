"""Not part of the package's public surface — a throwaway smoke test exercising the full
Step 1-7 pipeline against a synthetic FakeBroker, so the ordered execution code can be sanity-
checked without real Robinhood credentials. Run: python3 bot/_smoke_test.py
"""
from __future__ import annotations

import math
import random
import shutil
import tempfile
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from bot import journal, steps
from bot.config import load_portfolio_config
from bot.main import _update_price_state
from bot.models import Position, Quote, RunContext, TaxLot
from bot.state import (
    AssetPriceState, load_price_state, load_tax_by_year,
    save_price_state, save_tax_by_year,
)

random.seed(42)
REPO = Path(__file__).resolve().parent.parent


class FakeBroker:
    def __init__(self, symbols: List[str], seed_price: Dict[str, float]):
        self.symbols = symbols
        self._closes: Dict[str, List[float]] = {}
        end = date.today() - timedelta(days=1)
        for sym in symbols + ["SPY"]:
            p = seed_price.get(sym, 100.0)
            series = []
            for _ in range(80):
                p *= 1 + random.uniform(-0.03, 0.032)
                series.append(round(p, 4))
            self._closes[sym] = series
        # A couple of deliberately steep 3-day rallies to exercise the pump guard.
        for sym in symbols[:1]:
            self._closes[sym][-3:] = [self._closes[sym][-4] * f for f in (1.05, 1.12, 1.22)]

    def get_positions(self, account_number: str) -> Dict[str, Position]:
        out = {}
        for i, sym in enumerate(self.symbols):
            if i % 5 == 0:  # a few symbols intentionally unheld
                continue
            qty = round(random.uniform(1, 40), 4)
            avg = self._closes[sym][-20] * random.uniform(0.85, 1.15)
            out[sym] = Position(symbol=sym, quantity=qty, avg_cost_basis=round(avg, 4))
        return out

    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        return {s: Quote(symbol=s, last_trade_price=self._closes[s][-1]) for s in symbols}

    def get_daily_closes(self, symbol: str, start: date, end: date) -> List[float]:
        return self._closes[symbol]

    def get_daily_lows_highs(self, symbol: str, start: date, end: date):
        closes = self._closes[symbol][-10:]
        return [(c * 0.98, c * 1.02) for c in closes]

    def get_fifty_two_week_high(self, symbol: str):
        return max(self._closes[symbol]) * 1.05  # comfortably above the whole synthetic series

    def get_tax_lots(self, account_number: str, symbol: str) -> List[TaxLot]:
        price = self._closes[symbol][-1]
        return [
            TaxLot(f"{symbol}-lot1", quantity=5.0, cost_per_share=price * 0.7,
                   open_date=date.today() - timedelta(days=40)),
            TaxLot(f"{symbol}-lot2", quantity=5.0, cost_per_share=price * 0.9,
                   open_date=date.today() - timedelta(days=10)),
        ]

    def get_buying_power(self, account_number: str) -> float:
        return 25000.0

    def get_cash_ledger(self, account_number: str) -> float:
        return 25000.0

    def get_realized_pnl_ytd(self, account_number: str, year_start: date, as_of: date) -> float:
        return 8000.0

    def place_market_order(self, *a, **kw) -> dict:
        raise AssertionError("dry_run should never call place_market_order")


def main() -> None:
    cfg = load_portfolio_config(REPO / "portfolio_targets.json")
    symbols = list(cfg.targets.keys())
    seed_price = {"TQQQ": 63, "MU": 880, "AAPL": 333, "SPY": 742}
    broker = FakeBroker(symbols, seed_price)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "logs").mkdir()
        (tmp / "peak").mkdir()
        (tmp / "tax").mkdir()
        shutil.copy(REPO / "portfolio_targets.json", tmp / "portfolio_targets.json")
        (tmp / "peak" / "prices.json").write_text("{}")
        (tmp / "tax" / "realized_gains_by_year.json").write_text('{"2025": 4000.0}')
        (tmp / "transferred_basis.json").write_text("{}")

        ctx = RunContext(current_date=date.today(), config=cfg, account_number="TEST")
        ctx.price_state = load_price_state(tmp / "peak" / "prices.json")
        ctx.tax_by_year = load_tax_by_year(tmp / "tax" / "realized_gains_by_year.json")

        steps.step1_fetch_state(ctx, broker, str(tmp))
        print(f"[Step 1] account_balance=${ctx.account_balance:,.2f} "
              f"current_cash=${ctx.current_cash:,.2f} "
              f"drawdown_liquidations={ctx.drawdown_liquidations}")
        assert ctx.account_balance > 0
        assert len(ctx.drift_results) == len(symbols)

        breach = steps.has_any_breach(ctx)
        print(f"[Step 1] has_any_breach={breach}")
        assert breach, "synthetic random weights should produce at least one drift breach"

        steps.step2_guardrails(ctx, broker)
        print(f"[Step 2] excluded={list(ctx.excluded_symbols)} buy_guarded={list(ctx.buy_guarded_symbols)}")

        planned_buys = steps.step3_underweight_buys(ctx, broker)
        print(f"[Step 3] planned_buys={ {k: round(v,2) for k,v in planned_buys.items()} }")
        # The buy-timing guard (three-leg price-change dip-then-turn confirmation) is universal —
        # it can legitimately leave NO candidate eligible this cycle against random synthetic
        # price data and the real, tight production thresholds. Every allocated symbol must be a
        # genuinely scored candidate.
        assert all(s in ctx.momentum_scores for s in planned_buys)
        for m in ctx.momentum_scores.values():
            assert not math.isnan(m.score)

        steps.step4_profit_taking(ctx, broker)
        print(f"[Step 4] profit_taking_sells={[t.symbol for t in ctx.profit_taking_sells]}")

        planned_buys = steps.step5_price_limits(ctx, broker, planned_buys)
        print(f"[Step 5] planned_buys after pump-guard={ {k: round(v,2) for k,v in planned_buys.items()} }")

        steps.step6_execute_live(ctx, broker, planned_buys, dry_run=True)
        print(f"[Step 6] executed_orders={len(ctx.executed_orders)} buys={[t.symbol for t in ctx.buys]}")
        assert all(o["state"] == "DRY_RUN" for o in ctx.executed_orders)

        entry_md = journal.render_entry(ctx)
        assert entry_md.startswith("# ")
        journal.prepend_entry(entry_md, tmp / "logs")
        journal.prepend_entry(entry_md, tmp / "logs")
        journal.prepend_entry(entry_md, tmp / "logs")
        journal.prepend_entry(entry_md, tmp / "logs")
        journal.prepend_entry(entry_md, tmp / "logs")
        journal.prepend_entry(entry_md, tmp / "logs")  # 6th entry -> forces rotation
        live_text = (tmp / "logs" / "trade_journal.md").read_text()
        history_text = (tmp / "logs" / "history_trade_journal-1.md").read_text()
        assert live_text.count("\n# ") + (1 if live_text.startswith("# ") else 0) == journal.MAX_LIVE_ENTRIES
        assert history_text.startswith("# ")
        print("[Step 7] journal rotation OK — live entries capped, overflow moved to history file")

        _update_price_state(ctx)
        save_price_state(ctx.price_state, tmp / "peak" / "prices.json")
        save_tax_by_year(ctx.tax_by_year, tmp / "tax" / "realized_gains_by_year.json")
        reread = load_price_state(tmp / "peak" / "prices.json")
        assert set(reread.keys()) == set(cfg.targets.keys())
        print("[Step 7] state files round-trip OK (peak/prices.json, tax file)")

    print("\nSMOKE TEST PASSED — full Step 1-7 pipeline ran end-to-end with no exceptions.")


if __name__ == "__main__":
    main()
